# ESPORTS Mature Deep-Reset Subtype — Frozen OOS Transfer Test

This pass tests transferability only. It does not relabel external campaigns as ESPORTS patterns and does not rewrite the original ESPORTS replay.

| Symbol | Evaluable campaigns | Full context | Full-context outcomes | Full-context path classes | Symbol result |
|---|---:|---:|---|---|---|
| MAGMAUSDT | 0 | 0 | {} | {} | NO_EVALUABLE_CAMPAIGNS |
| TLMUSDT | 9 | 1 | {"FAILURE": 1} | {"MATCHED_CONTROL_LIKE": 1} | FULL_CONTEXT_CONTRADICTED_WITHIN_SYMBOL |
| VELVETUSDT | 0 | 0 | {} | {} | NO_EVALUABLE_CAMPAIGNS |

## Aggregate

- Transfer result: `EXTERNAL_TRANSFER_CONTRADICTION`
- Transfer decision: `REJECT_TRANSFER_CLAIM`
- Full-context successes: 0
- Full-context failures: 1
- Full-context unresolved: 0
- Symbols with a full-context success: 0
- Positive-path outliers: 0
- Negative-path outliers: 0
- Matched-control-like paths: 1

## Rule lifecycle

- `ESPORTS_MATURE_DEEP_RESET_SUBTYPE`: remains `RESEARCH_HYPOTHESIS` restricted to ESPORTS evidence.
- `MATURE_DEEP_RESET_CONTEXT_TRANSFER`: `REJECT_TRANSFER_CLAIM`.
- No result is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.

## Constraints

- Eligibility was frozen from data coverage and quality before reconstruction.
- Baselines use only completed prior campaigns from the same symbol.
- Missing current context or fewer than two prior values per component produces abstention.
- Outcome and matched-control path class are attached only after the context assessment is frozen.
- Cross-symbol equality of the three measurements does not establish causal identity.
