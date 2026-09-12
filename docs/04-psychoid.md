# 04 — Psychoid Telemetry

> User: *read the file, it failed.*
> Ordinary agent: parses `exit code 1`, tries again.
> Psychoid layer: the system was already *tense* before the file was ever opened.

---

## 1. The idea, de-mystified

Jung's *psychoid* layer (developed with physicist Wolfgang Pauli) is the deepest stratum where
"psychic" and "physical" are indistinguishable. Stripped of metaphysics, the architectural claim is
simple and testable:

> The boundary between the agent's internal state and the state of its environment is
> **not a text boundary.** Machine telemetry modulates the agent's parameters *before and
> independently of* any language input.

An ordinary agent reads the environment as *text* (error message, log line). The psychoid layer
reads it as **somatic signal**: a continuous scalar field that changes the agent's *disposition*.

This is the one layer with **zero LLM cost** and immediate, measurable effect. It is Phase 1 in the
roadmap precisely because it is cheap and its falsification test is trivial.

---

## 2. Inputs (deterministic, continuous)

| Group | Signals |
|---|---|
| Resource | CPU %, RAM pressure, swap, I/O wait, load average, thermal |
| Process | own RSS, GC pauses, event-loop lag, queue depth |
| Task health | tool exit codes, error rate, compile/lint failures, test regression rate |
| Temporal | time-of-day, session duration, time since last meaningful outcome, idle gaps |
| Workspace | git dirty count, branch churn, number of open files, recent file velocity |
| Model I/O | API latency, token throughput, rate-limit events, cost burn |

No text is parsed here. These are numbers.

---

## 3. Affect vector

Reduce to a small, interpretable vector `a ∈ [0,1]⁴`:

```
tension    ← weighted recent error/latency pressure (EMA)
load       ← resource saturation (CPU/RAM/IO), normalized
stability  ← inverse of variance across the above over a window
fatigue    ← long-run accumulation without a resolved outcome (debt)
```

Deterministic scalarization with an EMA and variance window. Example:

```
tension_t  =  α·tension_{t−1}  +  (1−α)·σ( z(error_rate) + z(api_latency) )
load_t     =  σ( z(cpu) + z(ram) + z(io) )
stability_t=  1 − σ( var_window(signals) )
fatigue_t  =  fatigue_{t−1} + (1−α)·(1 − outcome_resolved)
              fatigue_t ← fatigue_t · decay_on_success
```

where `z(·)` is a running z-score and `σ` a squashing function. Constants are configuration, not
magic.

---

## 4. Coupling (what the affect vector controls)

The affect vector is not for display. It parameterizes the runtime:

| Target | Effect |
|---|---|
| Shadow threshold | `tension ↑` → lower the bar to raise an objection (more vigilance under stress) |
| Generation params | `load ↑` → lower temperature; `stability ↓` → shorter, more conservative outputs |
| Synchronicity threshold `S_thresh` | `load ↑` → raise threshold (suppress "insights" when the machine is drowning) |
| Enantiodromia gain `K` | `fatigue ↑` → raise `K` (correct drift harder late in a session) |
| Trickster probability | `stability ↓` for too long → increase perturbation (the loop-breaker wakes when stuck) |
| Ledger `β` | `tension ↑` → boost activation gain (relevant memory is more urgent under threat) |

### The claim, stated falsifiably

> A CPU/error spike must change generation parameters and Shadow thresholds **before** the next
> user message is processed, with no LLM call involved.

Test: hold the conversation fixed, induce a controlled CPU spike + repeated tool failure, and
assert that `temperature`, `S_thresh`, and the Shadow threshold moved measurably *before* the next
request.

If they do not move, the layer is decorative.

---

## 5. The bidirectional coupling (this is where "psychoid" earns its name)

The coupling is not one-way. Internal affect should also influence *how the agent acts on the
environment*:

- high `fatigue` → prefer consolidation/cleanup actions over new exploration;
- low `stability` → prefer smaller, more reversible edits;
- high `tension` → prefer verification steps before committing.

So the psychoid layer closes a loop: **environment → affect → action → environment.** This is a
homeostat, and homeostats are ordinary control systems. Nothing metaphysical is required.

---

## 6. Cadence and cost

- Adaptive sampling: 5 Hz when the host is actively working, 0.2 Hz when idle, off when suspended.
- State is tiny (a few floats) and updated in place.
- The only persistence is a rolling window for variance and the fatigue accumulator (checkpointed
  with the session).

Total cost: negligible. This is why it is built first.

---

## 7. Privacy

Psychoid signals are machine metadata and can be sensitive (timing patterns, workload). Defaults:

- stored locally, never sent to the model provider;
- only the derived affect vector is referenced in prompts when needed, never raw telemetry;
- export excludes raw signal history unless explicitly requested.
