---
phase: 41-gromacs-export-for-custom-guests
plan: 10
subsystem: testing
tags: [gromacs, grompp, e2e, custom-guest, hydrate-export, gui-path, export-06]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: write_multi_molecule_gro_file + write_multi_molecule_top_file with custom_guest_info (41-02/41-03) and _stage_custom_guest_itp transformed-ITP staging (41-09)
provides:
  - "@gmx_skipif e2e grompp test proving gmx grompp exits 0 on a custom ethanol guest hydrate exported via the GUI multi-molecule writers (EXPORT-06 GUI half)"
affects: [41-11, custom-guest-grompp, e2e-gmx-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["GUI custom-guest grompp e2e: call writers directly + _stage_itp_files + _stage_custom_guest_itp + run_gmx_grompp (mirrors test_e2e_gmx_validation.py)"]

key-files:
  created:
    - tests/test_e2e_custom_guest_gui_grompp.py
  modified: []

key-decisions:
  - "Single solid @gmx_skipif test (no speculative parameterization) — the phase scope is one custom guest; sI is sufficient (plan explicit guidance)"
  - "Box size increased from the plan's literal 2.0 nm to 3.0 nm so the GROMACS PBC rule (cutoff 1.0 nm < half the shortest box vector) is satisfied; MDP untouched"
  - "Used the plan's cwd-relative Path('quickice/data/custom/etoh.itp') for custom_guest_info['itp_path'] (consumed by the TOP writer's atomtypes merge) — consistent with the existing test_multi_molecule_gro_custom_guest.py fixture; pytest runs from repo root"

patterns-established:
  - "Custom-guest GUI grompp e2e pattern: synthetic 2-water + 1-ethanol system (17 atoms, no GenIce2) → write_multi_molecule_gro_file + write_multi_molecule_top_file (custom_guest_info={'mol_type':'etoh_e2e','residue_name':'MOL_H','itp_path':...}) → _stage_itp_files + _stage_custom_guest_itp → assert_itp_completeness + assert_gro_top_consistent → run_gmx_grompp (exit 0)"
  - "GRO box must exceed 2*cutoff for grompp PBC: use 3.0 nm (cutoff 1.0 nm) for the synthetic in-memory system; the plan's 2.0 nm hits the exact 2*cutoff limit and grompp rejects it"

# Metrics
duration: 10min
completed: 2026-07-05
---

# Phase 41 Plan 10: GUI Custom Guest Grompp E2E Summary

**`@gmx_skipif` e2e test proving `gmx grompp` exits 0 on a custom ethanol guest hydrate exported via the GUI multi-molecule writers (`write_multi_molecule_gro_file` + `write_multi_molecule_top_file` with `custom_guest_info`), with the custom ITP staged via `_stage_custom_guest_itp` — closes EXPORT-06 for the GUI path.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-05T05:57:22Z
- **Completed:** 2026-07-05T06:08:00Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments
- Created `tests/test_e2e_custom_guest_gui_grompp.py` with one `@gmx_skipif` test (`test_custom_guest_gui_grompp_passes`) that builds a synthetic 2-water + 1-custom-ethanol-guest system IN MEMORY (17 atoms, no GenIce2 — fast and deterministic), exports it via `write_multi_molecule_gro_file` + `write_multi_molecule_top_file` with `custom_guest_info={'mol_type':'etoh_e2e','residue_name':'MOL_H','itp_path':Path('quickice/data/custom/etoh.itp')}`, stages `tip4p-ice.itp` + the transformed `etoh.itp` (moleculetype `MOL_H`), and runs `gmx grompp`.
- Verified all four `must_haves.truths`: (1) `gmx grompp` exits 0; (2) `.top [molecules]` lists `SOL` + `MOL_H` and `.gro` residues contain `SOL` + `MOL_H`; (3) `assert_itp_completeness` passes (all `#include`'d ITPs present); (4) `assert_gro_top_consistent` passes (GRO residues ↔ TOP `[molecules]`).
- Confirmed the test runs (NOT skipped — `gmx` IS on PATH): `1 passed in 0.32s`.
- Confirmed no regression: all 18 `test_e2e_gmx_validation.py` grompp tests still pass (`18 passed in 4.98s`).

## Task Commits

Each task was committed atomically:

1. **Task 1: GUI grompp e2e test for custom guest (write_multi_molecule_* + staging)** - `1a0d7ef` (test)

## Files Created/Modified
- `tests/test_e2e_custom_guest_gui_grompp.py` - New `@gmx_skipif` e2e test file (141 lines). Imports mirror `test_e2e_gmx_validation.py` (`gmx_skipif`, the two multi-molecule writers, `MoleculeIndex`, and the seven `e2e_export_helpers` helpers). The single `test_custom_guest_gui_grompp_passes(tmp_path)` test: (1) builds the 17-atom synthetic system; (2) writes `hydrate.gro` + `hydrate.top`; (3) stages `em.mdp` + `tip4p-ice.itp` + transformed `etoh.itp`; (4) asserts ITP completeness and GRO/TOP consistency; (5) runs `gmx grompp` and asserts exit code 0; (6) asserts `.top [molecules]` SOL+MOL_H and `.gro` residues SOL+MOL_H.

## Decisions Made
- **Single solid test (no parameterization).** The plan explicitly preferred "ONE solid test over speculative parameterization" — the phase scope is one custom guest, and a single sI test is sufficient. Adding sII would double the runtime for no incremental coverage of the EXPORT-06 truth.
- **Box size = 3.0 nm (not the plan's literal 2.0 nm).** `em.mdp` uses `rcoulomb=rvdw=1.0 nm`, and GROMACS requires the cutoff to be strictly less than half the shortest box vector. The plan's `cell = np.eye(3) * 2.0` put the box exactly at the `2*cutoff` limit, so `gmx grompp` rejected it ("The cut-off length is longer than half the shortest box vector"). Increasing to 3.0 nm (matching the repo's interface-test box convention) gives a comfortable margin. The MDP was NOT touched — only the test's `cell` changed.
- **Kept the plan's cwd-relative `Path("quickice/data/custom/etoh.itp")`** for `custom_guest_info['itp_path']` (consumed by the TOP writer's `_merge_custom_atomtypes`). This is consistent with the existing `test_multi_molecule_gro_custom_guest.py` fixture and with the plan's literal code block; pytest is invoked from the repo root.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed GROMACS PBC box-size rejection**

- **Found during:** Task 1 (first `pytest` run)
- **Issue:** The plan's literal `cell = np.eye(3) * 2.0` produced a 2.0 nm cube. With `em.mdp`'s `rcoulomb = rvdw = 1.0 nm`, this hit GROMACS's exact `2*cutoff` limit, so `gmx grompp` emitted `ERROR 1 [file hydrate.top, line 33]: The cut-off length is longer than half the shortest box vector` and exited 1.
- **Fix:** Increased the test's `cell` to `np.eye(3) * 3.0` (3.0 nm) so the cutoff (1.0 nm) is strictly less than half the box (1.5 nm). The MDP was NOT modified. The positions (`linspace(0.01, 0.17, 17)`) remain well inside the 3.0 nm box, so no coordinate change was needed.
- **Files modified:** `tests/test_e2e_custom_guest_gui_grompp.py` (the `cell` line, with an explanatory comment)
- **Commit:** `1a0d7ef`

## Issues Encountered
- The box-size rejection above (resolved inline as a Rule 1 bug fix).

## User Setup Required
None - no external service configuration required. `gmx` IS on PATH so the test runs (not skipped).

## Authentication Gates
None.

## Next Phase Readiness
- EXPORT-06 (GUI half) is proven: `gmx grompp` exits 0 on a custom ethanol guest hydrate exported via the GUI multi-molecule writers. The CLI half (plan 41-11) can now follow the same pattern using the CLI-side writers (`HydrateGROMACSExporter.export_hydrate` with `config.is_custom_guest`, from plan 41-06) + `copy_custom_guest_itp` (from plan 41-07) instead of the test-only `_stage_custom_guest_itp` helper.
- The `_stage_custom_guest_itp` helper (41-09) + the `custom_guest_info` writer APIs (41-02/41-03) + the box-size guidance (3.0 nm > 2*cutoff) are the reusable contract for any future custom-guest grompp test.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
