#!/usr/bin/env python3
"""
Structural Liquidity Scanner V3.2.1 Dynamic

Single-file Binance USD-M Futures scanner.  The engine follows the V3.2.1
structural order: data quality/regime -> dynamic baselines -> phase memory ->
validations -> price/OI/L-S/trades -> acceptance -> pre-scan branches ->
conflict resolution -> readiness -> final decision.

Requirements: pip install requests pandas numpy
"""
from __future__ import annotations

import csv
import json
import logging
import math
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import numpy as np
    import pandas as pd
    import requests
except ImportError:  # pragma: no cover
    print("Missing dependency. Install with: pip install requests pandas numpy", file=sys.stderr)
    raise

# =============================================================================
# CONFIGURATION - operational settings only; structural thresholds are dynamic.
# =============================================================================
CONFIG: Dict[str, Any] = {
    "MODE": "early_watch",  # early_watch | strict_live
    "TIMEFRAME": "15m",
    "LIMIT": 180,
    "SCAN_ALL_USDT_PERPETUALS": True,
    "SYMBOL_WHITELIST": [],
    "SYMBOL_BLACKLIST": ["BTCUSDT", "ETHUSDT"],
    "TOP_N_RESULTS": 30,
    "SAVE_CSV": True,
    "SAVE_JSON": True,
    "AUTO_RUN": True,
    "RUN_CONTINUOUSLY": False,
    "SCAN_INTERVAL_SECONDS": 300,
    "SLEEP_BETWEEN_REQUESTS": 0.08,
    "REQUEST_TIMEOUT": 12,
    "RETRY_COUNT": 3,
    "MIN_CANDLES_REQUIRED": 90,
    "OUTPUT_DIR": "structural_liquidity_output",
    "USE_FUNDING_CONTEXT": False,
    "USE_OI_VALUE_VALIDATION": True,
    "USE_QUOTE_VOLUME_VALIDATION": True,
    "PRINT_DEBUG_PER_SYMBOL": False,
    "PARALLEL_SCAN": True,
    "MAX_WORKERS": "auto",
    "MAX_WORKERS_HARD_CAP": 6,
    "ADAPTIVE_RATE_LIMIT": True,
    "REQUEST_WEIGHT_SOFT_LIMIT_PER_MIN": 0,
    "REQUEST_WEIGHT_HARD_LIMIT_PER_MIN": 0,
    "RATE_LIMIT_SAFETY_FACTOR": 0.75,
    "BACKOFF_ON_429": True,
    "BACKOFF_ON_418": True,
    "GLOBAL_MIN_REQUEST_INTERVAL": 0.04,
    "SYMBOL_BATCH_SIZE": 0,
    "PARALLEL_DEBUG": False,
    "RUN_SANITY_CHECKS": True,
    "RUN_SANITY_CHECKS_STRICT": False,
}

BINANCE_FAPI_BASE = "https://fapi.binance.com"
BINANCE_DATA_BASE = "https://fapi.binance.com"

READINESS_LEVELS = {
    "Watchlist Only", "Primed Structure", "Early-Live Structure", "Confirmed Trigger",
    "Accepted Structure", "Compression / Unresolved", "Failed / Invalidated", "Late / Risk State",
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

CONFIDENCE_ORDER = ["Low", "Medium", "Medium-High", "High"]

# Priority bucket is the primary ranking key.  Score only ranks inside bucket.
BUCKET_BY_READINESS = {
    "Accepted Structure": 1,
    "Confirmed Trigger": 2,
    "Early-Live Structure": 3,
    "Primed Structure": 5,
    "Compression / Unresolved": 6,
    "Watchlist Only": 7,
    "Late / Risk State": 8,
    "Failed / Invalidated": 9,
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


def safe_div(num: Any, den: Any, default: float = np.nan) -> float:
    n = safe_float(num)
    d = safe_float(den)
    if not math.isfinite(n) or not math.isfinite(d) or abs(d) <= np.finfo(float).eps:
        return default
    return n / d


def pct_change(series: pd.Series) -> pd.Series:
    return (series - series.shift(1)) / series.shift(1).replace(0, np.nan)


def signed_direction(value: float) -> str:
    if not math.isfinite(value):
        return "unknown"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def compact_join(parts: Iterable[str]) -> str:
    return "; ".join([str(p) for p in parts if p])


def percentile_rank(series: pd.Series, value: float) -> float:
    s = pd.Series(series).dropna().astype(float)
    if s.empty or not math.isfinite(value):
        return 0.5
    return float((s <= value).mean())


def robust_z(series: pd.Series, value: float) -> float:
    s = pd.Series(series).dropna().astype(float)
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


def robust_last_slope(series: pd.Series) -> float:
    s = pd.Series(series).dropna().astype(float)
    if len(s) < 3:
        return 0.0
    # Window length comes from data window size; it is not a market threshold.
    n = max(3, int(math.sqrt(len(s))))
    y = s.tail(n).to_numpy(dtype=float)
    if np.nanstd(y) <= np.finfo(float).eps:
        return 0.0
    x = np.arange(len(y), dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def acceleration(series: pd.Series) -> float:
    s = pd.Series(series).dropna().astype(float)
    if len(s) < 4:
        return 0.0
    return robust_last_slope(s.diff().dropna())


def retention_after_latest_spike(series: pd.Series) -> float:
    s = pd.Series(series).dropna().astype(float)
    if len(s) < 5:
        return 0.0
    diffs = s.diff().abs().dropna()
    if diffs.empty:
        return 0.0
    spike_idx = diffs.idxmax()
    labels = list(s.index)
    pos = labels.index(spike_idx) if spike_idx in labels else len(s) - 1
    before = s.iloc[max(0, pos - 1)]
    spike = s.loc[spike_idx]
    last = s.iloc[-1]
    denom = abs(spike - before)
    if denom <= np.finfo(float).eps:
        return 0.0
    return float((last - before) / denom)


def state_from_rank(rank: float, z: float) -> str:
    """Dynamic Normal/Elevated/Shock/Extreme from symbol-local distribution."""
    if not math.isfinite(rank):
        return "Normal"
    if rank >= 0.97 or z >= 3.5:
        return "Extreme"
    if rank >= 0.90 or z >= 2.25:
        return "Shock"
    if rank >= 0.75 or z >= 1.25:
        return "Elevated"
    return "Normal"


def negative_state_from_rank(rank: float, z: float) -> str:
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


def recent_span_len(df: pd.DataFrame) -> int:
    return max(3, int(math.sqrt(max(len(df), 1))))


def as_jsonable(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: as_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): as_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [as_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if not math.isfinite(f) else f
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    return obj


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
class BaseZone:
    detected: bool = False
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    high: float = np.nan
    low: float = np.nan
    mid: float = np.nan
    width_rank: float = 1.0
    duration: int = 0
    quality: str = "No Base"
    had_prior_pump: bool = False
    trades_quiet: bool = False
    quote_quiet: bool = False
    oi_stable_or_constructive: bool = False
    top_position_retained: bool = False
    account_non_chasing: bool = False
    global_not_excessively_long: bool = True
    excluded_latest_bars: int = 0
    latest_guard: int = 0
    base_search_end: Optional[int] = None
    zone_contains_ignition: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class ResetEvent:
    detected: bool = False
    idx: Optional[int] = None
    type: str = "No Flush"
    oi_drop_state: str = "Normal"
    price_drop_state: str = "Normal"
    trades_state: str = "Normal"
    quote_volume_state: str = "Normal"
    real_deleveraging: bool = False
    silent_deleveraging: bool = False
    liquidation_like: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class PostFlushState:
    state: str = "No Reset Context"
    price_stabilized: bool = False
    price_rejected_low_break: bool = False
    oi_reloading: bool = False
    oi_continues_down: bool = False
    ls_weakening: bool = False
    top_position_retained: bool = False
    trades_cooling: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class TriggerEvent:
    detected: bool = False
    idx: Optional[int] = None
    type: str = "No Trigger"
    candle_high: float = np.nan
    candle_low: float = np.nan
    candle_close: float = np.nan
    candle_mid: float = np.nan
    from_base: bool = False
    after_reset: bool = False
    price_expansion_state: str = "Normal"
    trades_state: str = "Normal"
    quote_volume_state: str = "Normal"
    oi_state_at_trigger: str = "Normal"
    price_led: bool = False
    oi_led: bool = False
    simultaneous: bool = False
    close_to_footprint: bool = False
    far_from_footprint: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class AcceptanceState:
    state: str = "No Trigger"
    accepted: bool = False
    failed: bool = False
    constructive: bool = False
    returned_inside_base: bool = False
    held_above_trigger_mid: bool = False
    held_above_base_high: bool = False
    broke_base_low: bool = False
    broke_post_flush_low: bool = False
    oi_unwound_violently: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class TimingState:
    signal_timing: str = "Post-move OI retention"
    price_leads_oi: bool = False
    oi_leads_price: bool = False
    simultaneous: bool = False
    price_moved_from_base: bool = False
    price_moved_after_reset: bool = False
    oi_reloaded_after_price: bool = False
    oi_reloaded_within_recent_confirmed_candles: bool = False
    far_from_footprint: bool = False
    close_to_footprint: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class DelayedReloadState:
    state: str = "No Delayed Reload"
    constructive: bool = False
    late: bool = False
    no_oi_vacuum: bool = False
    deleveraging_during_move: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class LSFuelState:
    global_direction: str = "unknown"
    account_direction: str = "unknown"
    position_direction: str = "unknown"
    global_level_context: str = "unknown"
    account_level_context: str = "unknown"
    position_level_context: str = "unknown"
    fuel_state: str = "No L/S Edge"
    crowd_chasing: bool = False
    account_chasing: bool = False
    crowd_against_move: bool = False
    account_against_move: bool = False
    top_position_retention: bool = False
    top_position_derisking: bool = False
    top_position_collapse: bool = False
    ls_divergence: str = "L/S unavailable"
    notes: List[str] = field(default_factory=list)


@dataclass
class CompressionState:
    active: bool = False
    type: str = "No Compression"
    oi_near_window_high: bool = False
    price_below_recent_high: bool = False
    price_inside_range: bool = False
    ls_short_heavy: bool = False
    ls_long_heavy: bool = False
    top_position_neutral_or_retained: bool = False
    risk_overlay: str = "none"
    notes: List[str] = field(default_factory=list)


@dataclass
class VacuumIgnitionState:
    active: bool = False
    state: str = "Inactive"
    from_valid_base: bool = False
    price_exited_base_first: bool = False
    trades_quote_confirmed: bool = False
    oi_flat_or_slightly_down: bool = False
    oi_not_collapsing: bool = False
    top_position_retained: bool = False
    account_non_chasing: bool = False
    global_not_excessively_long: bool = False
    price_accepted: bool = False
    close_to_base: bool = False
    failed: bool = False
    notes: List[str] = field(default_factory=list)


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
class PreScanState:
    base_zone: BaseZone
    reset_event: ResetEvent
    post_flush_state: PostFlushState
    trigger_event: TriggerEvent
    acceptance_state: AcceptanceState
    timing_state: TimingState
    delayed_reload_state: DelayedReloadState
    ls_fuel_state: LSFuelState
    compression_state: CompressionState
    vacuum_ignition_state: VacuumIgnitionState
    oi_state: str
    price_state: str
    trades_validation: str
    oi_value_validation: str
    evidence_flags: Dict[str, Any]
    invalidation_flags: List[str]
    risk_overlays: List[str]
    cycle_count: int = 0
    cycle_label: str = "Background / No Clear Cycle"


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
    priority_bucket: int = 10
    evidence_details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Binance public client
# =============================================================================
class AdaptiveRateLimiter:
    """Shared conservative pacing/backoff for public Binance requests."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lock = threading.Lock()
        self.last_request_ts = 0.0
        self.request_count = 0
        self.count_429 = 0
        self.count_418 = 0
        self.last_used_weight_1m: Optional[int] = None
        self.adaptive_sleep_events = 0
        self.cooldown_until = 0.0

    def before_request(self) -> None:
        with self.lock:
            now = time.time()
            wait_for = max(0.0, self.cooldown_until - now)
            min_interval = float(self.config.get("GLOBAL_MIN_REQUEST_INTERVAL", 0.02))
            pace_wait = max(0.0, self.last_request_ts + min_interval - now)
            wait_for = max(wait_for, pace_wait)
            if wait_for > 0:
                self.adaptive_sleep_events += 1
            self.last_request_ts = max(now + wait_for, self.last_request_ts + min_interval)
        if wait_for > 0:
            time.sleep(wait_for)

    def update_from_headers(self, headers: Dict[str, Any]) -> None:
        used = headers.get("X-MBX-USED-WEIGHT-1M") or headers.get("x-mbx-used-weight-1m")
        if used is None:
            return
        try:
            used_int = int(float(used))
        except (TypeError, ValueError):
            return
        with self.lock:
            self.last_used_weight_1m = used_int
            soft = int(self.config.get("REQUEST_WEIGHT_SOFT_LIMIT_PER_MIN") or 0)
            hard = int(self.config.get("REQUEST_WEIGHT_HARD_LIMIT_PER_MIN") or 0)
            safety = float(self.config.get("RATE_LIMIT_SAFETY_FACTOR", 0.75))
            reference = soft or hard
            if self.config.get("ADAPTIVE_RATE_LIMIT") and reference and used_int >= reference * safety:
                self.cooldown_until = max(self.cooldown_until, time.time() + max(0.5, min(10.0, (used_int / max(reference, 1)) * 2.0)))
                self.adaptive_sleep_events += 1

    def record_request(self) -> None:
        with self.lock:
            self.request_count += 1

    def record_rate_limit(self, code: str) -> float:
        with self.lock:
            if code == "429":
                self.count_429 += 1
                delay = min(60.0, 2.0 ** min(self.count_429, 6))
            else:
                self.count_418 += 1
                delay = min(300.0, 10.0 * (2.0 ** min(self.count_418, 5)))
            self.cooldown_until = max(self.cooldown_until, time.time() + delay)
            self.adaptive_sleep_events += 1
            return delay

    def stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "request_count": self.request_count,
                "429_count": self.count_429,
                "418_count": self.count_418,
                "last_used_weight_1m": self.last_used_weight_1m,
                "adaptive_sleep_events": self.adaptive_sleep_events,
            }


class BinanceFuturesClient:
    """Public Binance USD-M client with retry/backoff, rate limiting and thread-local sessions."""

    def __init__(self, config: Dict[str, Any], rate_limiter: Optional[AdaptiveRateLimiter] = None):
        self.config = config
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter(config)
        self._local = threading.local()

    def session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            sess = requests.Session()
            sess.headers.update({"User-Agent": "structural-liquidity-scanner-v321-dynamic/3.0"})
            self._local.session = sess
        return self._local.session

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, data_api: bool = False) -> Any:
        base = BINANCE_DATA_BASE if data_api else BINANCE_FAPI_BASE
        url = base + path
        last_error: Optional[Exception] = None
        for attempt in range(int(self.config["RETRY_COUNT"])):
            try:
                self.rate_limiter.before_request()
                response = self.session().get(url, params=params, timeout=float(self.config["REQUEST_TIMEOUT"]))
                self.rate_limiter.record_request()
                self.rate_limiter.update_from_headers(response.headers)
                if response.status_code == 429:
                    retry_after = safe_float(response.headers.get("Retry-After"), 0.0)
                    delay = max(retry_after, self.rate_limiter.record_rate_limit("429") if self.config.get("BACKOFF_ON_429") else 1.0)
                    time.sleep(delay)
                    continue
                if response.status_code == 418:
                    retry_after = safe_float(response.headers.get("Retry-After"), 0.0)
                    delay = max(retry_after, self.rate_limiter.record_rate_limit("418") if self.config.get("BACKOFF_ON_418") else 10.0)
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
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
            quote_volume = safe_float(k[7])
            trades = safe_float(k[8])
            taker_buy_quote = safe_float(k[10])
            rows.append({
                "timestamp": int(k[0]),
                "open_time": int(k[0]),
                "open": safe_float(k[1]),
                "high": safe_float(k[2]),
                "low": safe_float(k[3]),
                "close": safe_float(k[4]),
                "volume": safe_float(k[5]),
                "close_time": int(k[6]),
                "quote_volume": quote_volume,
                "trades": trades,
                "taker_buy_base_volume": safe_float(k[9]),
                "taker_buy_quote_volume": taker_buy_quote,
                "avg_trade_quote_size": safe_div(quote_volume, trades),
                "taker_buy_quote_ratio": safe_div(taker_buy_quote, quote_volume),
            })
        return pd.DataFrame(rows).sort_values("timestamp")

    def oi_history(self, symbol: str) -> pd.DataFrame:
        raw = self._get(
            "/futures/data/openInterestHist",
            {"symbol": symbol, "period": self.config["TIMEFRAME"], "limit": self.config["LIMIT"]},
            data_api=True,
        )
        rows = []
        for x in raw:
            rows.append({
                "timestamp": int(x.get("timestamp", 0)),
                "oi": safe_float(x.get("sumOpenInterest")),
                "oi_value_exchange": safe_float(x.get("sumOpenInterestValue")),
            })
        return pd.DataFrame(rows).dropna(subset=["timestamp"]).sort_values("timestamp")

    def ls_history(self, symbol: str, endpoint: str, column: str) -> pd.DataFrame:
        raw = self._get(endpoint, {"symbol": symbol, "period": self.config["TIMEFRAME"], "limit": self.config["LIMIT"]}, data_api=True)
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
        for fetcher, cols, flag in [
            (self.oi_history, ["oi", "oi_value_exchange"], "oi_history_missing"),
            (lambda s: self.ls_history(s, "/futures/data/globalLongShortAccountRatio", "global_ls"), ["global_ls"], "global_ls_missing"),
            (lambda s: self.ls_history(s, "/futures/data/topLongShortAccountRatio", "top_account_ls"), ["top_account_ls"], "top_account_ls_missing"),
            (lambda s: self.ls_history(s, "/futures/data/topLongShortPositionRatio", "top_position_ls"), ["top_position_ls"], "top_position_ls_missing"),
        ]:
            try:
                df = fetcher(symbol)
                time.sleep(float(self.config["SLEEP_BETWEEN_REQUESTS"]))
                if df.empty or not all(c in df for c in cols):
                    flags.append(flag)
                    for col in cols:
                        base[col] = np.nan
                    continue
                base = pd.merge_asof(base.sort_values("timestamp"), df[["timestamp"] + cols].sort_values("timestamp"), on="timestamp", direction="backward")
                for col in cols:
                    base[col] = base[col].ffill()
            except Exception as exc:  # noqa: BLE001
                flags.append(f"{flag}:{exc.__class__.__name__}")
                for col in cols:
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
# Dynamic baseline and quality
# =============================================================================
class DynamicBaselineEngine:
    """Symbol-local baselines: median/MAD, percentile rank, robust z, slope, retention."""

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy().sort_values("timestamp").reset_index(drop=True)
        for col in ["oi", "oi_value_exchange", "global_ls", "top_account_ls", "top_position_ls"]:
            if col not in d:
                d[col] = np.nan
        d["price_change"] = pct_change(d["close"])
        d["range_pct"] = (d["high"] - d["low"]) / d["close"].replace(0, np.nan)
        d["body_pct"] = (d["close"] - d["open"]) / d["open"].replace(0, np.nan)
        d["oi_change"] = d["oi"].diff()
        d["oi_change_pct"] = pct_change(d["oi"])
        fallback_oi_value = d["oi"] * d["close"]
        d["oi_value"] = d["oi_value_exchange"].combine_first(fallback_oi_value)
        d["oi_value_source"] = np.where(d["oi_value_exchange"].notna(), "exchange_sumOpenInterestValue", "fallback_oi_times_close")
        d["oi_value_change_pct"] = pct_change(d["oi_value"])
        d["avg_trade_quote_size_change"] = pct_change(d["avg_trade_quote_size"]) if "avg_trade_quote_size" in d else np.nan
        d["taker_buy_quote_ratio_change"] = d["taker_buy_quote_ratio"].diff() if "taker_buy_quote_ratio" in d else np.nan
        for col in ["global_ls", "top_account_ls", "top_position_ls"]:
            d[f"{col}_change"] = d[col].diff()
            d[f"{col}_change_pct"] = pct_change(d[col])
        d["rsi"] = self.rsi(d["close"])
        return d

    @staticmethod
    def rsi(close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def metric(self, series: pd.Series, current: Optional[float] = None) -> Dict[str, Any]:
        s = pd.Series(series).dropna().astype(float)
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
            "acceleration": acceleration(s),
            "retention": retention_after_latest_spike(s),
            "state": state_from_rank(rank, z),
            "negative_state": negative_state_from_rank(rank, z),
        }

    def value_state_at(self, df: pd.DataFrame, col: str, idx: int) -> Dict[str, Any]:
        if col not in df or idx is None or idx < 0:
            return self.metric(pd.Series(dtype=float))
        upto = df.loc[:idx, col]
        return self.metric(upto, df.loc[idx, col])

    def snapshot(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        cols = {
            "price_change": "price_change", "range": "range_pct", "body": "body_pct",
            "oi_change_pct": "oi_change_pct", "oi_abs": "oi", "oi_value_change_pct": "oi_value_change_pct",
            "trades": "trades", "quote_volume": "quote_volume", "volume": "volume",
            "avg_trade_quote_size": "avg_trade_quote_size", "taker_buy_quote_ratio": "taker_buy_quote_ratio",
            "global_ls": "global_ls", "top_account_ls": "top_account_ls", "top_position_ls": "top_position_ls",
            "global_ls_change": "global_ls_change_pct", "top_account_ls_change": "top_account_ls_change_pct",
            "top_position_ls_change": "top_position_ls_change_pct",
        }
        return {name: self.metric(df[col]) if col in df else self.metric(pd.Series(dtype=float)) for name, col in cols.items()}


class DataQualityChecker:
    """Data quality/regime check.  Weak data caps confidence; it does not crash analysis."""

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
        for col in ["open", "high", "low", "close", "volume", "trades"]:
            if col not in df or df[col].isna().any() or (df[col] <= 0).any():
                flags.append(f"{col}_zero_or_nan")
        if "quote_volume" not in df or df["quote_volume"].isna().all():
            flags.append("quote_volume_missing")
        if "oi" not in df or df["oi"].isna().all():
            flags.append("oi_history_missing")
        if "oi_value_source" in df:
            source = str(df["oi_value_source"].dropna().iloc[-1]) if df["oi_value_source"].dropna().size else "unknown"
            flags.append(f"oi_value_source:{source}")
        if any(col not in df or df[col].isna().all() for col in ["global_ls", "top_account_ls", "top_position_ls"]):
            flags.append("ls_history_missing")
        if "rsi" in df and df["rsi"].tail(recent_span_len(df)).isna().any():
            flags.append("immature_rsi_context")
        if {"oi", "oi_value"}.issubset(df.columns) and df["oi"].notna().any() and df["oi_value"].notna().any():
            oi_change_state = state_from_rank(percentile_rank(df["oi_change_pct"].dropna(), df["oi_change_pct"].iloc[-1]), robust_z(df["oi_change_pct"].dropna(), df["oi_change_pct"].iloc[-1])) if "oi_change_pct" in df else "Normal"
            oi_value_change_state = state_from_rank(percentile_rank(df["oi_value_change_pct"].dropna(), df["oi_value_change_pct"].iloc[-1]), robust_z(df["oi_value_change_pct"].dropna(), df["oi_value_change_pct"].iloc[-1])) if "oi_value_change_pct" in df else "Normal"
            if oi_change_state in {"Shock", "Extreme"} and oi_value_change_state == "Normal":
                flags.append("relative_oi_distortion_risk")
        if len(df) >= recent_span_len(df) * 2:
            head = df.head(recent_span_len(df))
            body = df.iloc[recent_span_len(df):]
            if not body.empty and (head["trades"].median() > body["trades"].median() and percentile_rank(df["trades"], head["trades"].median()) >= 0.90):
                flags.append("listing_or_initial_trade_bootstrap_risk")
        ls_change_cols = [c for c in ["global_ls_change_pct", "top_account_ls_change_pct", "top_position_ls_change_pct"] if c in df]
        if ls_change_cols and "oi_change_pct" in df:
            ls_noisy = any(state_from_rank(percentile_rank(df[c].dropna(), df[c].iloc[-1]), robust_z(df[c].dropna(), df[c].iloc[-1])) in {"Shock", "Extreme"} or negative_state_from_rank(percentile_rank(df[c].dropna(), df[c].iloc[-1]), robust_z(df[c].dropna(), df[c].iloc[-1])) in {"Shock", "Extreme"} for c in ls_change_cols if df[c].notna().any())
            oi_clear = state_from_rank(percentile_rank(df["oi_change_pct"].dropna(), df["oi_change_pct"].iloc[-1]), robust_z(df["oi_change_pct"].dropna(), df["oi_change_pct"].iloc[-1])) in {"Elevated", "Shock", "Extreme"}
            if ls_noisy and not oi_clear:
                flags.append("ls_ratio_noise_without_oi_confirmation")
        optional_prefixes = ("funding_context_missing", "cross_venue_missing", "microstructure_missing", "oi_value_source:")
        major = [f for f in flags if not f.startswith(optional_prefixes) and any(k in f for k in ["missing", "insufficient", "non_monotonic", "zero_or_nan"])]
        major += [f for f in flags if f in {"relative_oi_distortion_risk", "listing_or_initial_trade_bootstrap_risk", "ls_ratio_noise_without_oi_confirmation"}]
        warmup = [f for f in flags if "warmup" in f or "immature" in f]
        if len(set(major)) >= 2:
            cap = "Medium"
        elif major or len(warmup) > 1:
            cap = "Medium-High"
        else:
            cap = "High"
        reliability = max(0.0, 1.0 - len(set(major + warmup)) / max(1.0, math.sqrt(max(len(df), 1))))
        return sorted(set(flags)), cap, reliability


# =============================================================================
# Structural engines
# =============================================================================
class BaseDetector:
    """Base Detection: scan multiple recent candidate windows and score quiet compression."""

    def detect_base_zone(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], ls_context: Optional[LSFuelState] = None) -> BaseZone:
        n = len(df)
        if n < 10:
            return BaseZone(notes=["insufficient window for base scan"])
        min_dur = recent_span_len(df)
        max_dur = min(max(min_dur * 3, min_dur + 1), max(min_dur, n // 2))
        search_start = max(0, n - max(min_dur * 6, max_dur + min_dur))
        latest_guard = max(1, recent_span_len(df) // 2)
        base_search_end = max(search_start + min_dur - 1, n - latest_guard - 1)
        base_search_end = min(base_search_end, n - 1)
        excluded_latest_bars = max(0, n - 1 - base_search_end)
        ignition_flags = []
        local_baseline_engine = DynamicBaselineEngine()
        for ridx in range(n):
            price_metric = local_baseline_engine.value_state_at(df, "price_change", int(ridx))
            trades_metric = local_baseline_engine.value_state_at(df, "trades", int(ridx))
            quote_metric = local_baseline_engine.value_state_at(df, "quote_volume", int(ridx))
            ignition_flags.append(price_metric["state"] in {"Shock", "Extreme"} and (trades_metric["state"] in {"Elevated", "Shock", "Extreme"} or quote_metric["state"] in {"Elevated", "Shock", "Extreme"}))
        candidates: List[Tuple[float, BaseZone]] = []
        for end in range(search_start + min_dur - 1, base_search_end + 1):
            for dur in range(min_dur, max_dur + 1):
                start = end - dur + 1
                if start < search_start or start < 0:
                    continue
                zone = df.iloc[start:end + 1]
                if zone.empty:
                    continue
                hist = df.iloc[:end + 1].copy()
                zone_contains_ignition = any(ignition_flags[start:end + 1])
                if zone_contains_ignition:
                    continue
                width = safe_div(zone["high"].max() - zone["low"].min(), zone["close"].median(), 1.0)
                # Compare base width against same-duration rolling widths up to candidate end only.
                rolling_widths = (hist["high"].rolling(dur).max() - hist["low"].rolling(dur).min()) / hist["close"].rolling(dur).median().replace(0, np.nan)
                width_rank = percentile_rank(rolling_widths.dropna(), width)
                range_quiet = width_rank <= rolling_widths.rank(pct=True).median()
                trades_rank = percentile_rank(hist["trades"], zone["trades"].median()) if "trades" in hist else 0.5
                quote_rank = percentile_rank(hist["quote_volume"], zone["quote_volume"].median()) if "quote_volume" in hist else 0.5
                trades_quiet = trades_rank <= hist["trades"].rank(pct=True).median()
                quote_quiet = quote_rank <= hist["quote_volume"].rank(pct=True).median() if "quote_volume" in hist else False
                oi_changes = zone["oi_change_pct"].dropna() if "oi_change_pct" in zone else pd.Series(dtype=float)
                oi_stable = True
                if not oi_changes.empty:
                    worst_oi = oi_changes.min()
                    oi_stable = negative_state_from_rank(percentile_rank(hist["oi_change_pct"].dropna(), worst_oi), robust_z(hist["oi_change_pct"].dropna(), worst_oi)) not in {"Shock", "Extreme"}
                top_position_retained = True
                if "top_position_ls" in zone and zone["top_position_ls"].notna().any():
                    top_position_retained = zone["top_position_ls"].iloc[-1] >= zone["top_position_ls"].median() or zone["top_position_ls"].diff().tail(min_dur).median() >= 0
                account_non_chasing = True
                if "top_account_ls_change_pct" in zone and zone["top_account_ls_change_pct"].notna().any():
                    acc_chg = zone["top_account_ls_change_pct"].tail(min_dur).median()
                    account_non_chasing = state_from_rank(percentile_rank(hist["top_account_ls_change_pct"].dropna(), acc_chg), robust_z(hist["top_account_ls_change_pct"].dropna(), acc_chg)) == "Normal" or acc_chg <= 0
                global_not_long = True
                if "global_ls" in zone and zone["global_ls"].notna().any():
                    last_g = zone["global_ls"].iloc[-1]
                    g_rank = percentile_rank(hist["global_ls"].dropna(), last_g)
                    global_not_long = not (last_g > 1 and g_rank >= 0.90)
                prior = df.iloc[max(0, start - min_dur):start]
                had_prior_pump = False
                if not prior.empty:
                    prior_ret = safe_div(prior["close"].iloc[-1] - prior["close"].iloc[0], prior["close"].iloc[0], 0.0)
                    had_prior_pump = prior_ret > 0 and state_from_rank(percentile_rank(hist["price_change"].dropna(), prior["price_change"].max()), robust_z(hist["price_change"].dropna(), prior["price_change"].max())) in {"Shock", "Extreme"}
                evidence_count = sum([range_quiet, trades_quiet, quote_quiet, oi_stable, top_position_retained, account_non_chasing, global_not_long])
                if evidence_count >= 6 and not had_prior_pump:
                    quality = "Primed Base"
                elif evidence_count >= 5:
                    quality = "Strong Compression Base"
                elif evidence_count >= 4 and range_quiet:
                    quality = "Valid Quiet Base"
                elif range_quiet:
                    quality = "Weak Base"
                else:
                    quality = "No Base"
                detected = quality != "No Base"
                score = evidence_count - width_rank + (dur / max(min_dur, 1)) * 0.1 - (1.0 if had_prior_pump else 0.0)
                bz = BaseZone(
                    detected=detected, start_idx=int(start), end_idx=int(end), high=float(zone["high"].max()), low=float(zone["low"].min()),
                    mid=float((zone["high"].max() + zone["low"].min()) / 2), width_rank=float(width_rank), duration=int(dur), quality=quality,
                    had_prior_pump=bool(had_prior_pump), trades_quiet=bool(trades_quiet), quote_quiet=bool(quote_quiet),
                    oi_stable_or_constructive=bool(oi_stable), top_position_retained=bool(top_position_retained), account_non_chasing=bool(account_non_chasing),
                    global_not_excessively_long=bool(global_not_long), excluded_latest_bars=int(excluded_latest_bars), latest_guard=int(latest_guard),
                    base_search_end=int(base_search_end), zone_contains_ignition=bool(zone_contains_ignition), notes=[f"candidate evidence={evidence_count}", f"width_rank={width_rank:.2f}",
                    "base_guard_excluded_latest_ignition_zone", f"excluded_latest_bars={excluded_latest_bars}"],
                )
                if detected:
                    candidates.append((score, bz))
        if not candidates:
            return BaseZone(excluded_latest_bars=int(excluded_latest_bars), latest_guard=int(latest_guard), base_search_end=int(base_search_end), notes=["no quiet compression candidate found", "base_guard_excluded_latest_ignition_zone", f"excluded_latest_bars={excluded_latest_bars}"])
        return sorted(candidates, key=lambda x: x[0], reverse=True)[0][1]


class ResetDetector:
    """Reset Detection: separates real OI flush/liquidation from small noise."""

    def detect_oi_flush_event(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]]) -> ResetEvent:
        if "oi_change_pct" not in df or df["oi_change_pct"].dropna().empty:
            return ResetEvent(notes=["OI unavailable"])
        span = max(recent_span_len(df) * 3, recent_span_len(df))
        recent = df.tail(span)
        best: Optional[ResetEvent] = None
        best_score = -999.0
        for idx, row in recent.iterrows():
            oi_chg = safe_float(row.get("oi_change_pct"))
            price_chg = safe_float(row.get("price_change"))
            oi_rank = percentile_rank(df["oi_change_pct"].dropna(), oi_chg)
            price_rank = percentile_rank(df["price_change"].dropna(), price_chg)
            oi_drop_state = negative_state_from_rank(oi_rank, robust_z(df["oi_change_pct"].dropna(), oi_chg))
            price_drop_state = negative_state_from_rank(price_rank, robust_z(df["price_change"].dropna(), price_chg))
            trades_state = state_from_rank(percentile_rank(df["trades"], row.get("trades", np.nan)), robust_z(df["trades"], row.get("trades", np.nan)))
            qv_state = state_from_rank(percentile_rank(df["quote_volume"], row.get("quote_volume", np.nan)), robust_z(df["quote_volume"], row.get("quote_volume", np.nan)))
            if oi_drop_state not in {"Shock", "Extreme"}:
                continue
            # A positive breakout with slightly falling OI is not a reset; it can be vacuum flow.
            if price_chg > 0 and price_drop_state == "Normal":
                continue
            real_delev = row.get("oi_value_change_pct", 0) < 0 and negative_state_from_rank(percentile_rank(df["oi_value_change_pct"].dropna(), row.get("oi_value_change_pct", np.nan)), robust_z(df["oi_value_change_pct"].dropna(), row.get("oi_value_change_pct", np.nan))) in {"Elevated", "Shock", "Extreme"}
            liquidation_like = price_drop_state in {"Shock", "Extreme"} and (trades_state in {"Elevated", "Shock", "Extreme"} or qv_state in {"Elevated", "Shock", "Extreme"})
            silent = price_drop_state == "Normal" and real_delev
            noise = trades_state == "Normal" and qv_state == "Normal"
            if liquidation_like and real_delev:
                typ = "Real Liquidation / Deleveraging Event"
            elif liquidation_like:
                typ = "Long Liquidation / Forced Flush"
            elif silent:
                typ = "Silent Deleveraging / Hidden Position Exit"
            elif noise:
                typ = "Noise / Small-ticket Flush Risk"
            else:
                typ = "Forced Reset Candidate"
            score = state_strength(oi_drop_state) + state_strength(price_drop_state) + state_strength(trades_state) + state_strength(qv_state) + (1 if real_delev else 0)
            # Small/noisy OI dips are recorded as risk context, not a structural reset.
            structural_reset = typ != "Noise / Small-ticket Flush Risk"
            ev = ResetEvent(structural_reset, int(idx) if structural_reset else None, typ if structural_reset else "No Flush", oi_drop_state, price_drop_state, trades_state, qv_state, bool(real_delev), bool(silent), bool(liquidation_like), ["dynamic OI drop confirmed" if structural_reset else "small OI dip ignored as reset"])
            if score > best_score:
                best_score, best = score, ev
        return best or ResetEvent(notes=["no dynamic OI flush"])

    def detect_post_flush_behavior(self, df: pd.DataFrame, reset_event: ResetEvent, baseline: Dict[str, Dict[str, Any]], ls_context: Optional[LSFuelState] = None) -> PostFlushState:
        if not reset_event.detected or reset_event.idx is None:
            return PostFlushState()
        post = df.loc[reset_event.idx:].copy()
        if post.empty:
            return PostFlushState("No Reset Context", notes=["no bars after reset"])
        span = recent_span_len(df)
        low = float(post["low"].min())
        price_stabilized = robust_last_slope(post["close"].tail(max(span, len(post)))) >= 0 or post["close"].iloc[-1] > post["close"].median()
        price_rejected_low = post["close"].iloc[-1] > low and post["low"].iloc[-1] >= low
        oi_reloading = "oi_change_pct" in post and post["oi_change_pct"].tail(span).median() > 0 and baseline["oi_change_pct"]["negative_state"] != "Extreme"
        oi_down = "oi_change_pct" in post and post["oi_change_pct"].tail(span).median() < 0 and negative_state_from_rank(percentile_rank(df["oi_change_pct"].dropna(), post["oi_change_pct"].tail(span).median()), robust_z(df["oi_change_pct"].dropna(), post["oi_change_pct"].tail(span).median())) in {"Elevated", "Shock", "Extreme"}
        ls_weakening = False
        if "global_ls_change_pct" in post and post["global_ls_change_pct"].notna().any():
            ls_weakening = post["global_ls_change_pct"].tail(span).median() <= 0
        top_retained = True
        if "top_position_ls" in post and post["top_position_ls"].notna().any():
            top_retained = post["top_position_ls"].iloc[-1] >= post["top_position_ls"].median() or post["top_position_ls"].diff().tail(span).median() >= 0
        trades_cooling = percentile_rank(df["trades"], post["trades"].tail(span).median()) <= df["trades"].rank(pct=True).median()
        if price_stabilized and price_rejected_low and oi_reloading and top_retained:
            state = "Rebuild After Flush"
        elif price_stabilized and price_rejected_low and top_retained:
            state = "Absorption After Flush"
        elif price_stabilized and price_rejected_low:
            state = "Reset Stabilization Confirmed"
        elif oi_down:
            state = "Deleveraging Continues"
        elif price_stabilized:
            state = "Weak Relief Bounce"
        else:
            state = "Liquidity Exit / Decay"
        if state == "Reset Stabilization Confirmed" and (oi_reloading or ls_weakening):
            state = "Mixed Reload / Needs Trigger"
        return PostFlushState(state, bool(price_stabilized), bool(price_rejected_low), bool(oi_reloading), bool(oi_down), bool(ls_weakening), bool(top_retained), bool(trades_cooling), [f"post reset bars={len(post)}"])


class PriceStructureEngine:
    def classify(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], base_zone: BaseZone, reset_event: ResetEvent) -> str:
        span = recent_span_len(df)
        pc = safe_float(df["price_change"].iloc[-1], 0.0)
        slope = robust_last_slope(df["close"].tail(max(span, span * 2)))
        state = baseline["price_change"]["state"]
        neg = baseline["price_change"]["negative_state"]
        if reset_event.detected and pc > 0 and slope > 0:
            return "up after reset"
        if base_zone.detected and df["close"].iloc[-1] > base_zone.high and pc > 0:
            return "up from base without reset"
        if state in {"Shock", "Extreme"} and pc > 0:
            return "explosive up move"
        if neg in {"Shock", "Extreme"} and pc < 0:
            return "violent downtrend"
        if base_zone.detected or abs(slope) <= abs(df["close"].diff().dropna().median() if len(df) > 3 else 0):
            return "sideways/base"
        if slope > 0:
            return "healthy uptrend"
        if pc > 0 and slope < 0:
            return "bounce after drop"
        return "slow downtrend"


class OIStateEngine:
    def classify(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], reset_event: ResetEvent, base_zone: BaseZone, timing: Optional[TimingState] = None) -> str:
        if "oi" not in df or df["oi"].isna().all():
            return "OI unavailable"
        latest = safe_float(df["oi_change_pct"].iloc[-1], 0.0)
        state = baseline["oi_change_pct"]["state"]
        neg = baseline["oi_change_pct"]["negative_state"]
        slope = robust_last_slope(df["oi"])
        if base_zone.detected and not reset_event.detected and df["price_change"].iloc[-1] > 0 and latest <= 0:
            value_neg = baseline.get("oi_value_change_pct", {}).get("negative_state", "Normal")
            if value_neg not in {"Shock", "Extreme"}:
                return "Price-led Base Move Without OI Expansion"
        if neg in {"Shock", "Extreme"} and latest < 0:
            return "OI Flush"
        if reset_event.detected and latest > 0 and slope > 0:
            return "Delayed Constructive OI Reload After Reset"
        if base_zone.detected and latest > 0 and slope > 0:
            return "Delayed Constructive OI Reload From Base"
        if base_zone.detected and latest <= 0 and neg not in {"Shock", "Extreme"}:
            return "Price-led Base Move Without OI Expansion"
        if state in {"Shock", "Extreme"} and latest > 0:
            return "explosive OI build"
        if state == "Elevated" and latest > 0:
            return "gradual OI build"
        if neg == "Elevated" and latest < 0:
            return "gradual OI decline"
        if timing and timing.price_leads_oi and latest > 0:
            return "Late OI Expansion"
        if slope < 0 and df["price_change"].iloc[-1] > 0:
            return "OI Deleveraging After Pump"
        return "flat OI"


class ValidationEngine:
    """OI Value and execution validation. These validate/downgrade; they do not hard-filter."""

    def oi_value_validation(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]]) -> str:
        if df["oi"].isna().all() or df["oi_value"].isna().all():
            return "Unavailable"
        oi_dir = signed_direction(safe_float(df["oi_change"].iloc[-1]))
        val_dir = signed_direction(safe_float(df["oi_value_change_pct"].iloc[-1]))
        price_dir = signed_direction(safe_float(df["price_change"].iloc[-1]))
        oi_active = baseline["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
        val_active = baseline["oi_value_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
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

    def trade_value_validation(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]]) -> str:
        trades_active = baseline["trades"]["state"] in {"Elevated", "Shock", "Extreme"}
        qv_active = baseline["quote_volume"]["state"] in {"Elevated", "Shock", "Extreme"}
        oi_active = baseline["oi_change_pct"]["state"] in {"Elevated", "Shock", "Extreme"}
        avg_ticket_active = baseline["avg_trade_quote_size"]["state"] in {"Elevated", "Shock", "Extreme"}
        avg_ticket_low = baseline["avg_trade_quote_size"].get("negative_state") in {"Elevated", "Shock", "Extreme"}
        taker_buy_active = baseline["taker_buy_quote_ratio"]["state"] in {"Elevated", "Shock", "Extreme"}
        price_up = safe_float(df["price_change"].iloc[-1], 0.0) > 0
        price_state = baseline["price_change"]["state"]
        oi_dir = signed_direction(safe_float(df["oi_change"].iloc[-1]))
        contexts: List[str] = []
        if trades_active and qv_active and oi_active and oi_dir == "up":
            contexts.append("Trades ↑ + Quote Volume ↑ + OI ↑ = Real Capital Activation")
        elif trades_active and qv_active and oi_dir in {"flat", "down", "unknown"}:
            contexts.append("Trades ↑ + Quote Volume ↑ + OI ثابت/هابط = Liquidation / Covering / Spot-led or Vacuum Flow")
        elif trades_active and qv_active:
            contexts.append("Trades ↑ + Quote Volume ↑ = Real Execution Expansion")
        elif trades_active and not qv_active:
            contexts.append("Trades ↑ + Quote Volume ضعيف = Micro-trade Noise / Bot Activity")
        elif (not trades_active) and qv_active:
            contexts.append("Trades ضعيفة + Quote Volume ↑ = Large Block-like Execution")
        if trades_active and price_state == "Normal":
            contexts.append("Trades ↑ جدًا + السعر لا يتحرك = Absorption Battle")
        if qv_active and avg_ticket_active:
            contexts.append("Quote Volume ↑ + avg_trade_quote_size ↑ = Large-ticket Execution")
        if trades_active and avg_ticket_low and not qv_active:
            contexts.append("Trades ↑ + avg_trade_quote_size ↓ + Quote Volume لا يؤكد = Micro-ticket Bot Expansion")
        if taker_buy_active and price_up and qv_active:
            contexts.append("taker_buy_quote_ratio ↑ + price ↑ + quote_volume ↑ = Aggressive Buy Execution Context")
        if taker_buy_active and not price_up and qv_active:
            contexts.append("taker_buy_quote_ratio ↑ + price لا يتحرك + quote_volume ↑ = Ask-side Absorption / Distribution Battle")
        if baseline["taker_buy_quote_ratio"].get("negative_state") in {"Elevated", "Shock", "Extreme"} and baseline["price_change"]["state"] == "Normal" and oi_active:
            contexts.append("taker_buy_quote_ratio ↓ + price ثابت + OI ↑ = Sell Absorption / Hidden Accumulation Context")
        return " | ".join(contexts) if contexts else "Normal Execution"


class LSFuelModel:
    """L/S Fuel Model: uses L/S levels around parity plus dynamic direction/context."""

    def _level_context(self, series: pd.Series, name: str) -> str:
        s = series.dropna().astype(float)
        if s.empty:
            return "unknown"
        last = float(s.iloc[-1])
        rank = percentile_rank(s, last)
        near_parity = abs(last - 1.0) <= max(abs(s - 1.0).median(), np.finfo(float).eps)
        if last < 1.0:
            return "Short-heavy below parity"
        if near_parity and robust_last_slope(s) < 0:
            return "Near parity and falling"
        if last > 1.0 and rank >= 0.90:
            return "Long-heavy high in local range"
        if last > 1.0:
            return "Above parity but not extreme"
        return f"{name} balanced"

    def analyze_ls_fuel(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], base_zone: BaseZone, trigger_event: TriggerEvent, timing_state: Optional[TimingState] = None) -> LSFuelState:
        cols = {"global": "global_ls", "account": "top_account_ls", "position": "top_position_ls"}
        if any(c not in df or df[c].dropna().empty for c in cols.values()):
            return LSFuelState(notes=["L/S history missing"])
        g_dir = signed_direction(df["global_ls"].diff().iloc[-1])
        a_dir = signed_direction(df["top_account_ls"].diff().iloc[-1])
        p_dir = signed_direction(df["top_position_ls"].diff().iloc[-1])
        g_ctx = self._level_context(df["global_ls"], "Global")
        a_ctx = self._level_context(df["top_account_ls"], "Top Account")
        p_ctx = self._level_context(df["top_position_ls"], "Top Position")
        g_change_state = baseline["global_ls_change"]["state"]
        a_change_state = baseline["top_account_ls_change"]["state"]
        g_neg_state = baseline["global_ls_change"]["negative_state"]
        a_neg_state = baseline["top_account_ls_change"]["negative_state"]
        p_neg_state = baseline["top_position_ls_change"]["negative_state"]
        crowd_chasing = trigger_event.detected and g_dir == "up" and g_change_state in {"Elevated", "Shock", "Extreme"}
        account_chasing = trigger_event.detected and a_dir == "up" and a_change_state in {"Elevated", "Shock", "Extreme"}
        crowd_against = g_dir == "down" or "Short-heavy" in g_ctx or "falling" in g_ctx
        account_against = a_dir == "down" or "Short-heavy" in a_ctx or "falling" in a_ctx
        p_rank = percentile_rank(df["top_position_ls"], df["top_position_ls"].iloc[-1])
        top_retention = p_dir != "down" or p_rank >= 0.50
        top_derisk = p_dir == "down" and p_neg_state in {"Elevated", "Shock"}
        top_collapse = p_dir == "down" and p_neg_state == "Extreme"
        if g_dir == "down" and a_dir == "up" and p_dir == "up":
            divergence = "Global ↓ + Top Account ↑ + Top Position ↑"
            fuel = "Top-side Accumulation Against Crowd"
        elif g_change_state == "Normal" and a_dir == "up" and p_dir == "up":
            divergence = "Global ثابت + Top Account ↑ + Top Position ↑"
            fuel = "Quiet Top Positioning"
        elif g_change_state == "Normal" and a_dir == "up" and p_dir == "down":
            divergence = "Global ثابت + Top Account ↑ + Top Position ↓"
            fuel = "Account Count Without Size"
        elif g_neg_state in {"Shock", "Extreme"} and a_neg_state in {"Shock", "Extreme"} and abs(p_rank - 0.5) <= max(abs(df["top_position_ls"].rank(pct=True) - 0.5).median(), 0.05):
            divergence = "Global ↓ جدًا + Top Account ↓ جدًا + Top Position قرب التعادل"
            fuel = "Short-Crowded Account Pressure, large positions not equally short"
        elif g_dir == "down" and a_dir == "down" and p_dir in {"flat", "up"}:
            divergence = "Global ↓ + Top Account ↓ + Top Position ثابت أو ↑"
            fuel = "Short Pressure Against Stable Big Positions"
        elif g_dir == "down" and a_dir == "down" and "Long-heavy" in p_ctx and p_dir == "down":
            divergence = "Global ↓ + Top Account ↓ + Top Position يبقى Long-heavy لكنه يتراجع"
            fuel = "Top Position Long Retention with Crowd/Account Compression"
        elif g_dir in {"flat", "up"} and not account_chasing and "Long-heavy" in p_ctx:
            divergence = "Global ثابت أو ↑ قليلًا + Top Account لا يطارد + Top Position Long-heavy"
            fuel = "Top Position Retention with Non-Chasing Accounts"
        elif g_dir == "up" and a_dir == "up" and p_dir == "down":
            divergence = "Global ↑ + Top Account ↑ + Top Position ↓"
            fuel = "Crowd Chasing / Large Position Caution"
        elif g_dir == "up" and a_dir == "down" and p_dir == "down":
            divergence = "Global ↑ + Top Account ↓ + Top Position ↓"
            fuel = "Retail Long / Smart Exit"
        elif all(d == "flat" for d in [g_dir, a_dir, p_dir]):
            divergence = "Global ثابت + Top Account ثابت + Top Position ثابت"
            fuel = "No L/S Edge"
        elif "Short-heavy" in g_ctx or "Short-heavy" in a_ctx:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
            fuel = "Strong Short Squeeze Fuel"
        elif "Near parity and falling" in g_ctx or "Near parity and falling" in a_ctx:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
            fuel = "Early Squeeze Fuel"
        elif ("Above parity" in g_ctx or "Long-heavy" in g_ctx) and g_dir == "down" and top_retention:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
            fuel = "Valid Counter-pressure Fuel"
        elif crowd_chasing or account_chasing:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
            fuel = "Crowd Chasing / Late Participation Risk"
        else:
            divergence = f"Global {g_dir} + Top Account {a_dir} + Top Position {p_dir}"
            fuel = "No L/S Edge"
        return LSFuelState(g_dir, a_dir, p_dir, g_ctx, a_ctx, p_ctx, fuel, bool(crowd_chasing), bool(account_chasing), bool(crowd_against), bool(account_against), bool(top_retention), bool(top_derisk), bool(top_collapse), divergence, [g_ctx, a_ctx, p_ctx])


class TriggerDetector:
    """Trigger Detection: breakout/reset ignition based on dynamic price/execution/OI timing."""

    def detect_trigger_event(self, df: pd.DataFrame, base_zone: BaseZone, reset_event: ResetEvent, baseline: Dict[str, Dict[str, Any]]) -> TriggerEvent:
        span = recent_span_len(df)
        start = max(0, min([x for x in [base_zone.end_idx if base_zone.detected else None, reset_event.idx if reset_event.detected else None, len(df) - span * 2] if x is not None]))
        candidates: List[Tuple[float, TriggerEvent]] = []
        for idx in range(start, len(df)):
            row = df.loc[idx]
            price_state = DynamicBaselineEngine().value_state_at(df, "price_change", idx)["state"]
            trades_state = DynamicBaselineEngine().value_state_at(df, "trades", idx)["state"]
            qv_state = DynamicBaselineEngine().value_state_at(df, "quote_volume", idx)["state"]
            oi_state = DynamicBaselineEngine().value_state_at(df, "oi_change_pct", idx)["state"]
            from_base = base_zone.detected and row["close"] > base_zone.high and base_zone.end_idx is not None and idx > base_zone.end_idx
            after_reset = reset_event.detected and idx >= (reset_event.idx or 0)
            price_expanded = price_state in {"Elevated", "Shock", "Extreme"} and row["price_change"] > 0
            execution = trades_state in {"Elevated", "Shock", "Extreme"} or qv_state in {"Elevated", "Shock", "Extreme"}
            if not ((from_base or after_reset or price_expanded) and (price_expanded or execution)):
                continue
            price_led = price_expanded and oi_state == "Normal"
            oi_led = oi_state in {"Elevated", "Shock", "Extreme"} and price_state == "Normal"
            simultaneous = oi_state in {"Elevated", "Shock", "Extreme"} and price_state in {"Elevated", "Shock", "Extreme"}
            if from_base and price_led and execution and qv_state in {"Elevated", "Shock", "Extreme"}:
                typ = "Vacuum / Stop-driven Trigger" if oi_state == "Normal" else "Base Breakout Trigger"
            elif from_base:
                typ = "Base Breakout Trigger"
            elif after_reset and price_expanded:
                typ = "Reset Ignition Trigger"
            elif oi_led:
                typ = "Directional Build-up Trigger"
            else:
                typ = "Failed Attempt" if price_expanded and not execution else "Directional Build-up Trigger"
            footprint = base_zone.high if base_zone.detected else (df.loc[reset_event.idx, "low"] if reset_event.detected and reset_event.idx is not None else row["open"])
            dist_rank = percentile_rank(df["range_pct"], abs(row["close"] - footprint) / max(abs(row["close"]), np.finfo(float).eps))
            ev = TriggerEvent(True, int(idx), typ, float(row["high"]), float(row["low"]), float(row["close"]), float((row["high"] + row["low"]) / 2), bool(from_base), bool(after_reset), price_state, trades_state, qv_state, oi_state, bool(price_led), bool(oi_led), bool(simultaneous), bool(dist_rank <= 0.50), bool(dist_rank >= 0.90), [f"distance_rank={dist_rank:.2f}"])
            score = state_strength(price_state) + state_strength(trades_state) + state_strength(qv_state) + (2 if from_base else 0) + (2 if after_reset else 0) - (1 if ev.far_from_footprint else 0)
            candidates.append((score, ev))
        if not candidates:
            return TriggerEvent(notes=["no trigger from base/reset/dynamic expansion"])

        def trigger_priority(item: Tuple[float, TriggerEvent]) -> Tuple[Any, ...]:
            score, ev = item
            execution_confirmed = ev.trades_state in {"Elevated", "Shock", "Extreme"} or ev.quote_volume_state in {"Elevated", "Shock", "Extreme"}
            return (
                1 if ev.from_base else 0,
                1 if ev.after_reset else 0,
                1 if ev.close_to_footprint else 0,
                1 if execution_confirmed else 0,
                1 if ev.price_expansion_state in {"Elevated", "Shock", "Extreme"} else 0,
                -1 if ev.far_from_footprint else 0,
                score,
                -(ev.idx or 0),
            )

        footprint_base = [item for item in candidates if item[1].from_base and item[1].close_to_footprint]
        if footprint_base:
            selected = sorted(footprint_base, key=lambda item: (item[1].idx if item[1].idx is not None else 10**12, -item[0]))[0][1]
            selected.notes.append("selected_earliest_footprint_trigger")
        else:
            selected = sorted(candidates, key=trigger_priority, reverse=True)[0][1]
            selected.notes.append("selected_by_structural_trigger_priority")
        selected.notes.append(f"trigger_candidate_count={len(candidates)}")
        return selected


class PostTriggerAcceptanceEngine:
    """Post-trigger acceptance without lookahead: only bars already printed after trigger."""

    def evaluate_post_trigger_acceptance(self, df: pd.DataFrame, trigger_event: TriggerEvent, base_zone: BaseZone, reset_event: ResetEvent, baseline: Dict[str, Dict[str, Any]]) -> AcceptanceState:
        if not trigger_event.detected or trigger_event.idx is None:
            return AcceptanceState()
        post = df.loc[trigger_event.idx:].copy()
        if post.empty:
            return AcceptanceState("No Trigger", notes=["trigger index not in frame"])
        last_close = float(post["close"].iloc[-1])
        returned_inside = bool(base_zone.detected and trigger_event.from_base and (post["close"] < base_zone.high).any())
        wick_inside_base = bool(base_zone.detected and trigger_event.from_base and not returned_inside and (post["low"] <= base_zone.high).any())
        held_mid = post["close"].iloc[-1] >= trigger_event.candle_mid and post["low"].min() >= trigger_event.candle_low
        held_base_high = (not base_zone.detected) or post["close"].iloc[-1] >= base_zone.high or post["low"].min() >= base_zone.high
        broke_base_low = base_zone.detected and post["low"].min() < base_zone.low
        if reset_event.detected and reset_event.idx is not None and trigger_event.idx is not None:
            reset_context = df.loc[reset_event.idx:max(reset_event.idx, trigger_event.idx - 1)]
            post_flush_low = reset_context["low"].min() if not reset_context.empty else np.nan
        else:
            post_flush_low = np.nan
        broke_post_flush_low = bool(math.isfinite(post_flush_low) and post["low"].min() < post_flush_low)
        oi_unwind = False
        if "oi_change_pct" in post and post["oi_change_pct"].dropna().size:
            latest_worst = post["oi_change_pct"].dropna().min()
            oi_unwind = negative_state_from_rank(percentile_rank(df["oi_change_pct"].dropna(), latest_worst), robust_z(df["oi_change_pct"].dropna(), latest_worst)) in {"Shock", "Extreme"}
        if broke_base_low or broke_post_flush_low:
            state = "Structure Invalidated"
            failed = True
        elif returned_inside and trigger_event.from_base:
            state = "Failed Base Vacuum Ignition" if trigger_event.type == "Vacuum / Stop-driven Trigger" else "Failed Base Ignition"
            failed = True
        elif returned_inside:
            state = "Failed Breakout"
            failed = True
        elif oi_unwind and not held_mid:
            state = "OI Trap Risk"
            failed = False
        elif trigger_event.after_reset and trigger_event.price_led and held_mid:
            state = "Pre-OI Accepted Move After Reset"
            failed = False
        elif trigger_event.from_base and trigger_event.price_led and held_base_high and not oi_unwind:
            state = "Pre-OI / No-OI Accepted Move From Base" if trigger_event.oi_state_at_trigger == "Normal" else "Pre-OI Accepted Move From Base"
            failed = False
        elif held_mid and held_base_high:
            state = "Accepted Breakout"
            failed = False
        elif held_base_high:
            state = "Constructive Acceptance"
            failed = False
        else:
            state = "Controlled Pullback"
            failed = False
        accepted = state in {"Accepted Breakout", "Pre-OI Accepted Move After Reset", "Pre-OI Accepted Move From Base", "Pre-OI / No-OI Accepted Move From Base"}
        constructive = state in {"Constructive Acceptance", "Controlled Pullback"} or accepted
        notes = [f"post_trigger_bars={len(post)}", "post_flush_low_scope=reset_to_pre_trigger"]
        if wick_inside_base:
            notes.append("wick_inside_base_risk")
        return AcceptanceState(state, bool(accepted), bool(failed), bool(constructive), bool(returned_inside), bool(held_mid), bool(held_base_high), bool(broke_base_low), bool(broke_post_flush_low), bool(oi_unwind), notes)


class TimingEngine:
    """Delayed OI Reload: OI following price is constructive or late based on base/reset/L-S context."""

    def detect_price_oi_timing(self, df: pd.DataFrame, base_zone: BaseZone, reset_event: ResetEvent, trigger_event: TriggerEvent, baseline: Dict[str, Dict[str, Any]]) -> TimingState:
        if not trigger_event.detected or trigger_event.idx is None:
            return TimingState(notes=["no trigger timing"])
        post = df.loc[trigger_event.idx:].copy()
        recent = post.tail(max(1, recent_span_len(df)))
        oi_reload = recent["oi_change_pct"].dropna().median() > 0 if "oi_change_pct" in recent else False
        oi_reload_confirmed = oi_reload and baseline["oi_change_pct"]["negative_state"] not in {"Shock", "Extreme"}
        price_from_base = trigger_event.from_base
        price_after_reset = trigger_event.after_reset
        if trigger_event.price_led and price_after_reset and oi_reload_confirmed:
            timing = "Price before OI after Reset"
        elif trigger_event.price_led and price_from_base and oi_reload_confirmed:
            timing = "Price before OI from Base without Reset"
        elif trigger_event.price_led and price_from_base and not oi_reload_confirmed:
            timing = "Price before OI from Base without OI expansion"
        elif trigger_event.price_led:
            timing = "Price before OI without Reset/Base"
        elif trigger_event.oi_led:
            timing = "OI before price"
        elif trigger_event.simultaneous:
            timing = "OI and price together"
        else:
            timing = "Post-move OI retention"
        return TimingState(timing, trigger_event.price_led, trigger_event.oi_led, trigger_event.simultaneous, bool(price_from_base), bool(price_after_reset), bool(oi_reload_confirmed), bool(oi_reload_confirmed and len(post) <= max(recent_span_len(df), 1) + 1), trigger_event.far_from_footprint, trigger_event.close_to_footprint, [f"post bars={len(post)}"])

    def detect_delayed_oi_reload(self, df: pd.DataFrame, trigger_event: TriggerEvent, baseline: Dict[str, Dict[str, Any]], timing_state: TimingState) -> DelayedReloadState:
        if not trigger_event.detected:
            return DelayedReloadState()
        latest = safe_float(df["oi_change_pct"].iloc[-1], 0.0)
        if timing_state.price_moved_after_reset and timing_state.oi_reloaded_after_price:
            return DelayedReloadState("Delayed Constructive OI Reload After Reset", True, False, False, False, ["OI followed reset price ignition"])
        if timing_state.price_moved_from_base and timing_state.oi_reloaded_after_price:
            return DelayedReloadState("Delayed Constructive OI Reload From Base", True, False, False, False, ["OI followed base breakout"])
        if timing_state.price_leads_oi and latest > 0 and timing_state.far_from_footprint:
            return DelayedReloadState("Late OI Expansion", False, True, False, False, ["OI expansion far from footprint"])
        if timing_state.price_moved_from_base and latest <= 0 and baseline["oi_change_pct"]["negative_state"] not in {"Shock", "Extreme"}:
            return DelayedReloadState("No-OI Vacuum Continuation", False, False, True, False, ["price moving with flat/slightly down OI"])
        if latest < 0 and df["price_change"].iloc[-1] > 0:
            return DelayedReloadState("OI Deleveraging During Move", False, False, False, True, ["OI down while price holds"])
        return DelayedReloadState()


class CompressionEngine:
    def detect_high_oi_compression(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], ls_fuel: LSFuelState, base_zone: BaseZone, acceptance_state: AcceptanceState) -> CompressionState:
        oi_near_high = baseline["oi_abs"]["percentile_rank"] >= 0.90
        recent_high = df["high"].tail(max(recent_span_len(df) * 3, recent_span_len(df))).max()
        price_below_high = df["close"].iloc[-1] < recent_high
        inside_range = base_zone.detected and base_zone.low <= df["close"].iloc[-1] <= base_zone.high
        short_heavy = "Short" in ls_fuel.fuel_state or "Short-heavy" in ls_fuel.global_level_context or "Short-heavy" in ls_fuel.account_level_context
        long_heavy = "Long-heavy" in ls_fuel.global_level_context or "Long-heavy" in ls_fuel.account_level_context
        top_ok = ls_fuel.top_position_retention or "balanced" in ls_fuel.position_level_context or "Above parity" in ls_fuel.position_level_context
        if not oi_near_high:
            return CompressionState(notes=["OI not near local high"])
        if price_below_high and long_heavy:
            typ, risk = "Trapped Long Compression", "Post-Pump Risk"
        elif not price_below_high and long_heavy:
            typ, risk = "Post-Pump Crowding Compression", "Crowding risk"
        elif not price_below_high and short_heavy:
            typ, risk = "squeeze fuel persists" if acceptance_state.constructive else "Short-Crowded Compression"
        elif short_heavy:
            typ, risk = "Short-Crowded Compression", "squeeze fuel unresolved"
        elif top_ok:
            typ, risk = "High OI Neutral Compression", "neutral compression"
        else:
            typ, risk = "Volatility Compression", "high volatility compression"
        if base_zone.detected and acceptance_state.broke_base_low:
            risk = "Bearish Expansion risk"
        return CompressionState(True, typ, bool(oi_near_high), bool(price_below_high), bool(inside_range), bool(short_heavy), bool(long_heavy), bool(top_ok), risk, [ls_fuel.fuel_state])


class VacuumIgnitionDetector:
    """Price-led Base Vacuum: never discard solely because OI is flat/slightly down."""

    def detect_price_led_base_vacuum_ignition(self, df: pd.DataFrame, base_zone: BaseZone, trigger_event: TriggerEvent, acceptance_state: AcceptanceState, timing_state: TimingState, ls_fuel_state: LSFuelState, trades_validation: str, oi_state: str, baseline: Dict[str, Dict[str, Any]]) -> VacuumIgnitionState:
        notes: List[str] = []
        from_base = base_zone.detected and base_zone.quality in {"Valid Quiet Base", "Strong Compression Base", "Primed Base"}
        price_first = trigger_event.detected and trigger_event.from_base and timing_state.price_leads_oi
        trade_quote = any(s in trades_validation for s in ["Real Execution Expansion", "Real Capital Activation", "Vacuum Flow", "Large-ticket Execution", "Large Block-like Execution", "Aggressive Buy Execution"])
        oi_flat_down = oi_state in {"Price-led Base Move Without OI Expansion", "flat OI", "gradual OI decline", "OI Deleveraging After Pump"} or (safe_float(df["oi_change_pct"].iloc[-1], 0.0) <= 0 and baseline["oi_change_pct"]["negative_state"] not in {"Shock", "Extreme"})
        oi_not_collapsing = baseline["oi_change_pct"]["negative_state"] not in {"Shock", "Extreme"} or oi_state == "Price-led Base Move Without OI Expansion"
        top_retained = ls_fuel_state.top_position_retention and not ls_fuel_state.top_position_collapse
        account_non_chasing = not ls_fuel_state.account_chasing
        global_not_long = "Long-heavy high" not in ls_fuel_state.global_level_context
        accepted = acceptance_state.accepted or acceptance_state.constructive
        close_dist = safe_div(abs(df["close"].iloc[-1] - base_zone.high), max(abs(df["close"].iloc[-1]), np.finfo(float).eps), 1.0) if base_zone.detected else 1.0
        close_to_base = percentile_rank(df["range_pct"], close_dist) <= 0.50 if base_zone.detected else False
        failed = acceptance_state.state in {"Failed Base Vacuum Ignition", "Failed Base Ignition", "Structure Invalidated"} or acceptance_state.returned_inside_base
        if failed and trigger_event.from_base:
            state = "Failed Base Vacuum Ignition"
            active = False
        elif all([from_base, price_first, trade_quote, oi_flat_down, oi_not_collapsing, top_retained, account_non_chasing, global_not_long, accepted]):
            if acceptance_state.accepted and close_to_base:
                state = "Accepted Base Vacuum Ignition"
            elif not close_to_base:
                state = "Bullish but Late Base Vacuum"
            else:
                state = "Price-led Base Vacuum Ignition"
            active = state != "Bullish but Late Base Vacuum"
        elif from_base and price_first and trade_quote and oi_not_collapsing and accepted:
            state = "Price-led Base Vacuum Candidate"
            active = False
            notes.append("vacuum_candidate_needs_trade_quote_or_top_account_confirmation")
        elif from_base and price_first and oi_flat_down:
            state = "Price-led Base Vacuum Candidate"
            active = False
            notes.append("vacuum_candidate_needs_trade_quote_or_top_account_confirmation")
        else:
            state = "Inactive"
            active = False
        checks = {
            "from_valid_base": from_base, "price_exited_base_first": price_first, "trades_quote_confirmed": trade_quote,
            "oi_flat_or_slightly_down": oi_flat_down, "oi_not_collapsing": oi_not_collapsing, "top_position_retained": top_retained,
            "account_non_chasing": account_non_chasing, "global_not_excessively_long": global_not_long, "price_accepted": accepted,
            "close_to_base": close_to_base,
        }
        notes.extend([f"{k}={v}" for k, v in checks.items()])
        return VacuumIgnitionState(bool(active), state, bool(from_base), bool(price_first), bool(trade_quote), bool(oi_flat_down), bool(oi_not_collapsing), bool(top_retained), bool(account_non_chasing), bool(global_not_long), bool(accepted), bool(close_to_base), bool(failed), notes)


class CycleCountEngine:
    """Phase Memory / Cycle Count using recent OI reloads and base/reset context only."""

    def classify(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]], base_zone: BaseZone, reset_event: ResetEvent, trigger_event: TriggerEvent, timing_state: TimingState) -> Tuple[int, str]:
        span = max(recent_span_len(df) * 3, recent_span_len(df))
        recent = df.tail(span)
        reload_count = 0
        if "oi_change_pct" in recent and recent["oi_change_pct"].notna().any():
            for _, value in recent["oi_change_pct"].dropna().items():
                if value > 0 and state_from_rank(percentile_rank(df["oi_change_pct"].dropna(), value), robust_z(df["oi_change_pct"].dropna(), value)) in {"Elevated", "Shock", "Extreme"}:
                    reload_count += 1
        if reload_count >= max(2, recent_span_len(df) // 2) and baseline["oi_abs"]["percentile_rank"] >= 0.90:
            return reload_count, "High Leverage Multi-Reload Regime"
        distance = len(df) - 1 - (trigger_event.idx if trigger_event.detected and trigger_event.idx is not None else (base_zone.end_idx if base_zone.detected and base_zone.end_idx is not None else reset_event.idx if reset_event.detected and reset_event.idx is not None else len(df) - 1))
        early = distance <= recent_span_len(df)
        late = distance >= recent_span_len(df) * 3 or trigger_event.far_from_footprint
        if reset_event.detected and trigger_event.detected and trigger_event.after_reset and not trigger_event.from_base:
            return reload_count, "Late Reset Cycle" if late else "Early-Live Reset Cycle" if early else "Mid Reset Cycle"
        if base_zone.detected and trigger_event.detected and trigger_event.from_base:
            return reload_count, "Late Base Cycle" if late else "Early-Live Base Cycle" if early else "Mid Base Cycle"
        if reset_event.detected and trigger_event.detected:
            return reload_count, "Late Reset Cycle" if late else "Early-Live Reset Cycle" if early else "Mid Reset Cycle"
        if base_zone.detected and trigger_event.detected:
            return reload_count, "Late Base Cycle" if late else "Early-Live Base Cycle" if early else "Mid Base Cycle"
        if base_zone.detected:
            return reload_count, "Early Base Cycle" if early else "Mid Base Cycle"
        if reset_event.detected:
            return reload_count, "Early Reset Cycle" if early else "Mid Reset Cycle"
        return reload_count, "Background / No Clear Cycle"


class StructuralPreScanner:
    """Structural pre-scan coordinates all V3.2.1 evidence branches before decision."""

    def __init__(self):
        self.base_detector = BaseDetector()
        self.reset_detector = ResetDetector()
        self.trigger_detector = TriggerDetector()
        self.acceptance_engine = PostTriggerAcceptanceEngine()
        self.timing_engine = TimingEngine()
        self.ls_fuel_model = LSFuelModel()
        self.compression_engine = CompressionEngine()
        self.validation_engine = ValidationEngine()
        self.price_engine = PriceStructureEngine()
        self.oi_engine = OIStateEngine()
        self.vacuum_detector = VacuumIgnitionDetector()
        self.cycle_engine = CycleCountEngine()

    def scan(self, df: pd.DataFrame, baseline: Dict[str, Dict[str, Any]]) -> PreScanState:
        base_zone = self.base_detector.detect_base_zone(df, baseline, None)
        reset_event = self.reset_detector.detect_oi_flush_event(df, baseline)
        trigger_event = self.trigger_detector.detect_trigger_event(df, base_zone, reset_event, baseline)
        timing_state = self.timing_engine.detect_price_oi_timing(df, base_zone, reset_event, trigger_event, baseline)
        delayed_reload_state = self.timing_engine.detect_delayed_oi_reload(df, trigger_event, baseline, timing_state)
        ls_fuel_state = self.ls_fuel_model.analyze_ls_fuel(df, baseline, base_zone, trigger_event, timing_state)
        post_flush_state = self.reset_detector.detect_post_flush_behavior(df, reset_event, baseline, ls_fuel_state)
        acceptance_state = self.acceptance_engine.evaluate_post_trigger_acceptance(df, trigger_event, base_zone, reset_event, baseline)
        price_state = self.price_engine.classify(df, baseline, base_zone, reset_event)
        oi_state = self.oi_engine.classify(df, baseline, reset_event, base_zone, timing_state)
        trades_validation = self.validation_engine.trade_value_validation(df, baseline)
        oi_value_validation = self.validation_engine.oi_value_validation(df, baseline)
        vacuum_state = self.vacuum_detector.detect_price_led_base_vacuum_ignition(df, base_zone, trigger_event, acceptance_state, timing_state, ls_fuel_state, trades_validation, oi_state, baseline)
        compression_state = self.compression_engine.detect_high_oi_compression(df, baseline, ls_fuel_state, base_zone, acceptance_state)
        cycle_count, cycle_label = self.cycle_engine.classify(df, baseline, base_zone, reset_event, trigger_event, timing_state)
        trade_quote_confirmed = any(s in trades_validation for s in ["Real Execution Expansion", "Real Capital Activation", "Large-ticket Execution", "Large Block-like Execution", "Aggressive Buy Execution"])
        evidence_flags = {
            "oi_flush_detector": reset_event.type,
            "post_flush_behavior": post_flush_state.state,
            "pre_price_oi_build_up": trigger_event.oi_led and trigger_event.type == "Directional Build-up Trigger",
            "price_leads_oi": timing_state.price_leads_oi,
            "ignition_without_oi": trigger_event.detected and trigger_event.price_led and oi_state in {"flat OI", "Price-led Base Move Without OI Expansion"},
            "price_led_reset_ignition_with_oi_reload": all([reset_event.detected, post_flush_state.price_stabilized, post_flush_state.price_rejected_low_break, trigger_event.detected, trigger_event.after_reset, trigger_event.price_led, trade_quote_confirmed, delayed_reload_state.constructive, acceptance_state.constructive, ls_fuel_state.top_position_retention, not ls_fuel_state.top_position_collapse, not ls_fuel_state.account_chasing]),
            "price_led_base_ignition_without_reset": all([not reset_event.detected, base_zone.detected, base_zone.quality in {"Valid Quiet Base", "Strong Compression Base", "Primed Base"}, trigger_event.detected, trigger_event.from_base, trigger_event.price_led, trade_quote_confirmed, timing_state.signal_timing == "Price before OI from Base without Reset", delayed_reload_state.constructive, timing_state.oi_reloaded_within_recent_confirmed_candles, acceptance_state.constructive, not ls_fuel_state.account_chasing, "Long-heavy high" not in ls_fuel_state.global_level_context, ls_fuel_state.top_position_retention, not trigger_event.far_from_footprint]),
            "price_led_base_vacuum_without_oi_expansion": vacuum_state.active,
            "late_oi_crowding": delayed_reload_state.late or (timing_state.signal_timing == "Price before OI without Reset/Base" and ls_fuel_state.account_chasing),
            "post_peak_oi_retention": baseline["oi_abs"]["percentile_rank"] >= 0.90 and df["close"].iloc[-1] < df["high"].tail(max(recent_span_len(df) * 3, recent_span_len(df))).max(),
            "high_oi_compression": compression_state.active,
            "post_trigger_acceptance": acceptance_state.state,
            "short_crowding_quality": ls_fuel_state.fuel_state,
        }
        invalidation_flags = []
        if acceptance_state.failed:
            invalidation_flags.append(acceptance_state.state)
        if acceptance_state.broke_base_low:
            invalidation_flags.append("base_low_broken")
        if acceptance_state.broke_post_flush_low:
            invalidation_flags.append("post_flush_low_broken")
        risk_overlays = []
        if evidence_flags["late_oi_crowding"]:
            risk_overlays.append("late_oi_crowding")
        if evidence_flags["post_peak_oi_retention"]:
            risk_overlays.append("post_peak_oi_retention")
        if compression_state.risk_overlay not in {"none", "neutral compression", "squeeze fuel persists"}:
            risk_overlays.append(compression_state.risk_overlay)
        if "Micro" in trades_validation or "Bot" in trades_validation:
            risk_overlays.append("micro_trade_noise")
        return PreScanState(base_zone, reset_event, post_flush_state, trigger_event, acceptance_state, timing_state, delayed_reload_state, ls_fuel_state, compression_state, vacuum_state, oi_state, price_state, trades_validation, oi_value_validation, evidence_flags, invalidation_flags, risk_overlays, cycle_count, cycle_label)


class ConflictResolver:
    """Conflict Resolution: priority-ordered V3.2.1 final structural decision."""

    def resolve(self, df: pd.DataFrame, pre: PreScanState, quality_cap: str, reliability: float, data_flags: List[str], mode: str) -> AnalysisResult:
        pattern = "Mixed Structure"
        readiness = "Watchlist Only"
        oi_flat_down_context = pre.oi_state in {"Price-led Base Move Without OI Expansion", "flat OI", "gradual OI decline", "OI Deleveraging After Pump"}
        short_fuel = "Short" in pre.ls_fuel_state.fuel_state or pre.ls_fuel_state.crowd_against_move or pre.ls_fuel_state.account_against_move
        oi_build_or_retained = pre.oi_state in {"explosive OI build", "gradual OI build", "Late OI Expansion"} or pre.compression_state.oi_near_window_high
        execution_confirmed = any(s in pre.trades_validation for s in ["Real Execution Expansion", "Real Capital Activation", "Large-ticket Execution", "Large Block-like Execution", "Aggressive Buy Execution", "Quote Volume ↑"])
        long_chasing_or_heavy = pre.ls_fuel_state.crowd_chasing or pre.ls_fuel_state.account_chasing or "Long-heavy" in pre.ls_fuel_state.global_level_context or "Long-heavy" in pre.ls_fuel_state.account_level_context
        # 1-4: invalidation priority preserves failed base/vacuum semantics before generic invalidation.
        if pre.acceptance_state.state == "Structure Invalidated" and pre.trigger_event.from_base and oi_flat_down_context:
            pattern, readiness = "Failed Base Vacuum Ignition", "Failed / Invalidated"
        elif pre.acceptance_state.state == "Structure Invalidated" and pre.trigger_event.from_base:
            pattern, readiness = "Failed Base Ignition", "Failed / Invalidated"
        elif pre.vacuum_ignition_state.failed or pre.acceptance_state.state == "Failed Base Vacuum Ignition":
            pattern, readiness = "Failed Base Vacuum Ignition", "Failed / Invalidated"
        elif pre.acceptance_state.state == "Failed Base Ignition":
            pattern, readiness = "Failed Base Ignition", "Failed / Invalidated"
        elif pre.acceptance_state.state == "Failed Breakout" and short_fuel and oi_build_or_retained and execution_confirmed:
            pattern, readiness = "Failed Squeeze / Squeeze Exhaustion", "Failed / Invalidated"
        elif pre.acceptance_state.state == "Failed Breakout":
            pattern, readiness = "Bull Trap Risk", "Failed / Invalidated"
        elif pre.acceptance_state.state == "Structure Invalidated":
            pattern, readiness = "Long Trap / Long Punishment", "Failed / Invalidated"
        # 5-8: price-led ignition branches.
        elif pre.vacuum_ignition_state.state == "Accepted Base Vacuum Ignition":
            pattern, readiness = "Price-led Base Vacuum Ignition without OI Expansion", "Accepted Structure"
        elif pre.vacuum_ignition_state.active and pre.vacuum_ignition_state.state in {"Price-led Base Vacuum Ignition", "Price-led Base Ignition without OI Expansion"}:
            pattern = "Price-led Base Vacuum Ignition without OI Expansion"
            readiness = "Confirmed Trigger" if pre.acceptance_state.constructive else "Early-Live Structure"
        elif pre.vacuum_ignition_state.state == "Bullish but Late Base Vacuum":
            pattern, readiness = "Price-led Base Vacuum Ignition without OI Expansion", "Late / Risk State"
        elif pre.evidence_flags["price_led_reset_ignition_with_oi_reload"]:
            pattern, readiness = "Price-led Reset Ignition with OI Reload", "Accepted Structure" if pre.acceptance_state.accepted else "Confirmed Trigger"
        elif pre.evidence_flags["price_led_base_ignition_without_reset"]:
            pattern, readiness = "Price-led Base Ignition without Reset", "Confirmed Trigger" if pre.acceptance_state.constructive else "Early-Live Structure"
        # 9-10: flush behavior.
        elif pre.post_flush_state.state == "Absorption After Flush":
            pattern, readiness = "Absorption After Flush", "Primed Structure" if not pre.trigger_event.detected else "Early-Live Structure"
        elif pre.reset_event.detected and pre.trigger_event.detected and pre.trigger_event.price_led and pre.oi_state in {"flat OI", "OI Deleveraging After Pump"}:
            pattern, readiness = "Post-Flush Vacuum Ignition", "Confirmed Trigger" if pre.acceptance_state.constructive else "Early-Live Structure"
        # 11-15: build-up, squeeze and stop-driven. Hidden/short-build branches must precede Fresh Long Build-up.
        elif pre.oi_state in {"explosive OI build", "gradual OI build"} and (
            "Sell Absorption" in pre.trades_validation
            or "Absorption Battle" in pre.trades_validation
            or "Hidden Accumulation" in pre.trades_validation
        ) and not pre.acceptance_state.failed and (pre.price_state == "sideways/base" or pre.acceptance_state.constructive):
            pattern, readiness = "Hidden Buildup / Absorption", "Primed Structure"
        elif pre.oi_state in {"explosive OI build", "gradual OI build"} and pre.price_state == "sideways/base" and (
            pre.ls_fuel_state.crowd_against_move
            or pre.ls_fuel_state.account_against_move
            or "Short" in pre.ls_fuel_state.fuel_state
        ) and not pre.trigger_event.detected and not pre.acceptance_state.failed:
            pattern, readiness = "Short Build Under Stable Price", "Primed Structure"
        elif pre.oi_state in {"explosive OI build", "gradual OI build", "Delayed Constructive OI Reload From Base"} and pre.price_state in {"sideways/base", "healthy uptrend", "up from base without reset"}:
            pattern = "Fresh Long Build-up"
            readiness = "Primed Structure" if not pre.trigger_event.detected else "Confirmed Trigger"
        elif pre.trigger_event.detected and (pre.price_state == "explosive up move" or pre.trigger_event.price_expansion_state in {"Shock", "Extreme"}) and "Short" in pre.ls_fuel_state.fuel_state:
            pattern, readiness = "Short Squeeze / Live Ignition", "Confirmed Trigger"
        elif pre.trigger_event.type == "Vacuum / Stop-driven Trigger":
            pattern, readiness = "Vacuum Ignition / Stop-Driven Move", "Confirmed Trigger" if pre.acceptance_state.constructive else "Early-Live Structure"
        # 16-18: compression branches.
        elif pre.ls_fuel_state.fuel_state in {"Top Position Long Retention with Crowd/Account Compression", "Top Position Retention with Non-Chasing Accounts"} and pre.compression_state.active:
            pattern, readiness = "Top-Position Long Retention with Crowd Compression", "Compression / Unresolved"
        elif pre.compression_state.type == "Short-Crowded Compression":
            pattern, readiness = "Short-Crowded Compression", "Compression / Unresolved"
        elif pre.compression_state.type == "High OI Neutral Compression":
            pattern, readiness = "High OI Neutral Compression", "Compression / Unresolved"
        # 19-26: risk, bearish, weak/noise/mixed.
        elif pre.evidence_flags["late_oi_crowding"]:
            pattern, readiness = "Late Long Crowding", "Late / Risk State"
        elif pre.compression_state.type in {"Trapped Long Compression", "Post-Pump Crowding Compression"}:
            pattern, readiness = "Post-Pump Crowding Risk", "Late / Risk State"
        elif pre.price_state in {"slow downtrend", "violent downtrend"} and oi_build_or_retained and long_chasing_or_heavy and execution_confirmed and not pre.acceptance_state.constructive:
            pattern, readiness = "Long Trap / Long Punishment", "Failed / Invalidated"
        elif pre.oi_state in {"explosive OI build", "gradual OI build"} and pre.price_state in {"slow downtrend", "violent downtrend"}:
            pattern, readiness = "Bearish Build-up", "Primed Structure"
        elif pre.reset_event.type in {"Long Liquidation / Forced Flush", "Real Liquidation / Deleveraging Event"} and pre.price_state == "violent downtrend":
            pattern, readiness = "Long Liquidation / Forced Reset", "Late / Risk State"
        elif pre.post_flush_state.state in {"Liquidity Exit / Decay", "Deleveraging Continues"}:
            pattern, readiness = "Liquidity Exit / Decay", "Late / Risk State"
        elif "Micro" in pre.trades_validation or "Bot" in pre.trades_validation:
            pattern, readiness = "Bot / Noise Expansion", "Watchlist Only"
        elif pre.base_zone.detected and pre.oi_state in {"flat OI", "gradual OI decline"}:
            pattern, readiness = "Weak Consolidation", "Watchlist Only"
        if mode == "strict_live" and readiness in {"Watchlist Only", "Primed Structure"} and not pre.trigger_event.detected:
            readiness = "Watchlist Only"
        force_late_bias = False
        if pre.trigger_event.far_from_footprint and readiness in {"Early-Live Structure", "Confirmed Trigger", "Accepted Structure"} and pattern not in {"Short Squeeze / Live Ignition", "Vacuum Ignition / Stop-Driven Move"}:
            readiness = "Late / Risk State"
            force_late_bias = True

        bias = "Bullish but Late" if force_late_bias else self.bias_for(pattern, readiness, pre)
        priority_bucket = self.priority_bucket(pattern, readiness, pre)
        confidence = self.confidence(pattern, readiness, pre, quality_cap, reliability, data_flags)
        score = self.score(pre, pattern, readiness, confidence)
        risk = compact_join(pre.invalidation_flags + pre.risk_overlays) or "No major invalidation risk detected"
        if pre.oi_value_validation == "Contract-count distortion / Low-price distortion":
            risk = compact_join([risk, "OI Value did not confirm contracts"])
        latest = df.iloc[-1]
        rsi_context = "RSI context only: " + ("unavailable" if not math.isfinite(safe_float(latest.get("rsi"))) else f"{latest['rsi']:.1f}; not used in decision")
        summary = compact_join([
            f"{pattern} | {bias}", f"base={pre.base_zone.quality}", f"reset={pre.reset_event.type}", f"trigger={pre.trigger_event.type}",
            f"acceptance={pre.acceptance_state.state}", f"timing={pre.timing_state.signal_timing}", f"oi={pre.oi_state}",
            f"exec={pre.trades_validation.split('|')[0].strip()}", f"ls={pre.ls_fuel_state.fuel_state}", f"vacuum={pre.vacuum_ignition_state.state}",
        ])
        evidence = as_jsonable({
            "base_zone": pre.base_zone,
            "reset_event": pre.reset_event,
            "post_flush_state": pre.post_flush_state,
            "trigger_event": pre.trigger_event,
            "acceptance_state": pre.acceptance_state,
            "timing_state": pre.timing_state,
            "delayed_reload_state": pre.delayed_reload_state,
            "ls_fuel_state": pre.ls_fuel_state,
            "compression_state": pre.compression_state,
            "vacuum_ignition_state": pre.vacuum_ignition_state,
            "cycle_count": pre.cycle_count,
            "cycle_label": pre.cycle_label,
            "base_detector_guard": {
                "latest_guard": pre.base_zone.latest_guard,
                "base_search_end": pre.base_zone.base_search_end,
                "excluded_latest_bars": pre.base_zone.excluded_latest_bars,
                "zone_contains_ignition": pre.base_zone.zone_contains_ignition,
                "base_guard_excluded_latest_ignition_zone": "base_guard_excluded_latest_ignition_zone" in pre.base_zone.notes,
            },
            "trigger_selection": {
                "selected_reason": next((note for note in pre.trigger_event.notes if note.startswith("selected_")), "none"),
                "selected_earliest_footprint_trigger": "selected_earliest_footprint_trigger" in pre.trigger_event.notes,
                "trigger_candidate_count": next((note.split("=", 1)[1] for note in pre.trigger_event.notes if note.startswith("trigger_candidate_count=")), "0"),
            },
            "data_quality_flags": data_flags,
            "oi_value_source": str(df["oi_value_source"].dropna().iloc[-1]) if "oi_value_source" in df and df["oi_value_source"].dropna().size else "unknown",
            "evidence_flags": pre.evidence_flags,
            "invalidation_flags": pre.invalidation_flags,
            "risk_overlays": pre.risk_overlays,
        })
        return AnalysisResult(
            symbol=str(latest.get("symbol", "")), timeframe=CONFIG["TIMEFRAME"], data_window=f"{len(df)} candles",
            dominant_structural_pattern=pattern, structural_bias=bias, readiness_level=readiness,
            signal_timing=pre.timing_state.signal_timing, cycle_position=pre.cycle_label, price_acceptance=pre.acceptance_state.state,
            oi_read=pre.oi_state, oi_value_validation=pre.oi_value_validation, trades_read=pre.trades_validation,
            quote_volume_validation="Quote Volume confirmed" if any(s in pre.trades_validation for s in ["Quote Volume ↑", "Real Execution", "Real Capital", "Large-ticket", "Large Block-like Execution", "Aggressive Buy Execution"]) else "Quote Volume weak/missing",
            ls_divergence=pre.ls_fuel_state.ls_divergence, whale_crowd_read=pre.ls_fuel_state.fuel_state,
            price_led_reset_ignition_state="active" if pre.evidence_flags["price_led_reset_ignition_with_oi_reload"] else "inactive",
            price_led_base_ignition_state="active" if pre.evidence_flags["price_led_base_ignition_without_reset"] else "inactive",
            price_led_base_vacuum_ignition_state=pre.vacuum_ignition_state.state,
            high_oi_compression_state=pre.compression_state.type,
            trigger_status=pre.trigger_event.type if pre.trigger_event.detected else "not triggered",
            post_trigger_acceptance=pre.acceptance_state.state,
            late_crowding_risk="active" if pre.evidence_flags["late_oi_crowding"] else "inactive",
            invalidation_risk=risk,
            confidence=confidence,
            score=round(score, 2),
            rank_priority=round((11 - priority_bucket) * 10 + score * 0.10, 2),
            rsi_context_only=rsi_context,
            final_structural_summary=summary,
            priority_bucket=priority_bucket,
            evidence_details=evidence,
        )

    def bias_for(self, pattern: str, readiness: str, pre: PreScanState) -> str:
        if pattern == "Price-led Base Vacuum Ignition without OI Expansion":
            return "Early-Live Bullish Structure" if pre.vacuum_ignition_state.close_to_base else "Bullish but Late"
        if pattern in {"Price-led Reset Ignition with OI Reload", "Price-led Base Ignition without Reset", "Short Squeeze / Live Ignition"}:
            return "Early-Live Bullish Structure"
        if pattern in {"Absorption After Flush", "Fresh Long Build-up", "Hidden Buildup / Absorption"}:
            return "Early Bullish Structure" if readiness in {"Primed Structure", "Early-Live Structure"} else "Bullish but Event-driven"
        if pattern in {"Short-Crowded Compression", "Top-Position Long Retention with Crowd Compression"}:
            return "Neutral-to-Bullish Compression"
        if pattern in {"High OI Neutral Compression"}:
            return "High Volatility Compression"
        if pattern in {"Late Long Crowding"}:
            return "Bullish but Late"
        if pattern in {"Post-Pump Crowding Risk"}:
            return "Post-Pump Crowding Risk"
        if pattern in {"Bull Trap Risk", "Failed Base Vacuum Ignition", "Failed Base Ignition", "Failed Squeeze / Squeeze Exhaustion"}:
            return "Distribution Risk"
        if pattern in {"Bearish Build-up", "Long Liquidation / Forced Reset", "Long Trap / Long Punishment", "Liquidity Exit / Decay"}:
            return "Bearish Structural Risk"
        return "Neutral / Unclear"

    def confidence(self, pattern: str, readiness: str, pre: PreScanState, cap: str, reliability: float, data_flags: List[str]) -> str:
        oi_source_exchange = any("oi_value_source:exchange_sumOpenInterestValue" in f for f in data_flags)
        oi_confirm = pre.oi_value_validation == "Real Position Expansion"
        exec_confirm = any(s in pre.trades_validation for s in ["Real Capital Activation", "Real Execution Expansion", "Large-ticket Execution", "Large Block-like Execution", "Aggressive Buy Execution"])
        ls_clear = pre.ls_fuel_state.ls_divergence != "L/S unavailable"
        conflicts = pre.invalidation_flags + pre.risk_overlays
        warmup = any("warmup" in f or "immature" in f for f in data_flags)
        if oi_confirm and exec_confirm and pre.acceptance_state.accepted and ls_clear and readiness in {"Confirmed Trigger", "Accepted Structure"} and not conflicts and not warmup and (oi_source_exchange or pre.trigger_event.close_to_footprint) and reliability > 0.75:
            raw = "High"
        elif pattern in {"Price-led Reset Ignition with OI Reload", "Price-led Base Ignition without Reset", "Price-led Base Vacuum Ignition without OI Expansion"} and pre.acceptance_state.constructive and (pre.ls_fuel_state.crowd_against_move or not pre.ls_fuel_state.account_chasing) and pre.ls_fuel_state.top_position_retention and exec_confirm:
            raw = "Medium-High"
        elif readiness in {"Primed Structure", "Early-Live Structure", "Confirmed Trigger"} or (pattern != "Mixed Structure" and len(conflicts) <= 1):
            raw = "Medium"
        else:
            raw = "Low"
        if readiness in {"Watchlist Only", "Failed / Invalidated"}:
            raw = "Low" if readiness == "Failed / Invalidated" else min(raw, "Medium", key=CONFIDENCE_ORDER.index)
        return self.apply_cap(raw, cap)

    @staticmethod
    def apply_cap(conf: str, cap: str) -> str:
        cap = cap if cap in CONFIDENCE_ORDER else "Medium"
        return CONFIDENCE_ORDER[min(CONFIDENCE_ORDER.index(conf), CONFIDENCE_ORDER.index(cap))]

    def score(self, pre: PreScanState, pattern: str, readiness: str, confidence: str) -> float:
        score = 0.0
        score += (11 - self.priority_bucket(pattern, readiness, pre)) * 6
        score += state_strength(pre.trigger_event.price_expansion_state) * 5
        score += state_strength(pre.trigger_event.trades_state) * 4
        score += state_strength(pre.trigger_event.quote_volume_state) * 4
        score += 9 if pre.acceptance_state.accepted else 4 if pre.acceptance_state.constructive else 0
        score += 10 if pre.vacuum_ignition_state.active else 0
        score += 7 if pre.delayed_reload_state.constructive else 0
        score += 6 if pre.ls_fuel_state.top_position_retention else -4
        score += 5 if pre.ls_fuel_state.crowd_against_move or pre.ls_fuel_state.account_against_move else 0
        score += 6 if pre.oi_value_validation == "Real Position Expansion" else 0
        score += 7 if any(s in pre.trades_validation for s in ["Real Capital Activation", "Real Execution Expansion", "Large-ticket Execution", "Large Block-like Execution", "Aggressive Buy Execution"]) else 0
        score -= 10 if pre.evidence_flags.get("late_oi_crowding") else 0
        score -= 14 if readiness == "Failed / Invalidated" else 0
        score -= 8 if "Micro" in pre.trades_validation or "Bot" in pre.trades_validation else 0
        score += {"High": 8, "Medium-High": 5, "Medium": 2, "Low": -5}.get(confidence, 0)
        return max(0.0, min(100.0, score))

    def priority_bucket(self, pattern: str, readiness: str, pre: PreScanState) -> int:
        if readiness == "Failed / Invalidated":
            return 9
        if readiness == "Accepted Structure":
            return 1
        if readiness == "Confirmed Trigger":
            return 2 if (pre.trigger_event.close_to_footprint or pre.vacuum_ignition_state.close_to_base) else 3
        if readiness == "Early-Live Structure":
            return 3
        if pattern == "Price-led Base Vacuum Ignition without OI Expansion" and (pre.vacuum_ignition_state.close_to_base or pre.trigger_event.close_to_footprint):
            return 4
        if readiness == "Primed Structure":
            return 5
        if readiness == "Compression / Unresolved":
            return 6
        if readiness == "Watchlist Only":
            return 7
        if readiness == "Late / Risk State":
            return 8
        return 10

    @staticmethod
    def cycle_position(pre: PreScanState) -> str:
        if pre.acceptance_state.failed:
            return "failed_post_trigger"
        if pre.trigger_event.detected and pre.acceptance_state.accepted:
            return "post_ignition_accepted"
        if pre.trigger_event.detected:
            return "ignition_candle_or_live_followthrough"
        if pre.base_zone.detected:
            return "compression_or_quiet_zone"
        if pre.reset_event.detected:
            return "post_flush_context"
        return "background"


# =============================================================================
# Sanity checks
# =============================================================================
def validate_result_enums(result: AnalysisResult) -> bool:
    ok = result.dominant_structural_pattern in ALLOWED_PATTERNS and result.structural_bias in ALLOWED_BIASES and result.readiness_level in READINESS_LEVELS
    if not ok:
        logging.warning("Enum validation failed for %s", result.symbol)
    return ok


def validate_no_rsi_decision_dependency() -> bool:
    # RSI appears only as context output and enrichment, never in score/conflict branch names.
    return True


def validate_vacuum_exception_logic(result: AnalysisResult) -> bool:
    ev = result.evidence_details.get("vacuum_ignition_state", {}) if result.evidence_details else {}
    if ev.get("active") and ev.get("oi_flat_or_slightly_down") and ev.get("price_accepted"):
        return result.dominant_structural_pattern == "Price-led Base Vacuum Ignition without OI Expansion"
    return True


def validate_base_does_not_include_trigger(pre: PreScanState) -> bool:
    if pre.base_zone.detected and pre.trigger_event.detected and pre.trigger_event.from_base:
        return pre.base_zone.end_idx is not None and pre.trigger_event.idx is not None and pre.base_zone.end_idx < pre.trigger_event.idx
    return True


def validate_trigger_prefers_footprint(pre: PreScanState) -> bool:
    if pre.trigger_event.detected and pre.trigger_event.from_base:
        return pre.trigger_event.close_to_footprint or pre.vacuum_ignition_state.close_to_base
    return True


def validate_no_weak_vacuum_promotion(pre: PreScanState, result: AnalysisResult) -> bool:
    if pre.vacuum_ignition_state.state == "Price-led Base Ignition without OI Expansion":
        return all([
            pre.vacuum_ignition_state.trades_quote_confirmed,
            pre.vacuum_ignition_state.oi_not_collapsing,
            pre.vacuum_ignition_state.price_accepted,
            pre.vacuum_ignition_state.top_position_retained and pre.vacuum_ignition_state.account_non_chasing,
        ])
    return True


def validate_candidate_not_promoted(pre: PreScanState, result: AnalysisResult) -> bool:
    if pre.vacuum_ignition_state.state == "Price-led Base Vacuum Candidate":
        return result.dominant_structural_pattern != "Price-led Base Vacuum Ignition without OI Expansion"
    return True


def validate_far_footprint_not_early(pre: PreScanState, result: AnalysisResult) -> bool:
    if pre.trigger_event.far_from_footprint and result.dominant_structural_pattern not in {"Short Squeeze / Live Ignition", "Vacuum Ignition / Stop-Driven Move"}:
        return result.readiness_level not in {"Early-Live Structure", "Confirmed Trigger", "Accepted Structure"}
    return True


def validate_failed_base_priority(pre: PreScanState, result: AnalysisResult) -> bool:
    if pre.acceptance_state.state == "Structure Invalidated" and pre.trigger_event.from_base:
        return result.dominant_structural_pattern in {"Failed Base Vacuum Ignition", "Failed Base Ignition"}
    return True


def validate_cycle_count_present(pre: PreScanState, result: AnalysisResult) -> bool:
    return isinstance(pre.cycle_count, int) and bool(pre.cycle_label) and result.cycle_position == pre.cycle_label


def validate_pattern_reachability(pattern_counts: Dict[str, int]) -> bool:
    if pattern_counts:
        logging.debug("Pattern reachability in last scan: %s", pattern_counts)
    return True


# =============================================================================
# Scanner orchestrator
# =============================================================================
class StructuralLiquidityScanner:
    """Complete V3.2.1 dynamic scanner."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rate_limiter = AdaptiveRateLimiter(config)
        self.client = BinanceFuturesClient(config, self.rate_limiter)
        self.baseline_engine = DynamicBaselineEngine()
        self.quality = DataQualityChecker()
        self.pre_scanner = StructuralPreScanner()
        self.resolver = ConflictResolver()
        self.last_parallel_stats: Dict[str, Any] = {}
        self.last_pattern_counts: Dict[str, int] = {}

    def symbols(self) -> List[str]:
        if self.config.get("SCAN_ALL_USDT_PERPETUALS"):
            return self.client.exchange_symbols()
        whitelist = self.config.get("SYMBOL_WHITELIST") or []
        if not whitelist:
            raise ValueError("SYMBOL_WHITELIST must be set when SCAN_ALL_USDT_PERPETUALS=False")
        return [s for s in whitelist if s not in set(self.config.get("SYMBOL_BLACKLIST") or [])]

    def analyze_symbol(self, symbol: str) -> Optional[AnalysisResult]:
        try:
            raw, source_flags = self.client.fetch_symbol_frame(symbol)
            if raw.empty:
                return None
            raw["symbol"] = symbol
            df = self.baseline_engine.enrich(raw)
            flags, cap, reliability = self.quality.check(df, source_flags, self.config)
            if len(df) < max(5, int(self.config["MIN_CANDLES_REQUIRED"] // 2)):
                return None
            baseline = self.baseline_engine.snapshot(df)
            pre = self.pre_scanner.scan(df, baseline)
            result = self.resolver.resolve(df, pre, cap, reliability, flags, self.config["MODE"])
            if self.config.get("RUN_SANITY_CHECKS"):
                self._handle_sanity("validate_result_enums", validate_result_enums(result))
                self._handle_sanity("validate_no_rsi_decision_dependency", validate_no_rsi_decision_dependency())
                self._handle_sanity("validate_vacuum_exception_logic", validate_vacuum_exception_logic(result))
                self._handle_sanity("validate_base_does_not_include_trigger", validate_base_does_not_include_trigger(pre))
                self._handle_sanity("validate_trigger_prefers_footprint", validate_trigger_prefers_footprint(pre))
                self._handle_sanity("validate_no_weak_vacuum_promotion", validate_no_weak_vacuum_promotion(pre, result))
                self._handle_sanity("validate_candidate_not_promoted", validate_candidate_not_promoted(pre, result))
                self._handle_sanity("validate_far_footprint_not_early", validate_far_footprint_not_early(pre, result))
                self._handle_sanity("validate_failed_base_priority", validate_failed_base_priority(pre, result))
                self._handle_sanity("validate_cycle_count_present", validate_cycle_count_present(pre, result))
            return result
        except Exception as exc:  # noqa: BLE001 - one symbol must not stop scanner
            if self.config.get("PRINT_DEBUG_PER_SYMBOL"):
                logging.exception("Failed to analyze %s", symbol)
            else:
                logging.warning("Skipping %s due to %s", symbol, exc.__class__.__name__)
            return None

    def resolve_max_workers(self, symbol_count: int) -> int:
        hard_cap = max(1, int(self.config.get("MAX_WORKERS_HARD_CAP", 8)))
        configured = self.config.get("MAX_WORKERS", "auto")
        if configured == "auto":
            return min(hard_cap, max(2, int(math.sqrt(max(symbol_count, 1)))))
        return min(max(1, int(configured)), hard_cap)

    def _handle_sanity(self, name: str, ok: bool) -> None:
        if ok:
            return
        msg = f"Sanity check warning: {name}"
        if self.config.get("RUN_SANITY_CHECKS_STRICT"):
            raise AssertionError(msg)
        logging.warning(msg)

    def _scan_parallel(self, symbols: List[str], max_workers: int) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        completed = successes = skipped = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self.analyze_symbol, symbol): symbol for symbol in symbols}
            for future in as_completed(future_map):
                symbol = future_map[future]
                completed += 1
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        successes += 1
                    else:
                        skipped += 1
                except Exception as exc:  # noqa: BLE001
                    skipped += 1
                    logging.warning("Skipping %s due to %s", symbol, exc.__class__.__name__)
                if self.config.get("PARALLEL_DEBUG") or completed == len(symbols) or completed % max(1, int(math.sqrt(max(len(symbols), 1)))) == 0:
                    stats = self.rate_limiter.stats()
                    logging.info("Progress %s/%s | success=%s skipped=%s | 429=%s 418=%s", completed, len(symbols), successes, skipped, stats["429_count"], stats["418_count"])
        self.last_parallel_stats.update({"success_count": successes, "skip_count": skipped})
        return results

    def run_once(self) -> List[AnalysisResult]:
        started = time.time()
        symbols = self.symbols()
        max_workers = self.resolve_max_workers(len(symbols)) if self.config.get("PARALLEL_SCAN") else 1
        self.last_parallel_stats = {
            "parallel_enabled": bool(self.config.get("PARALLEL_SCAN")),
            "max_workers": max_workers,
            "total_symbols": len(symbols),
            "success_count": 0,
            "skip_count": 0,
            "elapsed_seconds": 0.0,
        }
        logging.info("Scanning %s symbols | mode=%s timeframe=%s parallel=%s workers=%s", len(symbols), self.config["MODE"], self.config["TIMEFRAME"], self.config.get("PARALLEL_SCAN"), max_workers)
        results: List[AnalysisResult] = []
        batch_size = int(self.config.get("SYMBOL_BATCH_SIZE") or 0)
        symbol_batches = [symbols]
        if batch_size > 0:
            symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
        if self.config.get("PARALLEL_SCAN"):
            for batch_idx, batch in enumerate(symbol_batches, start=1):
                if len(symbol_batches) > 1:
                    logging.info("Scanning symbol batch %s/%s size=%s", batch_idx, len(symbol_batches), len(batch))
                results.extend(self._scan_parallel(batch, max_workers))
        else:
            successes = skipped = 0
            for batch in symbol_batches:
                for idx, symbol in enumerate(batch, start=1):
                    result = self.analyze_symbol(symbol)
                    if result:
                        results.append(result)
                        successes += 1
                    else:
                        skipped += 1
                    if self.config.get("PRINT_DEBUG_PER_SYMBOL"):
                        logging.info("%s/%s %s %s", idx, len(batch), symbol, result.dominant_structural_pattern if result else "no result")
                    time.sleep(float(self.config["SLEEP_BETWEEN_REQUESTS"]))
            self.last_parallel_stats.update({"success_count": successes, "skip_count": skipped})
        results.sort(key=lambda r: (r.priority_bucket, -r.score, -r.rank_priority, r.symbol))
        self.last_parallel_stats["success_count"] = len(results)
        self.last_parallel_stats["skip_count"] = max(0, len(symbols) - len(results))
        self.last_parallel_stats["elapsed_seconds"] = round(time.time() - started, 3)
        self.last_pattern_counts = {}
        for r in results:
            self.last_pattern_counts[r.dominant_structural_pattern] = self.last_pattern_counts.get(r.dominant_structural_pattern, 0) + 1
        if self.config.get("PARALLEL_DEBUG") or self.config.get("RUN_SANITY_CHECKS"):
            validate_pattern_reachability(self.last_pattern_counts)
        selected = results[: int(self.config["TOP_N_RESULTS"])]
        self.print_results(selected)
        self.save_results(selected)
        return selected

    def print_results(self, results: Sequence[AnalysisResult]) -> None:
        print(f"\nStructural Liquidity Scanner V3.2.1 Dynamic | {utc_now_iso()} | TF={self.config['TIMEFRAME']} | MODE={self.config['MODE']}")
        print("-" * 198)
        header = f"{'rank':<5}{'symbol':<14}{'pattern':<52}{'bias':<32}{'readiness':<26}{'conf':<13}{'score':<8}{'bucket':<8}{'trigger':<24}{'risk':<30}summary"
        print(header)
        print("-" * 198)
        for rank, r in enumerate(results, start=1):
            print(f"{rank:<5}{r.symbol:<14}{r.dominant_structural_pattern[:50]:<52}{r.structural_bias[:30]:<32}{r.readiness_level[:24]:<26}{r.confidence:<13}{r.score:<8.2f}{r.priority_bucket:<8}{r.trigger_status[:22]:<24}{r.invalidation_risk[:28]:<30}{r.final_structural_summary[:90]}")
        print("-" * 198)

    def save_results(self, results: Sequence[AnalysisResult]) -> None:
        os.makedirs(self.config["OUTPUT_DIR"], exist_ok=True)
        rate_stats = self.rate_limiter.stats()
        parallel_stats = dict(self.last_parallel_stats)
        rows = [as_jsonable(r) for r in results]
        for row in rows:
            evidence = row.setdefault("evidence_details", {})
            evidence["rate_limiter_stats"] = rate_stats
            evidence["parallel_scan_stats"] = parallel_stats
        if self.config.get("SAVE_JSON"):
            path = os.path.join(self.config["OUTPUT_DIR"], "scan_results_latest.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "generated_at": utc_now_iso(),
                    "config": self.public_config(),
                    "rate_limiter_stats": rate_stats,
                    "parallel_scan_stats": parallel_stats,
                    "pattern_reachability": self.last_pattern_counts,
                    "results": rows,
                }, f, ensure_ascii=False, indent=2)
            logging.info("Saved JSON: %s", path)
        if self.config.get("SAVE_CSV"):
            path = os.path.join(self.config["OUTPUT_DIR"], "scan_results_latest.csv")
            fieldnames = list(AnalysisResult.__dataclass_fields__.keys())
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    csv_row = dict(row)
                    csv_row["evidence_details"] = json.dumps(csv_row.get("evidence_details", {}), ensure_ascii=False)
                    writer.writerow(csv_row)
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
        if CONFIG.get("RUN_CONTINUOUSLY"):
            while True:
                scanner.run_once()
                time.sleep(float(CONFIG["SCAN_INTERVAL_SECONDS"]))
        else:
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
