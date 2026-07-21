# Causal Upside Precursor Detector

## Authoritative production path

`causal_upside_scanner.py` and the `causal_upside/` package are the sole production decision path for current scanning and historical blind replay.

The following root scanners are retained only as historical research artifacts and must not be imported or deployed as decision engines:

- `structural_liquidity_scanner_v321_dynamic.py`
- `2_v321_operational_v321o_patch1.py`
- `backtest_v321o_uploaded_cases.py`

They contain duplicate classifiers, fixed score weights, missing-value defaults, or non-persistent decision paths that conflict with the repository's current governance contract.

## Architecture

```text
Binance public endpoints or enriched CSV
→ closed-candle normalization
→ bounded causal as-of alignment
→ data quality and confidence cap
→ historical-only adaptive features
→ structural phase reconstruction
→ competing positive, alternative, failure, and unidentified hypotheses
→ conflict resolution
→ separate bias / importance / readiness / entry safety / confidence / reliability
→ atomic persistent campaign ledger
→ deterministic JSON/CSV output
```

## Guarantees

- Unfinished candles are excluded.
- Feature baselines contain only observations strictly before the active cutoff.
- OI and L/S series use bounded backward alignment; stale values remain missing.
- Missing evidence is explicit and lowers reliability.
- A failed TLM short-covering discriminator is never promoted as a bullish rule.
- The same detector is used for live scan and blind replay.
- State transitions are serialized atomically and use failure hysteresis.
- Results are research assessments, not guaranteed returns or automatic trade instructions.

## Commands

```bash
python causal_upside_scanner.py scan --symbol AKEUSDT --symbol TLMUSDT
python causal_upside_scanner.py replay AKEUSDT_15m_limit100_20260715_085112_enriched_candles.csv
python -m unittest discover -s tests -v
```

The scanner output exposes the dominant hypothesis, alternatives, a failure hypothesis, supporting/opposing/missing evidence, research status, next discriminator, invalidation, freshness, and quality flags.
