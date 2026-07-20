# Research Data Dictionary

## Identity and chronology

`code_version`, timestamps, symbol, timeframe and `is_closed_candle` establish provenance and causal availability.

## Price and mark structure

OHLC, mark-price OHLC, premium-index fields, range, body, wicks and close location describe outcome and structural location. Price rise alone is not proof of accumulation or institutional intent.

## Execution and volume

`number_of_trades`, base/quote volume, average size per trade, taker buy/sell volume and imbalance describe activity and economic execution. Trades count is not economic value by itself; interpret it with quote value, persistence, price response and OI.

## Open interest and fuel

`oi`, `oi_value` and their changes describe outstanding commitment, not direction. Contract OI and OI value must not be conflated.

## Positioning

Global L/S describes broad accounts; Top Account L/S describes account counts; Top Position L/S describes position size. They must not be treated as equivalent.

## Premium and funding

Premium and funding describe carry and pressure context, not independent entry signals.

## Momentum context

RSI is phase context only. It cannot independently terminate or bury a campaign.

## Adaptive derived evidence

Research may derive symbol-local percentile ranks, median/MAD deviations, slopes, acceleration, persistence, retention, compression, expansion, distance from footprint, acceptance/rejection and cross-layer divergence. All derivation must use observations available at the active cutoff only.

## Missing-data semantics

Missing means `UNKNOWN` or `NOT_AVAILABLE`, never neutral. Stale, sparse, misaligned and conflicting observations require explicit flags and confidence caps.

## Source hierarchy

1. Closed observed market rows after quality checks.
2. Causal features derived from those rows.
3. Frozen State Ledger records.
4. Validated research rules.
5. Background skills and previous narratives.
