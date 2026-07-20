# Research State Ledger Schema

Create one ledger per symbol and campaign. Append transitions; never overwrite prior judgments.

```yaml
schema_version: 1
symbol: SYMBOLUSDT
timeframe: 15m
campaign_id: SYMBOLUSDT-15m-YYYYMMDD-NNN
source_files: []
data_range:
  first_closed_candle: null
  last_closed_candle: null
quality:
  status: HIGH | MEDIUM | LOW | UNUSABLE
  flags: []
  confidence_cap: null
campaign:
  birth_time: null
  last_observed_time: null
  age_candles: null
  direction: BULLISH | BEARISH | MIXED | UNRESOLVED
  previous_state: null
  current_state: LATENT | EARLY_BUILD | CONFIRMED_BUILD | ARMED | IGNITION_CANDIDATE | ACCEPTED_IGNITION | EXPANSION | CONTINUATION_RELOAD | COOLING | EXHAUSTION | FAILURE | DISTRIBUTION | RESET | REBUILD | UNRESOLVED
  new_or_continuation: NEW | CONTINUATION | RELOAD | RESET | REBUILD | UNRESOLVED
milestones:
  first_detection: null
  first_warning: null
  armed: null
  ignition: null
  acceptance: null
  expansion: null
  weakness: null
  failure: null
  reset: null
  rebuild: null
hypotheses:
  dominant:
    name: null
    status: RESEARCH_HYPOTHESIS
  alternatives: []
  failure_or_noise: null
  unidentified_structure_considered: true
evidence:
  supporting: []
  opposing: []
  missing: []
trajectories:
  price: null
  oi: null
  oi_value: null
  execution: null
  positioning: null
  acceptance: null
assessment:
  structural_bias: null
  signal_importance: null
  readiness: null
  entry_safety: null
  data_reliability: null
  research_confidence: null
  freshness: null
  contradiction_level: null
next_discriminator: []
invalidation: []
transitions:
  - timestamp: null
    from_state: null
    to_state: null
    facts_added: []
    rationale: null
    opposing_evidence_preserved: []
    cutoff_frozen: true
outcome:
  visibility: HIDDEN | REVEALED
  classification: null
  revealed_after_frozen_record: true
```

## Rules

- Record `NOT_OBSERVED_IN_CURRENT_SAMPLE` as an observation, not failure.
- One opposing candle cannot reverse the campaign.
- Every transition needs independent timestamped evidence.
- Outcome fields remain hidden during blind replay.
