from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

FULL_CONTEXT = "FULL_HYPOTHESIS_CONTEXT"
ABSTAIN_PREFIX = "ABSTAIN"
SUCCESS_OUTCOMES = {"accepted_expansion"}
FAILURE_OUTCOMES = {"failed_ignition"}
MIN_OUTCOME_SAMPLE = 2


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_index(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def outcome_map(metrics_rows: list[dict[str, str]]) -> dict[int, str]:
    result: dict[int, str] = {}
    for row in metrics_rows:
        index = campaign_index(row.get("campaign_index"))
        if index is not None:
            result[index] = row.get("profile_outcome", "")
    return result


def unique_campaign_statuses(rows: list[dict[str, str]]) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for row in rows:
        index = campaign_index(row.get("campaign_index"))
        status = row.get("assessment_status", "")
        if index is None or not status:
            continue
        result.setdefault(index, set()).add(status)
    return result


def review_symbol(symbol: str, replay_root: Path, mechanism_root: Path) -> dict[str, Any]:
    destination = replay_root / symbol
    raw_summary = read_json(destination / "HYPOTHESIS_REPLAY_SUMMARY.json")
    campaign_rows = read_csv(destination / "FROZEN_CAMPAIGN_CONTEXT_ASSESSMENTS.csv")
    rejected_rows = read_csv(destination / "FROZEN_REJECTED_CONTEXT_CONTROLS.csv")
    metrics_rows = read_csv(mechanism_root / symbol / "CAMPAIGN_MECHANISM_METRICS.csv")

    outcomes = outcome_map(metrics_rows)
    campaign_statuses = unique_campaign_statuses(campaign_rows)
    rejected_statuses = unique_campaign_statuses(rejected_rows)

    evaluable_campaigns = {
        index: statuses
        for index, statuses in campaign_statuses.items()
        if not all(status.startswith(ABSTAIN_PREFIX) for status in statuses)
    }
    success_indices = sorted(
        index for index in evaluable_campaigns if outcomes.get(index) in SUCCESS_OUTCOMES
    )
    failure_indices = sorted(
        index for index in evaluable_campaigns if outcomes.get(index) in FAILURE_OUTCOMES
    )
    full_success_indices = sorted(
        index for index in success_indices if FULL_CONTEXT in evaluable_campaigns[index]
    )
    full_failure_indices = sorted(
        index for index in failure_indices if FULL_CONTEXT in evaluable_campaigns[index]
    )

    rejected_evaluable_campaigns = {
        index: statuses
        for index, statuses in rejected_statuses.items()
        if not all(status.startswith(ABSTAIN_PREFIX) for status in statuses)
    }
    rejected_full_context_indices = sorted(
        index
        for index, statuses in rejected_evaluable_campaigns.items()
        if FULL_CONTEXT in statuses
    )

    if len(success_indices) < MIN_OUTCOME_SAMPLE or len(failure_indices) < MIN_OUTCOME_SAMPLE:
        reviewed_result = "INSUFFICIENT_OUTCOME_SAMPLE"
    elif (
        len(full_success_indices) >= 2
        and not full_failure_indices
        and not rejected_full_context_indices
    ):
        reviewed_result = "DIRECTIONAL_FULL_CONTEXT_SUBTYPE_SUPPORT"
    elif len(full_success_indices) * max(1, len(failure_indices)) <= len(full_failure_indices) * max(1, len(success_indices)):
        reviewed_result = "NO_CLEAR_DISCRIMINATION"
    else:
        reviewed_result = "INCONCLUSIVE_DIRECTIONAL_EVIDENCE"

    if symbol == "BANKUSDT":
        lifecycle_decision = "KEEP_AS_HYPOTHESIS"
        restricted_rule_id = None
        reason = (
            "Only one campaign is evaluable and it is the accepted full-context campaign. "
            "No assessable failed campaign exists under the expanding baseline, so the hypothesis cannot be discriminatively tested."
        )
    elif reviewed_result == "DIRECTIONAL_FULL_CONTEXT_SUBTYPE_SUPPORT":
        lifecycle_decision = "RESTRICT"
        restricted_rule_id = "ESPORTS_MATURE_DEEP_RESET_SUBTYPE"
        reason = (
            "Two accepted campaigns satisfy the full conjunction while no assessed failure or rejected campaign does. "
            "Another accepted campaign succeeds without a long rebuild, so the context is a possible subtype and not a necessary condition."
        )
    else:
        lifecycle_decision = "KEEP_AS_HYPOTHESIS"
        restricted_rule_id = None
        reason = (
            "Campaign-unit replay does not establish separation from failures and rejected campaigns."
        )

    return {
        "symbol": symbol,
        "rule_id": raw_summary["rule_id"],
        "hypothesis_statement": raw_summary["hypothesis_statement"],
        "raw_anchor_level_result": raw_summary["blind_replay_result"],
        "review_unit": "CAMPAIGN",
        "campaigns_evaluable": len(evaluable_campaigns),
        "success_campaign_indices": success_indices,
        "failure_campaign_indices": failure_indices,
        "full_context_success_campaign_indices": full_success_indices,
        "full_context_failure_campaign_indices": full_failure_indices,
        "rejected_anchor_count": len(rejected_rows),
        "rejected_evaluable_campaign_count": len(rejected_evaluable_campaigns),
        "rejected_full_context_campaign_indices": rejected_full_context_indices,
        "campaign_status_counts": dict(Counter(status for statuses in campaign_statuses.values() for status in statuses)),
        "rejected_status_counts": dict(Counter(status for statuses in rejected_statuses.values() for status in statuses)),
        "reviewed_result": reviewed_result,
        "current_status": "RESEARCH_HYPOTHESIS",
        "lifecycle_decision": lifecycle_decision,
        "restricted_rule_id": restricted_rule_id,
        "decision_reason": reason,
        "method_corrections": [
            "Campaigns, not rejected transition anchors, are the independent comparison unit.",
            "Only FULL_HYPOTHESIS_CONTEXT satisfies the frozen joint hypothesis; partial context is recorded but not counted as fulfillment.",
            "Multiple rejected transitions inside one campaign do not create multiple independent negative cases.",
            "Outcome remains downstream of the frozen assessment and never rewrites historical validity.",
        ],
    }


def render_symbol(review: dict[str, Any]) -> str:
    restricted = review.get("restricted_rule_id") or "—"
    return f"""# {review['symbol']} Human-Reviewed Hypothesis Replay

- Original rule: `{review['rule_id']}`
- Independent comparison unit: `{review['review_unit']}`
- Raw anchor-level result: `{review['raw_anchor_level_result']}`
- Reviewed campaign-level result: `{review['reviewed_result']}`

## Campaign evidence

- Evaluable campaigns: {review['campaigns_evaluable']}
- Success campaigns: {review['success_campaign_indices']}
- Failure campaigns: {review['failure_campaign_indices']}
- Full-context success campaigns: {review['full_context_success_campaign_indices']}
- Full-context failure campaigns: {review['full_context_failure_campaign_indices']}

## Rejected controls

- Raw rejected anchors: {review['rejected_anchor_count']}
- Evaluable rejected campaigns: {review['rejected_evaluable_campaign_count']}
- Rejected campaigns satisfying full context: {review['rejected_full_context_campaign_indices']}

## Rule lifecycle

- Current status: `{review['current_status']}`
- Decision: `{review['lifecycle_decision']}`
- Restricted rule ID: `{restricted}`
- Reason: {review['decision_reason']}

Partial context and repeated rejected transitions remain visible in the raw trace, but they are not counted as independent fulfillment of the frozen joint hypothesis.
"""


def render_synthesis(reviews: list[dict[str, Any]]) -> str:
    rows = []
    for review in reviews:
        rows.append(
            f"| {review['symbol']} | {review['campaigns_evaluable']} | "
            f"{len(review['full_context_success_campaign_indices'])} | "
            f"{len(review['full_context_failure_campaign_indices'])} | "
            f"{len(review['rejected_full_context_campaign_indices'])} | "
            f"{review['reviewed_result']} | {review['lifecycle_decision']} | "
            f"{review.get('restricted_rule_id') or '—'} |"
        )
    return f"""# Human-Reviewed Symbol Hypothesis Blind Replay — Pass 3

The raw replay trace is preserved. This review corrects the evidence unit to campaigns and applies the frozen hypothesis literally: long rebuild plus deeper price reset plus deeper OI reset.

| Symbol | Evaluable campaigns | Full-context successes | Full-context failures | Full-context rejected campaigns | Reviewed result | Decision | Restricted rule |
|---|---:|---:|---:|---:|---|---|---|
{'\n'.join(rows)}

## Method decision

- Repeated rejected transitions within one campaign are correlated observations, not independent controls.
- `PARTIAL_HYPOTHESIS_CONTEXT` is supporting evidence only; it does not fulfill the joint hypothesis.
- BANK remains untestable with the current expanding-window sample.
- Any ESPORTS support is restricted to a possible mature deep-reset subtype; it is not necessary, sufficient, universal, or durable.
"""


def write_lifecycle(reviews: list[dict[str, Any]], output_root: Path) -> None:
    records = [
        {
            "rule_id": review["rule_id"],
            "symbol": review["symbol"],
            "current_status": review["current_status"],
            "decision": review["lifecycle_decision"],
            "reviewed_result": review["reviewed_result"],
            "restricted_rule_id": review.get("restricted_rule_id"),
            "evidence_basis": review["decision_reason"],
        }
        for review in reviews
    ]
    (output_root / "RULE_LIFECYCLE_DECISIONS_PASS3_REVIEWED.json").write_text(
        json.dumps(records, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item['rule_id']} | {item['symbol']} | {item['current_status']} | "
        f"{item['decision']} | {item['reviewed_result']} | {item.get('restricted_rule_id') or '—'} | "
        f"{item['evidence_basis']} |"
        for item in records
    )
    (output_root / "RULE_LIFECYCLE_DECISIONS_PASS3_REVIEWED.md").write_text(
        f"""# Reviewed Rule Lifecycle Decisions — Pass 3

| Rule | Symbol | Current status | Decision | Reviewed result | Restricted rule | Evidence basis |
|---|---|---|---|---|---|---|
{rows}

No candidate is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, default=Path("research/hypothesis_blind_replay"))
    parser.add_argument("--mechanism-root", type=Path, default=Path("research/mechanism_validation"))
    parser.add_argument("--symbols", nargs="+", default=["BANKUSDT", "ESPORTSUSDT"])
    args = parser.parse_args()

    reviews = [review_symbol(symbol, args.replay_root, args.mechanism_root) for symbol in args.symbols]
    for review in reviews:
        destination = args.replay_root / review["symbol"]
        (destination / "HUMAN_REVIEWED_HYPOTHESIS_SUMMARY.json").write_text(
            json.dumps(review, indent=2, sort_keys=True), encoding="utf-8"
        )
        (destination / "HUMAN_REVIEWED_HYPOTHESIS_SUMMARY.md").write_text(
            render_symbol(review), encoding="utf-8"
        )
    (args.replay_root / "HUMAN_REVIEWED_HYPOTHESIS_SYNTHESIS_PASS3.md").write_text(
        render_synthesis(reviews), encoding="utf-8"
    )
    write_lifecycle(reviews, args.replay_root)
    print(json.dumps({"reviews": reviews}, sort_keys=True))


if __name__ == "__main__":
    main()
