# QuickIce

## What This Is

A lightweight CLI tool that generates plausible ice structures for water given temperature, pressure, and molecule count. Users specify conditions via flags; the tool outputs 10 ranked PDB file candidates. 

## Core Value

Generate plausible ice structure candidates quickly for a given set of thermodynamic conditions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] CLI interface with flags: temperature, pressure, molecule count
- [ ] Phase diagram mapping (T,P → ice polymorphs)
- [ ] GenIce integration for coordinate generation
- [ ] Output 10 ranked PDB candidates per query
- [ ] Energy/density-based ranking
- [ ] Basic structure validation
- [ ] README noting "pure vibe coding project"
- [ ] Professional documentation (usage, principles, explanation of outcomes)
- [ ] Use only Python libraries in current conda environment

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Visualization
- Python API (CLI only)
- Non-water systems
- Training new ML models

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with a simple condition matching interface
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
| Ranking approach | Research phase will determine best strategy | — Pending |
| Pre-trained model | Minimal resources, no training needed | — Pending |

---
*Last updated: 2026-03-26 after initialization*
