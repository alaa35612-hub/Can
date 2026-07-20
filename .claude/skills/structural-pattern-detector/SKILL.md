# Structural Pattern Detector

## Mission
Detect multiple causal campaign paths without forcing all symbols into one template.

## Pattern families
Quiet accumulation; Cold-Start OI Ignition; OI Reset Absorption and Rebuild; Price-led Base Ignition; Price-led Vacuum Ignition; High-OI Compression; Whale Divergence Build; Short Squeeze; Long-Crowded Flush Reclaim; Failed Flash; Distribution; Late Crowding; Continuation.

## Contract for each pattern
Define prerequisites, ordered evidence, persistence, confirmation, price acceptance, invalidation, freshness, entry quality and failure state.

## Rules
- Evaluate evidence sequences over time, not one candle.
- Allow parallel hypotheses until conflict resolution.
- Separate detection from entry timing.
- RSI describes phase only.
- Missing history reduces certainty but must not automatically reject legitimate cold-start campaigns.
- Every positive classification must expose the evidence timestamps that caused it.