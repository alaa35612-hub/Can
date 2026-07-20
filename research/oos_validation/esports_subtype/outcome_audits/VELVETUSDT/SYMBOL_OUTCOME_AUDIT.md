# VELVETUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 3
- Horizons: 30, 60, 120, 240, 480, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 49

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 2 | 20.490021734835008 | 26.7140881248765 | -4.090100770598692 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 1} |
| CONFIRMED_BUILD | 2 | 18.96449117238643 | 27.21682205911524 | -3.7095814322555043 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 1} |
| IGNITION_CANDIDATE | 1 | 33.95366502088875 | 34.922142043296645 | 3.019369540448169 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |
| ACCEPTED_IGNITION | 1 | 30.433179723502302 | 30.967741935483883 | 6.027649769585275 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |
| EXPANSION | 1 | 19.62680237489398 | 20.525869380831207 | -2.4257845631891373 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from causal inactive states with a labeled quiet fallback.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
