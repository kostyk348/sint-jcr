/**
 * jcr-harness — the in-loop executive hand for opencode.
 *
 * This plugin is what turns JCR from "more MCP servers" into a *harness*.
 * MCP tools are chosen by the model; these hooks run around the model and can
 * enforce. See docs/11-harness.md.
 *
 * Now wired (H3 + H4):
 *   chat.params                          -> psychoid coupling (affect -> sampling)
 *   permission.ask                       -> the veto
 *   experimental.chat.messages.transform -> context compiler (budgeted assembly)
 *   experimental.chat.system.transform   -> character + state injection
 *
 * Design rule: the harness must NEVER break the loop. Every call to jcr-core is
 * timeboxed and failure-tolerant; if the daemon is down, the host behaves as a
 * normal agent.
 */

import type { Plugin } from "@opencode-ai/plugin"

import { applyParams, applyVeto, injectIntoMessages, renderContext } from "./directives.ts"
import type { MessageLike } from "./directives.ts"

const JCR_URL = process.env.JCR_URL ?? "http://127.0.0.1:8765"
const JCR_TIMEOUT_MS = Number(process.env.JCR_TIMEOUT_MS ?? 400)

async function jcr(path: string, body: unknown, method: "GET" | "POST" = "POST"): Promise<any | null> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), JCR_TIMEOUT_MS)
  try {
    const res = await fetch(`${JCR_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: method === "POST" ? JSON.stringify(body ?? {}) : undefined,
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

const jcrGet = (path: string) => jcr(path, null, "GET")

function partsToText(parts: Array<Record<string, unknown>>): string {
  return parts
    .map((p) => (typeof p.text === "string" ? p.text : ""))
    .filter(Boolean)
    .join("\n")
}

function lastUserText(messages: MessageLike[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m?.info?.role === "user") return partsToText((m.parts ?? []) as Array<Record<string, unknown>>)
  }
  return ""
}

export default (async ({ project }) => {
  const session = () => process.env.OPENCODE_SESSION ?? project?.id ?? "default"

  return {
    // turn_open: observe the incoming user message
    "chat.message": async (_input, output) => {
      const text = partsToText(output.parts as Array<Record<string, unknown>>)
      await jcr("/observe", { text, session: session(), turn: 0 })
    },

    // H3 — psychoid coupling: affect -> sampling parameters
    "chat.params": async (_input, output) => {
      const p = await jcrGet("/params")
      applyParams(output, p?.params ?? null)
    },

    // H4 — context compiler: budgeted assembly injected into the message array
    "experimental.chat.messages.transform": async (_input, output) => {
      const messages = output.messages as MessageLike[]
      const text = lastUserText(messages)
      if (!text) return
      const compiled = await jcr("/compile", { text, budget: 1200, k: 8 })
      const block = renderContext(compiled)
      if (block) injectIntoMessages(messages, block)
    },

    // dynamic system-prompt assembly: character traits + runtime state
    "experimental.chat.system.transform": async (_input, output) => {
      const [state, character] = await Promise.all([jcrGet("/state"), jcrGet("/character")])
      if (state?.ledger) {
        const mean = Number(state.ledger.mean_energy ?? 0).toFixed(3)
        output.system.push(
          `## JCR runtime state (auto)\nbus=${state.bus?.format} events=${state.bus?.events} chain_ok=${state.bus?.chain?.ok} nodes=${state.ledger.nodes} mean_energy=${mean}`,
        )
      }
      const traits = character?.traits ?? []
      if (traits.length) {
        output.system.push(
          ["## Character (operative dispositions)", ...traits.map((t: any) => `- ${t.statement}`)].join("\n"),
        )
      }
    },

    // H3 — the veto: deny or gate a tool call
    "permission.ask": async (input, output) => {
      const anyIn = input as any
      const tool = anyIn?.tool ?? anyIn?.type ?? anyIn?.permission ?? "unknown"
      const decision = await jcr("/veto", { tool, args: anyIn })
      applyVeto(output, decision)
    },

    // capability narrowing — reserved for Phase 3
    "tool.execute.before": async (_input, _output) => {},

    // turn telemetry: feed tool output back into the field
    "tool.execute.after": async (input, output) => {
      const text = `${input.tool}: ${String(output.output ?? "")}`.slice(0, 2000)
      await jcr("/observe", { text, session: session(), turn: 0 })
    },

    event: async () => {
      // Phase 5: publish harness-level telemetry.
    },
  }
}) satisfies Plugin
