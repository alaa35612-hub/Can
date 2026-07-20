# LYNUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 5
- Horizons: 60, 90, 240, 360, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 114

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 5 | 1.2895991028875953 | 1.8783291281188497 | -0.05606952621249883 | {"MATCHED_CONTROL_LIKE": 2, "NEGATIVE_PATH_OUTLIER": 1, "POSITIVE_PATH_OUTLIER": 2} |
| CONFIRMED_BUILD | 5 | 1.7329545454545459 | 2.187500000000009 | 0.029351335485761076 | {"MATCHED_CONTROL_LIKE": 2, "POSITIVE_PATH_OUTLIER": 3} |
| IGNITION_CANDIDATE | 5 | 0.13743815283120409 | 1.3437849944009095 | -1.7077267637177984 | {"MATCHED_CONTROL_LIKE": 4, "POSITIVE_PATH_OUTLIER": 1} |
| ACCEPTED_IGNITION | 2 | 1.0098891047813197 | 1.7668559362504666 | -1.238280561813021 | {"MATCHED_CONTROL_LIKE": 1, "POSITIVE_PATH_OUTLIER": 1} |
| EXPANSION | 2 | 0.7238149304570007 | 1.8076980069910986 | -0.805637730410097 | {"MATCHED_CONTROL_LIKE": 2} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from causal inactive states with a labeled quiet fallback.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
