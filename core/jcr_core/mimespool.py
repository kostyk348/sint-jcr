"""MimeSpool — the append-only, hash-chained `.eml` event bus.

This is the *source of truth* for the JCR bus. It replaces SQLite as the log,
for four reasons (see docs/01-architecture.md §Bus):

1. **Tamper-evidence.** Every event carries ``X-JCR-Prev-Hash``/``X-JCR-Hash``,
   so the log is a verifiable hash-chain. SQLite gives durability, not integrity.
2. **One artifact, two roles.** An event is a valid EML-IPC message
   (``X-Event`` + JSON body), so the *same* file is a local log entry and a
   wire message that can travel over emlbox's SMTP/mesh transport.
3. **Corruption-proof.** One file per event, atomic ``tmp + rename``; a torn
   write can never corrupt the log, and header-only scans stay cheap.
4. **Ecosystem fit.** It is the format mime-os/emlbox already reads
   (``fs index``, ``tagdb query``, ``mail``, ``sync``).

Compatibility: headers ``From`` / ``To`` / ``X-Event`` / ``X-EMLBox-Msg`` /
``Content-Type`` follow ``mime-os/docs/FORMAT.md`` (EML-IPC). JCR adds
``X-JCR-*`` headers for sequencing and the hash-chain.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Iterable

from jcr_core.types import Event

GENESIS = "0" * 16


def chain_hash(seq: int, event_id: str, ts: str, kind: str, payload_json: str, prev_hash: str) -> str:
    h = hashlib.sha256()
    h.update(f"{seq}|{event_id}|{ts}|{kind}|{payload_json}|{prev_hash}".encode("utf-8"))
    return h.hexdigest()[:16]


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)


class MimeSpool:
    """Append-only log of RFC822/MIME events on disk (one file per event)."""

    def __init__(self, spool_dir: str | Path) -> None:
        self.dir = Path(spool_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cache: list[Event] = []
        self._seq = 0
        self._head = GENESIS
        self._load()

    # ------------------------------------------------------------------ write

    def append(self, event: Event) -> Event:
        with self._lock:
            self._seq += 1
            event.seq = self._seq
            payload_json = canonical(event.payload)
            event.prev_hash = self._head
            event.hash = chain_hash(event.seq, event.id, event.ts, event.kind_value(), payload_json, self._head)

            text = _render(event, payload_json)
            # `.msg.eml` is the EML-IPC filename convention (mime-os/src/ipc.rs),
            # so `emlbox ipc list <spool>` sees JCR events natively.
            fname = f"{event.seq:08d}.{event.id}.msg.eml"
            tmp = self.dir / (fname + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.dir / fname)  # atomic: never a torn record

            self._cache.append(event)
            self._head = event.hash or GENESIS
            return event

    # ------------------------------------------------------------------- read

    def read(
        self,
        since: int = 0,
        kinds: Iterable[str] | None = None,
        session: str | None = None,
        limit: int = 1000,
    ) -> list[Event]:
        kinds_set = set(kinds) if kinds else None
        out: list[Event] = []
        for e in self._cache:
            if e.seq is None or e.seq <= since:
                continue
            if kinds_set and e.kind_value() not in kinds_set:
                continue
            if session and e.session != session:
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out

    def tail(self, n: int = 20) -> list[Event]:
        return self._cache[-n:] if n > 0 else []

    def count(self) -> int:
        return len(self._cache)

    def head_hash(self) -> str:
        return self._head

    # ------------------------------------------------------------- integrity

    def verify_chain(self) -> dict:
        """Recompute the hash-chain. Returns {ok, checked, broken_at}."""
        prev = GENESIS
        for i, e in enumerate(self._cache):
            payload_json = canonical(e.payload)
            expect = chain_hash(e.seq, e.id, e.ts, e.kind_value(), payload_json, prev)
            if e.prev_hash != prev or e.hash != expect:
                return {"ok": False, "checked": i, "broken_at": e.seq}
            prev = e.hash
        return {"ok": True, "checked": len(self._cache), "broken_at": None}

    # ---------------------------------------------------------------- internal

    def _load(self) -> None:
        for path in sorted(self.dir.glob("*.eml")):
            ev = self._parse(path)
            if ev is not None:
                self._cache.append(ev)
        if self._cache:
            self._seq = self._cache[-1].seq or 0
            self._head = self._cache[-1].hash or GENESIS

    def _parse(self, path: Path) -> Event | None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            return _parse_message(text)
        except Exception:  # noqa: BLE001 - a broken record must not kill the log
            return None

    def close(self) -> None:
        """Drop in-memory caches. The spool is append-only; nothing to flush."""
        with self._lock:
            self._cache.clear()


def _render(event: Event, payload_json: str) -> str:
    sid = event.session or "-"
    turn = "-" if event.turn is None else str(event.turn)
    caused = ",".join(event.caused_by)
    return (
        "From: <jcr@localhost>\n"
        "To: <jcr-core@localhost>\n"
        "X-EMLBox-Msg: v1\n"
        f"X-Event: {event.kind_value()}\n"
        f"X-JCR-Kind: {event.kind_value()}\n"
        f"X-JCR-Seq: {event.seq}\n"
        f"X-JCR-Source: {event.source}\n"
        f"X-JCR-Priority: {float(event.priority):.6f}\n"
        f"X-JCR-Session: {sid}\n"
        f"X-JCR-Turn: {turn}\n"
        f"X-JCR-Caused-By: {caused}\n"
        f"X-JCR-Prev-Hash: {event.prev_hash}\n"
        f"X-JCR-Hash: {event.hash}\n"
        f"Message-ID: <{event.id}@jcr>\n"
        f"Date: {event.ts}\n"
        "Content-Type: application/json; charset=utf-8\n"
        "\n"
        f"{payload_json}\n"
    )


def _parse_message(text: str) -> Event:
    head, _, body = text.partition("\n\n")
    headers: dict[str, str] = {}
    for line in head.splitlines():
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        headers[k.strip().lower()] = v.strip()

    payload = json.loads(body.strip()) if body.strip() else {}
    caused = headers.get("x-jcr-caused-by", "")
    return Event(
        id=headers["message-id"].strip("<>").split("@")[0],
        ts=headers.get("date", ""),
        kind=headers.get("x-jcr-kind") or headers.get("x-event", "error"),
        source=headers.get("x-jcr-source", "unknown"),
        priority=float(headers.get("x-jcr-priority", 0.0)),
        payload=payload,
        caused_by=[c for c in caused.split(",") if c],
        session=None if headers.get("x-jcr-session", "-") == "-" else headers.get("x-jcr-session"),
        turn=None if headers.get("x-jcr-turn", "-") == "-" else int(headers["x-jcr-turn"]),
        seq=int(headers.get("x-jcr-seq", 0)),
        prev_hash=headers.get("x-jcr-prev-hash"),
        hash=headers.get("x-jcr-hash"),
    )
