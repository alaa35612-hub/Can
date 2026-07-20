from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TF_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
FIELDS = (
    "close", "rsi", "number_of_trades", "quote_volume", "avg_quote_per_trade",
    "taker_quote_imbalance_pct", "oi", "oi_value", "acco_ls_ratio",
    "posit_ls_ratio", "global_ls_ratio", "funding_rate",
)


def num(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def timeframe_of(path: Path):
    return next((tf for tf in TF_MS if f"_{tf}_" in path.name), None)


def load_symbol(root: Path, symbol: str):
    rows, sources = [], []
    for path in sorted(root.glob(f"{symbol}_*_enriched_candles.csv")):
        timeframe = timeframe_of(path)
        if not timeframe:
            continue
        sources.append(path.name)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                if raw.get("symbol") != symbol:
                    continue
                if str(raw.get("is_closed_candle", "")).lower() not in {"true", "1"}:
                    continue
                timestamp = int(float(raw.get("timestamp") or raw.get("open_time") or 0))
                row = {
                    "timestamp": timestamp,
                    "close_time": int(float(raw.get("close_time") or timestamp + TF_MS[timeframe] - 1)),
                    "timeframe": timeframe,
                    "source": path.name,
                }
                row.update({field: num(raw.get(field)) for field in FIELDS})
                rows.append(row)
    return sources, rows


def deduplicate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["timeframe"], row["timestamp"])].append(row)

    merged, conflicts = [], []
    for (timeframe, timestamp), group in groups.items():
        group.sort(
            key=lambda row: (sum(value is not None for value in row.values()), row["source"]),
            reverse=True,
        )
        chosen = group[0]
        merged.append(chosen)
        disagreements = []
        for other in group[1:]:
            fields = []
            for field in FIELDS:
                left, right = chosen.get(field), other.get(field)
                if left is None or right is None:
                    continue
                if abs(left - right) / max(abs(left), abs(right), 1e-12) > 1e-8:
                    fields.append(field)
            if fields:
                disagreements.append({"source": other["source"], "fields": fields})
        if disagreements:
            conflicts.append(
                {
                    "timeframe": timeframe,
                    "timestamp": timestamp,
                    "chosen": chosen["source"],
                    "conflicts": disagreements,
                }
            )
    return sorted(merged, key=lambda row: (row["timeframe"], row["timestamp"])), conflicts


def percentile_rank(value, history, minimum=24):
    if value is None or len(history) < minimum:
        return None
    less = sum(item < value for item in history)
    equal = sum(item == value for item in history)
    return (less + 0.5 * equal) / len(history)


def percent_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def enrich(rows):
    by_timeframe = defaultdict(list)
    for row in rows:
        by_timeframe[row["timeframe"]].append(row)

    enriched = []
    for timeframe, sequence in by_timeframe.items():
        sequence.sort(key=lambda row: row["timestamp"])
        histories = defaultdict(list)
        previous = None
        for row in sequence:
            current = dict(row)
            current["price_change_pct"] = percent_change(current["close"], previous["close"] if previous else None)
            current["oi_change_pct"] = percent_change(current["oi"], previous["oi"] if previous else None)
            for field in ("number_of_trades", "quote_volume", "oi", "oi_value", "avg_quote_per_trade"):
                current[field + "_rank"] = percentile_rank(current[field], histories[field])
            absolute_return = abs(current["price_change_pct"]) if current["price_change_pct"] is not None else None
            current["price_abs_rank"] = percentile_rank(absolute_return, histories["absolute_return"])
            enriched.append(current)
            for field in ("number_of_trades", "quote_volume", "oi", "oi_value", "avg_quote_per_trade"):
                if current[field] is not None:
                    histories[field].append(current[field])
            if absolute_return is not None:
                histories["absolute_return"].append(absolute_return)
            previous = current
    return sorted(enriched, key=lambda row: (row["timestamp"], TF_MS[row["timeframe"]]))


def latest_closed(rows, timeframe, cutoff):
    candidates = [row for row in rows if row["timeframe"] == timeframe and row["close_time"] <= cutoff]
    return candidates[-1] if candidates else None


def high_rank(value, peer_values):
    values = [item for item in peer_values if item is not None]
    if value is None or not values:
        return False
    return value >= statistics.median(values)


def split_primary(rows, gap_multiple=4):
    primary = sorted((row for row in rows if row["timeframe"] == "15m"), key=lambda row: row["timestamp"])
    if not primary:
        return []
    groups = [[primary[0]]]
    for row in primary[1:]:
        if row["timestamp"] - groups[-1][-1]["timestamp"] > gap_multiple * TF_MS["15m"]:
            groups.append([])
        groups[-1].append(row)
    return groups


def build_segment_ledger(symbol, all_rows, primary_rows, segment_id):
    state = "LATENT"
    campaign_id = None
    persistence = 0
    opposition = 0
    transitions = []

    for index, row in enumerate(primary_rows):
        execution_rank = max(
            [rank for rank in (row.get("number_of_trades_rank"), row.get("quote_volume_rank")) if rank is not None],
            default=None,
        )
        history_ranks = [
            item.get("number_of_trades_rank")
            for item in primary_rows[:index]
            if item.get("number_of_trades_rank") is not None
        ]
        execution_expansion = execution_rank is not None and high_rank(execution_rank, history_ranks[-32:])
        execution_shock = execution_rank is not None and execution_rank >= max(history_ranks[-32:], default=execution_rank)
        abnormal_price = row.get("price_abs_rank") is not None and high_rank(
            row["price_abs_rank"],
            [item.get("price_abs_rank") for item in primary_rows[:index]][-32:],
        )

        price_change = row.get("price_change_pct") or 0.0
        oi_change = row.get("oi_change_pct")
        oi_rank = row.get("oi_rank")
        oi_history = [item.get("oi_rank") for item in primary_rows[:index] if item.get("oi_rank") is not None]
        oi_expansion = oi_change is not None and oi_change > 0 and high_rank(oi_rank, oi_history[-32:])
        oi_contraction = oi_change is not None and oi_change < 0 and oi_rank is not None and not high_rank(oi_rank, oi_history[-32:])

        positive_release = abnormal_price and price_change > 0 and (
            row.get("taker_quote_imbalance_pct") is None or row["taker_quote_imbalance_pct"] > -20
        )
        negative_dislocation = abnormal_price and price_change < 0 and (
            row.get("taker_quote_imbalance_pct") is None or row["taker_quote_imbalance_pct"] < 20
        )

        higher = {tf: latest_closed(all_rows, tf, row["close_time"]) for tf in ("1h", "4h", "1d")}
        higher_support = sum(1 for item in higher.values() if item and (item.get("price_change_pct") or 0) > 0)
        higher_opposition = sum(1 for item in higher.values() if item and (item.get("price_change_pct") or 0) < 0)

        support_count = sum((execution_expansion, oi_expansion, positive_release, higher_support >= 2))
        opposition_count = sum((oi_contraction, negative_dislocation, higher_opposition >= 2))
        persistence = persistence + 1 if support_count >= 2 else max(0, persistence - 1)
        opposition = opposition + 1 if opposition_count >= 2 else max(0, opposition - 1)

        facts = []
        if execution_shock:
            facts.append("execution_shock")
        elif execution_expansion:
            facts.append("execution_expansion")
        if oi_expansion:
            facts.append("oi_expansion")
        if oi_contraction:
            facts.append("oi_contraction")
        if positive_release:
            facts.append("positive_price_release")
        if negative_dislocation:
            facts.append("negative_price_dislocation")
        if higher_support >= 2:
            facts.append("higher_timeframe_support")
        if higher_opposition >= 2:
            facts.append("higher_timeframe_opposition")

        candidate = state
        rationale = []

        if state in {"LATENT", "FAILURE", "RESET"} and (
            (execution_expansion and (oi_expansion or positive_release))
            or (oi_expansion and not abnormal_price)
        ):
            candidate = "EARLY_BUILD"
            rationale.append("relative fuel/execution changed before or with price response")

        if candidate == "EARLY_BUILD" and persistence >= 2:
            candidate = "CONFIRMED_BUILD"
            rationale.append("support persisted across successive observations")

        if candidate in {"EARLY_BUILD", "CONFIRMED_BUILD"} and execution_shock and positive_release:
            candidate = "IGNITION_CANDIDATE"
            rationale.append("relative execution extreme aligned with positive release")

        if state == "IGNITION_CANDIDATE" and index:
            previous = primary_rows[index - 1]
            retained = (
                previous.get("price_change_pct") or 0
            ) > 0 and row.get("close") and previous.get("close") and row["close"] / previous["close"] >= 0.94
            if retained and not oi_contraction:
                candidate = "ACCEPTED_IGNITION"
                rationale.append("post-release retention without immediate OI collapse")
            elif opposition >= 2:
                candidate = "FAILURE"
                rationale.append("opposition persisted after ignition proposal")

        if state == "ACCEPTED_IGNITION":
            if support_count >= 2 and positive_release:
                candidate = "EXPANSION"
                rationale.append("accepted structure received fresh independent support")
            elif opposition >= 2:
                candidate = "COOLING"
                rationale.append("opposition increased after acceptance")

        if state == "EXPANSION":
            if execution_expansion and not oi_contraction:
                candidate = "CONTINUATION_RELOAD"
                rationale.append("execution persisted without fuel collapse")
            elif opposition >= 2:
                candidate = "COOLING"
                rationale.append("persistent opposition")

        if state in {"COOLING", "CONTINUATION_RELOAD"}:
            if execution_shock and positive_release and not oi_contraction:
                candidate = "CONTINUATION_RELOAD"
                rationale.append("fresh relative execution release")
            elif opposition >= 3:
                candidate = "FAILURE"
                rationale.append("opposition exceeded campaign tolerance")

        if candidate != state:
            if candidate == "EARLY_BUILD" and campaign_id is None:
                stamp = datetime.fromtimestamp(row["timestamp"] / 1000, tz=timezone.utc)
                campaign_id = f"{symbol}-15m-{stamp:%Y%m%d-%H%M}-S{segment_id}"

            hypothesis = (
                "Quiet build" if candidate in {"EARLY_BUILD", "CONFIRMED_BUILD"}
                else "Execution-led ignition" if candidate == "IGNITION_CANDIDATE"
                else "Accepted expansion/continuation" if candidate in {"ACCEPTED_IGNITION", "EXPANSION", "CONTINUATION_RELOAD"}
                else "Cooling versus distribution" if candidate == "COOLING"
                else "Failed/exhausted campaign"
            )
            transitions.append(
                {
                    "symbol": symbol,
                    "segment_id": segment_id,
                    "campaign_id": campaign_id,
                    "timestamp": row["timestamp"],
                    "time": datetime.fromtimestamp(row["timestamp"] / 1000, tz=timezone.utc).isoformat(),
                    "from_state": state,
                    "to_state": candidate,
                    "facts_added": facts,
                    "rationale": rationale,
                    "supporting_score": support_count,
                    "opposing_score": opposition_count,
                    "dominant_hypothesis": hypothesis,
                    "alternative_hypotheses": [
                        "Short-covering only",
                        "Transient event spike",
                        "New unidentified structure",
                    ],
                    "higher_timeframes_visible": {
                        tf: item["timestamp"] if item else None for tf, item in higher.items()
                    },
                    "cutoff_frozen": True,
                }
            )
            state = candidate
            if state == "FAILURE":
                campaign_id = None
                persistence = 0
                opposition = 0
    return transitions


def build_ledger(symbol, rows):
    higher = [row for row in rows if row["timeframe"] != "15m"]
    segments = split_primary(rows)
    combined = []
    for segment_id, primary in enumerate(segments, 1):
        segment_rows = sorted(higher + primary, key=lambda row: (row["timestamp"], TF_MS[row["timeframe"]]))
        if combined and primary:
            timestamp = primary[0]["timestamp"]
            combined.append(
                {
                    "symbol": symbol,
                    "segment_id": segment_id,
                    "campaign_id": None,
                    "timestamp": timestamp,
                    "time": datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat(),
                    "from_state": "UNOBSERVED_GAP",
                    "to_state": "RESET",
                    "facts_added": ["data_gap_campaign_boundary"],
                    "rationale": ["continuity cannot be verified across missing primary observations"],
                    "supporting_score": 0,
                    "opposing_score": 0,
                    "dominant_hypothesis": "New campaign must be reconstructed independently",
                    "alternative_hypotheses": ["Continuation remains unverified"],
                    "higher_timeframes_visible": {},
                    "cutoff_frozen": True,
                }
            )
        combined.extend(build_segment_ledger(symbol, segment_rows, primary, segment_id))
    return combined, len(segments)


def choose_controls(rows, ledger, limit=5):
    primary = [row for row in rows if row["timeframe"] == "15m"]
    transition_times = {item["timestamp"] for item in ledger}
    controls = []
    for index in range(8, len(primary) - 4):
        if any(abs(primary[index]["timestamp"] - timestamp) <= 8 * TF_MS["15m"] for timestamp in transition_times):
            continue
        window = primary[index - 4:index + 5]
        execution = max(
            max(item.get("number_of_trades_rank") or -1, item.get("quote_volume_rank") or -1)
            for item in window
        )
        movement = max(item.get("price_abs_rank") or -1 for item in window)
        historical_execution = [
            max(item.get("number_of_trades_rank") or -1, item.get("quote_volume_rank") or -1)
            for item in primary[:index]
        ]
        historical_movement = [item.get("price_abs_rank") or -1 for item in primary[:index]]
        if execution <= statistics.median(historical_execution) and movement <= statistics.median(historical_movement):
            controls.append(
                {
                    "center_timestamp": primary[index]["timestamp"],
                    "center_time": datetime.fromtimestamp(primary[index]["timestamp"] / 1000, tz=timezone.utc).isoformat(),
                    "window_candles": 9,
                    "selection_reason": "ordinary same-asset causal window",
                }
            )
        if len(controls) >= limit:
            break
    return controls


def adversarial_review(item, row):
    status, reasons = "PASS", []
    target = item.get("to_state")
    facts = set(item.get("facts_added") or [])
    negative = "negative_price_dislocation" in facts

    if target == "ACCEPTED_IGNITION" and negative:
        status = "REJECT"
        reasons.append("acceptance conflicts with abnormal negative-price dislocation")
    if target == "EXPANSION":
        if item.get("supporting_score", 0) < 2:
            status = "REJECT"
            reasons.append("expansion lacks two independent current-cutoff supports")
        if negative:
            status = "REJECT"
            reasons.append("expansion conflicts with abnormal negative response")
    if target == "CONTINUATION_RELOAD" and negative:
        status = "RESTRICT"
        reasons.append("continuation remains possible but negative response caps confidence")
    if target in {"EARLY_BUILD", "CONFIRMED_BUILD"} and negative:
        status = "RESTRICT"
        reasons.append("fuel evidence exists but direction is unresolved")
    if target == "ACCEPTED_IGNITION" and not (
        {"execution_expansion", "execution_shock", "oi_expansion", "positive_price_release"} & facts
    ):
        if status == "PASS":
            status = "RESTRICT"
        reasons.append("acceptance relies mainly on retention and needs independent confirmation")
    if not reasons:
        reasons.append("no adversarial rejection condition triggered")

    reviewed = dict(item)
    reviewed["adversarial_status"] = status
    reviewed["adversarial_reasons"] = reasons
    reviewed["contemporary_close"] = row.get("close") if row else None
    reviewed["contemporary_price_change_pct"] = row.get("price_change_pct") if row else None
    return reviewed


def write_outputs(output_dir, symbol, sources, rows, conflicts, ledger, controls, segments):
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = symbol.replace("USDT", "")
    fields = sorted({key for row in rows for key in row})
    with (output_dir / f"{prefix}_CAUSAL_TIMELINE.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    timeline = {row["timestamp"]: row for row in rows if row["timeframe"] == "15m"}
    reviewed = [adversarial_review(item, timeline.get(item["timestamp"])) for item in ledger]
    counts = {status: sum(item["adversarial_status"] == status for item in reviewed) for status in ("PASS", "RESTRICT", "REJECT")}

    (output_dir / f"{prefix}_STATE_LEDGER.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    (output_dir / f"{prefix}_REVIEWED_STATE_LEDGER.json").write_text(json.dumps(reviewed, indent=2), encoding="utf-8")
    (output_dir / f"{prefix}_BLIND_REPLAY_TRACE.jsonl").write_text(
        "\n".join(json.dumps(item) for item in reviewed) + "\n", encoding="utf-8"
    )
    (output_dir / f"{prefix}_CONTROL_WINDOWS.json").write_text(json.dumps(controls, indent=2), encoding="utf-8")
    (output_dir / f"{prefix}_SOURCE_CONFLICTS.json").write_text(json.dumps(conflicts, indent=2), encoding="utf-8")
    (output_dir / f"{prefix}_REVIEW_SUMMARY.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")

    rows_md = "\n".join(
        f"| {item['time']} | {item['from_state']} → {item['to_state']} | {item['adversarial_status']} | {'; '.join(item['adversarial_reasons'])} |"
        for item in reviewed
    )
    report = f"""# {symbol} Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
""" + "\n".join(f"- `{source}`" for source in sources) + f"""

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
{rows_md or '| — | — | — | no transition |'}

## Run summary

- Sources: {len(sources)}
- Causal rows: {len(rows)}
- Segments: {segments}
- Proposed transitions: {len(ledger)}
- PASS: {counts['PASS']}
- RESTRICT: {counts['RESTRICT']}
- REJECT: {counts['REJECT']}
- Control windows: {len(controls)}
- Preserved source conflicts: {len(conflicts)}
- No rule is promoted to durable status from this single case.
"""
    (output_dir / f"{prefix}_CAMPAIGN_RECONSTRUCTION.md").write_text(report, encoding="utf-8")
    summary = {
        "symbol": symbol,
        "sources": len(sources),
        "causal_rows": len(rows),
        "segments": segments,
        "transitions": len(ledger),
        "controls": len(controls),
        "source_conflicts": len(conflicts),
        "review": counts,
    }
    (output_dir / f"{prefix}_RUN_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_symbol(root: Path, symbol: str, output_root: Path):
    sources, raw = load_symbol(root, symbol)
    if not sources:
        raise SystemExit(f"No CSV files found for {symbol}")
    merged, conflicts = deduplicate(raw)
    rows = enrich(merged)
    ledger, segments = build_ledger(symbol, rows)
    controls = choose_controls(rows, ledger)
    output_dir = output_root / symbol / "generated"
    return write_outputs(output_dir, symbol, sources, rows, conflicts, ledger, controls, segments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-root", type=Path, default=Path("research/case_studies"))
    parser.add_argument("--symbols", nargs="+", required=True)
    args = parser.parse_args()
    summaries = [run_symbol(args.root, symbol, args.output_root) for symbol in args.symbols]
    print(json.dumps(summaries))


if __name__ == "__main__":
    main()
