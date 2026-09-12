"""Cache ledger — measure the harness's prompt-cache behaviour.

Prefix caching is the difference between an affordable harness and an expensive
one. The rule is simple and unforgiving: **the prefix must be byte-stable**; only
the tail may change. This module records the host's real cache token counts so the
claim "we are cache-friendly" is a measured number, not a hope.

`hit_rate = cache_read / (input + cache_read + cache_write)`
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_turns (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    input       INTEGER NOT NULL,
    output      INTEGER NOT NULL,
    cache_read  INTEGER NOT NULL,
    cache_write INTEGER NOT NULL
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


class CacheLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(self, input_tokens: int, output_tokens: int, cache_read: int, cache_write: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO cache_turns (ts, input, output, cache_read, cache_write) VALUES (?,?,?,?,?)",
                (_now(), int(input_tokens), int(output_tokens), int(cache_read), int(cache_write)),
            )
            self._conn.commit()

    @staticmethod
    def _rate(r: sqlite3.Row) -> float:
        prompt = r["input"] + r["cache_read"] + r["cache_write"]
        return (r["cache_read"] / prompt) if prompt > 0 else 0.0

    def stats(self) -> dict:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM cache_turns ORDER BY seq").fetchall()
        if not rows:
            return {"turns": 0, "hit_rate": None, "last_hit_rate": None, "worst_hit_rate": None,
                    "prompt_tokens": 0, "cache_read_tokens": 0}
        total_prompt = sum(r["input"] + r["cache_read"] + r["cache_write"] for r in rows)
        total_read = sum(r["cache_read"] for r in rows)
        rates = [self._rate(r) for r in rows]
        return {
            "turns": len(rows),
            "hit_rate": round(total_read / total_prompt, 4) if total_prompt else None,
            "last_hit_rate": round(rates[-1], 4),
            "worst_hit_rate": round(min(rates), 4),
            "mean_hit_rate": round(sum(rates) / len(rates), 4),
            "prompt_tokens": total_prompt,
            "cache_read_tokens": total_read,
            "cache_write_tokens": sum(r["cache_write"] for r in rows),
            "uncached_input_tokens": sum(r["input"] for r in rows),
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
