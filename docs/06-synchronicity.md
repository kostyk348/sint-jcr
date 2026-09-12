# 06 — Synchronicity Monitor

> RAG is blind until you ask. The monitor is what makes a memory arrive *unasked* —
> which is also exactly why it can become a machine for producing noise.

---

## 1. What synchronicity must mean, computationally

Jung's synchronicity is *not* "things that are similar." It has three criteria. We take all three
seriously, because **they are also the best available filter against false positives.**

| Jung's criterion | Computational reading |
|---|---|
| 1. **Acausal connection** | The match is *far in the causal/semantic graph* — not a neighbor, not a retrieval hit. |
| 2. **Meaningful coincidence** | High structural/functional resonance, not lexical overlap. |
| 3. **Constellated by an archetype** | The match aligns with a pattern in the collective-unconscious library. |

A candidate that satisfies only (2) is just a good retrieval — that is RAG, and it already exists.
A candidate that satisfies all three is a *crossing*: a normally-unreachable association that is
nonetheless meaningful. **The filter is the point.**

---

## 2. The continuous loop

```
        ┌────────────────────────────────────────────┐
        │              jcr-core (background)          │
        │                                             │
  buf ──► embed ──► resonance vs hot+cold sample ──► 3-condition filter
        │                                             │      │
        │                                             │      ├─ fail → drop (log)
        │                                             │      └─ pass → "crossing" event
        └────────────────────────────────────────────┘             │
                                                                    ▼
                                                          priority ↑ in ledger
                                                                    │
                                            (soft default) ─────────┤
                                                                    │
                                            (hard, opt-in) → jcr_inject → context
```

Runs while the host is idle. This is precisely what an MCP server cannot do.

---

## 3. Resonance, weighted by distance

Plain cosine similarity finds *neighbors* — the opposite of criterion (1). So define:

```
resonance(buf, n) = cos(emb(buf), emb(n)) · φ( dist_graph(buf_anchor, n) )
```

where `dist_graph` is graph/temporal distance and `φ` is **increasing** in distance (within a
band). A node far away in the past and in a different project that nonetheless matches
structurally is a candidate; a node next door is not.

Structural matching (already prototyped in `sint-resonance`'s `resonance_structural`) compares
*shape*, not words: tree/graph isomorphisms of the problem, not token overlap.

---

## 4. The three-condition filter in detail

### Condition 1 — acausality / distance
```
dist_graph(buf, n) > D_min        (not a neighbor)
no causal edge path from buf to n  (no "you were just working on this")
```

### Condition 2 — meaningful coincidence
```
resonance_struct(buf, n) > S_min
and  | domain(buf) − domain(n) | is large   (cross-domain is the point)
```

### Condition 3 — archetypal constellator
The collective-unconscious library (global priors: algorithms, control patterns, structural
tropes) must contain a pattern `P` such that both the buffer and the node instantiate `P`:
```
∃ P : match(buf, P) ∧ match(n, P)
```
This is the strictest filter and the main defense against aporhenia. It says: *a crossing is not
"this reminds me of that"; it is "these two are the same pattern in different clothes".*

---

## 5. Soft by default, hard on request

A system that seizes the conversation to share an insight becomes intolerable. Default behavior:

- **Soft:** the crossing raises the node's priority in the ledger and attaches a *passive marker*.
  When the Ego next queries the field naturally, the node is more likely to appear. The user
  experiences "the agent remembered the relevant thing", not "the agent interrupted me".
- **Hard (opt-in):** for high-confidence, high-archetypal crossings, emit an `inject` event that
  the host may surface. Off by default; requires an explicit threshold and, in interactive use, a
  human/agent gate (`jcr_inject`).

This is the difference between a useful colleague and a haunting.

---

## 6. Calibration protocol (the anti-aporhenia requirement)

The monitor **must** be calibrated or disabled. Protocol:

1. Every surfaced crossing is logged with its three condition scores.
2. The host (or human) labels it `useful` / `useless` via `jcr_outcome`.
3. Maintain precision/recall against the labels; track a rolling precision at the current
   threshold.
4. Auto-tune `D_min, S_min` to hold precision above a configured floor (e.g. 0.6) — high recall is
   useless if precision is 0.05.
5. If precision cannot be held above the floor on a horizon, **automatically reduce to
   soft-mode-only** and stop surfacing.

> **The honest failure mode:** if human labels show precision ≈ chance, the monitor is generating
> coincidences with no meaning. The correct response is to turn it off and publish the null result,
> not to lower the threshold until something "feels" insightful.

---

## 7. Cost

- Embedding the buffer: one local embedding call per change/heartbeat — the main recurring cost.
- Index search: ANN over hot + a *sampled* cold set, not the whole cold store.
- Archetype matching: precomputed pattern fingerprints, cheap set/graph operations.
- No LLM call in the loop. The expensive step (evaluating insights) happens only when a crossing
  is surfaced and, optionally, reviewed by the Shadow.

---

## 8. Falsification summary

| Claim | Test |
|---|---|
| Not just RAG | crossings are graph-distant and cross-domain; retrieval hits are not surfaced |
| Filter helps | precision with the 3-condition filter > precision with similarity alone |
| Soft mode is enough | measured usefulness of soft markers ≈ hard injections, with fewer interruptions |
| Calibratable | precision stable across sessions; auto-tuning holds the floor |
