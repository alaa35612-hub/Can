from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "review_hypothesis_blind_replay.py"
SPEC = importlib.util.spec_from_file_location("review_hypothesis_blind_replay", MODULE_PATH)
assert SPEC and SPEC.loader
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class CampaignUnitReviewTests(unittest.TestCase):
    def test_repeated_rejected_anchors_count_as_one_campaign(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            replay = root / "replay"
            mechanism = root / "mechanism"
            symbol = "ESPORTSUSDT"
            destination = replay / symbol
            destination.mkdir(parents=True)
            (destination / "HYPOTHESIS_REPLAY_SUMMARY.json").write_text(
                json.dumps(
                    {
                        "rule_id": "ESPORTS_DEEP_RESET_CYCLE_CONTEXT",
                        "hypothesis_statement": "test",
                        "blind_replay_result": "INCONCLUSIVE_DIRECTIONAL_EVIDENCE",
                    }
                ),
                encoding="utf-8",
            )
            write_csv(
                destination / "FROZEN_CAMPAIGN_CONTEXT_ASSESSMENTS.csv",
                [
                    {"campaign_index": 1, "assessment_status": "FULL_HYPOTHESIS_CONTEXT"},
                    {"campaign_index": 2, "assessment_status": "FULL_HYPOTHESIS_CONTEXT"},
                    {"campaign_index": 3, "assessment_status": "HYPOTHESIS_CONTEXT_NOT_SUPPORTED"},
                    {"campaign_index": 4, "assessment_status": "HYPOTHESIS_CONTEXT_NOT_SUPPORTED"},
                ],
            )
            write_csv(
                destination / "FROZEN_REJECTED_CONTEXT_CONTROLS.csv",
                [
                    {"campaign_index": 5, "assessment_status": "PARTIAL_HYPOTHESIS_CONTEXT"},
                    {"campaign_index": 5, "assessment_status": "PARTIAL_HYPOTHESIS_CONTEXT"},
                    {"campaign_index": 5, "assessment_status": "PARTIAL_HYPOTHESIS_CONTEXT"},
                ],
            )
            write_csv(
                mechanism / symbol / "CAMPAIGN_MECHANISM_METRICS.csv",
                [
                    {"campaign_index": 1, "profile_outcome": "accepted_expansion"},
                    {"campaign_index": 2, "profile_outcome": "accepted_expansion"},
                    {"campaign_index": 3, "profile_outcome": "failed_ignition"},
                    {"campaign_index": 4, "profile_outcome": "failed_ignition"},
                    {"campaign_index": 5, "profile_outcome": "failed_ignition"},
                ],
            )
            result = REVIEW.review_symbol(symbol, replay, mechanism)
            self.assertEqual(result["rejected_evaluable_campaign_count"], 1)
            self.assertEqual(result["rejected_full_context_campaign_indices"], [])
            self.assertEqual(result["reviewed_result"], "DIRECTIONAL_FULL_CONTEXT_SUBTYPE_SUPPORT")
            self.assertEqual(result["lifecycle_decision"], "RESTRICT")

    def test_partial_context_does_not_fulfill_joint_hypothesis(self):
        statuses = REVIEW.unique_campaign_statuses(
            [
                {"campaign_index": "1", "assessment_status": "PARTIAL_HYPOTHESIS_CONTEXT"},
                {"campaign_index": "1", "assessment_status": "PARTIAL_HYPOTHESIS_CONTEXT"},
            ]
        )
        self.assertNotIn(REVIEW.FULL_CONTEXT, statuses[1])

    def test_bank_remains_hypothesis_with_one_evaluable_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            replay = root / "replay"
            mechanism = root / "mechanism"
            symbol = "BANKUSDT"
            destination = replay / symbol
            destination.mkdir(parents=True)
            (destination / "HYPOTHESIS_REPLAY_SUMMARY.json").write_text(
                json.dumps(
                    {
                        "rule_id": "BANK_LONG_REBUILD_DEEP_RESET_CONTEXT",
                        "hypothesis_statement": "test",
                        "blind_replay_result": "INSUFFICIENT_OUTCOME_SAMPLE",
                    }
                ),
                encoding="utf-8",
            )
            write_csv(
                destination / "FROZEN_CAMPAIGN_CONTEXT_ASSESSMENTS.csv",
                [{"campaign_index": 4, "assessment_status": "FULL_HYPOTHESIS_CONTEXT"}],
            )
            write_csv(destination / "FROZEN_REJECTED_CONTEXT_CONTROLS.csv", [])
            write_csv(
                mechanism / symbol / "CAMPAIGN_MECHANISM_METRICS.csv",
                [{"campaign_index": 4, "profile_outcome": "accepted_expansion"}],
            )
            result = REVIEW.review_symbol(symbol, replay, mechanism)
            self.assertEqual(result["reviewed_result"], "INSUFFICIENT_OUTCOME_SAMPLE")
            self.assertEqual(result["lifecycle_decision"], "KEEP_AS_HYPOTHESIS")


if __name__ == "__main__":
    unittest.main()
