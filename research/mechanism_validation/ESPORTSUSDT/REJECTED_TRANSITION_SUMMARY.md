# ESPORTSUSDT Rejected-Transition Negative Controls

Rejected transitions remain invalid historical decisions. Their future paths are measured only to test whether the review gate discriminated useful from misleading proposals.

- Negative anchors: 15
- Outcome rows: 105
- Comparison horizon: 720 minutes

| Proposed state | Observations | Complete | Median terminal return % | Path classes |
|---|---:|---:|---:|---|
| ACCEPTED_IGNITION | 4 | 4 | 2.142940990207609 | {"MATCHED_CONTROL_LIKE": 3, "POSITIVE_PATH_OUTLIER": 1} |
| CONTINUATION_RELOAD | 3 | 3 | 3.7904893177119314 | {"MATCHED_CONTROL_LIKE": 2, "POSITIVE_PATH_OUTLIER": 1} |
| COOLING | 2 | 2 | 3.5360967012503353 | {"MATCHED_CONTROL_LIKE": 2} |
| EXPANSION | 2 | 2 | 1.7560611548297134 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |
| FAILURE | 4 | 4 | 2.576507054620325 | {"MATCHED_CONTROL_LIKE": 3, "POSITIVE_PATH_OUTLIER": 1} |

## Valid versus rejected proposals

| Stage | Valid complete | Rejected complete | Valid median terminal % | Rejected median terminal % | Directional result | Discrimination |
|---|---:|---:|---:|---:|---|---|
| ACCEPTED_IGNITION | 3 | 4 | 13.320647002854425 | 2.142940990207609 | VALID_DIRECTIONALLY_HIGHER | NO_CLEAR_DISCRIMINATION |
| CONFIRMED_BUILD | 5 | 0 | 2.0804438280166426 | None | UNRESOLVED | NO_PAIRED_SAMPLE |
| CONTINUATION_RELOAD | 0 | 3 | None | 3.7904893177119314 | UNRESOLVED | NO_PAIRED_SAMPLE |
| COOLING | 0 | 2 | None | 3.5360967012503353 | UNRESOLVED | NO_PAIRED_SAMPLE |
| EARLY_BUILD | 7 | 0 | 1.4619883040935644 | None | UNRESOLVED | NO_PAIRED_SAMPLE |
| EXPANSION | 3 | 2 | 14.979454613373179 | 1.7560611548297134 | VALID_DIRECTIONALLY_HIGHER | NO_CLEAR_DISCRIMINATION |
| FAILURE | 0 | 4 | None | 2.576507054620325 | UNRESOLVED | NO_PAIRED_SAMPLE |
| IGNITION_CANDIDATE | 7 | 0 | 1.3937282229965264 | None | UNRESOLVED | NO_PAIRED_SAMPLE |

No rejected transition is retroactively promoted because its future path happened to be positive.
