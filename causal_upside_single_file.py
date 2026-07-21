#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Causal Binance USD-M Futures upside-precursor scanner — standalone build.

Generated deterministically from the authoritative ``causal_upside`` package.
Edit SETTINGS near the end of this file and press Run in any Python editor.
Standard-library only; no API keys are required.
"""
from __future__ import annotations

import argparse


# =============================================================================
# SOURCE: causal_upside/config.py
# =============================================================================
from dataclasses import dataclass
from pathlib import Path


TIMEFRAME_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    timeframe: str = "15m"
    history_limit: int = 200
    min_history: int = 80
    max_workers: int = 8
    request_timeout: float = 12.0
    retries: int = 3
    backoff_base: float = 0.5
    max_requests_per_second: float = 8.0
    top_n: int = 30
    state_dir: Path = Path("causal_upside_state")
    output_dir: Path = Path("causal_upside_output")
    whitelist: tuple[str, ...] = ()
    blacklist: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    scan_all_usdt_perpetuals: bool = True
    include_funding: bool = True
    adaptive_quantiles: tuple[float, float, float] = (0.75, 0.90, 0.975)
    minimum_baseline_observations: int = 24
    max_alignment_age_intervals: int = 1
    ledger_schema_version: int = 1

    def validate(self) -> "ScannerConfig":
        if self.timeframe not in TIMEFRAME_MS:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")
        if self.history_limit < self.min_history:
            raise ValueError("history_limit must be >= min_history")
        if self.min_history < 20:
            raise ValueError("min_history must be at least 20 closed bars")
        if not 1 <= self.max_workers <= 32:
            raise ValueError("max_workers must be between 1 and 32")
        if self.retries < 1:
            raise ValueError("retries must be positive")
        if self.max_requests_per_second <= 0:
            raise ValueError("max_requests_per_second must be positive")
        if tuple(sorted(self.adaptive_quantiles)) != self.adaptive_quantiles:
            raise ValueError("adaptive_quantiles must be increasing")
        if any(not 0 < item < 1 for item in self.adaptive_quantiles):
            raise ValueError("adaptive_quantiles must be inside (0, 1)")
        return self

    @property
    def interval_ms(self) -> int:
        return TIMEFRAME_MS[self.timeframe]

# =============================================================================
# SOURCE: causal_upside/models.py
# =============================================================================
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CampaignState(str, Enum):
    LATENT = "LATENT"
    EARLY_BUILD = "EARLY_BUILD"
    CONFIRMED_BUILD = "CONFIRMED_BUILD"
    ARMED = "ARMED"
    IGNITION_CANDIDATE = "IGNITION_CANDIDATE"
    ACCEPTED_IGNITION = "ACCEPTED_IGNITION"
    EXPANSION = "EXPANSION"
    CONTINUATION_RELOAD = "CONTINUATION_RELOAD"
    COOLING = "COOLING"
    FAILURE = "FAILURE"
    DISTRIBUTION = "DISTRIBUTION"
    RESET = "RESET"
    REBUILD = "REBUILD"
    UNRESOLVED = "UNRESOLVED"


class Hypothesis(str, Enum):
    QUIET_ACCUMULATION = "QUIET_ACCUMULATION"
    OI_RESET_ABSORPTION_REBUILD = "OI_RESET_ABSORPTION_REBUILD"
    PRICE_LED_BASE_IGNITION = "PRICE_LED_BASE_IGNITION"
    PRICE_LED_VACUUM_IGNITION = "PRICE_LED_VACUUM_IGNITION"
    HIGH_OI_COMPRESSION = "HIGH_OI_COMPRESSION"
    WHALE_DIVERGENCE_BUILD = "WHALE_DIVERGENCE_BUILD"
    COLD_START_OI_IGNITION = "COLD_START_OI_IGNITION"
    POST_IGNITION_FUEL_RETENTION = "POST_IGNITION_FUEL_RETENTION"
    SHORT_COVERING_ONLY = "SHORT_COVERING_ONLY"
    TRANSIENT_EXECUTION_SPIKE = "TRANSIENT_EXECUTION_SPIKE"
    LATE_CROWDING = "LATE_CROWDING"
    DISTRIBUTION = "DISTRIBUTION"
    FAILED_FLASH = "FAILED_FLASH"
    NEW_UNIDENTIFIED_STRUCTURE = "NEW_UNIDENTIFIED_STRUCTURE"


class RuleStatus(str, Enum):
    BACKGROUND_CONCEPT = "BACKGROUND_CONCEPT"
    RESEARCH_HYPOTHESIS = "RESEARCH_HYPOTHESIS"
    SUPPORTED_PATTERN = "SUPPORTED_PATTERN"
    CONDITIONAL_RULE = "CONDITIONAL_RULE"
    DURABLE_RULE = "DURABLE_RULE"
    REJECTED_RULE = "REJECTED_RULE"
    DEPRECATED = "DEPRECATED"


class Readiness(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    EARLY_BUILD = "EARLY_BUILD"
    CONFIRMED_BUILD = "CONFIRMED_BUILD"
    ARMED = "ARMED"
    LIVE_IGNITION = "LIVE_IGNITION"
    ACCEPTED = "ACCEPTED"
    CONTINUATION = "CONTINUATION"
    COOLING = "COOLING"
    LATE_NO_CHASE = "LATE_NO_CHASE"
    FAILED = "FAILED"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    HIGH = "HIGH"


class Reliability(str, Enum):
    UNUSABLE = "UNUSABLE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class MarketBar:
    """One causally observable, closed market bar.

    Optional positioning values remain ``None`` when unavailable. Missing evidence
    is never silently converted to zero or a neutral ratio.
    """

    symbol: str
    timeframe: str
    timestamp_ms: int
    close_time_ms: int
    is_closed: bool
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    quote_volume: float | None = None
    trades: float | None = None
    taker_buy_quote: float | None = None
    oi: float | None = None
    global_ls: float | None = None
    top_account_ls: float | None = None
    top_position_ls: float | None = None
    funding_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdaptiveMetric:
    name: str
    value: float | None
    median: float | None
    mad: float | None
    percentile: float | None
    robust_z: float | None
    direction: str
    state: str
    baseline_count: int
    warm: bool


@dataclass(frozen=True, slots=True)
class QualityReport:
    flags: tuple[str, ...]
    reliability: Reliability
    confidence_cap: Confidence
    usable: bool
    closed_bars: int
    expected_interval_ms: int


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    category: str
    observation: str
    timestamp_ms: int
    strength: str = "CONTEXT"
    rule_status: RuleStatus = RuleStatus.RESEARCH_HYPOTHESIS


@dataclass(frozen=True, slots=True)
class HypothesisAssessment:
    hypothesis: Hypothesis
    rule_status: RuleStatus
    supporting: tuple[EvidenceItem, ...] = ()
    opposing: tuple[EvidenceItem, ...] = ()
    missing: tuple[str, ...] = ()
    invalidated: bool = False
    research_scope: str = "cross-symbol validation pending"

    @property
    def evidence_balance(self) -> tuple[int, int, int]:
        """Transparent ordering key, not a probability or profit score."""
        strong = sum(item.strength == "STRONG" for item in self.supporting)
        return (strong, len(self.supporting) - len(self.opposing), -len(self.missing))


@dataclass(frozen=True, slots=True)
class SignalAssessment:
    symbol: str
    timeframe: str
    cutoff_ms: int
    campaign_state: CampaignState
    dominant_hypothesis: Hypothesis
    alternative_hypotheses: tuple[Hypothesis, ...]
    failure_hypothesis: Hypothesis
    structural_bias: str
    signal_importance: str
    readiness: Readiness
    entry_safety: str
    confidence: Confidence
    data_reliability: Reliability
    supporting_evidence: tuple[EvidenceItem, ...]
    opposing_evidence: tuple[EvidenceItem, ...]
    missing_evidence: tuple[str, ...]
    next_discriminator: str
    invalidation: str
    abstention_reason: str | None
    research_status: RuleStatus
    campaign_age_bars: int
    distance_from_footprint_rank: float | None
    quality_flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["campaign_state"] = self.campaign_state.value
        value["dominant_hypothesis"] = self.dominant_hypothesis.value
        value["alternative_hypotheses"] = [item.value for item in self.alternative_hypotheses]
        value["failure_hypothesis"] = self.failure_hypothesis.value
        value["readiness"] = self.readiness.value
        value["confidence"] = self.confidence.value
        value["data_reliability"] = self.data_reliability.value
        value["research_status"] = self.research_status.value
        for key in ("supporting_evidence", "opposing_evidence"):
            for item in value[key]:
                item["rule_status"] = item["rule_status"].value if isinstance(item["rule_status"], RuleStatus) else item["rule_status"]
        return value


@dataclass(slots=True)
class CampaignLedger:
    schema_version: int
    symbol: str
    timeframe: str
    campaign_id: str
    state: CampaignState
    birth_ms: int
    last_observed_ms: int
    first_detection_ms: int | None = None
    first_warning_ms: int | None = None
    armed_ms: int | None = None
    ignition_ms: int | None = None
    acceptance_ms: int | None = None
    expansion_ms: int | None = None
    weakness_ms: int | None = None
    failure_ms: int | None = None
    reset_ms: int | None = None
    rebuild_ms: int | None = None
    dominant_hypothesis: Hypothesis = Hypothesis.NEW_UNIDENTIFIED_STRUCTURE
    alternatives: list[Hypothesis] = field(default_factory=list)
    contradiction_streak: int = 0
    transition_history: list[dict[str, Any]] = field(default_factory=list)
    last_assessment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        value["dominant_hypothesis"] = self.dominant_hypothesis.value
        value["alternatives"] = [item.value for item in self.alternatives]
        return value

# =============================================================================
# SOURCE: causal_upside/alignment.py
# =============================================================================
from bisect import bisect_right
from typing import Any, Iterable, Mapping, Sequence



def bounded_asof(
    target_timestamps: Sequence[int],
    observations: Sequence[tuple[int, float | None]],
    *,
    max_age_ms: int,
) -> list[float | None]:
    """Align the latest past observation without future or unbounded fill."""
    clean = sorted((int(ts), value) for ts, value in observations if value is not None)
    source_times = [item[0] for item in clean]
    output: list[float | None] = []
    for target in target_timestamps:
        position = bisect_right(source_times, int(target)) - 1
        if position < 0:
            output.append(None)
            continue
        source_time, value = clean[position]
        output.append(value if 0 <= int(target) - source_time <= max_age_ms else None)
    return output


def closed_klines(raw: Iterable[Sequence[Any]], *, symbol: str, timeframe: str, now_ms: int) -> list[MarketBar]:
    """Normalize Binance kline arrays and discard the unfinished candle."""
    output: list[MarketBar] = []
    for row in raw:
        if len(row) < 11:
            continue
        close_time = int(row[6])
        if close_time > now_ms:
            continue
        output.append(
            MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp_ms=int(row[0]),
                close_time_ms=close_time,
                is_closed=True,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_volume=float(row[7]),
                trades=float(row[8]),
                taker_buy_quote=float(row[10]),
            )
        )
    deduplicated = {item.timestamp_ms: item for item in output}
    return [deduplicated[key] for key in sorted(deduplicated)]


def attach_series(
    bars: Sequence[MarketBar],
    series: Mapping[str, Sequence[tuple[int, float | None]]],
    *,
    max_age_ms: int,
    funding_rate: float | None = None,
) -> list[MarketBar]:
    """Attach OI and positioning series while preserving explicit missingness."""
    timestamps = [item.close_time_ms for item in bars]
    aligned = {name: bounded_asof(timestamps, values, max_age_ms=max_age_ms) for name, values in series.items()}
    output: list[MarketBar] = []
    for index, bar in enumerate(bars):
        output.append(
            MarketBar(
                **{
                    **bar.to_dict(),
                    "oi": aligned.get("oi", [None] * len(bars))[index],
                    "global_ls": aligned.get("global_ls", [None] * len(bars))[index],
                    "top_account_ls": aligned.get("top_account_ls", [None] * len(bars))[index],
                    "top_position_ls": aligned.get("top_position_ls", [None] * len(bars))[index],
                    "funding_rate": funding_rate,
                }
            )
        )
    return output

# =============================================================================
# SOURCE: causal_upside/binance.py
# =============================================================================
import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Sequence



BASE_URL = "https://fapi.binance.com"


@dataclass(frozen=True, slots=True)
class FetchResult:
    bars: tuple[MarketBar, ...]
    flags: tuple[str, ...]


class RequestLimiter:
    def __init__(self, requests_per_second: float):
        self.minimum_interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.minimum_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


class BinancePublicClient:
    """Network I/O is isolated from all analysis logic."""

    def __init__(self, config: ScannerConfig, *, opener: Callable[..., Any] | None = None):
        self.config = config.validate()
        self._opener = opener or urllib.request.urlopen
        self._limiter = RequestLimiter(self.config.max_requests_per_second)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{BASE_URL}{path}{'?' + query if query else ''}"
        last_error: Exception | None = None
        for attempt in range(self.config.retries):
            self._limiter.wait()
            request = urllib.request.Request(url, headers={"User-Agent": "causal-upside-scanner/1.0"})
            try:
                with self._opener(request, timeout=self.config.request_timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if exc.code not in {418, 429, 500, 502, 503, 504}:
                    break
                delay = float(retry_after) if retry_after else self.config.backoff_base * (2**attempt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                delay = self.config.backoff_base * (2**attempt)
            time.sleep(delay + random.uniform(0, self.config.backoff_base))
        raise RuntimeError(f"GET {path} failed after {self.config.retries} attempts: {last_error}")

    def symbols(self) -> list[str]:
        payload = self._get("/fapi/v1/exchangeInfo")
        symbols = [
            item["symbol"]
            for item in payload.get("symbols", [])
            if item.get("contractType") == "PERPETUAL"
            and item.get("quoteAsset") == "USDT"
            and item.get("status") == "TRADING"
        ]
        whitelist = set(self.config.whitelist)
        blacklist = set(self.config.blacklist)
        if whitelist:
            symbols = [item for item in symbols if item in whitelist]
        return sorted(item for item in symbols if item not in blacklist)

    @staticmethod
    def _series(payload: Sequence[dict[str, Any]], field: str) -> list[tuple[int, float | None]]:
        output: list[tuple[int, float | None]] = []
        for item in payload:
            try:
                output.append((int(item["timestamp"]), float(item[field])))
            except (KeyError, TypeError, ValueError):
                continue
        return output

    def fetch_symbol(self, symbol: str, *, now_ms: int | None = None) -> FetchResult:
        flags: list[str] = []
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        raw_klines = self._get(
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": self.config.timeframe, "limit": self.config.history_limit + 1},
        )
        bars = closed_klines(raw_klines, symbol=symbol, timeframe=self.config.timeframe, now_ms=now_ms)
        if len(bars) > self.config.history_limit:
            bars = bars[-self.config.history_limit :]
        if not bars:
            return FetchResult((), ("KLINES_MISSING",))

        endpoints = {
            "oi": ("/futures/data/openInterestHist", "sumOpenInterest"),
            "global_ls": ("/futures/data/globalLongShortAccountRatio", "longShortRatio"),
            "top_account_ls": ("/futures/data/topLongShortAccountRatio", "longShortRatio"),
            "top_position_ls": ("/futures/data/topLongShortPositionRatio", "longShortRatio"),
        }
        series: dict[str, list[tuple[int, float | None]]] = {}
        for name, (endpoint, field) in endpoints.items():
            try:
                payload = self._get(
                    endpoint,
                    {"symbol": symbol, "period": self.config.timeframe, "limit": self.config.history_limit},
                )
                series[name] = self._series(payload, field)
                if not series[name]:
                    flags.append(f"{name.upper()}_MISSING")
            except RuntimeError as exc:
                series[name] = []
                flags.append(f"{name.upper()}_ENDPOINT_FAILED:{type(exc).__name__}")

        funding_rate = None
        if self.config.include_funding:
            try:
                premium = self._get("/fapi/v1/premiumIndex", {"symbol": symbol})
                funding_rate = float(premium["lastFundingRate"])
            except (RuntimeError, KeyError, TypeError, ValueError):
                flags.append("FUNDING_CONTEXT_MISSING")
        aligned = attach_series(
            bars,
            series,
            max_age_ms=self.config.interval_ms * self.config.max_alignment_age_intervals,
            funding_rate=funding_rate,
        )
        for name in endpoints:
            if all(getattr(item, name) is None for item in aligned):
                flags.append(f"{name.upper()}_ALIGNMENT_EMPTY")
        return FetchResult(tuple(aligned), tuple(sorted(set(flags))))

# =============================================================================
# SOURCE: causal_upside/adaptive.py
# =============================================================================
import math
import statistics
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence



def finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def safe_return(previous: float | None, current: float | None) -> float | None:
    if not finite(previous) or not finite(current) or previous == 0:
        return None
    return (float(current) - float(previous)) / abs(float(previous))


def median(values: Iterable[float | None]) -> float | None:
    data = [float(item) for item in values if finite(item)]
    return statistics.median(data) if data else None


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires observations")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def percentile(values: Sequence[float], current: float) -> float:
    if not values:
        return 0.5
    less = sum(item < current for item in values)
    equal = sum(item == current for item in values)
    return (less + 0.5 * equal) / len(values)


def robust_z(values: Sequence[float], current: float) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    center = statistics.median(values)
    deviations = [abs(item - center) for item in values]
    mad = statistics.median(deviations)
    if mad <= math.ulp(1.0):
        if len(values) < 2:
            return center, mad, 0.0
        q25 = quantile(values, 0.25)
        q75 = quantile(values, 0.75)
        mad = (q75 - q25) / 1.349 if q75 > q25 else statistics.pstdev(values)
    if mad <= math.ulp(1.0):
        return center, mad, 0.0
    return center, mad, 0.6745 * (current - center) / mad


def slope(values: Sequence[float | None]) -> float | None:
    data = [float(item) for item in values if finite(item)]
    if len(data) < 3:
        return None
    x_mean = (len(data) - 1) / 2
    y_mean = statistics.fmean(data)
    denominator = sum((index - x_mean) ** 2 for index in range(len(data)))
    if denominator == 0:
        return 0.0
    return sum((index - x_mean) * (value - y_mean) for index, value in enumerate(data)) / denominator


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    timestamp_ms: int
    price_return: AdaptiveMetric
    range_fraction: AdaptiveMetric
    trades: AdaptiveMetric
    quote_volume: AdaptiveMetric
    oi_return: AdaptiveMetric
    oi_level: AdaptiveMetric
    global_ls_change: AdaptiveMetric
    top_account_ls_change: AdaptiveMetric
    top_position_ls_change: AdaptiveMetric
    close_location: float | None
    taker_imbalance: float | None
    price_slope: float | None
    oi_slope: float | None
    execution_retention: float | None
    compression_persistence: float | None


class AdaptiveFeatureEngine:
    """Compute adaptive states from observations strictly before each cutoff."""

    def __init__(self, config: ScannerConfig):
        self.config = config.validate()

    def _classify(self, name: str, history: Sequence[float | None], current: float | None, *, magnitude: bool = False) -> AdaptiveMetric:
        data = [float(item) for item in history if finite(item)]
        value = float(current) if finite(current) else None
        minimum = self.config.minimum_baseline_observations
        if value is None:
            return AdaptiveMetric(name, None, median(data), None, None, None, "UNKNOWN", "UNKNOWN", len(data), len(data) >= minimum)
        comparison = [abs(item) for item in data] if magnitude else data
        target = abs(value) if magnitude else value
        center, mad, z_value = robust_z(comparison, target)
        rank = percentile(comparison, target) if comparison else None
        direction = "UP" if value > 0 else "DOWN" if value < 0 else "FLAT"
        if len(comparison) < minimum or rank is None:
            state = "WARMUP"
        else:
            elevated, shock, extreme = self.config.adaptive_quantiles
            state = "EXTREME" if rank >= extreme else "SHOCK" if rank >= shock else "ELEVATED" if rank >= elevated else "TYPICAL"
        return AdaptiveMetric(name, value, center, mad, rank, z_value, direction, state, len(data), len(data) >= minimum)

    @staticmethod
    def _series(bars: Sequence[MarketBar], getter: Callable[[MarketBar], float | None]) -> list[float | None]:
        return [getter(item) for item in bars]

    @staticmethod
    def _returns(values: Sequence[float | None]) -> list[float | None]:
        return [safe_return(previous, current) for previous, current in zip(values, values[1:])]

    @staticmethod
    def _close_location(bar: MarketBar) -> float | None:
        width = bar.high - bar.low
        if width <= 0:
            return None
        return (bar.close - bar.low) / width

    @staticmethod
    def _taker_imbalance(bar: MarketBar) -> float | None:
        if not finite(bar.taker_buy_quote) or not finite(bar.quote_volume) or not bar.quote_volume:
            return None
        sell = float(bar.quote_volume) - float(bar.taker_buy_quote)
        return (float(bar.taker_buy_quote) - sell) / float(bar.quote_volume)

    def snapshot(self, bars: Sequence[MarketBar]) -> FeatureSnapshot:
        if len(bars) < 2:
            raise ValueError("At least two bars are required")
        ordered = list(bars)
        current = ordered[-1]

        closes = self._series(ordered, lambda item: item.close)
        ranges = [(item.high - item.low) / abs(item.close) if item.close else None for item in ordered]
        trades = self._series(ordered, lambda item: item.trades)
        quote = self._series(ordered, lambda item: item.quote_volume)
        oi = self._series(ordered, lambda item: item.oi)
        global_ls = self._series(ordered, lambda item: item.global_ls)
        top_account = self._series(ordered, lambda item: item.top_account_ls)
        top_position = self._series(ordered, lambda item: item.top_position_ls)

        price_returns = self._returns(closes)
        oi_returns = self._returns(oi)
        global_changes = self._returns(global_ls)
        account_changes = self._returns(top_account)
        position_changes = self._returns(top_position)

        segment = max(4, int(math.sqrt(len(ordered))))
        recent_quote = [item for item in quote[-segment:] if finite(item)]
        baseline_quote = [item for item in quote[:-segment] if finite(item)]
        execution_retention = None
        if recent_quote and baseline_quote:
            baseline_center = statistics.median(baseline_quote)
            peak = max(recent_quote)
            denominator = peak - baseline_center
            execution_retention = 0.0 if denominator <= 0 else (recent_quote[-1] - baseline_center) / denominator

        range_history = [item for item in ranges[:-1] if finite(item)]
        compression_hits = 0
        compression_total = 0
        if len(range_history) >= self.config.minimum_baseline_observations:
            low_reference = quantile(range_history, 1 - self.config.adaptive_quantiles[0])
            for value in ranges[-segment:]:
                if finite(value):
                    compression_total += 1
                    compression_hits += float(value) <= low_reference
        compression_persistence = compression_hits / compression_total if compression_total else None

        return FeatureSnapshot(
            timestamp_ms=current.timestamp_ms,
            price_return=self._classify("price_return", price_returns[:-1], price_returns[-1], magnitude=True),
            range_fraction=self._classify("range_fraction", ranges[:-1], ranges[-1]),
            trades=self._classify("trades", trades[:-1], trades[-1]),
            quote_volume=self._classify("quote_volume", quote[:-1], quote[-1]),
            oi_return=self._classify("oi_return", oi_returns[:-1], oi_returns[-1], magnitude=True),
            oi_level=self._classify("oi_level", oi[:-1], oi[-1]),
            global_ls_change=self._classify("global_ls_change", global_changes[:-1], global_changes[-1], magnitude=True),
            top_account_ls_change=self._classify("top_account_ls_change", account_changes[:-1], account_changes[-1], magnitude=True),
            top_position_ls_change=self._classify("top_position_ls_change", position_changes[:-1], position_changes[-1], magnitude=True),
            close_location=self._close_location(current),
            taker_imbalance=self._taker_imbalance(current),
            price_slope=slope(closes[-segment:]),
            oi_slope=slope(oi[-segment:]),
            execution_retention=execution_retention,
            compression_persistence=compression_persistence,
        )

    def timeline(self, bars: Sequence[MarketBar]) -> list[FeatureSnapshot]:
        output: list[FeatureSnapshot] = []
        minimum = max(2, self.config.minimum_baseline_observations + 1)
        for end in range(minimum, len(bars) + 1):
            output.append(self.snapshot(bars[:end]))
        return output

# =============================================================================
# SOURCE: causal_upside/quality.py
# =============================================================================
import math
from collections import Counter
from typing import Sequence



class DataQualityChecker:
    def __init__(self, config: ScannerConfig):
        self.config = config.validate()

    def check(self, bars: Sequence[MarketBar], *, source_flags: Sequence[str] = ()) -> QualityReport:
        flags = list(source_flags)
        if not bars:
            return QualityReport(tuple(sorted(set(flags + ["NO_BARS"]))), Reliability.UNUSABLE, Confidence.LOW, False, 0, self.config.interval_ms)

        ordered = list(bars)
        timestamps = [item.timestamp_ms for item in ordered]
        closed = [item for item in ordered if item.is_closed]
        if len(closed) != len(ordered):
            flags.append("OPEN_CANDLE_PRESENT")
        if len(closed) < self.config.min_history:
            flags.append("INSUFFICIENT_CLOSED_HISTORY")
        if timestamps != sorted(timestamps):
            flags.append("NON_MONOTONIC_TIMESTAMPS")
        duplicate_count = len(timestamps) - len(set(timestamps))
        if duplicate_count:
            flags.append(f"DUPLICATE_TIMESTAMPS:{duplicate_count}")
        gaps = [right - left for left, right in zip(timestamps, timestamps[1:])]
        irregular = sum(delta != self.config.interval_ms for delta in gaps)
        if irregular:
            flags.append(f"IRREGULAR_INTERVALS:{irregular}")
        for item in ordered:
            numeric = (item.open, item.high, item.low, item.close)
            if any(not math.isfinite(value) or value <= 0 for value in numeric):
                flags.append("INVALID_OHLC")
                break
            if not item.low <= min(item.open, item.close) <= max(item.open, item.close) <= item.high:
                flags.append("INCONSISTENT_OHLC")
                break
        missing = Counter()
        for item in ordered:
            for field in ("quote_volume", "trades", "oi", "global_ls", "top_account_ls", "top_position_ls"):
                value = getattr(item, field)
                if value is None or not math.isfinite(value):
                    missing[field] += 1
        for field, count in missing.items():
            if count == len(ordered):
                flags.append(f"{field.upper()}_MISSING")
            elif count:
                flags.append(f"{field.upper()}_PARTIAL:{count}")

        unique = set(flags)
        fatal = any(flag.startswith(("NO_BARS", "NON_MONOTONIC", "INVALID_OHLC", "INCONSISTENT_OHLC")) for flag in unique)
        major = sum(
            flag.startswith(("INSUFFICIENT", "OPEN_CANDLE", "DUPLICATE", "IRREGULAR", "OI_MISSING", "QUOTE_VOLUME_MISSING", "TRADES_MISSING"))
            for flag in unique
        )
        if fatal:
            reliability = Reliability.UNUSABLE
            cap = Confidence.LOW
        elif major >= 3:
            reliability = Reliability.LOW
            cap = Confidence.LOW
        elif major or len(unique) >= 4:
            reliability = Reliability.MEDIUM
            cap = Confidence.MEDIUM
        else:
            reliability = Reliability.HIGH
            cap = Confidence.HIGH
        return QualityReport(tuple(sorted(unique)), reliability, cap, not fatal and len(closed) >= 2, len(closed), self.config.interval_ms)

# =============================================================================
# SOURCE: causal_upside/detector.py
# =============================================================================
import math
import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence


ACTIVE_STATES = {"ELEVATED", "SHOCK", "EXTREME"}
SHOCK_STATES = {"SHOCK", "EXTREME"}
FAILURE_HYPOTHESES = {
    Hypothesis.TRANSIENT_EXECUTION_SPIKE,
    Hypothesis.FAILED_FLASH,
    Hypothesis.SHORT_COVERING_ONLY,
    Hypothesis.LATE_CROWDING,
    Hypothesis.DISTRIBUTION,
}
RULE_SCOPE: dict[Hypothesis, tuple[RuleStatus, str]] = {
    Hypothesis.QUIET_ACCUMULATION: (RuleStatus.BACKGROUND_CONCEPT, "generic adaptive hypothesis; cross-symbol controls required"),
    Hypothesis.OI_RESET_ABSORPTION_REBUILD: (RuleStatus.RESEARCH_HYPOTHESIS, "repository mechanism; production sufficiency unproven"),
    Hypothesis.PRICE_LED_BASE_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "ordered price/execution/OI context; independent validation pending"),
    Hypothesis.PRICE_LED_VACUUM_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "exception path; OI non-expansion is not confirmation"),
    Hypothesis.HIGH_OI_COMPRESSION: (RuleStatus.BACKGROUND_CONCEPT, "context pattern, not directional proof"),
    Hypothesis.WHALE_DIVERGENCE_BUILD: (RuleStatus.RESEARCH_HYPOTHESIS, "positioning divergence is ambiguous without acceptance"),
    Hypothesis.COLD_START_OI_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "sparse-history path with confidence cap"),
    Hypothesis.POST_IGNITION_FUEL_RETENTION: (RuleStatus.RESEARCH_HYPOTHESIS, "TLM-restricted context; no cross-symbol promotion"),
    Hypothesis.SHORT_COVERING_ONLY: (RuleStatus.REJECTED_RULE, "rejected as an outcome discriminator in TLM replay"),
    Hypothesis.TRANSIENT_EXECUTION_SPIKE: (RuleStatus.RESEARCH_HYPOTHESIS, "TLM-restricted failure warning"),
    Hypothesis.LATE_CROWDING: (RuleStatus.BACKGROUND_CONCEPT, "risk overlay"),
    Hypothesis.DISTRIBUTION: (RuleStatus.BACKGROUND_CONCEPT, "risk overlay"),
    Hypothesis.FAILED_FLASH: (RuleStatus.RESEARCH_HYPOTHESIS, "failure/noise explanation"),
    Hypothesis.NEW_UNIDENTIFIED_STRUCTURE: (RuleStatus.RESEARCH_HYPOTHESIS, "mandatory abstention hypothesis"),
}


@dataclass(frozen=True, slots=True)
class StructuralContext:
    segment: int
    base_detected: bool
    base_high: float
    base_low: float
    breakout: bool
    accepted: bool
    close_to_footprint: bool
    distance_rank: float | None
    recent_oi_flush: bool
    oi_reload: bool
    price_leads_oi: bool
    execution_confirmed: bool
    top_position_retained: bool | None
    crowd_compressing: bool | None
    prior_execution_shock: bool
    prior_price_shock: bool


def _active(metric: object) -> bool:
    return getattr(metric, "state", "UNKNOWN") in ACTIVE_STATES


def _shock(metric: object) -> bool:
    return getattr(metric, "state", "UNKNOWN") in SHOCK_STATES


def _median(values: Iterable[float | None]) -> float | None:
    data = [float(value) for value in values if finite(value)]
    return statistics.median(data) if data else None


def _evidence(category: str, observation: str, timestamp_ms: int, strength: str = "CONTEXT", status: RuleStatus = RuleStatus.RESEARCH_HYPOTHESIS) -> EvidenceItem:
    return EvidenceItem(category, observation, timestamp_ms, strength, status)


class CausalUpsideDetector:
    """Single final decision path shared by live scan and blind replay."""

    def __init__(self, config: ScannerConfig):
        self.config = config.validate()
        self.features = AdaptiveFeatureEngine(config)
        self.quality = DataQualityChecker(config)

    def _context(self, bars: Sequence[MarketBar], current: FeatureSnapshot, timeline: Sequence[FeatureSnapshot]) -> StructuralContext:
        segment = max(4, int(math.sqrt(len(bars))))
        pre = list(bars[-2 * segment : -segment]) if len(bars) >= 2 * segment else list(bars[:-segment])
        pre = pre or list(bars[:-1])
        ranges = [(bar.high - bar.low) / abs(bar.close) for bar in bars[:-1] if bar.close]
        pre_ranges = [(bar.high - bar.low) / abs(bar.close) for bar in pre if bar.close]
        base_detected = (
            _median(pre_ranges) is not None
            and _median(ranges) is not None
            and float(_median(pre_ranges)) <= float(_median(ranges))
            and current.compression_persistence is not None
            and current.compression_persistence >= 0.5
        )
        base_high = max((bar.high for bar in pre), default=bars[-2].high)
        base_low = min((bar.low for bar in pre), default=bars[-2].low)
        breakout = bars[-1].close > base_high
        locations = [
            (bar.close - bar.low) / (bar.high - bar.low)
            for bar in bars[:-1]
            if bar.high > bar.low
        ]
        location_rank = percentile(locations, current.close_location) if locations and current.close_location is not None else None
        accepted = breakout and location_rank is not None and location_rank >= 0.5
        distance = abs(bars[-1].close - base_high) / abs(bars[-1].close) if bars[-1].close else None
        distance_rank = percentile(ranges, distance) if ranges and distance is not None else None
        recent = list(timeline[-2 * segment :])
        flush_positions = [
            index for index, item in enumerate(recent)
            if item.oi_return.direction == "DOWN" and _shock(item.oi_return)
        ]
        recent_oi_flush = bool(flush_positions)
        oi_reload = recent_oi_flush and current.oi_slope is not None and current.oi_slope > 0 and current.oi_return.direction == "UP"
        price_leads_oi = current.price_return.direction == "UP" and _active(current.price_return) and not (
            current.oi_return.direction == "UP" and _active(current.oi_return)
        )
        top_history = [bar.top_position_ls for bar in bars[:-1] if finite(bar.top_position_ls)]
        retained = None
        if finite(bars[-1].top_position_ls) and top_history:
            retained = float(bars[-1].top_position_ls) >= statistics.median(float(value) for value in top_history)
            retained = retained and not (current.top_position_ls_change.direction == "DOWN" and _shock(current.top_position_ls_change))
        crowd = None
        if finite(bars[-1].global_ls) and finite(bars[-1].top_account_ls):
            crowd = current.global_ls_change.direction == "DOWN" and current.top_account_ls_change.direction == "DOWN"
        return StructuralContext(
            segment=segment,
            base_detected=base_detected,
            base_high=base_high,
            base_low=base_low,
            breakout=breakout,
            accepted=accepted,
            close_to_footprint=distance_rank is None or distance_rank < self.config.adaptive_quantiles[1],
            distance_rank=distance_rank,
            recent_oi_flush=recent_oi_flush,
            oi_reload=oi_reload,
            price_leads_oi=price_leads_oi,
            execution_confirmed=_active(current.trades) and _active(current.quote_volume),
            top_position_retained=retained,
            crowd_compressing=crowd,
            prior_execution_shock=any(_shock(item.trades) and _shock(item.quote_volume) for item in recent[:-1]),
            prior_price_shock=any(item.price_return.direction == "UP" and _shock(item.price_return) for item in recent[:-1]),
        )

    def _candidate(
        self,
        hypothesis: Hypothesis,
        timestamp_ms: int,
        checks: Sequence[tuple[bool | None, str, str, str, str]],
        *,
        invalidated: bool = False,
    ) -> HypothesisAssessment:
        status, scope = RULE_SCOPE[hypothesis]
        supporting: list[EvidenceItem] = []
        opposing: list[EvidenceItem] = []
        missing: list[str] = []
        for condition, category, positive, negative, strength in checks:
            if condition is True:
                supporting.append(_evidence(category, positive, timestamp_ms, strength, status))
            elif condition is False:
                opposing.append(_evidence(category, negative, timestamp_ms, "CONTEXT", status))
            else:
                missing.append(positive)
        return HypothesisAssessment(
            hypothesis=hypothesis,
            rule_status=status,
            supporting=tuple(supporting),
            opposing=tuple(opposing),
            missing=tuple(sorted(set(missing))),
            invalidated=invalidated,
            research_scope=scope,
        )

    def _hypotheses(self, bars: Sequence[MarketBar], feature: FeatureSnapshot, context: StructuralContext) -> list[HypothesisAssessment]:
        timestamp = bars[-1].timestamp_ms
        price_up = feature.price_return.direction == "UP" and _active(feature.price_return)
        oi_up = feature.oi_return.direction == "UP" and _active(feature.oi_return)
        oi_down = feature.oi_return.direction == "DOWN"
        price_resilient = feature.price_slope is not None and feature.price_slope >= 0
        high_oi = _active(feature.oi_level)
        execution_retained = None if feature.execution_retention is None else feature.execution_retention >= 0
        close_below_base = bars[-1].close < context.base_low
        candidates = [
            self._candidate(Hypothesis.QUIET_ACCUMULATION, timestamp, [
                (context.base_detected, "price", "persistent symbol-relative compression", "no persistent compression base", "STRONG"),
                (None if feature.oi_slope is None else feature.oi_slope >= 0, "oi", "OI stable or rising through base", "OI contracts through base", "CONTEXT"),
                (context.top_position_retained, "positioning", "top-position exposure retained", "top-position exposure did not retain", "CONTEXT"),
            ], invalidated=context.breakout),
            self._candidate(Hypothesis.OI_RESET_ABSORPTION_REBUILD, timestamp, [
                (context.recent_oi_flush, "oi", "recent symbol-relative OI flush", "no recent OI flush", "STRONG"),
                (price_resilient, "price", "price remained resilient or recovered after reset", "price has not recovered", "STRONG"),
                (None if feature.oi_slope is None else context.oi_reload, "oi", "OI reload followed the flush", "no constructive OI reload", "STRONG"),
            ]),
            self._candidate(Hypothesis.PRICE_LED_BASE_IGNITION, timestamp, [
                (context.base_detected, "price", "ignition emerged from a compression base", "no causal base", "STRONG"),
                (context.breakout, "price", "closed above the causal base high", "no closed breakout", "STRONG"),
                (price_up, "price", "upward move is exceptional to symbol history", "price move is not exceptional", "STRONG"),
                (context.execution_confirmed, "execution", "trade count and quote value confirm activation", "execution lacks two-channel confirmation", "STRONG"),
                (context.price_leads_oi or oi_up, "oi", "OI lagged price or reloaded constructively", "OI path is destructive or unresolved", "CONTEXT"),
                (context.accepted, "acceptance", "close location accepted the breakout", "breakout was not accepted", "STRONG"),
            ], invalidated=close_below_base),
            self._candidate(Hypothesis.PRICE_LED_VACUUM_IGNITION, timestamp, [
                (context.base_detected, "price", "vacuum path started from a base", "no causal base", "CONTEXT"),
                (context.breakout and price_up, "price", "price led the break", "no price-led break", "STRONG"),
                (context.execution_confirmed, "execution", "notional execution confirms activity", "execution lacks confirmation", "STRONG"),
                (oi_down and not _shock(feature.oi_return), "oi", "OI stayed slightly lower without a flush", "OI path does not match vacuum context", "CONTEXT"),
                (context.accepted, "acceptance", "price accepted above the base", "price did not accept above base", "STRONG"),
            ], invalidated=close_below_base),
            self._candidate(Hypothesis.HIGH_OI_COMPRESSION, timestamp, [
                (context.base_detected, "price", "price remains compressed", "price is not compressed", "STRONG"),
                (None if feature.oi_level.value is None else high_oi, "oi", "OI level is elevated relative to symbol history", "OI level is not elevated", "STRONG"),
            ], invalidated=context.breakout),
            self._candidate(Hypothesis.WHALE_DIVERGENCE_BUILD, timestamp, [
                (context.crowd_compressing, "positioning", "global and top-account ratios contracted", "crowd/account ratios are not compressing", "STRONG"),
                (context.top_position_retained, "positioning", "top-position ratio retained during account compression", "top-position exposure did not retain", "STRONG"),
                (price_resilient, "price", "price remained resilient during positioning divergence", "price weakened during divergence", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.COLD_START_OI_IGNITION, timestamp, [
                (not feature.oi_return.warm, "quality", "OI history is in cold-start warm-up", "OI history is mature", "CONTEXT"),
                (context.breakout and price_up, "price", "price ignition is visible despite immature OI history", "no price ignition", "STRONG"),
                (context.execution_confirmed, "execution", "execution confirms cold-start activity", "execution lacks confirmation", "STRONG"),
            ]),
            self._candidate(Hypothesis.POST_IGNITION_FUEL_RETENTION, timestamp, [
                (context.accepted, "acceptance", "ignition remains accepted", "no accepted ignition", "STRONG"),
                (None if feature.price_slope is None else feature.price_slope > 0, "price", "price trajectory retains fuel", "price trajectory lost fuel", "CONTEXT"),
                (None if feature.oi_slope is None else feature.oi_slope > 0, "oi", "OI trajectory retains fuel", "OI trajectory lost fuel", "CONTEXT"),
                (execution_retained, "execution", "execution has not decayed below baseline", "execution decayed after activation", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.SHORT_COVERING_ONLY, timestamp, [
                (price_up and oi_down, "mechanism", "price rose while OI contracted", "price/OI path is not short-covering-only", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "execution decayed during the rise", "execution did not decay", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.TRANSIENT_EXECUTION_SPIKE, timestamp, [
                (context.prior_execution_shock, "execution", "recent execution shock was observed", "no recent execution shock", "STRONG"),
                (not context.accepted and not oi_up, "failure", "shock lacks price acceptance and OI support", "price acceptance or OI support survived", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "execution decayed after the spike", "execution retained", "STRONG"),
            ]),
            self._candidate(Hypothesis.LATE_CROWDING, timestamp, [
                (None if context.distance_rank is None else context.distance_rank >= self.config.adaptive_quantiles[1], "freshness", "price is extended from the original footprint", "price remains near the footprint", "STRONG"),
                (high_oi and feature.global_ls_change.direction == "UP", "crowding", "OI and crowd participation expanded late", "no late OI/crowd expansion", "STRONG"),
            ]),
            self._candidate(Hypothesis.FAILED_FLASH, timestamp, [
                (context.prior_price_shock and not context.accepted, "failure", "prior price shock failed to retain base acceptance", "no rejected flash sequence", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "post-shock execution retention is negative", "execution retained", "STRONG"),
            ]),
        ]
        status, scope = RULE_SCOPE[Hypothesis.NEW_UNIDENTIFIED_STRUCTURE]
        candidates.append(HypothesisAssessment(
            hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
            rule_status=status,
            supporting=(_evidence("governance", "unidentified structure remains an active alternative", timestamp),),
            research_scope=scope,
        ))
        return candidates

    @staticmethod
    def _select(candidates: Sequence[HypothesisAssessment]) -> tuple[HypothesisAssessment, tuple[HypothesisAssessment, ...], HypothesisAssessment]:
        usable = [candidate for candidate in candidates if not candidate.invalidated]
        unidentified = next(candidate for candidate in candidates if candidate.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE)
        failures = [candidate for candidate in usable if candidate.hypothesis in FAILURE_HYPOTHESES]
        positives = [candidate for candidate in usable if candidate.hypothesis not in FAILURE_HYPOTHESES and candidate.hypothesis != Hypothesis.NEW_UNIDENTIFIED_STRUCTURE]
        failure = max(failures, key=lambda item: item.evidence_balance, default=unidentified)
        ordered = sorted(positives, key=lambda item: item.evidence_balance, reverse=True)
        if not ordered or ordered[0].evidence_balance[1] <= 0:
            dominant = unidentified
        elif len(ordered) > 1 and ordered[0].evidence_balance == ordered[1].evidence_balance:
            dominant = unidentified
        elif failure.evidence_balance > ordered[0].evidence_balance:
            dominant = unidentified
        else:
            dominant = ordered[0]
        alternatives = tuple(
            candidate for candidate in sorted(usable, key=lambda item: item.evidence_balance, reverse=True)
            if candidate.hypothesis != dominant.hypothesis
        )[:3]
        return dominant, alternatives, failure

    @staticmethod
    def _decision(dominant: HypothesisAssessment, failure: HypothesisAssessment, context: StructuralContext, quality: QualityReport) -> tuple[CampaignState, Readiness, str, str, str, str, str | None]:
        if not quality.usable:
            return CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT_FOR_VALID_DATA", "restore valid chronological closed-bar coverage", "data quality is unusable"
        if dominant.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE:
            return CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT", "wait for a discriminating ordered sequence", "no hypothesis dominates materially"
        if failure.hypothesis in {Hypothesis.TRANSIENT_EXECUTION_SPIKE, Hypothesis.FAILED_FLASH} and failure.evidence_balance[0] >= 2:
            return CampaignState.FAILURE, Readiness.FAILED, "FAILURE_RISK", "HIGH", "AVOID", "price acceptance and execution/OI retention must recover", None
        mapping = {
            Hypothesis.QUIET_ACCUMULATION: (CampaignState.EARLY_BUILD, Readiness.EARLY_BUILD, "EARLY_BULLISH_STRUCTURE", "MEDIUM", "WAIT_FOR_CONFIRMATION"),
            Hypothesis.HIGH_OI_COMPRESSION: (CampaignState.CONFIRMED_BUILD, Readiness.CONFIRMED_BUILD, "NEUTRAL_TO_BULLISH_COMPRESSION", "MEDIUM", "WAIT_FOR_DIRECTION"),
            Hypothesis.WHALE_DIVERGENCE_BUILD: (CampaignState.CONFIRMED_BUILD, Readiness.CONFIRMED_BUILD, "EARLY_BULLISH_STRUCTURE", "MEDIUM", "WAIT_FOR_ACCEPTANCE"),
            Hypothesis.OI_RESET_ABSORPTION_REBUILD: (CampaignState.REBUILD, Readiness.CONFIRMED_BUILD, "EARLY_BULLISH_STRUCTURE", "HIGH", "WAIT_FOR_IGNITION"),
            Hypothesis.PRICE_LED_BASE_IGNITION: (CampaignState.ACCEPTED_IGNITION if context.accepted else CampaignState.IGNITION_CANDIDATE, Readiness.ACCEPTED if context.accepted else Readiness.LIVE_IGNITION, "BULLISH_IGNITION_CONTEXT", "HIGH", "CONDITIONAL_NEAR_FOOTPRINT"),
            Hypothesis.PRICE_LED_VACUUM_IGNITION: (CampaignState.ACCEPTED_IGNITION if context.accepted else CampaignState.IGNITION_CANDIDATE, Readiness.ACCEPTED if context.accepted else Readiness.LIVE_IGNITION, "EVENT_DRIVEN_BULLISH_CONTEXT", "HIGH", "HIGHER_RISK_OI_UNCONFIRMED"),
            Hypothesis.COLD_START_OI_IGNITION: (CampaignState.IGNITION_CANDIDATE, Readiness.LIVE_IGNITION, "BULLISH_COLD_START_CONTEXT", "HIGH", "HIGHER_RISK_SPARSE_HISTORY"),
            Hypothesis.POST_IGNITION_FUEL_RETENTION: (CampaignState.CONTINUATION_RELOAD, Readiness.CONTINUATION, "BULLISH_CONTINUATION_CONTEXT", "HIGH", "NO_CHASE_IF_EXTENDED"),
        }
        state, readiness, bias, importance, safety = mapping.get(dominant.hypothesis, (CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT"))
        if not context.close_to_footprint and readiness in {Readiness.LIVE_IGNITION, Readiness.ACCEPTED, Readiness.CONTINUATION}:
            readiness, safety = Readiness.LATE_NO_CHASE, "LATE_NO_CHASE"
        return state, readiness, bias, importance, safety, "confirm ordered price acceptance, execution retention, and non-destructive OI behavior", None

    @staticmethod
    def _confidence(candidate: HypothesisAssessment, quality: QualityReport) -> Confidence:
        if candidate.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE:
            raw = Confidence.LOW
        elif candidate.evidence_balance[0] >= 3 and not candidate.opposing:
            raw = Confidence.HIGH
        elif candidate.evidence_balance[0] >= 2:
            raw = Confidence.MEDIUM_HIGH
        else:
            raw = Confidence.MEDIUM
        order = [Confidence.LOW, Confidence.MEDIUM, Confidence.MEDIUM_HIGH, Confidence.HIGH]
        if candidate.rule_status in {RuleStatus.BACKGROUND_CONCEPT, RuleStatus.RESEARCH_HYPOTHESIS, RuleStatus.REJECTED_RULE} and raw == Confidence.HIGH:
            raw = Confidence.MEDIUM_HIGH
        if len(candidate.opposing) >= 2 and order.index(raw) > order.index(Confidence.MEDIUM):
            raw = Confidence.MEDIUM
        return order[min(order.index(raw), order.index(quality.confidence_cap))]

    def analyze(self, bars: Sequence[MarketBar], *, source_flags: Sequence[str] = ()) -> SignalAssessment:
        ordered = sorted((bar for bar in bars if bar.is_closed), key=lambda bar: bar.timestamp_ms)
        quality = self.quality.check(ordered, source_flags=source_flags)
        minimum = max(2, self.config.minimum_baseline_observations + 1)
        if len(ordered) < minimum:
            latest = ordered[-1] if ordered else None
            return SignalAssessment(
                symbol=latest.symbol if latest else "UNKNOWN",
                timeframe=latest.timeframe if latest else self.config.timeframe,
                cutoff_ms=latest.close_time_ms if latest else 0,
                campaign_state=CampaignState.UNRESOLVED,
                dominant_hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
                alternative_hypotheses=(),
                failure_hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
                structural_bias="UNRESOLVED",
                signal_importance="LOW",
                readiness=Readiness.UNRESOLVED,
                entry_safety="WAIT_FOR_HISTORY",
                confidence=Confidence.LOW,
                data_reliability=quality.reliability,
                supporting_evidence=(),
                opposing_evidence=(),
                missing_evidence=("causal warm-up history",),
                next_discriminator="accumulate more closed bars without gaps",
                invalidation="not applicable before warm-up",
                abstention_reason="insufficient causal baseline",
                research_status=RuleStatus.RESEARCH_HYPOTHESIS,
                campaign_age_bars=0,
                distance_from_footprint_rank=None,
                quality_flags=quality.flags,
            )
        timeline = self.features.timeline(ordered)
        context = self._context(ordered, timeline[-1], timeline)
        dominant, alternatives, failure = self._select(self._hypotheses(ordered, timeline[-1], context))
        state, readiness, bias, importance, safety, discriminator, abstention = self._decision(dominant, failure, context, quality)
        effective = failure if state in {CampaignState.FAILURE, CampaignState.DISTRIBUTION} else dominant
        missing = tuple(sorted(set(effective.missing + (() if quality.reliability == Reliability.HIGH else ("higher data reliability",)))))
        return SignalAssessment(
            symbol=ordered[-1].symbol,
            timeframe=ordered[-1].timeframe,
            cutoff_ms=ordered[-1].close_time_ms,
            campaign_state=state,
            dominant_hypothesis=effective.hypothesis,
            alternative_hypotheses=tuple(candidate.hypothesis for candidate in alternatives),
            failure_hypothesis=failure.hypothesis,
            structural_bias=bias,
            signal_importance=importance,
            readiness=readiness,
            entry_safety=safety,
            confidence=self._confidence(effective, quality),
            data_reliability=quality.reliability,
            supporting_evidence=effective.supporting,
            opposing_evidence=effective.opposing,
            missing_evidence=missing,
            next_discriminator=discriminator,
            invalidation=f"closed price below causal base low {context.base_low:.12g} or independent failure evidence dominates",
            abstention_reason=abstention,
            research_status=effective.rule_status,
            campaign_age_bars=min(len(ordered), max(1, 2 * context.segment)),
            distance_from_footprint_rank=context.distance_rank,
            quality_flags=quality.flags,
        )

# =============================================================================
# SOURCE: causal_upside/ledger.py
# =============================================================================
import json
import os
import tempfile
from pathlib import Path



PROGRESSIVE = {
    CampaignState.LATENT: 0,
    CampaignState.EARLY_BUILD: 1,
    CampaignState.CONFIRMED_BUILD: 2,
    CampaignState.REBUILD: 2,
    CampaignState.ARMED: 3,
    CampaignState.IGNITION_CANDIDATE: 4,
    CampaignState.ACCEPTED_IGNITION: 5,
    CampaignState.EXPANSION: 6,
    CampaignState.CONTINUATION_RELOAD: 7,
    CampaignState.COOLING: 7,
    CampaignState.RESET: 1,
    CampaignState.FAILURE: -1,
    CampaignState.DISTRIBUTION: -1,
    CampaignState.UNRESOLVED: 0,
}


class LedgerStore:
    def __init__(self, config: ScannerConfig):
        self.config = config.validate()
        self.root = self.config.state_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, symbol: str, timeframe: str) -> Path:
        safe = "".join(char for char in f"{symbol}_{timeframe}" if char.isalnum() or char in "-_")
        return self.root / f"{safe}.json"

    def load(self, symbol: str, timeframe: str) -> CampaignLedger | None:
        path = self.path(symbol, timeframe)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if int(value.get("schema_version", -1)) != self.config.ledger_schema_version:
            raise ValueError(f"Unsupported ledger schema in {path}")
        value["state"] = CampaignState(value["state"])
        value["dominant_hypothesis"] = Hypothesis(value["dominant_hypothesis"])
        value["alternatives"] = [Hypothesis(item) for item in value.get("alternatives", [])]
        return CampaignLedger(**value)

    def save(self, ledger: CampaignLedger) -> None:
        path = self.path(ledger.symbol, ledger.timeframe)
        payload = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def update(self, assessment: SignalAssessment) -> CampaignLedger:
        prior = self.load(assessment.symbol, assessment.timeframe)
        if prior and assessment.cutoff_ms <= prior.last_observed_ms:
            return prior
        if prior is None:
            ledger = CampaignLedger(
                schema_version=self.config.ledger_schema_version,
                symbol=assessment.symbol,
                timeframe=assessment.timeframe,
                campaign_id=f"{assessment.symbol}-{assessment.timeframe}-{assessment.cutoff_ms}",
                state=CampaignState.LATENT,
                birth_ms=assessment.cutoff_ms,
                last_observed_ms=assessment.cutoff_ms,
            )
        else:
            ledger = prior

        proposed = assessment.campaign_state
        negative = proposed in {CampaignState.FAILURE, CampaignState.DISTRIBUTION}
        independent_negative_categories = {item.category for item in assessment.opposing_evidence}
        strong_failure_categories = {item.category for item in assessment.supporting_evidence if item.strength == "STRONG"} if negative else set()
        if negative and len(strong_failure_categories | independent_negative_categories) >= 2:
            ledger.contradiction_streak += 1
        elif negative:
            ledger.contradiction_streak = max(ledger.contradiction_streak, 1)
        else:
            ledger.contradiction_streak = 0

        previous_state = ledger.state
        if negative and ledger.state not in {CampaignState.LATENT, CampaignState.UNRESOLVED} and ledger.contradiction_streak < 2:
            next_state = CampaignState.COOLING
        elif proposed == CampaignState.UNRESOLVED and PROGRESSIVE.get(ledger.state, 0) > 0:
            next_state = ledger.state
        elif PROGRESSIVE.get(proposed, 0) >= PROGRESSIVE.get(ledger.state, 0) or negative:
            next_state = proposed
        else:
            next_state = CampaignState.COOLING

        ledger.state = next_state
        ledger.last_observed_ms = assessment.cutoff_ms
        ledger.dominant_hypothesis = assessment.dominant_hypothesis
        ledger.alternatives = list(assessment.alternative_hypotheses)
        ledger.last_assessment = assessment.to_dict()
        if ledger.first_detection_ms is None and next_state not in {CampaignState.LATENT, CampaignState.UNRESOLVED}:
            ledger.first_detection_ms = assessment.cutoff_ms
        if ledger.first_warning_ms is None and assessment.readiness in {Readiness.CONFIRMED_BUILD, Readiness.ARMED, Readiness.LIVE_IGNITION, Readiness.ACCEPTED}:
            ledger.first_warning_ms = assessment.cutoff_ms
        timestamp_fields = {
            CampaignState.ARMED: "armed_ms",
            CampaignState.IGNITION_CANDIDATE: "ignition_ms",
            CampaignState.ACCEPTED_IGNITION: "acceptance_ms",
            CampaignState.EXPANSION: "expansion_ms",
            CampaignState.COOLING: "weakness_ms",
            CampaignState.FAILURE: "failure_ms",
            CampaignState.RESET: "reset_ms",
            CampaignState.REBUILD: "rebuild_ms",
        }
        field = timestamp_fields.get(next_state)
        if field and getattr(ledger, field) is None:
            setattr(ledger, field, assessment.cutoff_ms)
        if previous_state != next_state:
            ledger.transition_history.append(
                {
                    "timestamp_ms": assessment.cutoff_ms,
                    "from_state": previous_state.value,
                    "to_state": next_state.value,
                    "dominant_hypothesis": assessment.dominant_hypothesis.value,
                    "supporting_categories": sorted({item.category for item in assessment.supporting_evidence}),
                    "opposing_categories": sorted({item.category for item in assessment.opposing_evidence}),
                    "quality_flags": list(assessment.quality_flags),
                }
            )
        self.save(ledger)
        return ledger

# =============================================================================
# SOURCE: causal_upside/service.py
# =============================================================================
import csv
import json
import logging
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Sequence



READINESS_PRIORITY = {
    Readiness.ARMED: 0,
    Readiness.LIVE_IGNITION: 1,
    Readiness.ACCEPTED: 2,
    Readiness.CONFIRMED_BUILD: 3,
    Readiness.EARLY_BUILD: 4,
    Readiness.CONTINUATION: 5,
    Readiness.COOLING: 6,
    Readiness.LATE_NO_CHASE: 7,
    Readiness.UNRESOLVED: 8,
    Readiness.FAILED: 9,
}


class AtomicOutput:
    @staticmethod
    def write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class ScannerService:
    def __init__(self, config: ScannerConfig, *, client: BinancePublicClient | None = None):
        self.config = config.validate()
        self.client = client or BinancePublicClient(config)
        self.detector = CausalUpsideDetector(config)
        self.ledger = LedgerStore(config)

    def _analyze(self, symbol: str) -> SignalAssessment | None:
        try:
            fetched = self.client.fetch_symbol(symbol)
            if not fetched.bars:
                return None
            assessment = self.detector.analyze(fetched.bars, source_flags=fetched.flags)
            self.ledger.update(assessment)
            return assessment
        except Exception:
            logging.exception("Symbol analysis failed: %s", symbol)
            return None

    def scan(self, symbols: Sequence[str] | None = None) -> list[SignalAssessment]:
        universe = list(symbols) if symbols is not None else self.client.symbols()
        results: list[SignalAssessment] = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers, thread_name_prefix="upside-scan") as executor:
            futures = {executor.submit(self._analyze, symbol): symbol for symbol in universe}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
        results.sort(
            key=lambda item: (
                READINESS_PRIORITY[item.readiness],
                0 if item.entry_safety.startswith("CONDITIONAL") else 1,
                -len(item.supporting_evidence),
                len(item.opposing_evidence),
                item.symbol,
            )
        )
        selected = results[: self.config.top_n]
        self.write_results(selected)
        return selected

    def write_results(self, assessments: Sequence[SignalAssessment]) -> None:
        payload = [item.to_dict() for item in assessments]
        AtomicOutput.write_text(
            self.config.output_dir / "latest_assessments.json",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        rows = []
        for item in assessments:
            rows.append(
                {
                    "symbol": item.symbol,
                    "timeframe": item.timeframe,
                    "cutoff_ms": item.cutoff_ms,
                    "campaign_state": item.campaign_state.value,
                    "dominant_hypothesis": item.dominant_hypothesis.value,
                    "alternatives": "|".join(value.value for value in item.alternative_hypotheses),
                    "failure_hypothesis": item.failure_hypothesis.value,
                    "structural_bias": item.structural_bias,
                    "signal_importance": item.signal_importance,
                    "readiness": item.readiness.value,
                    "entry_safety": item.entry_safety,
                    "confidence": item.confidence.value,
                    "data_reliability": item.data_reliability.value,
                    "research_status": item.research_status.value,
                    "supporting_evidence": "|".join(value.observation for value in item.supporting_evidence),
                    "opposing_evidence": "|".join(value.observation for value in item.opposing_evidence),
                    "missing_evidence": "|".join(item.missing_evidence),
                    "next_discriminator": item.next_discriminator,
                    "invalidation": item.invalidation,
                    "abstention_reason": item.abstention_reason or "",
                    "quality_flags": "|".join(item.quality_flags),
                }
            )
        if rows:
            import io

            path = self.config.output_dir / "latest_assessments.csv"
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            AtomicOutput.write_text(path, stream.getvalue())


class ReplayService:
    """Blind replay through the same production detector path."""

    FIELD_ALIASES = {
        "timestamp_ms": ("timestamp_ms", "timestamp", "open_time"),
        "close_time_ms": ("close_time_ms", "close_time"),
        "is_closed": ("is_closed_candle", "is_closed"),
        "trades": ("number_of_trades", "trades"),
        "quote_volume": ("quote_volume",),
        "taker_buy_quote": ("taker_buy_quote_volume", "taker_buy_quote"),
        "oi": ("oi", "open_interest"),
        "global_ls": ("global_ls_ratio", "global_long_short_ratio", "global_ls", "global_lsr"),
        "top_account_ls": ("acco_ls_ratio", "top_account_long_short_ratio", "top_account_ls", "account_lsr"),
        "top_position_ls": ("posit_ls_ratio", "top_position_long_short_ratio", "top_position_ls", "position_lsr"),
        "funding_rate": ("funding_rate", "last_funding_rate"),
    }

    def __init__(self, config: ScannerConfig):
        replay_config = replace(config.validate(), state_dir=config.state_dir / "replay")
        self.config = replay_config
        self.detector = CausalUpsideDetector(replay_config)

    @staticmethod
    def _number(row: dict[str, str], names: Iterable[str], *, required: bool = False) -> float | None:
        for name in names:
            value = row.get(name)
            if value not in (None, ""):
                try:
                    number = float(value)
                    return number if math.isfinite(number) else None
                except ValueError:
                    continue
        if required:
            raise ValueError(f"Required numeric field missing: {tuple(names)}")
        return None

    @staticmethod
    def _boolean(value: str | None) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def load_csv(self, path: Path, *, symbol: str | None = None, timeframe: str | None = None) -> list[MarketBar]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        bars: list[MarketBar] = []
        for row in rows:
            timestamp = int(self._number(row, self.FIELD_ALIASES["timestamp_ms"], required=True) or 0)
            close_time = int(self._number(row, self.FIELD_ALIASES["close_time_ms"]) or timestamp + self.config.interval_ms - 1)
            closed_value = next((row.get(name) for name in self.FIELD_ALIASES["is_closed"] if name in row), "true")
            if not self._boolean(closed_value):
                continue

            def optional(field: str) -> float | None:
                return self._number(row, self.FIELD_ALIASES[field])

            bars.append(
                MarketBar(
                    symbol=symbol or row.get("symbol") or path.name.split("_")[0],
                    timeframe=timeframe or row.get("timeframe") or self.config.timeframe,
                    timestamp_ms=timestamp,
                    close_time_ms=close_time,
                    is_closed=True,
                    open=float(self._number(row, ("open",), required=True)),
                    high=float(self._number(row, ("high",), required=True)),
                    low=float(self._number(row, ("low",), required=True)),
                    close=float(self._number(row, ("close",), required=True)),
                    volume=self._number(row, ("volume",)),
                    quote_volume=optional("quote_volume"),
                    trades=optional("trades"),
                    taker_buy_quote=optional("taker_buy_quote"),
                    oi=optional("oi"),
                    global_ls=optional("global_ls"),
                    top_account_ls=optional("top_account_ls"),
                    top_position_ls=optional("top_position_ls"),
                    funding_rate=optional("funding_rate"),
                )
            )
        deduplicated = {item.timestamp_ms: item for item in bars}
        return [deduplicated[key] for key in sorted(deduplicated)]

    def run(self, bars: Sequence[MarketBar], output_path: Path) -> list[SignalAssessment]:
        records: list[SignalAssessment] = []
        minimum = max(self.config.min_history, self.config.minimum_baseline_observations + 1)
        for end in range(minimum, len(bars) + 1):
            records.append(self.detector.analyze(bars[:end]))
        AtomicOutput.write_text(
            output_path,
            "".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        )
        return records

# =============================================================================
# EDITOR-FIRST SETTINGS, ARABIC OUTPUT, AND AUTO-RUN
# =============================================================================
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence



# =============================================================================
# EDITOR SETTINGS
# Fixed values here are operational controls only. Structural thresholds remain
# adaptive to each symbol's own causal history inside causal_upside/adaptive.py.
# =============================================================================
SETTINGS: dict[str, Any] = {
    # Execution
    "AUTO_RUN": True,
    "RUN_CONTINUOUSLY": True,
    "SCAN_INTERVAL_SECONDS": 180,

    # Market window
    "TIMEFRAME": "15m",
    "CANDLES": 200,
    "MIN_HISTORY": 80,

    # Universe
    "SCAN_ALL_USDT_PERPETUALS": True,
    "SYMBOL_WHITELIST": [],  # Example: ["AKEUSDT", "TLMUSDT"]
    "SYMBOL_BLACKLIST": ["BTCUSDT", "ETHUSDT"],

    # Runtime and Binance public API
    "MAX_WORKERS": 8,
    "REQUEST_TIMEOUT": 12.0,
    "RETRIES": 3,
    "BACKOFF_BASE": 0.5,
    "MAX_REQUESTS_PER_SECOND": 8.0,
    "INCLUDE_FUNDING": True,
    "MAX_ALIGNMENT_AGE_INTERVALS": 1,

    # Output
    "TOP_N": 30,
    "STATE_DIR": "causal_upside_state",
    "OUTPUT_DIR": "causal_upside_output",
    "PRINT_EVIDENCE_LIMIT": 3,
    "PRINT_MISSING_LIMIT": 4,
    "LOG_LEVEL": "INFO",
}


READINESS_AR = {
    Readiness.ARMED: "مسلح / قريب من الاشتعال",
    Readiness.LIVE_IGNITION: "اشتعال حي",
    Readiness.ACCEPTED: "اشتعال مقبول",
    Readiness.CONFIRMED_BUILD: "بناء مؤكد",
    Readiness.EARLY_BUILD: "بناء مبكر",
    Readiness.CONTINUATION: "استمرار / إعادة تحميل",
    Readiness.COOLING: "تبريد مع بقاء الهيكل",
    Readiness.LATE_NO_CHASE: "متأخر - لا مطاردة",
    Readiness.UNRESOLVED: "غير محسوم",
    Readiness.FAILED: "فشل / توزيع",
}


def _symbols(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip().upper() for value in values if str(value).strip()}))


def build_config(settings: Mapping[str, Any] = SETTINGS) -> ScannerConfig:
    """Translate editor settings into the validated production configuration."""
    history_limit = int(settings["CANDLES"])
    if not 20 <= history_limit <= 500:
        raise ValueError("CANDLES must be between 20 and 500 for aligned Binance history endpoints")
    whitelist = _symbols(settings.get("SYMBOL_WHITELIST", ()))
    scan_all = bool(settings.get("SCAN_ALL_USDT_PERPETUALS", True))
    if not scan_all and not whitelist:
        raise ValueError("Set SYMBOL_WHITELIST when SCAN_ALL_USDT_PERPETUALS is False")
    return ScannerConfig(
        timeframe=str(settings["TIMEFRAME"]),
        history_limit=history_limit,
        min_history=int(settings["MIN_HISTORY"]),
        max_workers=int(settings["MAX_WORKERS"]),
        request_timeout=float(settings["REQUEST_TIMEOUT"]),
        retries=int(settings["RETRIES"]),
        backoff_base=float(settings["BACKOFF_BASE"]),
        max_requests_per_second=float(settings["MAX_REQUESTS_PER_SECOND"]),
        top_n=int(settings["TOP_N"]),
        state_dir=Path(str(settings["STATE_DIR"])),
        output_dir=Path(str(settings["OUTPUT_DIR"])),
        whitelist=whitelist,
        blacklist=_symbols(settings.get("SYMBOL_BLACKLIST", ())),
        scan_all_usdt_perpetuals=scan_all,
        include_funding=bool(settings.get("INCLUDE_FUNDING", True)),
        max_alignment_age_intervals=int(settings.get("MAX_ALIGNMENT_AGE_INTERVALS", 1)),
    ).validate()


def _utc_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _short(text: str, limit: int = 150) -> str:
    clean = " ".join(str(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def _list_text(values: Sequence[str], limit: int, *, empty: str = "لا يوجد") -> str:
    selected = [_short(value) for value in values[: max(0, limit)]]
    return " | ".join(selected) if selected else empty


def assessment_lines(
    item: SignalAssessment,
    rank: int,
    *,
    evidence_limit: int,
    missing_limit: int,
) -> list[str]:
    """Render one explainable assessment without converting it into a trade call."""
    support = [evidence.observation for evidence in item.supporting_evidence]
    oppose = [evidence.observation for evidence in item.opposing_evidence]
    distance = "غير متاح" if item.distance_from_footprint_rank is None else f"{item.distance_from_footprint_rank:.3f}"
    alternatives = ", ".join(value.value for value in item.alternative_hypotheses) or "لا يوجد"
    flags = ", ".join(item.quality_flags) or "لا توجد أعلام جوهرية"
    return [
        f"[{rank:02d}] {item.symbol} | {READINESS_AR[item.readiness]} ({item.readiness.value})",
        f"     الفرضية: {item.dominant_hypothesis.value} | البدائل: {alternatives}",
        f"     الفشل المرجح: {item.failure_hypothesis.value}",
        f"     الانحياز: {item.structural_bias} | الأهمية: {item.signal_importance}",
        f"     أمان الدخول: {item.entry_safety} | الثقة: {item.confidence.value} | موثوقية البيانات: {item.data_reliability.value}",
        f"     عمر الحملة: {item.campaign_age_bars} شمعة | قرب البصمة(rank): {distance} | cutoff: {_utc_from_ms(item.cutoff_ms)}",
        f"     أدلة مؤيدة: {_list_text(support, evidence_limit)}",
        f"     أدلة معارضة: {_list_text(oppose, evidence_limit)}",
        f"     أدلة مفقودة: {_list_text(list(item.missing_evidence), missing_limit)}",
        f"     الدليل التالي المطلوب: {_short(item.next_discriminator, 220)}",
        f"     الإبطال: {_short(item.invalidation, 220)}",
        f"     حالة البحث: {item.research_status.value} | الجودة: {_short(flags, 220)}",
    ] + ([f"     سبب الامتناع: {_short(item.abstention_reason, 220)}"] if item.abstention_reason else [])


def render_console_report(
    assessments: Sequence[SignalAssessment],
    config: ScannerConfig,
    *,
    cycle: int,
    elapsed_seconds: float,
    evidence_limit: int = 3,
    missing_limit: int = 4,
) -> str:
    line = "=" * 118
    scope = "كل عقود USDT الدائمة" if config.scan_all_usdt_perpetuals else ", ".join(config.whitelist)
    output = [
        "",
        line,
        f"ماسح البصمات السابقة للصعود | الدورة {cycle} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"الفريم={config.timeframe} | الشموع المغلقة={config.history_limit} | الحد الأدنى={config.min_history} | النطاق={scope}",
        f"النتائج المعروضة={len(assessments)}/{config.top_n} | زمن الدورة={elapsed_seconds:.2f}s | المخرجات={config.output_dir}",
        "ملاحظة: النتائج تقييمات بحثية سببية وليست ضمانًا للصعود أو أمر دخول آلي.",
        line,
    ]
    if not assessments:
        output.append("لا توجد نتائج قابلة للتقييم في هذه الدورة. راجع الاتصال، أعلام الجودة، وعدد الشموع.")
        return "\n".join(output)

    for rank, item in enumerate(assessments, start=1):
        output.extend(
            assessment_lines(
                item,
                rank,
                evidence_limit=evidence_limit,
                missing_limit=missing_limit,
            )
        )
        output.append("-" * 118)
    return "\n".join(output)


class EditorScannerRunner:
    """One-process runner that preserves the production service and ledger across cycles."""

    def __init__(self, settings: Mapping[str, Any] = SETTINGS):
        self.settings = dict(settings)
        self.config = build_config(settings)
        self.service = ScannerService(self.config)
        self.explicit_symbols = None if self.config.scan_all_usdt_perpetuals else list(self.config.whitelist)
        self.cycle = 0

    def run_cycle(self) -> list[SignalAssessment]:
        self.cycle += 1
        started = time.monotonic()
        assessments = self.service.scan(self.explicit_symbols)
        elapsed = time.monotonic() - started
        report = render_console_report(
            assessments,
            self.config,
            cycle=self.cycle,
            elapsed_seconds=elapsed,
            evidence_limit=int(self.settings.get("PRINT_EVIDENCE_LIMIT", 3)),
            missing_limit=int(self.settings.get("PRINT_MISSING_LIMIT", 4)),
        )
        print(report, flush=True)
        return assessments

    def run(self) -> None:
        continuous = bool(self.settings.get("RUN_CONTINUOUSLY", True))
        interval = int(self.settings.get("SCAN_INTERVAL_SECONDS", 180))
        if continuous and interval < 1:
            raise ValueError("SCAN_INTERVAL_SECONDS must be at least 1")
        while True:
            cycle_started = time.monotonic()
            self.run_cycle()
            if not continuous:
                return
            remaining = max(0.0, interval - (time.monotonic() - cycle_started))
            next_run = datetime.now(timezone.utc) + timedelta(seconds=remaining)
            print(
                f"الدورة التالية تقريبًا: {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')} | أوقف التشغيل بواسطة Ctrl+C",
                flush=True,
            )
            time.sleep(remaining)


def configure_logging(settings: Mapping[str, Any] = SETTINGS) -> None:
    level_name = str(settings.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    configure_logging()
    try:
        EditorScannerRunner().run()
    except KeyboardInterrupt:
        print("\nتم إيقاف الماسح يدويًا مع حفظ آخر حالة ومخرجات.")
        return 0
    except Exception as exc:
        logging.exception("تعذر تشغيل الماسح: %s", exc)
        return 1
    return 0


# =============================================================================
# STANDALONE COMMAND-LINE OVERRIDES AND SELF-TEST
# =============================================================================
def _standalone_self_test() -> None:
    assert bounded_asof([1_000], [(1_001, 7.0)], max_age_ms=100) == [None]
    assert bounded_asof([1_000], [(900, 7.0)], max_age_ms=100) == [7.0]
    raw = [[0, "1", "2", "0.5", "1.5", "10", 999, "15", 4, "0", "8"],
           [1_000, "1.5", "2", "1", "1.8", "11", 2_000, "18", 5, "0", "9"]]
    bars = closed_klines(raw, symbol="TESTUSDT", timeframe="1m", now_ms=1_500)
    assert len(bars) == 1 and bars[0].is_closed
    assert RULE_SCOPE[Hypothesis.SHORT_COVERING_ONLY][0] == RuleStatus.REJECTED_RULE
    ScannerConfig(timeframe="15m", history_limit=80, min_history=40).validate()
    print("SELF-TESTS: PASS")


def standalone_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standalone causal Binance Futures upside-precursor scanner")
    parser.add_argument("--timeframe", help="Binance interval, e.g. 5m, 15m, 1h, 4h")
    parser.add_argument("--candles", type=int, help="closed candle history, 20..500")
    parser.add_argument("--symbol", action="append", default=[], help="repeat to scan an explicit whitelist")
    parser.add_argument("--once", action="store_true", help="run one scan cycle")
    parser.add_argument("--continuous", action="store_true", help="repeat scan cycles")
    parser.add_argument("--interval", type=int, help="seconds between cycle starts")
    parser.add_argument("--replay", type=Path, help="blind-replay an enriched repository CSV")
    parser.add_argument("--replay-output", type=Path, default=Path("causal_upside_output/replay.jsonl"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _standalone_self_test()
        return 0
    settings = dict(SETTINGS)
    if args.timeframe:
        settings["TIMEFRAME"] = args.timeframe
    if args.candles is not None:
        settings["CANDLES"] = args.candles
    if args.symbol:
        settings["SCAN_ALL_USDT_PERPETUALS"] = False
        settings["SYMBOL_WHITELIST"] = [value.upper() for value in args.symbol]
    if args.once:
        settings["RUN_CONTINUOUSLY"] = False
    if args.continuous:
        settings["RUN_CONTINUOUSLY"] = True
    if args.interval is not None:
        settings["SCAN_INTERVAL_SECONDS"] = args.interval
    configure_logging(settings)
    if args.replay:
        config = build_config(settings)
        replay = ReplayService(config)
        bars = replay.load_csv(args.replay, timeframe=config.timeframe)
        records = replay.run(bars, args.replay_output)
        summary = {
            "input": str(args.replay),
            "closed_bars": len(bars),
            "frozen_cutoffs": len(records),
            "output": str(args.replay_output),
            "last_assessment": records[-1].to_dict() if records else None,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    try:
        EditorScannerRunner(settings).run()
    except KeyboardInterrupt:
        print("\nتم إيقاف الماسح يدويًا مع حفظ آخر حالة ومخرجات.")
        return 0
    return 0


if __name__ == "__main__":
    if SETTINGS.get("AUTO_RUN", True) or len(sys.argv) > 1:
        raise SystemExit(standalone_cli())
    print("AUTO_RUN=False. غيّرها إلى True أو استدعِ standalone_cli() يدويًا.", file=sys.stderr)


# =============================================================================
# GENERATED BUILD METADATA
# =============================================================================
STANDALONE_BUILD = {
    "generator": "tools/build_single_file_scanner.py",
    "source_modules": ('causal_upside/config.py', 'causal_upside/models.py', 'causal_upside/alignment.py', 'causal_upside/binance.py', 'causal_upside/adaptive.py', 'causal_upside/quality.py', 'causal_upside/detector.py', 'causal_upside/ledger.py', 'causal_upside/service.py', 'run_causal_upside_scanner.py'),
    "warning": "Generated file. Edit SETTINGS only; change analytical logic in causal_upside/.",
}
