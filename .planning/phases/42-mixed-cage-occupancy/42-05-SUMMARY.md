---
phase: 42-mixed-cage-occupancy
plan: 05
subsystem: export
tags: [gromacs, hydrate, mixed-occupancy, gui, grompp, moleculetype-registry, custom-guest]

# Dependency graph
requires:
  - phase: 42-03
    provides: "Four hydrate GROMACS writers accept custom_guest_info: list[dict] | None (custom_by_moltype dict, _merge_custom_atomtypes loop, DeprecationWarning+wrap for legacy single dict)"
  - phase: 42-01
    provides: "HydrateConfig.cage_guest_assignments dict[str, CageGuestAssignment] + CageGuestAssignment.is_custom_guest property + __post_init__ legacy shim (empty assignments -> synthesize small/large from guest_type)"
  - phase: 41-06
    provides: "HydrateGROMACSExporter.export_hydrate single-guest is_custom_guest branch + single transform_guest_itp call (the code 42-05 refactors)"
  - phase: 41-10
    provides: "@gmx_skipif GUI custom-guest grompp e2e pattern (synthetic 2-water + 1-ethanol -> write_multi_molecule_* -> _stage_itp_files + _stage_custom_guest_itp -> run_gmx_grompp exit 0)"
provides:
  - "HydrateGROMACSExporter.export_hydrate iterates config.cage_guest_assignments building custom_guest_info list + itp_files dict + custom_guest_itps transform queue"
  - "Built-in guests (ch4/thf) register idempotently in MoleculetypeRegistry; custom guests append to custom_guest_info list"
  - "transform_guest_itp called once per guest ITP (idempotent no-op on pre-transformed built-in ITPs)"
  - "GUI mixed CH4+ethanol grompp e2e test (test_mixed_gui_grompp_passes) proving gmx grompp exit 0 on multi-guest export"
  - "MIXED-04 closed for the GUI path (CLI half is 42-07)"
affects: [42-mixed-cage-occupancy, hydrate-export, gui-export, gromacs-writers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-assignment iteration over config.cage_guest_assignments in export_hydrate (built-in -> registry, custom -> custom_guest_info list)"
    - "Idempotent register_hydrate_guest for same-guest multi-cage assignments (legacy single-ch4 config synthesizes small+large with same ch4)"
    - "Idempotent transform_guest_itp on pre-transformed built-in ITPs (Step 2 line.replace(old, new, 1) is a no-op when old==new; Step 3 rewrites resname to same value)"
    - "custom_guest_itps transform queue decouples the per-assignment collection loop from the per-ITP transform+write loop"

key-files:
  created: []
  modified:
    - "quickice/gui/hydrate_export.py"
    - "tests/test_e2e_mixed_cage_occupancy.py"

key-decisions:
  - "register_hydrate_guest is already idempotent (moleculetype_registry.py lines 62-65 check source_key in _registered before adding) — no guard needed for same-guest multi-cage assignments"
  - "transform_guest_itp is idempotent on pre-transformed built-in ITPs (Step 2 old_name == new_name == 'CH4_H' -> no-op replace; Step 3 rewrites resname to same value) — built-in ITPs can safely go through the transform loop"
  - "Kept title strings '{lattice} + {guest}' (NOT the plan snippet's '{lattice}') to honor byte-identical single-guest success criteria — plan snippet would have changed .gro/.top title text (Rule 1 auto-fix)"
  - "cgi_for_writers = custom_guest_info if non-empty else None — writers' None-equivalent (list[dict] API treats None and [] identically via `for ci in (custom_guest_info or [])` loop)"
  - "itp_files keyed by mol_type (ch4 -> ch4_hydrate.itp, etoh_mix -> etoh.itp) so write_multi_molecule_top_file emits one #include per unique guest"
  - "Test fixture reuses the 42-03 synthetic 22-atom HydrateStructure (2 water + 1 CH4 + 1 ethanol) with cell scaled to 3.0 nm for grompp (STATE [41-10] lesson: grompp rejects box at 2*cutoff)"

patterns-established:
  - "Mixed-occupancy GUI export: iterate cage_guest_assignments once, dispatch built-in vs custom, then loop transform_guest_itp per collected ITP"
  - "Mixed grompp e2e: _stage_itp_files stages ALL #include'd ITPs (tip4p + ch4_hydrate + etoh) + _stage_custom_guest_itp overwrites the custom one — no separate built-in ITP staging needed"

# Metrics
duration: 4 min
completed: 2026-07-06
---

# Phase 42 Plan 5: GUI Mixed-Cage Multi-Guest Export Summary

**HydrateGROMACSExporter.export_hydrate iterates cage_guest_assignments (built-in -> registry, custom -> custom_guest_info list) + mixed CH4+ethanol grompp e2e (exit 0)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-06T05:19:43Z
- **Completed:** 2026-07-06T05:23:40Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Refactored `export_hydrate` to iterate `config.cage_guest_assignments`: built-in guests (ch4/thf) register idempotently in `MoleculetypeRegistry` + use bundled `_hydrate.itp`; custom guests append to a `custom_guest_info` list + `itp_files` dict + `custom_guest_itps` transform queue
- `transform_guest_itp` now runs once per guest ITP (loop over `custom_guest_itps`), idempotent on pre-transformed built-in ITPs
- Single-guest legacy export byte-identical (no regression): the legacy `HydrateConfig(guest_type="ch4")` path synthesizes small+large assignments via the 42-01 `__post_init__` shim, both register CH4_H once (idempotent), both queue the same `ch4_hydrate.itp` for transform (idempotent no-op)
- Added `test_mixed_gui_grompp_passes` (@gmx_skipif) proving `gmx grompp` exits 0 on a mixed CH4+ethanol hydrate exported via the GUI multi-molecule writers — closes MIXED-04 for the GUI path

## Task Commits

Each task was committed atomically:

1. **Task 1: export_hydrate builds custom_guest_info list + itp_files dict + loops transform_guest_itp** - `a3c2a9d` (feat)
2. **Task 2: GUI mixed grompp e2e test (CH4 + ethanol -> grompp exit 0)** - `8441adf` (test)

**Plan metadata:** pending (will be committed after SUMMARY + STATE update)

## Files Created/Modified
- `quickice/gui/hydrate_export.py` - Replaced single-guest `is_custom_guest` branch + single `transform_guest_itp` call with a loop over `config.cage_guest_assignments`; built-ins register in registry, customs append to `custom_guest_info` list + `itp_files` dict + `custom_guest_itps` transform queue; `transform_guest_itp` called per guest ITP
- `tests/test_e2e_mixed_cage_occupancy.py` - Added `test_mixed_gui_grompp_passes` (@gmx_skipif): synthetic 22-atom mixed HydrateStructure (2 water + 1 CH4 + 1 ethanol) -> write_multi_molecule_* (custom_guest_info list + registry) -> stage ITPs -> gmx grompp exit 0

## Decisions Made
- **register_hydrate_guest idempotency:** Verified `MoleculetypeRegistry.register_hydrate_guest` (moleculetype_registry.py lines 62-65) already checks `source_key in self._registered` before adding — returns existing name on duplicate. No guard needed; the plan's suggested `if hydrate_key not in reg._registered` guard would be redundant.
- **transform_guest_itp idempotency on built-in ITPs:** Verified `transform_guest_itp(content, "CH4", suffix="_H")` on the pre-transformed `ch4_hydrate.itp` (moleculetype "CH4_H", [atoms] resname "CH4_H") is a no-op: Step 2 `line.replace(old_name="CH4_H", new_name="CH4_H", 1)` replaces with the same string; Step 3 rewrites [atoms] resname to "CH4_H" (same value). Built-in ITPs safely go through the transform loop.
- **Title strings kept as `{lattice} + {guest}` (Rule 1 auto-fix):** The plan's snippet used `f"Hydrate structure ({lattice}) exported by QuickIce"` and `f"Hydrate ({lattice})"` (dropping `{guest}`), but the success criteria explicitly requires "Single-guest GUI export byte-identical (no regression)". Kept the existing `f"Hydrate structure ({lattice} + {guest}) exported by QuickIce"` and `f"Hydrate ({lattice} + {guest})"` title format to honor byte-identical output. The `guest` variable (config.guest_type, the primary) is still defined and meaningful for both single-guest and mixed hydrates.
- **cgi_for_writers None-equivalence:** `cgi_for_writers = custom_guest_info if custom_guest_info else None` — when all guests are built-in (e.g. legacy single-ch4 config), `custom_guest_info` is `[]` and `None` is passed to the writers (their `for ci in (custom_guest_info or [])` loop treats both identically).
- **Test fixture reuses 42-03 structure with 3.0 nm box:** The 22-atom synthetic HydrateStructure (2 water + 1 CH4 + 1 ethanol) mirrors the 42-03 `_build_mixed_hydrate_structure` fixture, but with `cell = np.eye(3) * 3.0` (3.0 nm box) instead of 1.2 nm — grompp rejects a box exactly at 2*cutoff (STATE [41-10] lesson).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Kept .gro/.top title strings byte-identical**
- **Found during:** Task 1 (export_hydrate refactor)
- **Issue:** The plan's literal code snippet used `f"Hydrate structure ({lattice}) exported by QuickIce"` and `f"Hydrate ({lattice})"` for the writer title strings, dropping the `{guest}` variable. This would change the .gro title from "Hydrate structure (sI + ch4) exported by QuickIce" to "Hydrate structure (sI) exported by QuickIce" and the .top title from "Hydrate (sI + ch4)" to "Hydrate (sI)" — violating the success criteria "Single-guest GUI export byte-identical (no regression)".
- **Fix:** Kept the existing title format `f"Hydrate structure ({lattice} + {guest}) exported by QuickIce"` and `f"Hydrate ({lattice} + {guest})"` (the `guest` variable = `config.guest_type` is still defined and meaningful as the primary guest for both single-guest and mixed hydrates).
- **Files modified:** quickice/gui/hydrate_export.py
- **Verification:** `pytest tests/test_output/test_gromacs_export_hydrate.py -x` — 12/12 pass (single-guest GUI export byte-identical, no regression)
- **Committed in:** a3c2a9d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Auto-fix necessary to honor the byte-identical success criteria. No scope creep — the title string format is unchanged from the pre-42-05 code.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 42-05 (GUI multi-guest export) complete: `export_hydrate` iterates `cage_guest_assignments`, MIXED-04 closed for the GUI path.
- 42-06 and 42-07 remain in Phase 42. A concurrent agent committed `f0caeff feat(42-07)` (CLI --cage-guest flag + list-based `_build_custom_guest_info`) during this plan's execution — 42-07 may be partially or fully complete; verify before executing.
- The 41-10 test (`test_e2e_custom_guest_gui_grompp.py`) still passes a legacy single dict to the writers (DeprecationWarning fires, 42-03 wrap produces correct output). This is a test-file concern, not a production call site — `export_hydrate` (42-05) and `_run_export_step` (42-07) now both pass lists. The 41-10 test can be updated to pass a list in a future cleanup pass (not blocking).

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-06*
