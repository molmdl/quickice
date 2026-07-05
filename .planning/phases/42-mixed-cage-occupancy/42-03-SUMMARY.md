---
phase: 42-mixed-cage-occupancy
plan: 03
subsystem: output
tags: [gromacs, hydrate, multi-guest, custom-guest, atomtypes-merge, dedup, deprecation, backward-compat]

# Dependency graph
requires:
  - phase: 41-hydrate-custom-guest-export/41-02
    provides: write_multi_molecule_gro_file custom_guest_info: dict | None param + dict shape {mol_type, residue_name, itp_path} — promoted to list[dict] here
  - phase: 41-hydrate-custom-guest-export/41-03
    provides: write_multi_molecule_top_file custom_guest_info dict (first _merge_custom_atomtypes consumer) — promoted to list[dict] + looped merge here
  - phase: 41-hydrate-custom-guest-export/41-04
    provides: write_interface_gro_file custom_guest_info dict + chunk-by-molecule_index .count — promoted to list[dict] + custom_by_moltype here
  - phase: 41-hydrate-custom-guest-export/41-05
    provides: write_interface_top_file custom_guest_info dict + _merge_custom_atomtypes + #include + [molecules] — promoted to list[dict] + looped merge here
  - phase: 41-hydrate-custom-guest-export/41-01
    provides: _merge_custom_atomtypes(f, itp_path, written, label) shared merge+dedup primitive — UNCHANGED, only called in a loop here
  - phase: 42-mixed-cage-occupancy/42-02
    provides: Multi-guest molecule_index with distinct MoleculeIndex.mol_type per guest type (resname_to_moltype dict) — the per-mol_type dict lookup this plan consumes via custom_by_moltype
provides:
  - All four hydrate GROMACS writers accept custom_guest_info: list[dict] | None (one dict per custom guest)
  - custom_by_moltype dict drives res_name resolution in [molecules] and .gro residue name loops (replaces single-dict match)
  - _merge_custom_atomtypes called in a loop over each custom guest ITP with _written_atomtypes accumulating across guests (shared atomtypes e.g. hc written once)
  - DeprecationWarning + 1-element wrap for legacy single-dict callers (transition safety through 42-05/42-07, not silent wrong output)
  - Multi-guest writer unit tests (synthetic 22-atom 2-water + 1-CH4 + 1-ethanol fixture, no GenIce2, <1s per test)
affects: [42-05 interface-writers, 42-06 gui-hydrate-panel, 42-07 cli-pipeline, 44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern 5: list[dict] custom_guest_info API — custom_by_moltype dict (mol_type → ci) built ONCE before the per-molecule / per-mol_type loop drives O(1) res_name resolution for N custom guests with no loop-structure change to [molecules] or #include (they already iterated unique_types)"
    - "Looped atomtypes merge: `for ci in (custom_guest_info or []): if ci.get('itp_path'): _merge_custom_atomtypes(...)` with _written_atomtypes dict accumulating across guests → shared atomtypes (e.g. hc across two custom ITPs) written only once (Don't Hand-Roll table)"
    - "DeprecationWarning + wrap for legacy single-dict callers: `isinstance(custom_guest_info, dict)` guard at the top of each writer wraps to [custom_guest_info] with stacklevel=2 — transition safety, not silent wrong output (42-05/42-07 update all call sites to pass lists)"

key-files:
  created: []
  modified:
    - quickice/output/gromacs_writer.py
    - tests/test_output/test_gromacs_export_hydrate.py

key-decisions:
  - "custom_by_moltype dict built ONCE before the per-molecule loop (write_multi_molecule_gro_file) / per-mol_type loop (write_multi_molecule_top_file) — replaces the single-dict `mol.mol_type == custom_guest_info['mol_type']` match with `mol.mol_type in custom_by_moltype` so N custom guests each resolve via their own entry in O(1) per molecule."
  - "write_interface_gro_file / write_interface_top_file resolve the single guest stream via `next(m for m in iface.molecule_index if m.mol_type in custom_by_moltype)` — the interface carries ONE guest stream, so only one custom_by_moltype entry matches a molecule_index entry; defensive fallback to `next(iter(custom_by_moltype.values()))` when molecule_index lacks a match (caller is expected to keep them consistent)."
  - "Looped atomtypes merge: `for ci in (custom_guest_info or []): if ci.get('itp_path')` — _written_atomtypes accumulates across guests so shared atomtypes (hc, c3, h1) are written only once. _merge_custom_atomtypes itself is UNCHANGED (shared primitive, [41-01]); only the call site loops."
  - "DeprecationWarning + wrap for legacy single-dict callers — isinstance(custom_guest_info, dict) guard at the top of each of the 4 writers wraps to [custom_guest_info] with stacklevel=2. The plan's DECIDE: 'since 42-05/42-07 will update all call sites to pass lists, a single dict is no longer valid' — chose graceful handling (wrap + warn) over hard break so any MISSED call site still produces correct output during the transition, not silent wrong output."
  - "custom_active for the interface writers keeps `is not None` AND adds `len(custom_guest_info) > 0` — a non-empty list is truthy, but the explicit len check makes the empty-list equivalence with None self-documenting (None or [] → custom_active=False → built-in path byte-identical)."
  - "Test fixture: synthetic 22-atom mixed HydrateStructure (2 water + 1 CH4 + 1 etoh_mix) built manually — no GenIce2 — fast <1s per test. Mirrors the 41-06 17-atom 2-water + 1-ethanol pattern but adds a 5-atom built-in CH4 so both the registry path (CH4 → CH4_H) and the custom_guest_info path (etoh_mix → MOL_H) fire in the same test."

patterns-established:
  - "list[dict] custom_guest_info API across all 4 hydrate writers (replaces Phase 41's dict | None)"
  - "custom_by_moltype dict for O(1) multi-guest res_name resolution (built once before the per-molecule loop)"
  - "Looped _merge_custom_atomtypes with _written_atomtypes accumulating across guests (dedup across multiple custom ITPs)"
  - "DeprecationWarning + 1-element wrap for legacy single-dict callers (transition safety, stacklevel=2)"

# Metrics
duration: 5 min
completed: 2026-07-05
---

# Phase 42 Plan 03: Mixed Cage Occupancy GROMACS Writers Summary

**All four hydrate GROMACS writers promoted to list[dict] custom_guest_info with custom_by_moltype-driven res_name resolution and looped atomtypes merge (dedup across multiple custom ITPs), plus a DeprecationWarning wrap for legacy single-dict callers — built-in single-guest export byte-identical.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-05T08:28:52Z
- **Completed:** 2026-07-05T08:34:10Z
- **Tasks:** 2
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments
- Promoted all four hydrate GROMACS writers (`write_multi_molecule_gro_file`, `write_multi_molecule_top_file`, `write_interface_gro_file`, `write_interface_top_file`) from `custom_guest_info: dict | None` to `custom_guest_info: list[dict] | None` — one dict per custom guest. The `[molecules]` and `#include` loops already iterated `unique_types`, so no loop-structure change was needed; only `res_name` resolution and the atomtypes merge needed list-awareness (Pattern 5).
- Introduced `custom_by_moltype = {ci["mol_type"]: ci for ci in (custom_guest_info or [])}` built ONCE before the per-molecule / per-mol_type loop in each writer. This drives O(1) res_name resolution for N custom guests: `if mol.mol_type in custom_by_moltype: res_name = custom_by_moltype[mol.mol_type]["residue_name"]`. The built-in `elif mol.mol_type in ["ch4","thf","co2","h2"]:` and `else` (UNK) branches are UNCHANGED — no hardcoded built-in gates that would exclude custom mol_types (Pitfall avoided).
- Looped the atomtypes merge in `write_multi_molecule_top_file` and `write_interface_top_file`: `for ci in (custom_guest_info or []): if ci.get("itp_path"): _merge_custom_atomtypes(f, Path(ci["itp_path"]), _written_atomtypes, f"custom guest {ci['mol_type']} atom types")`. The `_written_atomtypes` dict accumulates across guests → shared atomtypes (e.g. `hc` in two custom ITPs) are written only once (Don't Hand-Roll table). `_merge_custom_atomtypes` itself is UNCHANGED (shared primitive, [41-01]).
- Added a `DeprecationWarning` + 1-element wrap guard at the top of each of the 4 writers: `isinstance(custom_guest_info, dict)` → wrap to `[custom_guest_info]` with `stacklevel=2`. Legacy single-dict callers (e.g. `quickice/cli/pipeline.py::_build_custom_guest_info` + the 41-10/41-11 e2e tests) still produce correct output during the transition; 42-05/42-07 will update all call sites to pass lists, after which the guard can be removed.
- Extended `tests/test_output/test_gromacs_export_hydrate.py` with a `TestMultiGuestWriter` class (4 new tests) using a synthetic 22-atom mixed `HydrateStructure` (2 water + 1 CH4 + 1 etoh_mix) built manually — no GenIce2 — fast <1s per test. Tests prove: (1) `.top [molecules]` lists SOL:2 + CH4_H:1 (registry) + MOL_H:1 (custom); (2) `.gro` has SOL (8 atoms) + CH4_H (5 atoms) + MOL_H (9 atoms) + `assert_gro_top_consistent` cross-check; (3) `custom_guest_info=None` is equivalent to empty list (built-in path fires unchanged; etoh_mix falls through to UNK — no regression); (4) a legacy single `dict` emits `DeprecationWarning` + wraps to a 1-element list for all 4 writers (transition safety).

## Task Commits

Each task was committed atomically:

1. **Task 1: Change 4 writers to list[dict] custom_guest_info + custom_by_moltype resolution + looped atomtypes merge** — `aff7c63` (feat)
2. **Task 2: Multi-guest writer unit tests** — `04c0530` (test)

**Plan metadata:** _(pending final docs commit)_

## Files Created/Modified
- `quickice/output/gromacs_writer.py` — Added `import warnings`. `write_multi_molecule_gro_file`: signature → `custom_guest_info: list[dict] | None`; DeprecationWarning + wrap guard; `custom_by_moltype` dict built before the `for res_idx, mol in enumerate(molecule_index):` loop; `if mol.mol_type in custom_by_moltype:` replaces single-dict match. `write_multi_molecule_top_file`: signature → list[dict]; DeprecationWarning + wrap guard; `custom_by_moltype` built before the `for mol_type in unique_types:` loop; `if mol_type in custom_by_moltype:` replaces single-dict match; atomtypes merge looped `for ci in (custom_guest_info or []):`. `write_interface_gro_file`: signature → list[dict]; DeprecationWarning + wrap guard; custom branch builds `custom_by_moltype` and resolves the single guest stream via `next(m for m in iface.molecule_index if m.mol_type in custom_by_moltype)`; built-in `else` branch byte-identical. `write_interface_top_file`: signature → list[dict]; DeprecationWarning + wrap guard; `custom_active` adds `len(custom_guest_info) > 0` check; `custom_by_moltype` built once; atomtypes merge looped; `#include` looped over `custom_guest_info`; `[molecules]` resolves via `custom_by_moltype` + molecule_index match; built-in `elif` branch byte-identical.
- `tests/test_output/test_gromacs_export_hydrate.py` — Appended `TestMultiGuestWriter` class (4 new tests) + helper functions (`_build_mixed_hydrate_structure`, `_build_registry_with_ch4_hydrate`, `_custom_guest_info_etoh_mix`). Tests use a synthetic 22-atom mixed HydrateStructure (2 water + 1 CH4 + 1 etoh_mix, no GenIce2) and directly call `write_multi_molecule_gro_file` / `write_multi_molecule_top_file` / `write_interface_gro_file` / `write_interface_top_file` in isolation (no GUI, no grompp). Tests: `test_multi_guest_top_has_both_molecules`, `test_multi_guest_gro_has_both_residues`, `test_custom_guest_info_list_backward_compat_none`, `test_single_dict_deprecated_warns`.

## Decisions Made
- `custom_by_moltype` dict built ONCE before the per-molecule / per-mol_type loop (replaces single-dict match) — O(1) res_name resolution for N custom guests with no loop-structure change.
- Interface writers resolve the single guest stream via `next(m for m in iface.molecule_index if m.mol_type in custom_by_moltype)` — the interface carries ONE guest stream so only one entry matches; defensive fallback to `next(iter(custom_by_moltype.values()))` when molecule_index lacks a match.
- DeprecationWarning + wrap (not hard break) for legacy single-dict callers — chose graceful handling so any missed call site still produces correct output during the 42-05/42-07 transition; `stacklevel=2` so the warning points at the caller.
- `custom_active` for the interface writers keeps `is not None` AND adds `len(custom_guest_info) > 0` — self-documents the None/empty-list equivalence.
- Test fixture: synthetic 22-atom mixed structure (2 water + 1 CH4 + 1 etoh_mix) — adds a 5-atom built-in CH4 to the 41-06 17-atom pattern so both the registry path (CH4 → CH4_H) and the custom_guest_info path (etoh_mix → MOL_H) fire in the same test.

## Deviations from Plan

None — plan executed exactly as written. The plan's line numbers matched the source closely; the only adjustment was the test file path (`tests/test_output/test_gromacs_export_hydrate.py` vs the plan's `tests/test_gromacs_export_hydrate.py` — the file lives in `tests/test_output/`, not `tests/` directly; this is a minor plan doc discrepancy, not a code issue).

## Issues Encountered
- The plan's test file path `tests/test_gromacs_export_hydrate.py` did not match the actual repo path `tests/test_output/test_gromacs_export_hydrate.py`. Located the file via glob and appended to the existing module per the plan's instruction ("do NOT create a new file — append to the existing Phase 41 test module"). No code change required; the existing `sys.path.insert` + `e2e_export_helpers` import pattern works from either location.

## User Setup Required
None — no external service configuration required. Pure in-repo writer refactor + unit tests.

## Next Phase Readiness
- **42-03 GROMACS writers complete.** All four hydrate writers accept `list[dict]`; `custom_by_moltype` drives res_name resolution; atomtypes merge loops over each custom ITP with `_written_atomtypes` accumulating; built-in single-guest export byte-identical; legacy single-dict callers get a `DeprecationWarning` + wrap.
- **Ready for 42-05-PLAN.md** (interface-writers: the interface writers are already updated here; 42-05 likely wires the CLI pipeline `_build_custom_guest_info` to return a list + updates the e2e tests to pass lists — the DeprecationWarning will guide which call sites need updating).
- **Ready for 42-06/42-07** (GUI hydrate_panel `get_configuration` / CLI pipeline: build `custom_guest_info` as a list of dicts from `cage_guest_assignments` / per-cage UI controls — the writers already accept the list API).
- **No blockers.** Existing call sites in `quickice/cli/pipeline.py` (line 845-847) and the 41-10/41-11 e2e tests still pass single dicts — the DeprecationWarning fires (visible in test output) but the wrap produces correct output. These will be updated to pass lists in 42-05/42-07.

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-05*
