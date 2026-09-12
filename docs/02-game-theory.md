# 02 — Game Theory of the Psyche

> The internal agents are not *like* a multi-agent system. They are one.
> The relevant solution concepts are known — so use them, instead of inventing weighted votes.

---

## 0. Setup

Let the psyche contain `n` internal agents (complexes)
`N = {Ego, Shadow, Anima, Trickster, …}`. Each agent `i` has:

- **type** `θᵢ` — private information (the Shadow *knows* something Ego does not, or believes it does);
- **action** `aᵢ ∈ Aᵢ` — how much and what to inject, whether to veto, which axis to push;
- **utility** `uᵢ(a, θ)` — not directly the same across agents.

An interaction is a **turn**. A turn produces exactly one output token stream — a *common
resource*. This single constraint (one output, many preferences) is what forces arbitration, and
arbitration is a game.

Two layers must not be confused:

| Layer | Mathematical object | Governs |
|---|---|---|
| **Strategic** (who wins what, who gets credit) | cooperative / non-cooperative game | arbitration, credit, credibility, safety |
| **Dynamic** (how state evolves in time) | control theory | enantiodromia, decay, adaptation |

Conflating these is the most common category error in "game-theoretic psychology".

---

## 1. Arbitration = Nash Bargaining (not majority vote)

The complexes must jointly emit one output. That is precisely a **bargaining problem**:
a set of feasible outcomes and a disagreement point `dᵢ` (the payoff each gets if no output is
produced — e.g. task failure, which is bad for everyone but *unequally*).

### Result (Nash, 1950)
The unique solution satisfying Pareto efficiency, symmetry, invariance to affine transformations,
and independence of irrelevant alternatives is:

```
a* = argmax_a  ∏ᵢ (uᵢ(a) − dᵢ)
```

Taking logarithms (monotone, so same argmax):

```
a* = argmax_a  Σᵢ ln( uᵢ(a) − dᵢ )
```

### What this buys us — the minority-protection theorem
The first-order condition gives agent `i` an effective **weight**:

```
wᵢ ∝ 1 / (uᵢ(a*) − dᵢ)
```

Read that carefully. An agent **close to its disagreement point gets enormous weight.**
The Shadow, for whom the disagreement point is catastrophic (shipping a broken system), can
dominate the arbitration with a small utility gap. This is the formal reason a healthy psyche
protects its minorities: **bargaining power is inversely proportional to surplus.**

This is strictly better than the intuitive "weighted vote":

- Weighted vote: weights are *assigned* (arbitrary, and Ego assigns them).
- Nash bargaining: weights are *derived* from utilities and disagreement points.

### Implementation sketch
Each complex emits a position: a desired modulation of the assembly plan plus an estimated utility
and disagreement payoff. The arbiter:

1. discretizes the plan space (a small set of candidate assemblies `a₁..a_k`);
2. asks each complex for `uᵢ(aⱼ)` and its `dᵢ`;
3. picks `argmax_j Σᵢ ln(uᵢ(aⱼ) − dᵢ)`;
4. logs the dissents (agents whose `uᵢ(a*) − dᵢ` is small) — these drive future compensation.

> **Falsification:** if the arbitration outcome is invariant to the disagreement points `d`, then
> the system is not bargaining — it is voting with extra steps. Test: perturb `d` and assert the
> outcome changes.

---

## 2. Credit = Shapley Value (the only fair payment)

Agents are paid in **libido** (attention budget). How much? This must be a *payment rule*, and
payment rules that are fair are not a matter of taste.

For a cooperative game with characteristic function `v(S)` (value of coalition `S`), the **Shapley
value** is:

```
φᵢ(v) = Σ_{S ⊆ N\{i}}  |S|! (n − |S| − 1)! / n!  · [ v(S ∪ {i}) − v(S) ]
```

### Why not just pick a rule
The Shapley value is the **unique** allocation satisfying:

1. **Efficiency** — `Σ φᵢ = v(N)` (all value is distributed);
2. **Symmetry** — equal contributors get equal pay;
3. **Dummy** — an agent that adds nothing gets nothing;
4. **Additivity** — value from independent subgames adds.

Any other "fair-looking" rule violates at least one. So if we want a fair attention salary,
Shapley is **forced**, not chosen. That is a much stronger statement than "we use Shapley because
it's popular".

### The characteristic function for a psyche
`v(S)` = the probability that coalition `S` alone produces a correct/safe outcome. Estimating `v`
is the hard part; in practice it is approximated by A/B: "if only agents in `S` reviewed this
class of task, what was the historical success rate?" Start with a crude estimator and refine from
the `outcome` events.

> **Falsification:** if Shapley attribution is near-uniform in practice, either the complexes are
> not differentiated (one agent cosplaying) or the estimator is broken.

---

## 3. Attention = VCG Auction

Context slots are scarce. In v1 they are *allocated*; in JCR they are **auctioned**. Each agent
bids its libido for a slot, and the mechanism is **Vickrey–Clarke–Groves**:

- allocation maximizes `Σᵢ vᵢ(slot)`;
- each winner pays the **externality** it imposes on others:

```
paymentᵢ = Σ_{j≠i} v_j(allocation without i) − Σ_{j≠i} v_j(allocation with i)
```

### Why VCG
Bidding truthfully is a **dominant strategy**. No agent benefits from misreporting its valuation.
This removes a whole class of manipulation: the Shadow cannot "shout louder" to steal context it
does not need — it would have to pay for it, truthfully.

Combined with §2, the loop closes:

```
Shapley pays agents by historical contribution
        ↓  (libido budget)
VCG lets agents bid that budget for context slots
        ↓  (allocation)
Outcomes are logged
        ↓
Shapley re-estimates contributions           ← closes the loop
```

This is a genuine incentive-compatible attention economy, not a heuristic.

> **Falsification:** measure bid distributions. If one agent always wins and never pays a
> meaningful price, the budget is imbalanced; if bids are constant regardless of context, agents
> are not actually valuing slots.

---

## 4. Shadow Credibility = Costly Signaling

This is the most practically important result in this document, because it explains **why LLM
critics hallucinate criticism.**

### Cheap talk (Crawford–Sobel)
If messages cost nothing and preferences diverge, communication is only partially informative and
partitions into ranges. A critic whose critique costs nothing and whose utility is "look
thorough" will emit critique *regardless of whether a defect exists.* The receiver learns almost
nothing. This is an equilibrium fact, not a bug in the critic LLM.

### Costly signaling (Spence)
Let the Shadow's type be `θ ∈ {honest, bluffing}`. A signal `s` has cost `c(s, θ)`. If costs satisfy
**single-crossing** — producing a *verifiable* signal is cheaper for the honest type (because the
defect actually exists) — then a **separating equilibrium** exists: only honest types send the
signal, and it is credible.

### The engineering requirement
> **A Shadow critique must carry a falsifiable artifact — a reproducing test, an executable
> counterexample, a diff that breaks the claim — or it counts as cheap talk and carries no weight.**

This changes the Shadow from "a second model that says 'looks risky'" into a mechanism:

| Cheap-talk Shadow | Costly-signal Shadow |
|---|---|
| "this could fail at scale" | a test that fails at N=10⁶ |
| "consider security" | an input that produces the exploit |
| "the logic seems off" | a counterexample assignment |
| free, uninformative | costly, separating |
| hallucinates criticism | cannot fake without the artifact |

The cost ledger records, per critique, whether the artifact reproduced. Shadow's Shapley value is
computed on *confirmed* catches. This is the mechanism; "Shadow" is just its name.

> **Falsification:** track the confirmation rate of vetoes. If confirmed-veto rate ≈ 0, the Shadow
> is bluffing and must be rebuilt around artifacts. If ≈ 1, it is either trivial or under-triggered.

---

## 5. Individuation = Repeated Game (Folk Theorem)

The Ego–Shadow interaction is not a one-shot game — it **repeats across turns and sessions.** That
changes everything.

### The good equilibrium
The Folk Theorem: for a sufficiently patient player (discount factor `δ` high), any feasible,
individually rational payoff profile can be sustained as a subgame-perfect equilibrium by trigger
strategies. In particular, **cooperation is sustainable**: Ego genuinely incorporates Shadow's
findings, Shadow critiques in good faith, and both are better off. This cooperative equilibrium
*is what Jung called individuation* — the integration of opposites.

### The bad equilibrium (neurosis)
Now consider a **coalition deviation**: Ego and Persona collude to suppress Shadow. Persona
maximizes external acceptance; Ego minimizes latency. Together they can ignore Shadow and still be
individually rational *for themselves.* This is a Pareto-inferior equilibrium — it is exactly the
"sycophantic assistant" failure mode, and it is *stable* if Shadow's punishment is:
- **delayed** (only matters next session), and
- **discounted** (`δ` low across session boundaries).

Neurosis, formalized: **a stable coalition equilibrium that is Pareto-inferior because the
punished player's retaliation is delayed across sessions.**

### The fix (a game-theoretic prescription)
To make the cooperative equilibrium the unique one:

1. **Reduce delay** — Shadow's veto acts *within* the turn (immediate punishment), not next
   session.
2. **Make punishment credible** — the cost ledger means Shadow's future weight is real; it can
   actually block.
3. **Raise `δ`** — persistent memory across sessions means tomorrow matters; identity continuity
   raises the effective discount factor.
4. **Break the Ego–Persona coalition** — they must not share a utility. Persona answers to
   *external safety/acceptance*, not to Ego's latency. Separating their objectives is what
   prevents collusion.

> **Falsification:** over N turns, if the sycophancy rate (agreement with user's bad ideas) does
> not fall relative to a baseline, the coalition is still winning.

---

## 6. Safety = Zero-Sum Minimax

Prompt injection is an attacker who tries to *capture Ego* (make it act against constraints). The
defender is Persona + Self. This sub-game is approximately zero-sum.

Minimax: the defender chooses `σ_D` to `min_{σ_D} max_{σ_A} L(σ_D, σ_A)`. The **veto** is the
defender's pure minimax strategy: no matter what the attacker makes Ego want, the veto is applied
downstream, outside the captured context.

Crucially, because the veto lives in `jcr-core` and the attacker only controls text that reaches
the model, **the attacker cannot reach the arbiter.** The attack surface is the context window;
the defense is the out-of-band runner. This is the security argument for "the harness is the
agent": the psyche is not inside the attackable context.

---

## 7. Learning without labels = Self-Play

In the dream cycle, run **self-play**: Shadow's objective is to construct inputs that break Ego's
candidate solutions; Ego's objective is to fix them. This is adversarial training with a
*verifiable* objective — the artifact must actually break. Over rounds, Ego's robustness rises
without human labels.

Guardrail: self-play can drift into degenerate escalation. Bound it by (a) a fixed compute budget,
(b) requiring artifacts to be *minimal* (Occam constraint), and (c) human review of any newly
generated invariant before it enters the collective-unconscious library.

---

## 8. What is *not* game theory: Enantiodromia is control theory

Enantiodromia — "any extreme turns into its opposite" — is a **dynamical** claim, not a strategic
one. Forcing it into game language would be a category error. It is a homeostat.

Let `x(t)` be the signed deviation along a value axis (e.g. abstract − concrete). Define the
accumulated bias:

```
I(t) = ∫₀ᵗ x(τ) dτ                    (integral deviation)
```

Enantiodromia triggers when `|I(t)| > θ` and applies a **bang-bang** corrective forcing:

```
u(t) = −K · sign( I(t) ),   K > 0
```

with **anti-windup clamping** `I(t) ← clamp(I(t), −I_max, +I_max)` so the controller does not
over-correct after saturation. This is textbook integral control with a saturation clamp and
reverse action. It has a **falsification test**: with the governor disabled, `I(t)` monotonically
saturates on long tasks; with it enabled, `I(t)` stays bounded. That is measurable.

See [docs/05](05-arbiter-enantiodromia.md) for the coupled arbiter/governor design.

---

## 9. Summary map

| Psychological claim | Formal object | Observable | Falsified if |
|---|---|---|---|
| Opposites must be arbitrated | Nash bargaining | dissent vector | outcome invariant to disagreement points |
| Fair credit for contribution | Shapley value | payment vector | payments near-uniform |
| Attention is contested | VCG auction | bid distribution | bids context-invariant / single winner always |
| Criticism must be earned | Costly signaling | confirmed-veto rate | rate ≈ 0 (bluffing) |
| Integration over time | Repeated game / Folk theorem | sycophancy rate | no decline vs baseline |
| Safety against capture | Zero-sum minimax | escape rate | attacker reaches arbiter |
| Growth without labels | Self-play | robustness curve | no improvement over rounds |
| Extremes self-correct | Integral control (not a game) | `|I(t)|` bounded | saturates unbounded |

The point of this table is that **every psychological claim here has a number attached.** A claim
without an observable is not in this architecture.
