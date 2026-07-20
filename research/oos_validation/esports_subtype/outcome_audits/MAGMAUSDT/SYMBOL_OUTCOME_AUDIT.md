# MAGMAUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 2
- Horizons: 30, 60, 120, 240, 480, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 14

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 1 | 29.664142884876732 | 30.656668608037286 | -1.1454086585129142 | {"NEGATIVE_PATH_OUTLIER": 1} |
| IGNITION_CANDIDATE | 1 | 29.50533462657614 | 30.555286129970916 | -1.2221144519883542 | {"NEGATIVE_PATH_OUTLIER": 1} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from causal inactive states with a labeled quiet fallback.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
