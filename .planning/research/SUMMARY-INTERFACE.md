# Project Research Summary: Ice-Water Interface Generation

**Project:** QuickIce v3.0 — Ice-Water Interface Generation  
**Domain:** Computational Chemistry / Molecular Simulation Structure Generation  
**Researched:** 2026-04-08  
**Confidence:** HIGH

---

## Executive Summary

Ice-water interface generation for QuickIce requires **building custom functionality on top of existing GenIce2 capabilities**—GenIce2 generates only pure ice structures, so interface assembly must be implemented as a new layer. The approach uses existing stack components (NumPy/SciPy for spatial operations, GenIce2 for ice generation, existing GROMACS export) without adding new external dependencies.

The recommended approach is a **Pure Python implementation** following the exact same MVVM architecture pattern used for existing ice generation: InterfaceGenerationWorker runs in QThread, MainViewModel manages lifecycle, and new service-layer components (InterfaceGenerator, LiquidGenerator) handle the business logic. Three geometry modes are specified: slab (layer stacking), ice-in-water (embedded crystal), and water-in-ice (cavity/carving).

Key risks center on **atom overlap at ice-water boundaries**—collision detection is essential, not optional. Secondary risks include hydrogen bond network discontinuity at interfaces, density mismatches (~8% between ice and liquid), and user confusion with new scientific parameters. These are addressable through validation checks, sensible defaults, and comprehensive tooltips.

---

## Key Findings

### Recommended Stack

**No new dependencies required.** The implementation uses:
- **NumPy** — Coordinate manipulation for ice + liquid assembly (existing)
- **SciPy** — Spatial operations (KD-tree for collision detection, convex hull for cavity detection) (existing)
- **GenIce2** — Ice structure generation (existing, confirmed ice-only)
- **VTK** — Rendering with phase-based coloring enhancement (existing)
- **Existing GROMACS writers** — Export combined structures (existing)

The only optional addition would be MDAnalysis if complexity warrants, but starting without it is strongly recommended—NumPy/SciPy are sufficient.

### Expected Features

**Must have (table stakes):**
- Mode selector (slab/ice-in-water/water-in-ice) — core milestone requirement
- Box size input (nm) — replaces molecule-count-based sizing
- Ice thickness + water thickness inputs (nm) — controls layer sizes in slab mode
- Seed input — reproducibility for random elements
- Phase selector (Ih, Ic, II-VI) — which ice polymorph for solid phase
- Interface assembly for all three modes — slab stacking, particle embedding, cavity filling
- Phase-differentiated visualization — ice vs. liquid coloring
- PDB and GROMACS export — standard structure output

**Should have (competitive):**
- Ice crystal size control (ice-in-water mode) — embedding crystal dimensions
- Cavity size control (water-in-ice mode) — water pocket dimensions
- Interface orientation control — crystallographic face selection
- Interface boundary visualization — plane indicator at transition
- Quick presets — common configurations (Ih-slab-3nm, Ic-in-water)

**Defer (v2+):**
- Automatic density matching — smooth transition regions
- Multiple interface types beyond three modes — complex geometries
- Guest molecule inclusion — advanced use cases

### Architecture Approach

**Identical MVVM pattern to existing ice generation.** New components integrate in parallel without modifying existing code paths:

1. **InterfaceGenerationWorker** — QThread worker with same signal pattern as GenerationWorker
2. **MainViewModel** — Extended with interface_* signals/methods (not a new ViewModel)
3. **InterfaceGenerator** — Service that composes IceStructureGenerator + LiquidGenerator
4. **LiquidGenerator** — Sub-module generating random water positions at correct density
5. **MolecularViewerWidget** — Extended with phase-based coloring (single viewer, not separate)

**Data flow mirrors existing generation:**
```
User Input → MainViewModel.start_interface_generation() → InterfaceGenerationWorker.run()
→ InterfaceGenerator.generate() → InterfaceCandidate → Export
```

### Critical Pitfalls

1. **Atom overlap at ice-water boundary** — Implement KD-tree collision detection before placement. Minimum O-O distance ~2.5 Å. This causes simulation failures if skipped.

2. **Hydrogen bond network discontinuity** — Surface ice molecules lose partners when truncated. Document as "initial configuration requiring MD relaxation" rather than trying to fix algorithmically.

3. **Density discontinuity (~8% difference)** — Ice (0.92 g/cm³) vs. liquid (1.0 g/cm³). Calculate separate dimensions for each region; don't use single box size for both.

4. **Export missing phase information** — Use chain/residue identifiers to distinguish ice (chain A) vs. liquid (chain B) in PDB output. Without this, downstream tools can't distinguish phases.

5. **User confusion with new parameters** — Every new input needs tooltips, sensible defaults, and validation feedback. Presets for common configurations reduce cognitive load.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Infrastructure
**Rationale:** Build service layer isolated from GUI, enabling unit testing without Qt event loop.
**Delivers:** Working interface generation pipeline without UI.
**Addresses:** Mode selector, interface assembly, liquid generation
**Avoids:** Atom overlap (collision detection from day one)
**Components:**
- `structure_generation/types.py` — InterfaceCandidate, InterfaceConfig dataclasses
- `structure_generation/liquid.py` — LiquidGenerator with random placement + density
- `structure_generation/interface.py` — InterfaceGenerator composing ice + liquid
- Slab mode implementation (simplest geometry)

### Phase 2: ViewModel Integration
**Rationale:** Connect worker to ViewModel following existing pattern exactly.
**Delivers:** Signal flow from generation to UI.
**Uses:** Existing MainViewModel extension pattern
**Implements:** InterfaceGenerationWorker, interface_* signals
**Components:**
- `gui/workers.py` — InterfaceGenerationWorker (same signals as GenerationWorker)
- `gui/viewmodel.py` — interface_started/complete/error signals, start_interface_generation()
- Unit tests verifying signal emission

### Phase 3: View Integration
**Rationale:** Connect UI to ViewModel, enable user interaction.
**Delivers:** Complete user workflow for interface generation.
**Addresses:** Box size input, thickness inputs, mode selector
**Avoids:** User confusion (tooltips, presets)
**Components:**
- `gui/main_window.py` — Mode toggle, input panel updates, signal connections
- `gui/molecular_viewer.py` — set_interface_candidate(), phase-based coloring
- Validation messages for nonsensical inputs

### Phase 4: Export and Polish
**Rationale:** Complete feature with working export.
**Delivers:** End-to-end usable feature.
**Addresses:** PDB/GROMACS export with phase markers
**Avoids:** Export missing phase information
**Components:**
- Verify existing exporters handle InterfaceCandidate
- Add chain/residue markers for phase distinction
- End-to-end tests: generate → view → export
- Performance validation with >2000 molecules

### Phase Ordering Rationale

- **Phase 1 first:** Service layer is core logic; building it first enables testing without GUI complexity. Collision detection implemented here prevents downstream debugging.
- **Phase 2 second:** ViewModel connects service to UI; low-risk addition following existing patterns exactly.
- **Phase 3 third:** View changes require UI understanding; build incrementally with each connection tested.
- **Phase 4 last:** Export is the completion criteria; validate entire pipeline before marking done.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Liquid water generation algorithm — decision needed between random placement, grid-based, or template-based. Research suggests grid-with-noise is adequate for MVP, but benchmark needed.
- **Phase 1:** Collision detection thresholds — specific minimum O-O distance values need verification from MD literature.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Worker/ViewModel integration — identical to existing GenerationWorker pattern, well-documented in codebase.
- **Phase 3:** Basic UI controls — standard PySide6 patterns, no novel implementation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via GenIce2 docs and existing codebase — no new libraries needed |
| Features | HIGH | Clear milestone requirements from project brief, GenIce2 limitations confirmed |
| Architecture | HIGH | Identical pattern to existing ice generation, source code reviewed |
| Pitfalls | MEDIUM-HIGH | Based on domain knowledge and computational chemistry principles; specific thresholds need verification |

**Overall confidence:** HIGH

### Gaps to Address

- **Collision detection thresholds:** Minimum O-O distance for physically reasonable interfaces. Handle by: using conservative 2.5 Å default, allow configuration, document as user-adjustable.
- **Surface premelting layer thickness:** Whether to include quasi-liquid layer on ice surfaces. Handle by: document as future enhancement, use sharp interface for MVP.
- **Crystal orientation defaults:** Which crystallographic face to use for slab mode. Handle by: default to basal plane [001] for Ih (thermodynamically preferred).

---

## Sources

### Primary (HIGH confidence)
- **GenIce2 Documentation** (PyPI, GitHub) — Confirmed ice-only generation, no liquid or interface support
- **QuickIce source code** — Existing MVVM patterns, worker implementation, VTK viewer, export writers
- **Architecture research** (ARCHITECTURE-INTERFACE.md) — Complete integration analysis with HIGH confidence rating

### Secondary (MEDIUM confidence)
- **Ice phase properties** — Densities from IAPWS and computational chemistry literature
- **Interface generation approaches** — Standard layer-stacking and particle-embedding techniques from MD simulation practice
- **GenIce2 architecture** — Seven-stage pipeline understanding from code review

### Tertiary (LOW confidence)
- **Specific collision thresholds** — Values inferred from van der Waals radii; need MD literature verification
- **Surface premelting effects** — Not critical for MVP; may need research if users request physically realistic surface layers

---

## Roadmap Ready

**Summary:** Ice-water interface generation is achievable as a Pure Python layer on existing infrastructure. The implementation follows proven MVVM patterns, requires no new dependencies, and has well-understood pitfalls with clear mitigations. Primary risk is atom overlap, addressed by mandatory collision detection in Phase 1.

**Recommendation:** Proceed with 4-phase roadmap. Flag Phase 1 for threshold research during planning.

---

*Research completed: 2026-04-08*  
*Ready for roadmap: yes*
