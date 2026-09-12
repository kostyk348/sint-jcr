"""Tests for the Nash-bargaining arbiter and the enantiodromia governor."""

from __future__ import annotations

import unittest

from jcr_core.arbiter import Arbiter, EnantiodromiaGovernor, Position


class ArbiterTest(unittest.TestCase):
    def test_infeasible_candidate_is_excluded(self) -> None:
        positions = [
            Position("a", {"x": 0.9, "y": 0.6}, 0.0),
            Position("b", {"x": 0.9, "y": 0.6}, 0.0),
            Position("c", {"x": 0.1, "y": 0.7}, 0.5),  # prefers failure over x
        ]
        res = Arbiter().arbitrate(positions, ["x", "y"])
        self.assertEqual(res.selected, "y")
        self.assertIn("y", res.feasible)
        self.assertNotIn("x", res.feasible)

    def test_deadlock_when_all_infeasible(self) -> None:
        positions = [Position("a", {"x": 0.1}, 0.9)]
        res = Arbiter().arbitrate(positions, ["x"])
        self.assertTrue(res.deadlock)
        self.assertIsNone(res.selected)

    def test_outcome_responds_to_disagreement(self) -> None:
        base = [Position("a", {"A": 0.8, "B": 0.7}, 0.0), Position("b", {"A": 0.5, "B": 0.6}, 0.0)]
        first = Arbiter().arbitrate(base, ["A", "B"])
        self.assertEqual(first.selected, "B")
        shifted = [Position("a", {"A": 0.8, "B": 0.7}, 0.75), Position("b", {"A": 0.5, "B": 0.6}, 0.0)]
        second = Arbiter().arbitrate(shifted, ["A", "B"])
        self.assertEqual(second.selected, "A")  # B became infeasible for a

    def test_minority_gains_weight(self) -> None:
        positions = [
            Position("strong", {"x": 1.0}, 0.0),
            Position("weak", {"x": 0.4}, 0.3),  # small surplus -> more bargaining power
        ]
        res = Arbiter().arbitrate(positions, ["x"])
        self.assertEqual(res.selected, "x")
        self.assertGreater(res.weights["weak"], res.weights["strong"])
        self.assertGreater(res.dissent["weak"], 0)

    def test_artifact_veto_is_recorded(self) -> None:
        positions = [Position("shadow", {"x": 0.0}, 0.5, artifact="repro://1042")]
        res = Arbiter().arbitrate(positions, ["x"])
        self.assertTrue(res.deadlock)
        self.assertEqual(res.vetoes[0]["artifact"], "repro://1042")


class GovernorTest(unittest.TestCase):
    def test_forcing_fires_after_threshold(self) -> None:
        g = EnantiodromiaGovernor(["abstract"], theta=1.0, K=0.5)
        for _ in range(2):
            g.observe({"abstract": 0.3})
        self.assertEqual(g.forcing()["abstract"], 0.0)  # below threshold
        for _ in range(3):
            g.observe({"abstract": 0.3})
        self.assertLess(g.forcing()["abstract"], 0.0)  # counter-force

    def test_anti_windup_bounds_the_integral(self) -> None:
        g = EnantiodromiaGovernor(["x"], theta=0.1, K=0.5, i_max=1.5)
        for _ in range(100):
            g.observe({"x": 1.0})
        self.assertLessEqual(g.I["x"], 1.5)

    def test_governor_steers_selection(self) -> None:
        g = EnantiodromiaGovernor(["abstract"], theta=0.5, K=1.0)
        for _ in range(3):
            g.observe({"abstract": 0.5})  # saturated -> forces the opposite pole
        positions = [Position("ego", {"high": 0.6, "low": 0.6}, 0.0)]
        axes = {"high": {"abstract": 1.0}, "low": {"abstract": -1.0}}
        res = Arbiter(g).arbitrate(positions, ["high", "low"], candidate_axes=axes)
        self.assertEqual(res.selected, "low")


if __name__ == "__main__":
    unittest.main()
