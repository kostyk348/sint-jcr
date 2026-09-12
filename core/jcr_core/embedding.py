"""Embedding interface and a zero-dependency default.

Phase 0 must run with no model and no downloads, so the default embedder is a
deterministic hashing embedder. A real local embedder (e.g. fastembed) can be
dropped in later behind the same :class:`Embedder` protocol.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

_WORD = re.compile(r"[A-Za-z0-9_]+")


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]:  # pragma: no cover - protocol
        ...


class HashingEmbedder:
    """Deterministic feature-hashing embedder over word + char-trigram features.

    Not semantically rich, but stable, fast, dependency-free, and good enough to
    exercise the ledger and its falsification tests. It makes the field *work*
    before making it *smart*.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        low = text.lower()
        words = _WORD.findall(low)
        feats: list[str] = list(words)
        for i in range(max(0, len(low) - 2)):
            feats.append(low[i : i + 3])
        for f in feats:
            h = hashlib.blake2b(f.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if (h[4] & 1) else -1.0
            # words weigh more than character trigrams
            v[idx] += sign * (2.0 if f in words else 1.0)
        return _l2(v)


def _l2(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0.0:
        return v
    return [x / norm for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Returns 0.0 on empty or zero vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))
