# Requirements: QuickIce v3.0 Interface Generation

**Defined:** 2026-04-08
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface
**Status:** Ready for roadmap

---

## Overview

This milestone adds ice-water interface generation capability with a two-tab workflow:
1. **Tab 1 (existing):** Generate ice candidates → Select one
2. **Tab 2 (new):** Build interface using selected ice candidate

Three geometry modes: slab, pocket, piece.

---

## v3.0 Requirements

### Tab Workflow

- [ ] **WF-01**: Application has two tabs: Ice Generation (existing) and Interface Construction (new)
- [ ] **WF-02**: Tab 1 functionality unchanged — generate ice candidates, select one
- [ ] **WF-03**: Selected ice candidate from Tab 1 is used as input for Tab 2
- [ ] **WF-04**: Tab 2 generates exactly one interface structure (not 10 candidates)

### Interface Configuration (Tab 2)

- [ ] **CFG-01**: User can select interface mode: slab, pocket, or piece
- [ ] **CFG-02**: User can input box size in nanometers
- [ ] **CFG-03**: For slab mode: user can input ice layer thickness (nm) and water layer thickness (nm)
- [ ] **CFG-04**: For pocket mode: user can input pocket size (diameter in nm) and shape (sphere/ellipse)
- [ ] **CFG-05**: For piece mode: user can input ice piece dimensions (uses selected candidate size as reference)
- [ ] **CFG-06**: User can input random seed for reproducibility

### Structure Generation

- [ ] **GEN-01**: Slab mode generates ice layer + water layer sandwich with correct densities
- [ ] **GEN-02**: Pocket mode generates water cavity inside ice matrix
- [ ] **GEN-03**: Piece mode generates ice crystal embedded in water box
- [ ] **GEN-04**: Ice structure comes from GenIce2 via selected candidate (Tab 1)
- [ ] **GEN-05**: Water structure comes from bundled quickice/data/tip4p.gro
- [ ] **GEN-06**: Interface assembly detects and resolves atom overlaps at boundaries
- [ ] **GEN-07**: Periodic boundary conditions are properly handled

### Visualization (Tab 2)

- [ ] **VIS-01**: Single VTK viewer displays the interface structure (not dual viewport)
- [ ] **VIS-02**: Bond rendering uses lines (not ball-and-stick) for performance
- [ ] **VIS-03**: Ice region atoms render in one color, liquid water in different color
- [ ] **VIS-04**: Hydrogen bonds display as dashed lines across interface boundary

### Export

- [ ] **EXP-01**: User can export interface structure as GROMACS files (.gro/.top/.itp)
- [ ] **EXP-02**: Ice and water phases are distinguished in topology (chain A = ice, chain B = water)
- [ ] **EXP-03**: Same TIP4P-ICE topology applies to both ice and water phases

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| PDB export for interface | GROMACS-only workflow |
| Multiple interface candidates | Single model sufficient |
| Dual viewport comparison | Memory constraints |
| Ball-and-stick rendering | Performance priority |
| MD simulation in-app | Generation only |
| Energy minimization | Visualization-focused MVP |
| Interface orientation control | Defer to future version |
| Multiple water models | TIP4P-ICE only |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WF-01 | Phase 16 | Pending |
| WF-02 | Phase 16 | Pending |
| WF-03 | Phase 16 | Pending |
| WF-04 | Phase 16 | Pending |
| CFG-01 | Phase 17 | Pending |
| CFG-02 | Phase 17 | Pending |
| CFG-03 | Phase 17 | Pending |
| CFG-04 | Phase 17 | Pending |
| CFG-05 | Phase 17 | Pending |
| CFG-06 | Phase 17 | Pending |
| GEN-01 | Phase 18 | Pending |
| GEN-02 | Phase 18 | Pending |
| GEN-03 | Phase 18 | Pending |
| GEN-04 | Phase 18 | Pending |
| GEN-05 | Phase 18 | Pending |
| GEN-06 | Phase 18 | Pending |
| GEN-07 | Phase 18 | Pending |
| VIS-01 | Phase 19 | Pending |
| VIS-02 | Phase 19 | Pending |
| VIS-03 | Phase 19 | Pending |
| VIS-04 | Phase 19 | Pending |
| EXP-01 | Phase 20 | Pending |
| EXP-02 | Phase 20 | Pending |
| EXP-03 | Phase 20 | Pending |

**Coverage:**
- v3.0 requirements: 23 total
- Mapped to phases: 23 ✓
- Unmapped: 0

---

*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 — Roadmap created, traceability added*
