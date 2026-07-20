# Structural State Ledger

## Mission
Maintain a persistent causal campaign state for every symbol instead of restarting judgment from the latest candle.

## Reference lifecycle
Latent → Build → Armed → Ignition → Acceptance → Expansion → Exhaustion or Failure → Reset or Rebuild.

## Ledger fields
Campaign birth, first detection, first warning, readiness, execution, price acceptance, expansion and weakness timestamps; direction; current state; supporting and opposing evidence; transition history; persistence strength; contradiction score; campaign age; freshness; temporary pullback versus structural failure.

## Transition rules
- Update previous state; never replace history silently.
- Use hysteresis and independent contrary evidence before reversing direction.
- A single opposing candle cannot terminate a campaign.
- Distinguish a new campaign from continuation, reset and rebuild.
- Persist atomically with schema version and deterministic replay support.