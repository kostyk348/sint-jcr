"""Tests for Shapley attribution."""

from __future__ import annotations

import itertools
import unittest

from jcr_core.attribution import Observation, ValueEstimator, credit_from_turns, shapley_exact, shapley_monte_carlo


def majority_game(players: list[str]) -> dict[frozenset, float]:
    values: dict[frozenset, float] = {}
    for r in range(len(players) + 1):
        for combo in itertools.combinations(players, r):
            values[frozenset(combo)] = 1.0 if len(combo) >= 2 else 0.0
    return values


class ExactShapleyTest(unittest.TestCase):
    def test_majority_game_symmetric(self) -> None:
        players = ["a", "b", "c"]
        credit = shapley_exact(majority_game(players), players)
        for p in players:
            self.assertAlmostEqual(credit[p], 1 / 3, places=6)

    def test_efficiency_sums_to_grand_coalition(self) -> None:
        players = ["a", "b", "c"]
        values = majority_game(players)
        credit = shapley_exact(values, players)
        self.assertAlmostEqual(sum(credit.values()), values[frozenset(players)], places=6)

    def test_dummy_player_gets_nothing(self) -> None:
        # d never changes the value: both a and b are required, d is irrelevant
        values = {
            frozenset(): 0.0,
            frozenset({"a"}): 0.0,
            frozenset({"b"}): 0.0,
            frozenset({"d"}): 0.0,
            frozenset({"a", "b"}): 1.0,
            frozenset({"a", "d"}): 0.0,
            frozenset({"b", "d"}): 0.0,
            frozenset({"a", "b", "d"}): 1.0,
        }
        credit = shapley_exact(values, ["a", "b", "d"])
        self.assertAlmostEqual(credit["d"], 0.0, places=6)
        self.assertAlmostEqual(credit["a"], 0.5, places=6)
        self.assertAlmostEqual(credit["b"], 0.5, places=6)


class MonteCarloTest(unittest.TestCase):
    def test_converges_to_exact(self) -> None:
        players = ["a", "b", "c"]
        values = majority_game(players)
        exact = shapley_exact(values, players)
        approx = shapley_monte_carlo(lambda S: values.get(S, 0.0), players, samples=4000, seed=7)
        for p in players:
            self.assertLess(abs(approx[p] - exact[p]), 0.05)


class ValueEstimatorTest(unittest.TestCase):
    def test_base_rate_and_conditional(self) -> None:
        obs = [
            Observation(frozenset({"a"}), True),
            Observation(frozenset({"a"}), True),
            Observation(frozenset({"b"}), False),
            Observation(frozenset({"b"}), False),
        ]
        est = ValueEstimator(obs)
        self.assertAlmostEqual(est.base, 0.5, places=6)
        self.assertGreater(est.value(frozenset({"a"})), est.value(frozenset({"b"})))
        self.assertEqual(est.coverage(frozenset({"a"})), 2)

    def test_credit_from_turns(self) -> None:
        turns = [
            {"trait_ids": ["t1"], "useful": True},
            {"trait_ids": ["t1"], "useful": True},
            {"trait_ids": ["t2"], "useful": False},
            {"trait_ids": ["t2"], "useful": False},
        ]
        report = credit_from_turns(turns, samples=500, seed=3)
        self.assertGreater(report["credit"]["t1"], report["credit"]["t2"])
        self.assertEqual(report["coverage"]["t1"], 2)

    def test_empty(self) -> None:
        self.assertEqual(credit_from_turns([])["credit"], {})


if __name__ == "__main__":
    unittest.main()
