# Symbol-Specific Mechanism Validation — Pass 2

## Campaign mechanisms

| Symbol | Campaigns | Leading mechanisms by outcome |
|---|---:|---|
| AKEUSDT | 4 | {"accepted_expansion": {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "OI_LEADS": 1}, "accepted_without_expansion": {"OI_LEADS": 1}, "failed_ignition": {"OI_LEADS": 1}} |
| BANKUSDT | 5 | {"accepted_expansion": {"EXECUTION_AND_PRICE_SIMULTANEOUS": 1}, "failed_ignition": {"EXECUTION_AND_PRICE_SIMULTANEOUS": 3}, "unresolved": {"EXECUTION_AND_PRICE_SIMULTANEOUS": 1}} |
| ESPORTSUSDT | 8 | {"accepted_expansion": {"EXECUTION_AND_PRICE_SIMULTANEOUS": 3, "OI_LEADS": 1}, "failed_ignition": {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "EXECUTION_AND_PRICE_SIMULTANEOUS": 1, "OI_LEADS": 2}} |
| LYNUSDT | 5 | {"accepted_expansion": {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "EXECUTION_AND_PRICE_SIMULTANEOUS": 1}, "failed_ignition": {"EXECUTION_AND_OI_SIMULTANEOUS": 3}} |

## Rejected transitions as negative controls

| Symbol | Rejected anchors | Validated discrimination | No clear discrimination | Insufficient paired sample |
|---|---:|---:|---:|---:|
| AKEUSDT | 5 | 0 | 0 | 2 |
| BANKUSDT | 4 | 0 | 0 | 2 |
| ESPORTSUSDT | 15 | 0 | 2 | 0 |
| LYNUSDT | 7 | 0 | 2 | 0 |

A rejected cutoff is never converted into a valid historical signal because its future path was positive. The audit tests the review gate; it does not rewrite the frozen decision.

## Source-selection sensitivity

| Symbol | Status | Material conflict groups | Decision-relevant conflict groups | Conflict fields |
|---|---|---:|---:|---|
| BANKUSDT | STABLE_VALID_PATH | 412 | 0 | {"rsi": 412} |
| LYNUSDT | STABLE_VALID_PATH | 214 | 0 | {"rsi": 214} |

## Research status

- Shared states remain indexing vocabulary.
- Mechanism timing, reset depth and negative-control discrimination are interpreted within each symbol first.
- Cross-symbol transfer is not claimed.
- No durable rule is created.
