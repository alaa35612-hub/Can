# AKEUSDT Rejected-Transition Negative Controls

Rejected transitions remain invalid historical decisions. Their future paths are measured only to test whether the review gate discriminated useful from misleading proposals.

- Negative anchors: 5
- Outcome rows: 30
- Comparison horizon: 720 minutes

| Proposed state | Observations | Complete | Median terminal return % | Path classes |
|---|---:|---:|---:|---|
| ACCEPTED_IGNITION | 1 | 1 | 4.3636363636363695 | {"POSITIVE_PATH_OUTLIER": 1} |
| CONTINUATION_RELOAD | 2 | 1 | -0.9518773135906877 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 1} |
| EXPANSION | 2 | 2 | 1.6225385852547514 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |

## Valid versus rejected proposals

| Stage | Valid complete | Rejected complete | Valid median terminal % | Rejected median terminal % | Discrimination |
|---|---:|---:|---:|---:|---|
| ACCEPTED_IGNITION | 2 | 1 | 3.4184994165767986 | 4.3636363636363695 | NO_CLEAR_DISCRIMINATION |
| CONFIRMED_BUILD | 2 | 0 | 1.085328333259128 | None | NO_PAIRED_SAMPLE |
| CONTINUATION_RELOAD | 0 | 1 | None | -0.9518773135906877 | NO_PAIRED_SAMPLE |
| EARLY_BUILD | 3 | 0 | 0.8397135095085329 | None | NO_PAIRED_SAMPLE |
| EXPANSION | 1 | 2 | 20.74416342412451 | 1.6225385852547514 | VALID_STAGE_DISCRIMINATES |
| IGNITION_CANDIDATE | 3 | 0 | 1.5136226034308864 | None | NO_PAIRED_SAMPLE |

No rejected transition is retroactively promoted because its future path happened to be positive.
