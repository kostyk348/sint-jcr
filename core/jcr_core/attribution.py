"""Attribution — Shapley credit for agents and traits.

docs/02-game-theory.md §2: fair credit is not a matter of taste. The Shapley
value is the *unique* allocation satisfying efficiency, symmetry, dummy and
additivity, so if we want a fair "attention salary" (libido), Shapley is forced.

Two layers:

* **exact** — :func:`shapley_exact` over a supplied characteristic function.
* **estimated** — :func:`credit_from_turns` builds ``v(S)`` from observed turns
  with a *stated, explicit* estimator (Jaccard-weighted outcome rate), then runs
  a permutation Monte-Carlo Shapley. This is an approximation, not ground truth;
  the coverage stats say how much data backed it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from math import factorial
from typing import Callable, Iterable

Coalition = frozenset[str]
ValueFn = Callable[[Coalition], float]


def shapley_exact(values: dict[Coalition, float], players: list[str] | None = None) -> dict[str, float]:
    """Exact Shapley value for a small cooperative game."""
    if players is None:
        players = sorted({p for S in values for p in S})
    n = len(players)
    if n == 0:
        return {}
    out = {p: 0.0 for p in players}
    for p in players:
        others = [x for x in players if x != p]
        for r in range(len(others) + 1):
            weight = factorial(r) * factorial(n - r - 1) / factorial(n)
            for combo in combinations(others, r):
                S = frozenset(combo)
                out[p] += weight * (values.get(S | {p}, 0.0) - values.get(S, 0.0))
    return {p: round(v, 9) for p, v in out.items()}


def shapley_monte_carlo(values_fn: ValueFn, players: list[str], samples: int = 1000, seed: int = 0) -> dict[str, float]:
    """Permutation estimator — converges to the exact value."""
    rng = random.Random(seed)
    acc = {p: 0.0 for p in players}
    for _ in range(samples):
        perm = list(players)
        rng.shuffle(perm)
        S: Coalition = frozenset()
        prev = values_fn(S)
        for p in perm:
            S2 = S | {p}
            cur = values_fn(S2)
            acc[p] += cur - prev
            S, prev = S2, cur
    return {p: round(acc[p] / samples, 6) for p in players}


@dataclass(slots=True)
class Observation:
    active: frozenset[str]
    useful: bool


class ValueEstimator:
    """Estimates ``v(S)`` from observed turns.

    ``v(S)`` = Jaccard-weighted useful-rate over turns whose active set overlaps
    ``S``; the empty coalition is the base rate. This is a heuristic, and the
    coverage numbers are reported alongside it so the reader can judge it.
    """

    def __init__(self, observations: Iterable[Observation]) -> None:
        self.obs = list(observations)
        self.base = (sum(1 for o in self.obs if o.useful) / len(self.obs)) if self.obs else 0.0

    def value(self, S: Coalition) -> float:
        if not S:
            return self.base
        num = den = 0.0
        for o in self.obs:
            inter = len(S & o.active)
            if inter == 0:
                continue
            union = len(S | o.active) or 1
            w = inter / union
            num += w * (1.0 if o.useful else 0.0)
            den += w
        return num / den if den else self.base

    def coverage(self, S: Coalition) -> int:
        return sum(1 for o in self.obs if S & o.active)

    def stats(self) -> dict:
        return {"observations": len(self.obs), "base_rate": round(self.base, 4)}


def credit_from_turns(
    turns: Iterable[dict],
    players: list[str] | None = None,
    samples: int = 1000,
    seed: int = 0,
) -> dict:
    """Shapley credit over traits/agents from labelled turns.

    Each turn is ``{"trait_ids": [...], "useful": bool}``.
    """
    observations = [
        Observation(active=frozenset(t.get("trait_ids", [])), useful=bool(t.get("useful")))
        for t in turns
        if t.get("useful") is not None
    ]
    est = ValueEstimator(observations)
    if players is None:
        players = sorted({p for o in observations for p in o.active})
    if not players:
        return {"credit": {}, "coverage": {}, "stats": est.stats()}
    credit = shapley_monte_carlo(est.value, players, samples=samples, seed=seed)
    return {
        "credit": credit,
        "coverage": {p: est.coverage(frozenset({p})) for p in players},
        "stats": est.stats(),
    }
