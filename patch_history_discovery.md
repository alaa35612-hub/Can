# Patch History Discovery

## Patch: Discovery Pre-Rally Base Compression
- Reason: Project discovery found repeated pre-rise bases where price structure, top-position retention, and non-chasing account/global L/S appeared before full trigger confirmation.
- Data evidence: `project_discovery_report.md` records median prev-8 base range ~5.1%, median 24-bar OI change positive but with valid flat/down OI cases, and positive median position-account spread.
- Baseline before: `backtest_project_discovery.py` with `2_v321_operational_v321o_patch1.py` early_watch detected 3/16 events (18.75% recall), 5 late detections, 8 too-early/exhausted signals, no reliable precision because all controls are rising symbols.
- Change: Created `2_v321_operational_discovery_pro.py` with a past-only `discovery_pre_rally_candidate` helper and two generic pattern candidates: `Discovery Pre-Rally Base Compression` and `Discovery Delayed-OI Base Watch`.
- Result after: early_watch detected 3/16 events (18.75% recall), unchanged in the capped 220-candle discovery harness. Self-test passed.
- Decision: Accepted as conservative diagnostics/pattern scaffolding because it does not use future data or symbol/time fitting and keeps risk gates, but it did not improve measured recall on this limited harness. It should be evaluated on non-rising controls before raising confidence.

## Rejected adjustment: Lower all early_watch thresholds until every historical rise is flagged
- Reason: Would improve recall superficially.
- Data evidence: Existing first signals are often too early/exhausted and all uploaded controls are rising symbols, so precision would be fake.
- Result before/after: Not applied.
- Decision: Rejected due to overfitting and false precision risk.

## Rejected adjustment: Treat missing Quote Volume as positive confirmation
- Reason: Quote Volume is absent in uploaded data.
- Data evidence: All parsed uploaded candle tables report `quote_volume_available=False`.
- Result before/after: Not applied.
- Decision: Rejected; missing Quote Volume caps confidence only and is not bullish evidence.
