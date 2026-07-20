from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "build_symbol_campaign.py"
SPEC = importlib.util.spec_from_file_location("build_symbol_campaign", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["build_symbol_campaign"] = MODULE
SPEC.loader.exec_module(MODULE)


class SymbolCampaignTests(unittest.TestCase):
    def test_percentile_rank_is_prior_only(self):
        self.assertIsNone(MODULE.percentile_rank(5, [1, 2, 3]))
        history = list(range(30))
        self.assertGreater(MODULE.percentile_rank(29, history), 0.9)

    def test_split_primary_on_gap(self):
        rows = [
            {"timeframe": "15m", "timestamp": 0},
            {"timeframe": "15m", "timestamp": MODULE.TF_MS["15m"]},
            {"timeframe": "15m", "timestamp": 10 * MODULE.TF_MS["15m"]},
        ]
        groups = MODULE.split_primary(rows)
        self.assertEqual(len(groups), 2)

    def test_higher_timeframe_close_guard(self):
        rows = [
            {"timeframe": "1h", "timestamp": 0, "close_time": 3_599_999},
            {"timeframe": "1h", "timestamp": 3_600_000, "close_time": 7_199_999},
        ]
        self.assertIsNone(MODULE.latest_closed(rows, "1h", 3_000_000))
        self.assertEqual(MODULE.latest_closed(rows, "1h", 4_000_000)["timestamp"], 0)

    def test_adversarial_rejects_negative_acceptance(self):
        item = {
            "to_state": "ACCEPTED_IGNITION",
            "facts_added": ["negative_price_dislocation"],
            "supporting_score": 2,
        }
        reviewed = MODULE.adversarial_review(item, {})
        self.assertEqual(reviewed["adversarial_status"], "REJECT")


if __name__ == "__main__":
    unittest.main()
