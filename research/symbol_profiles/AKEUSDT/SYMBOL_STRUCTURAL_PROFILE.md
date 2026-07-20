# AKEUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 99
- Reliable timeframes: 5m, 15m, 1h, 4h
- Limited timeframes: 1d
- Median execution/OI anomaly to material price-response lag: None minutes
- Lag observations: 0
- Provisional false-ignition rate: 0.0

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 5m | 499 | 2026-07-16T03:35:00+00:00 | 2026-07-17T21:05:00+00:00 | 28681.0 | 71238.0 | 2197425.3948153 | 5869943.69201148 |
| 15m | 1097 | 2026-07-02T13:15:00+00:00 | 2026-07-17T20:45:00+00:00 | 1119.0 | 104981.59999999999 | 43874.4566673 | 8558543.278777339 |
| 1h | 499 | 2026-06-27T02:00:00+00:00 | 2026-07-17T20:00:00+00:00 | 2354.0 | 246414.8 | 85488.0011387 | 17487641.447494816 |
| 4h | 179 | 2026-06-18T00:00:00+00:00 | 2026-07-17T16:00:00+00:00 | 8889.0 | 103202.8000000004 | 332121.2521287 | 7625515.298381534 |
| 1d | 29 | 2026-06-18T00:00:00+00:00 | 2026-07-16T00:00:00+00:00 | 65139.0 | 325229.6 | 2551942.1907172 | 21219835.74045794 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-07-02T13:30:00+00:00 | 2026-07-07T08:00:00+00:00 | accepted_expansion | EARLY_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 2 | 2026-07-07T09:00:00+00:00 | 2026-07-07T10:15:00+00:00 | accepted_expansion | EARLY_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD |
| 3 | 2026-07-10T11:00:00+00:00 | 2026-07-11T00:00:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, EXPANSION, CONTINUATION_RELOAD |
| 4 | 2026-07-12T16:30:00+00:00 | 2026-07-14T16:15:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, CONTINUATION_RELOAD |

## Symbol-specific deductions

- Material source conflicts exist and cap confidence.
- Multiple accepted campaigns occur; do not compress history into one campaign.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
