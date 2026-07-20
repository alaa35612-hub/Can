# ESPORTSUSDT Hypothesis Blind Replay

## Frozen hypothesis

- Rule ID: `ESPORTS_DEEP_RESET_CYCLE_CONTEXT`
- Statement: A mature ESPORTS cycle with a longer-than-prior build and jointly deeper observed price/OI reset may define a successful expansion subtype.
- Status before replay: `RESEARCH_HYPOTHESIS`

## Expanding-window campaign assessments

| Campaign | Cutoff | Frozen assessment | Age min | Price reset magnitude % | OI reset magnitude % |
|---:|---|---|---:|---:|---:|
| 1 | 2026-07-13T20:15:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 30.0 | None | None |
| 2 | 2026-07-14T12:00:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 180.0 | 3.356643356643352 | 1.1466090308052457 |
| 3 | 2026-07-14T21:45:00+00:00 | ABSTAIN_INSUFFICIENT_PRIOR_HISTORY | 150.0 | 3.0344827586206935 | 0.19770059161228204 |
| 4 | 2026-07-15T05:15:00+00:00 | HYPOTHESIS_CONTEXT_NOT_SUPPORTED | 390.0 | 0.0 | 0.0 |
| 5 | 2026-07-15T19:15:00+00:00 | PARTIAL_HYPOTHESIS_CONTEXT | 255.0 | 0.7357859531772482 | 2.3166473329126913 |
| 6 | 2026-07-16T13:30:00+00:00 | FULL_HYPOTHESIS_CONTEXT | 420.0 | 21.879815100154087 | 2.100242368257277 |
| 7 | 2026-07-17T18:00:00+00:00 | DEEP_RESET_WITHOUT_LONG_REBUILD | 15.0 | 16.936050597329576 | 22.733523525261123 |
| 8 | 2026-07-18T16:30:00+00:00 | FULL_HYPOTHESIS_CONTEXT | 600.0 | 14.547473625763473 | 9.250699013238584 |

## Replay result

- Total campaign assessments: 8
- Evaluable: 5
- Abstained: 3
- Assessed successes: 3
- Assessed failures: 2
- Full-context successes: 2
- Full-context failures: 0
- Evaluable rejected controls: 8
- Rejected controls with positive context: 4
- Blind replay result: `INCONCLUSIVE_DIRECTIONAL_EVIDENCE`

## Rule lifecycle

- Decision: `KEEP_AS_HYPOTHESIS`
- Reason: Expanding-window replay does not establish reliable discrimination from failures and rejected controls.
- No historical decision is rewritten after outcome reveal.
- No promotion to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` is made by this pass.
