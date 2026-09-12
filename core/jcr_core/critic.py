"""LLM critic behind the Shadow protocol.

The Shadow mechanism (docs/02 §4) requires every critique to carry a
falsifiable artifact. This module turns a chat model into a ``Critic`` that is
*asked for artifacts* and whose output is parsed strictly — a critique without
an artifact is kept but marked cheap talk by the Shadow, with zero weight.

Deterministic by default in tests: inject a ``transport`` to avoid network.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Callable

from jcr_core.shadow import Critique

SYSTEM_PROMPT = (
    "You are an adversarial reviewer. For each real defect you find, output one JSON object with:\n"
    '  "claim": a one-line description of the defect,\n'
    '  "artifact": a FALSIFIABLE artifact that demonstrates it (a reproducing command, a minimal '
    "counterexample, a failing test) — or null if you cannot produce one,\n"
    '  "severity": a number in [0,1].\n'
    "Return ONLY a JSON array. A critique without an artifact carries no weight, so do not invent "
    "artifacts; if you cannot demonstrate the defect, set artifact to null."
)


def parse_critiques(text: str) -> list[Critique]:
    """Parse a model response into critiques. Tolerates prose around the JSON."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        raw = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    out: list[Critique] = []
    if not isinstance(raw, list):
        return []
    for item in raw:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        if not claim:
            continue
        artifact = item.get("artifact")
        artifact = str(artifact) if artifact else None
        try:
            severity = float(item.get("severity", 0.5))
        except (TypeError, ValueError):
            severity = 0.5
        out.append(Critique(claim=claim, artifact=artifact, severity=severity))
    return out


@dataclass
class HttpCritic:
    """A chat-model critic. ``transport(url, headers, body) -> str`` is injectable."""

    base_url: str
    model: str
    api_key: str = ""
    timeout: float = 60.0
    transport: Callable[[str, dict, bytes], str] | None = None

    def _raw(self, url: str, headers: dict, body: bytes) -> str:
        """Return the raw HTTP response body (transport is injectable)."""
        if self.transport:
            return self.transport(url, headers, body)
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8")

    def critique(self, draft: str) -> list[Critique]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": draft},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            raw = self._raw(self.base_url.rstrip("/") + "/chat/completions", headers, body)
        except Exception:  # noqa: BLE001 - a failed critic must not break the loop
            return []
        return parse_critiques(extract_content(raw))


def extract_content(raw: str) -> str:
    """Extract the assistant message from a chat-completion body, or pass through."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return raw


class MockCritic:
    """Deterministic critic for tests and dry runs."""

    def __init__(self, critiques: list[Critique] | None = None) -> None:
        self._critiques = critiques or []

    def critique(self, draft: str) -> list[Critique]:
        return list(self._critiques)
