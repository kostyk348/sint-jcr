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

    def ensure_home(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
