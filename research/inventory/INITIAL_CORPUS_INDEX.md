# Initial Research Corpus Index

## Source snapshot

- Repository: `alaa35612-hub/Can`
- Imported dataset branch: `ai-skills-python-crypto-v1`
- Import merged through PR #14.
- Original uploaded files remain at repository root during this phase.

## Observed source groups

The corpus contains enriched CSV/JSONL candles across `5m`, `15m`, `1h`, `4h` and `1d`, plus symbol TXT files, Arabic research notes, rule documents and binary DOC files. TXT/DOC sources are prior claims or unknown sources until inspected; they are not labels.

Observed enriched fields include closed-candle status, OHLC, mark and premium, RSI context, Trades, volume/quote volume, taker flow, candle geometry, OI/OI value, Global/Top Account/Top Position L/S, funding and timestamps.

## Priority research cohorts

1. Deep multi-timeframe cases: AKE, BANK, ESPORTS, LYN, MAGMA, TLM, TRADOOR, VELVET and ZBT.
2. Pattern references: OGN cold-start and 1000XEC reset-absorption when complete source is present.
3. Repeated 15m snapshots: BEL, CLO, HMSTR, LAB, SKYAI and TAC.
4. Execution-led narratives: AIOT and related TXT analyses.
5. Negative/control windows sampled from ordinary periods inside the same files.

## Initial treatment

- `*enriched_candles.csv|jsonl`: observed market data after quality audit.
- symbol/general `.txt`: classify semantically before use.
- `.doc`: preserve original and extract to a derivative.
- `.py`: implementation, outside this phase.
- generated reports: experimental evidence only after methodology audit.

## Open limitations

DOC content is not yet semantically extracted; TXT content needs classification; CSV/JSONL twins need equivalence checks; exact coverage, gaps, duplicates and alignment must be computed per file.

## Future machine-readable manifest

`source_path,sha,source_class,symbol,timeframe,collection_time,row_count,first_timestamp,last_timestamp,closed_candle_coverage,field_coverage,duplicate_group,quality_status,analysis_status,linked_campaigns`
