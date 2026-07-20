# BANKUSDT Hypothesis Blind Replay

## Frozen hypothesis

- Rule ID: `BANK_LONG_REBUILD_DEEP_RESET_CONTEXT`
- Statement: A BANK campaign with a longer-than-prior rebuild and jointly deeper observed price/OI reset may be more likely to survive ignition than ordinary BANK attempts.
- Status before replay: `RESEARCH_HYPOTHESIS`

## Expanding-window campaign assessments

| Campaign | Cutoff | Frozen assessment | Age min | Price reset magnitude % | OI reset magnitude % |
|---:|---|---|---:|---:|---:|
| 1 | 2026-07-13T23:00:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 135.0 | None | None |
| 2 | 2026-07-14T00:00:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 15.0 | 0.6107587502936274 | 0.49055686495192985 |
| 3 | 2026-07-14T23:45:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 1275.0 | 1.2316988147803798 | 0.8102476276513615 |
| 4 | 2026-07-18T15:15:00+00:00 | FULL_HYPOTHESIS_CONTEXT | 1590.0 | 14.448713470718355 | 10.748591595275547 |

## Replay result

- Total campaign assessments: 4
- Evaluable: 1
- Abstained: 3
- Assessed successes: 1
- Assessed failures: 0
- Full-context successes: 1
- Full-context failures: 0
- Evaluable rejected controls: 0
- Rejected controls with positive context: 0
- Blind replay result: `INSUFFICIENT_OUTCOME_SAMPLE`

## Rule lifecycle

- Decision: `KEEP_AS_HYPOTHESIS`
- Reason: The sole assessable accepted campaign may satisfy the full context, but the replay lacks the minimum paired success/failure sample required for promotion.
- No historical decision is rewritten after outcome reveal.
- No promotion to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` is made by this pass.
