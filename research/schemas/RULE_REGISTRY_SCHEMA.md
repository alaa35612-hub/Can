# Rule Registry Schema

```yaml
rule_id: BJ-RULE-0001
version: 1
name: null
status: BACKGROUND_CONCEPT | RESEARCH_HYPOTHESIS | SUPPORTED_PATTERN | CONDITIONAL_RULE | DURABLE_RULE | REJECTED_RULE | DEPRECATED
statement_adaptive: null
legacy_claims: []
causal_mechanism: null
applicability:
  symbols: []
  timeframes: []
  liquidity_contexts: []
  volatility_contexts: []
  regimes: []
required_ordered_evidence: []
supporting_evidence: []
discriminators: []
failure_filters: []
invalidation: []
cases: {successful: [], failed: [], contradictory: [], controls: []}
blind_replay:
  runs: []
  first_warning_quality: null
  activation_quality: null
  false_positive_notes: null
  false_negative_notes: null
exceptions: []
confidence: null
limitations: []
provenance: []
revision_history: []
decision: PROMOTE | RESTRICT | KEEP_AS_HYPOTHESIS | REJECT | DEPRECATE
```

`DURABLE_RULE` requires recurrence across independent campaigns, discrimination from failures and controls, strict cutoff survival, adaptive evidence, documented applicability, explicit invalidation and no outcome-specific fitting.
