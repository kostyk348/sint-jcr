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
def jcr_poll_events(since: int = 0, kinds: list[str] | None = None, limit: int = 200) -> dict:
    """Drain bus events newer than `since`."""
    return {"events": runtime().events(since=since, kinds=kinds, limit=limit)}


@mcp.tool()
def jcr_outcome(node_ids: list[str], useful: bool = True) -> dict:
    """Label activated nodes as useful/useless — feeds synchronicity calibration."""
    return runtime().outcome(node_ids, useful)


if __name__ == "__main__":
    mcp.run()
