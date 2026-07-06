---
phase: 42-mixed-cage-occupancy
plan: 08
subsystem: ui
tags: [hydrate, gromacs-export, mixed-cage-occupancy, gui, regression-test]

# Dependency graph
requires:
  - phase: 42-mixed-cage-occupancy
    provides: "HydrateConfig.cage_guest_assignments + HydrateStructure.guest_descriptors + GUI per-cage rows (42-06) + export_hydrate cage_guest_assignments-driven ITP staging (42-05)"
provides:
  - "Structure-driven ITP staging in HydrateGROMACSExporter.export_hydrate (stages ITPs from structure.molecule_index, not config.cage_guest_assignments)"
  - "Accurate mixed-guest export dialog label via _hydrate_export_guest_label helper (per-type composition when 2+ guest_descriptors)"
  - "Regression test proving ITPs staged from structure even when config is empty (lattice-change-without-regen desync)"
  - "Unit tests for the dialog label helper (single/mixed/missing-attribute)"
affects: [43-interface-generation, hydrate-export, gui-export-dialog]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structure-driven export staging: drive file staging from structure.molecule_index (what's exported), not config (what the panel says) — prevents config/structure desync bugs"
    - "Hybrid lookup for custom guests: structure.guest_descriptors gives residue_name (WHAT), config.cage_guest_assignments gives ITP path (WHERE) — single source of truth per concern"
    - "Testable dialog label helper: extract pure-function label builders from Qt slot bodies for headless unit testing"

key-files:
  created:
    - tests/test_output/test_hydrate_export_dialog_label.py
  modified:
    - quickice/gui/hydrate_export.py
    - quickice/gui/main_window.py
    - tests/test_output/test_gromacs_export_hydrate.py
    - .planning/debug/mixed-export-itp-and-dialog.md

key-decisions:
  - "Drive ITP staging from structure.molecule_index (what's actually exported) instead of config.cage_guest_assignments (what the panel says); the .gro/.top writers already iterate structure.molecule_index so the staged ITPs now match the exported content regardless of config/structure desync"
  - "Hybrid lookup for custom guests: structure.guest_descriptors supplies residue_name, config.cage_guest_assignments supplies the ITP path — structure is the source of WHAT to stage, config is the source of WHERE the ITP file is"
  - "Backward-compat fallback: when structure.guest_descriptors is empty (pre-Phase-42 structures), fall back to the old config-driven staging loop — the desync bug only manifests with mixed-guest structures which require guest_descriptors"
  - "Extract dialog label to module-level pure function _hydrate_export_guest_label(structure, config) for headless unit testability; mixed (2+ descriptors) shows per-type counts '1 ch4 + 6 thf', single-guest keeps legacy 'N ch4'"
  - "hasattr guard on guest_descriptors so older/incomplete HydrateStructure-like objects fall back to legacy format without crashing"

patterns-established:
  - "Structure-driven staging: when an export's file-list output is driven by structure.molecule_index (writers) but the staging loop iterates config, drive the staging from structure too so they can't desync"
  - "Pure-function label helpers: extract user-facing string builders from Qt slot bodies into module-level functions taking (structure, config) for headless test coverage"

# Metrics
duration: 7min
completed: 2026-07-06
---

# Phase 42 Plan 08: Mixed-Export ITP + Dialog Bugfix Summary

**Structure-driven hydrate ITP staging (fixes missing-guest-ITP export after lattice change without regen) + accurate per-type mixed-guest export dialog label**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-07-06T11:06:38Z
- **Completed:** 2026-07-06T11:13:32Z
- **Tasks:** 3
- **Files modified:** 4 (+1 created)

## Accomplishments
- Fixed Issue 1 (functional): `HydrateGROMACSExporter.export_hydrate` now stages guest `.itp` files from `structure.molecule_index` + `structure.guest_descriptors` instead of `config.cage_guest_assignments`, so staged ITPs always match the exported `.gro`/`.top` content — even when the user changes the lattice without regenerating (config becomes empty for sTprime, structure retains the old mixed guests).
- Fixed Issue 2 (cosmetic): the export success dialog now shows accurate per-type guest composition for mixed hydrates (`Guests: 1 ch4 + 6 thf`) via a new `_hydrate_export_guest_label` helper, instead of mislabelling all guests as the primary `config.guest_type` (`Guests: 7 ch4`).
- Added a regression test (`test_export_hydrate_stages_itps_from_structure_not_config`) that FAILS with the old config-driven code (verified via git stash RED check) and PASSES with the fix — proves ITPs are staged from the structure even when `config.cage_guest_assignments` is empty.
- Added 5 unit tests for the dialog label helper covering single-guest (no/one descriptor), mixed (per-type), multi-molecule-per-type counts, and the missing-attribute defensive fallback.
- Marked the debug file `.planning/debug/mixed-export-itp-and-dialog.md` as `status: resolved` with root cause, fix, verification, files_changed, and commits documented.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix 1 — structure-driven ITP staging** - `32ed9dc` (fix)
2. **Task 2: Fix 2 — accurate mixed-guest export dialog label** - `d910fbd` (fix)
3. **Task 3: Update debug file + commit metadata** - `eb0708e` (docs)

## Files Created/Modified
- `quickice/gui/hydrate_export.py` - Refactored ITP staging loop to iterate unique guest mol_types in `structure.molecule_index` (excluding water); built-in path registers + uses bundled `_hydrate.itp`; custom path uses `structure.guest_descriptors` for residue_name + `config.cage_guest_assignments` for ITP path; backward-compat fallback to config-driven loop when `guest_descriptors` is empty.
- `quickice/gui/main_window.py` - Replaced inline `f"Guests: {structure.guest_count} {config.guest_type}"` in `_on_export_hydrate_gromacs` with a call to the new module-level `_hydrate_export_guest_label(structure, config)` helper; added the helper near `_configure_opengl_for_remote`.
- `tests/test_output/test_gromacs_export_hydrate.py` - Added `TestStructureDrivenItpStaging` regression test class + `_build_mixed_ch4_thf_structure_with_descriptors` helper (mixed CH4+THF structure with `guest_descriptors` + empty sTprime config).
- `tests/test_output/test_hydrate_export_dialog_label.py` - NEW: 5 unit tests for `_hydrate_export_guest_label` (single/mixed/missing-attribute).
- `.planning/debug/mixed-export-itp-and-dialog.md` - Status `investigating` → `resolved`; Resolution section filled.

## Decisions Made
- **Structure-driven staging (Fix 1):** the `.gro`/`.top` writers iterate `structure.molecule_index`, so the ITP staging loop must iterate the same source — otherwise config/structure desync (lattice change without regen) produces a `.top` that `#include`s ITPs which were never staged. Driving from structure guarantees the staged ITP set always matches the exported content.
- **Hybrid lookup for custom guests:** `structure.guest_descriptors` carries residue_name + atom info but NOT the ITP path; `config.cage_guest_assignments` carries the ITP path. The fix uses structure for WHAT to stage and config for WHERE the ITP file is, with explicit `ValueError`/`FileNotFoundError` when either lookup fails (a custom guest in the structure but absent from config cannot be exported).
- **Backward-compat fallback:** the desync bug only manifests with mixed-guest structures, which require `guest_descriptors` (populated by the Phase 42 generator). Pre-Phase-42 structures have empty `guest_descriptors` and were always consistent with their config, so the old config-driven loop is safe for them — preserved as a fallback (`if unique_mol_types and not structure.guest_descriptors:`).
- **Testable dialog helper (Fix 2):** extracted the label logic to a module-level pure function so it can be unit-tested headlessly without instantiating `MainWindow` or driving the Qt event loop. `hasattr(structure, "guest_descriptors")` guards the mixed path for older/incomplete structures.

## Deviations from Plan

None - plan executed exactly as written. The two fixes and the debug-file update were implemented as specified; the only addition beyond the literal plan text was making the dialog label a testable module-level helper (the plan's example implementation was inline), which the plan explicitly permitted ("Add a small unit test if feasible").

## Issues Encountered
- Initial edit attempt for the `_hydrate_export_guest_label` helper accidentally removed the body of `_configure_opengl_for_remote` (a too-broad `oldString` match). Caught immediately by re-reading the file and restored the function body in the next edit. No behavioral impact — verified the restored file imports cleanly and `_configure_opengl_for_remote` is intact (lines 2099-2123).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both confirmed GUI hydrate export bugs are closed; the export path now produces self-consistent `.gro` + `.top` + staged ITPs even under config/structure desync (lattice change without regen).
- The structure-driven staging pattern is a reusable invariant for any export whose file list is driven by `structure.molecule_index` — future export paths (interface, ion, solute) should audit whether their staging loops iterate config or structure.
- Phase 42 mixed-cage-occupancy is now fully closed including this post-phase bugfix (42-08). Ready for Phase 43.

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-06*
