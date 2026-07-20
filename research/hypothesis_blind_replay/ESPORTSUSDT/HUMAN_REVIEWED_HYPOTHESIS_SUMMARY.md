# ESPORTSUSDT Human-Reviewed Hypothesis Replay

- Original rule: `ESPORTS_DEEP_RESET_CYCLE_CONTEXT`
- Independent comparison unit: `CAMPAIGN`
- Raw anchor-level result: `INCONCLUSIVE_DIRECTIONAL_EVIDENCE`
- Reviewed campaign-level result: `DIRECTIONAL_FULL_CONTEXT_SUBTYPE_SUPPORT`

## Campaign evidence

- Evaluable campaigns: 5
- Success campaigns: [6, 7, 8]
- Failure campaigns: [4, 5]
- Full-context success campaigns: [6, 8]
- Full-context failure campaigns: []

## Rejected controls

- Raw rejected anchors: 15
- Evaluable rejected campaigns: 2
- Rejected campaigns satisfying full context: []

## Rule lifecycle

- Current status: `RESEARCH_HYPOTHESIS`
- Decision: `RESTRICT`
- Restricted rule ID: `ESPORTS_MATURE_DEEP_RESET_SUBTYPE`
- Reason: Two accepted campaigns satisfy the full conjunction while no assessed failure or rejected campaign does. Another accepted campaign succeeds without a long rebuild, so the context is a possible subtype and not a necessary condition.

Partial context and repeated rejected transitions remain visible in the raw trace, but they are not counted as independent fulfillment of the frozen joint hypothesis.
