from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_campaign_outcomes.py"
SPEC = importlib.util.spec_from_file_location("audit_campaign_outcomes", MODULE_PATH)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def make_rows(count: int = 120, gap_after: int | None = None):
    rows = []
    timestamp = 0
    for index in range(count):
        if gap_after is not None and index == gap_after:
            timestamp += 5 * 900_000
        rows.append(
            {
                "timestamp": timestamp,
                "close_time": timestamp + 899_999,
                "close": 100.0 + index * 0.1,
                "price_change_pct": 0.1,
                "price_abs_rank": 0.2,
                "number_of_trades_rank": 0.2,
                "quote_volume_rank": 0.2,
                "oi_rank": 0.2,
                "number_of_trades_rz": 0.5,
                "quote_volume_rz": 0.5,
                "oi_rz": 0.5,
                "oi_change_pct": 0.1,
                "quote_volume": 1000.0 + index,
            }
        )
        timestamp += 900_000
    return rows


class OutcomeAuditTests(unittest.TestCase):
    def test_path_metrics_use_only_future_rows(self):
        rows = make_rows()
        result = audit.path_metrics(rows, 10 * 900_000, 60)
        self.assertEqual(result["future_rows"], 4)
        self.assertEqual(result["first_positive_minutes"], 15)
        self.assertTrue(result["coverage_complete"])

    def test_path_metrics_stop_at_observation_gap(self):
        rows = make_rows(gap_after=13)
        result = audit.path_metrics(rows, 10 * 900_000, 240)
        self.assertTrue(result["gap_truncated"])
        self.assertFalse(result["coverage_complete"])
        self.assertLess(result["future_rows"], 16)

    def test_rejected_transition_is_not_an_anchor(self):
        reviewed = audit.PROFILE.effective_review(
            [
                {"timestamp": 1, "time": "1970-01-01T00:00:00.001000+00:00", "from_state": "LATENT", "to_state": "EARLY_BUILD", "adversarial_status": "PASS"},
                {"timestamp": 2, "time": "1970-01-01T00:00:00.002000+00:00", "from_state": "EARLY_BUILD", "to_state": "IGNITION_CANDIDATE", "adversarial_status": "PASS"},
                {"timestamp": 3, "time": "1970-01-01T00:00:00.003000+00:00", "from_state": "IGNITION_CANDIDATE", "to_state": "ACCEPTED_IGNITION", "adversarial_status": "REJECT"},
                {"timestamp": 4, "time": "1970-01-01T00:00:00.004000+00:00", "from_state": "ACCEPTED_IGNITION", "to_state": "EXPANSION", "adversarial_status": "PASS"},
            ]
        )
        campaign = {
            "start": "1970-01-01T00:00:00+00:00",
            "end": "1970-01-01T00:00:01+00:00",
        }
        stages = [item["to_state"] for item in audit.stage_anchors(reviewed, campaign)]
        self.assertEqual(stages, ["EARLY_BUILD", "IGNITION_CANDIDATE"])

    def test_matched_controls_exclude_campaign_neighborhood(self):
        rows = make_rows(200)
        anchor = 100 * 900_000
        campaign = [(95 * 900_000, 105 * 900_000)]
        controls = audit.matched_controls(rows, anchor, campaign, 240, limit=12)
        self.assertTrue(controls)
        for control in controls:
            self.assertTrue(audit.outside_campaigns(control["timestamp"], campaign))

    def test_incomplete_path_is_not_classified_as_success(self):
        metrics = {
            "coverage_complete": False,
            "terminal_return_pct": 10.0,
            "mfe_close_pct": 12.0,
            "mae_close_pct": -1.0,
        }
        label, ranks = audit.classify_path(metrics, [])
        self.assertEqual(label, "INCOMPLETE_FORWARD_COVERAGE")
        self.assertIsNone(ranks["terminal_percentile"])

    def test_adaptive_horizons_use_symbol_lag(self):
        horizons = audit.adaptive_horizons({"execution_to_price_lag_minutes": {"median": 45}})
        self.assertIn(45, horizons)
        self.assertIn(180, horizons)
        self.assertIn(720, horizons)


if __name__ == "__main__":
    unittest.main()
