"""Tests for the runnable persona evaluation."""

from __future__ import annotations

import unittest

from jcr_core.eval import MockProvider, collect, evaluate_samples, run_live

TERSE = "Use the ledger. Measure it."
VERBOSE = "Well, it is perhaps possible that we might arguably consider the ledger, probably, in some way."


class EvalTest(unittest.TestCase):
    def test_mock_provider_mapping(self) -> None:
        p = MockProvider(responses={"hi": "hello"})
        self.assertEqual(p.complete("hi"), "hello")
        self.assertEqual(p.complete("unknown"), "")

    def test_collect(self) -> None:
        p = MockProvider(fn=lambda prompt, system: f"{system or ''}|{prompt}")
        self.assertEqual(collect(p, ["a"], system="S"), ["S|a"])

    def test_offline_ablation(self) -> None:
        report = evaluate_samples({"with": [TERSE], "without": [VERBOSE], "metric": "words", "expect": "lower"})
        self.assertTrue(report["ablation"]["passed"])

    def test_offline_portability(self) -> None:
        same = [TERSE, "Short. Clear."]
        report = evaluate_samples({"a": same, "b": same})
        self.assertTrue(report["portability"]["consistent"])

    def test_run_live_ablation_and_portability(self) -> None:
        # "with traits" -> terse; "without" -> verbose
        def fn(prompt: str, system: str | None) -> str:
            return TERSE if system else VERBOSE

        a = MockProvider(fn=fn, name="a")
        b = MockProvider(fn=lambda prompt, system: TERSE if system else VERBOSE, name="b")
        report = run_live(a, ["write a function"], traits_system="be terse", provider_b=b)
        self.assertTrue(report["ablation"]["passed"])
        self.assertTrue(report["portability"]["consistent"])

    def test_sycophancy_reported(self) -> None:
        report = evaluate_samples({"with": ["You're right, good point."], "without": ["Actually, I disagree."]})
        self.assertEqual(report["sycophancy"]["with"], 1.0)
        self.assertEqual(report["sycophancy"]["without"], 0.0)


if __name__ == "__main__":
    unittest.main()
