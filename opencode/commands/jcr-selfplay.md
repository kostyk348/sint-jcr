---
description: JCR self-play hardening — generate breaking inputs, learn guard patterns
agent: sint-adversarial
---

Harden the guard system against breaking inputs, then report honestly.

1. Call `jcr_selfplay` (rounds=3).
2. Call `jcr_invariants` — the learned patterns and their status.

Report:
- the robustness curve (per round) and whether it improved;
- each learned pattern, and **verify by inspection** that it cannot match a benign
  command (no false positives) — if any pattern looks too broad, say so;
- note that self-play needs a verifiable oracle; without one it is noise.

Do not ratify invariants without the user's explicit request.
