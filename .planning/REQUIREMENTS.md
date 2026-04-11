# Requirements: QuickIce v3.5

**Defined:** 2026-04-12
**Core Value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface

## v3.5 Requirements

Requirements for Interface Enhancements milestone.

### Triclinic Transformation

- [ ] **TRAN-01**: System auto-detects triclinic cells for ice_ii and ice_v phases
- [ ] **TRAN-02**: System transforms triclinic cells to orthogonal while preserving crystal structure
- [ ] **TRAN-03**: System skips transformation for already-orthogonal phases (ice_ih, ice_ic, ice_iii, ice_vi, ice_vii, ice_viii)

### CLI Interface Generation

- [ ] **CLI-01**: User can generate interface via `--interface` flag with mode parameter (slab/pocket/piece)
- [ ] **CLI-02**: User can specify box dimensions (box_x, box_y, box_z) and seed for all modes
- [ ] **CLI-03**: User can specify ice_thickness and water_thickness for slab mode
- [ ] **CLI-04**: User can specify pocket_diameter and pocket_shape for pocket mode
- [ ] **CLI-05**: User can export interface structures to GROMACS format from CLI

### Density Features

- [ ] **DENS-01**: System calculates water density from T/P using IAPWS library
- [ ] **DENS-02**: System displays water density in UI
- [ ] **DENS-03**: System calculates Ice Ih density from IAPWS (temperature-dependent, replaces hardcoded 0.9167 g/cm³)
- [ ] **DENS-04**: System caches IAPWS density lookups for performance

## v4.0 Requirements (Future)

Deferred to next milestone.

### Molecule Insertion to Ice (Tab 2)

- **MOLI-01**: User can generate GenIce2 hydrate structures with custom topology
- **MOLI-02**: User can insert custom molecules into ice lattice
- **MOLI-03**: System supports multiple molecule types in single structure

### Molecule Insertion to Liquid (Tab 4)

- **MOLL-01**: User can add NaCl ions to liquid phase from concentration
- **MOLL-02**: System replaces water molecules, not ice molecules, when inserting ions
- **MOLL-03**: User can insert custom molecules with random or specified placement
- **MOLL-04**: 3D viewer displays distinct styles per molecule type

## Out of Scope

| Feature | Reason |
|---------|--------|
| Additional ice phases beyond GenIce2 support | Depends on GenIce2 library updates |
| Automated interface geometry optimization | MD simulation required, out of scope |
| Real-time density preview while typing | Performance concern, defer to future |
| Multiple salt types (KCl, MgCl2) | NaCl sufficient for v4.0 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRAN-01 | — | Pending |
| TRAN-02 | — | Pending |
| TRAN-03 | — | Pending |
| CLI-01 | — | Pending |
| CLI-02 | — | Pending |
| CLI-03 | — | Pending |
| CLI-04 | — | Pending |
| CLI-05 | — | Pending |
| DENS-01 | — | Pending |
| DENS-02 | — | Pending |
| DENS-03 | — | Pending |
| DENS-04 | — | Pending |

**Coverage:**
- v3.5 requirements: 12 total
- Mapped to phases: 0
- Unmapped: 12 ⚠️

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after initial definition*
