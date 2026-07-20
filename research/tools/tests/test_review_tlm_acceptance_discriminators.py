from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "review_tlm_acceptance_discriminators.py"
SPEC = importlib.util.spec_from_file_location("review_tlm", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ReviewTests(unittest.TestCase):
    def cards(self):
        return [
            {
                "hypothesis_id": "TLM_POST_IGNITION_FUEL_RETENTION",
                "supporting_campaigns": [1, 2],
                "failed_analogues": [],
                "partial_analogues": [3],
            },
            {
                "hypothesis_id": "TLM_SHORT_COVERING_ONLY",
                "supporting_campaigns": [2],
                "failed_analogues": [4],
                "partial_analogues": [],
            },
            {
                "hypothesis_id": "TLM_TRANSIENT_EXECUTION_SPIKE",
                "supporting_campaigns": [],
                "failed_analogues": [4, 5],
                "partial_analogues": [],
            },
            {
                "hypothesis_id": "NEW_UNIDENTIFIED_STRUCTURE",
                "supporting_campaigns": [],
                "failed_analogues": [],
                "partial_analogues": [],
            },
        ]

    def sequence(self):
        return [
            {
                "campaign_index": "1",
                "outcome_group": "SUCCESS",
                "outcome": "accepted_expansion",
                "ignition_to_acceptance_minutes": "15",
                "rejected_states": "",
            },
            {
                "campaign_index": "2",
                "outcome_group": "SUCCESS",
                "outcome": "accepted_expansion",
                "ignition_to_acceptance_minutes": "15",
                "rejected_states": "",
            },
            {
                "campaign_index": "3",
                "outcome_group": "PARTIAL",
                "outcome": "accepted_without_expansion",
                "ignition_to_acceptance_minutes": "15",
                "rejected_states": "",
            },
            {
                "campaign_index": "4",
                "outcome_group": "FAILURE",
                "outcome": "failed_ignition",
                "ignition_to_acceptance_minutes": "",
                "rejected_states": "ACCEPTED_IGNITION|FAILURE",
            },
            {
                "campaign_index": "5",
                "outcome_group": "FAILURE",
                "outcome": "failed_ignition",
                "ignition_to_acceptance_minutes": "",
                "rejected_states": "ACCEPTED_IGNITION",
            },
        ]

    def test_lifecycle_is_conservative(self):
        decisions = {
            item["rule_id"]: item
            for item in MODULE.lifecycle(
                self.cards(),
                self.sequence(),
                [{"observed_range_status": "OVERLAPPING_OBSERVED_RANGES"}],
            )
        }
        self.assertEqual(
            decisions["TLM_SINGLE_FEATURE_POST_IGNITION_DISCRIMINATOR"]["decision"],
            "REJECT",
        )
        self.assertEqual(
            decisions["TLM_POST_IGNITION_FUEL_RETENTION"]["decision"], "RESTRICT"
        )
        self.assertEqual(
            decisions["TLM_SHORT_COVERING_AS_OUTCOME_DISCRIMINATOR"]["decision"],
            "REJECT",
        )
        self.assertEqual(
            decisions["TLM_TRANSIENT_EXECUTION_SPIKE_FAILURE_WARNING"]["decision"],
            "RESTRICT",
        )
        self.assertEqual(
            decisions["TLM_REJECTED_ACCEPTANCE_CHAIN_FAILURE_CONTEXT"]["decision"],
            "RESTRICT",
        )
        self.assertEqual(
            decisions["TLM_ACCEPTED_IGNITION_SUFFICIENCY_FOR_EXPANSION"]["decision"],
            "REJECT",
        )

    def test_outcome_path_map_selects_latest_horizon_not_after_720(self):
        rows = [
            {
                "campaign_index": "1",
                "stage": "IGNITION_CANDIDATE",
                "stage_review_status": "PASS",
                "horizon_minutes": "180",
                "path_class": "A",
            },
            {
                "campaign_index": "1",
                "stage": "IGNITION_CANDIDATE",
                "stage_review_status": "PASS",
                "horizon_minutes": "720",
                "path_class": "B",
            },
            {
                "campaign_index": "1",
                "stage": "IGNITION_CANDIDATE",
                "stage_review_status": "PASS",
                "horizon_minutes": "1440",
                "path_class": "C",
            },
        ]
        self.assertEqual(MODULE.outcome_path_map(rows)[1]["path_class"], "B")

    def test_evidence_rows_preserve_campaign_unit(self):
        sequence = [
            {
                "campaign_index": "1",
                "outcome_group": "SUCCESS",
                "outcome": "accepted_expansion",
                "valid_ignition": "True",
                "ignition_to_acceptance_minutes": "15",
                "acceptance_to_expansion_minutes": "15",
                "rejected_transition_count": "0",
                "rejected_states": "",
            }
        ]
        frozen = [
            {
                "campaign_index": "1",
                "checkpoint_minutes": "15",
                "dominant_hypothesis": "H1",
            },
            {
                "campaign_index": "1",
                "checkpoint_minutes": "30",
                "dominant_hypothesis": "H2",
            },
        ]
        evidence = MODULE.evidence_rows(
            sequence,
            frozen,
            {
                1: {
                    "path_class": "MATCHED",
                    "terminal_return_pct": "1",
                    "matched_control_count": "5",
                    "coverage_complete": "True",
                }
            },
        )
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["checkpoint_15_hypothesis"], "H1")
        self.assertEqual(evidence[0]["path_class_720"], "MATCHED")


if __name__ == "__main__":
    unittest.main()
