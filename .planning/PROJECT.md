# QuickIce

## What This Is

A lightweight CLI tool that generates plausible ice structures for water given temperature, pressure, and molecule count. Users specify conditions via flags; the tool outputs 10 ranked PDB file candidates.

## Core Value

Generate plausible ice structure candidates quickly for a given set of thermodynamic conditions.

## Requirements

### Validated

- ✓ CLI interface with flags: temperature, pressure, molecule count — v1.0
- ✓ Phase diagram mapping (T,P → ice polymorphs) — v1.0 (12 phases)
- ✓ GenIce integration for coordinate generation — v1.0
- ✓ Output 10 ranked PDB candidates per query — v1.0
- ✓ Energy/density-based ranking — v1.0
- ✓ Basic structure validation (spglib) — v1.0
- ✓ README noting "pure vibe coding project" — v1.0
- ✓ Professional documentation (usage, principles, explanation of outcomes) — v1.0
- ✓ Use only Python libraries in current conda environment — v1.0

### Active

(v1.0 shipped — new requirements coming in next milestone)

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Visualization
- Python API (CLI only)
- Non-water systems
- Training new ML models

## Current State

**Version:** v1.0 (shipped 2026-03-29)
**Tech Stack:** Python, GenIce2, spglib, numpy, matplotlib
**Code:** ~3,800 lines of Python
**Test Coverage:** 200+ tests passing
**Output:** PDB files with CRYST1 records, optional phase diagram visualization
**Phases Supported:** 12 (Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X, XV)

## Next Milestone Goals

- ML-based phase prediction
- Confidence scoring for candidates
- Performance optimizations (parallel generation)
- Additional output formats (CIF, GRO)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-only interface | Keep it simple, fast to use | ✓ Confirmed — works well |
| PDB output format | Standard, universal compatibility | ✓ Confirmed — universal |
| Ranking approach | Knowledge-based (energy, density, diversity) | ✓ Confirmed — simple and effective |
| Pre-trained model | Minimal resources, no training needed | ✓ Confirmed — vibe-based ranking works |
| Curve-based phase lookup | Avoid polygon overlap errors | ✓ Confirmed — clean boundaries |
| Extended to 12 phases | Comprehensive coverage | ✓ Confirmed — user value |

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

---

*Last updated: 2026-03-29 after v1.0 milestone*
