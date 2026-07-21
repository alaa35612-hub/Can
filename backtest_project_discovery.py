#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discovery backtest harness for the Binance Futures structural scanner.

The classifier is called candle-by-candle with a rolling past-only window. Future
candles are used only after a decision is already produced to label whether the
signal was useful, late, missed, or false-positive.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timezone

REPORT_DIR = Path("backtest_reports_discovery")
TEXT_ROW_RE = re.compile(r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)\s*(?P<symbol>[A-Z0-9]+USDT)\s+(?P<rest>.+)$")
SIGNAL_READINESS_EARLY = {"Primed Structure", "Early-Live Structure", "Confirmed Trigger", "Accepted Structure"}
SIGNAL_READINESS_STRICT = {"Early-Live Structure", "Confirmed Trigger", "Accepted Structure"}
BULLISH_BIASES = {"Early Bullish Structure", "Early-Live Bullish Structure", "Bullish but Event-driven"}
LATE_BIASES = {"Bullish but Late", "Post-Pump Crowding Risk"}


def load_engine_module(path: Path):
    spec = importlib.util.spec_from_file_location("discovery_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import engine file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def sf(x: Any, default: float = 0.0) -> float:
    try:
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def si(x: Any, default: int = 0) -> int:
    try:
        return int(float(str(x).replace(",", "").strip()))
    except Exception:
        return default


def pct(prev: float, cur: float) -> float:
    return 0.0 if abs(prev) <= 1e-12 else (cur - prev) / abs(prev) * 100.0


def parse_time_ms(text: str) -> int:
    dt = datetime.strptime(text.replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def lsp(ratio: float) -> Tuple[float, float]:
    r = max(0.0001, float(ratio or 1.0))
    long_pct = r / (1 + r) * 100
    return long_pct, 100 - long_pct


def row_to_candle(row: Dict[str, Any], engine: Any, fallback_symbol: str = "UNKNOWN") -> Any:
    Candle = engine.Candle
    Indicators = engine.Indicators
    symbol = str(row.get("symbol") or row.get("Symbol") or fallback_symbol).strip().upper()
    time_text = str(row.get("time") or row.get("Time") or "").strip()
    close = sf(row.get("close", row.get("Close", 0)))
    oi = sf(row.get("oi", row.get("OI", 0)))
    account_lsr = sf(row.get("account_lsr", row.get("Acco L/S", row.get("Account L/S", 1))), 1)
    position_lsr = sf(row.get("position_lsr", row.get("Posit L/S", row.get("Position L/S", 1))), 1)
    global_lsr = sf(row.get("global_lsr", row.get("Global L/S", 1)), 1)
    account_long, account_short = lsp(account_lsr)
    position_long, position_short = lsp(position_lsr)
    global_long, global_short = lsp(global_lsr)
    if "Acco L%" in row:
        account_long = sf(row.get("Acco L%"), account_long); account_short = sf(row.get("Acco S%"), account_short)
    if "Posit L%" in row:
        position_long = sf(row.get("Posit L%"), position_long); position_short = sf(row.get("Posit S%"), position_short)
    if "Global L%" in row:
        global_long = sf(row.get("Global L%"), global_long); global_short = sf(row.get("Global S%"), global_short)
    volume = sf(row.get("volume", row.get("Volume", 0)))
    quote_volume = sf(row.get("quote_volume", row.get("Quote Volume", 0)))
    return Candle(
        time_ms=parse_time_ms(time_text), time=time_text, symbol=symbol,
        open=sf(row.get("open", row.get("Open", close)), close), high=sf(row.get("high", row.get("High", close)), close),
        low=sf(row.get("low", row.get("Low", close)), close), close=close,
        volume=volume, quote_volume=quote_volume, trades=si(row.get("trades", row.get("Trades", 0))),
        taker_buy_quote=sf(row.get("taker_buy_quote", 0)), rsi=sf(row.get("rsi", row.get("RSI", 50)), 50),
        oi=oi, oi_value=oi * close, oi_change=sf(row.get("oi_change", row.get("OI Chg", 0))),
        oi_change_pct=sf(row.get("oi_change_pct", row.get("OI Chg %", 0))),
        account_lsr=account_lsr, account_long_pct=account_long, account_short_pct=account_short,
        position_lsr=position_lsr, position_long_pct=position_long, position_short_pct=position_short,
        global_lsr=global_lsr, global_long_pct=global_long, global_short_pct=global_short,
    )


def normalize_candles(candles: List[Any], engine: Any) -> List[Any]:
    candles = sorted(candles, key=lambda c: c.time_ms)
    closes = [c.close for c in candles]
    rsi_values = engine.Indicators.rsi(closes, 14) if closes else []
    out: List[Any] = []
    seen = set(); prev_oi: Optional[float] = None
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
            prev_oi = c.oi; c.oi_value = c.oi * c.close
        out.append(c)
    return out


def parse_text_table(path: Path, engine: Any) -> List[Any]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    fallback_symbol = "UNKNOWN"
    m_symbol = re.search(r"SYMBOL\s*:\s*([A-Z0-9]+USDT)", text)
    if m_symbol:
        fallback_symbol = m_symbol.group(1)
    rows: List[Any] = []
    keys = ["Close", "RSI", "Trades", "OI", "OI Chg", "OI Chg %", "Acco L/S", "Acco Chg", "Acco Chg%", "Acco L%", "Acco S%", "Posit L/S", "Posit Chg", "Posit Chg%", "Posit L%", "Posit S%", "Global L/S", "Global Chg", "Global Chg%", "Global L%", "Global S%"]
    for raw in text.splitlines():
        m = TEXT_ROW_RE.match(raw.strip())
        if not m:
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", m.group("rest"))
        if len(nums) < 20:
            continue
        row = {k: nums[i] for i, k in enumerate(keys) if i < len(nums)}
        row["Time"] = m.group("time"); row["Symbol"] = m.group("symbol") or fallback_symbol
        rows.append(row_to_candle(row, engine, fallback_symbol))
    return normalize_candles(rows, engine)


def parse_csv_table(path: Path, engine: Any) -> List[Any]:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as fh:
        sample = fh.read(4096); fh.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        rows = [row_to_candle(r, engine, path.stem.upper()) for r in csv.DictReader(fh, dialect=dialect) if r]
    return normalize_candles(rows, engine)


def discover_cases(input_dir: Path, engine: Any) -> List[Tuple[Path, List[Any]]]:
    cases: List[Tuple[Path, List[Any]]] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or "backtest_reports" in path.parts or path.suffix.lower() not in {".txt", ".csv", ".doc"}:
            continue
        try:
            candles = parse_csv_table(path, engine) if path.suffix.lower() == ".csv" else parse_text_table(path, engine)
        except Exception:
            candles = []
        if len(candles) >= 30 and candles[0].symbol != "UNKNOWN" and sum(1 for c in candles if c.close > 0) >= len(candles) * 0.95:
            cases.append((path, candles))
    return cases


def median(vals: Iterable[float], default: float = 0.0) -> float:
    vals = [float(x) for x in vals if math.isfinite(float(x))]
    return statistics.median(vals) if vals else default


def future_stats(candles: List[Any], idx: int, lookahead: int) -> Dict[str, Any]:
    future = candles[idx + 1: idx + 1 + lookahead]
    if not future:
        return {"future_max_return": 0.0, "future_max_time": "", "bars_to_future_max": "", "adverse_before_future_max": 0.0}
    base = candles[idx].close
    if base <= 0:
        return {"future_max_return": 0.0, "future_max_time": "", "bars_to_future_max": "", "adverse_before_future_max": 0.0}
    peak_offset, peak = max(enumerate(future, 1), key=lambda t: t[1].close)
    trough = min(c.low for c in future[:peak_offset])
    return {"future_max_return": peak.close / base - 1, "future_max_time": peak.time, "bars_to_future_max": peak_offset, "adverse_before_future_max": min(0.0, trough / base - 1)}


def trades_expansion(candles: List[Any], idx: int) -> bool:
    hist = candles[max(0, idx - 24):idx]
    if not hist:
        return False
    return candles[idx].trades >= median([c.trades for c in hist], 1) * 1.35


def label_event_starts(candles: List[Any], rise_threshold: float, lookahead: int) -> List[Dict[str, Any]]:
    candidates = []
    for i in range(4, len(candles) - 1):
        fs = future_stats(candles, i, lookahead)
        ret = fs["future_max_return"]
        prev = candles[max(0, i - 8):i]
        if not prev:
            continue
        local_ok = candles[i].close <= min(c.close for c in prev) * 1.04 or (max(c.close for c in prev) / max(1e-12, min(c.close for c in prev)) - 1) <= 0.08
        next4 = candles[i + 1:min(len(candles), i + 5)]
        accel = next4 and max(c.close for c in next4) / candles[i].close - 1 >= 0.015
        if (ret >= rise_threshold or (ret >= 0.08 and trades_expansion(candles, i))) and local_ok and accel:
            candidates.append({"idx": i, "start_time": candles[i].time, "peak_time": fs["future_max_time"], "peak_return": ret, "bars_to_peak": fs["bars_to_future_max"]})
    events: List[Dict[str, Any]] = []
    blocked_until = -1
    for ev in candidates:
        if ev["idx"] <= blocked_until:
            continue
        events.append(ev); blocked_until = ev["idx"] + int(ev["bars_to_peak"] or 0) + 4
    return events


def extract_pre_pattern(candles: List[Any], event_idx: int) -> Dict[str, Any]:
    pre24 = candles[max(0, event_idx - 24):event_idx]
    pre8 = candles[max(0, event_idx - 8):event_idx]
    pre4 = candles[max(0, event_idx - 4):event_idx]
    if not pre24:
        return {}
    base_range = (max(c.close for c in pre8) - min(c.close for c in pre8)) / max(1e-12, median([c.close for c in pre8], candles[event_idx].close)) if pre8 else 0.0
    tr_ratio = median([c.trades for c in pre4], 0) / max(1.0, median([c.trades for c in pre24[:-4] or pre4], 1)) if pre4 else 0.0
    return {
        "base_range_prev8": round(base_range, 6),
        "price_change_prev24": round(candles[event_idx - 1].close / pre24[0].close - 1, 6) if event_idx > 0 else 0,
        "oi_change_prev24": round(candles[event_idx - 1].oi / pre24[0].oi - 1, 6) if pre24[0].oi else 0,
        "oi_change_pct_last4_sum": round(sum(c.oi_change_pct for c in pre4), 6),
        "trades_ratio_last4": round(tr_ratio, 6),
        "account_long_pct": candles[event_idx - 1].account_long_pct if event_idx else candles[event_idx].account_long_pct,
        "position_long_pct": candles[event_idx - 1].position_long_pct if event_idx else candles[event_idx].position_long_pct,
        "global_long_pct": candles[event_idx - 1].global_long_pct if event_idx else candles[event_idx].global_long_pct,
        "position_minus_account": (candles[event_idx - 1].position_long_pct - candles[event_idx - 1].account_long_pct) if event_idx else 0,
        "reset_or_flush_last12": any(c.oi_change_pct < -1.5 for c in candles[max(0, event_idx - 12):event_idx]),
    }


def is_signal(decision: Any, mode: str) -> bool:
    if decision is None:
        return False
    readiness = decision.readiness_level
    bias = decision.structural_bias
    if mode == "strict_live":
        return readiness in SIGNAL_READINESS_STRICT and bias in BULLISH_BIASES
    return readiness in SIGNAL_READINESS_EARLY and (bias in BULLISH_BIASES or bias == "Neutral-to-Bullish Compression")


def failure_reason_at(decision: Any, pattern: Dict[str, Any]) -> str:
    if decision is None:
        return "NO_DECISION_MIN_WINDOW_OR_PARSE"
    diag = getattr(decision, "diagnostics", {}) or {}
    if "No Trigger" in str(getattr(decision, "trigger_status", "")) and pattern.get("base_range_prev8", 1) <= 0.08:
        return "TRIGGER_DETECTED_TOO_LATE"
    if pattern.get("oi_change_prev24", 0) <= 0 and "OI" in getattr(decision, "oi_read", ""):
        return "OI_FLAT_DOWN_REJECTED_OR_NOT_PRIORITIZED"
    if "Quote Volume غير متوفر" in getattr(decision, "quote_volume_validation", ""):
        return "QUOTE_VOLUME_MISSING_CONFIDENCE_CAP"
    if "Failed" in getattr(decision, "readiness_level", ""):
        return "CONFLICT_OR_ACCEPTANCE_INVALIDATION"
    if pattern.get("trades_ratio_last4", 1) < 1:
        return "QUIET_TRADES_BEFORE_MOVE"
    return "BASE_TRIGGER_ACCEPTANCE_PRIORITY_GAP"


def decision_row(c: Any, d: Any, fs: Dict[str, Any], signal: bool) -> Dict[str, Any]:
    return {
        "time": c.time, "close": c.close, "future_max_return": round(fs["future_max_return"], 8),
        "future_max_time": fs["future_max_time"], "bars_to_future_max": fs["bars_to_future_max"],
        "adverse_before_future_max": round(fs["adverse_before_future_max"], 8), "is_signal": signal,
        "pattern": getattr(d, "dominant_structural_pattern", ""), "bias": getattr(d, "structural_bias", ""),
        "readiness": getattr(d, "readiness_level", ""), "confidence": getattr(d, "confidence", ""),
        "trigger_status": getattr(d, "trigger_status", ""), "price_acceptance": getattr(d, "price_acceptance", ""),
        "oi_read": getattr(d, "oi_read", ""), "trades_read": getattr(d, "trades_read", ""),
        "ls_divergence": getattr(d, "ls_divergence", ""), "quote_volume_validation": getattr(d, "quote_volume_validation", ""),
    }


def analyze_case(path: Path, candles: List[Any], engine: Any, args: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    tree = engine.StructuralLiquidityDiscoveryTreeV321()
    events = label_event_starts(candles, args.rise_threshold, args.max_lookahead_bars)
    event = max(events, key=lambda e: e["peak_return"], default=None)
    timeline: List[Dict[str, Any]] = []
    first_signal: Optional[Dict[str, Any]] = None
    false_pos: List[Dict[str, Any]] = []
    for idx in range(len(candles)):
        window = candles[max(0, idx - args.engine_window + 1):idx + 1]
        decision = tree.analyze(window)
        fs = future_stats(candles, idx, args.max_lookahead_bars)
        sig = is_signal(decision, args.mode)
        row = decision_row(candles[idx], decision, fs, sig)
        timeline.append(row)
        if sig and first_signal is None:
            first_signal = {**row, "idx": idx, "decision": decision}
        if sig and fs["future_max_return"] < args.rise_threshold and (event is None or idx > event["idx"] + int(event.get("bars_to_peak") or 0) + args.max_lookahead_bars):
            false_pos.append({"symbol": candles[0].symbol, "file": path.name, "time": candles[idx].time, "pattern": row["pattern"], "future_max_return": fs["future_max_return"]})
    pattern = extract_pre_pattern(candles, event["idx"]) if event else {}
    result = "No Event"
    lead = ""; max_ret_after_signal = ""; adverse = ""; failure = ""
    if event:
        if first_signal:
            lead = event["idx"] - int(first_signal["idx"])
            max_ret_after_signal = first_signal["future_max_return"]
            adverse = first_signal["adverse_before_future_max"]
            if lead >= args.min_lead_bars and float(max_ret_after_signal) >= args.rise_threshold:
                result = "Early Success"
            elif 0 <= lead < args.min_lead_bars and float(max_ret_after_signal) >= args.rise_threshold:
                result = "Live Success"
            elif lead < 0:
                result = "Late Detection"
            else:
                result = "Too Early / Exhausted Before Event"
                failure = "SIGNAL_TOO_EARLY_NO_VALID_FUTURE_RETURN"
        else:
            result = "Missed Opportunity"
            failure = failure_reason_at(timeline[event["idx"]].get("decision"), pattern)
        if result in {"Late Detection", "Missed Opportunity"} and not failure:
            event_decision = None
            if event["idx"] < len(candles):
                event_decision = tree.analyze(candles[max(0, event["idx"] - args.engine_window + 1):event["idx"] + 1])
            failure = failure_reason_at(event_decision, pattern)
    elif first_signal:
        result = "False Positive"
        failure = "NO_MAJOR_RISE_AFTER_SIGNAL"
    report = {
        "symbol": candles[0].symbol, "file": path.name, "candles": len(candles),
        "event_start_time": event["start_time"] if event else "", "event_peak_time": event["peak_time"] if event else "",
        "event_peak_return": round(event["peak_return"], 8) if event else "", "first_signal_time": first_signal["time"] if first_signal else "",
        "first_signal_price": first_signal["close"] if first_signal else "", "first_signal_pattern": first_signal["pattern"] if first_signal else "",
        "first_signal_bias": first_signal["bias"] if first_signal else "", "first_signal_readiness": first_signal["readiness"] if first_signal else "",
        "first_signal_confidence": first_signal["confidence"] if first_signal else "", "lead_bars": lead,
        "max_future_return_after_signal": max_ret_after_signal, "max_adverse_before_rise": adverse,
        "result_class": result, "failure_reason": failure, "total_labeled_events_in_file": len(events),
        "quote_volume_available": any(c.quote_volume > 0 for c in candles), **{f"pattern_{k}": v for k, v in pattern.items()},
    }
    missed = []
    if result in {"Late Detection", "Missed Opportunity", "Too Early / Exhausted Before Event"}:
        missed.append({"symbol": candles[0].symbol, "file": path.name, "result_class": result, "failure_reason": failure, "event": event, "pre_pattern": pattern, "first_signal": {k: v for k, v in (first_signal or {}).items() if k != "decision"}})
    return report, timeline, missed, false_pos, events


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> None:
    if fields is None:
        fields = sorted({k for r in rows for k in r.keys()}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def summarize(rows: List[Dict[str, Any]], mode: str) -> Dict[str, Any]:
    total_events = sum(1 for r in rows if r["event_start_time"])
    early = sum(1 for r in rows if r["result_class"] == "Early Success")
    live = sum(1 for r in rows if r["result_class"] == "Live Success")
    late = sum(1 for r in rows if r["result_class"] == "Late Detection")
    missed = sum(1 for r in rows if r["result_class"] == "Missed Opportunity")
    too_early = sum(1 for r in rows if r["result_class"] == "Too Early / Exhausted Before Event")
    fp = sum(1 for r in rows if r["result_class"] == "False Positive")
    detected = early + live
    leads = [int(r["lead_bars"]) for r in rows if r.get("lead_bars") not in {"", None} and r["result_class"] in {"Early Success", "Live Success"}]
    no_negative_controls = all(r["event_start_time"] for r in rows) if rows else True
    return {
        "mode": mode, "total_symbols": len(rows), "total_events": total_events,
        "detected_events": detected, "early_success_count": early, "live_success_count": live,
        "late_detection_count": late, "missed_events": missed, "too_early_exhausted_count": too_early,
        "false_positives": fp, "recall": detected / total_events if total_events else None,
        "detection_rate_on_rising_cases": detected / total_events if total_events else None,
        "precision": None if no_negative_controls else (detected / (detected + fp) if detected + fp else None),
        "precision_warning": "Precision is not reliable without non-rising control symbols." if no_negative_controls else "",
        "average_lead_bars": statistics.mean(leads) if leads else 0,
        "median_lead_bars": statistics.median(leads) if leads else 0,
        "failure_reason_counts": {reason: sum(1 for r in rows if r.get("failure_reason") == reason) for reason in sorted({r.get("failure_reason", "") for r in rows if r.get("failure_reason")})},
    }


def aggregate_patterns(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    fields = ["pattern_base_range_prev8", "pattern_price_change_prev24", "pattern_oi_change_prev24", "pattern_oi_change_pct_last4_sum", "pattern_trades_ratio_last4", "pattern_position_minus_account"]
    out: Dict[str, Any] = {"observations": []}
    for f in fields:
        vals = [float(r[f]) for r in rows if r.get(f) not in {"", None}]
        out[f] = {"count": len(vals), "median": statistics.median(vals) if vals else None, "mean": statistics.mean(vals) if vals else None, "min": min(vals) if vals else None, "max": max(vals) if vals else None}
    for r in rows:
        if r.get("event_start_time"):
            out["observations"].append({k: r.get(k) for k in ["symbol", "event_start_time", "event_peak_return", *fields, "pattern_reset_or_flush_last12"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=".")
    ap.add_argument("--engine-file", default="2_v321_operational_v321o_patch1.py")
    ap.add_argument("--mode", choices=["early_watch", "strict_live"], default="early_watch")
    ap.add_argument("--rise-threshold", type=float, default=0.12)
    ap.add_argument("--min-lead-bars", type=int, default=1)
    ap.add_argument("--max-lookahead-bars", type=int, default=24)
    ap.add_argument("--max-adverse-before-rise", type=float, default=0.06)
    ap.add_argument("--engine-window", type=int, default=40)
    ap.add_argument("--max-candles-per-case", type=int, default=220, help="Use the most recent N candles per file to keep discovery runs practical; 0 = all")
    args = ap.parse_args()
    engine = load_engine_module(Path(args.engine_file))
    cases = discover_cases(Path(args.input_dir), engine)
    REPORT_DIR.mkdir(exist_ok=True)
    rows: List[Dict[str, Any]] = []; missed: List[Dict[str, Any]] = []; fps: List[Dict[str, Any]] = []
    all_events: Dict[str, Any] = {}
    for path, candles in cases:
        if args.max_candles_per_case and len(candles) > args.max_candles_per_case:
            candles = candles[-args.max_candles_per_case:]
        report, timeline, m, fp, events = analyze_case(path, candles, engine, args)
        rows.append(report); missed.extend(m); fps.extend(fp); all_events[report["symbol"]] = events
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{Path(path).stem}_{report['symbol']}_{args.mode}")
        write_csv(REPORT_DIR / f"candidate_timeline_{safe}.csv", timeline)
    rows.sort(key=lambda r: (r["symbol"], r["file"]))
    per_fields = ["symbol", "file", "candles", "event_start_time", "event_peak_time", "event_peak_return", "first_signal_time", "first_signal_price", "first_signal_pattern", "first_signal_bias", "first_signal_readiness", "first_signal_confidence", "lead_bars", "max_future_return_after_signal", "max_adverse_before_rise", "result_class", "failure_reason", "total_labeled_events_in_file", "quote_volume_available", "pattern_base_range_prev8", "pattern_price_change_prev24", "pattern_oi_change_prev24", "pattern_oi_change_pct_last4_sum", "pattern_trades_ratio_last4", "pattern_position_minus_account", "pattern_reset_or_flush_last12"]
    write_csv(REPORT_DIR / "per_symbol_report.csv", rows, per_fields)
    write_csv(REPORT_DIR / f"per_symbol_report_{args.mode}.csv", rows, per_fields)
    summary = summarize(rows, args.mode)
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / f"summary_{args.mode}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "missed_cases.json").write_text(json.dumps(missed, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / f"missed_cases_{args.mode}.json").write_text(json.dumps(missed, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "false_positive_cases.json").write_text(json.dumps(fps, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / f"false_positive_cases_{args.mode}.json").write_text(json.dumps(fps, ensure_ascii=False, indent=2), encoding="utf-8")
    pattern_report = aggregate_patterns(rows)
    pattern_report["events"] = all_events
    pattern_report["method"] = "Classifier used past-only rolling candles; future windows used only for evaluation labels and pattern summaries."
    (REPORT_DIR / "pattern_discovery_report.json").write_text(json.dumps(pattern_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
