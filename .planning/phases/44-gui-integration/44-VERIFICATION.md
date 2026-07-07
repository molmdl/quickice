---
phase: 44-gui-integration
verified: 2026-07-07T13:10:02Z
status: passed
score: 8/8 must-haves verified
must_haves:
  truths:
    - "User can upload a .gro file and a .itp file from the Hydrate tab via two QFileDialog buttons"
    - "User sees specific validation error messages when the uploaded pair is invalid (residue name too long, wrong comb-rule, unparseable GRO)"
    - "User sees a green success indicator when the uploaded pair is valid"
    - "User can assign the uploaded custom guest to a cage type via the per-cage combo (Custom: {residue} option appears after a valid upload)"
    - "User can set occupancy for the custom guest in that cage"
    - "User can mix custom guest in one cage + built-in guest in another cage (GUI-06 custom path, no crash)"
    - "The same custom guest cannot be assigned to two cages simultaneously (auto-clear mitigation prevents Pitfall 6 ValueError)"
    - "Generating a hydrate with a custom guest assignment succeeds (the engine, already built in Phases 40/42, handles the HydrateConfig the GUI builds)"
  artifacts:
    - path: "quickice/gui/hydrate_panel.py"
      provides: "Custom guest upload QGroupBox + per-cage Custom option + custom CageGuestAssignment construction + Pitfall 6 mitigation"
      contains: "_create_custom_guest_group"
    - path: "tests/test_hydrate_panel.py"
      provides: "TestCustomGuestUpload class with headless offscreen fixture"
      contains: "class TestCustomGuestUpload"
  key_links:
    - from: "quickice/gui/hydrate_panel.py::_upload_custom_gro/_upload_custom_itp"
      to: "quickice/structure_generation/custom_guest_bridge.py::validate_custom_guest_files"
      via: "lazy import inside handler + call with (gro_path, itp_path, guest_type)"
      pattern: "validate_custom_guest_files\\("
    - from: "quickice/gui/hydrate_panel.py::_try_validate_custom_guest"
      to: "quickice/structure_generation/gro_parser.py::parse_gro_file"
      via: "lazy import inside handler, called only when result.is_valid, to get atom_names"
      pattern: "parse_gro_file\\("
    - from: "quickice/gui/hydrate_panel.py::_rebuild_cage_rows"
      to: "per-cage QComboBox items"
      via: "if self._custom_guest is not None: combo.addItem(f\"Custom: {residue}\", guest_type)"
      pattern: "Custom:"
    - from: "quickice/gui/hydrate_panel.py::get_configuration"
      to: "quickice/structure_generation/types.py::CageGuestAssignment (custom path)"
      via: "guest_id not in GUEST_MOLECULES -> CageGuestAssignment(guest_type, occupancy, guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count)"
      pattern: "CageGuestAssignment\\("
    - from: "quickice/gui/hydrate_panel.py (Pitfall 6 mitigation)"
      to: "per-cage combos"
      via: "selecting Custom in a second cage auto-clears the first cage back to a built-in before get_configuration runs"
      pattern: "setCurrentIndex"
---

# Phase 44: GUI Integration Verification Report

**Phase Goal:** All new hydrate features are accessible from the Hydrate tab with validation feedback
**Verified:** 2026-07-07T13:10:02Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can upload a .gro file and a .itp file from the Hydrate tab via two QFileDialog buttons | ✓ VERIFIED | `_create_custom_guest_group` (hydrate_panel.py:235) creates `cg_gro_button` ("Upload .gro File") wired to `_upload_custom_gro` (line 294) which calls `QFileDialog.getOpenFileName` (line 296); `cg_itp_button` ("Upload .itp File") wired to `_upload_custom_itp` (line 306) which calls `QFileDialog.getOpenFileName` (line 308). Test `test_valid_upload_populates_custom_guest_and_adds_combo_option` passes. |
| 2 | User sees specific validation error messages when the uploaded pair is invalid (residue name too long, wrong comb-rule, unparseable GRO) | ✓ VERIFIED | `_try_validate_custom_guest` (line 332) lazy-imports `validate_custom_guest_files` (line 362) and on `not result.is_valid` sets `cg_validation_label` red with `"\n".join(result.errors)` (lines 370-373) — reuses the canonical engine validator (GUI-05 exact messages, never reimplemented). 3 tests confirm: `test_invalid_combrule1_shows_specific_error_and_keeps_none` (wrong comb-rule), `test_invalid_not_a_gro_shows_parse_error` (unparseable GRO), `test_invalid_long_resname_shows_specific_error` (residue name too long). |
| 3 | User sees a green success indicator when the uploaded pair is valid | ✓ VERIFIED | On valid upload, `cg_validation_label` set to `"✓ Custom guest validated: {residue} ({count} atoms)"` with `"color: green;"` (lines 412-416). Test `test_valid_upload_populates_custom_guest_and_adds_combo_option` asserts green. User also manually confirmed green validation label. |
| 4 | User can assign the uploaded custom guest to a cage type via the per-cage combo (Custom: {residue} option appears after a valid upload) | ✓ VERIFIED | `_rebuild_cage_rows` (line 450) appends `f"Custom: {self._custom_guest['residue_name']}"` to every per-cage combo when `self._custom_guest is not None` (lines 496-500); called after valid upload (line 417). Test confirms. User manually confirmed "Custom: MOL" appears in every per-cage combo. |
| 5 | User can set occupancy for the custom guest in that cage | ✓ VERIFIED | Each per-cage row has a `QDoubleSpinBox` (0-100%) stored in `self._cage_occupancy_spins[cage_key]` (lines 510-519). `get_configuration` reads `occ = self._cage_occupancy_spins[cage_key].value()` (line 750) and passes it to `CageGuestAssignment(occupancy=occ, ...)` for the custom path (line 757). Test `test_get_configuration_round_trips_custom_in_one_cage` confirms. |
| 6 | User can mix custom guest in one cage + built-in guest in another cage (GUI-06 custom path, no crash) | ✓ VERIFIED | `get_configuration` builds per-cage `CageGuestAssignment` independently (lines 748-767) — custom path for cages with `guest_id not in GUEST_MOLECULES`, built-in path for others. Test `test_get_configuration_round_trips_custom_in_one_cage` confirms mixed 1-custom + 1-builtin round-trips. User manually verified mixed MOL-large + ch4-small generates + exports valid GROMACS (grompp PASSED, 3.0 nm box, .top has #include etoh.itp + [molecules] MOL_H 6 + CH4_H 2 + SOL 46). |
| 7 | The same custom guest cannot be assigned to two cages simultaneously (auto-clear mitigation prevents Pitfall 6 ValueError) | ✓ VERIFIED | `_enforce_single_custom_cage` (line 636) called on every per-cage combo change via `_on_cage_guest_changed` (line 631). If `len(cages_with_custom) > 1`, resets every other cage to index 0 via `setCurrentIndex(0)` (line 667). Per-cage combos routed through `_on_cage_guest_changed` via lambda capturing `cage_key` by default arg (lines 504-506). Test `test_pitfall6_auto_clears_second_cage` confirms. |
| 8 | Generating a hydrate with a custom guest assignment succeeds (the engine, already built in Phases 40/42, handles the HydrateConfig the GUI builds) | ✓ VERIFIED | `get_configuration` builds fully-populated custom `CageGuestAssignment` with all 6 metadata fields (lines 755-763: guest_type, occupancy, guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count). Test `test_get_configuration_round_trips_custom_in_one_cage` confirms `HydrateConfig(...)` accepts the custom assignment without raising. User manually verified full generate + export + grompp pipeline PASSED. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `quickice/gui/hydrate_panel.py` | Custom guest upload QGroupBox + per-cage Custom option + custom CageGuestAssignment construction + Pitfall 6 mitigation; contains `_create_custom_guest_group` | ✓ VERIFIED | EXISTS (815 lines, SUBSTANTIVE). `_create_custom_guest_group` at line 235. All 9 new methods present: `_create_custom_guest_group`, `_upload_custom_gro`, `_upload_custom_itp`, `_derive_guest_type_slug`, `_try_validate_custom_guest`, `_on_cage_guest_changed`, `_enforce_single_custom_cage`; extended `_rebuild_cage_rows` (line 450) and `get_configuration` (line 734). Dead `_on_guest_changed` removed (only docstring mentions at lines 462, 628 remain). WIRED: called in `_setup_ui` at line 78 between lattice group (line 72) and cage group (line 83). No stubs, no empty returns. |
| `tests/test_hydrate_panel.py` | TestCustomGuestUpload class with headless offscreen fixture; contains `class TestCustomGuestUpload` | ✓ VERIFIED | EXISTS (359 lines, SUBSTANTIVE). `class TestCustomGuestUpload` at line 228 with 7 tests (lines 246, 267, 276, 284, 294, 306, 332). Helpers `_upload_valid_pair` (line 189) and `_make_long_resname_gro` (line 202) present. Imports `from pathlib import Path` (line 20) + `QMessageBox` (line 23). No stubs, no skips, no empty test bodies. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `_upload_custom_gro` / `_upload_custom_itp` | `validate_custom_guest_files` | lazy import inside handler + call with (gro_path, itp_path, guest_type) | ✓ WIRED | Lazy import INSIDE `_try_validate_custom_guest` body at lines 362-364 (NOT top-level). Called at line 365 with `(self._cg_gro_path, self._cg_itp_path, guest_type)`. Result used (line 369 `if not result.is_valid`). |
| `_try_validate_custom_guest` | `parse_gro_file` | lazy import inside handler, called only when result.is_valid, to get atom_names | ✓ WIRED | Lazy import INSIDE handler body at line 392 (NOT top-level). Called at line 393 ONLY after `result.is_valid` check passes (line 369 returns early on invalid). Response used: `_, atom_names, _ = parse_gro_file(...)` → stored in `self._custom_guest['atom_labels']` (line 409). |
| `_rebuild_cage_rows` | per-cage QComboBox items | `if self._custom_guest is not None: combo.addItem(f"Custom: {residue}", guest_type)` | ✓ WIRED | Lines 496-500: conditional append of "Custom: {residue}" item with `guest_type` as item data. Called after valid upload (line 417) and on invalid upload (line 375 to remove stale option). |
| `get_configuration` | `CageGuestAssignment` (custom path) | `guest_id not in GUEST_MOLECULES -> CageGuestAssignment(guest_type, occupancy, guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count)` | ✓ WIRED | Lines 751-763: branch `if guest_id not in GUEST_MOLECULES and self._custom_guest is not None` builds `CageGuestAssignment` with all 7 fields (guest_type, occupancy, guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count). Built-in path at lines 765-767 supplies only guest_type + occupancy. |
| Pitfall 6 mitigation | per-cage combos | selecting Custom in a second cage auto-clears the first cage back to a built-in before get_configuration runs | ✓ WIRED | `_enforce_single_custom_cage` (line 636) called from `_on_cage_guest_changed` (line 631), which is wired to every per-cage combo via lambda (lines 504-506). Uses `setCurrentIndex(0)` (line 667) to reset other cages. Recursion terminates because reset cage no longer has custom guest. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| GUI-01: Hydrate tab lattice dropdown includes all new lattice types (filled ices + Ice XVI/XVII + sT') | ✓ SATISFIED | None. `HYDRATE_LATTICES` has 10 entries: `['sI', 'sII', 'sH', 'c0te', 'c1te', 'c2te', 'ice1hte', 'sTprime', '16', '17']`. Lattice dropdown iterates `HYDRATE_LATTICES.items()` (hydrate_panel.py:187). (Delivered in 39-04.) |
| GUI-02: Hydrate tab has custom guest upload panel (.gro + .itp file pair selection) | ✓ SATISFIED | None. `_create_custom_guest_group` (line 235) with two QFileDialog buttons. (Delivered in 44-02.) |
| GUI-03: Hydrate tab has cage-type guest assignment controls (small/large/medium → guest type) | ✓ SATISFIED | None. `_cage_guest_combos` + `_cage_occupancy_spins` (lines 436-437) populated by `_rebuild_cage_rows` (line 450), one row per `cage_type_map` key. (Delivered in 42-06.) |
| GUI-04: Hydrate tab has depol mode dropdown (strict/optimal) | ✓ SATISFIED | None. `depol_combo` QComboBox with "Strict (ice rules, zero net dipole)" + "Optimal (relaxed)" (lines 218-220), strict as default (first item). `get_configuration` passes `depol_mode=self.depol_combo.currentData()` (line 774). (Delivered in 43-02.) |
| GUI-05: Custom guest upload shows validation errors with specific messages (name too long, wrong comb-rule, unparseable) | ✓ SATISFIED | None. `_try_validate_custom_guest` reuses `validate_custom_guest_files` (the canonical engine validator) and surfaces `result.errors` in red. 3 tests confirm specific messages. (Delivered in 44-02.) |
| GUI-06: Hydrate tab mixed occupancy shows per-cage-type guest type and occupancy controls | ✓ SATISFIED | None. Per-cage rows (42-06) + custom-per-cage option (44-02). Test `test_get_configuration_round_trips_custom_in_one_cage` confirms mixed custom+builtin. (Built-in path 42-06; custom path 44-02.) |

### Phase Success Criteria (from ROADMAP.md)

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Hydrate tab lattice dropdown includes all new lattice types (filled ices + Ice XVI/XVII + sT') | ✓ VERIFIED | `HYDRATE_LATTICES` = 10 types incl. c0te/c1te/c2te (filled ices) + '16'/'17' (Ice XVI/XVII) + sTprime. Dropdown iterates `HYDRATE_LATTICES.items()` (line 187). |
| 2 | User can upload a custom guest .gro+.itp pair from the Hydrate tab and see specific validation errors (name too long, wrong comb-rule, unparseable) | ✓ VERIFIED | Two QFileDialog buttons (lines 296, 308) + `validate_custom_guest_files` reuse + red error label. 3 invalid-upload tests pass. |
| 3 | Hydrate tab has cage-type guest assignment controls (small/large/medium → guest type) for mixed occupancy | ✓ VERIFIED | Per-cage rows built by `_rebuild_cage_rows` from `cage_type_map`; `_cage_guest_combos` + `_cage_occupancy_spins` (lines 436-437, 518-519). |
| 4 | Hydrate tab has depol mode dropdown (strict/optimal) with strict as default | ✓ VERIFIED | `depol_combo` (line 218) with strict as first item (default); `test_depol_combo_default_is_strict` passes. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | — | — | None found. Scan for TODO/FIXME/XXX/HACK/placeholder/not implemented/coming soon/lorem ipsum/return null/return {}/return []/empty handlers yielded ZERO matches in both modified files. No skipped tests, no empty test bodies. |

### Constraints Verification (per AGENTS.md / 44-02 PLAN)

| Constraint | Status | Evidence |
| --- | --- | --- |
| No NEW top-level engine imports in hydrate_panel.py (lazy imports only) | ✓ VERIFIED | `rg "^from quickice.structure_generation|^import quickice.structure_generation" quickice/gui/hydrate_panel.py` shows ONLY the pre-existing `from quickice.structure_generation.types import (...)` (lines 21-24). `validate_custom_guest_files` and `parse_gro_file` are lazy-imported INSIDE `_try_validate_custom_guest` body (lines 362-364, 392). NO new custom_guest_bridge/gro_parser/itp_parser top-level imports. |
| No engine files modified by Phase 44-02 | ✓ VERIFIED | `git show --stat a259fee` → only `quickice/gui/hydrate_panel.py`. `git show --stat 1b4b25e` → only `tests/test_hydrate_panel.py`. `git show --stat 59225fe` → only `.planning/STATE.md` + `44-02-SUMMARY.md`. `git diff ea772ea..HEAD -- quickice/structure_generation/{custom_guest_bridge,gro_parser,itp_parser,types}.py` → EMPTY. |
| QFileDialog + QMessageBox added to existing QtWidgets import block (not separate line) | ✓ VERIFIED | Lines 13-18: single `from PySide6.QtWidgets import (...)` block includes `QFileDialog, QMessageBox` at line 17. No separate import line. |
| `from pathlib import Path` added | ✓ VERIFIED | Line 11. |
| Dead `_on_guest_changed` removed (SUMMARY claim) | ✓ VERIFIED | No `def _on_guest_changed` in file. Only docstring mentions at lines 462, 628 referencing the "legacy `_on_guest_changed` flow" as context. |

### Test Execution

| Suite | Result |
| --- | --- |
| `QT_QPA_PLATFORM=offscreen pytest tests/test_hydrate_panel.py -v` | **17 passed in 1.42s** (6 cage-row + 4 depol + 7 custom-guest-upload) |
| `QT_QPA_PLATFORM=offscreen pytest tests/test_hydrate_panel.py tests/test_hydrate_config_custom.py tests/test_custom_guest_bridge.py` | **49 passed in 1.00s** — no regressions across hydrate panel + hydrate config custom + custom guest bridge |

### Human Verification Required

The user has ALREADY completed manual verification of the human-checkpoint items (44-02 PLAN Task 3). Recorded here for completeness:

| # | Test | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Panel renders between lattice and cage groups (visual) | ✓ User-verified | User confirmed checkpoint item 2. |
| 2 | Valid upload → green validation label + "Custom: MOL" in every per-cage combo | ✓ User-verified | User confirmed checkpoint item 3. |
| 3 | Mixed MOL-large + ch4-small generates + exports valid GROMACS | ✓ User-verified | User confirmed checkpoint item 6: grompp PASSED, 3.0 nm box, .top has `#include etoh.itp` + `[molecules] MOL_H 6 + CH4_H 2 + SOL 46`, .gro residues SOL/CH4_H/MOL_H all ≤5 chars. |
| 4 | Specific validation errors for 3 invalid fixtures | ✓ Covered by headless tests | `test_invalid_combrule1_shows_specific_error_and_keeps_none`, `test_invalid_not_a_gro_shows_parse_error`, `test_invalid_long_resname_shows_specific_error`. |
| 5 | No-atomtypes warning + upload succeeds | ✓ Covered by headless tests | `test_no_atomtypes_warning_shown_but_upload_succeeds`. |
| 6 | Pitfall 6 auto-clear | ✓ Covered by headless tests | `test_pitfall6_auto_clears_second_cage`. |
| 7 | Lattice-change rebuild | ✓ Covered by headless tests | `test_lattice_change_rebuilds_rows` (42-06). |

No outstanding human verification items remain.

### Out-of-Scope Items (NOT counted as Phase 44 gaps)

| Item | Scope | Rationale |
| --- | --- | --- |
| Custom guest hydrate → Interface tab → export is broken (`to_candidate` drops custom descriptors; `export_interface_gromacs` doesn't thread `custom_guest_info`; old `_detect_guest_type_from_structure` heuristic returns None for custom) | Future urgent cross-tab phase | Phase 44 goal is "Hydrate tab" only. User explicitly noted this is OUT OF SCOPE and will be addressed in a future cross-tab phase. |
| Pitfall 6 same-custom-in-all-cages not allowed (engine validation at types.py:712 checks `guest_residue_name` duplication without distinguishing same-guest-type from different-guest-type-same-name) | Future engine phase | The auto-revert (`_enforce_single_custom_cage`) is the 44-02 GUI-side mitigation. The engine fix to relax Pitfall 6 is explicitly out of scope per the 44-02 PLAN (42-01 design decision). KNOWN LIMITATION, not a gap. |

### Gaps Summary

**No gaps found.** All 8 observable truths verified. Both required artifacts pass all three levels (exists, substantive, wired). All 5 key links wired correctly with lazy imports inside handler bodies (no top-level engine imports). All 6 requirements (GUI-01 through GUI-06) satisfied. All 4 phase success criteria verified. No anti-patterns, no stubs, no skipped tests. 17/17 hydrate_panel tests pass; 49/49 across the three related suites pass (no regressions). No engine files modified by the 44-02 commits (GUI-only changes, as required). The user has already completed manual verification of the human-checkpoint items, including a full generate + export + grompp pipeline run that PASSED.

Phase 44 goal — "All new hydrate features are accessible from the Hydrate tab with validation feedback" — is achieved.

---

_Verified: 2026-07-07T13:10:02Z_
_Verifier: OpenCode (gsd-verifier)_
