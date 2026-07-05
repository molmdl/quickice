---
phase: 41-gromacs-export-for-custom-guests
plan: 06
subsystem: ui
tags: [gromacs, hydrate, custom-guest, gui, export, mol_h, residue-name, transform_guest_itp, branching]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: "write_multi_molecule_gro_file custom_guest_info param (plan 41-02) — GRO writer emits MOL_H for the custom guest mol_type"
  - phase: 41-gromacs-export-for-custom-guests
    provides: "write_multi_molecule_top_file custom_guest_info param (plan 41-03) — TOP writer lists MOL_H in [molecules] and merges oh/ho atomtypes via _merge_custom_atomtypes"
  - phase: 40-extended-hydrate-generation
    provides: "HydrateConfig.is_custom_guest property + guest_itp_path + guest_residue_name fields (plan 40-03); transform_guest_itp full transformation incl. [atoms] resname rewrite (plan 40-02)"
provides:
  - "HydrateGROMACSExporter.export_hydrate now branches on config.is_custom_guest — custom guests export .gro/.top/.itp without FileNotFoundError or ValueError (EXPORT-01 + EXPORT-02 + EXPORT-04 for the GUI path)"
  - "Custom-guest export threads custom_guest_info {mol_type, residue_name, itp_path} to both write_multi_molecule_gro_file and write_multi_molecule_top_file (first GUI-side consumer of the 41-02/41-03 writer APIs)"
  - "Custom-guest .itp is copied to the export dir with the FULL transform_guest_itp (moleculetype MOL_H, [atomtypes] commented, [atoms] resname MOL_H) — internally consistent with .gro/.top"
affects: [41-08-cli-hydrate-export, 41-10-grompp-validation, EXPORT-01, EXPORT-02, EXPORT-04, custom-guest-hydrate-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "is_custom_guest branch in export_hydrate: built-in path uses _get_hydrate_guest_itp_path + guest_type.upper() + registry.register_hydrate_guest; custom path uses config.guest_itp_path + config.guest_residue_name + custom_guest_info dict — two disjoint code paths sharing only the registry instance (left empty for custom)"
    - "guest_name_for_transform indirection: a single variable bound in each branch (custom: config.guest_residue_name <=3 chars; built-in: config.guest_type.upper()) so the trailing transform_guest_itp call is branch-agnostic"
    - "Manual HydrateStructure construction in tests (no GenIce2): mirror simple_hydrate_structure from conftest but with a 9-atom ethanol guest — fast (<1s) and deterministic"

key-files:
  created:
    - tests/test_output/test_gromacs_export_hydrate_custom.py
  modified:
    - quickice/gui/hydrate_export.py

key-decisions:
  - "Branch on config.is_custom_guest BEFORE the registry.register_hydrate_guest call — built-in path keeps the existing registry registration (CH4->CH4_H), custom path leaves the registry empty (writers use custom_guest_info instead); the same MoleculetypeRegistry instance is shared by both paths"
  - "Custom branch uses config.guest_itp_path directly (Path-wrapped) and raises FileNotFoundError if the file is missing — no _get_hydrate_guest_itp_path lookup that would FileNotFoundError for 'etoh_e2e' (a custom guest_type not in quickice/data/)"
  - "guest_name_for_transform = config.guest_residue_name (<=3 chars) so transform_guest_itp builds 'MOL_H' (5 chars) which passes validate_gro_residue_name — using config.guest_type.upper() ('ETOH_E2E') would yield 'ETOH_E2E_H' (8 chars) and raise ValueError"
  - "custom_guest_info dict shape kept identical to 41-02/41-03: {mol_type, residue_name, itp_path} — residue_name pre-computed as '{config.guest_residue_name}_H' so both writers receive the final 5-char GRO residue name"
  - "GUI broad 'except Exception as e: QMessageBox.critical(...)' retained per AGENTS.md (GUI code may use broad catches for user-facing workflows)"
  - "Built-in ch4/thf path unchanged (regression): same _get_hydrate_guest_itp_path call, same registry.register_hydrate_guest(guest_upper), same transform_guest_itp(guest_upper, suffix='_H') — 8/8 existing test_gromacs_export_hydrate.py tests still pass"

patterns-established:
  - "Custom-guest fixture pattern for GUI export tests: HydrateConfig(guest_type='etoh_e2e', guest_residue_name='MOL', guest_gro_path='quickice/data/custom/etoh.gro', guest_itp_path='quickice/data/custom/etoh.itp', guest_atom_labels=[...], guest_atom_count=9) + manual 17-atom HydrateStructure (2 water + 1 ethanol) — no GenIce2 dependency"
  - "Assertion vocabulary for custom-guest export: parse_gro_residue_names + parse_top_molecules + parse_top_includes (from e2e_export_helpers) for the .gro/.top side; inline _parse_moleculetype_name / _count_atomtype_occurrences / _itp_atomtypes_section_active helpers for the copied .itp side"
  - "Truth-table test style: each must-have truth from the PLAN maps 1:1 to a labeled assertion block, with a descriptive failure message naming the root cause (e.g. 'custom_guest_info was not threaded to write_multi_molecule_gro_file')"

# Metrics
duration: 2min
completed: 2026-07-05
---

# Phase 41 Plan 06: GUI Custom Guest Hydrate Export Summary

**`is_custom_guest` branch in `HydrateGROMACSExporter.export_hydrate` so a custom ethanol hydrate exports `.gro`/`.top`/`.itp` with consistent `MOL_H` names — using `config.guest_itp_path` (no `FileNotFoundError`) and `config.guest_residue_name` (no `ValueError` on `ETOH_E2E_H` = 8 chars), threading `custom_guest_info` to both `write_multi_molecule_*` writers (params from 41-02/41-03) — fixing EXPORT-01 + EXPORT-02 + EXPORT-04 for the GUI path.**

## Performance

- **Duration:** 2 min (116 s)
- **Started:** 2026-07-05T05:46:06Z
- **Completed:** 2026-07-05T05:48:02Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified GUI exporter, 1 created test file)

## Accomplishments
- Added `config.is_custom_guest` branch to `HydrateGROMACSExporter.export_hydrate` (quickice/gui/hydrate_export.py): custom guests use `config.guest_itp_path` (Path-wrapped, FileNotFoundError if missing) and `config.guest_residue_name` for the ITP transform; built-in ch4/thf path unchanged (same `_get_hydrate_guest_itp_path` + `registry.register_hydrate_guest(guest_upper)` + `transform_guest_itp(guest_upper, '_H')`).
- Threaded `custom_guest_info` dict `{"mol_type": config.guest_type, "residue_name": "MOL_H", "itp_path": Path(config.guest_itp_path)}` to both `write_multi_molecule_gro_file` and `write_multi_molecule_top_file` (params added by plans 41-02/41-03) — first GUI-side consumer of those writer APIs.
- The trailing `transform_guest_itp` call now uses the branch-bound `guest_name_for_transform` (custom: `config.guest_residue_name`; built-in: `config.guest_type.upper()`) so the custom path builds `MOL_H` (5 chars, passes `validate_gro_residue_name`) instead of `ETOH_E2E_H` (8 chars, ValueError).
- 1 GUI e2e test (`tests/test_output/test_gromacs_export_hydrate_custom.py`) covering all 6 must-have truths from the plan: export returns True, `.gro` residues `MOL_H`×9 + `SOL`×8 (no `UNK`), `.top [molecules]` `SOL:2, MOL_H:1` (no `UNK`), `.top #include` `etoh.itp` + `tip4p-ice.itp`, copied `etoh.itp` has `[moleculetype] MOL_H` + fully-commented `[atomtypes]` + `[atoms]` resname `MOL_H`, and `.top [atomtypes]` merges `oh`/`ho` from the custom ITP with `hc`/`c3`/`h1` each ≤1 (dedup).
- Zero regression: 8/8 built-in ch4 hydrate-export tests still pass (test_gromacs_export_hydrate.py).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add is_custom_guest branch to export_hydrate** - `f9f5fe3` (feat)
2. **Task 2: GUI e2e test for custom guest export** - `2c74c92` (test)

**Plan metadata:** pending — `docs(41-06)` commit follows this summary.

## Files Created/Modified
- `quickice/gui/hydrate_export.py` — Replaced the built-in-only guest ITP lookup / registry registration / `transform_guest_itp(guest_upper, ...)` block (lines 140-187) with a branch on `config.is_custom_guest`. Custom branch: `Path(config.guest_itp_path)` + `config.guest_residue_name` + `custom_guest_info` dict (registry left empty). Built-in branch: `_get_hydrate_guest_itp_path` + `registry.register_hydrate_guest(config.guest_type.upper())` + `custom_guest_info=None`. Both writers receive the `custom_guest_info` keyword. The trailing `transform_guest_itp` call uses the branch-bound `guest_name_for_transform` variable.
- `tests/test_output/test_gromacs_export_hydrate_custom.py` — New file (387 lines). One `test_export_custom_guest` test with a `custom_etoh_config` fixture (HydrateConfig for `etoh_e2e` guest, `MOL` residue name) and a `custom_etoh_structure` fixture (17-atom HydrateStructure: 2 water + 9-atom ethanol, no GenIce2). Inline helpers `_parse_moleculetype_name`, `_count_atomtype_occurrences`, `_atomtypes_block_uncommented_headers`, `_itp_atomtypes_section_active` parse the exported `.itp` / `.top` for the truth-table assertions. Reuses `mock_hydrate_save_dialog` from `tests/test_output/conftest.py` and `parse_gro_residue_names` / `parse_top_molecules` / `parse_top_includes` from `tests/e2e_export_helpers.py`.

## Decisions Made
- Branch on `config.is_custom_guest` BEFORE the `registry.register_hydrate_guest` call — built-in path keeps the existing registry registration (`CH4` → `CH4_H`), custom path leaves the registry empty (writers use `custom_guest_info` instead); the same `MoleculetypeRegistry` instance is shared by both paths (instantiated before the branch).
- Custom branch uses `config.guest_itp_path` directly (`Path`-wrapped) and raises `FileNotFoundError` if the file is missing — no `_get_hydrate_guest_itp_path` lookup that would `FileNotFoundError` for `etoh_e2e` (a custom guest_type not in `quickice/data/`).
- `guest_name_for_transform = config.guest_residue_name` (≤3 chars) so `transform_guest_itp` builds `MOL_H` (5 chars) which passes `validate_gro_residue_name` — using `config.guest_type.upper()` (`ETOH_E2E`) would yield `ETOH_E2E_H` (8 chars) and raise `ValueError`.
- `custom_guest_info` dict shape kept identical to 41-02/41-03: `{mol_type, residue_name, itp_path}` — `residue_name` pre-computed as `f"{config.guest_residue_name}_H"` so both writers receive the final 5-char GRO residue name.
- GUI broad `except Exception as e: QMessageBox.critical(...)` retained per AGENTS.md (GUI code may use broad catches for user-facing workflows).
- Built-in ch4/thf path unchanged (regression): same `_get_hydrate_guest_itp_path` call, same `registry.register_hydrate_guest(guest_upper)`, same `transform_guest_itp(guest_upper, suffix='_H')` — 8/8 existing `test_gromacs_export_hydrate.py` tests still pass.
- Manual `HydrateStructure` construction in the test (no GenIce2): mirrors `simple_hydrate_structure` from conftest but with a 9-atom ethanol guest — fast (<1s) and deterministic. The `MoleculeIndex(8, 9, "etoh_e2e")` matches the `config.guest_type` so the `custom_guest_info["mol_type"]` lookup in both writers fires.

## Deviations from Plan

None - plan executed exactly as written. The two tasks committed in order (feat, test); the verification commands all printed the expected output:
- `python -c "from quickice.gui.hydrate_export import HydrateGROMACSExporter; print('ok')"` → `ok`
- `QT_QPA_PLATFORM=offscreen pytest tests/test_output/test_gromacs_export_hydrate_custom.py -v` → 1 passed
- `QT_QPA_PLATFORM=offscreen pytest tests/test_output/test_gromacs_export_hydrate.py -q --timeout=120` → 8 passed (built-in ch4 regression)
- `python -c "...print('is_custom_guest' in src and 'guest_residue_name' in src)"` → `True`

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- GUI `export_hydrate` now produces a complete, internally-consistent custom-guest hydrate export (`.gro` MOL_H, `.top [molecules]` MOL_H + `[atomtypes]` oh/ho merged + `#include etoh.itp`, copied `etoh.itp` with `[moleculetype] MOL_H + commented [atomtypes] + [atoms] resname MOL_H`). The export is ready for `gmx grompp` validation in plan 41-10.
- Plan 41-08 (CLI hydrate export `copy_itp_files_for_structure` custom branch) can mirror the same `is_custom_guest` dispatch pattern — note 41-07 already added `copy_custom_guest_itp` to `quickice/cli/itp_helpers.py` doing the same `transform_guest_itp(content, residue_name, '_H')` transformation.
- The 6 truth-table assertions in `test_gromacs_export_hydrate_custom.py` give plan 41-10 a concrete checklist of GROMACS-level invariants to verify with `gmx grompp` (residue name match, atomtype presence, `#include` resolution).
- No blockers — built-in hydrate export (8/8) + new custom-guest test (1/1) pass; the `is_custom_guest` branch is purely additive (built-in path unchanged line-for-line modulo the shared registry instantiation moved before the branch).

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
