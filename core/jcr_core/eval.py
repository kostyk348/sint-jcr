"""Runnable persona evaluation (falsification harness).

Consumes recorded samples *or* calls a provider, then renders the verdicts from
``falsify.py``. Two modes:

* offline — ``--samples samples.json`` with recorded outputs;
* live    — an OpenAI-compatible endpoint (``--base-url``/``--model``), running
  the same task with and without the trait block (ablation) and optionally on a
  second provider (portability).

Zero dependencies: the HTTP provider uses ``urllib``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol

from jcr_core.falsify import (
    ablation_delta,
    aggregate,
    portability_consistency,
    sycophancy_rate,
)


class Provider(Protocol):
    name: str

    def complete(self, prompt: str, system: str | None = None) -> str:  # pragma: no cover
        ...


@dataclass
class MockProvider:
    """Deterministic provider for tests and dry runs."""

    responses: dict[str, str] | None = None
    fn: Callable[[str, str | None], str] | None = None
    name: str = "mock"

    def complete(self, prompt: str, system: str | None = None) -> str:
        if self.fn:
            return self.fn(prompt, system)
        return (self.responses or {}).get(prompt, "")


@dataclass
class HttpProvider:
    """Minimal OpenAI-compatible chat provider."""

    base_url: str
    model: str
    api_key: str = ""
    name: str = "http"
    timeout: float = 60.0

    def complete(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({"model": self.model, "messages": messages, "temperature": 0.7}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def collect(provider: Provider, prompts: list[str], system: str | None = None) -> list[str]:
    return [provider.complete(p, system) for p in prompts]


def evaluate_samples(samples: dict) -> dict:
    """Offline evaluation from recorded samples.

    Expected shape::

        {
          "metric": "words", "expect": "lower",
          "with": ["..."], "without": ["..."],
          "a": ["..."], "b": ["..."]        # optional, for portability
        }
    """
    metric = samples.get("metric", "words")
    expect = samples.get("expect", "lower")
    report: dict = {}
    if samples.get("with") and samples.get("without"):
        report["ablation"] = ablation_delta(samples["with"], samples["without"], metric=metric, expect=expect)
        report["sycophancy"] = {
            "with": sycophancy_rate(samples["with"]),
            "without": sycophancy_rate(samples["without"]),
        }
    if samples.get("a") and samples.get("b"):
        report["portability"] = portability_consistency(aggregate(samples["a"]), aggregate(samples["b"]))
    return report


def run_live(
    provider: Provider,
    prompts: list[str],
    traits_system: str,
    provider_b: Provider | None = None,
    metric: str = "words",
    expect: str = "lower",
) -> dict:
    with_traits = collect(provider, prompts, system=traits_system)
    without_traits = collect(provider, prompts, system=None)
    report: dict = {
        "provider": provider.name,
        "ablation": ablation_delta(with_traits, without_traits, metric=metric, expect=expect),
        "sycophancy": {"with": sycophancy_rate(with_traits), "without": sycophancy_rate(without_traits)},
    }
    if provider_b is not None:
        b = collect(provider_b, prompts, system=traits_system)
        report["portability"] = portability_consistency(aggregate(with_traits), aggregate(b))
        report["provider_b"] = provider_b.name
    return report


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="JCR persona falsification harness")
    ap.add_argument("--samples", help="recorded samples JSON (offline mode)")
    ap.add_argument("--base-url", help="OpenAI-compatible base URL (live mode)")
    ap.add_argument("--model", help="model id for live mode")
    ap.add_argument("--api-key", default=os.environ.get("JCR_EVAL_API_KEY", ""))
    ap.add_argument("--base-url-b", help="second provider base URL (portability)")
    ap.add_argument("--model-b", default="")
    ap.add_argument("--prompts", help="JSON file with a list of prompts")
    ap.add_argument("--traits", default="", help="trait block (system) to ablate, or @file")
    ap.add_argument("--metric", default="words")
    ap.add_argument("--expect", default="lower", choices=["lower", "higher"])
    args = ap.parse_args(argv)

    if args.samples:
        print(json.dumps(evaluate_samples(_load_json(args.samples)), indent=2))
        return 0

    if not (args.base_url and args.model and args.prompts):
        ap.error("live mode needs --base-url, --model and --prompts")
        return 2

    loaded = _load_json(args.prompts)
    prompts = loaded if isinstance(loaded, list) else []
    traits = args.traits
    if traits.startswith("@"):
        with open(traits[1:], "r", encoding="utf-8") as fh:
            traits = fh.read()
    provider = HttpProvider(args.base_url, args.model, args.api_key)
    provider_b = HttpProvider(args.base_url_b, args.model_b, args.api_key, name="http-b") if args.base_url_b and args.model_b else None
    print(json.dumps(run_live(provider, prompts, traits, provider_b, args.metric, args.expect), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
