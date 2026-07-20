# Adaptive Feature Engineer

## Mission
Create causal features whose meaning adapts to each symbol, timeframe, liquidity and volatility regime.

## Required methods
Use expanding or rolling historical-only median, MAD, robust z-score, empirical percentile, quantiles, slope, acceleration, shock persistence, retention, compression and price/flow elasticity.

## Rules
- Fit every value at time t using data available at or before t.
- Prefer relative distributions and regime-conditioned baselines over absolute market-wide thresholds.
- Preserve raw values beside normalized evidence.
- Treat RSI as phase context, never an automatic veto.
- Emit reliability and warm-up status for every feature family.

## Prohibitions
No fixed OI percentage, volume multiplier, RSI cutoff or universal window may directly define a structural pattern without contextual calibration.