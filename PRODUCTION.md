# Causal Upside Precursor Detector

## Authoritative production path

`causal_upside_scanner.py`, `run_causal_upside_scanner.py`, and the `causal_upside/` package are the sole production decision path for current scanning and historical blind replay.

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
→ deterministic JSON/CSV and explainable console output
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

## Run directly from an editor

Open `run_causal_upside_scanner.py`, edit the `SETTINGS` dictionary at the top, and press **Run**.

Important settings:

- `TIMEFRAME`: Binance interval such as `5m`, `15m`, `1h`, or `4h`.
- `CANDLES`: closed historical bars, from 20 through 500.
- `MIN_HISTORY`: minimum usable bars before an assessment is allowed.
- `SCAN_ALL_USDT_PERPETUALS`: scan the full Binance USD-M perpetual universe.
- `SYMBOL_WHITELIST`: explicit symbols when full-universe scanning is disabled.
- `RUN_CONTINUOUSLY`: repeat scans in the same process so the campaign ledger remains loaded.
- `SCAN_INTERVAL_SECONDS`: time between cycle starts.
- `TOP_N`: maximum assessments printed and saved.

The editor runner prints readiness, dominant and alternative hypotheses, failure context, structural bias, signal importance, entry safety, confidence, reliability, campaign age, distance from the footprint, supporting/opposing/missing evidence, next discriminator, invalidation, research status, and quality flags. It saves the same assessments to `causal_upside_output/latest_assessments.json` and `.csv`.

## Command line

```bash
python run_causal_upside_scanner.py
python causal_upside_scanner.py scan --symbol AKEUSDT --symbol TLMUSDT
python causal_upside_scanner.py replay AKEUSDT_15m_limit100_20260715_085112_enriched_candles.csv
python -m unittest discover -s tests -v
```

The scanner output exposes the dominant hypothesis, alternatives, a failure hypothesis, supporting/opposing/missing evidence, research status, next discriminator, invalidation, freshness, and quality flags.
