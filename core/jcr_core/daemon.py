"""jcr-daemon — a tiny local HTTP/JSON surface over the runtime.

This is the integration point for the ``jcr-harness`` opencode plugin, which is
written in TypeScript. JSON over localhost keeps the boundary language-agnostic
and lets the harness stay dumb while policy lives in Python.

Endpoints
---------
GET  /health
GET  /state
GET  /params
GET  /character
GET  /telemetry
GET  /proposals
GET  /invariants
GET  /credit
POST /observe   {"text": "...", "session": "...", "turn": 0}
POST /remember  {"content": "...", "register": "FACT", "project": "..."}
POST /plan      {"text": "...", "k": 8}
POST /compile   {"text": "...", "budget": 1200, "k": 8}
POST /veto      {"tool": "bash", "args": {...}}
POST /shadow    {"draft": "..."}
POST /teach     {"statement": "...", "weight": 0.7, "scope": "*", "polarity": 1.0}
POST /dream     {"min_evidence": 2}
POST /ratify    {"proposal_id": "p_...", "weight": 0.5}
POST /selfplay  {"rounds": 3}
POST /ratify_invariant {"invariant_id": "inv_..."}
POST /axes      {"x": {"abstract": 0.4}, "dt": 1.0}
POST /arbitrate {"positions": [...], "candidates": [...], "candidate_axes": {...}}
POST /import    {"path": "...", "limit": null, "force": false}
POST /events    {"since": 0, "kinds": ["activation"], "limit": 200}
POST /outcome   {"node_ids": [...], "useful": true, "turn_id": "turn_..."}

Run: python -m jcr_core.daemon  (JCR_HOST / JCR_PORT / JCR_HOME env)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jcr_core.runtime import Runtime


def _make_handler(rt: Runtime):
    class Handler(BaseHTTPRequestHandler):
        server_version = "jcr-daemon/0.1"

        def log_message(self, fmt, *args):  # keep the console quiet
            if os.environ.get("JCR_VERBOSE"):
                super().log_message(fmt, *args)

        def _send(self, code: int, body: dict) -> None:
            raw = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return {}

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                return self._send(200, {"ok": True})
            if self.path == "/state":
                return self._send(200, rt.state())
            if self.path == "/params":
                return self._send(200, rt.params())
            if self.path == "/character":
                return self._send(200, rt.character_state())
            if self.path == "/telemetry":
                return self._send(200, rt.telemetry())
            if self.path == "/proposals":
                return self._send(200, {"proposals": rt.trait_proposals()})
            if self.path == "/invariants":
                return self._send(200, {"invariants": rt.invariants_list()})
            if self.path == "/credit":
                return self._send(200, rt.credit())
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            b = self._body()
            try:
                if self.path == "/observe":
                    return self._send(200, rt.observe(b.get("text", ""), b.get("session"), b.get("turn")))
                if self.path == "/remember":
                    return self._send(200, rt.remember(b["content"], b.get("register", "FACT"), b.get("project", "SYSTEM")))
                if self.path == "/plan":
                    return self._send(200, rt.plan(b.get("text", ""), int(b.get("k", 8))))
                if self.path == "/compile":
                    return self._send(200, rt.compile(b.get("text", ""), int(b.get("budget", 1200)), int(b.get("k", 8))))
                if self.path == "/params":
                    return self._send(200, rt.params())
                if self.path == "/veto":
                    return self._send(200, rt.veto(b.get("tool", ""), b.get("args")))
                if self.path == "/teach":
                    return self._send(
                        200,
                        rt.teach(
                            b["statement"],
                            float(b.get("weight", 0.5)),
                            b.get("scope", "*"),
                            float(b.get("polarity", 1.0)),
                        ),
                    )
                if self.path == "/events":
                    return self._send(200, {"events": rt.events(int(b.get("since", 0)), b.get("kinds"), int(b.get("limit", 200)))})
                if self.path == "/outcome":
                    return self._send(200, rt.outcome(list(b.get("node_ids", [])), bool(b.get("useful", True)), b.get("turn_id")))
                if self.path == "/dream":
                    return self._send(200, rt.dream_consolidate(int(b.get("min_evidence", 2))))
                if self.path == "/ratify":
                    return self._send(200, rt.ratify(b["proposal_id"], float(b.get("weight", 0.5))) or {"error": "not found or already ratified"})
                if self.path == "/selfplay":
                    return self._send(200, rt.selfplay_run(int(b.get("rounds", 3))))
                if self.path == "/shadow":
                    return self._send(200, rt.shadow_review(b.get("draft", "")))
                if self.path == "/ratify_invariant":
                    return self._send(200, {"ratified": rt.ratify_invariant(b["invariant_id"])})
                if self.path == "/axes":
                    return self._send(200, rt.observe_axes(b.get("x", {}), float(b.get("dt", 1.0))))
                if self.path == "/arbitrate":
                    return self._send(200, rt.arbitrate(b.get("positions", []), b.get("candidates", []), b.get("candidate_axes")))
                if self.path == "/import":
                    return self._send(200, rt.import_memory(b.get("path"), b.get("limit"), bool(b.get("force", False))))
            except KeyError as exc:
                return self._send(400, {"error": f"missing field {exc}"})
            except Exception as exc:  # noqa: BLE001
                return self._send(500, {"error": str(exc)})
            self._send(404, {"error": "not found"})

    return Handler


def main() -> None:
    host = os.environ.get("JCR_HOST", "127.0.0.1")
    port = int(os.environ.get("JCR_PORT", "8765"))
    rt = Runtime()
    httpd = ThreadingHTTPServer((host, port), _make_handler(rt))
    if os.environ.get("JCR_VERBOSE"):
        print(f"jcr-daemon listening on http://{host}:{port}  home={rt.cfg.home}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        rt.close()


if __name__ == "__main__":
    main()
