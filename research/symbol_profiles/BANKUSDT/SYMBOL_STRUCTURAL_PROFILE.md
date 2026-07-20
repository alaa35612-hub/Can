# BANKUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 412
- Reliable timeframes: 5m, 15m, 1h, 4h
- Limited timeframes: 1d
- Median execution/OI anomaly to material price-response lag: 30.0 minutes
- Lag observations: 301
- Provisional false-ignition rate: 0.4

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 5m | 499 | 2026-07-17T23:30:00+00:00 | 2026-07-19T17:00:00+00:00 | 26581.0 | 116412.19999999998 | 1468755.92337 | 8591108.846283998 |
| 15m | 593 | 2026-07-13T12:45:00+00:00 | 2026-07-19T16:45:00+00:00 | 15458.0 | 164183.20000000004 | 959412.18463 | 10704678.272062032 |
| 1h | 523 | 2026-06-27T22:00:00+00:00 | 2026-07-19T16:00:00+00:00 | 3344.0 | 138426.0000000001 | 85733.71514 | 7637151.661398002 |
| 4h | 179 | 2026-06-19T20:00:00+00:00 | 2026-07-19T12:00:00+00:00 | 11797.0 | 259932.8000000002 | 294152.00801 | 15637065.445386022 |
| 1d | 30 | 2026-06-19T00:00:00+00:00 | 2026-07-18T00:00:00+00:00 | 77731.5 | 826010.1000000018 | 2022639.75198 | 48024607.231202155 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-07-13T20:45:00+00:00 | 2026-07-13T23:15:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, FAILURE |
| 2 | 2026-07-13T23:45:00+00:00 | 2026-07-14T01:30:00+00:00 | failed_ignition | EARLY_BUILD, IGNITION_CANDIDATE, FAILURE |
| 3 | 2026-07-14T02:30:00+00:00 | 2026-07-17T12:30:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 4 | 2026-07-17T12:45:00+00:00 | 2026-07-19T16:00:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 5 | 2026-07-19T16:15:00+00:00 | 2026-07-19T16:15:00+00:00 | unresolved | EARLY_BUILD |

## Symbol-specific deductions

- High source-conflict burden; source-selection sensitivity is mandatory.
- Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
