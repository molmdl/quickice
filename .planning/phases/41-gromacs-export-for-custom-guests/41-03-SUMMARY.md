---
phase: 41-gromacs-export-for-custom-guests
plan: 03
subsystem: testing
tags: [gromacs, top, atomtypes, custom-guest, hydrate, merge, dedup, tdd]

# Dependency graph
requires:
  - phase: 41-gromacs-export-for-custom-guests
    provides: "_merge_custom_atomtypes(f, itp_path, written, label) shared merge+dedup helper (plan 41-01) — consumed here for the [atomtypes] merge"
  - phase: 41-gromacs-export-for-custom-guests
    provides: "custom_guest_info dict shape {mol_type, residue_name, itp_path} (plan 41-02) — same API, now consumed by the TOP writer (itp_path used here for the atomtypes merge)"
provides:
  - "write_multi_molecule_top_file custom_guest_info param — lets the GUI hydrate exporter (41-06) thread the custom guest residue name + itp_path so [molecules] lists MOL_H (EXPORT-01) and [atomtypes] merges oh/ho with dedup (EXPORT-03)"
  - "First writer-side consumption of _merge_custom_atomtypes (41-01) — validates the shared helper integrates cleanly with the _written_atomtypes dedup dict seeded by water/ion/GAFF2 blocks"
affects: [EXPORT-01, EXPORT-03, 41-06-gui-hydrate-export, 41-04-interface-top, 41-05-custom-guest-itp-include, 41-10-grompp-validation, cli-hydrate-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-context-dict pattern: custom_guest_info carries the per-mol_type residue-name override + itp_path for atomtypes merge; None or mol_type-mismatch falls through to the existing built-in/registry path (no regression)"
    - "Atomtypes-merge placement invariant: custom merge written AFTER built-in GAFF2 blocks (ch4/thf/co2/h2) and BEFORE the #include block, so all [atomtypes] (water+ion+GAFF2+custom) precede molecule definitions (GROMACS ordering invariant, research Pitfall 3)"
    - "Reusing _merge_custom_atomtypes (41-01) as the single merge+dedup primitive — no inline parse/conflict-check/record logic in the writer (DRY vs. the triplicated inline pattern in write_custom_molecule_top_file / write_ion_top_file)"

key-files:
  created:
    - tests/test_output/test_multi_molecule_top_custom_guest.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "custom_guest_info is an Optional dict (default None) added as the LAST keyword param (after registry) — backward-compatible call-site signature; existing callers (GUI hydrate_export.py, tests) unaffected"
  - "Custom-guest residue-name branch inserted INSIDE the existing 'if res_name is None:' chain (custom_guest_info -> elif built-in ch4/thf/co2/h2 -> else UNK) so the registry path still wins when present and the built-in guest path still wins for known guest mol_types"
  - "Atomtypes merge placed AFTER the h2 GAFF2 block and BEFORE the '\\n' + '; Molecule definitions' / #include block — guarantees all [atomtypes] precede #include (GROMACS ordering invariant)"
  - "#include for the custom .itp is produced by the EXISTING itp_files mechanism (unchanged) — plan does NOT add a second #include"
  - "custom_guest_info.get('itp_path') guard: merge is a no-op when itp_path is falsy (None/empty), so a caller with a residue name but no ITP path still gets only the residue-name fix"

patterns-established:
  - "TDD RED-GREEN for additive writer API: RED with TypeError on missing kwarg (5 custom-guest tests fail), GREEN by adding the param + residue branch + merge call (built-in CH4 regression test stayed green throughout)"
  - "In-memory synthetic system (no GenIce2) for TOP writer unit tests: 2 water + 1 custom ethanol guest assembled from MoleculeIndex lists; itp_files maps the custom mol_type to its .itp filename"
  - "Atomtypes-block slicing helper in tests: text.index('[ atomtypes ]') to text.find('\\n[ ', ...) isolates the [atomtypes] section for first-token / regex token-count assertions"

# Metrics
duration: 2min
completed: 2026-07-05
---

# Phase 41 Plan 03: Custom Guest TOP Molecules + Atomtypes Merge Summary

**Optional `custom_guest_info` dict on `write_multi_molecule_top_file` so the GUI hydrate `.top` lists the custom guest as `MOL_H` in `[molecules]` (EXPORT-01) and merges its GAFF2 atomtypes (`oh`/`ho`) into `[atomtypes]` with dedup via `_merge_custom_atomtypes` (41-01) (EXPORT-03) — fixing the grompp "Unknown atomtype" FATAL for custom-guest hydrate exports.**

## Performance

- **Duration:** 2 min (148 s)
- **Started:** 2026-07-05T05:33:57Z
- **Completed:** 2026-07-05T05:36:25Z
- **Tasks:** 2
- **Files modified:** 2 (1 created test file, 1 modified writer)

## Accomplishments
- Added `custom_guest_info: dict | None = None` parameter to `write_multi_molecule_top_file` (last keyword, after `registry`), with docstring documenting the `{mol_type, residue_name, itp_path}` shape and the no-regression fall-through semantics.
- `[molecules]`: inserted a custom-guest branch before the built-in/`UNK` fallback — when `custom_guest_info` is non-None and `mol_type == custom_guest_info["mol_type"]`, the writer emits `custom_guest_info["residue_name"]` (e.g. `MOL_H`) with the correct count (EXPORT-01; was `UNK`).
- `[atomtypes]`: calls `_merge_custom_atomtypes` (from plan 41-01) to merge the custom guest's atomtypes with dedup — `oh`/`ho` are written (new), `hc`/`c3`/`h1` are deduped against already-written types (EXPORT-03; was: no custom atomtypes → grompp "Unknown atomtype").
- Merge placement invariant: the custom merge is written AFTER the built-in GAFF2 blocks (ch4/thf/co2/h2) and BEFORE the `\n` + `; Molecule definitions` / `#include` block, so all `[atomtypes]` (water+ion+GAFF2+custom) precede molecule definitions (GROMACS ordering invariant).
- 6 unit tests: `[molecules]` `MOL_H`, `[atomtypes]` `oh`/`ho`, `hc`/`c3`/`h1` dedup (≤1), `#include etoh.itp` + `tip4p-ice.itp`, atomtypes-before-`#include` ordering, and a built-in CH4 regression (no `custom_guest_info`).
- Zero regression: 8/8 built-in hydrate-export tests + 44 related GROMACS writer tests (moleculetype names, scancode bugs, TIP4P-ICE LJ values, `_merge_custom_atomtypes` helper) still pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for custom guest .top merge** - `4796363` (test)
2. **Task 2: GREEN — thread custom_guest_info + atomtypes merge into write_multi_molecule_top_file** - `fef7c29` (feat)

**Plan metadata:** pending — `docs(41-03)` commit follows this summary.

## Files Created/Modified
- `tests/test_output/test_multi_molecule_top_custom_guest.py` — 6 unit tests (synthetic 2-water + 1-custom-ethanol-guest system; built-in CH4 regression). Reuses `parse_top_molecules` + `parse_top_includes` from `tests/e2e_export_helpers.py`. Uses a cwd-independent absolute `_ETOH_ITP` path (same convention as `test_merge_custom_atomtypes.py` in this directory) because the TOP writer opens `itp_path` via `parse_itp_atomtypes`.
- `quickice/output/gromacs_writer.py` — `write_multi_molecule_top_file` gains the `custom_guest_info` param + a 3-branch residue-name resolution (custom → built-in guest → UNK fallback) in the `molecules_lines` loop, plus a `_merge_custom_atomtypes` call placed between the h2 GAFF2 block and the `#include` block.

## Decisions Made
- `custom_guest_info` is an Optional dict (default None) added as the LAST keyword param (after `registry`) — backward-compatible call-site signature; existing callers (GUI `hydrate_export.py`, tests) unaffected.
- Custom-guest residue-name branch inserted INSIDE the existing `if res_name is None:` chain (custom_guest_info → elif built-in ch4/thf/co2/h2 → else UNK), so the registry path still wins when present and the built-in guest path still wins for known guest mol_types.
- Atomtypes merge placed AFTER the h2 GAFF2 block and BEFORE the `\n` + `; Molecule definitions` / `#include` block — guarantees all `[atomtypes]` precede `#include` (GROMACS ordering invariant).
- `#include` for the custom `.itp` is produced by the EXISTING `itp_files` mechanism (unchanged) — plan does NOT add a second `#include`.
- `custom_guest_info.get("itp_path")` guard: the merge is a no-op when `itp_path` is falsy (None/empty), so a caller with a residue name but no ITP path still gets only the residue-name fix.

## Deviations from Plan

None - plan executed exactly as written. The RED phase behaved exactly as the plan's `<done>` criteria predicted (tests 1-5 failed with `TypeError: write_multi_molecule_top_file() got an unexpected keyword argument 'custom_guest_info'`; test 6 — built-in CH4 regression — passed), and the GREEN phase made all 6 tests pass with zero regression.

### Workflow Note (not a plan deviation)

`quickice/output/gromacs_writer.py` matches the `.gitignore` `output/` pattern but is already tracked. Plain `git add` refuses with "The following paths are ignored by one of your .gitignore files"; the commit was completed using `git add -f` (force). This is a pre-existing repo gitignore interaction already noted in the 41-02 SUMMARY; it affects all 41-03..41-05 edits to the same file.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `write_multi_molecule_top_file` now accepts `custom_guest_info` — ready for plan 41-06 (GUI hydrate exporter `export_hydrate`) to pass `{"mol_type": config.guest_type, "residue_name": "MOL_H", "itp_path": Path(config.guest_itp_path)}`.
- First writer-side consumption of `_merge_custom_atomtypes` (41-01) validates the shared helper integrates cleanly; plan 41-04 (CLI `write_interface_top_file`) can adopt the same pattern.
- Plan 41-10 (`gmx grompp` validation) can now construct a custom ethanol guest hydrate `.top` that defines `oh`/`ho` — the prerequisite for EXPORT-06.
- No blockers — built-in hydrate export (8/8) + 44 related writer tests pass; the `custom_guest_info` path is purely additive.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
