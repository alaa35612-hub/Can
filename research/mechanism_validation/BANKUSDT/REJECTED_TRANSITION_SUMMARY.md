# BANKUSDT Rejected-Transition Negative Controls

Rejected transitions remain invalid historical decisions. Their future paths are measured only to test whether the review gate discriminated useful from misleading proposals.

- Negative anchors: 4
- Outcome rows: 28
- Comparison horizon: 720 minutes

| Proposed state | Observations | Complete | Median terminal return % | Path classes |
|---|---:|---:|---:|---|
| ACCEPTED_IGNITION | 1 | 1 | 0.8480403392161273 | {"NEGATIVE_PATH_OUTLIER": 1} |
| CONTINUATION_RELOAD | 1 | 1 | 0.2733485193621821 | {"NEGATIVE_PATH_OUTLIER": 1} |
| EXPANSION | 1 | 1 | 0.7776761207685334 | {"NEGATIVE_PATH_OUTLIER": 1} |
| FAILURE | 1 | 1 | 9.584664536741204 | {"NEGATIVE_PATH_OUTLIER": 1} |

## Valid versus rejected proposals

| Stage | Valid complete | Rejected complete | Valid median terminal % | Rejected median terminal % | Directional result | Discrimination |
|---|---:|---:|---:|---:|---|---|
| ACCEPTED_IGNITION | 1 | 1 | 52.60552729272652 | 0.8480403392161273 | VALID_DIRECTIONALLY_HIGHER | INSUFFICIENT_PAIRED_SAMPLE |
| CONFIRMED_BUILD | 3 | 0 | 1.6721620348563393 | None | UNRESOLVED | NO_PAIRED_SAMPLE |
| CONTINUATION_RELOAD | 0 | 1 | None | 0.2733485193621821 | UNRESOLVED | NO_PAIRED_SAMPLE |
| EARLY_BUILD | 4 | 0 | 1.1173972909795271 | None | UNRESOLVED | NO_PAIRED_SAMPLE |
| EXPANSION | 1 | 1 | 43.012383118524134 | 0.7776761207685334 | VALID_DIRECTIONALLY_HIGHER | INSUFFICIENT_PAIRED_SAMPLE |
| FAILURE | 0 | 1 | None | 9.584664536741204 | UNRESOLVED | NO_PAIRED_SAMPLE |
| IGNITION_CANDIDATE | 4 | 0 | 2.0546681345847695 | None | UNRESOLVED | NO_PAIRED_SAMPLE |

No rejected transition is retroactively promoted because its future path happened to be positive.
