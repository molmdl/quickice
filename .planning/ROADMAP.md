# QuickIce v4.0 Roadmap

**Version:** 4.0  
**Goal:** Add molecule insertion capabilities to interface systems via new tabs  
**Phases:** 5  
**Depth:** comprehensive  
**Started:** 2026-04-14  

---

## Overview

QuickIce v4.0 adds molecule insertion capabilities: hydrates (Tab 2), NaCl ions (Tab 4), custom molecules, and enhanced 3D viewer controls. The milestone builds on v3.5's interface generation with new generation pipelines that handle multiple molecule types, per-type VTK rendering, and multi-molecule GROMACS export.

The 5-phase structure derives from research recommendations: fix pre-existing bugs first, establish multi-molecule data structures, then build ion insertion (simpler path), hydrate generation (new GenIce2 API), and custom molecule support with display controls.

---

## Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 28 - Pre-requisite Fixes | Fix 4 pre-existing bugs that block v4.0 development | — | 3 criteria |
| 28.1 - Urgent Bugfixes + FF (INSERTED) | Fix GUI errors, replace FF parameters | — | 3 plans complete |
| 29 - Data Structures + Multi-Molecule GROMACS | Establish foundation for multi-molecule work | GRO-01 to GRO-03, HYDR-01 to HYDR-05 | 5 criteria |
| 30 - Tab 4 Ion Insertion (NaCl) | User can insert NaCl ions into liquid phase | ION-01 to ION-07, WATER-02 | 5 criteria |
| 31 - Tab 2 Hydrate Generation | User can generate hydrate structures with guest molecules | HYDR-06 to HYDR-08, WATER-03 | 4 criteria |
| 31.1 - Integration Fixes (INSERTED) | Wire hydrate→interface, fix remaining ion insertion | — | 2 criteria |
| 32 - Custom Molecules + Display Controls | User can upload custom molecules and control 3D display | CUST-01 to CUST-07, VIEW-01 to VIEW-04, WATER-04 | 5 criteria |

---

## Dependencies

```
Phase 28 (Prerequisite Fixes)
    │
    ▼
Phase 28.1 (Urgent Bugfixes + FF) ─────────┐
    │                                       │
    ▼                                       │
Phase 29 (Data Structures + GROMACS) ──────┐│
    │                                       ││
    ▼                                       ││
Phase 30 (Ion Insertion) ◄──────────────────┤┘
    │                                       │
    ▼                                       │
Phase 31 (Hydrate Generation) ◄─────────────┘
    │
    ▼
Phase 32 (Custom Molecules + Display Controls)
```

- Phase 28 must complete before any other v4.0 phase (pre-existing bugs corrupt results)
- Phase 28.1 must complete before Phases 29-31 (bugfixes and FF corrections)
- Phase 29 must complete before Phases 30, 31, 32 (data structures needed)
- Phase 30 can start after Phase 29 (reuses InterfaceStructure from Tab 3)
- Phase 31 can start after Phase 29 (reuses multi-actor viewer pattern from Phase 30)
- Phase 32 depends on Phases 29, 30, 31 (needs all molecule type patterns established)

---

## Phase Details

### Phase 28: Pre-requisite Fixes

**Goal:** Fix 4 pre-existing bugs that block v4.0 development

**Rationale:** Four bugs documented in research/PITFALLS.md will silently corrupt results or crash the app during v4.0 development. Fixing them first prevents cascading failures.

**Requirements:** None (internal fixes)

**Plans:** 3 plans in 1 wave (all parallel)

Plans:
- [x] 28-01-PLAN.md — Fix random state restoration + add T/P metadata (generator.py)
- [x] 28-02-PLAN.md — Deduplicate GRO parser into shared module (gro_parser.py)
- [x] 28-03-PLAN.md — Unify is_cell_orthogonal() implementation (cell_utils.py)

**Success Criteria:**
1. GenIce2 numpy random state restored in finally block after any generation exception (Pitfall #7)
2. Temperature/Pressure metadata correctly stored in StructureResult (Pitfall #15)
3. GRO parser deduplicated into single _parse_gro_file() function used by all importers (Pitfall #16)
4. is_cell_orthogonal() unified with single implementation across codebase (Pitfall #21)

---

### Phase 28.1: Urgent Bugfixes + FF Corrections (INSERTED)

**Goal:** Fix GUI generation errors and replace incorrect force field parameters

**Rationale:** Critical bugs discovered during Phase 31 execution block hydrate and ion generation. Ion parameters used amberGS.ff without user approval - must replace with Madrid2019. CO2/H2 removed from UI but code not updated.

**Depends on:** Phase 28 (prerequisite fixes)

**Requirements:** None (urgent fixes)

**Plans:** 3 plans in 2 waves

Plans:
- [x] 28.1-01-PLAN.md — Fix tab ordering + ion insertion (main_window.py)
- [x] 28.1-02-PLAN.md — Remove CO2/H2 from types + hydrate code
- [x] 28.1-03-PLAN.md — FF corrections: Madrid2019 + atomtype ordering + CH4/THF

**Details:**
- Bugfix: Hydrate generation error
- Bugfix: Ion insertion error
- Bugfix: Tab ordering issues
- FF: Replace amberGS → Madrid2019 for ions
- FF: User will provide ch4.itp, thf.itp (GAFF)
- Cleanup: Remove CO2/H2 from hydrate code

---

### Phase 29: Data Structures + Multi-Molecule GROMACS

**Goal:** Establish foundation for multi-molecule work with extensible data structures and multi-type GROMACS export

**Rationale:** The single biggest risk is that the entire codebase assumes uniform atoms_per_molecule (3 for ice, 4 for water). Adding ions (1 atom) and guest molecules (5+ atoms) breaks every position-array iteration, bond-creation loop, and GROMACS export function. This phase resolves the molecule-segment index structure before any Tab 2/4 code works.

**Requirements:**
- GRO-01: Export produces .top with multiple [moleculetype] sections
- GRO-02: Export includes correct [molecules] counts per type
- GRO-03: User-provided .itp files included or referenced in export
- HYDR-01: User can select hydrate structure type (sI, sII, sH)
- HYDR-02: User can select built-in guest molecule (CH4, THF, CO2, H2)
- HYDR-03: User can specify cage occupancy (which cages get which guests)
- HYDR-04: User can set supercell repetition (nx, ny, nz)
- HYDR-05: System generates hydrate structure via GenIce2

**Plans:** 6 plans in 4 waves (COMPLETE)

Plans:
- [x] 29-01-PLAN.md — MoleculeIndex dataclass + InterfaceStructure extension
- [x] 29-02-PLAN.md — Hydrate configuration data structures (HydrateConfig, HydrateLatticeInfo)
- [x] 29-03-PLAN.md — Multi-molecule GROMACS export refactor
- [x] 29-04-PLAN.md — HydratePanel UI widget
- [x] 29-05-PLAN.md — Integrate HydratePanel into main window
- [x] 29-06-PLAN.md — HydrateStructureGenerator class with GenIce2 integration

**Plans:** 5 plans in 3 waves (READY)

Plans:
- [x] 30-01-PLAN.md — IonInserter class with concentration calculation and water replacement
- [x] 30-02-PLAN.md — GROMACS ion export (ion.itp generation)
- [x] 30-03-PLAN.md — IonPanel UI widget (Tab 4)
- [x] 30-04-PLAN.md — Ion rendering (VTK VDW sphere actors)
- [x] 30-05-PLAN.md — Water density display in Tab 1 info panel

**Success Criteria:**
1. User can select hydrate lattice (sI, sII, sH) and see lattice info display (cage types, counts)
2. User can select guest molecule (CH4, CO2) and specify cage occupancy (0-100%)
3. User can set supercell size (nx, ny, nz) and generate hydrate structure
4. 3D viewer renders hydrate with distinct styles for water framework vs guest molecules
5. GROMACS export produces valid .top with multiple [moleculetype] sections (water, ion, guest)

**Research Flags:** Phase 1 in research/SUMMARY.md flags multi-molecule data structure design as needing deeper research during planning.

---

### Phase 30: Tab 4 - Ion Insertion (NaCl)

**Goal:** User can insert NaCl ions into liquid phase of interface with concentration-based calculation

**Rationale:** Tab 4 reuses the most existing infrastructure (InterfaceStructure from Tab 3, cKDTree from overlap_resolver, GROMACS writer pattern). Proving multi-actor viewer and multi-type export with simpler ion insertion reduces risk before hydrate generation.

**Requirements:**
- ION-01: User can specify NaCl concentration (mol/L or g/kg)
- ION-02: System auto-calculates ion count from concentration and volume
- ION-03: System replaces water molecules (not ice) with ions
- ION-04: System enforces charge neutrality (equal Na+ and Cl-)
- ION-05: Ion placement avoids overlap with existing atoms
- ION-06: 3D viewer renders ions as VDW spheres (Na+ yellow, Cl- green)
- ION-07: GROMACS export includes bundled Na+/Cl- ion parameters
- WATER-02: Water density displayed in Tab 1 info panel

**Plans:** 5 plans in 3 waves (READY)

Plans:
- [x] 30-01-PLAN.md — IonInserter class with concentration calculation and water replacement
- [x] 30-02-PLAN.md — GROMACS ion export (ion.itp generation)
- [x] 30-03-PLAN.md — IonPanel UI widget (Tab 4)
- [x] 30-04-PLAN.md — Ion rendering (VTK VDW sphere actors)
- [x] 30-05-PLAN.md — Water density display in Tab 1 info panel

**Success Criteria:**
1. User can enter NaCl concentration in mol/L and see calculated ion count (auto-updates on change)
2. User can click "Insert Ions" and see Na+/Cl- ions appear in liquid region (not ice region)
3. User can toggle ion visibility on/off in 3D viewer (ions render as yellow/green spheres)
4. User can export to GROMACS and receive valid .gro/.top/.itp with Na+ and Cl- parameters
5. Water density from IAPWS-95 displays in Tab 1 info panel

**Key Guards:**
- Assertion: ion placement starts at liquid atom index (never replaces ice)
- Electroneutrality: always insert equal Na+ and Cl- counts

---

### Phase 31: Tab 2 - Hydrate Generation

**Goal:** User can generate hydrate structures with guest molecules via GenIce2 and export to GROMACS

**Rationale:** Requires a completely new GenIce2 API path (guests parameter, cage-based occupancy). Building after Phase 30 means the multi-actor viewer and multi-type export patterns are already proven.

**Requirements:**
- HYDR-06: 3D viewer displays guest molecules in distinct style from ice framework
- HYDR-07: GROMACS export produces valid .gro/.top/.itp with guest molecules
- HYDR-08: System displays hydrate unit cell info (cage counts, types)
- WATER-03: Interface liquid spacing matches target water density

**Success Criteria:**
1. User can generate sI/sII hydrate with CH4 guest and see water framework + guest in viewer
2. Guest molecules render in distinct style (ball-and-stick) from water framework (lines)
3. GROMACS export includes bundled ch4.itp with correct [moleculetype] and [molecules] count
4. Hydrate unit cell info displays: cage types (512, 51262), cage counts, guest occupancy

**Research Flags:** Phase 3 in research/SUMMARY.md flags GenIce2 hydrate API as needing deeper research during planning (guests parameter format undocumented).

**Plans:** 5 plans in 3 waves (PLANNED)

Plans:
- [x] 31-01-PLAN.md — HydrateWorker QThread class (background generation with progress)
- [x] 31-02-PLAN.md — HydrateRenderer module (dual-style VTK rendering)
- [x] 31-03-PLAN.md — HydrateViewerWidget class (viewer with placeholder/3D stack)
- [x] 31-04-PLAN.md — Hydrate tab integration (panel + viewer + worker wiring)
- [x] 31-05-PLAN.md — GROMACS export with bundled ch4.itp/thf.itp

---

### Phase 31.1: Integration Fixes (INSERTED)

**Goal:** Wire hydrate output to interface, fix remaining ion insertion issues

**Rationale:** Critical gaps discovered: (1) hydrate generated in Tab 2 cannot feed to Interface tab, (2) ion insertion was partially fixed in 28.1, remaining issues deferred

**Depends on:** Phase 31 (hydrate generation), Phase 28.1 (partial ion fix)

**Requirements:** None (integration fixes)

**Plans:** 4 plans in 1 wave

Plans:
- [x] 31.1-01-PLAN.md — IonViewerWidget (3D viewer for ion visualization)
- [x] 31.1-02-PLAN.md — IonPanel integration (viewer + main_window wiring)
- [x] 31.1-03-PLAN.md — Hydrate→Interface wiring (export capability)
- [ ] 31.1-04-PLAN.md — Hydrate-to-interface conversion (gap closure)

**Success Criteria:**
1. IonPanel has 3D viewer alongside configuration controls (like HydratePanel)
2. Ions render to IonPanel viewer, not Tab 1 viewer (clean separation)
3. Hydrate structure generated in Tab 2 can be used as input for Interface tab

---

### Phase 32: Custom Molecules + Display Controls

**Goal:** User can upload custom molecules and control 3D display per molecule type

**Rationale:** Both Tab 2 and Tab 4 need custom molecule support. Building it last lets the basic NaCl and CH4 flows stabilize first. File upload and validation add complexity best handled when core paths work.

**Requirements:**
- CUST-01: User can upload custom .gro file
- CUST-02: User can upload custom .itp topology file
- CUST-03: System validates .gro/.itp consistency (atom counts)
- CUST-04: User can select random placement mode in liquid phase
- CUST-05: System checks overlap after custom molecule placement
- CUST-06: 3D viewer renders custom molecules distinct from water/ions
- CUST-07: GROMACS export includes custom molecule .itp
- VIEW-01: System renders 5 molecule types (ice, liquid, ions, small molecules, large molecules)
- VIEW-02: User can toggle visibility per molecule type
- VIEW-03: User can select display style per molecule type (lines, ball-stick, VDW, stick)
- VIEW-04: User can select color per molecule type
- WATER-04: IAPWS density lookup cached (@lru_cache)

**Success Criteria:**
1. User can upload .gro + .itp files for custom molecule and see them render in 3D viewer
2. Validation error shows if .gro atom count doesn't match .itp [atoms] count
3. User can toggle visibility for each molecule type independently (ice, water, ions, small, large)
4. User can change display style per molecule type (lines for water, VDW for ions, ball-stick for guests)
5. IAPWS density lookups are cached (verify: repeated T/P lookups return cached value instantly)

---

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRO-01 | Phase 29 | Pending |
| GRO-02 | Phase 29 | Pending |
| GRO-03 | Phase 29 | Pending |
| HYDR-01 | Phase 29 | Pending |
| HYDR-02 | Phase 29 | Pending |
| HYDR-03 | Phase 29 | Pending |
| HYDR-04 | Phase 29 | Pending |
| HYDR-05 | Phase 29 | Pending |
| ION-01 | Phase 30 | Pending |
| ION-02 | Phase 30 | Pending |
| ION-03 | Phase 30 | Pending |
| ION-04 | Phase 30 | Pending |
| ION-05 | Phase 30 | Pending |
| ION-06 | Phase 30 | Pending |
| ION-07 | Phase 30 | Pending |
| HYDR-06 | Phase 31 | Pending |
| HYDR-07 | Phase 31 | Pending |
| HYDR-08 | Phase 31 | Pending |
| CUST-01 | Phase 32 | Pending |
| CUST-02 | Phase 32 | Pending |
| CUST-03 | Phase 32 | Pending |
| CUST-04 | Phase 32 | Pending |
| CUST-05 | Phase 32 | Pending |
| CUST-06 | Phase 32 | Pending |
| CUST-07 | Phase 32 | Pending |
| VIEW-01 | Phase 32 | Pending |
| VIEW-02 | Phase 32 | Pending |
| VIEW-03 | Phase 32 | Pending |
| VIEW-04 | Phase 32 | Pending |
| WATER-01 | Phase 29 | Pending |
| WATER-02 | Phase 30 | Pending |
| WATER-03 | Phase 31 | Pending |
| WATER-04 | Phase 32 | Pending |

**Coverage:** 33/33 requirements mapped ✓

---

## Progress

| Phase | Goal | Status |
|-------|------|--------|
| 28 | Pre-requisite Fixes | ✓ Complete |
| 28.1 | Urgent Bugfixes + FF Corrections | ✓ Complete (3/3 plans, human verified) |
| 29 | Data Structures + Multi-Molecule GROMACS | ✓ Complete |
| 30 | Tab 4 - Ion Insertion (NaCl) | ✓ Complete |
| 31 | Tab 2 - Hydrate Generation | ✓ Complete (5/5 plans, verified) |
| 31.1 | Integration Fixes (INSERTED) | ✓ Complete (4/4 plans, verified) |
| 32 | Custom Molecules + Display Controls | Not started |

**Overall:** ████████░ 83% (5/6 phases complete - Phase 32 pending)

---

*Roadmap created: 2026-04-14*
*Next: /gsd-plan-phase 28*