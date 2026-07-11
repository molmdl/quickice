---
phase: 45-e2e-hydrate-tab-workflow
plan: 11
subsystem: testing
tags: [custom-guest, ethanol, non-sI-lattices, sII, c2te, ice1hte, 16, cli-interface-export, grompp, e2e, pytest, CLIPipeline]

# Dependency graph
requires:
  - phase: 40-custom-hydrate-guest
    provides: Custom guest GenIce2 bridge (build_custom_guest_module / custom_guest_module) + HydrateConfig.is_custom_guest + guest_residue_name/gro_path/itp_path/atom_labels/atom_count fields
  - phase: 44.1-08
    provides: _build_custom_guest_info (moved to quickice/output/guest_info.py) returns list[dict] for custom guests (mol_type, residue_name with _H suffix, itp_path)
  - phase: 44.1-17
    provides: _run_export_step reads hydrate_config = getattr(self._hydrate_result, "config", None) -> _build_custom_guest_info -> custom_guest_info threaded to write_interface_gro/top_file
  - phase: 41-07
    provides: copy_itp_files_for_structure custom branch (config.is_custom_guest) copies + transforms custom etoh.itp (moleculetype MOL_H)
  - phase: 44.1-20
    provides: test_e2e_custom_guest_cross_tab_cli.py template (custom ethanol + sI + full CLI chain) mirrored by this plan
  - phase: 45-10
    provides: test_e2e_custom_guest_lattices_gui.py GUI half of Wave 4 (custom ethanol + 4 non-sI lattices GUI interface export)
  - phase: 45-RESEARCH
    provides: Empirical verification that custom ethanol generation is OK for sII/c2te/ice1hte/16 (Gap 6 = NOT tested through CLI interface + export + grompp)
provides:
  - E2E proof that a custom ethanol guest hydrate with 4 non-sI lattices (sII, c2te, ice1hte, 16) produces grompp-valid output through the CLI Interface tab export (CLIPipeline._run_export_step interface branch with _hydrate_result carrying the CUSTOM .config)
  - Proof that MOL_H (custom guest _H suffix) is correctly staged (transformed etoh.itp via copy_itp_files_for_structure) + referenced in .top [molecules] + .gro residues at the export step (no GUE fallback)
  - Module-scoped fixture pattern amortizing GenIce2 generation (~3-5s per lattice) across the 4 parametrized export cases
affects:
  - 45-e2e-hydrate-tab-workflow (phase completion)
  - 47-05 (filled-ice grompp gap — c2te/ice1hte custom guest CLI interface export now covered)

# Tech tracking
tech-stack:
  added: []  # No new libraries — test-only plan
  patterns:
    - "Custom-guest-with-non-sI-lattice CLI interface export test: module-scoped fixture builds custom ethanol hydrate (GenIce2) + slab interface ONCE per lattice, parametrized _make_cli_pipeline + _run_export_step interface branch asserts MOL_H staged + grompp rc=0"
    - "_make_cli_pipeline(ws, hydrate, '_interface_result', iface) sets _hydrate_result=hydrate (carries .config) + _interface_result=iface so _run_export_step priority selection picks the interface branch"
    - "_run_export_step reads hydrate_config = getattr(self._hydrate_result, 'config', None) -> _build_custom_guest_info(config) -> list[dict] with MOL_H threaded to write_interface_gro/top_file + copy_itp_files_for_structure"
    - "Do NOT assert exact guest counts (vary by lattice) — assert > 0 + 9 * guest_nmolecules consistency (44.1-05 fix threading guest_atom_count)"
    - "Use ETOH_GRO/ETOH_ITP absolute paths from e2e_export_helpers (CWD-independent)"

key-files:
  created:
    - tests/test_e2e_custom_guest_lattices_cli.py
  modified: []

key-decisions:
  - "Mirrored test_e2e_custom_guest_cross_tab_cli.py (44.1-20 template) swapping sI -> parametrized 4 lattices (sII, c2te, ice1hte, 16); tested CLI interface export branch ONLY (not the full interface -> solute -> ion chain) to keep the test focused and small per the plan"
  - "Used ETOH_GRO/ETOH_ITP absolute path constants from e2e_export_helpers instead of cwd-relative paths for CWD-independence (per plan IMPORTANT note + 44.1-20 convention)"
  - "Asserted guest_nmolecules > 0 + guest_atom_count == 9 * guest_nmolecules (NOT exact counts) — counts vary by lattice; the 9*consistency check confirms the 44.1-05 guest_atom_count threading fix"
  - "Single atomic test commit (matching the established phase-45 pattern: one commit per test file)"

patterns-established:
  - "Pattern: custom-guest + non-sI-lattice CLI interface export test — module-scoped fixture per lattice + parametrized _make_cli_pipeline + _run_export_step interface branch + shared _assert_custom_cli_export (SOL + MOL_H not GUE, transformed etoh.itp, file consistency, grompp rc=0)"

# Metrics
duration: 1 min
completed: 2026-07-11
---

# Phase 45 Plan 11: Custom Guest Lattices CLI Grompp Summary

**Custom ethanol guest hydrate with 4 non-sI lattices (sII, c2te, ice1hte, 16) proven grompp-valid through CLI CLIPipeline._run_export_step interface branch with _hydrate_result carrying the CUSTOM .config (MOL_H staged + referenced, no GUE fallback)**

## Performance

- **Duration:** 1 min (75s)
- **Started:** 2026-07-11T05:17:46Z
- **Completed:** 2026-07-11T05:19:01Z
- **Tasks:** 2
- **Files modified:** 1 (test file created)

## Accomplishments
- Proved that a custom ethanol guest hydrate with each of the 4 non-sI lattices (sII, c2te, ice1hte, 16) produces grompp-valid output (rc=0) through the CLI Interface tab export (`CLIPipeline._run_export_step` interface branch with `_hydrate_result` carrying the CUSTOM `.config`)
- Confirmed `MOL_H` (custom guest with `_H` suffix) is correctly staged (transformed `etoh.itp` with moleculetype `MOL_H` via `copy_itp_files_for_structure` 41-07 custom branch) + referenced in `.top [molecules]` + `.gro` residues at the export step — no `GUE` fallback (`custom_guest_info` correctly threaded via `hydrate_config` -> `_build_custom_guest_info`)
- Closed Phase 45 Gap 6 (CLI side): custom guest with non-sI lattices through CLI interface export + grompp — generation was verified OK in RESEARCH but NOT through CLI interface + export + grompp before this plan
- Together with 45-10 (GUI half), Wave 4 is complete: custom ethanol + 4 non-sI lattices proven grompp-valid through BOTH GUI and CLI interface export paths
- Amortized GenIce2 generation (~3-5s per lattice) across the 4 parametrized export cases via a module-scoped fixture (per AGENTS.md testing guidance)

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Custom ethanol + 4 non-sI lattices CLI interface export + grompp test** - `5d59629` (test)

**Plan metadata:** (pending — docs commit below)

## Files Created/Modified
- `tests/test_e2e_custom_guest_lattices_cli.py` - Module-scoped fixture building custom ethanol hydrate (GenIce2) + slab interface ONCE per lattice (sII, c2te, ice1hte, 16) + parametrized CLI `_make_cli_pipeline` + `_run_export_step` interface branch test with shared `_assert_custom_cli_export` (SOL + MOL_H not GUE, transformed etoh.itp, file consistency, grompp rc=0) (327 lines)

## Decisions Made
- Mirrored `test_e2e_custom_guest_cross_tab_cli.py` (44.1-20 template) swapping sI -> parametrized 4 lattices; tested CLI interface export branch ONLY (not the full interface -> solute -> ion chain) to keep the test focused and small per the plan
- Used `ETOH_GRO`/`ETOH_ITP` absolute path constants from `e2e_export_helpers` for CWD-independence (per plan IMPORTANT note + 44.1-20 convention)
- Asserted `guest_nmolecules > 0` + `guest_atom_count == 9 * guest_nmolecules` (NOT exact counts) — counts vary by lattice; the `9*` consistency check confirms the 44.1-05 `guest_atom_count` threading fix
- Single atomic test commit (matching the established phase-45 pattern: one commit per test file)

## Deviations from Plan

None - plan executed exactly as written. All 4 parametrized cases (sII, c2te, ice1hte, 16) passed grompp on the first run; no test fixes or source changes were needed.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Custom ethanol guest with the 4 non-sI lattices (sII, c2te, ice1hte, 16) now fully covered through CLI interface export + grompp with MOL_H staging validation
- Wave 4 complete: 45-10 (GUI half) + 45-11 (CLI half) together prove custom ethanol + 4 non-sI lattices produce grompp-valid output through BOTH GUI and CLI interface export paths
- Closes Phase 45 Gap 6 (custom guest with non-sI lattices, CLI side); together with 45-01 (new lattices interface export) + 45-03/04 (full tab chain) + 45-08/09 (triclinic) + 45-10 (GUI custom guest lattices), the lattice × custom-guest × path coverage matrix is nearly complete
- Remaining: 45-12 through 45-14 (depol CLI flag + lower-priority mixed occupancy / docs)

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
