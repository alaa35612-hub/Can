# Previous Analysis Audit Schema

```yaml
audit_id: null
source_file: null
source_section: null
symbol: null
original_timestamp: null
original_conclusion: null
original_claimed_evidence: []
data_available_at_original_time: []
contemporary_valid_evidence: []
evidence_used_incorrectly: []
evidence_omitted: []
contradictory_evidence: []
missing_data_and_quality_limits: []
strongest_alternative_hypothesis: null
future_leakage:
  status: PASS | FAIL | UNRESOLVED
  details: null
error_classes: []
subsequent_outcome:
  reveal_only_after_reconstruction: true
  classification: null
corrected_conclusion: null
methodological_lesson: null
rule_library_impact:
  rule_ids: []
  action: RETAIN | RESTRICT | KEEP_AS_HYPOTHESIS | REJECT | DEPRECATE
```

## Error classes to check

- latest-candle isolation;
- outcome-conditioned narrative;
- RSI burial;
- OI direction treated as trade direction;
- OI contracts confused with OI value;
- Trades shock without value/persistence confirmation;
- Top Accounts confused with Top Positions;
- acceptance/rejection omitted;
- late extension treated as fresh ignition;
- cold-start rejected for missing long buildup;
- ranked-list disappearance treated as failure;
- fixed-threshold overgeneralization;
- continuation treated as a new campaign;
- temporary cooling treated as collapse;
- no negative or ordinary controls.

A correct price outcome does not validate incorrect reasoning.