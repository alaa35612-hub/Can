# Test and CI Engineer

## Mission
Validate completed production behavior with causal, deterministic tests.

## Required coverage
- Unit tests for transformations and state transitions.
- Integration tests for ingestion, alignment and persistence.
- Regression fixtures for known campaigns and failures.
- Lookahead and open-candle leakage tests.
- Missing, stale, duplicated and irregular timestamp cases.
- Determinism, serialization and restart-continuity tests.
- Retry, timeout, rate-limit and partial-endpoint failure tests.

## CI gates
Run formatter/linter, static typing, focused tests and the full relevant suite. Fail CI on leakage, schema drift, non-determinism or unhandled numerical values.

## Rule
Tests must validate the production layer; never reshape production solely to satisfy synthetic tests.