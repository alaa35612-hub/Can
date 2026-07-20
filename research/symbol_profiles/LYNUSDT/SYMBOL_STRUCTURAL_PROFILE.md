# LYNUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 214
- Reliable timeframes: 5m, 15m, 1h, 4h
- Limited timeframes: none
- Median execution/OI anomaly to material price-response lag: 90.0 minutes
- Lag observations: 94
- Provisional false-ignition rate: 0.2

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 5m | 499 | 2026-07-17T01:15:00+00:00 | 2026-07-18T18:45:00+00:00 | 94.0 | 319.2 | 3395.16501 | 19106.400608 |
| 15m | 500 | 2026-07-13T14:00:00+00:00 | 2026-07-18T18:45:00+00:00 | 274.0 | 832.6000000000001 | 8819.428615 | 41580.039073000036 |
| 1h | 499 | 2026-06-28T00:00:00+00:00 | 2026-07-18T18:00:00+00:00 | 1071.0 | 3157.7999999999993 | 42880.0382 | 172963.35950599998 |
| 4h | 179 | 2026-06-18T20:00:00+00:00 | 2026-07-18T12:00:00+00:00 | 5247.0 | 14710.000000000004 | 245740.74797 | 951292.3742940008 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-07-13T20:15:00+00:00 | 2026-07-14T06:45:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 2 | 2026-07-14T07:30:00+00:00 | 2026-07-15T07:30:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 3 | 2026-07-15T07:45:00+00:00 | 2026-07-16T01:30:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, FAILURE |
| 4 | 2026-07-16T03:15:00+00:00 | 2026-07-17T17:00:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 5 | 2026-07-17T22:00:00+00:00 | 2026-07-18T07:00:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |

## Symbol-specific deductions

- High source-conflict burden; source-selection sensitivity is mandatory.
- Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.
- Multiple accepted campaigns occur; do not compress history into one campaign.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
