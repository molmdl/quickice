# Milestone v4.5: Solute & Custom Molecule Insertion

**Status:** 🔄 IN PROGRESS
**Phases:** 32-37 (with 34.1, 34.2, 34.3, 34.4, 34.5, 34.6, 34.7, 34.8, 37.1 inserted)
**Total Plans:** 86+ plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 34.6: 9, Phase 34.7: 3, Phase 34.8: 5, Phase 35: 7, Phase 36: 11, Phase 37: 20, Phase 37.1: 15, e2e-compute-export: 11, completed: 86/86+)

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
**Plans:** 9 plans in 4 waves + gap closure

Plans:
- [x] 34.6-01-PLAN.md — Fix validation warnings and button state persistence
- [x] 34.6-02-PLAN.md — Add liquid region bounds display and volume preview
- [x] 34.6-03-PLAN.md — Integration tests for bug fixes (Wave 2)
- [x] 34.6-04-PLAN.md — Modify CustomMoleculeStructure to include complete system
- [x] 34.6-05-PLAN.md — Update CustomMoleculeInserter to return complete system
- [x] 34.6-06-PLAN.md — Update CustomMoleculeGROMACSExporter for complete system export
- [x] 34.6-07-PLAN.md — Enable Custom Molecule as source for Solute tab
- [x] 34.6-08-PLAN.md — Comprehensive integration tests for complete workflow
- [x] 34.6-09-PLAN.md — GAP: Fix TOP [molecules] assertion (ETOH→etoh)

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

### Phase 34.7: Fix Verified Scancode Bugs (INSERTED)

**Goal:** Fix verified critical/high bugs in GROMACS export pipeline and inserters discovered during codebase scanning, ensuring correct atom coordinates, reproducible placement, and consistent forcefield defaults
**Depends on:** Phase 34.6
**Plans:** 3 plans

Plans:
- [x] 34.7-01-PLAN.md — Fix GROMACS writer bugs: BUG-05 (HW1 Z-coordinate), MW-01 (molecule-aware wrapping), DEFLT-01 (fudgeLJ standardization)
- [x] 34.7-02-PLAN.md — Fix inserter bugs: ATOM-01 (WATER_ATOMS_PER_MOLECULE constant), RNG-01 (seeded RNG + Rotation.random)
- [x] 34.7-03-PLAN.md — Fix KDTree optimization: TREE-01 (conditional rebuild in ion inserter)

**Details:**

Verified issues from `.planning/codebase/20260608_ISSUES_VERIFICATION.md`:

| ID | Severity | Finding | Fix Complexity |
|----|----------|---------|---------------|
| BUG-05 | 🔴 CRITICAL | HW1 Z-coordinate copy-paste at gromacs_writer.py:1971 (`h2_pos[2]` should be `h1_pos[2]`) | Trivial (1 char) |
| MW-01 | 🟠 HIGH | `write_ice_gro_file` uses atom-level wrapping; MW recomputed from discontinuous positions | Simple (switch to `wrap_molecules_into_box`) |
| RNG-01 | 🟠 HIGH | `CustomMoleculeInserter.place_random()` uses unseeded RNG; non-reproducible results | Moderate (add seed param + seed Rotation.random) |
| DEFLT-01 | 🟠 HIGH | `fudgeLJ=0.5` in simple writers vs `0.0` in multi-molecule writers; different simulation results | Moderate (determine correct values from forcefield docs) |
| ATOM-01 | 🟡 MEDIUM | Hardcoded `// 4` for water atom count in 7+ places; breaks for non-TIP4P models | Moderate (replace with derived value or constant) |
| TREE-01 | 🟡 MEDIUM | KDTree rebuilt every iteration in ion inserter even when no ion placed | Simple (rebuild only on successful placement) |

**Scope decisions:**
- BUG-05, MW-01: Must fix (wrong simulation results)
- RNG-01: Must fix (scientific reproducibility)
- DEFLT-01: Must fix (inconsistent simulation behavior)
- ATOM-01: Should fix (latent maintenance trap)
- TREE-01: Should fix (performance waste)
- GUEST-01 (LOW): Defer — no current molecule misidentified, latent design concern only

**Verification reference:** `.planning/codebase/20260608_ISSUES_VERIFICATION.md`

---

### Phase 34.8: Fix Performance Issues and Test Gaps (INSERTED)

**Goal:** Optimize scorer memory usage (27×→1× via cKDTree boxsize) and close test coverage gaps (moleculetype name matching, diversity_score correctness) to ensure scientific reliability and GROMACS compatibility
**Depends on:** Phase 34.7
**Plans:** 5 plans

Plans:
- [x] 34.8-01-PLAN.md — PERF-02: Optimize scorer memory with cKDTree boxsize (Wave 1)
- [x] 34.8-02-PLAN.md — TEST-09: Add TOP/ITP moleculetype name matching test (Wave 1)
- [x] 34.8-03-PLAN.md — BUG-04: Fix diversity_score with structural fingerprints (Wave 2, depends on 01)
- [x] 34.8-04-PLAN.md — GAP: Update diversity tests for fingerprint behavior (Wave 1 gap closure)
- [x] 34.8-05-PLAN.md — GAP: Fix Ice V cKDTree boxsize float64 edge case (Wave 1 gap closure)

**Details:**

Remaining open issues from `.planning/codebase/CONCERNS.md`:

| ID | Category | Finding | Fix Complexity |
|----|----------|---------|---------------|
| PERF-02 | 🟠 HIGH | Scorer builds 3×3×3 supercell (~650 MB for 100k atoms) instead of using `cKDTree(boxsize=)` like `overlap_resolver.py` already does | Moderate (replace supercell with boxsize param, keep triclinic fallback) |
| BUG-04 | 🟡 MEDIUM | `diversity_score()` always returns 1.0 — provides zero discriminatory value in ranking | Moderate (redesign seed-based diversity metric) |
| TEST-09 | 🟡 MEDIUM | No test verifying `[ molecules ]` names in TOP files match `[ moleculetype ]` names in ITP files — GROMACS fatal error risk | Simple (assert name consistency in exported files) |
| PERF-04 | 🟢 LOW | Nested loops in guest molecule detection — N is small, low impact | Low priority (batch classification possible but not urgent) |
| TEST-03 | 🟢 LOW | Triclinic cell interface tests — currently blocked by design (Ice II rejected at validation) | Deferred (add defensive tests only) |
| TEST-06 | 🟢 LOW | VTK rendering fallback path untested — headless VTK tricky | Deferred (mock-based testing possible) |

**Scope decisions:**
- PERF-02: Must fix (650 MB memory waste for large structures)
- BUG-04: Should fix (ranking has zero diversity discrimination)
- TEST-09: Should fix (GROMACS compatibility regression risk)
- PERF-04, TEST-03, TEST-06: Defer — low priority, blocked, or tricky

**Reference patterns:**
- `overlap_resolver.py:72` already uses `cKDTree(positions, boxsize=box_list)` — copy this pattern for scorer
- Existing e2e test infrastructure in `tests/` provides patterns for TEST-09

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
- [x] 35-06-PLAN.md — Screenshots checkpoint: Rename existing + recapture new (Option 1 decision from f345ca9)
- [x] 35-07-PLAN.md — Quick Task docs: Document Quick Task 017/018 features (concentration input, delete/overlap)

---

### Phase 36: CLI Feature Parity

**Goal:** User can generate all v4.5 structures (solute, custom molecule, ion source selection, interface mode) from CLI with the same capabilities as the GUI
**Depends on:** Phase 35
**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04, CLI-05

**Success Criteria:**
1. User can insert solutes (THF/CH₄) via CLI with concentration input matching GUI Tab 4 behavior
2. User can insert custom molecules via CLI with .gro/.itp file paths matching GUI Tab 3 behavior
3. User can specify ion source (Interface/Custom/Solute) via CLI matching GUI Tab 5 source dropdown
4. User can specify solute source (Interface/Custom Molecule) via CLI matching GUI Tab 4 source dropdown
5. User can run interface generation with all modes (slab/pocket/piece) via CLI

**Details:**
- Extends existing CLI (quickice/cli.py) with v4.5 features
- CLI-01: Solute insertion (--solute-type, --concentration, --solute-source)
- CLI-02: Custom molecule insertion (--custom-gro, --custom-itp, --placement-mode)
- CLI-03: Ion source selection (--ion-source)
- CLI-04: Interface mode CLI support (already partially exists from v3.5)
- CLI-05: Solute source selection (--solute-source)
- Follows existing CLI patterns from Quick Tasks 013/014/015 (hydrate, ion, progress)
- No GUI dependency — purely backend computation + GROMACS export

**Plans:** 11 plans in 9 waves

Plans:
- [x] 36-01-PLAN.md — Parser flags + validation + CSV example (Wave 1)
- [x] 36-02-PLAN.md — ITP path resolvers with case normalization (Wave 1)
- [x] 36-03-PLAN.md — CLIPipeline scaffold with execute(), helpers, stubs (Wave 2)
- [x] 36-04-PLAN.md — ITP copy function with all 6 step cases including hydrate (Wave 2)
- [x] 36-05-PLAN.md — Ice source step + interface step with seed (Wave 3)
- [x] 36-06-PLAN.md — Hydrate source step with HydrateStructure attribute mapping (Wave 4)
- [x] 36-07-PLAN.md — Export step with hydrate→interface wrapper (Wave 5)
- [x] 36-08-PLAN.md — Custom + solute steps with SoluteInserter seed fix (Wave 6)
- [x] 36-09-PLAN.md — Ion step with 3 source modes + guest_atom_count offset (Wave 7)
- [x] 36-10-PLAN.md — main.py wiring (Wave 8)
- [x] 36-11-PLAN.md — CLI integration tests (Wave 9)

---

### Phase 37: Unified Entry Point

**Goal:** User has a single entry point (`python -m quickice`) that launches CLI or GUI mode, and test suite uses consistent invocation patterns
**Depends on:** Phase 36
**Requirements:** No new requirements — tooling improvement for distribution and test consistency

**Success Criteria:**
1. `python -m quickice` with no args shows help (like `git` with no args)
2. `python -m quickice` with computation flags (e.g., `-T 300`) runs CLI mode automatically
3. `python -m quickice --gui` launches GUI when display available; errors gracefully when not
4. `python -m quickice --cli` forces CLI mode, skipping PySide6 import entirely
5. PySide6 not installed → graceful fallback with informative message
6. Test suite uses unified `run_quickice()` helper from conftest.py
7. Existing `python quickice.py` entry point still works (backward compat)

**Details:**
- Create `quickice/__main__.py` + `quickice/entry.py` router (detects CLI flags / display availability)
- Handles missing PySide6 gracefully (headless environments, CLI-only installs)
- Update `quickice.py` to delegate to `entry.main()`
- Update PyInstaller spec for dual-mode binary (`console=True` + `hide_console='hide-late'`)
- Add `--cli`/`--gui` flags to argparse for discoverability
- Normalize test suite invocation (shared `run_quickice()` helper, migrate 4 test files)
- Update all docs from `python quickice.py` → `python -m quickice`
- Resolves pending todo: `.planning/todos/pending/2026-05-09-unify-gui-cli-entry-point.md`
- CLI-only PyInstaller bundle deferred (stays as pending todo)

**Plans:** 20 plans

Plans:
- [x] 37-01-PLAN.md — Create quickice/entry.py (routing logic) [Wave 1]
- [x] 37-02-PLAN.md — Create quickice/__main__.py (3-line stub) [Wave 2]
- [x] 37-03-PLAN.md — Update quickice.py to delegate to entry.main() [Wave 2]
- [x] 37-04-PLAN.md — Update quickice/cli/parser.py (prog, epilog, --cli/--gui) [Wave 1]
- [x] 37-05-PLAN.md — Update quickice-gui.spec (entry point, console flag) [Wave 1]
- [x] 37-06-PLAN.md — Add run_quickice() to tests/conftest.py [Wave 1]
- [x] 37-07-PLAN.md — Create tests/test_entry_point.py (8-10 routing tests) [Wave 3]
- [x] 37-08-PLAN.md — Migrate tests/test_cli_integration.py to run_quickice() [Wave 3]
- [x] 37-09-PLAN.md — Migrate tests/test_cli_pipeline.py to run_quickice() [Wave 4]
- [x] 37-10-PLAN.md — Migrate tests/test_integration_v35.py to run_quickice() [Wave 4]
- [x] 37-11-PLAN.md — Migrate tests/test_phase_mapping.py to run_quickice() [Wave 4]
- [x] 37-12-PLAN.md — Update docs/cli-reference.md — replace all quickice.py refs [Wave 2]
- [x] 37-13-PLAN.md — Update docs/cli-reference.md — add unified entry sections [Wave 5]
- [x] 37-14-PLAN.md — Update docs/flowchart.md [Wave 2]
- [x] 37-15-PLAN.md — Update README.md [Wave 3]
- [x] 37-16-PLAN.md — Update README_bin.md [Wave 3]
- [x] 37-17-PLAN.md — Update setup.sh [Wave 4]
- [x] 37-18-PLAN.md — Backward compat + full integration verification [Wave 5]
- [x] 37-19-PLAN.md — CLI examples script + CLI reference update [Wave 6]
- [x] 37-20-PLAN.md — Hydrate-interface-custom-ion workflow script + doc updates [Wave 6]

---

### Phase 37.1: Fix Verified Scancode Findings (INSERTED)

**Goal:** Fix verified critical/high code bugs (AN-01, AN-02, AN-03, CP-01, UM-01, V-02, V-05), code quality issues (V-07 duplication, V-17 mutation), shared constants (UM-02 water volume, AVOGADRO-DRY), input validation (CP-03, SEC-02), error handling (EH-01, EH-02, EH-05), documentation accuracy (README Ice X/XV/DOI/IAPWS, gui-guide v4.5, cli-reference, help_dialog, parser), and grompp validation tests for CLI pipeline and GUI export paths
**Depends on:** Phase 37
**Plans:** 15 plans in 5 waves

Plans:
- [x] 37.1-01-PLAN.md — Fix data model bugs: AN-01 (atom count), CP-01 (InterfaceStructure fields), UM-01 (AVOGADRO import)
- [x] 37.1-02-PLAN.md — Fix GRO coordinate bugs: AN-02 (MW recomputation), AN-03 (PBC wrapping for solute/custom)
- [x] 37.1-03-PLAN.md — Fix CLI documentation: DOC-C1 (hydrate flags), DOC-C2 (missing pipeline flags), DOC-C3 (exit codes), DOC-C4 (--gromacs no-op)
- [x] 37.1-04-PLAN.md — Fix GUI docs and tooltips: DOC-G1 (tab numbers), DOC-G2 (THF ring), DOC-G3 (overlap tooltip), DOC-G4 (principles diversity)
- [x] 37.1-05-PLAN.md — Add grompp validation tests: GROMPP skipif + hydrate/custom/solute standalone + CLI pipeline grompp
- [x] 37.1-06-PLAN.md — GAP: Add dedicated ### subsections for --no-overwrite, --pocket-shape, and interface flags (DOC-C2 closure)
- [x] 37.1-07-PLAN.md — GAP: Add PBC wrapping integration test for write_ion_gro_file (AN-03 closure)
- [x] 37.1-08-PLAN.md — Fix CRITICAL code bugs: V-02 (cKDTree O(N²) rebuild), V-05 (unknown atoms silently skipped)
- [x] 37.1-09-PLAN.md — Fix HIGH code quality: V-07 (deduplicate detect_atoms_per_molecule), V-17 (stop input structure mutation)
- [x] 37.1-10-PLAN.md — Fix MEDIUM shared constants: UM-02 (WATER_VOLUME_NM3), AVOGADRO-DRY (consolidate 3 definitions)
- [x] 37.1-11-PLAN.md — Fix MEDIUM input validation: CP-03 (concentration/occupancy range), SEC-02 (file path extension)
- [x] 37.1-12-PLAN.md — Fix MEDIUM error handling: EH-01 (GRO file I/O protection), EH-02 (hydrate wrapper assertion), EH-05 (ValueError catch)
- [x] 37.1-13-PLAN.md — Fix documentation accuracy: README (Ice X, Ice XV, DOI, IAPWS, test path), gui-guide, cli-reference, help_dialog, parser
- [x] 37.1-14-PLAN.md — Gap closure: write_interface_gro_file PBC wrapping, --ion-source custom in workflow script
- [x] 37.1-15-PLAN.md — Gap closure: V-03 solute cKDTree conditional rebuild (TestTREE03)

**Details:**

Verified issues from `.planning/code_analysis/20260615_SCAN_VERIFICATION.md` (21 TRUE / 1 FALSE_ALARM / 3 MISLEADING):

| ID | Severity | Category | Finding | Source |
|----|----------|----------|---------|--------|
| AN-01 | 🔴 CRITICAL | Code | `MOLECULE_TYPE_INFO["ice"]["atoms"] = 3` should be 4 | vulnerability_scan |
| AN-02 | 🔴 CRITICAL | Code | MW recomputed on 4-atom hydrate ice, overwrites correct MW | vulnerability_scan |
| AN-03 | 🟠 HIGH | Code | `write_ion_gro_file` writes solute/custom positions without PBC wrapping | vulnerability_scan |
| CP-01 | 🟠 HIGH | Code | Duck-typing attrs on `InterfaceStructure` (solute_positions, custom_molecule_count, etc.) | vulnerability_scan |
| DOC-C1 | 🟠 HIGH | Docs | 7 hydrate CLI examples missing required `-T`/`-P` flags | doc_crosscheck_cli |
| DOC-C2 | 🟠 HIGH | Docs | 18 v4.5 pipeline flags missing from `docs/cli-reference.md` | doc_crosscheck_cli |
| DOC-G1 | 🟠 HIGH | Docs | Interface tooltips use wrong tab numbers (Tab 1→0, Tab 3→1) | doc_crosscheck_gui |
| GROMPP | 🟠 HIGH | Tests | GUI + CLI export paths have 0 grompp validation tests | grompp_test_coverage |
| DOC-C3 | 🟡 MEDIUM | Docs | Exit codes table wrong in CLI reference | doc_crosscheck_cli |
| DOC-C4 | 🟡 MEDIUM | Docs | `--gromacs` is no-op in pipeline mode | doc_crosscheck_cli |
| DOC-G2 | 🟡 MEDIUM | Docs | THF tooltip says "4-membered ring" — it's 5 | doc_crosscheck_gui |
| DOC-G3 | 🟡 MEDIUM | Docs | Custom molecule tooltip says "no overlap checking" but code does check | doc_crosscheck_gui |
| DOC-G4 | 🟡 MEDIUM | Docs | `docs/principles.md` says "rewards unique seeds" — outdated | doc_crosscheck_gui |
| UM-01 | 🟢 LOW | Code | AVOGADRO hardcoded in CLI pipeline instead of shared constant | vulnerability_scan |

**Scope decisions:**
- AN-01, AN-02: Must fix (wrong simulation data)
- AN-03: Must fix (invalid GRO files for solute/custom molecules)
- CP-01: Must fix (fragile duck-typing on dataclass, breaks if `__slots__` added)
- DOC-C1, DOC-C2, DOC-G1: Must fix (user-facing documentation errors)
- GROMPP: Should fix (no grompp validation for CLI or GUI export paths)
- DOC-C3, DOC-C4, DOC-G2–G4: Should fix (accuracy and consistency)
- UM-01: Low priority (values identical, only DRY risk)

**Deferred (not in this phase):**
- Bundle optimization (scipy collect_all, GenIce2 narrowing, CLI-only binary) → separate Phase 38

**Verification reference:** `.planning/code_analysis/20260615_SCAN_VERIFICATION.md`

---

## Milestone Summary

**Phase Count:** 15 (Phases 32-37, with 34.1, 34.2, 34.3, 34.4, 34.5, 34.6, 34.7, 34.8, and 37.1 inserted)

**Total Plans:** 64+ plans (Phase 32: 3, Phase 33: 4, Phase 34: 5, Phase 34.1: 3, Phase 34.2: 2, Phase 34.3: 1, Phase 34.4: 2, Phase 34.5: 3, Phase 34.6: 9, Phase 34.7: 3, Phase 34.8: 5, Phase 35: 7, Phase 36: 11, Phase 37: 20, Phase 37.1: 15, e2e-compute-export: 11, completed: 64/64+)

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

**Note:** CLI requirements (CLI-01 to CLI-05) now in Phase 36 of this milestone.

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
| 34.6 - Revise Custom Panel for Valid Input | ✓ Complete | 9 | 9 |
| 34.7 - Fix Verified Scancode Bugs | ✓ Complete | 3 | 3 |
| 34.8 - Fix Performance Issues and Test Gaps | ✓ Complete | 5 | 5 |
| 35 - Integration & Documentation | ✓ Complete | 7 | 7 |
| 36 - CLI Feature Parity | ✓ Complete | 11 | 11 |
| 37 - Unified Entry Point | ✓ Complete | 20 | 20 |
| 37.1 - Fix Verified Scancode Findings | ✓ Complete | 15 | 15 |
| e2e-export-test - E2E GROMACS Export Testing | ✓ Complete | 8 | 8 |
| e2e-api-workflow - E2E API Workflow Testing | ✓ Complete | 5 | 5 |
| e2e-compute-export - E2E Compute→Export Bridge Testing | ✓ Complete | 11 | 11 |

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

**Plans:** 11 plans in 7 waves
- [x] e2e-compute-export-01-PLAN.md — (Wave 1) Shared helpers module + Ice/Interface single-structure export (16 tests)
- [x] e2e-compute-export-02-PLAN.md — (Wave 2) Custom + Solute single-structure export (21 tests + 3 bugfixes)
- [x] e2e-compute-export-03-PLAN.md — (Wave 2) Ion single-structure export + ITP baseline (28 tests + bugfix)
- [x] e2e-compute-export-04-PLAN.md — (Wave 3) Full chain export F1-F4 (26 tests + bugfix)
- [x] e2e-compute-export-05-PLAN.md — (Wave 3) Simple chain export F5-F7 + cross-chain invariants (25 tests)
- [x] e2e-compute-export-06-PLAN.md — (Wave 4) Fix 3 GROMACS-simulation bugs in TOP writers + grompp validation helpers
- [x] e2e-compute-export-07-PLAN.md — (Wave 4) GROMACS grompp validation tests: ice, interface, F1-F7 (8 tests)
- [x] e2e-compute-export-08-PLAN.md — (Wave 5) Missing grompp cross-combinations: F2, F1+THF, F3+THF, F4+CH4 (4 tests)
- [x] e2e-compute-export-09-PLAN.md — (Wave 6) sII hydrate grompp validation: sII helpers + F3-sII, F4-sII (2 tests)
- [x] e2e-compute-export-10-PLAN.md — (Wave 7) Test output cleanup script (scripts/clean-test-output.sh)
- [x] e2e-compute-export-11-PLAN.md — (Wave 1 gap closure) Molecule-type presence assertions in grompp tests

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
*Last updated: 2026-06-15 - Phase 37.1 inserted (Fix Verified Scancode Findings)*
*For current state, see .planning/STATE.md*
