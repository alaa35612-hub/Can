#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candle-by-candle backtest harness for V3.2.1-O uploaded Binance Futures cases.

The harness deliberately keeps future return labels outside the scanner call.  At
bar ``i`` it invokes the V3.2.1-O engine with ``candles[: i + 1]`` only; future
windows are calculated afterward for evaluation/reporting.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import math
import re
import statistics
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENGINE_PATH = Path(__file__).with_name("2_v321_operational_v321o_patch1.py")
REPORT_DIR = Path("backtest_reports_v321o")

FAILURE_REASONS = [
    "BASE_NOT_DETECTED",
    "PRICE_LED_MOVE_CLASSIFIED_MIXED",
    "QUOTE_VOLUME_MISSING_DOWNGRADED_TOO_HARD",
    "OI_FLAT_DOWN_REJECTED_WRONGLY",
    "TOP_POSITION_RETENTION_TOO_STRICT",
    "DELAYED_OI_RELOAD_NOT_RECOGNIZED",
    "TRIGGER_DETECTED_TOO_LATE",
    "ACCEPTANCE_TOO_STRICT",
    "LATE_RISK_OVERRIDE_TOO_AGGRESSIVE",
    "DATA_PARSING_LOSS",
]

READINESS_BY_MODE = {
    "early_watch": {"Primed Structure", "Early-Live Structure", "Confirmed Trigger", "Accepted Structure"},
    "strict_live": {"Early-Live Structure", "Confirmed Trigger", "Accepted Structure"},
}
ALLOWED_BIASES = {
    "Early Bullish Structure",
    "Early-Live Bullish Structure",
    "Bullish but Event-driven",
    "Neutral-to-Bullish Compression",
}
EXCLUDED_PATTERN_PARTS = (
    "Late Long Crowding",
    "Post-Pump Crowding Risk",
    "Failed",
    "Invalidated",
    "Bearish Structural Risk",
    "Distribution Risk",
    "Bot / Noise",
    "Bull Trap",
)


def load_engine_module() -> Any:
    spec = importlib.util.spec_from_file_location("v321o_engine", ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import engine from {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


engine_mod = load_engine_module()
Candle = engine_mod.Candle
Indicators = engine_mod.Indicators
Engine = engine_mod.StructuralLiquidityDiscoveryTreeV321
pct = engine_mod.pct
sf = engine_mod.sf
si = engine_mod.si


def clean_number(text: str, default: float = 0.0) -> float:
    text = str(text).replace(",", "").replace("%", "").strip()
    try:
        value = float(text)
        return value if math.isfinite(value) else default
    except Exception:
        return default


def parse_time_ms(text: str) -> int:
    dt = datetime.strptime(text.replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def lsp(ratio: float) -> Tuple[float, float]:
    r = max(0.0001, float(ratio or 1.0))
    long_pct = r / (1 + r) * 100
    return long_pct, 100 - long_pct


def row_to_candle(row: Dict[str, Any], fallback_symbol: str = "UNKNOWN") -> Any:
    symbol = str(row.get("symbol") or row.get("Symbol") or fallback_symbol).strip().upper()
    time_text = str(row.get("time") or row.get("Time") or "").strip()
    close = clean_number(row.get("close", row.get("Close", 0)))
    oi = clean_number(row.get("oi", row.get("OI", 0)))
    oi_chg = clean_number(row.get("oi_change", row.get("OI Chg", 0)))
    oi_chg_pct = clean_number(row.get("oi_change_pct", row.get("OI Chg %", 0)))
    account_lsr = clean_number(row.get("account_lsr", row.get("Acco L/S", row.get("Account L/S", 1))), 1)
    position_lsr = clean_number(row.get("position_lsr", row.get("Posit L/S", row.get("Position L/S", 1))), 1)
    global_lsr = clean_number(row.get("global_lsr", row.get("Global L/S", 1)), 1)
    account_long, account_short = lsp(account_lsr)
    position_long, position_short = lsp(position_lsr)
    global_long, global_short = lsp(global_lsr)
    if "Acco L%" in row:
        account_long = clean_number(row.get("Acco L%"), account_long)
        account_short = clean_number(row.get("Acco S%"), account_short)
    if "Posit L%" in row:
        position_long = clean_number(row.get("Posit L%"), position_long)
        position_short = clean_number(row.get("Posit S%"), position_short)
    if "Global L%" in row:
        global_long = clean_number(row.get("Global L%"), global_long)
        global_short = clean_number(row.get("Global S%"), global_short)
    volume = clean_number(row.get("volume", row.get("Volume", 0)))
    quote_volume = clean_number(row.get("quote_volume", row.get("Quote Volume", 0)))
    return Candle(
        time_ms=parse_time_ms(time_text),
        time=time_text,
        symbol=symbol,
        open=clean_number(row.get("open", row.get("Open", close)), close),
        high=clean_number(row.get("high", row.get("High", close)), close),
        low=clean_number(row.get("low", row.get("Low", close)), close),
        close=close,
        volume=volume,
        quote_volume=quote_volume,
        trades=si(row.get("trades", row.get("Trades", 0))),
        taker_buy_quote=clean_number(row.get("taker_buy_quote", 0)),
        rsi=clean_number(row.get("rsi", row.get("RSI", 50)), 50),
        oi=oi,
        oi_value=oi * close,
        oi_change=oi_chg,
        oi_change_pct=oi_chg_pct,
        account_lsr=account_lsr,
        account_long_pct=account_long,
        account_short_pct=account_short,
        position_lsr=position_lsr,
        position_long_pct=position_long,
        position_short_pct=position_short,
        global_lsr=global_lsr,
        global_long_pct=global_long,
        global_short_pct=global_short,
    )


TEXT_ROW_RE = re.compile(r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)\s*(?P<symbol>[A-Z0-9]+USDT)\s+(?P<rest>.+)$")


def parse_text_table(path: Path) -> List[Any]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    rows: List[Any] = []
    fallback_symbol = "UNKNOWN"
    m_symbol = re.search(r"SYMBOL\s*:\s*([A-Z0-9]+USDT)", text)
    if m_symbol:
        fallback_symbol = m_symbol.group(1)
    for raw in text.splitlines():
        m = TEXT_ROW_RE.match(raw.strip())
        if not m:
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", m.group("rest"))
        if len(nums) < 20:
            continue
        keys = [
            "Close", "RSI", "Trades", "OI", "OI Chg", "OI Chg %",
            "Acco L/S", "Acco Chg", "Acco Chg%", "Acco L%", "Acco S%",
            "Posit L/S", "Posit Chg", "Posit Chg%", "Posit L%", "Posit S%",
            "Global L/S", "Global Chg", "Global Chg%", "Global L%", "Global S%",
        ]
        row = {k: nums[i] for i, k in enumerate(keys) if i < len(nums)}
        row["Time"] = m.group("time")
        row["Symbol"] = m.group("symbol") or fallback_symbol
        rows.append(row_to_candle(row, fallback_symbol))
    return normalize_candles(rows)


def parse_csv_table(path: Path) -> List[Any]:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        rows = [row_to_candle(r, path.stem.upper()) for r in reader if r]
    return normalize_candles(rows)


def normalize_candles(candles: List[Any]) -> List[Any]:
    candles = sorted(candles, key=lambda c: c.time_ms)
    out: List[Any] = []
    seen = set()
    prev_oi: Optional[float] = None
    closes = [c.close for c in candles]
    rsi_values = Indicators.rsi(closes, 14) if closes else []
    for i, c in enumerate(candles):
        if c.time_ms in seen:
            continue
        seen.add(c.time_ms)
        if c.rsi <= 0 or c.rsi == 50:
            c.rsi = rsi_values[i] if i < len(rsi_values) else c.rsi
        if prev_oi is not None and (c.oi_change == 0 and c.oi != prev_oi):
            c.oi_change = c.oi - prev_oi
        if prev_oi not in (None, 0) and c.oi_change_pct == 0 and c.oi != prev_oi:
            c.oi_change_pct = pct(prev_oi, c.oi)
        if c.oi > 0:
            prev_oi = c.oi
            c.oi_value = c.oi * c.close
        out.append(c)
    return out


def discover_cases(input_dir: Path) -> List[Tuple[Path, List[Any]]]:
    cases = []
    for path in sorted(input_dir.iterdir()):
        if path.name.startswith(".") or path.name == Path(__file__).name:
            continue
        if path.suffix.lower() not in {".txt", ".doc", ".csv"}:
            continue
        try:
            candles = parse_csv_table(path) if path.suffix.lower() == ".csv" else parse_text_table(path)
        except Exception as exc:
            print(f"WARN parse failed {path}: {exc}")
            candles = []
        if candles:
            cases.append((path, candles))
    return cases


def future_stats(candles: Sequence[Any], idx: int, max_lookahead: int) -> Dict[str, Any]:
    close = candles[idx].close
    end = min(len(candles) - 1, idx + max_lookahead)
    best_i = idx
    best_return = 0.0
    for j in range(idx + 1, end + 1):
        ret = candles[j].close / close - 1 if close else 0.0
        if ret > best_return:
            best_return = ret
            best_i = j
    low_before = min((candles[j].close for j in range(idx, best_i + 1)), default=close)
    adverse = max(0.0, 1 - low_before / close) if close else 0.0
    return {
        "future_max_return": best_return,
        "future_max_time": candles[best_i].time if best_i != idx else "",
        "future_max_idx": best_i,
        "adverse_move_before_future_max": adverse,
        "bars_to_future_max": best_i - idx,
    }


def trades_expansion(candles: Sequence[Any], start: int, peak: int) -> bool:
    before = [c.trades for c in candles[max(0, start - 12):start] if c.trades > 0]
    during = [c.trades for c in candles[start:min(len(candles), peak + 1)] if c.trades > 0]
    if not before or not during:
        return False
    return max(during) >= max(1.0, statistics.median(before)) * 1.5


def label_events(candles: Sequence[Any], rise_threshold: float, max_lookahead: int) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    i = 0
    while i < max(0, len(candles) - 4):
        stats = future_stats(candles, i, max_lookahead)
        bars = stats["bars_to_future_max"]
        ret = stats["future_max_return"]
        major = bars >= 4 and ret >= rise_threshold
        early_trade_major = 4 <= bars <= 16 and ret >= 0.08 and trades_expansion(candles, i, stats["future_max_idx"])
        if major or early_trade_major:
            events.append({
                "start_idx": i,
                "peak_idx": stats["future_max_idx"],
                "start_time": candles[i].time,
                "peak_time": stats["future_max_time"],
                "peak_return": ret,
                "adverse": stats["adverse_move_before_future_max"],
            })
            i = max(i + 1, stats["future_max_idx"] + 1)
        else:
            i += 1
    return events


def is_suitable_signal(decision: Any, mode: str) -> bool:
    if decision is None:
        return False
    pattern = decision.dominant_structural_pattern
    if any(part in pattern for part in EXCLUDED_PATTERN_PARTS):
        return False
    if decision.readiness_level not in READINESS_BY_MODE[mode]:
        return False
    if decision.structural_bias not in ALLOWED_BIASES:
        return False
    if decision.readiness_level in {"Late / Risk State", "Failed / Invalidated"}:
        return False
    return True


def classify_failure(timeline: List[Dict[str, Any]], event: Dict[str, Any], had_parse_loss: bool = False) -> str:
    if had_parse_loss or not timeline:
        return "DATA_PARSING_LOSS"
    pre = [r for r in timeline if r["idx"] <= event["peak_idx"]]
    accepted_late = [r for r in pre if r.get("suitable")]
    if accepted_late and min(r["idx"] for r in accepted_late) > event["start_idx"]:
        return "TRIGGER_DETECTED_TOO_LATE"
    near = [r for r in pre if event["start_idx"] - 8 <= r["idx"] <= event["start_idx"] + 2]
    blob = " | ".join((r.get("pattern", "") + " " + r.get("bias", "") + " " + r.get("readiness", "") + " " + r.get("quote_validation", "") + " " + r.get("oi_state", "") + " " + r.get("base_vacuum", "")) for r in near)
    if "Quote Volume غير متوفر" in blob or "UNAVAILABLE" in blob:
        return "QUOTE_VOLUME_MISSING_DOWNGRADED_TOO_HARD"
    if "Mixed Structure" in blob:
        return "PRICE_LED_MOVE_CLASSIFIED_MIXED"
    if "No Base" in blob or "base_detected': False" in blob:
        return "BASE_NOT_DETECTED"
    if "OI ثابت" in blob or "OI هابط" in blob or "Without OI" in blob:
        return "OI_FLAT_DOWN_REJECTED_WRONGLY"
    if "Weak Vacuum" in blob or "Retention" in blob:
        return "TOP_POSITION_RETENTION_TOO_STRICT"
    if "Delayed" in blob and "Watchlist" in blob:
        return "DELAYED_OI_RELOAD_NOT_RECOGNIZED"
    if "Late" in blob or "Risk" in blob:
        return "LATE_RISK_OVERRIDE_TOO_AGGRESSIVE"
    if "Needs" in blob or "Watchlist" in blob:
        return "ACCEPTANCE_TOO_STRICT"
    return "BASE_NOT_DETECTED"


def decision_row(decision: Any) -> Dict[str, Any]:
    diag = getattr(decision, "diagnostics", {}) or {}
    return {
        "pattern": decision.dominant_structural_pattern if decision else "",
        "bias": decision.structural_bias if decision else "",
        "readiness": decision.readiness_level if decision else "",
        "confidence": decision.confidence if decision else "",
        "quote_validation": decision.quote_volume_validation if decision else "",
        "oi_state": decision.oi_read if decision else "",
        "base_vacuum": decision.price_led_base_vacuum_ignition_state if decision else "",
        "base_detected": (diag.get("phase_memory") or {}).get("base_detected", "") if decision else "",
    }


def analyze_case(path: Path, candles: List[Any], args: argparse.Namespace) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    engine = Engine()
    events = label_events(candles, args.rise_threshold, args.max_lookahead_bars)
    primary_event = events[0] if events else None
    timeline: List[Dict[str, Any]] = []
    first_signal: Optional[Dict[str, Any]] = None
    for idx in range(len(candles)):
        engine_slice = candles[max(0, idx + 1 - args.engine_window): idx + 1]
        decision = engine.analyze(engine_slice) if len(engine_slice) >= 30 else None
        stats = future_stats(candles, idx, args.max_lookahead_bars)
        row = {
            "idx": idx,
            "time": candles[idx].time,
            "symbol": candles[idx].symbol,
            "close": candles[idx].close,
            "trades": candles[idx].trades,
            "oi": candles[idx].oi,
            "oi_change_pct": candles[idx].oi_change_pct,
            "account_lsr": candles[idx].account_lsr,
            "position_lsr": candles[idx].position_lsr,
            "global_lsr": candles[idx].global_lsr,
            "future_max_return": round(stats["future_max_return"], 8),
            "bars_to_future_max": stats["bars_to_future_max"],
            "result_tag": "",
            "suitable": False,
        }
        row.update(decision_row(decision))
        row["suitable"] = is_suitable_signal(decision, args.mode) if decision else False
        if row["suitable"] and first_signal is None:
            first_signal = row.copy()
        timeline.append(row)

    result_class = "Missed Opportunity" if primary_event else "No Major Event"
    failure_reason = ""
    lead_bars: Optional[int] = None
    max_future_after_signal = 0.0
    adverse_after_signal = 0.0

    if primary_event and first_signal:
        lead_bars = primary_event["peak_idx"] - first_signal["idx"]
        signal_ret_from_event_start = candles[first_signal["idx"]].close / candles[primary_event["start_idx"]].close - 1 if first_signal["idx"] >= primary_event["start_idx"] else 0.0
        fs = future_stats(candles, first_signal["idx"], args.max_lookahead_bars)
        max_future_after_signal = fs["future_max_return"]
        adverse_after_signal = fs["adverse_move_before_future_max"]
        if max_future_after_signal >= args.rise_threshold and adverse_after_signal <= args.max_adverse_before_rise and first_signal["idx"] < primary_event["start_idx"] and (primary_event["start_idx"] - first_signal["idx"]) >= args.min_lead_bars:
            result_class = "Early Success"
        elif max_future_after_signal >= args.rise_threshold and adverse_after_signal <= args.max_adverse_before_rise and first_signal["idx"] <= primary_event["start_idx"]:
            result_class = "Live Success"
        elif first_signal["idx"] <= primary_event["peak_idx"] and max_future_after_signal >= args.rise_threshold and adverse_after_signal <= args.max_adverse_before_rise and signal_ret_from_event_start < args.rise_threshold * 0.50:
            result_class = "Live Success"
        else:
            result_class = "Late Detection"
            failure_reason = "TRIGGER_DETECTED_TOO_LATE"
    elif primary_event and not first_signal:
        result_class = "Missed Opportunity"
        failure_reason = classify_failure(timeline, primary_event)
    elif not primary_event and first_signal:
        fs = future_stats(candles, first_signal["idx"], args.max_lookahead_bars)
        max_future_after_signal = fs["future_max_return"]
        adverse_after_signal = fs["adverse_move_before_future_max"]
        if max_future_after_signal < args.rise_threshold:
            result_class = "False Positive"
            failure_reason = "TRUE_NEGATIVE_NOT_A_VALID_SETUP"

    for row in timeline:
        if primary_event and row["idx"] == primary_event["start_idx"]:
            row["result_tag"] = "EVENT_START"
        if primary_event and row["idx"] == primary_event["peak_idx"]:
            row["result_tag"] = (row["result_tag"] + ";" if row["result_tag"] else "") + "EVENT_PEAK"
        if first_signal and row["idx"] == first_signal["idx"]:
            row["result_tag"] = (row["result_tag"] + ";" if row["result_tag"] else "") + "FIRST_SIGNAL"

    symbol = candles[0].symbol if candles else path.stem.upper()
    report = {
        "symbol": symbol,
        "file": path.name,
        "event_start_time": primary_event["start_time"] if primary_event else "",
        "event_peak_time": primary_event["peak_time"] if primary_event else "",
        "event_peak_return": round(primary_event["peak_return"], 8) if primary_event else 0.0,
        "first_signal_time": first_signal["time"] if first_signal else "",
        "first_signal_price": first_signal["close"] if first_signal else "",
        "first_signal_pattern": first_signal["pattern"] if first_signal else "",
        "first_signal_bias": first_signal["bias"] if first_signal else "",
        "first_signal_readiness": first_signal["readiness"] if first_signal else "",
        "first_signal_confidence": first_signal["confidence"] if first_signal else "",
        "lead_bars": lead_bars if lead_bars is not None else "",
        "max_future_return_after_signal": round(max_future_after_signal, 8),
        "max_adverse_before_rise": round(adverse_after_signal if first_signal else (primary_event["adverse"] if primary_event else 0.0), 8),
        "result_class": result_class,
        "failure_reason": failure_reason,
        "total_labeled_events_in_file": len(events),
        "quote_volume_available": any(c.quote_volume > 0 for c in candles),
    }
    missed_cases: List[Dict[str, Any]] = []
    if result_class in {"Missed Opportunity", "Late Detection"}:
        missed_cases.append({
            "symbol": symbol,
            "time_range": f"{primary_event['start_time']} -> {primary_event['peak_time']}" if primary_event else "",
            "what_happened": f"Future rise reached {primary_event['peak_return']:.2%}" if primary_event else "No major event",
            "expected_pattern": "Early/Live bullish readiness before the major rise",
            "actual_pattern": report["first_signal_pattern"] or (timeline[primary_event["start_idx"]].get("pattern") if primary_event and primary_event["start_idx"] < len(timeline) else ""),
            "actual_readiness": report["first_signal_readiness"] or (timeline[primary_event["start_idx"]].get("readiness") if primary_event and primary_event["start_idx"] < len(timeline) else ""),
            "why_missed": failure_reason or classify_failure(timeline, primary_event) if primary_event else "DATA_PARSING_LOSS",
            "suggested_fix": "Review conservative V3.2.1-O gate only; do not use future labels or symbol-specific thresholds.",
            "patch_applied": False,
        })
    return report, timeline, missed_cases


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    if fieldnames is None:
        fieldnames = sorted({k for row in rows for k in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: List[Dict[str, Any]], mode: str) -> Dict[str, Any]:
    total_events = sum(1 for r in rows if r["event_start_time"])
    detected = sum(1 for r in rows if r["result_class"] in {"Early Success", "Live Success"})
    late = sum(1 for r in rows if r["result_class"] == "Late Detection")
    missed = sum(1 for r in rows if r["result_class"] == "Missed Opportunity")
    fp = sum(1 for r in rows if r["result_class"] == "False Positive")
    early = sum(1 for r in rows if r["result_class"] == "Early Success")
    live = sum(1 for r in rows if r["result_class"] == "Live Success")
    precision_den = detected + fp
    precision = detected / precision_den if precision_den else None
    recall = detected / total_events if total_events else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and (precision + recall) else None
    leads = [int(r["lead_bars"]) for r in rows if r["lead_bars"] != "" and r["result_class"] in {"Early Success", "Live Success"}]
    future_returns = [float(r["max_future_return_after_signal"]) for r in rows if r["first_signal_time"]]
    adverse = [float(r["max_adverse_before_rise"]) for r in rows if r["event_start_time"] or r["first_signal_time"]]
    no_negative_controls = all(r["event_start_time"] for r in rows) if rows else True
    return {
        "mode": mode,
        "total_symbols": len(rows),
        "total_events": total_events,
        "detected_events": detected,
        "missed_events": missed,
        "false_positives": fp,
        "early_success_count": early,
        "live_success_count": live,
        "late_detection_count": late,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "success_rate": detected / total_events if total_events else None,
        "detection_rate_on_rising_cases": detected / total_events if total_events else None,
        "average_lead_bars": statistics.mean(leads) if leads else 0,
        "median_lead_bars": statistics.median(leads) if leads else 0,
        "average_future_return_after_signal": statistics.mean(future_returns) if future_returns else 0,
        "average_adverse_move_before_rise": statistics.mean(adverse) if adverse else 0,
        "precision_warning": "Precision is not reliable without non-rising control symbols." if no_negative_controls else "",
        "failure_reason_counts": {reason: sum(1 for r in rows if r.get("failure_reason") == reason) for reason in FAILURE_REASONS + ["TRUE_NEGATIVE_NOT_A_VALID_SETUP"]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest V3.2.1-O uploaded Binance Futures cases without lookahead in classification")
    parser.add_argument("--input-dir", default=".")
    parser.add_argument("--mode", choices=["early_watch", "strict_live"], default="early_watch")
    parser.add_argument("--accepted-patterns", choices=["early_watch", "strict_live"], default=None, help="Alias for --mode compatibility")
    parser.add_argument("--rise-threshold", type=float, default=0.12)
    parser.add_argument("--min-lead-bars", type=int, default=1)
    parser.add_argument("--max-lookahead-bars", type=int, default=24)
    parser.add_argument("--max-adverse-before-rise", type=float, default=0.06)
    parser.add_argument("--engine-window", type=int, default=40, help="Rolling past-only candle window sent to the scanner at each bar")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)), help="Parallel case workers")
    args = parser.parse_args()
    if args.accepted_patterns:
        args.mode = args.accepted_patterns

    cases = discover_cases(Path(args.input_dir))
    REPORT_DIR.mkdir(exist_ok=True)
    rows: List[Dict[str, Any]] = []
    all_missed: List[Dict[str, Any]] = []
    if args.workers > 1 and len(cases) > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = [pool.submit(analyze_case, path, candles, args) for path, candles in cases]
            for fut in as_completed(futs):
                report, timeline, missed = fut.result()
                rows.append(report)
                all_missed.extend(missed)
                safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{report['file']}_{report['symbol']}_{args.mode}")
                write_csv(REPORT_DIR / f"candidate_timeline_{safe}.csv", timeline)
    else:
        for path, candles in cases:
            report, timeline, missed = analyze_case(path, candles, args)
            rows.append(report)
            all_missed.extend(missed)
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{Path(path).stem}_{report['symbol']}_{args.mode}")
            write_csv(REPORT_DIR / f"candidate_timeline_{safe}.csv", timeline)
    rows.sort(key=lambda r: (r["symbol"], r["file"]))

    summary = summarize(rows, args.mode)
    per_fields = [
        "symbol", "file", "event_start_time", "event_peak_time", "event_peak_return",
        "first_signal_time", "first_signal_price", "first_signal_pattern", "first_signal_bias",
        "first_signal_readiness", "first_signal_confidence", "lead_bars",
        "max_future_return_after_signal", "max_adverse_before_rise", "result_class", "failure_reason",
        "total_labeled_events_in_file", "quote_volume_available",
    ]
    write_csv(REPORT_DIR / "per_symbol_report.csv", rows, per_fields)
    write_csv(REPORT_DIR / f"per_symbol_report_{args.mode}.csv", rows, per_fields)
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / f"summary_{args.mode}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "missed_cases.json").write_text(json.dumps(all_missed, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / f"missed_cases_{args.mode}.json").write_text(json.dumps(all_missed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
