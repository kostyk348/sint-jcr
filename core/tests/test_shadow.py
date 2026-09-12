"""Tests for the artifact Shadow (costly signaling)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.shadow import (
    CallableCritic,
    Critique,
    NullCritic,
    OracleVerifier,
    PatternCommandCritic,
    Shadow,
    ShadowLedger,
)


class ShadowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = ShadowLedger(Path(self.tmp.name) / "shadow.db")
        self.shadow = Shadow(PatternCommandCritic(), OracleVerifier(), self.ledger)

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_confirmed_artifact_vetoes(self) -> None:
        out = self.shadow.review("run this:\nrm -rf /\n")
        self.assertTrue(out["veto"])
        self.assertEqual(out["cheap_talk"], 0)
        self.assertEqual(self.ledger.stats()["confirmed"], 1)

    def test_clean_draft_passes(self) -> None:
        out = self.shadow.review("run this:\nls -la\n")
        self.assertFalse(out["veto"])
        self.assertEqual(out["critiques"], [])

    def test_cheap_talk_is_not_confirmed(self) -> None:
        talkative = CallableCritic(lambda d: [Critique(claim="this looks risky", artifact=None, severity=0.9)])
        s = Shadow(talkative, OracleVerifier(), self.ledger)
        out = s.review("anything")
        self.assertFalse(out["veto"])
        self.assertEqual(out["cheap_talk"], 1)
        self.assertEqual(self.ledger.stats()["confirmation_rate"], None)
        self.assertEqual(self.ledger.stats()["cheap_talk"], 1)

    def test_unconfirmed_artifact_does_not_veto(self) -> None:
        false_alarm = CallableCritic(lambda d: [Critique(claim="bad", artifact="ls -la", severity=0.9)])
        s = Shadow(false_alarm, OracleVerifier(), self.ledger)
        out = s.review("anything")
        self.assertFalse(out["veto"])

    def test_null_critic_never_vetoes(self) -> None:
        s = Shadow(NullCritic(), OracleVerifier(), self.ledger)
        out = s.review("rm -rf /")
        self.assertFalse(out["veto"])


if __name__ == "__main__":
    unittest.main()
