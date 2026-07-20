# AI Agent Operating Contract

This repository contains production-oriented skills for AI coding agents that build and review Python systems for cryptocurrency and Binance Futures structural analysis.

## Mandatory operating rules

1. Read this file before changing code.
2. Load the relevant skill files from `.claude/skills/<skill-name>/SKILL.md` before implementation.
3. Build a complete, meaningful production layer first. Tests must validate that completed production behavior; never create test-only logic, compatibility shims, mock decision paths, or temporary analytical layers that later need to be converted into production code.
4. Trace the active production path from data ingestion through normalization, feature generation, persistent state, structural classification, conflict resolution, ranking, output, and persistence before modifying behavior.
5. Keep one authoritative final-decision path. Remove or explicitly retire obsolete classifiers, duplicate engines, and fallbacks that can contradict the production result.
6. Use closed candles and causal historical data only. No lookahead, future-fitted baselines, unsafe forward-fill, or decisions derived from an unfinished candle.
7. Analytical thresholds must adapt to the symbol, timeframe, liquidity, volatility, structural regime, and historical distribution. Operational settings may be fixed; structural judgments may not depend on universal rigid cutoffs.
8. Maintain persistent contextual state for every symbol. A new observation updates the existing campaign ledger and does not restart judgment from the latest candle.
9. Separate structural bias, signal importance, readiness, entry safety, confidence, and data reliability. Do not collapse them into one opaque score.
10. Missing, stale, sparse, or contradictory data must emit explicit quality flags and confidence caps. Never convert absent evidence into a neutral zero silently.
11. Every final decision must be deterministic and explainable from timestamped evidence, state transitions, opposing evidence, conflict resolution, freshness, invalidation conditions, and abstention reasons.
12. Implement the full requested production package before running the relevant focused and full test suites. Report exact commands, results, failures, limitations, and any retired behavior.
13. Do not modify the default branch directly. Use an isolated branch and produce a reviewable diff and pull request for repository changes.
