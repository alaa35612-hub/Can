# AKEUSDT Campaign Outcome Audit

Future outcomes are attached after the original frozen cutoff. They do not rewrite the original research decision.

- Campaigns: 4
- Horizons: 45, 60, 180, 240, 720, 1440 minutes
- Longest audited horizon: 1440 minutes
- Comparison horizon: 720 minutes
- Outcome rows: 90

## Stage results at the comparison horizon

| Stage | Campaign observations | Median terminal return % | Median close-path MFE % | Median close-path MAE % | Path classes |
|---|---:|---:|---:|---:|---|
| EARLY_BUILD | 4 | 0.8397135095085329 | 0.8397135095085329 | -4.236855538540063 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 3} |
| CONFIRMED_BUILD | 2 | 1.085328333259128 | 3.0011301838802518 | -4.097727373922105 | {"INSUFFICIENT_MATCHED_CONTROLS": 2} |
| IGNITION_CANDIDATE | 4 | 1.5136226034308864 | 5.751765893037342 | -4.113763331640419 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 3} |
| ACCEPTED_IGNITION | 3 | 3.4184994165767986 | 5.9580314763927 | -2.4648349181152165 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 2} |
| EXPANSION | 2 | 20.74416342412451 | 21.352140077821 | -0.4863813229571967 | {"INCOMPLETE_FORWARD_COVERAGE": 1, "INSUFFICIENT_MATCHED_CONTROLS": 1} |

## Interpretation constraints

- Original state decisions remain frozen.
- Close-path MFE/MAE are not intrabar MFE/MAE.
- Controls are same-symbol, context-matched, and from non-active causal states.
- Path classes describe relative outcomes; they are not entries, exits, or universal rules.
- Incomplete forward coverage is retained rather than extrapolated.
