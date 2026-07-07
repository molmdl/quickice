---
phase: 44-gui-integration
plan: 02
subsystem: ui
tags: [pyside6, gui, custom-guest, hydrate, qfiledialog, validation, pitfall6]

# Dependency graph
requires:
  - phase: 42-gui-cage-rows
    provides: Per-cage QComboBox + QDoubleSpinBox row infrastructure (_rebuild_cage_rows, _cage_guest_combos, _cage_occupancy_spins) that 44-02 extends with a Custom option
  - phase: 40-custom-guest-bridge
    provides: validate_custom_guest_files (canonical 7-step GRO+ITP validator) + parse_gro_file — reused, NOT reimplemented
  - phase: 42-01-cage-guest-assignment
    provides: CageGuestAssignment dataclass + HydrateConfig.__post_init__ explicit path (incl. Pitfall 6 duplicate-residue-name rejection)
  - phase: 43-02-depol-combo
    provides: depol_combo QGroupBox style template that _create_custom_guest_group mirrors
provides:
  - Custom guest upload QGroupBox in the Hydrate tab (two QFileDialog buttons + status labels + validation label)
  - _try_validate_custom_guest reusing validate_custom_guest_files (GUI-05 exact engine messages)
  - "Custom: {residue}" per-cage combo option added by _rebuild_cage_rows when a valid pair is loaded
  - get_configuration custom CageGuestAssignment branch (full metadata: guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count)
  - Pitfall 6 mitigation (_enforce_single_custom_cage): selecting custom in a second cage auto-clears the first back to ch4
  - 7 headless TestCustomGuestUpload tests (valid upload, 3 invalid uploads, no-atomtypes warning, get_configuration round-trip, Pitfall 6 auto-clear)
affects: [45-cli-integration, 47-filled-ice-grompp, 48-help-restructure]

# Tech tracking
tech-stack:
  added: []  # no new deps — QFileDialog + QMessageBox already in PySide6 6.10.2
  patterns:
    - "Lazy engine imports inside GUI handler bodies (validate_custom_guest_files, parse_gro_file) per AGENTS.md — no top-level quickice.structure_generation imports in hydrate_panel.py"
    - "Single shared custom-guest upload slot (QFileDialog pair) -> _custom_guest descriptor dict -> per-cage combo option; re-upload overwrites the slot entirely"
    - "Pitfall 6 mitigation via auto-clear (restrict custom to one cage) rather than try/except wrap — 42-01 design decision, engine fix out of scope"

key-files:
  created: []
  modified:
    - quickice/gui/hydrate_panel.py
    - tests/test_hydrate_panel.py

key-decisions:
  - "Fixed 'custom_gui' slug for the guest_type (single-occupancy slot; re-upload overwrites _custom_guest entirely; audit_name accepts ^[A-Za-z0-9-_]+$)"
  - "Pitfall 6 mitigation = auto-clear second cage back to ch4 (NOT try/except wrap); 42-01 design decision — _H hydrate path does not disambiguate residue names, so an engine fix is out of scope for 44-02"
  - "Reuse validate_custom_guest_files (NEVER reimplement) — GUI-05 requires the exact engine error messages"
  - "Call parse_gro_file AFTER validation succeeds to get atom_names (validator does NOT return atom_labels — Pitfall 3)"
  - "Removed dead _on_guest_changed (zero callers after re-routing per-cage combo signals through _on_cage_guest_changed)"
  - "Long-resname test fixture uses fixed-width column replacement (cols 5-9) not naive src.replace — naive replace shifts GRO columns and fails the parser before the 'exceeds 3 chars' validator step fires (Rule 1 deviation from plan's helper)"

patterns-established:
  - "Custom guest upload panel: QGroupBox + two QFileDialog buttons + status QLabels + word-wrapped validation QLabel (gray/black/green/red) — mirrors custom_molecule_panel.py style"
  - "Per-cage combo change routes through _on_cage_guest_changed(cage_key) via lambda (captures cage_key by default arg) so the Pitfall 6 mitigation runs on every change"
  - "Bypass-QFileDialog test helper (_upload_valid_pair) sets _cg_gro_path/_cg_itp_path directly + calls _try_validate_custom_guest — same validation path as the handlers, headless-safe"

# Metrics
duration: 5 min
completed: 2026-07-07
---

# Phase 44 Plan 02: Custom Guest Upload Panel Summary

**Custom guest upload QGroupBox in the Hydrate tab reusing validate_custom_guest_files (GUI-05 exact messages) + per-cage "Custom: {residue}" option + Pitfall 6 auto-clear mitigation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-07T10:25:44Z
- **Completed:** 2026-07-07T10:31:34Z (Tasks 1-2; Task 3 checkpoint reached)
- **Tasks:** 2/3 complete (Task 3 is a human-verify checkpoint awaiting user approval)
- **Files modified:** 2

## Accomplishments
- Added a "Custom Guest (optional)" QGroupBox between the Hydrate Lattice and Cage Guest Assignment groups, with two QFileDialog upload buttons (.gro / .itp), status labels, and a word-wrapped validation label surfacing the canonical engine messages (GUI-02 + GUI-05)
- Extended the 42-06 per-cage row infrastructure so every per-cage combo gains a "Custom: {residue}" option after a valid upload, and get_configuration builds a fully-populated custom CageGuestAssignment (unblocking GUI-06 custom-per-cage path)
- Implemented Pitfall 6 mitigation: selecting the custom guest in a second cage auto-clears the first back to ch4, preventing the ValueError: Duplicate guest_residue_name crash from HydrateConfig.__post_init__
- Added 7 headless TestCustomGuestUpload tests covering valid upload, 3 invalid-upload error messages, the no-atomtypes warning, the get_configuration round-trip (mixed 1-custom + 1-builtin), and the Pitfall 6 auto-clear

## Task Commits

Each task was committed atomically:

1. **Task 1: Custom guest upload panel + per-cage wiring + Pitfall 6 mitigation** - `a259fee` (feat)
2. **Task 2: Headless tests for custom guest upload** - `1b4b25e` (test)
3. **Task 3: Human-verify checkpoint** - _awaiting user approval_ (not yet committed)

**Plan metadata:** _pending — will be committed by the continuation agent after the checkpoint is approved (`docs(44-02): complete custom guest upload plan`).

## Files Created/Modified
- `quickice/gui/hydrate_panel.py` - Added _create_custom_guest_group, _upload_custom_gro, _upload_custom_itp, _try_validate_custom_guest, _derive_guest_type_slug, _on_cage_guest_changed, _enforce_single_custom_cage; extended _rebuild_cage_rows (Custom option + lambda connect) and get_configuration (custom CageGuestAssignment branch); removed dead _on_guest_changed; added QFileDialog + QMessageBox to widgets import + from pathlib import Path
- `tests/test_hydrate_panel.py` - Added TestCustomGuestUpload class (7 tests) + _upload_valid_pair + _make_long_resname_gro helpers; added from pathlib import Path + QMessageBox to imports

## Decisions Made
- **Fixed "custom_gui" slug** for the guest_type (single-occupancy slot; re-upload overwrites _custom_guest entirely; the generator only registers what's in cage_guest_assignments, so no sys.modules collision; audit_name accepts ^[A-Za-z0-9-_]+$ and is already called inside validate_custom_guest_files step 7). The ITP-moleculetype-name-derived slug was also valid but adds complexity for no benefit in a single-slot design.
- **Pitfall 6 mitigation = auto-clear second cage** (NOT try/except wrap in main_window.py:742,748). Rationale: 42-01 design decision — the _H hydrate path does not disambiguate residue names, so an engine fix to relax Pitfall 6 is out of scope for 44-02. Auto-clear is the simplest, zero-crash approach and still satisfies GUI-06 (mixed 1-custom + 1-builtin works perfectly — verified: has_custom_assignment=True, no error). The most-recently-changed cage keeps the custom guest; every other cage with the custom guest reverts to index 0 (ch4). The auto-clear IS the feedback (no dialog).
- **Reuse validate_custom_guest_files** (NEVER reimplement) — GUI-05 requires the exact engine error messages (e.g. "ITP comb-rule must be 2 ... got comb-rule=1", "Failed to parse GRO file ...: list index out of range", "Custom guest residue name 'ETHAN' (5 chars) exceeds 3 chars ...").
- **Call parse_gro_file AFTER validation succeeds** to get atom_names (the validator does NOT return atom_labels — Pitfall 3). For a single-molecule custom-guest GRO, atom_names IS guest_atom_labels.
- **Removed dead _on_guest_changed** for cleanliness (grep-verified zero callers after re-routing per-cage combo signals through _on_cage_guest_changed; the method was prefixed with _ so removal breaks no public API contract).
- **Long-resname test fixture uses fixed-width column replacement** (cols 5-9, 0-indexed, 5 chars wide) not naive src.replace("MOL", "ETHAN"). Rule 1 deviation: the plan's naive helper would shift every subsequent GRO column by 2 chars (ETHAN is 5 chars vs MOL is 3), making the GRO unparseable ("could not convert string to float") before the validator's "exceeds 3 chars" step 4 check could fire — failing the test's intent. Fixed the helper to replace exactly the residue-name field so the validator's step-4 check fires as the plan intended.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed long-resname test helper to preserve GRO fixed-width columns**
- **Found during:** Task 2 (Headless tests for custom guest upload)
- **Issue:** The plan's `_make_long_resname_gro` helper used naive `src.replace("MOL", "ETHAN")` to create a 5-char residue-name GRO. But "ETHAN" (5 chars) replaces "MOL" (3 chars) and shifts every subsequent GRO column by 2 chars. The GRO parser's fixed-width column slicing (line[10:15] for atom name, line[20:28] for x coordinate) then reads misaligned data and fails with "could not convert string to float: ' 1   0.2'" — BEFORE the validator's step-4 "exceeds 3 chars" check can fire. The test `test_invalid_long_resname_shows_specific_error` would therefore fail its assertions ("exceeds 3 chars" and "ETHAN" not in the error message).
- **Fix:** Rewrote `_make_long_resname_gro` to replace exactly the residue-name field (columns 5-9, 0-indexed, 5 chars wide) in every atom line with "ETHAN", preserving the alignment of all subsequent columns. Verified the validator now returns the intended error: `"Custom guest residue name 'ETHAN' (5 chars) exceeds 3 chars. GRO format allows 5-char residue names; QuickIce reserves 2 chars for the '_H' hydrate suffix. Use a residue name of 3 chars or fewer (e.g. 'MOL')."`
- **Files modified:** tests/test_hydrate_panel.py (the `_make_long_resname_gro` helper)
- **Verification:** `test_invalid_long_resname_shows_specific_error` passes — asserts "exceeds 3 chars" and "ETHAN" both appear in the validation label text + "red" in the stylesheet.
- **Committed in:** 1b4b25e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for the long-resname test to actually exercise the intended validation path. No scope creep — the test's intent (assert the "exceeds 3 chars" error) is unchanged; only the helper's implementation was corrected.

## Issues Encountered
None — the engine validator, GRO parser, CageGuestAssignment dataclass, and per-cage row infrastructure all behaved as documented in the 44-RESEARCH.md findings. The fixed-width column replacement was the only surprise (a test-helper implementation detail, not an engine issue).

## User Setup Required
None — no external service configuration required. The custom guest upload panel uses only in-repo bundled fixtures (quickice/data/custom/etoh.gro + etoh.itp + test_invalid/*) for tests, and user-provided .gro/.itp files at runtime via QFileDialog.

## Next Phase Readiness
- **Task 3 (human-verify checkpoint) is awaiting user approval.** The headless tests pass (17/17 in tests/test_hydrate_panel.py; 49/49 across hydrate_panel + hydrate_config_custom + custom_guest_bridge — no regression). The user should launch the GUI (`python -m quickice`), navigate to the Hydrate tab, and verify the 8 steps in the plan's Task 3 (custom guest panel renders, valid upload turns the label green + adds "Custom: MOL" to combos, specific validation errors for the 3 invalid fixtures, no-atomtypes warning + upload succeeds, generate + export with a mixed 1-custom + 1-builtin, Pitfall 6 auto-clear, lattice-change rebuild).
- **After the checkpoint is approved:** a continuation agent will do the final `docs(44-02): complete custom guest upload plan` commit (staging this SUMMARY.md + STATE.md).
- **Phase 44 is otherwise complete** (44-01/03/04 done in prior phases 39-04/42-06/43-02; 44-02 done here pending the checkpoint). After 44-02's checkpoint is approved, Phase 44 is complete and ready for Phase 45 (CLI integration — 45-01b+02a combined: --custom-guest + --depol).

---
*Phase: 44-gui-integration*
*Completed: 2026-07-07 (Tasks 1-2; Task 3 checkpoint pending)*
