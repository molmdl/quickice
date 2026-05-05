# Requirements: QuickIce v4.5 Solute & Custom Molecule Insertion

**Defined:** 2026-05-05
**Core Value:** Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface

## v4.5 Requirements

Requirements for solute insertion and custom molecule upload. Each maps to roadmap phases.

### Architecture & Infrastructure

- [x] **ARCH-01**: Tab index constants defined as named enum (prevent hardcoded reference bugs)
- [x] **ARCH-02**: MoleculetypeRegistry tracks molecule types and generates unique GROMACS names
- [x] **ARCH-03**: ITP parser module extracts molecule name, atom types, atom count from .itp files
- [x] **ARCH-04**: Molecule validator module checks GRO/ITP consistency (atom count, residue name)
- [x] **ARCH-05a**: TabIndex enum defines constants for current tab positions (Phase 32, Ion at position 3)
- [ ] **ARCH-05b**: Tab reordering when new tabs added (Ion moves from position 3 to position 5 in Phase 35)
- [x] **ARCH-06**: Data transfer mechanism between tabs (exact flow to be determined during implementation)
- [ ] **ARCH-07**: Keyboard shortcut Ctrl+S (or Ctrl+E) for GROMACS export from active tab

### Tab 4 — Solute Insertion

- [ ] **SOLUTE-01**: User can input solute concentration in mol/L
- [ ] **SOLUTE-02**: System auto-calculates molecule count from concentration and liquid volume
- [ ] **SOLUTE-03**: User can select solute type (THF or CH₄) via dropdown
- [ ] **SOLUTE-04**: System inserts solutes into liquid phase only (respects ice_atom_count boundary)
- [ ] **SOLUTE-05**: Placement uses random position and rotation with all-atom overlap checking
- [ ] **SOLUTE-06**: System uses bundled .itp files for THF and CH₄ (GAFF2 parameters)
- [ ] **SOLUTE-07**: GROMACS export uses distinct moleculetype names (CH4_LIQ, THF_LIQ)
- [ ] **SOLUTE-08**: 3D viewer displays solutes with distinct actor style (follows interface visualization patterns)
- [ ] **SOLUTE-09**: Tab layout follows existing hydrate/interface/ion tab patterns

### Tab 5 — Custom Molecule Upload

- [ ] **CUSTOM-01**: User can upload .gro file via file dialog
- [ ] **CUSTOM-02**: User can upload .itp file via file dialog
- [ ] **CUSTOM-03**: System validates GRO atom count matches ITP atom count
- [ ] **CUSTOM-04**: System validates residue name consistency between GRO and ITP
- [ ] **CUSTOM-05**: System extracts atomtypes from ITP for GROMACS export compatibility
- [ ] **CUSTOM-06**: System provides specific error messages for invalid files (atom count mismatch, missing sections, etc.)
- [ ] **CUSTOM-07**: Random placement mode: random position in liquid, random rotation, all-atom overlap checking
- [ ] **CUSTOM-08**: Custom placement mode: user-specified COM (x, y, z) and rotation matrix
- [ ] **CUSTOM-09**: GROMACS export bundles custom .itp file to output directory
- [ ] **CUSTOM-10**: GROMACS export uses unique moleculetype name (CUSTOM_MOL_1, etc.)
- [ ] **CUSTOM-11**: 3D viewer displays custom molecules with distinct actor style
- [ ] **CUSTOM-12**: Tab layout follows existing hydrate/interface/ion tab patterns

### Visualization

- [ ] **VIS-01**: 3D viewer follows interface visualization style for molecule representation
- [ ] **VIS-02**: Per-molecule-type display controls (visibility, style, color) available in viewer
- [ ] **VIS-03**: Solute molecules rendered distinctly from water, ice, hydrate guests, and ions

### GROMACS Export

- [ ] **GROMACS-01**: Export order enforced: SOL (ice + water) → hydrate guests → liquid solutes → custom molecules → ions
- [x] **GROMACS-02**: Moleculetype naming distinguishes hydrate guests (CH4_HYD) from liquid solutes (CH4_LIQ)
- [ ] **GROMACS-03**: All .itp files bundled correctly (tip4p-ice.itp, ch4.itp, thf.itp, ion.itp, custom .itp)

### Documentation

- [ ] **DOCS-01**: README.md updated with v4.5 features and usage examples
- [ ] **DOCS-02**: In-app tooltips added for Tab 4 and Tab 5 controls
- [ ] **DOCS-03**: In-app help text updated with solute/custom molecule workflows
- [ ] **DOCS-04**: Screenshot placeholders added to documentation for critical UI states
- [ ] **DOCS-05**: User guide created for creating valid .gro/.itp files for custom molecules

## v4.5.1 Requirements (CLI Extensions)

Deferred to v4.5.1 follow-up milestone. Linked to quicktasks 013-015.

### CLI Support

- **CLI-01**: CLI accepts --solute flag for solute insertion (THF/CH₄)
- **CLI-02**: CLI accepts --solute-concentration (mol/L)
- **CLI-03**: CLI accepts --custom-molecule flag with .gro/.itp file paths
- **CLI-04**: CLI accepts --placement-mode (random/custom) with custom COM/rotation parameters
- **CLI-05**: CLI progress reporting for solute/custom molecule insertion

**Note:** CLI implementation will follow patterns from quicktasks 013-015 (hydrate/ion CLI support, progress reporting).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multiple solute types simultaneously | HIGH complexity, defer to v5.0 |
| Multiple custom molecule types in single session | Each needs own .gro/.itp pair, complex UI |
| Placement preview before commit | Computationally expensive for large systems |
| GRO/ITP template generator | Molecule builder interface is stretch goal |
| Force field parameter auto-generation | User must provide complete .itp files |
| Solubility limit validation | Requires extensive property database |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 32 | Complete |
| ARCH-02 | Phase 32 | Complete |
| ARCH-03 | Phase 32 | Complete |
| ARCH-04 | Phase 32 | Complete |
| ARCH-05a | Phase 32 | Complete |
| ARCH-05b | Phase 35 | Pending |
| ARCH-06 | Phase 32 | Complete |
| ARCH-07 | Phase 35 | Pending |
| SOLUTE-01 | Phase 33 | Pending |
| SOLUTE-02 | Phase 33 | Pending |
| SOLUTE-03 | Phase 33 | Pending |
| SOLUTE-04 | Phase 33 | Pending |
| SOLUTE-05 | Phase 33 | Pending |
| SOLUTE-06 | Phase 33 | Pending |
| SOLUTE-07 | Phase 33 | Pending |
| SOLUTE-08 | Phase 33 | Pending |
| SOLUTE-09 | Phase 33 | Pending |
| CUSTOM-01 | Phase 34 | Pending |
| CUSTOM-02 | Phase 34 | Pending |
| CUSTOM-03 | Phase 34 | Pending |
| CUSTOM-04 | Phase 34 | Pending |
| CUSTOM-05 | Phase 34 | Pending |
| CUSTOM-06 | Phase 34 | Pending |
| CUSTOM-07 | Phase 34 | Pending |
| CUSTOM-08 | Phase 34 | Pending |
| CUSTOM-09 | Phase 34 | Pending |
| CUSTOM-10 | Phase 34 | Pending |
| CUSTOM-11 | Phase 34 | Pending |
| CUSTOM-12 | Phase 34 | Pending |
| VIS-01 | Phase 33 | Pending |
| VIS-02 | Phase 34 | Pending |
| VIS-03 | Phase 33 | Pending |
| GROMACS-01 | Phase 35 | Pending |
| GROMACS-02 | Phase 32 | Complete |
| GROMACS-03 | Phase 35 | Pending |
| DOCS-01 | Phase 35 | Pending |
| DOCS-02 | Phase 35 | Pending |
| DOCS-03 | Phase 35 | Pending |
| DOCS-04 | Phase 35 | Pending |
| DOCS-05 | Phase 35 | Pending |

**Coverage:**
- v4.5 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-05*
*Last updated: 2026-05-05 after roadmap creation (Phases 32-35)*
