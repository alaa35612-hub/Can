# AKEUSDT Research Synthesis — Pass 1

## Research status

This is the first causal, multi-timeframe, blind-replay-compatible reconstruction for AKEUSDT. It is not a durable-rule declaration and does not claim that every machine-proposed transition is valid.

## What the data supports

The latest independently reconstructed 15m segment begins after the documented observation gap on 12 July 2026.

Reviewed sequence:

```text
2026-07-12 16:15 UTC  Data-gap boundary / campaign reset
2026-07-12 16:30 UTC  Early Build — PASS
2026-07-12 20:00 UTC  Confirmed Build — PASS
2026-07-14 03:45 UTC  Ignition Candidate — PASS
2026-07-14 04:00 UTC  Accepted Ignition — PASS
2026-07-14 05:00 UTC  Expansion proposal — REJECTED
2026-07-14 16:15 UTC  Continuation/Reload proposal — RESTRICTED
```

The important research result is not the later rally itself. The causal ledger identified a fresh campaign structure from 12 July and reached an accepted ignition hypothesis on 14 July, before the major daily expansion visible on 15 July.

## Why this is not yet a final rule

- The campaign is one positive case.
- The 15m history contains source gaps.
- There are 99 materially conflicting overlapping rows across captures; they remain preserved and must be reconciled by source version and capture provenance.
- Daily history is short and cannot provide a mature higher-timeframe baseline.
- The automated expansion transition failed adversarial review.
- Failed and ordinary windows must be compared using the same evidence sequence.

## Dominant interpretation

The strongest current explanation is a staged build followed by execution-led ignition:

```text
Reset / new observable segment
→ OI-led Early Build
→ persistent Confirmed Build
→ execution shock with positive release
→ retained price structure / Accepted Ignition
```

This resembles a hybrid of Quiet Build and Execution-led Ignition. It should not yet be forced into one legacy pattern family.

## Competing explanations still open

- short-covering-only movement;
- event-driven transient repricing;
- derivatives response to spot-led demand;
- an unidentified structure not represented in the existing skills corpus.

These alternatives require taker-flow persistence, spot evidence, post-ignition OI retention and failed-analogue comparison.

## Methodological corrections learned

1. Data gaps must reset campaign continuity unless continuation can be independently reconstructed.
2. A retention candle alone does not always confirm acceptance; abnormal negative price displacement can invalidate it.
3. Expansion cannot be inherited from prior support. It needs current-cutoff independent confirmation.
4. Continuation with negative displacement must be restricted rather than accepted automatically.
5. Raw State Ledger transitions are candidate judgments; the adversarially reviewed ledger is the valid research interface.

## Next required validation

- reconcile the 99 overlapping-row conflicts by capture/version provenance;
- compare the 12–14 July sequence against the five ordinary AKE controls;
- identify failed AKE ignition candidates with similar OI/execution signatures;
- audit prior narrative analyses that mention AKE;
- reproduce the same protocol on BANKUSDT, ESPORTSUSDT and LYNUSDT;
- update the rule registry only after cross-case discrimination and blind replay.
