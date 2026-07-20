from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MINUTE_MS = 60_000
PRIMARY_TF = "15m"
STAGES = ("EARLY_BUILD", "CONFIRMED_BUILD", "IGNITION_CANDIDATE", "ACCEPTED_IGNITION", "EXPANSION")


def load_profile_module() -> Any:
    path = Path(__file__).resolve().parent / "build_symbol_profiles.py"
    spec = importlib.util.spec_from_file_location("symbol_profiles", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROFILE = load_profile_module()


def f(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def percentile(values: list[float], p: float) -> float | None:
    return PROFILE.q(values, p)


def iso_to_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def ms_to_iso(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def primary_rows(timeline: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in timeline:
        if raw.get("timeframe") != PRIMARY_TF:
            continue
        timestamp = int(float(raw["timestamp"]))
        close = f(raw.get("close"))
        if close is None:
            continue
        row: dict[str, Any] = dict(raw)
        row["timestamp"] = timestamp
        row["close_time"] = int(float(raw.get("close_time") or timestamp + 900_000 - 1))
        row["close"] = close
        for key in (
            "price_change_pct",
            "price_abs_rank",
            "number_of_trades_rank",
            "quote_volume_rank",
            "number_of_trades_rz",
            "quote_volume_rz",
            "oi_rank",
            "oi_rz",
            "oi_change_pct",
            "quote_volume",
        ):
            row[key] = f(raw.get(key))
        rows.append(row)
    return sorted(rows, key=lambda row: row["timestamp"])


def adaptive_horizons(profile: dict[str, Any]) -> list[int]:
    lag = f((profile.get("execution_to_price_lag_minutes") or {}).get("median"))
    lag = 60.0 if lag is None else max(15.0, lag)
    lag = int(round(lag / 15.0) * 15)
    horizons = {lag, min(1440, lag * 4), min(1440, lag * 16), 60, 240, 720, 1440}
    return sorted(h for h in horizons if h >= 15)


def row_index_at_or_before(rows: list[dict[str, Any]], timestamp: int) -> int | None:
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid]["timestamp"] <= timestamp:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1 if lo else None


def path_metrics(rows: list[dict[str, Any]], anchor_timestamp: int, horizon_minutes: int) -> dict[str, Any] | None:
    anchor_index = row_index_at_or_before(rows, anchor_timestamp)
    if anchor_index is None:
        return None
    anchor = rows[anchor_index]
    if anchor["timestamp"] != anchor_timestamp:
        return None
    end_timestamp = anchor_timestamp + horizon_minutes * MINUTE_MS
    future: list[dict[str, Any]] = []
    gap_truncated = False
    previous_timestamp = anchor_timestamp
    for row in rows[anchor_index + 1 :]:
        if row["timestamp"] > end_timestamp:
            break
        if row["timestamp"] - previous_timestamp > 4 * 900_000:
            gap_truncated = True
            break
        future.append(row)
        previous_timestamp = row["timestamp"]
    if not future:
        return None
    base = anchor["close"]
    returns = [(row["close"] / base - 1.0) * 100.0 for row in future]
    first_positive = next((future[i]["timestamp"] for i, value in enumerate(returns) if value > 0), None)
    first_negative = next((future[i]["timestamp"] for i, value in enumerate(returns) if value < 0), None)
    return {
        "anchor_timestamp": anchor_timestamp,
        "anchor_close_time": anchor["close_time"],
        "horizon_minutes": horizon_minutes,
        "observed_minutes": int((future[-1]["timestamp"] - anchor_timestamp) / MINUTE_MS),
        "future_rows": len(future),
        "terminal_return_pct": returns[-1],
        "mfe_close_pct": max(returns),
        "mae_close_pct": min(returns),
        "first_positive_minutes": None if first_positive is None else int((first_positive - anchor_timestamp) / MINUTE_MS),
        "first_negative_minutes": None if first_negative is None else int((first_negative - anchor_timestamp) / MINUTE_MS),
        "coverage_complete": (not gap_truncated) and future[-1]["timestamp"] >= end_timestamp - 900_000,
        "gap_truncated": gap_truncated,
    }


def trailing_context(rows: list[dict[str, Any]], index: int, window: int = 16) -> dict[str, float | None]:
    sample = rows[max(0, index - window + 1) : index + 1]
    abs_returns = [abs(row["price_change_pct"]) for row in sample if row.get("price_change_pct") is not None]
    quote = [row["quote_volume"] for row in sample if row.get("quote_volume") is not None and row["quote_volume"] > 0]
    oi_moves = [abs(row["oi_change_pct"]) for row in sample if row.get("oi_change_pct") is not None]
    return {
        "volatility": percentile(abs_returns, 0.5),
        "quote_volume": percentile(quote, 0.5),
        "oi_movement": percentile(oi_moves, 0.5),
    }


def anomaly_level(row: dict[str, Any]) -> float:
    rank_values = [
        row.get("price_abs_rank"),
        row.get("number_of_trades_rank"),
        row.get("quote_volume_rank"),
        row.get("oi_rank"),
    ]
    rank_score = max((value for value in rank_values if value is not None), default=0.0)
    rz_values = [
        abs(row.get("number_of_trades_rz") or 0.0),
        abs(row.get("quote_volume_rz") or 0.0),
        abs(row.get("oi_rz") or 0.0),
    ]
    rz_score = max(rz_values, default=0.0) / 5.0
    return max(rank_score, min(1.0, rz_score))


def context_distance(left: dict[str, float | None], right: dict[str, float | None]) -> float:
    total = 0.0
    used = 0
    for key in ("volatility", "quote_volume", "oi_movement"):
        a, b = left.get(key), right.get(key)
        if a is None or b is None:
            continue
        if key == "quote_volume":
            if a <= 0 or b <= 0:
                continue
            total += abs(math.log(a / b))
        else:
            scale = max(abs(a), abs(b), 1e-12)
            total += abs(a - b) / scale
        used += 1
    return total / used if used else 999.0


def campaign_ranges(profile: dict[str, Any]) -> list[tuple[int, int]]:
    return [(iso_to_ms(item["start"]), iso_to_ms(item["end"])) for item in profile.get("campaigns", [])]


def outside_campaigns(timestamp: int, ranges: list[tuple[int, int]], buffer_minutes: int = 240) -> bool:
    buffer_ms = buffer_minutes * MINUTE_MS
    return all(timestamp < start - buffer_ms or timestamp > end + buffer_ms for start, end in ranges)


def matched_controls(
    rows: list[dict[str, Any]],
    anchor_timestamp: int,
    ranges: list[tuple[int, int]],
    max_horizon: int,
    limit: int = 12,
) -> list[dict[str, Any]]:
    anchor_index = row_index_at_or_before(rows, anchor_timestamp)
    if anchor_index is None or rows[anchor_index]["timestamp"] != anchor_timestamp:
        return []
    anchor_context = trailing_context(rows, anchor_index)
    last_usable = rows[-1]["timestamp"] - max_horizon * MINUTE_MS
    candidates: list[tuple[float, dict[str, Any]]] = []
    for index in range(16, len(rows)):
        row = rows[index]
        timestamp = row["timestamp"]
        if timestamp > last_usable or not outside_campaigns(timestamp, ranges):
            continue
        anomaly_inputs = [
            row.get("price_abs_rank"),
            row.get("number_of_trades_rank"),
            row.get("quote_volume_rank"),
            row.get("oi_rank"),
            row.get("number_of_trades_rz"),
            row.get("quote_volume_rz"),
            row.get("oi_rz"),
        ]
        if not any(value is not None for value in anomaly_inputs) or anomaly_level(row) >= 0.80:
            continue
        context = trailing_context(rows, index)
        distance = context_distance(anchor_context, context)
        if distance >= 999.0:
            continue
        candidates.append((distance, {"timestamp": timestamp, "distance": distance, "context": context}))
    candidates.sort(key=lambda pair: (pair[0], pair[1]["timestamp"]))
    selected: list[dict[str, Any]] = []
    spacing_ms = 240 * MINUTE_MS
    for _, candidate in candidates:
        if any(abs(candidate["timestamp"] - item["timestamp"]) < spacing_ms for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def empirical_percentile(value: float, controls: list[float]) -> float | None:
    if not controls:
        return None
    return sum(control <= value for control in controls) / len(controls)


def classify_path(metrics: dict[str, Any], control_metrics: list[dict[str, Any]]) -> tuple[str, dict[str, float | None]]:
    if not metrics.get("coverage_complete"):
        return "INCOMPLETE_FORWARD_COVERAGE", {
            "terminal_percentile": None,
            "mfe_percentile": None,
            "mae_percentile": None,
        }
    complete = [item for item in control_metrics if item and item.get("coverage_complete")]
    if len(complete) < 5:
        return "INSUFFICIENT_MATCHED_CONTROLS", {
            "terminal_percentile": None,
            "mfe_percentile": None,
            "mae_percentile": None,
        }
    terminal_controls = [item["terminal_return_pct"] for item in complete]
    mfe_controls = [item["mfe_close_pct"] for item in complete]
    mae_controls = [item["mae_close_pct"] for item in complete]
    ranks = {
        "terminal_percentile": empirical_percentile(metrics["terminal_return_pct"], terminal_controls),
        "mfe_percentile": empirical_percentile(metrics["mfe_close_pct"], mfe_controls),
        "mae_percentile": empirical_percentile(metrics["mae_close_pct"], mae_controls),
    }
    if ranks["mfe_percentile"] >= 0.80 and ranks["mae_percentile"] <= 0.20:
        label = "TWO_SIDED_VOLATILITY_OUTLIER"
    elif ranks["mfe_percentile"] >= 0.80 and ranks["terminal_percentile"] >= 0.60:
        label = "POSITIVE_PATH_OUTLIER"
    elif ranks["mae_percentile"] <= 0.20 and ranks["terminal_percentile"] <= 0.40:
        label = "NEGATIVE_PATH_OUTLIER"
    else:
        label = "MATCHED_CONTROL_LIKE"
    return label, ranks


def stage_anchors(reviewed: list[dict[str, Any]], campaign: dict[str, Any]) -> list[dict[str, Any]]:
    start = iso_to_ms(campaign["start"])
    end = iso_to_ms(campaign["end"])
    anchors: dict[str, dict[str, Any]] = {}
    for item in reviewed:
        timestamp = int(item["timestamp"])
        effective = item.get("effective_status", item.get("adversarial_status", "PASS"))
        stage = item.get("to_state")
        if start <= timestamp <= end and effective in {"PASS", "RESTRICT"} and stage in STAGES:
            anchors.setdefault(stage, item)
    return [anchors[stage] for stage in STAGES if stage in anchors]


def audit_symbol(symbol: str, case_root: Path, profile_root: Path, output_root: Path) -> dict[str, Any]:
    prefix = symbol.replace("USDT", "")
    generated = case_root / symbol / "generated"
    profile = load_json(profile_root / symbol / "SYMBOL_STRUCTURAL_PROFILE.json", {})
    rows = primary_rows(load_csv(generated / f"{prefix}_CAUSAL_TIMELINE.csv"))
    reviewed = PROFILE.effective_review(load_json(generated / f"{prefix}_REVIEWED_STATE_LEDGER.json", []))
    horizons = adaptive_horizons(profile)
    max_horizon = max(horizons)
    ranges = campaign_ranges(profile)
    audit_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    stage_counter: Counter[str] = Counter()
    label_counter: Counter[str] = Counter()

    for campaign in profile.get("campaigns", []):
        for anchor in stage_anchors(reviewed, campaign):
            anchor_timestamp = int(anchor["timestamp"])
            controls = matched_controls(rows, anchor_timestamp, ranges, max_horizon)
            for horizon in horizons:
                metrics = path_metrics(rows, anchor_timestamp, horizon)
                if metrics is None:
                    continue
                control_metrics: list[dict[str, Any]] = []
                for control in controls:
                    measured = path_metrics(rows, control["timestamp"], horizon)
                    if measured is None:
                        continue
                    measured["distance"] = control["distance"]
                    control_metrics.append(measured)
                    control_rows.append(
                        {
                            "symbol": symbol,
                            "campaign_index": campaign["campaign_index"],
                            "stage": anchor["to_state"],
                            "anchor_timestamp": anchor_timestamp,
                            "control_timestamp": control["timestamp"],
                            "control_time": ms_to_iso(control["timestamp"]),
                            "horizon_minutes": horizon,
                            **measured,
                        }
                    )
                label, ranks = classify_path(metrics, control_metrics)
                audit_rows.append(
                    {
                        "symbol": symbol,
                        "campaign_index": campaign["campaign_index"],
                        "campaign_profile_outcome": campaign["outcome"],
                        "stage": anchor["to_state"],
                        "stage_review_status": anchor.get("effective_status", anchor.get("adversarial_status", "PASS")),
                        "anchor_timestamp": anchor_timestamp,
                        "anchor_time": anchor.get("time") or ms_to_iso(anchor_timestamp),
                        "decision_available_time": ms_to_iso(metrics["anchor_close_time"]),
                        "horizon_minutes": horizon,
                        "matched_control_count": len(control_metrics),
                        "path_class": label,
                        **metrics,
                        **ranks,
                    }
                )
                stage_counter[anchor["to_state"]] += 1
                label_counter[label] += 1

    output_dir = output_root / symbol
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "CAMPAIGN_STAGE_OUTCOMES.csv", audit_rows)
    write_csv(output_dir / "MATCHED_CONTROL_OUTCOMES.csv", control_rows)
    summary = summarize_symbol(symbol, profile, horizons, audit_rows, stage_counter, label_counter)
    (output_dir / "SYMBOL_OUTCOME_AUDIT.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "SYMBOL_OUTCOME_AUDIT.md").write_text(render_symbol_summary(summary), encoding="utf-8")
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize_symbol(
    symbol: str,
    profile: dict[str, Any],
    horizons: list[int],
    rows: list[dict[str, Any]],
    stage_counter: Counter[str],
    label_counter: Counter[str],
) -> dict[str, Any]:
    longest = max(horizons)
    comparison_horizon = max(horizon for horizon in horizons if horizon <= 720)
    stage_summaries: dict[str, Any] = {}
    for stage in STAGES:
        all_stage_rows = [row for row in rows if row["stage"] == stage and row["horizon_minutes"] == comparison_horizon]
        stage_rows = [row for row in all_stage_rows if row.get("coverage_complete")]
        if not all_stage_rows:
            continue
        stage_summaries[stage] = {
            "campaign_observations": len(all_stage_rows),
            "complete_observations": len(stage_rows),
            "incomplete_observations": len(all_stage_rows) - len(stage_rows),
            "median_terminal_return_pct": percentile([row["terminal_return_pct"] for row in stage_rows], 0.5),
            "median_mfe_close_pct": percentile([row["mfe_close_pct"] for row in stage_rows], 0.5),
            "median_mae_close_pct": percentile([row["mae_close_pct"] for row in stage_rows], 0.5),
            "path_class_counts": dict(Counter(row["path_class"] for row in all_stage_rows)),
        }
    return {
        "symbol": symbol,
        "campaign_count": len(profile.get("campaigns", [])),
        "profile_campaign_outcomes": profile.get("campaign_outcome_counts", {}),
        "adaptive_horizons_minutes": horizons,
        "longest_horizon_minutes": longest,
        "comparison_horizon_minutes": comparison_horizon,
        "outcome_rows": len(rows),
        "stage_observation_counts_all_horizons": dict(stage_counter),
        "path_class_counts_all_horizons": dict(label_counter),
        "stage_summaries_at_longest_horizon": stage_summaries,
        "method_constraints": [
            "Original state decisions remain frozen; future paths are attached only after reconstruction.",
            "Metrics use 15m close paths because reconstructed timelines do not retain intrabar highs and lows.",
            "Controls are matched within the same symbol and exclude campaign neighborhoods.",
            "Path classes are descriptive relative to matched controls, not trade labels.",
            "Incomplete forward coverage remains explicit.",
        ],
    }


def render_symbol_summary(summary: dict[str, Any]) -> str:
    rows = []
    for stage, item in summary["stage_summaries_at_longest_horizon"].items():
        rows.append(
            f"| {stage} | {item['campaign_observations']} | {item['median_terminal_return_pct']} | "
            f"{item['median_mfe_close_pct']} | {item['median_mae_close_pct']} | "
            f"{json.dumps(item['path_class_counts'], sort_keys=True)} |"
        )
    table = "\n".join(rows) or "| — | 0 | — | — | — | {} |"
    return f"""# {summary['symbol']} Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: {summary['campaign_count']}
- Horizons: {', '.join(str(value) for value in summary['adaptive_horizons_minutes'])} minutes
- Longest audited horizon: {summary['longest_horizon_minutes']} minutes
- Comparison horizon: {summary['comparison_horizon_minutes']} minutes
- Outcome rows: {summary['outcome_rows']}

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
{table}

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and outside campaign neighborhoods.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
"""


def render_cross_symbol(summaries: list[dict[str, Any]]) -> str:
    rows = []
    for summary in summaries:
        accepted = summary["stage_summaries_at_longest_horizon"].get("ACCEPTED_IGNITION", {})
        ignition = summary["stage_summaries_at_longest_horizon"].get("IGNITION_CANDIDATE", {})
        rows.append(
            f"| {summary['symbol']} | {summary['campaign_count']} | "
            f"{ignition.get('campaign_observations', 0)} | {ignition.get('median_terminal_return_pct')} | "
            f"{accepted.get('campaign_observations', 0)} | {accepted.get('median_terminal_return_pct')} | "
            f"{json.dumps(accepted.get('path_class_counts', {}), sort_keys=True)} |"
        )
    return f"""# Symbol-Specific Campaign Outcome Comparison

This comparison is downstream of symbol-specific profiles. It compares mechanism performance without assuming one universal pattern.

| Symbol | Campaigns | Ignition observations | Ignition median terminal % | Accepted observations | Accepted median terminal % | Accepted path classes |
|---|---:|---:|---:|---:|---:|---|
{'\n'.join(rows)}

## Reading rule

- Compare stages within a symbol before comparing symbols.
- A stage name is shared vocabulary, not proof of shared causal structure.
- Control-relative path classes are descriptive and sample-size dependent.
- No durable rule is promoted by this pass alone.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, default=Path("research/case_studies"))
    parser.add_argument("--profile-root", type=Path, default=Path("research/symbol_profiles"))
    parser.add_argument("--output-root", type=Path, default=Path("research/outcome_audits"))
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()
    summaries = [audit_symbol(symbol, args.case_root, args.profile_root, args.output_root) for symbol in args.symbols]
    (args.output_root / "SYMBOL_SPECIFIC_OUTCOME_COMPARISON.md").write_text(render_cross_symbol(summaries), encoding="utf-8")
    print(json.dumps({"symbols": len(summaries), "outcome_rows": sum(item["outcome_rows"] for item in summaries)}))


if __name__ == "__main__":
    main()
