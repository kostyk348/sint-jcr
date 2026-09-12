"""Runtime — the object the daemon, the MCP facade and the harness plugin all talk to.

It wires the bus and the ledger together and exposes the handful of operations
that define Phase 0: observe a buffer, report state, drain events, record outcomes.
"""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from jcr_core.config import JCRConfig
from jcr_core.embedding import Embedder, HashingEmbedder
from jcr_core.events import Bus, EventLog
from jcr_core.ledger import LibidoLedger
from jcr_core.types import Event, EventKind, Register


class Runtime:
    def __init__(self, config: JCRConfig | None = None, embedder: Embedder | None = None) -> None:
        self.cfg = config or JCRConfig()
        self.cfg.ensure_home()
        self.log = EventLog(self.cfg.db_path())
        self.bus = Bus(self.log)
        self.ledger = LibidoLedger(self.cfg.db_path(), self.cfg, embedder or HashingEmbedder(self.cfg.embed_dim))
        self.started = time.time()

    # ------------------------------------------------------------------ write

    def observe(
        self,
        text: str,
        session: str | None = None,
        turn: int | None = None,
        k: int = 8,
    ) -> dict:
        """Push the live buffer into the field; return the top activations.

        This is the soft-synchronicity path: it raises priority, it does not
        seize the conversation.
        """
        emb = self.ledger.embedder.embed(text)
        activations = self.ledger.inject(emb, k=k)
        for a in activations:
            self.bus.publish(
                Event(
                    kind=EventKind.ACTIVATION,
                    source="ledger",
                    priority=a.resonance,
                    payload={"node_id": a.node_id, "resonance": a.resonance, "energy": a.energy},
                    session=session,
                    turn=turn,
                )
            )
        self.bus.publish(
            Event(
                kind=EventKind.SYNC_CHECK,
                source="runtime",
                payload={"buffer_len": len(text), "activated": len(activations)},
                session=session,
                turn=turn,
            )
        )
        return {"activations": [asdict(a) for a in activations]}

    def remember(
        self,
        content: str,
        register: Register | str = Register.FACT,
        project: str = "SYSTEM",
        provenance: dict | None = None,
    ) -> dict:
        node = self.ledger.add_node(content, register=register, project=project, provenance=provenance)
        self.bus.publish(
            Event(
                kind=EventKind.RESONANCE,
                source="runtime",
                payload={"node_id": node.id, "project": project},
            )
        )
        return {"node_id": node.id, "tier": node.tier.value, "energy": node.energy}

    def outcome(self, node_ids: list[str], useful: bool) -> dict:
        """Label activated nodes: reinforce useful, penalise noise. Feeds calibration."""
        delta = 0.10 if useful else -0.15
        self.ledger.reinforce(node_ids, delta)
        self.bus.publish(
            Event(
                kind=EventKind.OUTCOME,
                source="runtime",
                payload={"node_ids": node_ids, "useful": useful, "delta": delta},
            )
        )
        return {"reinforced": len(node_ids), "delta": delta}

    # ------------------------------------------------------------------- read

    def state(self) -> dict:
        return {
            "version": "0.1.0",
            "uptime_s": round(time.time() - self.started, 1),
            "events": self.log.count(),
            "ledger": self.ledger.stats(),
        }

    def events(self, since: int = 0, kinds: list[str] | None = None, limit: int = 200) -> list[dict]:
        return [e.to_row() | {"seq": e.seq} for e in self.bus.drain(since=since, kinds=kinds, limit=limit)]

    def plan(self, text: str = "", k: int = 8) -> dict:
        """Phase 0 assembly plan: which nodes to promote for the next call.

        No model, no arbiter yet — the arbiter lands in Phase 3. This exists so
        the harness has something to consume from day one.
        """
        obs = self.observe(text, k=k) if text else {"activations": []}
        return {
            "promote": [a["node_id"] for a in obs["activations"]],
            "soft": True,
            "reason": "phase0-resonance",
        }

    def close(self) -> None:
        self.ledger.close()
        self.log.close()

    # ------------------------------------------------------------- factories

    @classmethod
    def open(cls, home: str | Path | None = None) -> "Runtime":
        cfg = JCRConfig()
        if home is not None:
            cfg.home = Path(home).expanduser()
        return cls(cfg)
