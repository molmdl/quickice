---
phase: 42-mixed-cage-occupancy
plan: 02
subsystem: core
tags: [hydrate, mixed-cage-occupancy, genice2, exitstack, multi-guest, parse-guest, molecule-index, guest-descriptor, backward-compat]

# Dependency graph
requires:
  - phase: 42-mixed-cage-occupancy/42-01
    provides: CageGuestAssignment dataclass + HydrateConfig.cage_guest_assignments + __post_init__ legacy shim + GuestDescriptor + HydrateStructure.guest_descriptors + has_custom_assignment property — the data model this plan wires into the generator
  - phase: 42-mixed-cage-occupancy/42-00
    provides: Correct HYDRATE_LATTICES cage_type_map for all lattice types (sH large→20, medium→12_1) — the loop routes cage keys through cage_type_map
  - phase: 40-custom-guest-config
    provides: custom_guest_module context manager + build_custom_guest_module (sys.modules injection / cleanup) — extended to ExitStack for multi-guest
provides:
  - Multi-guest _run_via_api loop iterating cage_guest_assignments calling parse_guest per cage key (Pattern 2)
  - generate() ExitStack nesting custom_guest_module per DISTINCT custom guest_type (Pattern 3, deduped)
  - Multi-guest _build_molecule_index using resname_to_moltype dict for per-type MoleculeIndex.mol_type (Pattern 4)
  - HydrateStructure.guest_descriptors populated with one GuestDescriptor per cage assignment
  - E2E mixed occupancy test proving sI 2×2×2 CH4-small + etoh-large → 16 CH4 + 48 MOL
affects: [42-03 gromacs-writers, 42-05 interface-writers, 42-06 gui-hydrate-panel, 42-07 cli-pipeline, 44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern 2: _run_via_api loops cage_guest_assignments calling parse_guest per cage key (distinct cage_id per cage_key via cage_type_map — parse_guest's 'Cage type already specified' assert never fires)"
    - "Pattern 3: generate() uses ExitStack to nest custom_guest_module per DISTINCT custom guest_type (deduped — legacy single-custom-guest path assigns the same guest_type to small+large, which would trip custom_guest_module's sys.modules key-absent assert if registered twice)"
    - "Pattern 4: _build_molecule_index builds resname_to_moltype dict from ALL cage assignments → per-type MoleculeIndex.mol_type (built-ins: guest_type.upper(); custom: guest_residue_name)"

key-files:
  created:
    - tests/test_e2e_mixed_cage_occupancy.py
  modified:
    - quickice/structure_generation/hydrate_generator.py

key-decisions:
  - "Dedup custom assignments by guest_type in generate() ExitStack — the plan's snippet registered one custom_guest_module per custom ASSIGNMENT, but custom_guest_module asserts the sys.modules key is absent; the 42-01 legacy shim synthesizes the SAME guest_type for small+large (legacy single-custom-guest), so the second registration would crash the assert. Fixed by deduping to one module per DISTINCT guest_type (Rule 1 — bug in plan snippet)."
  - "Kept guest_signature/guest_type/guest_atom_labels/guest_atom_count defined in _build_molecule_index metadata-driven path — the plan's replacement snippet omitted them, but the atom-label fallback path (kept per plan) still uses them; removing them would cause NameError. guest_type is the PRIMARY (first) assignment's type for the single-guest fallback (Rule 1 — bug in plan snippet)."
  - "guest_descriptors: one GuestDescriptor per cage assignment (one per cage_key), NOT per distinct guest_type — the plan explicitly says 'one per assignment'. For legacy single-custom-guest (small+large same guest_type), this yields 2 descriptors with the same mol_type but different cage_keys."
  - "GuestDescriptor.guest_name: built-ins use GUEST_MOLECULES[guest_type]['name'] (e.g. 'Methane'); custom uses guest_residue_name (e.g. 'MOL') — mirrors HydrateConfig.__post_init__ primary-guest logic."
  - "Plan's verify referenced tests/test_hydrate_generator.py which does not exist; used tests/test_e2e_hydrate_generation.py (the equivalent sI/sII×CH4/THF e2e regression file) instead. Minor plan doc discrepancy."

patterns-established:
  - "ExitStack over DISTINCT custom guest_types (dedup) — not per-assignment — to respect custom_guest_module's sys.modules key-absent assert"
  - "resname_to_moltype dict for multi-guest residue grouping in _build_molecule_index (replaces single guest_res_name)"
  - "Per-assignment GuestDescriptor list on HydrateStructure (one per cage_key) alongside the legacy primary-guest fields (Pitfall 7)"

# Metrics
duration: 5 min
completed: 2026-07-05
---

# Phase 42 Plan 02: Mixed Cage Occupancy Generation Core Summary

**Multi-guest _run_via_api loop + ExitStack-nested custom_guest_module per distinct guest_type + resname_to_moltype multi-guest molecule index, proving sI 2×2×2 CH4-small + custom-etoh-large → 16 CH4 + 48 MOL with distinct mol_types and clean sys.modules.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-05T08:21:08Z
- **Completed:** 2026-07-05T08:26:57Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- Refactored `_run_via_api` to iterate `config.cage_guest_assignments` and route each cage key through `parse_guest` with per-assignment `guest_type` + occupancy (Pattern 2). Each cage_key maps to a distinct `cage_id` via `cage_type_map`, so `parse_guest`'s "Cage type already specified" assert never fires for valid configs (Pitfall 2). Water-only lattices and zero-occupancy assignments are skipped.
- Refactored `generate()` to nest `custom_guest_module` via an `ExitStack` for each DISTINCT custom guest_type (Pattern 3). Deduped by `guest_type` because the 42-01 legacy shim synthesizes the SAME `guest_type` for small+large (legacy single-custom-guest path), and `custom_guest_module` asserts the `sys.modules` key is absent — registering twice would crash. ExitStack guarantees cleanup on exception (Pitfall 5 — no stale pollution).
- Refactored `_build_molecule_index` to build a `resname_to_moltype` dict from ALL cage assignments (Pattern 4): built-ins map `guest_type.upper()` → `guest_type` (ch4 → "CH4"); custom maps `guest_residue_name` → `guest_type` (MOL → "etoh_mix"). Each guest type gets its own `MoleculeIndex.mol_type` via the dict lookup. The atom-label fallback path is preserved (uses the primary/first assignment's labels/count) for backward compat with single-guest configs.
- Populated `HydrateStructure.guest_descriptors` with one `GuestDescriptor` per cage assignment (mol_type, cage_key, guest_name, residue_name, is_custom, atom_labels, atom_count). Legacy single-guest fields preserved as primary guest (Pitfall 7).
- Created `tests/test_e2e_mixed_cage_occupancy.py` with a module-scoped fixture generating sI 2×2×2 CH4-small + custom-etoh-large. 4 tests prove: both guest types placed (ch4 + etoh_mix in mol_types); exact counts 16 CH4 + 48 MOL; sys.modules clean post-generation (ExitStack cleanup); guest_descriptors has 2 entries with correct mol_types/cage_keys/is_custom flags.

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-guest generation path (_run_via_api loop + generate ExitStack)** — `b590f55` (feat)
2. **Task 2: Multi-guest _build_molecule_index + e2e mixed occupancy test** — `e74dd35` (feat)

**Plan metadata:** _(pending final docs commit)_

## Files Created/Modified
- `quickice/structure_generation/hydrate_generator.py` — Added `GuestDescriptor` import. `generate()`: replaced single `custom_guest_module` context manager with ExitStack over DISTINCT custom guest_types (deduped); added `guest_descriptors` population (one GuestDescriptor per cage assignment) passed to HydrateStructure. `_run_via_api`: replaced single-guest small/large branch with a loop over `cage_guest_assignments` calling `parse_guest` per cage key (skips cage keys not in cage_type_map with a warning; skips zero-occupancy). `_build_molecule_index`: replaced single `guest_res_name` lookup with `resname_to_moltype` dict built from ALL assignments; residue grouping now yields per-type `mol_type` via dict lookup (kept `guest_signature`/`guest_type`/`guest_atom_labels`/`guest_atom_count` for the atom-label fallback).
- `tests/test_e2e_mixed_cage_occupancy.py` — New e2e test (module-scoped fixture `mixed_si_hydrate`) generating sI 2×2×2 with CH4 in small + custom ethanol (etoh_mix) in large. 4 tests across 4 classes: `TestMixedOccupancyPlacesBothGuestTypes`, `TestMixedCh4Count16`, `TestSysModulesCleanAfterMixed`, `TestGuestDescriptorsPopulated`. Uses unique guest_type "etoh_mix" to avoid sys.modules key collisions with test_e2e_custom_guest_hydrate.py ("etoh_e2e").

## Decisions Made
- Deduped custom assignments by `guest_type` in `generate()` ExitStack (see Deviations #1) — necessary for the legacy single-custom-guest path to work through the new ExitStack code.
- Kept `guest_signature`/`guest_type` defined in `_build_molecule_index` (see Deviations #2) — necessary for the atom-label fallback path the plan explicitly kept.
- Built `guest_descriptors` as one-per-assignment (per the plan's explicit wording "one per assignment"), not one-per-distinct-guest-type. For legacy single-custom-guest this yields 2 descriptors (same mol_type, different cage_keys); for mixed (ch4+etoh_mix) this yields 2 descriptors (different mol_types).
- `GuestDescriptor.guest_name`: built-ins use `GUEST_MOLECULES[guest_type]["name"]` (e.g. "Methane"); custom uses `guest_residue_name` (e.g. "MOL") — mirrors the `HydrateConfig.__post_init__` primary-guest logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deduped custom assignments by guest_type in generate() ExitStack**
- **Found during:** Task 1 (generate() refactor)
- **Issue:** The plan's `generate()` snippet collected `custom_assignments = {k: a for k, a in config.cage_guest_assignments.items() if a.is_custom_guest}` and registered one `custom_guest_module` per custom ASSIGNMENT via ExitStack. But `custom_guest_module` asserts `key not in sys.modules` (stale-state guard). The 42-01 legacy shim synthesizes the SAME `guest_type` for both small+large (legacy single-custom-guest path, e.g. test_e2e_custom_guest_hydrate.py with etoh_e2e), so the second `enter_context` would trip the assert and crash — a regression for the existing custom-guest tests.
- **Fix:** Deduped by `guest_type` — collect `custom_by_type: dict[guest_type, assignment]` keeping only the FIRST occurrence of each distinct custom guest_type, then register ONE module per distinct type. This handles: legacy single-custom-guest (small+large same type → 1 module); mixed (small=ch4 built-in, large=etoh_mix custom → 1 module for etoh_mix); multi-custom (small=guestA, large=guestB → 2 modules). Matches the old single-module behavior for the legacy path.
- **Files modified:** quickice/structure_generation/hydrate_generator.py
- **Verification:** `pytest tests/test_e2e_custom_guest_hydrate.py -x` passes (legacy single-custom-guest path works through the new ExitStack); `pytest tests/test_e2e_mixed_cage_occupancy.py -x` passes (mixed path registers 1 module for etoh_mix).
- **Committed in:** b590f55 (Task 1 commit)

**2. [Rule 1 - Bug] Kept guest_signature/guest_type defined in _build_molecule_index**
- **Found during:** Task 2 (_build_molecule_index refactor)
- **Issue:** The plan's replacement snippet for the single-name setup (lines 598-610) defined `resname_to_moltype`, `guest_atom_labels`, and `guest_atom_count` but OMITTED `guest_signature` and `guest_type`. The plan explicitly kept the atom-label fallback path (lines 629-636) which uses `guest_signature`, `guest_atom_labels`, `guest_atom_count`, AND `guest_type` (line 634: `MoleculeIndex(i, guest_atom_count, guest_type)`). Removing `guest_signature`/`guest_type` without removing the fallback would cause a `NameError` on the first non-water, non-residue-matched atom.
- **Fix:** Added `guest_type = config.guest_type` (primary/first assignment) and `guest_signature = guest_atom_labels[0] if guest_atom_labels else None` to the replacement setup block. The fallback now uses the primary guest's signature — backward compatible with single-guest configs (where the fallback is the secondary identification path); for multi-guest the residue-grouping path is authoritative (GenIce2 writes per-guest residue names).
- **Files modified:** quickice/structure_generation/hydrate_generator.py
- **Verification:** `pytest tests/test_e2e_hydrate_generation.py tests/test_e2e_custom_guest_hydrate.py -x` passes (single-guest fallback path intact); `pytest tests/test_e2e_mixed_cage_occupancy.py -x` passes (multi-guest residue-grouping path authoritative).
- **Committed in:** e74dd35 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in plan snippets)
**Impact on plan:** Both auto-fixes necessary for correctness — the plan's snippets would have crashed the legacy custom-guest path (Deviation #1) and the atom-label fallback path (Deviation #2). No scope creep; both fixes preserve backward compat and match the plan's stated intent.

## Issues Encountered
- Plan's `<verify>` sections reference `tests/test_hydrate_generator.py` which does not exist in the repo. Used `tests/test_e2e_hydrate_generation.py` (the equivalent sI/sII×CH4/THF e2e regression file covering to_candidate, molecule_index, guest atom counts, error handling) for the single-guest legacy regression verification. This is a minor plan doc discrepancy, not a code issue.

## User Setup Required
None — no external service configuration required. Pure in-repo generator refactor + e2e test.

## Next Phase Readiness
- **42-02 generation core complete.** Multi-guest `_run_via_api` loop + ExitStack-nested `custom_guest_module` + `resname_to_moltype` molecule index + `guest_descriptors` are all in place.
- **Ready for 42-03-PLAN.md** (gromacs-writers: consume `cage_guest_assignments` for per-cage guest metadata; `guest_descriptors` for multi-guest reporting; the multi-guest molecule_index now carries distinct `mol_type`s for each guest type).
- **Ready for 42-05** (interface-writers: consume `guest_descriptors` for multi-guest reporting; `to_candidate()` already multi-guest-aware via `guest_type_counts`).
- **Ready for 42-06/42-07** (GUI hydrate_panel `get_configuration` / CLI pipeline: build `cage_guest_assignments` dict from per-cage UI controls / CLI args — the generator now iterates it correctly).
- **No blockers.**
- **Verified POC:** sI 2×2×2 mixed CH4-small + etoh-large → 16 CH4 + 48 MOL with distinct `mol_type`s ("ch4" and "etoh_mix"), matching the research POC exactly. sys.modules clean post-generation.

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-05*
