# Master File Manifest — Pass 1

## Scope

This manifest pass covers the complete 255-file import merged through PR #14. It is based on the authoritative PR file list plus direct content inspection of the first AKEUSDT cohort. It does not infer semantic truth from filenames and does not delete, move, collapse or relabel original evidence.

## Corpus baseline

| Measure | Count |
|---|---:|
| Total imported files | 255 |
| Enriched market files | 216 |
| CSV market files | 172 |
| JSONL market files | 44 |
| Narrative TXT files | 36 |
| Binary DOC files | 3 |
| Unique symbols represented by market files | 77 |
| Available timeframes | 5m, 15m, 1h, 4h, 1d |

## Classification policy

- `*_enriched_candles.csv` and `*.jsonl` are initially classified as `OBSERVED_MARKET_DATA_PENDING_QUALITY_AUDIT`.
- TXT files remain `UNKNOWN_REQUIRES_CONTENT_REVIEW` until observations and interpretation are separated.
- DOC files remain `BINARY_LEGACY_DOCUMENT_PENDING_EXTRACTION`.
- CSV/JSONL twins are not double-counted during analysis until row-level equivalence is verified.
- Repeated captures are retained because they may be extensions, overlapping captures, corrected outputs or distinct historical windows.
- Filename `limitN` is a requested limit, not proof of actual row count.

## First-pass file groups

### First deep cohort

- AKEUSDT — 14 market files across 5m, 15m, 1h, 4h and 1d.
- BANKUSDT — 10 market files across 5m, 15m, 1h, 4h and 1d.
- ESPORTSUSDT — 11 market files across 5m, 15m, 1h, 4h and 1d.
- LYNUSDT — 10 market files across 5m, 15m, 1h and 4h.

### High-context priority

ARIAUSDT, MAGMAUSDT, OGNUSDT, TLMUSDT, TRADOORUSDT, VELVETUSDT and ZBTUSDT.

### Repeated-capture or multi-timeframe groups

ACT, BEL, CLO, EPIC, FOGO, GUA, HMSTR, LAB, MANTA, MUS, SKYAI, TAC, TAG and US.

## Fields observed in enriched market files

Direct inspection confirms a full enriched schema containing:

- producer version and candle timestamps;
- closed-candle flag;
- OHLC and mark-price OHLC;
- premium index;
- RSI context;
- trades, volume and quote volume;
- average base and quote value per trade;
- candle geometry and close location;
- taker buy/sell base and quote flow;
- OI contracts and OI value;
- Top Account, Top Position and Global L/S ratios;
- cross-ratio spreads;
- funding context.

## AKEUSDT content audit status

| File | Actual rows | First observed candle | Last observed candle | Closed endpoints | Status |
|---|---:|---|---|---|---|
| `AKEUSDT_15m_limit100_20260711_113420_enriched_candles.csv` | 99 | 2026-07-10 10:45 UTC | 2026-07-11 11:15 UTC | True | pass-1 endpoints valid |
| `AKEUSDT_15m_limit500_20260717_211231_enriched_candles.csv` | 499 | 2026-07-12 16:15 UTC | 2026-07-17 20:45 UTC | True | pass-1 endpoints valid |
| `AKEUSDT_5m_limit500_20260717_211054_enriched_candles.csv` | 499 | 2026-07-16 03:35 UTC | 2026-07-17 21:05 UTC | True | pass-1 endpoints valid |
| `AKEUSDT_1h_limit500_20260717_211343_enriched_candles.csv` | 499 | 2026-06-27 02:00 UTC | 2026-07-17 20:00 UTC | True | pass-1 endpoints valid |
| `AKEUSDT_4h_limit500_20260717_211446_enriched_candles.csv` | 179 | 2026-06-18 00:00 UTC | 2026-07-17 16:00 UTC | True | shorter history than nominal limit |
| `AKEUSDT_1d_limit500_20260717_212121_enriched_candles.csv` | 29 | 2026-06-18 00:00 UTC | 2026-07-16 00:00 UTC | True | listing-age constrained |

## Initial quality findings

1. `limit500` does not guarantee 500 data rows; the higher-timeframe AKE files contain 179 and 29 rows.
2. The old 15m AKE window ends on 11 July, while the newer 15m capture begins on 12 July. It is a separate adjacent historical window, not an automatic duplicate.
3. Timeframe endpoints differ. The 5m file extends beyond the 15m file, while 1h/4h/1d end earlier. Multi-timeframe joins must use only values closed at each active cutoff.
4. Directly inspected AKE endpoint rows are closed candles.
5. CSV/JSONL twins still require row-level equality checks before one is treated as a mirror.
6. Narrative files cannot be used as labels until content review and prior-analysis auditing are completed.

## Remaining pass-2 work

- inspect every market file for actual row count, coverage, closure, chronology and schema;
- calculate exact duplicate, overlap and extension groups;
- verify CSV/JSONL equivalence;
- inspect every TXT file semantically;
- extract DOC files into separate derivatives without modifying originals;
- produce the final machine-readable `MASTER_FILE_MANIFEST.csv`;
- link prior analyses to symbols, campaigns and source data;
- select matched ordinary control windows.
