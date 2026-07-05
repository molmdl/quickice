---
phase: 41-gromacs-export-for-custom-guests
plan: 04
subsystem: testing
tags: [gromacs, gro, custom-guest, hydrate, metadata-driven, p3, tdd]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: "custom_guest_info dict shape {mol_type, residue_name, itp_path} (plan 41-02) — same API, now consumed by the interface GRO writer (residue_name used; itp_path unused here, kept for API consistency)"
  - phase: 41-gromacs-export-for-custom-guests
    provides: "InterfaceStructure.molecule_index with MoleculeIndex(start_idx, count, mol_type) (long-standing) — guest entry's mol_type + count drive the custom branch"
provides:
  - "write_interface_gro_file custom_guest_info param — lets the CLI hydrate exporter (41-08) thread the custom guest residue name + mol_type so the .gro lists MOL_H (EXPORT-04) and chunks the 9-atom ethanol as one whole molecule (EXPORT-05 / P3)"
  - "Metadata-driven custom-guest path in the interface GRO writer — bypasses detect_guest_type_from_atoms (returns None for ethanol) and count_guest_atoms (miscounts ethanol as 5)"
affects: [EXPORT-04, EXPORT-05, 41-08-cli-hydrate-export, 41-10-grompp-validation, cli-hydrate-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-context-dict pattern: custom_guest_info carries the per-mol_type residue-name override; None falls through to the existing built-in path (detect_guest_type_from_atoms + count_guest_atoms + ch4/thf reorder) — no regression"
    - "Metadata-driven chunking: atoms_per_mol taken from the matching molecule_index entry's .count (NOT the count_guest_atoms heuristic) so non-ch4/thf guests like ethanol are written as whole molecules"
    - "Monkeypatch-then-call pattern to prove a code path is NOT taken: monkeypatch detect_guest_type_from_atoms to raise AssertionError; the custom branch must NOT invoke it (test_custom_branch_skips_detect)"

key-files:
  created:
    - tests/test_output/test_interface_gro_custom_guest.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "custom_guest_info is an Optional dict (default None) added as the LAST keyword param (after filepath) — backward-compatible call-site signature; existing callers (GUI export, tests) unaffected"
  - "Custom branch chunks guest atoms by the matching molecule_index entry's .count (NOT count_guest_atoms) — fixes the 9-atom ethanol being miscounted as 5 (EXPORT-05 / P3)"
  - "Custom branch uses custom_guest_info['residue_name'] directly (e.g. 'MOL_H') — does NOT call detect_guest_type_from_atoms, which returns None for unknown guests and falls through to 'UNK' (EXPORT-04)"
  - "Built-in path (ch4/thf via detect + count_guest_atoms + reorder) indented verbatim under else: — byte-identical for built-in guests (no regression)"
  - "Fallback atoms_per_mol = iface.guest_atom_count // max(iface.guest_nmolecules, 1) when no molecule_index entry matches custom_guest_info['mol_type'] — defensive; real callers always populate molecule_index"

patterns-established:
  - "TDD RED-GREEN for additive writer API: RED with TypeError on missing kwarg (3 custom-guest tests fail; built-in CH4 regression test stays green throughout), GREEN by adding the param + custom branch (all 4 tests pass)"
  - "In-memory synthetic InterfaceStructure (no GenIce2) for GRO writer unit tests: 0 ice + 2 water + 1 custom ethanol guest assembled from MoleculeIndex lists; asserts residue names + atom count header"

# Metrics
duration: 2min
completed: 2026-07-05
---

# Phase 41 Plan 04: P3 Custom Guest Interface GRO Summary

**Optional `custom_guest_info` dict on `write_interface_gro_file` so the CLI hydrate `.gro` writes the custom guest with residue `MOL_H` (EXPORT-04) and chunks the 9-atom ethanol by the `molecule_index` entry's `count` (EXPORT-05 / P3) — instead of falling through to `UNK` via `detect_guest_type_from_atoms` (returns None for ethanol) and miscounting via `count_guest_atoms` (5, not 9).**

## Performance

- **Duration:** 2 min (123 s)
- **Started:** 2026-07-05T05:46:15Z
- **Completed:** 2026-07-05T05:48:18Z
- **Tasks:** 2
- **Files modified:** 2 (1 created test file, 1 modified writer)

## Accomplishments
- Added `custom_guest_info: dict | None = None` parameter to `write_interface_gro_file` (last keyword, after `filepath`), with docstring documenting the `{mol_type, residue_name, itp_path}` shape and the no-regression fall-through semantics.
- Custom branch (when `custom_guest_info is not None`): uses `custom_guest_info["residue_name"]` directly (e.g. `MOL_H`) and validates it via `validate_gro_residue_name` — does NOT call `detect_guest_type_from_atoms` (which returns `None` for ethanol and falls through to `UNK`; EXPORT-04 + EXPORT-05 / P3).
- Custom branch chunks guest atoms by the matching `molecule_index` entry's `.count` (looked up by `mol_type == custom_guest_info["mol_type"]`) — NOT the `count_guest_atoms` heuristic, which miscounts ethanol as 5. Falls back to `guest_atom_count // max(guest_nmolecules, 1)` when no index entry matches (defensive).
- Built-in path (ch4/thf via `detect_guest_type_from_atoms` + `count_guest_atoms` + `reorder_guest_atoms`) indented verbatim under `else:` — byte-identical for built-in guests (no regression).
- 4 unit tests: `MOL_H` residue for 9 guest atoms, header atom count == 17 (NOT 13), `detect_guest_type_from_atoms` not called (monkeypatched to raise), and built-in CH4 regression (`CH4_H` + `SOL`, no `UNK`).
- Zero regression: 8/8 existing `interface_gro`/`interface_top` tests pass; 96/96 tests in `tests/test_output/` pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for custom guest interface GRO (P3)** - `49516fa` (test)
2. **Task 2: GREEN — P3 fix — metadata-driven custom guest in write_interface_gro_file** - `21a7e97` (feat)

**Plan metadata:** pending — `docs(41-04)` commit follows this summary.

## Files Created/Modified
- `tests/test_output/test_interface_gro_custom_guest.py` — 4 unit tests (synthetic 0-ice + 2-water + 1-custom-ethanol-guest `InterfaceStructure`; built-in CH4 regression using the `interface_with_ch4_guests` fixture). Reuses `parse_gro_residue_names` + `parse_gro_atom_count` from `tests/e2e_export_helpers.py`. Uses `monkeypatch.setattr("quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom)` to prove the custom branch bypasses the heuristic.
- `quickice/output/gromacs_writer.py` — `write_interface_gro_file` gains the `custom_guest_info` param + an if/else wrap around the existing guest-writing block: the custom branch (metadata-driven residue name + `molecule_index`-count chunking) is opt-in; the built-in branch is indented verbatim under `else:` (no logic change, only indentation).

## Decisions Made
- `custom_guest_info` is an Optional dict (default None) added as the LAST keyword param (after `filepath`) — backward-compatible call-site signature; existing callers (GUI `export.py`, CLI pipeline, tests) unaffected.
- Custom branch chunks guest atoms by the matching `molecule_index` entry's `.count` (NOT `count_guest_atoms`) — fixes the 9-atom ethanol being miscounted as 5 (EXPORT-05 / P3).
- Custom branch uses `custom_guest_info["residue_name"]` directly (e.g. `MOL_H`) — does NOT call `detect_guest_type_from_atoms`, which returns `None` for unknown guests and falls through to `UNK` (EXPORT-04).
- Built-in path (ch4/thf via `detect_guest_type_from_atoms` + `count_guest_atoms` + `reorder_guest_atoms`) indented verbatim under `else:` — byte-identical for built-in guests (no regression).
- Fallback `atoms_per_mol = iface.guest_atom_count // max(iface.guest_nmolecules, 1)` when no `molecule_index` entry matches `custom_guest_info["mol_type"]` — defensive; real callers always populate `molecule_index`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `report="test"` to the synthetic InterfaceStructure in tests**
- **Found during:** Task 1 (RED — failing tests for custom guest interface GRO)
- **Issue:** The plan's code snippet for `_build_custom_guest_iface()` omitted the `report` field, but `InterfaceStructure.report` is a required positional field (no default). Tests failed with `TypeError: InterfaceStructure.__init__() missing 1 required positional argument: 'report'` before ever reaching `write_interface_gro_file`, masking the intended RED state (kwarg rejection).
- **Fix:** Added `report="test"` to the `InterfaceStructure(...)` construction in `_build_custom_guest_iface()`.
- **Files modified:** `tests/test_output/test_interface_gro_custom_guest.py`
- **Verification:** Tests now fail with the intended `TypeError: write_interface_gro_file() got an unexpected keyword argument 'custom_guest_info'` (RED), then pass after the GREEN commit.
- **Committed in:** `49516fa` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial test-fixture fix needed to exercise the intended RED state. No scope creep — the test assertions and GREEN implementation are exactly as the plan specified.

### Workflow Note (not a plan deviation)

`quickice/output/gromacs_writer.py` matches the `.gitignore` `output/` pattern but is already tracked. Plain `git add` refuses with "The following paths are ignored by one of your .gitignore files"; the commit was completed using `git add -f` (force). This is a pre-existing repo gitignore interaction already noted in the 41-02 and 41-03 SUMMARYs; it affects all 41-02..41-05 edits to the same file.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `write_interface_gro_file` now accepts `custom_guest_info` — ready for plan 41-08 (CLI hydrate exporter `_run_export_step`) to pass `{"mol_type": config.guest_type, "residue_name": "MOL_H", "itp_path": Path(config.guest_itp_path)}` when `config.is_custom_guest`.
- The metadata-driven custom-guest path established here mirrors the pattern in `write_multi_molecule_gro_file` (41-02) and `write_multi_molecule_top_file` (41-03); plan 41-05 (CLI `write_interface_top_file` custom-guest branch) can adopt the same pattern.
- Plan 41-10 (`gmx grompp` validation) can now construct a custom ethanol guest hydrate `.gro` + `.top` pair where the residue name (`MOL_H`) and atom count (17) are consistent — the prerequisite for EXPORT-06.
- No blockers — built-in interface export (8/8) + 96 tests in `tests/test_output/` pass; the `custom_guest_info` path is purely additive.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
