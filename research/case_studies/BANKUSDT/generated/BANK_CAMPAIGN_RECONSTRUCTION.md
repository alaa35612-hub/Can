# BANKUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `BANKUSDT_15m_limit500_20260718_174346_enriched_candles.csv`
- `BANKUSDT_15m_limit500_20260719_170943_enriched_candles.csv`
- `BANKUSDT_1d_limit500_20260718_174500_enriched_candles.csv`
- `BANKUSDT_1d_limit500_20260719_170839_enriched_candles.csv`
- `BANKUSDT_1h_limit500_20260718_174357_enriched_candles.csv`
- `BANKUSDT_1h_limit500_20260719_170932_enriched_candles.csv`
- `BANKUSDT_4h_limit500_20260719_170921_enriched_candles.csv`
- `BANKUSDT_5m_limit500_20260719_170954_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-07-13T20:45:00+00:00 | LATENT → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-13T23:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-13T23:15:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-13T23:45:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T00:00:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T01:30:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T02:30:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T02:45:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T23:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T00:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-15T00:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-15T00:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T12:30:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T12:45:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T13:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-18T15:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T15:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T15:45:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T16:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-19T16:00:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-19T16:15:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |

## Run summary

- Sources: 8
- Causal rows: 1824
- Segments: 1
- Proposed transitions: 21
- PASS: 19
- RESTRICT: 1
- REJECT: 1
- Control windows: 5
- Preserved source conflicts: 412
- No rule is promoted to durable status from this single case.
