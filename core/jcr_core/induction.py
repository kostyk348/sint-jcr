"""Dream cycle — automatic trait induction and telemetry (H5).

This closes the personality loop: the harness records which traits were injected
on each turn, the outcome is labelled, and consolidation moves traits toward
whatever actually worked. It also *induces* candidate traits from recurring
context keywords in successful turns — but only as **proposals**, ratified by
the owner, never auto-installed.

See ``docs/12-character.md`` §3.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from jcr_core.character import CharacterLedger

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id        TEXT PRIMARY KEY,
    session   TEXT,
    ts        TEXT NOT NULL,
    trait_ids TEXT NOT NULL DEFAULT '[]',
    node_ids  TEXT NOT NULL DEFAULT '[]',
    keywords  TEXT NOT NULL DEFAULT '[]',
    useful    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_turns_useful ON turns(useful);

CREATE TABLE IF NOT EXISTS proposals (
    id        TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    scope     TEXT NOT NULL DEFAULT '*',
    evidence  INTEGER NOT NULL DEFAULT 0,
    created   TEXT NOT NULL,
    ratified  INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_stmt ON proposals(statement);
"""

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was",
    "were", "be", "been", "it", "this", "that", "as", "at", "by", "from", "we", "i", "you",
    "not", "no", "do", "does", "did", "but", "if", "then", "so", "than", "into", "about",
    "can", "will", "would", "should", "could", "has", "have", "had", "its", "our", "your",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def keywords(text: str, limit: int = 12) -> list[str]:
    words = [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(w) > 3]
    seen: list[str] = []
    for w in words:
        if w in _STOPWORDS or w in seen:
            continue
        seen.append(w)
        if len(seen) >= limit:
            break
    return seen


@dataclass(slots=True)
class ConsolidationReport:
    turns: int
    labelled: int
    reinforced: list[dict]
    decayed: list[dict]
    new_proposals: list[dict]

    def as_dict(self) -> dict:
        return {
            "turns": self.turns,
            "labelled": self.labelled,
            "reinforced": self.reinforced,
            "decayed": self.decayed,
            "new_proposals": self.new_proposals,
        }


class DreamCycle:
    """Outcome-driven consolidation of character and candidate traits."""

    def __init__(self, path: str | Path, character: CharacterLedger) -> None:
        self.path = str(path)
        self.character = character
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------ write

    def record_turn(
        self,
        session: str | None,
        trait_ids: list[str],
        node_ids: list[str],
        text: str = "",
    ) -> str:
        tid = f"turn_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._conn.execute(
                "INSERT INTO turns (id, session, ts, trait_ids, node_ids, keywords, useful) VALUES (?,?,?,?,?,?,NULL)",
                (tid, session, _now(), json.dumps(trait_ids), json.dumps(node_ids), json.dumps(keywords(text))),
            )
            self._conn.commit()
        return tid

    def label(self, turn_id: str, useful: bool) -> bool:
        with self._lock:
            cur = self._conn.execute("UPDATE turns SET useful = ? WHERE id = ?", (1 if useful else 0, turn_id))
            self._conn.commit()
            return cur.rowcount > 0

    def label_latest(self, useful: bool, session: str | None = None) -> str | None:
        sql = "SELECT id FROM turns WHERE useful IS NULL"
        params: list[object] = []
        if session:
            sql += " AND session = ?"
            params.append(session)
        sql += " ORDER BY rowid DESC LIMIT 1"
        with self._lock:
            r = self._conn.execute(sql, params).fetchone()
        if not r:
            return None
        self.label(r["id"], useful)
        return r["id"]

    # ------------------------------------------------------------- induction

    def consolidate(self, min_evidence: int = 2, reinforce: float = 0.05, decay: float = 0.06) -> ConsolidationReport:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM turns WHERE useful IS NOT NULL").fetchall()

        positive: dict[str, int] = {}
        negative: dict[str, int] = {}
        useful_keywords: dict[str, int] = {}
        for r in rows:
            useful = bool(r["useful"])
            for t in json.loads(r["trait_ids"]):
                (positive if useful else negative)[t] = (positive if useful else negative).get(t, 0) + 1
            if useful:
                for k in json.loads(r["keywords"]):
                    useful_keywords[k] = useful_keywords.get(k, 0) + 1

        reinforced: list[dict] = []
        decayed: list[dict] = []
        for trait_id in set(positive) | set(negative):
            pos = positive.get(trait_id, 0)
            neg = negative.get(trait_id, 0)
            if pos + neg < min_evidence:
                continue
            delta = reinforce * pos - decay * neg
            if abs(delta) < 1e-9:
                continue
            t = self.character.reinforce(trait_id, delta, evidence=f"dream:useful={pos},useless={neg}")
            if t is None:
                continue
            entry = {"trait_id": trait_id, "delta": round(delta, 4), "weight": round(t.weight, 4)}
            (reinforced if delta > 0 else decayed).append(entry)

        # candidate induction: recurring keywords in successful turns
        existing = " ".join(t.statement.lower() + " " + t.scope.lower() for t in self.character.all_traits())
        new_proposals: list[dict] = []
        for kw, count in useful_keywords.items():
            if count < min_evidence or kw in existing:
                continue
            statement = f"prefer {kw} when it applies"
            with self._lock:
                try:
                    self._conn.execute(
                        "INSERT INTO proposals (id, statement, scope, evidence, created, ratified) VALUES (?,?,?,?,?,0)",
                        (f"p_{uuid.uuid4().hex[:12]}", statement, kw, count, _now()),
                    )
                    self._conn.commit()
                except sqlite3.IntegrityError:
                    continue
            new_proposals.append({"statement": statement, "scope": kw, "evidence": count})

        return ConsolidationReport(
            turns=self._count_turns(),
            labelled=len(rows),
            reinforced=reinforced,
            decayed=decayed,
            new_proposals=new_proposals,
        )

    def proposals(self, include_ratified: bool = False) -> list[dict]:
        sql = "SELECT * FROM proposals"
        if not include_ratified:
            sql += " WHERE ratified = 0"
        sql += " ORDER BY evidence DESC"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def ratify(self, proposal_id: str, weight: float = 0.5) -> dict | None:
        """Owner ratifies a proposed trait -> it becomes a real disposition."""
        with self._lock:
            r = self._conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not r or r["ratified"]:
            return None
        t = self.character.teach(r["statement"], weight=weight, scope=r["scope"])
        with self._lock:
            self._conn.execute("UPDATE proposals SET ratified = 1 WHERE id = ?", (proposal_id,))
            self._conn.commit()
        return {"trait_id": t.id, "statement": t.statement, "scope": t.scope}

    # ------------------------------------------------------------------- read

    def turns(self, labelled_only: bool = True) -> list[dict]:
        sql = "SELECT * FROM turns"
        if labelled_only:
            sql += " WHERE useful IS NOT NULL"
        sql += " ORDER BY ts"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        return [
            {
                "id": r["id"],
                "session": r["session"],
                "trait_ids": json.loads(r["trait_ids"]),
                "node_ids": json.loads(r["node_ids"]),
                "useful": None if r["useful"] is None else bool(r["useful"]),
            }
            for r in rows
        ]

    def telemetry(self) -> dict:
        with self._lock:
            total = int(self._conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0])
            labelled = int(self._conn.execute("SELECT COUNT(*) FROM turns WHERE useful IS NOT NULL").fetchone()[0])
            useful = int(self._conn.execute("SELECT COUNT(*) FROM turns WHERE useful = 1").fetchone()[0])
            proposals = int(self._conn.execute("SELECT COUNT(*) FROM proposals WHERE ratified = 0").fetchone()[0])
        return {
            "turns": total,
            "labelled": labelled,
            "pending": total - labelled,
            "useful_rate": round(useful / labelled, 4) if labelled else None,
            "proposals_open": proposals,
        }

    def _count_turns(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
