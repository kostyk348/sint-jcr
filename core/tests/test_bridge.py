"""Tests for the sint-memory -> ledger import bridge."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jcr_core.bridge import import_chain, source_hash, verify_source_chain
from jcr_core.config import JCRConfig
from jcr_core.ledger import LibidoLedger
from jcr_core.types import Register


def make_chain(path: Path, blocks: list[dict]) -> None:
    prev = "0" * 16
    with path.open("w", encoding="utf-8") as fh:
        for b in blocks:
            b = dict(b)
            b["prev_hash"] = prev
            b["hash"] = source_hash(b["id"], b["register"], b["content"], prev)
            prev = b["hash"]
            fh.write(json.dumps(b) + "\n")


class BridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.chain = Path(self.tmp.name) / "chain.jsonl"
        make_chain(self.chain, [
            {"id": "0000", "register": "SENSE", "content": "init", "project": "SYS", "tags": ["x"]},
            {"id": "0001", "register": "FACT", "content": "the bus is eml", "project": "JCR", "tags": []},
        ])
        self.ledger = LibidoLedger(Path(self.tmp.name) / "ledger.db", JCRConfig())

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_verify_source_chain(self) -> None:
        self.assertTrue(verify_source_chain(self.chain)["ok"])

    def test_tamper_detected(self) -> None:
        text = self.chain.read_text(encoding="utf-8").replace("the bus is eml", "the bus is sqlite")
        self.chain.write_text(text, encoding="utf-8")
        self.assertFalse(verify_source_chain(self.chain)["ok"])

    def test_import_is_idempotent(self) -> None:
        first = import_chain(self.ledger, self.chain)
        self.assertEqual(first["imported"], 2)
        second = import_chain(self.ledger, self.chain)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["skipped"], 2)

    def test_provenance_and_register_preserved(self) -> None:
        import_chain(self.ledger, self.chain)
        node = self.ledger.get_node("n_mem0001")
        self.assertIsNotNone(node)
        self.assertEqual(node.register, Register.FACT)
        self.assertEqual(node.project, "JCR")
        self.assertEqual(node.provenance["source"], "sint-memory")
        self.assertEqual(node.provenance["block_id"], "0001")

    def test_limit_and_force(self) -> None:
        r = import_chain(self.ledger, self.chain, limit=1)
        self.assertEqual(r["imported"], 1)
        r2 = import_chain(self.ledger, self.chain, force=True)
        self.assertEqual(r2["imported"], 2)


if __name__ == "__main__":
    unittest.main()
