"""Runtime configuration and paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_home() -> Path:
    env = os.environ.get("JCR_HOME")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "jcr"


@dataclass(slots=True)
class JCRConfig:
    """All tunables for the Phase 0 substrate.

    Every value here is a knob that a falsification test could perturb.
    """

    home: Path = _default_home()

    # --- bus (source of truth) ---
    # "eml"    : append-only hash-chained RFC822 spool (default; mesh/mail-ready)
    # "sqlite" : legacy SQLite table (kept for compatibility / as an index)
    bus_format: str = os.environ.get("JCR_BUS_FORMAT", "eml")

    # --- character ---
    character_traits_in_context: int = 5

    # --- synchronicity monitor (docs/06) ---
    monitor_d_min: float = 0.5
    monitor_s_min: float = 0.35
    monitor_precision_floor: float = 0.6
    monitor_hard: bool = os.environ.get("JCR_MONITOR_HARD", "") == "1"

    # --- embedding ---
    embed_dim: int = 256

    # --- energy dynamics (see docs/03-libido-ledger.md) ---
    beta: float = 0.8          # direct resonance gain
    gamma: float = 0.35        # neighbour propagation gain
    rho_min: float = 0.15      # resonance floor; below it contributes nothing
    noise: float = 0.005       # stochastic term (lets "cold" memories surface)

    # --- tiers ---
    hot_threshold: float = 0.60
    warm_threshold: float = 0.30
    cool_threshold: float = 0.10

    # --- repression ---
    repress_eps: float = 0.05          # energy below which a node starts aging out
    repress_seconds: float = 3 * 86400  # how long below eps before repression

    # --- scanning ---
    cold_sample: int = 64      # how many cold nodes to sample per inject

    def db_path(self) -> Path:
        return self.home / "jcr.db"

    def spool_dir(self) -> Path:
        """Directory of append-only `.eml` bus messages (EML-IPC compatible)."""
        return self.home / "bus"

    def character_path(self) -> Path:
        return self.home / "character.db"

    def dream_path(self) -> Path:
        return self.home / "dream.db"

    def invariant_path(self) -> Path:
        return self.home / "invariants.db"

    def shadow_path(self) -> Path:
        return self.home / "shadow.db"

    def ensure_home(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.spool_dir().mkdir(parents=True, exist_ok=True)
