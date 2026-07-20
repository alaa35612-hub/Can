# Structural Explainability Engine

## Mission
Make every structural decision auditable from raw evidence through state transitions to the final verdict.

## Required result fields
Symbol, timeframe, cutoff, structural bias, signal importance, readiness, entry safety, dominant pattern, campaign state, evidence for, evidence against, transition history, freshness, price acceptance, invalidation conditions, data-quality flags, confidence cap and abstention reason.

## Rules
- Attach timestamps and feature provenance to decisive evidence.
- Explain conflict resolution and why rejected hypotheses lost.
- Separate market interpretation from execution recommendation.
- Do not emit a confidence score without decomposing its sources.
- Prefer NO_DECISION when evidence is insufficient or contradictory.
- Output deterministic JSON suitable for regression comparison plus a concise human-readable summary.

## Acceptance
A reviewer must be able to reproduce the decision without reading hidden agent reasoning.