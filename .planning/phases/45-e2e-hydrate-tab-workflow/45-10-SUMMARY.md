---
phase: 45-e2e-hydrate-tab-workflow
plan: 10
subsystem: testing
tags: [custom-guest, ethanol, non-sI-lattices, sII, c2te, ice1hte, 16, gui-interface-export, grompp, e2e, pytest, PySide6]

# Dependency graph
requires:
  - phase: 40-custom-hydrate-guest
    provides: Custom guest GenIce2 bridge (build_custom_guest_module / custom_guest_module) + HydrateConfig.is_custom_guest + guest_residue_name/gro_path/itp_path/atom_labels/atom_count fields
  - phase: 44.1-08
    provides: _stage_hydrate_guest_itps config-driven ITP staging helper (builds custom_guest_info with MOL_H + stages transformed etoh.itp)
  - phase: 44.1-09
    provides: InterfaceGROMACSExporter.export_interface_gromacs accepts hydrate_config param + calls _stage_hydrate_guest_itps + threads custom_guest_info to write_interface_gro/top_file
  - phase: 44.1-19
    provides: test_e2e_custom_guest_cross_tab_gui.py template (custom ethanol + sI + all 4 GUI exporters) mirrored by this plan
  - phase: 45-RESEARCH
    provides: Empirical verification that custom ethanol generation is OK for sII/c2te/ice1hte/16 (Gap 6 = NOT tested through interface + export + grompp)
provides:
  - E2E proof that a custom ethanol guest hydrate with 4 non-sI lattices (sII, c2te, ice1hte, 16) produces grompp-valid output through the GUI Interface tab export (InterfaceGROMACSExporter.export_interface_gromacs with the CUSTOM hydrate_config)
  - Proof that MOL_H (custom guest _H suffix) is correctly staged (transformed etoh.itp) + referenced in .top [molecules] + .gro residues at every export step (no GUE fallback)
  - Module-scoped fixture pattern amortizing GenIce2 generation (~3-5s per lattice) across the 4 parametrized export cases
affects:
  - 45-e2e-hydrate-tab-workflow (phase completion)
  - 47-05 (filled-ice grompp gap — c2te/ice1hte custom guest interface export now covered)

# Tech tracking
tech-stack:
  added: []  # No new libraries — test-only plan
  patterns:
    - "Custom-guest-with-non-sI-lattice GUI interface export test: module-scoped fixture builds custom ethanol hydrate (GenIce2) + slab interface ONCE per lattice, parametrized InterfaceGROMACSExporter.export_interface_gromacs(hydrate_config=chain.config) asserts MOL_H staged + grompp rc=0"
    - "Pass hydrate_config=chain.config (the CUSTOM HydrateConfig) NOT None so _stage_hydrate_guest_itps reads config.is_custom_guest -> True -> builds custom_guest_info with MOL_H + stages transformed etoh.itp"
    - "Do NOT assert exact guest counts (vary by lattice) — assert > 0 + 9 * guest_nmolecules consistency (44.1-05 fix threading guest_atom_count)"
    - "Use ETOH_GRO/ETOH_ITP absolute paths from e2e_export_helpers (CWD-independent) instead of the template's relative quickice/data/custom/etoh.{gro,itp} paths"

key-files:
  created:
    - tests/test_e2e_custom_guest_lattices_gui.py
  modified: []

key-decisions:
  - "Mirrored test_e2e_custom_guest_cross_tab_gui.py (44.1-19 template) swapping sI -> parametrized 4 lattices (sII, c2te, ice1hte, 16); tested interface export ONLY (not all 4 exporters) to keep the test focused and small per the plan"
  - "Used ETOH_GRO/ETOH_ITP absolute path constants from e2e_export_helpers instead of the template's cwd-relative quickice/data/custom/etoh.{gro,itp} paths for CWD-independence (per plan IMPORTANT note)"
  - "Asserted guest_nmolecules > 0 + guest_atom_count == 9 * guest_nmolecules (NOT exact counts) — counts vary by lattice; the 9*consistency check confirms the 44.1-05 guest_atom_count threading fix"
  - "Single atomic test commit (matching the established phase-45 pattern: one commit per test file)"

patterns-established:
  - "Pattern: custom-guest + non-sI-lattice GUI interface export test — module-scoped fixture per lattice + parametrized export_interface_gromacs(hydrate_config=custom_config) + shared _assert_custom_guest_export (SOL + MOL_H not GUE, transformed etoh.itp, file consistency, grompp rc=0)"

# Metrics
duration: 1 min
completed: 2026-07-11
---

# Phase 45 Plan 10: Custom Guest Lattices GUI Grompp Summary

**Custom ethanol guest hydrate with 4 non-sI lattices (sII, c2te, ice1hte, 16) proven grompp-valid through GUI InterfaceGROMACSExporter.export_interface_gromacs with the CUSTOM hydrate_config (MOL_H staged + referenced, no GUE fallback)**

## Performance

- **Duration:** 1 min (83s)
- **Started:** 2026-07-11T05:15:14Z
- **Completed:** 2026-07-11T05:16:37Z
- **Tasks:** 2
- **Files modified:** 1 (test file created)

## Accomplishments
- Proved that a custom ethanol guest hydrate with each of the 4 non-sI lattices (sII, c2te, ice1hte, 16) produces grompp-valid output (rc=0) through the GUI Interface tab export (`InterfaceGROMACSExporter.export_interface_gromacs` called with the CUSTOM `hydrate_config`)
- Confirmed `MOL_H` (custom guest with `_H` suffix) is correctly staged (transformed `etoh.itp` with moleculetype `MOL_H`) + referenced in `.top [molecules]` + `.gro` residues at every export step — no `GUE` fallback (custom_guest_info correctly threaded via `hydrate_config`)
- Closed Phase 45 Gap 6 (custom guest with non-sI lattices through GUI interface export + grompp) — generation was verified OK in RESEARCH but NOT through interface + export + grompp before this plan
- Amortized GenIce2 generation (~3-5s per lattice) across the 4 parametrized export cases via a module-scoped fixture (per AGENTS.md testing guidance)

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Custom ethanol + 4 non-sI lattices GUI interface export + grompp test** - `36fc505` (test)

**Plan metadata:** (pending — docs commit below)

## Files Created/Modified
- `tests/test_e2e_custom_guest_lattices_gui.py` - Module-scoped fixture building custom ethanol hydrate (GenIce2) + slab interface ONCE per lattice (sII, c2te, ice1hte, 16) + parametrized GUI `InterfaceGROMACSExporter.export_interface_gromacs(hydrate_config=chain.config)` test with shared `_assert_custom_guest_export` (SOL + MOL_H not GUE, transformed etoh.itp, file consistency, grompp rc=0) (292 lines)

## Decisions Made
- Mirrored `test_e2e_custom_guest_cross_tab_gui.py` (44.1-19 template) swapping sI -> parametrized 4 lattices; tested interface export ONLY (not all 4 exporters) to keep the test focused and small per the plan
- Used `ETOH_GRO`/`ETOH_ITP` absolute path constants from `e2e_export_helpers` instead of the template's cwd-relative `quickice/data/custom/etoh.{gro,itp}` paths for CWD-independence (per plan IMPORTANT note)
- Asserted `guest_nmolecules > 0` + `guest_atom_count == 9 * guest_nmolecules` (NOT exact counts) — counts vary by lattice; the `9*` consistency check confirms the 44.1-05 `guest_atom_count` threading fix
- Single atomic test commit (matching the established phase-45 pattern: one commit per test file)

## Deviations from Plan

None - plan executed exactly as written. All 4 parametrized cases (sII, c2te, ice1hte, 16) passed grompp on the first run; no test fixes or source changes were needed.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Custom ethanol guest with the 4 non-sI lattices (sII, c2te, ice1hte, 16) now fully covered through GUI interface export + grompp with MOL_H staging validation
- Closes Phase 45 Gap 6 (custom guest with non-sI lattices); together with 45-01 (new lattices interface export) + 45-03/04 (full tab chain) + 45-08/09 (triclinic), the lattice × custom-guest coverage matrix is nearly complete
- Remaining: 45-11 through 45-14 (depol CLI flag + lower-priority mixed occupancy / docs)

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
