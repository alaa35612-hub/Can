# ESPORTSUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 8
- Horizons: 30, 60, 120, 240, 480, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 210

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 8 | 1.4619883040935644 | 4.920405209840806 | -1.3212795549374157 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 6, "POSITIVE_PATH_OUTLIER": 1} |
| CONFIRMED_BUILD | 6 | 2.0804438280166426 | 5.238095238095242 | -1.5950069348127704 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 4, "POSITIVE_PATH_OUTLIER": 1} |
| IGNITION_CANDIDATE | 8 | 1.3937282229965264 | 4.253835425383534 | -2.0408163265306034 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 6, "NEGATIVE_PATH_OUTLIER": 1} |
| ACCEPTED_IGNITION | 4 | 13.320647002854425 | 35.39486203615603 | -4.689655172413798 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 2, "NEGATIVE_PATH_OUTLIER": 1} |
| EXPANSION | 4 | 14.979454613373179 | 31.15207373271889 | -6.649234217407551 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "MATCHED_CONTROL_LIKE": 3} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from causal inactive states with a labeled quiet fallback.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
