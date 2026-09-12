"""Runtime — the object the daemon, the MCP facade and the harness plugin talk to.

Wiring (log/state split):
    bus       -> MimeSpool  (append-only, hash-chained `.eml`; SOURCE OF TRUTH)
    ledger    -> SQLite     (derived state; rebuildable by replay)
    character -> SQLite     (derived state; dispositions)
    psychoid  -> in-memory  (somatic signals, affect vector)
"""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from jcr_core.character import CharacterLedger
from jcr_core.compiler import ContextCompiler
from jcr_core.config import JCRConfig
from jcr_core.embedding import Embedder, HashingEmbedder
from jcr_core.events import Bus, EventLog
from jcr_core.induction import DreamCycle
from jcr_core.ledger import LibidoLedger
from jcr_core.mimespool import MimeSpool
from jcr_core.psychoid import PsychoidSampler, veto_decision
from jcr_core.types import Event, EventKind, Register


class Runtime:
    def __init__(self, config: JCRConfig | None = None, embedder: Embedder | None = None) -> None:
        self.cfg = config or JCRConfig()
        self.cfg.ensure_home()

        # bus: the immutable log is the .eml spool by default
        if self.cfg.bus_format == "sqlite":
            self.log = EventLog(self.cfg.db_path())
        else:
            self.log = MimeSpool(self.cfg.spool_dir())
        self.bus = Bus(self.log)

        self.ledger = LibidoLedger(self.cfg.db_path(), self.cfg, embedder or HashingEmbedder(self.cfg.embed_dim))
        self.character = CharacterLedger(self.cfg.character_path())
        self.dream = DreamCycle(self.cfg.dream_path(), self.character)
        self.psychoid = PsychoidSampler()
        self.compiler = ContextCompiler(self.ledger, self.character, self.cfg)
        self.started = time.time()
        self._last_turn: str | None = None

    # ------------------------------------------------------------------ write

    def observe(self, text: str, session: str | None = None, turn: int | None = None, k: int = 8) -> dict:
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
            Event(kind=EventKind.SYNC_CHECK, source="runtime", payload={"buffer_len": len(text), "activated": len(activations)}, session=session, turn=turn)
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
        self.bus.publish(Event(kind=EventKind.RESONANCE, source="runtime", payload={"node_id": node.id, "project": project}))
        return {"node_id": node.id, "tier": node.tier.value, "energy": node.energy}

    def outcome(self, node_ids: list[str], useful: bool, turn_id: str | None = None) -> dict:
        delta = 0.10 if useful else -0.15
        self.ledger.reinforce(node_ids, delta)
        if useful:
            self.psychoid.note_success()
        else:
            self.psychoid.note_error(weight=0.5)
        labelled = turn_id or self._last_turn
        if labelled:
            self.dream.label(labelled, useful)
        self.bus.publish(Event(kind=EventKind.OUTCOME, source="runtime", payload={"node_ids": node_ids, "useful": useful, "delta": delta, "turn_id": labelled}))
        return {"reinforced": len(node_ids), "delta": delta, "turn_id": labelled}

    def teach(self, statement: str, weight: float = 0.5, scope: str = "*", polarity: float = 1.0) -> dict:
        """Owner teaching: install a disposition into the character ledger."""
        t = self.character.teach(statement, weight=weight, scope=scope, polarity=polarity)
        self.bus.publish(Event(kind=EventKind.RESONANCE, source="character", payload={"trait_id": t.id, "statement": t.statement}))
        return {"trait_id": t.id, "statement": t.statement, "weight": t.weight, "scope": t.scope}

    # --------------------------------------------------------------- actuator

    def params(self) -> dict:
        """Psychoid coupling: affect -> generation parameters."""
        affect = self.psychoid.sample()
        params = PsychoidSampler.params_for(affect)
        self.bus.publish(Event(kind=EventKind.AFFECT, source="psychoid", priority=affect.tension, payload={"affect": asdict(affect), "params": params}))
        return {"affect": asdict(affect), "params": params}

    def veto(self, tool: str, args: object = None) -> dict:
        """Veto decision for a tool call (applied by the harness at permission.ask)."""
        affect = self.psychoid.sample()
        decision = veto_decision(tool, args, affect)
        if decision["status"] != "allow":
            self.bus.publish(Event(kind=EventKind.VETO, source="arbiter", priority=1.0, payload={"tool": tool, "decision": decision}))
        return decision

    def compile(self, text: str = "", budget_tokens: int = 1200, k: int = 8) -> dict:
        """Context compiler: budgeted assembly for the next model call.

        Also records a *turn* (which traits and nodes were injected) so the
        dream cycle can later correlate them with the outcome. This is what
        closes the personality loop.
        """
        c = self.compiler.compile(text, budget_tokens=budget_tokens, k=k)
        turn_id = self.dream.record_turn(
            session=None,
            trait_ids=[t["id"] for t in c.traits],
            node_ids=[n["node_id"] for n in c.nodes],
            text=text,
        )
        self._last_turn = turn_id
        out = asdict(c)
        out["turn_id"] = turn_id
        return out

    # ------------------------------------------------------------ dream cycle

    def dream_consolidate(self, min_evidence: int = 2) -> dict:
        report = self.dream.consolidate(min_evidence=min_evidence)
        self.bus.publish(Event(kind=EventKind.DREAM, source="dream", payload=report.as_dict()))
        return report.as_dict()

    def telemetry(self) -> dict:
        return {
            "dream": self.dream.telemetry(),
            "character": self.character.stats(),
            "ledger": self.ledger.stats(),
        }

    def trait_proposals(self) -> list[dict]:
        return self.dream.proposals()

    def ratify(self, proposal_id: str, weight: float = 0.5) -> dict | None:
        out = self.dream.ratify(proposal_id, weight=weight)
        if out:
            self.bus.publish(Event(kind=EventKind.DREAM, source="character", payload={"ratified": out}))
        return out

    # ------------------------------------------------------------------- read

    def state(self) -> dict:
        chain = self.log.verify_chain() if isinstance(self.log, MimeSpool) else {"ok": None, "checked": 0, "broken_at": None}
        return {
            "version": "0.1.0",
            "uptime_s": round(time.time() - self.started, 1),
            "bus": {"format": self.cfg.bus_format, "events": self.log.count(), "chain": chain},
            "ledger": self.ledger.stats(),
            "character": self.character.stats(),
            "telemetry": self.dream.telemetry(),
        }

    def events(self, since: int = 0, kinds: list[str] | None = None, limit: int = 200) -> list[dict]:
        return [e.to_row() for e in self.bus.drain(since=since, kinds=kinds, limit=limit)]

    def plan(self, text: str = "", k: int = 8) -> dict:
        obs = self.observe(text, k=k) if text else {"activations": []}
        return {"promote": [a["node_id"] for a in obs["activations"]], "soft": True, "reason": "phase0-resonance"}

    def character_state(self) -> dict:
        return {"stats": self.character.stats(), "drift": self.character.drift(), "traits": [asdict(t) for t in self.character.all_traits()]}

    def close(self) -> None:
        self.dream.close()
        self.ledger.close()
        self.character.close()
        self.log.close()

    @classmethod
    def open(cls, home: str | Path | None = None) -> "Runtime":
        cfg = JCRConfig()
        if home is not None:
            cfg.home = Path(home).expanduser()
        return cls(cfg)
