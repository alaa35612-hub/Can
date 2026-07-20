from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MINUTE_MS = 60_000
COMPARISON_HORIZON = 720
MIN_PRIOR_COMPARABLE = 2
MIN_OUTCOME_SAMPLE = 2

HYPOTHESES = {
    "BANKUSDT": {
        "rule_id": "BANK_LONG_REBUILD_DEEP_RESET_CONTEXT",
        "statement": (
            "A BANK campaign with a longer-than-prior rebuild and jointly deeper observed price/OI reset "
            "may be more likely to survive ignition than ordinary BANK attempts."
        ),
    },
    "ESPORTSUSDT": {
        "rule_id": "ESPORTS_DEEP_RESET_CYCLE_CONTEXT",
        "statement": (
            "A mature ESPORTS cycle with a longer-than-prior build and jointly deeper observed price/OI reset "
            "may define a successful expansion subtype."
        ),
    },
}

SUCCESS_OUTCOMES = {"accepted_expansion"}
FAILURE_OUTCOMES = {"failed_ignition"}


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def integer(value: Any) -> int | None:
    number = finite_float(value)
    return None if number is None else int(number)


def iso_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def ms_to_iso(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not fields:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def reset_magnitude(value: Any) -> float | None:
    """Return drawdown magnitude; positive depth means no observed reset drawdown."""
    number = finite_float(value)
    if number is None:
        return None
    return max(0.0, -number)


def parse_campaign(raw: dict[str, str]) -> dict[str, Any]:
    birth_timestamp = iso_to_ms(raw.get("birth_time"))
    ignition_timestamp = iso_to_ms(raw.get("ignition_time"))
    end_timestamp = iso_to_ms(raw.get("campaign_end"))
    return {
        "symbol": raw.get("symbol"),
        "campaign_index": integer(raw.get("campaign_index")),
        "birth_timestamp": birth_timestamp,
        "birth_time": raw.get("birth_time"),
        "ignition_timestamp": ignition_timestamp,
        "ignition_time": raw.get("ignition_time"),
        "end_timestamp": end_timestamp,
        "end_time": raw.get("campaign_end"),
        "age_at_ignition_minutes": finite_float(raw.get("birth_to_ignition_minutes")),
        "price_reset_depth_pct": finite_float(raw.get("price_reset_depth_pct")),
        "oi_reset_depth_pct": finite_float(raw.get("oi_reset_depth_pct")),
        "price_reset_magnitude_pct": reset_magnitude(raw.get("price_reset_depth_pct")),
        "oi_reset_magnitude_pct": reset_magnitude(raw.get("oi_reset_depth_pct")),
        "reset_depth_status": raw.get("reset_depth_status"),
        "leading_mechanism": raw.get("leading_mechanism"),
        "profile_outcome": raw.get("profile_outcome"),
        "valid_transition_count": integer(raw.get("valid_transition_count")),
        "rejected_transition_count": integer(raw.get("rejected_transition_count")),
    }


def completed_prior_campaigns(
    campaigns: list[dict[str, Any]],
    cutoff_timestamp: int,
    current_campaign_index: int | None,
) -> list[dict[str, Any]]:
    prior = []
    for campaign in campaigns:
        if campaign.get("campaign_index") == current_campaign_index:
            continue
        end_timestamp = campaign.get("end_timestamp")
        ignition_timestamp = campaign.get("ignition_timestamp")
        if end_timestamp is None or ignition_timestamp is None:
            continue
        if end_timestamp <= cutoff_timestamp:
            prior.append(campaign)
    return sorted(prior, key=lambda item: item["ignition_timestamp"])


def feature_baseline(prior: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = [finite_float(item.get(feature)) for item in prior]
    clean = [value for value in values if value is not None]
    return {
        "feature": feature,
        "observations": len(clean),
        "median": statistics.median(clean) if clean else None,
        "minimum_required": MIN_PRIOR_COMPARABLE,
    }


def assess_context(
    campaigns: list[dict[str, Any]],
    campaign: dict[str, Any],
    cutoff_timestamp: int,
    age_minutes: float | None,
) -> dict[str, Any]:
    prior = completed_prior_campaigns(campaigns, cutoff_timestamp, campaign.get("campaign_index"))
    baselines = {
        "age": feature_baseline(prior, "age_at_ignition_minutes"),
        "price_reset": feature_baseline(prior, "price_reset_magnitude_pct"),
        "oi_reset": feature_baseline(prior, "oi_reset_magnitude_pct"),
    }
    current = {
        "age_at_cutoff_minutes": age_minutes,
        "price_reset_magnitude_pct": campaign.get("price_reset_magnitude_pct"),
        "oi_reset_magnitude_pct": campaign.get("oi_reset_magnitude_pct"),
    }

    missing_baselines = [
        name for name, item in baselines.items() if item["observations"] < MIN_PRIOR_COMPARABLE
    ]
    missing_current = [name for name, value in current.items() if value is None]

    if missing_baselines:
        status = "ABSTAIN_INSUFFICIENT_PRIOR_HISTORY"
        evidence = []
        opposition = []
    elif missing_current:
        status = "ABSTAIN_MISSING_CAUSAL_CONTEXT"
        evidence = []
        opposition = []
    else:
        comparisons = {
            "longer_than_prior_median": current["age_at_cutoff_minutes"] > baselines["age"]["median"],
            "deeper_price_reset_than_prior_median": current["price_reset_magnitude_pct"]
            > baselines["price_reset"]["median"],
            "deeper_oi_reset_than_prior_median": current["oi_reset_magnitude_pct"]
            > baselines["oi_reset"]["median"],
        }
        evidence = [name for name, supported in comparisons.items() if supported]
        opposition = [name for name, supported in comparisons.items() if not supported]
        age_support = comparisons["longer_than_prior_median"]
        price_support = comparisons["deeper_price_reset_than_prior_median"]
        oi_support = comparisons["deeper_oi_reset_than_prior_median"]
        if age_support and price_support and oi_support:
            status = "FULL_HYPOTHESIS_CONTEXT"
        elif age_support and (price_support or oi_support):
            status = "PARTIAL_HYPOTHESIS_CONTEXT"
        elif price_support and oi_support:
            status = "DEEP_RESET_WITHOUT_LONG_REBUILD"
        else:
            status = "HYPOTHESIS_CONTEXT_NOT_SUPPORTED"

    return {
        "assessment_status": status,
        "prior_campaign_count": len(prior),
        "prior_campaign_indices": [item["campaign_index"] for item in prior],
        "current_context": current,
        "causal_baselines": baselines,
        "supporting_evidence": evidence,
        "opposing_evidence": opposition,
        "missing_baselines": missing_baselines,
        "missing_current_context": missing_current,
        "expected_discriminator": (
            "FULL_HYPOTHESIS_CONTEXT should occur more consistently in accepted expansion campaigns "
            "than in failed campaigns or rejected-transition controls."
        ),
        "invalidation": (
            "Repeated failed or rejected cases with the same full context, or successful campaigns "
            "without the context, weaken necessity or sufficiency claims."
        ),
    }


def campaign_assessment_records(
    symbol: str,
    campaigns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frozen: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    hypothesis = HYPOTHESES[symbol]

    for campaign in sorted(campaigns, key=lambda item: item.get("birth_timestamp") or 0):
        cutoff = campaign.get("ignition_timestamp")
        age = campaign.get("age_at_ignition_minutes")
        if cutoff is None:
            continue
        assessment = assess_context(campaigns, campaign, cutoff, age)
        record = {
            "symbol": symbol,
            "rule_id": hypothesis["rule_id"],
            "record_type": "CAMPAIGN_IGNITION_CONTEXT",
            "campaign_index": campaign.get("campaign_index"),
            "cutoff_timestamp": cutoff,
            "cutoff_time": ms_to_iso(cutoff),
            "decision_available_time": ms_to_iso(cutoff + 900_000 - 1),
            "leading_mechanism": campaign.get("leading_mechanism"),
            "outcome_hidden": True,
            **assessment,
        }
        frozen.append(record)
        trace.append(record)
        trace.append(
            {
                "symbol": symbol,
                "rule_id": hypothesis["rule_id"],
                "record_type": "CAMPAIGN_OUTCOME_REVEALED",
                "campaign_index": campaign.get("campaign_index"),
                "cutoff_timestamp": cutoff,
                "cutoff_time": ms_to_iso(cutoff),
                "assessment_status_frozen": assessment["assessment_status"],
                "outcome_hidden": False,
                "revealed_profile_outcome": campaign.get("profile_outcome"),
                "historical_assessment_rewritten": False,
            }
        )
    return frozen, trace


def find_campaign_for_timestamp(
    campaigns: list[dict[str, Any]], timestamp: int
) -> dict[str, Any] | None:
    for campaign in campaigns:
        start = campaign.get("birth_timestamp")
        end = campaign.get("end_timestamp")
        if start is not None and end is not None and start <= timestamp <= end:
            return campaign
    return None


def rejected_control_records(
    symbol: str,
    campaigns: list[dict[str, Any]],
    rejected_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hypothesis = HYPOTHESES[symbol]
    by_anchor: dict[int, dict[str, str]] = {}
    for raw in rejected_rows:
        if integer(raw.get("horizon_minutes")) != COMPARISON_HORIZON:
            continue
        timestamp = integer(raw.get("anchor_timestamp"))
        if timestamp is not None:
            by_anchor.setdefault(timestamp, raw)

    frozen: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    for timestamp, raw in sorted(by_anchor.items()):
        campaign = find_campaign_for_timestamp(campaigns, timestamp)
        if campaign is None or campaign.get("birth_timestamp") is None:
            continue
        age = (timestamp - campaign["birth_timestamp"]) / MINUTE_MS
        assessment = assess_context(campaigns, campaign, timestamp, age)
        record = {
            "symbol": symbol,
            "rule_id": hypothesis["rule_id"],
            "record_type": "REJECTED_TRANSITION_CONTEXT_CONTROL",
            "campaign_index": campaign.get("campaign_index"),
            "cutoff_timestamp": timestamp,
            "cutoff_time": raw.get("anchor_time") or ms_to_iso(timestamp),
            "proposed_state": raw.get("proposed_state"),
            "proposed_from_state": raw.get("proposed_from_state"),
            "adversarial_reasons": raw.get("adversarial_reasons"),
            "historical_validity": "REJECTED",
            "outcome_hidden": True,
            **assessment,
        }
        frozen.append(record)
        trace.append(record)
        trace.append(
            {
                "symbol": symbol,
                "rule_id": hypothesis["rule_id"],
                "record_type": "REJECTED_CONTROL_OUTCOME_REVEALED",
                "campaign_index": campaign.get("campaign_index"),
                "cutoff_timestamp": timestamp,
                "cutoff_time": raw.get("anchor_time") or ms_to_iso(timestamp),
                "assessment_status_frozen": assessment["assessment_status"],
                "historical_validity": "REJECTED",
                "outcome_hidden": False,
                "revealed_path_class": raw.get("path_class"),
                "revealed_terminal_return_pct": finite_float(raw.get("terminal_return_pct")),
                "historical_assessment_rewritten": False,
            }
        )
    return frozen, trace


def is_context_positive(status: str) -> bool:
    return status in {"FULL_HYPOTHESIS_CONTEXT", "PARTIAL_HYPOTHESIS_CONTEXT"}


def summarize_symbol(
    symbol: str,
    campaigns: list[dict[str, Any]],
    campaign_records: list[dict[str, Any]],
    rejected_records: list[dict[str, Any]],
) -> dict[str, Any]:
    evaluated = [
        record
        for record in campaign_records
        if not record["assessment_status"].startswith("ABSTAIN")
    ]
    revealed_by_index = {item["campaign_index"]: item["profile_outcome"] for item in campaigns}
    successes = [
        record for record in evaluated if revealed_by_index.get(record["campaign_index"]) in SUCCESS_OUTCOMES
    ]
    failures = [
        record for record in evaluated if revealed_by_index.get(record["campaign_index"]) in FAILURE_OUTCOMES
    ]
    positive_successes = sum(is_context_positive(item["assessment_status"]) for item in successes)
    positive_failures = sum(is_context_positive(item["assessment_status"]) for item in failures)
    full_successes = sum(item["assessment_status"] == "FULL_HYPOTHESIS_CONTEXT" for item in successes)
    full_failures = sum(item["assessment_status"] == "FULL_HYPOTHESIS_CONTEXT" for item in failures)
    rejected_evaluated = [
        record for record in rejected_records if not record["assessment_status"].startswith("ABSTAIN")
    ]
    rejected_positive = sum(is_context_positive(item["assessment_status"]) for item in rejected_evaluated)

    if len(successes) < MIN_OUTCOME_SAMPLE or len(failures) < MIN_OUTCOME_SAMPLE:
        replay_result = "INSUFFICIENT_OUTCOME_SAMPLE"
    elif full_successes >= 2 and full_failures == 0 and rejected_positive == 0:
        replay_result = "DIRECTIONAL_FULL_CONTEXT_SUPPORT"
    elif positive_successes * max(1, len(failures)) <= positive_failures * max(1, len(successes)):
        replay_result = "NO_DISCRIMINATION_OR_CONTRADICTION"
    else:
        replay_result = "INCONCLUSIVE_DIRECTIONAL_EVIDENCE"

    if symbol == "BANKUSDT":
        lifecycle_decision = "KEEP_AS_HYPOTHESIS"
        lifecycle_reason = (
            "The sole assessable accepted campaign may satisfy the full context, but the replay lacks "
            "the minimum paired success/failure sample required for promotion."
        )
    elif replay_result == "DIRECTIONAL_FULL_CONTEXT_SUPPORT":
        lifecycle_decision = "RESTRICT"
        lifecycle_reason = (
            "Full context is directionally associated with a successful subtype, but it is not necessary, "
            "the sample is small, and no cross-symbol transfer is established."
        )
    else:
        lifecycle_decision = "KEEP_AS_HYPOTHESIS"
        lifecycle_reason = (
            "Expanding-window replay does not establish reliable discrimination from failures and rejected controls."
        )

    return {
        "symbol": symbol,
        "rule_id": HYPOTHESES[symbol]["rule_id"],
        "hypothesis_statement": HYPOTHESES[symbol]["statement"],
        "campaigns_total": len(campaigns),
        "campaign_assessments": len(campaign_records),
        "campaign_assessments_evaluable": len(evaluated),
        "campaign_assessments_abstained": len(campaign_records) - len(evaluated),
        "assessed_successes": len(successes),
        "assessed_failures": len(failures),
        "positive_context_successes": positive_successes,
        "positive_context_failures": positive_failures,
        "full_context_successes": full_successes,
        "full_context_failures": full_failures,
        "rejected_controls_total": len(rejected_records),
        "rejected_controls_evaluable": len(rejected_evaluated),
        "rejected_controls_positive_context": rejected_positive,
        "campaign_context_status_counts": dict(Counter(item["assessment_status"] for item in campaign_records)),
        "rejected_context_status_counts": dict(Counter(item["assessment_status"] for item in rejected_records)),
        "blind_replay_result": replay_result,
        "rule_status": "RESEARCH_HYPOTHESIS",
        "lifecycle_decision": lifecycle_decision,
        "lifecycle_reason": lifecycle_reason,
        "constraints": [
            "Each assessment uses only campaigns completed before the active cutoff.",
            "Outcome is attached only after the context assessment is frozen.",
            "The baseline is symbol-local and expanding; no universal numerical threshold is used.",
            "Observation-gap or missing-reset cases abstain rather than infer continuity.",
            "Rejected controls remain historically rejected even when their later path is positive.",
            "No result qualifies as a durable rule in this pass.",
        ],
    }


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    context = record.get("current_context") or {}
    baselines = record.get("causal_baselines") or {}
    return {
        "symbol": record.get("symbol"),
        "rule_id": record.get("rule_id"),
        "record_type": record.get("record_type"),
        "campaign_index": record.get("campaign_index"),
        "cutoff_timestamp": record.get("cutoff_timestamp"),
        "cutoff_time": record.get("cutoff_time"),
        "assessment_status": record.get("assessment_status"),
        "age_at_cutoff_minutes": context.get("age_at_cutoff_minutes"),
        "price_reset_magnitude_pct": context.get("price_reset_magnitude_pct"),
        "oi_reset_magnitude_pct": context.get("oi_reset_magnitude_pct"),
        "prior_campaign_count": record.get("prior_campaign_count"),
        "age_prior_median": (baselines.get("age") or {}).get("median"),
        "price_reset_prior_median": (baselines.get("price_reset") or {}).get("median"),
        "oi_reset_prior_median": (baselines.get("oi_reset") or {}).get("median"),
        "supporting_evidence": "|".join(record.get("supporting_evidence") or []),
        "opposing_evidence": "|".join(record.get("opposing_evidence") or []),
        "missing_baselines": "|".join(record.get("missing_baselines") or []),
        "missing_current_context": "|".join(record.get("missing_current_context") or []),
        "proposed_state": record.get("proposed_state"),
        "historical_validity": record.get("historical_validity"),
    }


def render_summary(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    rows = []
    for record in records:
        rows.append(
            f"| {record['campaign_index']} | {record['cutoff_time']} | {record['assessment_status']} | "
            f"{record['current_context'].get('age_at_cutoff_minutes')} | "
            f"{record['current_context'].get('price_reset_magnitude_pct')} | "
            f"{record['current_context'].get('oi_reset_magnitude_pct')} |"
        )
    table = "\n".join(rows) or "| — | — | — | — | — | — |"
    return f"""# {summary['symbol']} Hypothesis Blind Replay

## Frozen hypothesis

- Rule ID: `{summary['rule_id']}`
- Statement: {summary['hypothesis_statement']}
- Status before replay: `RESEARCH_HYPOTHESIS`

## Expanding-window campaign assessments

| Campaign | Cutoff | Frozen assessment | Age min | Price reset magnitude % | OI reset magnitude % |
|---:|---|---|---:|---:|---:|
{table}

## Replay result

- Total campaign assessments: {summary['campaign_assessments']}
- Evaluable: {summary['campaign_assessments_evaluable']}
- Abstained: {summary['campaign_assessments_abstained']}
- Assessed successes: {summary['assessed_successes']}
- Assessed failures: {summary['assessed_failures']}
- Full-context successes: {summary['full_context_successes']}
- Full-context failures: {summary['full_context_failures']}
- Evaluable rejected controls: {summary['rejected_controls_evaluable']}
- Rejected controls with positive context: {summary['rejected_controls_positive_context']}
- Blind replay result: `{summary['blind_replay_result']}`

## Rule lifecycle

- Decision: `{summary['lifecycle_decision']}`
- Reason: {summary['lifecycle_reason']}
- No historical decision is rewritten after outcome reveal.
- No promotion to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` is made by this pass.
"""


def render_cross_symbol(summaries: list[dict[str, Any]]) -> str:
    rows = []
    for summary in summaries:
        rows.append(
            f"| {summary['symbol']} | {summary['campaign_assessments_evaluable']} | "
            f"{summary['assessed_successes']} | {summary['assessed_failures']} | "
            f"{summary['full_context_successes']} | {summary['full_context_failures']} | "
            f"{summary['rejected_controls_positive_context']} | {summary['blind_replay_result']} | "
            f"{summary['lifecycle_decision']} |"
        )
    return f"""# Symbol-Specific Hypothesis Blind Replay — Pass 3

This pass evaluates two already-registered symbol-specific hypotheses. It does not search for a new winning threshold and does not impose a common market pattern.

| Symbol | Evaluable campaigns | Successes | Failures | Full-context successes | Full-context failures | Positive rejected controls | Replay result | Lifecycle decision |
|---|---:|---:|---:|---:|---:|---:|---|---|
{'\n'.join(rows)}

## Reading constraints

- Context is assessed at the original ignition or rejected-transition cutoff.
- Baselines contain only campaigns completed before that cutoff.
- Outcomes are revealed after the assessment record is frozen.
- Missing history or reset continuity produces abstention.
- The same context definition is not transferred from BANK to ESPORTS or vice versa.
- No candidate becomes a durable rule in this pass.
"""


def run_symbol(symbol: str, mechanism_root: Path, output_root: Path) -> dict[str, Any]:
    metrics_path = mechanism_root / symbol / "CAMPAIGN_MECHANISM_METRICS.csv"
    rejected_path = mechanism_root / symbol / "REJECTED_TRANSITION_OUTCOMES.csv"
    campaigns = [parse_campaign(raw) for raw in read_csv(metrics_path)]
    campaigns = [item for item in campaigns if item.get("campaign_index") is not None]
    campaign_records, campaign_trace = campaign_assessment_records(symbol, campaigns)
    rejected_records, rejected_trace = rejected_control_records(
        symbol, campaigns, read_csv(rejected_path)
    )
    summary = summarize_symbol(symbol, campaigns, campaign_records, rejected_records)

    destination = output_root / symbol
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "FROZEN_CAMPAIGN_CONTEXT_ASSESSMENTS.csv", [flatten_record(item) for item in campaign_records])
    write_csv(destination / "FROZEN_REJECTED_CONTEXT_CONTROLS.csv", [flatten_record(item) for item in rejected_records])
    with (destination / "BLIND_REPLAY_TRACE.jsonl").open("w", encoding="utf-8") as handle:
        for item in sorted(campaign_trace + rejected_trace, key=lambda row: (row.get("cutoff_timestamp", 0), row["record_type"])):
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    (destination / "HYPOTHESIS_REPLAY_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    (destination / "HYPOTHESIS_REPLAY_SUMMARY.md").write_text(
        render_summary(summary, campaign_records), encoding="utf-8"
    )
    return summary


def write_rule_lifecycle(summaries: list[dict[str, Any]], output_root: Path) -> None:
    records = [
        {
            "rule_id": summary["rule_id"],
            "symbol": summary["symbol"],
            "current_status": summary["rule_status"],
            "decision": summary["lifecycle_decision"],
            "blind_replay_result": summary["blind_replay_result"],
            "evidence_basis": summary["lifecycle_reason"],
            "unresolved_limitations": summary["constraints"],
        }
        for summary in summaries
    ]
    (output_root / "RULE_LIFECYCLE_DECISIONS_PASS3.json").write_text(
        json.dumps(records, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item['rule_id']} | {item['symbol']} | {item['current_status']} | {item['decision']} | "
        f"{item['blind_replay_result']} | {item['evidence_basis']} |"
        for item in records
    )
    (output_root / "RULE_LIFECYCLE_DECISIONS_PASS3.md").write_text(
        f"""# Rule Lifecycle Decisions — Hypothesis Blind Replay Pass 3

| Rule | Symbol | Current status | Decision | Replay result | Evidence basis |
|---|---|---|---|---|---|
{rows}

No candidate is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` in this pass.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mechanism-root", type=Path, default=Path("research/mechanism_validation")
    )
    parser.add_argument(
        "--output-root", type=Path, default=Path("research/hypothesis_blind_replay")
    )
    parser.add_argument("--symbols", nargs="+", default=["BANKUSDT", "ESPORTSUSDT"])
    args = parser.parse_args()

    unsupported = [symbol for symbol in args.symbols if symbol not in HYPOTHESES]
    if unsupported:
        raise SystemExit(f"No frozen hypothesis configuration for: {', '.join(unsupported)}")

    args.output_root.mkdir(parents=True, exist_ok=True)
    summaries = [run_symbol(symbol, args.mechanism_root, args.output_root) for symbol in args.symbols]
    (args.output_root / "HYPOTHESIS_BLIND_REPLAY_SYNTHESIS_PASS3.md").write_text(
        render_cross_symbol(summaries), encoding="utf-8"
    )
    write_rule_lifecycle(summaries, args.output_root)
    print(json.dumps({"symbols": len(summaries), "summaries": summaries}, sort_keys=True))


if __name__ == "__main__":
    main()
