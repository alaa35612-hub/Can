# TLMUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 13
- Horizons: 45, 60, 180, 240, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 264

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 12 | -0.7803121248499356 | 4.021094264996705 | -3.736654804270456 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 6, "NEGATIVE_PATH_OUTLIER": 1, "POSITIVE_PATH_OUTLIER": 3, "TWO_SIDED_VOLATILITY_OUTLIER": 1} |
| CONFIRMED_BUILD | 11 | -0.6633906633906672 | 4.190177019124375 | -2.287613488975354 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 6, "POSITIVE_PATH_OUTLIER": 4} |
| IGNITION_CANDIDATE | 12 | 0.9638554216867545 | 5.1040967092008005 | -5.991077119184196 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 3, "NEGATIVE_PATH_OUTLIER": 3, "POSITIVE_PATH_OUTLIER": 3, "TWO_SIDED_VOLATILITY_OUTLIER": 2} |
| ACCEPTED_IGNITION | 5 | 0.6355573255326763 | 4.219521811180915 | -2.3240422592044507 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 1, "NEGATIVE_PATH_OUTLIER": 1, "POSITIVE_PATH_OUTLIER": 2} |
| EXPANSION | 4 | 0.26385224274407815 | 3.692674210839786 | -2.6801667659321016 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 2, "POSITIVE_PATH_OUTLIER": 1} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from causal inactive states with a labeled quiet fallback.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
