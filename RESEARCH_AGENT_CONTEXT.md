# Black John Research Agent Context

## Purpose

This repository is a forensic structural-market research corpus. For research tasks, the agent's job is not to modify the scanner or summarize files superficially. The job is to reconstruct complete market campaigns, audit previous conclusions, test competing explanations, discover corrected or new rules, and identify partial structures that may be preparing for an upward campaign.

## Scope boundary

- Do not change production scanner, backtest or runtime code unless explicitly requested.
- Preserve all uploaded source files as evidence.
- Treat CSV/JSONL market files as observed data, TXT/DOC analyses as fallible prior claims, and Black John skills as a hypothesis corpus.
- Never infer campaign termination from absence in a ranked sample.
- Never convert legacy numeric thresholds into universal gates.

## Mandatory load order

1. `AGENTS.md`
2. `BLACK_JOHN_RESEARCH_SKILLS.md`
3. `.claude/skills/black-john-research-governance/SKILL.md`
4. `.claude/skills/black-john-fact-reconstruction/SKILL.md`
5. `.claude/skills/black-john-research-state-ledger/SKILL.md`
6. `.claude/skills/black-john-hypothesis-engine/SKILL.md`
7. `.claude/skills/black-john-background-corpus/SKILL.md`
8. `.claude/skills/black-john-previous-analysis-auditor/SKILL.md`
9. `.claude/skills/black-john-blind-replay/SKILL.md`
10. `.claude/skills/black-john-rule-validation-lifecycle/SKILL.md`
11. `.claude/skills/black-john-cross-coin-synthesis/SKILL.md`
12. `.claude/skills/black-john-current-scan-research/SKILL.md`
13. `research/README.md`
14. Relevant schemas and registries under `research/`

## Authority order

```text
Research protocol governs.
Raw observed data judges.
State Ledgers preserve context.
Skills propose hypotheses.
Blind replay tests detectability.
Controls prevent sample illusion.
Previous analyses are audited.
```

## Required research cycle

```text
Inventory and quality audit
→ chronological fact reconstruction
→ campaign segmentation
→ State Ledger update
→ competing hypotheses
→ adversarial falsification
→ success/failure/control comparison
→ blind replay
→ rule lifecycle decision
→ cross-coin synthesis
→ current partial-sequence scan
```

## Completion standard

A research task is incomplete unless it exposes observed facts, temporal ordering, dominant and alternative hypotheses, supporting/opposing/missing evidence, historical and failed analogues, uncertainty, next discriminator, invalidation, data reliability, and the validation status of every invoked rule.
