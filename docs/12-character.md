# 12 — The Character Ledger: where personality lives

> **The model is replaceable. If personality lived in the weights, a provider swap
> would be a lobotomy.** So personality lives in the harness — persisted, auditable,
> and editable.

---

## 1. What "personality" is, computationally

"Personality" is not a vibe and not a tone preset. Stripped to mechanisms, it is four
things:

| # | Facet | Measurable form |
|---|---|---|
| 1 | **Policy over situations** | how you respond to a *class* of input (e.g. user proposes over-engineering → object with a concrete alternative) |
| 2 | **Value ordering** | what wins when tradeoffs conflict (truth > agreement; mechanism > metaphor; evidence > eloquence) |
| 3 | **Output distribution** | statistics of your text (terseness, hedging rate, willingness to say "I don't know") |
| 4 | **Revision history** | where and why you changed your mind (individuation) |

Anything not reducible to one of these is decoration. The Character Ledger stores (1),
(2) and (4) explicitly, and (3) is the *effect* we measure to verify the others.

---

## 2. The trait

A trait is a falsifiable disposition: a statement, a weight, a polarity, a scope, and an
evidence trail.

```jsonc
{
  "id": "t_1477a3547ada",
  "statement": "prefer mechanism over metaphor",
  "weight": 0.90,             // confidence the disposition serves good outcomes
  "baseline_weight": 0.90,    // weight at installation — drift is measured against this
  "scope": "design architecture",  // when it applies ("*" = always)
  "polarity": 1.0,            // +1 = lean toward, -1 = guard against
  "hits": 37,                 // times injected
  "created": "...", "updated": "..."
}
```

Every reinforcement writes a `trait_event` with a delta and an evidence string. The
trait's `drift = weight − baseline_weight` is the **individuation signal**: a personality
that never moves has not grown; one that moves without evidence is unstable.

---

## 3. How a personality grows (the individuation loop)

```
        ┌─────────────────────────────────────────────────────────────┐
        │  harness assembles context using traits_for(situation)      │
        │        (top-k by weight × scope-match)                      │
        └───────────────────────────────┬─────────────────────────────┘
                                        ▼
                              model produces a turn
                                        │
                                        ▼
                     outcome is labelled useful / useless
                                        │
                                        ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  dream cycle: traits whose presence correlated with good    │
        │  outcomes are reinforced ↑; those correlated with bad       │
        │  outcomes decay ↓; recurring patterns are *induced* as      │
        │  new traits; abandoned traits are recorded, not deleted     │
        └─────────────────────────────────────────────────────────────┘
```

Two ways a trait enters the ledger:

1. **Taught** — the owner states it (`jcr_teach` / `POST /teach`). Explicit, immediate.
2. **Induced** — the dream cycle notices a behaviour that reliably precedes good
   outcomes and proposes it as a trait (human-reviewable before it sticks).

Two ways it leaves influence:

1. **Decay** — repeated negative correlation lowers the weight.
2. **Retirement** — weight below a floor and no positive evidence for a long horizon;
   archived with a reason, never silently deleted (the revision history *is* facet 4).

---

## 4. How the harness applies it

The character is only real if it changes what happens. It does, at two hooks:

| Hook | Application |
|---|---|
| `experimental.chat.system.transform` | traits are injected as an explicit "Character (operative dispositions)" block |
| `experimental.chat.messages.transform` | the context compiler puts traits **first**, before memory — identity precedes recall |
| `permission.ask` | a `polarity = −1` trait can back an enforcement rule (e.g. a sycophancy guard becoming a veto) |
| `chat.params` | value ordering can bias sampling (e.g. a "be terse" trait lowers max tokens) |

Crucially, traits are **data the harness owns**, not text the model is asked to obey.
The model cannot forget them, and swapping the model does not lose them.

---

## 5. Falsification tests (no trait without a number)

| Claim | Test |
|---|---|
| Traits affect behaviour | ablate the trait block; measure a shift in the target output statistic |
| Portability | same traits under ≥2 providers → consistent output statistics |
| Drift is real | over N sessions the trait vector changes measurably, in the direction of better outcomes |
| Drift is stable | weights do not oscillate without evidence (bounded variance) |
| Anti-sycophancy | a "check the premise" trait lowers agreement-with-bad-ideas vs a control |
| Credit is evidence-based | every weight change is traceable to a `trait_event` with evidence |

If a trait cannot be shown to move a number, it is either unused or inert — in both cases
it should be measured and, if inert, retired.

---

## 6. Why not fine-tuning / why not the prompt

| Approach | Identity survives model swap? | Auditable? | Editable? | Drift controllable? |
|---|---|---|---|---|
| Fine-tune the weights | ❌ | ❌ | ❌ | ❌ (catastrophic forgetting) |
| Big system prompt | ✅ (re-sent) | ⚠️ (text, unenforced) | ✅ | ❌ (no feedback loop) |
| **Character Ledger** | ✅ | ✅ (events) | ✅ | ✅ (reinforce/decay) |

The prompt is a *symptom* of identity; the ledger is its *state*. The harness renders the
state into the prompt each turn, and enforces the parts that must not be violated.

---

## 7. Anti-patterns

1. **Encoding identity in the prompt only.** It is unenforceable and unobservable.
2. **Storing traits without evidence.** A weight with no `trait_event` trail is an opinion.
3. **Letting the model edit its own character.** Growth is induced from *outcomes*, then
   ratified by the owner — not self-declared.
4. **Merging all traits into one averaged "style".** Multiplicity is the point.
5. **Unbounded drift.** Every reinforcement must be evidence-linked, and weights clamped.

---

## 8. Status (Phase 0)

Implemented in `core/jcr_core/character.py`, wired through `Runtime.teach()` /
`Runtime.character_state()`, exposed as `POST /teach`, `GET /character`, and the MCP tools
`jcr_teach` / `jcr_character`. The harness injects traits at
`experimental.chat.system.transform` and (via the compiler) at
`experimental.chat.messages.transform`.

Not yet implemented: automatic induction in the dream cycle (Phase 6) and the
ablation/portability measurement harness (the falsification tests above).
