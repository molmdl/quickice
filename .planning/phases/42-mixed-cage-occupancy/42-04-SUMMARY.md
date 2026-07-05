---
phase: 42-mixed-cage-occupancy
plan: 04
subsystem: ui
tags: [vtk, hydrate, rendering, mixed-occupancy, pyside6, visualization]

# Dependency graph
requires:
  - phase: 42-02
    provides: per-mol_type MoleculeIndex (resname_to_moltype dict) + guest_descriptors that create_guest_actor groups on
provides:
  - create_guest_actor returns list[vtkActor] (one per non-water mol_type, grouped via defaultdict)
  - render_hydrate_structure returns [water_actor, *guest_actors] (variable length)
  - _DEFAULT_PALETTE bond-color cycle (gray/cyan/yellow/red/purple) for per-type visual distinction
  - _guest_actors list on hydrate_viewer + interface_viewer for per-type visibility toggles
  - per_type_colors override hook on create_guest_actor
affects: [42-05, 42-06, 42-07, GUI per-cage-type rows, future per-type visibility checkbox]

# Tech tracking
tech-stack:
  added: []  # no new libraries — reuses vtkMoleculeMapper/vtkMolecule/vtkActor
  patterns:
    - "Pattern 6: defaultdict(list) by mol_type (excluding water) → one vtkActor per group"
    - "Variable-length actor list: [water, *guests]; water = [0], guests = [1:] (never hard-index [1])"
    - "Per-type BOND color only (atoms stay CPK via atomic-number lookup) — minimal change, no per-atom scalar arrays"

key-files:
  created: []  # test file extended, not created
  modified:
    - quickice/gui/hydrate_renderer.py
    - quickice/gui/hydrate_viewer.py
    - quickice/gui/interface_viewer.py
    - tests/test_custom_molecule_renderer.py

key-decisions:
  - "create_guest_actor returns list (one vtkActor per non-water mol_type); empty list for no guests (not a hidden actor) — callers iterate [1:]"
  - "render_hydrate_structure returns [water, *guests] variable-length (was always 2-element [water, guest]) — breaking return-shape change, callers updated"
  - "Per-type BOND color from _DEFAULT_PALETTE cycle; atom coloring stays CPK — keeps change minimal, avoids per-atom scalar arrays"
  - "per_type_colors override takes precedence over palette; fallback palette[i % len] by first-occurrence insertion order"
  - "interface_viewer keeps _guest_actor (singular) as primary = _guest_actors[0] if any, for back-compat with methods referencing a single actor; _guest_actors (list) is source of truth"
  - "hydrate_viewer adds _guest_actors = _hydrate_actors[1:] for future per-type visibility toggles; _water_actor stays [0]"

patterns-established:
  - "Pattern 6: defaultdict(list) by mol_type → one actor per group (first-occurrence order = palette index)"
  - "water=[0], guests=[1:] convention for variable-length hydrate actor lists"

# Metrics
duration: 5 min
completed: 2026-07-05
---

# Phase 42 Plan 04: Per-Type Guest VTK Actors Summary

**create_guest_actor builds one vtkActor per guest mol_type (defaultdict grouping) and render_hydrate_structure returns [water, *guests] (variable length) with a gray/cyan/yellow bond-color palette; hydrate_viewer + interface_viewer handle the list without hard indexing**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-05T08:29:02Z
- **Completed:** 2026-07-05T08:34:31Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `create_guest_actor` now groups `molecule_index` by `mol_type` (excluding water) via `collections.defaultdict(list)` and returns one `vtkActor` per non-water `mol_type` (a `list`, was a single `vtkActor`); empty list when there are no guests (was a hidden actor)
- `render_hydrate_structure` returns `[water_actor, *guest_actors]` (variable length): water-only → `[water]`, single guest → `[water, guest]`, mixed → `[water, guest1, guest2, ...]`
- Per-type BOND color from `_DEFAULT_PALETTE` cycle `[(180,180,180), (0,200,200), (220,220,0), (200,80,80), (160,80,200)]` (gray/cyan/yellow/red/purple); atom coloring stays CPK via `ELEMENT_TO_ATOMIC_NUMBER` — only bond color differs per type, keeping the change minimal
- `per_type_colors` override hook on `create_guest_actor` (dict `{mol_type: (r,g,b)}`) takes precedence over the palette; fallback `palette[i % len]` by first-occurrence insertion order
- `hydrate_viewer` tracks `_guest_actors = _hydrate_actors[1:]` (set after each render + cleared in `_clear_actors`); existing `for actor in self._hydrate_actors:` loops already handle variable length
- `interface_viewer` stores `_guest_actors = hydrate_actors[1:]` (list) and keeps `_guest_actor` (singular) as the primary = `_guest_actors[0] if _guest_actors else None` for back-compat; `AddActor`/`RemoveActor` loop the list; `_clear_actors` removes ALL guest actors then clears both refs
- 6 new `TestPerTypeGuestActors` tests: mixed (3 actors), single (2), water-only (1), per-type visibility toggle, list-not-actor shape contract, `per_type_colors` override — all pass (24/24 in file)

## Task Commits

Each task was committed atomically:

1. **Task 1: create_guest_actor returns list per mol_type + render_hydrate_structure variable-length** - `1d4de75` (feat)
2. **Task 2: Update callers (hydrate_viewer + interface_viewer) for variable-length actor list + render tests** - `7f34570` (feat)

**Plan metadata:** pending (docs commit after STATE.md update)

## Files Created/Modified
- `quickice/gui/hydrate_renderer.py` — `create_guest_actor` refactored to group by `mol_type` (defaultdict) and return `list[vtkActor]`; `render_hydrate_structure` returns `[water, *guests]`; added `_DEFAULT_PALETTE` + `per_type_colors` param
- `quickice/gui/hydrate_viewer.py` — added `_guest_actors` attr, set after each render (`set_hydrate_structure` + `set_representation_mode` re-render) + cleared in `_clear_actors`; water stays `[0]`, guests `[1:]`
- `quickice/gui/interface_viewer.py` — `set_hydrate_structure` stores `_guest_actors = hydrate_actors[1:]` + primary `_guest_actor`; `AddActor`/`RemoveActor` loop the list; `_clear_actors` removes all; `InterfaceStructure` path tracks `[guest_actor]` in both refs
- `tests/test_custom_molecule_renderer.py` — 6 new `TestPerTypeGuestActors` tests (per-type actor count + visibility + shape contract + override); `QT_QPA_PLATFORM=offscreen` autouse fixture + `pytest.importorskip("vtk")` headless guard

## Decisions Made
- **List return shape (Q3)**: `create_guest_actor` returns a `list` (not a single `vtkActor`) and `render_hydrate_structure` returns `[water, *guests]` variable-length. This is the plan's Q3 recommendation (a) — minimal, keeps ordering, callers iterate `[1:]`. Breaking change to the 2-element `[water, guest]` shape; both callers updated.
- **Per-type BOND color only**: Atoms stay CPK (atomic-number driven via `ELEMENT_TO_ATOMIC_NUMBER`); only `mapper.SetBondColor(*color)` differs per type. Avoids per-atom scalar arrays (Q4) and keeps the change minimal. First guest keeps the legacy gray `(180,180,180)` so single-guest rendering is visually unchanged.
- **Empty list, not hidden actor**: When there are no guests, `create_guest_actor` returns `[]` (was a hidden `vtkActor` with `VisibilityOff`). Callers handle empty by iterating `[1:]` (no-op for water-only). This removes the stale hidden-actor from the scene graph.
- **Singular `_guest_actor` back-compat in interface_viewer**: Other methods in `interface_viewer.py` historically referenced `self._guest_actor` (singular). Kept it as the primary = `_guest_actors[0] if _guest_actors else None` so `RemoveActor`/guard code keeps working for the common 1-guest case; `_guest_actors` (list) is the source of truth and the loop target.
- **Palette by first-occurrence order**: `defaultdict` preserves insertion order (Py3.7+), so the i-th distinct `mol_type` (in `molecule_index` order) gets `palette[i % len]`. Deterministic across runs for the same structure.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Pre-existing uncommitted `quickice/output/gromacs_writer.py` change present at Task 1 staging time.** It was 42-03 work-in-progress from a concurrent session (later committed as `aff7c63` + `04c0530`), NOT part of plan 42-04's `files_modified`. Per AGENTS.md atomic-commit rules ("Never `git add .` or `git add -A`. Stage only intended files"), I staged ONLY `quickice/gui/hydrate_renderer.py` for Task 1 and ONLY the 3 caller/test files for Task 2 — the unrelated `gromacs_writer.py` change was never included in my commits. No merge conflict; the concurrent 42-03 commits landed cleanly between my two task commits.
- **Headless VTK widget construction crashes under SSH X11 forwarding** (`QVTKRenderWindowInteractor` → `X Error of failed request: BadWindow`). This is the documented AGENTS.md limitation ("VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed"). The plan's verify anticipated this ("or VTK tests skip on headless crash"). The actor COUNT and VISIBILITY assertions do NOT require a render window (just `vtkActor` object creation, which works offscreen), so all 6 new renderer tests pass. Full-widget caller smoke tests (`HydrateViewerWidget`/`InterfaceViewerWidget` instantiation + `set_hydrate_structure`) are not viable headless; caller indexing logic was instead verified by (a) static grep confirming no `[1]` hard indexing remains (only `[0]` for water + `[1:]` for guests) and (b) unit tests proving `render_hydrate_structure` returns the correct variable-length shape that the callers slice. The referenced `tests/test_hydrate_viewer.py` and `tests/test_interface_viewer.py` from the plan's verify do not exist in the repo — there were no caller tests to regress.
- **Dead import in `main_window.py`**: `render_hydrate_structure` is imported on line 34 but never called anywhere in `main_window.py`. Not a caller (no indexing), so no update needed; left as-is to avoid scope creep.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 42-04 complete: mixed hydrates now render N+1 actors (1 water + N guest types) with per-type bond colors. Ready for 42-05 (GUI per-cage-type rows) and any future per-type visibility checkbox (the `_guest_actors` list on both viewers is the toggle target).
- `per_type_colors` override hook on `create_guest_actor` is available for a future GUI color picker.
- No blockers. The headless VTK widget crash is a pre-existing environment limitation (AGENTS.md), not introduced by this plan; GUI rendering works on the user's local display.

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-05*
