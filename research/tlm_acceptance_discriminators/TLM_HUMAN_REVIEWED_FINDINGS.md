# TLMUSDT Acceptance Discriminators — Human Review

## Effective evidence

- Campaigns reviewed: 13
- Accepted expansion: 4
- Accepted without expansion: 1
- Failed ignition: 8
- Continuous metrics with non-overlapping observed success/failure ranges: 0
- Fuel-retention campaigns: [3, 10, 13]
- Transient-spike campaigns: [8, 11]
- Rejected-acceptance-chain campaigns: [4, 6, 7, 11]

## Rule lifecycle

| Rule | Decision | Evidence basis | Limitations |
|---|---|---|---|
| TLM_SINGLE_FEATURE_POST_IGNITION_DISCRIMINATOR | REJECT | No tested price, OI, execution, or taker-flow metric produced a non-overlapping success/failure range at 15, 30, 45, or 60 minutes. | Rejects standalone feature sufficiency; ordered multi-feature context remains testable. |
| TLM_POST_IGNITION_FUEL_RETENTION | RESTRICT | Observed in accepted-expansion campaigns [3, 13], failed analogues [], and accepted-without-expansion campaigns [10]. | The accepted-without-expansion case prevents an expansion-sufficiency claim; campaigns are from one symbol and one observed period. |
| TLM_SHORT_COVERING_AS_OUTCOME_DISCRIMINATOR | REJECT | Accepted-expansion analogues [5, 9] and failed analogues [12] share the same short-covering context. | Short covering may describe a mechanism, but it does not discriminate acceptance from failure in this sample. |
| TLM_TRANSIENT_EXECUTION_SPIKE_FAILURE_WARNING | RESTRICT | Failed analogues [8, 11]; accepted-expansion analogues []. | Not necessary for failure: several failed campaigns used other paths or lacked an evaluable prior baseline. |
| TLM_REJECTED_ACCEPTANCE_CHAIN_FAILURE_CONTEXT | RESTRICT | Rejected acceptance chains by outcome: {'FAILURE': 4}. | A rejection chain is not necessary for failure; fast failures also occur without an acceptance proposal. |
| TLM_ACCEPTED_IGNITION_SUFFICIENCY_FOR_EXPANSION | REJECT | Accepted-without-expansion campaigns: [10]. | Accepted ignition remains a state observation, not a guaranteed expansion outcome. |

## Interpretation boundary

- All decisions are TLM-specific.
- `RESTRICT` creates a narrower research hypothesis, not a production signal.
- Structural outcome, nominal forward return, and matched-control path class remain separate.
- No result is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.
