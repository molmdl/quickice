---
phase: 41-gromacs-export-for-custom-guests
plan: 11
subsystem: testing
tags: [gromacs, grompp, e2e, custom-guest, hydrate-export, cli-path, export-06]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: write_interface_gro_file + write_interface_top_file with custom_guest_info (41-04/41-05) and _stage_custom_guest_itp transformed-ITP staging (41-09)
provides:
  - "@gmx_skipif e2e grompp test proving gmx grompp exits 0 on a custom ethanol guest hydrate exported via the CLI interface writers (EXPORT-06 CLI half)"
  - "Together with 41-10 (GUI half, already merged), EXPORT-06 is satisfied for BOTH export paths"
affects: [custom-guest-grompp, e2e-gmx-validation, phase-41-completion]

# Tech tracking
tech-stack:
  added: []
  patterns: ["CLI custom-guest grompp e2e: call writers directly + _stage_itp_files + _stage_custom_guest_itp + run_gmx_grompp (mirrors test_e2e_gmx_validation.py); the CLI path uses InterfaceStructure + write_interface_gro_file/write_interface_top_file (the GUI path 41-10 used write_multi_molecule_* directly)"]

key-files:
  created:
    - tests/test_e2e_custom_guest_cli_grompp.py
  modified: []

key-decisions:
  - "Single solid @gmx_skipif test (no speculative parameterization) — the phase scope is one custom guest; a single sI test is sufficient (mirrors 41-10 guidance)"
  - "Box size = 3.0 nm (NOT the plan's literal 2.0 nm) so the GROMACS PBC rule (cutoff 1.0 nm < half the shortest box vector) is satisfied; MDP untouched. Lesson carried over from 41-10"
  - "Added report='test' to the InterfaceStructure constructor — the plan's literal code block omitted it but InterfaceStructure.report is a required dataclass field with no default (would raise TypeError). Execution context pre-corrected this; documented as a Rule 3 auto-fix"
  - "Kept the plan's cwd-relative Path('quickice/data/custom/etoh.itp') for custom_guest_info['itp_path'] (consumed by the TOP writer's _merge_custom_atomtypes) — consistent with 41-10 and the existing test fixtures; pytest runs from repo root"

patterns-established:
  - "Custom-guest CLI grompp e2e pattern: synthetic 2-water + 1-ethanol InterfaceStructure (17 atoms, no GenIce2) → write_interface_gro_file + write_interface_top_file (custom_guest_info={'mol_type':'etoh_e2e','residue_name':'MOL_H','itp_path':...}) → _stage_itp_files + _stage_custom_guest_itp → assert_itp_completeness + assert_gro_top_consistent → run_gmx_grompp (exit 0)"
  - "CLI vs GUI custom-guest grompp tests differ only in the writer pair: CLI uses InterfaceStructure + write_interface_* (the P3-fixed writers 41-04/41-05); GUI uses write_multi_molecule_* (41-02/41-03). Both share the same staging + assertion + grompp contract"
  - "GRO box must exceed 2*cutoff for grompp PBC: use 3.0 nm (cutoff 1.0 nm) for the synthetic in-memory system; the plan's 2.0 nm hits the exact 2*cutoff limit and grompp rejects it (confirmed again by 41-10)"

# Metrics
duration: 1min
completed: 2026-07-05
---

# Phase 41 Plan 11: CLI Custom Guest Grompp E2E Summary

**`@gmx_skipif` e2e test proving `gmx grompp` exits 0 on a custom ethanol guest hydrate exported via the CLI interface writers (`write_interface_gro_file` + `write_interface_top_file` with `custom_guest_info`), with the custom ITP staged via `_stage_custom_guest_itp` — closes EXPORT-06 for the CLI path and, together with 41-10 (GUI half), completes EXPORT-06 for both export paths.**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-07-05T06:37:16Z
- **Completed:** 2026-07-05T06:37:53Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments
- Created `tests/test_e2e_custom_guest_cli_grompp.py` with one `@gmx_skipif` test (`test_custom_guest_cli_grompp_passes`) that builds a synthetic 2-water + 1-custom-ethanol-guest `InterfaceStructure` IN MEMORY (17 atoms, no GenIce2 — fast and deterministic), exports it via `write_interface_gro_file` + `write_interface_top_file` with `custom_guest_info={'mol_type':'etoh_e2e','residue_name':'MOL_H','itp_path':Path('quickice/data/custom/etoh.itp')}`, stages `tip4p-ice.itp` + the transformed `etoh.itp` (moleculetype `MOL_H`), and runs `gmx grompp`.
- Verified all four `must_haves.truths`: (1) `gmx grompp` exits 0; (2) `.top [molecules]` lists `SOL` + `MOL_H` and `.gro` residues contain `SOL` + `MOL_H`; (3) `assert_itp_completeness` passes (all `#include`'d ITPs present); (4) `assert_gro_top_consistent` passes (GRO residues ↔ TOP `[molecules]`).
- Confirmed the test runs (NOT skipped — `gmx` IS on PATH, GROMACS 2023.5-plumed_2.9.3): `1 passed in 0.33s`.
- Confirmed no regression: all 18 `test_e2e_gmx_validation.py` grompp tests still pass (`18 passed in 5.11s`).
- EXPORT-06 is now satisfied for BOTH export paths (GUI half = 41-10, CLI half = 41-11).

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI grompp e2e test for custom guest (write_interface_* + staging)** - `c2a876e` (test)

**Plan metadata:** (pending — committed after SUMMARY + STATE update)

## Files Created/Modified
- `tests/test_e2e_custom_guest_cli_grompp.py` - New `@gmx_skipif` e2e test file (152 lines). Imports mirror `test_e2e_gmx_validation.py` (`gmx_skipif`, the two interface writers, `InterfaceStructure` + `MoleculeIndex`, and the seven `e2e_export_helpers` helpers). The single `test_custom_guest_cli_grompp_passes(tmp_path)` test: (1) builds the 17-atom synthetic `InterfaceStructure` (module-scope, immutable-ish); (2) writes `hydrate.gro` + `hydrate.top` with `custom_guest_info`; (3) stages `em.mdp` + `tip4p-ice.itp` + transformed `etoh.itp`; (4) asserts ITP completeness and GRO/TOP consistency; (5) runs `gmx grompp` and asserts exit code 0; (6) asserts `.top [molecules]` SOL+MOL_H and `.gro` residues SOL+MOL_H.

## Decisions Made
- **Single solid test (no parameterization).** Mirrors 41-10's guidance — the phase scope is one custom guest, and a single sI test is sufficient. The CLI path differs from the GUI path only in the writer pair, which is the unit under test; parameterizing over lattice types would not add incremental coverage of the EXPORT-06 truth.
- **Box size = 3.0 nm (not the plan's literal 2.0 nm).** Lesson carried over verbatim from 41-10: `em.mdp` uses `rcoulomb=rvdw=1.0 nm`, and GROMACS requires the cutoff to be strictly less than half the shortest box vector. The plan's `cell = np.eye(3) * 2.0` would put the box exactly at the `2*cutoff` limit, so `gmx grompp` would reject it. 3.0 nm gives a comfortable margin (the execution context pre-flagged this). MDP untouched.
- **Added `report="test"` to the `InterfaceStructure` constructor.** The plan's literal code block omitted it, but `InterfaceStructure.report` is a required dataclass field with no default (would raise `TypeError: __init__() missing 1 required argument: 'report'`). The execution context pre-corrected this (`report="test"`). Documented as a Rule 3 auto-fix below for transparency.
- **Kept the plan's cwd-relative `Path("quickice/data/custom/etoh.itp")`** for `custom_guest_info['itp_path']` (consumed by the TOP writer's `_merge_custom_atomtypes`). Consistent with 41-10 and the existing `test_multi_molecule_gro_custom_guest.py` fixture; pytest is invoked from the repo root.
- **Module-scope fixture system.** `_IFACE` / `_CGI` / `_ATOM_NAMES` / `_POSITIONS` / `_CELL` / `_MOLECULE_INDEX` defined at module scope (immutable-ish and cheap, matching the convention in `test_e2e_gmx_validation.py` of building fixtures outside the test body). The plan explicitly permitted this ("module-scope is fine since they are immutable-ish and cheap").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing `report="test"` to InterfaceStructure constructor**

- **Found during:** Task 1 (file creation, before first `pytest` run)
- **Issue:** The plan's literal code block (lines 97-99 of `41-11-PLAN.md`) constructed `InterfaceStructure(...)` without the `report` argument. `InterfaceStructure.report` is a required dataclass field with no default (`types.py:408`), so the literal code would have raised `TypeError: __init__() missing 1 required argument: 'report'` at import time. The execution context (objective section) pre-corrected this with `report="test"`.
- **Fix:** Added `report="test"` to the `InterfaceStructure(...)` call in the test file (matching the execution context). No behavioral impact — `report` is only consumed by human-readable report generation, not by the writers under test.
- **Files modified:** `tests/test_e2e_custom_guest_cli_grompp.py` (the `InterfaceStructure(...)` call)
- **Verification:** `pytest tests/test_e2e_custom_guest_cli_grompp.py -v` → `1 passed in 0.33s` (grompp exits 0)
- **Committed in:** `c2a876e` (part of the task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial — required dataclass field added per the execution context's pre-correction. No scope creep, no behavioral change to the writers under test. The box-size lesson from 41-10 was applied as a known constraint (documented in Decisions, not as a deviation, since the execution context pre-flagged it).

## Issues Encountered
None beyond the documented `report=` field auto-fix. The test passed on the first `pytest` run (the box-size 3.0 nm and staging order were carried over as known-good from 41-10).

## User Setup Required
None - no external service configuration required. `gmx` IS on PATH (GROMACS 2023.5-plumed_2.9.3) so the test runs (not skipped).

## Authentication Gates
None.

## Next Phase Readiness
- EXPORT-06 is fully closed: both the GUI half (41-10) and the CLI half (41-11) prove `gmx grompp` exits 0 on a custom ethanol guest hydrate. The two tests share the same staging + assertion + grompp contract; they differ only in the writer pair under test (`write_multi_molecule_*` vs `write_interface_*`).
- Phase 41 is now 10/11 plans complete (41-01..41-07, 41-09, 41-10, 41-11). The only remaining plan is 41-08 (executing in parallel per STATE.md).
- The reusable contract for any future custom-guest grompp test: `_stage_custom_guest_itp` (41-09) + the `custom_guest_info` writer APIs (41-02..41-05) + the box-size guidance (3.0 nm > 2*cutoff).

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
