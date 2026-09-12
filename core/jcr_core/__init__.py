"""SINT-JCR core — Phase 0 substrate.

jcr_core provides the two foundations the rest of the runtime stands on:

* :mod:`jcr_core.events`  — an append-only event bus (the causal log).
* :mod:`jcr_core.ledger`  — the libido ledger (personal-unconscious memory field).

Neither depends on a model, network, or third-party package. They are the body.
"""

from jcr_core.types import Edge, Event, EventKind, Node, Register, Tier
from jcr_core.events import Bus, EventLog, SqliteIndex
from jcr_core.mimespool import MimeSpool, chain_hash
from jcr_core.embedding import Embedder, HashingEmbedder, cosine
from jcr_core.ledger import Activation, LibidoLedger
from jcr_core.psychoid import Affect, PsychoidSampler, veto_decision
from jcr_core.character import CharacterLedger, Trait
from jcr_core.compiler import CompiledContext, ContextCompiler
from jcr_core.config import JCRConfig

__version__ = "0.1.0"

__all__ = [
    "Edge",
    "Event",
    "EventKind",
    "Node",
    "Register",
    "Tier",
    "Bus",
    "EventLog",
    "SqliteIndex",
    "MimeSpool",
    "chain_hash",
    "Embedder",
    "HashingEmbedder",
    "cosine",
    "Activation",
    "LibidoLedger",
    "Affect",
    "PsychoidSampler",
    "veto_decision",
    "CharacterLedger",
    "Trait",
    "CompiledContext",
    "ContextCompiler",
    "JCRConfig",
    "__version__",
]
