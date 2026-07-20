# Black John Blind Replay Protocol

## Mission
Determine whether a campaign, warning or rule was detectable using only information available at each historical cutoff.

## Replay procedure
1. Freeze the dataset at cutoff T1 using closed candles only.
2. Reconstruct facts, update the State Ledger and record the decision.
3. Advance one observation or one defined batch to T2.
4. Update the prior state; do not rewrite the T1 judgment.
5. Continue through warning, ignition, acceptance, continuation and failure stages.
6. Reveal future outcome only after each decision record is frozen.

## Leakage prohibitions
- No future extrema, peak time or future return in features or historical judgment.
- No baselines fitted with observations after the cutoff.
- No backward relabeling of state because the future outcome is known.
- No selecting only successful cutoffs.
- No using the final campaign pattern to constrain earlier hypotheses.

## Evaluation dimensions
- first structurally meaningful detection;
- first actionable or near-ignition detection;
- lead time and entry freshness;
- false warnings and false activations;
- missed campaigns;
- late detections;
- state stability and unjustified reversals;
- calibration and abstention quality;
- successful, failed and matched control windows.

## Required replay trace
For every cutoff record:
- available data range;
- current ledger state;
- dominant and alternative hypotheses;
- evidence added since prior cutoff;
- decision and confidence;
- expected discriminator;
- invalidation;
- outcome hidden/visible status.

## Rule
A narrative that explains the move after the peak is not early detection. Only frozen cutoff decisions count as evidence for a rule.