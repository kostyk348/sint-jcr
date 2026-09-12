"""The context compiler — budgeted assembly of what the model sees.

See ``docs/11-harness.md`` §4. This is the function that makes the harness an
executive rather than a static prompt: instead of dumping everything into the
context, it *selects* under a token budget, in a defined order:

    1. character traits (who I am)      — always, they are short
    2. promoted memory nodes (what I know) — by resonance, until budget
    3. a system addendum describing both

Phase 0 is deliberately simple and deterministic. The arbiter (Phase 3) and the
synchronicity monitor (Phase 4) will feed richer signals into the same budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jcr_core.character import CharacterLedger, Trait
from jcr_core.config import JCRConfig
from jcr_core.ledger import LibidoLedger


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass(slots=True)
class CompiledContext:
    nodes: list[dict] = field(default_factory=list)
    traits: list[dict] = field(default_factory=list)
    system_addendum: str = ""
    tokens_estimate: int = 0
    budget: int = 0
    dropped: int = 0


class ContextCompiler:
    def __init__(self, ledger: LibidoLedger, character: CharacterLedger, cfg: JCRConfig | None = None) -> None:
        self.ledger = ledger
        self.character = character
        self.cfg = cfg or JCRConfig()

    def compile(self, text: str, budget_tokens: int = 1200, k: int = 8) -> CompiledContext:
        out = CompiledContext(budget=budget_tokens)

        # 1) character traits — always first
        traits: list[Trait] = self.character.traits_for(text, k=self.cfg.character_traits_in_context)
        used = 0
        for t in traits:
            line = f"{'DO' if t.polarity >= 0 else 'AVOID'}: {t.statement}"
            used += estimate_tokens(line)
            out.traits.append({"id": t.id, "statement": t.statement, "weight": round(t.weight, 3), "polarity": t.polarity})

        # 2) memory nodes — by resonance, until the budget is spent
        embedding = self.ledger.embedder.embed(text)
        activations = self.ledger.inject(embedding, k=k)
        for a in activations:
            node = self.ledger.get_node(a.node_id)
            if node is None:
                continue
            preview = node.content if len(node.content) <= 240 else node.content[:237] + "..."
            cost = estimate_tokens(preview)
            if used + cost > budget_tokens:
                out.dropped += 1
                continue
            used += cost
            out.nodes.append(
                {
                    "node_id": node.id,
                    "register": node.register.value,
                    "project": node.project,
                    "resonance": round(a.resonance, 4),
                    "preview": preview,
                }
            )

        out.tokens_estimate = used
        out.system_addendum = self._render(traits, out.nodes)
        return out

    @staticmethod
    def _render(traits: list[Trait], nodes: list[dict]) -> str:
        parts: list[str] = []
        if traits:
            parts.append("## Character (operative dispositions)")
            for t in traits:
                head = "Lean toward" if t.polarity >= 0 else "Guard against"
                parts.append(f"- {head}: {t.statement} (w={t.weight:.2f})")
        if nodes:
            parts.append("\n## Resonant memory (soft, from the local field)")
            for n in nodes:
                parts.append(f"- [{n['register']}/{n['project']}] {n['preview']}")
        return "\n".join(parts)
