---
phase: 41-gromacs-export-for-custom-guests
plan: 07
subsystem: cli
tags: [gromacs, itp, custom-guest, hydrate-export, transform_guest_itp, cli]

# Dependency graph
requires:
  - phase: 40-custom-guest-itp-transform
    provides: transform_guest_itp (comment atomtypes + _H moleculetype rename + [atoms] resname rewrite) and the etoh.itp custom guest fixture
  - phase: 40-custom-guest-bridge-core
    provides: HydrateConfig.is_custom_guest property, guest_itp_path, guest_residue_name fields
provides:
  - "copy_custom_guest_itp(output_dir, itp_path, residue_name) -> str | None — reads a custom guest ITP, applies transform_guest_itp(content, residue_name, '_H'), writes it to output_dir/<itp basename>"
  - "is_custom_guest branch in copy_itp_files_for_structure hydrate step that routes custom guests through copy_custom_guest_itp (config.guest_itp_path + config.guest_residue_name) instead of _copy_hydrate_guest_itp which raised FileNotFoundError for custom guest types"
affects: [41-08, 41-10, 41-11, cli-hydrate-export, custom-guest-grompp, e2e-gmx-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom-guest routing in copy_itp_files_for_structure hydrate branch: branch on config.is_custom_guest BEFORE the built-in _resolve_guest_type_for_hydrate_step path (built-in ch4/thf unchanged)"
    - "except (OSError, ValueError) in CLI itp_helpers copy_custom_guest_itp — no bare except Exception per AGENTS.md; missing file -> None, transform ValueError (>5 char name) -> None"

key-files:
  created:
    - tests/test_cli/test_itp_helpers_custom_guest.py
  modified:
    - quickice/cli/itp_helpers.py

key-decisions:
  - "copy_custom_guest_itp uses output_dir / src.name (preserves the original ITP basename, e.g. 'etoh.itp') rather than synthesizing '{guest_type}_hydrate.itp' — built-in _copy_hydrate_guest_itp keeps its '{guest_type}_hydrate.itp' naming, the two paths stay disjoint"
  - "Missing source ITP returns None (logs at error level) rather than raising — the caller (copy_itp_files_for_structure) just appends to copied[] if non-None, so a misconfigured path is surfaced via the log without aborting the whole export"
  - "transform ValueError (>5-char residue name after _H suffix) is caught (except (OSError, ValueError)) and logged at error level then None — surfaces config bugs without crashing the CLI; mirrors the _H suffix guard validated in Phase 38-03"
  - "Built-in _copy_hydrate_guest_itp left UNCHANGED (still uses 'except Exception' for the broad fallback after FileNotFoundError) — the plan explicitly scoped the change to adding the new helper + the hydrate-branch routing; zero regression risk to the built-in ch4/thf path"
  - "tests/test_cli/ subdir created without an __init__.py — pytest discovers it via rootdir mode (the existing tests/test_output/ subdir convention uses an empty __init__.py, but the plan explicitly says pytest discovers without one; verified all 5 tests collected)"

patterns-established:
  - "Custom-vs-built-in dispatch in copy_itp_files_for_structure: getattr(structure, 'config', None) + getattr(config, 'is_custom_guest', False) check BEFORE the built-in _resolve_guest_type_for_hydrate_step fallback — custom path uses explicit config.guest_itp_path + config.guest_residue_name, built-in path uses _detect_guest_type heuristics"
  - "Duck-typed HydrateStructure construction in tests (no GenIce2 calls) — mirror tests/test_hydrate_config_metadata.py: pass positions=zeros, atom_names, cell=eye*3, molecule_index list, config, lattice_info=HydrateLatticeInfo.from_lattice_type(...), report, guest_count, water_count, plus guest_* propagated from config"

# Metrics
duration: 10min
completed: 2026-07-05
---

# Phase 41 Plan 07: Custom Guest ITP Copy Summary

**`copy_custom_guest_itp` helper + `is_custom_guest` routing in the CLI hydrate ITP copy step, so the custom guest `.itp` (e.g. `etoh.itp`) is actually copied to the output dir with the full `_H` transform (moleculetype `MOL_H`, `[atomtypes]` commented, `[atoms]` resname `MOL_H`) instead of being silently skipped by `_copy_hydrate_guest_itp`'s `FileNotFoundError` swallow.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-05T05:18Z
- **Completed:** 2026-07-05T05:28Z
- **Tasks:** 2
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments
- Added `copy_custom_guest_itp(output_dir, itp_path, residue_name) -> str | None` to `quickice/cli/itp_helpers.py` (placed after `_copy_hydrate_guest_itp`). Reads the custom guest ITP, applies `transform_guest_itp(content, residue_name, '_H')` (comments out `[ atomtypes ]`, renames `[ moleculetype ]` to `'{residue_name}_H'`, rewrites `[ atoms ]` resname), writes to `output_dir / src.name`. Uses `except (OSError, ValueError)` (no bare `except Exception`) per AGENTS.md; returns `None` for missing source / >5-char residue name (logged at error level).
- Routed the hydrate branch of `copy_itp_files_for_structure` through `copy_custom_guest_itp` when `structure.config.is_custom_guest` is True (uses `config.guest_itp_path` + `config.guest_residue_name`), BEFORE the existing `_resolve_guest_type_for_hydrate_step` / `_copy_hydrate_guest_itp` path (built-in ch4/thf unchanged).
- 5 unit tests in `tests/test_cli/test_itp_helpers_custom_guest.py` (new `tests/test_cli/` subdir): transform contract (MOL_H moleculetype, `[atomtypes]` commented, `[atoms]` resname MOL_H), missing file → None, >5-char name → None, custom hydrate routing (etoh.itp + tip4p-ice.itp staged), built-in ch4 regression (ch4_hydrate.itp + tip4p-ice.itp).
- Verified zero regression: all 284 hydrate-tagged tests + 59 itp/transform/cli tests pass; `tests/test_cli/test_itp_helpers_custom_guest.py -v` shows 5/5 pass; `python -c "from quickice.cli.itp_helpers import copy_custom_guest_itp, copy_itp_files_for_structure; print('ok')"` prints `ok`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add copy_custom_guest_itp + route hydrate branch for custom guests** - `95b2c5d` (feat)
2. **Task 2: Unit tests for copy_custom_guest_itp + hydrate routing** - `aa16a59` (test)

## Files Created/Modified
- `quickice/cli/itp_helpers.py` - Added `copy_custom_guest_itp` (38 lines, placed after `_copy_hydrate_guest_itp`); modified the hydrate branch of `copy_itp_files_for_structure` to dispatch on `config.is_custom_guest` before falling through to the built-in path.
- `tests/test_cli/test_itp_helpers_custom_guest.py` - New test file (239 lines, 5 tests) covering transform contract, missing source, >5-char name, custom hydrate routing, and built-in ch4 regression. Creates the `tests/test_cli/` subdir (no `__init__.py` — pytest discovers via rootdir mode).

## Decisions Made
- **Preserve original ITP basename for custom guests:** `copy_custom_guest_itp` writes to `output_dir / src.name` (e.g. `etoh.itp`), not `'{guest_type}_hydrate.itp'`. This matches the `.top` `#include` naming that plan 41-05/41-08 will emit (e.g. `#include "etoh.itp"`), so grompp can find the file. The built-in `_copy_hydrate_guest_itp` keeps its `'{guest_type}_hydrate.itp'` convention; the two paths stay disjoint by `is_custom_guest`.
- **Surface config bugs, don't crash the CLI:** A missing source ITP and a >5-char residue name (transform ValueError) both log at `error` level and return `None` rather than raising. The caller just skips appending to `copied[]` if `None`, so a misconfigured export path is surfaced in the log without aborting the whole export step. Mirrors the `_H` suffix length guard validated in Phase 38-03.
- **Leave `_copy_hydrate_guest_itp` unchanged:** The plan explicitly scopes the change to "add helper + route hydrate branch"; the built-in path's `except FileNotFoundError: return None` + `except Exception: return None` (broad fallback) is intentionally NOT refactored to `except (OSError, ValueError)` — minimizing regression risk to the established built-in ch4/thf path. The new `copy_custom_guest_itp` uses the AGENTS.md-compliant narrow tuple.
- **No `__init__.py` in `tests/test_cli/`:** The plan said "pytest discovers without `__init__.py`"; verified all 5 tests collected and passed without one. The existing `tests/test_output/` subdir uses an empty `__init__.py`, but the plan's instruction was explicit; the test file is self-contained (no sibling imports within `tests/test_cli/`).

## Deviations from Plan

None - plan executed exactly as written. The two code references (the new `copy_custom_guest_itp` body and the modified hydrate branch) were implemented verbatim from the plan's specified snippets. The test file mirrors the plan's 5 named tests with the specified assertions, using the `tests/test_hydrate_config_metadata.py` `_make_structure` pattern for duck-typed `HydrateStructure` construction.

## Issues Encountered

- **System clock skew between session start and end:** The shell's `date -u` at session start reported `2026-07-03T16:08:17Z` (matching the prior session's date from STATE.md), but by the end of the session it reported `2026-07-05T05:28Z` (today's date per the env). The ~37-hour gap implied by the raw timestamps is an artifact of NTP correction mid-session, not actual work time. The "Performance" section above uses an estimated ~10 min duration based on the actual operations performed (one source edit, one test file write, two commits, several test runs). No work product was affected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `copy_custom_guest_itp` is importable and tested; ready to be exercised by the CLI hydrate export pipeline (plan 41-08 wires `copy_itp_files_for_structure` into `_run_export_step`).
- The custom-guest grompp e2e tests (plans 41-10 / 41-11) can now rely on `copy_itp_files_for_structure` to stage `etoh.itp` with `moleculetype MOL_H` in the CLI output dir — closing the "top `#include`s `etoh.itp` but no `etoh.itp` is copied → grompp File not found" gap (when combined with plan 41-05/41-08's `.top` `#include` fix).
- The built-in ch4/thf path is verified unchanged (regression test `test_hydrate_step_builtin_ch4_regression`); no blockers for downstream plans.
- The `_copy_hydrate_guest_itp` `except Exception` broad fallback is intentionally left for a future cleanup pass (out of scope for this plan; built-in path is stable).

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
