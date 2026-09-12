# 14 — Cache Discipline

> A harness that mutates the prompt prefix is a harness that pays full price on
> every token. This document is a hard rule, a measurement, and a test.

---

## 1. Why it matters

Providers cache the **prefix** of the prompt (system + earlier messages). A cache
hit costs a fraction of a miss. The failure is absolute: **if any early byte
changes, everything after it misses.** There is no partial credit for a changed
system prompt — it is position 0.

A harness that injects `uptime`, `events=N`, `mean_energy`, or a timestamp into
the system prompt every turn guarantees a **0% hit rate**. This is easy to do by
accident and expensive to keep doing.

Target: **≥ 98% of prompt tokens read from cache.**

---

## 2. The rule

```
[ IMMUTABLE PREFIX ................ ][ TAIL ]
  system prompt (static)              newest user message
  conversation history                + injected dynamic block
```

1. **The system prompt must be byte-identical across turns.**
   The only thing the harness may add to it is the **deterministic character
   block** — and only when the trait set changes (rare: teach / dream / ratify).
2. **All volatile content goes to the tail.** Runtime state, resonant memory,
   crossings, focus — appended to the newest user message, never to system.
3. **No counters, timestamps, uptime, or event counts anywhere in the prompt.**
   They change every call by definition. If the agent needs them, it asks via a
   tool.
4. **Sampling params are quantized.** `temperature` to 0.1, `top_p` to 0.05,
   `max_output_tokens` to 256. Near-identical affects then produce identical
   params, so they do not churn.
5. **Never rewrite earlier messages.** `messages.transform` may append to the last
   user message; it must not edit history.

---

## 3. What we fixed

| Where | Before (cache-hostile) | After |
|---|---|---|
| `jcr-harness` `system.transform` | pushed `bus/events/chain_ok/nodes/mean_energy` every turn | pushes only the deterministic character block |
| `jcr-harness` `messages.transform` | (already tail) | tail injection only, budgeted |
| `jcr-harness` `chat.params` | raw float params every turn | quantized params |
| `sint-hooks` `system.transform` | appended `focus/pending/last_session/session_count` to system | moved to the **tail** (messages.transform) |

The `sint-hooks` change matters beyond JCR: it affected every session.

---

## 4. Measurement (not a claim)

opencode exposes real token accounting on assistant messages:
`tokens.cache.read` / `tokens.cache.write`. The harness plugin forwards these to
`jcr-core`, which computes:

```
hit_rate = cache_read / (input + cache_read + cache_write)
```

Endpoints:

```bash
curl -s localhost:8765/cache | python3 -m json.tool
# { "turns": N, "hit_rate": 0.98, "last_hit_rate": ..., "worst_hit_rate": ...,
#   "prompt_tokens": ..., "cache_read_tokens": ..., "uncached_input_tokens": ... }
```

`worst_hit_rate` is the important number: a single prefix mutation shows up there.

---

## 5. Tests (merge gates)

| Claim | Test |
|---|---|
| Character block is byte-stable | `renderCharacterBlock` identical for the same set, order-independent |
| No volatile tokens in system | `renderCharacterBlock` contains no `uptime/events=/nodes=/chain_ok/T…Z` |
| Params do not churn | two near-identical affects quantize to the same params |
| Dynamic content is tail-only | `injectIntoMessages` targets the last user message |
| Hit-rate math | `test_cache.py` (0.98 / 0.50 / write-only cases) |

If a change would make the system prompt vary per turn, these tests fail.

---

## 6. Residual cost (honest)

- The injected tail block is uncached each turn — keep it small (budgeted).
- Injected blocks remain in history on later turns (then cached, but they occupy
  context). Compaction is the host's job; keep injections lean.
- A trait change costs exactly one cache miss. That is the intended price of
  updating identity.
- If a provider keys cache on sampling params, quantization bounds the churn;
  it does not eliminate it. Measure with `/cache`.
