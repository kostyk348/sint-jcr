/**
 * jcr-harness — the in-loop executive hand for opencode.
 *
 * This plugin is what turns JCR from "more MCP servers" into a *harness*.
 * MCP tools are chosen by the model; these hooks run around the model and can
 * enforce. See docs/11-harness.md.
 *
 * Phase 0 wires observation + state injection. Later phases fill the gaps:
 *   chat.params        -> psychoid coupling (Phase 1)
 *   permission.ask     -> the veto        (Phase 3)
 *   tool.execute.before-> capability narrowing (Phase 3)
 *   messages.transform -> context compiler (Phase 4)
 *
 * Design rule: the harness must NEVER break the loop. Every call to jcr-core is
 * timeboxed and failure-tolerant; if the daemon is down, the host behaves as a
 * normal agent.
 */

import type { Plugin } from "@opencode-ai/plugin"

const JCR_URL = process.env.JCR_URL ?? "http://127.0.0.1:8765"
const JCR_TIMEOUT_MS = Number(process.env.JCR_TIMEOUT_MS ?? 400)

async function jcr(path: string, body: unknown): Promise<any | null> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), JCR_TIMEOUT_MS)
  try {
    const res = await fetch(`${JCR_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null // degrade silently: the daemon is optional
  } finally {
    clearTimeout(timer)
  }
}

function partsToText(parts: Array<Record<string, unknown>>): string {
  return parts
    .map((p) => (typeof p.text === "string" ? p.text : ""))
    .filter(Boolean)
    .join("\n")
}

export default (async ({ project }) => {
  const session = () => process.env.OPENCODE_SESSION ?? project?.id ?? "default"

  return {
    // turn_open: observe the incoming user message
    "chat.message": async (_input, output) => {
      const text = partsToText(output.parts as Array<Record<string, unknown>>)
      await jcr("/observe", { text, session: session(), turn: 0 })
    },

    // dynamic system-prompt assembly from live state
    "experimental.chat.system.transform": async (_input, output) => {
      const state = await jcr("/state", {})
      if (!state?.ledger) return
      const mean = Number(state.ledger.mean_energy ?? 0).toFixed(3)
      output.system.push(
        [
          "## JCR runtime state (auto-injected)",
          `nodes=${state.ledger.nodes} edges=${state.ledger.edges} events=${state.events} mean_energy=${mean}`,
          "This is a stateless projection of the local memory field. Use jcr_* tools to query it.",
        ].join("\n"),
      )
    },

    // psychoid coupling — reserved for Phase 1
    "chat.params": async (_input, _output) => {
      // Phase 1: effect vector -> temperature / topP / maxOutputTokens.
    },

    // capability narrowing — reserved for Phase 3
    "tool.execute.before": async (_input, _output) => {
      // Phase 3: constrain args, or narrow the available capability set.
    },

    // turn telemetry: feed tool output back into the field
    "tool.execute.after": async (input, output) => {
      const text = `${input.tool}: ${String(output.output ?? "")}`.slice(0, 2000)
      await jcr("/observe", { text, session: session(), turn: 0 })
    },

    // the veto — reserved for Phase 3
    "permission.ask": async (_input, _output) => {
      // Phase 3: set output.status = "deny" to block a captured/injected action.
    },

    // full observability
    event: async () => {
      // Phase 5: publish harness-level telemetry.
    },
  }
}) satisfies Plugin
