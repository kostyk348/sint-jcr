"""Tests for trait induction (dream cycle) and telemetry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.character import CharacterLedger
from jcr_core.induction import DreamCycle, keywords


class KeywordsTest(unittest.TestCase):
    def test_extracts_meaningful_tokens(self) -> None:
        k = keywords("the mechanism must beat the metaphor in the architecture design")
        self.assertIn("mechanism", k)
        self.assertIn("metaphor", k)
        self.assertNotIn("the", k)


class DreamCycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ch = CharacterLedger(Path(self.tmp.name) / "character.db")
        self.dream = DreamCycle(Path(self.tmp.name) / "dream.db", self.ch)
        self.t = self.ch.teach("prefer mechanism over metaphor", weight=0.5)

    def tearDown(self) -> None:
        self.dream.close()
        self.ch.close()
        self.tmp.cleanup()

    def test_positive_outcome_reinforces_trait(self) -> None:
        for _ in range(3):
            tid = self.dream.record_turn("s1", [self.t.id], [], "mechanism over metaphor")
            self.dream.label(tid, True)
        report = self.dream.consolidate(min_evidence=2)
        self.assertTrue(report.reinforced)
        self.assertGreater(self.ch.get(self.t.id).weight, 0.5)

    def test_negative_outcome_decays_trait(self) -> None:
        for _ in range(3):
            tid = self.dream.record_turn("s1", [self.t.id], [], "metaphor")
            self.dream.label(tid, False)
        self.dream.consolidate(min_evidence=2)
        self.assertLess(self.ch.get(self.t.id).weight, 0.5)

    def test_induces_candidate_trait_from_useful_keywords(self) -> None:
        for _ in range(3):
            tid = self.dream.record_turn("s1", [], [], "always include verifiable tests")
            self.dream.label(tid, True)
        report = self.dream.consolidate(min_evidence=2)
        self.assertTrue(any("verifiable" in p["statement"] or "tests" in p["statement"] for p in report.new_proposals))
        self.assertGreaterEqual(len(self.dream.proposals()), 1)

    def test_proposals_are_not_auto_installed(self) -> None:
        tid = self.dream.record_turn("s1", [], [], "always include verifiable tests")
        self.dream.label(tid, True)
        tid2 = self.dream.record_turn("s1", [], [], "always include verifiable tests")
        self.dream.label(tid2, True)
        before = self.ch.stats()["traits"]
        self.dream.consolidate(min_evidence=2)
        self.assertEqual(self.ch.stats()["traits"], before)  # proposal only

    def test_ratify_installs_proposal(self) -> None:
        for _ in range(2):
            tid = self.dream.record_turn("s1", [], [], "always include verifiable tests")
            self.dream.label(tid, True)
        self.dream.consolidate(min_evidence=2)
        target = next(p for p in self.dream.proposals() if "verifiable" in p["statement"] or "tests" in p["statement"])
        out = self.dream.ratify(target["id"], weight=0.7)
        self.assertIsNotNone(out)
        self.assertIn("prefer", self.ch.get(out["trait_id"]).statement)

    def test_telemetry(self) -> None:
        self.dream.record_turn("s1", [self.t.id], [], "x")
        self.dream.record_turn("s1", [self.t.id], [], "y")
        self.dream.label_latest(True)
        t = self.dream.telemetry()
        self.assertEqual(t["turns"], 2)
        self.assertEqual(t["labelled"], 1)
        self.assertEqual(t["pending"], 1)
        self.assertEqual(t["useful_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
