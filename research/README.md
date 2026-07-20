# Black John Research Layer

## Purpose

This directory is the stable entrypoint for agents working with the repository's Binance Futures research corpus and Black John skills.

The layer does **not** replace raw data, rewrite legacy notes, or modify production scanner behavior. It organizes how an agent should discover, load, audit, and use the existing corpus.

## Authority order

1. Research protocol and governance.
2. Raw chronological market data.
3. Persistent State Ledger.
4. Validated or conditional research rules.
5. Background skills and historical analyses.

Skills propose hypotheses. Raw data and blind replay decide whether those hypotheses survive.

## Mandatory skill entrypoint

Read the root registry first:

- [`BLACK_JOHN_RESEARCH_SKILLS.md`](../BLACK_JOHN_RESEARCH_SKILLS.md)
- [`RESEARCH_AGENT_CONTEXT.md`](../RESEARCH_AGENT_CONTEXT.md)

Then load the skills in the registry order, beginning with:

- `.claude/skills/black-john-research-governance/SKILL.md`
- `.claude/skills/black-john-fact-reconstruction/SKILL.md`
- `.claude/skills/black-john-research-state-ledger/SKILL.md`
- `.claude/skills/black-john-hypothesis-engine/SKILL.md`

## Corpus entrypoints

Use [`CORPUS_INDEX.md`](CORPUS_INDEX.md) to locate the major source classes, then use:

- `methodology/RESEARCH_PROTOCOL.md` for the mandatory forensic method;
- `methodology/DATA_DICTIONARY.md` for field semantics;
- `inventory/` for source classification and corpus status;
- `schemas/` for case studies, State Ledgers, hypotheses, audits and rule records;
- `registry/` for pattern hypotheses and rule lifecycle status;
- `cross_coin/` for campaign-level comparison.

## Source classes

1. **Observed market data** — CSV and JSONL enriched candle files. Highest evidentiary value after quality checks.
2. **Prior narrative analyses** — TXT and DOC files. Audit targets, not labels.
3. **Black John skills and prompts** — candidate mechanisms, questions and terminology. Hypothesis support only.
4. **Research outputs** — State Ledgers, campaign records, hypothesis cards, replay traces, rule registry and cross-coin synthesis.
5. **Production code** — outside the research phase unless explicitly requested.

## Required workflow

```text
Inventory and data-quality audit
→ chronological fact reconstruction
→ multi-timeframe alignment
→ campaign segmentation
→ State Ledger update
→ competing hypotheses
→ supporting/opposing/missing evidence
→ adversarial falsification
→ positive/failed/control comparison
→ blind replay without lookahead
→ previous-analysis audit
→ rule-status decision
→ cross-coin synthesis
→ current scan only after research validation
```

## Non-negotiable constraints

- Never analyze only the final candle when earlier rows are available.
- Never use universal fixed analytical thresholds.
- Never treat RSI as an automatic blocker or directional decision.
- Never use future outcome while reconstructing a historical decision.
- Never convert missing data into neutral evidence.
- Never promote a narrative rule without failed cases, controls, and blind replay.
- Never let an old analysis override raw data.
- Preserve symbol-specific, timeframe-specific, liquidity-specific, and regime-specific context.
- One opposing candle cannot terminate a campaign.
- Absence from a ranked file means `NOT_OBSERVED_IN_CURRENT_SAMPLE`, not campaign failure.
- A long narrative is not evidence of deep analysis; traceable chronology, comparison and falsification are required.

## Repository policy

Raw files remain in their original paths during the inventory phase. The research layer references them without moving, renaming, deleting or overwriting evidence. Production code, scanners, backtests and decision logic remain outside scope unless a later task explicitly authorizes changes.
