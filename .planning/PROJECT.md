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

**Version:** v1.1 (shipped 2026-03-31)
**Tech Stack:** Python, GenIce2, spglib, numpy, matplotlib, scipy.spatial.cKDTree
**Code:** ~7,151 lines of Python
**Test Coverage:** 200+ tests passing
**Output:** PDB files with CRYST1 records, optional phase diagram visualization
**Phases Supported:** 12 (Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X, XV)
**Performance:** O(n log n) for large structures (KDTree optimization)

## Next Milestone Goals

- ML-based phase prediction
- Confidence scoring for candidates
- Performance optimizations (parallel generation)
- Additional output formats (CIF, GRO)

---

## Current Milestone: v2.0 GUI Application

**Goal:** Transform QuickIce from CLI tool to cross-platform GUI application with interactive phase diagram and 3D structure viewer

**Target features:**
- Interactive phase diagram (click to select T,P)
- Textbox input for options
- Info window with citations for ice phases
- Generate 3D structure button
- Progress bar for generation
- 3D viewer (stick/ball + hydrogen bonds)
- Save/export options (plot, 3D scene, data)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-only interface | Keep it simple, fast to use | ✓ Confirmed — works well |
| PDB output format | Standard, universal compatibility | ✓ Confirmed — universal |
| Ranking approach | Knowledge-based (energy, density, diversity) | ✓ Confirmed — simple and effective |
| Pre-trained model | Minimal resources, no training needed | ✓ Confirmed — vibe-based ranking works |
| Curve-based phase lookup | Avoid polygon overlap errors | ✓ Confirmed — clean boundaries |
| Extended to 12 phases | Comprehensive coverage | ✓ Confirmed — user value |
| KDTree for neighbor search | O(n log n) performance | ✓ Confirmed — 50x faster for large structures |
| Save/restore numpy state | GenIce compatibility | ✓ Confirmed — preserves reproducibility |

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

*Last updated: 2026-03-31 after v1.1 milestone*
