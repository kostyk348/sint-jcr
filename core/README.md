# jcr-core (Phase 0)

The runtime substrate: an append-only **event bus** and the **libido ledger**
memory field. Zero third-party dependencies for the core — stdlib only — so it
runs anywhere a Python 3.11+ interpreter does.

## Layout

```
jcr_core/
  types.py      Event / Node / Register / Tier / EventKind
  config.py     JCRConfig — every tunable, each falsifiable
  embedding.py  Embedder protocol + HashingEmbedder (zero-dep default)
  events.py     EventLog (SQLite) + Bus (pub/sub)
  ledger.py     LibidoLedger — energy, decay, propagation, repression, economy
  runtime.py    Runtime — wires bus+ledger; the daemon/facade/harness share it
  daemon.py     local HTTP/JSON surface (the harness integration point)
jcr_mcp/
  server.py     FastMCP facade (portable, but advisory only — cannot enforce)
tests/          16 tests, stdlib unittest
```

## Run

```bash
# tests
python3 -m unittest discover -s tests -v

# daemon (harness integration point)
JCR_VERBOSE=1 python3 -m jcr_core.daemon   # http://127.0.0.1:8765

# quick check
curl -s localhost:8765/state | python3 -m json.tool
```

## API (daemon)

| Method | Path | Body |
|---|---|---|
| GET | `/health` | — |
| GET | `/state` | — |
| POST | `/observe` | `{"text": "...", "session": "...", "turn": 0}` |
| POST | `/remember` | `{"content": "...", "register": "FACT", "project": "..."}` |
| POST | `/plan` | `{"text": "...", "k": 8}` |
| POST | `/events` | `{"since": 0, "kinds": ["activation"], "limit": 200}` |
| POST | `/outcome` | `{"node_ids": [...], "useful": true}` |

## What Phase 0 proves

| Claim | Test |
|---|---|
| Events are durable and replayable | `test_persistence_across_reopen` |
| Publication survives a broken subscriber | `test_failing_subscriber_does_not_break_publish` |
| Resonance ranks the relevant node first | `test_inject_ranks_similar_node_higher` |
| Energy decays exponentially | `test_decay_follows_exponential` |
| Activation propagates along edges | `test_propagation_spreads_activation` |
| Repression ≠ deletion | `test_repression_is_not_deletion` |
| Energy behaves as currency | `test_energy_is_the_economy` |

## Environment

| Var | Default | Meaning |
|---|---|---|
| `JCR_HOME` | `~/.local/share/jcr` | database location |
| `JCR_HOST` | `127.0.0.1` | daemon bind |
| `JCR_PORT` | `8765` | daemon port |
| `JCR_VERBOSE` | unset | log requests |

## Install (optional)

```bash
pip install -e ".[mcp]"   # adds fastmcp for jcr_mcp/server.py
```
