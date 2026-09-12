"""Tests for the synchronicity monitor (3-condition filter + calibration)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jcr_core.config import JCRConfig
from jcr_core.ledger import LibidoLedger
from jcr_core.monitor import SynchronicityMonitor, archetypes_in


class ArchetypeTest(unittest.TestCase):
    def test_detects_patterns(self) -> None:
        self.assertIn("cycle", archetypes_in("retry the loop"))
        self.assertIn("guard", archetypes_in("add an invariant check"))
        self.assertEqual(archetypes_in("alpha beta gamma"), set())


class MonitorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.cfg = JCRConfig(embed_dim=256, home=base)
        self.ledger = LibidoLedger(base / "ledger.db", self.cfg)
        self.mon = SynchronicityMonitor(self.ledger, self.cfg, db_path=base / "monitor.db", d_min=0.5, s_min=0.15)

        self.far = self.ledger.add_node("retry the loop until it converges", project="other")
        self.same_project = self.ledger.add_node("retry the loop until it converges", project="jcr")
        self.recent = self.ledger.add_node("retry the loop until it converges", project="other")
        self.ledger.touch(self.recent.id)
        self.no_arch = self.ledger.add_node("alpha converge gamma", project="other")

    def tearDown(self) -> None:
        self.mon.close()
        self.ledger.close()
        self.tmp.cleanup()

    def test_only_all_three_conditions_cross(self) -> None:
        crossings = self.mon.scan("alpha retry loop converge", project="jcr")
        ids = {c.node_id for c in crossings}
        self.assertIn(self.far.id, ids)          # distant + cross-domain + archetype
        self.assertNotIn(self.same_project.id, ids)  # condition 2 fails
        self.assertNotIn(self.recent.id, ids)        # condition 1 fails
        self.assertNotIn(self.no_arch.id, ids)       # condition 3 fails

    def test_no_archetype_in_buffer_means_no_scan(self) -> None:
        self.assertEqual(self.mon.scan("alpha beta gamma", project="jcr"), [])

    def test_crossing_raises_priority(self) -> None:
        before_node = self.ledger.get_node(self.far.id)
        assert before_node is not None
        before = before_node.energy
        self.mon.scan("alpha retry loop converge", project="jcr")
        after_node = self.ledger.get_node(self.far.id)
        assert after_node is not None
        self.assertGreater(after_node.energy, before)

    def test_calibration_and_hard_gate(self) -> None:
        c = self.mon.scan("alpha retry loop converge", project="jcr")[0]
        self.assertIsNone(self.mon.precision())
        self.mon.label(c.id, True)
        self.mon.label(c.id, True)
        self.assertEqual(self.mon.precision(), 1.0)
        self.assertFalse(self.mon.may_inject())  # soft by default
        self.mon.hard = True
        self.assertTrue(self.mon.may_inject())
        self.mon.label(c.id, False)
        p = self.mon.precision()
        assert p is not None
        self.assertLess(p, 1.0)

    def test_status_shape(self) -> None:
        self.mon.scan("alpha retry loop converge", project="jcr")
        s = self.mon.status()
        self.assertIn("precision", s)
        self.assertIn("thresholds", s)


if __name__ == "__main__":
    unittest.main()
