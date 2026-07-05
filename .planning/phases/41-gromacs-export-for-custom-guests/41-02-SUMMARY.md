---
phase: 41-gromacs-export-for-custom-guests
plan: 02
subsystem: testing
tags: [gromacs, gro, residue-name, custom-guest, hydrate, tdd]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: "_merge_custom_atomtypes shared helper (plan 41-01) — not used by this GRO writer but part of the same EXPORT-04 wave"
  - phase: 38-gro-resname-validation
    provides: "validate_gro_residue_name (5-char limit) still enforced on every residue path"
  - phase: 40-hydrate-config-custom
    provides: "HydrateConfig.guest_residue_name / is_custom_guest concept — the GUI exporter (41-06) will read these to build custom_guest_info"
provides:
  - "write_multi_molecule_gro_file custom_guest_info param — lets callers (GUI hydrate exporter 41-06) thread the custom guest residue name (e.g. 'MOL_H') so the .gro residues match the .top [molecules] entry and gmx grompp does not FATAL"
  - "Consistent custom_guest_info dict shape {mol_type, residue_name, itp_path} shared by plans 41-02..41-05 (itp_path unused by GRO writer, consumed by TOP writers for atomtypes merge)"
affects: [EXPORT-04, 41-06-gui-hydrate-export, 41-03-multi-molecule-top, 41-04-interface-top, 41-05-custom-guest-itp-include, cli-hydrate-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-context-dict pattern: custom_guest_info carries the per-mol_type override; None or mol_type-mismatch falls through to the existing built-in/registry path (no regression)"
    - "Single consistent API dict shape {mol_type, residue_name, itp_path} reused across the GRO writer (41-02) and TOP writers (41-03/41-04/41-05) — itp_path unused here but kept for caller simplicity"

key-files:
  created:
    - tests/test_output/test_multi_molecule_gro_custom_guest.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "custom_guest_info is an Optional dict (default None) added as the LAST keyword param (after registry) — backward-compatible call-site signature, existing callers unaffected"
  - "Custom-guest branch inserted INSIDE the existing 'if res_name is None:' chain (custom_guest_info -> elif built-in ch4/thf/co2/h2 -> else UNK), so the registry path still wins when present and the built-in guest path still wins for known guest mol_types"
  - "itp_path is carried on the dict but unused by this GRO writer (only the TOP writers read it for the atomtypes merge) — kept for a single consistent API across plans 41-02..41-05"
  - "validate_gro_residue_name(res_name, context=...) still called unconditionally — 'MOL_H' (5 chars) passes; the custom path does not bypass the 5-char GRO format limit"

patterns-established:
  - "TDD RED-GREEN for additive API: RED with TypeError on missing kwarg (2 custom-guest tests), GREEN by adding the param + branch (built-in regression test stayed green throughout)"
  - "In-memory synthetic system (no GenIce2) for writer unit tests: 2 water + 1 custom ethanol guest assembled from MoleculeIndex + atom_names lists"

# Metrics
duration: 2min
completed: 2026-07-05
---

# Phase 41 Plan 02: Custom Guest GRO Residue Name Summary

**Optional `custom_guest_info` dict on `write_multi_molecule_gro_file` so the GUI hydrate exporter can thread the custom guest residue name (`MOL_H`) instead of the writer falling through to `UNK` — fixing the grompp FATAL where `.gro` residues mismatch `.top [molecules]`.**

## Performance

- **Duration:** 2 min (169 s)
- **Started:** 2026-07-05T05:28:04Z
- **Completed:** 2026-07-05T05:30:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `custom_guest_info: dict | None = None` parameter to `write_multi_molecule_gro_file` (last keyword, after `registry`), with docstring documenting the `{mol_type, residue_name, itp_path}` shape and the no-regression fall-through semantics.
- Inserted the custom-guest branch before the `else: ... UNK` fallback in the per-molecule residue-name resolution: when `custom_guest_info` is non-None and `mol.mol_type == custom_guest_info["mol_type"]`, the writer emits `custom_guest_info["residue_name"]` (e.g. `MOL_H`); otherwise the built-in registry / `get_guest_residue_name` / `MOLECULE_TO_GROMACS` path is unchanged.
- 4 unit tests covering the custom-guest path (custom → `MOL_H`, water → `SOL`), the built-in regression path (CH4 → `CH4_H` via `MoleculetypeRegistry.register_hydrate_guest("CH4")`, no `UNK`), and the `validate_gro_residue_name` 5-char limit (`MOL_H` passes).
- All 8 built-in hydrate-export regression tests + 33 related GRO/ordering/resname-validation tests still pass — zero regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing test for custom guest GRO residue name** - `f00326b` (test)
2. **Task 2: GREEN — thread custom_guest_info into write_multi_molecule_gro_file** - `7648848` (feat)

**Plan metadata:** pending — `docs(41-02)` commit follows this summary.

## Files Created/Modified
- `tests/test_output/test_multi_molecule_gro_custom_guest.py` — 4 unit tests (synthetic 2-water + 1-custom-ethanol-guest system; built-in CH4 regression; validate limit assertion). Reuses `parse_gro_residue_names` from `tests/e2e_export_helpers.py` (already present).
- `quickice/output/gromacs_writer.py` — `write_multi_molecule_gro_file` gains `custom_guest_info` param + 3-branch residue-name resolution (custom → built-in guest → UNK fallback); `validate_gro_residue_name` still enforced on every path.

## Decisions Made
- `custom_guest_info` is an Optional dict (default None) added as the LAST keyword param (after `registry`) — backward-compatible call-site signature, existing callers unaffected.
- Custom-guest branch inserted INSIDE the existing `if res_name is None:` chain (custom_guest_info → elif built-in ch4/thf/co2/h2 → else UNK), so the registry path still wins when present and the built-in guest path still wins for known guest mol_types.
- `itp_path` is carried on the dict but unused by this GRO writer (only the TOP writers read it for the atomtypes merge) — kept for a single consistent API across plans 41-02..41-05.
- `validate_gro_residue_name(res_name, context=...)` still called unconditionally — `MOL_H` (5 chars) passes; the custom path does not bypass the 5-char GRO format limit.

## Deviations from Plan

None - plan executed exactly as written. The RED phase behaved exactly as the plan's `<done>` criteria predicted ("custom-guest test fails because writer emits 'UNK' (or rejects the unknown kwarg)" — the custom-guest tests failed with `TypeError: unexpected keyword argument 'custom_guest_info'`), and the GREEN phase made all 4 tests pass with zero regression.

### Workflow Note (not a plan deviation)

`quickice/output/gromacs_writer.py` matches the `.gitignore` pattern `output/` (line 215). Although the file is already tracked (`git ls-files` confirms), plain `git add quickice/output/gromacs_writer.py` refused with "The following paths are ignored by one of your .gitignore files". The commit was completed using `git add -f` (force), which correctly staged the tracked file. Subsequent plans editing `quickice/output/gromacs_writer.py` (41-03..41-05) will need the same `-f` flag — this is a pre-existing repo gitignore interaction, not a change introduced by this plan.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `write_multi_molecule_gro_file` now accepts `custom_guest_info` — ready for plan 41-06 (GUI hydrate exporter `export_hydrate`) to pass `{"mol_type": config.guest_type, "residue_name": "MOL_H", "itp_path": Path(config.guest_itp_path)}`.
- The dict shape `{mol_type, residue_name, itp_path}` is fixed for plans 41-03 (write_multi_molecule_top_file), 41-04 (write_interface_top_file), and 41-05 (custom guest ITP #include) — those TOP writers will consume `itp_path` for the atomtypes merge (reusing the `_merge_custom_atomtypes` helper from 41-01).
- No blockers — built-in hydrate export (8/8) and related GRO/ordering/resname tests (33/33) pass; the `custom_guest_info` path is purely additive.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
