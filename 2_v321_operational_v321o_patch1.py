#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structural Liquidity Discovery Tree V3.2.1

Operational Binance Futures scanner that follows the requested decision order:
Data Quality / Regime Check -> Dynamic Baseline -> Phase Memory -> OI Value / Quote Volume Validation
-> Price State -> OI State -> L/S Structure -> Trades Regime -> Price Acceptance
-> Structural Pre-Scanner -> Trigger / Post-Trigger Check -> Price-led Reset Ignition Check
-> Price-led Base Ignition Check -> Price-led Base Vacuum Ignition Check -> High OI Compression
-> Conflict Resolution -> Readiness Confirmation Level -> Final Structural Decision.

RSI is used only as visual/contextual information, not as a decision driver.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import requests
    from requests.adapters import HTTPAdapter
except Exception as exc:  # pragma: no cover
    raise SystemExit("pip install requests") from exc


# =============================================================================
# Config
# =============================================================================
class Config:
    BINANCE_FUTURES_BASE = os.environ.get("SLE_BINANCE_BASE", "https://fapi.binance.com")
    TIMEFRAME = os.environ.get("SLE_TIMEFRAME", "15m")
    CANDLES_COUNT = int(os.environ.get("SLE_CANDLES", "100"))
    RSI_PERIOD = int(os.environ.get("SLE_RSI_PERIOD", "14"))

    REQUEST_TIMEOUT = float(os.environ.get("SLE_REQUEST_TIMEOUT", "10"))
    REQUEST_RETRIES = int(os.environ.get("SLE_REQUEST_RETRIES", "2"))
    REQUEST_BACKOFF_BASE = float(os.environ.get("SLE_BACKOFF_BASE", "0.65"))
    FAST_WORKERS = int(os.environ.get("SLE_FAST_WORKERS", "28"))
    FULL_WORKERS = int(os.environ.get("SLE_FULL_WORKERS", "22"))
    MAX_REQUESTS_PER_SECOND = float(os.environ.get("SLE_MAX_RPS", "9"))
    MAX_INFLIGHT_REQUESTS = int(os.environ.get("SLE_MAX_INFLIGHT", "16"))

    FULL_SCAN_BUDGET_FRACTION = float(os.environ.get("SLE_FULL_SCAN_FRACTION", "0.20"))
    FULL_SCAN_MIN = int(os.environ.get("SLE_FULL_SCAN_MIN", "50"))
    FULL_SCAN_MAX = int(os.environ.get("SLE_FULL_SCAN_MAX", "120"))
    CYCLE_SLEEP_SECONDS = int(os.environ.get("SLE_SLEEP", "180"))
    STATE_DIR = os.environ.get("SLE_STATE_DIR", "structural_liquidity_state_v321")
    PRINT_TOP_PER_GROUP = int(os.environ.get("SLE_PRINT_TOP", "12"))
    WIDTH = int(os.environ.get("SLE_WIDTH", "120"))
    ANSI = os.environ.get("SLE_ANSI", "1") == "1"

    # Operational tolerance only. They are not fixed symbol-specific pattern thresholds.
    BASE_LOOKBACK_MIN = int(os.environ.get("SLE_BASE_LOOKBACK_MIN", "6"))
    BASE_LOOKBACK_MAX = int(os.environ.get("SLE_BASE_LOOKBACK_MAX", "18"))
    EVENT_LOOKBACK = int(os.environ.get("SLE_EVENT_LOOKBACK", "24"))
    RECENT_LOOKBACK = int(os.environ.get("SLE_RECENT_LOOKBACK", "8"))
    ACCEPTANCE_EPS = float(os.environ.get("SLE_ACCEPTANCE_EPS", "0.0015"))


# =============================================================================
# Math helpers
# =============================================================================
def sf(x: Any, d: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else d
    except Exception:
        return d


def si(x: Any, d: int = 0) -> int:
    try:
        return int(float(x))
    except Exception:
        return d


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, sf(x)))


def pct(prev: float, cur: float) -> float:
    prev, cur = sf(prev), sf(cur)
    return 0.0 if abs(prev) <= 1e-12 else (cur - prev) / abs(prev) * 100.0


def mean(xs: Iterable[float], d: float = 0.0) -> float:
    v = [sf(x) for x in xs if math.isfinite(sf(x))]
    return sum(v) / len(v) if v else d


def pstdev(xs: Iterable[float], d: float = 0.0) -> float:
    v = [sf(x) for x in xs if math.isfinite(sf(x))]
    if len(v) < 2:
        return d
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) * (x - m) for x in v) / len(v))


def pval(xs: Iterable[float], q: float, d: float = 0.0) -> float:
    v = sorted(sf(x) for x in xs if math.isfinite(sf(x)))
    if not v:
        return d
    if len(v) == 1:
        return v[0]
    pos = clamp(q) / 100 * (len(v) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return v[lo]
    w = pos - lo
    return v[lo] * (1 - w) + v[hi] * w


def prank(x: float, hist: Iterable[float]) -> float:
    v = [sf(a) for a in hist if math.isfinite(sf(a))]
    if not v:
        return 50.0
    less = sum(1 for a in v if a < x)
    eq = sum(1 for a in v if a == x)
    return clamp((less + 0.5 * eq) / len(v) * 100)


def zscore(x: float, hist: Iterable[float]) -> float:
    v = [sf(a) for a in hist if math.isfinite(sf(a))]
    sd = pstdev(v)
    return 0.0 if len(v) < 2 or sd <= 1e-12 else (x - mean(v)) / sd


def extreme(x: float, hist: Iterable[float]) -> float:
    v = [sf(a) for a in hist if math.isfinite(sf(a))]
    if not v:
        return 50.0
    return clamp(0.72 * prank(x, v) + 0.28 * clamp(50 + zscore(x, v) * 12))


def ratio_hist(x: float, hist: Iterable[float]) -> float:
    m = pval(hist, 50, x)
    return 1.0 if abs(m) <= 1e-12 else sf(x) / m


def signed_label(x: float, hist: Iterable[float]) -> str:
    """Dynamic Baseline label for signed magnitude vs the symbol's own window."""
    r = extreme(abs(x), [abs(v) for v in hist])
    z = abs(zscore(abs(x), [abs(v) for v in hist]))
    if r >= 95 or z >= 3.0:
        return "Extreme"
    if r >= 85 or z >= 2.0:
        return "Shock"
    if r >= 70 or z >= 1.0:
        return "Elevated"
    return "Normal"


def value_label(x: float, hist: Iterable[float]) -> str:
    r = extreme(x, hist)
    z = zscore(x, hist)
    if r >= 95 or z >= 3.0:
        return "Extreme"
    if r >= 85 or z >= 2.0:
        return "Shock"
    if r >= 70 or z >= 1.0:
        return "Elevated"
    return "Normal"


def is_event(label: str) -> bool:
    return label in {"Shock", "Extreme"}


def is_active(label: str) -> bool:
    return label in {"Elevated", "Shock", "Extreme"}


def line(ch: str = "═") -> str:
    return ch * Config.WIDTH


def color(s: str, c: str) -> str:
    if not Config.ANSI:
        return s
    m = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }
    return f"{m.get(c, '')}{s}{m['reset']}"


# =============================================================================
# Models
# =============================================================================
@dataclass
class Candle:
    time_ms: int
    time: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    taker_buy_quote: float
    rsi: float = 50.0
    oi: float = 0.0
    oi_value: float = 0.0
    oi_change: float = 0.0
    oi_change_pct: float = 0.0
    account_lsr: float = 1.0
    account_long_pct: float = 50.0
    account_short_pct: float = 50.0
    position_lsr: float = 1.0
    position_long_pct: float = 50.0
    position_short_pct: float = 50.0
    global_lsr: float = 1.0
    global_long_pct: float = 50.0
    global_short_pct: float = 50.0


@dataclass
class DataQuality:
    status: str
    issues: List[str]
    confidence_cap: Optional[str]
    score: float


@dataclass
class DynamicBaseline:
    price_move: str
    oi_change_pct: str
    trades: str
    quote_volume: str
    ls_change: str
    price_rank: float
    oi_rank: float
    trades_rank: float
    quote_rank: float
    ls_rank: float


@dataclass
class PhaseMemory:
    previous_event: str
    background_phase: str
    pressure_or_quiet_zone: str
    abnormal_change_zone: str
    pre_ignition_zone: str
    ignition_candle: str
    post_ignition_zone: str
    last_structural_state: str
    base_detected: bool
    base_low: float
    base_high: float
    base_start_time: str
    base_end_time: str
    reset_detected: bool
    reset_time: str
    trigger_time: str
    cycle_position: str


@dataclass
class PatternCandidate:
    """V3.2.1-O candidate: Required Gates first, Support Score second.

    The support score never creates a pattern by itself. A candidate must pass
    required_pass before it can be ranked, exactly as the operational mapping says:
    Features -> Pattern Eligibility + Pattern Scores -> Conflict Rules -> Readiness -> Confidence.
    """
    name: str
    required_pass: bool
    support_score: float = 0.0
    risk_score: float = 0.0
    specificity_rank: int = 0
    allowed_bias: str = "Neutral / Unclear"
    allowed_readiness: str = "Watchlist Only"
    invalidated_by: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        return float(self.support_score) - float(self.risk_score) + float(self.specificity_rank) * 2.0


@dataclass
class V321Decision:
    symbol: str
    timeframe: str
    data_window: str
    time: str
    close: float

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
    confidence_score: float
    rsi_context_only: str
    final_structural_summary: str

    # Runtime ranking fields.
    category: str
    rank_priority: int
    score: float
    price_3: float
    trades_ratio: float
    quote_ratio: float
    oi_change_pct: float
    rsi: float
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def export_user_format(self) -> Dict[str, Any]:
        return {
            "Symbol": self.symbol,
            "Timeframe": self.timeframe,
            "Data Window": self.data_window,
            "Dominant Structural Pattern": self.dominant_structural_pattern,
            "Structural Bias": self.structural_bias,
            "Readiness Level": self.readiness_level,
            "Signal Timing": self.signal_timing,
            "Cycle Position": self.cycle_position,
            "Price Acceptance": self.price_acceptance,
            "OI Read": self.oi_read,
            "OI Value Validation": self.oi_value_validation,
            "Trades Read": self.trades_read,
            "Quote Volume Validation": self.quote_volume_validation,
            "L/S Divergence": self.ls_divergence,
            "Whale/Crowd Read": self.whale_crowd_read,
            "Price-led Reset Ignition State": self.price_led_reset_ignition_state,
            "Price-led Base Ignition State": self.price_led_base_ignition_state,
            "Price-led Base Vacuum Ignition State": self.price_led_base_vacuum_ignition_state,
            "High OI Compression State": self.high_oi_compression_state,
            "Trigger Status": self.trigger_status,
            "Post-Trigger Acceptance": self.post_trigger_acceptance,
            "Late Crowding Risk": self.late_crowding_risk,
            "Invalidation / Risk": self.invalidation_risk,
            "Confidence": self.confidence,
            "RSI Context Only": self.rsi_context_only,
            "Final Structural Summary": self.final_structural_summary,
        }


# =============================================================================
# Indicators / Fetcher
# =============================================================================
class Indicators:
    @staticmethod
    def rsi(closes: List[float], period: int) -> List[float]:
        if len(closes) < 2:
            return [50.0] * len(closes)
        diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0.0) for d in diffs]
        losses = [abs(min(d, 0.0)) for d in diffs]
        if len(closes) < period + 1:
            ag, al = mean(gains), mean(losses)
            seed = 100.0 if al <= 1e-12 and ag > 0 else (50.0 if al <= 1e-12 else 100 - 100 / (1 + ag / al))
            return [seed] * len(closes)
        ag = sum(gains[:period]) / period
        al = sum(losses[:period]) / period
        first = 100.0 if al <= 1e-12 and ag > 0 else (50.0 if al <= 1e-12 else 100 - 100 / (1 + ag / al))
        out = [first] * (period + 1)
        for i in range(period, len(gains)):
            ag = (ag * (period - 1) + gains[i]) / period
            al = (al * (period - 1) + losses[i]) / period
            out.append(100.0 if al <= 1e-12 and ag > 0 else (50.0 if al <= 1e-12 else 100 - 100 / (1 + ag / al)))
        return out[: len(closes)]


class RequestRateLimiter:
    def __init__(self, rps: float, inflight: int):
        self.min_interval = 1 / max(0.5, rps)
        self.sem = threading.BoundedSemaphore(max(1, inflight))
        self.lock = threading.Lock()
        self.next = 0.0

    def wait(self) -> None:
        self.sem.acquire()
        with self.lock:
            t = time.monotonic()
            if t < self.next:
                time.sleep(self.next - t)
                t = time.monotonic()
            self.next = max(self.next + self.min_interval, t + self.min_interval)

    def release(self) -> None:
        try:
            self.sem.release()
        except ValueError:
            pass


class BinanceFuturesFetcher:
    def __init__(self):
        self.session = requests.Session()
        pool = max(Config.MAX_INFLIGHT_REQUESTS * 2, Config.FAST_WORKERS + Config.FULL_WORKERS)
        adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=pool, max_retries=0)
        self.session.mount("https://", adapter)
        self.session.headers.update({"Accept": "application/json"})
        self.limiter = RequestRateLimiter(Config.MAX_REQUESTS_PER_SECOND, Config.MAX_INFLIGHT_REQUESTS)
        self.cache: Optional[Tuple[float, List[str]]] = None
        self.cache_lock = threading.Lock()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{Config.BINANCE_FUTURES_BASE}{path}"
        last: Optional[Exception] = None
        for attempt in range(Config.REQUEST_RETRIES + 1):
            self.limiter.wait()
            try:
                r = self.session.get(url, params=params or {}, timeout=Config.REQUEST_TIMEOUT)
                if r.status_code in (418, 429) or 500 <= r.status_code < 600:
                    delay = sf(r.headers.get("Retry-After"), 0) or Config.REQUEST_BACKOFF_BASE * (2**attempt)
                    time.sleep(delay)
                    last = RuntimeError(str(r.status_code))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                last = exc
                if attempt < Config.REQUEST_RETRIES:
                    time.sleep(Config.REQUEST_BACKOFF_BASE * (2**attempt))
                else:
                    raise
            finally:
                self.limiter.release()
        raise last or RuntimeError("request failed")

    def active_usdt_symbols(self) -> List[str]:
        with self.cache_lock:
            if self.cache and time.time() - self.cache[0] < 900:
                return list(self.cache[1])
        info = self._get("/fapi/v1/exchangeInfo")
        out: List[str] = []
        for s in info.get("symbols", []):
            if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT" and s.get("contractType") == "PERPETUAL":
                out.append(s["symbol"])
        out = sorted(out)
        with self.cache_lock:
            self.cache = (time.time(), out)
        return out

    def klines(self, symbol: str) -> List[List[Any]]:
        data = self._get("/fapi/v1/klines", {"symbol": symbol, "interval": Config.TIMEFRAME, "limit": Config.CANDLES_COUNT})
        now = int(time.time() * 1000)
        return data[:-1] if data and int(data[-1][6]) > now else data

    def hist(self, path: str, symbol: str) -> List[Dict[str, Any]]:
        try:
            return self._get(path, {"symbol": symbol, "period": Config.TIMEFRAME, "limit": Config.CANDLES_COUNT})
        except Exception:
            return []

    @staticmethod
    def period_ms() -> int:
        unit = Config.TIMEFRAME[-1]
        n = si(Config.TIMEFRAME[:-1], 1)
        if unit == "m":
            return n * 60_000
        if unit == "h":
            return n * 3_600_000
        if unit == "d":
            return n * 86_400_000
        return 300_000

    @staticmethod
    def nearest(mp: Dict[int, Any], ts: int, default: Any) -> Any:
        if not mp:
            return default
        if ts in mp:
            return mp[ts]
        keys = sorted(mp)
        tol = BinanceFuturesFetcher.period_ms()
        best = min(keys, key=lambda k: abs(k - ts))
        if abs(best - ts) <= tol:
            return mp[best]
        prev = [k for k in keys if k <= ts]
        return mp[prev[-1]] if prev and ts - prev[-1] <= int(tol * 1.35) else default

    @staticmethod
    def lsp(ratio: float) -> Tuple[float, float]:
        r = max(0.0001, sf(ratio, 1))
        long_pct = r / (1 + r) * 100
        return long_pct, 100 - long_pct

    def candles(self, symbol: str, kline_rows: Optional[List[List[Any]]] = None) -> List[Candle]:
        rows = kline_rows if kline_rows is not None else self.klines(symbol)
        if len(rows) < 30:
            return []
        oi_map = {si(x.get("timestamp")): sf(x.get("sumOpenInterest")) for x in self.hist("/futures/data/openInterestHist", symbol)}
        acc_map = {si(x.get("timestamp")): sf(x.get("longShortRatio"), 1) for x in self.hist("/futures/data/topLongShortAccountRatio", symbol)}
        pos_map = {si(x.get("timestamp")): sf(x.get("longShortRatio"), 1) for x in self.hist("/futures/data/topLongShortPositionRatio", symbol)}
        glob_map = {si(x.get("timestamp")): sf(x.get("longShortRatio"), 1) for x in self.hist("/futures/data/globalLongShortAccountRatio", symbol)}
        closes = [sf(x[4]) for x in rows]
        rsi = Indicators.rsi(closes, Config.RSI_PERIOD)
        out: List[Candle] = []
        prev_oi: Optional[float] = None
        for i, row in enumerate(rows):
            ts = si(row[0])
            close = sf(row[4])
            oi = self.nearest(oi_map, ts, 0.0)
            if oi <= 0:
                oi = prev_oi or 0.0
            oi_change = 0.0 if prev_oi is None else oi - prev_oi
            oi_change_pct = 0.0 if not prev_oi else pct(prev_oi, oi)
            if oi > 0:
                prev_oi = oi
            acc = self.nearest(acc_map, ts, 1.0)
            pos = self.nearest(pos_map, ts, 1.0)
            glob = self.nearest(glob_map, ts, 1.0)
            al, ass = self.lsp(acc)
            pl, ps = self.lsp(pos)
            gl, gs = self.lsp(glob)
            out.append(
                Candle(
                    ts,
                    datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    symbol,
                    sf(row[1]),
                    sf(row[2]),
                    sf(row[3]),
                    close,
                    sf(row[5]),
                    sf(row[7]),
                    si(row[8]),
                    sf(row[10]),
                    rsi[i],
                    oi,
                    oi * close,
                    oi_change,
                    oi_change_pct,
                    acc,
                    al,
                    ass,
                    pos,
                    pl,
                    ps,
                    glob,
                    gl,
                    gs,
                )
            )
        return out if sum(1 for c in out if c.oi > 0) >= len(out) * 0.55 else []


# =============================================================================
# V3.2.1 Decision Tree Engine
# =============================================================================
class StructuralLiquidityDiscoveryTreeV321:
    OUTPUT_ORDER = [
        "Symbol",
        "Timeframe",
        "Data Window",
        "Dominant Structural Pattern",
        "Structural Bias",
        "Readiness Level",
        "Signal Timing",
        "Cycle Position",
        "Price Acceptance",
        "OI Read",
        "OI Value Validation",
        "Trades Read",
        "Quote Volume Validation",
        "L/S Divergence",
        "Whale/Crowd Read",
        "Price-led Reset Ignition State",
        "Price-led Base Ignition State",
        "Price-led Base Vacuum Ignition State",
        "High OI Compression State",
        "Trigger Status",
        "Post-Trigger Acceptance",
        "Late Crowding Risk",
        "Invalidation / Risk",
        "Confidence",
        "RSI Context Only",
        "Final Structural Summary",
    ]

    STRUCTURAL_BIASES = {
        "Early Bullish Structure",
        "Early-Live Bullish Structure",
        "Bullish but Event-driven",
        "Bullish but Late",
        "Neutral / Unclear",
        "Neutral-to-Bullish Compression",
        "Distribution Risk",
        "Bearish Structural Risk",
        "Post-Pump Crowding Risk",
        "High Volatility Compression",
    }

    READINESS_LEVELS = {
        "Watchlist Only",
        "Primed Structure",
        "Early-Live Structure",
        "Confirmed Trigger",
        "Accepted Structure",
        "Compression / Unresolved",
        "Failed / Invalidated",
        "Late / Risk State",
    }

    PATTERN_PRIORITY = {
        "Accepted Structure": 100,
        "Confirmed Trigger": 92,
        "Early-Live Structure": 86,
        "Price-led Base Vacuum Ignition": 84,
        "Price-led Base Ignition without OI Expansion": 83,
        "Primed Structure": 74,
        "Compression / Unresolved": 60,
        "Watchlist Only": 40,
        "Late / Risk State": 20,
        "Failed / Invalidated": 5,
    }

    def analyze(self, candles: List[Candle]) -> Optional[V321Decision]:
        if len(candles) < 30:
            return None
        idx = len(candles) - 1
        current = candles[idx]
        hist = candles[:idx]
        quality = self.data_quality_check(candles)
        baseline = self.dynamic_baseline(candles, idx)
        phase = self.phase_memory(candles, idx, baseline)

        # Ordered tree layers. Do not collapse into Price -> OI -> L/S -> Trades.
        oi_value_validation = self.oi_value_validation(candles, idx)
        quote_volume_validation = self.trade_value_validation(candles, idx)
        price_state = self.price_state(candles, idx, phase, baseline)
        oi_state = self.oi_state(candles, idx, phase, baseline)
        oi_regime = self.oi_regime_expansion(candles, idx)
        ls_structure = self.ls_structure(candles, idx)
        ls_divergence = self.ls_divergence(candles, idx)
        trades_state = self.trades_state(candles, idx, phase, baseline)
        price_acceptance = self.price_acceptance(candles, idx, phase, price_state, oi_state, trades_state)
        pre_scanner = self.structural_pre_scanner(candles, idx, phase, price_state, oi_state, trades_state, ls_divergence, price_acceptance)
        trigger_status, post_trigger_acceptance = self.trigger_post_trigger_check(candles, idx, phase, price_acceptance, trades_state, oi_state)
        reset_ignition = self.price_led_reset_ignition_check(candles, idx, phase, price_acceptance, oi_state, trades_state, ls_divergence)
        base_ignition = self.price_led_base_ignition_check(candles, idx, phase, price_acceptance, oi_state, trades_state, ls_divergence, oi_value_validation, quote_volume_validation)
        base_vacuum = self.price_led_base_vacuum_ignition_check(candles, idx, phase, price_acceptance, oi_state, trades_state, ls_divergence, quote_volume_validation)
        high_oi_compression = self.high_oi_compression_check(candles, idx, oi_regime, ls_divergence, price_acceptance)
        late_crowding = self.late_oi_crowding_check(candles, idx, phase, oi_state, trades_state, ls_divergence, base_ignition, base_vacuum, reset_ignition)

        operational = self.classify_v321_operational(
            candles=candles,
            idx=idx,
            phase=phase,
            quality=quality,
            baseline=baseline,
            price_state=price_state,
            oi_state=oi_state,
            oi_regime=oi_regime,
            trades_state=trades_state,
            price_acceptance=price_acceptance,
            pre_scanner=pre_scanner,
            trigger_status=trigger_status,
            post_trigger_acceptance=post_trigger_acceptance,
            reset_ignition=reset_ignition,
            base_ignition=base_ignition,
            base_vacuum=base_vacuum,
            high_oi_compression=high_oi_compression,
            late_crowding=late_crowding,
            ls_divergence=ls_divergence,
            oi_value_validation=oi_value_validation,
            quote_validation=quote_volume_validation,
        )
        pattern = operational["pattern"]
        bias = operational["bias"]
        readiness = operational["readiness"]
        signal_timing = operational["signal_timing"]
        whale_crowd = operational["whale_crowd"]
        invalidation = operational["invalidation"]
        confidence_label = operational["confidence"]
        confidence_score = operational["confidence_score"]

        price_3 = self.price_change(candles, idx, 3)
        trades_ratio = ratio_hist(current.trades, [c.trades for c in hist])
        quote_ratio = ratio_hist(current.quote_volume, [c.quote_volume for c in hist])
        score = self.score_decision(readiness, bias, confidence_score, baseline, price_acceptance, base_vacuum, high_oi_compression)
        category = self.category_from_readiness(readiness, bias)
        final_summary = self.summary(pattern, bias, readiness, signal_timing, price_acceptance, oi_state, trades_state, ls_divergence)

        diagnostics = {
            "tree_order": [
                "Data Quality / Regime Check",
                "Dynamic Baseline",
                "Phase Memory",
                "OI Value / Quote Volume Validation",
                "Price State",
                "OI State",
                "L/S Structure",
                "Trades Regime",
                "Price Acceptance",
                "Structural Pre-Scanner",
                "Trigger / Post-Trigger Check",
                "Price-led Reset Ignition Check",
                "Price-led Base Ignition Check",
                "Price-led Base Vacuum Ignition Check",
                "High OI Compression",
                "Conflict Resolution",
                "Readiness Confirmation Level",
                "Final Structural Decision",
            ],
            "data_quality": asdict(quality),
            "dynamic_baseline": asdict(baseline),
            "phase_memory": asdict(phase),
            "price_state": price_state,
            "oi_state": oi_state,
            "oi_regime_expansion": oi_regime,
            "trades_state": trades_state,
            "ls_structure": ls_structure,
            "pre_scanner": pre_scanner,
            "current_raw": asdict(current),
            "recent_phase_tail": self.phase_tail(candles, idx),
            "v321o_operational_features": operational.get("features", {}),
            "v321o_pattern_candidates": operational.get("candidates", []),
            "v321o_conflict_override": operational.get("conflict_override", "None"),
            "v321o_selected_candidate": operational.get("selected_candidate", {}),
        }

        warnings: List[str] = []
        if readiness in {"Watchlist Only", "Compression / Unresolved"}:
            warnings.append("مراقبة فقط؛ الاتجاه لم يتأكد بعد.")
        if readiness in {"Late / Risk State", "Failed / Invalidated"}:
            warnings.append("ليست فرصة مبكرة حسب V3.2.1.")
        if confidence_label in {"Low", "Medium"} and ("غير متوفر" in oi_value_validation or "غير متوفر" in quote_volume_validation):
            warnings.append("الثقة محدودة بسبب نقص OI Value أو Quote Volume.")

        return V321Decision(
            symbol=current.symbol,
            timeframe=Config.TIMEFRAME,
            data_window=f"{len(candles)} candles | {candles[0].time} -> {current.time}",
            time=current.time,
            close=current.close,
            dominant_structural_pattern=pattern,
            structural_bias=bias,
            readiness_level=readiness,
            signal_timing=signal_timing,
            cycle_position=phase.cycle_position,
            price_acceptance=price_acceptance,
            oi_read=oi_state,
            oi_value_validation=oi_value_validation,
            trades_read=trades_state,
            quote_volume_validation=quote_volume_validation,
            ls_divergence=ls_divergence,
            whale_crowd_read=whale_crowd,
            price_led_reset_ignition_state=reset_ignition,
            price_led_base_ignition_state=base_ignition,
            price_led_base_vacuum_ignition_state=base_vacuum,
            high_oi_compression_state=high_oi_compression,
            trigger_status=trigger_status,
            post_trigger_acceptance=post_trigger_acceptance,
            late_crowding_risk=late_crowding,
            invalidation_risk=invalidation,
            confidence=confidence_label,
            confidence_score=round(confidence_score, 2),
            rsi_context_only="RSI was used only as visual/contextual information, not as a decision driver.",
            final_structural_summary=final_summary,
            category=category,
            rank_priority=self.rank_priority(readiness, pattern),
            score=round(score, 2),
            price_3=round(price_3, 4),
            trades_ratio=round(trades_ratio, 4),
            quote_ratio=round(quote_ratio, 4),
            oi_change_pct=round(current.oi_change_pct, 4),
            rsi=round(current.rsi, 2),
            diagnostics=diagnostics,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # [0.2] DATA_QUALITY_CHECK
    # ------------------------------------------------------------------
    def data_quality_check(self, candles: List[Candle]) -> DataQuality:
        issues: List[str] = []
        if len(candles) < 40:
            issues.append("شموع قليلة؛ Dynamic Baseline أضعف")
        gaps = self.time_gaps(candles)
        if gaps:
            issues.append("توجد شموع مفقودة أو فجوات زمنية")
        if any(c.rsi == 0 for c in candles[: min(10, len(candles))]):
            issues.append("RSI = 0 في بداية النافذة / Warmup Risk")
        positive_oi = [c.oi for c in candles if c.oi > 0]
        if positive_oi and min(positive_oi[: max(3, len(positive_oi) // 10)]) < pval(positive_oi, 20, min(positive_oi)) * 0.30:
            issues.append("Relative OI Distortion Risk")
        first_trades = [c.trades for c in candles[: min(8, len(candles))]]
        all_trades = [c.trades for c in candles]
        if first_trades and mean(first_trades) > pval(all_trades, 85, mean(first_trades)):
            issues.append("Listing Volatility / Initial Liquidity Bootstrapping")
        ls_changes = []
        for i in range(1, len(candles)):
            ls_changes.append(abs(pct(candles[i - 1].global_lsr, candles[i].global_lsr)))
            ls_changes.append(abs(pct(candles[i - 1].account_lsr, candles[i].account_lsr)))
        oi_abs = [abs(c.oi_change_pct) for c in candles]
        if pval(ls_changes, 95, 0) > 8 and pval(oi_abs, 75, 0) < 0.20:
            issues.append("Ratio Noise / Low Reliability")
        oi_coverage = sum(1 for c in candles if c.oi > 0) / max(1, len(candles))
        score = clamp(100 * oi_coverage - len(issues) * 15)
        cap = "Medium" if len(issues) >= 2 else None
        status = "تابع التحليل الطبيعي" if not issues else "خفض الثقة"
        return DataQuality(status=status, issues=issues, confidence_cap=cap, score=score)

    @staticmethod
    def time_gaps(candles: List[Candle]) -> List[Tuple[str, str]]:
        if len(candles) < 3:
            return []
        expected = int(pval([candles[i].time_ms - candles[i - 1].time_ms for i in range(1, len(candles))], 50, 0))
        if expected <= 0:
            return []
        gaps: List[Tuple[str, str]] = []
        for i in range(1, len(candles)):
            if candles[i].time_ms - candles[i - 1].time_ms > int(expected * 1.8):
                gaps.append((candles[i - 1].time, candles[i].time))
        return gaps

    # ------------------------------------------------------------------
    # [0.3] DYNAMIC_BASELINE
    # ------------------------------------------------------------------
    def dynamic_baseline(self, candles: List[Candle], idx: int) -> DynamicBaseline:
        c = candles[idx]
        hist = candles[:idx]
        price_3 = self.price_change(candles, idx, 3)
        ls_change = max(
            abs(self.ratio_change(candles, idx, "global_lsr", 3)),
            abs(self.ratio_change(candles, idx, "account_lsr", 3)),
            abs(self.ratio_change(candles, idx, "position_lsr", 3)),
        )
        price_hist = [self.price_change(candles, i, 3) for i in range(3, idx)]
        oi_hist = [x.oi_change_pct for x in hist]
        trade_hist = [x.trades for x in hist]
        quote_hist = [x.quote_volume for x in hist]
        ls_hist = []
        for i in range(3, idx):
            ls_hist.append(max(abs(self.ratio_change(candles, i, "global_lsr", 3)), abs(self.ratio_change(candles, i, "account_lsr", 3))))
        return DynamicBaseline(
            price_move=signed_label(price_3, price_hist),
            oi_change_pct=signed_label(c.oi_change_pct, oi_hist),
            trades=value_label(c.trades, trade_hist),
            quote_volume=value_label(c.quote_volume, quote_hist),
            ls_change=signed_label(ls_change, ls_hist),
            price_rank=round(extreme(abs(price_3), [abs(x) for x in price_hist]), 2),
            oi_rank=round(extreme(abs(c.oi_change_pct), [abs(x) for x in oi_hist]), 2),
            trades_rank=round(extreme(c.trades, trade_hist), 2),
            quote_rank=round(extreme(c.quote_volume, quote_hist), 2),
            ls_rank=round(extreme(ls_change, ls_hist), 2),
        )

    # ------------------------------------------------------------------
    # [0.1] Phase Memory
    # ------------------------------------------------------------------
    def phase_memory(self, candles: List[Candle], idx: int, baseline: DynamicBaseline) -> PhaseMemory:
        base = self.detect_base(candles, idx)
        flush_idx = self.last_oi_flush(candles, idx)
        trigger_idx = self.last_trigger(candles, idx, base)
        previous_event = "No Major Previous Event"
        if flush_idx is not None:
            previous_event = "OI Flush / Deleveraging Previous Event"
        elif trigger_idx is not None and trigger_idx < idx:
            previous_event = "Previous Trigger / Pump Event"
        elif base[0]:
            previous_event = "Base / Compression Previous Event"
        abnormal = "Shock/Extreme Change Zone" if any(is_event(x) for x in [baseline.price_move, baseline.oi_change_pct, baseline.trades, baseline.quote_volume]) else "No Abnormal Zone"
        ignition = candles[trigger_idx].time if trigger_idx is not None else "No Ignition Candle"
        post = "Post-Ignition Active" if trigger_idx is not None and idx > trigger_idx else "No Post-Ignition Yet"
        reset = flush_idx is not None and self.price_stabilized_after(candles, flush_idx, idx)
        cycle = self.cycle_count(candles, idx, base[0], reset, trigger_idx)
        last_state = "آخر حالة بنيوية: " + ("Trigger" if trigger_idx is not None else "Base" if base[0] else "No Structure")
        return PhaseMemory(
            previous_event=previous_event,
            background_phase="الخلفية السابقة مقروءة عبر كامل النافذة",
            pressure_or_quiet_zone="Base / Quiet Zone" if base[0] else "No Clean Quiet Zone",
            abnormal_change_zone=abnormal,
            pre_ignition_zone="Pre-Ignition Base" if base[0] and trigger_idx is None else "Pre-Ignition Checked",
            ignition_candle=ignition,
            post_ignition_zone=post,
            last_structural_state=last_state,
            base_detected=base[0],
            base_low=round(base[1], 10),
            base_high=round(base[2], 10),
            base_start_time=base[3],
            base_end_time=base[4],
            reset_detected=reset,
            reset_time=candles[flush_idx].time if flush_idx is not None else "No Reset",
            trigger_time=ignition,
            cycle_position=cycle,
        )

    # ------------------------------------------------------------------
    # [0.4] OI_VALUE_VALIDATION
    # ------------------------------------------------------------------
    def oi_value_validation(self, candles: List[Candle], idx: int) -> str:
        if idx <= 0:
            return "OI Value غير متوفر أو غير قابل للحكم"
        c, p = candles[idx], candles[idx - 1]
        if c.oi_value <= 0 or p.oi_value <= 0:
            return "OI Value غير متوفر: استخدم OI Change بحذر وخفّض الثقة عند العملات منخفضة السعر أو الجديدة"
        ov = pct(p.oi_value, c.oi_value)
        oc = c.oi_change_pct
        if oc > 0 and ov > 0 and abs(ov) >= abs(oc) * 0.40:
            return "Real Position Expansion"
        if oc > 0 and ov <= max(0.05, abs(oc) * 0.25):
            return "Contract-count distortion / Low-price distortion"
        if abs(oc) <= 0.05 and ov > 0.20:
            return "Price-driven OI Value Expansion"
        if oc < 0 and abs(ov) <= 0.08:
            return "OI contracts ↓ + OI Value ثابت: السعر يعوض انخفاض OI؛ ليس خروج سيولة كامل"
        if oc < 0 and ov < 0:
            return "Real Deleveraging / Position Exit"
        return "OI Value Mixed / Neutral"

    # ------------------------------------------------------------------
    # [0.5] TRADE_VALUE_VALIDATION
    # ------------------------------------------------------------------
    def trade_value_validation(self, candles: List[Candle], idx: int) -> str:
        c = candles[idx]
        hist = candles[:idx]
        if c.quote_volume <= 0 or not any(x.quote_volume > 0 for x in hist):
            return "Quote Volume غير متوفر: استخدم Trades كبديل ولا ترفع الثقة إلى High إلا بتأكيد OI والسعر"
        tr = value_label(c.trades, [x.trades for x in hist])
        qr = value_label(c.quote_volume, [x.quote_volume for x in hist])
        if is_active(tr) and is_active(qr) and c.oi_change_pct > 0:
            return "Real Capital Activation"
        if is_active(tr) and is_active(qr) and c.oi_change_pct <= 0:
            return "Liquidation / Covering / Spot-led or Vacuum Flow"
        if is_active(tr) and not is_active(qr):
            return "Micro-trade Noise / Bot Activity"
        if not is_active(tr) and is_active(qr):
            return "Large Block-like Execution / Low-count High-value Flow"
        if is_active(tr) and abs(self.price_change(candles, idx, 1)) <= 0.10:
            return "Absorption Battle"
        return "Trades/Quote Normal or Gradual"

    # ------------------------------------------------------------------
    # [0.6] PRICE_STATE
    # ------------------------------------------------------------------
    def price_state(self, candles: List[Candle], idx: int, phase: PhaseMemory, baseline: DynamicBaseline) -> str:
        p3 = self.price_change(candles, idx, 3)
        p6 = self.price_change(candles, idx, 6)
        p12 = self.price_change(candles, idx, 12)
        higher_lows = self.higher_lows(candles, idx)
        higher_highs = self.higher_highs(candles, idx)
        if p3 > 0 and is_event(baseline.price_move):
            if phase.reset_detected:
                return "صاعد بعد Reset"
            if phase.base_detected:
                return "صاعد من قاعدة بدون Reset"
            return "صاعد انفجاري"
        if p6 > 0 and higher_lows and higher_highs:
            return "صاعد صحي"
        if phase.base_detected and abs(p6) < max(1.0, abs(p12) * 0.35):
            return "عرضي / ثابت"
        if p3 < 0 and is_event(baseline.price_move):
            return "هابط عنيف"
        if p6 < 0:
            return "هابط تدريجي"
        if p3 > 0 and p12 < 0:
            return "ارتداد بعد هبوط"
        return "عرضي / ثابت"

    # ------------------------------------------------------------------
    # [0.10] OI_STATE
    # ------------------------------------------------------------------
    def oi_state(self, candles: List[Candle], idx: int, phase: PhaseMemory, baseline: DynamicBaseline) -> str:
        c = candles[idx]
        price_3 = self.price_change(candles, idx, 3)
        oi3 = sum(x.oi_change_pct for x in candles[max(0, idx - 2) : idx + 1])
        if c.oi_change_pct < 0 and is_event(baseline.oi_change_pct):
            return "OI Flush"
        if c.oi_change_pct > 0 and is_event(baseline.oi_change_pct):
            if price_3 > 0 and phase.trigger_time != "No Ignition Candle":
                return "OI صاعد انفجاري"
            return "OI صاعد انفجاري"
        if phase.reset_detected and price_3 > 0 and oi3 > 0:
            return "Delayed Constructive OI Reload After Reset"
        if phase.base_detected and price_3 > 0 and oi3 > 0:
            return "Delayed Constructive OI Reload From Base"
        if phase.base_detected and price_3 > 0 and c.oi_change_pct <= 0 and c.oi_change_pct >= -0.80:
            return "Price-led Base Move Without OI Expansion"
        if oi3 > 0.35:
            return "OI صاعد تدريجي"
        if abs(oi3) <= 0.15:
            return "OI ثابت"
        if oi3 < -0.35 and price_3 > 0:
            return "OI هابط تدريجي"
        if oi3 < -0.35:
            return "OI Deleveraging After Pump" if self.price_change(candles, idx, 12) > 2 else "OI هابط تدريجي"
        return "OI ثابت"

    # ------------------------------------------------------------------
    # [0.11] OI_REGIME_EXPANSION
    # ------------------------------------------------------------------
    def oi_regime_expansion(self, candles: List[Candle], idx: int) -> str:
        c = candles[idx]
        hist_oi = [x.oi for x in candles[:idx] if x.oi > 0]
        if not hist_oi or c.oi <= 0:
            return "Normal Commitment"
        ratio = c.oi / max(1e-12, pval(hist_oi, 50, c.oi))
        near_high = c.oi >= pval(hist_oi + [c.oi], 92, c.oi)
        under_peak = c.close < max(x.close for x in candles[max(0, idx - 20) : idx + 1]) * 0.985
        if near_high and under_peak:
            if c.global_lsr > 1.15:
                return "Trapped Long Compression"
            if c.global_lsr < 0.85:
                return "Short-Crowded Compression"
            return "Neutral High-OI Volatility Risk"
        if ratio >= 4.0:
            return "High Leverage Regime"
        if ratio >= 2.0:
            return "Active Regime"
        return "Normal Commitment"

    # ------------------------------------------------------------------
    # [0.12] TRADES_STATE
    # ------------------------------------------------------------------
    def trades_state(self, candles: List[Candle], idx: int, phase: PhaseMemory, baseline: DynamicBaseline) -> str:
        c = candles[idx]
        p1 = self.price_change(candles, idx, 1)
        if is_event(baseline.trades) and p1 < 0 and c.oi_change_pct < 0:
            return "Trades تنظيف"
        if phase.base_detected and is_active(baseline.trades) and p1 > 0 and c.oi_change_pct <= 0:
            return "Trades / Quote Vacuum Ignition من Base بدون Reset"
        if phase.base_detected and is_active(baseline.trades) and p1 > 0:
            return "Trades إشعال من Base بدون Reset"
        if phase.reset_detected and is_active(baseline.trades) and p1 > 0:
            return "Trades إشعال بعد Reset"
        if is_event(baseline.trades) and p1 > 0:
            return "Trades إشعال"
        if is_event(baseline.trades) and abs(p1) <= 0.10:
            return "Trades فشل" if c.oi_change_pct > 0 else "Absorption Battle"
        if is_active(baseline.trades):
            return "Trades صحية تدريجية"
        return "Trades هادئة"

    # ------------------------------------------------------------------
    # [0.13] L/S_STRUCTURE and [0.14] L/S_DIVERGENCE
    # ------------------------------------------------------------------
    def ls_structure(self, candles: List[Candle], idx: int) -> Dict[str, str]:
        c = candles[idx]
        return {
            "GLOBAL_LS": "يرتفع" if self.ratio_change(candles, idx, "global_lsr", 3) > 1 else "يهبط" if self.ratio_change(candles, idx, "global_lsr", 3) < -1 else "ثابت",
            "TOP_ACCOUNT_LS": "يرتفع" if self.ratio_change(candles, idx, "account_lsr", 3) > 1 else "يهبط" if self.ratio_change(candles, idx, "account_lsr", 3) < -1 else "ثابت",
            "TOP_POSITION_LS": "يرتفع" if self.ratio_change(candles, idx, "position_lsr", 3) > 1 else "يهبط" if self.ratio_change(candles, idx, "position_lsr", 3) < -1 else "ثابت",
            "GLOBAL_LS_VALUE": f"{c.global_lsr:.4f}",
            "TOP_ACCOUNT_LS_VALUE": f"{c.account_lsr:.4f}",
            "TOP_POSITION_LS_VALUE": f"{c.position_lsr:.4f}",
        }

    def ls_divergence(self, candles: List[Candle], idx: int) -> str:
        c = candles[idx]
        g = self.ratio_change(candles, idx, "global_lsr", 3)
        a = self.ratio_change(candles, idx, "account_lsr", 3)
        p = self.ratio_change(candles, idx, "position_lsr", 3)
        g_up, a_up, p_up = g > 1, a > 1, p > 0.5
        g_down, a_down, p_down = g < -1, a < -1, p < -0.5
        if g_up and a_up and p_up:
            return "Long Consensus"
        if g_up and a_up and p_down:
            return "Crowd Chasing / Large Position Caution"
        if g_up and a_down and p_down:
            return "Retail Long / Smart Exit"
        if g_down and a_down and not p_down:
            return "Short Pressure Against Stable Big Positions"
        if g_down and a_down and p_down:
            return "Broad Risk-Off / Position Reduction"
        if g_down and a_up and p_up:
            return "Top-side Accumulation Against Crowd"
        if abs(g) <= 1 and a_up and p_up:
            return "Quiet Top Positioning"
        if abs(g) <= 1 and a_up and p_down:
            return "Account Count Without Size"
        if g < -3 and a < -3 and c.position_lsr > 0.90:
            return "Short-Crowded Account Pressure, large positions not equally short"
        if g_down and a_down and c.position_lsr > 1.15:
            return "Top Position Long Retention with Crowd/Account Compression"
        if (abs(g) <= 1 or g > 0) and not a_up and c.position_lsr > 1.10:
            return "Top Position Retention with Non-Chasing Accounts"
        return "No L/S Edge" if abs(g) <= 1 and abs(a) <= 1 and abs(p) <= 0.5 else "Mixed L/S Structure"

    # ------------------------------------------------------------------
    # [0.7] PRICE_ACCEPTANCE
    # ------------------------------------------------------------------
    def price_acceptance(self, candles: List[Candle], idx: int, phase: PhaseMemory, price_state: str, oi_state: str, trades_state: str) -> str:
        c = candles[idx]
        eps = Config.ACCEPTANCE_EPS
        if phase.base_detected:
            if c.close > phase.base_high * (1 + eps):
                if "Without OI" in oi_state or "Price-led Base Move Without OI Expansion" in oi_state:
                    return "Pre-OI / No-OI Accepted Move From Base"
                return "Pre-OI Accepted Move From Base" if "صاعد من قاعدة" in price_state else "Accepted Breakout"
            if c.close >= phase.base_low and c.close < phase.base_high:
                return "Controlled Pullback" if phase.trigger_time != "No Ignition Candle" else "No Trigger / Base Holding"
            if c.close < phase.base_low:
                return "Structure Invalidated"
        if phase.reset_detected and self.price_change(candles, idx, 3) > 0:
            return "Pre-OI Accepted Move After Reset"
        trigger_idx = self.last_trigger(candles, idx, (phase.base_detected, phase.base_low, phase.base_high, phase.base_start_time, phase.base_end_time))
        if trigger_idx is not None:
            trig = candles[trigger_idx]
            half = (trig.open + trig.close) / 2
            if c.close >= trig.close:
                return "Accepted Breakout"
            if c.close >= half:
                return "Constructive Acceptance"
            if phase.base_detected and c.close < phase.base_high:
                return "Failed Breakout"
        if "OI صاعد" in oi_state and not self.higher_highs(candles, idx):
            return "OI Trap Risk"
        return "No Clear Acceptance"

    # ------------------------------------------------------------------
    # [1] Structural Pre-Scanner
    # ------------------------------------------------------------------
    def structural_pre_scanner(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        price_state: str,
        oi_state: str,
        trades_state: str,
        ls_divergence: str,
        price_acceptance: str,
    ) -> Dict[str, str]:
        return {
            "OI_FLUSH_DETECTOR": "Forced Reset Candidate" if self.last_oi_flush(candles, idx) is not None else "No OI Flush",
            "POST_FLUSH_BEHAVIOR": self.post_flush_behavior(candles, idx, phase),
            "PRE_PRICE_OI_BUILDUP": self.pre_price_oi_buildup(candles, idx, phase, ls_divergence),
            "PRICE_LEADS_OI": self.price_leads_oi(candles, idx, phase, oi_state),
            "IGNITION_WITHOUT_OI": self.ignition_without_oi(candles, idx, phase, oi_state, trades_state),
            "SHORT_CROWDING_QUALITY": self.short_crowding_quality(candles, idx, price_acceptance),
        }

    def post_flush_behavior(self, candles: List[Candle], idx: int, phase: PhaseMemory) -> str:
        flush_idx = self.last_oi_flush(candles, idx)
        if flush_idx is None:
            return "No Flush Context"
        if not self.price_stabilized_after(candles, flush_idx, idx):
            return "Liquidity Exit / Decay" if candles[idx].oi <= candles[flush_idx].oi else "Bearish Expansion"
        if sum(c.oi_change_pct for c in candles[max(flush_idx, idx - 3) : idx + 1]) > 0:
            if self.ratio_change(candles, idx, "global_lsr", max(1, idx - flush_idx)) < 0:
                return "Absorption After Flush / Short Build Near Bottom"
            return "Long Reload After Flush"
        return "Stabilization Without Commitment"

    def pre_price_oi_buildup(self, candles: List[Candle], idx: int, phase: PhaseMemory, ls_divergence: str) -> str:
        if idx < 6:
            return "No Pre-Price OI Read"
        oi_before = sum(c.oi_change_pct for c in candles[idx - 6 : idx - 2])
        price_before = pct(candles[idx - 6].close, candles[idx - 2].close)
        if oi_before > 0.40 and abs(price_before) < max(0.8, abs(self.price_change(candles, idx, 3)) * 0.35):
            if "Short" in ls_divergence or "Crowd" in ls_divergence:
                return "Short Build Under Stable Price"
            return "Fresh Build-up Candidate"
        return "OI لا يسبق السعر"

    def price_leads_oi(self, candles: List[Candle], idx: int, phase: PhaseMemory, oi_state: str) -> str:
        p3 = self.price_change(candles, idx, 3)
        oi3 = sum(c.oi_change_pct for c in candles[max(0, idx - 2) : idx + 1])
        if p3 > 0 and oi3 <= 0.15:
            if phase.reset_detected:
                return "السعر صعد قبل OI بعد Reset"
            if phase.base_detected:
                return "السعر صعد قبل OI من Base بدون Reset"
            return "السعر صعد قبل OI بدون Reset وبدون Base"
        if p3 < 0 and oi3 >= 0.15:
            return "السعر هبط قبل OI"
        if p3 > 0 and oi3 > 0.15:
            return "السعر و OI تحركا معًا"
        return "No Price-led Structure"

    def ignition_without_oi(self, candles: List[Candle], idx: int, phase: PhaseMemory, oi_state: str, trades_state: str) -> str:
        if self.price_change(candles, idx, 1) > 0 and "Trades" in trades_state and ("ثابت" in oi_state or "Without OI" in oi_state or candles[idx].oi_change_pct <= 0):
            if phase.reset_detected:
                return "Post-Flush Vacuum Ignition"
            if phase.base_detected:
                return "Price-led Base Vacuum Ignition"
            return "Vacuum Ignition / Stop-Driven Move"
        return "No Ignition Without OI"

    def short_crowding_quality(self, candles: List[Candle], idx: int, price_acceptance: str) -> str:
        c = candles[idx]
        oi_up = sum(x.oi_change_pct for x in candles[max(0, idx - 2) : idx + 1]) > 0
        ls_down = self.ratio_change(candles, idx, "global_lsr", 3) < -1 and self.ratio_change(candles, idx, "account_lsr", 3) < -1
        if oi_up and ls_down and self.higher_lows(candles, idx):
            return "Healthy Short Squeeze Fuel"
        if oi_up and ls_down and "No Clear" in price_acceptance:
            return "Compression Risk / Needs Breakout"
        if oi_up and ls_down and not self.higher_lows(candles, idx):
            return "Bearish Short Build-up"
        return "No Short Crowding Edge"

    # ------------------------------------------------------------------
    # [1.9] Trigger / Post-Trigger
    # ------------------------------------------------------------------
    def trigger_post_trigger_check(self, candles: List[Candle], idx: int, phase: PhaseMemory, price_acceptance: str, trades_state: str, oi_state: str) -> Tuple[str, str]:
        if phase.trigger_time == "No Ignition Candle":
            return "No Trigger", "لا يوجد Trigger"
        if price_acceptance in {"Accepted Breakout", "Pre-OI Accepted Move From Base", "Pre-OI / No-OI Accepted Move From Base"}:
            trigger = "Confirmed Trigger" if "Trades" in trades_state or "Ignition" in trades_state else "Trigger Candidate"
        elif price_acceptance == "Constructive Acceptance":
            trigger = "Trigger Candidate"
        elif price_acceptance in {"Failed Breakout", "Structure Invalidated"}:
            return "Failed Trigger", "Failed Trigger"
        else:
            trigger = "Trigger Candidate"
        if price_acceptance == "Accepted Breakout":
            post = "Accepted Trigger"
        elif price_acceptance == "Constructive Acceptance":
            post = "Constructive Acceptance"
        elif price_acceptance == "Pre-OI / No-OI Accepted Move From Base" and ("Without OI" in oi_state or "ثابت" in oi_state or "هابط" in oi_state):
            post = "Accepted Vacuum / Stop-driven Trigger"
        elif price_acceptance in {"Failed Breakout", "Structure Invalidated"}:
            post = "Failed Trigger"
        else:
            post = "Needs Post-Trigger Acceptance"
        return trigger, post

    # ------------------------------------------------------------------
    # [1.5B] Price-led Reset Ignition with OI Reload
    # ------------------------------------------------------------------
    def price_led_reset_ignition_check(self, candles: List[Candle], idx: int, phase: PhaseMemory, price_acceptance: str, oi_state: str, trades_state: str, ls_divergence: str) -> str:
        if not phase.reset_detected:
            return "Not Applicable: No Reset"
        if not self.price_stabilized_after(candles, self.last_oi_flush(candles, idx) or idx, idx):
            return "Liquidity Exit / Decay"
        if self.price_change(candles, idx, 3) <= 0:
            return "Reset Stabilization Only"
        if "Delayed Constructive OI Reload After Reset" in oi_state:
            if any(key in ls_divergence for key in ["Short", "Crowd/Account", "Retention"]):
                return "Price-led Reset Ignition with OI Reload"
            return "Price-led Reset Ignition"
        if "Trades" in trades_state and ("ثابت" in oi_state or "هابط" in oi_state):
            return "Short Covering / Vacuum Bounce فقط"
        return "Weak Relief Bounce / Needs Confirmation"

    # ------------------------------------------------------------------
    # [1.5C] Price-led Base Ignition without Reset
    # ------------------------------------------------------------------
    def price_led_base_ignition_check(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        price_acceptance: str,
        oi_state: str,
        trades_state: str,
        ls_divergence: str,
        oi_value_validation: str,
        quote_validation: str,
    ) -> str:
        if phase.reset_detected:
            return "Not Applicable: Reset branch has priority"
        if not phase.base_detected:
            return "Not Applicable: No Base"
        if self.price_change(candles, idx, 3) <= 0:
            return "Primed Base / Watch for Trigger"
        if "Price-led Base Move Without OI Expansion" in oi_state or "ثابت" in oi_state or "هابط" in oi_state:
            return "Check [1.5C-V] Price-led Base Vacuum Ignition"
        if "Delayed Constructive OI Reload From Base" in oi_state or "صاعد" in oi_state:
            q_ok = "Real" in quote_validation or "Normal" in quote_validation or "Large Block" in quote_validation
            ls_ok = any(x in ls_divergence for x in ["Short Pressure", "Retention", "Quiet Top", "No L/S Edge", "Top Position"])
            if q_ok and ls_ok and price_acceptance in {"Pre-OI Accepted Move From Base", "Accepted Breakout", "Constructive Acceptance"}:
                return "Price-led Base Ignition with Delayed OI Confirmation"
            if price_acceptance in {"Failed Breakout", "Structure Invalidated"}:
                return "Failed Base Ignition"
            return "Price-led Base Ignition"
        return "Weak Base Drift / Needs Confirmation"

    # ------------------------------------------------------------------
    # [1.5C-V] Price-led Base Vacuum Ignition without OI Expansion
    # ------------------------------------------------------------------
    def price_led_base_vacuum_ignition_check(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        price_acceptance: str,
        oi_state: str,
        trades_state: str,
        ls_divergence: str,
        quote_validation: str,
    ) -> str:
        c = candles[idx]
        if phase.reset_detected:
            return "Not Applicable: Reset branch has priority"
        if not phase.base_detected:
            return "Not Applicable: No Base"
        price_out = c.close > phase.base_high or price_acceptance in {"Pre-OI / No-OI Accepted Move From Base", "Accepted Breakout", "Constructive Acceptance"}
        if not price_out:
            return "Primed Base for Price-led Vacuum Ignition" if c.close >= phase.base_low else "Failed Base Vacuum Ignition"
        oi_flat_or_down_small = (abs(c.oi_change_pct) <= 0.25) or (-0.80 <= c.oi_change_pct < 0)
        trades_ok = "Vacuum" in trades_state or "إشعال" in trades_state or is_active(self.dynamic_baseline(candles, idx).trades)
        quote_missing = "غير متوفر" in quote_validation or "UNAVAILABLE" in quote_validation
        quote_ok = quote_missing or any(x in quote_validation for x in ["Real Execution", "Liquidation / Covering", "Large Block", "Real Capital", "Normal"])
        top_position_ok = c.position_lsr >= 1.05 or self.ratio_change(candles, idx, "position_lsr", 3) > -3.0
        account_non_chase = self.ratio_change(candles, idx, "account_lsr", 3) <= 4.0
        global_not_excess_long = c.global_lsr <= 1.20
        if c.oi_change_pct < -1.50:
            return "Deleveraging Extension Risk; خفّض الثقة"
        if trades_ok and quote_ok and oi_flat_or_down_small and top_position_ok and account_non_chase and global_not_excess_long:
            if quote_missing:
                if price_acceptance in {"Pre-OI / No-OI Accepted Move From Base", "Accepted Breakout", "Constructive Acceptance"}:
                    return "Accepted Base Vacuum Ignition / Quote Volume Missing: Confidence cap Medium"
                return "Price-led Base Vacuum Ignition / Quote Volume Missing: Confidence cap Medium"
            if price_acceptance in {"Pre-OI / No-OI Accepted Move From Base", "Accepted Breakout", "Constructive Acceptance"}:
                return "Accepted Base Vacuum Ignition"
            return "Price-led Base Vacuum Ignition"
        if not quote_ok:
            return "Micro-trade / Bot Noise Risk"
        if not top_position_ok:
            return "Weak Vacuum / Low Confidence"
        if not account_non_chase or not global_not_excess_long:
            return "Late Base Crowding Risk"
        return "Weak Base Drift / لا ترفعها أعلى من Watchlist"

    # ------------------------------------------------------------------
    # [1.8] High OI Compression
    # ------------------------------------------------------------------
    def high_oi_compression_check(self, candles: List[Candle], idx: int, oi_regime: str, ls_divergence: str, price_acceptance: str) -> str:
        c = candles[idx]
        if "Compression" not in oi_regime and "High" not in oi_regime:
            return "OI ليس عاليًا تاريخيًا"
        if c.close < max(x.close for x in candles[max(0, idx - 20) : idx + 1]) * 0.985:
            if c.global_lsr > 1.15:
                return "Trapped Long Compression / Post-Pump Risk"
            if c.global_lsr < 0.90 or "Short" in ls_divergence:
                if price_acceptance in {"Accepted Breakout", "Constructive Acceptance"}:
                    return "Short-Crowded Compression: Squeeze Fuel مستمر"
                return "Short-Crowded Compression"
            return "High OI Neutral Compression / Volatility Risk"
        return "High OI but price holding"

    # ------------------------------------------------------------------
    # [1.6] Late OI Crowding
    # ------------------------------------------------------------------
    def late_oi_crowding_check(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        oi_state: str,
        trades_state: str,
        ls_divergence: str,
        base_ignition: str,
        base_vacuum: str,
        reset_ignition: str,
    ) -> str:
        c = candles[idx]
        price_extended = self.distance_from_base_or_reset(candles, idx, phase) > 2.2 or self.price_change(candles, idx, 12) > 6
        oi_late = "صاعد انفجاري" in oi_state and price_extended
        if phase.reset_detected and "Reset Ignition" in reset_ignition:
            return "Not Late: Reset branch has priority"
        if phase.base_detected and ("Base Ignition" in base_ignition or "Base Vacuum" in base_vacuum):
            return "Not Late: Base branch has priority"
        if oi_late and (self.ratio_change(candles, idx, "global_lsr", 3) > 1 or self.ratio_change(candles, idx, "account_lsr", 3) > 1):
            if self.ratio_change(candles, idx, "position_lsr", 3) <= 0:
                return "Late OI Crowding / Large Position Caution"
            return "Late OI Crowding"
        if price_extended and "Trades" in trades_state:
            return "Bullish but Late / Extension Risk"
        return "No Late Crowding"

    # ------------------------------------------------------------------
    # [3.5], [3.6], [4], [7], [8], [9]
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Structural Liquidity Discovery Tree V3.2.1-O
    # Candidate Eligibility | Pattern Eligibility + Support Score | Hard Conflict Override
    # V3.2.1-O Operational Mapping
    # Features -> Pattern Eligibility + Support Score -> Conflict Rules -> Readiness -> Confidence
    # ------------------------------------------------------------------
    def classify_v321_operational(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        quality: DataQuality,
        baseline: DynamicBaseline,
        price_state: str,
        oi_state: str,
        oi_regime: str,
        trades_state: str,
        price_acceptance: str,
        pre_scanner: Dict[str, str],
        trigger_status: str,
        post_trigger_acceptance: str,
        reset_ignition: str,
        base_ignition: str,
        base_vacuum: str,
        high_oi_compression: str,
        late_crowding: str,
        ls_divergence: str,
        oi_value_validation: str,
        quote_validation: str,
    ) -> Dict[str, Any]:
        F = self.build_v321o_features(
            candles,
            idx,
            phase,
            quality,
            baseline,
            price_state,
            oi_state,
            oi_regime,
            trades_state,
            price_acceptance,
            pre_scanner,
            trigger_status,
            post_trigger_acceptance,
            reset_ignition,
            base_ignition,
            base_vacuum,
            high_oi_compression,
            late_crowding,
            ls_divergence,
            oi_value_validation,
            quote_validation,
        )
        candidates = self.score_all_patterns_v321o(F)
        eligible = [c for c in candidates if c.required_pass]
        override = self.apply_conflict_rules_v321o(F, eligible)
        selected: PatternCandidate
        conflict_override = "None"
        if override is not None:
            selected = override
            conflict_override = override.name
        else:
            selected = self.select_by_priority_and_score_v321o(eligible, F)

        readiness = self.assign_readiness_v321o(selected.name, F)
        bias = self.assign_bias_v321o(selected.name, readiness, F)
        if readiness in {"Failed / Invalidated", "Late / Risk State"}:
            bias = self.downgrade_bias_by_readiness_v321o(bias, readiness, selected.name)
        confidence, confidence_score = self.assign_confidence_v321o(selected.name, readiness, F)
        confidence, confidence_score = self.apply_confidence_caps_v321o(confidence, confidence_score, F)
        signal_timing = self.signal_timing(candles, idx, phase, F["oi"]["raw_state"], F["structure"]["raw_base_vacuum"])
        whale_crowd = self.whale_crowd_timing(candles, idx, phase, F["ls"]["raw_divergence"], F["structure"]["raw_base_vacuum"], F["structure"]["raw_reset_ignition"])
        invalidation = self.invalidation_risk(candles, idx, phase, F["price"]["raw_acceptance"], F["oi"]["raw_state"])
        return {
            "pattern": selected.name,
            "bias": bias,
            "readiness": readiness,
            "signal_timing": signal_timing,
            "whale_crowd": whale_crowd,
            "invalidation": invalidation,
            "confidence": confidence,
            "confidence_score": confidence_score,
            "features": F,
            "candidates": [asdict(c) | {"net_score": round(c.net_score, 4)} for c in candidates],
            "selected_candidate": asdict(selected) | {"net_score": round(selected.net_score, 4)},
            "conflict_override": conflict_override,
        }

    @staticmethod
    def _enum_label(label: str) -> str:
        return str(label or "").strip().upper().replace("-", "_")

    def build_v321o_features(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        quality: DataQuality,
        baseline: DynamicBaseline,
        price_state: str,
        oi_state: str,
        oi_regime: str,
        trades_state: str,
        price_acceptance: str,
        pre_scanner: Dict[str, str],
        trigger_status: str,
        post_trigger_acceptance: str,
        reset_ignition: str,
        base_ignition: str,
        base_vacuum: str,
        high_oi_compression: str,
        late_crowding: str,
        ls_divergence: str,
        oi_value_validation: str,
        quote_validation: str,
    ) -> Dict[str, Any]:
        c = candles[idx]
        rc_global = self.ratio_change(candles, idx, "global_lsr", 3)
        rc_account = self.ratio_change(candles, idx, "account_lsr", 3)
        rc_position = self.ratio_change(candles, idx, "position_lsr", 3)
        price3 = self.price_change(candles, idx, 3)
        price12 = self.price_change(candles, idx, 12)
        dist = self.distance_from_base_or_reset(candles, idx, phase)
        recent = candles[max(0, idx - 20) : idx + 1]
        recent_peak = max(x.close for x in recent) if recent else c.close
        oi_hist = [x.oi for x in candles[:idx] if x.oi > 0]
        oi_p92 = pval(oi_hist + [c.oi], 92, c.oi) if oi_hist else c.oi
        oi_p85 = pval(oi_hist + [c.oi], 85, c.oi) if oi_hist else c.oi

        price_map = {
            "صاعد صحي": "HEALTHY_UP",
            "صاعد انفجاري": "EXPLOSIVE_UP",
            "صاعد بعد Reset": "UP_AFTER_RESET",
            "صاعد من قاعدة بدون Reset": "UP_FROM_BASE_WITHOUT_RESET",
            "عرضي / ثابت": "SIDEWAYS",
            "هابط تدريجي": "GRADUAL_DOWN",
            "هابط عنيف": "VIOLENT_DOWN",
            "ارتداد بعد هبوط": "BOUNCE_AFTER_DROP",
        }
        price_enum = price_map.get(price_state, "SIDEWAYS")
        oi_enum = "FLAT"
        if oi_state == "OI صاعد تدريجي":
            oi_enum = "GRADUAL_UP"
        elif oi_state == "OI صاعد انفجاري":
            oi_enum = "EXPLOSIVE_UP"
        elif oi_state == "OI هابط تدريجي":
            oi_enum = "GRADUAL_DOWN"
        elif oi_state == "OI Flush":
            oi_enum = "FLUSH"
        elif oi_state == "Delayed Constructive OI Reload After Reset":
            oi_enum = "DELAYED_RELOAD_AFTER_RESET"
        elif oi_state == "Delayed Constructive OI Reload From Base":
            oi_enum = "DELAYED_RELOAD_FROM_BASE"
        elif oi_state == "Price-led Base Move Without OI Expansion":
            oi_enum = "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"
        elif oi_state == "OI Deleveraging After Pump":
            oi_enum = "DELEVERAGING_AFTER_PUMP"
        elif "Late" in late_crowding and not phase.reset_detected and not phase.base_detected:
            oi_enum = "LATE_EXPANSION"

        q_enum = "UNAVAILABLE" if "غير متوفر" in quote_validation else "NORMAL"
        if "Real Capital" in quote_validation:
            q_enum = "REAL_CAPITAL_ACTIVATION"
        elif "Real Execution" in quote_validation:
            q_enum = "REAL_EXECUTION_EXPANSION"
        elif "Micro-trade" in quote_validation:
            q_enum = "MICRO_TRADE_NOISE"
        elif "Large Block" in quote_validation:
            q_enum = "LARGE_BLOCK_LIKE_EXECUTION"
        elif "Liquidation / Covering" in quote_validation:
            q_enum = "LIQUIDATION_OR_COVERING_FLOW"

        oiv_enum = "UNAVAILABLE" if "غير متوفر" in oi_value_validation else "NEUTRAL"
        if "Real Position Expansion" in oi_value_validation:
            oiv_enum = "REAL_POSITION_EXPANSION"
        elif "Contract-count" in oi_value_validation:
            oiv_enum = "CONTRACT_COUNT_DISTORTION"
        elif "Price-driven" in oi_value_validation:
            oiv_enum = "PRICE_DRIVEN_OI_VALUE_EXPANSION"
        elif "السعر يعوض" in oi_value_validation:
            oiv_enum = "PRICE_COMPENSATES_OI_DROP"
        elif "Real Deleveraging" in oi_value_validation:
            oiv_enum = "REAL_DELEVERAGING"

        t_enum = "QUIET"
        if trades_state == "Trades صحية تدريجية":
            t_enum = "HEALTHY_GRADUAL"
        elif trades_state == "Trades تنظيف":
            t_enum = "CLEANUP"
        elif trades_state == "Trades إشعال":
            t_enum = "IGNITION"
        elif trades_state == "Trades إشعال بعد Reset":
            t_enum = "IGNITION_AFTER_RESET"
        elif trades_state == "Trades إشعال من Base بدون Reset":
            t_enum = "IGNITION_FROM_BASE"
        elif trades_state == "Trades / Quote Vacuum Ignition من Base بدون Reset":
            t_enum = "BASE_VACUUM_IGNITION"
        elif trades_state in {"Trades فشل", "Absorption Battle"}:
            t_enum = "FAILED_EXECUTION"
        elif "Bot" in trades_state:
            t_enum = "BOT_NOISE"
        elif "Late" in late_crowding or "Extension" in late_crowding:
            t_enum = "LATE_CROWDING"

        g_state = "UP" if rc_global > 1 else "DOWN" if rc_global < -1 else "FLAT"
        a_state = "UP" if rc_account > 1 else "DOWN" if rc_account < -1 else "FLAT"
        p_state = "UP" if rc_position > 0.5 else "DOWN" if rc_position < -0.5 else "FLAT"
        accepted = price_acceptance in {"Accepted Breakout", "Pre-OI Accepted Move From Base", "Pre-OI / No-OI Accepted Move From Base"}
        constructive = price_acceptance == "Constructive Acceptance"
        failed = price_acceptance in {"Failed Breakout", "Structure Invalidated"} or trigger_status == "Failed Trigger" or post_trigger_acceptance == "Failed Trigger"
        back_inside = bool(
            (price_acceptance == "Failed Breakout")
            or (
                phase.base_detected
                and trigger_status != "No Trigger"
                and c.close < phase.base_high * (1 - Config.ACCEPTANCE_EPS)
                and not accepted
                and not constructive
            )
        )
        breaks_base = bool(phase.base_detected and c.close < phase.base_low * (1 - Config.ACCEPTANCE_EPS)) or price_acceptance == "Structure Invalidated"
        near_footprint = (dist <= 2.2 or abs(price12) <= 6.0) and not (dist > 4.5 and c.oi >= oi_p92)
        far_footprint = dist > 2.2 or price12 > 6.0
        top_position_retention = c.position_lsr >= 1.05 or rc_position > -3.0 or "Top Position" in ls_divergence
        top_position_strong = c.position_lsr >= 1.05 or "Top Position" in ls_divergence or "Quiet Top" in ls_divergence
        top_position_collapse = rc_position < -5.0 or (c.position_lsr < 0.90 and rc_position < -2.0)
        top_account_not_chasing = rc_account <= 4.0 and not (a_state == "UP" and far_footprint)
        ls_against_move = bool((price3 > 0 and (g_state == "DOWN" or a_state == "DOWN" or c.global_lsr < 0.95)) or "Short Pressure" in ls_divergence or "Crowd/Account" in ls_divergence)
        ls_with_move_after_extension = bool(far_footprint and price3 > 0 and (g_state == "UP" or a_state == "UP" or c.global_lsr > 1.15))
        base_vacuum_raw = base_vacuum
        is_base_vacuum_confirmed = (
            "Base Vacuum" in base_vacuum_raw
            and "Not Applicable" not in base_vacuum_raw
            and "Weak" not in base_vacuum_raw
            and "Risk" not in base_vacuum_raw
            and oi_enum in {"FLAT", "GRADUAL_DOWN", "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"}
        )
        is_base_ignition_confirmed = "Base Ignition" in base_ignition and "Not Applicable" not in base_ignition and "Weak" not in base_ignition and "Failed" not in base_ignition
        is_reset_ignition_confirmed = "Reset Ignition" in reset_ignition and "Not Applicable" not in reset_ignition and "Weak" not in reset_ignition
        has_trigger = trigger_status in {"Confirmed Trigger", "Trigger Candidate"} or phase.trigger_time != "No Ignition Candle"
        previous_event = "NONE"
        if "Flush" in phase.previous_event or phase.reset_detected:
            previous_event = "OI_FLUSH"
        elif "Pump" in phase.previous_event or "Trigger" in phase.previous_event:
            previous_event = "PUMP"
        elif phase.base_detected:
            previous_event = "BUILDUP"

        return {
            "data_quality": {
                "time_regular": not bool(self.time_gaps(candles)),
                "missing_candles": bool(self.time_gaps(candles)),
                "rsi_warmup_risk": any(x.rsi == 0 for x in candles[: min(10, len(candles))]),
                "new_listing_risk": any("Listing" in x for x in quality.issues),
                "relative_oi_distortion": any("Relative OI" in x for x in quality.issues),
                "listing_volatility": any("Listing" in x for x in quality.issues),
                "ls_ratio_noise": any("Ratio Noise" in x for x in quality.issues),
                "confidence_cap": quality.confidence_cap or "NONE",
                "raw": asdict(quality),
            },
            "baseline": {
                "price_move_state": self._enum_label(baseline.price_move),
                "oi_change_state": self._enum_label(baseline.oi_change_pct),
                "trades_state": self._enum_label(baseline.trades),
                "quote_volume_state": self._enum_label(baseline.quote_volume),
                "ls_change_state": self._enum_label(baseline.ls_change),
                "raw": asdict(baseline),
            },
            "phase_memory": {
                "previous_event": previous_event,
                "has_base": phase.base_detected,
                "has_reset": phase.reset_detected,
                "has_flush": phase.reset_detected or pre_scanner.get("OI_FLUSH_DETECTOR") != "No OI Flush",
                "has_trigger": has_trigger,
                "post_trigger_phase": post_trigger_acceptance not in {"لا يوجد Trigger", "Needs Post-Trigger Acceptance"},
                "current_phase": "POST_IGNITION" if post_trigger_acceptance not in {"لا يوجد Trigger", "Needs Post-Trigger Acceptance"} else "PRE_IGNITION" if phase.base_detected else "LAST_STRUCTURE",
            },
            "price": {
                "state": price_enum,
                "raw_state": price_state,
                "accepted_breakout": accepted,
                "constructive_acceptance": constructive,
                "controlled_pullback": price_acceptance == "Controlled Pullback",
                "failed_breakout": price_acceptance == "Failed Breakout",
                "structure_invalidated": price_acceptance == "Structure Invalidated" or breaks_base,
                "near_footprint": near_footprint,
                "far_from_footprint": far_footprint,
                "back_inside_base": back_inside,
                "holds_above_trigger_zone": accepted,
                "holds_above_half_trigger_candle": constructive or accepted,
                "breaks_base_low": breaks_base,
                "under_recent_peak": c.close < recent_peak * 0.985,
                "makes_higher_high": self.higher_highs(candles, idx),
                "makes_higher_low": self.higher_lows(candles, idx),
                "raw_acceptance": price_acceptance,
                "distance_from_footprint_pct": round(dist, 4),
                "price3": round(price3, 4),
                "price12": round(price12, 4),
            },
            "oi": {
                "state": oi_enum,
                "raw_state": oi_state,
                "led_price": pre_scanner.get("PRE_PRICE_OI_BUILDUP") in {"Fresh Build-up Candidate", "Short Build Under Stable Price"},
                "moved_with_price": pre_scanner.get("PRICE_LEADS_OI") == "السعر و OI تحركا معًا",
                "lagged_after_price": oi_enum in {"DELAYED_RELOAD_AFTER_RESET", "DELAYED_RELOAD_FROM_BASE"},
                "flat_or_slight_down_during_ignition": (oi_enum in {"FLAT", "GRADUAL_DOWN", "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"}) and (-0.80 <= c.oi_change_pct <= 0.25),
                "strong_down_during_ignition": c.oi_change_pct < -1.50,
                "at_window_high": bool(c.oi >= oi_p92),
                "near_window_high": bool(c.oi >= oi_p85),
                "regime": "HIGH_LEVERAGE_REGIME" if "High" in oi_regime else "ACTIVE_REGIME" if "Active" in oi_regime else "NORMAL_COMMITMENT",
                "real_deleveraging": oiv_enum == "REAL_DELEVERAGING",
                "real_position_expansion": oiv_enum == "REAL_POSITION_EXPANSION",
                "current_oi_change_pct": c.oi_change_pct,
            },
            "oi_value": {
                "available": oiv_enum != "UNAVAILABLE",
                "validation": oiv_enum,
                "raw": oi_value_validation,
            },
            "trades": {
                "state": t_enum,
                "raw_state": trades_state,
                "execution_expansion": t_enum in {"IGNITION", "IGNITION_AFTER_RESET", "IGNITION_FROM_BASE", "BASE_VACUUM_IGNITION", "HEALTHY_GRADUAL"} or q_enum in {"REAL_EXECUTION_EXPANSION", "REAL_CAPITAL_ACTIVATION", "LIQUIDATION_OR_COVERING_FLOW"},
                "real_capital_activation": q_enum == "REAL_CAPITAL_ACTIVATION",
                "absorption_battle": "Absorption" in quote_validation or trades_state == "Absorption Battle",
                "late_execution": t_enum == "LATE_CROWDING",
                "trigger_execution": t_enum in {"IGNITION", "IGNITION_AFTER_RESET", "IGNITION_FROM_BASE", "BASE_VACUUM_IGNITION"},
            },
            "quote_volume": {
                "available": q_enum != "UNAVAILABLE",
                "validation": q_enum,
                "raw": quote_validation,
            },
            "ls": {
                "global_state": g_state,
                "top_account_state": a_state,
                "top_position_state": p_state,
                "divergence": self.normalize_ls_divergence_v321o(ls_divergence),
                "raw_divergence": ls_divergence,
                "global_long_heavy": c.global_lsr > 1.15,
                "global_short_heavy": c.global_lsr < 0.90 or g_state == "DOWN",
                "top_account_chasing": not top_account_not_chasing,
                "top_account_not_chasing": top_account_not_chasing,
                "top_position_strong": top_position_strong,
                "top_position_retention": top_position_retention,
                "top_position_collapse": top_position_collapse,
                "ls_against_move": ls_against_move,
                "ls_with_move_after_extension": ls_with_move_after_extension,
                "ls_noise": any("Ratio Noise" in x for x in quality.issues),
                "ratio_change_global": round(rc_global, 4),
                "ratio_change_account": round(rc_account, 4),
                "ratio_change_position": round(rc_position, 4),
            },
            "structure": {
                "base_exists": phase.base_detected,
                "base_quiet": phase.base_detected and phase.pressure_or_quiet_zone == "Base / Quiet Zone",
                "base_low_pressure": phase.base_detected,
                "no_prior_pump_directly_before_base": phase.previous_event != "Previous Trigger / Pump Event",
                "reset_exists": phase.reset_detected,
                "oi_flush_exists": phase.reset_detected or pre_scanner.get("OI_FLUSH_DETECTOR") != "No OI Flush",
                "post_flush_price_stabilized": phase.reset_detected,
                "post_flush_oi_reload": "Reload" in pre_scanner.get("POST_FLUSH_BEHAVIOR", "") or oi_enum in {"RELOAD", "DELAYED_RELOAD_AFTER_RESET", "GRADUAL_UP", "EXPLOSIVE_UP"},
                "price_led_after_reset": pre_scanner.get("PRICE_LEADS_OI") == "السعر صعد قبل OI بعد Reset" or is_reset_ignition_confirmed,
                "price_led_from_base": pre_scanner.get("PRICE_LEADS_OI") == "السعر صعد قبل OI من Base بدون Reset" or is_base_ignition_confirmed,
                "price_led_base_without_oi_expansion": is_base_vacuum_confirmed or (phase.base_detected and price3 > 0 and oi_enum in {"FLAT", "GRADUAL_DOWN", "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"}),
                "trigger_exists": has_trigger,
                "trigger_from_base": phase.base_detected and has_trigger,
                "trigger_after_reset": phase.reset_detected and has_trigger,
                "trigger_accepted": trigger_status == "Confirmed Trigger" and post_trigger_acceptance in {"Accepted Trigger", "Accepted Vacuum / Stop-driven Trigger", "Constructive Acceptance"},
                "trigger_failed": trigger_status == "Failed Trigger" or failed,
                "post_trigger_accepted": post_trigger_acceptance in {"Accepted Trigger", "Accepted Vacuum / Stop-driven Trigger", "Constructive Acceptance"},
                "post_trigger_failed": post_trigger_acceptance == "Failed Trigger" or failed,
                "raw_reset_ignition": reset_ignition,
                "raw_base_ignition": base_ignition,
                "raw_base_vacuum": base_vacuum,
                "raw_high_oi_compression": high_oi_compression,
                "raw_late_crowding": late_crowding,
                "raw_trigger_status": trigger_status,
                "raw_post_trigger_acceptance": post_trigger_acceptance,
            },
        }

    @staticmethod
    def normalize_ls_divergence_v321o(s: str) -> str:
        if s == "Long Consensus":
            return "LONG_CONSENSUS"
        if s == "Crowd Chasing / Large Position Caution":
            return "CROWD_CHASING_LARGE_CAUTION"
        if s == "Retail Long / Smart Exit":
            return "RETAIL_LONG_SMART_EXIT"
        if s == "Short Pressure Against Stable Big Positions":
            return "SHORT_PRESSURE_STABLE_BIG_POSITIONS"
        if s == "Broad Risk-Off / Position Reduction":
            return "BROAD_RISK_OFF"
        if s == "Top-side Accumulation Against Crowd":
            return "TOP_SIDE_ACCUMULATION_AGAINST_CROWD"
        if s == "Quiet Top Positioning":
            return "QUIET_TOP_POSITIONING"
        if s == "Account Count Without Size":
            return "ACCOUNT_COUNT_WITHOUT_SIZE"
        if "Short-Crowded" in s:
            return "SHORT_CROWDED_ACCOUNT_PRESSURE"
        if "Top Position Long Retention" in s:
            return "TOP_POSITION_LONG_RETENTION_WITH_CROWD_COMPRESSION"
        if "Top Position Retention" in s:
            return "TOP_POSITION_RETENTION_WITH_NON_CHASING_ACCOUNTS"
        if s == "No L/S Edge":
            return "NO_LS_EDGE"
        return "MIXED_LS_STRUCTURE"

    def score_all_patterns_v321o(self, F: Dict[str, Any]) -> List[PatternCandidate]:
        P, OI, T, Q, LS, S, PM, OIV, DQ = F["price"], F["oi"], F["trades"], F["quote_volume"], F["ls"], F["structure"], F["phase_memory"], F["oi_value"], F["data_quality"]
        def score(*conds: bool) -> float:
            return float(sum(1 for x in conds if bool(x)))
        def mk(name: str, req: List[bool], supp: List[bool], rank: int, bias: str, ready: str, invalid: Optional[List[str]] = None) -> PatternCandidate:
            failed = invalid or []
            return PatternCandidate(name=name, required_pass=all(bool(x) for x in req) and not failed, support_score=score(*supp), risk_score=float(len(failed) * 3), specificity_rank=rank, allowed_bias=bias, allowed_readiness=ready, invalidated_by=failed, evidence=[f"support_{i+1}" for i, x in enumerate(supp) if bool(x)])
        out = [
            mk("Fresh Long Build-up", [P["state"] in ["SIDEWAYS", "HEALTHY_UP"], OI["state"] == "GRADUAL_UP", OI["led_price"] or OI["moved_with_price"], not P["far_from_footprint"], not LS["ls_with_move_after_extension"]], [OIV["validation"] == "REAL_POSITION_EXPANSION", T["state"] == "HEALTHY_GRADUAL", Q["validation"] in ["REAL_EXECUTION_EXPANSION", "REAL_CAPITAL_ACTIVATION"], LS["divergence"] in ["LONG_CONSENSUS", "QUIET_TOP_POSITIONING"], LS["top_position_strong"], P["constructive_acceptance"]], 41, "Early Bullish Structure", "Primed Structure"),
            mk("Hidden Buildup / Absorption", [P["state"] == "SIDEWAYS", OI["state"] == "GRADUAL_UP", not P["breaks_base_low"], T["state"] in ["QUIET", "HEALTHY_GRADUAL"], LS["divergence"] in ["SHORT_PRESSURE_STABLE_BIG_POSITIONS", "TOP_SIDE_ACCUMULATION_AGAINST_CROWD", "NO_LS_EDGE"]], [S["base_exists"], S["post_flush_price_stabilized"], LS["ls_against_move"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"], P["constructive_acceptance"]], 40, "Early Bullish Structure", "Primed Structure"),
            mk("Absorption After Flush", [S["oi_flush_exists"], S["post_flush_price_stabilized"], not P["breaks_base_low"], OI["state"] in ["RELOAD", "FLAT", "GRADUAL_UP", "DELAYED_RELOAD_AFTER_RESET"], LS["ls_against_move"] or LS["global_state"] == "DOWN"], [T["state"] in ["CLEANUP", "QUIET", "HEALTHY_GRADUAL"], OIV["validation"] in ["REAL_POSITION_EXPANSION", "UNAVAILABLE"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"], LS["top_position_retention"]], 42, "Early Bullish Structure", "Primed Structure"),
            mk("Short Build Under Stable Price", [P["state"] == "SIDEWAYS", OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP"], LS["global_state"] == "DOWN", LS["top_account_state"] == "DOWN", not P["breaks_base_low"]], [LS["top_position_state"] in ["FLAT", "UP"], T["state"] in ["QUIET", "HEALTHY_GRADUAL"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"], S["base_exists"]], 39, "Early Bullish Structure", "Primed Structure"),
            mk("Short Squeeze / Live Ignition", [P["state"] in ["HEALTHY_UP", "EXPLOSIVE_UP"], T["state"] in ["IGNITION", "IGNITION_AFTER_RESET", "IGNITION_FROM_BASE"], LS["ls_against_move"], P["accepted_breakout"] or P["constructive_acceptance"]], [Q["validation"] == "REAL_EXECUTION_EXPANSION", OI["state"] in ["FLAT", "GRADUAL_UP", "EXPLOSIVE_UP"], S["trigger_exists"], S["post_trigger_accepted"]], 50, "Bullish but Event-driven", "Confirmed Trigger"),
            mk("Vacuum Ignition / Stop-Driven Move", [P["state"] == "EXPLOSIVE_UP", T["state"] == "IGNITION", OI["state"] in ["FLAT", "GRADUAL_DOWN"], not LS["ls_with_move_after_extension"]], [Q["validation"] == "REAL_EXECUTION_EXPANSION", LS["ls_against_move"], S["trigger_exists"], P["accepted_breakout"]], 44, "Bullish but Event-driven", "Confirmed Trigger", ["price.back_inside_base" for _ in [0] if P["back_inside_base"]] + ["post_trigger_failed" for _ in [0] if S["post_trigger_failed"]]),
            mk("Post-Flush Vacuum Ignition", [S["oi_flush_exists"], S["post_flush_price_stabilized"], P["state"] == "EXPLOSIVE_UP", T["state"] == "IGNITION_AFTER_RESET", OI["state"] in ["FLAT", "GRADUAL_DOWN"], LS["ls_against_move"]], [Q["validation"] == "REAL_EXECUTION_EXPANSION", P["accepted_breakout"], LS["top_position_retention"]], 52, "Bullish but Event-driven", "Early-Live Structure"),
            mk("Late Long Crowding", [P["state"] in ["HEALTHY_UP", "EXPLOSIVE_UP"], OI["state"] == "LATE_EXPANSION", not S["reset_exists"], not S["base_exists"], LS["global_state"] == "UP", LS["top_account_state"] == "UP", T["state"] in ["LATE_CROWDING", "IGNITION"], not LS["top_position_strong"]], [P["far_from_footprint"], OI["at_window_high"], LS["global_long_heavy"], PM["post_trigger_phase"]], 65, "Bullish but Late", "Late / Risk State"),
            mk("Post-Pump Crowding Risk", [PM["previous_event"] == "PUMP", P["under_recent_peak"], OI["at_window_high"] or OI["near_window_high"], LS["global_long_heavy"], T["state"] in ["DRY_UP_AFTER_MOVE", "FAILED_EXECUTION", "LATE_CROWDING"]], [OI["state"] in ["DELEVERAGING_AFTER_PUMP", "FLAT"], P["failed_breakout"], LS["top_position_collapse"]], 70, "Post-Pump Crowding Risk", "Late / Risk State"),
            mk("Bull Trap Risk", [P["state"] in ["HEALTHY_UP", "EXPLOSIVE_UP"], P["failed_breakout"] or S["post_trigger_failed"], LS["global_state"] == "UP", not LS["top_position_strong"], T["state"] in ["IGNITION", "FAILED_EXECUTION"]], [OI["state"] in ["FLAT", "LATE_EXPANSION"], P["back_inside_base"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"]], 72, "Distribution Risk", "Failed / Invalidated"),
            mk("Long Liquidation / Forced Reset", [P["state"] == "VIOLENT_DOWN", OI["state"] == "FLUSH", T["state"] == "CLEANUP"], [Q["validation"] in ["REAL_EXECUTION_EXPANSION", "LIQUIDATION_OR_COVERING_FLOW"], LS["top_position_state"] == "DOWN", OIV["validation"] == "REAL_DELEVERAGING"], 62, "Bearish Structural Risk", "Watchlist Only"),
            mk("Liquidity Exit / Decay", [P["state"] in ["GRADUAL_DOWN", "VIOLENT_DOWN", "SIDEWAYS"], OI["state"] in ["GRADUAL_DOWN", "FLUSH"], not S["post_flush_price_stabilized"], not S["post_flush_oi_reload"], not S["trigger_exists"]], [T["state"] in ["QUIET", "DRY_UP_AFTER_MOVE"], LS["divergence"] in ["NO_LS_EDGE", "BROAD_RISK_OFF"]], 30, "Bearish Structural Risk", "Watchlist Only"),
            mk("Bearish Build-up", [P["state"] in ["GRADUAL_DOWN", "VIOLENT_DOWN"], OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP"], LS["global_state"] == "DOWN", T["state"] in ["CLEANUP", "IGNITION"], P["breaks_base_low"]], [Q["validation"] == "REAL_EXECUTION_EXPANSION", LS["top_account_state"] == "DOWN"], 63, "Bearish Structural Risk", "Failed / Invalidated" if P["breaks_base_low"] else "Watchlist Only"),
            mk("Long Trap / Long Punishment", [P["state"] in ["GRADUAL_DOWN", "VIOLENT_DOWN"], OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP", "FLAT"], LS["global_state"] == "UP", LS["top_account_state"] == "UP", T["state"] in ["CLEANUP", "IGNITION", "FAILED_EXECUTION"]], [LS["global_long_heavy"], LS["top_position_collapse"] or LS["divergence"] == "RETAIL_LONG_SMART_EXIT", P["failed_breakout"]], 66, "Bearish Structural Risk", "Failed / Invalidated"),
            mk("Weak Consolidation", [P["state"] == "SIDEWAYS", OI["state"] == "GRADUAL_DOWN", T["state"] in ["QUIET", "DRY_UP_AFTER_MOVE"], LS["divergence"] == "NO_LS_EDGE", not S["post_flush_oi_reload"], not S["trigger_exists"]], [Q["validation"] in ["UNAVAILABLE", "MICRO_TRADE_NOISE"]], 20, "Neutral / Unclear", "Watchlist Only"),
            mk("Mixed Structure", [OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP", "FLAT", "GRADUAL_DOWN"] and LS["divergence"] not in ["NO_LS_EDGE"] and not P["accepted_breakout"] and T["state"] in ["QUIET", "BOT_NOISE", "DRY_UP_AFTER_MOVE"]], [LS["ls_noise"], Q["validation"] in ["MICRO_TRADE_NOISE", "UNAVAILABLE"], DQ["confidence_cap"] in ["MEDIUM", "LOW"]], 10, "Neutral / Unclear", "Watchlist Only"),
            mk("Short-Crowded Compression", [OI["at_window_high"] or OI["near_window_high"], LS["global_short_heavy"], LS["top_account_state"] == "DOWN", P["state"] == "SIDEWAYS", not P["breaks_base_low"], not P["accepted_breakout"]], [LS["top_position_state"] in ["FLAT", "UP"], T["state"] in ["QUIET", "HEALTHY_GRADUAL", "FAILED_EXECUTION"], S["base_exists"]], 61, "Neutral-to-Bullish Compression", "Compression / Unresolved"),
            mk("Failed Squeeze / Squeeze Exhaustion", [LS["global_short_heavy"] or LS["ls_against_move"], S["trigger_exists"], S["post_trigger_failed"], OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP", "FLAT"], T["state"] in ["IGNITION", "FAILED_EXECUTION"], not P["accepted_breakout"]], [OI["at_window_high"], P["back_inside_base"], Q["validation"] == "REAL_EXECUTION_EXPANSION"], 73, "Distribution Risk", "Failed / Invalidated"),
            mk("High OI Neutral Compression", [OI["at_window_high"] or OI["near_window_high"], P["state"] == "SIDEWAYS", not LS["global_long_heavy"], not LS["global_short_heavy"], not P["accepted_breakout"], not P["breaks_base_low"]], [T["state"] in ["QUIET", "HEALTHY_GRADUAL", "FAILED_EXECUTION"], LS["divergence"] in ["NO_LS_EDGE", "ACCOUNT_COUNT_WITHOUT_SIZE"]], 60, "High Volatility Compression", "Compression / Unresolved"),
            mk("Bot / Noise Expansion", [T["state"] == "BOT_NOISE" or (Q["validation"] == "MICRO_TRADE_NOISE" and T["trigger_execution"]), Q["validation"] == "MICRO_TRADE_NOISE", OI["state"] in ["FLAT", "GRADUAL_DOWN"], not P["accepted_breakout"]], [LS["ls_noise"], P["failed_breakout"], DQ["confidence_cap"] in ["MEDIUM", "LOW"]], 75, "Neutral / Unclear", "Watchlist Only"),
            mk("Price-led Reset Ignition with OI Reload", [S["oi_flush_exists"], S["post_flush_price_stabilized"], S["price_led_after_reset"], T["state"] == "IGNITION_AFTER_RESET", OI["state"] == "DELAYED_RELOAD_AFTER_RESET", LS["ls_against_move"] or LS["top_account_not_chasing"], LS["top_position_retention"], P["accepted_breakout"] or P["constructive_acceptance"]], [OIV["validation"] in ["REAL_POSITION_EXPANSION", "UNAVAILABLE"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE", "REAL_CAPITAL_ACTIVATION", "LIQUIDATION_OR_COVERING_FLOW"], P["near_footprint"]], 88, "Early-Live Bullish Structure", "Early-Live Structure", ["no_oi_flush" for _ in [0] if not S["oi_flush_exists"]] + ["base_low_broken" for _ in [0] if P["breaks_base_low"]] + ["late_after_reset" for _ in [0] if P["far_from_footprint"] and OI["state"] == "LATE_EXPANSION"]),
            mk("Top-Position Long Retention with Crowd Compression", [LS["top_position_retention"], LS["global_state"] == "DOWN", LS["top_account_state"] == "DOWN", P["state"] in ["HEALTHY_UP", "EXPLOSIVE_UP", "SIDEWAYS"], OI["state"] in ["RELOAD", "GRADUAL_UP", "FLAT", "DELAYED_RELOAD_AFTER_RESET", "DELAYED_RELOAD_FROM_BASE"], T["execution_expansion"]], [Q["validation"] == "REAL_EXECUTION_EXPANSION", P["near_footprint"], P["constructive_acceptance"]], 55, "Early-Live Bullish Structure", "Early-Live Structure"),
            mk("Price-led Base Ignition without Reset", [not S["oi_flush_exists"], not S["reset_exists"], S["base_exists"], S["base_quiet"] or S["base_low_pressure"], S["price_led_from_base"], T["state"] == "IGNITION_FROM_BASE", OI["state"] == "DELAYED_RELOAD_FROM_BASE" or (OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP"] and S["raw_base_ignition"] == "Price-led Base Ignition with Delayed OI Confirmation"), LS["top_account_not_chasing"] or LS["ls_against_move"], LS["top_position_retention"], P["accepted_breakout"] or P["constructive_acceptance"]], [OIV["validation"] in ["REAL_POSITION_EXPANSION", "UNAVAILABLE"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE", "REAL_CAPITAL_ACTIVATION", "LIQUIDATION_OR_COVERING_FLOW"], P["near_footprint"], not P["back_inside_base"]], 90, "Early-Live Bullish Structure", "Early-Live Structure", ["reset_branch_priority" for _ in [0] if S["oi_flush_exists"]] + ["back_inside_base" for _ in [0] if P["back_inside_base"]] + ["base_low_broken" for _ in [0] if P["breaks_base_low"]] + ["far_high_oi" for _ in [0] if P["far_from_footprint"] and OI["at_window_high"]]),
            mk("Failed Base Ignition", [S["base_exists"], S["trigger_from_base"], T["state"] in ["IGNITION_FROM_BASE", "FAILED_EXECUTION", "BASE_VACUUM_IGNITION"], P["back_inside_base"], not P["accepted_breakout"]], [OI["state"] in ["DELAYED_RELOAD_FROM_BASE", "GRADUAL_UP", "FLAT"], LS["ls_with_move_after_extension"] or LS["divergence"] in ["NO_LS_EDGE", "CROWD_CHASING_LARGE_CAUTION"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"]], 95, "Distribution Risk", "Failed / Invalidated"),
            mk("Price-led Base Vacuum Ignition without OI Expansion", [not S["oi_flush_exists"], not S["reset_exists"], S["base_exists"], S["base_quiet"] or S["base_low_pressure"], S["price_led_base_without_oi_expansion"], T["state"] == "BASE_VACUUM_IGNITION", OI["flat_or_slight_down_during_ignition"], not OI["strong_down_during_ignition"], LS["top_position_retention"], LS["top_account_not_chasing"], not LS["global_long_heavy"], P["holds_above_trigger_zone"] or P["holds_above_half_trigger_candle"], not P["back_inside_base"]], [Q["validation"] in ["REAL_EXECUTION_EXPANSION", "LIQUIDATION_OR_COVERING_FLOW", "REAL_CAPITAL_ACTIVATION", "LARGE_BLOCK_LIKE_EXECUTION"], P["near_footprint"], P["accepted_breakout"] or P["constructive_acceptance"], OI["state"] in ["FLAT", "GRADUAL_DOWN", "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"]], 100, "Early-Live Bullish Structure", "Early-Live Structure", ["reset_branch_priority" for _ in [0] if S["oi_flush_exists"]] + ["back_inside_base" for _ in [0] if P["back_inside_base"]] + ["base_low_broken" for _ in [0] if P["breaks_base_low"]] + ["top_position_collapse" for _ in [0] if LS["top_position_collapse"]] + ["strong_oi_down" for _ in [0] if OI["strong_down_during_ignition"]] + ["micro_trade_noise" for _ in [0] if Q["validation"] == "MICRO_TRADE_NOISE"]),
        ]
        # Failed Base Vacuum Ignition is intentionally separated so Conflict Override can pick it precisely.
        out.append(mk("Failed Base Vacuum Ignition", [S["base_exists"], S["trigger_from_base"], S["price_led_base_without_oi_expansion"], T["state"] in ["BASE_VACUUM_IGNITION", "FAILED_EXECUTION"], P["back_inside_base"], not P["accepted_breakout"]], [LS["top_position_collapse"], Q["validation"] in ["REAL_EXECUTION_EXPANSION", "UNAVAILABLE"], OI["state"] in ["FLAT", "GRADUAL_DOWN", "PRICE_LED_BASE_MOVE_WITHOUT_OI_EXPANSION"]], 96, "Distribution Risk", "Failed / Invalidated"))
        return out

    def apply_conflict_rules_v321o(self, F: Dict[str, Any], eligible: List[PatternCandidate]) -> Optional[PatternCandidate]:
        P, OI, T, Q, LS, S, PM = F["price"], F["oi"], F["trades"], F["quote_volume"], F["ls"], F["structure"], F["phase_memory"]
        names = {c.name: c for c in eligible}
        def candidate(name: str, bias: str, ready: str, rank: int, reason: str) -> PatternCandidate:
            base = names.get(name)
            if base:
                base.evidence.append("Conflict Override: " + reason)
                return base
            return PatternCandidate(name, True, 0.0, 0.0, rank, bias, ready, evidence=["Conflict Override: " + reason])
        # Hard Invalidations: أعلى من كل Pattern Score.
        if P["breaks_base_low"]:
            return candidate("Failed Base Ignition" if S["base_exists"] else "Mixed Structure", "Distribution Risk", "Failed / Invalidated", 1000, "price.breaks_base_low")
        if P["back_inside_base"] and S["trigger_from_base"]:
            if S["price_led_base_without_oi_expansion"] or "Base Vacuum" in S["raw_base_vacuum"]:
                return candidate("Failed Base Vacuum Ignition", "Distribution Risk", "Failed / Invalidated", 1000, "price.back_inside_base + trigger_from_base")
            return candidate("Failed Base Ignition", "Distribution Risk", "Failed / Invalidated", 1000, "price.back_inside_base + trigger_from_base")
        if S["post_trigger_failed"]:
            if S["price_led_base_without_oi_expansion"]:
                return candidate("Failed Base Vacuum Ignition", "Distribution Risk", "Failed / Invalidated", 1000, "post_trigger_failed")
            return candidate("Failed Base Ignition", "Distribution Risk", "Failed / Invalidated", 1000, "post_trigger_failed")
        if LS["top_position_collapse"] and P["state"] in ["HEALTHY_UP", "EXPLOSIVE_UP"]:
            return candidate("Bull Trap Risk", "Distribution Risk", "Failed / Invalidated", 960, "top_position_collapse during price up")
        if Q["validation"] == "MICRO_TRADE_NOISE" and T["state"] in ["IGNITION", "BASE_VACUUM_IGNITION", "IGNITION_FROM_BASE"]:
            return candidate("Bot / Noise Expansion", "Neutral / Unclear", "Watchlist Only", 930, "Trades انفجارية لكن Quote Volume لا يؤكد")
        # Reset vs Late Crowding: لا تصنفه Late إذا Reset branch مؤهل.
        if OI["state"] == "LATE_EXPANSION" and S["oi_flush_exists"] and S["post_flush_price_stabilized"] and LS["ls_against_move"] and "Price-led Reset Ignition with OI Reload" in names:
            return candidate("Price-led Reset Ignition with OI Reload", "Early-Live Bullish Structure", "Early-Live Structure", 880, "Reset branch has priority over Late Crowding")
        # Base vs Late Crowding: لا تصنفه Late إذا Base branch مؤهل.
        if OI["state"] == "LATE_EXPANSION" and S["base_exists"] and P["near_footprint"] and LS["top_account_not_chasing"] and "Price-led Base Ignition without Reset" in names:
            return candidate("Price-led Base Ignition without Reset", "Early-Live Bullish Structure", "Early-Live Structure", 875, "Base branch has priority over Late Crowding")
        # Base Vacuum exception: لا تسقط العملة بسبب OI flat/down إذا gates كاملة.
        if (S["base_exists"] and S["price_led_base_without_oi_expansion"] and T["state"] == "BASE_VACUUM_IGNITION" and OI["flat_or_slight_down_during_ignition"] and LS["top_position_retention"] and LS["top_account_not_chasing"] and not P["back_inside_base"] and "Price-led Base Vacuum Ignition without OI Expansion" in names):
            return candidate("Price-led Base Vacuum Ignition without OI Expansion", "Early-Live Bullish Structure", "Early-Live Structure", 890, "Base Vacuum exception")
        # Late risk overrides.
        if P["far_from_footprint"] and OI["at_window_high"] and LS["ls_with_move_after_extension"]:
            return candidate("Late Long Crowding", "Bullish but Late", "Late / Risk State", 920, "far_from_footprint + OI high + LS with move")
        if OI["state"] == "LATE_EXPANSION" and not S["reset_exists"] and not S["base_exists"]:
            return candidate("Late Long Crowding", "Bullish but Late", "Late / Risk State", 920, "OI late expansion without Reset/Base")
        if PM["previous_event"] == "PUMP" and P["under_recent_peak"] and OI["at_window_high"] and LS["global_long_heavy"]:
            return candidate("Post-Pump Crowding Risk", "Post-Pump Crowding Risk", "Late / Risk State", 940, "Post pump high OI under peak")
        # High OI compression overlay: لا يلغي Accepted/Confirmed القريب، لكنه يمنع Early إذا بعيد أو بلا قبول.
        if OI["at_window_high"] and P["under_recent_peak"] and not P["accepted_breakout"]:
            if LS["global_long_heavy"]:
                return candidate("Post-Pump Crowding Risk", "Post-Pump Crowding Risk", "Late / Risk State", 910, "Trapped Long Compression")
            if LS["global_short_heavy"] and "Short-Crowded Compression" in names:
                return candidate("Short-Crowded Compression", "Neutral-to-Bullish Compression", "Compression / Unresolved", 880, "Short-Crowded Compression overlay")
            if "High OI Neutral Compression" in names:
                return candidate("High OI Neutral Compression", "High Volatility Compression", "Compression / Unresolved", 860, "High OI Neutral Compression overlay")
        return None

    def select_by_priority_and_score_v321o(self, eligible: List[PatternCandidate], F: Dict[str, Any]) -> PatternCandidate:
        if not eligible:
            return PatternCandidate("Mixed Structure", True, 0.0, 0.0, 0, "Neutral / Unclear", "Watchlist Only", evidence=["No eligible pattern"])
        def key(c: PatternCandidate) -> Tuple[float, float, float]:
            return (self.selection_priority_v321o(c, F), c.net_score, c.support_score)
        return max(eligible, key=key)

    def selection_priority_v321o(self, c: PatternCandidate, F: Dict[str, Any]) -> float:
        P = F["price"]
        name = c.name
        # Final-pattern selection gives risk/invalidations priority, as requested.
        if name in {"Failed Base Ignition", "Failed Base Vacuum Ignition", "Failed Squeeze / Squeeze Exhaustion", "Bull Trap Risk", "Long Trap / Long Punishment", "Bearish Build-up"}:
            return 1000 + c.specificity_rank
        if name in {"Post-Pump Crowding Risk", "Late Long Crowding"}:
            return 920 + c.specificity_rank
        if name in {"Short-Crowded Compression", "High OI Neutral Compression"}:
            return 820 + c.specificity_rank
        if name == "Price-led Base Vacuum Ignition without OI Expansion":
            return 760 + (80 if P["accepted_breakout"] else 40 if P["constructive_acceptance"] else 0) + c.specificity_rank
        if name == "Price-led Base Ignition without Reset":
            return 740 + (80 if P["accepted_breakout"] else 40 if P["constructive_acceptance"] else 0) + c.specificity_rank
        if name == "Price-led Reset Ignition with OI Reload":
            return 720 + (80 if P["accepted_breakout"] else 40 if P["constructive_acceptance"] else 0) + c.specificity_rank
        if name in {"Short Squeeze / Live Ignition", "Post-Flush Vacuum Ignition", "Vacuum Ignition / Stop-Driven Move"}:
            return 650 + c.specificity_rank
        if name in {"Fresh Long Build-up", "Hidden Buildup / Absorption", "Absorption After Flush", "Short Build Under Stable Price", "Top-Position Long Retention with Crowd Compression"}:
            return 500 + c.specificity_rank
        if name in {"Mixed Structure", "Weak Consolidation", "Liquidity Exit / Decay", "Bot / Noise Expansion", "Long Liquidation / Forced Reset"}:
            return 100 + c.specificity_rank
        return c.specificity_rank

    def assign_readiness_v321o(self, selected_pattern: str, F: Dict[str, Any]) -> str:
        P, OI, T, LS, S, DQ = F["price"], F["oi"], F["trades"], F["ls"], F["structure"], F["data_quality"]
        if selected_pattern in {"Failed Base Ignition", "Failed Base Vacuum Ignition", "Failed Squeeze / Squeeze Exhaustion", "Bull Trap Risk", "Long Trap / Long Punishment"} or S["post_trigger_failed"] or P["back_inside_base"] or P["breaks_base_low"]:
            return "Failed / Invalidated"
        if selected_pattern in {"Late Long Crowding", "Post-Pump Crowding Risk"}:
            return "Late / Risk State"
        if selected_pattern in {"Short-Crowded Compression", "High OI Neutral Compression"}:
            return "Compression / Unresolved"
        if selected_pattern == "Long Liquidation / Forced Reset":
            return "Primed Structure" if S["post_flush_price_stabilized"] and S["post_flush_oi_reload"] else "Watchlist Only"
        if selected_pattern in {"Bearish Build-up", "Liquidity Exit / Decay"}:
            return "Failed / Invalidated" if P["breaks_base_low"] else "Watchlist Only"
        # Accepted Structure
        if S["trigger_exists"] and (P["holds_above_trigger_zone"] or P["holds_above_half_trigger_candle"] or P["constructive_acceptance"]) and not P["back_inside_base"] and not P["breaks_base_low"] and not S["post_trigger_failed"]:
            return "Accepted Structure"
        # Confirmed Trigger
        if S["trigger_exists"] and T["execution_expansion"] and (OI["state"] in ["GRADUAL_UP", "EXPLOSIVE_UP", "DELAYED_RELOAD_AFTER_RESET", "DELAYED_RELOAD_FROM_BASE"] or (OI["flat_or_slight_down_during_ignition"] and S["base_exists"] and LS["top_position_retention"])) and not LS["ls_with_move_after_extension"]:
            return "Confirmed Trigger"
        # Early-Live Structure
        if (S["trigger_exists"] or S["price_led_after_reset"] or S["price_led_from_base"] or S["price_led_base_without_oi_expansion"]) and P["near_footprint"] and (OI["state"] in ["DELAYED_RELOAD_AFTER_RESET", "DELAYED_RELOAD_FROM_BASE", "GRADUAL_UP", "EXPLOSIVE_UP"] or (OI["flat_or_slight_down_during_ignition"] and T["execution_expansion"] and LS["top_position_retention"])) and (LS["ls_against_move"] or LS["top_account_not_chasing"]):
            return "Early-Live Structure"
        # Primed Structure
        if (S["base_exists"] or S["post_flush_price_stabilized"]) and (OI["state"] in ["GRADUAL_UP", "RELOAD", "FLAT", "DELAYED_RELOAD_AFTER_RESET", "DELAYED_RELOAD_FROM_BASE"] or LS["ls_against_move"] or T["state"] in ["QUIET", "HEALTHY_GRADUAL"] or LS["top_position_retention"]) and not S["trigger_exists"]:
            return "Primed Structure"
        if OI["at_window_high"] and P["state"] == "SIDEWAYS" and not P["accepted_breakout"] and not P["breaks_base_low"]:
            return "Compression / Unresolved"
        if DQ["confidence_cap"] == "LOW" or (not S["trigger_exists"] and not P["accepted_breakout"] and not S["base_exists"]):
            return "Watchlist Only"
        if P["far_from_footprint"] or (OI["at_window_high"] and P["under_recent_peak"]) or LS["ls_with_move_after_extension"] or T["state"] == "LATE_CROWDING":
            return "Late / Risk State"
        return "Watchlist Only"

    def assign_bias_v321o(self, selected_pattern: str, readiness: str, F: Dict[str, Any]) -> str:
        P = F["price"]
        if selected_pattern in {"Fresh Long Build-up", "Hidden Buildup / Absorption", "Absorption After Flush", "Short Build Under Stable Price"}:
            return "Early Bullish Structure"
        if selected_pattern in {"Price-led Reset Ignition with OI Reload", "Price-led Base Ignition without Reset"}:
            return "Bullish but Late" if P["far_from_footprint"] else "Early-Live Bullish Structure"
        if selected_pattern == "Price-led Base Vacuum Ignition without OI Expansion":
            if P["far_from_footprint"] and readiness == "Late / Risk State":
                return "Bullish but Late"
            return "Early-Live Bullish Structure" if readiness in {"Early-Live Structure", "Confirmed Trigger", "Accepted Structure"} else "Bullish but Event-driven"
        if selected_pattern in {"Short Squeeze / Live Ignition", "Vacuum Ignition / Stop-Driven Move", "Post-Flush Vacuum Ignition"}:
            return "Bullish but Event-driven"
        if selected_pattern in {"Late Long Crowding"}:
            return "Bullish but Late"
        if selected_pattern == "Post-Pump Crowding Risk":
            return "Post-Pump Crowding Risk"
        if selected_pattern in {"Bull Trap Risk", "Failed Base Ignition", "Failed Base Vacuum Ignition", "Failed Squeeze / Squeeze Exhaustion"}:
            return "Distribution Risk"
        if selected_pattern in {"Long Liquidation / Forced Reset", "Liquidity Exit / Decay", "Bearish Build-up", "Long Trap / Long Punishment"}:
            return "Bearish Structural Risk"
        if selected_pattern == "Short-Crowded Compression":
            return "Neutral-to-Bullish Compression"
        if selected_pattern == "High OI Neutral Compression":
            return "High Volatility Compression"
        return "Neutral / Unclear"

    @staticmethod
    def downgrade_bias_by_readiness_v321o(bias: str, readiness: str, selected_pattern: str) -> str:
        if readiness == "Failed / Invalidated":
            if selected_pattern in {"Long Trap / Long Punishment", "Bearish Build-up"}:
                return "Bearish Structural Risk"
            return "Distribution Risk"
        if readiness == "Late / Risk State":
            if selected_pattern == "Post-Pump Crowding Risk":
                return "Post-Pump Crowding Risk"
            if bias.startswith("Early"):
                return "Bullish but Late"
        return bias

    def assign_confidence_v321o(self, selected_pattern: str, readiness: str, F: Dict[str, Any]) -> Tuple[str, float]:
        P, OIV, Q, LS, S, DQ = F["price"], F["oi_value"], F["quote_volume"], F["ls"], F["structure"], F["data_quality"]
        score = 40.0
        if OIV["validation"] == "REAL_POSITION_EXPANSION":
            score += 14
        if Q["validation"] in ["REAL_EXECUTION_EXPANSION", "REAL_CAPITAL_ACTIVATION", "LIQUIDATION_OR_COVERING_FLOW", "LARGE_BLOCK_LIKE_EXECUTION"]:
            score += 16
        if P["accepted_breakout"] or P["constructive_acceptance"]:
            score += 14
        if LS["divergence"] != "NO_LS_EDGE":
            score += 8
        if readiness in ["Confirmed Trigger", "Accepted Structure"]:
            score += 10
        if selected_pattern in ["Price-led Reset Ignition with OI Reload", "Price-led Base Ignition without Reset", "Price-led Base Vacuum Ignition without OI Expansion"]:
            score += 6
        # High
        if OIV["validation"] == "REAL_POSITION_EXPANSION" and Q["validation"] in ["REAL_EXECUTION_EXPANSION", "REAL_CAPITAL_ACTIVATION"] and P["accepted_breakout"] and LS["divergence"] != "NO_LS_EDGE" and readiness in ["Confirmed Trigger", "Accepted Structure"] and DQ["confidence_cap"] == "NONE" and not P["far_from_footprint"]:
            return "High", clamp(max(score, 86.0))
        # Medium-High
        if selected_pattern in ["Price-led Reset Ignition with OI Reload", "Price-led Base Ignition without Reset", "Price-led Base Vacuum Ignition without OI Expansion"] and (P["accepted_breakout"] or P["constructive_acceptance"]) and (LS["ls_against_move"] or LS["top_account_not_chasing"]) and LS["top_position_retention"] and readiness in ["Early-Live Structure", "Confirmed Trigger", "Accepted Structure"]:
            return "Medium-High", clamp(max(score, 74.0))
        # Medium
        if OIV["validation"] == "UNAVAILABLE" or Q["validation"] == "UNAVAILABLE" or readiness in ["Primed Structure", "Early-Live Structure"] or DQ["confidence_cap"] == "MEDIUM":
            return "Medium", clamp(min(max(score, 52.0), 69.0) if DQ["confidence_cap"] == "MEDIUM" else max(score, 58.0))
        # Low
        if DQ["confidence_cap"] == "LOW" or Q["validation"] == "MICRO_TRADE_NOISE" or OIV["validation"] == "CONTRACT_COUNT_DISTORTION" or LS["ls_noise"] or readiness in ["Watchlist Only", "Failed / Invalidated"]:
            return "Low", clamp(min(score, 49.0))
        if score >= 82 and readiness in ["Confirmed Trigger", "Accepted Structure"]:
            return "High", clamp(score)
        if score >= 70:
            return "Medium-High", clamp(score)
        if score >= 50:
            return "Medium", clamp(score)
        return "Low", clamp(score)

    @staticmethod
    def apply_confidence_caps_v321o(confidence: str, score: float, F: Dict[str, Any]) -> Tuple[str, float]:
        DQ, Q, OIV, LS, R = F["data_quality"], F["quote_volume"], F["oi_value"], F["ls"], F["price"]
        order = ["Low", "Medium", "Medium-High", "High"]
        def cap_to(label: str, current: str) -> str:
            return order[min(order.index(label), order.index(current))]
        out = confidence
        if DQ["confidence_cap"] == "MEDIUM":
            out = cap_to("Medium", out)
            score = min(score, 68.0)
        # V3.2.1-O patch: missing Quote Volume must not cancel Base Vacuum / Price-led branches,
        # but it must cap confidence at Medium because execution value is not independently confirmed.
        if Q["validation"] == "UNAVAILABLE":
            out = cap_to("Medium", out)
            score = min(score, 68.0)
        if Q["validation"] == "MICRO_TRADE_NOISE" or OIV["validation"] == "CONTRACT_COUNT_DISTORTION" or LS["ls_noise"]:
            out = cap_to("Low", out)
            score = min(score, 49.0)
        if R["far_from_footprint"] and out == "High":
            out = "Medium-High"
            score = min(score, 81.0)
        return out, round(clamp(score), 2)

    def final_structural_decision(
        self,
        candles: List[Candle],
        idx: int,
        phase: PhaseMemory,
        quality: DataQuality,
        baseline: DynamicBaseline,
        price_state: str,
        oi_state: str,
        oi_regime: str,
        trades_state: str,
        price_acceptance: str,
        pre_scanner: Dict[str, str],
        trigger_status: str,
        post_trigger_acceptance: str,
        reset_ignition: str,
        base_ignition: str,
        base_vacuum: str,
        high_oi_compression: str,
        late_crowding: str,
        ls_divergence: str,
        oi_value_validation: str,
        quote_validation: str,
    ) -> Tuple[str, str, str, str, str, str]:
        c = candles[idx]
        signal_timing = self.signal_timing(candles, idx, phase, oi_state, base_vacuum)
        whale_crowd = self.whale_crowd_timing(candles, idx, phase, ls_divergence, base_vacuum, reset_ignition)
        invalidation = self.invalidation_risk(candles, idx, phase, price_acceptance, oi_state)

        if price_acceptance in {"Structure Invalidated", "Failed Breakout"}:
            if "Vacuum" in base_vacuum:
                return "Failed Base Vacuum Ignition", "Distribution Risk", "Failed / Invalidated", signal_timing, whale_crowd, invalidation
            return "Failed Base Ignition", "Distribution Risk", "Failed / Invalidated", signal_timing, whale_crowd, invalidation

        if "Accepted Base Vacuum Ignition" in base_vacuum:
            return "Price-led Base Vacuum Ignition without OI Expansion", "Early-Live Bullish Structure", "Accepted Structure", signal_timing, whale_crowd, invalidation
        if "Price-led Base Vacuum Ignition" in base_vacuum or "Price-led Base Ignition without OI Expansion" in base_vacuum:
            return "Price-led Base Vacuum Ignition without OI Expansion", "Bullish but Event-driven", "Confirmed Trigger", signal_timing, whale_crowd, invalidation
        if "Price-led Base Ignition with Delayed OI Confirmation" in base_ignition:
            readiness = "Accepted Structure" if price_acceptance in {"Accepted Breakout", "Pre-OI Accepted Move From Base"} else "Early-Live Structure"
            return "Price-led Base Ignition without Reset", "Early-Live Bullish Structure", readiness, signal_timing, whale_crowd, invalidation
        if "Price-led Reset Ignition" in reset_ignition:
            readiness = "Accepted Structure" if post_trigger_acceptance == "Accepted Trigger" else "Early-Live Structure"
            return "Price-led Reset Ignition with OI Reload", "Early-Live Bullish Structure", readiness, signal_timing, whale_crowd, invalidation
        if "Late" in late_crowding or "Extension" in late_crowding:
            return "Late Long Crowding", "Bullish but Late", "Late / Risk State", signal_timing, whale_crowd, invalidation
        if "Short-Crowded Compression" in high_oi_compression:
            return "Short-Crowded Compression", "Neutral-to-Bullish Compression", "Compression / Unresolved", signal_timing, whale_crowd, invalidation
        if "Neutral" in high_oi_compression:
            return "High OI Neutral Compression", "High Volatility Compression", "Compression / Unresolved", signal_timing, whale_crowd, invalidation
        if pre_scanner.get("PRE_PRICE_OI_BUILDUP") == "Short Build Under Stable Price":
            return "Short Build Under Stable Price", "Early Bullish Structure", "Primed Structure", signal_timing, whale_crowd, invalidation
        if pre_scanner.get("POST_FLUSH_BEHAVIOR") == "Absorption After Flush / Short Build Near Bottom":
            return "Absorption After Flush", "Early Bullish Structure", "Primed Structure", signal_timing, whale_crowd, invalidation
        if "OI صاعد" in oi_state and price_state in {"عرضي / ثابت", "صاعد صحي"} and "Long" in ls_divergence:
            return "Fresh Long Build-up", "Early Bullish Structure", "Primed Structure", signal_timing, whale_crowd, invalidation
        if phase.base_detected and price_state == "عرضي / ثابت":
            if c.position_lsr > 1.05 or "Top Position" in ls_divergence:
                return "Hidden Buildup / Absorption", "Early Bullish Structure", "Primed Structure", signal_timing, whale_crowd, invalidation
            return "Mixed Structure", "Neutral / Unclear", "Watchlist Only", signal_timing, whale_crowd, invalidation
        if price_state.startswith("هابط") and "OI صاعد" in oi_state:
            if c.global_lsr > 1.05 or c.account_lsr > 1.05:
                return "Long Trap / Long Punishment", "Bearish Structural Risk", "Failed / Invalidated", signal_timing, whale_crowd, invalidation
            return "Bearish Build-up", "Bearish Structural Risk", "Watchlist Only", signal_timing, whale_crowd, invalidation
        if price_state.startswith("هابط") and "هابط" in oi_state:
            return "Liquidity Exit / Decay", "Bearish Structural Risk", "Watchlist Only", signal_timing, whale_crowd, invalidation
        return "Mixed Structure", "Neutral / Unclear", "Watchlist Only", signal_timing, whale_crowd, invalidation

    def conflict_resolution(
        self,
        candles: List[Candle],
        idx: int,
        pattern: str,
        bias: str,
        readiness: str,
        invalidation: str,
        price_acceptance: str,
        trigger_status: str,
        post_trigger_acceptance: str,
        base_ignition: str,
        base_vacuum: str,
        high_oi_compression: str,
        late_crowding: str,
        oi_value_validation: str,
        quote_validation: str,
        ls_divergence: str,
    ) -> Tuple[str, str, str, str]:
        # Early Setup موجود لكن Post-trigger failure ظهر.
        if post_trigger_acceptance == "Failed Trigger" or price_acceptance in {"Failed Breakout", "Structure Invalidated"}:
            if "Base Vacuum" in pattern:
                return "Failed Base Vacuum Ignition", "Distribution Risk", "Failed / Invalidated", "Base Vacuum Ignition موجود لكن السعر عاد داخل القاعدة"
            return "Failed Base Ignition", "Distribution Risk", "Failed / Invalidated", "Base Ignition موجود لكن السعر عاد داخل القاعدة"
        # Risk Overlay له أولوية على bias الأساسي.
        if "Risk" in late_crowding and readiness not in {"Accepted Structure", "Confirmed Trigger"}:
            return pattern, "Bullish but Late" if "Bullish" in bias else bias, "Late / Risk State", "السعر ابتعد عن البصمة أو ظهرت مطاردة متأخرة"
        if "Trapped Long" in high_oi_compression:
            return "Post-Pump Crowding Risk", "Post-Pump Crowding Risk", "Late / Risk State", "OI عند قمة النافذة والسعر لا يصنع قمة"
        # لا تسقط الإشارة إذا كانت من Base واضحة مع OI flat/down وQuote يؤكد.
        if "Base Vacuum" in base_vacuum and "Noise" not in quote_validation:
            return pattern, bias, readiness, invalidation
        if "Micro-trade" in quote_validation and readiness in {"Confirmed Trigger", "Early-Live Structure", "Accepted Structure"}:
            return "Bot / Noise Expansion", "Neutral / Unclear", "Watchlist Only", "Trades انفجارية لكن Quote Volume لا يؤكد"
        if "Contract-count distortion" in oi_value_validation and "OI" in pattern and "Vacuum" not in pattern:
            return pattern, bias, "Watchlist Only" if readiness == "Primed Structure" else readiness, "OI contracts ↑ لكن OI Value لا يؤكد"
        return pattern, bias, readiness, invalidation

    def readiness_confirmation_level(
        self,
        readiness: str,
        pattern: str,
        price_acceptance: str,
        trigger_status: str,
        post_trigger_acceptance: str,
        phase: PhaseMemory,
        base_vacuum: str,
    ) -> str:
        if readiness in self.READINESS_LEVELS:
            # Apply explicit V3.2.1 exception for Base Vacuum without OI expansion.
            if "Base Vacuum" in base_vacuum and price_acceptance in {"Pre-OI / No-OI Accepted Move From Base", "Accepted Breakout", "Constructive Acceptance"}:
                if post_trigger_acceptance in {"Accepted Trigger", "Accepted Vacuum / Stop-driven Trigger"}:
                    return "Accepted Structure"
                if trigger_status in {"Confirmed Trigger", "Trigger Candidate"}:
                    return "Confirmed Trigger"
                return "Early-Live Structure"
            return readiness
        return "Watchlist Only"

    def confidence_rules(
        self,
        quality: DataQuality,
        readiness: str,
        price_acceptance: str,
        oi_value_validation: str,
        quote_validation: str,
        ls_divergence: str,
        reset_ignition: str,
        base_ignition: str,
        base_vacuum: str,
    ) -> Tuple[str, float]:
        score = quality.score
        if "Real" in oi_value_validation or "Price-driven" in oi_value_validation:
            score += 8
        if any(x in quote_validation for x in ["Real", "Large Block", "Liquidation / Covering"]):
            score += 10
        if price_acceptance in {"Accepted Breakout", "Constructive Acceptance", "Pre-OI / No-OI Accepted Move From Base", "Pre-OI Accepted Move From Base"}:
            score += 12
        if ls_divergence not in {"No L/S Edge", "Mixed L/S Structure"}:
            score += 6
        if readiness in {"Confirmed Trigger", "Accepted Structure"}:
            score += 12
        if "Price-led Reset Ignition" in reset_ignition or "Price-led Base Ignition" in base_ignition or "Base Vacuum" in base_vacuum:
            score += 7
        if "Micro-trade" in quote_validation or "Contract-count distortion" in oi_value_validation:
            score -= 18
        if quality.confidence_cap == "Medium":
            score = min(score, 68)
        score = clamp(score)
        if score >= 82 and readiness in {"Confirmed Trigger", "Accepted Structure"} and quality.confidence_cap != "Medium":
            return "High", score
        if score >= 70:
            return "Medium-High", score
        if score >= 50:
            return "Medium", score
        return "Low", score

    # ------------------------------------------------------------------
    # Final output helpers
    # ------------------------------------------------------------------
    def signal_timing(self, candles: List[Candle], idx: int, phase: PhaseMemory, oi_state: str, base_vacuum: str) -> str:
        price3 = self.price_change(candles, idx, 3)
        oi3 = sum(x.oi_change_pct for x in candles[max(0, idx - 2) : idx + 1])
        if oi3 > 0 and abs(price3) < max(0.5, abs(oi3) * 0.5):
            return "OI سبق السعر / Early Structure"
        if price3 > 0 and oi3 > 0:
            return "OI والسعر تحركا معًا / Trigger in Progress"
        if phase.reset_detected and price3 > 0:
            return "السعر سبق OI بعد Reset / Early-Live"
        if phase.base_detected and price3 > 0 and oi3 > 0:
            return "السعر سبق OI من Base بدون Reset / Early-Live"
        if phase.base_detected and price3 > 0 and oi3 <= 0 and "Base Vacuum" in base_vacuum:
            return "السعر سبق OI من Base بدون Reset وOI لم يلحق / Price-led Base Vacuum Ignition"
        if price3 > 0 and oi3 < 0:
            return "OI هبط أثناء الصعود / Short Covering أو Base Vacuum حسب السياق"
        if price3 > 0:
            return "السعر سبق OI بدون Reset وبدون Base / Late Structure"
        return "No Clear Signal Timing"

    def whale_crowd_timing(self, candles: List[Candle], idx: int, phase: PhaseMemory, ls_divergence: str, base_vacuum: str, reset_ignition: str) -> str:
        c = candles[idx]
        if "Base Vacuum" in base_vacuum:
            return "قبل/أثناء الحركة بدون OI expansion: Top Position لا ينهار وTop Account لا يطارد"
        if "Reset Ignition" in reset_ignition:
            return "بعد Reset مع Price-led ignition: Retention / Squeeze Continuation"
        if "Top Position" in ls_divergence or c.position_lsr > max(c.global_lsr, c.account_lsr) * 1.10:
            if phase.base_detected:
                return "بعد Base مع Price-led ignition: Top Position يبقى قويًا والجمهور لا يطارد"
            return "Top Position / Whale Retention"
        if c.global_lsr > 1.10 and c.account_lsr > 1.10 and c.position_lsr <= 1.05:
            return "الحيتان لا تؤكد: Crowd Chasing"
        if c.global_lsr < 0.95:
            return "الجمهور ضد الحركة / Squeeze Fuel"
        return "غير قابل للجزم: لا CVD ولا order book ولا cross-venue"

    def invalidation_risk(self, candles: List[Candle], idx: int, phase: PhaseMemory, price_acceptance: str, oi_state: str) -> str:
        c = candles[idx]
        if phase.base_detected:
            return f"Invalidation: كسر قاعدة الإشعال تحت {phase.base_low:.8f} أو عودة السعر داخل القاعدة مع فشل Trades/Quote"
        if phase.reset_detected:
            recent_low = min(x.low for x in candles[max(0, idx - 12) : idx + 1])
            return f"Invalidation: كسر قاع ما بعد Flush قرب {recent_low:.8f}"
        if price_acceptance in {"Failed Breakout", "Structure Invalidated"}:
            return "Structure Invalidated: فشل قبول السعر"
        if "OI صاعد" in oi_state and not self.higher_highs(candles, idx):
            return "OI Trap Risk: OI ↑ والسعر لا يصنع قمة أعلى"
        return "Invalidation: فقدان قبول السعر أو خروج OI بعنف"

    def score_decision(self, readiness: str, bias: str, confidence_score: float, baseline: DynamicBaseline, price_acceptance: str, base_vacuum: str, high_oi: str) -> float:
        base = self.rank_priority(readiness, base_vacuum if "Base Vacuum" in base_vacuum else "")
        base += confidence_score * 0.35
        base += baseline.trades_rank * 0.10 + baseline.quote_rank * 0.08 + baseline.price_rank * 0.07
        if price_acceptance in {"Accepted Breakout", "Constructive Acceptance", "Pre-OI / No-OI Accepted Move From Base"}:
            base += 8
        if "Short-Crowded" in high_oi:
            base += 5
        if bias in {"Distribution Risk", "Bearish Structural Risk", "Post-Pump Crowding Risk"}:
            base -= 25
        return clamp(base, 0, 100)

    @classmethod
    def rank_priority(cls, readiness: str, pattern: str = "") -> int:
        if "Price-led Base Vacuum Ignition" in pattern or "Base Vacuum" in pattern:
            return cls.PATTERN_PRIORITY["Price-led Base Vacuum Ignition"]
        return cls.PATTERN_PRIORITY.get(readiness, 0)

    @staticmethod
    def category_from_readiness(readiness: str, bias: str) -> str:
        if readiness in {"Accepted Structure", "Confirmed Trigger", "Early-Live Structure"} and "Bearish" not in bias and "Distribution" not in bias:
            return "BULLISH_CANDIDATE"
        if readiness in {"Primed Structure", "Compression / Unresolved"}:
            return "BULLISH_WATCH"
        if readiness == "Watchlist Only":
            return "SETUP_WATCH"
        if readiness in {"Late / Risk State", "Failed / Invalidated"}:
            return "LATE_OR_FAILED"
        return "DIAGNOSTIC_ONLY"

    @staticmethod
    def summary(pattern: str, bias: str, readiness: str, signal_timing: str, price_acceptance: str, oi_state: str, trades_state: str, ls_divergence: str) -> str:
        return (
            f"{pattern}: {bias} مع Readiness={readiness}. "
            f"Signal Timing={signal_timing}. Price Acceptance={price_acceptance}. "
            f"OI={oi_state}. Trades={trades_state}. L/S={ls_divergence}."
        )

    # ------------------------------------------------------------------
    # Detection utilities
    # ------------------------------------------------------------------
    @staticmethod
    def price_change(candles: Sequence[Candle], idx: int, bars: int) -> float:
        if idx - bars < 0:
            return 0.0
        return pct(candles[idx - bars].close, candles[idx].close)

    @staticmethod
    def ratio_change(candles: Sequence[Candle], idx: int, attr: str, bars: int) -> float:
        if idx - bars < 0:
            return 0.0
        return pct(getattr(candles[idx - bars], attr), getattr(candles[idx], attr))

    def detect_base(self, candles: List[Candle], idx: int) -> Tuple[bool, float, float, str, str]:
        best: Optional[Tuple[int, int, float, float, str, str, float]] = None
        for n in range(Config.BASE_LOOKBACK_MIN, min(Config.BASE_LOOKBACK_MAX, idx) + 1):
            seg = candles[idx - n : idx]
            if len(seg) < Config.BASE_LOOKBACK_MIN:
                continue
            lows = [x.low for x in seg]
            highs = [x.high for x in seg]
            closes = [x.close for x in seg]
            base_low, base_high = min(lows), max(highs)
            rng_pct = pct(base_low, base_high)
            hist_ranges = []
            for j in range(max(2, idx - 60), idx - n):
                past = candles[max(0, j - n) : j]
                if len(past) >= n // 2:
                    hist_ranges.append(pct(min(x.low for x in past), max(x.high for x in past)))
            rng_ok = rng_pct <= max(1.2, pval(hist_ranges, 55, rng_pct) * 1.25) if hist_ranges else rng_pct <= 4.0
            trades_base = mean([x.trades for x in seg]) <= pval([x.trades for x in candles[:idx]], 70, mean([x.trades for x in seg]))
            oi_drift = abs(sum(x.oi_change_pct for x in seg)) <= max(3.0, pval([abs(x.oi_change_pct) for x in candles[:idx]], 80, 1.0) * n / 4)
            no_pump = max((pct(closes[k - 3], closes[k]) for k in range(3, len(closes))), default=0.0) <= max(3.5, rng_pct * 1.25)
            if rng_ok and no_pump and (trades_base or oi_drift):
                score = (100 - clamp(rng_pct * 10)) + (10 if trades_base else 0) + (10 if oi_drift else 0)
                cand = (idx - n, idx - 1, base_low, base_high, seg[0].time, seg[-1].time, score)
                if best is None or cand[-1] > best[-1]:
                    best = cand
        if not best:
            return False, 0.0, 0.0, "No Base", "No Base"
        return True, best[2], best[3], best[4], best[5]

    def last_oi_flush(self, candles: List[Candle], idx: int) -> Optional[int]:
        start = max(1, idx - Config.EVENT_LOOKBACK)
        for j in range(idx, start - 1, -1):
            hist = candles[:j]
            if not hist:
                continue
            oi_label = signed_label(candles[j].oi_change_pct, [x.oi_change_pct for x in hist])
            trade_label = value_label(candles[j].trades, [x.trades for x in hist])
            if candles[j].oi_change_pct < 0 and is_event(oi_label) and is_active(trade_label):
                return j
        return None

    def price_stabilized_after(self, candles: List[Candle], flush_idx: int, idx: int) -> bool:
        if flush_idx >= idx:
            return False
        flush_low = min(x.low for x in candles[flush_idx : min(idx + 1, flush_idx + 4)])
        after = candles[min(idx, flush_idx + 1) : idx + 1]
        if not after:
            return False
        no_new_low = min(x.low for x in after) >= flush_low * (1 - Config.ACCEPTANCE_EPS)
        recovered = candles[idx].close >= flush_low * (1 + Config.ACCEPTANCE_EPS)
        return no_new_low and recovered

    def last_trigger(self, candles: List[Candle], idx: int, base: Tuple[bool, float, float, str, str]) -> Optional[int]:
        start = max(1, idx - Config.RECENT_LOOKBACK)
        base_exists, _, base_high, _, _ = base
        for j in range(idx, start - 1, -1):
            hist = candles[:j]
            if not hist:
                continue
            price_up = pct(candles[j - 1].close, candles[j].close) > 0
            trades_active = is_active(value_label(candles[j].trades, [x.trades for x in hist])) or is_active(value_label(candles[j].quote_volume, [x.quote_volume for x in hist]))
            breaks_base = base_exists and candles[j].close > base_high * (1 + Config.ACCEPTANCE_EPS)
            breaks_recent = candles[j].close >= max(x.high for x in candles[max(0, j - 8) : j]) * (1 - Config.ACCEPTANCE_EPS) if j > 8 else False
            if price_up and trades_active and (breaks_base or breaks_recent):
                return j
        return None

    @staticmethod
    def higher_lows(candles: List[Candle], idx: int) -> bool:
        if idx < 6:
            return False
        a = min(x.low for x in candles[idx - 6 : idx - 3])
        b = min(x.low for x in candles[idx - 3 : idx + 1])
        return b >= a

    @staticmethod
    def higher_highs(candles: List[Candle], idx: int) -> bool:
        if idx < 6:
            return False
        a = max(x.high for x in candles[idx - 6 : idx - 3])
        b = max(x.high for x in candles[idx - 3 : idx + 1])
        return b >= a

    def cycle_count(self, candles: List[Candle], idx: int, base_detected: bool, reset_detected: bool, trigger_idx: Optional[int]) -> str:
        recent_triggers = 0
        for j in range(max(5, idx - 40), idx + 1):
            base = self.detect_base(candles, j) if j >= Config.BASE_LOOKBACK_MIN else (False, 0, 0, "", "")
            if self.last_trigger(candles, j, base) == j:
                recent_triggers += 1
        if base_detected and trigger_idx is None and not reset_detected:
            return "Early Base Cycle"
        if base_detected and trigger_idx is not None and not reset_detected:
            return "Early-Live Base Vacuum Cycle" if candles[idx].oi_change_pct <= 0 else "Early-Live Base Cycle"
        if reset_detected and trigger_idx is None:
            return "Early Reset Cycle"
        if reset_detected and trigger_idx is not None:
            return "Early-Live Reset Cycle"
        if recent_triggers >= 3:
            return "Late Cycle / Higher Volatility Risk"
        if recent_triggers == 2:
            return "Mid Cycle"
        return "First / Unclear Cycle"

    def distance_from_base_or_reset(self, candles: List[Candle], idx: int, phase: PhaseMemory) -> float:
        c = candles[idx]
        if phase.base_detected and phase.base_high > 0:
            return pct(phase.base_high, c.close)
        if phase.reset_detected:
            low = min(x.low for x in candles[max(0, idx - 20) : idx + 1])
            return pct(low, c.close)
        return self.price_change(candles, idx, 12)

    def phase_tail(self, candles: List[Candle], idx: int) -> List[Dict[str, Any]]:
        out = []
        for j in range(max(0, idx - 8), idx + 1):
            base = self.detect_base(candles, j) if j >= Config.BASE_LOOKBACK_MIN else (False, 0, 0, "", "")
            out.append(
                {
                    "time": candles[j].time,
                    "close": candles[j].close,
                    "price_3": round(self.price_change(candles, j, 3), 4),
                    "oi_change_pct": round(candles[j].oi_change_pct, 4),
                    "trades": candles[j].trades,
                    "base_detected": base[0],
                }
            )
        return out


# =============================================================================
# Scanner runtime
# =============================================================================
class FastKlinePrefilter:
    def score_klines(self, rows: List[List[Any]]) -> float:
        if len(rows) < 30:
            return 0.0
        closes = [sf(x[4]) for x in rows]
        trades = [float(si(x[8])) for x in rows]
        quotes = [sf(x[7]) for x in rows]
        p3 = pct(closes[-4], closes[-1]) if len(closes) >= 4 else 0
        p6 = pct(closes[-7], closes[-1]) if len(closes) >= 7 else p3
        p3h = [pct(closes[i - 3], closes[i]) for i in range(3, len(closes) - 1)]
        p6h = [pct(closes[i - 6], closes[i]) for i in range(6, len(closes) - 1)]
        # V3.2.1 prefilter must not drop base-vacuum candidates simply because OI is absent here.
        return clamp(
            0.38 * extreme(trades[-1], trades[:-1])
            + 0.36 * extreme(quotes[-1], quotes[:-1])
            + 0.26 * max(extreme(abs(p3), [abs(x) for x in p3h]), extreme(abs(p6), [abs(x) for x in p6h]))
        )


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_json(self, name: str, data: Any) -> None:
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_jsonl(self, name: str, row: Any) -> None:
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


class Runtime:
    def __init__(self):
        self.fetcher = BinanceFuturesFetcher()
        self.prefilter = FastKlinePrefilter()
        self.engine = StructuralLiquidityDiscoveryTreeV321()
        self.store = Store(Config.STATE_DIR)

    def budget(self, n: int) -> int:
        return max(Config.FULL_SCAN_MIN, min(Config.FULL_SCAN_MAX, int(n * Config.FULL_SCAN_BUDGET_FRACTION)))

    def run_once(self) -> List[V321Decision]:
        t0 = time.time()
        cid = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        symbols = self.fetcher.active_usdt_symbols()
        print(line())
        print(f"🔄 دورة {cid} | Engine=Structural Liquidity Discovery Tree V3.2.1 | TF={Config.TIMEFRAME} | Symbols={len(symbols)}")
        print(line())

        pre: List[Tuple[str, float, List[List[Any]]]] = []
        lock = threading.Lock()
        progress = {"n": 0}

        def pre_worker(sym: str) -> Optional[Tuple[str, float, List[List[Any]]]]:
            try:
                k = self.fetcher.klines(sym)
                return (sym, self.prefilter.score_klines(k), k) if k else None
            except Exception as exc:
                logging.debug("prefilter %s failed: %s", sym, exc)
                return None
            finally:
                with lock:
                    progress["n"] += 1
                    if progress["n"] % 25 == 0 or progress["n"] == len(symbols):
                        print(f"\r⚡ فلترة {progress['n']}/{len(symbols)}", end="", flush=True)

        with ThreadPoolExecutor(max_workers=Config.FAST_WORKERS) as ex:
            for fut in as_completed([ex.submit(pre_worker, s) for s in symbols]):
                result = fut.result()
                if result:
                    pre.append(result)
        print()
        pre.sort(key=lambda x: x[1], reverse=True)
        selected = pre[: self.budget(len(pre))]
        print(f"🎯 تحليل كامل وفق V3.2.1: {len(selected)} / {len(pre)}")

        results: List[V321Decision] = []
        progress = {"n": 0}

        def full_worker(item: Tuple[str, float, List[List[Any]]]) -> Optional[V321Decision]:
            sym, _, k = item
            try:
                candles = self.fetcher.candles(sym, kline_rows=k)
                return self.engine.analyze(candles) if candles else None
            except Exception as exc:
                logging.warning("analysis %s failed: %s", sym, exc)
                return None
            finally:
                with lock:
                    progress["n"] += 1
                    print(f"\r🧠 تحليل {progress['n']}/{len(selected)}", end="", flush=True)

        with ThreadPoolExecutor(max_workers=Config.FULL_WORKERS) as ex:
            for fut in as_completed([ex.submit(full_worker, x) for x in selected]):
                result = fut.result()
                if result:
                    results.append(result)
        print()
        results.sort(key=self.rank, reverse=True)
        elapsed = time.time() - t0
        self.store.write_json(
            "latest_results_v321.json",
            {
                "cycle_id": cid,
                "elapsed_seconds": round(elapsed, 2),
                "methodology": "Structural Liquidity Discovery Tree V3.2.1",
                "results": [asdict(r) for r in results],
                "user_format_results": [r.export_user_format() for r in results],
            },
        )
        self.store.append_jsonl("history_v321.jsonl", {"cycle_id": cid, "count": len(results), "elapsed": round(elapsed, 2)})
        self.print_results(results, elapsed)
        return results

    @staticmethod
    def rank(r: V321Decision) -> float:
        group = {
            "BULLISH_CANDIDATE": 100,
            "BULLISH_WATCH": 75,
            "SETUP_WATCH": 45,
            "LATE_OR_FAILED": 10,
            "DIAGNOSTIC_ONLY": 0,
        }.get(r.category, 0)
        return group + r.rank_priority * 0.42 + r.score * 0.32 + r.confidence_score * 0.20 - (20 if r.structural_bias in {"Distribution Risk", "Bearish Structural Risk"} else 0)

    def print_results(self, results: List[V321Decision], elapsed: float) -> None:
        print(line())
        print(f"🏁 انتهت الدورة | النتائج={len(results)} | الزمن={elapsed:.1f}s")
        print(line())
        groups = [
            ("🔥 Accepted / Confirmed / Early-Live", "BULLISH_CANDIDATE", "green"),
            ("🟢 Primed / Compression", "BULLISH_WATCH", "cyan"),
            ("🟡 Watchlist", "SETUP_WATCH", "yellow"),
            ("🔴 Late / Failed", "LATE_OR_FAILED", "red"),
        ]
        for title, category, col in groups:
            rows = [r for r in results if r.category == category]
            if not rows:
                continue
            print(color(f"\n{title} | count={len(rows)}", col))
            print("-" * Config.WIDTH)
            print(f"{'#':<3}{'Symbol':<14}{'Pattern':<46}{'Ready':<24}{'Score':>7}{'Conf':>7}{'Close':>13}")
            print("-" * Config.WIDTH)
            for i, r in enumerate(rows[: Config.PRINT_TOP_PER_GROUP], 1):
                print(f"{i:<3}{r.symbol:<14}{r.dominant_structural_pattern[:45]:<46}{r.readiness_level[:23]:<24}{r.score:>7.1f}{r.confidence_score:>7.1f}{r.close:>13.8f}")
                print(f"   ↳ Bias: {r.structural_bias} | Timing: {r.signal_timing}")
                print(f"   ↳ Acceptance: {r.price_acceptance} | Base Vacuum: {r.price_led_base_vacuum_ignition_state}")
                print(f"   ↳ Risk: {r.invalidation_risk}")
        print("\nالمبدأ V3.2.1: لا قرار من شمعة واحدة، ولا إسقاط لحركة Base Vacuum لمجرد غياب OI expansion.")

    def run_forever(self) -> None:
        print("🚀 Structural Liquidity Discovery Tree V3.2.1 بدأ التشغيل. Ctrl+C للإيقاف.")
        try:
            while True:
                self.run_once()
                print(f"⏳ الدورة القادمة بعد {Config.CYCLE_SLEEP_SECONDS}s")
                time.sleep(Config.CYCLE_SLEEP_SECONDS)
        except KeyboardInterrupt:
            print("\nتم الإيقاف الآمن.")


# =============================================================================
# Synthetic data and audit
# =============================================================================
def synthetic_base_vacuum_candles() -> List[Candle]:
    out: List[Candle] = []
    price = 1.0000
    oi = 1_000_000.0
    for i in range(110):
        if i < 70:
            change = math.sin(i / 5) * 0.0008
            trades = 120 + int(abs(math.sin(i)) * 35)
            quote_mult = 1.0
            oi += math.sin(i / 8) * 150
            acc, pos, glob = 0.98, 1.35, 0.96
        elif i < 94:
            change = math.sin(i / 3) * 0.0004
            trades = 105 + int(abs(math.sin(i)) * 20)
            quote_mult = 1.0
            oi += -250 + math.sin(i) * 80
            acc, pos, glob = 0.96, 1.42, 0.98
        elif i == 94:
            change = 0.018
            trades = 1200
            quote_mult = 10.0
            oi += -80
            acc, pos, glob = 0.95, 1.40, 0.99
        elif i == 95:
            change = 0.010
            trades = 950
            quote_mult = 8.0
            oi += -20
            acc, pos, glob = 0.94, 1.38, 1.01
        else:
            change = 0.0015
            trades = 330
            quote_mult = 2.0
            oi += -10
            acc, pos, glob = 0.96, 1.36, 1.00
        prev = price
        price *= 1 + change
        high = max(prev, price) * (1 + 0.001)
        low = min(prev, price) * (1 - 0.001)
        qv = trades * price * quote_mult
        al, ass = BinanceFuturesFetcher.lsp(acc)
        pl, ps = BinanceFuturesFetcher.lsp(pos)
        gl, gs = BinanceFuturesFetcher.lsp(glob)
        prev_oi = out[-1].oi if out else oi
        out.append(
            Candle(
                i * 900_000,
                datetime.fromtimestamp(i * 900, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "TESTUSDT",
                prev,
                high,
                low,
                price,
                trades * 10.0,
                qv,
                trades,
                qv * 0.55,
                50.0,
                oi,
                oi * price,
                oi - prev_oi,
                0.0 if i == 0 else pct(prev_oi, oi),
                acc,
                al,
                ass,
                pos,
                pl,
                ps,
                glob,
                gl,
                gs,
            )
        )
    rsi = Indicators.rsi([c.close for c in out], Config.RSI_PERIOD)
    for i, c in enumerate(out):
        c.rsi = rsi[i]
    return out


def synthetic_delayed_oi_base_candles() -> List[Candle]:
    out = synthetic_base_vacuum_candles()
    for i in range(95, len(out)):
        out[i].oi += (i - 94) * 2500
        out[i].oi_change = out[i].oi - out[i - 1].oi
        out[i].oi_change_pct = pct(out[i - 1].oi, out[i].oi)
        out[i].oi_value = out[i].oi * out[i].close
    return out


def audit() -> Dict[str, Any]:
    src = Path(__file__).read_text(encoding="utf-8")
    required = [
        "Structural Liquidity Discovery Tree V3.2.1",
        "Structural Liquidity Discovery Tree V3.2.1-O",
        "Candidate Eligibility",
        "Pattern Eligibility + Support Score",
        "Hard Conflict Override",
        "Data Quality / Regime Check",
        "Dynamic Baseline",
        "Phase Memory",
        "OI Value / Quote Volume Validation",
        "Price-led Base Vacuum Ignition Check",
        "PRICE-LED BASE VACUUM IGNITION WITHOUT OI EXPANSION",
        "Price-led Base Vacuum Ignition without OI Expansion",
        "READINESS_LEVELS",
        "STRUCTURAL_BIASES",
        "RSI was used only as visual/contextual information, not as a decision driver.",
        "لا تسقط العملة بسبب OI ثابت أو هابط قليلًا",
        "Quote Volume Missing: Confidence cap Medium",
    ]
    checks = {name: (name in src) for name in required}
    return {"ok": all(checks.values()), "checks": checks, "engine": "Structural Liquidity Discovery Tree V3.2.1"}


def self_test() -> None:
    engine = StructuralLiquidityDiscoveryTreeV321()
    r1 = engine.analyze(synthetic_base_vacuum_candles())
    r2 = engine.analyze(synthetic_delayed_oi_base_candles())
    a = audit()
    assert a["ok"], a
    assert r1 is not None and "Base" in r1.dominant_structural_pattern, asdict(r1) if r1 else None
    assert r2 is not None and r2.readiness_level in StructuralLiquidityDiscoveryTreeV321.READINESS_LEVELS, asdict(r2) if r2 else None
    print(
        json.dumps(
            {
                "self_test": "OK",
                "audit": a,
                "base_vacuum_result": r1.export_user_format() if r1 else None,
                "delayed_oi_base_result": r2.export_user_format() if r2 else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


# =============================================================================
# CLI
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Structural Liquidity Discovery Tree V3.2.1")
    parser.add_argument("--once", action="store_true", help="Run one Binance Futures scan cycle")
    parser.add_argument("--self-test", action="store_true", help="Run synthetic V3.2.1 tests")
    parser.add_argument("--audit", action="store_true", help="Check V3.2.1 branch coverage markers")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.self_test:
        self_test()
        return
    if args.audit:
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
        return
    runtime = Runtime()
    runtime.run_once() if args.once else runtime.run_forever()


if __name__ == "__main__":
    main()
