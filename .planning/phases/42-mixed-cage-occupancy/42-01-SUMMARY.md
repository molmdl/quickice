---
phase: 42-mixed-cage-occupancy
plan: 01
subsystem: core
tags: [hydrate, cage-occupancy, data-model, cage-guest-assignment, guest-descriptor, backward-compat, validation]

# Dependency graph
requires:
  - phase: 42-mixed-cage-occupancy/42-00
    provides: Correct HYDRATE_LATTICES cage_type_map for all 10 lattice types (sH large→20, medium→12_1) — prerequisite so the legacy shim's cage_type_map lookup yields correct keys
  - phase: 40-custom-guest-config
    provides: HydrateConfig custom-guest fields (guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count) + is_custom_guest property — mirrored per-assignment in CageGuestAssignment
  - phase: 38-hydrate-config-metadata
    provides: Built-in guest auto-populate in __post_init__ from GUEST_MOLECULES (count key "atoms") — extended to per-assignment
provides:
  - CageGuestAssignment dataclass with is_custom_guest property (per-cage-key guest assignment)
  - HydrateConfig.cage_guest_assignments field (dict[str, CageGuestAssignment]) — the central Phase 42 API
  - __post_init__ legacy-shim synthesizing small/large from legacy single-guest fields (backward compat — no caller change required)
  - __post_init__ explicit-API handling: per-assignment built-in metadata auto-populate + per-assignment custom-guest validation + Pitfall 6 duplicate-residue-name rejection
  - HydrateConfig.has_custom_assignment property (generator ExitStack decision for 42-02)
  - HydrateConfig.from_dict rebuilding CageGuestAssignment per dict entry
  - GuestDescriptor dataclass + HydrateStructure.guest_descriptors field (populated by 42-02)
  - 6 config validation tests covering explicit API, legacy shim (sI + filled ice), duplicate rejection, water-only lattice
affects: [42-02 hydrate-generator, 42-03 gromacs-writers, 42-05 interface-writers, 42-06 gui-hydrate-panel, 42-07 cli-pipeline, 44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-assignment metadata auto-populate in __post_init__ as single source of truth (NOT deferred to GUI get_configuration) — CageGuestAssignment entries for built-in guests get complete atom_labels/atom_count even when only guest_type+occupancy supplied"
    - "Legacy-shim backward-compat synthesis: empty cage_guest_assignments + non-empty guest_type → synthesize small/large from cage_type_map keys + legacy occupancy fields (medium/guest only via explicit API)"
    - "Pitfall 6 distinct-residue-name validation: custom assignments with duplicate guest_residue_name rejected with clear ValueError naming the colliding name and both cage keys (no auto-disambiguate — _H hydrate path does not disambiguate unlike _L liquid path)"
    - "Explicit-API vs legacy-API branching in __post_init__ (elif): explicit dict wins, legacy fields synthesize only when dict empty"

key-files:
  created: []
  modified:
    - quickice/structure_generation/types.py
    - tests/test_hydrate_config_custom.py

key-decisions:
  - "CageGuestAssignment.is_custom_guest property mirrors HydrateConfig.is_custom_guest but per-assignment (guest_type not in GUEST_MOLECULES)"
  - "__post_init__ is the canonical single source of truth for per-assignment built-in metadata auto-populate (count key 'atoms', matching existing legacy code) — NOT 42-06's get_configuration"
  - "Legacy shim synthesizes only small/large from cage_type_map keys; medium/guest have no legacy field so they are only set via the explicit Phase 42 API"
  - "Pitfall 6: duplicate custom guest_residue_name across assignments rejected with ValueError naming the colliding name + both cage keys; no auto-disambiguation (_H path's register_hydrate_guest does not disambiguate)"
  - "has_custom_assignment property (any(a.is_custom_guest ...)) added for the generator's ExitStack decision in 42-02 (mirrors 40-05 custom_guest_module context manager need)"
  - "Legacy is_custom_guest property preserved (reflects PRIMARY guest_type) — not removed/renamed (Pitfall 4)"
  - "HydrateStructure.guest_descriptors field added with default empty list (populated by generator 42-02); legacy single-guest fields (guest_name, guest_atom_labels, guest_atom_count, guest_itp_path) kept as primary guest (Pitfall 7) — to_candidate() unchanged (already multi-guest-aware via guest_types accumulation)"
  - "from_dict rebuilds CageGuestAssignment per entry accepting both dict and CageGuestAssignment instance values (natural serialization form); non-dict/non-instance values skipped silently (shim handles the now-empty dict)"

patterns-established:
  - "Per-assignment metadata auto-populate in __post_init__ (single source of truth, not deferred to callers)"
  - "Legacy-shim backward-compat: empty explicit dict → synthesize from legacy fields (no caller migration required)"
  - "Distinct-residue-name validation across custom assignments (Pitfall 6 — reject, do not auto-disambiguate)"

# Metrics
duration: 4 min
completed: 2026-07-05
---

# Phase 42 Plan 01: Mixed Cage Occupancy Data Model Summary

**CageGuestAssignment dataclass + HydrateConfig.cage_guest_assignments with a __post_init__ legacy-shim (backward-compat, no caller change) and explicit-API per-assignment built-in metadata auto-populate + Pitfall 6 duplicate-residue-name rejection, plus GuestDescriptor + HydrateStructure.guest_descriptors — the central Phase 42 data-model change every downstream plan (generator, writers, GUI, CLI) consumes.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-05T08:14:55Z
- **Completed:** 2026-07-05T08:19:15Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added the `CageGuestAssignment` dataclass (guest_type, occupancy, guest_residue_name, guest_gro_path, guest_itp_path, guest_atom_labels, guest_atom_count) with an `is_custom_guest` property — the per-cage-key guest assignment unit consumed by every downstream Phase 42 plan.
- Added `HydrateConfig.cage_guest_assignments: dict[str, CageGuestAssignment]` and extended `__post_init__` with: (1) a **legacy-shim** that synthesizes `small`/`large` assignments from the legacy single-guest fields when the dict is empty (backward compat — GUI hydrate_panel, CLI pipeline, ~30 existing tests need no change); (2) an **explicit-API** branch that auto-populates per-assignment built-in metadata from `GUEST_MOLECULES` (single source of truth in `__post_init__`), validates per-assignment custom-guest metadata, and rejects duplicate `guest_residue_name` across custom assignments (Pitfall 6).
- Added the `has_custom_assignment` property (any custom assignment) for the generator's ExitStack decision (42-02), and updated `from_dict` to rebuild `CageGuestAssignment` per dict entry (accepting dict or instance values).
- Added the `GuestDescriptor` dataclass + `HydrateStructure.guest_descriptors: list[GuestDescriptor]` field (default empty, populated by 42-02); preserved all legacy single-guest fields as the "primary guest" (Pitfall 7) — `to_candidate()` is unchanged (already multi-guest-aware).
- Added 6 config validation tests covering: explicit API + legacy `guest_type` stays default (primary); per-assignment built-in metadata auto-population; legacy shim (sI small/large + filled-ice single-key); duplicate-residue rejection (Pitfall 6); water-only lattice empty assignments.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CageGuestAssignment dataclass + HydrateConfig.cage_guest_assignments + legacy shim** — `80d3ef0` (feat)
2. **Task 2: Add HydrateStructure.guest_descriptors + config validation tests** — `a69c918` (feat)

**Plan metadata:** _(pending final docs commit)_

## Files Created/Modified
- `quickice/structure_generation/types.py` — Added `CageGuestAssignment` (before `HydrateConfig`) and `GuestDescriptor` (after `CageGuestAssignment`) dataclasses; `HydrateConfig.cage_guest_assignments` field; `__post_init__` legacy-shim + explicit-API (per-assignment auto-populate + custom validation + Pitfall 6 duplicate rejection); `from_dict` rebuild; `has_custom_assignment` property; `HydrateStructure.guest_descriptors` field (after `guest_itp_path`). Legacy `is_custom_guest` property preserved.
- `tests/test_hydrate_config_custom.py` — Added `CageGuestAssignment` import + `TestCageGuestAssignments` class with 6 new tests (explicit API, per-assignment built-in metadata, legacy shim sI, legacy shim filled-ice single-key, duplicate-residue rejection, water-only empty). All 16 tests (10 existing + 6 new) pass.

## Decisions Made
- Placed `CageGuestAssignment` and `GuestDescriptor` adjacent (before `HydrateConfig` and after `CageGuestAssignment` respectively) — both reference `GUEST_MOLECULES` defined earlier, and `CageGuestAssignment` is tightly coupled to `HydrateConfig` (its primary consumer), so locality aids readability. The plan permitted either "after GUEST_MOLECULES" or "just before HydrateConfig"; chose the latter for consumer locality.
- `from_dict` accepts both `dict` entries (natural serialization form, rebuilt via `CageGuestAssignment(**entry)`) and existing `CageGuestAssignment` instances (passed through); non-dict/non-instance values are skipped silently so the legacy shim handles the now-empty dict. This is a permissive interpretation of "build CageGuestAssignment per entry" that stays robust to varied caller input.
- Did **not** add per-assignment occupancy range validation (0–100) in Task 1 — the plan scoped (b) to custom-guest metadata + Pitfall 6 only; per-assignment occupancy validation can be added by the generator (42-02) or a later plan if needed. The legacy `cage_occupancy_small`/`large` range validation (lines 496–499) still runs and covers the legacy path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. Both tasks executed cleanly; all 198 verification tests (test_hydrate_config_custom + test_hydrate_config_metadata + test_hydrate_lattice_types) pass, plus 71 broader tests touching HydrateStructure (structure_generation, cli pipeline, itp helpers, gromacs export, guest tiling) confirm no regression from the new `guest_descriptors` field.

## User Setup Required
None — no external service configuration required. Pure in-repo data-model change + tests.

## Next Phase Readiness
- **42-01 data model complete.** `CageGuestAssignment` + `HydrateConfig.cage_guest_assignments` + legacy shim + `GuestDescriptor` + `HydrateStructure.guest_descriptors` are all in place.
- **Ready for 42-02-PLAN.md** (hydrate_generator: iterate `cage_guest_assignments.items()` → per-cage `parse_guest` with per-assignment occupancy/guest_type; populate `HydrateStructure.guest_descriptors`; use `has_custom_assignment` for the ExitStack/custom_guest_module decision).
- **Ready for 42-03/42-05** (writers: consume `cage_guest_assignments` for per-cage guest metadata; `guest_descriptors` for multi-guest reporting).
- **Ready for 42-06/42-07** (GUI hydrate_panel `get_configuration` / CLI pipeline: build `cage_guest_assignments` dict from per-cage UI controls / CLI args — built-in metadata auto-populate in `__post_init__` means `get_configuration` only needs to supply `guest_type`+`occupancy` per cage).
- **No blockers.**
- **Note for 42-02:** GenIce2's sH 1×1×1 cell contains 2 crystallographic unit cells (68 waters); per-cage multiplicities are 6 small / 4 medium / 2 large (from 42-00). The generator must iterate `cage_guest_assignments.items()` and route each cage key through `parse_guest` with the per-assignment occupancy (not the legacy single `cage_occupancy_small`/`large`).

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-05*
