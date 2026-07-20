from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DERIVATION_SYMBOLS = {"AKEUSDT", "BANKUSDT", "ESPORTSUSDT", "LYNUSDT"}
ELIGIBILITY_RULE = {
    "minimum_15m_files": 2,
    "minimum_higher_timeframe_types": 2,
    "require_all_files_high_quality": True,
    "excluded_derivation_symbols": sorted(DERIVATION_SYMBOLS),
}
EXPECTED_FROZEN_SYMBOLS = ["MAGMAUSDT", "TLMUSDT", "VELVETUSDT"]
MIN_PRIOR_VALUES_PER_COMPONENT = 2
SUCCESS_OUTCOMES = {"accepted_expansion"}
FAILURE_OUTCOMES = {"failed_ignition"}
FULL_CONTEXT = "FULL_TRANSFER_CONTEXT"
PARTIAL_CONTEXT = "PARTIAL_TRANSFER_CONTEXT"
NO_CONTEXT = "TRANSFER_CONTEXT_NOT_SUPPORTED"


def load_module(name: str, filename: str) -> Any:
    path = HERE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MECHANISM = load_module("oos_mechanism", "validate_symbol_mechanisms.py")


def number(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def iso_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def integer(row: dict[str, str], key: str) -> int:
    return int(float(row.get(key) or 0))


def select_eligible_symbols(rows: list[dict[str, str]]) -> list[str]:
    selected: list[str] = []
    for row in rows:
        symbol = str(row.get("symbol") or "")
        if not symbol or symbol in DERIVATION_SYMBOLS:
            continue
        higher_types = sum(integer(row, timeframe) > 0 for timeframe in ("1h", "4h", "1d"))
        all_high = (
            integer(row, "high_quality") == integer(row, "total")
            and integer(row, "medium_quality") == 0
            and integer(row, "low_quality") == 0
            and integer(row, "unusable") == 0
        )
        if integer(row, "15m") < ELIGIBILITY_RULE["minimum_15m_files"]:
            continue
        if higher_types < ELIGIBILITY_RULE["minimum_higher_timeframe_types"]:
            continue
        if ELIGIBILITY_RULE["require_all_files_high_quality"] and not all_high:
            continue
        selected.append(symbol)
    return sorted(selected)


def reset_magnitude(value: Any) -> float | None:
    parsed = number(value)
    if parsed is None:
        return None
    return max(0.0, -parsed)


def median(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.median(clean) if clean else None


def baseline_component(prior: list[dict[str, Any]], key: str, transform=lambda x: x) -> dict[str, Any]:
    values: list[float] = []
    indices: list[int] = []
    for item in prior:
        value = transform(item.get(key))
        if value is None:
            continue
        values.append(float(value))
        indices.append(int(item["campaign_index"]))
    return {
        "count": len(values),
        "median": median(values),
        "campaign_indices": indices,
    }


def assess_campaign_context(current: dict[str, Any], prior_completed: list[dict[str, Any]]) -> dict[str, Any]:
    current_age = number(current.get("birth_to_ignition_minutes"))
    current_price_reset = reset_magnitude(current.get("price_reset_depth_pct"))
    current_oi_reset = reset_magnitude(current.get("oi_reset_depth_pct"))
    current_values = {
        "age_minutes": current_age,
        "price_reset_magnitude_pct": current_price_reset,
        "oi_reset_magnitude_pct": current_oi_reset,
    }
    baselines = {
        "age_minutes": baseline_component(prior_completed, "birth_to_ignition_minutes", number),
        "price_reset_magnitude_pct": baseline_component(prior_completed, "price_reset_depth_pct", reset_magnitude),
        "oi_reset_magnitude_pct": baseline_component(prior_completed, "oi_reset_depth_pct", reset_magnitude),
    }
    missing_current = [key for key, value in current_values.items() if value is None]
    insufficient_baselines = [
        key for key, item in baselines.items()
        if item["count"] < MIN_PRIOR_VALUES_PER_COMPONENT or item["median"] is None
    ]
    if missing_current:
        status = "ABSTAIN_MISSING_CURRENT_CONTEXT"
        comparisons: dict[str, bool] = {}
    elif insufficient_baselines:
        status = "ABSTAIN_INSUFFICIENT_PRIOR_BASELINE"
        comparisons = {}
    else:
        comparisons = {
            key: float(current_values[key]) > float(baselines[key]["median"])
            for key in current_values
        }
        support_count = sum(comparisons.values())
        if support_count == 3:
            status = FULL_CONTEXT
        elif support_count:
            status = PARTIAL_CONTEXT
        else:
            status = NO_CONTEXT
    return {
        "assessment_status": status,
        "current_context": current_values,
        "causal_baselines": baselines,
        "comparisons": comparisons,
        "missing_current_context": missing_current,
        "insufficient_baselines": insufficient_baselines,
        "prior_completed_campaign_indices": sorted(
            int(item["campaign_index"]) for item in prior_completed
        ),
    }


def outcome_at_ignition(outcome_rows: list[dict[str, str]], campaign_index: int) -> dict[str, Any]:
    candidates = [
        row for row in outcome_rows
        if int(float(row.get("campaign_index") or -1)) == campaign_index
        and row.get("stage") == "IGNITION_CANDIDATE"
    ]
    if not candidates:
        return {}
    horizons = sorted({int(float(row["horizon_minutes"])) for row in candidates})
    comparison = max((value for value in horizons if value <= 720), default=max(horizons))
    row = next(item for item in candidates if int(float(item["horizon_minutes"])) == comparison)
    return {
        "comparison_horizon_minutes": comparison,
        "forward_coverage_complete": str(row.get("coverage_complete", "")).lower() == "true",
        "terminal_return_pct": number(row.get("terminal_return_pct")),
        "mfe_close_pct": number(row.get("mfe_close_pct")),
        "mae_close_pct": number(row.get("mae_close_pct")),
        "path_class": row.get("path_class"),
        "matched_control_count": int(float(row.get("matched_control_count") or 0)),
    }


def campaign_rejection_flags(reviewed: list[dict[str, Any]], campaign: dict[str, Any]) -> dict[str, Any]:
    start = iso_to_ms(campaign.get("start"))
    end = iso_to_ms(campaign.get("end"))
    if start is None or end is None:
        return {"rejected_transition_count": 0, "rejected_states": []}
    selected = [
        item for item in reviewed
        if start <= int(item["timestamp"]) <= end
        and str(item.get("effective_status", item.get("adversarial_status", ""))).startswith("REJECT")
    ]
    return {
        "rejected_transition_count": len(selected),
        "rejected_states": sorted({str(item.get("to_state")) for item in selected}),
    }


def assess_symbol(
    symbol: str,
    case_root: Path,
    profile_root: Path,
    outcome_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prefix = symbol.replace("USDT", "")
    generated = case_root / symbol / "generated"
    profile = load_json(profile_root / symbol / "SYMBOL_STRUCTURAL_PROFILE.json", {})
    reviewed = MECHANISM.PROFILE.effective_review(
        load_json(generated / f"{prefix}_REVIEWED_STATE_LEDGER.json", [])
    )
    metrics = MECHANISM.campaign_mechanism_metrics(symbol, case_root, profile_root)
    metric_by_index = {int(item["campaign_index"]): item for item in metrics}
    outcome_rows = load_csv(outcome_root / symbol / "CAMPAIGN_STAGE_OUTCOMES.csv")
    campaigns = sorted(profile.get("campaigns", []), key=lambda item: int(item["campaign_index"]))
    records: list[dict[str, Any]] = []

    for campaign in campaigns:
        index = int(campaign["campaign_index"])
        metric = metric_by_index.get(index)
        if not metric or not metric.get("ignition_time"):
            continue
        cutoff = iso_to_ms(metric.get("ignition_time"))
        if cutoff is None:
            continue
        prior_completed = [
            item for item in metrics
            if int(item["campaign_index"]) < index
            and iso_to_ms(item.get("campaign_end")) is not None
            and int(iso_to_ms(item.get("campaign_end")) or 0) < cutoff
        ]
        frozen = assess_campaign_context(metric, prior_completed)
        flags = campaign_rejection_flags(reviewed, campaign)
        record = {
            "symbol": symbol,
            "campaign_index": index,
            "cutoff_time": metric.get("ignition_time"),
            "cutoff_timestamp": cutoff,
            "record_type": "OOS_CAMPAIGN_CONTEXT_ASSESSMENT",
            "hypothesis_source": "ESPORTS_MATURE_DEEP_RESET_SUBTYPE",
            "transfer_claim": "MATURE_DEEP_RESET_CONTEXT_TRANSFER",
            "outcome_hidden_at_assessment": True,
            **frozen,
            **flags,
        }
        revealed = {
            "profile_outcome": metric.get("profile_outcome"),
            "outcome_group": (
                "SUCCESS" if metric.get("profile_outcome") in SUCCESS_OUTCOMES
                else "FAILURE" if metric.get("profile_outcome") in FAILURE_OUTCOMES
                else "UNRESOLVED"
            ),
            **outcome_at_ignition(outcome_rows, index),
        }
        record["revealed_outcome"] = revealed
        record["outcome_hidden_after_reveal"] = False
        record["historical_assessment_rewritten"] = False
        records.append(record)

    summary = summarize_symbol(symbol, records)
    return records, summary


def full_context_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in records if item["assessment_status"] == FULL_CONTEXT]


def summarize_symbol(symbol: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    evaluable = [item for item in records if not item["assessment_status"].startswith("ABSTAIN")]
    full = full_context_records(evaluable)
    full_outcomes = Counter(item["revealed_outcome"]["outcome_group"] for item in full)
    full_paths = Counter(
        item["revealed_outcome"].get("path_class") or "MISSING"
        for item in full
    )
    if not evaluable:
        result = "NO_EVALUABLE_CAMPAIGNS"
    elif full_outcomes["FAILURE"]:
        result = "FULL_CONTEXT_CONTRADICTED_WITHIN_SYMBOL"
    elif not full:
        result = "NO_FULL_CONTEXT_MATCH"
    elif full_outcomes["SUCCESS"]:
        result = "DIRECTIONAL_FULL_CONTEXT_MATCH"
    else:
        result = "FULL_CONTEXT_OUTCOME_UNRESOLVED"
    return {
        "symbol": symbol,
        "campaign_cutoffs": len(records),
        "evaluable_campaigns": len(evaluable),
        "abstained_campaigns": len(records) - len(evaluable),
        "assessment_status_counts": dict(Counter(item["assessment_status"] for item in records)),
        "full_context_campaigns": len(full),
        "full_context_outcome_counts": dict(full_outcomes),
        "full_context_path_class_counts": dict(full_paths),
        "full_context_campaign_indices": [item["campaign_index"] for item in full],
        "symbol_transfer_result": result,
    }


def aggregate_transfer(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    full_successes = sum(item["full_context_outcome_counts"].get("SUCCESS", 0) for item in summaries)
    full_failures = sum(item["full_context_outcome_counts"].get("FAILURE", 0) for item in summaries)
    full_unresolved = sum(item["full_context_outcome_counts"].get("UNRESOLVED", 0) for item in summaries)
    symbols_with_success = sum(item["full_context_outcome_counts"].get("SUCCESS", 0) > 0 for item in summaries)
    negative_paths = sum(item["full_context_path_class_counts"].get("NEGATIVE_PATH_OUTLIER", 0) for item in summaries)
    positive_paths = sum(item["full_context_path_class_counts"].get("POSITIVE_PATH_OUTLIER", 0) for item in summaries)
    matched_paths = sum(item["full_context_path_class_counts"].get("MATCHED_CONTROL_LIKE", 0) for item in summaries)

    if full_failures or negative_paths:
        transfer_result = "EXTERNAL_TRANSFER_CONTRADICTION"
        transfer_decision = "REJECT_TRANSFER_CLAIM"
    elif full_successes >= 2 and symbols_with_success >= 2:
        transfer_result = "DIRECTIONAL_EXTERNAL_SUPPORT"
        transfer_decision = "KEEP_TRANSFER_AS_HYPOTHESIS"
    elif full_successes == 0:
        transfer_result = "NO_EXTERNAL_FULL_CONTEXT_EVIDENCE"
        transfer_decision = "REJECT_OR_ABSTAIN_TRANSFER_CLAIM"
    else:
        transfer_result = "INSUFFICIENT_EXTERNAL_EVIDENCE"
        transfer_decision = "ABSTAIN_TRANSFER_CLAIM"

    return {
        "frozen_source_rule": "ESPORTS_MATURE_DEEP_RESET_SUBTYPE",
        "tested_transfer_claim": "MATURE_DEEP_RESET_CONTEXT_TRANSFER",
        "symbols": [item["symbol"] for item in summaries],
        "evaluable_campaigns": sum(item["evaluable_campaigns"] for item in summaries),
        "full_context_successes": full_successes,
        "full_context_failures": full_failures,
        "full_context_unresolved": full_unresolved,
        "symbols_with_full_context_success": symbols_with_success,
        "full_context_positive_path_outliers": positive_paths,
        "full_context_negative_path_outliers": negative_paths,
        "full_context_matched_control_like": matched_paths,
        "transfer_result": transfer_result,
        "transfer_decision": transfer_decision,
        "source_rule_lifecycle": {
            "rule_id": "ESPORTS_MATURE_DEEP_RESET_SUBTYPE",
            "status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_ESPORTS_SPECIFIC_HYPOTHESIS",
            "reason": "External transfer testing does not rewrite the original ESPORTS campaign evidence.",
        },
        "transfer_rule_lifecycle": {
            "rule_id": "MATURE_DEEP_RESET_CONTEXT_TRANSFER",
            "status": "RESEARCH_HYPOTHESIS",
            "decision": transfer_decision,
            "reason": transfer_result,
        },
        "promotion_prohibited": True,
    }


def flatten(record: dict[str, Any]) -> dict[str, Any]:
    current = record.get("current_context") or {}
    baseline = record.get("causal_baselines") or {}
    revealed = record.get("revealed_outcome") or {}
    return {
        "symbol": record.get("symbol"),
        "campaign_index": record.get("campaign_index"),
        "cutoff_time": record.get("cutoff_time"),
        "assessment_status": record.get("assessment_status"),
        "age_minutes": current.get("age_minutes"),
        "age_prior_median": (baseline.get("age_minutes") or {}).get("median"),
        "price_reset_magnitude_pct": current.get("price_reset_magnitude_pct"),
        "price_reset_prior_median": (baseline.get("price_reset_magnitude_pct") or {}).get("median"),
        "oi_reset_magnitude_pct": current.get("oi_reset_magnitude_pct"),
        "oi_reset_prior_median": (baseline.get("oi_reset_magnitude_pct") or {}).get("median"),
        "prior_completed_campaign_indices": "|".join(str(value) for value in record.get("prior_completed_campaign_indices", [])),
        "rejected_transition_count": record.get("rejected_transition_count"),
        "rejected_states": "|".join(record.get("rejected_states") or []),
        "profile_outcome": revealed.get("profile_outcome"),
        "outcome_group": revealed.get("outcome_group"),
        "comparison_horizon_minutes": revealed.get("comparison_horizon_minutes"),
        "terminal_return_pct": revealed.get("terminal_return_pct"),
        "path_class": revealed.get("path_class"),
        "forward_coverage_complete": revealed.get("forward_coverage_complete"),
        "historical_assessment_rewritten": record.get("historical_assessment_rewritten"),
    }


def render_cohort_freeze(selected: list[str]) -> str:
    return f"""# Frozen Out-of-Sample Cohort

The cohort is selected before campaign reconstruction or outcome reveal.

- Excluded derivation symbols: {', '.join(sorted(DERIVATION_SYMBOLS))}
- Minimum 15m files: {ELIGIBILITY_RULE['minimum_15m_files']}
- Minimum higher-timeframe types among 1h/4h/1d: {ELIGIBILITY_RULE['minimum_higher_timeframe_types']}
- All inventoried files must be HIGH quality: {ELIGIBILITY_RULE['require_all_files_high_quality']}
- Frozen eligible symbols: {', '.join(selected)}

No symbol may be added or removed after outcome inspection in this pass.
"""


def render_symbol_summary(summary: dict[str, Any]) -> str:
    return f"""# {summary['symbol']} OOS Transfer Summary

- Campaign ignition cutoffs: {summary['campaign_cutoffs']}
- Evaluable campaigns: {summary['evaluable_campaigns']}
- Abstained campaigns: {summary['abstained_campaigns']}
- Full-context campaigns: {summary['full_context_campaigns']}
- Full-context outcomes: `{json.dumps(summary['full_context_outcome_counts'], sort_keys=True)}`
- Full-context path classes: `{json.dumps(summary['full_context_path_class_counts'], sort_keys=True)}`
- Result: `{summary['symbol_transfer_result']}`

The shared conjunction is evaluated with this symbol's own expanding history. A match does not prove the same causal mechanism as ESPORTS.
"""


def render_synthesis(aggregate: dict[str, Any], summaries: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f"| {item['symbol']} | {item['evaluable_campaigns']} | {item['full_context_campaigns']} | "
        f"{json.dumps(item['full_context_outcome_counts'], sort_keys=True)} | "
        f"{json.dumps(item['full_context_path_class_counts'], sort_keys=True)} | {item['symbol_transfer_result']} |"
        for item in summaries
    )
    return f"""# ESPORTS Mature Deep-Reset Subtype — Frozen OOS Transfer Test

This pass tests transferability only. It does not relabel external campaigns as ESPORTS patterns and does not rewrite the original ESPORTS replay.

| Symbol | Evaluable campaigns | Full context | Full-context outcomes | Full-context path classes | Symbol result |
|---|---:|---:|---|---|---|
{rows}

## Aggregate

- Transfer result: `{aggregate['transfer_result']}`
- Transfer decision: `{aggregate['transfer_decision']}`
- Full-context successes: {aggregate['full_context_successes']}
- Full-context failures: {aggregate['full_context_failures']}
- Full-context unresolved: {aggregate['full_context_unresolved']}
- Symbols with a full-context success: {aggregate['symbols_with_full_context_success']}
- Positive-path outliers: {aggregate['full_context_positive_path_outliers']}
- Negative-path outliers: {aggregate['full_context_negative_path_outliers']}
- Matched-control-like paths: {aggregate['full_context_matched_control_like']}

## Rule lifecycle

- `ESPORTS_MATURE_DEEP_RESET_SUBTYPE`: remains `RESEARCH_HYPOTHESIS` restricted to ESPORTS evidence.
- `MATURE_DEEP_RESET_CONTEXT_TRANSFER`: `{aggregate['transfer_decision']}`.
- No result is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.

## Constraints

- Eligibility was frozen from data coverage and quality before reconstruction.
- Baselines use only completed prior campaigns from the same symbol.
- Missing current context or fewer than two prior values per component produces abstention.
- Outcome and matched-control path class are attached only after the context assessment is frozen.
- Cross-symbol equality of the three measurements does not establish causal identity.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol-map", type=Path, default=Path("research/inventory/generated/SYMBOL_FILE_MAP.csv"))
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--outcome-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-symbols", nargs="+", default=EXPECTED_FROZEN_SYMBOLS)
    args = parser.parse_args()

    selected = select_eligible_symbols(load_csv(args.symbol_map))
    expected = sorted(args.expected_symbols)
    if selected != expected:
        raise SystemExit(f"Frozen cohort mismatch: derived={selected}, expected={expected}")

    args.output_root.mkdir(parents=True, exist_ok=True)
    freeze = {
        "selection_frozen_before_outcomes": True,
        "eligibility_rule": ELIGIBILITY_RULE,
        "symbols": selected,
    }
    (args.output_root / "OOS_COHORT_FREEZE.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    (args.output_root / "OOS_COHORT_FREEZE.md").write_text(render_cohort_freeze(selected), encoding="utf-8")

    summaries: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    for symbol in selected:
        records, summary = assess_symbol(symbol, args.case_root, args.profile_root, args.outcome_root)
        summaries.append(summary)
        all_records.extend(records)
        symbol_dir = args.output_root / "transfer_assessments" / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        write_csv(symbol_dir / "FROZEN_CAMPAIGN_TRANSFER_ASSESSMENTS.csv", [flatten(item) for item in records])
        (symbol_dir / "FROZEN_CAMPAIGN_TRANSFER_TRACE.jsonl").write_text(
            "\n".join(json.dumps(item) for item in records) + ("\n" if records else ""),
            encoding="utf-8",
        )
        (symbol_dir / "SYMBOL_TRANSFER_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (symbol_dir / "SYMBOL_TRANSFER_SUMMARY.md").write_text(render_symbol_summary(summary), encoding="utf-8")

    aggregate = aggregate_transfer(summaries)
    (args.output_root / "OOS_TRANSFER_RESULT.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    (args.output_root / "OOS_TRANSFER_SYNTHESIS.md").write_text(render_synthesis(aggregate, summaries), encoding="utf-8")
    (args.output_root / "RULE_LIFECYCLE_DECISION.json").write_text(
        json.dumps(
            [aggregate["source_rule_lifecycle"], aggregate["transfer_rule_lifecycle"]],
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"symbols": selected, "records": len(all_records), **aggregate}))


if __name__ == "__main__":
    main()
