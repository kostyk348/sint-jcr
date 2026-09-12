"""jcr-mcp — the portable MCP facade over the JCR runtime.

IMPORTANT: this facade cannot enforce anything. MCP is called *by the model*, so
it can only advise. Real enforcement (veto, context rewrite, parameter control)
lives in ``harness/`` via opencode plugin hooks. This server exists so that any
MCP host can read state and feed observations — it is a port, not the executive.

See docs/11-harness.md.
"""

from __future__ import annotations

from fastmcp import FastMCP

from jcr_core.runtime import Runtime

mcp = FastMCP("jcr", version="0.1.0")

_rt: Runtime | None = None


def runtime() -> Runtime:
    global _rt
    if _rt is None:
        _rt = Runtime()
    return _rt


@mcp.tool()
def jcr_state() -> dict:
    """Current runtime state: uptime, event count, ledger statistics."""
    return runtime().state()


@mcp.tool()
def jcr_observe(text: str, session: str | None = None, turn: int = 0) -> dict:
    """Feed the live context buffer into the field; returns top activations (soft mode)."""
    return runtime().observe(text, session=session, turn=turn)


@mcp.tool()
def jcr_remember(content: str, register: str = "FACT", project: str = "SYSTEM") -> dict:
    """Store a memory node in the libido field."""
    return runtime().remember(content, register=register, project=project)


@mcp.tool()
def jcr_plan(text: str = "", k: int = 8) -> dict:
    """Produce an assembly plan: which nodes to promote for the next call."""
    return runtime().plan(text, k=k)


@mcp.tool()
def jcr_compile(text: str = "", budget: int = 1200, k: int = 8) -> dict:
    """Budgeted context assembly: character traits + resonant nodes + system addendum."""
    return runtime().compile(text, budget_tokens=budget, k=k)


@mcp.tool()
def jcr_params() -> dict:
    """Psychoid coupling: current affect vector and derived generation parameters."""
    return runtime().params()


@mcp.tool()
def jcr_veto(tool: str, args: str = "") -> dict:
    """Veto decision (allow/ask/deny) for a proposed tool call."""
    return runtime().veto(tool, args)


@mcp.tool()
def jcr_teach(statement: str, weight: float = 0.5, scope: str = "*", polarity: float = 1.0) -> dict:
    """Install a disposition into the character ledger (grows the harness personality)."""
    return runtime().teach(statement, weight=weight, scope=scope, polarity=polarity)


@mcp.tool()
def jcr_character() -> dict:
    """Character ledger: traits, weights and drift (individuation signal)."""
    return runtime().character_state()


@mcp.tool()
def jcr_dream(min_evidence: int = 2) -> dict:
    """Run the dream cycle: reinforce/decay traits from outcomes, induce proposals."""
    return runtime().dream_consolidate(min_evidence)


@mcp.tool()
def jcr_telemetry() -> dict:
    """Harness telemetry: turn/label counts, useful rate, open trait proposals."""
    return runtime().telemetry()


@mcp.tool()
def jcr_proposals() -> list:
    """Candidate traits induced by the dream cycle, awaiting owner ratification."""
    return runtime().trait_proposals()


@mcp.tool()
def jcr_ratify(proposal_id: str, weight: float = 0.5) -> dict:
    """Ratify a proposed trait, installing it as a real disposition."""
    return runtime().ratify(proposal_id, weight) or {"error": "not found or already ratified"}


@mcp.tool()
def jcr_selfplay(rounds: int = 3) -> dict:
    """Adversarial hardening: generate breaking inputs and learn minimal guard patterns."""
    return runtime().selfplay_run(rounds)


@mcp.tool()
def jcr_invariants() -> list:
    """Learned guard patterns (self-play), with ratification status."""
    return runtime().invariants_list()


@mcp.tool()
def jcr_shadow_review(draft: str) -> dict:
    """Artifact Shadow: critique a draft; only confirmed (costly) signals can veto."""
    return runtime().shadow_review(draft)


@mcp.tool()
def jcr_arbitrate(positions: list, candidates: list, candidate_axes: dict | None = None) -> dict:
    """Nash bargaining over candidates; enantiodromia forcing enters as a position."""
    return runtime().arbitrate(positions, candidates, candidate_axes)


@mcp.tool()
def jcr_observe_axes(x: dict, dt: float = 1.0) -> dict:
    """Feed signed value-axis deviations to the enantiodromia homeostat."""
    return runtime().observe_axes(x, dt)


@mcp.tool()
def jcr_credit(samples: int = 1000) -> dict:
    """Shapley credit over traits from labelled outcomes; pays libido proportionally."""
    return runtime().credit(samples=samples)


@mcp.tool()
def jcr_import_memory(path: str = "", limit: int = 0, force: bool = False) -> dict:
    """Import sint-memory blocks into the ledger (verifies the source hash-chain)."""
    return runtime().import_memory(path or None, limit=limit or None, force=force)


@mcp.tool()
def jcr_poll_events(since: int = 0, kinds: list[str] | None = None, limit: int = 200) -> dict:
    """Drain bus events newer than `since`."""
    return {"events": runtime().events(since=since, kinds=kinds, limit=limit)}


@mcp.tool()
def jcr_outcome(node_ids: list[str], useful: bool = True) -> dict:
    """Label activated nodes as useful/useless — feeds synchronicity calibration."""
    return runtime().outcome(node_ids, useful)


if __name__ == "__main__":
    mcp.run()
