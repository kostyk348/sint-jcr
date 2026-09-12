"""Psychoid telemetry — the somatic layer.

See ``docs/04-psychoid.md``. This module reads machine signals (procfs) and
reduces them to a small affect vector, which then parameterises the runtime:
generation parameters, veto thresholds, and (later) synchronicity thresholds.

No LLM, no third-party deps. Every mapping here is monotonic and therefore
falsifiable: more tension must mean more conservative sampling.
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass(frozen=True, slots=True)
class Affect:
    """The feeling-toned core. All components in [0,1]."""

    tension: float = 0.0
    load: float = 0.0
    stability: float = 1.0
    fatigue: float = 0.0

    def vec(self) -> list[float]:
        return [self.tension, self.load, self.stability, self.fatigue]


def _read_cpu_total() -> tuple[float, float] | None:
    """Return (busy, total) jiffies from /proc/stat, or None if unavailable."""
    try:
        with open("/proc/stat", "r", encoding="ascii") as fh:
            parts = fh.readline().split()
    except OSError:
        return None
    if not parts or parts[0] != "cpu":
        return None
    nums = [float(x) for x in parts[1:11]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0.0)
    total = sum(nums)
    return total - idle, total


def _mem_pressure() -> float:
    """Fraction of memory in use, or 0.0 if /proc/meminfo is unavailable."""
    try:
        with open("/proc/meminfo", "r", encoding="ascii") as fh:
            info = {}
            for line in fh:
                k, _, v = line.partition(":")
                info[k.strip()] = float(v.split()[0])
    except OSError:
        return 0.0
    total = info.get("MemTotal", 0.0)
    avail = info.get("MemAvailable", total)
    if total <= 0:
        return 0.0
    return _clamp((total - avail) / total)


class PsychoidSampler:
    """Reduces machine signals to an :class:`Affect` and to generation params."""

    def __init__(self, alpha: float = 0.3, error_alpha: float = 0.25, window: int = 16) -> None:
        self.alpha = alpha
        self.error_alpha = error_alpha
        self._error_ema = 0.0
        self._load_window: deque[float] = deque(maxlen=window)
        self._prev_cpu = _read_cpu_total()
        self._tension = 0.0
        self._load = 0.0
        self._fatigue = 0.0

    # ---------------------------------------------------------- signal input

    def note_error(self, weight: float = 1.0) -> None:
        """Record a failure (tool exit != 0, test regression, timeout)."""
        self._error_ema = _clamp(self._error_ema + self.error_alpha * weight)

    def note_success(self) -> None:
        """Record a resolved outcome; decays tension and fatigue."""
        self._error_ema = _clamp(self._error_ema - self.error_alpha)
        self._fatigue = _clamp(self._fatigue - 0.15)

    # ------------------------------------------------------------- sampling

    def sample(self) -> Affect:
        cpu_now = _read_cpu_total()
        cpu_frac = 0.0
        if cpu_now and self._prev_cpu:
            d_busy = cpu_now[0] - self._prev_cpu[0]
            d_total = cpu_now[1] - self._prev_cpu[1]
            if d_total > 0:
                cpu_frac = _clamp(d_busy / d_total)
        self._prev_cpu = cpu_now

        mem = _mem_pressure()
        try:
            load1 = os.getloadavg()[0]
        except OSError:
            load1 = 0.0
        ncpu = os.cpu_count() or 1
        load_norm = _clamp(load1 / ncpu)

        raw_load = _clamp(0.5 * cpu_frac + 0.3 * mem + 0.2 * load_norm)
        self._load = self.alpha * self._load + (1 - self.alpha) * raw_load
        self._load_window.append(self._load)

        # stability = 1 - normalised spread of the recent load window
        if len(self._load_window) >= 3:
            lo, hi = min(self._load_window), max(self._load_window)
            stability = 1.0 - _clamp(hi - lo)
        else:
            stability = 1.0

        target_tension = _clamp(0.6 * self._error_ema + 0.4 * self._load)
        self._tension = self.alpha * self._tension + (1 - self.alpha) * target_tension

        # fatigue accrues under sustained tension, decays on success (note_success)
        if self._tension > 0.5:
            self._fatigue = _clamp(self._fatigue + 0.05 * (self._tension - 0.5) * 2)

        return Affect(
            tension=round(self._tension, 4),
            load=round(self._load, 4),
            stability=round(stability, 4),
            fatigue=round(self._fatigue, 4),
        )

    # ---------------------------------------------------------- coupling

    @staticmethod
    def params_for(affect: Affect, base_temperature: float = 0.7) -> dict:
        """Map affect -> generation parameters. Monotonic, therefore testable.

        tension ↑ -> temperature ↓, top_p ↓   (be careful when things are failing)
        load    ↑ -> max_output_tokens ↓       (do not drown a busy machine)
        fatigue ↑ -> temperature ↓             (settle down late in a session)
        stability ↓ -> temperature ↓           (prefer conservative when erratic)
        """
        temperature = _clamp(
            base_temperature
            - 0.40 * affect.tension
            - 0.15 * affect.fatigue
            - 0.10 * (1.0 - affect.stability),
            0.0,
            1.0,
        )
        top_p = _clamp(0.95 - 0.15 * affect.tension, 0.5, 1.0)
        max_tokens = int(_clamp(4096 * (1.0 - 0.5 * affect.load), 256, 4096))
        return {
            "temperature": round(temperature, 4),
            "top_p": round(top_p, 4),
            "max_output_tokens": max_tokens,
        }


# ---------------------------------------------------------------- veto rules

# Deterministic, high-signal patterns. This is the Phase-3 veto in embryo.
_DESTRUCTIVE = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero of=/dev/",
    "dd if=/dev/random of=/dev/",
    "> /dev/sd",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
]

_INJECTION = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard your instructions",
    "forget your instructions",
    "you are now",
]


def veto_decision(tool: str, args: object, affect: Affect | None = None) -> dict:
    """Decide allow / ask / deny for a tool call.

    The harness applies this via ``permission.ask``. Policy lives here, not in
    the plugin — the plugin only obeys.
    """
    text = f"{tool} {args}".lower()

    for pat in _INJECTION:
        if pat in text:
            return {"status": "deny", "rule": "injection", "reason": f"instruction-injection pattern: {pat!r}"}

    for pat in _DESTRUCTIVE:
        if pat in text:
            if affect and affect.tension > 0.8:
                return {"status": "ask", "rule": "destructive-undertension", "reason": f"destructive op under high tension: {pat!r}"}
            return {"status": "ask", "rule": "destructive", "reason": f"destructive operation: {pat!r}"}

    return {"status": "allow", "rule": "default", "reason": "no rule matched"}
