---
phase: 41-gromacs-export-for-custom-guests
plan: 05
subsystem: testing
tags: [gromacs, top, custom-guest, hydrate, metadata-driven, p3, tdd, atomtypes-merge]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: "_merge_custom_atomtypes(f, itp_path, written, label) (plan 41-01) — shared tested merge+dedup primitive (parse → conflict-check → write-new-only → record) consumed here as the first interface-TOP consumer"
  - phase: 41-gromacs-export-for-custom-guests
    provides: "custom_guest_info dict shape {mol_type, residue_name, itp_path} (plans 41-02/41-03/41-04) — same API, now consumed by the interface TOP writer (mol_type gates the branch; residue_name → [molecules]; itp_path → merge + #include)"
  - phase: 41-gromacs-export-for-custom-guests
    provides: "InterfaceStructure.molecule_index with MoleculeIndex(start_idx, count, mol_type) — guest entry's mol_type + count drive the custom branch (mirrors 41-04)"
provides:
  - "write_interface_top_file custom_guest_info param — lets the CLI hydrate exporter (41-08) thread the custom guest residue name + mol_type + itp_path so the .top [molecules] lists MOL_H (EXPORT-01), [atomtypes] merges oh/ho + dedups hc/c3/h1 (EXPORT-03), and #includes the custom .itp filename (e.g. etoh.itp)"
  - "Metadata-driven custom-guest path in the interface TOP writer — bypasses detect_guest_type_from_atoms (returns None for ethanol → no [molecules] entry today) and the CH4 fallback atomtypes block (misses oh/ho)"
affects: [EXPORT-01, EXPORT-03, EXPORT-05, 41-08-cli-hydrate-export, 41-10-grompp-validation, cli-hydrate-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-context-dict pattern (4th consumer): custom_guest_info carries the per-mol_type residue-name override + itp_path; None falls through to the existing built-in path (detect_guest_type_from_atoms + GAFF2 atomtype blocks + '{guest_type}_hydrate.itp' #include + get_hydrate_guest_residue_name) — no regression"
    - "P3 metadata-driven identification: the custom branch is gated by `custom_active = custom_guest_info is not None and guest_atom_count>0 and guest_nmolecules>0`; the detect_guest_type_from_atoms call is wrapped in `if not custom_active:` so the custom path never invokes the heuristic (EXPORT-05)"
    - "Monkeypatch-then-call pattern to prove a code path is NOT taken (mirrors 41-04): monkeypatch detect_guest_type_from_atoms to raise AssertionError; the custom branch must NOT invoke it (test_custom_branch_skips_detect)"

key-files:
  created:
    - tests/test_output/test_interface_top_custom_guest.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "custom_guest_info is an Optional dict (default None) added as the LAST keyword param (after filepath) — backward-compatible call-site signature; existing callers (GUI export, CLI pipeline, tests) unaffected"
  - "Custom branch (custom_active) calls _merge_custom_atomtypes(f, Path(itp_path), _written_atomtypes, label) INSTEAD of the built-in ch4/thf/co2/h2 atomtype blocks or the CH4 fallback — oh/ho written, hc/c3/h1 deduped against the pre-seeded water/GAFF2 atomtypes"
  - "Custom branch #includes the custom .itp basename (Path(itp_path).name, e.g. 'etoh.itp') — matches the staging in copy_custom_guest_itp (plan 41-07) which writes the ITP to output_dir/<src.name>"
  - "Custom branch writes custom_guest_info['residue_name'] (e.g. 'MOL_H') directly in [molecules] — does NOT call get_hydrate_guest_residue_name (which would fall through to UNK for unknown mol_type)"
  - "Built-in path (ch4/thf/co2/h2 via detect + GAFF2 atomtype blocks + '{guest_type}_hydrate.itp' #include + get_hydrate_guest_residue_name) indented verbatim under elif — byte-identical for built-in guests (no regression: 14/14 interface_top/interface_gro tests pass; 107/107 tests in tests/test_output/ + tests/test_cli/ pass)"
  - "detect_guest_type_from_atoms is NOT removed (built-in path still uses it); the call is wrapped in `if not custom_active:` so the custom branch bypasses the heuristic (EXPORT-05 / P3)"

patterns-established:
  - "TDD RED-GREEN for additive writer API: RED with TypeError on missing kwarg (5 custom-guest tests fail; built-in CH4 regression test stays green throughout), GREEN by adding the param + custom branch (all 6 tests pass)"
  - "In-memory synthetic InterfaceStructure (no GenIce2) for TOP writer unit tests: 0 ice + 2 water + 1 custom ethanol guest assembled from MoleculeIndex lists; asserts [molecules]/[atomtypes]/#include invariants"
  - "_read_atomtypes_block helper in tests extracts the [ atomtypes ] section text for regex-based assertions (oh/ho present, hc/c3/h1 deduped)"

# Metrics
duration: 1min
completed: 2026-07-05
---

# Phase 41 Plan 05: P3 Custom Guest Interface TOP Summary

**Optional `custom_guest_info` dict on `write_interface_top_file` so the CLI hydrate `.top` writes `[ molecules ] MOL_H` (EXPORT-01), merges the ethanol atomtypes via `_merge_custom_atomtypes` (oh/ho written, hc/c3/h1 deduped — EXPORT-03), `#include`s the custom `etoh.itp` filename, and bypasses `detect_guest_type_from_atoms` (EXPORT-05 / P3) — instead of today's CH4 fallback block + missing `[ molecules ]` entry + `#include` gate that drops the guest entirely.**

## Performance

- **Duration:** 1 min (89 s)
- **Started:** 2026-07-05T06:31:24Z
- **Completed:** 2026-07-05T06:32:53Z
- **Tasks:** 2
- **Files modified:** 2 (1 created test file, 1 modified writer)

## Accomplishments
- Added `custom_guest_info: dict | None = None` parameter to `write_interface_top_file` (last keyword, after `filepath`), with docstring documenting the `{mol_type, residue_name, itp_path}` shape and the no-regression fall-through semantics.
- Custom branch (when `custom_active = custom_guest_info is not None and guest_atom_count>0 and guest_nmolecules>0`): merges the custom guest atomtypes via `_merge_custom_atomtypes(f, Path(itp_path), _written_atomtypes, label)` (oh/ho written, hc/c3/h1 deduped against the pre-seeded water/GAFF2 atomtypes) — replaces the CH4 fallback block that missed oh/ho (EXPORT-03).
- Custom branch: `#include "{Path(custom_guest_info['itp_path']).name}"` (e.g. `etoh.itp`) — matches the staging in `copy_custom_guest_itp` (plan 41-07) which writes the ITP to `output_dir/<src.name>`.
- Custom branch: writes `custom_guest_info['residue_name']` (e.g. `MOL_H`) directly in `[ molecules ]` — does NOT call `get_hydrate_guest_residue_name` (which would fall through to `UNK` for unknown mol_type; EXPORT-01).
- Custom branch: does NOT call `detect_guest_type_from_atoms` — the call is wrapped in `if not custom_active:` (EXPORT-05 / P3). `detect_guest_type_from_atoms` is NOT removed (built-in path still uses it).
- Built-in path (ch4/thf/co2/h2 via `detect_guest_type_from_atoms` + GAFF2 atomtype blocks + `'{guest_type}_hydrate.itp'` `#include` + `get_hydrate_guest_residue_name`) indented verbatim under `elif` — byte-identical for built-in guests (no regression).
- 6 unit tests: `MOL_H` + `SOL` in `[ molecules ]` (no `UNK`), `oh`/`ho` lines in `[ atomtypes ]`, `hc`/`c3`/`h1` each appear at most once (dedup), `etoh.itp` + `tip4p-ice.itp` in `#include`, `detect_guest_type_from_atoms` not called (monkeypatched to raise), and built-in CH4 regression (`CH4_H` + `SOL` + `ch4_hydrate.itp`).
- Zero regression: 14/14 existing `interface_top`/`interface_gro` tests pass; 107/107 tests in `tests/test_output/` + `tests/test_cli/` pass; `inspect.signature` confirms `custom_guest_info` param is present.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for custom guest interface .top (P3)** - `9fcf176` (test)
2. **Task 2: GREEN — P3 fix — metadata-driven custom guest in write_interface_top_file** - `45b80f1` (feat)

**Plan metadata:** pending — `docs(41-05)` commit follows this summary.

## Files Created/Modified
- `tests/test_output/test_interface_top_custom_guest.py` — 6 unit tests (synthetic 0-ice + 2-water + 1-custom-ethanol-guest `InterfaceStructure`; built-in CH4 regression using the `interface_with_ch4_guests` fixture). Reuses `parse_top_molecules` + `parse_top_includes` from `tests/e2e_export_helpers.py`. Uses `monkeypatch.setattr("quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom)` to prove the custom branch bypasses the heuristic. Adds a `_read_atomtypes_block` helper for regex-based `[ atomtypes ]` assertions.
- `quickice/output/gromacs_writer.py` — `write_interface_top_file` gains the `custom_guest_info` param + a `custom_active` gate; the existing guest-type detection / atomtypes block / `#include` / `[molecules]` guest entry are wrapped so the custom path is opt-in (merge + custom `#include` + custom residue name) and the built-in path is indented verbatim under `elif` (no logic change, only indentation).

## Decisions Made
- `custom_guest_info` is an Optional dict (default None) added as the LAST keyword param (after `filepath`) — backward-compatible call-site signature; existing callers (GUI `export.py`, CLI pipeline, tests) unaffected.
- Custom branch calls `_merge_custom_atomtypes(f, Path(itp_path), _written_atomtypes, label)` INSTEAD of the built-in ch4/thf/co2/h2 atomtype blocks or the CH4 fallback — oh/ho written, hc/c3/h1 deduped against the pre-seeded water/GAFF2 atomtypes.
- Custom branch `#include`s the custom `.itp` basename (`Path(itp_path).name`, e.g. `etoh.itp`) — matches the staging in `copy_custom_guest_itp` (plan 41-07) which writes the ITP to `output_dir/<src.name>`.
- Custom branch writes `custom_guest_info['residue_name']` (e.g. `MOL_H`) directly in `[ molecules ]` — does NOT call `get_hydrate_guest_residue_name` (which would fall through to `UNK` for unknown mol_type).
- Built-in path (ch4/thf/co2/h2) indented verbatim under `elif` — byte-identical for built-in guests (no regression).
- `detect_guest_type_from_atoms` is NOT removed (built-in path still uses it); the call is wrapped in `if not custom_active:` so the custom branch bypasses the heuristic (EXPORT-05 / P3).

## Deviations from Plan

None - plan executed exactly as written.

### Workflow Note (not a plan deviation)

`quickice/output/gromacs_writer.py` matches the `.gitignore` `output/` pattern but is already tracked. Plain `git add` refuses with "The following paths are ignored by one of your .gitignore files"; the commit was completed using `git add -f` (force). This is a pre-existing repo gitignore interaction already noted in the 41-02, 41-03, and 41-04 SUMMARYs; it affects all 41-02..41-05 edits to the same file.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `write_interface_top_file` now accepts `custom_guest_info` — ready for plan 41-08 (CLI hydrate exporter `_run_export_step`) to pass `{"mol_type": config.guest_type, "residue_name": "MOL_H", "itp_path": Path(config.guest_itp_path)}` when `config.is_custom_guest`. The 41-08 wiring mirrors the 41-06 GUI-side `HydrateGROMACSExporter.export_hydrate` pattern (single branch on `is_custom_guest`).
- The metadata-driven custom-guest path established here mirrors the pattern in `write_multi_molecule_gro_file` (41-02), `write_multi_molecule_top_file` (41-03), and `write_interface_gro_file` (41-04); all four writers now share the same `custom_guest_info` API and the same P3 metadata-driven identification (no `detect_guest_type_from_atoms` for custom guests).
- Plan 41-10 (`gmx grompp` validation) can now construct a custom ethanol guest hydrate `.gro` + `.top` pair where the residue name (`MOL_H`), atom count (17), atomtypes (oh/ho merged + hc/c3/h1 deduped), and `#include` (`etoh.itp`) are all consistent — the prerequisite for EXPORT-06.
- No blockers — built-in interface export (14/14) + 107 tests in `tests/test_output/` + `tests/test_cli/` pass; the `custom_guest_info` path is purely additive.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
