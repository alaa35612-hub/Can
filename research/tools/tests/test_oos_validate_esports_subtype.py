from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "oos_validate_esports_subtype.py"
SPEC = importlib.util.spec_from_file_location("oos_validate_esports_subtype", MODULE_PATH)
assert SPEC and SPEC.loader
OOS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OOS)


class CohortSelectionTests(unittest.TestCase):
    def test_selection_is_quality_and_coverage_based(self) -> None:
        rows = [
            {
                "symbol": "AKEUSDT", "15m": "6", "1h": "2", "4h": "2", "1d": "2",
                "total": "14", "high_quality": "14", "medium_quality": "0", "low_quality": "0", "unusable": "0",
            },
            {
                "symbol": "VELVETUSDT", "15m": "7", "1h": "2", "4h": "2", "1d": "2",
                "total": "13", "high_quality": "13", "medium_quality": "0", "low_quality": "0", "unusable": "0",
            },
            {
                "symbol": "FOGOUSDT", "15m": "2", "1h": "0", "4h": "2", "1d": "0",
                "total": "4", "high_quality": "4", "medium_quality": "0", "low_quality": "0", "unusable": "0",
            },
            {
                "symbol": "TACUSDT", "15m": "5", "1h": "0", "4h": "0", "1d": "0",
                "total": "7", "high_quality": "6", "medium_quality": "1", "low_quality": "0", "unusable": "0",
            },
        ]
        self.assertEqual(OOS.select_eligible_symbols(rows), ["VELVETUSDT"])


class FrozenAssessmentTests(unittest.TestCase):
    @staticmethod
    def campaign(index: int, age: float, price_depth: float, oi_depth: float) -> dict:
        return {
            "campaign_index": index,
            "birth_to_ignition_minutes": age,
            "price_reset_depth_pct": price_depth,
            "oi_reset_depth_pct": oi_depth,
        }

    def test_full_context_requires_all_three_components(self) -> None:
        prior = [
            self.campaign(1, 100, -2, -1),
            self.campaign(2, 200, -4, -3),
        ]
        current = self.campaign(3, 300, -8, -6)
        result = OOS.assess_campaign_context(current, prior)
        self.assertEqual(result["assessment_status"], OOS.FULL_CONTEXT)
        self.assertEqual(result["comparisons"], {
            "age_minutes": True,
            "price_reset_magnitude_pct": True,
            "oi_reset_magnitude_pct": True,
        })

    def test_partial_context_is_not_full_fulfillment(self) -> None:
        prior = [
            self.campaign(1, 100, -2, -1),
            self.campaign(2, 200, -4, -3),
        ]
        current = self.campaign(3, 300, -1, -6)
        result = OOS.assess_campaign_context(current, prior)
        self.assertEqual(result["assessment_status"], OOS.PARTIAL_CONTEXT)

    def test_insufficient_component_history_abstains(self) -> None:
        prior = [self.campaign(1, 100, -2, -1)]
        current = self.campaign(2, 300, -8, -6)
        result = OOS.assess_campaign_context(current, prior)
        self.assertEqual(result["assessment_status"], "ABSTAIN_INSUFFICIENT_PRIOR_BASELINE")

    def test_missing_reset_context_abstains(self) -> None:
        prior = [
            self.campaign(1, 100, -2, -1),
            self.campaign(2, 200, -4, -3),
        ]
        current = self.campaign(3, 300, None, -6)
        result = OOS.assess_campaign_context(current, prior)
        self.assertEqual(result["assessment_status"], "ABSTAIN_MISSING_CURRENT_CONTEXT")


class AggregateDecisionTests(unittest.TestCase):
    def test_contradiction_overrides_successes(self) -> None:
        summaries = [
            {
                "symbol": "AAAUSDT",
                "evaluable_campaigns": 3,
                "full_context_outcome_counts": {"SUCCESS": 2},
                "full_context_path_class_counts": {"POSITIVE_PATH_OUTLIER": 2},
            },
            {
                "symbol": "BBBUSDT",
                "evaluable_campaigns": 2,
                "full_context_outcome_counts": {"FAILURE": 1},
                "full_context_path_class_counts": {},
            },
        ]
        result = OOS.aggregate_transfer(summaries)
        self.assertEqual(result["transfer_result"], "EXTERNAL_TRANSFER_CONTRADICTION")
        self.assertEqual(result["transfer_decision"], "REJECT_TRANSFER_CLAIM")

    def test_two_symbols_can_only_create_directional_support(self) -> None:
        summaries = [
            {
                "symbol": "AAAUSDT",
                "evaluable_campaigns": 3,
                "full_context_outcome_counts": {"SUCCESS": 1},
                "full_context_path_class_counts": {"POSITIVE_PATH_OUTLIER": 1},
            },
            {
                "symbol": "BBBUSDT",
                "evaluable_campaigns": 3,
                "full_context_outcome_counts": {"SUCCESS": 1},
                "full_context_path_class_counts": {"MATCHED_CONTROL_LIKE": 1},
            },
        ]
        result = OOS.aggregate_transfer(summaries)
        self.assertEqual(result["transfer_result"], "DIRECTIONAL_EXTERNAL_SUPPORT")
        self.assertEqual(result["transfer_decision"], "KEEP_TRANSFER_AS_HYPOTHESIS")
        self.assertTrue(result["promotion_prohibited"])


if __name__ == "__main__":
    unittest.main()
