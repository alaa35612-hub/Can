# Human-Reviewed Symbol Hypothesis Blind Replay — Pass 3

The raw replay trace is preserved. This review corrects the evidence unit to campaigns and applies the frozen hypothesis literally: long rebuild plus deeper price reset plus deeper OI reset.

| Symbol | Evaluable campaigns | Full-context successes | Full-context failures | Full-context rejected campaigns | Reviewed result | Decision | Restricted rule |
|---|---:|---:|---:|---:|---|---|---|
| BANKUSDT | 1 | 1 | 0 | 0 | INSUFFICIENT_OUTCOME_SAMPLE | KEEP_AS_HYPOTHESIS | — |
| ESPORTSUSDT | 5 | 2 | 0 | 0 | DIRECTIONAL_FULL_CONTEXT_SUBTYPE_SUPPORT | RESTRICT | ESPORTS_MATURE_DEEP_RESET_SUBTYPE |

## Method decision

- Repeated rejected transitions within one campaign are correlated observations, not independent controls.
- `PARTIAL_HYPOTHESIS_CONTEXT` is supporting evidence only; it does not fulfill the joint hypothesis.
- BANK remains untestable with the current expanding-window sample.
- Any ESPORTS support is restricted to a possible mature deep-reset subtype; it is not necessary, sufficient, universal, or durable.
