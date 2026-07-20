# File Classification Rules

Classify by content and provenance, not extension or filename alone.

## Classes

### OBSERVED_MARKET_DATA
Timestamped enriched-candle CSV or JSONL data. Highest evidentiary role after quality checks.

### RAW_MONITOR_EXPORT
Ranked monitor snapshots. Useful as batch context; absence from a later list is not failure.

### PRIOR_ANALYSIS
Narrative conclusions, rankings or reports. Audit targets, not labels.

### RULE_OR_HYPOTHESIS_NOTE
Documents proposing rules, pattern names, thresholds or interpretations. Preserve provenance, then translate claims into adaptive research questions.

### MIXED_SOURCE
Files combining raw observations and interpretation. Separate quoted facts from conclusions.

### BINARY_LEGACY_DOCUMENT
Binary `.doc` files requiring safe extraction. Do not infer semantic content from filename alone.

### IMPLEMENTATION
Python source or runtime logic. Outside the research-only phase unless explicitly requested.

### GENERATED_ARTIFACT
Backtest reports and diagnostics. Record producer version and reproducibility.

### UNKNOWN_REQUIRES_REVIEW
Use when content has not been inspected or cannot be parsed reliably.

## Filename hints

`<SYMBOL>_<timeframe>_limit<rows>_<timestamp>_enriched_candles.csv|jsonl` strongly suggests observed data, but content controls classification.

Symbol-named and Arabic-titled TXT files must remain unverified until inspected.

## Manifest fields

- source path and immutable name;
- content class;
- symbol(s), timeframe and capture time;
- actual row count and first/last timestamp;
- field and closed-candle coverage;
- duplicate, gap and alignment flags;
- related files and extraction status;
- integrity hash when materialized;
- research notes.

## Integrity rules

- Do not move or rename evidence before a complete manifest exists.
- Never overwrite extracted text onto a binary original.
- Preserve CSV/JSONL twins until equality is verified.
- Preserve repeated captures; do not deduplicate by filename similarity alone.
