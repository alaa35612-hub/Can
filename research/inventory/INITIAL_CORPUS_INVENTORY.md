# Initial Corpus Inventory

## Scope

This inventory covers the market and narrative files merged from branch `ai-skills-python-crypto-v1` through PR #14. It is a repository-level first pass based on file paths, filename metadata, sampled content and the PR file list. It is not yet a row-level semantic audit of every file.

## Observed source groups

### Enriched market datasets

The corpus contains many symbol-level `CSV` and `JSONL` enriched-candle files with filename metadata for symbol, timeframe, nominal row limit and capture time.

Observed timeframes include:

- `5m`
- `15m`
- `1h`
- `4h`
- `1d`

Observed row limits include small event windows and broader histories such as 10, 20, 50, 100, 170 and 500 rows.

Sampled enriched files contain closed-candle status, OHLC, mark price, premium index, Trades, volume, quote volume, average trade size, taker flow, OI, OI value, Global/Top Account/Top Position L/S, funding and RSI context.

### Multi-timeframe research-rich symbols

The following symbols have multiple timeframes or repeated captures and should be prioritized for complete campaign reconstruction:

- `AKEUSDT`
- `ARIAUSDT`
- `BANKUSDT`
- `ESPORTSUSDT`
- `LYNUSDT`
- `MAGMAUSDT`
- `TLMUSDT`
- `TRADOORUSDT`
- `VELVETUSDT`
- `ZBTUSDT`

Additional symbols with repeated or paired CSV/JSONL evidence include ACT, BEL, CLO, EPIC, FOGO, GUA, HMSTR, LAB, MANTA, SKYAI and TAC.

### Focused event-window symbols

The repository also contains shorter 5m/15m windows for many symbols, including 1MBABYDOGE, ACE, AGLD, ALLO, ARPA, BIRB, BREV, CELO, COOKIE, DODOX, EDGE, EVAA, GWEI, HEI, HOT, KORU, MAVIA, NFP, NOM, OGN, PIPPIN, POWER, PUNDIX, RAVE, RPL, RVN, SAFE, SENT, SIREN, SKL, SLP, SNX, SXT, SYN, TAG, TAIKO, TUT, UAI, US, VANRY, XPIN, YFI and ZKP.

These are useful for focused event reconstruction but may require adjacent context before supporting durable rules.

### Symbol-named TXT sources

Examples include:

- `AIOTUSDT.txt`
- `AIOTUSDT١.txt`
- `BOBUSDT.txt`
- `JOEUSDT.txt`
- `KOMAUSDT.txt`
- `MAGMAUSDT.txt`
- `MAGMAUSDT TOWNSUSDT.txt`
- `MMTUSDT.txt`
- `OLUSDT.txt`
- `TRUSTUSDT.txt`

These must be classified by content. Sampled PR content shows at least some contain prior conclusions, admitted misses, fixed-threshold proposals and rule-generation narratives rather than raw observations. They are therefore audit targets until separated into observations and interpretations.

### Arabic-titled research notes

The corpus includes files concerning:

- reasons for coin rises;
- deep analyses;
- short cases;
- complete cases;
- divergence;
- momentum continuation/exemption;
- failure warnings;
- why some rallies continued while others collapsed;
- proposed rules and theoretical explanations;
- data requirements and broad 500-row analyses.

Filename semantics are insufficient. Each file remains `UNKNOWN_REQUIRES_REVIEW` or `PRIOR_ANALYSIS/RULE_OR_HYPOTHESIS_NOTE` only after content inspection.

### Binary legacy documents

Observed `.doc` files include symbol/case documents and general data notes. Their contents have not been fully parsed in this phase. They require extraction into separate text/Markdown derivatives while preserving the originals.

## Known research risks

- Top Gainers and ranked-list sample bias.
- Previous analyses that propose hard thresholds after observing a missed rally.
- Outcome-conditioned explanations.
- CSV/JSONL twins that may be duplicates or serialization variants.
- Repeated captures that overlap but may differ in source coverage.
- Files with nominal 500-row names but shorter actual histories on newer symbols or higher timeframes.
- Binary documents not yet semantically indexed.
- Symbol-named TXT files mixing observations and conclusions.
- Potential timestamp and field-coverage differences across producer versions.

## First research cohort

The first deep research cohort should use symbols with the richest multi-timeframe and prior-analysis evidence:

1. AKEUSDT
2. BANKUSDT
3. ESPORTSUSDT
4. LYNUSDT
5. MAGMAUSDT
6. TLMUSDT
7. VELVETUSDT
8. OGNUSDT as a focused cold-start reference

For each, include successful, failed and ordinary control windows. Do not treat the cohort as representative of the entire market.

## Required next inventory work

- inspect every TXT file and assign a content class;
- extract every DOC into a separate derivative and record extraction quality;
- calculate actual rows, first/last timestamps and field coverage for each market file;
- verify candle closure and chronological order;
- identify duplicate and overlapping captures;
- map all files by symbol and timeframe;
- identify prior analyses associated with each symbol;
- create integrity hashes after files are materialized for programmatic inventory;
- populate case-study queues and matched controls.
