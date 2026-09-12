# 10 — Honest Risks, Anti-Patterns, Failure Modes

> This document exists because the project's greatest danger is that it *sounds* right.

---

## 1. Aporhenia (the synchronicity trap)

**Risk:** a tunable resonance threshold will always produce *some* striking coincidences. Humans
are pattern-hungry and will read meaning into noise. A "mystically insightful" system that is
actually random is worse than an honest RAG, because it erodes trust in the whole system.

**Mitigation:**
- the 3-condition filter ([docs/06](06-synchronicity.md)) — acausal **and** meaningful **and**
  archetypal; the archetypal condition is the strict one;
- mandatory calibration with `jcr_outcome` labels and a precision floor;
- automatic downgrade to soft-only if the floor cannot be held;
- commitment to publish a null result if precision ≈ chance.

**Residual risk:** medium. This is the hardest layer to validate and the easiest to fool oneself
about.

---

## 2. Metaphor as proof (cargo-culting)

**Risk:** naming a module "Shadow" makes reviewers assume Shadow-like behavior. The name hides the
absence of mechanism.

**Mitigation:**
- the reduction table in [docs/00](00-thesis.md) — every concept has state reads/writes and a
  falsification test;
- no component ships without its test as a merge gate;
- vocabulary discipline: the mechanism is always named alongside the metaphor
  ("Shadow (adversarial critic with costly signals)").

**Residual risk:** high if discipline slips. This is a *process* risk, not a technical one.

---

## 3. Uncalibratable payoffs

**Risk:** quantities like `FragilityExposed`, `Diversity`, `ΔEntropy` cannot be observed. If the
game-theoretic layer relies on them, it operates on fiction.

**Mitigation:**
- only observable quantities are logged: veto rate, confirmation rate, disagreement, dissent,
  downstream outcome, token cost, loop-exit time;
- utilities are *estimated from outcomes*, not declared;
- Shapley is computed on confirmed artifacts.

**Residual risk:** medium. The `v(S)` estimator is crude at first; it must be refined or the
credit allocation is noise.

---

## 4. Runtime cost

**Risk:** continuous embedding and background workers are expensive on a personal machine.

**Mitigation:**
- adaptive cadence and the [degradation ladder](01-architecture.md#6-degradation-ladder);
- local embeddings, cached by content hash;
- ANN over hot nodes + a *sample* of cold, never the whole store;
- the expensive layer (Shadow) is on-demand and Phase 2, not Phase 0.

**Residual risk:** low, if the degradation ladder is actually implemented and tested.

---

## 5. The uncanny assistant

**Risk:** a system that "spontaneously remembers" can feel intrusive or unsettling. Trust falls
faster than it is built.

**Mitigation:**
- **soft synchronicity by default** — priority is raised, the conversation is not seized;
- hard injection is opt-in and gated;
- all surfaced material is labeled and dismissable.

**Residual risk:** low with soft defaults; high if defaults are flipped for a demo.

---

## 6. Degenerate self-play

**Risk:** adversarial self-play escalates into unusable complexity — the Shadow generates absurd
edge cases, Ego bloats to defend against them.

**Mitigation:**
- fixed compute budget per round;
- minimality constraint on generated artifacts (Occam);
- human review before a new invariant enters the collective-unconscious library.

**Residual risk:** medium.

---

## 7. Arbitration capture

**Risk:** one agent (Ego, or the model itself) learns to game the utilities and always win.

**Mitigation:**
- VCG makes truthful bidding dominant for attention;
- Shapley payments are tied to *confirmed* outcomes, which Ego cannot fabricate alone;
- Shadow lives out-of-band, unreachable by prompt injection;
- dissent logs are audited for uniformity.

**Residual risk:** medium; requires monitoring the dissent distribution over time.

---

## 8. Continuity illusion

**Risk:** we may over-read continuity into what is, mechanically, a state machine with a rich
memory. Over-claiming (in docs or in marketing) invites justified dismissal.

**Mitigation:**
- explicit non-claims: JCR does not claim consciousness, sentience, or subjective experience;
- it is a *control system* with a rich internal state that behaves consistently over time;
- provider-portability is about *behavioral* consistency, not identity.

**Residual risk:** low for the engineering, high for the narrative. Keep the narrative honest.

---

## 9. Anti-patterns (do not do these)

1. **Shadow-before-Ledger.** Building the critic first; it has nothing to record its cost against.
2. **Hard synchronicity by default.** Interrupting the user with "insights".
3. **Majority vote dressed as bargaining.** If `d` doesn't affect the outcome, it's voting.
4. **Cheap-talk critics.** A critic with no artifact is a second opinion, not evidence.
5. **Merging the complexes** into one averaged policy. That destroys the diversity that justifies
   the architecture (Hillman's point).
6. **Declaring victory from a diagram.** No layer is "done" without its falsification test.
7. **Training the model to encode identity.** Identity belongs outside the weights, always.
8. **Deleting memories.** Repress, don't delete; provenance is sacred.

---

## 10. What would falsify the whole project

Stated plainly, so it can be checked:

- If the Libido Ledger does **not** improve the token economy at matched quality → the energetic
  memory is decorative.
- If the Shadow's vetoes do not measurably reduce bad outcomes → adversarial criticism adds cost,
  not value.
- If the arbiter's bargaining is invariant to disagreement points → it is voting.
- If synchronicity precision ≈ chance → the layer is a coincidence machine.
- If none of these improve, the honest conclusion is that the Jungian framing was
  **good design vocabulary and bad engineering**, and it should be reported as such.
