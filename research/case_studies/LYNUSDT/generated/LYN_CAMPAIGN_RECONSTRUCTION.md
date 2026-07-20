# LYNUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `LYNUSDT_15m_limit500_20260718_185949_enriched_candles.csv`
- `LYNUSDT_15m_limit500_20260718_190753_enriched_candles.csv`
- `LYNUSDT_1h_limit500_20260718_190125_enriched_candles.csv`
- `LYNUSDT_4h_limit500_20260718_190717_enriched_candles.csv`
- `LYNUSDT_5m_limit500_20260718_185241_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-07-13T20:15:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-13T22:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T03:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T03:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-14T04:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-14T04:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T06:45:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T07:30:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-14T10:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-15T07:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T07:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T07:30:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T07:45:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-15T08:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T01:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T01:30:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T03:15:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T04:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T05:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T06:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T07:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T07:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T17:00:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T22:00:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T02:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T04:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T05:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-18T05:45:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-18T07:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |

## Run summary

- Sources: 5
- Causal rows: 1677
- Segments: 1
- Proposed transitions: 31
- PASS: 22
- RESTRICT: 2
- REJECT: 7
- Control windows: 5
- Preserved source conflicts: 214
- No rule is promoted to durable status from this single case.
