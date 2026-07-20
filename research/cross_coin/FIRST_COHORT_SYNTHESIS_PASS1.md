# First Cohort Synthesis — Causal Pass 1

## Scope

This synthesis compares AKEUSDT, BANKUSDT, ESPORTSUSDT and LYNUSDT using frozen cutoffs, prior-only symbol-local distributions, higher-timeframe close guards, same-asset control windows, data-gap boundaries and adversarial transition review.

The output is a research synthesis, not a trading rule set. No pattern is promoted to durable status.

## Evidence quality

| Symbol | Main evidence advantage | Main confidence limitation |
|---|---|---|
| AKEUSDT | Three separately reconstructed observation segments and a pre-expansion accepted ignition path | 99 materially conflicting overlapping rows and short daily history |
| BANKUSDT | Multiple timeframes and repeated captures | 412 source conflicts; provenance disagreement materially caps confidence |
| ESPORTSUSDT | Clean source overlap with zero material conflicts | Many repeated campaign attempts, including several rejected acceptance chains |
| LYNUSDT | Multiple accepted sequences across the observed window | 214 source conflicts and repeated ignition failures before later valid sequences |

## Reviewed structural findings

### AKEUSDT

The newest independently observed segment progressed through:

`EARLY_BUILD → CONFIRMED_BUILD → IGNITION_CANDIDATE → ACCEPTED_IGNITION`

The automated transition to `EXPANSION` was rejected because it lacked two independent current-cutoff supports. This is retained as an accepted ignition case, not an automatically confirmed expansion case.

### BANKUSDT

BANK produced several failed ignition attempts before a later reviewed sequence on 18 July:

`CONFIRMED_BUILD → IGNITION_CANDIDATE → ACCEPTED_IGNITION → EXPANSION → CONTINUATION_RELOAD`

A prior 15 July acceptance was rejected because it occurred on abnormal negative price dislocation. Every dependent expansion/continuation transition was also rejected until a later campaign was independently re-anchored.

BANK cannot be treated as a clean reference case until the 412 source conflicts are resolved or sensitivity-tested across competing source selections.

### ESPORTSUSDT

ESPORTS contained the largest number of proposed transitions. This did not imply superior detectability. Adversarial review rejected several acceptance proposals and their entire descendant chains.

Clean reviewed sequences remained on 14, 16, 17 and 18 July. The repeated alternation between campaign success and failure indicates a highly recurrent or rotational structure rather than one continuous accumulation campaign.

ESPORTS is therefore useful for studying:

- recurrent ignition attempts;
- failed acceptance versus valid acceptance;
- campaign reset and re-anchoring;
- why transition count must never become a ranking score.

### LYNUSDT

LYN contained valid accepted sequences on 14 and 17 July, while acceptance proposals on 15 and 18 July were rejected due to abnormal negative price dislocation. Descendant expansion and continuation states were rejected automatically when their predecessor was invalid.

This makes LYN a useful within-symbol contrast between:

- accepted ignition followed by expansion;
- ignition candidate followed by false acceptance;
- later re-anchoring from fresh build evidence.

## Cross-case deductions

### 1. Ignition is not acceptance

An execution shock and positive build can justify `IGNITION_CANDIDATE`, but the next state requires price retention without contradictory negative dislocation or immediate fuel collapse.

### 2. Rejected ancestry invalidates descendants

If `ACCEPTED_IGNITION` is rejected, later machine-proposed `EXPANSION`, `CONTINUATION_RELOAD` or `FAILURE` states that depend on that invalid state cannot remain valid by default.

A new chain may become reviewable only after independent evidence re-anchors the campaign.

### 3. Repeated attempts are structurally meaningful

Repeated failed and successful ignition attempts should not be compressed into one campaign narrative. They may indicate rotational leverage, repeated liquidity tests, event-driven execution or unstable acceptance.

### 4. Source agreement is part of structural confidence

BANK and LYN have substantial conflicting overlaps. A structurally attractive sequence from one chosen source is not enough for high confidence when another capture materially disagrees at the same timestamp.

### 5. Transition count is not signal strength

ESPORTS produced many transitions because its structure repeatedly rotated through build, ignition, acceptance, continuation and failure. This is a complexity measure, not a bullish score.

## Rule-status decisions

| Candidate rule | Status after cohort pass 1 | Reason |
|---|---|---|
| Execution shock alone confirms ignition | REJECTED | It can mark an ignition candidate, but not acceptance or direction persistence |
| Positive OI plus execution implies bullish acceptance | CONDITIONAL | Requires price response, retention and contradiction review |
| Negative price dislocation can coexist with accepted ignition | REJECTED for immediate acceptance | Observed false acceptance chains in BANK, ESPORTS and LYN |
| A rejected state may still support valid descendants | REJECTED | Descendant states require a valid predecessor or independent re-anchoring |
| Repeated campaign attempts imply one continuous campaign | REJECTED | ESPORTS and LYN show distinct failed and successful attempts |
| Data-source conflict is merely a technical detail | REJECTED | It directly caps structural confidence and must remain visible |
| Same-symbol adaptive history is preferable to universal raw thresholds | SUPPORTED METHODOLOGICALLY | It preserves asset-specific scale, liquidity and regime context; predictive value still requires broader replay |

## Next validation requirement

The next pass must evaluate event outcomes and pre-signal lead time without allowing outcome data into the state decisions. It should compare:

- accepted sequences that led to material continuation;
- accepted sequences that failed shortly afterward;
- rejected acceptance proposals;
- ordinary control windows;
- sensitivity to competing source captures for BANK and LYN.

Only after this comparison may a rule move from research hypothesis toward supported or conditional status.
