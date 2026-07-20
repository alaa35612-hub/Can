# AKEUSDT Adversarial Transition Review

The automated ledger proposes transitions; this file evaluates whether each transition survives explicit contradiction checks. `REJECT` transitions must not be used as facts. `RESTRICT` transitions remain hypotheses with capped confidence.

## Counts

- PASS: 19
- RESTRICT: 4
- REJECT: 2

## Review table

| Cutoff | Candidate transition | Status | Reason |
|---|---|---|---|
| 2026-07-02T13:30:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-02T21:30:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-02T21:45:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | RESTRICT | acceptance is based mainly on retention and needs independent execution/fuel confirmation |
| 2026-07-03T02:30:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-03T02:45:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-07T08:00:00+00:00 | CONTINUATION_RELOAD → FAILURE | PASS | no adversarial rejection condition triggered |
| 2026-07-07T09:00:00+00:00 | FAILURE → EARLY_BUILD | RESTRICT | fuel/build evidence exists, but direction remains unresolved under negative price response |
| 2026-07-07T09:15:00+00:00 | EARLY_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-07T09:30:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-07T10:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-07T10:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | RESTRICT | continuation remains possible but negative price dislocation prevents full confirmation |
| 2026-07-10T10:45:00+00:00 | UNOBSERVED_GAP → RESET | PASS | no adversarial rejection condition triggered |
| 2026-07-10T11:00:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-10T11:15:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-10T13:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-10T14:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | REJECT | acceptance cannot be confirmed on an abnormal negative-price-dislocation candle |
| 2026-07-10T18:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | PASS | no adversarial rejection condition triggered |
| 2026-07-11T00:00:00+00:00 | EXPANSION → CONTINUATION_RELOAD | PASS | no adversarial rejection condition triggered |
| 2026-07-12T16:15:00+00:00 | UNOBSERVED_GAP → RESET | PASS | no adversarial rejection condition triggered |
| 2026-07-12T16:30:00+00:00 | LATENT → EARLY_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-12T20:00:00+00:00 | EARLY_BUILD → CONFIRMED_BUILD | PASS | no adversarial rejection condition triggered |
| 2026-07-14T03:45:00+00:00 | CONFIRMED_BUILD → IGNITION_CANDIDATE | PASS | no adversarial rejection condition triggered |
| 2026-07-14T04:00:00+00:00 | IGNITION_CANDIDATE → ACCEPTED_IGNITION | PASS | no adversarial rejection condition triggered |
| 2026-07-14T05:00:00+00:00 | ACCEPTED_IGNITION → EXPANSION | REJECT | expansion lacks two independent current-cutoff supports |
| 2026-07-14T16:15:00+00:00 | EXPANSION → CONTINUATION_RELOAD | RESTRICT | continuation remains possible but negative price dislocation prevents full confirmation |

## Interpretation

The raw State Ledger is an algorithmic proposal. The reviewed ledger is the valid research interface. A later transition depending on a rejected predecessor must be re-evaluated during the next campaign pass rather than inherited automatically.
