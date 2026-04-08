# QuickIce Roadmap: v3.0 Interface Generation

**Milestone:** v3.0 Interface Generation  
**Created:** 2026-04-08  
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface

---

## Overview

This milestone adds ice-water interface generation capability with a two-tab workflow: Tab 1 for generating ice candidates (existing) and Tab 2 for building interface structures using a selected candidate. Three geometry modes are supported: slab (layer stacking), pocket (water cavity in ice), and piece (ice crystal embedded in water). The feature requires new configuration controls, structure generation logic, visualization updates, and GROMACS export enhancements.

---

## Phases

### Phase 16: Tab Infrastructure

**Goal:** Users can switch between Ice Generation tab and Interface Construction tab to generate interface structures

**Dependencies:** None (foundation for remaining phases)

**Requirements:**
- WF-01: Application has two tabs: Ice Generation (existing) and Interface Construction (new)
- WF-02: Tab 1 functionality unchanged — generate ice candidates, select one
- WF-03: Selected ice candidate from Tab 1 is used as input for Tab 2
- WF-04: Tab 2 generates exactly one interface structure (not 10 candidates)

**Plans:** 2 plans

Plans:
- [x] 16-01-PLAN.md — Refactor MainWindow to QTabWidget, create InterfacePanel
- [x] 16-02-PLAN.md — Wire candidate dropdown, refresh button, preserve tab state

**Success Criteria:**

1. User sees two tabs in the application main window
2. Tab 1 (Ice Generation) allows generating and selecting ice candidates without modification
3. Selected ice candidate from Tab 1 is available in Tab 2 when tab is switched
4. Tab 2 generates exactly one interface structure per user action (not multiple candidates)

---

### Phase 17: Configuration Controls

**Goal:** Users can configure interface generation parameters through intuitive UI controls

**Dependencies:** Phase 16 (tab infrastructure must exist)

**Requirements:**
- CFG-01: User can select interface mode: slab, pocket, or piece
- CFG-02: User can input box size in nanometers
- CFG-03: For slab mode: user can input ice layer thickness (nm) and water layer thickness (nm)
- CFG-04: For pocket mode: user can input pocket size (diameter in nm) and shape (sphere/ellipse)
- CFG-05: For piece mode: user can input ice piece dimensions (uses selected candidate size as reference)
- CFG-06: User can input random seed for reproducibility

**Success Criteria:**

1. User can select interface mode from dropdown (slab, pocket, or piece)
2. Box size input field accepts numeric values in nanometers with validation
3. Slab mode shows ice thickness and water thickness input fields; pocket mode shows pocket size and shape; piece mode shows dimension inputs
4. Random seed input accepts integer values for reproducible generation
5. Input controls show tooltips explaining each parameter

---

### Phase 18: Structure Generation

**Goal:** Interface structures are correctly generated with ice and water phases assembled according to mode

**Dependencies:** Phase 16 (Tab 2 must exist to display results)

**Requirements:**
- GEN-01: Slab mode generates ice layer + water layer sandwich with correct densities
- GEN-02: Pocket mode generates water cavity inside ice matrix
- GEN-03: Piece mode generates ice crystal embedded in water box
- GEN-04: Ice structure comes from GenIce2 via selected candidate (Tab 1)
- GEN-05: Water structure comes from bundled quickice/data/tip4p.gro
- GEN-06: Interface assembly detects and resolves atom overlaps at boundaries
- GEN-07: Periodic boundary conditions are properly handled

**Success Criteria:**

1. Slab mode produces ice layer above/below water layer with correct densities (~0.92 g/cm³ ice, ~1.0 g/cm³ water)
2. Pocket mode creates water cavity within ice matrix at specified size
3. Piece mode embeds ice crystal in water box with ice dimensions from selected candidate
4. Atom overlaps at ice-water boundary are detected and resolved (minimum O-O distance ~2.5 Å)
5. Periodic boundary conditions maintain structural continuity across box edges

**Research Flag:**

> Piece mode shape control: Current MVP uses cube/box shape. Research needed on whether to support sphere, cylinder, or irregular shapes. Decision deferred to Phase 18 planning.

---

### Phase 19: Visualization

**Goal:** Users can view interface structures in 3D with clear visual distinction between ice and water phases

**Dependencies:** Phase 18 (structure generation must produce results)

**Requirements:**
- VIS-01: Single VTK viewer displays the interface structure (not dual viewport)
- VIS-02: Bond rendering uses lines (not ball-and-stick) for performance
- VIS-03: Ice region atoms render in one color, liquid water in different color
- VIS-04: Hydrogen bonds display as dashed lines across interface boundary

**Success Criteria:**

1. Single VTK viewer displays the complete interface structure
2. Molecular bonds render as lines (not ball-and-stick) for performance with large systems
3. Ice molecules render in one distinct color (e.g., cyan), water molecules in another (e.g., blue)
4. Hydrogen bonds display as dashed lines, including across the ice-water boundary

---

### Phase 20: Export

**Goal:** Users can export interface structures as GROMACS simulation files with phase distinction

**Dependencies:** Phase 19 (visualization confirms structure is correct before export)

**Requirements:**
- EXP-01: User can export interface structure as GROMACS files (.gro/.top/.itp)
- EXP-02: Ice and water phases are distinguished in topology (chain A = ice, chain B = water)
- EXP-03: Same TIP4P-ICE topology applies to both ice and water phases

**Success Criteria:**

1. User can export interface structure via GROMACS format action/shortcut
2. Exported .gro file contains chain identifiers: chain A for ice atoms, chain B for water atoms
3. Exported .top and .itp files use TIP4P-ICE force field for both ice and water molecules

---

## Progress

| Phase | Goal | Status | Requirements |
|-------|------|--------|--------------|
| 16 | Tab Infrastructure | Complete | WF-01, WF-02, WF-03, WF-04 |
| 17 | Configuration Controls | Pending | CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06 |
| 18 | Structure Generation | Pending | GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07 |
| 19 | Visualization | Pending | VIS-01, VIS-02, VIS-03, VIS-04 |
| 20 | Export | Pending | EXP-01, EXP-02, EXP-03 |

---

## Coverage

- **v3.0 requirements:** 23 total
- **Mapped to phases:** 23
- **Unmapped:** 0 ✓

---

*Roadmap created: 2026-04-08*