from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "review_esports_subtype_oos.py"
SPEC = importlib.util.spec_from_file_location("review_esports_subtype_oos", MODULE_PATH)
assert SPEC and SPEC.loader
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


class ReviewDecisionTests(unittest.TestCase):
    def test_abstention_is_not_counted_as_failure(self) -> None:
        records = [
            {
                "symbol": "MAGMAUSDT",
                "campaign_index": 1,
                "assessment_status": "ABSTAIN_MISSING_CURRENT_CONTEXT",
                "outcome_group": "FAILURE",
                "path_class": "NEGATIVE_PATH_OUTLIER",
            }
        ]
        findings = REVIEW.reviewed_findings(records)
        self.assertEqual(findings["evaluable_campaigns"], 0)
        self.assertEqual(findings["full_context_failure_campaigns"], [])
        self.assertEqual(findings["abstained_only_symbols"], ["MAGMAUSDT"])

    def test_full_context_failure_rejects_sufficiency(self) -> None:
        records = [
            {
                "symbol": "TLMUSDT",
                "campaign_index": 11,
                "assessment_status": REVIEW.FULL_CONTEXT,
                "outcome_group": REVIEW.FAILURE,
                "path_class": "MATCHED_CONTROL_LIKE",
                "terminal_return_pct": 2.1,
                "rejected_transition_count": "3",
            }
        ]
        findings = REVIEW.reviewed_findings(records)
        self.assertEqual(findings["sufficiency_claim"]["decision"], "REJECT")
        self.assertEqual(findings["association_result"], "INSUFFICIENT_INDEPENDENT_SYMBOL_SAMPLE")

    def test_nonfull_success_rejects_necessity(self) -> None:
        records = [
            {
                "symbol": "TLMUSDT",
                "campaign_index": 13,
                "assessment_status": "PARTIAL_TRANSFER_CONTEXT",
                "outcome_group": REVIEW.SUCCESS,
                "path_class": "POSITIVE_PATH_OUTLIER",
            }
        ]
        findings = REVIEW.reviewed_findings(records)
        self.assertEqual(findings["necessity_claim"]["decision"], "REJECT")

    def test_source_rule_is_not_rewritten_by_external_counterexample(self) -> None:
        records = [
            {
                "symbol": "TLMUSDT",
                "campaign_index": 11,
                "assessment_status": REVIEW.FULL_CONTEXT,
                "outcome_group": REVIEW.FAILURE,
                "path_class": "MATCHED_CONTROL_LIKE",
                "terminal_return_pct": 2.1,
                "rejected_transition_count": "3",
            }
        ]
        findings = REVIEW.reviewed_findings(records)
        self.assertEqual(
            findings["source_rule"]["decision"],
            "KEEP_AS_ESPORTS_SPECIFIC_HYPOTHESIS",
        )
        self.assertTrue(findings["promotion_prohibited"])


if __name__ == "__main__":
    unittest.main()
