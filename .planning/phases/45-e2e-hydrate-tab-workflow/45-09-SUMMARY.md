---
phase: 45-e2e-hydrate-tab-workflow
plan: 09
subsystem: testing
tags: [triclinic-filled-ice, hydrate-export, e2e, cli-pipeline, gui-exporter, c0te, c1te, grompp, 4x4x4-supercell, pytest, PySide6]

# Dependency graph
requires:
  - phase: 39-hydrate-lattice-expansion
    provides: Triclinic filled-ice c0te/c1te lattice definitions (HYDRATE_LATTICES) + HydrateStructureGenerator support
  - phase: 45-08
    provides: E2E proof c0te/c1te are BLOCKED at the interface tab (only Hydrate -> Export is possible for triclinic filled ice)
provides:
  - E2E proof that triclinic filled-ice lattices (c0te, c1te) at 4x4x4 supercell produce grompp-valid hydrate-only export through the CLI _run_export_step hydrate branch (write_interface_* via InterfaceStructure wrapper)
  - E2E proof that the same lattices produce grompp-valid output through the GUI HydrateGROMACSExporter.export_hydrate (write_multi_molecule_* via MoleculetypeRegistry) — a DIFFERENT code path (Pitfall 6)
  - Module-scoped fixture pattern amortizing GenIce2 4x4x4 generation (~5-15s/lattice) across parametrized CLI+GUI export cases
  - Empirical confirmation that c1te 4x4x4 passes grompp (shortest vector 2.41 nm > 2.0 nm) — not previously run, only inferred from c0te
affects:
  - 45-e2e-hydrate-tab-workflow (phase completion)
  - 47-05 (filled-ice grompp gap TEST-08 — triclinic filled-ice hydrate-only export now covered)

# Tech tracking
tech-stack:
  added: []  # No new libraries — test-only plan
  patterns:
    - "Pitfall 1 (box-size) mitigation: triclinic filled-ice hydrate-only export MUST use 4x4x4 supercell (NOT 1x1x1) — 1x1x1 shortest vector ~0.54-0.61 nm < 2*rcoulomb=2.0 nm fails grompp; 4x4x4 -> 2.14/2.41 nm passes"
    - "Pitfall 6 (two export paths): CLI _run_export_step hydrate branch wraps HydrateStructure in InterfaceStructure + write_interface_*; GUI HydrateGROMACSExporter.export_hydrate uses write_multi_molecule_* + MoleculetypeRegistry — test BOTH separately"
    - "CLI hydrate-branch testing: set ONLY _hydrate_result (NOT _interface_result) so _run_export_step priority (ion>solute>custom>interface>hydrate>ice) picks the hydrate branch; the hydrate branch writes hydrate.gro/hydrate.top"
    - "GUI hydrate exporter lazy-imported inside the test function (NOT module top) to keep PySide6 out of the CLI test's import path (AGENTS.md)"

key-files:
  created:
    - tests/test_e2e_triclinic_hydrate_export.py
  modified: []

key-decisions:
  - "Used 4x4x4 supercell for BOTH c0te and c1te (Pitfall 1) — c0te 4x4x4 shortest vector 2.14 nm, c1te 4x4x4 shortest vector 2.41 nm, both > 2.0 nm grompp threshold"
  - "c1te 4x4x4 passed grompp on the first try (did NOT need 5x5x5) — confirmed the research inference (4*0.6017=2.407 > 2.0)"
  - "Tested CLI and GUI export paths as SEPARATE parametrized test functions (Pitfall 6) — CLI uses write_interface_* via InterfaceStructure wrapper; GUI uses write_multi_molecule_* via MoleculetypeRegistry"
  - "GUI HydrateGROMACSExporter lazy-imported inside the GUI test (NOT module top) per AGENTS.md — PySide6/VTK/GenIce2 imported inside function bodies, never at module top level"

patterns-established:
  - "Pattern: triclinic filled-ice hydrate-only export test — module-scoped fixture builds c0te/c1te @ 4x4x4 ONCE, parametrized CLI (_run_export_step hydrate branch) + GUI (HydrateGROMACSExporter.export_hydrate) tests assert CH4_H + ch4_hydrate.itp + grompp rc=0"
  - "Pattern: shared _assert_hydrate_export helper for both CLI+GUI paths — asserts files written, built-in CH4_H residue (not GUE/MOL_H), ch4_hydrate.itp staged, file consistency (assert_itp_completeness + assert_gro_top_consistent), grompp rc=0 when gmx on PATH"

# Metrics
duration: <1 min
completed: 2026-07-11
---

# Phase 45 Plan 09: Triclinic Hydrate-Only Export Summary

**Triclinic filled-ice c0te/c1te @ 4x4x4 supercell proven grompp-valid through BOTH CLI (_run_export_step hydrate branch via write_interface_*) and GUI (HydrateGROMACSExporter.export_hydrate via write_multi_molecule_*) hydrate-only export paths**

## Performance

- **Duration:** <1 min (56s)
- **Started:** 2026-07-11T05:12:47Z
- **Completed:** 2026-07-11T05:13:43Z
- **Tasks:** 2
- **Files modified:** 1 (test file created)

## Accomplishments
- Proved triclinic filled-ice hydrate-only export (c0te + c1te @ 4x4x4) produces grompp-valid output through the CLI `_run_export_step` hydrate branch (wraps HydrateStructure in InterfaceStructure + `write_interface_gro/top_file` + `copy_itp_files_for_structure`)
- Proved the same lattices produce grompp-valid output through the GUI `HydrateGROMACSExporter.export_hydrate` (uses `write_multi_molecule_gro/top_file` + `MoleculetypeRegistry`) — a DIFFERENT code path (Pitfall 6)
- Confirmed Pitfall 1 mitigation: 4x4x4 supercell expands the shortest box vector to 2.14 nm (c0te) / 2.41 nm (c1te), both > 2.0 nm grompp threshold (1x1x1 fails at ~0.54-0.61 nm)
- Empirically confirmed c1te 4x4x4 passes grompp (previously only inferred from c0te + math; not directly run before)

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Triclinic hydrate-only export @ 4x4x4 (CLI + GUI) + grompp test** - `5277cb5` (test)

**Plan metadata:** (pending — docs commit below)

## Files Created/Modified
- `tests/test_e2e_triclinic_hydrate_export.py` - Module-scoped 4x4x4 fixture for c0te+c1te + parametrized CLI (_run_export_step hydrate branch) and GUI (HydrateGROMACSExporter.export_hydrate) hydrate-only export tests with grompp rc=0 assertion (257 lines)

## Decisions Made
- Used 4x4x4 supercell for BOTH c0te and c1te (Pitfall 1) — 1x1x1 fails grompp box-size; 4x4x4 is the minimum that passes (2.14/2.41 nm > 2.0 nm)
- c1te 4x4x4 passed on the first try — no need for 5x5x5 fallback (confirmed research inference 4*0.6017=2.407 > 2.0)
- Tested CLI and GUI as SEPARATE parametrized test functions (Pitfall 6) since they use different writers (write_interface_* vs write_multi_molecule_*)
- GUI HydrateGROMACSExporter lazy-imported inside the GUI test function (NOT module top) per AGENTS.md to keep PySide6 out of the CLI test's import path
- Single atomic test commit (matching the established phase-45 pattern: one commit per test file)

## Deviations from Plan

None - plan executed exactly as written. c1te 4x4x4 passed grompp on the first attempt (no 5x5x5 fallback needed, as the plan anticipated as a contingency).

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Triclinic filled-ice hydrate-only export (c0te, c1te) now fully covered at 4x4x4 through BOTH CLI and GUI export paths with grompp validation
- Closes the TEST-08 / 47-05 filled-ice grompp gap for the triclinic filled-ice subset (c2te/ice1hte interface export covered in 45-01; c0te/c1te hydrate-only covered here)
- Together with 45-08 (triclinic blocking e2e), the triclinic filled-ice c0te/c1te lifecycle is complete: blocked at interface (45-08) + hydrate-only export grompp-valid (45-09)
- Phase 45 wave 3 (triclinic) complete; remaining plans 45-10 through 45-14 cover custom guest + depol

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
