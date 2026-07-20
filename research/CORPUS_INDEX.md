# Research Corpus Index

## 1. Scope

The repository contains a mixed research corpus rather than a single homogeneous dataset. Agents must identify the source class before interpreting any file.

The major classes are:

| Class | Typical files | Proper use | Primary risk |
|---|---|---|---|
| Enriched market data | `*_enriched_candles.csv`, `*_enriched_candles.jsonl` | Reconstruct observable market sequence | Lookahead, timestamp misalignment, missing fields |
| Multi-timeframe symbol sets | Same symbol across `5m`, `15m`, `1h`, `4h`, `1d` | Separate local ignition from higher-timeframe context | Treating frames as independent or perfectly synchronous |
| Historical analysis notes | `.txt`, `.doc` | Generate hypotheses and audit prior reasoning | Treating narrative conclusions as labels |
| Failure/missed-move studies | Notes describing missed rallies, failed ignition, collapse, climax | Extract counterexamples and invalidation evidence | Adding rules after the outcome without blind replay |
| Research skills | `.claude/skills/**/SKILL.md` | Govern reconstruction, hypotheses, replay, validation, synthesis | Loading specialist patterns before governance |
| Skills registry | `BLACK_JOHN_RESEARCH_SKILLS.md` | Mandatory load order and authority model | Skipping the registry |

## 2. Data naming convention

Most enriched data files encode the following metadata in their names:

```text
<SYMBOL>_<TIMEFRAME>_limit<ROWS>_<CAPTURE_TIMESTAMP>_enriched_candles.<csv|jsonl>
```

Example:

```text
AKEUSDT_15m_limit500_20260717_211231_enriched_candles.csv
```

Interpretation:

- symbol: `AKEUSDT`;
- timeframe: `15m`;
- requested row limit: `500`;
- capture timestamp: `2026-07-17 21:12:31` in the filename convention;
- content class: enriched candles.

Do not assume two files with the same symbol and timeframe are duplicates. They may represent different capture windows or revised collectors.

## 3. Observed enriched schema

Representative enriched files contain fields spanning:

- candle identity and closure state;
- open, high, low, close;
- mark-price OHLC and mark/last spread;
- premium-index OHLC;
- RSI context;
- number of trades and changes;
- base and quote volume;
- average size per trade;
- candle body, range, wick, and close location;
- taker-buy and taker-sell base/quote flow;
- taker imbalance and buy/sell ratios;
- open interest and OI value;
- global account long/short ratio;
- top-account long/short ratio;
- top-position long/short ratio;
- cross-ratio spreads;
- funding context.

Before analysis, inspect the actual header because collector versions and available columns may differ.

## 4. Priority symbol groups currently represented

The merged corpus includes extensive or multi-timeframe studies for symbols such as:

- `AKEUSDT`
- `BANKUSDT`
- `ARIAUSDT`
- `ESPORTSUSDT`
- `LYNUSDT`
- `MAGMAUSDT`
- `TLMUSDT`
- `TRADOORUSDT`
- `VELVETUSDT`
- `ZBTUSDT`

It also includes focused or shorter studies for many other symbols, including `OGNUSDT`, `AIOTUSDT`, `TACUSDT`, `LABUSDT`, `SKYAIUSDT`, `HMSTRUSDT`, `FOGOUSDT`, `MANTAUSDT`, `NFPUSDT`, and others.

This list is an index aid, not a ranking and not a complete manifest.

## 5. Source classification protocol

For every file loaded, record:

```yaml
path:
source_class:
symbols:
timeframes:
collector_or_document_version:
first_timestamp:
last_timestamp:
closed_candle_policy:
row_count:
columns_present:
columns_missing:
data_quality_flags:
relationship_to_other_files:
allowed_use:
prohibited_use:
```

### Allowed use by class

**Raw enriched data**

- factual reconstruction;
- adaptive feature computation;
- State Ledger updates;
- blind replay;
- positive, failed, and control comparisons.

**Historical notes**

- hypothesis generation;
- locating candidate intervals;
- identifying prior errors or omissions;
- extracting claims that require validation.

Historical notes must not supply ground-truth labels by themselves.

## 6. Multi-timeframe loading protocol

When multiple timeframes exist for one symbol:

1. establish the exact timestamp coverage of every file;
2. choose one primary execution timeframe, normally `15m` when that is the research target;
3. use `5m` only for microstructure refinement, not to leak post-close information into a `15m` decision;
4. use `1h`, `4h`, and `1d` for regime and campaign context;
5. align only information that was closed and observable at the active cutoff;
6. record disagreements between frames rather than forcing consensus.

## 7. Duplicate and overlap policy

Potential duplicate files must be compared using:

- symbol;
- timeframe;
- first and last timestamp;
- row count;
- collector version;
- column set;
- content hash where available.

Possible outcomes:

- exact duplicate;
- overlapping capture;
- extended capture;
- revised schema;
- corrected collector output;
- separate historical window.

Do not delete or collapse files automatically.

## 8. Historical-note audit protocol

The repository contains prior analyses with useful observations but also outcome-driven rules, fixed thresholds, immediate-entry language, and post-hoc explanations.

Each claim extracted from a note must be transformed into a research record:

```yaml
claim_id:
source_file:
original_claim:
observable_precursors:
claimed_outcome:
implicit_thresholds:
alternative_hypotheses:
positive_cases:
failed_cases:
matched_controls:
blind_replay_result:
current_status:
```

Permitted statuses are defined in `BLACK_JOHN_RESEARCH_SKILLS.md`.

## 9. Required anti-leakage checks

Before accepting a historical detection result, verify:

- the active cutoff preceded the move being predicted;
- only closed candles were used;
- higher-timeframe values were available at the cutoff;
- rolling baselines used only prior observations;
- normalization did not use the full future series;
- candidate selection did not begin from known winners only;
- thresholds were not selected after viewing the outcome;
- failed and control cases were evaluated using the same procedure.

## 10. Research output contract

Every symbol-level research output should expose:

- chronological observed facts;
- current State Ledger and transition history;
- dominant hypothesis;
- alternative hypotheses;
- evidence supporting each hypothesis;
- evidence opposing each hypothesis;
- missing evidence;
- earliest detectable timestamp;
- readiness timestamp, if any;
- ignition and acceptance timestamps, if any;
- invalidation evidence;
- whether the move is new or continuation;
- data reliability;
- rule status and validation scope;
- abstention reason when evidence is insufficient.

## 11. Current repository state

The Black John research skills package has already been merged into `main`. This index is maintained on the dedicated branch `black-john-research-layer-v1` so indexing and research-layer documentation can be reviewed separately from raw corpus ingestion and production code.