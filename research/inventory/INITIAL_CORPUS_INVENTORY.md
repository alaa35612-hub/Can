# Initial Corpus Inventory

## Scope

First-pass inventory of files merged from `ai-skills-python-crypto-v1` through PR #14. It is based on paths, filename metadata, sampled content and the PR file list; it is not yet a row-level audit of every file.

## Enriched datasets

Observed timeframes: `5m`, `15m`, `1h`, `4h`, `1d`. Observed nominal limits include 10, 20, 50, 100, 170 and 500 rows. Sampled rows include closed-candle status, OHLC, mark/premium, Trades, quote volume, taker flow, OI/OI value, Global/Top Account/Top Position L/S, funding and RSI context.

## Research-rich symbols

AKEUSDT, ARIAUSDT, BANKUSDT, ESPORTSUSDT, LYNUSDT, MAGMAUSDT, TLMUSDT, TRADOORUSDT, VELVETUSDT and ZBTUSDT have multi-timeframe or repeated captures. ACT, BEL, CLO, EPIC, FOGO, GUA, HMSTR, LAB, MANTA, SKYAI and TAC also have repeated or paired evidence.

Shorter focused windows exist for many other symbols and may require adjacent context before supporting durable rules.

## Narrative sources

Symbol TXT files and Arabic research notes may contain raw observations, prior conclusions, admitted misses, fixed-threshold proposals or mixed content. They remain audit targets until observations and interpretations are separated. Binary DOC files require extraction into separate derivatives while preserving originals.

## Known risks

- Top-gainer sample bias.
- Post-hoc thresholds and outcome-conditioned explanations.
- CSV/JSONL twins and overlapping captures.
- Short histories on new symbols or high timeframes.
- Timestamp and field-coverage differences across collector versions.
- Symbol TXT files mixing evidence and narrative.

## First deep research cohort

1. AKEUSDT
2. BANKUSDT
3. ESPORTSUSDT
4. LYNUSDT
5. MAGMAUSDT
6. TLMUSDT
7. VELVETUSDT
8. OGNUSDT as a focused cold-start reference

Every case must include successful, failed and ordinary control windows.

## Required next inventory work

Inspect every TXT; extract DOC derivatives; calculate rows and exact coverage; verify closure and chronology; identify duplicate/overlap groups; map files by symbol/timeframe; associate prior analyses; compute integrity hashes when materialized; populate case-study and control queues.
