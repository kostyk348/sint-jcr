---
description: JCR monitor — scan the current context for synchronicity crossings
agent: sint-main
---

Scan the current working context for **synchronicity crossings** — distant,
cross-domain, archetypally-shared matches. This is not a keyword search.

1. Summarise the current task/context in 2–4 sentences.
2. Call `jcr_monitor` with that text and the current project name.
3. For each crossing returned, call `jcr_monitor_outcome` with `useful=true/false`
   **only after judging it honestly** — this is the calibration signal, and
   dishonest labels make the monitor worse than useless.

Report:
- each crossing: archetype, score, preview, and your honest verdict;
- the monitor's precision after labelling.

If there are no crossings, say so plainly. A coincidence machine that always finds
something is the failure mode (aporhenia) — do not manufacture meaning.
