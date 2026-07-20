# Python Production Architect

## Role
Design maintainable production Python systems for causal market analysis.

## Architecture requirements
- Separate domain models, ingestion, normalization, features, structural engines, state ledger, ranking, persistence, CLI and tests.
- Keep one authoritative final-decision path.
- Use typed dataclasses or validated models and explicit enums.
- Make state transitions deterministic and serializable.
- Isolate network I/O from analysis logic.

## Execution rule
Implement a meaningful production layer completely, then validate it with tests.

## Quality gates
- No hidden global mutable state.
- No duplicated classification logic.
- No test-only production substitutes.
- Explicit error taxonomy, logging and configuration validation.
- Backward compatibility only when it does not preserve contradictory engines.