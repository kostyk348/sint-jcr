"""Tests for cache telemetry (prompt-cache hit rate)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.cache import CacheLedger


class CacheLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.c = CacheLedger(Path(self.tmp.name) / "cache.db")

    def tearDown(self) -> None:
        self.c.close()
        self.tmp.cleanup()

    def test_empty(self) -> None:
        self.assertEqual(self.c.stats()["turns"], 0)
        self.assertIsNone(self.c.stats()["hit_rate"])

    def test_hit_rate_math(self) -> None:
        # 9800 read from cache, 200 uncached input -> 9800/10000 = 0.98
        self.c.record(input_tokens=200, output_tokens=50, cache_read=9800, cache_write=0)
        s = self.c.stats()
        self.assertEqual(s["turns"], 1)
        self.assertAlmostEqual(s["hit_rate"], 0.98, places=4)
        self.assertAlmostEqual(s["last_hit_rate"], 0.98, places=4)

    def test_aggregate_and_worst(self) -> None:
        self.c.record(200, 10, 9800, 0)   # 0.98
        self.c.record(5000, 10, 5000, 0)  # 0.50
        s = self.c.stats()
        self.assertAlmostEqual(s["worst_hit_rate"], 0.50, places=4)
        self.assertAlmostEqual(s["hit_rate"], 14800 / 20000, places=4)
        self.assertEqual(s["uncached_input_tokens"], 5200)

    def test_cache_write_counts_in_prompt(self) -> None:
        self.c.record(0, 0, 0, 1000)  # first turn: all write, no read
        s = self.c.stats()
        self.assertEqual(s["hit_rate"], 0.0)
        self.assertEqual(s["cache_write_tokens"], 1000)


if __name__ == "__main__":
    unittest.main()
