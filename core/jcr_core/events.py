"""The resonance bus: an append-only event log with in-process pub/sub.

The log is the source of truth. Any derived state (the ledger) is reproducible by
replay. This is what makes crash recovery and audit possible, and it is the
substrate for the "decisions are observable" property the harness needs.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from jcr_core.types import Event

Subscriber = Callable[[Event], None]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    id        TEXT UNIQUE NOT NULL,
    ts        TEXT NOT NULL,
    kind      TEXT NOT NULL,
    source    TEXT NOT NULL,
    priority  REAL NOT NULL DEFAULT 0,
    payload   TEXT NOT NULL,
    caused_by TEXT NOT NULL DEFAULT '[]',
    session   TEXT,
    turn      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session);
"""


class EventLog:
    """Durable, append-only event store on SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def append(self, event: Event) -> Event:
        row = event.to_row()
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO events (id, ts, kind, source, priority, payload, caused_by, session, turn)
                   VALUES (:id, :ts, :kind, :source, :priority, :payload, :caused_by, :session, :turn)""",
                {
                    **row,
                    "payload": json.dumps(row["payload"], default=str),
                    "caused_by": json.dumps(row["caused_by"]),
                },
            )
            self._conn.commit()
            event.seq = int(cur.lastrowid)
        return event

    def read(
        self,
        since: int = 0,
        kinds: Iterable[str] | None = None,
        session: str | None = None,
        limit: int = 1000,
    ) -> list[Event]:
        sql = "SELECT * FROM events WHERE seq > ?"
        params: list[object] = [since]
        if kinds:
            kinds = list(kinds)
            sql += f" AND kind IN ({','.join('?' * len(kinds))})"
            params.extend(kinds)
        if session:
            sql += " AND session = ?"
            params.append(session)
        sql += " ORDER BY seq ASC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_event(r) for r in rows]

    def tail(self, n: int = 20) -> list[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY seq DESC LIMIT ?", (n,)
            ).fetchall()
        return [_row_to_event(r) for r in reversed(rows)]

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _row_to_event(r: sqlite3.Row) -> Event:
    return Event(
        id=r["id"],
        ts=r["ts"],
        kind=r["kind"],
        source=r["source"],
        priority=r["priority"],
        payload=json.loads(r["payload"]),
        caused_by=json.loads(r["caused_by"]),
        session=r["session"],
        turn=r["turn"],
        seq=r["seq"],
    )


class Bus:
    """Event log + synchronous in-process fan-out.

    Subscribers are keyed by event kind; ``"*"`` subscribes to everything.
    Fan-out is synchronous and best-effort: a failing subscriber must not break
    the publisher, so exceptions are swallowed and reported as ``error`` events.
    """

    def __init__(self, log: EventLog) -> None:
        self.log = log
        self._subs: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, kind: str, fn: Subscriber) -> None:
        with self._lock:
            self._subs[kind].append(fn)

    def unsubscribe(self, kind: str, fn: Subscriber) -> None:
        with self._lock:
            if fn in self._subs.get(kind, []):
                self._subs[kind].remove(fn)

    def publish(self, event: Event) -> Event:
        event = self.log.append(event)
        with self._lock:
            handlers = list(self._subs.get(event.kind_value(), [])) + list(self._subs.get("*", []))
        for fn in handlers:
            try:
                fn(event)
            except Exception as exc:  # noqa: BLE001 - subscriber isolation is intentional
                self.log.append(
                    Event(kind="error", source="bus", payload={"subscriber": repr(fn), "error": str(exc)})
                )
        return event

    def drain(self, since: int = 0, kinds: Iterable[str] | None = None, limit: int = 1000) -> list[Event]:
        """Pull events newer than ``since`` — the read side of push."""
        return self.log.read(since=since, kinds=kinds, limit=limit)
