# Symbol File Map — Pass 1

This table counts market files imported through PR #14. Counts include CSV and JSONL separately because equivalence has not yet been verified.

| Symbol | 5m | 15m | 1h | 4h | 1d | Total | Research role |
|---|---:|---:|---:|---:|---:|---:|---|
| AKEUSDT | 2 | 6 | 2 | 2 | 2 | 14 | FIRST_DEEP_COHORT |
| VELVETUSDT | 0 | 7 | 2 | 2 | 2 | 13 | HIGH_CONTEXT_PRIORITY |
| ESPORTSUSDT | 3 | 2 | 2 | 2 | 2 | 11 | FIRST_DEEP_COHORT |
| BANKUSDT | 1 | 3 | 2 | 1 | 3 | 10 | FIRST_DEEP_COHORT |
| LYNUSDT | 2 | 4 | 2 | 2 | 0 | 10 | FIRST_DEEP_COHORT |
| MAGMAUSDT | 0 | 4 | 2 | 2 | 2 | 10 | HIGH_CONTEXT_PRIORITY |
| TLMUSDT | 3 | 2 | 1 | 1 | 1 | 8 | HIGH_CONTEXT_PRIORITY |
| TACUSDT | 2 | 5 | 0 | 0 | 0 | 7 | REPEATED_OR_MULTI_TF |
| LABUSDT | 1 | 5 | 0 | 0 | 0 | 6 | REPEATED_OR_MULTI_TF |
| ARIAUSDT | 1 | 1 | 1 | 1 | 1 | 5 | HIGH_CONTEXT_PRIORITY |
| TRADOORUSDT | 1 | 1 | 1 | 1 | 1 | 5 | HIGH_CONTEXT_PRIORITY |
| ZBTUSDT | 1 | 1 | 1 | 1 | 1 | 5 | HIGH_CONTEXT_PRIORITY |
| USUSDT | 4 | 1 | 0 | 0 | 0 | 5 | REPEATED_OR_MULTI_TF |
| ACTUSDT | 2 | 1 | 1 | 0 | 0 | 4 | REPEATED_OR_MULTI_TF |
| BELUSDT | 0 | 4 | 0 | 0 | 0 | 4 | REPEATED_OR_MULTI_TF |
| CLOUSDT | 1 | 3 | 0 | 0 | 0 | 4 | REPEATED_OR_MULTI_TF |
| FOGOUSDT | 0 | 2 | 0 | 2 | 0 | 4 | REPEATED_OR_MULTI_TF |
| HMSTRUSDT | 0 | 4 | 0 | 0 | 0 | 4 | REPEATED_OR_MULTI_TF |
| MANTAUSDT | 2 | 1 | 1 | 0 | 0 | 4 | REPEATED_OR_MULTI_TF |
| EPICUSDT | 0 | 3 | 0 | 0 | 0 | 3 | REPEATED_OR_MULTI_TF |
| GUAUSDT | 0 | 3 | 0 | 0 | 0 | 3 | REPEATED_OR_MULTI_TF |
| MUSDT | 1 | 2 | 0 | 0 | 0 | 3 | REPEATED_OR_MULTI_TF |
| TAGUSDT | 2 | 1 | 0 | 0 | 0 | 3 | REPEATED_OR_MULTI_TF |
| OGNUSDT | 0 | 2 | 0 | 0 | 0 | 2 | FOCUSED_PATTERN_REFERENCE |

## Interpretation rules

- File count is not evidence strength.
- CSV/JSONL pairs must not be treated as two independent observations.
- Multiple captures on the same timeframe may be duplicates, overlaps, extensions or separate windows.
- A symbol with one short window may still be useful as a focused event or control case, but cannot support a durable rule alone.
- The first deep cohort is AKEUSDT, BANKUSDT, ESPORTSUSDT and LYNUSDT because they combine repeated captures, multiple timeframes and prior research relevance.
