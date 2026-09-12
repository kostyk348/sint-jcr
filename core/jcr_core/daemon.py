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
POST /observe   {"text": "...", "session": "...", "turn": 0}
POST /remember  {"content": "...", "register": "FACT", "project": "..."}
POST /plan      {"text": "...", "k": 8}
POST /compile   {"text": "...", "budget": 1200, "k": 8}
POST /veto      {"tool": "bash", "args": {...}}
POST /teach     {"statement": "...", "weight": 0.7, "scope": "*", "polarity": 1.0}
POST /events    {"since": 0, "kinds": ["activation"], "limit": 200}
POST /outcome   {"node_ids": [...], "useful": true}

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
                    return self._send(200, rt.outcome(list(b.get("node_ids", [])), bool(b.get("useful", True))))
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
