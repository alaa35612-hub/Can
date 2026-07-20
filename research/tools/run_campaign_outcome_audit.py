from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("campaign_outcomes_base", HERE / "audit_campaign_outcomes.py")
if not SPEC or not SPEC.loader:
    raise RuntimeError("Unable to load audit_campaign_outcomes.py")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


def effective_state_at(reviewed: list[dict[str, Any]], timestamp: int) -> tuple[str, int | None]:
    state = "LATENT"
    last_transition: int | None = None
    for item in reviewed:
        item_timestamp = int(item["timestamp"])
        if item_timestamp > timestamp:
            break
        effective = item.get("effective_status", item.get("adversarial_status", "PASS"))
        if effective not in {"PASS", "RESTRICT"}:
            continue
        state = item.get("to_state") or state
        last_transition = item_timestamp
    return state, last_transition


def matched_controls(
    rows: list[dict[str, Any]],
    anchor_timestamp: int,
    reviewed: list[dict[str, Any]],
    max_horizon: int,
    limit: int = 12,
) -> list[dict[str, Any]]:
    anchor_index = BASE.row_index_at_or_before(rows, anchor_timestamp)
    if anchor_index is None or rows[anchor_index]["timestamp"] != anchor_timestamp:
        return []
    anchor_context = BASE.trailing_context(rows, anchor_index)
    last_usable = rows[-1]["timestamp"] - max_horizon * BASE.MINUTE_MS
    preferred: list[tuple[float, dict[str, Any]]] = []
    fallback: list[tuple[float, dict[str, Any]]] = []

    for index in range(16, len(rows)):
        row = rows[index]
        timestamp = row["timestamp"]
        if timestamp > last_usable or timestamp == anchor_timestamp:
            continue
        state, last_transition = effective_state_at(reviewed, timestamp)
        if last_transition is not None and timestamp - last_transition < 240 * BASE.MINUTE_MS:
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
        if not any(value is not None for value in anomaly_inputs) or BASE.anomaly_level(row) >= 0.80:
            continue
        context = BASE.trailing_context(rows, index)
        distance = BASE.context_distance(anchor_context, context)
        if distance >= 999.0:
            continue
        inactive = state in {"LATENT", "FAILURE", "RESET", "COOLING"}
        candidate = {
            "timestamp": timestamp,
            "distance": distance,
            "context": context,
            "causal_state": state,
            "control_tier": "CAUSAL_INACTIVE" if inactive else "QUIET_NON_TRANSITION_FALLBACK",
        }
        (preferred if inactive else fallback).append((distance, candidate))

    preferred.sort(key=lambda pair: (pair[0], pair[1]["timestamp"]))
    fallback.sort(key=lambda pair: (pair[0], pair[1]["timestamp"]))
    selected: list[dict[str, Any]] = []
    spacing_ms = 240 * BASE.MINUTE_MS
    for _, candidate in preferred + fallback:
        if any(abs(candidate["timestamp"] - item["timestamp"]) < spacing_ms for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def audit_symbol(symbol: str, case_root: Path, profile_root: Path, output_root: Path) -> dict[str, Any]:
    prefix = symbol.replace("USDT", "")
    generated = case_root / symbol / "generated"
    profile = BASE.load_json(profile_root / symbol / "SYMBOL_STRUCTURAL_PROFILE.json", {})
    rows = BASE.primary_rows(BASE.load_csv(generated / f"{prefix}_CAUSAL_TIMELINE.csv"))
    reviewed = BASE.PROFILE.effective_review(
        BASE.load_json(generated / f"{prefix}_REVIEWED_STATE_LEDGER.json", [])
    )
    horizons = BASE.adaptive_horizons(profile)
    max_horizon = max(horizons)
    audit_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    stage_counter: Counter[str] = Counter()
    label_counter: Counter[str] = Counter()

    for campaign in profile.get("campaigns", []):
        for anchor in BASE.stage_anchors(reviewed, campaign):
            anchor_timestamp = int(anchor["timestamp"])
            controls = matched_controls(rows, anchor_timestamp, reviewed, max_horizon)
            for horizon in horizons:
                metrics = BASE.path_metrics(rows, anchor_timestamp, horizon)
                if metrics is None:
                    continue
                control_metrics: list[dict[str, Any]] = []
                for control in controls:
                    measured = BASE.path_metrics(rows, control["timestamp"], horizon)
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
                            "control_time": BASE.ms_to_iso(control["timestamp"]),
                            "control_causal_state": control["causal_state"],
                            "control_tier": control["control_tier"],
                            "horizon_minutes": horizon,
                            **measured,
                        }
                    )
                label, ranks = BASE.classify_path(metrics, control_metrics)
                audit_rows.append(
                    {
                        "symbol": symbol,
                        "campaign_index": campaign["campaign_index"],
                        "campaign_profile_outcome": campaign["outcome"],
                        "stage": anchor["to_state"],
                        "stage_review_status": anchor.get(
                            "effective_status", anchor.get("adversarial_status", "PASS")
                        ),
                        "anchor_timestamp": anchor_timestamp,
                        "anchor_time": anchor.get("time") or BASE.ms_to_iso(anchor_timestamp),
                        "decision_available_time": BASE.ms_to_iso(metrics["anchor_close_time"]),
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
    BASE.write_csv(output_dir / "CAMPAIGN_STAGE_OUTCOMES.csv", audit_rows)
    BASE.write_csv(output_dir / "MATCHED_CONTROL_OUTCOMES.csv", control_rows)
    summary = BASE.summarize_symbol(
        symbol, profile, horizons, audit_rows, stage_counter, label_counter
    )
    summary["control_definition"] = (
        "Same-symbol context matches prefer causal LATENT/FAILURE/RESET/COOLING cutoffs; "
        "quiet non-transition cutoffs are used only as an explicit fallback."
    )
    summary["method_constraints"] = [
        item.replace(
            "Controls are matched within the same symbol and exclude campaign neighborhoods.",
            "Controls prefer causal inactive states; quiet non-transition controls are an explicit fallback.",
        )
        for item in summary["method_constraints"]
    ]
    (output_dir / "SYMBOL_OUTCOME_AUDIT.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    report = BASE.render_symbol_summary(summary).replace(
        "outside campaign neighborhoods", "from causal inactive states with a labeled quiet fallback"
    )
    (output_dir / "SYMBOL_OUTCOME_AUDIT.md").write_text(report, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, default=Path("research/case_studies"))
    parser.add_argument("--profile-root", type=Path, default=Path("research/symbol_profiles"))
    parser.add_argument("--output-root", type=Path, default=Path("research/outcome_audits"))
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()
    summaries = [
        audit_symbol(symbol, args.case_root, args.profile_root, args.output_root)
        for symbol in args.symbols
    ]
    (args.output_root / "SYMBOL_SPECIFIC_OUTCOME_COMPARISON.md").write_text(
        BASE.render_cross_symbol(summaries), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "symbols": len(summaries),
                "outcome_rows": sum(item["outcome_rows"] for item in summaries),
            }
        )
    )


if __name__ == "__main__":
    main()
