# MAGMAUSDT Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: 2
- Reliable timeframes: 15m, 1h, 4h
- Limited timeframes: 1d
- Median execution/OI anomaly to material price-response lag: 30.0 minutes
- Lag observations: 122
- Provisional false-ignition rate: 1.0

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
| 15m | 295 | 2026-06-25T12:45:00+00:00 | 2026-07-03T20:00:00+00:00 | 10903.0 | 69110.20000000001 | 420250.78635 | 3428990.8649400063 |
| 1h | 499 | 2026-06-05T19:00:00+00:00 | 2026-06-26T13:00:00+00:00 | 16048.0 | 72507.59999999998 | 335596.30617 | 1866632.0060759995 |
| 4h | 185 | 2026-05-26T16:00:00+00:00 | 2026-06-26T08:00:00+00:00 | 54704.0 | 277441.5999999999 | 1206763.72063 | 7961556.150021994 |
| 1d | 30 | 2026-05-27T00:00:00+00:00 | 2026-06-25T00:00:00+00:00 | 441505.0 | 1703464.0 | 9575713.71197 | 65219991.81392708 |

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
| 1 | 2026-06-25T19:15:00+00:00 | 2026-06-25T21:30:00+00:00 | failed_ignition | EARLY_BUILD, IGNITION_CANDIDATE |
| 2 | 2026-07-01T19:30:00+00:00 | 2026-07-02T01:00:00+00:00 | failed_ignition |  |

## Symbol-specific deductions

- Material source conflicts exist and cap confidence.
- Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.

## Unknowns and confidence limits

- Daily regime maturity is insufficient for durable long-horizon claims.
- Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
