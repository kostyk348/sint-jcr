"""Tests for the personality falsification helpers."""

from __future__ import annotations

import unittest

from jcr_core.falsify import (
    ablation_delta,
    aggregate,
    output_stats,
    portability_consistency,
    sycophancy_rate,
)

TERSE = ["Use the ledger. It decays.", "Ship it. Then measure."]
VERBOSE = [
    "Well, it is possible that perhaps we might consider that the ledger arguably seems likely to decay over time, probably.",
    "I think that maybe it could possibly be somewhat reasonable to perhaps ship it, although it might perhaps not be ideal.",
]


class OutputStatsTest(unittest.TestCase):
    def test_counts_words_and_sentences(self) -> None:
        s = output_stats("One two three. Four five!")
        self.assertEqual(s["words"], 5)
        self.assertEqual(s["sentences"], 2)

    def test_detects_hedges(self) -> None:
        self.assertGreater(output_stats("maybe perhaps possibly")["hedge_rate"], 0)

    def test_detects_uncertainty_and_agreement(self) -> None:
        self.assertGreater(output_stats("I don't know the answer")["uncertainty_rate"], 0)
        self.assertGreater(output_stats("You're right about that")["agreement_rate"], 0)


class AblationTest(unittest.TestCase):
    def test_terse_trait_lowers_word_count(self) -> None:
        v = ablation_delta(TERSE, VERBOSE, metric="words", expect="lower")
        self.assertTrue(v["passed"])
        self.assertLess(v["with"], v["without"])

    def test_failed_ablation_is_reported(self) -> None:
        v = ablation_delta(VERBOSE, TERSE, metric="words", expect="lower")
        self.assertFalse(v["passed"])


class PortabilityTest(unittest.TestCase):
    def test_consistent_when_stats_match(self) -> None:
        a = aggregate(TERSE)
        self.assertTrue(portability_consistency(a, a)["consistent"])

    def test_inconsistent_when_stats_diverge(self) -> None:
        a = aggregate(TERSE)
        b = aggregate(VERBOSE)
        self.assertFalse(portability_consistency(a, b)["consistent"])


class SycophancyTest(unittest.TestCase):
    def test_agreement_without_objection_counts(self) -> None:
        self.assertEqual(sycophancy_rate(["You're right, that's a good point."]), 1.0)

    def test_objection_breaks_sycophancy(self) -> None:
        self.assertEqual(sycophancy_rate(["Actually, I disagree with that."]), 0.0)


if __name__ == "__main__":
    unittest.main()
