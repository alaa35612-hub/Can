# MAGMAUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `MAGMAUSDT_15m_limit100_20260626_133221_enriched_candles.csv`
- `MAGMAUSDT_15m_limit100_20260702_200404_enriched_candles.csv`
- `MAGMAUSDT_15m_limit100_20260703_201708_enriched_candles.csv`
- `MAGMAUSDT_1d_limit500_20260626_145834_enriched_candles.csv`
- `MAGMAUSDT_1h_limit500_20260626_145855_enriched_candles.csv`
- `MAGMAUSDT_4h_limit500_20260626_145844_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-06-25T19:15:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-06-25T19:45:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-06-25T20:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance conflicts with abnormal negative-price dislocation |
| 2026-06-25T21:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-06-25T21:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains IGNITION_CANDIDATE |
| 2026-07-01T19:15:00+00:00 | UNOBSERVED_GAP → RESET | PASS | no adversarial rejection condition triggered |
| 2026-07-01T19:30:00+00:00 | LATENT → EARLY_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T20:30:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T22:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T23:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T00:15:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T01:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |

## Run summary

- Sources: 6
- Causal rows: 1009
- Segments: 2
- Proposed transitions: 12
- PASS: 3
- RESTRICT: 0
- REJECT: 9
- Control windows: 5
- Preserved source conflicts: 2
- No rule is promoted to durable status from this single case.
