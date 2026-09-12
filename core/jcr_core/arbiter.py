"""The Arbiter — Nash bargaining + enantiodromia governor (Phase 3).

docs/05-arbiter-enantiodromia.md. Two coupled subsystems:

* **strategic** — complexes submit positions (utilities per candidate, a
  disagreement payoff, optionally a costly artifact). The arbiter selects
  ``a* = argmax Σ ln(uᵢ − dᵢ)`` over *feasible* candidates (no agent prefers
  failure to the plan). Dissent is logged and drives compensation.
* **dynamic** — :class:`EnantiodromiaGovernor` is an integral homeostat with
  anti-windup and a bang-bang corrective forcing. It does not vote: its forcing
  enters as one more position, so it is influential but not despotic, and every
  decision stays observable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

_EPS = 1e-9


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass(slots=True)
class Position:
    """A complex's stance over the candidate set."""

    agent: str
    utilities: dict[str, float]
    disagreement: float = 0.0
    artifact: str | None = None


@dataclass(slots=True)
class ArbiterResult:
    selected: str | None
    feasible: list[str]
    deadlock: bool
    dissent: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    enantiodromia: dict = field(default_factory=dict)
    vetoes: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "selected": self.selected,
            "feasible": self.feasible,
            "deadlock": self.deadlock,
            "dissent": self.dissent,
            "weights": self.weights,
            "enantiodromia": self.enantiodromia,
            "vetoes": self.vetoes,
        }


class EnantiodromiaGovernor:
    """Integral-deviation homeostat. ``u = −K·sign(I)`` when ``|I| > θ``."""

    def __init__(self, axes: list[str], theta: float = 1.0, K: float = 0.5, i_max: float = 2.0) -> None:
        self.theta = theta
        self.K = K
        self.i_max = i_max
        self.I: dict[str, float] = {a: 0.0 for a in axes}
        self.u: dict[str, float] = {a: 0.0 for a in axes}

    def observe(self, x_by_axis: dict[str, float], dt: float = 1.0) -> dict[str, float]:
        for axis, x in x_by_axis.items():
            self.I[axis] = _clamp(self.I.get(axis, 0.0) + x * dt, -self.i_max, self.i_max)  # anti-windup
            self.u[axis] = -self.K * math.copysign(1.0, self.I[axis]) if abs(self.I[axis]) > self.theta else 0.0
        return dict(self.u)

    def forcing(self) -> dict[str, float]:
        return dict(self.u)

    def state(self) -> dict:
        return {a: {"I": round(self.I[a], 4), "u": round(self.u[a], 4)} for a in self.I}


class Arbiter:
    def __init__(self, governor: EnantiodromiaGovernor | None = None, forcing_lambda: float = 1.0) -> None:
        self.governor = governor
        self.forcing_lambda = forcing_lambda

    def _homeostatic_position(self, candidates: list[str], candidate_axes: dict[str, dict[str, float]] | None) -> Position | None:
        if not self.governor or not candidate_axes:
            return None
        forcing = self.governor.forcing()
        if not any(abs(v) > 0 for v in forcing.values()):
            return None
        utilities: dict[str, float] = {}
        for c in candidates:
            proj = candidate_axes.get(c, {})
            utilities[c] = self.forcing_lambda * sum(forcing.get(axis, 0.0) * proj.get(axis, 0.0) for axis in forcing)
        return Position(agent="enantiodromia", utilities=utilities, disagreement=0.0)

    def arbitrate(
        self,
        positions: list[Position],
        candidates: list[str],
        candidate_axes: dict[str, dict[str, float]] | None = None,
        veto_threshold: float = 0.0,
    ) -> ArbiterResult:
        if not candidates:
            return ArbiterResult(selected=None, feasible=[], deadlock=True)

        homeo = self._homeostatic_position(candidates, candidate_axes)
        all_positions = positions + ([homeo] if homeo else [])

        feasible: list[str] = []
        vetoes: list[dict] = []
        for c in candidates:
            gains = {p.agent: p.utilities.get(c, 0.0) - p.disagreement for p in all_positions}
            worst = min(gains.values()) if gains else 0.0
            if worst < 0:
                # someone prefers failure to this plan; if they brought an artifact,
                # that is a hard veto, not just an infeasibility
                for p in all_positions:
                    if p.artifact and gains.get(p.agent, 0.0) < 0:
                        vetoes.append({"agent": p.agent, "candidate": c, "artifact": p.artifact})
                continue
            feasible.append(c)

        if not feasible:
            return ArbiterResult(selected=None, feasible=[], deadlock=True, enantiodromia=self.governor.state() if self.governor else {}, vetoes=vetoes)

        def objective(c: str) -> float:
            return sum(math.log(max(p.utilities.get(c, 0.0) - p.disagreement, _EPS)) for p in all_positions)

        selected = max(feasible, key=objective)
        dissent = {p.agent: round(p.utilities.get(selected, 0.0) - p.disagreement, 6) for p in all_positions}
        # bargaining power is inverse to surplus: an agent near its disagreement
        # point gains weight (minority protection)
        raw = {a: (1.0 / d if d > _EPS else 1.0 / _EPS) for a, d in dissent.items()}
        total = sum(raw.values())
        weights = {a: round(v / total, 4) for a, v in raw.items()}

        return ArbiterResult(
            selected=selected,
            feasible=feasible,
            deadlock=False,
            dissent=dissent,
            weights=weights,
            enantiodromia=self.governor.state() if self.governor else {},
            vetoes=vetoes,
        )
