---
phase: 41-gromacs-export-for-custom-guests
verified: 2026-07-05T06:45:50Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: none
  previous_score: N/A
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 41: GROMACS Export for Custom Guests Verification Report

**Phase Goal:** Custom guest hydrate structures export to valid GROMACS input files that pass grompp
**Verified:** 2026-07-05T06:45:50Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                      | Status     | Evidence                                                                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Custom guest appears in .top with correct _H suffix moleculetype name                                      | ✓ VERIFIED | `test_molecules_has_mol_h` (multi-molecule + interface TOP) asserts `MOL_H` in `[molecules]`; both e2e grompp tests assert `MOL_H` in `[molecules]` after running real `gmx grompp`. Writer branches on `custom_guest_info["mol_type"]` → `residue_name` (`MOL_H`). |
| 2   | Custom guest atomtypes are commented out in the bundled .itp and merged into main .top [atomtypes] with dedup | ✓ VERIFIED | `transform_guest_itp` calls `comment_out_atomtypes_in_itp` (gromacs_writer.py:698); `test_copy_custom_guest_itp_transforms` asserts `; [ atomtypes ]` present and no uncommented header. `_merge_custom_atomtypes` (gromacs_writer.py:239) writes oh/ho, dedups hc/c3/h1 — `test_atomtypes_has_oh_ho` + `test_atomtypes_dedup_*` pass. | 
| 3   | GRO export writes correct ≤5-char residue name for custom guest (with _H suffix)                            | ✓ VERIFIED | `test_custom_guest_writes_mol_h` (multi-molecule + interface GRO) asserts `MOL_H` residues; `test_custom_residue_passes_validate` confirms `validate_gro_residue_name` accepts `MOL_H` (5 chars). e2e tests assert `.gro` residues contain `MOL_H`. |
| 4   | GROMACS grompp validates successfully on exported custom guest hydrate structures                          | ✓ VERIFIED | `test_custom_guest_gui_grompp_passes` + `test_custom_guest_cli_grompp_passes` both run real `gmx grompp` (gmx 2023.5-plumed on PATH, not skipped) and `assert exit_code == 0`. Tests also assert ITP completeness + GRO/TOP consistency before grompp. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact                                          | Expected                                                | Status      | Details                                                                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `quickice/output/gromacs_writer.py`               | `_merge_custom_atomtypes` + `custom_guest_info` params  | ✓ VERIFIED  | `_merge_custom_atomtypes` at :239 (35 lines, calls parse_itp_atomtypes/_check_custom_atomtype_conflict/_format_custom_atomtype_line); `custom_guest_info` param on all 4 writers (write_multi_molecule_gro_file :1604, write_multi_molecule_top_file :1733, write_interface_gro_file :1046, write_interface_top_file :1445). |
| `quickice/gui/hydrate_export.py`                   | `export_hydrate` branches on `is_custom_guest`          | ✓ VERIFIED  | Lines 154-175: builds `custom_guest_info` dict with `mol_type`/`residue_name`/`itp_path`, threads to both GRO and TOP writers. Built-in path sets `custom_guest_info=None`. |
| `quickice/cli/itp_helpers.py`                      | `copy_custom_guest_itp` + custom branch in copy_itp     | ✓ VERIFIED  | `copy_custom_guest_itp` at :201 (38 lines, calls `transform_guest_itp` with `_H` suffix, validates ≤5 chars, returns dest name or None). Custom branch in `copy_itp_files_for_structure` (hydrate step). |
| `quickice/cli/pipeline.py`                         | `_build_custom_guest_info` + `_run_export_step` thread | ✓ VERIFIED  | `_build_custom_guest_info` at :32 (returns dict or None based on `is_custom_guest`). `_run_export_step` at :750 calls it (line 845) and threads to `write_interface_gro_file`/`write_interface_top_file` (lines 846-847). |
| `tests/test_output/test_merge_custom_atomtypes.py` | 5 unit tests for merge helper                            | ✓ VERIFIED  | 173 lines, 5 tests pass (new-write, dedup, LJ-conflict-raises, no-section-noop, real-etoh-itp).                                                                                  |
| `tests/test_output/test_multi_molecule_gro_custom_guest.py` | 4 unit tests for GRO custom guest             | ✓ VERIFIED  | 173 lines, 4 tests pass (custom→MOL_H, water→SOL, built-in CH4 regression, validate 5-char).                                                                                    |
| `tests/test_output/test_multi_molecule_top_custom_guest.py`  | 6 unit tests for TOP custom guest              | ✓ VERIFIED  | 196 lines, 6 tests pass (MOL_H in molecules, oh/ho in atomtypes, dedup hc/c3/h1, #include etoh.itp, atomtypes-before-include, built-in regression).                              |
| `tests/test_output/test_interface_gro_custom_guest.py` | 4 unit tests for interface GRO custom guest     | ✓ VERIFIED  | 190 lines, 4 tests pass (MOL_H, atom count, skips detect_guest_type_from_atoms, built-in regression).                                                                            |
| `tests/test_output/test_interface_top_custom_guest.py` | 6 unit tests for interface TOP custom guest       | ✓ VERIFIED  | 252 lines, 6 tests pass (MOL_H, oh/ho, dedup, #include, skips detect, built-in regression).                                                                                     |
| `tests/test_output/test_gromacs_export_hydrate_custom.py` | GUI exporter custom guest test                  | ✓ VERIFIED  | 387 lines, 1 test class pass (`test_export_custom_guest`).                                                                                                                       |
| `tests/test_cli/test_itp_helpers_custom_guest.py`  | 5 unit tests for CLI ITP helpers                        | ✓ VERIFIED  | 239 lines, 5 tests pass (transform, missing-returns-None, name-too-long, hydrate-step-routes-to-custom, built-in CH4 regression).                                              |
| `tests/test_cli/test_pipeline_custom_guest_export.py` | 4 unit tests for CLI pipeline threading              | ✓ VERIFIED  | 274 lines, 4 tests pass (build_custom_guest_info custom, builtin-None, run_export_step custom, built-in CH4 regression).                                                         |
| `tests/test_e2e_stage_custom_guest_itp.py`        | 3 e2e tests for ITP staging                             | ✓ VERIFIED  | 122 lines, 3 tests pass (stages transformed MOL_H, overwrites under transformed copy, name-too-long raises).                                                                     |
| `tests/test_e2e_custom_guest_gui_grompp.py`       | e2e grompp GUI path                                      | ✓ VERIFIED  | 141 lines, 1 test passes — runs real `gmx grompp`, asserts exit_code==0, asserts SOL+MOL_H in molecules and GRO.                                                                |
| `tests/test_e2e_custom_guest_cli_grompp.py`       | e2e grompp CLI path                                      | ✓ VERIFIED  | 152 lines, 1 test passes — runs real `gmx grompp`, asserts exit_code==0, asserts SOL+MOL_H in molecules and GRO.                                                                 |

### Key Link Verification

| From                                                | To                                                          | Via                                                                                  | Status   | Details                                                                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| `_merge_custom_atomtypes`                            | `parse_itp_atomtypes`                                       | `parse_itp_atomtypes(itp_path)`                                                      | WIRED    | Called at gromacs_writer.py:254; returns list of atomtype tuples.                                                          |
| `_merge_custom_atomtypes`                            | `_check_custom_atomtype_conflict`                           | conflict check per atomtype                                                          | WIRED    | Called at gromacs_writer.py:261; raises ValueError on LJ mismatch.                                                        |
| `_merge_custom_atomtypes`                            | `_format_custom_atomtype_line`                             | `f.write(_format_custom_atomtype_line(atomtype))`                                   | WIRED    | Called at gromacs_writer.py:263; writes formatted atomtype line.                                                           |
| `write_multi_molecule_top_file`                      | `_merge_custom_atomtypes`                                   | `custom_guest_info.get("itp_path")` guard → merge call                               | WIRED    | Called at gromacs_writer.py:1883-1888; merge placed after built-in GAFF2 blocks, before #include.                          |
| `write_interface_top_file`                           | `_merge_custom_atomtypes`                                   | `custom_guest_info` guard → merge call                                               | WIRED    | Called at gromacs_writer.py:1526-1528; merge placed after built-in blocks, before #include.                                |
| `write_multi_molecule_gro_file`                      | `custom_guest_info["residue_name"]`                         | 3-branch residue resolution (custom → built-in → UNK)                               | WIRED    | gromacs_writer.py:1675-1676; `validate_gro_residue_name` called unconditionally.                                          |
| `write_interface_gro_file`                           | `custom_guest_info["residue_name"]`                         | custom branch in residue-name resolution                                             | WIRED    | gromacs_writer.py:1230-1236; skips `detect_guest_type_from_atoms` (P3 fix, EXPORT-05).                                    |
| GUI `export_hydrate`                                 | `write_multi_molecule_gro_file`/`write_multi_molecule_top_file` | `custom_guest_info={mol_type, residue_name, itp_path}`                               | WIRED    | hydrate_export.py:163-197; dict built from `config.guest_*` and passed to both writers.                                    |
| CLI `_run_export_step` (hydrate)                     | `write_interface_gro_file`/`write_interface_top_file`      | `custom_guest_info = _build_custom_guest_info(...)`                                  | WIRED    | pipeline.py:845-847; threads dict to both writers.                                                                         |
| CLI `copy_itp_files_for_structure` (hydrate)         | `copy_custom_guest_itp`                                     | custom branch routes to `copy_custom_guest_itp`                                      | WIRED    | itp_helpers.py:282+; test_hydrate_step_custom_routes_to_copy_custom passes.                                                |
| `copy_custom_guest_itp`                              | `transform_guest_itp`                                       | `transform_guest_itp(content, residue_name, suffix="_H")`                            | WIRED    | itp_helpers.py:229; comments out [atomtypes], renames moleculetype, rewrites [atoms] resname.                               |
| e2e grompp tests                                     | real `gmx grompp` binary                                    | `run_gmx_grompp(ws, gro_file, top_file)` → subprocess                                | WIRED    | Both e2e tests call `run_gmx_grompp` and `assert exit_code == 0`; gmx 2023.5-plumed on PATH (not skipped).                 |

### Requirements Coverage

| Requirement | Status      | Blocking Issue |
| ----------- | ----------- | -------------- |
| EXPORT-01: Custom guest appears in GROMACS .top with correct _H suffix moleculetype name | ✓ SATISFIED | — |
| EXPORT-02: Custom guest atomtypes are commented out in bundled .itp (moved to main .top [atomtypes] section) | ✓ SATISFIED | — |
| EXPORT-03: Custom guest ITP atomtypes are merged into main .top with deduplication (no duplicate atomtype entries) | ✓ SATISFIED | — |
| EXPORT-04: GRO export writes correct residue name for custom guest (≤5 chars with _H suffix) | ✓ SATISFIED | — |
| EXPORT-05: GROMACS export uses mol_type identity from pipeline (not re-detection from atom names) — P3 fix | ✓ SATISFIED | — |
| EXPORT-06: GROMACS grompp validates successfully on exported custom guest hydrate structures | ✓ SATISFIED | — |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| —    | —    | —       | —        | No TODO/FIXME/placeholder/stub patterns found in any phase-41 source or test file. |

### Human Verification Required

None. All phase-41 must-haves are verifiable programmatically and have been verified:
- gmx grompp is invoked by e2e tests (not mocked) and exits 0 on both GUI and CLI custom-guest hydrate paths.
- All unit tests assert the exact residue names, moleculetype names, atomtype dedup, and ITP transforms that the success criteria require.
- The P3 fix (EXPORT-05) is proven by monkeypatching `detect_guest_type_from_atoms` to raise `AssertionError` and asserting the custom branch does NOT trigger it.

### Gaps Summary

No gaps found. All 4 success-criteria truths are verified, all 15 required artifacts exist and are substantive (173-387 lines each, no stub patterns), all 13 key links are wired, all 6 requirements (EXPORT-01 through EXPORT-06) are satisfied, and no anti-patterns were detected.

**Test results summary:**
- Phase-41 output unit tests: 26/26 pass (1.06s)
- Phase-41 CLI/stage tests: 12/12 pass (0.35s)
- Phase-41 e2e grompp tests (real `gmx grompp`): 2/2 pass (0.33s, gmx not skipped)
- Regression — `tests/test_output/test_gromacs_export_hydrate.py`: 8/8 pass (0.79s)
- Regression — `tests/test_e2e_gmx_validation.py`: 18/18 pass (4.73s)

**Code-level must-haves (all confirmed):**
- `_merge_custom_atomtypes` importable from `quickice.output.gromacs_writer`
- `custom_guest_info` parameter present on all 4 writer signatures (multi-molecule GRO/TOP + interface GRO/TOP)
- `copy_custom_guest_itp` importable from `quickice.cli.itp_helpers`
- `_build_custom_guest_info` importable from `quickice.cli.pipeline`
- GUI `export_hydrate` source contains both `is_custom_guest` and `guest_residue_name`

---

_Verified: 2026-07-05T06:45:50Z_
_Verifier: OpenCode (gsd-verifier)_
