"""Bounded causal as-of alignment for Binance data families."""
from __future__ import annotations

from bisect import bisect_right
from typing import Any, Iterable, Mapping, Sequence

from .models import MarketBar


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
