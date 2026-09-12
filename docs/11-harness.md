# 11 — The Harness

> The ecosystem has 24 MCP servers and one passive plugin.
> That is many **organs** and no **executive**.
> This document defines what the harness is, why the current stack is not one, and how JCR
> becomes one.

---

## 1. Definition

A **harness** is the code that owns the control loop and the state that persists between model
calls. It is neither the model, nor the tools, nor the prompt.

```
model      = a stateless function  (state → text)
tools/MCP  = capabilities          (callable on request)
prompt     = instructions          (a suggestion to the model)
harness    = the executive         (owns loop, state, policy, enforcement)
```

The distinguishing question is simple:

> **Who decides what goes into the context, what happens next, and when to stop?**
> If the answer is "the model, following instructions", there is no harness.

---

## 2. The four levels of control

| Level | Name | Who is in control | Enforcement | Testable |
|---|---|---|---|---|
| **L0** | model-only | the model | none | no |
| **L1** | prompt-as-harness | the model, nudged by text | none | no |
| **L2** | tool-as-harness (MCP) | the model decides to call | none (advisory) | partial |
| **L3** | hook-as-harness (plugin) | code inside the loop | real (can deny/rewrite) | yes |
| **L4** | daemon-as-harness | an external process owning state/policy | real + persistent | yes |

**Where the current stack sits:** L1 (the `sint-main` system prompt encodes a full protocol:
session-start, classification, delegation) + L2 (24 MCP servers) + a *passive* L3
(`sint-hooks.ts` observes and injects text, but never decides).

**Diagnosis:** the system behaves like an executive only insofar as a language model *chooses* to
follow a long instruction. That is L1. It is the weakest form of control that still looks like a
harness.

---

## 3. Why a prompt is not a harness

The current `sint-main` prompt is, in effect, a program written in English and executed by a
probabilistic interpreter. It has all the failure modes of that arrangement:

1. **Unenforceable.** The model can skip steps; nothing catches it.
2. **Token-expensive.** The protocol is re-sent every turn; it competes with the actual task.
3. **Unobservable.** There is no telemetry on *compliance*. You cannot compute "session-start read
   the memory 87% of the time."
4. **Non-deterministic.** The same state can produce different orchestration.
5. **Non-composable.** Two rules can conflict and only the model resolves it, silently.
6. **Conflict of interest.** The model both *decides* to consult memory and *is* the thing that
   would be corrected by it. Self-policing is structural weakness, not a bug to be prompted away.

The JCR thesis is to **move the executive out of the prompt and into code**, leaving the model what
it is actually good at: symbolic projection.

---

## 4. The seven functions a harness must own

| # | Function | Meaning |
|---|---|---|
| 1 | **Turn lifecycle** | open → assemble → call → tool → draft → audit → final → close |
| 2 | **Context assembly** | the prompt compiler: build each call from state, not from a static string |
| 3 | **State ownership** | ledger, intentions, affect, deviations, budgets — outside the model |
| 4 | **Policy** | routing, escalation, stop conditions, capability selection |
| 5 | **Enforcement** | the ability to say *no*: veto, budget caps, capability narrowing |
| 6 | **Telemetry** | observability of the harness's own behavior and of model compliance |
| 7 | **Recovery** | snapshot / replay; the event log is the source of truth |

A component that does not do at least one of these is a tool or a library, not the harness.

---

## 5. The opencode hook surface (authoritative)

JCR's harness can be *in the loop* because opencode exposes hooks that permit control, not just
observation. (Source: `@opencode-ai/plugin` `Hooks` type.)

| Hook | Control it grants | JCR use |
|---|---|---|
| `chat.message` | observe new user message | `turn_open`; snapshot intent |
| `experimental.chat.system.transform` | rewrite the system prompt | assemble from ledger + persona, not static |
| `experimental.chat.messages.transform` | **rewrite the whole message array** | the **context compiler**: promote resonant nodes, drop noise |
| `chat.params` | set `temperature/topP/topK/maxOutputTokens/options` | **psychoid coupling** (affect → params) |
| `tool.execute.before` | mutate tool args | capability narrowing, argument constraints |
| `tool.execute.after` | observe tool result | telemetry, ledger reinforcement, outcome capture |
| `permission.ask` | set `allow/deny/ask` | **the veto** — the harness's hard "no" |
| `experimental.session.compacting` | control compaction | consolidation supervision |
| `event` | observe all events | full observability, drift detection |
| `tool` | register native tools | hot-path tools that bypass MCP entirely |

**This is the crucial capability gap the MCP layer cannot fill.** MCP tools are called *by the
model*. Hooks are called *by the host, around the model*. Only the latter can enforce.

---

## 6. JCR harness topology

```
                    ┌──────────────────────────────┐
                    │        opencode host         │
                    └───────────────┬──────────────┘
                                    │ hooks (in-loop)
                    ┌───────────────▼──────────────┐
                    │  jcr-harness  (TS plugin)    │  ← the executive's HANDS
                    │  system/messages/params/     │
                    │  permission/tool hooks       │
                    └───────────────┬──────────────┘
                                    │ JSON over unix socket / localhost
                    ┌───────────────▼──────────────┐
                    │  jcr-core  (Python daemon)   │  ← the executive's STATE + POLICY
                    │  bus · ledger · arbiter ·    │
                    │  psychoid · synchronicity    │
                    └───────────────┬──────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        MCP servers            LLM providers        collective library
        (organs / tools)       (effectors)          (sint-marketplace)
```

Plus `jcr-mcp` (FastMCP) as a **portable fallback** for hosts that do not support plugins. It
exposes a subset (`jcr_state`, `jcr_plan`, `jcr_observe`, `jcr_outcome`) but *cannot enforce*
anything — that limitation is stated explicitly so it is not mistaken for the harness.

---

## 7. The enforcement ladder

"The harness decides" is meaningless without concrete powers. JCR exposes five, weakest to
strongest:

| Rung | Mechanism | Hook | Reversible |
|---|---|---|---|
| 1 | **Advise** | append a line to system prompt | yes |
| 2 | **Constrain** | narrow tool args / available capability | yes |
| 3 | **Rewrite** | modify the message array | yes |
| 4 | **Deny** | `permission.ask → deny` | no (blocked) |
| 5 | **Halt** | refuse the turn; escalate to human | no |

Policy belongs in `jcr-core`, which decides *which rung* to use and returns a directive; the
plugin merely applies it. This keeps policy in one place and the plugin dumb.

---

## 8. MCP vs harness: division of labour

| Belongs to MCP | Belongs to harness |
|---|---|
| domain knowledge (crypto, RE, specs) | turn lifecycle |
| deterministic transformations | context assembly |
| stateless-ish request/response | persistent state & budgets |
| capabilities any host may expose | **policy and enforcement** |
| things the *model* should choose to call | things that must happen *whether or not* the model chooses |

**The rule:** if a component must run while the model is not thinking, it cannot be MCP. It is
harness (plugin/daemon). This is why the synchronicity monitor, the arbiter, and enantiodromia are
not servers — they are the body.

---

## 9. What the harness must not do

- **Not** become a monolithic prompt again (that is the failure being fixed).
- **Not** encode domain knowledge (that lives in MCP/skills; the harness stays domain-thin).
- **Not** block the loop: every hook call has a timeout and a degraded fallback.
- **Not** hold the only copy of state: the event log is authoritative; memory is reconstructible.
- **Not** be un-observable: every decision it makes emits an event.

---

## 10. Phase 0 harness milestones

| Milestone | Deliverable | Done when |
|---|---|---|
| H0 | Daemon skeleton: bus + event log | events persist and replay |
| H1 | HTTP/IPC surface (`/state`, `/observe`, `/plan`, `/events`, `/outcome`) | plugin can call it |
| H2 | `jcr-harness` plugin: `chat.message`, `system.transform`, `tool.execute.after` | state flows into the loop |
| H3 | Enforcement: `chat.params` + `permission.ask` | affect changes params; veto blocks a tool |
| H4 | Context compiler: `experimental.chat.messages.transform` | resonant nodes promoted, measured |
| H5 | Telemetry: compliance + dissent events | dashboard of harness behavior |

The Python core (Phases H0–H1) and the ledger are the foundation; the plugin (H2+) is what makes
it a *harness* rather than another server.

---

## 11. The one-line thesis

> **MCP lets the model do more. The harness decides whether the model should.**
> A system with 24 capability providers and no executive is a Swiss Army knife with no hand.
