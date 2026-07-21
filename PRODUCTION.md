# Causal Upside Precursor Detector

## Authoritative production path

The reviewable source of truth is the `causal_upside/` package. The following entrypoints use that same decision path:

- `causal_upside_scanner.py` — package command-line interface.
- `run_causal_upside_scanner.py` — editor-first runner.
- `causal_upside_single_file.py` — fully self-contained deployment file generated deterministically by `tools/build_single_file_scanner.py`.

The standalone file does not contain a second classifier. CI rebuilds it from the authoritative package and tests the generated file directly, preventing analytical drift.

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
- Short covering alone is never promoted as a bullish outcome discriminator.
- Live scanning and historical replay use the same detector.
- State transitions are serialized atomically and use failure hysteresis.
- Results are research assessments, not guaranteed returns or automatic trade instructions.

## Run the complete single file from an editor

Open `causal_upside_single_file.py`, edit the `SETTINGS` dictionary near the end of the file, and press **Run** in VS Code, PyCharm, IDLE, or another Python editor.

Important settings:

- `TIMEFRAME`: Binance interval such as `5m`, `15m`, `1h`, or `4h`.
- `CANDLES`: closed historical bars, from 20 through 500.
- `MIN_HISTORY`: minimum usable bars before an assessment is allowed.
- `SCAN_ALL_USDT_PERPETUALS`: scan the full Binance USD-M perpetual universe.
- `SYMBOL_WHITELIST`: explicit symbols when full-universe scanning is disabled.
- `SYMBOL_BLACKLIST`: symbols to omit.
- `RUN_CONTINUOUSLY`: repeat scans in the same process so the campaign ledger remains loaded.
- `SCAN_INTERVAL_SECONDS`: time between cycle starts.
- `TOP_N`: maximum assessments printed and saved.

The console report prints readiness, dominant and alternative hypotheses, failure context, structural bias, signal importance, entry safety, confidence, reliability, campaign age, distance from the footprint, supporting/opposing/missing evidence, next discriminator, invalidation, research status, and quality flags. JSON and CSV are written under `causal_upside_output/`.

## Commands

```bash
# Editor/default settings
python causal_upside_single_file.py

# One cycle with overrides
python causal_upside_single_file.py --once --timeframe 15m --candles 200 --symbol AKEUSDT --symbol TLMUSDT

# Continuous mode
python causal_upside_single_file.py --continuous --interval 180

# Causal blind replay of a repository CSV
python causal_upside_single_file.py --replay AKEUSDT_15m_limit100_20260715_085112_enriched_candles.csv

# Offline safety checks
python causal_upside_single_file.py --self-test
python -m unittest discover -s tests -v
```

To regenerate the standalone deployment artifact after an analytical source change:

```bash
python tools/build_single_file_scanner.py
python tools/build_single_file_scanner.py --check
```
