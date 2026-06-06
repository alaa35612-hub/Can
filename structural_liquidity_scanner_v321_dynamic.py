#!/usr/bin/env python3
"""
Structural Liquidity Scanner V3.2.1 Dynamic

Single-file live scanner for Binance USD-M Futures public data.
Requirements: requests, pandas, numpy.

The engine intentionally avoids fixed analytical thresholds for structural pattern
recognition. It builds symbol-local baselines using rolling medians, MAD,
percentile ranks, robust z-scores, retention, slope and acceleration, then
resolves evidence through the V3.2.1 structural order rather than the incorrect
Price -> OI -> L/S -> Trades shortcut.
"""
from __future__ import annotations

import csv
import json
import logging
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import numpy as np
    import pandas as pd
    import requests
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    print("Missing dependency. Install with: pip install requests pandas numpy", file=sys.stderr)
    raise


# =============================================================================
# CONFIGURATION - operational settings only; structural thresholds are dynamic.
# =============================================================================
CONFIG: Dict[str, Any] = {
    "MODE": "early_watch",  # "early_watch" or "strict_live"
    "TIMEFRAME": "15m",
    "LIMIT": 180,
    "SCAN_ALL_USDT_PERPETUALS": True,
    "SYMBOL_WHITELIST": [],
    "SYMBOL_BLACKLIST": ["BTCUSDT", "ETHUSDT"],
    "TOP_N_RESULTS": 30,
    "SAVE_CSV": True,
    "SAVE_JSON": True,
    "AUTO_RUN": True,
    "SLEEP_BETWEEN_REQUESTS": 0.08,
    "REQUEST_TIMEOUT": 12,
    "RETRY_COUNT": 3,
    "MIN_CANDLES_REQUIRED": 90,
    "OUTPUT_DIR": "structural_liquidity_output",
    "USE_FUNDING_CONTEXT": True,
    "USE_OI_VALUE_VALIDATION": True,
    "USE_QUOTE_VOLUME_VALIDATION": True,
    "PRINT_DEBUG_PER_SYMBOL": False,
}

BINANCE_FAPI_BASE = "https://fapi.binance.com"
BINANCE_DATA_BASE = "https://fapi.binance.com"

READINESS_ORDER = {
    "Accepted Structure": 1,
    "Confirmed Trigger": 2,
    "Early-Live Structure": 3,
    "Primed Structure": 5,
    "Compression / Unresolved": 6,
    "Watchlist Only": 7,
    "Late / Risk State": 8,
    "Failed / Invalidated": 9,
}

ALLOWED_PATTERNS = {
    "Fresh Long Build-up", "Hidden Buildup / Absorption", "Absorption After Flush",
    "Short Build Under Stable Price", "Short Squeeze / Live Ignition",
    "Vacuum Ignition / Stop-Driven Move", "Post-Flush Vacuum Ignition",
    "Late Long Crowding", "Post-Pump Crowding Risk", "Bull Trap Risk",
    "Long Liquidation / Forced Reset", "Liquidity Exit / Decay", "Bearish Build-up",
    "Long Trap / Long Punishment", "Weak Consolidation", "Mixed Structure",
    "Short-Crowded Compression", "Failed Squeeze / Squeeze Exhaustion",
    "High OI Neutral Compression", "Bot / Noise Expansion",
    "Price-led Reset Ignition with OI Reload",
    "Top-Position Long Retention with Crowd Compression",
    "Price-led Base Ignition without Reset", "Failed Base Ignition",
    "Price-led Base Vacuum Ignition without OI Expansion", "Failed Base Vacuum Ignition",
}

ALLOWED_BIASES = {
    "Early Bullish Structure", "Early-Live Bullish Structure", "Bullish but Event-driven",
    "Bullish but Late", "Neutral / Unclear", "Neutral-to-Bullish Compression",
    "Distribution Risk", "Bearish Structural Risk", "Post-Pump Crowding Risk",
    "High Volatility Compression",
}


# =============================================================================
# Utilities
# =============================================================================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def pct_change(series: pd.Series) -> pd.Series:
    prev = series.shift(1)
    return (series - prev) / prev.replace(0, np.nan)


def signed_direction(value: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def compact_join(parts: Iterable[str]) -> str:
    return "; ".join([p for p in parts if p])


def robust_last_slope(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 3:
        return 0.0
    # Dynamic segment length from available history, not a market threshold.
    n = max(3, int(math.sqrt(len(s))))
    y = s.tail(n).to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    if np.nanstd(y) == 0:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def retention_after_latest_spike(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 5:
        return 0.0
    changes = s.diff().abs().dropna()
    if changes.empty:
        return 0.0
    spike_idx = changes.idxmax()
    pos = list(s.index).index(spike_idx) if spike_idx in s.index else len(s) - 1
    before = s.iloc[max(0, pos - 1)]
    spike = s.loc[spike_idx]
    last = s.iloc[-1]
    denom = abs(spike - before)
    if denom <= np.finfo(float).eps:
        return 0.0
    return float((last - before) / denom)


def percentile_rank(series: pd.Series, value: float) -> float:
    s = series.dropna().astype(float)
    if s.empty or not math.isfinite(value):
        return 0.5
    return float((s <= value).mean())


def robust_z(series: pd.Series, value: float) -> float:
    s = series.dropna().astype(float)
    if s.empty or not math.isfinite(value):
        return 0.0
    med = float(s.median())
    mad = float((s - med).abs().median())
    if mad <= np.finfo(float).eps:
        iqr = float(s.quantile(0.75) - s.quantile(0.25))
        mad = iqr / 1.349 if iqr > 0 else float(s.std(ddof=0))
    if mad <= np.finfo(float).eps:
        return 0.0
    return float(0.6745 * (value - med) / mad)


def dynamic_state_from_rank(rank: float, z: float) -> str:
    """Classify by self-distribution quartiles and robust tail agreement."""
    if not math.isfinite(rank):
        return "Normal"
    # Quantile language is relative to the symbol-local sample; not a global numeric market rule.
    if rank >= 0.97 or z >= 3.5:
        return "Extreme"
    if rank >= 0.90 or z >= 2.25:
        return "Shock"
    if rank >= 0.75 or z >= 1.25:
        return "Elevated"
    return "Normal"


def negative_dynamic_state_from_rank(rank: float, z: float) -> str:
    if not math.isfinite(rank):
        return "Normal"
    if rank <= 0.03 or z <= -3.5:
        return "Extreme"
    if rank <= 0.10 or z <= -2.25:
        return "Shock"
    if rank <= 0.25 or z <= -1.25:
        return "Elevated"
    return "Normal"


def state_strength(state: str) -> float:
    return {"Normal": 0.0, "Elevated": 1.0, "Shock": 2.0, "Extreme": 3.0}.get(state, 0.0)


# =============================================================================
# Data classes
# =============================================================================
@dataclass
class Candle:
    timestamp: int
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: float
    oi: float = np.nan
    oi_change: float = np.nan
    oi_change_pct: float = np.nan
    oi_value: float = np.nan
    global_ls: float = np.nan
    top_account_ls: float = np.nan
    top_position_ls: float = np.nan
    rsi: float = np.nan


@dataclass
class AnalysisFeatures:
    price_move_state: str = "Normal"
    oi_state: str = "unknown"
    trades_state: str = "Normal"
    quote_volume_state: str = "Normal"
    global_ls_state: str = "unknown"
    top_account_ls_state: str = "unknown"
    top_position_ls_state: str = "unknown"
    oi_value_validation: str = "Unavailable"
    trade_value_validation: str = "Unavailable"
    data_quality_flags: List[str] = field(default_factory=list)
    phase_state: str = "unknown"
    base_detected: bool = False
    reset_detected: bool = False
    trigger_detected: bool = False
    acceptance_state: str = "unknown"
    compression_state: str = "unknown"
    late_crowding_state: str = "none"
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    symbol: str
    timeframe: str
    data_window: str
    dominant_structural_pattern: str
    structural_bias: str
    readiness_level: str
    signal_timing: str
    cycle_position: str
    price_acceptance: str
    oi_read: str
    oi_value_validation: str
    trades_read: str
    quote_volume_validation: str
    ls_divergence: str
    whale_crowd_read: str
    price_led_reset_ignition_state: str
    price_led_base_ignition_state: str
    price_led_base_vacuum_ignition_state: str
    high_oi_compression_state: str
    trigger_status: str
    post_trigger_acceptance: str
    late_crowding_risk: str
    invalidation_risk: str
    confidence: str
    score: float
    rank_priority: float
    rsi_context_only: str
    final_structural_summary: str


# =============================================================================
# Binance public client
# =============================================================================
class BinanceFuturesClient:
    """Small public Binance USD-M Futures client with retry/backoff."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "structural-liquidity-scanner-v321-dynamic/1.0"})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, data_api: bool = False) -> Any:
        base = BINANCE_DATA_BASE if data_api else BINANCE_FAPI_BASE
        url = base + path
        last_error: Optional[Exception] = None
        for attempt in range(int(self.config["RETRY_COUNT"])):
            try:
                response = self.session.get(url, params=params, timeout=float(self.config["REQUEST_TIMEOUT"]))
                if response.status_code in (418, 429):
                    retry_after = safe_float(response.headers.get("Retry-After"), 0.0)
                    time.sleep(max(retry_after, (attempt + 1) ** 2))
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001 - scanner must continue symbol-by-symbol
                last_error = exc
                time.sleep((attempt + 1) * 0.5)
        raise RuntimeError(f"GET failed {path}: {last_error}")

    def exchange_symbols(self) -> List[str]:
        info = self._get("/fapi/v1/exchangeInfo")
        symbols = []
        for item in info.get("symbols", []):
            if item.get("contractType") == "PERPETUAL" and item.get("quoteAsset") == "USDT" and item.get("status") == "TRADING":
                symbols.append(item["symbol"])
        whitelist = set(self.config.get("SYMBOL_WHITELIST") or [])
        blacklist = set(self.config.get("SYMBOL_BLACKLIST") or [])
        if whitelist:
            symbols = [s for s in symbols if s in whitelist]
        if blacklist:
            symbols = [s for s in symbols if s not in blacklist]
        return sorted(symbols)

    def klines(self, symbol: str) -> pd.DataFrame:
        raw = self._get("/fapi/v1/klines", {"symbol": symbol, "interval": self.config["TIMEFRAME"], "limit": self.config["LIMIT"]})
        rows = []
        for k in raw:
            rows.append({
                "timestamp": int(k[0]), "open": safe_float(k[1]), "high": safe_float(k[2]),
                "low": safe_float(k[3]), "close": safe_float(k[4]), "volume": safe_float(k[5]),
                "close_time": int(k[6]), "quote_volume": safe_float(k[7]), "trades": safe_float(k[8]),
            })
        return pd.DataFrame(rows).sort_values("timestamp")

    def oi_history(self, symbol: str) -> pd.DataFrame:
        raw = self._get(
            "/futures/data/openInterestHist",
            {"symbol": symbol, "period": self.config["TIMEFRAME"], "limit": self.config["LIMIT"]},
            data_api=True,
        )
        rows = [{"timestamp": int(x.get("timestamp", 0)), "oi": safe_float(x.get("sumOpenInterest"))} for x in raw]
        return pd.DataFrame(rows).dropna(subset=["timestamp"]).sort_values("timestamp")

    def ls_history(self, symbol: str, endpoint: str, column: str) -> pd.DataFrame:
        raw = self._get(
            endpoint,
            {"symbol": symbol, "period": self.config["TIMEFRAME"], "limit": self.config["LIMIT"]},
            data_api=True,
        )
        rows = [{"timestamp": int(x.get("timestamp", 0)), column: safe_float(x.get("longShortRatio"))} for x in raw]
        return pd.DataFrame(rows).dropna(subset=["timestamp"]).sort_values("timestamp")

    def premium_index(self, symbol: str) -> Dict[str, Any]:
        return self._get("/fapi/v1/premiumIndex", {"symbol": symbol})

    def fetch_symbol_frame(self, symbol: str) -> Tuple[pd.DataFrame, List[str]]:
        flags: List[str] = []
        kl = self.klines(symbol)
        if kl.empty:
            return kl, ["klines_missing"]
        base = kl.copy().sort_values("timestamp")
        for fetcher, col, flag in [
            (self.oi_history, "oi", "oi_history_missing"),
            (lambda s: self.ls_history(s, "/futures/data/globalLongShortAccountRatio", "global_ls"), "global_ls", "global_ls_missing"),
            (lambda s: self.ls_history(s, "/futures/data/topLongShortAccountRatio", "top_account_ls"), "top_account_ls", "top_account_ls_missing"),
            (lambda s: self.ls_history(s, "/futures/data/topLongShortPositionRatio", "top_position_ls"), "top_position_ls", "top_position_ls_missing"),
        ]:
            try:
                df = fetcher(symbol)
                time.sleep(float(self.config["SLEEP_BETWEEN_REQUESTS"]))
                if df.empty or col not in df:
                    flags.append(flag)
                    base[col] = np.nan
                    continue
                base = pd.merge_asof(
                    base.sort_values("timestamp"), df[["timestamp", col]].sort_values("timestamp"),
                    on="timestamp", direction="backward",
                )
                base[col] = base[col].ffill()
            except Exception as exc:  # noqa: BLE001
                flags.append(f"{flag}:{exc.__class__.__name__}")
                base[col] = np.nan
        if self.config.get("USE_FUNDING_CONTEXT"):
            try:
                premium = self.premium_index(symbol)
                base["last_funding_rate"] = safe_float(premium.get("lastFundingRate"))
            except Exception as exc:  # noqa: BLE001
                flags.append(f"funding_context_missing:{exc.__class__.__name__}")
                base["last_funding_rate"] = np.nan
        return base, flags


# =============================================================================
# Dynamic baseline and quality engines
# =============================================================================
class DynamicBaselineEngine:
    """Builds symbol-local baselines and dynamic states."""

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy().sort_values("timestamp").reset_index(drop=True)
        d["price_change"] = pct_change(d["close"])
        d["range_pct"] = (d["high"] - d["low"]) / d["close"].replace(0, np.nan)
        d["oi_change"] = d["oi"].diff()
        d["oi_change_pct"] = pct_change(d["oi"])
        d["oi_value"] = d["oi"] * d["close"]
        d["oi_value_change_pct"] = pct_change(d["oi_value"])
        for col in ["global_ls", "top_account_ls", "top_position_ls"]:
            d[f"{col}_change"] = d[col].diff() if col in d else np.nan
            d[f"{col}_change_pct"] = pct_change(d[col]) if col in d else np.nan
        d["rsi"] = self.rsi(d["close"])
        return d

    @staticmethod
    def rsi(close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        # RSI is context only; the smoothing window is a standard display setting, not decision logic.
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def metric(self, series: pd.Series, current: Optional[float] = None) -> Dict[str, Any]:
        s = series.dropna().astype(float)
        value = float(s.iloc[-1]) if current is None and not s.empty else safe_float(current)
        rank = percentile_rank(s, value)
        z = robust_z(s, value)
        return {
            "value": value,
            "median": float(s.median()) if not s.empty else np.nan,
            "mad": float((s - s.median()).abs().median()) if not s.empty else np.nan,
            "percentile_rank": rank,
            "robust_z": z,
            "slope": robust_last_slope(s),
            "acceleration": self.acceleration(s),
            "retention": retention_after_latest_spike(s),
            "state": dynamic_state_from_rank(rank, z),
            "negative_state": negative_dynamic_state_from_rank(rank, z),
        }

    @staticmethod
    def acceleration(series: pd.Series) -> float:
        s = series.dropna()
        if len(s) < 4:
            return 0.0
        return robust_last_slope(s.diff().dropna())

    def snapshot(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        cols = {
            "price_change": "price_change",
            "range": "range_pct",
            "oi_change_pct": "oi_change_pct",
            "oi_abs": "oi",
            "trades": "trades",
            "quote_volume": "quote_volume",
            "volume": "volume",
            "global_ls_change": "global_ls_change_pct",
            "top_account_ls_change": "top_account_ls_change_pct",
            "top_position_ls_change": "top_position_ls_change_pct",
            "oi_value_change_pct": "oi_value_change_pct",
        }
        return {name: self.metric(df[col]) if col in df else self.metric(pd.Series(dtype=float)) for name, col in cols.items()}


class DataQualityChecker:
    """Flags missing, irregular or noisy input without hard-failing analysis."""

    def check(self, df: pd.DataFrame, source_flags: List[str], config: Dict[str, Any]) -> Tuple[List[str], str, float]:
        flags = list(source_flags)
        if len(df) < int(config["MIN_CANDLES_REQUIRED"]):
            flags.append("insufficient_candles")
        if "timestamp" in df and len(df) > 3:
            diffs = df["timestamp"].diff().dropna()
            if not diffs.empty and diffs.nunique() > max(2, int(math.sqrt(len(diffs)))):
                flags.append("irregular_spacing")
            if diffs.le(0).any():
                flags.append("non_monotonic_timestamps")
        required = ["open", "high", "low", "close", "volume", "trades"]
        for col in required:
            if col not in df or df[col].isna().any() or (df[col] <= 0).any():
                flags.append(f"{col}_zero_or_nan")
        if "quote_volume" not in df or df["quote_volume"].isna().all():
            flags.append("quote_volume_missing")
        if "oi" not in df or df["oi"].isna().all():
            flags.append("oi_history_missing")
        else:
            oi = df["oi"].dropna()
            if len(oi) > 5 and oi.head(max(3, int(math.sqrt(len(oi))))).median() <= 0:
                flags.append("oi_warmup_jump_risk")
        ls_cols = ["global_ls", "top_account_ls", "top_position_ls"]
        if any(col not in df or df[col].isna().all() for col in ls_cols):
            flags.append("ls_history_missing")
        if "rsi" in df and df["rsi"].tail(max(3, int(math.sqrt(len(df))))).isna().any():
            flags.append("immature_rsi_context")
        if "trades" in df and len(df) > 10:
            first = df["trades"].head(max(3, int(math.sqrt(len(df))))).median()
            rest = df["trades"].iloc[max(3, int(math.sqrt(len(df)))):].median()
            if rest > 0 and first / rest > df["trades"].rank(pct=True).quantile(0.90):
                flags.append("early_trade_warmup_spike")
        major = [f for f in flags if any(k in f for k in ["missing", "insufficient", "non_monotonic", "zero_or_nan"])]
        if len(major) >= 3:
            cap = "Medium"
        elif len(major) >= 1:
            cap = "Medium-High"
        else:
            cap = "High"
        reliability = max(0.0, 1.0 - len(set(flags)) / max(1.0, math.sqrt(max(len(df), 1))))
        return sorted(set(flags)), cap, reliability


# =============================================================================
# Structural engines
# =============================================================================
class PhaseMemoryEngine:
    """Segments the window and remembers base/reset/ignition ordering."""

    def analyze(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        n = len(df)
        if n < 10:
            return {"phase_state": "insufficient", "base_detected": False, "reset_detected": False, "trigger_detected": False}
        seg = max(3, int(math.sqrt(n)))
        latest = df.tail(seg)
        pre = df.iloc[-2 * seg:-seg] if n >= 2 * seg else df.head(seg)
        background = df.iloc[:-2 * seg] if n > 2 * seg else df.head(max(1, n - seg))

        local_range_rank = percentile_rank(df["range_pct"], pre["range_pct"].median())
        local_vol_rank = percentile_rank(df["quote_volume"], pre["quote_volume"].median()) if "quote_volume" in df else 0.5
        base_detected = local_range_rank <= df["range_pct"].rank(pct=True).median() and local_vol_rank <= df["quote_volume"].rank(pct=True).median()

        oi_drop_rank = percentile_rank(df["oi_change_pct"].dropna(), df["oi_change_pct"].tail(seg).min()) if "oi_change_pct" in df else 0.5
        price_drop_rank = percentile_rank(df["price_change"].dropna(), df["price_change"].tail(seg).min())
        reset_detected = oi_drop_rank <= 0.10 or price_drop_rank <= 0.10

        latest_close = df["close"].iloc[-1]
        pre_high = pre["high"].max() if not pre.empty else df["high"].iloc[-2]
        trigger_detected = latest_close > pre_high and b["price_change"]["state"] in {"Elevated", "Shock", "Extreme"}

        price_leads_oi = False
        oi_leads_price = False
        if "oi_change_pct" in df:
            price_peak_pos = int(df["price_change"].tail(2 * seg).fillna(0).idxmax())
            oi_peak_pos = int(df["oi_change_pct"].tail(2 * seg).fillna(0).idxmax())
            price_leads_oi = price_peak_pos < oi_peak_pos or (trigger_detected and b["oi_change_pct"]["state"] == "Normal")
            oi_leads_price = oi_peak_pos < price_peak_pos and b["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}

        if trigger_detected:
            phase_state = "ignition_candle" if len(latest) <= seg else "latest_structure"
        elif base_detected:
            phase_state = "compression_or_quiet_zone"
        elif reset_detected:
            phase_state = "abnormal_change_zone"
        else:
            phase_state = "background"

        distance_from_footprint = abs(latest_close - pre_high) / max(abs(latest_close), np.finfo(float).eps)
        distance_rank = percentile_rank(df["range_pct"].dropna(), distance_from_footprint)
        return {
            "background_index": list(background.index),
            "compression_or_quiet_zone": list(pre.index) if base_detected else [],
            "abnormal_change_zone": list(df.tail(2 * seg).index) if reset_detected else [],
            "pre_ignition_zone": list(pre.index),
            "ignition_candle": int(df.index[-1]) if trigger_detected else None,
            "post_ignition": [],
            "latest_structure": list(latest.index),
            "phase_state": phase_state,
            "base_detected": bool(base_detected),
            "reset_detected": bool(reset_detected),
            "trigger_detected": bool(trigger_detected),
            "price_leads_oi": bool(price_leads_oi),
            "oi_leads_price": bool(oi_leads_price),
            "distance_from_footprint_rank": distance_rank,
            "close_to_footprint": distance_rank <= 0.50,
            "base_high": float(pre_high),
            "base_low": float(pre["low"].min()) if not pre.empty else float(df["low"].tail(seg).min()),
        }


class ValidationEngine:
    """OI value and quote-volume/trade validation."""

    def oi_value_validation(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]]) -> str:
        if df["oi"].isna().all() or df["oi_value"].isna().all():
            return "Unavailable"
        oi_dir = signed_direction(df["oi_change"].iloc[-1])
        val_dir = signed_direction(df["oi_value_change_pct"].iloc[-1])
        price_dir = signed_direction(df["price_change"].iloc[-1])
        oi_active = b["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
        val_active = b["oi_value_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
        if oi_dir == "up" and val_dir == "up" and (oi_active or val_active):
            return "Real Position Expansion"
        if oi_dir == "up" and val_dir != "up":
            return "Contract-count distortion / Low-price distortion"
        if oi_dir in {"flat", "unknown"} and val_dir == "up" and price_dir == "up":
            return "Price-driven OI Value Expansion"
        if oi_dir == "down" and val_dir in {"flat", "up"}:
            return "price offsets OI decline"
        if oi_dir == "down" and val_dir == "down":
            return "Real Deleveraging"
        return "Neutral OI Value Read"

    def trade_value_validation(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]]) -> str:
        trades_active = b["trades"]["state"] in {"Elevated", "Shock", "Extreme"}
        qv_active = b["quote_volume"]["state"] in {"Elevated", "Shock", "Extreme"}
        oi_active = b["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
        oi_dir = signed_direction(df["oi_change"].iloc[-1])
        price_move = b["price_change"]["state"]
        if trades_active and qv_active and oi_active and oi_dir == "up":
            return "Trades ↑ + Quote Volume ↑ + OI ↑ = Real Capital Activation"
        if trades_active and qv_active and oi_dir in {"flat", "down", "unknown"}:
            return "Trades ↑ + Quote Volume ↑ + OI ثابت/هابط = Liquidation / Covering / Spot-led or Vacuum Flow"
        if trades_active and qv_active:
            return "Trades ↑ + Quote Volume ↑ = Real Execution Expansion"
        if trades_active and not qv_active:
            return "Trades ↑ + Quote Volume ضعيف = Micro-trade Noise / Bot Activity"
        if (not trades_active) and qv_active:
            return "Trades ضعيفة + Quote Volume ↑ = Large Block-like Execution"
        if trades_active and price_move == "Normal":
            return "Trades ↑ جدًا + السعر لا يتحرك = Absorption Battle"
        return "Normal Execution"


class PriceStructureEngine:
    def classify(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]], phase: Dict[str, Any]) -> str:
        pc = df["price_change"].iloc[-1]
        slope = robust_last_slope(df["close"])
        latest_state = b["price_change"]["state"]
        neg_state = b["price_change"]["negative_state"]
        if phase.get("reset_detected") and pc > 0 and slope > 0:
            return "up after reset"
        if phase.get("base_detected") and pc > 0 and slope > 0:
            return "up from base without reset"
        if latest_state in {"Shock", "Extreme"} and pc > 0:
            return "explosive up move"
        if neg_state in {"Shock", "Extreme"} and pc < 0:
            return "violent downtrend"
        if abs(slope) <= abs(df["close"].diff().dropna().median() if len(df) > 3 else 0):
            return "sideways/base"
        if slope > 0:
            return "healthy uptrend"
        if pc > 0 and slope < 0:
            return "bounce after drop"
        return "slow downtrend"


class PriceAcceptanceEngine:
    def classify(self, df: pd.DataFrame, phase: Dict[str, Any]) -> str:
        if len(df) < 5:
            return "unknown"
        last = df.iloc[-1]
        base_high = phase.get("base_high", float(df["high"].iloc[-2]))
        base_low = phase.get("base_low", float(df["low"].tail(max(3, int(math.sqrt(len(df))))).min()))
        trigger_mid = (last["high"] + last["low"]) / 2
        close = last["close"]
        if close < base_low:
            return "Structure Invalidated"
        if phase.get("trigger_detected") and close > base_high and close >= trigger_mid:
            if phase.get("reset_detected"):
                return "Pre-OI Accepted Move After Reset"
            if phase.get("base_detected"):
                return "Pre-OI Accepted Move From Base"
            return "Accepted Breakout"
        if phase.get("base_detected") and close > base_high:
            return "Constructive Acceptance"
        if close >= trigger_mid and close >= base_low:
            return "Controlled Pullback"
        if phase.get("trigger_detected") and close <= base_high:
            return "Failed Breakout"
        return "OI Trap Risk" if close < base_high and phase.get("oi_leads_price") else "Constructive Acceptance"


class OIStateEngine:
    def classify(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]], phase: Dict[str, Any]) -> str:
        if df["oi"].isna().all():
            return "OI unavailable"
        latest = df["oi_change_pct"].iloc[-1]
        state = b["oi_change_pct"]["state"]
        neg = b["oi_change_pct"]["negative_state"]
        slope = robust_last_slope(df["oi"])
        if neg in {"Shock", "Extreme"}:
            return "OI Flush"
        if phase.get("reset_detected") and latest > 0 and slope > 0:
            return "Delayed Constructive OI Reload After Reset"
        if phase.get("base_detected") and latest > 0 and slope > 0:
            return "Delayed Constructive OI Reload From Base"
        if phase.get("base_detected") and latest <= 0 and neg not in {"Shock", "Extreme"}:
            return "Price-led Base Move Without OI Expansion"
        if state in {"Shock", "Extreme"} and latest > 0:
            return "explosive OI build"
        if state == "Elevated" and latest > 0:
            return "gradual OI build"
        if neg == "Elevated" and latest < 0:
            return "gradual OI decline"
        if slope > 0 and phase.get("price_leads_oi"):
            return "Late OI Expansion"
        if slope < 0 and df["price_change"].iloc[-1] > 0:
            return "OI Deleveraging After Pump"
        return "flat OI"


class LSStructureEngine:
    def analyze(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        def col_read(col: str, metric_name: str) -> Tuple[str, str]:
            if col not in df or df[col].isna().all():
                return "unknown", "unavailable"
            direction = signed_direction(df[col].diff().iloc[-1])
            change_state = b[metric_name]["state"] if metric_name in b else "Normal"
            neg_state = b[metric_name]["negative_state"] if metric_name in b else "Normal"
            if direction == "up" and change_state in {"Elevated", "Shock", "Extreme"}:
                return "up", "crowd/account chasing"
            if direction == "down" and neg_state in {"Elevated", "Shock", "Extreme"}:
                return "down", "short pressure / longs reducing"
            return direction, "stable"

        g_dir, g_state = col_read("global_ls", "global_ls_change")
        a_dir, a_state = col_read("top_account_ls", "top_account_ls_change")
        p_dir, p_state = col_read("top_position_ls", "top_position_ls_change")
        top_position_level_rank = percentile_rank(df["top_position_ls"].dropna(), df["top_position_ls"].iloc[-1]) if "top_position_ls" in df else 0.5
        top_position_retention = p_dir != "down" or top_position_level_rank >= 0.50
        if g_dir == "up" and a_dir == "up" and p_dir == "up":
            divergence = "Global ↑ + Top Account ↑ + Top Position ↑"
        elif g_dir == "up" and a_dir == "up" and p_dir == "down":
            divergence = "Global ↑ + Top Account ↑ + Top Position ↓"
        elif g_dir == "up" and a_dir == "down" and p_dir == "down":
            divergence = "Global ↑ + Top Account ↓ + Top Position ↓"
        elif g_dir == "down" and a_dir == "down" and p_dir in {"flat", "up"}:
            divergence = "Global ↓ + Top Account ↓ + Top Position ثابت أو ↑"
        elif g_dir == "down" and a_dir == "down" and p_dir == "down":
            divergence = "Global ↓ + Top Account ↓ + Top Position ↓"
        elif g_dir == "down" and a_dir == "up" and p_dir == "up":
            divergence = "Global ↓ + Top Account ↑ + Top Position ↑"
        elif g_dir == "flat" and a_dir == "up" and p_dir == "up":
            divergence = "Global ثابت + Top Account ↑ + Top Position ↑"
        elif g_dir == "flat" and a_dir == "up" and p_dir == "down":
            divergence = "Global ثابت + Top Account ↑ + Top Position ↓"
        elif g_dir == "down" and a_dir == "down" and abs(top_position_level_rank - 0.5) <= 0.1:
            divergence = "Global ↓ جدًا + Top Account ↓ جدًا + Top Position قرب التعادل"
        elif g_dir == "down" and a_dir == "down" and top_position_level_rank > 0.5 and p_dir == "down":
            divergence = "Global ↓ + Top Account ↓ + Top Position يبقى Long-heavy لكنه يتراجع"
        elif g_dir in {"flat", "up"} and a_dir != "up" and top_position_level_rank > 0.5:
            divergence = "Global ثابت أو ↑ قليلًا + Top Account لا يطارد + Top Position Long-heavy"
        else:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
        crowd_chasing = g_dir == "up" and a_dir == "up" and p_dir != "down"
        account_chasing = a_dir == "up" and "chasing" in a_state
        whale_read = "Top Position retention" if top_position_retention else "Top Position collapse"
        if crowd_chasing:
            whale_read += " with crowd chasing"
        elif g_dir == "down" or a_dir == "down":
            whale_read += " with crowd compression / short fuel"
        return {
            "global_ls_state": g_state,
            "top_account_ls_state": a_state,
            "top_position_ls_state": p_state,
            "ls_divergence": divergence,
            "whale_crowd_read": whale_read,
            "crowd_chasing": str(crowd_chasing),
            "account_chasing": str(account_chasing),
            "top_position_retention": str(top_position_retention),
        }


class StructuralPreScanner:
    """Produces evidence flags; no single flag is a final decision."""

    def scan(self, df: pd.DataFrame, b: Dict[str, Dict[str, Any]], phase: Dict[str, Any], validations: Dict[str, str], ls: Dict[str, str], acceptance: str) -> Dict[str, Any]:
        oi_read = OIStateEngine().classify(df, b, phase)
        trades_real = "Quote Volume ↑" in validations["trade_value"] or "Real Execution" in validations["trade_value"] or "Real Capital" in validations["trade_value"]
        price_up = df["price_change"].iloc[-1] > 0
        oi_hard_down = b["oi_change_pct"]["negative_state"] in {"Shock", "Extreme"}
        oi_expanding = b["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"} and df["oi_change_pct"].iloc[-1] > 0
        top_retention = ls.get("top_position_retention") == "True"
        account_chasing = ls.get("account_chasing") == "True"
        accepted = acceptance in {"Accepted Breakout", "Constructive Acceptance", "Pre-OI Accepted Move After Reset", "Pre-OI Accepted Move From Base", "Controlled Pullback"}

        flags = {
            "oi_flush_detector": "active" if oi_read == "OI Flush" else "inactive",
            "post_flush_behavior": "stable/reload" if phase.get("reset_detected") and not oi_hard_down else "none",
            "pre_price_oi_build_up": "active" if phase.get("oi_leads_price") and oi_expanding else "inactive",
            "price_leads_oi": "active" if phase.get("price_leads_oi") else "inactive",
            "ignition_without_oi": "active" if price_up and phase.get("trigger_detected") and not oi_expanding and not oi_hard_down else "inactive",
            "price_led_reset_ignition_with_oi_reload": "active" if phase.get("reset_detected") and phase.get("price_leads_oi") and (oi_expanding or oi_read == "Delayed Constructive OI Reload After Reset") and accepted else "inactive",
            "price_led_base_ignition_without_reset": "active" if phase.get("base_detected") and not phase.get("reset_detected") and price_up and phase.get("trigger_detected") and accepted else "inactive",
            "price_led_base_vacuum_without_oi_expansion": "active" if phase.get("base_detected") and not phase.get("reset_detected") and price_up and phase.get("trigger_detected") and trades_real and not oi_expanding and not oi_hard_down and top_retention and not account_chasing and accepted else "inactive",
            "late_oi_crowding": "active" if phase.get("price_leads_oi") and oi_expanding and account_chasing and not phase.get("base_detected") and not phase.get("reset_detected") else "inactive",
            "post_peak_oi_retention": "active" if b["oi_abs"]["percentile_rank"] >= 0.90 and price_up is False else "inactive",
            "high_oi_compression": "active" if b["oi_abs"]["percentile_rank"] >= 0.90 and b["range"]["percentile_rank"] <= 0.50 else "inactive",
            "post_trigger_acceptance": acceptance,
            "short_crowding_quality": "strong fuel" if "Global ↓" in ls.get("ls_divergence", "") and not account_chasing else "neutral/unclear",
        }
        return flags


class ConflictResolver:
    """Applies V3.2.1 conflict priority to evidence."""

    def resolve(
        self,
        df: pd.DataFrame,
        features: AnalysisFeatures,
        price_state: str,
        oi_read: str,
        validations: Dict[str, str],
        ls: Dict[str, str],
        pre: Dict[str, Any],
        quality_cap: str,
        reliability: float,
        mode: str,
    ) -> AnalysisResult:
        accepted = features.acceptance_state in {"Accepted Breakout", "Constructive Acceptance", "Pre-OI Accepted Move After Reset", "Pre-OI Accepted Move From Base", "Controlled Pullback"}
        invalid = features.acceptance_state in {"Structure Invalidated", "Failed Breakout"}
        vacuum = pre["price_led_base_vacuum_without_oi_expansion"] == "active"
        base_ignition = pre["price_led_base_ignition_without_reset"] == "active"
        reset_ignition = pre["price_led_reset_ignition_with_oi_reload"] == "active"
        late_crowding = pre["late_oi_crowding"] == "active"
        high_comp = pre["high_oi_compression"] == "active"
        bot_noise = "Micro-trade Noise" in validations["trade_value"]
        oi_value_downgrade = "distortion" in validations["oi_value"]

        if invalid and vacuum:
            pattern = "Failed Base Vacuum Ignition"
            bias = "Neutral / Unclear"
            readiness = "Failed / Invalidated"
        elif invalid and base_ignition:
            pattern = "Failed Base Ignition"
            bias = "Neutral / Unclear"
            readiness = "Failed / Invalidated"
        elif invalid:
            pattern = "Bull Trap Risk" if df["price_change"].iloc[-1] > 0 else "Long Trap / Long Punishment"
            bias = "Bearish Structural Risk"
            readiness = "Failed / Invalidated"
        elif vacuum:
            pattern = "Price-led Base Vacuum Ignition without OI Expansion"
            bias = "Early-Live Bullish Structure"
            readiness = "Confirmed Trigger" if accepted else "Early-Live Structure"
        elif reset_ignition:
            pattern = "Price-led Reset Ignition with OI Reload"
            bias = "Early-Live Bullish Structure"
            readiness = "Accepted Structure" if accepted else "Confirmed Trigger"
        elif base_ignition:
            pattern = "Price-led Base Ignition without Reset"
            bias = "Early-Live Bullish Structure"
            readiness = "Confirmed Trigger" if accepted else "Early-Live Structure"
        elif high_comp and "short fuel" in pre["short_crowding_quality"]:
            pattern = "Short-Crowded Compression"
            bias = "Neutral-to-Bullish Compression"
            readiness = "Compression / Unresolved"
        elif high_comp:
            pattern = "High OI Neutral Compression"
            bias = "High Volatility Compression"
            readiness = "Compression / Unresolved"
        elif late_crowding:
            pattern = "Late Long Crowding"
            bias = "Bullish but Late"
            readiness = "Late / Risk State"
        elif bot_noise:
            pattern = "Bot / Noise Expansion"
            bias = "Neutral / Unclear"
            readiness = "Watchlist Only"
        elif oi_read in {"explosive OI build", "gradual OI build"} and price_state in {"sideways/base", "healthy uptrend"}:
            pattern = "Fresh Long Build-up" if df["price_change"].iloc[-1] >= 0 else "Short Build Under Stable Price"
            bias = "Early Bullish Structure" if df["price_change"].iloc[-1] >= 0 else "Neutral / Unclear"
            readiness = "Primed Structure" if accepted else "Watchlist Only"
        elif oi_read == "OI Flush" and accepted:
            pattern = "Absorption After Flush"
            bias = "Bullish but Event-driven"
            readiness = "Primed Structure"
        elif price_state == "explosive up move" and accepted:
            pattern = "Short Squeeze / Live Ignition"
            bias = "Bullish but Event-driven"
            readiness = "Confirmed Trigger"
        elif price_state == "violent downtrend":
            pattern = "Long Liquidation / Forced Reset"
            bias = "Bearish Structural Risk"
            readiness = "Late / Risk State"
        elif price_state == "sideways/base" and oi_read in {"flat OI", "gradual OI decline"}:
            pattern = "Weak Consolidation"
            bias = "Neutral / Unclear"
            readiness = "Watchlist Only"
        else:
            pattern = "Mixed Structure"
            bias = "Neutral / Unclear"
            readiness = "Watchlist Only"

        if mode == "strict_live" and readiness in {"Watchlist Only", "Primed Structure"} and not accepted:
            readiness = "Watchlist Only"
            bias = "Neutral / Unclear" if bias.startswith("Early") else bias

        # Conflict overlays mandated by V3.2.1.
        risk_notes = []
        if invalid:
            risk_notes.append("Post-trigger failure / base break overrides bullish evidence")
        if oi_value_downgrade:
            risk_notes.append("OI contracts rose but OI Value did not confirm")
        if bot_noise:
            risk_notes.append("Trades expanded without quote-volume confirmation")
        if pre["post_peak_oi_retention"] == "active":
            risk_notes.append("OI near window high while price is not extending")
        if not CONFIG.get("USE_FUNDING_CONTEXT") or "funding_context_missing" in " ".join(features.data_quality_flags):
            risk_notes.append("Funding context unavailable")

        confidence = self.confidence(pattern, readiness, accepted, validations, ls, risk_notes, quality_cap, reliability)
        score = self.score(pattern, readiness, accepted, features, validations, ls, pre, confidence)
        rank_priority = self.rank_priority(readiness, pattern, features, pre, score)
        latest = df.iloc[-1]
        rsi_context = "RSI context only: " + ("unavailable" if not math.isfinite(latest.get("rsi", np.nan)) else f"{latest['rsi']:.1f}; not used in decision")
        signal_timing = "near footprint" if features.evidence.get("phase", {}).get("close_to_footprint") else "extended from footprint"
        cycle_position = features.phase_state
        summary = compact_join([
            f"{pattern} | {bias}",
            f"price={price_state}", f"oi={oi_read}", validations["oi_value"], validations["trade_value"],
            ls.get("ls_divergence", "L/S unavailable"), features.acceptance_state,
            "Base Vacuum exception preserved despite flat/slightly down OI" if vacuum else "",
            f"risk={', '.join(risk_notes)}" if risk_notes else "risk=none major",
        ])
        return AnalysisResult(
            symbol=str(latest.get("symbol", "")), timeframe=CONFIG["TIMEFRAME"], data_window=f"{len(df)} candles",
            dominant_structural_pattern=pattern if pattern in ALLOWED_PATTERNS else "Mixed Structure",
            structural_bias=bias if bias in ALLOWED_BIASES else "Neutral / Unclear",
            readiness_level=readiness,
            signal_timing=signal_timing,
            cycle_position=cycle_position,
            price_acceptance=features.acceptance_state,
            oi_read=oi_read,
            oi_value_validation=validations["oi_value"],
            trades_read=validations["trade_value"],
            quote_volume_validation="Quote Volume confirmed" if "Quote Volume ↑" in validations["trade_value"] or "Real Execution" in validations["trade_value"] or "Real Capital" in validations["trade_value"] else "Quote Volume weak/missing",
            ls_divergence=ls.get("ls_divergence", "L/S unavailable"),
            whale_crowd_read=ls.get("whale_crowd_read", "unknown"),
            price_led_reset_ignition_state=pre["price_led_reset_ignition_with_oi_reload"],
            price_led_base_ignition_state=pre["price_led_base_ignition_without_reset"],
            price_led_base_vacuum_ignition_state=pre["price_led_base_vacuum_without_oi_expansion"],
            high_oi_compression_state=pre["high_oi_compression"],
            trigger_status="triggered" if features.trigger_detected else "not triggered",
            post_trigger_acceptance=pre["post_trigger_acceptance"],
            late_crowding_risk=pre["late_oi_crowding"],
            invalidation_risk=compact_join(risk_notes) or "No major invalidation risk detected",
            confidence=confidence,
            score=round(score, 2),
            rank_priority=round(rank_priority, 2),
            rsi_context_only=rsi_context,
            final_structural_summary=summary,
        )

    def confidence(self, pattern: str, readiness: str, accepted: bool, validations: Dict[str, str], ls: Dict[str, str], risks: List[str], cap: str, reliability: float) -> str:
        high_conditions = [
            validations["oi_value"] == "Real Position Expansion",
            "Real Capital Activation" in validations["trade_value"] or "Real Execution Expansion" in validations["trade_value"],
            accepted,
            ls.get("ls_divergence") not in {None, "L/S unavailable"},
            readiness in {"Confirmed Trigger", "Accepted Structure"},
            not risks,
            reliability > 0.75,
        ]
        vacuum_medium_high = "Vacuum" in pattern and accepted and ls.get("top_position_retention") == "True"
        if all(high_conditions):
            raw = "High"
        elif vacuum_medium_high or (pattern.startswith("Price-led") and accepted and len(risks) <= 1):
            raw = "Medium-High"
        elif readiness in {"Primed Structure", "Early-Live Structure", "Confirmed Trigger"} or len(risks) <= 2:
            raw = "Medium"
        else:
            raw = "Low"
        return self.apply_cap(raw, cap)

    @staticmethod
    def apply_cap(conf: str, cap: str) -> str:
        order = ["Low", "Medium", "Medium-High", "High"]
        return order[min(order.index(conf), order.index(cap if cap in order else "Medium"))]

    def score(self, pattern: str, readiness: str, accepted: bool, features: AnalysisFeatures, validations: Dict[str, str], ls: Dict[str, str], pre: Dict[str, Any], confidence: str) -> float:
        score = 0.0
        score += (10 - READINESS_ORDER.get(readiness, 10)) * 8
        score += state_strength(features.price_move_state) * 5
        score += state_strength(features.trades_state) * 4
        score += state_strength(features.quote_volume_state) * 4
        score += 10 if accepted else 0
        score += 12 if pre["price_led_base_vacuum_without_oi_expansion"] == "active" else 0
        score += 10 if pre["price_led_reset_ignition_with_oi_reload"] == "active" else 0
        score += 9 if pre["price_led_base_ignition_without_reset"] == "active" else 0
        score += 6 if ls.get("top_position_retention") == "True" else -4
        score += 5 if "Global ↓" in ls.get("ls_divergence", "") else 0
        score += 6 if validations["oi_value"] == "Real Position Expansion" else 0
        score += 7 if "Real Capital Activation" in validations["trade_value"] or "Real Execution" in validations["trade_value"] else 0
        score -= 12 if pre["late_oi_crowding"] == "active" else 0
        score -= 14 if readiness == "Failed / Invalidated" else 0
        score -= 8 if "Micro-trade Noise" in validations["trade_value"] else 0
        score += {"High": 8, "Medium-High": 5, "Medium": 2, "Low": -5}.get(confidence, 0)
        return max(0.0, min(100.0, score))

    def rank_priority(self, readiness: str, pattern: str, features: AnalysisFeatures, pre: Dict[str, Any], score: float) -> float:
        base = 100 - READINESS_ORDER.get(readiness, 10) * 8
        if pre["price_led_base_vacuum_without_oi_expansion"] == "active":
            base += 9
        if features.evidence.get("phase", {}).get("close_to_footprint"):
            base += 6
        if "Late" in readiness or "Failed" in readiness:
            base -= 20
        return max(0.0, min(100.0, base + score * 0.25))


# =============================================================================
# Orchestrator
# =============================================================================
class StructuralLiquidityScanner:
    """Complete V3.2.1 dynamic scanner."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = BinanceFuturesClient(config)
        self.baseline = DynamicBaselineEngine()
        self.quality = DataQualityChecker()
        self.phase = PhaseMemoryEngine()
        self.validation = ValidationEngine()
        self.price = PriceStructureEngine()
        self.acceptance = PriceAcceptanceEngine()
        self.ls = LSStructureEngine()
        self.pre = StructuralPreScanner()
        self.resolver = ConflictResolver()

    def symbols(self) -> List[str]:
        if self.config.get("SCAN_ALL_USDT_PERPETUALS"):
            return self.client.exchange_symbols()
        whitelist = self.config.get("SYMBOL_WHITELIST") or []
        if not whitelist:
            raise ValueError("SYMBOL_WHITELIST must be set when SCAN_ALL_USDT_PERPETUALS=False")
        return [s for s in whitelist if s not in set(self.config.get("SYMBOL_BLACKLIST") or [])]

    def frame_to_candles(self, df: pd.DataFrame, symbol: str) -> List[Candle]:
        candles: List[Candle] = []
        for _, row in df.iterrows():
            candles.append(Candle(
                timestamp=int(row["timestamp"]), symbol=symbol, open=safe_float(row["open"]), high=safe_float(row["high"]),
                low=safe_float(row["low"]), close=safe_float(row["close"]), volume=safe_float(row["volume"]),
                quote_volume=safe_float(row.get("quote_volume")), trades=safe_float(row.get("trades")),
                oi=safe_float(row.get("oi")), oi_change=safe_float(row.get("oi_change")), oi_change_pct=safe_float(row.get("oi_change_pct")),
                oi_value=safe_float(row.get("oi_value")), global_ls=safe_float(row.get("global_ls")),
                top_account_ls=safe_float(row.get("top_account_ls")), top_position_ls=safe_float(row.get("top_position_ls")),
                rsi=safe_float(row.get("rsi")),
            ))
        return candles

    def analyze_symbol(self, symbol: str) -> Optional[AnalysisResult]:
        try:
            raw, source_flags = self.client.fetch_symbol_frame(symbol)
            if raw.empty:
                return None
            raw["symbol"] = symbol
            df = self.baseline.enrich(raw)
            flags, cap, reliability = self.quality.check(df, source_flags, self.config)
            if len(df) < max(5, int(self.config["MIN_CANDLES_REQUIRED"] // 2)):
                return None
            b = self.baseline.snapshot(df)
            phase = self.phase.analyze(df, b)
            price_state = self.price.classify(df, b, phase)
            acceptance = self.acceptance.classify(df, phase)
            oi_value = self.validation.oi_value_validation(df, b) if self.config.get("USE_OI_VALUE_VALIDATION") else "Disabled"
            trade_value = self.validation.trade_value_validation(df, b) if self.config.get("USE_QUOTE_VOLUME_VALIDATION") else "Disabled"
            validations = {"oi_value": oi_value, "trade_value": trade_value}
            ls = self.ls.analyze(df, b)
            oi_read = OIStateEngine().classify(df, b, phase)
            pre = self.pre.scan(df, b, phase, validations, ls, acceptance)
            features = AnalysisFeatures(
                price_move_state=b["price_change"]["state"],
                oi_state=oi_read,
                trades_state=b["trades"]["state"],
                quote_volume_state=b["quote_volume"]["state"],
                global_ls_state=ls.get("global_ls_state", "unknown"),
                top_account_ls_state=ls.get("top_account_ls_state", "unknown"),
                top_position_ls_state=ls.get("top_position_ls_state", "unknown"),
                oi_value_validation=oi_value,
                trade_value_validation=trade_value,
                data_quality_flags=flags,
                phase_state=phase.get("phase_state", "unknown"),
                base_detected=phase.get("base_detected", False),
                reset_detected=phase.get("reset_detected", False),
                trigger_detected=phase.get("trigger_detected", False),
                acceptance_state=acceptance,
                compression_state=pre.get("high_oi_compression", "inactive"),
                late_crowding_state=pre.get("late_oi_crowding", "inactive"),
                evidence={"baseline": b, "phase": phase, "pre_scanner": pre, "data_quality": {"flags": flags, "cap": cap, "reliability": reliability}},
            )
            return self.resolver.resolve(df, features, price_state, oi_read, validations, ls, pre, cap, reliability, self.config["MODE"])
        except Exception as exc:  # noqa: BLE001 - symbol isolation is mandatory
            if self.config.get("PRINT_DEBUG_PER_SYMBOL"):
                logging.exception("Failed to analyze %s", symbol)
            else:
                logging.warning("Skipping %s due to %s", symbol, exc.__class__.__name__)
            return None

    def run_once(self) -> List[AnalysisResult]:
        symbols = self.symbols()
        logging.info("Scanning %s symbols | mode=%s timeframe=%s", len(symbols), self.config["MODE"], self.config["TIMEFRAME"])
        results: List[AnalysisResult] = []
        for idx, symbol in enumerate(symbols, start=1):
            result = self.analyze_symbol(symbol)
            if result:
                results.append(result)
            if self.config.get("PRINT_DEBUG_PER_SYMBOL"):
                logging.info("%s/%s %s %s", idx, len(symbols), symbol, result.dominant_structural_pattern if result else "no result")
            time.sleep(float(self.config["SLEEP_BETWEEN_REQUESTS"]))
        results.sort(key=lambda r: (r.rank_priority, r.score), reverse=True)
        selected = results[: int(self.config["TOP_N_RESULTS"])]
        self.print_results(selected)
        self.save_results(selected)
        return selected

    def print_results(self, results: Sequence[AnalysisResult]) -> None:
        print(f"\nStructural Liquidity Scanner V3.2.1 Dynamic | {utc_now_iso()} | TF={self.config['TIMEFRAME']} | MODE={self.config['MODE']}")
        print("-" * 180)
        header = f"{'rank':<5}{'symbol':<14}{'pattern':<52}{'bias':<32}{'readiness':<26}{'conf':<13}{'score':<8}{'risk':<30}summary"
        print(header)
        print("-" * 180)
        for rank, r in enumerate(results, start=1):
            risk = r.invalidation_risk[:28]
            summary = r.final_structural_summary[:90]
            print(f"{rank:<5}{r.symbol:<14}{r.dominant_structural_pattern[:50]:<52}{r.structural_bias[:30]:<32}{r.readiness_level[:24]:<26}{r.confidence:<13}{r.score:<8.2f}{risk:<30}{summary}")
        print("-" * 180)

    def save_results(self, results: Sequence[AnalysisResult]) -> None:
        os.makedirs(self.config["OUTPUT_DIR"], exist_ok=True)
        rows = [asdict(r) for r in results]
        if self.config.get("SAVE_JSON"):
            path = os.path.join(self.config["OUTPUT_DIR"], "scan_results_latest.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": utc_now_iso(), "config": self.public_config(), "results": rows}, f, ensure_ascii=False, indent=2)
            logging.info("Saved JSON: %s", path)
        if self.config.get("SAVE_CSV"):
            path = os.path.join(self.config["OUTPUT_DIR"], "scan_results_latest.csv")
            fieldnames = list(AnalysisResult.__dataclass_fields__.keys())
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logging.info("Saved CSV: %s", path)

    def public_config(self) -> Dict[str, Any]:
        return dict(self.config)


def setup_logging() -> None:
    level = logging.DEBUG if CONFIG.get("PRINT_DEBUG_PER_SYMBOL") else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")


def main() -> None:
    setup_logging()
    scanner = StructuralLiquidityScanner(CONFIG)
    try:
        scanner.run_once()
    except KeyboardInterrupt:
        print("\nGraceful stop requested by user.")
    except Exception as exc:  # noqa: BLE001
        if CONFIG.get("PRINT_DEBUG_PER_SYMBOL"):
            logging.exception("Scanner failed")
        else:
            logging.error("Scanner failed: %s", exc)


if __name__ == "__main__" and CONFIG.get("AUTO_RUN", True):
    main()
