---
phase: 45-e2e-hydrate-tab-workflow
plan: 13
subsystem: testing
tags: [e2e, grompp, hydrate, mixed-occupancy, sII, ice-xvi, gui-exporter, multi-molecule-writers]

# Dependency graph
requires:
  - phase: 42
    provides: Mixed cage occupancy (cage_guest_assignments + CageGuestAssignment) + multi-molecule writers (write_multi_molecule_* list[dict] API) + HydrateGROMACSExporter.export_hydrate mixed-guest path
  - phase: 45
    provides: Wave 6 mixed-occupancy e2e testing scope (Pitfall 2 single-guest-stream guidance)
provides:
  - E2E proof that mixed built-in occupancy (CH4 small + THF large) with sII + 16 produces grompp-valid output via the GUI HydrateGROMACSExporter.export_hydrate
  - Parametrized test (sII, 16) asserting BOTH CH4_H + THF_H in .top [molecules] + .gro residues + both built-in ITPs staged + grompp rc=0
affects: [48-docs (mixed occupancy coverage matrix), future regression watchlist]

# Tech tracking
tech-stack:
  added: []  # No new libraries — test-only plan
  patterns:
    - "2x2x2 supercell for sII/16 hydrate-only grompp (Pitfall 1: 1x1x1 box 1.71 nm < 2.0 nm)"
    - "GUI exporter test: exporter stages ALL ITPs itself (tip4p-ice.itp + ch4_hydrate.itp + thf_hydrate.itp) — do NOT call _stage_itp_files (would re-stage + conflict)"
    - "Mixed built-in via write_multi_molecule_* (GUI path) NOT write_interface_* (CLI single-stream, Pitfall 2)"

key-files:
  created:
    - tests/test_e2e_mixed_lattice_gui.py
  modified: []

key-decisions:
  - "2x2x2 supercell (not plan's literal 1x1x1) for sII/16 hydrate-only grompp — Rule 3 blocking fix (Pitfall 1: 1x1x1 box 1.7121 nm < 2.0 nm -> grompp fatal 'cut-off longer than half shortest vector')"
  - "Exporter stages ITPs itself — test copies only MDP for grompp (NOT _stage_itp_files, which would re-stage from quickice/data/ and conflict with the exporter's transform_guest_itp output)"

patterns-established:
  - "Mixed built-in (CH4+THF) GUI export test: module-scoped fixture per lattice + parametrized QFileDialog-mocked HydrateGROMACSExporter.export_hydrate + assert BOTH guest residues/ITPs + grompp rc=0"
  - "sII/16 share cage_type_map {small:12, large:16} — both valid mixed built-in targets; GenIce2 places CH4 in 16 small + THF in 8 large per unit cell"

# Metrics
duration: 2min
completed: 2026-07-11
---

# Phase 45 Plan 13: Mixed Built-in Lattice GUI Grompp Summary

**Mixed built-in cage occupancy (CH4 small + THF large) proven grompp-valid for sII + 16 via GUI HydrateGROMACSExporter.export_hydrate (write_multi_molecule_* multi-guest writers)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-11T09:56:47Z
- **Completed:** 2026-07-11T09:58:31Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- Created `tests/test_e2e_mixed_lattice_gui.py` with a module-scoped fixture building sII + 16 mixed built-in hydrates (CH4 in small + THF in large cages) and a parametrized GUI export + grompp test
- Proved `gmx grompp` exits 0 on BOTH sII and 16 mixed built-in via the GUI `HydrateGROMACSExporter.export_hydrate` (multi-molecule writers) — the path that handles mixed guests (per-mol_type resolution registering BOTH CH4_H + THF_H)
- Asserted the mixed built-in signature: BOTH `CH4_H` + `THF_H` in `.top [molecules]` + `.gro` residues, and BOTH `ch4_hydrate.itp` + `thf_hydrate.itp` staged by the exporter
- Respected Pitfall 2: tested mixed built-in via GUI `write_multi_molecule_*` (NOT CLI `write_interface_*` single-guest-stream), extending mixed occupancy testing beyond sI (42-05/42-07)

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Write + commit mixed built-in (CH4+THF) + sII/16 GUI hydrate export grompp test** - `2f323fc` (test)

_Note: Tasks 1 and 2 were combined into a single test commit since Task 2 was "run full test + commit" — the test file was written, verified (2/2 PASSED), and committed in one atomic step per the plan's commit guidance._

## Files Created/Modified
- `tests/test_e2e_mixed_lattice_gui.py` - E2E mixed built-in (CH4 small + THF large) GUI hydrate export + grompp test for sII + 16 (245 lines); module-scoped fixture + parametrized QFileDialog-mocked HydrateGROMACSExporter.export_hydrate test asserting BOTH CH4_H + THF_H present + grompp rc=0

## Decisions Made
- **2x2x2 supercell (not plan's literal 1x1x1):** The plan specified `supercell_x=1, supercell_y=1, supercell_z=1`, but sII/16 at 1x1x1 have a shortest box vector of ~1.7121 nm — SMALLER than 2*rcoulomb = 2.0 nm — so grompp fatal-errors with "cut-off length is longer than half the shortest box vector" (Pitfall 1). The 2x2x2 supercell expands the shortest vector to ~3.4242 nm (> 2.0 nm) so grompp succeeds. Generation is fast (~0.1s). This is the same Pitfall 1 the triclinic filled-ice test (45-09) addressed with 4x4x4 — applied here to sII/16 hydrate-only export. Empirically verified: sII 2x2x2 grompp rc=0.
- **Exporter stages ITPs itself:** The GUI `HydrateGROMACSExporter.export_hydrate` copies `tip4p-ice.itp` + transforms+copies each guest ITP (`ch4_hydrate.itp`, `thf_hydrate.itp`) via `transform_guest_itp` (idempotent on pre-transformed built-in ITPs). The test therefore copies only the MDP for grompp and does NOT call `_stage_itp_files` (which would re-stage from `quickice/data/` and could conflict with the exporter's transform output). `assert_itp_completeness` still runs to verify all #include'd ITPs are present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used 2x2x2 supercell (not plan's literal 1x1x1) for sII/16 hydrate-only grompp**

- **Found during:** Task 1 (empirical pre-test verification of box sizes)
- **Issue:** The plan specified `supercell_x=1, supercell_y=1, supercell_z=1`, but sII/16 at 1x1x1 have a shortest box vector of ~1.7121 nm, which is SMALLER than 2*rcoulomb = 2.0 nm. grompp fatal-errors with "cut-off length is longer than half the shortest box vector" (Pitfall 1 — the same box-size rule that required 4x4x4 for the triclinic filled-ice lattices in 45-09). The plan's success criteria require `gmx grompp exits 0`, which is impossible at 1x1x1.
- **Fix:** Used `supercell_x=2, supercell_y=2, supercell_z=2` — expands the shortest vector to ~3.4242 nm (> 2.0 nm) so grompp succeeds. Generation is fast (~0.1s), so the module-scoped fixture remains cheap.
- **Files modified:** tests/test_e2e_mixed_lattice_gui.py (fixture supercell fields + comments documenting the Pitfall 1 rationale)
- **Verification:** Empirically verified sII 2x2x2 → shortest_vec=3.4242 nm, grompp rc=0; both parametrized cases (sII, 16) PASS in 1.17s
- **Committed in:** 2f323fc (Task 1+2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The 2x2x2 supercell is necessary to satisfy the grompp rc=0 success criteria (Pitfall 1 box-size). No scope creep — the test still proves exactly what the plan intended (mixed built-in CH4+THF with sII/16 through the GUI multi-molecule writers), just with a larger supercell so grompp can actually validate the topology.

## Issues Encountered
None — mixed built-in generation (CH4 small + THF large) worked out of the box for sII and 16 (both have `cage_type_map = {"small": "12", "large": "16"}` with distinct cage ids, so GenIce2's per-cage-key `parse_guest` calls don't trip the "Cage type already specified" assert). The GUI exporter correctly registered BOTH CH4 + THF in the `MoleculetypeRegistry` and staged both built-in ITPs.

## User Setup Required
None - no external service configuration required. `gmx` is on PATH (grompp runs; `@gmx_skipif` skips when absent).

## Next Phase Readiness
- Mixed built-in occupancy (CH4+THF) now proven for sII and 16 through the GUI hydrate exporter (extends beyond sI from 42-05/42-07)
- Wave 6 mixed-occupancy lattice coverage gap closed for the two-cage-type lattices (sII, 16)
- The CLI single-guest-stream limitation for mixed built-in (Pitfall 2) remains documented + out of scope (tested via GUI multi-molecule writers per the plan)
- Ready for the wave-completion orchestrator step (STATE.md update handled by orchestrator)

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
