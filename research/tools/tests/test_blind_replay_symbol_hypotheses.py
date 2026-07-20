from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "blind_replay_symbol_hypotheses.py"
SPEC = importlib.util.spec_from_file_location("blind_replay_symbol_hypotheses", MODULE_PATH)
assert SPEC and SPEC.loader
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


def campaign(index: int, birth: int, ignition: int, end: int, age: float, price: float | None, oi: float | None, outcome: str):
    return {
        "symbol": "BANKUSDT",
        "campaign_index": index,
        "birth_timestamp": birth,
        "ignition_timestamp": ignition,
        "end_timestamp": end,
        "age_at_ignition_minutes": age,
        "price_reset_magnitude_pct": price,
        "oi_reset_magnitude_pct": oi,
        "profile_outcome": outcome,
        "leading_mechanism": "TEST",
    }


class BlindReplayTests(unittest.TestCase):
    def test_reset_magnitude_does_not_treat_positive_depth_as_drawdown(self):
        self.assertEqual(REPLAY.reset_magnitude(-12.5), 12.5)
        self.assertEqual(REPLAY.reset_magnitude(3.0), 0.0)
        self.assertIsNone(REPLAY.reset_magnitude(None))

    def test_completed_prior_campaigns_excludes_future_and_current(self):
        rows = [
            campaign(1, 0, 10, 20, 10, 1, 1, "failed_ignition"),
            campaign(2, 30, 40, 50, 10, 2, 2, "failed_ignition"),
            campaign(3, 60, 70, 80, 10, 3, 3, "accepted_expansion"),
        ]
        prior = REPLAY.completed_prior_campaigns(rows, 70, 3)
        self.assertEqual([item["campaign_index"] for item in prior], [1, 2])

    def test_assessment_abstains_without_two_prior_comparables(self):
        rows = [
            campaign(1, 0, 10, 20, 10, 1, 1, "failed_ignition"),
            campaign(2, 30, 40, 50, 20, 2, 2, "accepted_expansion"),
        ]
        result = REPLAY.assess_context(rows, rows[1], 40, 20)
        self.assertEqual(result["assessment_status"], "ABSTAIN_INSUFFICIENT_PRIOR_HISTORY")

    def test_full_context_uses_only_completed_prior_medians(self):
        rows = [
            campaign(1, 0, 10, 20, 10, 1, 1, "failed_ignition"),
            campaign(2, 30, 40, 50, 20, 2, 2, "failed_ignition"),
            campaign(3, 60, 70, 80, 100, 10, 10, "accepted_expansion"),
            campaign(4, 90, 100, 110, 1, 100, 100, "accepted_expansion"),
        ]
        result = REPLAY.assess_context(rows, rows[2], 70, 100)
        self.assertEqual(result["assessment_status"], "FULL_HYPOTHESIS_CONTEXT")
        self.assertEqual(result["prior_campaign_indices"], [1, 2])
        self.assertEqual(result["causal_baselines"]["age"]["median"], 15)

    def test_outcome_is_revealed_after_frozen_assessment(self):
        rows = [
            campaign(1, 0, 10, 20, 10, 1, 1, "failed_ignition"),
            campaign(2, 30, 40, 50, 20, 2, 2, "failed_ignition"),
            campaign(3, 60, 70, 80, 100, 10, 10, "accepted_expansion"),
        ]
        frozen, trace = REPLAY.campaign_assessment_records("BANKUSDT", rows)
        target_frozen = next(item for item in frozen if item["campaign_index"] == 3)
        target_trace = [item for item in trace if item["campaign_index"] == 3]
        self.assertTrue(target_frozen["outcome_hidden"])
        self.assertNotIn("revealed_profile_outcome", target_frozen)
        self.assertEqual(target_trace[0]["record_type"], "CAMPAIGN_IGNITION_CONTEXT")
        self.assertEqual(target_trace[1]["record_type"], "CAMPAIGN_OUTCOME_REVEALED")
        self.assertFalse(target_trace[1]["outcome_hidden"])
        self.assertFalse(target_trace[1]["historical_assessment_rewritten"])

    def test_one_success_is_never_promoted(self):
        rows = [
            campaign(1, 0, 10, 20, 10, 1, 1, "failed_ignition"),
            campaign(2, 30, 40, 50, 20, 2, 2, "failed_ignition"),
            campaign(3, 60, 70, 80, 100, 10, 10, "accepted_expansion"),
        ]
        frozen, _ = REPLAY.campaign_assessment_records("BANKUSDT", rows)
        summary = REPLAY.summarize_symbol("BANKUSDT", rows, frozen, [])
        self.assertEqual(summary["blind_replay_result"], "INSUFFICIENT_OUTCOME_SAMPLE")
        self.assertEqual(summary["lifecycle_decision"], "KEEP_AS_HYPOTHESIS")


if __name__ == "__main__":
    unittest.main()
