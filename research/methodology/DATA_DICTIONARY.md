# Research Data Dictionary

## Purpose

Define the semantic role of fields used in forensic campaign research. Field presence varies by file; missing fields must remain explicit.

## Identity and chronology

- `code_version`: producer/version provenance.
- `timestamp`, `open_time`, `close_time`: chronological identifiers.
- `time`, `open_time_str`, `close_time_str`: human-readable times.
- `symbol`: contract identifier.
- `is_closed_candle`: whether the observation was complete at collection time.
- `timeframe`: inferred from filename or source metadata when not stored in rows.

## Price and mark structure

- `open`, `high`, `low`, `close`: contract kline prices.
- `close_change`, `close_change_pct`: row-to-row close movement.
- `mark_open`, `mark_high`, `mark_low`, `mark_close`: mark-price kline.
- `mark_last_close_spread`, `mark_last_close_spread_pct`: contract/mark divergence context.
- `price_range`, `price_range_pct`: candle range.
- `candle_body`, `candle_body_pct`, `candle_body_abs`, `candle_body_abs_pct`: body direction and magnitude.
- `upper_wick`, `upper_wick_pct_of_range`: upper rejection context.
- `lower_wick`, `lower_wick_pct_of_range`: lower rejection/absorption context.
- `close_location_in_range`: close placement inside the candle range.

Price variables are outcomes and structural-location evidence. A price rise alone is not proof of accumulation or institutional intent.

## Execution and volume

- `number_of_trades`: count of executions in the candle.
- `trades_change`, `trades_change_pct`: change from prior observation.
- `volume`: base-asset volume.
- `quote_volume`: quote-asset notional volume.
- `quote_volume_source`: provenance of quote volume.
- `avg_base_per_trade`, `avg_quote_per_trade`: average execution size proxies.
- `taker_buy_base_volume`, `taker_sell_base_volume`: aggressive base flow.
- `taker_buy_quote_volume`, `taker_sell_quote_volume`: aggressive quote-notional flow.
- `taker_buy_quote_pct`, `taker_sell_quote_pct`: taker-side proportions.
- `taker_buy_sell_base_ratio`, `taker_buy_sell_quote_ratio`: relative aggressive-side ratios.
- `taker_quote_imbalance`, `taker_quote_imbalance_pct`: directional execution imbalance.

Trades count is an execution-activity measure, not economic value by itself. It must be interpreted with quote volume, average trade value, persistence, price response and OI behavior.

## Open interest and fuel

- `oi`: open-interest contracts or source-native units.
- `oi_value`: notional value of open interest.
- `oi_change`, `oi_change_pct`: change in contract/unit OI.
- `oi_value_change`, `oi_value_change_pct`: notional OI change.

OI measures outstanding commitment, not direction. Contract OI and OI value must not be treated as interchangeable, especially when price changes materially.

## Positioning

- `global_ls_ratio`: broad account long/short ratio.
- `global_long_pct`, `global_short_pct`: broad account distribution.
- `acco_ls_ratio`: top-trader account-count long/short ratio.
- `acco_long_pct`, `acco_short_pct`: top-account distribution.
- `posit_ls_ratio`: top-trader position-size long/short ratio.
- `posit_long_pct`, `posit_short_pct`: top-position distribution.
- `acco_posit_ls_spread`: account-count versus position-size divergence.
- `global_acco_ls_spread`: broad versus top-account divergence.
- `global_posit_ls_spread`: broad versus top-position divergence.

Account ratios describe counts or participation; position ratios describe size. They must not be conflated.

## Premium and funding context

- `premium_index_*`: premium-index candle fields.
- `funding_time`, `funding_time_str`: funding event timestamp.
- `funding_rate`: funding context.
- `mark_price_at_funding`: mark price associated with funding.

Funding and premium describe positioning pressure and carry context. They are not independent entry signals.

## Momentum context

- `rsi`: phase/momentum context only. It cannot independently terminate or bury a campaign.

## Derived evidence requirements

Research may derive adaptive evidence such as:

- symbol-local percentile rank;
- median and MAD-relative deviation;
- slopes and acceleration;
- persistence and retention;
- compression and expansion;
- distance from campaign footprint;
- price acceptance/rejection;
- cross-layer divergence.

Derived evidence must use observations available at the active cutoff only.

## Missing-data semantics

- Missing means `UNKNOWN` or `NOT_AVAILABLE`, never neutral.
- Stale observations require a stale flag.
- Misaligned observations require an alignment-risk flag.
- Sparse warm-up history requires a confidence cap.
- Conflicting duplicate records must preserve both source paths until resolved.

## Source hierarchy

1. Closed raw/enriched market rows after quality checks.
2. Causally derived features from those rows.
3. Frozen State Ledger records.
4. Validated research rules.
5. Background skills and previous narratives.
