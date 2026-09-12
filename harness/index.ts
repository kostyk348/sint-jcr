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

import { applyParams, applyVeto, injectIntoMessages, quantizeParams, renderCharacterBlock, renderContext } from "./directives.ts"
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

    // H3 — psychoid coupling: affect -> sampling parameters (quantized, cache-safe)
    "chat.params": async (_input, output) => {
      const p = await jcrGet("/params")
      applyParams(output, quantizeParams(p?.params ?? null))
    },

    // H4 — context compiler. CACHE RULE: dynamic content goes to the TAIL only
    // (the newest user message). The cached prefix — system + history — is never
    // rewritten here, so only the small injected block is uncached.
    "experimental.chat.messages.transform": async (_input, output) => {
      const messages = output.messages as MessageLike[]
      const text = lastUserText(messages)
      if (!text) return
      const compiled = await jcr("/compile", { text, budget: 1200, k: 8 })
      const block = renderContext(compiled)
      if (block) injectIntoMessages(messages, block)
    },

    // CACHE RULE: the system prompt must be byte-stable. We therefore DO NOT
    // touch it unless explicitly opted in. Even the deterministic character
    // block is off by default — a single mutation at position 0 invalidates the
    // entire prefix cache. Set JCR_INJECT_CHARACTER=1 to enable it.
    "experimental.chat.system.transform": async (_input, output) => {
      if (process.env.JCR_INJECT_CHARACTER !== "1") return
      const character = await jcrGet("/character")
      const block = renderCharacterBlock(character?.traits ?? [])
      if (block) output.system.push(block)
    },

    // H3 — the veto: deny or gate a tool call. The artifact Shadow can also veto
    // (only if its critique carries a confirmed, costly signal).
    "permission.ask": async (input, output) => {
      const anyIn = input as any
      const tool = anyIn?.tool ?? anyIn?.type ?? anyIn?.permission ?? "unknown"
      const draft = typeof anyIn?.args === "string" ? anyIn.args : JSON.stringify(anyIn?.args ?? anyIn ?? {})
      const [decision, shadow] = await Promise.all([
        jcr("/veto", { tool, args: anyIn }),
        jcr("/shadow", { draft }),
      ])
      if (shadow?.veto) {
        output.status = "deny"
        return
      }
      applyVeto(output, decision)
    },

    // capability narrowing — reserved for Phase 3
    "tool.execute.before": async (_input, _output) => {},

    // turn telemetry: feed tool output back into the field
    "tool.execute.after": async (input, output) => {
      const text = `${input.tool}: ${String(output.output ?? "")}`.slice(0, 2000)
      await jcr("/observe", { text, session: session(), turn: 0 })
    },

    // Cache telemetry: report REAL prompt-cache usage from the host
    // (opencode exposes tokens.cache.read/write). This turns "is the harness
    // cache-friendly?" into a measured number instead of a claim.
    event: async ({ event }) => {
      const e = event as any
      if (e?.type !== "message.updated") return
      const info = e?.properties?.info
      if (!info || info.role !== "assistant" || !info.tokens) return
      const t = info.tokens
      await jcr("/cache", {
        input: t.input ?? 0,
        output: t.output ?? 0,
        cache_read: t.cache?.read ?? 0,
        cache_write: t.cache?.write ?? 0,
      })
    },
  }
}) satisfies Plugin
