---
phase: 40-custom-guest-bridge-core
plan: 04
subsystem: hydrate-generation
tags: [genice2, sys-modules, custom-guest, molecule-plugin, gromacs, validation, thread-safety]

# Dependency graph
requires:
  - phase: 40-01
    provides: parse_itp_defaults_comb_rule (int|None) used by validate_custom_guest_files to reject comb-rule=1
  - phase: 40-03
    provides: HydrateConfig.guest_residue_name / guest_gro_path / is_custom_guest consumed by the downstream integrator
  - phase: 38-internal-pipeline-refactor
    provides: metadata-driven _build_molecule_index + transform_guest_itp (companion pipeline)
provides:
  - build_custom_guest_module(gro_path, guest_type, residue_name) -> types.ModuleType in custom_guest_bridge.py
  - validate_custom_guest_files(gro_path, itp_path, guest_type) -> CustomGuestValidation with specific error messages
  - custom_guest_module context manager (try/finally sys.modules cleanup) for CLI/sync flows
  - register_custom_guest / unregister_custom_guest pair for GUI async (QThread) flows
  - CustomGuestValidation dataclass (is_valid, errors, warnings, atom counts, residue_name, comb_rule)
  - 16 unit tests covering all build/validate/inject/cleanup paths
affects: [40-05-hydrate-generator-integration, 41-gromacs-export, 44-gui-integration, 45-cli-integration, 47-validation-tests]

# Tech tracking
tech-stack:
  added: []  # stdlib + numpy + existing quickice parsers + genice2 (already installed); no new deps
  patterns:
    - "sys.modules injection of a synthetic types.ModuleType so GenIce2 safe_import('molecule', <guest_type>) finds the custom guest"
    - "try/finally cleanup of the injected key (context manager) to prevent stale module pollution"
    - "GRO centroid centering (sites_ = positions - mean) before injection — GenIce2 arrange() adds the cage center to sites_"
    - "register (main thread before QThread.start) / unregister (QThread finished signal) async pair for GUI"
    - "Validate BEFORE injection (parseable, atom count, name<=3 chars, comb-rule=2, audit_name)"

key-files:
  created:
    - quickice/structure_generation/custom_guest_bridge.py
    - tests/test_custom_guest_bridge.py
  modified: []

key-decisions:
  - "guest_type (plugin name / sys.modules key, ^[A-Za-z0-9-_]+$, may exceed 3 chars) is distinct from residue_name (Molecule.name_, <=3 chars base for the _H suffix)"
  - "build_custom_guest_module validates guest_type via audit_name and does NOT register in sys.modules (caller owns injection/cleanup)"
  - "validate_custom_guest_files accepts absent [ defaults ] (comb_rule=None — main .top supplies comb-rule=2); rejects only when present and != 2"
  - "custom_guest_module context manager asserts key absent before inject (stale-state guard); register/unregister pair does NOT assert (async overwrite is intentional for the GUI lifecycle)"
  - "Residue name >3 chars is a blocking error (base name; the _H suffix adds 2 chars, GRO allows 5)"
  - "[ atomtypes ] absence is a WARNING, not an error (the main .top may define them)"

patterns-established:
  - "Custom guest = synthetic genice2.molecules.<guest_type> ModuleType whose Molecule subclass exposes sites_ (centered, nm), labels_ (GRO atom names), name_ (residue_name)"
  - "sites_ MUST be centered (centroid subtracted) before injection — GenIce2 arrange() adds the cage center"
  - "Validation order: GRO parseable -> ITP parseable -> atom count -> residue name <=3 -> comb-rule=2 -> [ atomtypes ] warn -> audit_name"

# Metrics
duration: 7min
completed: 2026-06-30
---

# Phase 40 Plan 04: Custom Guest Bridge Core Summary

**Synthetic GenIce2 Molecule plugin via sys.modules injection — build/validate/inject/cleanup primitives for custom guest hydrate generation, with a 16-test suite**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-30T10:45:46Z
- **Completed:** 2026-06-30T10:53:35Z
- **Tasks:** 3
- **Files modified:** 2 (1 new module, 1 new test file)

## Accomplishments
- Built `custom_guest_bridge.py` (394 lines) — the heart of Phase 40: `build_custom_guest_module` parses a GRO file (reusing `parse_gro_file` for >50 nm Å-mixup validation), centers the molecule, validates the plugin name via GenIce2 `audit_name`, and constructs a synthetic `types.ModuleType` whose `Molecule` subclass exposes `sites_`/`labels_`/`name_`. Verified end-to-end: `MOL 9 (9, 3) True`.
- Implemented `validate_custom_guest_files` with the full research checklist (GRO parseable, ITP parseable, atom count, residue name <=3 chars, comb-rule=2 when `[ defaults ]` present, `[ atomtypes ]` warning, `audit_name`) returning a `CustomGuestValidation` dataclass with the exact success-criteria #2/#3 error messages.
- Added `custom_guest_module` context manager (try/finally `sys.modules.pop`) for CLI/sync flows and a `register_custom_guest`/`unregister_custom_guest` pair for GUI async (QThread) flows — both guarantee cleanup with no stale module pollution.
- Wrote 16 unit tests covering all build, validation reject paths (mismatch, not_gro, combrule1, name_too_long, bad_guest_type), no-atomtypes warning, and the full injection/cleanup lifecycle (normal exit, exception path, register/unregister pair, re-register, `safe_import` discovery).
- All plan verification checks pass: 16/16 bridge tests, 23/23 `custom_guest`-keyword tests (no regressions), injection-then-cleanup prints `injected` (no leak).

## Task Commits

Each task was committed atomically:

1. **Task 1: build_custom_guest_module — GRO to centered Molecule module** - `e40ada8` (feat)
2. **Task 2: validate_custom_guest_files — GRO+ITP validation** - `fce25a9` (feat)
3. **Task 3: sys.modules injection + cleanup primitives + unit tests** - `10510f0` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified
- `quickice/structure_generation/custom_guest_bridge.py` - NEW (394 lines): `build_custom_guest_module`, `validate_custom_guest_files`, `custom_guest_module` context manager, `register_custom_guest`/`unregister_custom_guest`, `CustomGuestValidation` dataclass
- `tests/test_custom_guest_bridge.py` - NEW (268 lines): 16 unit tests across build/validate/inject-cleanup test classes with an autouse sys.modules cleanup fixture

## Decisions Made
- Separated `guest_type` (plugin slug, may exceed 3 chars) from `residue_name` (GRO residue, <=3 chars base) — matches the research's name-separation pattern and avoids shadowing built-in plugins like `ch4`/`thf`.
- `build_custom_guest_module` validates `guest_type` with `audit_name` (raises `ValueError` on invalid chars) but does NOT register in `sys.modules` — the caller owns the injection/cleanup lifecycle, keeping build and registration as distinct concerns.
- The context manager asserts the key is absent before injecting (stale-state guard for sync flows) while the register/unregister pair does not (the GUI async flow intentionally overwrites since the pair IS the lifecycle owner).
- `[ atomtypes ]` absence is a warning, not a blocking error, because the main `.top` may define the atom types — consistent with the existing `molecule_validator.py` pattern.
- GenIce2 is imported lazily inside function bodies (`audit_name`, `safe_import` in tests) per AGENTS.md; no top-level GenIce2 import in the module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added IndexError to the GRO/ITP parse catch tuple**
- **Found during:** Task 2 (validate_custom_guest_files implementation)
- **Issue:** The plan specified catching `(ValueError, OSError, FileNotFoundError)` for GRO/ITP parse failures, but the `not_a_gro.txt` reject-path fixture (which the plan's own Task 3 test `test_validate_rejects_not_gro` relies on) raises `IndexError` from `parse_gro_file` (the single-line file has too few lines for `lines[1]` atom-count access). `IndexError` is NOT a subclass of `ValueError` or `OSError`, so the plan's exact catch tuple would let the exception propagate uncaught, crashing the test instead of returning an `is_valid=False` result.
- **Fix:** Used `except (ValueError, OSError, IndexError)` for both the GRO and ITP parse steps. `IndexError` covers truncated/malformed files with too few lines; `ValueError` covers float-conversion and the >50 nm guard; `OSError` (which includes `FileNotFoundError`) covers missing/unreadable files.
- **Files modified:** `quickice/structure_generation/custom_guest_bridge.py`
- **Verification:** `test_validate_rejects_not_gro` passes — `not_a_gro.txt` returns `is_valid=False` with a "Failed to parse GRO file ... list index out of range" error (mentions "parse"). `etoh_mismatch.gro` (ValueError) and missing files (FileNotFoundError ⊂ OSError) are all handled gracefully.
- **Committed in:** `fce25a9` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix is necessary for the plan's own reject-path test fixture to work. No scope creep — `IndexError` is the minimal addition that keeps the validation graceful on malformed input.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `build_custom_guest_module`, `validate_custom_guest_files`, and the `custom_guest_module` / `register_custom_guest` / `unregister_custom_guest` primitives are importable and ready for plan 40-05 (integrate bridge into `HydrateStructureGenerator.generate()` / `_run_via_api`): build+validate on the main thread, register before `generate_ice()`, cleanup in `finally`.
- All test fixtures (`etoh.gro`/`etoh.itp`, `etoh_mismatch.gro`, `not_a_gro.txt`, `etoh_combrule1.itp`, `etoh_no_atomtypes.itp`) exist and are exercised; no new fixtures were needed.
- No blockers: the bridge is a standalone module with lazy GenIce2 imports; thread-safety relies on the documented v4.7 main-thread-registration discipline.
- The `_build_molecule_index` integration (using `guest_residue_name` for residue grouping) and the GROMACS export wiring (Phase 41) remain the downstream consumers of this bridge.

---
*Phase: 40-custom-guest-bridge-core*
*Completed: 2026-06-30*
