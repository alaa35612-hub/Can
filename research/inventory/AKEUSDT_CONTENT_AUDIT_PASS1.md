# AKEUSDT Content Audit — Pass 1

## Purpose

Establish the first content-verified inventory record rather than relying on filenames. This is a data-quality and coverage audit, not yet a structural campaign conclusion.

## Files inspected directly

- `AKEUSDT_15m_limit100_20260711_113420_enriched_candles.csv`
- `AKEUSDT_15m_limit500_20260717_211231_enriched_candles.csv`
- `AKEUSDT_5m_limit500_20260717_211054_enriched_candles.csv`
- `AKEUSDT_1h_limit500_20260717_211343_enriched_candles.csv`
- `AKEUSDT_4h_limit500_20260717_211446_enriched_candles.csv`
- `AKEUSDT_1d_limit500_20260717_212121_enriched_candles.csv`

## Verified coverage

| Timeframe/capture | Actual data rows | First candle | Last candle | Endpoint closure |
|---|---:|---|---|---|
| 15m old capture | 99 | 2026-07-10 10:45 UTC | 2026-07-11 11:15 UTC | True at inspected endpoints |
| 15m main capture | 499 | 2026-07-12 16:15 UTC | 2026-07-17 20:45 UTC | True at inspected endpoints |
| 5m main capture | 499 | 2026-07-16 03:35 UTC | 2026-07-17 21:05 UTC | True at inspected endpoints |
| 1h main capture | 499 | 2026-06-27 02:00 UTC | 2026-07-17 20:00 UTC | True at inspected endpoints |
| 4h main capture | 179 | 2026-06-18 00:00 UTC | 2026-07-17 16:00 UTC | True at inspected endpoints |
| 1d main capture | 29 | 2026-06-18 00:00 UTC | 2026-07-16 00:00 UTC | True at inspected endpoints |

## Schema verification

The inspected CSV files expose the same full enriched header family:

- chronology and closed-candle state;
- last and mark OHLC;
- premium index;
- RSI context;
- number of trades, base volume and quote volume;
- average base/quote value per execution;
- candle geometry and close location;
- taker buy/sell base and quote flow;
- OI contracts and OI value;
- Top Account, Top Position and Global L/S;
- cross-ratio spreads;
- funding context.

A complete column-by-column equality check across all captures remains pending.

## Coverage relationships

### Separate 15m windows

The old 15m capture ends on 11 July at 11:15 UTC. The main 15m capture begins on 12 July at 16:15 UTC. They are not exact duplicates and should be preserved as separate historical windows. There is an uncovered interval between the captures that must be recorded rather than silently interpolated.

### Multi-timeframe endpoint mismatch

- 5m extends to 17 July 21:05 UTC.
- 15m extends to 17 July 20:45 UTC.
- 1h extends to 17 July 20:00 UTC.
- 4h extends to 17 July 16:00 UTC.
- 1d ends on 16 July 00:00 UTC.

Blind replay must only expose a higher-timeframe candle after it closed. A later 5m observation cannot use an unfinished 1h, 4h or 1d candle.

## Initial findings

1. Filename row limits are nominal requests, not actual row counts.
2. Higher-timeframe histories are constrained by listing age and available history.
3. AKE provides enough chronological coverage for a multi-timeframe campaign study, but the daily context is short and must receive a warm-up confidence cap.
4. The gap between the two 15m captures prevents treating them as one uninterrupted 15m series without an explicit gap record.
5. Endpoint closure is verified, but every row still requires a complete closure scan.
6. CSV/JSONL twins require content equivalence checks before deduplication.
7. The sharp July expansion is visible in the data, but this audit does not use it to assign a pattern or claim early detectability. That belongs to campaign reconstruction and blind replay.

## Required next work for AKE

- scan every row for closure, order, duplicate timestamps and gaps;
- compare each CSV with its JSONL twin;
- create a merged provenance-preserving timeline;
- establish adaptive symbol-local baselines at each cutoff;
- segment campaigns without future-conditioned boundaries;
- create the first AKE State Ledger;
- audit any prior AKE narrative files or general notes that refer to AKE;
- select failed and ordinary control windows from the same history;
- run blind replay before extracting rules.
