"""Synchronicity monitor (Phase 4) — unasked, meaningful arrivals, calibrated.

docs/06-synchronicity.md. Jung's synchronicity has three criteria, and they are
simultaneously the best available filter against aporhenia (seeing meaning in
noise). A candidate must satisfy **all three**:

1. **acausal / distant** — not a recent neighbour (a retrieval hit is not a crossing);
2. **meaningful** — high structural resonance, and *cross-domain*;
3. **archetypal** — buffer and node instantiate the same pattern from the
   collective-unconscious library.

Resonance alone is just RAG. The archetypal condition is the strict one.

Soft by default: a crossing raises priority; hard injection is opt-in and only
while measured precision holds above a floor.
"""

from __future__ import annotations

import math
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from jcr_core.config import JCRConfig
from jcr_core.embedding import cosine
from jcr_core.ledger import LibidoLedger

# Collective-unconscious library: structural control patterns, not content.
ARCHETYPES: dict[str, list[str]] = {
    "cycle": ["cycle", "loop", "iterate", "retry", "recur", "round", "again", "periodic"],
    "tree": ["tree", "hierarchy", "branch", "recursive", "nest", "parent", "child", "subtree"],
    "barrier": ["barrier", "block", "gate", "lock", "wait", "deadlock", "stall", "mutex"],
    "split": ["split", "partition", "divide", "separate", "shard", "fork", "decompose"],
    "reversal": ["reverse", "invert", "mirror", "swap", "flip", "opposite", "enantiodromia"],
    "feedback": ["feedback", "sensor", "measure", "adjust", "homeostat", "regulate", "control loop"],
    "guard": ["guard", "veto", "reject", "validate", "check", "invariant", "threshold"],
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS crossings (
    id        TEXT PRIMARY KEY,
    node_id   TEXT NOT NULL,
    archetype TEXT NOT NULL,
    score     REAL NOT NULL,
    distance  REAL NOT NULL,
    ts        TEXT NOT NULL,
    useful    INTEGER
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def archetypes_in(text: str) -> set[str]:
    low = text.lower()
    return {name for name, keys in ARCHETYPES.items() if any(k in low for k in keys)}


@dataclass(slots=True)
class Crossing:
    id: str
    node_id: str
    archetype: str
    score: float
    distance: float
    preview: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "archetype": self.archetype,
            "score": round(self.score, 4),
            "distance": round(self.distance, 4),
            "preview": self.preview,
        }


class SynchronicityMonitor:
    def __init__(
        self,
        ledger: LibidoLedger,
        cfg: JCRConfig | None = None,
        db_path: str | Path | None = None,
        d_min: float = 0.5,
        s_min: float = 0.5,
        precision_floor: float = 0.6,
        hard: bool = False,
    ) -> None:
        self.ledger = ledger
        self.cfg = cfg or JCRConfig()
        self.d_min = d_min
        self.s_min = s_min
        self.precision_floor = precision_floor
        self.hard = hard
        self._lock = threading.RLock()
        path = str(db_path or (self.cfg.home / "monitor.db"))
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------ scan

    def _distance(self, node, now: float) -> float:
        """Distance from the causal neighbourhood: 0 = just used, 1 = dormant."""
        if not node.last_activation:
            return 1.0
        try:
            ts = time.mktime(time.strptime(node.last_activation[:19], "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            return 1.0
        hours = max(0.0, (now - ts) / 3600.0)
        return 1.0 - math.exp(-hours / 24.0)

    def scan(self, text: str, project: str | None = None, k: int = 8, now: float | None = None) -> list[Crossing]:
        now = now if now is not None else time.time()
        buf_emb = self.ledger.embedder.embed(text)
        buf_arch = archetypes_in(text)
        if not buf_arch:
            return []  # condition 3 is mandatory

        out: list[Crossing] = []
        for node in self.ledger.all_nodes():
            cos = cosine(buf_emb, node.embedding)
            if cos < self.s_min:
                continue
            # condition 1: acausal / distant
            dist = self._distance(node, now)
            if dist < self.d_min:
                continue
            # condition 2: cross-domain
            if project is not None and node.project == project:
                continue
            # condition 3: shared archetype
            shared = buf_arch & archetypes_in(node.content)
            if not shared:
                continue
            archetype = sorted(shared)[0]
            cid = f"cross_{uuid.uuid4().hex[:12]}"
            preview = node.content if len(node.content) <= 200 else node.content[:197] + "..."
            crossing = Crossing(cid, node.id, archetype, cos * dist, dist, preview)
            self._record(crossing)
            self.ledger.reinforce([node.id], 0.05)  # soft: raise priority
            out.append(crossing)
        out.sort(key=lambda c: c.score, reverse=True)
        return out[:k]

    # ------------------------------------------------------------ calibration

    def _record(self, c: Crossing) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO crossings (id, node_id, archetype, score, distance, ts, useful) VALUES (?,?,?,?,?,?,NULL)",
                (c.id, c.node_id, c.archetype, c.score, c.distance, _now()),
            )
            self._conn.commit()

    def label(self, crossing_id: str, useful: bool) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE crossings SET useful = ? WHERE id = ?", (1 if useful else 0, crossing_id)
            )
            self._conn.commit()
            return cur.rowcount > 0

    def precision(self) -> float | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(useful),0) AS u FROM crossings WHERE useful IS NOT NULL"
            ).fetchone()
        return round(row["u"] / row["n"], 4) if row["n"] else None

    def may_inject(self) -> bool:
        """Hard injection only if enabled and precision holds above the floor."""
        p = self.precision()
        return bool(self.hard and p is not None and p >= self.precision_floor)

    def status(self) -> dict:
        with self._lock:
            total = int(self._conn.execute("SELECT COUNT(*) FROM crossings").fetchone()[0])
            labelled = int(self._conn.execute("SELECT COUNT(*) FROM crossings WHERE useful IS NOT NULL").fetchone()[0])
        return {
            "crossings": total,
            "labelled": labelled,
            "precision": self.precision(),
            "precision_floor": self.precision_floor,
            "hard": self.hard,
            "may_inject": self.may_inject(),
            "thresholds": {"d_min": self.d_min, "s_min": self.s_min},
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
