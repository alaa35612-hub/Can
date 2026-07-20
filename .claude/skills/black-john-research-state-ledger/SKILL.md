# Black John Research State Ledger

## Mission
Preserve what was knowable and believed at every timestamp so campaign analysis is cumulative, reviewable and resistant to hindsight.

## Required ledger fields
- symbol, timeframe and campaign ID;
- campaign birth and last-observed time;
- previous and current structural state;
- first detection, first warning, armed, ignition, acceptance, expansion, weakness, failure, reset and rebuild times;
- dominant and alternative hypotheses;
- supporting, opposing and missing evidence;
- price, OI, execution and positioning trajectories;
- data reliability and confidence cap;
- freshness, entry safety and campaign age;
- contradiction history;
- transition cause and evidence timestamps;
- invalidation conditions;
- outcome only after the decision record is frozen.

## Reference states
Latent → Early Build → Confirmed Build → Armed → Ignition Candidate → Accepted Ignition → Expansion → Continuation/Reload → Exhaustion, Failure, Distribution, Reset or Rebuild.

The state list is descriptive, not a forced path. Cold-start campaigns may enter through an inflection path when the evidence justifies it.

## Update rules
- A new observation updates the prior ledger; it never restarts analysis.
- Preserve every prior state and rationale.
- Do not reverse direction from one opposing candle.
- Use hysteresis: require independent contrary evidence and structural invalidation.
- Distinguish temporary cooling from campaign failure.
- Distinguish absence from a sample from evidence of termination. Record `NOT_OBSERVED_IN_CURRENT_SAMPLE` unless direct failure evidence exists.
- Distinguish new campaign, continuation, reset and rebuild.

## Review questions
At every update ask:
- What changed since the previous record?
- Was the change expected by the prior hypothesis?
- Which evidence caused the transition?
- Did uncertainty decrease or increase?
- Was an earlier warning missed?
- Did the system oscillate because of noise?

## Output
A timestamped transition ledger suitable for blind replay, error audit and cross-coin comparison.