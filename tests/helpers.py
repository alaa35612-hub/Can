from __future__ import annotations

from causal_upside.models import MarketBar


def make_bars(count: int = 100, *, breakout: bool = False, short_covering: bool = False) -> list[MarketBar]:
    bars: list[MarketBar] = []
    interval = 900_000
    price = 100.0
    oi = 1_000.0
    for index in range(count):
        compression = index >= count - 20 and index < count - 1
        drift = 0.02 if index % 2 == 0 else -0.015
        if compression:
            drift = 0.003 if index % 2 == 0 else -0.002
        if index == count - 1 and breakout:
            drift = 3.0
        price = max(1.0, price + drift)
        width = 0.08 if compression else 0.35
        quote = 10_000.0 + (index % 7) * 150
        trades = 100.0 + (index % 5) * 3
        if index == count - 1 and breakout:
            quote = 80_000.0
            trades = 700.0
        if short_covering and index == count - 1:
            oi *= 0.94
        else:
            oi *= 1.0003
        timestamp = index * interval
        bars.append(
            MarketBar(
                symbol="TESTUSDT",
                timeframe="15m",
                timestamp_ms=timestamp,
                close_time_ms=timestamp + interval - 1,
                is_closed=True,
                open=price - drift,
                high=max(price - drift, price) + width,
                low=min(price - drift, price) - width,
                close=price,
                volume=quote / price,
                quote_volume=quote,
                trades=trades,
                taker_buy_quote=quote * (0.56 if breakout and index == count - 1 else 0.5),
                oi=oi,
                global_ls=1.0 - index * 0.0005,
                top_account_ls=1.05 - index * 0.0004,
                top_position_ls=1.2 + index * 0.0002,
                funding_rate=0.0001,
            )
        )
    return bars
