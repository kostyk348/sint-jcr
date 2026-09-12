---
description: JCR credit — Shapley attribution of traits/agents from outcomes
agent: sint-main
---

Compute and interpret contribution credit.

1. Call `jcr_credit`.
2. Call `jcr_character` for trait weights.

Report:
- each player's Shapley credit and coverage (how many observations backed it);
- a caveat when coverage is low or when a trait was active in every labelled turn
  (then its credit is necessarily ~0 — there is no counterfactual to attribute);
- which traits earned libido and which are dummies.

Be explicit that this is an estimate from observed turns, not ground truth.
