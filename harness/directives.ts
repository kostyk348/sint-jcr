/**
 * Pure directive functions for jcr-harness.
 *
 * Kept free of I/O and of the opencode SDK so they can be unit-tested with
 * `node --test`. index.ts wires these to the hooks and to jcr-core.
 */

export type Params = {
  temperature?: number
  top_p?: number
  max_output_tokens?: number
}

export type ChatParamsOutput = {
  temperature: number
  topP: number
  topK: number
  maxOutputTokens: number | undefined
  options: Record<string, any>
}

/** Apply psychoid-derived parameters. Only touches fields that were provided. */
export function applyParams(output: ChatParamsOutput, p: Params | null | undefined): ChatParamsOutput {
  if (!p) return output
  if (typeof p.temperature === "number") output.temperature = p.temperature
  if (typeof p.top_p === "number") output.topP = p.top_p
  if (typeof p.max_output_tokens === "number") output.maxOutputTokens = p.max_output_tokens
  return output
}

export type VetoDecision = {
  status?: "allow" | "ask" | "deny"
  reason?: string
  rule?: string
}

/** Apply a veto decision from jcr-core. */
export function applyVeto(output: { status: "ask" | "deny" | "allow" }, d: VetoDecision | null | undefined): typeof output {
  if (d && (d.status === "allow" || d.status === "ask" || d.status === "deny")) {
    output.status = d.status
  }
  return output
}

export type CompiledNode = {
  node_id: string
  register?: string
  project?: string
  preview: string
}

export type CompiledTrait = {
  statement: string
  weight?: number
  polarity?: number
}

export type Compiled = {
  system_addendum?: string
  nodes?: CompiledNode[]
  traits?: CompiledTrait[]
  tokens_estimate?: number
}

/** Render a compiled context into a single block of text for injection. */
export function renderContext(c: Compiled | null | undefined): string {
  if (!c) return ""
  if (c.system_addendum && c.system_addendum.trim()) return c.system_addendum
  const lines: string[] = []
  for (const t of c.traits ?? []) lines.push(`- ${t.statement}`)
  for (const n of c.nodes ?? []) lines.push(`- [${n.register ?? "?"}] ${n.preview}`)
  return lines.join("\n")
}

export type MessageLike = {
  info?: { role?: string }
  parts?: Array<Record<string, any>>
}

/**
 * Inject a context block into the message array by appending a text part to the
 * last user message. Returns true if a target was found.
 */
export function injectIntoMessages(messages: MessageLike[], text: string): boolean {
  if (!text || !messages?.length) return false
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    const role = m?.info?.role
    if (role && role !== "user") continue
    m.parts = m.parts ?? []
    m.parts.push({ type: "text", text })
    return true
  }
  return false
}
