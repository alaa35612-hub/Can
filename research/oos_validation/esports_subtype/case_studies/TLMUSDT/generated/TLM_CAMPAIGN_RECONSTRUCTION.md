# TLMUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `TLMUSDT_15m_limit100_20260704_181750_enriched_candles.csv`
- `TLMUSDT_15m_limit500_20260719_171030_enriched_candles.csv`
- `TLMUSDT_1d_limit500_20260719_171101_enriched_candles.csv`
- `TLMUSDT_1h_limit500_20260719_171041_enriched_candles.csv`
- `TLMUSDT_4h_limit500_20260719_171051_enriched_candles.csv`
- `TLMUSDT_5m_limit100_20260701_200402_enriched_candles.csv`
- `TLMUSDT_5m_limit100_20260703_201211_enriched_candles.csv`
- `TLMUSDT_5m_limit500_20260719_171008_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-07-04T00:00:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-04T00:15:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-04T00:30:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-04T01:45:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-04T02:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-04T05:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-04T05:15:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-04T07:30:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-04T07:45:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-04T09:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-04T09:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-04T11:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-04T11:45:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T12:15:00+00:00 | UNOBSERVED_GAP → RESET | PASS | no adversarial rejection condition triggered |
| 2026-07-14T13:15:00+00:00 | LATENT → EARLY_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T15:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T16:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T16:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T16:45:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T17:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | continuation remains possible but negative response caps confidence; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T21:00:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-14T21:30:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-15T04:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T05:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T06:45:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T07:00:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T07:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T11:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T11:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-15T11:30:00+00:00 | ACCEPTED_IGNITION → COOLING | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T15:15:00+00:00 | COOLING → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T15:30:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-15T16:45:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T04:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T05:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-16T06:45:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-16T07:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | continuation remains possible but negative response caps confidence; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-16T07:30:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-16T09:15:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-16T09:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T15:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T15:30:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T16:45:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T17:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T00:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T00:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T00:30:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T00:45:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T01:30:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T02:00:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T06:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T08:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T08:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T09:30:00+00:00 | ACCEPTED_IGNITION → COOLING | PASS | no adversarial rejection condition triggered |
| 2026-07-17T13:15:00+00:00 | COOLING → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T16:45:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T22:15:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-18T00:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T08:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T08:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-18T08:45:00+00:00 | ACCEPTED_IGNITION → COOLING | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-18T09:00:00+00:00 | COOLING → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-18T09:15:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-18T09:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-18T11:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T11:30:00+00:00 | IGNITION_CANDIDATE → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T12:00:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T12:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-18T19:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T19:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T20:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T20:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | RESTRICT | continuation remains possible but negative response caps confidence |

## Run summary

- Sources: 8
- Causal rows: 2003
- Segments: 2
- Proposed transitions: 75
- PASS: 50
- RESTRICT: 8
- REJECT: 17
- Control windows: 5
- Preserved source conflicts: 0
- No rule is promoted to durable status from this single case.
