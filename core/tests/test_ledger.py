"""Tests for the Libido Ledger — the memory field."""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from jcr_core.config import JCRConfig
from jcr_core.embedding import HashingEmbedder, cosine
from jcr_core.ledger import LibidoLedger
from jcr_core.types import Register, Tier


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = JCRConfig(embed_dim=256)
        self.ledger = LibidoLedger(Path(self.tmp.name) / "ledger.db", self.cfg)

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_add_and_get_node(self) -> None:
        n = self.ledger.add_node("libido ledger energy decay", register=Register.LOGIC, project="JCR")
        got = self.ledger.get_node(n.id)
        self.assertIsNotNone(got)
        self.assertEqual(got.register, Register.LOGIC)
        self.assertEqual(got.project, "JCR")
        self.assertEqual(len(got.embedding), 256)

    def test_inject_ranks_similar_node_higher(self) -> None:
        relevant = self.ledger.add_node("libido ledger energy decay memory field", energy=0.2)
        unrelated = self.ledger.add_node("pasta tomato basil recipe", energy=0.2)
        acts = self.ledger.inject(self.ledger.embedder.embed("libido ledger energy decay memory field"), k=5)
        self.assertTrue(acts, "expected at least one activation")
        self.assertEqual(acts[0].node_id, relevant.id)
        self.assertNotEqual(acts[0].node_id, unrelated.id)
        self.assertGreater(self.ledger.get_node(relevant.id).energy, 0.2)

    def test_decay_follows_exponential(self) -> None:
        n = self.ledger.add_node("decay me", energy=0.5, tau=100.0)
        self.ledger.decay_tick(dt=100.0)
        self.assertAlmostEqual(self.ledger.get_node(n.id).energy, 0.5 * math.e**-1, places=3)

    def test_propagation_spreads_activation(self) -> None:
        a = self.ledger.add_node("source node", energy=1.0)
        b = self.ledger.add_node("target node", energy=0.1)
        self.ledger.add_edge(a.id, b.id, w=1.0, kind="assoc")
        self.ledger.propagate([a.id], hops=1)
        self.assertGreater(self.ledger.get_node(b.id).energy, 0.4)

    def test_reinforce_rewards_and_penalises(self) -> None:
        n = self.ledger.add_node("candidate", energy=0.5)
        self.ledger.reinforce([n.id], +0.1)
        self.assertAlmostEqual(self.ledger.get_node(n.id).energy, 0.6, places=6)
        self.ledger.reinforce([n.id], -0.25)
        self.assertAlmostEqual(self.ledger.get_node(n.id).energy, 0.35, places=6)

    def test_repression_is_not_deletion(self) -> None:
        cfg = JCRConfig(repress_eps=0.9, repress_seconds=0.0)
        ledger = LibidoLedger(Path(self.tmp.name) / "repress.db", cfg)
        try:
            n = ledger.add_node("fades away", energy=0.5)
            ledger.promote_or_repress(now=1000.0)  # starts the aging timer
            changes = ledger.promote_or_repress(now=1001.0)  # now past the window
            self.assertEqual(changes["repressed"], 1)
            node = ledger.get_node(n.id)
            self.assertEqual(node.tier, Tier.COLD)
            self.assertIsNotNone(node.content)  # still present, only cold
        finally:
            ledger.close()

    def test_energy_is_the_economy(self) -> None:
        self.assertEqual(self.ledger.budget("shadow"), 1.0)  # default account
        self.ledger.grant("shadow", 4.0)
        self.assertTrue(self.ledger.charge("shadow", 2.0))
        self.assertAlmostEqual(self.ledger.budget("shadow"), 3.0)
        self.assertFalse(self.ledger.charge("shadow", 10.0))
        self.assertAlmostEqual(self.ledger.budget("shadow"), 3.0)  # failed charge is a no-op

    def test_stats_report_tiers(self) -> None:
        self.ledger.add_node("hot", energy=0.9)
        self.ledger.add_node("cold", energy=0.01)
        s = self.ledger.stats()
        self.assertEqual(s["nodes"], 2)
        self.assertEqual(s["tiers"]["hot"], 1)
        self.assertEqual(s["tiers"]["cold"], 1)


class EmbeddingTest(unittest.TestCase):
    def test_cosine_identity_and_orthogonality(self) -> None:
        e = HashingEmbedder(dim=128)
        v = e.embed("some text here")
        self.assertAlmostEqual(cosine(v, v), 1.0, places=6)
        self.assertAlmostEqual(cosine(v, [0.0] * 128), 0.0)


if __name__ == "__main__":
    unittest.main()
