---
description: JCR runtime dashboard — state, telemetry, character, invariants, monitor
agent: sint-main
---

Report the current state of the JCR runtime. Call the `jcr` MCP tools and render a
compact dashboard:

1. `jcr_state` — bus/ledger/character/telemetry/shadow/invariants/governor/monitor
2. `jcr_telemetry` — turn + label counts, useful rate, open proposals
3. `jcr_character` — traits with weights and drift (individuation signal)
4. `jcr_invariants` — learned guard patterns and ratification status
5. `jcr_credit` — Shapley credit over traits

Format:

```
JCR — status
  bus        <format> · <events> events · chain <ok|BROKEN>
  ledger     <nodes> nodes · mean energy <x>
  character  <traits> traits · mean weight <x>
  turns      <labelled>/<total> labelled · useful <rate>
  shadow     <confirmed>/<with_artifact> confirmed · cheap talk <n>
  invariants <n> (<ratified> ratified)
  governor   <axis: I/u>
  monitor    precision <p> · hard <bool>
```

Then one line: the single most important thing to act on. Do not invent numbers.
