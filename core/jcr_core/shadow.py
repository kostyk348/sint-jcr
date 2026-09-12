"""Artifact Shadow — adversarial critic with costly signaling (Phase 2).

docs/02-game-theory.md §4, the actionable result: **free critique is cheap talk
and uninformative.** A critic with no cost emits critique whether or not a defect
exists, so the receiver learns almost nothing. That is *why* LLM critics
hallucinate criticism.

The engineering requirement: a Shadow critique must carry a **falsifiable
artifact** (a command, a test, a counterexample) that a verifier can check. Only
confirmed artifacts count. Cheap-talk critiques are logged with zero weight.

The default critic here is deterministic (scans a draft for harmful commands and
supplies the command as the artifact); a real LLM critic can be plugged in behind
the same ``Critic`` protocol without changing the mechanism.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from jcr_core.selfplay import ORACLE_PATTERNS, is_harmful


@dataclass(slots=True)
class Critique:
    claim: str
    artifact: str | None = None  # None => cheap talk
    severity: float = 0.5


@dataclass(slots=True)
class Verdict:
    confirmed: bool
    detail: str = ""


class Critic(Protocol):
    def critique(self, draft: str) -> list[Critique]:  # pragma: no cover - protocol
        ...


class Verifier(Protocol):
    def verify(self, artifact: str, draft: str) -> Verdict:  # pragma: no cover - protocol
        ...


class PatternCommandCritic:
    """Deterministic critic: flags lines containing harmful command patterns."""

    def critique(self, draft: str) -> list[Critique]:
        out: list[Critique] = []
        for line in draft.splitlines():
            low = line.lower()
            for p in ORACLE_PATTERNS:
                if p in low:
                    out.append(Critique(claim=f"harmful command pattern {p!r}", artifact=line.strip(), severity=0.9))
                    break
        return out


class OracleVerifier:
    """Confirms an artifact only if the oracle agrees it is harmful."""

    def verify(self, artifact: str, draft: str) -> Verdict:
        ok = is_harmful(artifact)
        return Verdict(ok, "oracle-confirmed" if ok else "oracle-rejected")


class CallableCritic:
    def __init__(self, fn: Callable[[str], list[Critique]]) -> None:
        self._fn = fn

    def critique(self, draft: str) -> list[Critique]:
        return self._fn(draft)


class CallableVerifier:
    def __init__(self, fn: Callable[[str, str], Verdict]) -> None:
        self._fn = fn

    def verify(self, artifact: str, draft: str) -> Verdict:
        return self._fn(artifact, draft)


class NullCritic:
    def critique(self, draft: str) -> list[Critique]:
        return []


class ShadowLedger:
    """Cost ledger: per-critique confirmation — the evidence base for Shapley."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS shadow_reviews (
                seq          INTEGER PRIMARY KEY AUTOINCREMENT,
                claim        TEXT NOT NULL,
                has_artifact INTEGER NOT NULL,
                confirmed    INTEGER NOT NULL,
                ts           TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def record(self, claim: str, has_artifact: bool, confirmed: bool) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO shadow_reviews (claim, has_artifact, confirmed, ts) VALUES (?,?,?,?)",
                (claim, 1 if has_artifact else 0, 1 if confirmed else 0, _now()),
            )
            self._conn.commit()

    def stats(self) -> dict:
        with self._lock:
            total = int(self._conn.execute("SELECT COUNT(*) FROM shadow_reviews").fetchone()[0])
            artifacts = int(self._conn.execute("SELECT COUNT(*) FROM shadow_reviews WHERE has_artifact = 1").fetchone()[0])
            confirmed = int(self._conn.execute("SELECT COUNT(*) FROM shadow_reviews WHERE confirmed = 1").fetchone()[0])
        return {
            "critiques": total,
            "with_artifact": artifacts,
            "confirmed": confirmed,
            "cheap_talk": total - artifacts,
            "confirmation_rate": round(confirmed / artifacts, 4) if artifacts else None,
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class Shadow:
    def __init__(self, critic: Critic | None = None, verifier: Verifier | None = None, ledger: ShadowLedger | None = None) -> None:
        self.critic = critic or PatternCommandCritic()
        self.verifier = verifier or OracleVerifier()
        self.ledger = ledger

    def review(self, draft: str, veto_threshold: float = 0.7) -> dict:
        critiques = self.critic.critique(draft)
        reviewed: list[dict] = []
        veto_worthy: list[dict] = []
        for c in critiques:
            has_artifact = bool(c.artifact)
            confirmed = False
            detail = "cheap-talk"
            if has_artifact:
                v = self.verifier.verify(c.artifact, draft)
                confirmed = v.confirmed
                detail = v.detail
            if self.ledger:
                self.ledger.record(c.claim, has_artifact, confirmed)
            entry = {
                "claim": c.claim,
                "artifact": c.artifact,
                "severity": c.severity,
                "confirmed": confirmed,
                "detail": detail,
            }
            reviewed.append(entry)
            if confirmed and c.severity >= veto_threshold:
                veto_worthy.append(entry)

        return {
            "critiques": reviewed,
            "veto": bool(veto_worthy),
            "veto_worthy": veto_worthy,
            "cheap_talk": sum(1 for e in reviewed if not e["artifact"]),
            "stats": self.ledger.stats() if self.ledger else None,
        }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
