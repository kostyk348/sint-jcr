"""Core types for the JCR runtime.

These mirror the JSON schemas in ``schemas/`` of the repository:
``node.schema.json`` and ``event.schema.json``. Keep them in sync.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Register(str, Enum):
    """Semantic register of a memory node (inherited from SINT)."""

    SENSE = "SENSE"
    FACT = "FACT"
    LOGIC = "LOGIC"
    OPINION = "OPINION"
    ACTION = "ACTION"
    CAUSALITY = "CAUSALITY"


class Tier(str, Enum):
    """Relevance tier of a node in the memory field."""

    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"


class EventKind(str, Enum):
    """Every signal that can travel on the resonance bus."""

    TURN_OPEN = "turn_open"
    TURN_CLOSE = "turn_close"
    AFFECT = "affect"
    ACTIVATION = "activation"
    RESONANCE = "resonance"
    CROSSING = "crossing"
    BID = "bid"
    VETO = "veto"
    ARBITRATE = "arbitrate"
    INJECT = "inject"
    SYNC_CHECK = "sync_check"
    OUTCOME = "outcome"
    DREAM = "dream"
    ERROR = "error"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@dataclass(slots=True)
class Edge:
    """A directed associative link between two nodes."""

    to: str
    w: float = 0.5
    kind: str = "assoc"  # assoc | contradicts | refines | archetype


@dataclass(slots=True)
class Node:
    """An autonomous memory capsule — the unit of the libido field."""

    id: str
    content: str
    register: Register = Register.FACT
    project: str = "SYSTEM"
    ts: str = field(default_factory=_now_iso)
    embedding: list[float] = field(default_factory=list)
    affect: list[float] = field(default_factory=lambda: [0.0, 0.0, 1.0, 0.0])
    energy: float = 0.5
    tau: float = 604800.0  # decay half-life, seconds (7 days)
    tier: Tier = Tier.WARM
    last_activation: str | None = None
    activation_count: int = 0
    edges: list[Edge] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(content: str, **kw: Any) -> "Node":
        return Node(id=_new_id("n"), content=content, **kw)


@dataclass(slots=True)
class Event:
    """Envelope for a bus event. Mirrors ``schemas/event.schema.json``."""

    kind: EventKind | str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: float = 0.0
    caused_by: list[str] = field(default_factory=list)
    session: str | None = None
    turn: int | None = None
    id: str = field(default_factory=lambda: _new_id("evt"))
    ts: str = field(default_factory=_now_iso)
    seq: int | None = None  # assigned by the log on persist
    prev_hash: str | None = None  # hash-chain: previous event hash
    hash: str | None = None  # hash-chain: this event's hash

    def kind_value(self) -> str:
        return self.kind.value if isinstance(self.kind, EventKind) else str(self.kind)

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "kind": self.kind_value(),
            "source": self.source,
            "priority": float(self.priority),
            "payload": self.payload,
            "caused_by": self.caused_by,
            "session": self.session,
            "turn": self.turn,
            "seq": self.seq,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }
