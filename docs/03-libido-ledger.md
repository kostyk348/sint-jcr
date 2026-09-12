# 03 — The Libido Ledger & Memory Field

> All memories are equally present in RAG. In a psyche, nothing is ever equally present.
> **What makes a memory urgent, as opposed to merely similar?**

---

## 1. The gap in current memory

The existing `sint-memory` server has typed blocks, a hash-chain, temporal decay, and
relevance tiers. That is a strong start. What it lacks is a **unified energetic field**:

- decay is a scalar per block, not a field with propagation;
- there is no notion of a node *urgently demanding* attention;
- there is no market where attention is contested;
- "repression" (a memory that still exists but is out of fast reach) is not modeled.

The Libido Ledger is the substrate that fixes this. It subsumes the functions of `sint-memory`
(decay, tiers, provenance), `sint-resonance` (activation), and adds the missing energetics.

---

## 2. The node

A node is an autonomous capsule. Schema: [`schemas/node.schema.json`](../schemas/node.schema.json).

```jsonc
{
  "id": "n_01J8Z...",
  "ts": "2026-09-12T19:48:00Z",
  "register": "FACT",              // SENSE|FACT|LOGIC|OPINION|ACTION|CAUSALITY
  "project": "school-v2",
  "content": "…",
  "embedding": [/* f32[] */],
  "affect": [/* f32[4] */],         // feeling-toned core (see §6)

  "E": 0.83,                        // libido: current energetic charge, [0,1]
  "tau": 604800,                    // decay half-life, seconds
  "tier": "hot",                    // hot | warm | cool | cold
  "last_activation": "2026-09-12T19:40:00Z",
  "activation_count": 47,

  "edges": [                        // associative links
    { "to": "n_01J8Y...", "w": 0.71, "kind": "assoc|contradicts|refines|archetype" }
  ],

  "provenance": { "session": "…", "block_id": "4522", "hash": "…" }
}
```

**The feeling-toned core.** Jung insisted a complex is organized around an *affect*, not around a
topic. So every node carries a low-dimensional affect signature (borrowed from the psychoid
layer). Clustering by `(embedding, affect)` — not by embedding alone — is what makes a cluster a
*complex* rather than a semantic neighborhood.

---

## 3. Energy dynamics

The charge of a node evolves by a leaky integrator with associative input:

```
dEᵢ/dt  =  −Eᵢ / τᵢ                       (decay)
          + β · resonanceᵢ(t)             (direct activation from current context)
          + γ · Σⱼ wᵢⱼ · aⱼ(t)            (propagation from active neighbours)
          + ξ(t)                          (small stochastic noise)
```

Discretized at tick `Δt`:

```
Eᵢ ← clamp( Eᵢ · exp(−Δt/τᵢ)
            + β · max(0, cos(buf, embᵢ) − ρ_min)
            + γ · Σⱼ wᵢⱼ · aⱼ
            + ξ ,  0, 1 )
```

- `aⱼ` — recent activation of neighbour `j` (EMA of its resonance).
- `ρ_min` — floor so unrelated content contributes nothing.
- `ξ` — keeps cold nodes from being perfectly unreachable (a memory can surface "for no reason",
  which is exactly the phenomenological point of synchronicity).

**Consumption:** an agent that bids `b` libido for a slot has it *charged* from its account, not
just subtracted from a standalone node. Libido is a conserved-ish currency per tick — the total
budget is fixed, so attention is zero-sum. This is what makes the VCG auction meaningful (§ game
theory).

---

## 4. Repression (not deletion)

A node is **repressed**, not removed, when its energy stays below `ε_repress` for longer than
`T_repress`:

```
if Eᵢ < ε for > T:  tier ← cold;  remove from hot ANN index;  keep in cold store
```

Properties of repression:

1. **Still reachable** — a cold node can be promoted by a strong resonance (a "return of the
   repressed"). It is out of the *fast* index, not gone.
2. **Still counted** — it participates in graph metrics and can still be an archetype attractor.
3. **Provenance intact** — the hash-chain is never broken by repression.

This is the mechanism that gives token economy: the hot index is small by construction, and only
resonant cold nodes are promoted.

> **Falsification:** correlate `ΔE` at time `t` with reuse at `t+Δ`. If `ρ(ΔE, reuse) ≈ 0`, the
> energy is decorative and the ledger should be replaced by plain recency.

---

## 5. Activation and promotion

On each turn:

1. Embed the live buffer (code, terminal, dialogue tail).
2. Compute `resonanceᵢ` for hot nodes and for a sampled subset of cold nodes.
3. Inject energy into the top-`k` by resonance (`β · …` above).
4. Propagate one hop to neighbours (`γ`).
5. Emit `activation` events for nodes crossing `E_promote`; the synchronicity monitor may raise a
   `crossing` (see [docs/06](06-synchronicity.md)).
6. At turn close, apply reinforcement: nodes whose content appeared in the final answer get
   `+ΔE`; nodes that were surfaced as noise get `−ΔE` (this feeds calibration).

---

## 6. Affect signatures and complexes

`affect` is a 4-vector `{tension, load, stability, fatigue}` produced by the psychoid layer.
A **complex** is detected as a dense cluster in `(embedding × affect)` space whose nodes co-activate
above a threshold across multiple sessions. Detection is deterministic (DBSCAN over the combined
space) — no LLM.

Each detected complex becomes a candidate **daemon** (see
[`schemas/complex-manifest.schema.json`](../schemas/complex-manifest.schema.json)): it gets a
name, a trigger signature, a memory cluster, and a bid strategy.

---

## 7. Persistence & performance

| Concern | Approach |
|---|---|
| Storage | SQLite: `nodes`, `edges`, `events`, plus a vector index (`sqlite-vec` / `sqlite-vss`) |
| Cold store | separate table/partition; not in ANN index |
| Rebuild | ledger state is derivable by replaying the event log |
| Cost | embedding is the only heavy op → batch, cache by content hash, throttle when idle |
| Privacy | local-only by default; embeddings never leave the machine unless configured |

---

## 8. Interface sketch (design, not implementation)

```python
class LibidoLedger:
    def inject(self, buffer_embedding, k: int) -> list[Activation]: ...
    def propagate(self, activated: list[NodeId], hops: int = 1) -> None: ...
    def charge(self, agent: str, amount: float) -> bool: ...      # for VCG
    def reinforce(self, node_ids: list[NodeId], delta: float) -> None: ...
    def decay_tick(self, dt: float) -> None: ...
    def promote_or_repress(self, now: float) -> TierChange: ...
    def export(self) -> FieldBundle: ...
    def import_(self, bundle: FieldBundle) -> None: ...
```

---

## 9. Falsification summary

| Claim | Test |
|---|---|
| Energy predicts reuse | `ρ(ΔE, later reuse) > 0` |
| Repression is not deletion | a cold node is promotable by resonance |
| Token economy improves | fewer context tokens at matched quality vs monolith |
| Affect cluster = complex | detected clusters are stable across sessions, not one-off |
