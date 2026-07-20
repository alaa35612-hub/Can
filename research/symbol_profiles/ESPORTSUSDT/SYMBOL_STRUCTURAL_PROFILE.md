# ESPORTSUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 0
- Reliable timeframes: 5m, 15m, 1h, 4h
- Limited timeframes: 1d
- Median execution/OI anomaly to material price-response lag: 30.0 minutes
- Lag observations: 161
- Provisional false-ignition rate: 0.0

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 5m | 598 | 2026-07-09T05:50:00+00:00 | 2026-07-18T18:20:00+00:00 | 9109.0 | 22727.600000000017 | 662198.068285 | 1695679.466373 |
| 15m | 499 | 2026-07-13T13:30:00+00:00 | 2026-07-18T18:00:00+00:00 | 4093.0 | 50158.59999999999 | 225929.9526 | 4138732.5459179995 |
| 1h | 499 | 2026-06-27T23:00:00+00:00 | 2026-07-18T17:00:00+00:00 | 9175.0 | 101097.99999999994 | 403218.81848 | 7132941.214314 |
| 4h | 179 | 2026-06-18T20:00:00+00:00 | 2026-07-18T12:00:00+00:00 | 54436.0 | 447079.6000000001 | 2863027.34294 | 29479106.78073001 |
| 1d | 29 | 2026-06-19T00:00:00+00:00 | 2026-07-17T00:00:00+00:00 | 327117.0 | 2133453.3999999994 | 19052074.90695 | 133500390.53132597 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-07-13T19:45:00+00:00 | 2026-07-14T05:15:00+00:00 | unresolved | EARLY_BUILD, IGNITION_CANDIDATE |
| 2 | 2026-07-14T09:00:00+00:00 | 2026-07-14T17:15:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 3 | 2026-07-14T19:15:00+00:00 | 2026-07-14T22:30:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 4 | 2026-07-14T22:45:00+00:00 | 2026-07-15T11:45:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 5 | 2026-07-15T15:00:00+00:00 | 2026-07-16T06:15:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE |
| 6 | 2026-07-16T06:30:00+00:00 | 2026-07-17T16:15:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 7 | 2026-07-17T17:45:00+00:00 | 2026-07-18T06:15:00+00:00 | accepted_expansion | EARLY_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD, FAILURE |
| 8 | 2026-07-18T06:30:00+00:00 | 2026-07-18T17:30:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD |

## Symbol-specific deductions

- No material overlap conflicts in the selected source set.
- Multiple accepted campaigns occur; do not compress history into one campaign.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
