# TLMUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 0
- Reliable timeframes: 5m, 15m, 1h, 4h
- Limited timeframes: 1d
- Median execution/OI anomaly to material price-response lag: 45.0 minutes
- Lag observations: 20
- Provisional false-ignition rate: 0.6153846153846154

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 5m | 698 | 2026-07-01T11:45:00+00:00 | 2026-07-19T17:05:00+00:00 | 1313.5 | 12097.400000000005 | 104542.751689 | 1258298.6282006032 |
| 15m | 598 | 2026-07-03T17:30:00+00:00 | 2026-07-19T16:45:00+00:00 | 2263.0 | 44506.300000000105 | 122995.541222 | 4789886.893700203 |
| 1h | 499 | 2026-06-28T22:00:00+00:00 | 2026-07-19T16:00:00+00:00 | 15208.0 | 161761.19999999998 | 1013166.640454 | 16386389.649840798 |
| 4h | 179 | 2026-06-19T20:00:00+00:00 | 2026-07-19T12:00:00+00:00 | 30924.0 | 548084.0000000006 | 1813155.047492 | 50240701.567809805 |
| 1d | 29 | 2026-06-20T00:00:00+00:00 | 2026-07-18T00:00:00+00:00 | 214257.0 | 3617687.3999999994 | 12348487.02338 | 340619561.12012875 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-07-04T00:00:00+00:00 | 2026-07-04T00:30:00+00:00 | failed_ignition | EARLY_BUILD, IGNITION_CANDIDATE, FAILURE |
| 2 | 2026-07-04T01:45:00+00:00 | 2026-07-04T05:15:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, FAILURE |
| 3 | 2026-07-04T07:30:00+00:00 | 2026-07-04T11:45:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD |
| 4 | 2026-07-14T13:15:00+00:00 | 2026-07-14T21:00:00+00:00 | failed_ignition |  |
| 5 | 2026-07-14T21:30:00+00:00 | 2026-07-15T06:45:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 6 | 2026-07-15T07:00:00+00:00 | 2026-07-15T15:15:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 7 | 2026-07-15T15:30:00+00:00 | 2026-07-16T07:30:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 8 | 2026-07-16T09:15:00+00:00 | 2026-07-16T15:30:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, FAILURE |
| 9 | 2026-07-16T16:45:00+00:00 | 2026-07-17T01:30:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 10 | 2026-07-17T02:00:00+00:00 | 2026-07-17T16:45:00+00:00 | accepted_without_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, COOLING, CONTINUATION_RELOAD, FAILURE |
| 11 | 2026-07-17T22:15:00+00:00 | 2026-07-18T09:00:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 12 | 2026-07-18T09:15:00+00:00 | 2026-07-18T11:30:00+00:00 | failed_ignition | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, FAILURE |
| 13 | 2026-07-18T12:00:00+00:00 | 2026-07-18T20:15:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD |

## Symbol-specific deductions

- No material overlap conflicts in the selected source set.
- Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.
- Multiple accepted campaigns occur; do not compress history into one campaign.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
