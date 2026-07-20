# Data Quality Report

Generated: 2026-07-20 19:48:12 UTC

## Corpus counts

| Measure | Count |
|---|---|
| Repository files audited | 692 |
| Market files parsed | 214 |
| Unique market symbols | 75 |
| CSV/JSONL twin pairs | 48 |
| Exact raw duplicate groups | 71 |
| Prior/background documents | 282 |

## Market quality statuses

| Status | Count |
|---|---|
| HIGH | 207 |
| MEDIUM | 7 |

## Timeframe counts

| Timeframe | Files |
|---|---|
| 15m | 116 |
| 1d | 15 |
| 1h | 18 |
| 4h | 17 |
| 5m | 48 |

## Files requiring attention

| Path | Quality | Rows | Gaps | Duplicates | Unclosed | Twin | Flags |
|---|---|---|---|---|---|---|---|
| CRWDUSDT_15m_limit100_20260702_200158_enriched_candles.csv | MEDIUM | 44 | 2 | 0 | 0 | NOT_APPLICABLE | INTRA_FILE_GAPS_OR_INTERVAL_MISMATCH;NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| HUSDT_15m_limit10_20260629_183223_enriched_candles.csv | MEDIUM | 9 | 0 | 0 | 0 | NOT_APPLICABLE | NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| OGUSDT_5m_limit20_20260705_171313_enriched_candles.csv | MEDIUM | 19 | 0 | 0 | 0 | NOT_APPLICABLE | NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| SNXXUSDT_5m_limit500_20260713_203459_enriched_candles.csv | MEDIUM | 498 | 1 | 0 | 0 | NOT_APPLICABLE | INTRA_FILE_GAPS_OR_INTERVAL_MISMATCH;NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| TACUSDT_5m_limit20_20260709_173836_enriched_candles.csv | MEDIUM | 19 | 0 | 0 | 0 | NOT_APPLICABLE | NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| TAGUSDT_15m_limit500_20260708_180104_enriched_candles.csv | MEDIUM | 498 | 1 | 0 | 0 | NOT_APPLICABLE | INTRA_FILE_GAPS_OR_INTERVAL_MISMATCH;NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |
| USUSDT_5m_limit20_20260706_192710_enriched_candles.csv | MEDIUM | 19 | 0 | 0 | 0 | NOT_APPLICABLE | NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS |

## Interpretation constraints

- `limitN` is nominal; `actual_rows` is authoritative.
- CSV/JSONL twins count as one source only after semantic equivalence passes.
- Missing fields remain unknown rather than neutral evidence.
- Higher-timeframe rows become visible only after their own close time.
- Data quality does not imply market direction.