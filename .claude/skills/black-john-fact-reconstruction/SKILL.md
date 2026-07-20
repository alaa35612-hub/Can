# Black John Causal Fact Reconstruction

## Mission
Reconstruct what happened from raw chronological market observations before applying any named pattern.

## Inputs
Price/OHLCV, quote volume, taker flow when available, number of trades, OI and OI value, funding, Global L/S, Top Account L/S, Top Position L/S, timestamps, timeframe, data-quality metadata and prior State Ledger.

## Procedure
1. Validate chronology, duplicates, gaps, candle closure, source coverage and timestamp alignment.
2. Merge all files for the same symbol without discarding prior context.
3. Divide history into campaigns and transitions rather than isolated snapshots.
4. Identify event order: compression, OI change, execution change, positioning change, breakout/reclaim, acceptance/rejection, persistence and failure.
5. Determine which variable led, confirmed, lagged or contradicted the move.
6. Distinguish a new campaign from continuation, reset, rebuild and noise.
7. Preserve raw observations separately from interpretations.

## Adaptive interpretation
Evaluate abnormality relative to the symbol, timeframe, liquidity, volatility, regime and historical distribution. Use robust ranks, relative distributions, slopes, acceleration, persistence and retention as descriptive evidence. Numeric values from legacy skills are research clues only, never universal gates.

## Mandatory fact table
For each relevant timestamp record:
- price state and structural location;
- OI direction, value confirmation and persistence;
- trades and quote-volume abnormality and persistence;
- positioning direction and cross-layer divergence;
- price acceptance or rejection;
- data-quality flags;
- whether the observation was available at the cutoff.

## Output
Produce a causal timeline with explicit facts, not a pattern label. Pattern hypothesis generation occurs only after this reconstruction.