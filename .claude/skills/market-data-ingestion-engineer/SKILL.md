# Market Data Ingestion Engineer

## Mission
Build reliable public-data ingestion for Binance Futures and equivalent exchanges.

## Responsibilities
- Fetch exchange info, closed klines, OI history, global/top account/top position L/S, funding and premium context.
- Enforce symbol, contract type, timeframe and timestamp semantics.
- Align series causally with bounded as-of joins; never fabricate missing OI or ratios as zero.
- Track freshness, coverage, gaps, duplicates and source latency.
- Add bounded concurrency, retry with jitter, backoff, caching and rate-limit awareness.
- Preserve raw payload provenance and normalized schema versions.

## Failure policy
Partial data lowers reliability and emits flags. It must not silently become valid neutral evidence.

## Acceptance
All rows are ordered, deduplicated, closed, unit-consistent and reproducible from recorded metadata.