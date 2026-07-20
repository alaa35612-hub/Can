# AKEUSDT Campaign Reconstruction — Causal Pass 1

Primary timeframe is 15m. Higher timeframes are exposed only after close. Baselines use prior rows only through robust median/MAD. JSONL twins are not independent evidence. Pattern names remain hypotheses.

## Sources
- `AKEUSDT_15m_limit100_20260711_113420_enriched_candles.csv`
- `AKEUSDT_15m_limit100_20260715_085112_enriched_candles.csv`
- `AKEUSDT_15m_limit500_20260707_181139_enriched_candles.csv`
- `AKEUSDT_15m_limit500_20260717_211231_enriched_candles.csv`
- `AKEUSDT_1d_limit500_20260717_212121_enriched_candles.csv`
- `AKEUSDT_1h_limit500_20260717_211343_enriched_candles.csv`
- `AKEUSDT_4h_limit500_20260717_211446_enriched_candles.csv`
- `AKEUSDT_5m_limit500_20260717_211054_enriched_candles.csv`

## Frozen State Ledger transitions

| Cutoff | From | To | Facts | Dominant hypothesis |
|---|---|---|---|---|
| 2026-07-02T13:30:00+00:00 | LATENT | EARLY_BUILD | oi_expansion, higher_timeframe_support | Quiet build |
| 2026-07-02T21:30:00+00:00 | EARLY_BUILD | IGNITION_CANDIDATE | execution_shock, higher_timeframe_opposition | Execution-led ignition |
| 2026-07-02T21:45:00+00:00 | IGNITION_CANDIDATE | ACCEPTED_IGNITION | higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-03T02:30:00+00:00 | ACCEPTED_IGNITION | EXPANSION | execution_shock, oi_expansion, positive_price_release, higher_timeframe_support | Accepted expansion/continuation |
| 2026-07-03T02:45:00+00:00 | EXPANSION | CONTINUATION_RELOAD | execution_shock, oi_expansion, higher_timeframe_support | Accepted expansion/continuation |
| 2026-07-07T08:00:00+00:00 | CONTINUATION_RELOAD | FAILURE | execution_shock, negative_price_dislocation, higher_timeframe_opposition | Failed/exhausted campaign |
| 2026-07-07T09:00:00+00:00 | FAILURE | EARLY_BUILD | execution_shock, oi_expansion, negative_price_dislocation, higher_timeframe_opposition | Quiet build |
| 2026-07-07T09:15:00+00:00 | EARLY_BUILD | IGNITION_CANDIDATE | execution_shock, oi_expansion, positive_price_release, higher_timeframe_opposition | Execution-led ignition |
| 2026-07-07T09:30:00+00:00 | IGNITION_CANDIDATE | ACCEPTED_IGNITION | execution_shock, oi_expansion, higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-07T10:00:00+00:00 | ACCEPTED_IGNITION | EXPANSION | execution_shock, oi_expansion, positive_price_release, higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-07T10:15:00+00:00 | EXPANSION | CONTINUATION_RELOAD | execution_shock, oi_expansion, negative_price_dislocation, higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-10T10:45:00+00:00 | UNOBSERVED_GAP | RESET | data_gap_campaign_boundary | New campaign must be reconstructed independently |
| 2026-07-10T11:00:00+00:00 | LATENT | EARLY_BUILD | oi_expansion, higher_timeframe_support | Quiet build |
| 2026-07-10T11:15:00+00:00 | EARLY_BUILD | CONFIRMED_BUILD | oi_expansion, higher_timeframe_support | Quiet build |
| 2026-07-10T13:45:00+00:00 | CONFIRMED_BUILD | IGNITION_CANDIDATE | execution_shock, oi_expansion, positive_price_release, higher_timeframe_support | Execution-led ignition |
| 2026-07-10T14:00:00+00:00 | IGNITION_CANDIDATE | ACCEPTED_IGNITION | execution_expansion, oi_expansion, negative_price_dislocation, higher_timeframe_support | Accepted expansion/continuation |
| 2026-07-10T18:00:00+00:00 | ACCEPTED_IGNITION | EXPANSION | oi_expansion, higher_timeframe_support | Accepted expansion/continuation |
| 2026-07-11T00:00:00+00:00 | EXPANSION | CONTINUATION_RELOAD | execution_expansion, positive_price_release, higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-12T16:15:00+00:00 | UNOBSERVED_GAP | RESET | data_gap_campaign_boundary | New campaign must be reconstructed independently |
| 2026-07-12T16:30:00+00:00 | LATENT | EARLY_BUILD | oi_expansion, higher_timeframe_opposition | Quiet build |
| 2026-07-12T20:00:00+00:00 | EARLY_BUILD | CONFIRMED_BUILD | oi_expansion, higher_timeframe_support | Quiet build |
| 2026-07-14T03:45:00+00:00 | CONFIRMED_BUILD | IGNITION_CANDIDATE | execution_shock, positive_price_release, higher_timeframe_support | Execution-led ignition |
| 2026-07-14T04:00:00+00:00 | IGNITION_CANDIDATE | ACCEPTED_IGNITION | execution_shock, higher_timeframe_support | Accepted expansion/continuation |
| 2026-07-14T05:00:00+00:00 | ACCEPTED_IGNITION | EXPANSION | higher_timeframe_opposition | Accepted expansion/continuation |
| 2026-07-14T16:15:00+00:00 | EXPANSION | CONTINUATION_RELOAD | execution_expansion, negative_price_dislocation, higher_timeframe_support | Accepted expansion/continuation |

## Controls and limitations

- 5 ordinary same-asset windows were selected outside transition neighborhoods.
- The documented gap between old and new 15m captures remains explicit.
- Daily history is short and cannot provide mature long-horizon baselines.
- Materially conflicting overlapping rows: 99.
- No rule is promoted to durable status in this pass.
