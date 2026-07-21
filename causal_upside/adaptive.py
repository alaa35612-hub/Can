"""Historical-only adaptive features for symbol-local market structure."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .config import ScannerConfig
from .models import AdaptiveMetric, MarketBar


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
