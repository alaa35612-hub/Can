# Patched V3.2.1 Tree Alignment Report

Generated: 2026-06-06T18:40:57.640838+00:00

## Data discovery
- BSBUSDT: `BSBUSDT.txt` rows=80
- GUAUSDT: `GUAUSDT.txt` rows=80

## Before / After Metrics
### baseline_early_watch
- total_symbols: 2
- total_events: 1
- detected_rallies: 1
- missed_rallies: 0
- false_positives: 2
- precision: 0.3333333333333333
- recall: 1.0
- average_max_return_after_signal: 0.0
- median_max_return_after_signal: 0.0
- early_success_count: 1
- live_success_count: 0
- late_detection_count: 0
- failed_invalidated_count: 0
- pattern_distribution: `{'Fresh Long Build-up': 2}`
### patched_early_watch
- total_symbols: 2
- total_events: 1
- detected_rallies: 0
- missed_rallies: 1
- false_positives: 0
- precision: None
- recall: 0.0
- average_max_return_after_signal: 0
- median_max_return_after_signal: 0
- early_success_count: 0
- live_success_count: 0
- late_detection_count: 0
- failed_invalidated_count: 0
- pattern_distribution: `{}`
### baseline_strict_live
- total_symbols: 2
- total_events: 1
- detected_rallies: 1
- missed_rallies: 0
- false_positives: 2
- precision: 0.3333333333333333
- recall: 1.0
- average_max_return_after_signal: 0.0
- median_max_return_after_signal: 0.0
- early_success_count: 1
- live_success_count: 0
- late_detection_count: 0
- failed_invalidated_count: 0
- pattern_distribution: `{'Fresh Long Build-up': 2}`
### patched_strict_live
- total_symbols: 2
- total_events: 1
- detected_rallies: 0
- missed_rallies: 1
- false_positives: 0
- precision: None
- recall: 0.0
- average_max_return_after_signal: 0
- median_max_return_after_signal: 0
- early_success_count: 0
- live_success_count: 0
- late_detection_count: 0
- failed_invalidated_count: 0
- pattern_distribution: `{}`

## Alignment checks
- Enum validation: scanner sanity checks available and smoke-tested.
- Vacuum exception logic: stop-driven branch restored before candidate; candidate remains inactive.
- Base detector: latest ignition guard and ignition-zone rejection remain active.
- Trigger selection: earliest footprint trigger remains preferred.
- Micro backtest is no-lookahead; future returns are used only for outcome labeling.

## Remaining risks
- This is a small repository-data smoke backtest using text exports and quote-volume proxy.
- Full production validation still requires raw OHLCV/OI/L-S archives and negative controls.