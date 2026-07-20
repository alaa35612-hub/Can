# VELVETUSDT Causal Campaign Reconstruction

Pattern labels remain hypotheses. Higher timeframes are visible only after close. Distribution ranks use prior same-symbol history. Data gaps reset unverified continuity.

## Sources
- `VELVETUSDT_15m_limit100_20260626_190253_enriched_candles.csv`
- `VELVETUSDT_15m_limit100_20260627_161019_enriched_candles.csv`
- `VELVETUSDT_15m_limit100_20260627_181248_enriched_candles.csv`
- `VELVETUSDT_15m_limit100_20260702_200210_enriched_candles.csv`
- `VELVETUSDT_1d_limit100_20260627_161135_enriched_candles.csv`
- `VELVETUSDT_1h_limit100_20260627_161039_enriched_candles.csv`
- `VELVETUSDT_4h_limit100_20260627_161103_enriched_candles.csv`

## Reviewed transitions

| Cutoff | Transition | Status | Adversarial reason |
|---|---|---|---|
| 2026-06-26T01:45:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-06-26T02:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-06-26T12:00:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-06-26T12:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-06-26T12:30:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-06-26T12:45:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-01T19:15:00+00:00 | UNOBSERVED_GAP → RESET | PASS | no adversarial rejection condition triggered |
| 2026-07-01T22:00:00+00:00 | LATENT → EARLY_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T22:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T22:30:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-01T23:15:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T00:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T02:30:00+00:00 | EXPANSION → CONTINUATION_RELOAD | REJECT | continuation remains possible but negative response caps confidence; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T07:45:00+00:00 | CONTINUATION_RELOAD → FAILURE | REJECT | no adversarial rejection condition triggered; transition depends on an unvalidated predecessor; reviewed state remains RESET |
| 2026-07-02T09:00:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | no adversarial rejection condition triggered; campaign re-anchored from independent build evidence after an invalid predecessor chain |
| 2026-07-02T09:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |

## Run summary

- Sources: 7
- Causal rows: 518
- Segments: 2
- Proposed transitions: 16
- PASS: 8
- RESTRICT: 1
- REJECT: 7
- Control windows: 5
- Preserved source conflicts: 99
- No rule is promoted to durable status from this single case.
