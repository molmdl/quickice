# QuickIce

## What This Is

A cross-platform GUI application for generating plausible ice structures. Users select thermodynamic conditions via interactive phase diagram or text input, and receive ranked PDB structure candidates with 3D visualization.

## Core Value

Generate plausible ice structure candidates quickly with an intuitive visual interface.

## Requirements

### Validated

**v1.0-v1.1 (CLI Tool):**
- ✓ CLI interface with flags: temperature, pressure, molecule count — v1.0
- ✓ Phase diagram mapping (T,P → ice polymorphs) — v1.0 (12 phases)
- ✓ GenIce integration for coordinate generation — v1.0
- ✓ Output 10 ranked PDB candidates per query — v1.0
- ✓ Energy/density-based ranking — v1.0
- ✓ Basic structure validation (spglib) — v1.0
- ✓ README noting "pure vibe coding project" — v1.0
- ✓ Professional documentation (usage, principles, explanation of outcomes) — v1.0
- ✓ Use only Python libraries in current conda environment — v1.0

**v2.0 (GUI Application):**
- ✓ Interactive 12-phase ice diagram with click-to-select — v2.0
- ✓ Textbox input with validation (T: 0-500K, P: 0-10000 bar, N: 4-216) — v2.0
- ✓ VTK-based 3D molecular viewer (ball-and-stick, stick, VDW) — v2.0
- ✓ Hydrogen bond visualization as dashed lines — v2.0
- ✓ Dual viewport for candidate comparison — v2.0
- ✓ Unit cell boundary box toggle — v2.0
- ✓ Auto-rotation and zoom-to-fit — v2.0
- ✓ Export: PDB, PNG, SVG — v2.0
- ✓ Phase info with citations (DOI references) — v2.0
- ✓ Help tooltips and in-app quick reference — v2.0
- ✓ Standalone Linux executable distribution — v2.0
- ✓ License compliance audit (MIT-compatible) — v2.0
- ✓ Exact version pinning for all dependencies — v2.0

### Active

(None — v2.0 shipped. Plan next milestone with `/gsd-new-milestone`)

### Out of Scope

- Physics-based ranking/simulation (GenIce for generation only)
- Structure analysis tools
- Python API (CLI + GUI only)
- Non-water systems
- Training new ML models
- Web-based viewer
- Real-time preview while typing
- Cloud sync/collaboration

## Current State

**Version:** v2.0 (shipped 2026-04-04)
**Tech Stack:** Python 3.11, PySide6 6.10.2, VTK 9.5.2, GenIce2, spglib, numpy, matplotlib
**Code:** 10,992 lines of Python
**Test Coverage:** 200+ tests passing
**Output:** PDB files with CRYST1 records, PNG/SVG exports, 3D viewport captures
**Phases Supported:** 12 (Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, X, XV)
**Distribution:** Standalone executable (quickice-v2.0.0-linux-x86_64.tar.gz, 299 MB)

## Next Milestone Goals

(None defined — use `/gsd-new-milestone` to define v2.1 or v3.0 goals)

---

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
| MVVM architecture for GUI | Separation of concerns, testability | ✓ Confirmed — clean signal/slot wiring |
| VTK for 3D viewer | Industry standard, MIT-compatible | ✓ Confirmed — full 3D interactivity |
| PyInstaller bundling | Standalone distribution | ✓ Confirmed — Linux executable complete |
| Exact version pinning | Reproducibility, security | ✓ Confirmed — all deps =x.y.z |

## Context

- GenIce codebase mapped: `./planning/codebase/` contains architecture docs
- GenIce provides ice generation pipeline and PDB output capability
- This project wraps/extends GenIce with a simple condition matching interface
- Initial prompt notes: "pure vibe coding project"
- v2.0 adds PySide6 GUI with interactive phase diagram and VTK 3D viewer

## Constraints

- **Runtime**: Minimal resource usage — lightweight model
- **Output**: PDB format only (plus image exports)
- **Dependencies**: Only Python libraries in current conda environment
- **Scope**: Water ice only, generation only
- **Installation**: Do NOT auto-install dependencies. Add to env.yml, seek approval, wait for user to install.

---

*Last updated: 2026-04-04 after v2.0 milestone*
