# ESPORTSUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `ESPORTSUSDT_15m_limit500_20260718_182815_enriched_candles.csv`
- `ESPORTSUSDT_1d_limit500_20260718_182741_enriched_candles.csv`
- `ESPORTSUSDT_1h_limit500_20260718_182804_enriched_candles.csv`
- `ESPORTSUSDT_4h_limit500_20260718_182753_enriched_candles.csv`
- `ESPORTSUSDT_5m_limit100_20260709_140856_enriched_candles.csv`
- `ESPORTSUSDT_5m_limit500_20260718_182823_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-07-13T19:45:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-13T20:15:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-13T20:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-13T21:30:00+00:00 | ACCEPTED_IGNITION → COOLING | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-14T00:00:00+00:00 | COOLING → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-14T05:15:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-14T09:00:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-14T10:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T12:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T12:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-14T13:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-14T13:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T17:15:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T19:15:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T21:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T21:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T22:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-14T22:15:00+00:00 | ACCEPTED_IGNITION → COOLING | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-14T22:30:00+00:00 | COOLING → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-14T22:45:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-14T23:45:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-15T05:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T05:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation; acceptance relies mainly on retention and needs independent confirmation |
| 2026-07-15T07:45:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T08:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T11:45:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T15:00:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-15T15:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | RESTRICT | fuel evidence exists but direction is unresolved |
| 2026-07-15T19:15:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-15T19:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-07-15T20:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-15T20:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-16T06:15:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-16T06:30:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-16T06:45:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-16T13:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-16T13:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-16T14:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-16T14:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T16:15:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T17:45:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-17T18:00:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-17T18:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T18:30:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-17T19:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T06:15:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T06:30:00+00:00 | FAILURE → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T12:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-18T16:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-18T16:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T17:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-18T17:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |

## Run summary

- Sources: 6
- Causal rows: 1804
- Segments: 1
- Proposed transitions: 52
- PASS: 32
- RESTRICT: 5
- REJECT: 15
- Control windows: 5
- Preserved source conflicts: 0
- No rule is promoted to durable status from this single case.
