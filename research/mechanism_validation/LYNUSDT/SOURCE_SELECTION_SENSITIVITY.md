# LYNUSDT Source-Selection Sensitivity

This audit reconstructs the reviewed path under multiple deterministic source-selection policies. It does not average conflicting rows or create synthetic candles.

- Status: `STABLE_VALID_PATH`
- Overlap groups: 498
- Material conflict groups: 214
- Decision-relevant conflict groups: 0
- Conflict fields: `{"rsi": 214}`

| Policy | Same valid path | Valid transition symmetric difference | Proposed transitions | Review counts |
|---|---|---:|---:|---|
| MOST_COMPLETE_LATEST | True | 0 | 31 | {"PASS": 22, "REJECT": 7, "RESTRICT": 2} |
| EARLIEST_CAPTURE | True | 0 | 31 | {"PASS": 22, "REJECT": 7, "RESTRICT": 2} |
| LATEST_CAPTURE | True | 0 | 31 | {"PASS": 22, "REJECT": 7, "RESTRICT": 2} |
| MIN_DISAGREEMENT | True | 0 | 31 | {"PASS": 22, "REJECT": 7, "RESTRICT": 2} |

## Interpretation

All tested source-selection policies preserve the valid reviewed transition path.

A stable result means only that the current research engine is insensitive to the tested source policies. It does not prove that every conflicting field is correct.
