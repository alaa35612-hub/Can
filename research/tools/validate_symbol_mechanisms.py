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


def load_module(name: str, filename: str) -> Any:
    path = HERE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load_module("symbol_campaign_builder", "build_symbol_campaign.py")
OUTCOME = load_module("campaign_outcome_core", "audit_campaign_outcomes.py")
OUTCOME_RUN = load_module("campaign_outcome_runner", "run_campaign_outcome_audit.py")
PROFILE = OUTCOME.PROFILE

MINUTE_MS = 60_000
PRIMARY_INTERVAL_MS = 900_000
SOURCE_POLICIES = (
    "MOST_COMPLETE_LATEST",
    "EARLIEST_CAPTURE",
    "LATEST_CAPTURE",
    "MIN_DISAGREEMENT",
)
DECISION_RELEVANT_FIELDS = {
    "close",
    "number_of_trades",
    "quote_volume",
    "taker_quote_imbalance_pct",
    "oi",
}
MECHANISM_FACTS = {
    "OI": {"oi_expansion"},
    "EXECUTION": {"execution_expansion", "execution_shock"},
    "PRICE": {"positive_price_release"},
}


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def ms_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def iso_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def number(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def relative_difference(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    return abs(left - right) / max(abs(left), abs(right), 1e-12)


def source_groups(rows: list[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["timeframe"], int(row["timestamp"]))].append(row)
    return groups


def row_completeness(row: dict[str, Any]) -> int:
    return sum(row.get(field) is not None for field in BUILD.FIELDS)


def disagreement_score(candidate: dict[str, Any], peers: list[dict[str, Any]]) -> int:
    score = 0
    for peer in peers:
        if peer is candidate:
            continue
        for field in BUILD.FIELDS:
            if relative_difference(candidate.get(field), peer.get(field)) > 1e-8:
                score += 1
    return score


def select_source_row(group: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    if not group:
        raise ValueError("Cannot select from an empty source group")
    if policy == "EARLIEST_CAPTURE":
        return min(group, key=lambda row: row["source"])
    if policy == "LATEST_CAPTURE":
        return max(group, key=lambda row: row["source"])
    if policy == "MIN_DISAGREEMENT":
        return min(
            group,
            key=lambda row: (
                disagreement_score(row, group),
                -row_completeness(row),
                row["source"],
            ),
        )
    if policy == "MOST_COMPLETE_LATEST":
        return max(group, key=lambda row: (row_completeness(row), row["source"]))
    raise ValueError(f"Unknown source policy: {policy}")


def deduplicate_with_policy(rows: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    selected = [select_source_row(group, policy) for group in source_groups(rows).values()]
    return sorted(selected, key=lambda row: (row["timeframe"], row["timestamp"]))


def conflict_field_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    field_counts: Counter[str] = Counter()
    material_groups = 0
    decision_relevant_groups = 0
    overlap_groups = 0
    for group in source_groups(rows).values():
        if len(group) < 2:
            continue
        overlap_groups += 1
        group_fields: set[str] = set()
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                for field in BUILD.FIELDS:
                    if relative_difference(left.get(field), right.get(field)) > 1e-8:
                        group_fields.add(field)
        if not group_fields:
            continue
        material_groups += 1
        field_counts.update(group_fields)
        if group_fields & DECISION_RELEVANT_FIELDS:
            decision_relevant_groups += 1
    return {
        "overlap_groups": overlap_groups,
        "material_conflict_groups": material_groups,
        "decision_relevant_conflict_groups": decision_relevant_groups,
        "field_counts": dict(sorted(field_counts.items())),
        "decision_relevant_fields": sorted(DECISION_RELEVANT_FIELDS),
    }


def review_ledger(ledger: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline = {row["timestamp"]: row for row in rows if row["timeframe"] == "15m"}
    reviewed: list[dict[str, Any]] = []
    valid_state = ledger[0]["from_state"] if ledger else "LATENT"
    for item in ledger:
        candidate = BUILD.adversarial_review(item, timeline.get(item["timestamp"]))
        from_state = item.get("from_state")
        to_state = item.get("to_state")
        boundary = to_state == "RESET" and "data_gap_campaign_boundary" in set(item.get("facts_added") or [])
        independent_reanchor = (
            to_state == "EARLY_BUILD"
            and from_state in {"FAILURE", "RESET"}
            and item.get("supporting_score", 0) >= 1
        )
        if boundary:
            valid_state = "RESET"
        elif from_state != valid_state:
            if independent_reanchor:
                if candidate["adversarial_status"] == "PASS":
                    candidate["adversarial_status"] = "RESTRICT"
                candidate["adversarial_reasons"].append(
                    "campaign re-anchored from independent build evidence after an invalid predecessor chain"
                )
                valid_state = to_state
            else:
                candidate["adversarial_status"] = "REJECT"
                candidate["adversarial_reasons"].append(
                    f"transition depends on an unvalidated predecessor; reviewed state remains {valid_state}"
                )
        elif candidate["adversarial_status"] != "REJECT":
            valid_state = to_state
        candidate["reviewed_from_state"] = from_state
        candidate["reviewed_state_after"] = valid_state
        candidate["effective_status"] = candidate["adversarial_status"]
        reviewed.append(candidate)
    return reviewed


def valid_transition_signature(reviewed: list[dict[str, Any]]) -> list[tuple[int, str, str]]:
    return [
        (int(item["timestamp"]), str(item.get("to_state")), str(item.get("effective_status")))
        for item in reviewed
        if item.get("effective_status") in {"PASS", "RESTRICT"}
    ]


def source_policy_run(raw: list[dict[str, Any]], symbol: str, policy: str) -> dict[str, Any]:
    merged = deduplicate_with_policy(raw, policy)
    rows = BUILD.enrich(merged)
    ledger, segments = BUILD.build_ledger(symbol, rows)
    reviewed = review_ledger(ledger, rows)
    counts = Counter(item["effective_status"] for item in reviewed)
    return {
        "policy": policy,
        "rows": len(rows),
        "segments": segments,
        "proposed_transitions": len(ledger),
        "review_counts": {status: counts.get(status, 0) for status in ("PASS", "RESTRICT", "REJECT")},
        "valid_signature": valid_transition_signature(reviewed),
    }


def source_sensitivity(symbol: str, root: Path) -> dict[str, Any]:
    sources, raw = BUILD.load_symbol(root, symbol)
    if not sources:
        raise RuntimeError(f"No sources found for {symbol}")
    field_summary = conflict_field_summary(raw)
    runs = [source_policy_run(raw, symbol, policy) for policy in SOURCE_POLICIES]
    baseline = runs[0]["valid_signature"]
    comparisons = []
    for run in runs:
        baseline_set = set(baseline)
        current_set = set(run["valid_signature"])
        comparisons.append(
            {
                "policy": run["policy"],
                "valid_signature_same_as_default": run["valid_signature"] == baseline,
                "valid_transition_symmetric_difference": len(baseline_set ^ current_set),
                "segments": run["segments"],
                "proposed_transitions": run["proposed_transitions"],
                "review_counts": run["review_counts"],
            }
        )
    stable = all(item["valid_signature_same_as_default"] for item in comparisons)
    return {
        "symbol": symbol,
        "sources": sorted(sources),
        "policies": comparisons,
        "conflicts": field_summary,
        "sensitivity_status": "STABLE_VALID_PATH" if stable else "SOURCE_SENSITIVE_VALID_PATH",
        "interpretation": (
            "All tested source-selection policies preserve the valid reviewed transition path."
            if stable
            else "At least one source-selection policy changes the valid reviewed transition path."
        ),
    }


def rejection_type(item: dict[str, Any]) -> str | None:
    effective = str(item.get("effective_status", item.get("adversarial_status", "")))
    adversarial = str(item.get("adversarial_status", ""))
    if effective == "REJECT_DEPENDENCY":
        return "REJECTED_DESCENDANT"
    if effective.startswith("REJECT") or adversarial == "REJECT":
        reasons = " ".join(item.get("adversarial_reasons") or []).lower()
        if "unvalidated predecessor" in reasons:
            return "REJECTED_DESCENDANT"
        return "DIRECT_REJECTED_TRANSITION"
    return None


def negative_control_anchors(reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors = []
    for item in reviewed:
        kind = rejection_type(item)
        if not kind:
            continue
        if item.get("to_state") == "RESET":
            continue
        anchor = dict(item)
        anchor["negative_control_type"] = kind
        anchors.append(anchor)
    return anchors


def median(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.median(clean) if clean else None


def summarize_negative_rows(rows: list[dict[str, Any]], comparison_horizon: int) -> dict[str, Any]:
    selected = [row for row in rows if row["horizon_minutes"] == comparison_horizon]
    by_stage: dict[str, Any] = {}
    for stage in sorted({row["proposed_state"] for row in selected}):
        stage_rows = [row for row in selected if row["proposed_state"] == stage]
        complete = [row for row in stage_rows if row["coverage_complete"]]
        by_stage[stage] = {
            "observations": len(stage_rows),
            "complete_observations": len(complete),
            "median_terminal_return_pct": median([row["terminal_return_pct"] for row in complete]),
            "path_class_counts": dict(Counter(row["path_class"] for row in stage_rows)),
            "rejection_type_counts": dict(Counter(row["negative_control_type"] for row in stage_rows)),
        }
    return {"comparison_horizon_minutes": comparison_horizon, "stage_summaries": by_stage}


def positive_outlier_rate(rows: list[dict[str, Any]]) -> float | None:
    complete = [row for row in rows if row.get("coverage_complete")]
    if not complete:
        return None
    return sum(row.get("path_class") == "POSITIVE_PATH_OUTLIER" for row in complete) / len(complete)


def discrimination_table(
    negative_rows: list[dict[str, Any]],
    valid_rows: list[dict[str, str]],
    comparison_horizon: int,
) -> list[dict[str, Any]]:
    negative = [row for row in negative_rows if row["horizon_minutes"] == comparison_horizon]
    valid = [
        row
        for row in valid_rows
        if int(float(row["horizon_minutes"])) == comparison_horizon
        and row.get("stage_review_status") in {"PASS", "RESTRICT"}
    ]
    stages = sorted({row["proposed_state"] for row in negative} | {row.get("stage", "") for row in valid})
    output = []
    for stage in stages:
        if not stage:
            continue
        rejected_stage = [row for row in negative if row["proposed_state"] == stage]
        valid_stage = [row for row in valid if row.get("stage") == stage]
        valid_complete = [row for row in valid_stage if str(row.get("coverage_complete")).lower() == "true"]
        rejected_complete = [row for row in rejected_stage if row.get("coverage_complete")]
        valid_median = median([number(row.get("terminal_return_pct")) for row in valid_complete])
        rejected_median = median([number(row.get("terminal_return_pct")) for row in rejected_complete])
        valid_rate = (
            sum(row.get("path_class") == "POSITIVE_PATH_OUTLIER" for row in valid_complete) / len(valid_complete)
            if valid_complete
            else None
        )
        rejected_rate = positive_outlier_rate(rejected_stage)
        if not valid_complete or not rejected_complete:
            status = "NO_PAIRED_SAMPLE"
        elif (
            valid_rate is not None
            and rejected_rate is not None
            and valid_rate >= rejected_rate + 0.25
            and valid_median is not None
            and rejected_median is not None
            and valid_median > rejected_median
        ):
            status = "VALID_STAGE_DISCRIMINATES"
        else:
            status = "NO_CLEAR_DISCRIMINATION"
        output.append(
            {
                "stage": stage,
                "valid_complete_observations": len(valid_complete),
                "rejected_complete_observations": len(rejected_complete),
                "valid_median_terminal_return_pct": valid_median,
                "rejected_median_terminal_return_pct": rejected_median,
                "valid_positive_outlier_rate": valid_rate,
                "rejected_positive_outlier_rate": rejected_rate,
                "discrimination_status": status,
            }
        )
    return output


def audit_negative_controls(
    symbol: str,
    case_root: Path,
    profile_root: Path,
    outcome_root: Path,
) -> dict[str, Any]:
    prefix = symbol.replace("USDT", "")
    generated = case_root / symbol / "generated"
    profile = load_json(profile_root / symbol / "SYMBOL_STRUCTURAL_PROFILE.json", {})
    timeline = OUTCOME.primary_rows(load_csv(generated / f"{prefix}_CAUSAL_TIMELINE.csv"))
    raw_reviewed = load_json(generated / f"{prefix}_REVIEWED_STATE_LEDGER.json", [])
    reviewed = PROFILE.effective_review(raw_reviewed)
    horizons = OUTCOME.adaptive_horizons(profile)
    max_horizon = max(horizons)
    comparison_horizon = max(horizon for horizon in horizons if horizon <= 720)
    result_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    for anchor in negative_control_anchors(reviewed):
        timestamp = int(anchor["timestamp"])
        controls = OUTCOME_RUN.matched_controls(timeline, timestamp, reviewed, max_horizon)
        for horizon in horizons:
            metrics = OUTCOME.path_metrics(timeline, timestamp, horizon)
            if metrics is None:
                continue
            measured_controls = []
            for control in controls:
                measured = OUTCOME.path_metrics(timeline, control["timestamp"], horizon)
                if measured is None:
                    continue
                measured_controls.append(measured)
                control_rows.append(
                    {
                        "symbol": symbol,
                        "negative_anchor_timestamp": timestamp,
                        "proposed_state": anchor.get("to_state"),
                        "negative_control_type": anchor["negative_control_type"],
                        "control_timestamp": control["timestamp"],
                        "control_time": OUTCOME.ms_to_iso(control["timestamp"]),
                        "control_causal_state": control["causal_state"],
                        "control_tier": control["control_tier"],
                        "horizon_minutes": horizon,
                        **measured,
                    }
                )
            path_class, ranks = OUTCOME.classify_path(metrics, measured_controls)
            result_rows.append(
                {
                    "symbol": symbol,
                    "anchor_timestamp": timestamp,
                    "anchor_time": anchor.get("time") or OUTCOME.ms_to_iso(timestamp),
                    "proposed_from_state": anchor.get("from_state"),
                    "proposed_state": anchor.get("to_state"),
                    "negative_control_type": anchor["negative_control_type"],
                    "adversarial_reasons": "; ".join(anchor.get("adversarial_reasons") or []),
                    "horizon_minutes": horizon,
                    "matched_control_count": len(measured_controls),
                    "path_class": path_class,
                    **metrics,
                    **ranks,
                }
            )
    valid_path = outcome_root / symbol / "CAMPAIGN_STAGE_OUTCOMES.csv"
    valid_rows = load_csv(valid_path) if valid_path.exists() else []
    summary = summarize_negative_rows(result_rows, comparison_horizon)
    summary.update(
        {
            "symbol": symbol,
            "negative_anchor_count": len(negative_control_anchors(reviewed)),
            "outcome_rows": len(result_rows),
            "discrimination": discrimination_table(result_rows, valid_rows, comparison_horizon),
        }
    )
    return {"summary": summary, "rows": result_rows, "controls": control_rows}


def row_at_timestamp(rows: list[dict[str, Any]], timestamp: int | None) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    index = OUTCOME.row_index_at_or_before(rows, timestamp)
    if index is None or rows[index]["timestamp"] != timestamp:
        return None
    return rows[index]


def first_valid_time(transitions: list[dict[str, Any]], state: str) -> int | None:
    for item in transitions:
        if item.get("effective_status") in {"PASS", "RESTRICT"} and item.get("to_state") == state:
            return int(item["timestamp"])
    return None


def leading_mechanism(transitions: list[dict[str, Any]]) -> str:
    first_times: dict[str, int] = {}
    for item in transitions:
        if item.get("effective_status") not in {"PASS", "RESTRICT"}:
            continue
        facts = set(item.get("facts_added") or [])
        for mechanism, mechanism_facts in MECHANISM_FACTS.items():
            if mechanism not in first_times and facts & mechanism_facts:
                first_times[mechanism] = int(item["timestamp"])
    if not first_times:
        return "UNRESOLVED"
    earliest = min(first_times.values())
    leaders = sorted(name for name, timestamp in first_times.items() if timestamp == earliest)
    return "_AND_".join(leaders) + ("_SIMULTANEOUS" if len(leaders) > 1 else "_LEADS")


def gap_between(rows: list[dict[str, Any]], start: int, end: int) -> bool:
    sample = [row for row in rows if start <= row["timestamp"] <= end]
    if len(sample) < 2:
        return True
    return any(
        right["timestamp"] - left["timestamp"] > 4 * PRIMARY_INTERVAL_MS
        for left, right in zip(sample, sample[1:])
    )


def reset_depth(
    rows: list[dict[str, Any]],
    previous_campaign: dict[str, Any] | None,
    birth_timestamp: int,
) -> dict[str, Any]:
    if previous_campaign is None:
        return {
            "reset_depth_status": "NO_PRIOR_CAMPAIGN",
            "price_reset_depth_pct": None,
            "oi_reset_depth_pct": None,
        }
    previous_start = iso_to_ms(previous_campaign.get("start"))
    previous_end = iso_to_ms(previous_campaign.get("end"))
    if previous_start is None or previous_end is None:
        return {
            "reset_depth_status": "MISSING_PRIOR_CAMPAIGN_TIME",
            "price_reset_depth_pct": None,
            "oi_reset_depth_pct": None,
        }
    if gap_between(rows, previous_end, birth_timestamp):
        return {
            "reset_depth_status": "UNOBSERVED_GAP",
            "price_reset_depth_pct": None,
            "oi_reset_depth_pct": None,
        }
    prior_rows = [row for row in rows if previous_start <= row["timestamp"] <= previous_end]
    birth = row_at_timestamp(rows, birth_timestamp)
    if not prior_rows or birth is None:
        return {
            "reset_depth_status": "INSUFFICIENT_ROWS",
            "price_reset_depth_pct": None,
            "oi_reset_depth_pct": None,
        }
    peak_close = max((row["close"] for row in prior_rows if row.get("close") is not None), default=None)
    peak_oi = max((number(row.get("oi")) for row in prior_rows if number(row.get("oi")) is not None), default=None)
    birth_close = number(birth.get("close"))
    birth_oi = number(birth.get("oi"))
    return {
        "reset_depth_status": "MEASURED",
        "price_reset_depth_pct": (
            None if peak_close in (None, 0) or birth_close is None else (birth_close / peak_close - 1.0) * 100.0
        ),
        "oi_reset_depth_pct": (
            None if peak_oi in (None, 0) or birth_oi is None else (birth_oi / peak_oi - 1.0) * 100.0
        ),
    }


def minutes_between(start: int | None, end: int | None) -> int | None:
    if start is None or end is None:
        return None
    return int((end - start) / MINUTE_MS)


def campaign_mechanism_metrics(
    symbol: str,
    case_root: Path,
    profile_root: Path,
) -> list[dict[str, Any]]:
    prefix = symbol.replace("USDT", "")
    generated = case_root / symbol / "generated"
    profile = load_json(profile_root / symbol / "SYMBOL_STRUCTURAL_PROFILE.json", {})
    timeline = OUTCOME.primary_rows(load_csv(generated / f"{prefix}_CAUSAL_TIMELINE.csv"))
    reviewed = PROFILE.effective_review(
        load_json(generated / f"{prefix}_REVIEWED_STATE_LEDGER.json", [])
    )
    campaigns = profile.get("campaigns", [])
    metrics = []
    for index, campaign in enumerate(campaigns):
        start = iso_to_ms(campaign.get("start"))
        end = iso_to_ms(campaign.get("end"))
        if start is None or end is None:
            continue
        transitions = [
            item for item in reviewed
            if start <= int(item["timestamp"]) <= end
        ]
        valid = [
            item for item in transitions
            if item.get("effective_status") in {"PASS", "RESTRICT"}
        ]
        birth = int(valid[0]["timestamp"]) if valid else start
        early = first_valid_time(transitions, "EARLY_BUILD")
        confirmed = first_valid_time(transitions, "CONFIRMED_BUILD")
        ignition = first_valid_time(transitions, "IGNITION_CANDIDATE")
        acceptance = first_valid_time(transitions, "ACCEPTED_IGNITION")
        expansion = first_valid_time(transitions, "EXPANSION")
        failure = first_valid_time(transitions, "FAILURE")
        depth = reset_depth(timeline, campaigns[index - 1] if index else None, birth)
        metrics.append(
            {
                "symbol": symbol,
                "campaign_index": campaign.get("campaign_index"),
                "profile_outcome": campaign.get("outcome"),
                "campaign_start": campaign.get("start"),
                "campaign_end": campaign.get("end"),
                "campaign_duration_minutes": minutes_between(start, end),
                "birth_time": ms_to_iso(birth),
                "early_build_time": ms_to_iso(early),
                "confirmed_build_time": ms_to_iso(confirmed),
                "ignition_time": ms_to_iso(ignition),
                "acceptance_time": ms_to_iso(acceptance),
                "expansion_time": ms_to_iso(expansion),
                "failure_time": ms_to_iso(failure),
                "birth_to_ignition_minutes": minutes_between(birth, ignition),
                "confirmed_to_ignition_minutes": minutes_between(confirmed, ignition),
                "ignition_to_acceptance_minutes": minutes_between(ignition, acceptance),
                "acceptance_to_expansion_minutes": minutes_between(acceptance, expansion),
                "campaign_age_at_acceptance_minutes": minutes_between(birth, acceptance),
                "campaign_age_at_expansion_minutes": minutes_between(birth, expansion),
                "leading_mechanism": leading_mechanism(transitions),
                "valid_transition_count": len(valid),
                "rejected_transition_count": sum(
                    str(item.get("effective_status", "")).startswith("REJECT")
                    for item in transitions
                ),
                **depth,
            }
        )
    return metrics


def summarize_mechanisms(symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes: dict[str, Any] = {}
    for outcome in sorted({str(row.get("profile_outcome")) for row in rows}):
        selected = [row for row in rows if str(row.get("profile_outcome")) == outcome]
        outcomes[outcome] = {
            "campaigns": len(selected),
            "median_birth_to_ignition_minutes": median(
                [row.get("birth_to_ignition_minutes") for row in selected]
            ),
            "median_campaign_age_at_acceptance_minutes": median(
                [row.get("campaign_age_at_acceptance_minutes") for row in selected]
            ),
            "median_price_reset_depth_pct": median(
                [row.get("price_reset_depth_pct") for row in selected]
            ),
            "median_oi_reset_depth_pct": median(
                [row.get("oi_reset_depth_pct") for row in selected]
            ),
            "leading_mechanism_counts": dict(
                Counter(str(row.get("leading_mechanism")) for row in selected)
            ),
        }
    return {"symbol": symbol, "campaigns": len(rows), "outcome_groups": outcomes}


def render_source_sensitivity(summary: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {item['policy']} | {item['valid_signature_same_as_default']} | "
        f"{item['valid_transition_symmetric_difference']} | {item['proposed_transitions']} | "
        f"{json.dumps(item['review_counts'], sort_keys=True)} |"
        for item in summary["policies"]
    )
    conflict = summary["conflicts"]
    return f"""# {summary['symbol']} Source-Selection Sensitivity

This audit reconstructs the reviewed path under multiple deterministic source-selection policies. It does not average conflicting rows or create synthetic candles.

- Status: `{summary['sensitivity_status']}`
- Overlap groups: {conflict['overlap_groups']}
- Material conflict groups: {conflict['material_conflict_groups']}
- Decision-relevant conflict groups: {conflict['decision_relevant_conflict_groups']}
- Conflict fields: `{json.dumps(conflict['field_counts'], sort_keys=True)}`

| Policy | Same valid path | Valid transition symmetric difference | Proposed transitions | Review counts |
|---|---|---:|---:|---|
{rows}

## Interpretation

{summary['interpretation']}

A stable result means only that the current research engine is insensitive to the tested source policies. It does not prove that every conflicting field is correct.
"""


def render_negative_summary(summary: dict[str, Any]) -> str:
    stage_rows = "\n".join(
        f"| {stage} | {item['observations']} | {item['complete_observations']} | "
        f"{item['median_terminal_return_pct']} | {json.dumps(item['path_class_counts'], sort_keys=True)} |"
        for stage, item in summary["stage_summaries"].items()
    ) or "| — | 0 | 0 | — | {} |"
    discrimination_rows = "\n".join(
        f"| {item['stage']} | {item['valid_complete_observations']} | "
        f"{item['rejected_complete_observations']} | {item['valid_median_terminal_return_pct']} | "
        f"{item['rejected_median_terminal_return_pct']} | {item['discrimination_status']} |"
        for item in summary["discrimination"]
    ) or "| — | 0 | 0 | — | — | NO_PAIRED_SAMPLE |"
    return f"""# {summary['symbol']} Rejected-Transition Negative Controls

Rejected transitions remain invalid historical decisions. Their future paths are measured only to test whether the review gate discriminated useful from misleading proposals.

- Negative anchors: {summary['negative_anchor_count']}
- Outcome rows: {summary['outcome_rows']}
- Comparison horizon: {summary['comparison_horizon_minutes']} minutes

| Proposed state | Observations | Complete | Median terminal return % | Path classes |
|---|---:|---:|---:|---|
{stage_rows}

## Valid versus rejected proposals

| Stage | Valid complete | Rejected complete | Valid median terminal % | Rejected median terminal % | Discrimination |
|---|---:|---:|---:|---:|---|
{discrimination_rows}

No rejected transition is retroactively promoted because its future path happened to be positive.
"""


def render_mechanism_summary(summary: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {outcome} | {item['campaigns']} | {item['median_birth_to_ignition_minutes']} | "
        f"{item['median_campaign_age_at_acceptance_minutes']} | {item['median_price_reset_depth_pct']} | "
        f"{item['median_oi_reset_depth_pct']} | {json.dumps(item['leading_mechanism_counts'], sort_keys=True)} |"
        for outcome, item in summary["outcome_groups"].items()
    ) or "| — | 0 | — | — | — | — | {} |"
    return f"""# {summary['symbol']} Campaign Mechanism Metrics

Campaigns are measured independently against the symbol's own timeline. Missing stages remain missing; they are not inferred.

| Outcome | Campaigns | Median birth→ignition min | Median age at acceptance min | Median price reset depth % | Median OI reset depth % | Leading mechanisms |
|---|---:|---:|---:|---:|---:|---|
{rows}

Reset depth is measured from the prior campaign's observed peak to the next campaign birth only when no observation gap interrupts the interval.
"""


def lifecycle_decisions(
    negative_summaries: list[dict[str, Any]],
    source_summaries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    bank_source = source_summaries.get("BANKUSDT", {})
    lyn_source = source_summaries.get("LYNUSDT", {})
    return [
        {
            "rule_id": "UNIVERSAL_IGNITION_SUFFICIENCY",
            "current_status": "REJECTED_RULE",
            "decision": "REJECT",
            "basis": "Valid ignition candidates remain mixed within symbols and rejected proposals can also have positive future paths.",
            "limitations": "No universal stage meaning is permitted.",
        },
        {
            "rule_id": "UNIVERSAL_ACCEPTANCE_SUFFICIENCY",
            "current_status": "REJECTED_RULE",
            "decision": "REJECT",
            "basis": "Accepted-stage outcomes differ materially by symbol and campaign.",
            "limitations": "Acceptance must be interpreted through symbol-specific structure.",
        },
        {
            "rule_id": "BANK_STRICT_ACCEPTANCE_MECHANISM",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_HYPOTHESIS",
            "basis": f"Source sensitivity status: {bank_source.get('sensitivity_status', 'NOT_RUN')}; accepted sample remains small.",
            "limitations": "Requires more accepted and rejected BANK campaigns plus source provenance resolution.",
        },
        {
            "rule_id": "LYN_BUILD_PERSISTENCE_MECHANISM",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_HYPOTHESIS",
            "basis": f"Source sensitivity status: {lyn_source.get('sensitivity_status', 'NOT_RUN')}; build persistence remains symbol-specific.",
            "limitations": "Requires additional campaigns and explicit negative controls.",
        },
        {
            "rule_id": "ESPORTS_RECURRENT_CYCLE_MECHANISM",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_HYPOTHESIS",
            "basis": "Repeated build, rejection and rebuild episodes remain distinct in the reviewed ledger.",
            "limitations": "Cycle-frequency discriminators are not yet validated outside ESPORTS.",
        },
        {
            "rule_id": "AKE_GAP_AWARE_CAMPAIGN_AGE",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_HYPOTHESIS",
            "basis": "AKE contains explicit observation gaps and multiple independent campaigns.",
            "limitations": "Gap boundaries reduce sample size and prevent continuity claims.",
        },
    ]


def render_lifecycle(decisions: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f"| {item['rule_id']} | {item['current_status']} | {item['decision']} | "
        f"{item['basis']} | {item['limitations']} |"
        for item in decisions
    )
    return f"""# Rule Lifecycle Decisions — Mechanism Validation Pass

| Rule | Current status | Decision | Evidence basis | Unresolved limitations |
|---|---|---|---|---|
{rows}

No candidate is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` in this pass.
"""


def render_cross_synthesis(
    mechanism_summaries: list[dict[str, Any]],
    negative_summaries: list[dict[str, Any]],
    source_summaries: dict[str, dict[str, Any]],
) -> str:
    mechanism_rows = "\n".join(
        f"| {item['symbol']} | {item['campaigns']} | "
        f"{json.dumps({key: value['leading_mechanism_counts'] for key, value in item['outcome_groups'].items()}, sort_keys=True)} |"
        for item in mechanism_summaries
    )
    negative_rows = "\n".join(
        f"| {item['symbol']} | {item['negative_anchor_count']} | "
        f"{sum(1 for row in item['discrimination'] if row['discrimination_status'] == 'VALID_STAGE_DISCRIMINATES')} | "
        f"{sum(1 for row in item['discrimination'] if row['discrimination_status'] == 'NO_CLEAR_DISCRIMINATION')} |"
        for item in negative_summaries
    )
    source_rows = "\n".join(
        f"| {symbol} | {item['sensitivity_status']} | "
        f"{item['conflicts']['material_conflict_groups']} | "
        f"{item['conflicts']['decision_relevant_conflict_groups']} |"
        for symbol, item in source_summaries.items()
    ) or "| — | NOT_RUN | 0 | 0 |"
    return f"""# Symbol-Specific Mechanism Validation — Pass 2

## Campaign mechanisms

| Symbol | Campaigns | Leading mechanisms by outcome |
|---|---:|---|
{mechanism_rows}

## Rejected transitions as negative controls

| Symbol | Rejected anchors | Stages with discrimination | Stages without clear discrimination |
|---|---:|---:|---:|
{negative_rows}

A rejected cutoff is never converted into a valid historical signal because its future path was positive. The audit tests the review gate; it does not rewrite the frozen decision.

## Source-selection sensitivity

| Symbol | Status | Material conflict groups | Decision-relevant conflict groups |
|---|---|---:|---:|
{source_rows}

## Research status

- Shared states remain indexing vocabulary.
- Mechanism timing, reset depth and negative-control discrimination are interpreted within each symbol first.
- Cross-symbol transfer is not claimed.
- No durable rule is created.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--case-root", type=Path, default=Path("research/case_studies"))
    parser.add_argument("--profile-root", type=Path, default=Path("research/symbol_profiles"))
    parser.add_argument("--outcome-root", type=Path, default=Path("research/outcome_audits"))
    parser.add_argument("--output-root", type=Path, default=Path("research/mechanism_validation"))
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--source-sensitivity-symbols", nargs="*", default=["BANKUSDT", "LYNUSDT"])
    args = parser.parse_args()

    mechanism_summaries = []
    negative_summaries = []
    source_summaries: dict[str, dict[str, Any]] = {}

    for symbol in args.symbols:
        output_dir = args.output_root / symbol
        output_dir.mkdir(parents=True, exist_ok=True)

        mechanism_rows = campaign_mechanism_metrics(symbol, args.case_root, args.profile_root)
        mechanism_summary = summarize_mechanisms(symbol, mechanism_rows)
        mechanism_summaries.append(mechanism_summary)
        write_csv(output_dir / "CAMPAIGN_MECHANISM_METRICS.csv", mechanism_rows)
        (output_dir / "CAMPAIGN_MECHANISM_SUMMARY.json").write_text(
            json.dumps(mechanism_summary, indent=2), encoding="utf-8"
        )
        (output_dir / "CAMPAIGN_MECHANISM_SUMMARY.md").write_text(
            render_mechanism_summary(mechanism_summary), encoding="utf-8"
        )

        negative = audit_negative_controls(
            symbol, args.case_root, args.profile_root, args.outcome_root
        )
        negative_summaries.append(negative["summary"])
        write_csv(output_dir / "REJECTED_TRANSITION_OUTCOMES.csv", negative["rows"])
        write_csv(output_dir / "REJECTED_TRANSITION_MATCHED_CONTROLS.csv", negative["controls"])
        (output_dir / "REJECTED_TRANSITION_SUMMARY.json").write_text(
            json.dumps(negative["summary"], indent=2), encoding="utf-8"
        )
        (output_dir / "REJECTED_TRANSITION_SUMMARY.md").write_text(
            render_negative_summary(negative["summary"]), encoding="utf-8"
        )

    for symbol in args.source_sensitivity_symbols:
        sensitivity = source_sensitivity(symbol, args.root)
        source_summaries[symbol] = sensitivity
        output_dir = args.output_root / symbol
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "SOURCE_SELECTION_SENSITIVITY.json").write_text(
            json.dumps(sensitivity, indent=2), encoding="utf-8"
        )
        (output_dir / "SOURCE_SELECTION_SENSITIVITY.md").write_text(
            render_source_sensitivity(sensitivity), encoding="utf-8"
        )

    decisions = lifecycle_decisions(negative_summaries, source_summaries)
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "RULE_LIFECYCLE_DECISIONS_PASS2.json").write_text(
        json.dumps(decisions, indent=2), encoding="utf-8"
    )
    (args.output_root / "RULE_LIFECYCLE_DECISIONS_PASS2.md").write_text(
        render_lifecycle(decisions), encoding="utf-8"
    )
    (args.output_root / "MECHANISM_VALIDATION_SYNTHESIS_PASS2.md").write_text(
        render_cross_synthesis(mechanism_summaries, negative_summaries, source_summaries),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "symbols": len(args.symbols),
                "campaigns": sum(item["campaigns"] for item in mechanism_summaries),
                "negative_anchors": sum(item["negative_anchor_count"] for item in negative_summaries),
                "source_sensitivity_symbols": sorted(source_summaries),
            }
        )
    )


if __name__ == "__main__":
    main()
