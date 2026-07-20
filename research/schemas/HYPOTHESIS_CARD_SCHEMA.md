# Competing Hypothesis Card Schema

```yaml
hypothesis_id: null
campaign_id: null
name: null
status: BACKGROUND_CONCEPT | RESEARCH_HYPOTHESIS | SUPPORTED_PATTERN | CONDITIONAL_RULE | DURABLE_RULE | REJECTED_RULE | DEPRECATED
source_provenance: []
causal_mechanism: null
prerequisites: []
expected_ordered_sequence: []
observed_sequence: []
supporting_evidence: []
opposing_evidence: []
missing_evidence: []
historical_successful_analogues: []
historical_failed_analogues: []
matched_controls: []
discriminators: []
invalidation_conditions: []
assumptions: []
future_leakage_check: PASS | FAIL | UNRESOLVED
adaptive_context:
  symbol_history: null
  timeframe: null
  liquidity: null
  volatility: null
  regime: null
adversarial_review:
  strongest_alternative: null
  same_signature_in_failures: null
  survives_indicator_removal: null
  institutional_intent_identifiable: null
conclusion:
  role: DOMINANT | ALTERNATIVE | FAILURE_NOISE | NEW_UNIDENTIFIED_STRUCTURE
  confidence: null
  abstention_reason: null
  next_discriminating_evidence: []
```

A pattern name is never sufficient. The card must explain the ordered facts better than alternatives with fewer unsupported assumptions.