# Rule Lifecycle Decisions — Mechanism Validation Pass

| Rule | Current status | Decision | Evidence basis | Unresolved limitations |
|---|---|---|---|---|
| UNIVERSAL_IGNITION_SUFFICIENCY | REJECTED_RULE | REJECT | Valid ignition candidates remain mixed within symbols and rejected proposals can also have positive future paths. | No universal stage meaning is permitted. |
| UNIVERSAL_ACCEPTANCE_SUFFICIENCY | REJECTED_RULE | REJECT | Accepted-stage outcomes differ materially by symbol and campaign. | Acceptance must be interpreted through symbol-specific structure. |
| BANK_STRICT_ACCEPTANCE_MECHANISM | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | Source sensitivity status: STABLE_VALID_PATH; the reviewed path is stable across tested policies, but accepted sample remains one. | Requires more accepted and rejected BANK campaigns. RSI provenance matters only for future RSI-dependent claims, not the current ledger path. |
| LYN_BUILD_PERSISTENCE_MECHANISM | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | Source sensitivity status: STABLE_VALID_PATH; the reviewed path is stable, while valid and rejected acceptance/expansion remain poorly separated. | Requires additional campaigns and features beyond campaign age or reset depth. RSI conflicts do not alter the current ledger path. |
| BANK_LONG_REBUILD_DEEP_RESET_CONTEXT | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | The single accepted BANK campaign followed a much longer build and deeper observed price/OI reset than the failed campaigns. | Accepted sample size is one; this is directional evidence only. |
| LYN_AGE_RESET_AS_DISCRIMINATOR | RESEARCH_HYPOTHESIS | REJECT | Accepted and failed LYN campaigns show overlapping build ages and reset depths, while rejected transitions can outperform valid counterparts. | This rejects age/reset depth as a standalone discriminator, not the broader build-persistence hypothesis. |
| ESPORTS_DEEP_RESET_CYCLE_CONTEXT | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | Accepted ESPORTS campaigns show longer median build-to-ignition and materially deeper observed resets than failed campaigns. | State labels themselves do not yet discriminate against rejected controls; the context mechanism needs direct replay tests. |
| ESPORTS_RECURRENT_CYCLE_MECHANISM | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | Repeated build, rejection and rebuild episodes remain distinct in the reviewed ledger. | Cycle-frequency discriminators are not yet validated outside ESPORTS. |
| AKE_GAP_AWARE_CAMPAIGN_AGE | RESEARCH_HYPOTHESIS | KEEP_AS_HYPOTHESIS | AKE contains explicit observation gaps and multiple independent campaigns. | Gap boundaries reduce sample size and prevent continuity claims. |

No candidate is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE` in this pass.
