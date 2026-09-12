"""Tests for the Character Ledger — dispositions, relevance, drift."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.character import CharacterLedger


class CharacterLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ch = CharacterLedger(Path(self.tmp.name) / "character.db")

    def tearDown(self) -> None:
        self.ch.close()
        self.tmp.cleanup()

    def test_teach_and_list(self) -> None:
        t = self.ch.teach("prefer mechanism over metaphor", weight=0.9)
        self.assertEqual(self.ch.stats()["traits"], 1)
        self.assertEqual(self.ch.get(t.id).statement, "prefer mechanism over metaphor")

    def test_scope_relevance(self) -> None:
        self.ch.teach("prefer mechanism over metaphor", weight=0.9, scope="design architecture")
        self.ch.teach("check the premise before agreeing", weight=0.8, scope="feedback opinion")
        design = self.ch.traits_for("architecture design review", k=5)
        self.assertTrue(any("mechanism" in t.statement for t in design))
        cooking = self.ch.traits_for("pasta tomato recipe", k=5)
        self.assertFalse(any("mechanism" in t.statement for t in cooking))

    def test_global_scope_always_matches(self) -> None:
        self.ch.teach("say I don't know rather than guess", weight=0.7, scope="*")
        self.assertTrue(self.ch.traits_for("anything at all", k=5))

    def test_reinforce_moves_weight_and_reports_drift(self) -> None:
        t = self.ch.teach("be terse", weight=0.5)
        self.ch.reinforce(t.id, +0.3, evidence="turn-42")
        self.assertAlmostEqual(self.ch.get(t.id).weight, 0.8, places=6)
        drift = self.ch.drift()
        self.assertEqual(drift["traits"], 1)
        self.assertEqual(len(drift["movers"]), 1)
        self.assertAlmostEqual(drift["movers"][0]["drift"], 0.3, places=6)

    def test_weight_is_clamped(self) -> None:
        t = self.ch.teach("bounded", weight=0.9)
        self.ch.reinforce(t.id, +0.5)
        self.assertLessEqual(self.ch.get(t.id).weight, 1.0)

    def test_negative_polarity_preserved(self) -> None:
        t = self.ch.teach("avoid sycophancy", weight=0.8, polarity=-1.0)
        self.assertEqual(t.polarity, -1.0)


if __name__ == "__main__":
    unittest.main()
