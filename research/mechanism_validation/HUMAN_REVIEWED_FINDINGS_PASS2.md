# Human-Reviewed Mechanism Findings — Pass 2

## Authority and scope

This review reads the symbol profile, campaign records, reviewed State Ledger, frozen-cutoff outcome audit, rejected-transition controls, and source-sensitivity results in that order. It does not rewrite any historical cutoff and does not promote a rejected transition because its later path was positive.

No result in this pass qualifies as a `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.

## Source-selection sensitivity

### BANKUSDT

- 908 overlapping source groups were inspected.
- 412 groups contain material differences.
- Every material difference is in `rsi`.
- Zero conflict groups affect fields used by the current State Ledger decision path.
- `MOST_COMPLETE_LATEST`, `EARLIEST_CAPTURE`, `LATEST_CAPTURE`, and `MIN_DISAGREEMENT` produce the same valid reviewed transition path: 15 PASS, 3 RESTRICT, and 4 REJECT.

Decision: the previous generic confidence penalty from “412 source conflicts” must be narrowed. These conflicts do not alter the current structural path. They remain relevant only to future claims that use RSI or to provenance auditing.

### LYNUSDT

- 498 overlapping source groups were inspected.
- 214 groups contain material differences.
- Every material difference is in `rsi`.
- Zero conflict groups affect fields used by the current State Ledger decision path.
- All four source-selection policies preserve the same valid path: 22 PASS, 2 RESTRICT, and 7 REJECT.

Decision: the current LYN structural path is source-policy stable. RSI provenance remains unresolved but is not a current decision-path limitation.

## Rejected transitions as negative controls

The minimum requirement for a discrimination claim is at least two complete valid observations and two complete rejected observations for the same proposed stage. A one-versus-one result is directional only.

### AKEUSDT

- Five rejected anchors were audited.
- Rejected `ACCEPTED_IGNITION` had one completed positive-path outlier.
- Valid acceptance versus rejected acceptance has no clear direction supporting the review gate.
- Valid expansion is directionally stronger than rejected expansion, but only one valid expansion observation is complete.

Decision: AKE acceptance and expansion gates are not validated as discriminators. The rejected positive acceptance path is not retroactively accepted; it shows that later recovery can follow a historically invalid acceptance proposal.

### BANKUSDT

- Four rejected anchors were audited.
- The single valid accepted campaign is directionally much stronger than the single rejected acceptance proposal at 720 minutes.
- The same directional separation appears for expansion.
- Both comparisons are one-versus-one and therefore `INSUFFICIENT_PAIRED_SAMPLE`.

Decision: retain strict BANK acceptance as a research hypothesis only. It is not a validated rule.

### ESPORTSUSDT

- Fifteen rejected anchors were audited.
- Valid versus rejected acceptance has `NO_CLEAR_DISCRIMINATION`.
- Valid versus rejected expansion also has `NO_CLEAR_DISCRIMINATION`.
- Rejected acceptance, continuation, expansion, cooling, and failure proposals can all be followed by ordinary or positive paths.

Decision: the shared state labels do not currently discriminate ESPORTS outcomes. Cycle position, reset context, and campaign history require direct testing.

### LYNUSDT

- Seven rejected anchors were audited.
- Valid versus rejected acceptance has `NO_CLEAR_DISCRIMINATION`.
- Valid versus rejected expansion has `NO_CLEAR_DISCRIMINATION`.
- Some rejected continuation and expansion proposals are followed by stronger paths than their valid counterparts.

Decision: acceptance and expansion labels are not reliable LYN discriminators in this corpus.

## Campaign mechanism measurements

### AKEUSDT

- Accepted-expansion campaigns have a median birth-to-ignition time of 247.5 minutes, but the two cases are structurally different: one is OI-led and one begins with simultaneous execution/OI evidence.
- The accepted-without-expansion campaign takes 2,115 minutes from birth to ignition.
- The failed ignition takes 165 minutes.
- Reset depth is unavailable for the later two campaigns because observation gaps interrupt continuity.

Decision: campaign age is context, not a standalone AKE rule. Gap boundaries remain mandatory.

### BANKUSDT

- The single accepted-expansion campaign takes 1,590 minutes from birth to ignition and 1,605 minutes to acceptance.
- Its observed reset from the previous campaign peak is approximately -14.45% in price and -10.75% in OI.
- Failed campaigns have a median birth-to-ignition time of 135 minutes and measured median resets near -0.92% in price and -0.65% in OI.
- All accepted, failed, and unresolved campaigns begin with simultaneous execution/price evidence; the leading mechanism alone does not discriminate them.

Decision: `BANK_LONG_REBUILD_DEEP_RESET_CONTEXT` remains a symbol-specific hypothesis. The accepted sample size is one.

### ESPORTSUSDT

- Four accepted-expansion campaigns have a median birth-to-ignition time of 300 minutes versus 202.5 minutes for four failed campaigns.
- Accepted campaigns have measured median resets near -15.74% in price and -5.68% in OI.
- Failed campaigns have measured median resets near -0.74% in price and -0.20% in OI.
- Despite this contextual separation, valid acceptance and expansion states do not discriminate against rejected controls.

Decision: retain `ESPORTS_DEEP_RESET_CYCLE_CONTEXT` and recurrent-cycle structure as hypotheses requiring direct blind replay. Do not promote the state labels.

### LYNUSDT

- Accepted campaigns have a median birth-to-ignition time of 1,012.5 minutes versus 1,050 minutes for failed campaigns.
- Accepted median resets are approximately -1.73% in price and -0.92% in OI.
- Failed median resets are approximately -2.39% in price and -1.63% in OI.
- These distributions overlap and do not explain the earlier observed usefulness of `CONFIRMED_BUILD`.

Decision: reject `LYN_AGE_RESET_AS_DISCRIMINATOR`. Retain the broader build-persistence hypothesis, but it requires other features.

## Rule lifecycle decisions

- Universal ignition sufficiency: `REJECT` / `REJECTED_RULE`.
- Universal acceptance sufficiency: `REJECT` / `REJECTED_RULE`.
- BANK strict acceptance: `KEEP_AS_HYPOTHESIS`.
- BANK long rebuild after deep reset: `KEEP_AS_HYPOTHESIS`.
- ESPORTS deep-reset cycle context: `KEEP_AS_HYPOTHESIS`.
- ESPORTS recurrent-cycle mechanism: `KEEP_AS_HYPOTHESIS`.
- LYN age/reset depth as a standalone discriminator: `REJECT`.
- LYN build persistence: `KEEP_AS_HYPOTHESIS`.
- AKE gap-aware campaign age: `KEEP_AS_HYPOTHESIS`.

## Required next validation

1. Blind-replay the BANK long-rebuild/deep-reset hypothesis with its discriminator frozen before acceptance.
2. Blind-replay ESPORTS cycle position using campaign number, reset depth, and build duration without using the final outcome.
3. Identify additional features that distinguish LYN confirmed builds from failed ignitions; age and reset depth are insufficient.
4. Keep RSI outside the decision path until its cross-capture provenance is resolved.
5. Add independent symbols before testing transfer of any mechanism across assets.
