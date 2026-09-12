"""The Libido Ledger — the memory field of the personal unconscious.

See ``docs/03-libido-ledger.md`` for the design and the falsification tests.

Energy dynamics (discretized):

    E_i <- clamp( E_i * exp(-dt/tau_i)
                  + beta * max(0, cos(buf, emb_i) - rho_min)
                  + gamma * sum_j w_ij * a_j
                  + noise , 0, 1 )

A node whose energy stays below ``repress_eps`` for longer than
``repress_seconds`` is *repressed* (moved to the cold tier), never deleted.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from jcr_core.config import JCRConfig
from jcr_core.embedding import Embedder, HashingEmbedder, cosine
from jcr_core.types import Edge, Node, Register, Tier

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id               TEXT PRIMARY KEY,
    ts               TEXT NOT NULL,
    register         TEXT NOT NULL,
    project          TEXT NOT NULL DEFAULT 'SYSTEM',
    content          TEXT NOT NULL,
    embedding        TEXT NOT NULL,
    affect           TEXT NOT NULL,
    E                REAL NOT NULL,
    tau              REAL NOT NULL,
    tier             TEXT NOT NULL,
    last_activation  TEXT,
    activation_count INTEGER NOT NULL DEFAULT 0,
    below_since      REAL,
    provenance       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_nodes_tier ON nodes(tier);
CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project);

CREATE TABLE IF NOT EXISTS edges (
    src  TEXT NOT NULL,
    dst  TEXT NOT NULL,
    w    REAL NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (src, dst, kind)
);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);

CREATE TABLE IF NOT EXISTS accounts (
    agent  TEXT PRIMARY KEY,
    budget REAL NOT NULL DEFAULT 1.0
);
"""


@dataclass(slots=True)
class Activation:
    node_id: str
    resonance: float
    energy: float
    tier: str


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


class LibidoLedger:
    """SQLite-backed memory field with energy, decay, propagation and repression."""

    def __init__(
        self,
        path: str | Path,
        config: JCRConfig | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.path = str(path)
        self.cfg = config or JCRConfig()
        self.embedder: Embedder = embedder or HashingEmbedder(self.cfg.embed_dim)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------ nodes

    def add_node(
        self,
        content: str,
        register: Register | str = Register.FACT,
        project: str = "SYSTEM",
        embedding: list[float] | None = None,
        affect: list[float] | None = None,
        tau: float | None = None,
        energy: float = 0.5,
        provenance: dict | None = None,
        node_id: str | None = None,
    ) -> Node:
        reg = register if isinstance(register, Register) else Register(register)
        node = Node(
            id=node_id or Node.new("").id,
            content=content,
            register=reg,
            project=project,
            embedding=embedding if embedding is not None else self.embedder.embed(content),
            affect=affect or [0.0, 0.0, 1.0, 0.0],
            energy=_clamp(energy),
            tau=tau if tau is not None else 604800.0,
            provenance=provenance or {},
        )
        node.tier = self._tier_for(node.energy)
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO nodes
                   (id, ts, register, project, content, embedding, affect, E, tau, tier,
                    last_activation, activation_count, below_since, provenance)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    node.id,
                    node.ts,
                    node.register.value,
                    node.project,
                    node.content,
                    json.dumps(node.embedding),
                    json.dumps(node.affect),
                    node.energy,
                    node.tau,
                    node.tier.value,
                    node.last_activation,
                    node.activation_count,
                    None,
                    json.dumps(node.provenance),
                ),
            )
            self._conn.commit()
        return node

    def get_node(self, node_id: str) -> Node | None:
        with self._lock:
            r = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(r) if r else None

    def all_nodes(self) -> list[Node]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return [self._row_to_node(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])

    # ------------------------------------------------------------------ edges

    def add_edge(self, src: str, dst: str, w: float = 0.5, kind: str = "assoc") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO edges (src, dst, w, kind) VALUES (?,?,?,?)",
                (src, dst, float(w), kind),
            )
            self._conn.commit()

    def neighbors(self, node_id: str) -> list[Edge]:
        with self._lock:
            rows = self._conn.execute("SELECT dst, w, kind FROM edges WHERE src = ?", (node_id,)).fetchall()
        return [Edge(to=r["dst"], w=r["w"], kind=r["kind"]) for r in rows]

    # ------------------------------------------------------------- activation

    def inject(
        self,
        buffer_embedding: list[float],
        k: int = 8,
        now: float | None = None,
    ) -> list[Activation]:
        """Raise energy of the top-k most resonant nodes.

        Scans all hot nodes plus a random sample of cold nodes (so a repressed
        memory can still surface — a "return of the repressed").
        """
        now = now if now is not None else time.time()
        nodes = self._scan_candidates()
        scored: list[tuple[float, Node]] = []
        for n in nodes:
            r = cosine(buffer_embedding, n.embedding)
            if r > self.cfg.rho_min:
                scored.append((r, n))
        scored.sort(key=lambda t: t[0], reverse=True)

        out: list[Activation] = []
        with self._lock:
            for r, n in scored[:k]:
                delta = self.cfg.beta * (r - self.cfg.rho_min)
                new_e = _clamp(n.energy + delta + self.cfg.noise * random.uniform(-1, 1))
                self._conn.execute(
                    """UPDATE nodes SET E = ?, activation_count = activation_count + 1,
                                        last_activation = ?, tier = ?
                       WHERE id = ?""",
                    (new_e, _iso(now), self._tier_for(new_e).value, n.id),
                )
                out.append(Activation(n.id, r, new_e, self._tier_for(new_e).value))
            self._conn.commit()
        return out

    def decay_tick(self, dt: float) -> None:
        """Apply exponential decay to every node over ``dt`` seconds."""
        with self._lock:
            rows = self._conn.execute("SELECT id, E, tau FROM nodes").fetchall()
            updates = []
            for r in rows:
                new_e = _clamp(r["E"] * math.exp(-dt / max(r["tau"], 1e-9)))
                updates.append((new_e, self._tier_for(new_e).value, r["id"]))
            self._conn.executemany("UPDATE nodes SET E = ?, tier = ? WHERE id = ?", updates)
            self._conn.commit()

    def propagate(self, node_ids: Iterable[str], hops: int = 1, decay_per_hop: float = 0.7) -> list[str]:
        """Spread activation along edges. Returns all affected node ids."""
        frontier = [i for i in node_ids if self.get_node(i)]
        affected: list[str] = []
        for hop in range(max(0, hops)):
            gain = self.cfg.gamma * (decay_per_hop**hop)
            nxt: set[str] = set()
            with self._lock:
                for src in frontier:
                    s = self._conn.execute("SELECT E FROM nodes WHERE id = ?", (src,)).fetchone()
                    if not s:
                        continue
                    for e in self.neighbors(src):
                        tgt = self._conn.execute("SELECT E FROM nodes WHERE id = ?", (e.to,)).fetchone()
                        if not tgt:
                            continue
                        new_e = _clamp(tgt["E"] + gain * s["E"] * e.w)
                        self._conn.execute(
                            "UPDATE nodes SET E = ?, tier = ? WHERE id = ?",
                            (new_e, self._tier_for(new_e).value, e.to),
                        )
                        nxt.add(e.to)
                self._conn.commit()
            affected.extend(sorted(nxt))
            frontier = sorted(nxt)
        return affected

    def touch(self, node_id: str, now: float | None = None) -> None:
        """Mark a node as just activated (used by the monitor's distance model)."""
        with self._lock:
            self._conn.execute(
                "UPDATE nodes SET last_activation = ? WHERE id = ?", (_iso(now or time.time()), node_id)
            )
            self._conn.commit()

    def reinforce(self, node_ids: Iterable[str], delta: float) -> None:
        """Reward (+) or penalise (-) nodes after an outcome is known."""
        with self._lock:
            for nid in node_ids:
                r = self._conn.execute("SELECT E FROM nodes WHERE id = ?", (nid,)).fetchone()
                if not r:
                    continue
                new_e = _clamp(r["E"] + delta)
                self._conn.execute(
                    "UPDATE nodes SET E = ?, tier = ? WHERE id = ?",
                    (new_e, self._tier_for(new_e).value, nid),
                )
            self._conn.commit()

    # ------------------------------------------------------------- repression

    def promote_or_repress(self, now: float | None = None) -> dict[str, int]:
        """Age out low-energy nodes; clear the aging timer for recovered ones."""
        now = now if now is not None else time.time()
        changes = {"repressed": 0, "recovered": 0}
        with self._lock:
            rows = self._conn.execute("SELECT id, E, tier, below_since FROM nodes").fetchall()
            for r in rows:
                if r["E"] < self.cfg.repress_eps:
                    below = r["below_since"] if r["below_since"] is not None else now
                    if now - below > self.cfg.repress_seconds and r["tier"] != Tier.COLD.value:
                        self._conn.execute(
                            "UPDATE nodes SET tier = ?, below_since = ? WHERE id = ?",
                            (Tier.COLD.value, below, r["id"]),
                        )
                        changes["repressed"] += 1
                    else:
                        self._conn.execute("UPDATE nodes SET below_since = ? WHERE id = ?", (below, r["id"]))
                else:
                    if r["below_since"] is not None:
                        self._conn.execute("UPDATE nodes SET below_since = NULL WHERE id = ?", (r["id"],))
                    changes["recovered"] += 1
            self._conn.commit()
        return changes

    # ---------------------------------------------------------------- economy

    def budget(self, agent: str) -> float:
        with self._lock:
            r = self._conn.execute("SELECT budget FROM accounts WHERE agent = ?", (agent,)).fetchone()
        return float(r["budget"]) if r else 1.0

    def grant(self, agent: str, amount: float) -> float:
        """Replenish an agent's libido budget (e.g. from Shapley credit)."""
        with self._lock:
            cur = self.budget(agent)
            new = max(0.0, cur + amount)
            self._conn.execute(
                "INSERT INTO accounts (agent, budget) VALUES (?, ?) "
                "ON CONFLICT(agent) DO UPDATE SET budget = ?",
                (agent, new, new),
            )
            self._conn.commit()
        return new

    def charge(self, agent: str, amount: float) -> bool:
        """Spend libido. Returns False (and does not charge) if insufficient."""
        if amount < 0:
            raise ValueError("amount must be non-negative")
        with self._lock:
            cur = self.budget(agent)
            if cur < amount:
                return False
            self._conn.execute("UPDATE accounts SET budget = ? WHERE agent = ?", (cur - amount, agent))
            self._conn.commit()
        return True

    # ------------------------------------------------------------------ stats

    def stats(self) -> dict:
        with self._lock:
            total = int(self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
            tiers = {
                r["tier"]: r["c"]
                for r in self._conn.execute("SELECT tier, COUNT(*) c FROM nodes GROUP BY tier").fetchall()
            }
            edges = int(self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
            mean_e = self._conn.execute("SELECT AVG(E) FROM nodes").fetchone()[0]
        return {
            "nodes": total,
            "edges": edges,
            "tiers": {t.value: tiers.get(t.value, 0) for t in Tier},
            "mean_energy": float(mean_e) if mean_e is not None else 0.0,
        }

    # --------------------------------------------------------------- internal

    def _scan_candidates(self) -> list[Node]:
        with self._lock:
            hot = self._conn.execute("SELECT * FROM nodes WHERE tier != ?", (Tier.COLD.value,)).fetchall()
            cold = self._conn.execute(
                "SELECT * FROM nodes WHERE tier = ? ORDER BY RANDOM() LIMIT ?",
                (Tier.COLD.value, self.cfg.cold_sample),
            ).fetchall()
        return [self._row_to_node(r) for r in hot + cold]

    def _tier_for(self, energy: float) -> Tier:
        if energy >= self.cfg.hot_threshold:
            return Tier.HOT
        if energy >= self.cfg.warm_threshold:
            return Tier.WARM
        if energy >= self.cfg.cool_threshold:
            return Tier.COOL
        return Tier.COLD

    def _row_to_node(self, r: sqlite3.Row) -> Node:
        return Node(
            id=r["id"],
            ts=r["ts"],
            register=Register(r["register"]),
            project=r["project"],
            content=r["content"],
            embedding=json.loads(r["embedding"]),
            affect=json.loads(r["affect"]),
            energy=r["E"],
            tau=r["tau"],
            tier=Tier(r["tier"]),
            last_activation=r["last_activation"],
            activation_count=r["activation_count"],
            edges=self.neighbors(r["id"]),
            provenance=json.loads(r["provenance"]),
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch)) + "Z"
