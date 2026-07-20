# Human-Reviewed ESPORTS Subtype OOS Findings

The raw frozen assessments remain unchanged. This review separates abstention, structural outcome and forward return, and evaluates claims at the campaign unit.

## Effective sample

- Total ignition assessments: 14
- Evaluable campaigns: 9
- Abstained campaigns: 5
- Symbols with evaluable campaigns: TLMUSDT
- Symbols contributing abstention only: MAGMAUSDT, VELVETUSDT
- Association result: `INSUFFICIENT_INDEPENDENT_SYMBOL_SAMPLE`

MAGMA and VELVET abstentions are missing-history evidence, not failed subtype cases.

## Full-context counterexamples

- TLMUSDT campaign 11: structural failure; path class `MATCHED_CONTROL_LIKE`; terminal return 2.1196063588190706%; rejected transitions 3.

A structural failure can still have a positive nominal return. The matched-control path class is therefore retained separately from the campaign-state outcome.

## Successful campaigns without full context

- TLMUSDT campaign 5: accepted expansion under `PARTIAL_TRANSFER_CONTEXT`; path class `POSITIVE_PATH_OUTLIER`.
- TLMUSDT campaign 9: accepted expansion under `PARTIAL_TRANSFER_CONTEXT`; path class `MATCHED_CONTROL_LIKE`.
- TLMUSDT campaign 13: accepted expansion under `PARTIAL_TRANSFER_CONTEXT`; path class `POSITIVE_PATH_OUTLIER`.

These campaigns reject cross-symbol necessity; they do not prove that partial context is sufficient.

## Rule lifecycle

- `MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_SUFFICIENCY`: `REJECT`.
- `MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_NECESSITY`: `REJECT`.
- `ESPORTS_MATURE_DEEP_RESET_SUBTYPE`: `KEEP_AS_ESPORTS_SPECIFIC_HYPOTHESIS`.
- Cross-symbol association remains `INSUFFICIENT_INDEPENDENT_SYMBOL_SAMPLE` because only one external symbol supplied evaluable campaigns.
- No rule is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.

## Interpretation boundary

The TLM counterexample rejects the claim that the frozen conjunction is sufficient for accepted expansion across symbols. It does not prove that deep-reset maturity is irrelevant, and it does not invalidate the ESPORTS-specific subtype. Estimating external association requires additional independent symbols with enough prior campaigns to avoid abstention.
