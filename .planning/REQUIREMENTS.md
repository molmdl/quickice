# Requirements: QuickIce

**Defined:** 2026-04-14
**Core Value:** Generate plausible ice structure candidates and interfaces quickly with an intuitive visual interface

## v4.0 Requirements

Molecule insertion milestone: hydrates + ions + custom molecules + enhanced 3D viewer

### Hydrates (Tab 2)

- [ ] **HYDR-01**: User can select hydrate structure type (sI, sII, sH)
- [ ] **HYDR-02**: User can select built-in guest molecule (CH4, THF, CO2, H2)
- [ ] **HYDR-03**: User can specify cage occupancy (which cages get which guests)
- [ ] **HYDR-04**: User can set supercell repetition (nx, ny, nz)
- [ ] **HYDR-05**: System generates hydrate structure via GenIce2
- [ ] **HYDR-06**: 3D viewer displays guest molecules in distinct style from ice framework
- [ ] **HYDR-07**: GROMACS export produces valid .gro/.top/.itp with guest molecules
- [ ] **HYDR-08**: System displays hydrate unit cell info (cage counts, types)

### Ions (Tab 4)

- [ ] **ION-01**: User can specify NaCl concentration (mol/L or g/kg)
- [ ] **ION-02**: System auto-calculates ion count from concentration and volume
- [ ] **ION-03**: System replaces water molecules (not ice) with ions
- [ ] **ION-04**: System enforces charge neutrality (equal Na+ and Cl-)
- [ ] **ION-05**: Ion placement avoids overlap with existing atoms
- [ ] **ION-06**: 3D viewer renders ions as VDW spheres (Na+ yellow, Cl- green)
- [ ] **ION-07**: GROMACS export includes bundled Na+/Cl- ion parameters

### Custom Molecules (Tab 4)

- [ ] **CUST-01**: User can upload custom .gro file
- [ ] **CUST-02**: User can upload custom .itp topology file
- [ ] **CUST-03**: System validates .gro/.itp consistency (atom counts)
- [ ] **CUST-04**: User can select random placement mode in liquid phase
- [ ] **CUST-05**: System checks overlap after custom molecule placement
- [ ] **CUST-06**: 3D viewer renders custom molecules distinct from water/ions
- [ ] **CUST-07**: GROMACS export includes custom molecule .itp

### 3D Viewer Enhancements

- [ ] **VIEW-01**: System renders 5 molecule types (ice, liquid, ions, small molecules, large molecules)
- [ ] **VIEW-02**: User can toggle visibility per molecule type
- [ ] **VIEW-03**: User can select display style per molecule type (lines, ball-stick, VDW, stick)
- [ ] **VIEW-04**: User can select color per molecule type

### GROMACS Export (Cross-Cutting)

- [ ] **GRO-01**: Export produces .top with multiple [moleculetype] sections
- [ ] **GRO-02**: Export includes correct [molecules] counts per type
- [ ] **GRO-03**: User-provided .itp files included or referenced in export

### Water Density (v3.5 Carryover)

- [ ] **WATER-01**: Water density calculated from T/P via IAPWS-95
- [ ] **WATER-02**: Water density displayed in Tab 1 info panel
- [ ] **WATER-03**: Interface liquid spacing matches target water density
- [ ] **WATER-04**: IAPWS density lookup cached (@lru_cache)

## v5.0 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Hydrates (Future)

- **HYDR-09**: Custom MOL file import from MolView.org
- **HYDR-10**: Mixed cage occupancy with fraction syntax
- **HYDR-11**: Ion doping in hydrate structures
- **HYDR-12**: Semiclathrate support (TBAB)

### Ions (Future)

- **ION-08**: Multiple salt types (KCl, MgCl2)
- **ION-09**: Concentration unit conversion (mol/L ↔ g/kg)

### Custom Molecules (Future)

- **CUST-08**: Custom COM + rotation placement mode
- **CUST-09**: Multiple custom molecule types in single system

### 3D Viewer (Future)

- **VIEW-05**: Cage boundary visualization (polyhedra)
- **VIEW-06**: Atom-type-based coloring
- **VIEW-07**: Unit cell overlay for hydrates

## Out of Scope

| Feature | Reason |
|---------|--------|
| MD simulation launch | Outside QuickIce scope (generation only) |
| Multiple salt types (KCl, MgCl2) | Requires different .itp parameters; start with NaCl only |
| Real-time 3D preview during generation | GenIce generation takes seconds |
| Force field parameter generation | Requires MD expertise beyond scope |
| Custom hydrate lattice creation | Crystallographically wrong structures |
| pH/ionic strength calculation | Too complex for MVP |
| Solvation free energy calculation | Research-grade simulation |

## Traceability

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

**Coverage:**
- v4.0 requirements: 33 total
- Mapped to phases: 33 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after v4.0 requirements definition*