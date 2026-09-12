"""Tests for the context compiler (budgeted assembly)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.character import CharacterLedger
from jcr_core.compiler import ContextCompiler, estimate_tokens
from jcr_core.config import JCRConfig
from jcr_core.ledger import LibidoLedger


class CompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.cfg = JCRConfig(embed_dim=256, character_traits_in_context=3)
        self.ledger = LibidoLedger(base / "ledger.db", self.cfg)
        self.ch = CharacterLedger(base / "character.db")
        self.compiler = ContextCompiler(self.ledger, self.ch, self.cfg)
        self.ch.teach("prefer mechanism over metaphor", weight=0.9)
        self.ledger.add_node("libido ledger energy decay memory field", energy=0.2)

    def tearDown(self) -> None:
        self.ledger.close()
        self.ch.close()
        self.tmp.cleanup()

    def test_compile_contains_traits_and_nodes(self) -> None:
        c = self.compiler.compile("libido ledger energy", budget_tokens=1200, k=5)
        self.assertTrue(c.traits)
        self.assertTrue(c.nodes)
        self.assertIn("mechanism", c.system_addendum)
        self.assertIn("libido", c.system_addendum.lower())

    def test_budget_is_respected(self) -> None:
        for i in range(20):
            self.ledger.add_node("x" * 2000 + f" {i}", energy=0.5)
        c = self.compiler.compile("x" * 2000, budget_tokens=200, k=20)
        self.assertLessEqual(c.tokens_estimate, 200 + estimate_tokens("x" * 2000))
        self.assertGreaterEqual(c.dropped, 0)

    def test_tokens_estimate_nonzero_when_content(self) -> None:
        c = self.compiler.compile("libido ledger", budget_tokens=1200, k=5)
        self.assertGreater(c.tokens_estimate, 0)


if __name__ == "__main__":
    unittest.main()
