"""Tests for the LLM critic behind the Shadow protocol."""

from __future__ import annotations

import json
import unittest

from jcr_core.critic import HttpCritic, MockCritic, parse_critiques
from jcr_core.shadow import OracleVerifier, Shadow


class ParseTest(unittest.TestCase):
    def test_parses_json_in_prose(self) -> None:
        text = 'Sure, here:\n[{"claim":"dangerous rm","artifact":"rm -rf /","severity":0.9}]\n'
        cs = parse_critiques(text)
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0].artifact, "rm -rf /")
        self.assertEqual(cs[0].severity, 0.9)

    def test_null_artifact_is_cheap_talk(self) -> None:
        cs = parse_critiques('[{"claim":"looks risky","artifact":null}]')
        self.assertEqual(len(cs), 1)
        self.assertIsNone(cs[0].artifact)

    def test_garbage_returns_empty(self) -> None:
        self.assertEqual(parse_critiques("no json here"), [])
        self.assertEqual(parse_critiques("[not json"), [])


class HttpCriticTest(unittest.TestCase):
    def _transport(self, payload: str):
        def fn(url: str, headers: dict, body: bytes) -> str:
            return json.dumps({"choices": [{"message": {"content": payload}}]})
        return fn

    def test_critic_returns_parsed_critiques(self) -> None:
        payload = '[{"claim":"rm","artifact":"rm -rf /","severity":0.9}]'
        critic = HttpCritic("http://x", "m", transport=self._transport(payload))
        cs = critic.critique("draft")
        self.assertEqual(len(cs), 1)

    def test_shadow_vetoes_only_confirmed_artifacts(self) -> None:
        payload = '[{"claim":"rm","artifact":"rm -rf /","severity":0.9},{"claim":"vague","artifact":null,"severity":0.9}]'
        critic = HttpCritic("http://x", "m", transport=self._transport(payload))
        out = Shadow(critic, OracleVerifier()).review("draft")
        self.assertTrue(out["veto"])
        self.assertEqual(out["cheap_talk"], 1)

    def test_transport_failure_is_silent(self) -> None:
        def boom(url, headers, body):
            raise RuntimeError("network down")
        critic = HttpCritic("http://x", "m", transport=boom)
        self.assertEqual(critic.critique("draft"), [])

    def test_mock_critic(self) -> None:
        from jcr_core.shadow import Critique
        c = MockCritic([Critique("x", "rm -rf /", 0.9)])
        self.assertEqual(len(c.critique("d")), 1)


if __name__ == "__main__":
    unittest.main()
