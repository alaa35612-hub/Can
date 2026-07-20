# File Classification Rules

Classify by content and provenance, not extension or filename alone.

## Classes

### OBSERVED_MARKET_DATA

Typical evidence:

- enriched-candle CSV or JSONL rows;
- timestamped OHLCV, mark, premium, trades, quote volume, taker flow, OI, L/S, funding and RSI fields;
- closed-candle indicators and producer version.

These files receive the highest evidentiary role after quality checks.

### RAW_MONITOR_EXPORT

Timestamped ranked lists or monitor snapshots rather than complete candles. Useful as batch context, but absence from a later list is not failure.

### PRIOR_ANALYSIS

Narrative conclusions, rankings, explanations, coin reports or agent outputs. These are audit targets, not labels.

### RULE_OR_HYPOTHESIS_NOTE

Documents proposing rules, pattern names, thresholds, exceptions or theoretical interpretations. Preserve claims and numeric provenance, then translate them into adaptive research questions.

### MIXED_SOURCE

A file combining raw observations, copied monitor output and interpretation. Separate quoted observations from author conclusions during extraction.

### BINARY_LEGACY_DOCUMENT

`.doc` or other binary documents that require safe text extraction. Do not infer semantic content from filename alone.

### IMPLEMENTATION

Python source, configuration or runtime logic. Outside the research-only phase unless explicitly requested.

### GENERATED_ARTIFACT

Backtest reports, summaries, CSV/JSON outputs and diagnostics. Record producing version and whether the artifact is reproducible.

### UNKNOWN_REQUIRES_REVIEW

Use when content has not been inspected or cannot be parsed reliably.

## Filename hints

`<SYMBOL>_<timeframe>_limit<rows>_<timestamp>_enriched_candles.csv|jsonl` is a strong hint for observed market data, but content still controls classification.

Symbol-named `.txt` files may be raw exports, prior analysis or mixed sources. Arabic-titled files commonly indicate analyses or rule notes, but must remain `UNKNOWN_REQUIRES_REVIEW` until inspected.

## Manifest fields

- source path;
- immutable source name;
- content class;
- symbol or symbols;
- timeframe;
- nominal row limit;
- capture timestamp from filename;
- actual first/last timestamp;
- actual row count;
- available field groups;
- closed-candle coverage;
- duplicate/gap/alignment flags;
- related source paths;
- prior-analysis status;
- extraction status;
- integrity hash when materialized;
- research notes.

## Integrity rules

- Do not move or rename original evidence before a complete manifest exists.
- Never overwrite extracted text onto the binary original.
- Preserve CSV and JSONL twins as separate provenance until equality is verified.
- Preserve repeated captures because they may extend context or reveal revisions.
- Do not deduplicate based only on filename similarity.
