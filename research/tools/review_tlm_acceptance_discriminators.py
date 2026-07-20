from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def outcome_path_map(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    grouped: dict[int, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for row in rows:
        if row.get("stage") != "IGNITION_CANDIDATE":
            continue
        if row.get("stage_review_status") not in {"PASS", "RESTRICT"}:
            continue
        horizon = int(float(row["horizon_minutes"]))
        if horizon <= 720:
            grouped[int(float(row["campaign_index"]))].append((horizon, row))
    return {campaign: max(values, key=lambda item: item[0])[1] for campaign, values in grouped.items()}


def evidence_rows(
    sequence: list[dict[str, str]],
    frozen: list[dict[str, str]],
    outcomes: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    frozen_by_campaign: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in frozen:
        frozen_by_campaign[int(float(row["campaign_index"]))].append(row)

    output: list[dict[str, Any]] = []
    for sequence_row in sequence:
        campaign_index = int(float(sequence_row["campaign_index"]))
        checkpoint_rows = frozen_by_campaign[campaign_index]
        by_checkpoint = {
            int(float(row["checkpoint_minutes"])): row for row in checkpoint_rows
        }
        outcome = outcomes.get(campaign_index, {})
        output.append(
            {
                "campaign_index": campaign_index,
                "outcome_group": sequence_row.get("outcome_group"),
                "outcome": sequence_row.get("outcome"),
                "valid_ignition": sequence_row.get("valid_ignition"),
                "ignition_to_acceptance_minutes": sequence_row.get(
                    "ignition_to_acceptance_minutes"
                ),
                "acceptance_to_expansion_minutes": sequence_row.get(
                    "acceptance_to_expansion_minutes"
                ),
                "rejected_transition_count": sequence_row.get(
                    "rejected_transition_count"
                ),
                "rejected_states": sequence_row.get("rejected_states"),
                "checkpoint_15_hypothesis": by_checkpoint.get(15, {}).get(
                    "dominant_hypothesis"
                ),
                "checkpoint_30_hypothesis": by_checkpoint.get(30, {}).get(
                    "dominant_hypothesis"
                ),
                "checkpoint_45_hypothesis": by_checkpoint.get(45, {}).get(
                    "dominant_hypothesis"
                ),
                "checkpoint_60_hypothesis": by_checkpoint.get(60, {}).get(
                    "dominant_hypothesis"
                ),
                "path_class_720": outcome.get("path_class"),
                "terminal_return_pct_720": outcome.get("terminal_return_pct"),
                "matched_control_count_720": outcome.get("matched_control_count"),
                "coverage_complete_720": outcome.get("coverage_complete"),
            }
        )
    return output


def lifecycle(
    cards: list[dict[str, Any]],
    sequence: list[dict[str, str]],
    matrix: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_hypothesis = {card["hypothesis_id"]: card for card in cards}
    decisions: list[dict[str, Any]] = []

    non_overlapping = [
        row
        for row in matrix
        if row.get("observed_range_status", "").startswith("NON_OVERLAPPING")
    ]
    decisions.append(
        {
            "rule_id": "TLM_SINGLE_FEATURE_POST_IGNITION_DISCRIMINATOR",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "REJECT",
            "basis": (
                "No tested price, OI, execution, or taker-flow metric produced a "
                "non-overlapping success/failure range at 15, 30, 45, or 60 minutes."
                if not non_overlapping
                else "At least one descriptive range did not overlap, but no threshold was frozen before this sample."
            ),
            "limitations": (
                "Rejects standalone feature sufficiency; ordered multi-feature context remains testable."
            ),
        }
    )

    fuel = by_hypothesis["TLM_POST_IGNITION_FUEL_RETENTION"]
    fuel_successes = len(fuel["supporting_campaigns"])
    fuel_failures = len(fuel["failed_analogues"])
    fuel_restrict = fuel_successes >= 2 and fuel_failures == 0
    decisions.append(
        {
            "rule_id": "TLM_POST_IGNITION_FUEL_RETENTION",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "RESTRICT" if fuel_restrict else "KEEP_AS_HYPOTHESIS",
            "restricted_rule_id": (
                "TLM_EARLY_FUEL_RETENTION_ACCEPTANCE_CONTEXT" if fuel_restrict else None
            ),
            "basis": (
                f"Observed in accepted-expansion campaigns {fuel['supporting_campaigns']}, "
                f"failed analogues {fuel['failed_analogues']}, and accepted-without-expansion "
                f"campaigns {fuel['partial_analogues']}."
            ),
            "limitations": (
                "The accepted-without-expansion case prevents an expansion-sufficiency claim; "
                "campaigns are from one symbol and one observed period."
            ),
        }
    )

    short_covering = by_hypothesis["TLM_SHORT_COVERING_ONLY"]
    mixed_short_covering = bool(
        short_covering["supporting_campaigns"] and short_covering["failed_analogues"]
    )
    decisions.append(
        {
            "rule_id": "TLM_SHORT_COVERING_AS_OUTCOME_DISCRIMINATOR",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "REJECT" if mixed_short_covering else "KEEP_AS_HYPOTHESIS",
            "basis": (
                f"Accepted-expansion analogues {short_covering['supporting_campaigns']} and "
                f"failed analogues {short_covering['failed_analogues']} share the same "
                "short-covering context."
            ),
            "limitations": (
                "Short covering may describe a mechanism, but it does not discriminate "
                "acceptance from failure in this sample."
            ),
        }
    )

    transient = by_hypothesis["TLM_TRANSIENT_EXECUTION_SPIKE"]
    transient_restrict = (
        len(transient["failed_analogues"]) >= 2
        and len(transient["supporting_campaigns"]) == 0
    )
    decisions.append(
        {
            "rule_id": "TLM_TRANSIENT_EXECUTION_SPIKE_FAILURE_WARNING",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "RESTRICT" if transient_restrict else "KEEP_AS_HYPOTHESIS",
            "restricted_rule_id": (
                "TLM_EARLY_TRANSIENT_SPIKE_WARNING" if transient_restrict else None
            ),
            "basis": (
                f"Failed analogues {transient['failed_analogues']}; accepted-expansion "
                f"analogues {transient['supporting_campaigns']}."
            ),
            "limitations": (
                "Not necessary for failure: several failed campaigns used other paths or "
                "lacked an evaluable prior baseline."
            ),
        }
    )

    rejected_acceptance = [
        row
        for row in sequence
        if "ACCEPTED_IGNITION" in (row.get("rejected_states") or "").split("|")
    ]
    rejected_counts = Counter(row.get("outcome_group") for row in rejected_acceptance)
    rejected_restrict = (
        rejected_counts.get("FAILURE", 0) >= 2
        and rejected_counts.get("SUCCESS", 0) == 0
        and rejected_counts.get("PARTIAL", 0) == 0
    )
    decisions.append(
        {
            "rule_id": "TLM_REJECTED_ACCEPTANCE_CHAIN_FAILURE_CONTEXT",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "RESTRICT" if rejected_restrict else "KEEP_AS_HYPOTHESIS",
            "restricted_rule_id": (
                "TLM_NEGATIVE_DISLOCATION_ACCEPTANCE_REJECTION_WARNING"
                if rejected_restrict
                else None
            ),
            "basis": f"Rejected acceptance chains by outcome: {dict(rejected_counts)}.",
            "limitations": (
                "A rejection chain is not necessary for failure; fast failures also occur "
                "without an acceptance proposal."
            ),
        }
    )

    accepted_without_expansion = [
        row
        for row in sequence
        if row.get("outcome_group") == "PARTIAL"
        and row.get("ignition_to_acceptance_minutes") not in {"", None}
    ]
    decisions.append(
        {
            "rule_id": "TLM_ACCEPTED_IGNITION_SUFFICIENCY_FOR_EXPANSION",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "REJECT" if accepted_without_expansion else "KEEP_AS_HYPOTHESIS",
            "basis": (
                "Accepted-without-expansion campaigns: "
                f"{[int(float(row['campaign_index'])) for row in accepted_without_expansion]}."
            ),
            "limitations": (
                "Accepted ignition remains a state observation, not a guaranteed expansion outcome."
            ),
        }
    )
    return decisions


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render(findings: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    decision_rows = "\n".join(
        f"| {item['rule_id']} | {item['decision']} | {item['basis']} | {item['limitations']} |"
        for item in decisions
    )
    return f"""# TLMUSDT Acceptance Discriminators — Human Review

## Effective evidence

- Campaigns reviewed: {findings['campaigns_reviewed']}
- Accepted expansion: {findings['accepted_expansion']}
- Accepted without expansion: {findings['accepted_without_expansion']}
- Failed ignition: {findings['failed_ignition']}
- Continuous metrics with non-overlapping observed success/failure ranges: {findings['non_overlapping_metric_count']}
- Fuel-retention campaigns: {findings['fuel_retention_campaigns']}
- Transient-spike campaigns: {findings['transient_spike_campaigns']}
- Rejected-acceptance-chain campaigns: {findings['rejected_acceptance_campaigns']}

## Rule lifecycle

| Rule | Decision | Evidence basis | Limitations |
|---|---|---|---|
{decision_rows}

## Interpretation boundary

- All decisions are TLM-specific.
- `RESTRICT` creates a narrower research hypothesis, not a production signal.
- Structural outcome, nominal forward return, and matched-control path class remain separate.
- No result is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("research/tlm_acceptance_discriminators"),
    )
    parser.add_argument(
        "--outcome-file",
        type=Path,
        default=Path(
            "research/oos_validation/esports_subtype/outcome_audits/"
            "TLMUSDT/CAMPAIGN_STAGE_OUTCOMES.csv"
        ),
    )
    args = parser.parse_args()

    cards = load_json(args.input_root / "TLM_HYPOTHESIS_CARDS.json")
    sequence = load_csv(args.input_root / "TLM_SEQUENCE_AND_REJECTION_SUMMARY.csv")
    frozen = load_csv(args.input_root / "TLM_FROZEN_CHECKPOINT_ASSESSMENTS.csv")
    matrix = load_csv(args.input_root / "TLM_DISCRIMINATOR_MATRIX.csv")
    outcomes = outcome_path_map(load_csv(args.outcome_file))

    campaign_evidence = evidence_rows(sequence, frozen, outcomes)
    decisions = lifecycle(cards, sequence, matrix)
    outcome_counts = Counter(row.get("outcome_group") for row in sequence)
    by_hypothesis = {card["hypothesis_id"]: card for card in cards}
    rejected_acceptance_campaigns = [
        int(float(row["campaign_index"]))
        for row in sequence
        if "ACCEPTED_IGNITION" in (row.get("rejected_states") or "").split("|")
    ]

    fuel = by_hypothesis["TLM_POST_IGNITION_FUEL_RETENTION"]
    transient = by_hypothesis["TLM_TRANSIENT_EXECUTION_SPIKE"]
    findings = {
        "symbol": "TLMUSDT",
        "campaigns_reviewed": len(sequence),
        "accepted_expansion": outcome_counts.get("SUCCESS", 0),
        "accepted_without_expansion": outcome_counts.get("PARTIAL", 0),
        "failed_ignition": outcome_counts.get("FAILURE", 0),
        "non_overlapping_metric_count": sum(
            row.get("observed_range_status", "").startswith("NON_OVERLAPPING")
            for row in matrix
        ),
        "fuel_retention_campaigns": sorted(
            set(
                fuel["supporting_campaigns"]
                + fuel["partial_analogues"]
                + fuel["failed_analogues"]
            )
        ),
        "transient_spike_campaigns": sorted(
            set(transient["supporting_campaigns"] + transient["failed_analogues"])
        ),
        "rejected_acceptance_campaigns": rejected_acceptance_campaigns,
        "decisions": decisions,
        "constraints": [
            "campaign unit",
            "outcome after frozen checkpoints",
            "no standalone threshold fitted",
            "no production promotion",
        ],
    }

    write_csv(args.input_root / "TLM_CAMPAIGN_UNIT_EVIDENCE.csv", campaign_evidence)
    (args.input_root / "TLM_HUMAN_REVIEWED_FINDINGS.json").write_text(
        json.dumps(findings, indent=2), encoding="utf-8"
    )
    (args.input_root / "TLM_HUMAN_REVIEWED_FINDINGS.md").write_text(
        render(findings, decisions), encoding="utf-8"
    )
    (args.input_root / "TLM_REVIEWED_RULE_LIFECYCLE.json").write_text(
        json.dumps(decisions, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "campaigns": len(sequence),
                "decisions": len(decisions),
                "non_overlapping_metrics": findings["non_overlapping_metric_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
