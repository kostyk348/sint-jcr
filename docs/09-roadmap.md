# 09 — Roadmap

> **You cannot individuate before you have an ego.**
> The ordering below is dictated by dependencies, not by which layer is most exciting.

---

## Phase 0 — Body and Field (foundation)

**Goal:** a running `jcr-core` with a bus and a memory field. No psychology yet.

| Deliverable | Notes |
|---|---|
| Event bus + append-only event log | in-process asyncio queue + SQLite, transport-agnostic interface |
| Libido Ledger v0 | nodes, edges, energy, decay, hot/cold tiers, activation |
| `jcr-mcp` facade skeleton | `jcr_state`, `jcr_poll_events`, `jcr_observe` |
| Import bridge | ingest existing `sint-memory` blocks + chain into the ledger |

**Exit criteria**
- Ledger survives restart via event replay.
- `ρ(ΔE, later reuse) > 0` on a held-out set of sessions.
- Token economy: task quality matched at fewer context tokens than a monolith. **If not, stop and
  reconsider the whole premise.**

---

## Phase 1 — Psychoid (cheap, high signal)

**Goal:** the runtime *feels* the machine.

| Deliverable | Notes |
|---|---|
| Psychoid sampler | CPU/RAM/IO/error/latency → affect vector |
| Coupling | affect → generation params, Shadow threshold, `S_thresh`, `K` |
| Degradation | adaptive cadence, off when idle |

**Exit criteria**
- A controlled CPU/error spike changes generation params and thresholds **before** the next user
  message, with no LLM call. Hard, binary test.
- Zero measurable latency added to a turn.

---

## Phase 2 — Shadow (first LLM cost)

**Goal:** a credible critic, built on costly signals from day one.

| Deliverable | Notes |
|---|---|
| Shadow daemon | audits Ego drafts |
| **Cost ledger** | every veto must carry a falsifiable artifact; track confirmation rate |
| Shapley v0 | contribution from *confirmed* catches |
| Veto path | one veto → one revision loop, then surface dissent |

**Exit criteria**
- Anti-sycophancy: on a labeled set of bad user ideas, veto rate > baseline planner.
- Confirmed-veto rate within a healthy band (not ≈0, not ≈1). Tune until it is.
- Veto reaches the arbiter out-of-band (prompt injection cannot reach it).

---

## Phase 3 — Arbiter + Enantiodromia

**Goal:** principled arbitration and drift control.

| Deliverable | Notes |
|---|---|
| Nash-bargaining arbiter | discrete candidate set, utilities, disagreement points, dissent log |
| Enantiodromia governor | integral deviation, bang-bang forcing, anti-windup |
| Compensation | neglected-axis inclusion |

**Exit criteria**
- Outcome responds to disagreement points `d` (perturbation test).
- `|I(t)|` bounded with governor on; saturates with it off.
- Dissent log non-uniform (if uniform, bargaining is fake).

---

## Phase 4 — Synchronicity Monitor

**Goal:** unasked, meaningful arrivals — without noise.

| Deliverable | Notes |
|---|---|
| Continuous background loop | local embeddings, hot + sampled cold |
| Graph-distance resonance | `φ(dist_graph)` increasing |
| 3-condition filter | acausal + meaningful + archetypal |
| Calibration | `jcr_outcome` labels, rolling precision, auto-threshold |

**Exit criteria**
- Precision with the 3-condition filter > precision with similarity alone, on labeled data.
- Precision held above the configured floor; otherwise **auto-downgrade to soft-only**.
- Soft markers deliver usefulness comparable to hard injections with fewer interruptions.

---

## Phase 5 — Transcendent Function

**Goal:** reframe structural deadlocks instead of voting.

| Deliverable | Notes |
|---|---|
| Deadlock detector | no individually rational candidate / oscillation |
| Reframing operators | lift, analogy, invert, decompose, resequence, rescale |
| Pareto check | synthesis must dominate the deadlock baseline |
| Honest escalation | report unresolved conflicts |

**Exit criteria**
- More Pareto-improving outcomes than majority vote and than averaging, on a deadlock set.
- Escalation rate > 0 on genuine deadlocks (it is allowed to fail).

---

## Phase 6 — Dream & Self-Play

**Goal:** learn without labels; evolve character.

| Deliverable | Notes |
|---|---|
| Dream cycle | consolidate, decay, detect complexes, update invariants |
| Self-play | Shadow generates break-inputs; Ego learns to parry |
| Individuation metric | measurable character drift over N sessions |

**Exit criteria**
- Robustness curve improves over self-play rounds without human labels.
- Character drift is measurable, bounded, and in the direction of integration.
- Sycophancy rate declines vs baseline over N sessions (the [folk-theorem test](02-game-theory.md#5-individuation--repeated-game-folk-theorem)).

---

## Cross-cutting: the anti-cargo-cult rule

At **every** phase, the falsification test from the corresponding doc is a **merge gate**. A layer
that does not pass is not merged — or, if merged provisionally, is marked experimental and
excluded from downstream claims. The worst outcome for this project is a beautiful diagram with
decorative modules. We guard against that with numbers.
