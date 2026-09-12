# 13 — MCP Review: what is worth upgrading

> 24 MCP servers is a lot of capability and a lot of overlap. Now that the
> harness exists, this is the honest audit: what to upgrade, what to leave,
> what is now **superseded**.

Scoring: **V** = value to the live system (0–3) · **G** = gap vs what JCR
actually needs (0–3) · **C** = cost to fix (L/M/H) · verdict.

---

## 1. Findings

| Server | V | G | C | Verdict |
|---|---|---|---|---|
| `sint-memory` | 3 | 3 | M | **Upgrade** — storage format + bridge |
| `sint-self` | 2 | 3 | M | **Upgrade** — one identity store (bridge to Character Ledger) |
| `sint-marketplace` | 2 | 3 | M | **Upgrade** — transport for the collective-unconscious library |
| `sint-resonance` | 2 | 2 | — | **Leave** — JCR supersedes with the continuous monitor |
| `sint-dream` | 2 | 2 | M | **Merge candidate** — JCR's DreamCycle is outcome-driven |
| `sint-epistemic` + `sint-liquid` | 3 | 1 | — | **Leave** — good; consider merging the two later |
| `sint-dso-matcher` / `-swarm` | 2 | 1 | — | **Leave** — deterministic primitives; JCR arbitrates above them |
| `sint-forest` | 1 | 1 | — | **Leave** — overlaps attribution; keep as a sampler |
| `sint-historian` | 2 | 0 | — | **Leave** — telemetry complements JCR's |
| `sint-prospective` | 2 | 0 | — | **Leave** |
| `sint-llm-swarm` | 1 | 1 | — | **Leave** — it averages; JCR bargains. Different by design |
| `sint-algo`, `sint-spec`, `sint-crypto`, `sint-embed`, `sint-re-graph`, `g-tools`, `sint-devflow`, `ada-spark`, `sint-kicad` | — | 0 | — | **Leave** — domain organs; no change |
| `kostyk348/sint` (monorepo) | — | 2 | L | **Fix** — stale: documents 11 servers, there are 24 |

Legend: V/G are judgments, not measurements. C is effort.

---

## 2. The three upgrades worth doing

### 2.1 `sint-memory` → `.eml` (or at minimum export)
The memory server stores 4 600+ blocks as **JSONL with a sha256 hash-chain**.
JCR's bus is now an **RFC822 `.eml` hash-chain**. Two chain formats is one too
many: unify on `.eml` so memory, bus, and mesh all speak one format and the
same `verify` / `mail` / `sync` tooling applies.
Cheap first step already done: an **import bridge** exists
(`jcr_core.bridge`) that verifies the source chain and ingests blocks into the
ledger. Next: make the memory server itself write `.eml` messages.

### 2.2 `sint-self` ↔ Character Ledger (one identity store)
Right now identity can live in two places: `sint-self` (vector character DB)
and JCR's `character.db` (traits + evidence + drift). Two sources of identity
is a correctness bug waiting to happen. Pick one authority — the Character
Ledger, because it has evidence and drift — and make `sint-self` a *recall
front-end* over it. This is **not** optional if we care about "identity survives
a model swap" being more than a slogan; if two stores disagree, it does not.

### 2.3 `sint-marketplace` → collective-unconscious transport
The marketplace already moves listings over SMTP/EML between instances. Since
JCR events are now `.eml`, the same artifact can carry **invariants** and
**ratified traits** between instances — the literal implementation of the
collective unconscious. Proposed: publish ratified traits / learned invariants
as `knowledge` listings, subscribe by domain. Guardrail: human ratification
before any invariant becomes permanent (already enforced locally).

---

## 3. What NOT to upgrade (and why)

- **`sint-resonance`** — its job is now split: the *primitive* (similarity) stays,
  the *continuous, calibrated, archetype-filtered* behavior belongs to the JCR
  monitor (a daemon, which MCP cannot be). Upgrading the server would fight the
  architecture.
- **`sint-dso-matcher` / `sint-dso-swarm`** — deterministic and cheap. The
  arbiter is a different object (Nash bargaining over disagreement points); do
  not smuggle bargaining into the matcher.
- **`sint-llm-swarm`** — bagging + averaging is a legitimate ensemble, but it is
  *not* the psyche. Keep it; do not call it the Shadow.

---

## 4. Redundancy map (after JCR)

```
identity      sint-self        ──►  Character Ledger (authority)
memory        sint-memory      ──►  Libido Ledger (derived) + import bridge ✅
synchronicity sint-resonance   ──►  JCR monitor (future); server stays a primitive
arbitration   dso-matcher/swarm──►  JCR arbiter (Nash)
learning      sint-dream        ──►  DreamCycle (outcome-driven) + sint-dream (content)
criticism     subagents/llm-swarm►  Artifact Shadow (costly signals)
```

**Rule going forward:** one authority per layer. A second store of the same
thing is not redundancy, it is a future contradiction.

---

## 5. Immediate hygiene

1. `kostyk348/sint` is stale (11 servers documented, 24 exist). Either regenerate
   it from `catalog/servers.json` or mark it archived pointing here.
2. A handful of server repos have uncommitted local changes (epistemic, forest,
   prospective, resonance, liquid, dream, all `dso-*`). Not urgent, but drift.
3. `sint-kicad` and the `g-tools` MCP wrapper are local-only (no repo). If they
   matter, give them repos; if not, document them as local.

---

## 6. Bottom line

Three upgrades are worth it (`sint-memory`, `sint-self`, `sint-marketplace`);
everything else is either already good, intentionally a primitive, or now
superseded by the harness. The biggest *risk* is not missing features — it is
**two sources of truth** for identity and memory, which quietly destroys the
portability claim. Fix that first.
