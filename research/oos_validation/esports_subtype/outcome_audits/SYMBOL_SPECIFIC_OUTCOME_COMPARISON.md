# Symbol-Specific Campaign Outcome Comparison

This comparison is downstream of symbol-specific profiles. It compares mechanism performance without assuming one universal pattern.

| Symbol | Campaigns | Ignition observations | Ignition median terminal % | Accepted observations | Accepted median terminal % | Accepted path classes |
|---|---:|---:|---:|---:|---:|---|
| MAGMAUSDT | 2 | 1 | 29.50533462657614 | 0 | None | {} |
| TLMUSDT | 13 | 12 | 0.9638554216867545 | 5 | 0.6355573255326763 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 1, "NEGATIVE_PATH_OUTLIER": 1, "POSITIVE_PATH_OUTLIER": 2} |
| VELVETUSDT | 3 | 1 | 33.95366502088875 | 1 | 30.433179723502302 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |

## Reading rule

- Compare stages within a symbol before comparing symbols.
- A stage name is shared vocabulary, not proof of shared causal structure.
- Control-relative path classes are descriptive and sample-size dependent.
- No durable rule is promoted by this pass alone.
