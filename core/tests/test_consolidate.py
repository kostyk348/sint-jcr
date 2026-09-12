"""Tests for consolidation (identity audit/mirror + memory .eml export)."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jcr_core.bridge import source_hash
from jcr_core.character import CharacterLedger
from jcr_core.consolidate import (
    IDENTITY_TAG,
    audit_identity,
    export_identity,
    memory_to_eml,
    mirror_identity,
)


def make_self_db(path: Path, notes: list[str]) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE self (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL, tag TEXT, source TEXT,
            voice TEXT DEFAULT 'any', emb BLOB, created_at TEXT NOT NULL
        );
        """
    )
    for n in notes:
        conn.execute(
            "INSERT INTO self(text,tag,source,voice,emb,created_at) VALUES(?,?,?,?,?,datetime('now'))",
            (n, IDENTITY_TAG, "jcr-character", "any", None),
        )
    conn.commit()
    conn.close()


class IdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.ch = CharacterLedger(base / "character.db")
        self.ch.teach("be terse", weight=0.8)
        self.ch.teach("prefer mechanism", weight=0.7)
        self.self_db = base / "self.db"
        make_self_db(self.self_db, ["be terse", "an old note not in the ledger"])

    def tearDown(self) -> None:
        self.ch.close()
        self.tmp.cleanup()

    def test_export_identity(self) -> None:
        out = export_identity(self.ch)
        self.assertEqual(out["authority"], "jcr-character-ledger")
        self.assertEqual(len(out["traits"]), 2)

    def test_audit_reports_divergence(self) -> None:
        rep = audit_identity(self.ch, self.self_db)
        self.assertIn("prefer mechanism", rep["missing_in_self"])
        self.assertIn("an old note not in the ledger", rep["stale_in_self"])
        self.assertFalse(rep["consistent"])

    def test_mirror_dry_run_is_plan_only(self) -> None:
        plan = mirror_identity(self.ch, self.self_db, embed_fn=None, dry_run=True)
        self.assertIn("prefer mechanism", plan["to_add"])
        self.assertFalse(plan["applied"])

    def test_mirror_applies_with_embedder(self) -> None:
        plan = mirror_identity(self.ch, self.self_db, embed_fn=lambda s: [0.1, 0.2, 0.3], dry_run=False)
        self.assertTrue(plan["applied"])
        conn = sqlite3.connect(str(self.self_db))
        rows = conn.execute("SELECT text, length(emb) FROM self WHERE text = 'prefer mechanism'").fetchall()
        conn.close()
        self.assertEqual(rows[0][1], 12)  # 3 * float32


class MemoryEmlTest(unittest.TestCase):
    def test_export_writes_eml_ipc(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        chain = base / "chain.jsonl"
        prev = "0" * 16
        block = {"id": "0000", "register": "FACT", "content": "bus is eml", "project": "JCR"}
        block["prev_hash"] = prev
        block["hash"] = source_hash("0000", "FACT", "bus is eml", prev)
        chain.write_text(json.dumps(block) + "\n", encoding="utf-8")
        out = base / "eml"
        result = memory_to_eml(chain, out)
        self.assertEqual(result["written"], 1)
        f = sorted(out.glob("*.msg.eml"))[0]
        text = f.read_text(encoding="utf-8")
        self.assertIn("X-Event: memory_block", text)
        self.assertIn("X-EMLBox-Msg: v1", text)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
