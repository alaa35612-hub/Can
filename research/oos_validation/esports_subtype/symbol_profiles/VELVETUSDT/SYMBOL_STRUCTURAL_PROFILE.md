# VELVETUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 99
- Reliable timeframes: 15m
- Limited timeframes: 1h, 4h, 1d
- Median execution/OI anomaly to material price-response lag: 30.0 minutes
- Lag observations: 125
- Provisional false-ignition rate: 0.3333333333333333

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 15m | 290 | 2026-06-25T18:15:00+00:00 | 2026-07-02T19:45:00+00:00 | 32275.0 | 205149.10000000006 | 1388723.588 | 12905976.229880001 |
| 1h | 99 | 2026-06-23T13:00:00+00:00 | 2026-06-27T15:00:00+00:00 | 19653.0 | 323867.2000000002 | 764809.96806 | 25890163.331440017 |
| 4h | 99 | 2026-06-11T04:00:00+00:00 | 2026-06-27T12:00:00+00:00 | 265210.0 | 3066826.4000000004 | 17661996.10945 | 200447428.6129201 |
| 1d | 30 | 2026-05-28T00:00:00+00:00 | 2026-06-26T00:00:00+00:00 | 1339540.5 | 9346072.600000005 | 62724878.035514995 | 521829082.7344332 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-06-26T01:45:00+00:00 | 2026-06-26T12:45:00+00:00 | accepted_expansion | EARLY_BUILD, CONFIRMED_BUILD, IGNITION_CANDIDATE, ACCEPTED_IGNITION, EXPANSION, CONTINUATION_RELOAD |
| 2 | 2026-07-01T22:00:00+00:00 | 2026-07-02T07:45:00+00:00 | failed_ignition |  |
| 3 | 2026-07-02T09:00:00+00:00 | 2026-07-02T09:15:00+00:00 | build_without_acceptance | EARLY_BUILD, CONFIRMED_BUILD |

## Symbol-specific deductions

- Material source conflicts exist and cap confidence.
- Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
