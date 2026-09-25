---
phase: 029-fix-cli-hydrate-export-0-ion-orphan-incl
plan: 029
subsystem: cli-export
tags: [cli, export, gromacs, hydrate, ions, e2e, grompp]
requires: [48.3-25 exit audit findings (a) + (b)]
provides:
  - "0-ion CLI exports produce NO orphan ion.itp include/staging (grompp rc==0)"
  - "CLI hydrate-branch export of mixed built-in hydrates emits per-type guests (CH4_H/THF_H) with both ITPs staged+included (grompp rc==0)"
  - "2 new true-e2e regression files (3 tests, RED-first)"
affects: [user manual UAT workflow (48.3 follow-up), any CLI mixed-hydrate or low-concentration-ion users]
tech-stack:
  added: []
  patterns:
    - "count-gated include+staging pairs: writer and staging gate on the SAME condition (na_count>0 or cl_count>0)"
    - "metadata threading into existing writer mixed_builtin gates (44.1-02..07 precedent) instead of writer rewrites"
key-files:
  created:
    - tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py
    - tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py
  modified:
    - quickice/output/ion_writer.py
    - quickice/cli/itp_helpers.py
    - quickice/cli/pipeline.py
    - tests/test_cli/test_cli_pipeline.py
    - tests/test_cli/test_mixed_cage_cli.py
decisions:
  - "Bug (a) fix = documented preferred option 2: skip include AND staging when 0 ions (no output change for ion users)"
  - "Bug (b) fix = thread guest_descriptors + guest_atom_counts into the CLI hydrate wrapper (not a reroute through multi-molecule writers)"
  - "Two pre-existing pin tests consciously re-pinned to the fixed behavior (their docstrings anticipated the fix)"
duration: ~12 min
completed: 2026-09-25
---

# Quick Task 029: CLI hydrate export fixes (0-ion orphan include + mixed built-in guest mislabeling) Summary

**One-liner:** Gate `#include "ion.itp"` + ion.itp staging on ion counts (bug a), and thread `guest_descriptors`/`guest_atom_counts` into the CLI hydrate wrapper + stage every distinct built-in guest ITP (bug b) — both 48.3-25 exit-audit bugs closed with RED-first true-e2e coverage.

## Overview

Two CLI export bugs from the 48.3-25 exit audit (STATE.md "Status") fixed:

- **(a) 0-ion orphan include:** `write_ion_top_file` unconditionally wrote `#include "ion.itp"` while the NA/CL `[atomtypes]` block was count-gated, and `copy_itp_files_for_structure` unconditionally staged ion.itp → grompp-fatal "Atomtype NA not found" for exports where a tiny concentration rounded to 0 ion pairs.
- **(b) Mixed built-in guest mislabeling:** the CLI hydrate branch's `InterfaceStructure` wrapper never threaded the per-type guest metadata, so the interface writers' existing mixed-built-in paths never activated and all guests collapsed to CH4_H (192 guests counted as 5-atom CH4 → grompp atom-count mismatch; only ch4_hydrate.itp staged).

## Tasks Completed

### Task 1: Bug (a) — skip ion.itp include+staging when 0 ions

- **Commit:** `1cfa8a70` — `fix(029): skip ion.itp include+staging for 0-ion CLI exports`
- **RED observed (exact documented signature):** leftover 0-ion export dir grompp fails with `ERROR 1 [file ion.itp, line 8]: Atomtype NA not found` (unconditional include with `0 Na+ + 0 Cl-` in the system name; test's assert 1 trips first catching the same root cause).
- **Fix:**
  - `quickice/output/ion_writer.py` `write_ion_top_file`: `f.write('#include "ion.itp"\n\n')` → `if na_count > 0 or cl_count > 0: f.write('#include "ion.itp"\n'); f.write("\n")` (byte-identical when ions present).
  - `quickice/cli/itp_helpers.py` ion branch: staging try-block wrapped in the same `na_count > 0 or cl_count > 0` gate; `logger.info("0 ions — skipping ion.itp generation")` otherwise.
- **GREEN:** `tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py` → 2 passed (0-ion: no include/staging/grompp-rc-0; ion-present 0.5 M guard: include+staged+counts match+grompp-rc-0).

### Task 2: Bug (b) — thread guest metadata into CLI hydrate export

- **Commit:** `d39e8ba4` — `fix(029): thread guest metadata into CLI hydrate export for mixed built-in guests`
- **RED observed (exact documented signature):** assertion 1 fails — `THF_H missing from .gro residues`, residues `{'SOL', 'CH4_H'}` (all 192 guests collapsed to CH4_H; only 2 ITP files staged).
- **Fix:**
  - `quickice/cli/pipeline.py` hydrate branch: `_derive_guest_atom_counts` added to the types import; wrapper gains `guest_descriptors=` and `guest_atom_counts=_derive_guest_atom_counts(hydrate.molecule_index, hydrate_descriptors)` kwargs (mirrors `HydrateStructure.to_candidate()`).
  - `quickice/cli/itp_helpers.py` hydrate branch built-in path: single `_resolve_guest_type_for_hydrate_step` staging replaced with `_detect_builtin_guest_types` loop staging every distinct built-in `{type}_hydrate.itp` (config-less/empty-index fallback preserves the old single-type path).
- **GREEN:** `tests/e2e/hydrate/test_e2e_cli_mixed_builtin_hydrate_grompp.py` → 1 passed (`[molecules] SOL/CH4_H 128/THF_H 64`, both ITPs staged+included, grompp rc==0).

## Regression Sweeps

| Sweep | Result |
|---|---|
| `tests/e2e` | 331 passed / 0 failed (73.29s) |
| `tests/test_cli tests/test_output` (first run, pre re-pin) | 2 failed (pin tests, see Deviations) / 244 passed |
| `tests/test_cli tests/test_output` (after re-pin) | 246 passed / 0 failed (108.73s) |
| **Final gate** `QT_QPA_PLATFORM=offscreen DISPLAY=localhost:11.0 timeout 900 python -m pytest -q` | **1847 passed / 2 skipped / 0 failed / 200.05s / exit 0** (1846 → 1849 collected: +2 +1 new tests; 2 skips pre-existing) |

Note: the final gate without `DISPLAY` core-dumped in a VTK GUI test (known headless-VTK flake per AGENTS.md — MainWindow-level tests want a localhost `DISPLAY` so `is_vtk_available()` returns False). Re-run with `DISPLAY=localhost:11.0` per AGENTS.md guidance was fully green. Not a product regression.

## Deviations from Plan

**1. [Rule 3 - Blocking] Re-pinned 2 pre-existing unit tests that pinned the buggy behavior**
- **Found during:** Task 2 Step 5 regression sweep (`tests/test_cli tests/test_output`: 2 failed)
- **Issue:** Two tests deliberately pinned the OLD buggy behavior and their own docstrings instruct updating consciously when the fix lands:
  - `tests/test_cli/test_mixed_cage_cli.py::test_mixed_cli_hydrate_branch_pins_single_guest_stream` — pinned bug (b) (single-guest-stream collapse; docstring: "update this pin test CONSCIOUSLY... alongside the metadata-threading fix... and re-pin the new behavior").
  - `tests/test_cli/test_cli_pipeline.py::test_pocket_mode_ion` — pinned bug (a) (0-ion orphan include; docstring: "PRODUCTION gap... out of scope for this test-only phase").
- **Fix:** Renamed/rewrote the mixed pin to `test_mixed_cli_hydrate_branch_mixed_builtin_output` (pins mixed output: CH4_H 16 + THF_H 8 in [molecules], both ITPs staged+included, both residue names in .gro; grompp not asserted at 1×1×1 because the box is <2*rcoulomb — grompp coverage lives in the new 2×2×2 e2e). Rewrote `test_pocket_mode_ion` to pin the fixed 0-ion state (NO ion.itp staged, NO include, NO NA/CL in [molecules]) and grompp-validate unconditionally (both ion states valid post-fix).
- **Files modified:** `tests/test_cli/test_mixed_cage_cli.py`, `tests/test_cli/test_cli_pipeline.py`
- **Commit:** `d39e8ba4` (staged alongside the Task-2 files; the pocket test pertains to Task 1's fix but Task 1 was already committed — one reconciliation commit avoids a third churny commit)

**2. [Note] `git add quickice/output/ion_writer.py` printed "The following paths are ignored"**
- quickice/output matches a .gitignore `output/` directory pattern, but `ion_writer.py` IS tracked, so the modification staged and committed correctly (verified via `git diff --cached --stat` before committing). Contradicts the planner's "plain git add works" note only cosmetically — outcome identical.

## Success Criteria Verification

- [x] Bug (a): 0-ion CLI export leaves NO ion.itp and NO `#include "ion.itp"`; grompp rc==0. Ion-present export unchanged (staged + included, counts match, grompp rc==0).
- [x] Bug (b): mixed built-in CLI hydrate export emits CH4_H 128 / THF_H 64 matching the .gro, stages+includes both `{ch4,thf}_hydrate.itp`, grompp rc==0. Single-guest CLI outcome unchanged (all single-guest e2e green: filled-ice/triclinic/mixed_ion etc. — 331/331 in tests/e2e).
- [x] Both fixes reuse existing writer/staging machinery — no writer rewrites, no new deps, no hardcoded TIP4P-ICE/water constants.
- [x] 3 new e2e tests pass; full suite green (1847 passed / 2 skipped / 0 failed); 2 atomic fix commits + this summary.

## Next Phase Readiness

Both 48.3-25 exit-audit follow-ups ((a) and (b)) are now closed — a passing CLI e2e covers the real workflow for 0-ion and mixed built-in hydrate exports. Ready for the user's manual full-workflow UAT run.
