# 00 — Thesis: From Myth to Mechanism

> *The danger of this project is not that it is wrong. It is that it sounds right.*

---

## 1. The problem with "Jungian AI"

Jung's model of the psyche is **mythopoetic**: it is descriptive, evocative, and deliberately
fuzzy at the boundaries. That is a feature for a theory of human meaning-making. It is a fatal
defect for an architecture, because an architecture must specify *what computation happens when*.

There is a well-known failure mode here. Take any evocative concept, give it to a builder, and
you will get a module with that name bolted onto a generic pipeline:

- "Shadow module" = a second prompt that says "now critique the above".
- "Synchronicity engine" = cosine similarity search with a different label.
- "Individuation" = a nightly cron job that summarizes logs.

These are not wrong *because* they are simple. They are wrong because **the name creates an
illusion of explanatory depth.** A reviewer sees "Shadow" in the diagram and assumes something
Shadow-like is happening.

The thesis of JCR is the opposite: **every Jungian concept must be reduced to a computational
signature — a set of observable state transitions and measurable quantities — or it is not
allowed in the architecture.**

---

## 2. Metaphor vs mechanism: the reduction table

For each concept we ask three questions:

1. **What state does it read?**
2. **What state does it write?**
3. **What observation would prove it is doing nothing?**

| Concept | Reads | Writes | Falsification test |
|---|---|---|---|
| Ego | current context buffer | generation request | If removing the arbiter changes nothing, Ego is just the model |
| Persona | candidate output | filtered output | Ablate tone/safety rules → output style must drift measurably |
| Shadow | Ego's draft + claims | veto / counterexample | If veto rate ≈ 0 **or** vetoes never change the outcome, it is ornamental |
| Anima/Animus | dominant axis of reasoning | orthogonal injection | Measure output variance along the un-dominant axis; if unchanged, it is not compensating |
| Trickster | loop detector state | stochastic perturbation | If removing it doesn't change loop-exit time, it does nothing |
| Self | all agents' utilities | resource allocation | Shapley attribution must be non-uniform; if all equal, arbitration is fake |
| Complex | memory cluster activation | bid for context | If clusters never co-activate distinctly, they are one agent cosplaying |
| Libido | activation history | node energy | Correlate `ΔE` with later reuse; if ρ≈0, the energy is decorative |
| Repression | node energy | tier demotion | A "repressed" node must still be reachable but outside the hot index |
| Psychoid | OS telemetry | affect vector → params | Show that a CPU/error spike changes generation params **before** any text is produced |
| Collective unconscious | problem structure | archetypal pattern | Pattern must come from a global library, not from session memory |
| Synchronicity | live buffer vs field | priority event | Enforce the 3-condition filter; measure precision against outcome labels |
| Enantiodromia | integral of axis deviation | forced reversal | With the governor off, the axis must monotonically saturate on long tasks |
| Transcendent function | two opposed positions | a third frame | If it only picks a winner, it is an arbiter, not a transcendent function |
| Individuation | cross-session outcomes | character drift | Character must change measurably over N sessions, in the direction of integration |

If a component cannot pass its falsification test, **it is deleted**, regardless of how good the
metaphor feels.

---

## 3. Why Jung at all? (the steelman)

If the reduction is the point, why start from Jung rather than, say, Minsky's *Society of Mind*,
or a plain multi-agent architecture? Three reasons that are not mystical:

### 3.1 Jung already contains a multi-agent dynamics with conflict
The `Society of Mind` is cooperative by default. Jung's key structural insight is **conflict and
compensation**: consciousness is necessarily one-sided, and the unconscious *compensates*. This is
a built-in mechanism for diversification and for catching the failure mode where a single dominant
policy runs away. It maps directly onto adversarial-agent design, but with a *dynamics* — not just
an ensemble.

### 3.2 Jung contains an energetic (not just storage) model of memory
Freud's and Jung's "libido" is a **charge** that attaches to representations and to complexes.
Modern RAG has no such thing: all retrieved chunks are equally "present" once in context. The
libido concept forces a design question most systems ignore: **what makes a memory *urgent*, as
opposed to merely similar?** This is the core of the Libido Ledger ([docs/03](03-libido-ledger.md)).

### 3.3 Jung contains an explicit theory of individuation over time
Most agent frameworks have no notion of developmental time. Jung's individuation — the two-half
process of building an ego and then integrating the Self — gives a principled *ordering* for a
long-lived agent's evolution. It tells you, concretely, **what to build first**: you cannot
individuate before you have an ego. This is why the [roadmap](09-roadmap.md) is ordered the way it
is.

What we explicitly **do not** import: metaphysical claims (a literal collective unconscious,
actual acausality in nature, transmigration). These are used only as *design vocabulary*, never as
mechanism.

---

## 4. The SINT continuity

JCR is not a break from SINT; it is the layer SINT left implicit.

SINT (see [manifesto](https://github.com/kostyk348/sint-manifesto)) defines seven cognitive layers
and an epistemic charter: registers, provenance, calibration. It builds **what an agent knows and
how it is accountable.** JCR builds **what an agent *is* over time** — the field dynamics, the
internal conflict, the arbitration, the memory energetics.

Concretely, the existing stack already implements a surprising amount of the mapping:

```
sint-memory          ⟶  personal unconscious (decay, tiers, hash-chain provenance)
sint-resonance       ⟶  synchronicity primitive (but reactive, not continuous)
sint-dream           ⟶  individuation / offline consolidation
dso-swarm + subagents⟶  complexes (but no competition for a bus, no interruption)
sint-self            ⟶  persona
liquid / epistemic   ⟶  belief revision and calibration
```

The gaps — libido field, psychoid telemetry, arbiter, continuous monitor, transcendent function —
are the subject of this repository.

---

## 5. What "working" means

JCR is successful when, and only when, the following are demonstrated with numbers:

1. **Token economy:** matched task quality at measurably fewer context tokens than a monolith,
   because only resonant nodes are promoted.
2. **Anti-sycophancy:** on a labeled set of user-proposed bad ideas, the Shadow raises objections
   at a higher rate than the baseline planner, *and* its objections are verifiable.
3. **Loop escape:** on tasks that trap a baseline agent, the Trickster/governor reduces
   time-to-exit, without increasing the regression rate.
4. **Portability:** the same identity/memory produces consistent behavior across ≥2 model
   providers.
5. **Calibrated synchronicity:** the monitor's surfaced events have precision above a stated
   threshold against human-labeled usefulness (see [docs/06](06-synchronicity.md)).

If none of these improve, the correct conclusion is that the psychology was decoration. We commit
to publishing that conclusion if it happens.
