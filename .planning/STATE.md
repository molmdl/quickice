# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface
**Current Focus:** e2e-compute-export phase — bridging computation pipeline with GROMACS export validation

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-05)

**Core value:** Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface

**Current focus:** e2e-compute-export — E2E compute-export bridge testing (Plan 01 of 05 complete)

**Tech stack:**
- PySide6 6.10.2 (LGPL, MIT-compatible)
- VTK 9.5.2 (BSD-licensed)
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | e2e-compute-export |
| Phase | e2e-compute-export (E2E Compute-Export Bridge Testing) |
| Plan | 3 of 5 complete |
| Status | In progress — Plans 01+03 complete (44 tests), Plans 02+04+05 pending |
| Last activity | 2026-06-03 — Completed e2e-compute-export-03 (Ion export + ITP baseline tests) |

**Progress:** ████████░░ 80% (160/192 plans across all milestones + e2e-compute-export)

---

## Milestone History

### e2e-api-workflow E2E API Workflow Testing (COMPLETE)

**Phases:** 5 plans (01-05)
**Purpose:** End-to-end API-level tests for QuickIce v4.5 UAT workflows 2-9
**Progress:** All 5 plans complete
**Key deliverables:**
- ✓ Shared conftest.py with 12 module-scoped real generation fixtures (Plan 01)
- ✓ 12 ice generation e2e tests covering all 6 orthogonal phases (Plan 01)
- ✓ 16 hydrate generation e2e tests covering sI/sII × CH4/THF + error handling (Plan 01)
- ✓ Interface generation e2e tests covering slab/pocket/piece + hydrate→interface + Ice II rejection + error handling (Plan 02)
- ✓ Custom molecule e2e tests covering validation + random/custom placement + edge cases (Plan 03)
- ✓ Solute insertion e2e tests covering Interface/Custom sources, CH4_H/CH4_L coexistence (P0), THF 13-atom, zero concentration, attribute propagation (Plan 04)
- ✓ Ion insertion e2e tests (14 tests) + P0 SoluteStructure→IonInserter AttributeError bug exposure + charge neutrality + attribute propagation (Plan 05)
- ✓ Workflow chain e2e tests (12 tests) covering F1–F7 chains + structural invariants + CH4_H/CH4_L distinction (Plan 05)

### v4.5 Solute & Custom Molecule Insertion (IN PROGRESS)

**Phases:** 32-35 (6 phases planned)
**Requirements:** 39 total (ARCH: 7, SOLUTE: 9, CUSTOM: 12, VIS: 3, GROMACS: 3, DOCS: 5)
**Progress:** Phase 32-34.6 complete, Phase 35 pending (37 requirements satisfied, 2 pending)
**Key features in progress:**
- ✓ Tab index constants and MoleculetypeRegistry
- ✓ ITP parser and molecule validator
- ✓ TabIndex refactoring complete
- ✓ Solute insertion tab (Tab 4) with THF/CH₄ concentration placement
- ✓ All-atom overlap checking for multi-atom molecules
- ✓ Ball-and-stick rendering with CPK colors
- ✓ Custom molecule validation infrastructure (GRO residue extraction)
- ✓ Custom molecule renderer with distinct colors (purple, cyan, yellow)
- ✓ Custom molecule insertion logic (CustomMoleculeInserter with two placement modes)
- ✓ Custom molecule upload tab (Tab 3) UI components (CustomMoleculePanel, CustomMoleculeWorker, CustomMoleculeViewerWidget)
- ✓ Tab reordering complete (Ion moves to Tab 6)
- ✓ GROMACS export with custom .itp bundling
- ✓ Integration tests for custom molecule workflow
- ✓ Unified export keyboard shortcut (Ctrl+S)
- ✓ Molecule ordering verification tests
- ✓ Ion source dropdown with charge warning
- ✓ Liquid solute ITP files with CH4_LIQ/THF_LIQ names
- ✓ Export pipeline uses correct ITP files for liquid solutes
- ✓ Tab order swapped (Custom→Tab 3, Solute→Tab 4) enabling Custom→Solute workflow
- ✓ Solute source dropdown with Interface/Custom Molecule selection
- ✓ Help dialog updated with Tab 0-5 numbering and workflows
- ✓ Placement validation with single-molecule preview (Phase 34.5)
- ✓ Semi-transparent preview rendering for proposed positions
- ✓ Validation UI with "Validate & Preview" button
- ✓ Generic residue name suppression for real molecule files (Phase 34.6-01)
- ✓ Liquid region bounds display for Custom mode (Phase 34.6-02)
- ✓ Volume preview and molecule count estimate for Random mode (Phase 34.6-02)
- ✓ Integration tests for Phase 34.6 bug fixes (Phase 34.6-03)
- ✓ Complete system export for Custom Molecule tab (Phase 34.6-04 to 34.6-08)
- ✓ Comprehensive integration tests with 10 tests covering complete system (Phase 34.6-08)
- ✓ Phase 34.5/34.6 feature documentation in GUI guide (Phase 35-06)
- ✓ Quick Task 017/018 documentation (concentration input, delete/overlap) (Phase 35-07)
- ⏳ Screenshots and release notes (Phase 35-06 deferred)

**Roadmap:** [.planning/ROADMAP.md](./ROADMAP.md)

### e2e-export-test E2E GROMACS Export Testing (COMPLETE)

**Phases:** 8 plans (01-08)
**Purpose:** End-to-end tests for the GROMACS export pipeline across all 6 tabs
**Progress:** All 8 plans complete
**Key deliverables:**
- ✓ Shared conftest.py with 13 fixtures covering all 6 structure types (Plan 01)
- ✓ Ice candidate export tests — 5 tests for GROMACSExporter (Plan 02)
- ✓ Hydrate structure export tests — 5 tests for HydrateGROMACSExporter + registry case bugfix (Plan 03)
- ✓ Interface structure export tests (Plan 04)
- ✓ Custom molecule export tests — 5 tests for CustomMoleculeGROMACSExporter + shutil bugfix (Plan 05)
- ✓ Solute export tests — 5 tests for SoluteGROMACSExporter (Plan 06)
- ✓ Ion export tests — 7 tests for IonGROMACSExporter + Madrid2019 validation (Plan 07)
- ✓ Cross-tab chain export tests — 4 tests for full pipeline (Plan 08)

### e2e-api-workflow E2E API Workflow Testing (COMPLETE)

**Phases:** 5 plans (01-05)
**Purpose:** API-level end-to-end tests for the computation pipeline catching logic bugs before human UAT
**Progress:** All 5 plans complete
**Key deliverables:**
- ✓ Shared conftest.py with 12 module-scoped fixtures for real GenIce2 generation (Plan 01)
- ✓ Ice generation tests — 12 tests covering all 6 orthogonal phases (Plan 01)
- ✓ Hydrate generation tests — 16 tests covering sI/sII × CH4/THF (Plan 01)
- ✓ Interface generation tests — 21 tests for slab/pocket/piece modes, Ice II rejection (Plan 02)
- ✓ Custom molecule tests — 20 tests for validation, random/custom placement (Plan 03)
- ✓ Solute insertion tests — 17 tests for Interface/Custom sources, CH4_H/CH4_L coexistence (Plan 04)
- ✓ Ion insertion + workflow chain tests — 26 tests, P0 bug I5 exposed, F1-F7 chains (Plan 05)
- ✓ Total: 112 e2e tests, 7/7 must-haves verified, all pass in ~13s

### e2e-compute-export E2E Compute-Export Bridge Testing (IN PROGRESS)

**Phases:** 5 plans (01-05)
**Purpose:** Bridge tests validating real GenIce2 computation pipeline output flows correctly through GROMACS writer functions
**Progress:** Plans 01+03 complete (44 tests), Plans 02+04+05 pending
**Key deliverables:**
- ✓ Shared e2e_export_helpers.py with 6 parsing functions + 9 chain-building helpers + 2 constants (Plan 01)
- ✓ 6 Ice Candidate export tests — GRO SOL-only, atom count, TOP molecules, inline [moleculetype], ITP existence, atom conservation (Plan 01)
- ✓ 4 Interface (no guests) export tests — GRO SOL-only, atom count, TOP molecules, #include (Plan 01)
- ✓ 6 Interface+Hydrate Guest export tests — SOL before guests, atom count, TOP molecules+guests, #include hydrate ITP, ITP existence, no interleaving (Plan 01)
- ✓ 6 Ion from Interface export tests — SOL→NA→CL, atom count, TOP molecules, #include, ITP validation, charge neutrality (Plan 03)
- ✓ 7 Ion from Custom export tests — SOL→MOL→NA→CL, atom count, TOP molecules, #include, ITP validation, custom count preserved, charge neutrality (Plan 03)
- ✓ 7 Ion from Solute export tests — SOL→CH4_L→NA→CL, atom count, TOP molecules, #include, ITP validation, solute info preserved, charge neutrality + BUG I5 workaround (Plan 03)
- ✓ 8 ITP baseline validation tests — 6 data ITPs exist with [moleculetype], ion.itp NA+CL generation, no duplicate moleculetype names (Plan 03)
- ✓ IonInserter custom_molecule_positions propagation fix for Custom→Ion workflow (Plan 03)
- ✓ Total: 44 bridge tests, 10/10 must-haves verified

### pocket-edge-tests Pocket Mode Edge Cases (COMPLETE)

**Phases:** 3 plans (01-03)
**Purpose:** Add FRAG-02 assertions, comprehensive edge-case tests, and fix cubic guest removal bug
**Progress:** All 3 plans complete
**Key deliverables:**
- ✓ FRAG-02 assertions in pocket.py after each overlap removal phase (Plan 01)
- ✓ 11 invariant tests across 4 classes (sphere, cubic, extremes, rectangular) (Plan 01)
- ✓ 33 edge case tests across 5 classes (shapes, sizes, geometry, invariants, hydrate) (Plan 02)
- ✓ Cubic pocket guest removal bug fix (shape-aware distance criterion) (Plan 03)
- ✓ 7 cubic guest tests across 3 classes (cubic removal, sphere regression, corner bug) (Plan 03)

### v4.0 Molecule Insertion (SHIPPED 2026-05-01)

**Phases:** 28-31.2 (7 phases, 29 plans, 4 inserted decimal phases)
**Requirements:** 19 satisfied, 11 deferred to v4.5, 3 pending
**Key features delivered:**
- Hydrate generation (sI, sII, sH with CH4/THF guests)
- Dual-style 3D rendering (water lines, guest ball-and-stick)
- Ion insertion (Na+/Cl- with Madrid2019 parameters)
- Multi-molecule GROMACS export
- Four-tab workflow (Ice, Hydrate, Interface, Ion)

**Archive:** [.planning/milestones/v4.0-ROADMAP.md](./milestones/v4.0-ROADMAP.md)

### v3.5 Interface Enhancements (SHIPPED 2026-04-13)

**Phases:** 22, 24-27 shipped; Phase 23 deferred
**Requirements:** 11 shipped, 4 deferred (WATER-01 to WATER-04)
**Key features delivered:**
- Ice Ih IAPWS density (temperature-dependent, replaces 0.9167 g/cm³)
- Native triclinic handling (Ice V, Ice VI work; Ice II blocked)
- CLI interface generation (--interface flag with full parameters)
- Crystal system documentation corrected

**Deferred:**
- Water density integration (Tab 1 display, Tab 2 interface spacing)

**Archive:** [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)

### v3.0 Interface Generation (Shipped 2026-04-11)

**Phases:** 16-21 (6 phases, 15 plans)
**Key features:**
- Tab infrastructure: Ice Generation + Interface Construction tabs
- Configuration controls: mode, boxsize, thickness, seed inputs
- Structure generation: slab/pocket/piece modes with collision detection
- Visualization: phase-distinct coloring in single VTK viewer
- Export: GROMACS files with phase distinction (single SOL)

**Archive:** [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)

### v2.1.1 Phase Diagram Data Update (Shipped 2026-04-08)

**Phase:** 15 (9 plans)
**Archive:** [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)

### v2.1 GROMACS Export (Shipped 2026-04-07)

**Phases:** 14 (8 plans)
**Archive:** [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)

### v2.0 GUI Application (Shipped 2026-04-04)

**Phases:** 8-13 (28 plans)
**Archive:** [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)

### v1.1 Hotfix (Shipped 2026-03-31)

**Archive:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

### v1.0 MVP (Shipped 2026-03-29)

**Archive:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

---

## Accumulated Context

### Roadmap Evolution

- Phase 34.1 inserted after Phase 34: Ion Source Dropdown with charge warning (URGENT)
- Phase 34.2 inserted after Phase 34.1: Fix liquid solute ITP export with proper residue names (URGENT)
- Phase 34.3 inserted after Phase 34.2: Tab order swap (Custom→Tab 4, Solute→Tab 5) to enable Custom→Solute workflow (URGENT)
- Phase 34.4 inserted after Phase 34.3: Solute source dropdown to complete Custom→Solute workflow (URGENT) — ✓ Complete
- Phase 34.5 inserted after Phase 34.4: Placement validation & preview enhancement (URGENT) — ✓ Complete
- Phase 34.6 inserted after Phase 34.5: Revise custom panel for valid input handling with real molecule testing (URGENT)

### v4.5 Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| TabIndex enum for tab positions | Prevents hardcoded index bugs after reordering | ✓ Shipped (32-01) |
| MoleculetypeRegistry for molecule tracking | Unique GROMACS naming (CH4_H vs CH4_L) | ✓ Shipped (32-01) |
| ITP parser with regex parsing | Extracts molecule info from .itp files without dependencies | ✓ Shipped (32-01) |
| Molecule validator with specific errors | GRO/ITP consistency validation with clear user feedback | ✓ Shipped (32-02) |
| TabIndex enum for all indices | All hardcoded tab indices replaced with named constants | ✓ Shipped (32-02) |
| Optional registry parameter | Backward-compatible GROMACS export with future registry support | ✓ Shipped (32-02) |
| Tab structure documentation | Current and planned tab order documented in code | ✓ Shipped (32-03) |
| Cross-tab data flow verification | Verified Ice→Interface, Hydrate→Interface, Interface→Ion | ✓ Shipped (32-03) |
| Solute renderer follows hydrate pattern | Consistency with existing ball-and-stick rendering | ✓ Shipped (33-02) |
| All-atom overlap checking | Multi-atom molecules need full overlap check (not center-of-mass) | ✓ Shipped (33-01) |
| Rotation matrices for molecule orientation | Multi-atom molecules have orientation | ✓ Shipped (33-01) |
| SoluteViewerWidget extends QWidget | GenericViewerWidget doesn't exist, follows IonViewerWidget pattern | ✓ Shipped (33-03) |
| Real-time preview on valueChanged | User sees molecule count update while typing concentration | ✓ Shipped (33-03) |
| Concentration range 0.0-2.0 M | Based on typical solute concentrations | ✓ Shipped (33-03) |
| GAFF2 parameters for THF/CH₄ solutes | Consistent with hydrate guest parameters | ✓ Shipped (33-01) |
| GRO residue name extraction | Fixed-width column parsing (cols 6-10) | ✓ Shipped (34-01) |
| Residue name mismatch as non-blocking | Triggers UI dialog for user choice | ✓ Shipped (34-01) |
| Custom molecule distinct colors | Purple, cyan, yellow to differentiate from predefined molecules | ✓ Shipped (34-03) |
| Custom molecule renderer follows solute pattern | Consistency with ball-and-stick rendering, same bond threshold | ✓ Shipped (34-03) |
| CustomMoleculeConfig two-mode pattern | Random/custom placement with validation | ✓ Shipped (34-01) |
| Euler angles for custom rotation | ZXZ convention via scipy Rotation.from_euler | ✓ Shipped (34-02) |
| Two placement modes | Random (with overlap checking) and custom (user responsibility) | ✓ Shipped (34-02) |
| InsertionError for placement failures | Provides attempt count for user feedback | ✓ Shipped (34-02) |
| User-provided [ atomtypes ] required | Avoids force field database complexity | ⏳ Planned |
| Euler angles for UI input | More intuitive than rotation matrices | ✓ Shipped (34-04) |
| Separate file upload buttons | User can upload .gro and .itp files separately | ✓ Shipped (34-04) |
| Residue name mismatch dialog | ITP name override option for user choice | ✓ Shipped (34-04) |
| Placement mode dropdown | Dynamic controls for Random vs Custom mode | ✓ Shipped (34-04) |
| Unified Ctrl+S export | Qt standard "Save" action for active tab export | ✓ Shipped (35-01) |
| Hydrate shortcut Ctrl+H | More intuitive than Ctrl+E (H for hydrate) | ✓ Shipped (35-01) |
| Export As... submenu | Tab-specific exports for discoverability | ✓ Shipped (35-01) |
| Molecule ordering tests | Verification via .gro file parsing | ✓ Shipped (35-01) |
| Ion source dropdown follows Interface pattern | Consistency in source selection UI across tabs | ✓ Shipped (34.1-01) |
| Source change handler with immediate UI effect | Real-time feedback, not deferred to Generate time | ✓ Shipped (34.1-02) |
| Charge warning for Custom Molecule source | Non-neutral charge detection for custom molecules | ✓ Shipped (34.1-02) |
| Ion configuration always neutral | Equal Na+/Cl- with Madrid2019 charges (±0.85) | ✓ Shipped (34.1-02) |
| Manual QApplication setup for tests | Avoids pytest-qt dependency, matches project pattern | ✓ Shipped (34.1-03) |
| Comprehensive test coverage (11 tests) | Exceeds minimum 8 tests for better coverage | ✓ Shipped (34.1-03) |
| Hydrate shortcut Ctrl+H | More intuitive than Ctrl+E (H for hydrate) | ✓ Shipped (35-01) |
| Export As... submenu | Tab-specific exports for discoverability | ✓ Shipped (35-01) |
| Molecule ordering tests | Verification via .gro file parsing | ✓ Shipped (35-01) |
| Separate liquid solute ITP files | CH4_LIQ and THF_LIQ distinct from hydrate guests | ✓ Shipped (34.2-01) |
| Liquid solute ITP export logic | Exporters use {type}_liquid.itp for solutes | ✓ Shipped (34.2-02) |
| Copy-existing-ITP pattern | Preserve force field parameters exactly | ✓ Shipped (34.2-01) |
| Tab order swap (Custom before Solute) | Enables Custom → Solute → Ion workflow chain | ✓ Shipped (34.3-01) |
| Solute source dropdown | Enables source selection for solute insertion | ✓ Shipped (34.4-01) |
| Solute source dropdown follows Ion pattern | Consistency in source selection UI across tabs | ✓ Shipped (34.4-01) |
| Custom Molecule source uses _current_interface_result | CustomMoleculeStructure doesn't store interface_structure field | ✓ Shipped (34.4-02) |
| Tooltip depth varies by audience | Detailed formula for scientific users (solute), brief guidance + doc reference for technical users (custom molecule) | ✓ Shipped (35-02) |
| HelpIcon widgets for consistency | GRO/ITP upload buttons have help icons for guidance | ✓ Shipped (35-02) |
| Help dialog reflects accurate v4.5 structure | Tab 0-5 numbering, complete workflows, updated shortcuts | ✓ Shipped (35-03) |
| GUI guide workflow documentation | Step-by-step instructions with prerequisites and outcomes | ✓ Shipped (35-05) |
| GRO/ITP guide tutorial-focused approach | Practical examples and three creation methods | ✓ Shipped (35-05) |
| README GUI-focused for v4.5 | 333 lines with concise feature overview, correct tab numbering | ✓ Shipped (35-04) |
| Placement validation logic | Read-only bounds and overlap checking for custom molecules | ✓ Shipped (34.5-01) |
| Semi-transparent preview rendering | Opacity 0.6 for visual distinction before insertion | ✓ Shipped (34.5-02) |
| Validation UI integration | Validate & Preview button with signal-slot wiring | ✓ Shipped (34.5-03) |
| Single-molecule validation approach | Validate ONE molecule at a time (O(M) cost) not full system (O(N×M) cost) | ✓ Shipped (34.5-01) |
| Read-only validation method | validate_single_placement() does not modify MoleculetypeRegistry | ✓ Shipped (34.5-01) |
| PlacementValidationResult dataclass | Structured validation feedback with bounds, overlap, distance info | ✓ Shipped (34.5-01) |
| Use parse_gro_file() directly | Non-existent CustomMoleculeLoader in plan; use established pattern instead | ✓ Shipped (34.5-03) |
| Validate button only in Custom mode | Validation meaningful only for user-specified position/rotation | ✓ Shipped (34.5-03) |
| CustomMoleculeStructure complete system | Follows IonStructure pattern with ice/water/custom atom counts | ✓ Shipped (34.6-04) |
| Store interface_structure reference | Enables Custom → Solute workflow chaining | ✓ Shipped (34.6-04) |
| MoleculeIndex for all molecule types | Consistent tracking across ice, water, custom molecules | ✓ Shipped (34.6-04) |
| Complete system assembly pattern | CustomMoleculeInserter combines interface + custom atoms | ✓ Shipped (34.6-05) |
| Molecule tracking via MoleculeIndex | Handles variable atoms per molecule (ice:4, water:4, custom:var) | ✓ Shipped (34.6-05) |
| Custom Molecule source for both tabs | Pass CustomMoleculeStructure to both SolutePanel and IonPanel | ✓ Shipped (34.6-07) |
| Dual workflow path support | Interface→Custom→Solute→Ion AND Interface→Custom→Ion | ✓ Shipped (34.6-07) |
| Custom molecule complete system export | CustomMoleculeGROMACSExporter exports ice + water + custom | ✓ Shipped (34.6-06) |
| Writer functions follow ion pattern | Consistency with IonGROMACSExporter for complete system export | ✓ Shipped (34.6-06) |
| Real molecule files for testing | etoh.gro/etoh.itp provide realistic integration test cases | ✓ Shipped (34.6-08) |
| Both workflow paths tested | Custom → Solute → Ion AND Custom → Ion direct | ✓ Shipped (34.6-08) |
| MoleculeIndex per molecule tracking | One entry per molecule with start_idx and atom count | ✓ Shipped (34.6-08) |
| Qt offscreen for headless testing | QT_QPA_PLATFORM=offscreen for CI environments | ✓ Shipped (34.6-08) |
| No QApplication fixture for export tests | Exporters only use static QFileDialog/QMessageBox calls, fully mocked | ✓ Shipped (e2e-export-test-01) |
| Factory pattern for mock dialog fixtures | Returns (path, dialog_patch, mb_patch) tuple for test flexibility | ✓ Shipped (e2e-export-test-01) |
| custom_structure uses etoh.itp | Points to existing file rather than creating temp files | ✓ Shipped (e2e-export-test-01) |
| ITP filename uses .gro stem | ice_test.gro → ice_test.itp, NOT tip4p-ice.itp | ✓ Shipped (e2e-export-test-02) |
| Mock dialog pattern validated | (save_path, dialog_patch, mb_patch) works for GROMACSExporter | ✓ Shipped (e2e-export-test-02) |
| SoluteGROMACSExporter nested access validated | interface_structure accessed for guest detection without AttributeError | ✓ Shipped (e2e-export-test-06) |
| Solute liquid ITP atomtypes commented | comment_out_atomtypes_in_itp() applied to solute ITP files | ✓ Shipped (e2e-export-test-06) |
| Conditional custom ITP in solute export | custom_molecule_count > 0 AND positions AND itp_path exists | ✓ Shipped (e2e-export-test-06) |
| TIP4P-ICE 3→4 expansion confirmed | nmolecules * 4 atoms (OW,HW1,HW2,MW), not nmolecules * 3 | ✓ Shipped (e2e-export-test-02) |
| Hydrate mock path differs from other exporters | QFileDialog in quickice.gui.hydrate_export, NOT quickice.gui.export | ✓ Shipped (e2e-export-test-03) |
| Registry keys must use uppercase mol_type | register_hydrate_guest('CH4') stores hydrate_CH4; write_multi_molecule_top_file must use .upper() for lookup | ✓ Shipped (e2e-export-test-03) |
| Custom ITP keeps original filename in output | etoh.itp stays etoh.itp (not stem-based like ice exporter) | ✓ Shipped (e2e-export-test-05) |
| comment_out_atomtypes_in_itp is read-only on source | Source ITP never modified; only output copy has [atomtypes] commented | ✓ Shipped (e2e-export-test-05) |
| Custom exporter needs import shutil in try block | Bug: CustomMoleculeGROMACSExporter used shutil.copy without import (other exporters have it) | ✓ Shipped (e2e-export-test-05) |
| ion.itp is GENERATED via write_ion_itp() | Distinct from other ITPs that are copied from data directory | ✓ Shipped (e2e-export-test-07) |
| solute_molecule_indices relative to solute_positions | (start, end) tuples index into solute_positions/solute_atom_names, NOT main positions array | ✓ Shipped (e2e-export-test-07) |
| IonStructure carries forward ALL conditional data | guest_nmolecules, solute_*, custom_molecule_* all accessible from IonStructure for cumulative ITP export | ✓ Shipped (e2e-export-test-08) |
| Chain E2E test validates cumulative file sets | Each pipeline level produces ALL previous ITPs plus its own additions | ✓ Shipped (e2e-export-test-08) |
| Full chain produces 5 ITP files | tip4p-ice.itp + ion.itp + ch4_hydrate.itp + ch4_liquid.itp + etoh.itp | ✓ Shipped (e2e-export-test-08) |
| Minimal chain produces 2 ITP files | tip4p-ice.itp + ion.itp only when no guests/solutes/custom | ✓ Shipped (e2e-export-test-08) |
| FRAG-02 assertions in pocket.py | Water count % 4 == 0 and atom_names == positions after each overlap removal | ✓ Shipped (pocket-edge-tests-01) |
| Shape-aware guest removal | Cubic pockets use cubic criterion; sphere uses Euclidean; unknown falls back to Euclidean | ✓ Shipped (pocket-edge-tests-03) |
| Test files in flat tests/ directory | Avoids name collision with tests/test_structure_generation.py | ✓ Shipped (pocket-edge-tests) |
| 12 fixtures (not 8) in e2e conftest | Added 4 raw HydrateStructure fixtures for hydrate-specific tests needing molecule_index | ✓ Shipped (e2e-api-workflow-01) |
| PHASE_CONDITIONS dict in conftest | Shared T/P mapping prevents duplication across test files | ✓ Shipped (e2e-api-workflow-01) |
| Fractional coordinate tolerance 0.01 | GenIce numerical rounding may place atoms slightly outside [0, L) | ✓ Shipped (e2e-api-workflow-01) |
| cKDTree for test overlap verification | Reuses scipy.spatial for efficient nearest-neighbor queries in test assertions | ✓ Shipped (e2e-api-workflow-03) |
| tmp_path for temporary GRO/ITP test files | pytest built-in fixture for per-test temporary directories; no cleanup needed | ✓ Shipped (e2e-api-workflow-03) |
| 0.2 nm COM bounds tolerance | Molecules extend beyond center-of-mass; tolerance allows edge placements near liquid boundary | ✓ Shipped (e2e-api-workflow-03) |
| Interface molecule counts over molecule_index | InterfaceStructure.molecule_index is empty after generate_interface(); downstream inserters build it. Tests verify ice_nmolecules+water_nmolecules+guest_nmolecules consistency | ✓ Shipped (e2e-api-workflow-02) |
| Inline fixtures for Ice Ic, Ice II, piece | Not in shared conftest; module-scoped inline keeps conftest clean | ✓ Shipped (e2e-api-workflow-02) |
| Ice II generated at 200K/300MPa | Confirmed via lookup_phase; GenIce2 supports generation, validate_interface_config rejects | ✓ Shipped (e2e-api-workflow-02) |
| Register hydrate guest before solute insertion in tests | Simulates real workflow where hydrate export registers guests first; SoluteInserter creates its own registry so hydrate guest must be registered manually before insert_solutes() | ✓ Shipped (e2e-api-workflow-04) |
| Inline THF hydrate interface for S4 test | conftest.py only has CH4 hydrate fixture; THF hydrate generated inline to avoid fixture explosion | ✓ Shipped (e2e-api-workflow-04) |
| THF_ATOMS_PER_MOLECULE=13 and CH4_ATOMS_PER_MOLECULE=5 as module constants | Avoids magic numbers in test assertions; matches MOLECULE_TYPE_INFO in types.py | ✓ Shipped (e2e-api-workflow-04) |
| Solute→Ion workaround helper _solute_to_ion_source() | Encapsulates I5 bug workaround (attach solute attrs to interface_structure); matches GUI behavior | ✓ Shipped (e2e-api-workflow-05) |
| guest_atom_count > 0 for F4 chain instead of guest_nmolecules > 0 | CustomMoleculeStructure lacks guest_nmolecules field; guest_atom_count IS preserved. Known limitation. | ✓ Shipped (e2e-api-workflow-05) |
| Custom molecule count+atom_count verification, not positions | CustomMoleculeStructure doesn't have custom_molecule_positions; uses molecule_index to track custom molecules | ✓ Shipped (e2e-api-workflow-05) |
| sys.path.insert for e2e_export_helpers import | pytest doesn't auto-add tests/ to sys.path; conftest import is unreliable | ✓ Shipped (e2e-compute-export-01) |
| Alpha-char filter for GRO residue parsing | Box vector lines have numeric-only content in [5:10] columns; prevent false positive residue names | ✓ Shipped (e2e-compute-export-01) |
| write_top_file uses inline [moleculetype] not #include | Older ice candidate writer writes full SOL definition inline; only interface+ writers use #include | ✓ Shipped (e2e-compute-export-01) |
| IonInserter extracts custom_molecule_positions from molecule_index | CustomMoleculeStructure stores custom molecules in shared positions with molecule_index entries, not separate custom_molecule_positions; IonInserter now extracts from molecule_index when getattr returns None | ✓ Shipped (e2e-compute-export-03) |
| Custom molecule residue name is MOL (from etoh.itp) | etoh.itp defines moleculetype as "MOL", not "ETOH"; write_ion_gro_file uses custom_molecule_moleculetype from moleculetype_name | ✓ Shipped (e2e-compute-export-03) |
| molecule_index-derived SOL counts for IonStructure | Ion insertion replaces water molecules, reducing SOL count; use ion.molecule_index counts not original interface counts | ✓ Shipped (e2e-compute-export-03) |
| ion.itp must be pre-generated before TOP write | write_ion_top_file #includes "ion.itp" which must exist in output directory; ion.itp is generated by write_ion_itp(), not copied from data/ | ✓ Shipped (e2e-compute-export-03) |

### v4.0 Key Decisions (Shipped)

| Decision | Rationale | Status |
|----------|-----------|--------|
| MoleculeIndex dataclass | Variable atoms-per-molecule tracking | ✓ Shipped |
| HydrateConfig/HydrateLatticeInfo | Configuration management | ✓ Shipped |
| Madrid2019 ion parameters | Scientifically validated charges (±0.85) | ✓ Shipped |
| GAFF2 guest parameters | CH4/THF topology for GROMACS | ✓ Shipped |
| Dual-style hydrate rendering | Water lines + guest ball-and-stick | ✓ Shipped |
| Concentration-based ion placement | mol/L → ion count calculation | ✓ Shipped |
| Per-type VTK actors | Multi-molecule visualization | ✓ Shipped |
| Tab order: Ice→Hydrate→Interface→Ion | User-approved deviation | ✓ Shipped |

### Blockers

**Phase 34.6 status:**
- ✓ 34.6-01 (validation warnings and button state) complete
- ✓ 34.6-02 (liquid bounds and volume preview) complete
- ✓ 34.6-03 (integration tests) complete
- ✓ 34.6-04 (CustomMoleculeStructure complete system) complete
- ✓ 34.6-05 (CustomMoleculeInserter complete system) complete
- ✓ 34.6-06 (custom molecule complete system export) complete
- ✓ 34.6-07 (Custom Molecule source for Solute and Ion) complete
- ✓ 34.6-08 (comprehensive integration tests) complete
- **Phase 34.6 COMPLETE!**

**Phase 35 documentation plans status:**
- ✓ 35-01 (unified export) complete
- ✓ 35-02 (tooltips) complete  
- ✓ 35-03 (help dialog) complete with correct tab numbering (Tab 0-5)
- ✓ 35-04 (README update) complete
- ✓ 35-05 (GUI guide & user guides) complete
- ⏳ 35-06 partial (Phase 34.5/34.6 feature docs complete, screenshots deferred)

**Phase 34.5 status:**
- ✓ 34.5-01 (validation logic) complete
- ✓ 34.5-02 (preview rendering) complete
- ✓ 34.5-03 (validation UI) complete

**Phase 34.6 status:**
- ✓ Complete! All 8 plans executed successfully

**Remaining Phase 35 work:**
- Screenshots recapture (35-06 checkpoint pending)
  - **Decision:** Option 1 (Rename existing + recapture new) — confirmed from commit f345ca9
  - Rename 5 existing files (remove tabX prefix)
  - Capture 6 new screenshots (Tabs 3-4, Phase 34.5/34.6 features)
  - See 35-06-SUMMARY.md for detailed steps
- Release notes preparation (pending)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 028 | Fix hydrate guest naming _HYD→_H with hydrate-specific ITP files | 2026-05-16 | 52c73e5 | [028-hydrate-naming-fix](./quick/028-hydrate-naming-fix/) |
| 027 | Fix exception handling across 5 files (logging, UI feedback, tracebacks) | 2026-05-16 | 719de7f | [027-fix-exception-handling](./quick/027-fix-exception-handling/) |
| 026 | Add Madrid2019 ion parameter citation to documentation | 2026-05-16 | cfc5286 | [026-add-madrid2019-citation](./quick/026-add-madrid2019-citation/) |
| 025 | Fix HydrateStructureGenerator docstring (guest molecule accuracy) | 2026-05-16 | 6defeed | [025-fix-hydrate-guest-docstring](./quick/025-fix-hydrate-guest-docstring/) |
| 024 | Clarify ice phases documentation (detection vs generation) | 2026-05-16 | 89c7efd | [024-clarify-ice-phases-documentation](./quick/024-clarify-ice-phases-documentation/) |
| 023 | UPX compression feasibility check (investigation) | 2026-05-16 | 2c51ae3 | [023-check-upx-compression-feasibility](./quick/023-check-upx-compression-feasibility/) |
| 022 | Optimize H-bond detection with KDTree | 2026-05-16 | d4a333e | [022-optimize-hbond-detection-kdtree](./quick/022-optimize-hbond-detection-kdtree/) |
| 021 | Remove unused build_molecule_index function | 2026-05-16 | 187368f | [021-remove-unused-build-molecule-index](./quick/021-remove-unused-build-molecule-index/) |
| 020 | Version bump to 4.5.0 | 2026-05-16 | bb9d9ed | [020-version-bump-4.5](./quick/020-version-bump-4.5/) |
| 019 | Remove old custom molecule preview system | 2026-05-10 | b7c1452 | [019-remove-old-custom-preview](./quick/019-remove-old-custom-preview/) |
| 018 | Custom molecule delete and overlap detection | 2026-05-10 | a9f9bb5 | [018-custom-mol-delete-and-overlap](./quick/018-custom-mol-delete-and-overlap/) |
| 017 | Add concentration input to Custom Molecule random mode | 2026-05-10 | 4a4bb6b | [017-custom-mol-concentration-input](./quick/017-custom-mol-concentration-input/) |
| 016 | ❌ REVERTED: Minimize bundle dependencies (broke executable) | 2026-05-04 | N/A (reverted) | [016-minimize-bundle-dependencies](./quick/016-minimize-bundle-dependencies/) |
| 008 | Optimize PyInstaller bundle size | 2026-05-03 | deae8b8 | [008-optimize-pyinstaller-bundle-size](./quick/008-optimize-pyinstaller-bundle-size/) |
| 007 | Code quality improvements (logging, deduplication, validation) | 2026-05-02 | 886ce83 | [007-code-quality-improvements-logging-dedu](./quick/007-code-quality-improvements-logging-dedu/) |
| 006 | Add GAFF2 preparation method citation to main documentation | 2026-04-30 | f319157 | [006-add-gaff2-preparation-method-citation-to](./quick/006-add-gaff2-preparation-method-citation-to/) |

### Pending Todos

- [2026-05-24] Pre-built small molecules for custom mol with GROMACS format (feature) — `.planning/todos/pending/2026-05-24-pre-built-small-molecules-gromacs.md`
- [2026-05-16] Install UPX for bundle compression (tooling) — `.planning/todos/pending/2026-05-16-install-upx-for-bundle-compression.md`
- [2026-05-07] Capture screenshots per Phase 35 suggestions (docs) — `.planning/todos/pending/2026-05-07-capture-screenshots-per-phase-35-suggestions.md`
- [2026-05-09] Unify GUI/CLI entry point into single executable (tooling) — `.planning/todos/pending/2026-05-09-unify-gui-cli-entry-point.md`
- [2026-05-09] Provide CLI-only executable for automation (tooling) — `.planning/todos/pending/2026-05-09-cli-only-executable-for-automation.md`
- [2026-05-09] Support flexible interface construction modes (feature) — `.planning/todos/pending/2026-05-09-flexible-interface-construction.md`
- [2026-05-09] Explore complex hydrate formation using atomsk (research) — `.planning/todos/pending/2026-05-09-complex-hydrate-formation-atomsk.md`

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v2.1.1: [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)
- v3.0: [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)
- v3.5: [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)
- v4.0: [.planning/milestones/v4.0-ROADMAP.md](./milestones/v4.0-ROADMAP.md)

---

## Session Continuity

**Last session:** 2026-06-03
**Completed:** e2e-compute-export-03 (Ion export + ITP baseline tests: 28 tests)
**Status:** e2e-compute-export Plans 01+03 of 05 complete.

**e2e-compute-export Phase Progress:**
- ✓ 01: Shared e2e_export_helpers.py (6 parsing + 9 chain-building helpers) + Ice/Interface export tests (16 total)
- ⏳ 02: Hydrate candidate export tests (pending)
- ✓ 03: Ion export tests (3 sources: Interface/Custom/Solute + BUG I5 workaround) + ITP baseline validation (28 total)
- ⏳ 04: Solute export tests (pending)
- ⏳ 05: Ion + full chain export tests (pending)

**Next session:**
- Continue e2e-compute-export phase with Plan 02 or Plan 04
- Key findings from Plan 03: Custom molecule residue name is MOL (not ETOH), IonInserter now propagates custom_molecule_positions from CustomMoleculeStructure's molecule_index, SOL count must use ion.molecule_index (not original interface counts), ion.itp must be generated before TOP write
- BUG I5 workaround confirmed working for Solute→Ion pathway
- ⚠ Uncommitted gromacs_writer.py changes from Plan 02 exist in working tree

---
*State updated: 2026-06-03 — e2e-compute-export Plan 03 complete (28 bridge tests, IonInserter custom propagation fix)*
