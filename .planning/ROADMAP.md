# Milestone v4.5: Solute & Custom Molecule Insertion

**Status:** 🔄 IN PROGRESS
**Phases:** 32-35 (with 34.1, 34.2, 34.3, 34.4, 34.5, 34.6 inserted)
**Total Plans:** 35 plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 34.6: 8, Phase 35: 6)

## Overview

QuickIce v4.5 extends the existing interface generation system with multi-atom molecule placement capabilities: solute insertion (Tab 4) for THF/CH₄ concentration-based placement in liquid water, and custom molecule upload (Tab 5) for user-provided .gro/.itp file pairs. The milestone adds two new tabs while moving Ion from Tab 4 to Tab 6, requiring careful architectural preparation to prevent cascading bugs from tab index changes.

The 4-phase structure delivers: architecture foundation (tab constants, MoleculetypeRegistry, ITP parser), solute insertion with concentration-based placement, custom molecule upload with validation, and integration with documentation. Key architectural shifts include all-atom overlap checking (vs. center-of-mass for ions), rotation matrices for multi-atom molecules, and MoleculetypeRegistry for distinguishing hydrate guests (CH4_HYD) from liquid solutes (CH4_LIQ).

## Phases

### Phase 32: Architecture Preparation

**Goal:** User can rely on stable tab infrastructure and molecule type tracking before new features are added
**Depends on:** v4.0 (Phase 31.2)
**Requirements:** ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05a, ARCH-06, GROMACS-02

**Success Criteria:**
1. Developer can reference tabs by TabIndex constants matching current positions (ION=3), preventing bugs when Ion moves to position 5 in Phase 35
2. User receives specific error messages when uploading invalid .gro/.itp files (atom count mismatch, residue name inconsistency)
3. Developer can reference tabs by named constants (TabIndex.ICE, TabIndex.HYDRATE, etc.) without hardcoded integers
4. GROMACS export distinguishes hydrate guests (CH4_HYD, THF_HYD) from liquid solutes (CH4_LIQ, THF_LIQ) in topology files

**Details:**
- TabIndex enum for tab position constants (defines current positions, Ion at position 3)
- MoleculetypeRegistry for tracking molecule types and generating unique GROMACS names
- itp_parser.py for parsing GROMACS .itp topology files (~80 lines)
- molecule_validator.py for GRO/ITP consistency checking
- Tab reordering preparation: Ion currently at position 3, will move to position 5 in Phase 35
- Cross-tab data flow verification (current flows work correctly)

**Plans:**
- [ ] 32-01-PLAN.md — Foundation: TabIndex enum, MoleculetypeRegistry, ITP parser
- [ ] 32-02-PLAN.md — Validation & refactoring: Molecule validator, TabIndex usage, GROMACS registry
- [ ] 32-03-PLAN.md — Verification: Cross-tab data flow, documentation, integration tests

---

### Phase 33: Solute Insertion (Tab 4)

**Goal:** User can insert THF or CH₄ solutes into liquid water at specified concentration with GROMACS-ready output
**Depends on:** Phase 32
**Requirements:** SOLUTE-01, SOLUTE-02, SOLUTE-03, SOLUTE-04, SOLUTE-05, SOLUTE-06, SOLUTE-07, SOLUTE-08, SOLUTE-09, VIS-01, VIS-03

**Success Criteria:**
1. User can input concentration (mol/L) and see calculated molecule count displayed
2. User can select THF or CH₄ from dropdown and see solutes inserted into liquid phase only
3. User sees solutes rendered distinctly from water, ice, hydrate guests, and ions in 3D viewer
4. User can export GROMACS files with solutes listed after SOL molecules in [molecules] section
5. User can generate multiple solute placements without atom overlap failures

**Details:**
- SolutePanel UI with concentration input, solute type dropdown, generate button
- SoluteWorker for background insertion with progress reporting
- SoluteInserter with concentration-based molecule count calculation
- Random placement with rotation matrix and all-atom overlap checking (cKDTree)
- Bundled .itp files for THF and CH₄ (GAFF2 parameters from existing data/)
- SoluteRenderer for distinct visualization (color/style from interface patterns)
- Moleculetype naming: CH4_LIQ, THF_LIQ (managed by MoleculetypeRegistry)

**Plans:**
- [x] 33-01-PLAN.md — Core insertion logic: SoluteConfig, SoluteStructure, SoluteInserter
- [x] 33-02-PLAN.md — Visualization: SoluteRenderer with ball-and-stick rendering
- [x] 33-03-PLAN.md — UI components: SolutePanel and SoluteViewerWidget
- [x] 33-04-PLAN.md — Integration & testing: MainWindow integration, TabIndex update, tests

---

### Phase 34: Custom Molecule Upload (Tab 5)

**Goal:** User can upload custom molecules via .gro/.itp files and insert them into liquid water with validation
**Depends on:** Phase 32, Phase 33
**Requirements:** CUSTOM-01, CUSTOM-02, CUSTOM-03, CUSTOM-04, CUSTOM-05, CUSTOM-06, CUSTOM-07, CUSTOM-08, CUSTOM-09, CUSTOM-10, CUSTOM-11, CUSTOM-12, VIS-02

**Success Criteria:**
1. User can upload .gro and .itp files via file dialogs and see validation status immediately
2. User receives specific error messages for invalid files (atom count mismatch, missing sections, residue name inconsistency)
3. User can choose random placement mode and see molecules inserted with all-atom overlap checking
4. User can specify custom center-of-mass position and rotation for precise placement
5. User can export GROMACS files with custom .itp bundled to output directory

**Details:**
- CustomMoleculePanel UI with file upload, placement mode selector, position/rotation inputs
- CustomMoleculeWorker for background validation and insertion
- CustomMoleculeInserter with two placement modes (random/custom)
- GRO/ITP parsing and validation (atom count, residue name, atomtypes extraction)
- All-atom overlap checking with VDW radii
- Custom molecule rendering with distinct actor style
- Moleculetype naming: CUSTOM_MOL_1, CUSTOM_MOL_2, etc.
- Error messages for specific validation failures

**Plans:**
- [x] 34-01-PLAN.md — Validation infrastructure: GRO residue extraction, molecule validator enhancement, type definitions
- [x] 34-02-PLAN.md — Core insertion logic: CustomMoleculeInserter with random and custom placement modes
- [x] 34-03-PLAN.md — Visualization: CustomMoleculeRenderer with distinct color palette
- [x] 34-04-PLAN.md — UI components: CustomMoleculePanel, CustomMoleculeWorker, CustomMoleculeViewerWidget
- [x] 34-05-PLAN.md — Integration & testing: MainWindow integration, GROMACS export, tests

---

### Phase 34.1: Ion Source Dropdown (INSERTED)

**Goal:** User can select ion insertion source (Interface/Custom/Solute) and receives warning when charge is not neutralized
**Depends on:** Phase 34
**Plans:** 3 plans

Plans:
- [x] 34.1-01-PLAN.md — UI foundation: Source dropdown, charge warning label, help icon
- [x] 34.1-02-PLAN.md — Handler logic: Source change handler, charge calculation, empty state
- [x] 34.1-03-PLAN.md — Integration tests: Source dropdown rendering, switching, warnings, empty states

**Details:**
- Ion tab source dropdown: Interface, Custom Molecule, or Solute
- Charge warning: Display warning message when custom molecules have non-neutral charge
- Charge neutralization: NOT implemented in this phase (user warned only)
- Follow Interface tab pattern for source selection UI and behavior

---

### Phase 34.2: Fix Liquid Solute ITP Export (INSERTED)

**Goal:** User can export liquid solutes with correct ITP files and residue names matching GROMACS requirements
**Depends on:** Phase 34.1
**Plans:** 2 plans

Plans:
- [x] 34.2-01-PLAN.md — Create liquid ITP files: ch4_liquid.itp and thf_liquid.itp
- [x] 34.2-02-PLAN.md — Update export integration: SoluteGROMACSExporter, IonGROMACSExporter, gromacs_writer

**Details:**
- Create separate ITP files for liquid solutes: ch4_liquid.itp, thf_liquid.itp
- Residue names: CH4_LIQ, THF_LIQ (matching MoleculetypeRegistry naming)
- Update export logic to copy correct ITP files based on molecule source
- Update GROMACS writer to use correct residue names for liquid solutes
- Ensure GRO and ITP residue names match
- Verify hydrate guests (CH4, THF) and liquid solutes (CH4_LIQ, THF_LIQ) can coexist

---

### Phase 34.3: Tab Order Swap (INSERTED)

**Goal:** User can upload custom molecules first (Tab 4), then use them as source for solute insertion (Tab 5), enabling Custom → Solute workflow
**Depends on:** Phase 34.2
**Plans:** 1 plan

Plans:
- [x] 34.3-01-PLAN.md — Swap Custom and Solute tab positions (TabIndex enum + addTab order)

**Details:**
- Swap TabIndex values: CUSTOM=4 → 3, SOLUTE=3 → 4
- Update addTab() order in MainWindow to match new enum values
- Update all comments to reflect new tab order
- Enables workflow: Custom Molecule upload → Solute insertion at concentration → Ion insertion
- No other files need changes (all code uses TabIndex constants)
- Phase 35 documentation plans need re-planning after this change (tab numbers will change)

---

### Phase 34.4: Solute Source Dropdown (INSERTED)

**Goal:** User can select solute insertion source (Interface or Custom Molecule) enabling the Custom → Solute workflow planned in architecture phase
**Depends on:** Phase 34.3
**Plans:** 2 plans

Plans:
- [x] 34.4-01-PLAN.md — UI foundation: Source dropdown, CustomMoleculePanel getters, availability tracking
- [x] 34.4-02-PLAN.md — MainWindow integration: Source handling, availability notifications

**Details:**
- Solute tab source dropdown: Interface (default) or Custom Molecule
- Follows Ion tab source dropdown pattern from Phase 34.1
- Implements planned architecture from 32-CONTEXT.md: "Internal CH4/THF can take from Interface or Custom"
- Enables workflow: Interface → Custom Molecule (Tab 3) → Solute (Tab 4) → Ion (Tab 5)
- Update MainWindow _on_insert_solutes handler to check source selection
- Integration tests for source switching

---

### Phase 34.5: Placement Validation & Preview (INSERTED)

**Goal:** User can preview custom molecule placement and receives validation for placement bounds and overlap detection
**Depends on:** Phase 34.4
**Plans:** 3 plans

Plans:
- [x] 34.5-01-PLAN.md — Validation logic: PlacementValidationResult dataclass, validate_single_placement method
- [x] 34.5-02-PLAN.md — Preview rendering: show_preview and clear_preview methods in CustomMoleculeViewerWidget
- [x] 34.5-03-PLAN.md — Validation UI: Validate & Preview button, result display, preview triggering in CustomMoleculePanel

**Details:**
- Single-molecule placement validation (bounds + overlap) without state mutation
- Semi-transparent preview rendering (opacity 0.6) for proposed positions
- On-demand validation via "Validate & Preview" button
- Structured feedback via PlacementValidationResult dataclass
- Clear validation result display in status log
- Preview shown in context of existing structure (ice, water, guests)
- Enables user to verify placement before committing to insertion
- Computationally feasible (O(M) for single molecule, not O(N×M) for full system)
- Addresses OUT OF SCOPE constraint by validating ONE molecule at a time

---

### Phase 34.6: Revise Custom Panel for Valid Input Handling (INSERTED - MAJOR SCOPE CHANGE)

**Goal:** Custom Molecule tab exports GROMACS-ready complete systems (ice + water + custom) that can be used as source for Solute tab
**Depends on:** Phase 34.5
**Plans:** 8 plans in 4 waves

Plans:
- [x] 34.6-01-PLAN.md — Fix validation warnings and button state persistence
- [x] 34.6-02-PLAN.md — Add liquid region bounds display and volume preview
- [x] 34.6-03-PLAN.md — Integration tests for bug fixes (Wave 2)
- [x] 34.6-04-PLAN.md — Modify CustomMoleculeStructure to include complete system
- [x] 34.6-05-PLAN.md — Update CustomMoleculeInserter to return complete system
- [x] 34.6-06-PLAN.md — Update CustomMoleculeGROMACSExporter for complete system export
- [x] 34.6-07-PLAN.md — Enable Custom Molecule as source for Solute tab
- [x] 34.6-08-PLAN.md — Comprehensive integration tests for complete workflow

**Details:**
- **MAJOR SCOPE CHANGE**: Each tab should export GROMACS-ready files prepared within the tab
- Custom Molecule tab exports complete system (ice + water + custom molecules)
- Custom Molecule result can be source for Solute tab (chain: Interface → Custom → Solute → Ion)
- Follows IonStructure/IonGROMACSExporter pattern for consistency

**Critical gap identified:**
- Current: CustomMoleculeStructure contains ONLY custom molecule atoms (incomplete)
- Required: CustomMoleculeStructure contains ALL atoms (ice + water + custom) like IonStructure

**Example inputs:** quickice/data/custom/etoh.itp and etoh.gro (ethanol molecule, 9 atoms, GAFF2 parameters)

**Bug fixes (Plans 01-02):**
- Preview button graying out after validation passes (should remain active)
- False positive warning: GRO resname "MOL" matches ITP moleculetype "etoh" (correct behavior, warning unnecessary)
- Missing documentation: liquid xyz range for manual placement
- Missing feature: volume preview for random concentration insertion

**Complete system export (Plans 04-07):**
- CustomMoleculeStructure includes ice_atom_count, water_atom_count, custom_molecule_atom_count
- CustomMoleculeInserter combines interface + custom molecules
- CustomMoleculeGROMACSExporter writes complete GRO/TOP files
- SolutePanel can receive CustomMoleculeStructure as source

**Testing requirements (Plans 03, 08):**
- Integration tests using etoh.itp/etoh.gro as valid input examples
- Test complete system generation (ice + water + custom)
- Test GROMACS export produces valid simulation files
- Test Custom → Solute workflow chain
- Test molecule_index tracking across all molecule types
  - Document moleculetype vs resname convention (GRO uses "MOL", ITP defines moleculetype name)
  - Add liquid xyz range guidance for manual placement mode
  - Example workflow: upload etoh files → validate → place in liquid → export

---

### Phase 35: Integration & Documentation

**Goal:** User has complete 6-tab workflow with reliable GROMACS export and comprehensive documentation
**Depends on:** Phase 32, Phase 33, Phase 34
**Requirements:** ARCH-05b, ARCH-07, GROMACS-01, GROMACS-03, DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05

**Success Criteria:**
1. User can navigate all 6 tabs (Ice, Hydrate, Interface, Solute, Custom, Ion) without data flow errors
2. User can export GROMACS files with correct molecule ordering: SOL → hydrate guests → liquid solutes → custom molecules → ions
3. User can press Ctrl+S to export from currently active tab
4. User can read documentation with v4.5 features, usage examples, and workflow guides
5. User can follow in-app tooltips and help text for solute and custom molecule workflows

**Details:**
- Unified keyboard shortcut implementation (Ctrl+S for export)
- GROMACS export order verification with tests
- README.md update for v4.5 (GUI-focused)
- In-app tooltips for Tab 4 (Solute) and Tab 5 (Custom) controls
- Help dialog update with correct tab numbering
- GUI guide extension with Tab 4/5 workflows
- User guide for creating valid .gro/.itp files
- Screenshot refresh (user checkpoint)

**Plans:**
- [x] 35-01-PLAN.md — Unified export & GROMACS verification: Keyboard shortcuts, molecule ordering tests
- [x] 35-02-PLAN.md — Tooltips for Tab 3/4: SolutePanel and CustomMoleculePanel tooltips
- [x] 35-03-PLAN.md — Help dialog update: Correct tab numbering, Tab 3/4 workflows, keyboard shortcuts
- [x] 35-04-PLAN.md — README update: v4.5 GUI focus, correct tab numbers, unified export
- [x] 35-05-PLAN.md — GUI guide & user guides: Tab 3/4 sections, .gro/.itp creation guide
- [ ] 35-06-PLAN.md — Screenshots checkpoint: Rename existing + recapture new (Option 1 decision from f345ca9)
- [ ] 35-07-PLAN.md — Quick Task docs: Document Quick Task 017/018 features (concentration input, delete/overlap)

---

## Milestone Summary

**Phase Count:** 10 (Phases 32-35, with 34.1, 34.2, 34.3, 34.4, 34.5, and 34.6 inserted)

**Total Plans:** 36 plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 34.6: 8, Phase 35: 7, e2e-export-test: 8, e2e-api-workflow: 5, e2e-compute-export: 5)

**Key Decisions:**
- TabIndex enum for tab position constants (prevents hardcoded index bugs)
- MoleculetypeRegistry for unique GROMACS naming (CH4_HYD vs CH4_LIQ distinction)
- All-atom overlap checking for multi-atom molecules (not center-of-mass)
- Rotation matrices for molecule orientation
- GAFF2 parameters for bundled THF/CH₄ solutes
- User-provided .itp files must include [ atomtypes ] section
- Euler angles for UI rotation input (converted internally to rotation matrix)

**Critical Pitfalls Addressed:**
- Overlap detection using all atoms (not center-of-mass) → prevents GROMACS failures
- Liquid-only placement (respects ice_atom_count boundary) → prevents crystal corruption
- Distinct moleculetype naming → prevents GROMACS duplicate moleculetype errors
- GRO/ITP validation before processing → prevents cryptic export failures

---

## Requirements Coverage

| Category | Mapped | Total | Coverage |
|----------|--------|-------|----------|
| Architecture (ARCH) | 7 | 7 | 100% |
| Solute Insertion (SOLUTE) | 9 | 9 | 100% |
| Custom Molecule (CUSTOM) | 12 | 12 | 100% |
| Visualization (VIS) | 3 | 3 | 100% |
| GROMACS Export (GROMACS) | 3 | 3 | 100% |
| Documentation (DOCS) | 5 | 5 | 100% |
| **Total v4.5** | **39** | **39** | **100%** |

**Note:** v4.5.1 CLI requirements (CLI-01 to CLI-05) deferred to follow-up milestone.

---

## Progress

| Phase | Status | Plans Completed | Total Plans |
|-------|--------|-----------------|-------------|
| 32 - Architecture Preparation | ✓ Complete | 3 | 3 |
| 33 - Solute Insertion | ✓ Complete | 4 | 4 |
| 34 - Custom Molecule Upload | ✓ Complete | 5 | 5 |
| 34.1 - Ion Source Dropdown | ✓ Complete | 3 | 3 |
| 34.2 - Fix Liquid Solute ITP Export | ✓ Complete | 2 | 2 |
| 34.3 - Tab Order Swap | ✓ Complete | 1 | 1 |
| 34.4 - Solute Source Dropdown | ✓ Complete | 2 | 2 |
| 34.5 - Placement Validation & Preview | ✓ Complete | 3 | 3 |
| 34.6 - Revise Custom Panel for Valid Input | ✓ Complete | 8 | 8 |
| 35 - Integration & Documentation | ⏳ In Progress | 5 | 7 |
| e2e-export-test - E2E GROMACS Export Testing | ✓ Complete | 8 | 8 |
| e2e-api-workflow - E2E API Workflow Testing | ✓ Complete | 5 | 5 |
| e2e-compute-export - E2E Compute→Export Bridge Testing | ✓ Complete | 5 | 5 |

---

### Phase e2e-compute-export: E2E Compute→Export Bridge Testing

**Goal:** Real computation pipeline output feeds into GROMACS exporters with correct atom ordering, topology format, and ITP bundling
**Depends on:** e2e-api-workflow (complete), e2e-export-test (complete)
**Requirements:** No new requirements — bridges two existing test phases

**Success Criteria:**
1. Full chain (Ice→Interface→Custom→Solute→Ion) output produces valid GROMACS .gro/.top/.itp files
2. Molecule ordering in .gro matches GROMACS convention: SOL→guests→solutes→custom→ions
3. .top [molecules] section lists all molecule types with correct counts
4. ITP files bundled correctly for each molecule type in the chain
5. Atom counts in .gro match structure positions (no atoms lost in export)

**Details:**
- Uses REAL structure generation (conftest.py fixtures from e2e-api-workflow)
- Calls GROMACS exporter methods directly (no QFileDialog mocking)
- Validates exported file content (parse .gro residue names, .top molecule sections, .itp presence)
- Tests the interface between computation pipeline output and export pipeline input
- Focuses on the gap not covered by either e2e-export-test (uses synthetic fixtures) or e2e-api-workflow (stops before export)

**Plans:** 5 plans in 3 waves
- [x] e2e-compute-export-01-PLAN.md — (Wave 1) Shared helpers module + Ice/Interface single-structure export (16 tests)
- [x] e2e-compute-export-02-PLAN.md — (Wave 2) Custom + Solute single-structure export (21 tests + 3 bugfixes)
- [x] e2e-compute-export-03-PLAN.md — (Wave 2) Ion single-structure export + ITP baseline (28 tests + bugfix)
- [x] e2e-compute-export-04-PLAN.md — (Wave 3) Full chain export F1-F4 (26 tests + bugfix)
- [x] e2e-compute-export-05-PLAN.md — (Wave 3) Simple chain export F5-F7 + cross-chain invariants (25 tests)

---

### Phase e2e-api-workflow: E2E API Workflow Testing

**Goal:** API-level end-to-end tests for the computation pipeline catch logic bugs before human UAT
**Depends on:** e2e-export-test (complete)
**Requirements:** No new requirements — tests verify existing v4.5 requirements work correctly at API level

**Success Criteria:**
1. Ice generation produces valid Candidate objects for all orthogonal phases
2. Hydrate generation works for sI/sII × ch4/thf with correct guest counts
3. Interface generation works for slab, pocket, piece modes with structural invariants
4. Custom molecule validation catches atom count mismatch, handles generic residue names
5. Solute insertion works from Interface and Custom sources with CH4_H/CH4_L coexistence
6. Ion insertion achieves charge neutrality, SoluteStructure bug (I5) exposed
7. Full workflow chains (F1-F7) produce structurally valid results

**Plans:**
- [x] e2e-api-workflow-01-PLAN.md — Shared conftest + ice/hydrate generation tests (~28 tests)
- [x] e2e-api-workflow-02-PLAN.md — Interface generation tests (~21 tests)
- [x] e2e-api-workflow-03-PLAN.md — Custom molecule validation + placement tests (~20 tests)
- [x] e2e-api-workflow-04-PLAN.md — Solute insertion tests (~17 tests)
- [x] e2e-api-workflow-05-PLAN.md — Ion insertion + workflow chain tests (~26 tests)

**Details:**
- 7 test files in flat tests/ directory (project convention)
- Module-scoped fixtures for real GenIce2 generation (~3-5s amortized)
- P0 tests: Full chain F1, CH4_H/CH4_L coexistence (S3), SoluteStructure bug (I5)
- P1 tests: Custom placement validation (C2), THF solute (S2), hydrate chain (F3), custom→ion (I3)
- P2 tests: Remaining combinations for coverage expansion
- Known bug exposure: SoluteStructure.molecule_index AttributeError when passed to IonInserter
- Total: ~82 tests across 5 plans, ~90s total execution time

---

*Roadmap created: 2026-05-05*
*Last updated: 2026-06-03 - e2e-compute-export phase complete (116 tests, 24/24 must-haves verified)*
*For current state, see .planning/STATE.md*
