"""Tests for the event bus and event log."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.events import Bus, EventLog
from jcr_core.types import Event, EventKind


class TestEventLog(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "events.db"
        self.log = EventLog(self.path)

    def tearDown(self) -> None:
        self.log.close()
        self.tmp.cleanup()

    def test_append_assigns_monotonic_seq(self) -> None:
        a = self.log.append(Event(kind=EventKind.TURN_OPEN, source="t"))
        b = self.log.append(Event(kind=EventKind.TURN_CLOSE, source="t"))
        self.assertEqual(a.seq, 1)
        self.assertEqual(b.seq, 2)

    def test_read_since_and_kind_filter(self) -> None:
        self.log.append(Event(kind=EventKind.AFFECT, source="psychoid"))
        e2 = self.log.append(Event(kind=EventKind.ACTIVATION, source="ledger"))
        self.log.append(Event(kind=EventKind.AFFECT, source="psychoid"))
        only_affect = self.log.read(kinds=["affect"])
        self.assertEqual(len(only_affect), 2)
        newer = self.log.read(since=e2.seq)
        self.assertEqual(len(newer), 1)
        self.assertEqual(newer[0].seq, 3)

    def test_persistence_across_reopen(self) -> None:
        self.log.append(Event(kind=EventKind.OUTCOME, source="t", payload={"useful": True}))
        self.log.close()
        reopened = EventLog(self.path)
        rows = reopened.read()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].payload["useful"])
        reopened.close()


class TestBus(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.log = EventLog(Path(self.tmp.name) / "events.db")
        self.bus = Bus(self.log)

    def tearDown(self) -> None:
        self.log.close()
        self.tmp.cleanup()

    def test_subscriber_receives_matching_kind(self) -> None:
        seen: list[str] = []
        self.bus.subscribe("activation", lambda e: seen.append(e.id))
        self.bus.publish(Event(kind=EventKind.ACTIVATION, source="ledger"))
        self.bus.publish(Event(kind=EventKind.AFFECT, source="psychoid"))
        self.assertEqual(len(seen), 1)

    def test_wildcard_subscriber_sees_all(self) -> None:
        seen: list[str] = []
        self.bus.subscribe("*", lambda e: seen.append(e.kind_value()))
        self.bus.publish(Event(kind=EventKind.ACTIVATION, source="a"))
        self.bus.publish(Event(kind=EventKind.VETO, source="b"))
        self.assertEqual(seen, ["activation", "veto"])

    def test_failing_subscriber_does_not_break_publish(self) -> None:
        def boom(_e):
            raise RuntimeError("subscriber exploded")

        self.bus.subscribe("*", boom)
        self.bus.publish(Event(kind=EventKind.TURN_OPEN, source="t"))
        # publish survived, and the failure was recorded as an error event
        kinds = [e.kind_value() for e in self.log.read()]
        self.assertIn("error", kinds)

    def test_drain_is_the_pull_side(self) -> None:
        for _ in range(3):
            self.bus.publish(Event(kind=EventKind.RESONANCE, source="t"))
        drained = self.bus.drain(since=0)
        self.assertEqual(len(drained), 3)


if __name__ == "__main__":
    unittest.main()
