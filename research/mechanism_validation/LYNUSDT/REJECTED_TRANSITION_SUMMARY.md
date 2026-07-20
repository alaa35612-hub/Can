# LYNUSDT Rejected-Transition Negative Controls

Rejected transitions remain invalid historical decisions. Their future paths are measured only to test whether the review gate discriminated useful from misleading proposals.

- Negative anchors: 7
- Outcome rows: 42
- Comparison horizon: 720 minutes

| Proposed state | Observations | Complete | Median terminal return % | Path classes |
|---|---:|---:|---:|---|
| ACCEPTED_IGNITION | 2 | 2 | 0.9745803185519542 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |
| CONTINUATION_RELOAD | 2 | 2 | 10.142497904442571 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |
| EXPANSION | 2 | 2 | 4.336510474202626 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |
| FAILURE | 1 | 1 | 1.1210762331838486 | {"MATCHED_CONTROL_LIKE": 1} |

## Valid versus rejected proposals

| Stage | Valid complete | Rejected complete | Valid median terminal % | Rejected median terminal % | Discrimination |
|---|---:|---:|---:|---:|---|
| ACCEPTED_IGNITION | 2 | 2 | 1.0098891047813197 | 0.9745803185519542 | NO_CLEAR_DISCRIMINATION |
| CONFIRMED_BUILD | 5 | 0 | 1.7329545454545459 | None | NO_PAIRED_SAMPLE |
| CONTINUATION_RELOAD | 0 | 2 | None | 10.142497904442571 | NO_PAIRED_SAMPLE |
| EARLY_BUILD | 5 | 0 | 1.2895991028875953 | None | NO_PAIRED_SAMPLE |
| EXPANSION | 2 | 2 | 0.7238149304570007 | 4.336510474202626 | NO_CLEAR_DISCRIMINATION |
| FAILURE | 0 | 1 | None | 1.1210762331838486 | NO_PAIRED_SAMPLE |
| IGNITION_CANDIDATE | 5 | 0 | 0.13743815283120409 | None | NO_PAIRED_SAMPLE |

No rejected transition is retroactively promoted because its future path happened to be positive.
