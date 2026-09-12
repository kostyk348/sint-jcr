# 05 — Arbiter & Enantiodromia Governor

> The Self is not another agent. The Self is the **mechanism**.
> It does not compete for the output; it decides how the output is chosen.

---

## 1. Two coupled subsystems

```
   positions from complexes                deviation integrals
            │                                     │
            ▼                                     ▼
   ┌────────────────────┐               ┌──────────────────────┐
   │   ARBITER          │               │  ENANTIODROMIA        │
   │  Nash bargaining   │◄──────────────│  homeostat (control)  │
   │  → assembly plan   │   forcing     │  integral + bang-bang │
   └─────────┬──────────┘               └───────────┬──────────┘
             │                                       │
             └───────────────┬───────────────────────┘
                             ▼
                    assembly_plan + params
```

The arbiter is **strategic** (game theory). The governor is **dynamic** (control theory). They are
coupled but must never be conflated — see [docs/02](02-game-theory.md) §8.

---

## 2. Arbiter

### 2.1 Inputs
Each active complex submits a **position**:

```jsonc
{
  "agent": "shadow",
  "candidate": "a3",                 // which assembly candidate it favours
  "u":  { "a1": 0.2, "a2": 0.4, "a3": 0.9 },  // utilities per candidate
  "d": 0.1,                          // disagreement payoff (if no output)
  "artifact": "test://repro-1042"    // costly signal, if any (see §02.4)
}
```

Candidates are a small discrete set of assembly plans (which nodes to include, what params). The
space is bounded so bargaining is cheap.

### 2.2 Rule
```
a* = argmax_a  Σᵢ  ln( uᵢ(a) − dᵢ )
```

Then the arbiter:

1. selects `a*`;
2. records **dissent** `δᵢ = uᵢ(a*) − dᵢ` for each agent;
3. adjusts weights for the next turn proportionally to `1/δᵢ` (a low-surplus agent gains weight);
4. if a candidate has `uᵢ(a*) < dᵢ` for any agent (someone prefers failure to this plan), the
   arbiter refuses and escalates to the [transcendent function](07-transcendent-function.md).

Those four steps are the whole mechanism. No LLM is required to run the arbiter — the utilities
may *come from* LLM agents, but the arbitration itself is deterministic.

### 2.3 Phase corrections (compensation)

If `Σ δᵢ` for a given axis is persistently low, the arbiter applies a **compensation term** to the
next assembly, forcing the neglected axis into consideration. This is the computational reading of
Jung's compensation principle: one-sidedness is corrected by construction.

---

## 3. Enantiodromia governor

### 3.1 Deviation axes

Track signed deviations along declared value axes. Start with:

```
x_abstract(t)      = abstraction  − concreteness
x_performance(t)   = optimization − readability
x_exploration(t)   = novelty      − consolidation
```

Each `x ∈ [−1, +1]`, estimated from the turn's output (deterministic proxies: ratio of new vs.
referenced concepts; diff size; cyclomatic/structure metrics; number of new files vs. edits).

### 3.2 Homeostat

```
I(t) = ∫₀ᵗ x(τ) dτ                        (integral deviation)
I(t) ← clamp(I(t), −I_max, +I_max)        (anti-windup)
if |I(t)| > θ:  u(t) = −K · sign(I(t))    (bang-bang reversal forcing)
```

`u(t)` biases the next assembly plan toward the opposite pole. `K`, `θ`, `I_max` are configured
per axis. `K` can itself be modulated by psychoid `fatigue` (see [docs/04](04-psychoid.md) §4).

### 3.3 Why integral, not instantaneous

An instantaneous threshold would fire on any single turn that leans one way, producing thrash.
The **integral** captures *sustained* one-sidedness — the thing Jung meant by an attitude driven to
an extreme. This is also why the governor must live in a long-running process: an integral needs
time.

### 3.4 Anti-windup is essential

Without the clamp, after a long saturated period the controller would demand an enormous reverse
correction and overshoot into the opposite pathology (the pendulum overshooting). The clamp is the
difference between a homeostat and an oscillator.

> **Falsification:** with the governor disabled, `|I(t)|` saturates monotonically over a long task;
> with it enabled, `|I(t)|` stays bounded and the axis distribution is roughly symmetric.

---

## 4. Coupling between arbiter and governor

- The governor does not vote; it **modifies candidate utilities** by adding `u_eni = −λ·u(t)·(axis
  projection of candidate)`.
- This means the governor's correction is *forced through the same bargaining mechanism* — it has
  no special authority. It is an agent with an unusual utility (a **homeostatic agent**).
- This preserves the property that the Self is a mechanism, not a tyrant.

---

## 5. Logging and audit

Every turn the arbiter writes an `arbitrate` event:

```jsonc
{
  "kind": "arbitrate",
  "selected": "a3",
  "dissent": { "ego": 0.42, "shadow": 0.05, "anima": 0.31 },
  "enantiodromia": { "x_abstract": 0.28, "I": 1.9, "u": -0.4 },
  "vetoes": [],
  "cheap_talk": ["a2:shadow"]
}
```

This log is the raw material for the Shapley estimator ([docs/02](02-game-theory.md) §2) and for
the [risk](10-risks.md) review. If the dissents are always equal, the bargaining is fake.

---

## 6. Falsification summary

| Claim | Test |
|---|---|
| Bargaining is real | outcome responds to disagreement points `d` |
| Compensation works | neglected-axis inclusion rate rises after sustained one-sidedness |
| Governor bounds bias | `|I(t)|` bounded with governor on, saturates with it off |
| No despot | disabling the governor changes behavior; it is influential but not all-powerful |
