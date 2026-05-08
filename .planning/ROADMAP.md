# Milestone v4.5: Solute & Custom Molecule Insertion

**Status:** 🔄 IN PROGRESS
**Phases:** 32-35 (with 34.1, 34.2, 34.3, 34.4, 34.5 inserted)
**Total Plans:** 27 plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 35: 6)

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
- [ ] 34.5-01-PLAN.md — Validation logic: PlacementValidationResult dataclass, validate_single_placement method
- [ ] 34.5-02-PLAN.md — Preview rendering: show_preview and clear_preview methods in CustomMoleculeViewerWidget
- [ ] 34.5-03-PLAN.md — Validation UI: Validate & Preview button, result display, preview triggering in CustomMoleculePanel

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
- [ ] 35-02-PLAN.md — Tooltips for Tab 3/4: SolutePanel and CustomMoleculePanel tooltips
- [ ] 35-03-PLAN.md — Help dialog update: Correct tab numbering, Tab 3/4 workflows, keyboard shortcuts
- [ ] 35-04-PLAN.md — README update: v4.5 GUI focus, correct tab numbers, unified export
- [ ] 35-05-PLAN.md — GUI guide & user guides: Tab 3/4 sections, .gro/.itp creation guide
- [ ] 35-06-PLAN.md — Screenshots: Rename existing files, capture new screenshots

---

## Milestone Summary

**Phase Count:** 9 (Phases 32-35, with 34.1, 34.2, 34.3, 34.4, and 34.5 inserted)

**Total Plans:** 27 plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 35: 6)

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
| 34.5 - Placement Validation & Preview | ⏳ Pending | 0 | 0 |
| 35 - Integration & Documentation | ⏳ Pending | 1 | 6 |

---

*Roadmap created: 2026-05-05*
*Last updated: 2026-05-08 - Phase 34.5 inserted*
*For current state, see .planning/STATE.md*
