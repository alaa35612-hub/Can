# Symbol-Specific Campaign Outcome Comparison

This comparison is downstream of symbol-specific profiles. It compares mechanism performance without assuming one universal pattern.

| Symbol | Campaigns | Ignition observations | Ignition median terminal % | Accepted observations | Accepted median terminal % | Accepted path classes |
|---|---:|---:|---:|---:|---:|---|
| AKEUSDT | 4 | 4 | 1.5136226034308864 | 3 | 3.4184994165767986 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 1, "NEGATIVE_PATH_OUTLIER": 1} |
| BANKUSDT | 5 | 4 | 2.0546681345847695 | 1 | 52.60552729272652 | {"POSITIVE_PATH_OUTLIER": 1} |
| ESPORTSUSDT | 8 | 8 | 1.3937282229965264 | 4 | 13.320647002854425 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 2, "NEGATIVE_PATH_OUTLIER": 1} |
| LYNUSDT | 5 | 5 | 0.13743815283120409 | 2 | 1.0098891047813197 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |

## Reading rule

- Compare stages within a symbol before comparing symbols.
- A stage name is shared vocabulary, not proof of shared causal structure.
- Control-relative path classes are descriptive and sample-size dependent.
- No durable rule is promoted by this pass alone.
