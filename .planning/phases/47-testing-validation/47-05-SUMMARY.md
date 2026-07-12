---
phase: 47-testing-validation
plan: 05
subsystem: testing
tags: [grompp, filled-ice, c2te, ice1hte, hydrate-export, cli, native-supercell, parse_guest, interface-structure-wrapper]

# Dependency graph
requires:
  - phase: 45-09
    provides: Triclinic CLI hydrate-branch grompp test pattern (CLIPipeline._run_export_step hydrate branch + _assert_hydrate_export helper — the exact pattern mirrored here for orthorhombic c2te/ice1hte)
  - phase: 45-14
    provides: Filled-ice per-lattice supercell constants (_FILLED_ICE_SUPERCELLS: c2te=3x3x3, ice1hte=4x4x4) + module-scoped filled_ice_hydrates fixture pattern with cage_guest_assignments={"small": ...}
  - phase: 41-07
    provides: copy_itp_files_for_structure (CLI hydrate branch ITP staging — stages ch4_hydrate.itp for built-in ch4)
  - phase: 39-02
    provides: Filled-ice single-cage-key path (parse_guest for guest placement; single-entry cage_type_map {"small": "Ne1"} prevents double-placement)
provides:
  - E2E proof that the CLI CLIPipeline._run_export_step hydrate branch (pipeline.py:886-929) produces grompp-valid output for c2te (3x3x3) and ice1hte (4x4x4) at their native orthorhombic supercells
  - Closes TEST-08 — the final remaining test gap in v4.7 (Phase 47 now 8/8 requirements complete: 47-01..04 done in prior phases, 47-05 done here)
  - Zero new production code, zero new helpers — single new test file composing existing verified patterns + helpers
affects: [48, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI hydrate-branch export test composition: mirror the triclinic CLI pattern (CLIPipeline + _hydrate_result + _run_export_step) with the filled-ice per-lattice supercell fixture (c2te=3x3x3, ice1hte=4x4x4)"
    - "Native orthorhombic supercell validation distinct from the 3x3x8 nm slab path (interface/solute/ion branches) — same lattices, different cell geometry, different export branch"

key-files:
  created:
    - tests/test_e2e_filled_ice_cli_hydrate_grompp.py
  modified: []

key-decisions:
  - "Per-lattice supercell: c2te=3x3x3 (shortest 2.65nm), ice1hte=4x4x4 (shortest 2.76nm) — both > 2.0nm for grompp; 2x2x2 fails both, ice1hte even fails 3x3x3 (2.07nm) due to GROMACS's stricter non-orthogonal cell check"
  - "cage_guest_assignments uses 'small' key (matching cage_type_map), NOT 'guest' (the cages display dict key) — using 'guest' produces 0 guests"
  - "Set ONLY _hydrate_result (NOT _interface_result) so the export priority selector (ion > solute > custom > interface > hydrate > ice) picks the hydrate branch"
  - "CLI-only test: no PySide6/VTK/HydrateGROMACSExporter/unittest.mock imports — uses CLIPipeline._run_export_step + write_interface_* writers (the CLI hydrate branch), NOT the GUI write_multi_molecule_* path"
  - "All assertion primitives imported from tests/e2e_export_helpers.py (run_gmx_grompp, parse_top_molecules, parse_gro_residue_names, assert_itp_completeness, assert_gro_top_consistent, MDP_PATH) — zero reimplemented"

patterns-established:
  - "Filled-ice CLI hydrate-branch grompp test: module-scoped fixture + parametrized CLIPipeline._run_export_step hydrate branch + shared _assert_filled_ice_hydrate_export helper"
  - "Test file naming convention: test_e2e_filled_ice_cli_hydrate_grompp.py (CLI + filled-ice + hydrate-branch + grompp) distinct from the triclinic sibling (test_e2e_triclinic_hydrate_export.py) and GUI sibling (test_e2e_mixed_filled_ice_gui.py)"

# Metrics
duration: 1 min
completed: 2026-07-12
---

# Phase 47 Plan 05: CLI Hydrate-Branch Grompp Validation for Filled-Ice Lattices Summary

**CLI CLIPipeline._run_export_step hydrate branch produces grompp-valid output for c2te (3x3x3) and ice1hte (4x4x4) at their native orthorhombic supercells, closing TEST-08 — the final v4.7 test gap**

## Performance

- **Duration:** 1 min (63 sec)
- **Started:** 2026-07-12T02:18:58Z
- **Completed:** 2026-07-12T02:20:01Z
- **Tasks:** 2
- **Files modified:** 1 (1 new test file)

## Accomplishments
- Created `tests/test_e2e_filled_ice_cli_hydrate_grompp.py` with a module-scoped `filled_ice_hydrates` fixture (c2te@3x3x3 + ice1hte@4x4x4, built-in ch4) and a parametrized `@gmx_skipif` test `test_filled_ice_cli_hydrate_export_grompp` for `["c2te", "ice1hte"]`
- Proved `gmx grompp` returns rc=0 for both c2te and ice1hte CLI hydrate-only exports at their native orthorhombic supercells (the HydrateStructure -> InterfaceStructure wrapper path at pipeline.py:886-929)
- Confirmed zero regressions: all 13 filled-ice + hydrate-export sibling tests pass (11 pre-existing + 2 new), all 16 CLI regression tests pass
- Closed TEST-08 — Phase 47 is now 8/8 requirements complete (47-01..04 satisfied by prior phases 39-05/40/41/42, 47-05 satisfied here)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_e2e_filled_ice_cli_hydrate_grompp.py** - `80bb6f5` (test)
2. **Task 2: Run full filled-ice test suite — confirm no regressions** - (verification-only gate; no file changes — test file already committed in Task 1; no empty commit per AGENTS.md)

**Plan metadata:** `docs(47-05): complete cli-hydrate-grompp plan` (see git log — self-referential hash omitted)

## Files Created/Modified
- `tests/test_e2e_filled_ice_cli_hydrate_grompp.py` - New e2e test: CLI hydrate-branch grompp validation for c2te (3x3x3) + ice1hte (4x4x4) filled-ice lattices. Module-scoped fixture + parametrized `@gmx_skipif` test driving `CLIPipeline._run_export_step` hydrate branch. Imports assertion primitives from `tests/e2e_export_helpers.py` (not reimplemented). No PySide6/VTK/HydrateGROMACSExporter imports (CLI-only).

## Decisions Made
- **Test file placement:** New dedicated file `tests/test_e2e_filled_ice_cli_hydrate_grompp.py` rather than extending `test_e2e_triclinic_hydrate_export.py` (c2te/ice1hte are ORTHORHOMBIC, not triclinic — mixing them in a "triclinic" file would be misleading) or `test_e2e_mixed_filled_ice_gui.py` (would mix CLI + GUI in a GUI file).
- **Cage-guest form:** Used explicit `cage_guest_assignments={"small": CageGuestAssignment(guest_type="ch4", occupancy=100.0)}` (matching the GUI sibling test 45-14 for these specific lattices) rather than the legacy `guest_type="ch4"`-only form — documents the cage-key pitfall ("small" matches cage_type_map, NOT "guest") inline.
- **Assertion helper:** Adapted `_assert_hydrate_export` from the triclinic test to `_assert_filled_ice_hydrate_export` — identical assertion sequence (files written + ch4_hydrate.itp staged with CH4_H + CH4_H/SOL in [molecules] + CH4_H/SOL in .gro residues + assert_itp_completeness + assert_gro_top_consistent + gmx grompp rc=0), with docstrings/variable names updated to "filled-ice".

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - the test passed on the first run. The empirically-verified supercell sizes (c2te=3x3x3, ice1hte=4x4x4) from the GUI sibling test (45-14) transferred directly to the CLI hydrate branch; the cage key "small" produced guests as expected (fixture sanity assert `hydrate.guest_count > 0` passed); no PySide6/VTK import contamination.

## User Setup Required
None - no external services configuration required. This is a test-only plan using the existing `quickice` conda env + `gmx` on PATH.

## Next Phase Readiness
- Phase 47 (Testing & Validation) is now COMPLETE — all 8 requirements (TEST-01..TEST-08) satisfied:
  - TEST-01/02/03: Unit tests for custom guest validation, sys.modules, _build_molecule_index (done in Phase 40)
  - TEST-04: E2E tests for filled ice generation (done in 39-05)
  - TEST-05/07: E2E tests for custom guest hydrate + GROMACS export (done in Phase 41)
  - TEST-06: E2E tests for mixed cage occupancy (done in Phase 42)
  - TEST-08: CLI hydrate-branch grompp for c2te/ice1hte filled-ice (done here — 47-05)
- Only Phase 48 (Documentation) remains for v4.7: 48-01 (external docs) + 48-02 (in-app help restructure).
- No blockers or concerns.

---
*Phase: 47-testing-validation*
*Completed: 2026-07-12*
