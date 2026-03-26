# QuickIce

## What This Is

A lightweight CLI tool that generates plausible ice structures for water given temperature, pressure, and molecule count. Users specify conditions via flags; the tool outputs 10 ranked PDB file candidates. Pure ML-based approach — no physics simulations.

## Core Value

Generate plausible ice structure candidates quickly for a given set of thermodynamic conditions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] CLI interface with flags: temperature, pressure, molecule count
- [ ] ML-based structure generation (no physics)
- [ ] Output 10 ranked PDB candidates per query
- [ ] Ranking approach: research and determine optimal strategy
- [ ] GenIce integration for coordinate generation and validation

### Out of Scope

- Physics-based simulations
- Structure analysis tools
- Visualization
- Python API (CLI only)
- Non-water systems

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with ML-guided condition matching
- Initial prompt notes: "pure vibe coding project"

## Constraints

- **Runtime**: Minimal resource usage — lightweight model
- **Output**: PDB format only
- **Dependencies**: Only Python libraries in current conda environment
- **Scope**: Water ice only, generation only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-only interface | Keep it simple, fast to use | — Pending |
| PDB output format | Standard, universal compatibility | — Pending |
| ML ranking approach | Research phase will determine best strategy | — Pending |
| Pre-trained model | Minimal resources, no training needed | — Pending |

---
*Last updated: 2026-03-26 after initialization*
