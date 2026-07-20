# Symbol-Specific Hypothesis Blind Replay — Pass 3

This pass evaluates two already-registered symbol-specific hypotheses. It does not search for a new winning threshold and does not impose a common market pattern.

| Symbol | Evaluable campaigns | Successes | Failures | Full-context successes | Full-context failures | Positive rejected controls | Replay result | Lifecycle decision |
|---|---:|---:|---:|---:|---:|---:|---|---|
| BANKUSDT | 1 | 1 | 0 | 1 | 0 | 0 | INSUFFICIENT_OUTCOME_SAMPLE | KEEP_AS_HYPOTHESIS |
| ESPORTSUSDT | 5 | 3 | 2 | 2 | 0 | 4 | INCONCLUSIVE_DIRECTIONAL_EVIDENCE | KEEP_AS_HYPOTHESIS |

## Reading constraints

- Context is assessed at the original ignition or rejected-transition cutoff.
- Baselines contain only campaigns completed before that cutoff.
- Outcomes are revealed after the assessment record is frozen.
- Missing history or reset continuity produces abstention.
- The same context definition is not transferred from BANK to ESPORTS or vice versa.
- No candidate becomes a durable rule in this pass.
