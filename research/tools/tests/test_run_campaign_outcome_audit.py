from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "run_campaign_outcome_audit.py"
SPEC = importlib.util.spec_from_file_location("run_campaign_outcome_audit", MODULE_PATH)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def make_rows(count: int = 200):
    rows = []
    for index in range(count):
        timestamp = index * 900_000
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
    return rows


class CausalControlTests(unittest.TestCase):
    def test_effective_state_uses_only_past_transitions(self):
        reviewed = [
            {"timestamp": 10, "to_state": "EARLY_BUILD", "effective_status": "PASS"},
            {"timestamp": 20, "to_state": "FAILURE", "effective_status": "PASS"},
        ]
        self.assertEqual(audit.effective_state_at(reviewed, 5)[0], "LATENT")
        self.assertEqual(audit.effective_state_at(reviewed, 15)[0], "EARLY_BUILD")
        self.assertEqual(audit.effective_state_at(reviewed, 25)[0], "FAILURE")

    def test_controls_prefer_inactive_states(self):
        rows = make_rows()
        reviewed = [
            {
                "timestamp": 40 * 900_000,
                "from_state": "LATENT",
                "to_state": "EARLY_BUILD",
                "effective_status": "PASS",
            },
            {
                "timestamp": 80 * 900_000,
                "from_state": "EARLY_BUILD",
                "to_state": "FAILURE",
                "effective_status": "PASS",
            },
        ]
        controls = audit.matched_controls(
            rows,
            anchor_timestamp=120 * 900_000,
            reviewed=reviewed,
            max_horizon=240,
            limit=12,
        )
        self.assertTrue(controls)
        self.assertEqual(controls[0]["control_tier"], "CAUSAL_INACTIVE")

    def test_quiet_active_state_is_labeled_fallback(self):
        rows = make_rows()
        reviewed = [
            {
                "timestamp": 0,
                "to_state": "CONTINUATION_RELOAD",
                "effective_status": "PASS",
            }
        ]
        controls = audit.matched_controls(
            rows,
            anchor_timestamp=150 * 900_000,
            reviewed=reviewed,
            max_horizon=240,
            limit=5,
        )
        self.assertTrue(controls)
        self.assertTrue(
            all(control["control_tier"] == "QUIET_NON_TRANSITION_FALLBACK" for control in controls)
        )

    def test_recent_transition_is_not_used_as_control(self):
        rows = make_rows()
        reviewed = [
            {
                "timestamp": 100 * 900_000,
                "to_state": "FAILURE",
                "effective_status": "PASS",
            }
        ]
        controls = audit.matched_controls(
            rows,
            anchor_timestamp=150 * 900_000,
            reviewed=reviewed,
            max_horizon=240,
            limit=20,
        )
        for control in controls:
            if control["timestamp"] >= reviewed[0]["timestamp"]:
                self.assertGreaterEqual(
                    control["timestamp"] - reviewed[0]["timestamp"],
                    240 * audit.BASE.MINUTE_MS,
                )


if __name__ == "__main__":
    unittest.main()
