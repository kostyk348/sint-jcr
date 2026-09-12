# jcr-harness

The in-loop executive hand for opencode. This is what makes JCR a **harness**
rather than "another MCP server".

## Why this directory exists

MCP tools are called *by the model*. The model decides whether to consult memory,
whether to be honest, when to stop. A plugin runs *around* the model and can
enforce. That difference is the whole point — see
[docs/11-harness.md](../docs/11-harness.md).

| Hook | Grants | Phase |
|---|---|---|
| `chat.message` | observe user turn | 0 ✅ |
| `experimental.chat.system.transform` | assemble system prompt | 0 ✅ |
| `tool.execute.after` | telemetry / reinforcement | 0 ✅ |
| `chat.params` | control temperature/topP/max tokens | 1 (psychoid) |
| `permission.ask` | **veto** (deny) | 3 (arbiter) |
| `tool.execute.before` | capability narrowing | 3 (arbiter) |
| `experimental.chat.messages.transform` | context compiler | 4 (synchronicity) |

## Run

```bash
# 1. start the core daemon
cd ../core && python -m jcr_core.daemon

# 2. register the plugin in opencode.json
{
  "plugin": ["./harness/index.ts"]
}
```

Environment: `JCR_URL` (default `http://127.0.0.1:8765`), `JCR_TIMEOUT_MS`
(default `400`).

## Contract

- The harness must **never break the loop**. Every `jcr-core` call is timeboxed
  and failure-tolerant; if the daemon is down the host behaves like a normal
  agent.
- Policy lives in `jcr-core`. The plugin is deliberately dumb: it applies
  directives, it does not invent them.
