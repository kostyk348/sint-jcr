---
description: Run the JCR dream cycle — consolidate traits and review proposals
agent: sint-main
---

Run consolidation and report what changed.

1. Call `jcr_dream` (min_evidence=2).
2. Call `jcr_proposals` — candidate traits induced from successful turns.
3. Call `jcr_character` — the trait set after consolidation.

Report:
- which traits were reinforced or decayed, with the delta and evidence counts;
- each open proposal, one line, with its evidence count;
- a recommendation: which proposals to ratify (and why), which to discard.

Do **not** ratify anything yourself unless the user explicitly asks. Proposals are
owner-ratified by design (docs/12-character.md).
