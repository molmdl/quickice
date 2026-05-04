# Milestone v4.5: Solute & Custom Molecule Insertion

**Status:** 🔄 IN PROGRESS
**Phases:** 32-35
**Total Plans:** 3 plans (Phase 32)

## Overview

QuickIce v4.5 extends the existing interface generation system with multi-atom molecule placement capabilities: solute insertion (Tab 4) for THF/CH₄ concentration-based placement in liquid water, and custom molecule upload (Tab 5) for user-provided .gro/.itp file pairs. The milestone adds two new tabs while moving Ion from Tab 4 to Tab 6, requiring careful architectural preparation to prevent cascading bugs from tab index changes.

The 4-phase structure delivers: architecture foundation (tab constants, MoleculetypeRegistry, ITP parser), solute insertion with concentration-based placement, custom molecule upload with validation, and integration with documentation. Key architectural shifts include all-atom overlap checking (vs. center-of-mass for ions), rotation matrices for multi-atom molecules, and MoleculetypeRegistry for distinguishing hydrate guests (CH4_HYD) from liquid solutes (CH4_LIQ).

## Phases

### Phase 32: Architecture Preparation

**Goal:** User can rely on stable tab infrastructure and molecule type tracking before new features are added
**Depends on:** v4.0 (Phase 31.2)
**Requirements:** ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05, ARCH-06, GROMACS-02

**Success Criteria:**
1. User sees Ion tab at position 6 (not position 4) with all cross-tab data flow working correctly
2. User receives specific error messages when uploading invalid .gro/.itp files (atom count mismatch, residue name inconsistency)
3. Developer can reference tabs by named constants (TabIndex.ICE, TabIndex.HYDRATE, etc.) without hardcoded integers
4. GROMACS export distinguishes hydrate guests (CH4_HYD, THF_HYD) from liquid solutes (CH4_LIQ, THF_LIQ) in topology files

**Details:**
- TabIndex enum for tab position constants
- MoleculetypeRegistry for tracking molecule types and generating unique GROMACS names
- itp_parser.py for parsing GROMACS .itp topology files (~80 lines)
- molecule_validator.py for GRO/ITP consistency checking
- Tab reordering: Ion moves Tab 4 → Tab 6
- Cross-tab data flow verification after reordering

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

---

### Phase 35: Integration & Documentation

**Goal:** User has complete 6-tab workflow with reliable GROMACS export and comprehensive documentation
**Depends on:** Phase 32, Phase 33, Phase 34
**Requirements:** ARCH-07, GROMACS-01, GROMACS-03, DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05

**Success Criteria:**
1. User can navigate all 6 tabs (Ice, Hydrate, Interface, Solute, Custom, Ion) without data flow errors
2. User can export GROMACS files with correct molecule ordering: SOL → hydrate guests → liquid solutes → custom molecules → ions
3. User can press Ctrl+S (or Ctrl+E) to export from currently active tab
4. User can read documentation with v4.5 features, usage examples, and workflow guides
5. User can follow in-app tooltips and help text for solute and custom molecule workflows

**Details:**
- Cross-tab data flow testing
- GROMACS export order enforcement
- Keyboard shortcut implementation (Ctrl+S or Ctrl+E)
- README.md update for v4.5
- In-app tooltips for Tab 4 and Tab 5 controls
- In-app help text update
- Screenshot placeholders for critical UI states
- User guide for creating valid .gro/.itp files

---

## Milestone Summary

**Phase Count:** 4 (Phases 32-35)

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
| 32 - Architecture Preparation | ⏳ Pending | 0 | 3 |
| 33 - Solute Insertion | ⏳ Pending | 0 | TBD |
| 34 - Custom Molecule Upload | ⏳ Pending | 0 | TBD |
| 35 - Integration & Documentation | ⏳ Pending | 0 | TBD |

---

*Roadmap created: 2026-05-05*
*For current state, see .planning/STATE.md*
