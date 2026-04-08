# Requirements: QuickIce v3 Combined Seawater + Interface

**Defined:** 2026-04-08
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface
**Status:** DRAFT — pending research on seawater 2-phase behavior

---

## Overview

This milestone combines:
1. **Seawater Phase Diagram** (from v2.5) — Salinity-Temperature phase diagram with ion placement
2. **Liquid-Solid Interface** (from v3.0) — Ice-water interface structure generation with new input controls

---

## v3 Requirements

### Seawater Phase Diagram

- [ ] **SEA-01**: User can view salinity-temperature (S-T) phase diagram
- [ ] **SEA-02**: S-T diagram displays freezing point depression curve (IAPWS-08)
- [ ] **SEA-03**: User can click on S-T diagram to select salinity and temperature
- [ ] **SEA-04**: Selected S,T values update input fields
- [ ] **SEA-05**: Diagram shows 2-phase regions (Sea Ice vs Liquid Seawater)
- [ ] **SEA-06**: Salinity range 0-12% (practical seawater range)

### Salt Ion Placement

- [ ] **SALT-01**: Generated structure includes Na+ and Cl- ions
- [ ] **SALT-02**: Ion count proportional to selected salinity
- [ ] **SALT-03**: Ions are included in PDB output
- [ ] **SALT-04**: Ions are included in GROMACS output (.gro/.top)

### Interface Generation

- [ ] **INT-01**: User can generate ice-water interface structure
- [ ] **INT-02**: Interface combines crystalline ice layer + liquid water layer
- [ ] **INT-03**: Ice layer uses GenIce2 generated structure
- [ ] **INT-04**: Liquid water layer uses GROMACS tip4p.gro (bundled in quickice/data/)
- [ ] **INT-05**: Interface plane orientation is selectable (basal/prism)
- [ ] **INT-06**: Ice layer thickness is configurable
- [ ] **INT-07**: Water layer thickness is configurable

### Interface Geometry Modes

- [ ] **MODE-01**: Slab mode — X nm ice layer + Y nm water layer (standard sandwich)
- [ ] **MODE-02**: Ice-in-water mode — small ice crystal embedded in liquid water box
- [ ] **MODE-03**: Water-in-ice mode — water droplet/cavity in ice matrix

### Input Controls (Replacing nmol)

- [ ] **CTRL-01**: Replace nmol input with boxsize (nm) control
- [ ] **CTRL-02**: Add mode selector (slab/ice-in-water/water-in-ice)
- [ ] **CTRL-03**: Add seed control for random placement
- [ ] **CTRL-04**: Add ice thickness control (nm)
- [ ] **CTRL-05**: Add water thickness control (nm)

### Visualization

- [ ] **VIS-01**: Interface structure displays in VTK viewer
- [ ] **VIS-02**: Ice and liquid regions are visually distinct (color/representation)
- [ ] **VIS-03**: Hydrogen bonds displayed across interface boundary

### Export

- [ ] **EXP-01**: Interface structure exports as single PDB file
- [ ] **EXP-02**: Interface structure exports as GROMACS files (.gro/.top/.itp)

### UI Integration

- [ ] **UI-01**: Seawater diagram is a separate tab from pure water phase diagram
- [ ] **UI-02**: Tab switching preserves application state
- [ ] **UI-03**: Help tooltips explain S-T vs T-P diagram difference
- [ ] **UI-04**: Interface generation controls available in main window

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| High-pressure ice polymorphs (for seawater) | Ocean pressures < 100 MPa only |
| Brine pocket visualization | Structural generation only |
| 3D S-T-P surface | 2D diagram sufficient |
| Other salts (KCl, MgCl2) | NaCl only for MVP |
| MD minimization | Rule-based assembly sufficient for visualization |
| Pre-generated library | Dynamic generation preferred |
| Multiple interfaces | Single interface for MVP |
| Energy validation | Visualization-focused MVP |

---

## Pending Research Questions

### Seawater 2-Phase Behavior

**Question:** Should seawater output include BOTH phases (ice + liquid seawater) in one structure?

Options to research:
- Option A: Output mixed structure (ice region + liquid region with ions)
- Option B: User selects which phase to generate (pure sea ice OR pure liquid seawater)
- Option C: Generate ice structure with excluded volume where brine would be

**Decision needed before requirements finalization.**

### Liquid Water Source

**Resolved:** Use GROMACS tip4p.gro (bundled in quickice/data/)
- GROMACS ships with equilibrated TIP4P water box
- Copy from `$GMXDATA/top/tip4p.gro` or equivalent
- Bundle with QuickIce to avoid GROMACS dependency at runtime

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEA-01 | TBD | Pending |
| SEA-02 | TBD | Pending |
| SEA-03 | TBD | Pending |
| SEA-04 | TBD | Pending |
| SEA-05 | TBD | Pending |
| SEA-06 | TBD | Pending |
| SALT-01 | TBD | Pending |
| SALT-02 | TBD | Pending |
| SALT-03 | TBD | Pending |
| SALT-04 | TBD | Pending |
| INT-01 | TBD | Pending |
| INT-02 | TBD | Pending |
| INT-03 | TBD | Pending |
| INT-04 | TBD | Pending |
| INT-05 | TBD | Pending |
| INT-06 | TBD | Pending |
| INT-07 | TBD | Pending |
| MODE-01 | TBD | Pending |
| MODE-02 | TBD | Pending |
| MODE-03 | TBD | Pending |
| CTRL-01 | TBD | Pending |
| CTRL-02 | TBD | Pending |
| CTRL-03 | TBD | Pending |
| CTRL-04 | TBD | Pending |
| CTRL-05 | TBD | Pending |
| VIS-01 | TBD | Pending |
| VIS-02 | TBD | Pending |
| VIS-03 | TBD | Pending |
| EXP-01 | TBD | Pending |
| EXP-02 | TBD | Pending |
| UI-01 | TBD | Pending |
| UI-02 | TBD | Pending |
| UI-03 | TBD | Pending |
| UI-04 | TBD | Pending |

**Coverage:**
- v3 requirements: 34 total
- Mapped to phases: 0 (TBD after roadmap creation)
- Unmapped: 34 ⚠️

---

## Source Files

This document synthesized from:
- `.planning/v2.5-REQUIREMENTS.md` — Original seawater requirements
- `.planning/v3.0-REQUIREMENTS.md` — Original interface requirements
- `.planning/v2.1.1_v2.5_v3_NOTES.md.md` — Updated requirements notes

---

*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 — Combined draft created, pending research*
