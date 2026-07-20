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

Then load the skills in its stated order, beginning with:

- `.claude/skills/black-john-research-governance/SKILL.md`
- `.claude/skills/black-john-fact-reconstruction/SKILL.md`
- `.claude/skills/black-john-research-state-ledger/SKILL.md`
- `.claude/skills/black-john-hypothesis-engine/SKILL.md`

## Corpus entrypoint

Use [`CORPUS_INDEX.md`](CORPUS_INDEX.md) to locate the major source classes:

- enriched Binance Futures candle datasets;
- multi-timeframe symbol studies;
- historical analyst notes and prior conclusions;
- failure and missed-move studies;
- structural-pattern research material;
- agent skills and research governance.

## Required workflow

```text
Inventory and data-quality audit
→ chronological fact reconstruction
→ multi-timeframe alignment
→ campaign segmentation
→ State Ledger update
→ competing hypotheses
→ supporting/opposing/missing evidence
→ positive/failed/control comparison
→ blind replay without lookahead
→ rule-status decision
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

## Repository mutation policy

This layer is documentation and indexing only. Raw files remain in their original paths. Production code, scanners, backtests, and decision logic are outside the scope of this branch unless a later task explicitly authorizes changes.
