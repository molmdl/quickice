---
phase: 40-custom-guest-bridge-core
plan: 05
subsystem: hydrate-generation
tags: [genice2, custom-guest, hydrate-generator, sys-modules, molecule-index, e2e, bridge-integration]

# Dependency graph
requires:
  - phase: 40-04
    provides: build_custom_guest_module, custom_guest_module context manager (try/finally sys.modules cleanup), register/unregister pair
  - phase: 40-03
    provides: HydrateConfig.guest_residue_name / guest_gro_path / is_custom_guest consumed by generate() branching
  - phase: 38-internal-pipeline-refactor
    provides: metadata-driven _build_molecule_index with residue-grouping preferred path + atom-label fallback
provides:
  - HydrateStructureGenerator.generate() with custom guest bridge integration (build+register on main thread, generate within custom_guest_module context manager, try/finally cleanup)
  - _build_molecule_index uses guest_residue_name (fallback guest_type.upper()) for residue grouping — backward compatible
  - _generate_report handles custom guests without KeyError (branches on config.is_custom_guest)
  - 7-test E2E suite proving custom guest (ethanol) generates a real sI hydrate with guests in cages + sys.modules cleanup
affects: [41-gromacs-export-custom-guests, 42-mixed-cage-occupancy, 44-gui-integration, 45-cli-integration, 47-validation-tests]

# Tech tracking
tech-stack:
  added: []  # stdlib + existing quickice + genice2 (already installed); no new deps
  patterns:
    - "generate() branches on config.is_custom_guest: custom path lazy-imports build_custom_guest_module/custom_guest_bridge, builds the synthetic Molecule module on the MAIN thread (caller's thread), wraps _run_via_api in the custom_guest_module context manager (try/finally sys.modules.pop); built-in path unchanged (no bridge import, no sys.modules injection)"
    - "_build_molecule_index uses guest_residue_name (fallback to guest_type.upper()) for residue grouping — preferred path for custom guests; atom-label sequence matching remains the fragile fallback"
    - "_generate_report branches on config.is_custom_guest to use config.guest_name + guest_residue_name instead of GUEST_MOLECULES[guest_type]['name'] (avoids KeyError for custom guests not in the dict)"
    - "mol_type for custom guests is config.guest_type (e.g. 'etoh_e2e'), NOT guest_residue_name ('MOL') — _build_molecule_index appends MoleculeIndex(start, count, guest_type); verified by E2E test"

key-files:
  created:
    - tests/test_e2e_custom_guest_hydrate.py
  modified:
    - quickice/structure_generation/hydrate_generator.py
    - tests/test_e2e_hydrate_generation.py

key-decisions:
  - "generate() builds+registers the custom guest module on the MAIN thread (the caller's thread) before _run_via_api, per v4.7 thread-safety decision; _build_molecule_index and HydrateStructure construction happen AFTER the context manager exits (they don't need the module — only generate_ice does)"
  - "_build_molecule_index uses guest_residue_name (fallback to guest_type.upper()) for residue grouping — backward compatible (built-ins have guest_residue_name='' → '' or guest_type.upper() → guest_type.upper(), same as before)"
  - "_generate_report uses config.guest_name + guest_residue_name for custom guests instead of GUEST_MOLECULES[guest_type]['name'] (avoids KeyError); report shows 'Guest: MOL (custom, residue=MOL)'"
  - "Lazy import of build_custom_guest_module/custom_guest_module inside generate() (per AGENTS.md — GenIce2/bridge stay lazy; no top-level import); built-in generation is unaffected (no bridge import, no sys.modules injection)"
  - "Existing except Exception in _run_via_api left as-is per plan (pre-existing GUI-adjacent code wrapping GenIce2 calls for user-facing error messages; minimize regression risk)"

patterns-established:
  - "Custom guest integration pattern: generate() branches on config.is_custom_guest → build module on main thread → context-managed _run_via_api (sys.modules registered before generate_ice, cleaned up after) → _build_molecule_index + HydrateStructure construction outside the context manager"
  - "Residue-grouping preferred over atom-label matching for custom guests: guest_residue_name (actual GRO residue from Molecule.name_) is robust; atom-label fallback is fragile when the guest's first atom collides with water (e.g. THF 'O')"

# Metrics
duration: 5min
completed: 2026-07-02
---

# Phase 40 Plan 05: Hydrate Generator Custom Guest Integration Summary

**Custom guest bridge wired into HydrateStructureGenerator.generate() — sys.modules injection on the main thread with try/finally cleanup, _build_molecule_index using guest_residue_name, and a 7-test E2E suite proving ethanol generates a real sI hydrate (8 guests in cages, 46 water, sys.modules clean)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-02T07:26:30Z
- **Completed:** 2026-07-02T07:31:28Z
- **Tasks:** 3
- **Files modified:** 3 (1 new test file, 2 modified)

## Accomplishments
- Wired the custom guest bridge (40-04) into `HydrateStructureGenerator.generate()`: when `config.is_custom_guest` is True, the method lazy-imports `build_custom_guest_module`/`custom_guest_module`, builds the synthetic GenIce2 Molecule module on the main thread, and wraps the `_run_via_api` call in the `custom_guest_module` context manager (try/finally `sys.modules.pop`) — so GenIce2's `safe_import('molecule', <guest_type>)` finds the custom guest during `generate_ice()`, and the module is always cleaned up after (no stale pollution, success criteria #5). Built-in guests (ch4/thf) skip the injection entirely (no bridge import, no sys.modules mutation) — zero regression risk.
- Fixed `_build_molecule_index` to use `guest_residue_name` (fallback `guest_type.upper()`) for residue grouping — one-line change that enables the **preferred** residue-grouping path for custom guests (GenIce2 outputs `Molecule.name_` as the GRO residue, e.g. "MOL", not the `guest_type` slug "etoh_e2e"). Backward compatible: built-ins have `guest_residue_name=""` → `"" or guest_type.upper()` → `guest_type.upper()` (ch4 → "CH4", same as before).
- Fixed `_generate_report` to branch on `config.is_custom_guest` — custom guests use `config.guest_name` + `guest_residue_name` (avoids `KeyError` on `GUEST_MOLECULES[config.guest_type]`); report shows "Guest: MOL (custom, residue=MOL)".
- Created a 7-test E2E suite (`tests/test_e2e_custom_guest_hydrate.py`) proving: custom guest placed in cages (guest_count=8, water_count=46), molecule_index identifies the custom guest by `guest_type` (not "unknown"), sys.modules is clean after generation (success criteria #5), guest atoms are at cage centers (max |pos| > 0.1 nm, not at origin), 9-atom guest signature appears in atom_names, and built-in ch4/thf still generate unchanged (no regression — THF is the critical case since its first atom "O" collides with water).
- Verified end-to-end: a custom ethanol guest generates a real sI hydrate with 8 ethanol molecules in cages (2 small + 6 large) and 46 water molecules, matching the research POC.

## Task Commits

Each task was committed atomically:

1. **Task 1: Integrate bridge into generate() + fix _generate_report for custom guests** - `f72ef0f` (feat)
2. **Task 2: _build_molecule_index uses guest_residue_name for custom guests** - `ec19550` (feat)
3. **Task 3: E2E test for custom guest hydrate generation** - `945b478` (test)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified
- `quickice/structure_generation/hydrate_generator.py` - `generate()` now branches on `config.is_custom_guest`: custom path lazy-imports `build_custom_guest_module`/`custom_guest_module`, builds the synthetic Molecule module on the main thread, wraps `_run_via_api` in the `custom_guest_module` context manager (try/finally cleanup); built-in path unchanged. `_build_molecule_index` uses `getattr(config, "guest_residue_name", "") or guest_type.upper()` for residue grouping. `_generate_report` branches on `config.is_custom_guest` to use `config.guest_name` + `guest_residue_name` (avoids KeyError).
- `tests/test_e2e_hydrate_generation.py` - Fixed stale `test_hydrate_invalid_guest_raises_error`: match pattern updated from "Unknown guest type" to "Custom guest_type 'invalid_guest' requires guest_residue_name" to reflect 40-03 behavior (custom guest without required metadata raises a field-specific error, not the legacy "Unknown guest type").
- `tests/test_e2e_custom_guest_hydrate.py` - NEW (274 lines): 7 E2E tests across 7 classes. Module-scoped `custom_guest_hydrate` fixture (unique guest_type "etoh_e2e") amortizes the GenIce2 call. Tests verify: guests in cages, molecule_index identification, sys.modules cleanup, positions not at origin, atom signature in output, built-in ch4/thf regression.

## Decisions Made
- `generate()` builds+registers the custom guest module on the MAIN thread (the caller's thread) before `_run_via_api`, per the v4.7 thread-safety decision. `_build_molecule_index` and `HydrateStructure` construction happen AFTER the context manager exits — they don't need the module (only `generate_ice` does, via `safe_import`). This keeps the sys.modules injection window minimal.
- `_build_molecule_index` uses `guest_residue_name` (fallback `guest_type.upper()`) for residue grouping — the **preferred** path for custom guests. The atom-label sequence matching fallback remains but is fragile (collides when the guest's first atom is "O", like THF). Residue grouping is robust because GenIce2 outputs `Molecule.name_` as the GRO residue.
- `_generate_report` branches on `config.is_custom_guest` rather than catching `KeyError` — cleaner and more explicit; the report shows "Guest: MOL (custom, residue=MOL)" for custom guests.
- The existing `except Exception` in `_run_via_api` was left as-is per the plan (pre-existing GUI-adjacent code wrapping GenIce2 calls for user-facing error messages; minimize regression risk).
- `mol_type` for custom guests is `config.guest_type` (e.g. "etoh_e2e"), NOT `guest_residue_name` ("MOL") — verified by reading `_build_molecule_index` (appends `MoleculeIndex(start, count, guest_type)`) and confirmed by the E2E test. The `guest_residue_name` is only used for the residue-grouping CHECK, not the `mol_type` value.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale test_hydrate_invalid_guest_raises_error match pattern**
- **Found during:** Task 1 (integrate bridge into generate())
- **Issue:** The pre-existing test `test_hydrate_invalid_guest_raises_error` in `tests/test_e2e_hydrate_generation.py` asserted `pytest.raises(ValueError, match="Unknown guest type")` for `HydrateConfig(lattice_type="sI", guest_type="invalid_guest")`. The 40-03 plan changed `HydrateConfig.__post_init__` so that a `guest_type` not in `GUEST_MOLECULES` is treated as a custom guest requiring explicit metadata — the error message became "Custom guest_type 'invalid_guest' requires guest_residue_name ..." (not "Unknown guest type"). The stale match pattern caused the test to FAIL, which the 40-05 plan's verification #2 (`pytest tests/test_e2e_hydrate_generation.py -v` — existing hydrate E2E tests still pass) explicitly requires to pass.
- **Fix:** Updated the match pattern from `"Unknown guest type"` to `"Custom guest_type 'invalid_guest' requires guest_residue_name"` and expanded the docstring to explain the 40-03 behavior change (custom guest without required metadata raises a field-specific error). The test name and intent ("invalid guest should raise ValueError") are preserved.
- **Files modified:** `tests/test_e2e_hydrate_generation.py`
- **Verification:** `pytest tests/test_e2e_hydrate_generation.py -v --timeout=120` — all 16 tests pass (was 15 passed + 1 failed before the fix).
- **Committed in:** `f72ef0f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix is necessary to satisfy the plan's own verification #2 (existing hydrate E2E tests must pass). The stale test was a pre-existing regression from 40-03 that 40-05 inherited. No scope creep — the fix is a one-line match-pattern update preserving the test's intent.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **Phase 40 complete (5/5 plans):** The custom guest bridge is fully wired end-to-end. A user-supplied custom guest (.gro + .itp) now flows through `generate()` → `_run_via_api` (with sys.modules injection on the main thread) → `_build_molecule_index` (residue grouping via `guest_residue_name`) → `HydrateStructure` with correct `guest_count`/`water_count`/`molecule_index`. sys.modules is cleaned up after generation (success criteria #5).
- **Ready for Phase 41 (GROMACS Export for Custom Guests):** The `molecule_index` now correctly identifies custom guests by `mol_type = config.guest_type` (e.g. "etoh_e2e"), and `HydrateStructure` carries `guest_name`, `guest_atom_labels`, `guest_atom_count`, and `guest_itp_path` from `HydrateConfig`. Phase 41's P3 fix (use `mol_type` from `molecule_index` instead of re-detecting from atom names) and custom guest atomtypes merging can consume this directly.
- **Ready for Phase 42 (Mixed Cage Occupancy):** The `generate()` branching on `config.is_custom_guest` and the context-managed `_run_via_api` are extensible to multiple custom guests (each would need its own `guest_type`/`guest_residue_name`/`guest_gro_path` and its own `custom_guest_module` context manager — nested or sequential).
- **Ready for Phase 44 (GUI Integration) / Phase 45 (CLI Integration):** The `register_custom_guest`/`unregister_custom_guest` pair (40-04) is available for the GUI async (QThread) flow; the CLI synchronous flow uses the `custom_guest_module` context manager (this plan).
- No blockers: all 282 hydrate tests pass (275 previous + 7 new); built-in ch4/thf/sI/sII/sH generation unchanged.

---
*Phase: 40-custom-guest-bridge-core*
*Completed: 2026-07-02*
