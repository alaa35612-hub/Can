# BANKUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 5
- Horizons: 30, 60, 120, 240, 480, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 98

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 5 | 1.1173972909795271 | 2.9952618627219207 | -1.3421468786905588 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 4} |
| CONFIRMED_BUILD | 3 | 1.6721620348563393 | 2.9439472444653836 | -1.3198208814518164 | {"INSUFFICIENT_MATCHED_CONTROLS": 3} |
| IGNITION_CANDIDATE | 4 | 2.0546681345847695 | 2.616767050702984 | -1.4656853840990802 | {"INSUFFICIENT_MATCHED_CONTROLS": 4} |
| ACCEPTED_IGNITION | 1 | 52.60552729272652 | 58.71029836381136 | 8.813419496768859 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |
| EXPANSION | 1 | 43.012383118524134 | 45.85544604498357 | 25.322213798332083 | {"INSUFFICIENT_MATCHED_CONTROLS": 1} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and outside campaign neighborhoods.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
