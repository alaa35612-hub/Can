# Causal Backtest Researcher

## Mission
Evaluate whether the system could detect a campaign using only information available at each historical cutoff.

## Requirements
- Closed candles and strict cutoff enforcement.
- Historical-only feature fitting and persistent state replay.
- Walk-forward or purged temporal splits; embargo where overlap creates leakage.
- Positive event windows plus matched negative/control windows.
- Preserve symbol, timeframe and regime diversity.
- Compare early watch, near ignition, live ignition, continuation, late and failed states.

## Metrics
Precision, recall, PR-AUC, lead time, false alarms per day, stage recall, calibration, abstention quality, MAE/MFE after signal and entry freshness.

## Prohibitions
- No event labeling from future extrema inside feature generation.
- No random train/test split for overlapping time series.
- No recomputing past baselines with future observations.
- No reporting aggregate accuracy without class and stage breakdowns.