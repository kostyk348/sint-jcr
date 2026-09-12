# 07 — The Transcendent Function (Deadlock Reframing)

> The arbiter picks a winner. The Trickster throws noise. Neither is what Jung meant by the
> **transcendent function**, and neither resolves a true deadlock.

---

## 1. Why this layer exists

Some conflicts have no winning candidate. When Ego says "ship it", Shadow says "it's unsound", and
Anima says "it's unmaintainable" — and *every* available plan makes someone prefer failure to it —
the arbiter has nothing to arbitrate. A majority vote picks a loser. Noise (Trickster) perturbs but
does not resolve. Averaging produces a compromise everyone dislikes.

Jung's **transcendent function** is the operation that produces a **third thing** from the tension
of two opposites, not by choosing between them but by **changing the level of representation** so a
new option appears that was not in the original set.

The engineering reading:

> **Deadlock reframing** — when no feasible plan is individually rational, do not decide;
> *re-represent the problem* to generate a new candidate set, then re-run bargaining.

---

## 2. Deadlock detection

The arbiter escalates to the transcendent function when:

```
deadlock  ⟺  ∃ i :  uᵢ(a*) < dᵢ   for every candidate a*      (someone vetoes everything)
             OR   max_a Σᵢ ln(uᵢ(a) − dᵢ)  <  τ_deadlock        (surplus too small)
             OR   the selected candidate oscillates between turns (no stable choice)
```

The oscillation case is important: a system that flip-flops is not bargaining, it is stuck in a
limit cycle, and limit cycles are what the transcendent function is for.

---

## 3. The reframing operators

Operators transform the *representation*, not the utilities. This is what creates candidates that
were never on the table.

| Operator | Transformation | Example |
|---|---|---|
| **Abstraction lift** | find the common super-concept of the opposed claims | "performance vs readability" → "what is the cost model?" |
| **Analogy transfer** | map to a structurally isomorphic problem in another domain | use `sint-resonance`/`sint-algo`: same deadlock in a different field |
| **Assumption inversion** | negate a shared premise both sides assume | "we must do this in one system" → "what if two systems?" |
| **Decomposition** | split the contested object by concern | "the module" → "the interface" + "the implementation" |
| **Sequence change** | same goals, different order | "optimize then ship" → "ship then optimize behind a flag" |
| **Scale change** | change the resolution/time-horizon | "this function" → "this dataflow" |

Analogy transfer is the most powerful and the most dangerous — it is exactly where the
**collective-unconscious library** (global algorithm/pattern priors) plugs in, and exactly where a
cross-domain match must be *structural*, not superficial.

---

## 4. Algorithm

```
on deadlock:
    Δ := the set of opposed positions (what each agent objects to)
    candidates := []
    for op in {lift, analogy, invert, decompose, resequence, rescale}:
        if op is applicable to Δ:
            candidates += op(Δ, collective_unconscious_library)

    new_candidates := filter_deterministic(candidates)   # dedupe, sanity, cost budget
    if new_candidates is empty:
        return escalate_to_human(Δ)                      # do not loop

    re-run bargaining over new_candidates
    if a* is Pareto-improving over the deadlock for ALL agents:
        return a*
    else:
        return escalate_to_human(Δ)                      # a failed synthesis is reported, not forced
```

### The Pareto requirement
This is the crux. Averaging (the naive "merge both sides") typically leaves every agent worse off.
A genuine synthesis must be **at least as good for every agent, and strictly better for at least
one** — a Pareto improvement over the deadlock baseline. If the reframing does not achieve that,
it has not resolved anything, and the system must say so rather than paper over it.

> **Falsification:** compare reframing against (a) majority vote and (b) simple averaging on a set
> of known deadlocks. If reframing does not produce more Pareto-improving outcomes, it is
> decoration, and the layer is deleted.

---

## 5. Relation to the other mechanisms

| Mechanism | What it does | What it does **not** do |
|---|---|---|
| Arbiter | picks among existing candidates | cannot create new ones |
| Trickster | injects entropy to escape a loop | does not make the result *meaningful* |
| Enantiodromia | corrects a drifting axis over time | not a per-conflict resolver |
| **Transcendent function** | changes the representation to create new candidates | does not decide |

They compose: enantiodromia prevents long-run drift, the arbiter handles ordinary conflicts, the
Trickster breaks stochastic loops, and the transcendent function handles *structural* deadlocks
where no candidate is acceptable.

---

## 6. Bounds (why it cannot run away)

Synthesis is expensive (it may call reasoning models and the knowledge bases). Bounds:

- **one reframing attempt per deadlock** in interactive mode; more only in the dream cycle;
- a hard cost budget per attempt;
- a required *deterministic* validation of candidate well-formedness;
- human escalation is the fallback, not an infinite loop.

A system that cannot admit an unresolved conflict will hallucinate a resolution. This layer is
built to *report* failure of synthesis, not to hide it.

---

## 7. Falsification summary

| Claim | Test |
|---|---|
| It reframes, not averages | output representation changes, not just weights |
| It produces Pareto improvements | measured vs vote and average on deadlock set |
| Analogy is structural | matched patterns are isomorphic, not lexically similar |
| It can fail honestly | escalation rate > 0; unresolved conflicts are reported |
