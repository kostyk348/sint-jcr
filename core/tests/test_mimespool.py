"""Tests for the .eml bus (MimeSpool): hash-chain, integrity, EML-IPC format."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.events import Bus
from jcr_core.mimespool import GENESIS, MimeSpool
from jcr_core.types import Event, EventKind


class MimeSpoolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "bus"
        self.spool = MimeSpool(self.dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_append_assigns_seq_and_chain(self) -> None:
        a = self.spool.append(Event(kind=EventKind.TURN_OPEN, source="t"))
        b = self.spool.append(Event(kind=EventKind.TURN_CLOSE, source="t"))
        self.assertEqual(a.seq, 1)
        self.assertEqual(a.prev_hash, GENESIS)
        self.assertEqual(b.prev_hash, a.hash)
        self.assertNotEqual(a.hash, b.hash)

    def test_files_are_eml_ipc_compatible(self) -> None:
        self.spool.append(Event(kind=EventKind.ACTIVATION, source="ledger", payload={"node_id": "n1"}))
        f = sorted(self.dir.glob("*.eml"))[0]
        self.assertTrue(f.name.endswith(".msg.eml"), "EML-IPC filename convention")
        text = f.read_text(encoding="utf-8")
        self.assertIn("X-Event: activation", text)
        self.assertIn("X-EMLBox-Msg: v1", text)
        self.assertIn("Content-Type: application/json", text)
        self.assertIn("X-JCR-Hash:", text)
        self.assertIn("X-JCR-Prev-Hash:", text)

    def test_read_filters(self) -> None:
        self.spool.append(Event(kind=EventKind.AFFECT, source="p"))
        self.spool.append(Event(kind=EventKind.ACTIVATION, source="l"))
        self.spool.append(Event(kind=EventKind.AFFECT, source="p"))
        self.assertEqual(len(self.spool.read(kinds=["affect"])), 2)
        self.assertEqual(len(self.spool.read(since=2)), 1)

    def test_persistence_and_chain_continue_across_reopen(self) -> None:
        a = self.spool.append(Event(kind=EventKind.RESONANCE, source="t"))
        reopened = MimeSpool(self.dir)
        self.assertEqual(reopened.count(), 1)
        self.assertEqual(reopened.head_hash(), a.hash)
        b = reopened.append(Event(kind=EventKind.OUTCOME, source="t"))
        self.assertEqual(b.seq, 2)
        self.assertEqual(b.prev_hash, a.hash)
        self.assertTrue(reopened.verify_chain()["ok"])

    def test_verify_chain_detects_tampering(self) -> None:
        self.spool.append(Event(kind=EventKind.OUTCOME, source="t", payload={"n": 1}))
        self.assertTrue(self.spool.verify_chain()["ok"])
        f = sorted(self.dir.glob("*.eml"))[0]
        f.write_text(f.read_text(encoding="utf-8").replace('{"n": 1}', '{"n": 2}'), encoding="utf-8")
        self.assertFalse(MimeSpool(self.dir).verify_chain()["ok"])

    def test_torn_write_does_not_corrupt_the_log(self) -> None:
        self.spool.append(Event(kind=EventKind.OUTCOME, source="t", payload={"ok": True}))
        (self.dir / "00000099.evt_broken.msg.eml").write_text("this is not a message", encoding="utf-8")
        reopened = MimeSpool(self.dir)
        self.assertEqual(reopened.count(), 1)  # broken record skipped, log intact


class BusOnSpoolTest(unittest.TestCase):
    def test_bus_works_with_eml_spool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bus = Bus(MimeSpool(Path(tmp)))
            seen: list[str] = []
            bus.subscribe("veto", lambda e: seen.append(e.id))
            bus.publish(Event(kind=EventKind.VETO, source="arbiter"))
            bus.publish(Event(kind=EventKind.AFFECT, source="psychoid"))
            self.assertEqual(len(seen), 1)
            self.assertEqual(len(bus.drain()), 2)


if __name__ == "__main__":
    unittest.main()
