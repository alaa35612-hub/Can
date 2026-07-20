# Initial Research Corpus Index

## Source snapshot

- Repository: `alaa35612-hub/Can`
- Imported dataset branch: `ai-skills-python-crypto-v1`
- Import merged through PR #14.
- Original uploaded files remain at repository root during this phase.

## Observed source groups

### Enriched market data

The corpus contains symbol-specific enriched candles in CSV and JSONL with filenames encoding symbol, timeframe, requested limit and collection timestamp. Available timeframes include `5m`, `15m`, `1h`, `4h` and `1d`. Several symbols have repeated snapshots and multi-timeframe coverage, including AKEUSDT, BANKUSDT, ESPORTSUSDT, LYNUSDT, MAGMAUSDT, TLMUSDT, TRADOORUSDT, VELVETUSDT and ZBTUSDT.

### Narrative and prior-analysis files

The root also contains symbol-specific TXT files, Arabic research notes, rule documents, comparative analyses and binary DOC files. These are classified as prior claims or background corpus until their content is reconstructed and audited.

### Known data fields

Observed enriched candle schemas include closed-candle flags; OHLC; mark price; premium index; RSI; number of trades; base and quote volume; taker-buy/taker-sell fields; candle geometry and close location; OI and OI value; Global, Top Account and Top Position L/S ratios; funding; timestamp metadata; and change fields.

## Initial classification rules

| Filename/content shape | Initial class | Research treatment |
|---|---|---|
| `*enriched_candles.csv` | observed market data | primary evidence after quality audit |
| `*enriched_candles.jsonl` | observed market data mirror | reconcile with CSV, do not double count |
| symbol-named `.txt` | unknown until content inspection | raw export or prior analysis; classify semantically |
| Arabic/general `.txt` | prior analysis/background claim | audit, extract hypotheses and provenance |
| `.doc` | binary legacy document | preserve original; conversion required before semantic use |
| `.py` | production/research code | out of scope for this research-only phase |
| generated reports | prior experimental output | evidence only after methodology audit |

## Priority research cohorts

1. **Deep multi-timeframe cases:** AKE, BANK, ESPORTS, LYN, MAGMA, TLM, TRADOOR, VELVET and ZBT.
2. **Known pattern-reference cases:** OGN for cold-start ignition and 1000XEC when its complete source is present for reset-absorption/rebuild.
3. **Repeated 15m snapshots:** BEL, CLO, HMSTR, LAB, SKYAI and TAC for campaign evolution and state-continuity testing.
4. **Execution-led narrative cases:** AIOT and other symbol TXT files, to audit whether prior conclusions were supported or outcome-conditioned.
5. **Negative/control cohort:** must be sampled from ordinary windows inside the same files, not only uploaded top-gainer outcomes.

## Inventory limitations still open

- Binary DOC contents have not yet been semantically extracted.
- TXT files must be classified by content, not extension.
- CSV/JSONL mirrors require checksum and row-level equivalence checks.
- Some requested limits are shorter than their filename suggests because listing age or endpoint availability may constrain rows.
- Exact coverage, gaps, duplicate rows and timestamp alignment must be computed per file before campaign analysis.

## Next inventory output

A machine-readable manifest must eventually contain:

```text
source_path,sha,source_class,symbol,timeframe,collection_time,row_count,
first_timestamp,last_timestamp,closed_candle_coverage,field_coverage,
duplicate_group,quality_status,analysis_status,linked_campaigns
```
