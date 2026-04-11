# Project Research Summary

**Project:** QuickIce v3.5 Interface Enhancements
**Domain:** Scientific visualization / Computational chemistry (ice structure generation)
**Researched:** 2026-04-12
**Confidence:** HIGH

## Executive Summary

QuickIce v3.5 is an incremental feature release for an existing scientific GUI application (PySide6 + VTK + GenIce2) that generates ice crystal structures and ice-water interfaces. The v3.5 release adds four tightly-scoped features: triclinic-to-orthogonal cell transformation (unlocking Ice II, V, VI for interface generation), CLI interface generation (`--interface` flag), water density calculation from T/P via IAPWS, and Ice Ih IAPWS density replacing a hardcoded value. All four features are additive — no core generation logic changes, no new external dependencies, and the existing MVVM architecture accommodates them through three new service modules.

The recommended approach is to build in dependency order: density service first (lowest risk, foundational), then triclinic transformation (unblocks interface for non-orthogonal phases), then CLI interface integration (builds on existing patterns), and finally integration/polish. The dominant risk is the triclinic→orthogonal coordinate transformation — an incorrect transformation silently produces structurally invalid crystals that may only fail downstream in GROMACS. This must be validated against known ice phases (Ice II, V) before any other feature depends on it. Secondary risks include IAPWS range violations returning `NaN`, performance regression from uncached density lookups, and breaking existing validation checks in `piece.py` that were specifically designed to reject triclinic cells.

## Key Findings

### Recommended Stack

No new dependencies are required. All four v3.5 features use the existing stack. This is a significant finding — it eliminates supply-chain risk, version conflict risk, and environment setup overhead.

**Core technologies (all existing):**
- **numpy 2.4.3**: Triclinic→orthogonal transformation — custom implementation using `linalg.norm`, `arccos`, `dot` products; no external crystallography library needed
- **argparse (stdlib)**: CLI `--interface` extension — matches existing parser pattern in `quickice/cli/parser.py`
- **iapws 1.5.5**: Water and Ice Ih density — `IAPWS97` class for liquid water, `_Ice` class for Ice Ih; already in `environment.yml`
- **spglib 2.7.0**: Confirmed NOT suitable for triclinic→orthogonal conversion (provides Niggli/Delaunay reduction only, not orthogonal cell conversion)

### Expected Features

**Must have (table stakes):**
- Triclinic→orthogonal transformation — currently QuickIce rejects Ice II/V/VI with error; transformation unblocks interface generation for these phases
- CLI interface generation — users expect full CLI parity with GUI; `--interface` flag with mode/thickness/box parameters
- Water density from T/P — interface generation needs correct water molecule spacing; static TIP4P template doesn't account for T/P effects

**Should have (competitive):**
- Ice Ih IAPWS density — replaces hardcoded 0.9167 g/cm³ with temperature-dependent calculation; scientific accuracy improvement, low risk

**Defer (post v3.5):**
- Additional ice phase support beyond GenIce2's current 8
- Automated interface geometry optimization
- GROMACS `gmx solvate` integration

### Architecture Approach

All new features follow the established service layer pattern: new modules in `structure_generation/` called from the existing ViewModel→Worker pipeline. No changes to core generation logic (`generator.py`), the MVVM signal/slot wiring, or the QThread worker architecture.

**Major components (new):**
1. `cell_transformer.py` — Triclinic→orthogonal transformation service; called by `interface_builder.py` when `is_cell_orthogonal()` returns false
2. `density_service.py` — IAPWS density calculations for water and Ice Ih; provides `get_water_density(T,P)`, `get_ice_ih_density(T)`, molecule count calculators
3. `interface_parser.py` — CLI interface argument handling; extends `cli/parser.py` with `--interface` argument group

**Modified components:**
- `interface_builder.py` — Call `transform_triclinic_to_orthogonal()` on triclinic detection instead of raising `InterfaceGenerationError`
- `cli/parser.py` — Add `--interface` argument group with mode/box/thickness sub-arguments
- `main.py` — Route `--interface` flag to interface generation flow
- `modes/piece.py` — Update orthogonal check (lines 61-71) to allow transformed triclinic cells
- `phase_mapping/lookup.py` — Add IAPWS density function alongside hardcoded values

### Critical Pitfalls

1. **Incorrect triclinic coordinate transformation** — Extracting only diagonal elements from the cell matrix produces structurally invalid crystals. Must use full 3×3 matrix transformation with volume verification and PBC wrapping. Validate against known Ice II structure before proceeding. (Recovery cost: HIGH)

2. **Breaking existing `piece.py` validation** — The orthogonal-only check at lines 61-71 was added in v3.0 specifically to block triclinic phases. Adding transformation without updating this check means the new feature silently fails. Must update or remove the validation and add integration tests for triclinic phases.

3. **IAPWS range violations** — `IAPWS97` returns `NaN` or throws exceptions outside its validity range (273.15–647 K, 0.006–22 MPa). Must add bounds checking with graceful fallback to reference density (~1.0 g/cm³) and display a warning.

4. **Performance regression from uncached IAPWS calls** — IAPWS-95 uses an iterative solver; calling it for each of 10+ candidates during ranking causes noticeable slowdown. Must implement `@lru_cache` keyed on `(T, P)` — since all candidates for the same phase share identical density, a single computation suffices.

5. **Density units confusion** — IAPWS returns kg/m³; QuickIce uses g/cm³. Factor-of-1000 error is easy to introduce and hard to catch visually. Add explicit conversion with unit tests.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Density Service Foundation
**Rationale:** Lowest risk, no dependencies on other features, validates IAPWS integration approach. Other features may optionally consume density data later.
**Delivers:** `density_service.py` with `get_water_density()`, `get_ice_ih_density()`, molecule count calculators, bounds checking, LRU cache, unit tests
**Addresses:** Water density from T/P (table stakes), Ice Ih IAPWS density (differentiator)
**Avoids:** Pitfalls 5 (IAPWS range violations), 7 (performance regression), 15 (density units confusion)

### Phase 2: Triclinic Transformation Service
**Rationale:** This is the highest-risk, highest-value feature. It must be built and validated before CLI or integration work depends on it. Isolating it enables thorough testing with known ice phases.
**Delivers:** `cell_transformer.py` with `transform_triclinic_to_orthogonal()`, `extract_lattice_parameters()`, `build_orthogonal_cell()`; integration with `interface_builder.py`; validation against Ice II/V structures
**Addresses:** Triclinic→orthogonal transformation (table stakes)
**Avoids:** Pitfalls 1 (incorrect transformation), 9 (detection failure), 14 (undocumented transformation)
**Uses:** numpy (existing stack)

### Phase 3: CLI Interface Integration
**Rationale:** Builds on existing argparse patterns and the now-available transformation service. Can be developed independently from GUI changes. High user demand for CLI parity.
**Delivers:** `interface_parser.py`, extended `cli/parser.py`, updated `main.py` routing, file naming strategy, CLI help text
**Addresses:** CLI interface generation (table stakes)
**Avoids:** Pitfalls 3 (parser not extended), 4 (file naming conflicts), 10 (missing help text)
**Implements:** CLI extension architecture pattern

### Phase 4: Integration, Polish & Validation
**Rationale:** Bring all features together, fix validation logic in `piece.py`, update GROMACS export for new cases, update GUI density display, end-to-end testing.
**Delivers:** Updated `piece.py` validation, GROMACS export verification, GUI density display updates, integration test suite, documentation
**Addresses:** Cross-cutting concerns
**Avoids:** Pitfalls 2 (breaking piece mode validation), 8 (integration breakage), 11 (GROMACS export), 12 (UI not updated)

### Phase Ordering Rationale

- Phase 1 first because density service is self-contained, low-risk, and establishes the IAPWS integration pattern that other phases may consume
- Phase 2 second because triclinic transformation is the critical-path blocker for non-orthogonal interface generation — it must be validated before any integration work
- Phase 3 third because CLI integration depends on transformation working correctly for triclinic phases, but is otherwise independent
- Phase 4 last because cross-cutting integration, validation updates, and GUI changes touch multiple modules and require all features to be stable

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Triclinic transformation algorithm correctness — the math is standard crystallography but needs validation against known structures. Consider `/gsd-research-phase` to verify the transformation preserves crystallographic symmetry, not just volume.
- **Phase 4:** GROMACS export compatibility — need to verify that transformed orthogonal cells produce valid `.gro` files that GROMACS accepts. May need to research GROMACS box vector format requirements.

Phases with standard patterns (skip research-phase):
- **Phase 1:** IAPWS library usage is well-documented; existing codebase already uses it for seawater phase diagrams
- **Phase 3:** argparse extension is a well-known pattern; existing CLI structure in `parser.py` is straightforward

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies already installed; no new dependencies; verified against `environment.yml` and codebase |
| Features | HIGH | Feature list is scoped from existing codebase gaps (triclinic rejection, missing CLI flag, hardcoded density); clear dependency graph |
| Architecture | HIGH | MVVM patterns verified against existing code; new modules follow established service layer pattern; build order respects dependency graph |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls well-identified from codebase analysis; some algorithm-specific risks (transformation correctness) need validation during implementation |

**Overall confidence:** HIGH

### Gaps to Address

- **Triclinic transformation algorithm validation:** Research shows the approach (extract lattice parameters → build orthogonal cell → transform coordinates) but doesn't verify it against a reference implementation. Need to compare output with ASE's `Cell.orthorhombic_cell()` or a known crystallographic tool during Phase 2 implementation.
- **IAPWS `_Ice` class API:** STACK.md and FEATURES.md disagree on the exact IAPWS API for Ice Ih density (`_Ice` class vs `IAPWS97` with `x=1`). Need to verify which API is correct in the installed `iapws==1.5.5` before implementing density service.
- **Default CLI interface parameters:** No consensus on default box dimensions or thickness values when not specified. Architecture doc flags this as an open question. Decide during Phase 3 planning.
- **Backward compatibility for triclinic transformation:** If transformation produces unexpected results, should users be able to disable it and get the original error? Flag for Phase 4 decision.

## Sources

### Primary (HIGH confidence)
- QuickIce codebase — Verified existing MVVM architecture, service patterns, CLI structure, interface builder, phase lookup
  - `gui/viewmodel.py`, `gui/workers.py` — MVVM patterns
  - `cli/parser.py` — CLI argument structure
  - `structure_generation/interface_builder.py` — Service layer pattern, orthogonal check
  - `structure_generation/generator.py` — Cell parsing, triclinic handling
  - `phase_mapping/lookup.py` — Hardcoded density values
- `environment.yml` — Dependency verification (iapws, spglib, numpy all present)
- IAPWS Python library (`iapws==1.5.5`) — Already installed; API documented on GitHub/PyPI

### Secondary (MEDIUM confidence)
- GenIce2 documentation — Triclinic cell format; cell parsing verified in `generator.py`
- IAPWS R10-06(2009) — Ice Ih equation of state; referenced for density values but implementation details need verification
- spglib documentation — Confirmed NOT providing triclinic→orthogonal conversion

### Tertiary (LOW confidence)
- ASE (Atomic Simulation Environment) — Referenced as alternative for cell transformation; not used but provides validation reference
- OVITO, Avogadro, Pymatgen — Scientific visualization tool patterns for feature landscape context (v2.0 research)

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
