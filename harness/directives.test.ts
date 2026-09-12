/**
 * Unit tests for the harness's pure directive logic.
 *   node --test harness/
 */

import { test } from "node:test"
import assert from "node:assert/strict"

import { applyParams, applyVeto, quantizeParams, renderCharacterBlock, renderContext, injectIntoMessages } from "./directives.ts"

test("applyParams sets only provided fields", () => {
  const out = { temperature: 0.7, topP: 0.9, topK: 40, maxOutputTokens: undefined, options: {} }
  applyParams(out, { temperature: 0.2, max_output_tokens: 1024 })
  assert.equal(out.temperature, 0.2)
  assert.equal(out.topP, 0.9) // untouched
  assert.equal(out.maxOutputTokens, 1024)
})

test("applyParams is a no-op on null", () => {
  const out = { temperature: 0.7, topP: 0.9, topK: 40, maxOutputTokens: undefined, options: {} }
  applyParams(out, null)
  assert.equal(out.temperature, 0.7)
})

test("applyVeto sets the status", () => {
  const out = { status: "ask" as "ask" | "deny" | "allow" }
  applyVeto(out, { status: "deny", reason: "destructive" })
  assert.equal(out.status, "deny")
})

test("applyVeto ignores malformed decisions", () => {
  const out = { status: "allow" as "ask" | "deny" | "allow" }
  applyVeto(out, { reason: "no status" })
  assert.equal(out.status, "allow")
})

test("renderContext prefers the server addendum", () => {
  const s = renderContext({ system_addendum: "## Character\n- Be terse", nodes: [] })
  assert.match(s, /Be terse/)
})

test("renderContext falls back to traits+nodes", () => {
  const s = renderContext({ traits: [{ statement: "Prefer mechanism" }], nodes: [{ node_id: "n1", preview: "x" }] })
  assert.match(s, /Prefer mechanism/)
  assert.match(s, /n1|\[.*\] x/)
})

test("injectIntoMessages appends to the last user message", () => {
  const msgs = [
    { info: { role: "user" }, parts: [{ type: "text", text: "hi" }] },
    { info: { role: "assistant" }, parts: [{ type: "text", text: "hello" }] },
    { info: { role: "user" }, parts: [{ type: "text", text: "task" }] },
  ]
  const ok = injectIntoMessages(msgs, "CONTEXT")
  assert.equal(ok, true)
  assert.equal(msgs[2].parts.length, 2)
  assert.equal(msgs[0].parts.length, 1) // earlier user message untouched
})

test("injectIntoMessages returns false on empty input", () => {
  assert.equal(injectIntoMessages([], "x"), false)
  assert.equal(injectIntoMessages([{ parts: [] }], ""), false)
})

// --- cache-stability guarantees -------------------------------------------

test("renderCharacterBlock is byte-stable for the same trait set", () => {
  const traits = [{ statement: "be terse", polarity: 1 }, { statement: "avoid sycophancy", polarity: -1 }]
  const a = renderCharacterBlock(traits)
  const b = renderCharacterBlock([...traits].reverse())
  assert.equal(a, b) // order-independent => stable across turns
})

test("renderCharacterBlock contains no volatile markers", () => {
  const block = renderCharacterBlock([{ statement: "be terse" }])
  for (const bad of ["uptime", "events=", "nodes=", "chain_ok", "mean_energy", "T00:", "Z"]) {
    assert.ok(!block.includes(bad), `system block must not contain volatile token: ${bad}`)
  }
})

test("renderCharacterBlock is empty when there are no traits", () => {
  assert.equal(renderCharacterBlock([]), "")
})

test("quantizeParams coarsens values so they change rarely", () => {
  const q = quantizeParams({ temperature: 0.6874, top_p: 0.9453, max_output_tokens: 3865 })
  assert.equal(q?.temperature, 0.7)
  assert.equal(q?.top_p, 0.95)
  assert.equal(q?.max_output_tokens, 3840)
})

test("quantizeParams keeps two near-identical affects identical", () => {
  const a = quantizeParams({ temperature: 0.71 })
  const b = quantizeParams({ temperature: 0.73 })
  assert.deepEqual(a, b) // both round to 0.7 => no cache churn
})
