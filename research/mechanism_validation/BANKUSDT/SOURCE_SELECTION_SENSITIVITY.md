# BANKUSDT Source-Selection Sensitivity

This audit reconstructs the reviewed path under multiple deterministic source-selection policies. It does not average conflicting rows or create synthetic candles.

- Status: `STABLE_VALID_PATH`
- Overlap groups: 908
- Material conflict groups: 412
- Decision-relevant conflict groups: 0
- Conflict fields: `{"rsi": 412}`

| Policy | Same valid path | Valid transition symmetric difference | Proposed transitions | Review counts |
|---|---|---:|---:|---|
| MOST_COMPLETE_LATEST | True | 0 | 22 | {"PASS": 15, "REJECT": 4, "RESTRICT": 3} |
| EARLIEST_CAPTURE | True | 0 | 22 | {"PASS": 15, "REJECT": 4, "RESTRICT": 3} |
| LATEST_CAPTURE | True | 0 | 22 | {"PASS": 15, "REJECT": 4, "RESTRICT": 3} |
| MIN_DISAGREEMENT | True | 0 | 22 | {"PASS": 15, "REJECT": 4, "RESTRICT": 3} |

## Interpretation

All tested source-selection policies preserve the valid reviewed transition path.

A stable result means only that the current research engine is insensitive to the tested source policies. It does not prove that every conflicting field is correct.
