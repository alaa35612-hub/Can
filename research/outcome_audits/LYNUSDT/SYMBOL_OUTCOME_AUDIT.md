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
| EARLY_BUILD | 5 | 1.2895991028875953 | 1.8783291281188497 | -0.05606952621249883 | {"INSUFFICIENT_MATCHED_CONTROLS": 5} |
| CONFIRMED_BUILD | 5 | 1.7329545454545459 | 2.187500000000009 | 0.029351335485761076 | {"INSUFFICIENT_MATCHED_CONTROLS": 5} |
| IGNITION_CANDIDATE | 5 | 0.13743815283120409 | 1.3437849944009095 | -1.7077267637177984 | {"INSUFFICIENT_MATCHED_CONTROLS": 5} |
| ACCEPTED_IGNITION | 2 | 1.0098891047813197 | 1.7668559362504666 | -1.238280561813021 | {"INSUFFICIENT_MATCHED_CONTROLS": 2} |
| EXPANSION | 2 | 0.7238149304570007 | 1.8076980069910986 | -0.805637730410097 | {"INSUFFICIENT_MATCHED_CONTROLS": 2} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from non-active causal states.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
