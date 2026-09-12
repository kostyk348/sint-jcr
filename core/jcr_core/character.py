"""The Character Ledger — where personality lives.

See ``docs/12-character.md``. Personality is not a prompt and not the weights.
It is a set of **dispositions** with weights, each backed by *evidence*, that
the harness injects into every turn and that evolves from outcomes
(individuation). Because it lives here — outside the model — it survives a model
swap, is auditable, and is editable by the owner.

A trait is a falsifiable object: it has a weight, an evidence list, and a
measured drift over time. "Personality" that cannot be measured is not stored.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traits (
    id              TEXT PRIMARY KEY,
    statement       TEXT NOT NULL,
    weight          REAL NOT NULL,
    baseline_weight REAL NOT NULL,
    scope           TEXT NOT NULL DEFAULT '*',
    polarity        REAL NOT NULL DEFAULT 1.0,
    created         TEXT NOT NULL,
    updated         TEXT NOT NULL,
    hits            INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS trait_events (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    trait_id TEXT NOT NULL,
    delta    REAL NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    ts       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trait_events ON trait_events(trait_id);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass(slots=True)
class Trait:
    id: str
    statement: str
    weight: float
    baseline_weight: float
    scope: str = "*"
    polarity: float = 1.0
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)
    hits: int = 0

    @property
    def drift(self) -> float:
        return round(self.weight - self.baseline_weight, 6)


class CharacterLedger:
    """Persistent dispositions the harness injects and outcomes revise."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------ write

    def teach(
        self,
        statement: str,
        weight: float = 0.5,
        scope: str = "*",
        polarity: float = 1.0,
    ) -> Trait:
        """Install or update a disposition (owner teaching / induction)."""
        t = Trait(
            id=f"t_{uuid.uuid4().hex[:12]}",
            statement=statement.strip(),
            weight=_clamp(weight),
            baseline_weight=_clamp(weight),
            scope=scope.strip() or "*",
            polarity=1.0 if polarity >= 0 else -1.0,
        )
        with self._lock:
            self._conn.execute(
                """INSERT INTO traits
                   (id, statement, weight, baseline_weight, scope, polarity, created, updated, hits)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (t.id, t.statement, t.weight, t.baseline_weight, t.scope, t.polarity, t.created, t.updated, t.hits),
            )
            self._conn.commit()
        return t

    def reinforce(self, trait_id: str, delta: float, evidence: str = "") -> Trait | None:
        """Move a trait by ``delta`` based on an observed outcome."""
        with self._lock:
            r = self._conn.execute("SELECT * FROM traits WHERE id = ?", (trait_id,)).fetchone()
            if not r:
                return None
            new_w = _clamp(r["weight"] + delta)
            self._conn.execute(
                "UPDATE traits SET weight = ?, updated = ? WHERE id = ?", (new_w, _now(), trait_id)
            )
            self._conn.execute(
                "INSERT INTO trait_events (trait_id, delta, evidence, ts) VALUES (?,?,?,?)",
                (trait_id, delta, evidence, _now()),
            )
            self._conn.commit()
            return self.get(trait_id)

    # ------------------------------------------------------------------- read

    def get(self, trait_id: str) -> Trait | None:
        with self._lock:
            r = self._conn.execute("SELECT * FROM traits WHERE id = ?", (trait_id,)).fetchone()
        return self._row(r) if r else None

    def all_traits(self) -> list[Trait]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM traits ORDER BY weight DESC").fetchall()
        return [self._row(r) for r in rows]

    def traits_for(self, context: str, k: int = 5) -> list[Trait]:
        """Top-k most relevant dispositions for the current situation."""
        ctx = set(_tokens(context))
        scored: list[tuple[float, Trait]] = []
        for t in self.all_traits():
            score = t.weight * _scope_match(t.scope, ctx)
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda x: (x[0], x[1].weight), reverse=True)
        chosen = [t for _, t in scored[:k]]
        if chosen:
            with self._lock:
                self._conn.executemany(
                    "UPDATE traits SET hits = hits + 1 WHERE id = ?", [(t.id,) for t in chosen]
                )
                self._conn.commit()
        return chosen

    def drift(self) -> dict:
        """How the character has moved since it was taught (individuation signal)."""
        traits = self.all_traits()
        movers = sorted(traits, key=lambda t: abs(t.drift), reverse=True)
        return {
            "traits": len(traits),
            "mean_weight": round(sum(t.weight for t in traits) / len(traits), 4) if traits else 0.0,
            "movers": [
                {"id": t.id, "statement": t.statement, "drift": t.drift, "weight": round(t.weight, 4)}
                for t in movers
                if abs(t.drift) > 1e-9
            ][:10],
        }

    def stats(self) -> dict:
        with self._lock:
            n = int(self._conn.execute("SELECT COUNT(*) FROM traits").fetchone()[0])
            ev = int(self._conn.execute("SELECT COUNT(*) FROM trait_events").fetchone()[0])
        return {"traits": n, "events": ev}

    # --------------------------------------------------------------- internal

    def _row(self, r: sqlite3.Row) -> Trait:
        return Trait(
            id=r["id"],
            statement=r["statement"],
            weight=r["weight"],
            baseline_weight=r["baseline_weight"],
            scope=r["scope"],
            polarity=r["polarity"],
            created=r["created"],
            updated=r["updated"],
            hits=r["hits"],
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _tokens(text: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if w]


def _scope_match(scope: str, ctx_tokens: set[str]) -> float:
    if scope == "*":
        return 1.0
    scope_tokens = set(_tokens(scope))
    if not scope_tokens:
        return 1.0
    return len(scope_tokens & ctx_tokens) / len(scope_tokens)
