---
phase: 41-gromacs-export-for-custom-guests
plan: 08
subsystem: cli
tags: [gromacs, custom-guest, hydrate-export, cli, pipeline, custom_guest_info]

# Dependency graph
requires:
  - phase: 41-04
    provides: write_interface_gro_file(custom_guest_info=None) keyword param + metadata-driven custom guest branch (chunk by molecule_index .count, residue_name from dict, no detect_guest_type_from_atoms)
  - phase: 41-05
    provides: write_interface_top_file(custom_guest_info=None) keyword param + _merge_custom_atomtypes integration + #include custom .itp basename + [molecules] residue_name
  - phase: 41-07
    provides: copy_custom_guest_itp + is_custom_guest routing in copy_itp_files_for_structure hydrate branch (already invoked by _run_export_step — unchanged here)
  - phase: 40-custom-guest-bridge-core
    provides: HydrateConfig.is_custom_guest property, guest_type, guest_residue_name, guest_itp_path fields
provides:
  - "_build_custom_guest_info(config) -> dict | None — module-level helper returning {'mol_type','residue_name','itp_path'} for a custom HydrateConfig and None for built-in/None"
  - "custom_guest_info threading in CLIPipeline._run_export_step hydrate branch — passes the dict to write_interface_gro_file + write_interface_top_file; built-in hydrate path passes None (no regression)"
affects: [41-11, cli-hydrate-export, custom-guest-grompp, e2e-gmx-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level _build_custom_guest_info helper (not a CLIPipeline method) so it can be unit-tested in isolation without instantiating the pipeline — mirrors the report_progress placement before the CLIPipeline class"
    - "Thread custom_guest_info from hydrate.config at the call site (write_interface_*) — the ITP copy stays with copy_itp_files_for_structure (plan 41-07); the writers consume the dict for residue naming + atomtypes merge + #include, the ITP copier reads config directly"

key-files:
  created:
    - tests/test_cli/test_pipeline_custom_guest_export.py
  modified:
    - quickice/cli/pipeline.py

key-decisions:
  - "Reuse the top-level `from pathlib import Path` import in pipeline.py (line 13) inside _build_custom_guest_info — no inline re-import; the plan's `from pathlib import Path` snippet was simplified to use the existing import"
  - "_build_custom_guest_info returns None for config is None AND for not is_custom_guest — built-in ch4/thf hydrate exports pass custom_guest_info=None to both writers (their built-in branch is byte-identical, verified by test_run_export_step_builtin_ch4_regression)"
  - "Integration test (test 3) uses ABSOLUTE guest_itp_path (ETOH_ITP constant) for cwd-independent ITP copy; unit test 1 uses the plan's literal relative path 'quickice/data/custom/etoh.itp' to match the exact Path-equality assertion (Path equality is structural, no file I/O in test 1)"
  - "HydrateStructure built manually (2 water + 1 ethanol, 17 atoms, no GenIce2, <1s per test) — mirrors tests/test_output/conftest.py::simple_hydrate_structure and tests/test_cli/test_itp_helpers_custom_guest.py; MoleculeIndex(8, 9, 'etoh_e2e') matches config.guest_type so the custom_guest_info['mol_type'] lookup in both writers fires"
  - "Existing except (OSError, ValueError) handler in _run_export_step kept AS-IS (lines 844-847) — no bare except Exception added (AGENTS.md); the helper's getattr(config, 'is_custom_guest', False) guard means a structure without config still passes None safely"

patterns-established:
  - "Module-level private helper for dict construction (_build_custom_guest_info) placed before the CLIPipeline class — unit-testable without pipeline instantiation; same pattern as report_progress"
  - "config -> custom_guest_info indirection: one branch-bound variable fed to BOTH writers (gro + top), so the ITP path/residue_name/mol_type stay consistent across the .gro/.top pair (single source of truth, no chance of drift)"

# Metrics
duration: 5min
completed: 2026-07-05
---

# Phase 41 Plan 08: CLI Custom Guest Threading Summary

**`_build_custom_guest_info` module helper + `_run_export_step` hydrate branch now threads the `custom_guest_info` dict (`mol_type`/`residue_name`/`itp_path`) into `write_interface_gro_file` + `write_interface_top_file`, so the CLI hydrate export for a custom ethanol guest writes `MOL_H` residues in `.gro`, `[molecules] MOL_H` + `#include "etoh.itp"` in `.top`, and copies the transformed `etoh.itp` (via plan 41-07) — built-in ch4 path unchanged (`custom_guest_info=None`).**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-07-05T06:36:41Z
- **Completed:** 2026-07-05T06:42Z
- **Tasks:** 2
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments
- Added `_build_custom_guest_info(config) -> dict | None` as a module-level function in `quickice/cli/pipeline.py` (placed before `CLIPipeline`, after `report_progress`). Returns `{'mol_type': config.guest_type, 'residue_name': '{guest_residue_name}_H', 'itp_path': Path(config.guest_itp_path)}` for custom guests, `None` for built-in/`None`. Reuses the top-level `from pathlib import Path` import (no inline re-import).
- Threaded `custom_guest_info` into the hydrate branch of `CLIPipeline._run_export_step`: after building the `InterfaceStructure` wrapper, `_build_custom_guest_info(getattr(hydrate, "config", None))` is computed and passed as a keyword arg to both `write_interface_gro_file` and `write_interface_top_file` (params added by plans 41-04/41-05). Built-in ch4/thf path passes `None` (writers' built-in branch byte-identical).
- 4 tests in `tests/test_cli/test_pipeline_custom_guest_export.py`: helper unit test (custom → dict), helper unit test (built-in/None → None), integration test (custom ethanol hydrate → MOL_H in .gro/.top, etoh.itp + tip4p-ice.itp copied, [molecules] SOL=2 MOL_H=1, #include etoh.itp), regression test (built-in ch4 → CH4_H + ch4_hydrate.itp, custom_guest_info=None path).
- Verified zero regression: all 4 new tests pass; 204 existing `pipeline or export`-tagged tests still pass; `inspect.getsource(CLIPipeline._run_export_step)` contains `custom_guest_info`; no bare `except Exception` introduced (existing `except (OSError, ValueError)` handler kept).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _build_custom_guest_info + thread into _run_export_step** - `e751f5a` (feat)
2. **Task 2: Unit + integration tests for CLI custom guest export** - `c80cb94` (test)

## Files Created/Modified
- `quickice/cli/pipeline.py` - Added module-level `_build_custom_guest_info` helper (21 lines, placed after `report_progress` before `CLIPipeline`); modified the hydrate branch of `_run_export_step` to compute `custom_guest_info = _build_custom_guest_info(getattr(hydrate, "config", None))` and pass it to both `write_interface_gro_file` and `write_interface_top_file` (5-line change). Existing `except (OSError, ValueError)` handler untouched; `copy_itp_files_for_structure` call unchanged (plan 41-07 routing handles the ITP copy).
- `tests/test_cli/test_pipeline_custom_guest_export.py` - New test file (274 lines, 4 tests) covering `_build_custom_guest_info` unit contract (custom/built-in/None) and `_run_export_step` integration for both custom ethanol (MOL_H + etoh.itp) and built-in ch4 (CH4_H + ch4_hydrate.itp). Uses absolute `ETOH_ITP`/`ETOH_GRO` paths for cwd-independence in the ITP copy; `HydrateStructure` built manually (no GenIce2, <1s per test).

## Decisions Made
- **Reuse top-level `Path` import:** The plan's snippet included an inline `from pathlib import Path` inside the helper, but `pipeline.py` already imports `Path` at line 13 (`from pathlib import Path`). Reused the top-level import instead of re-importing inside the helper — keeps the module's import block authoritative and avoids a redundant local import.
- **Test 1 follows the plan's literal relative-path assertion; test 3 uses absolute paths:** Test 1 (`test_build_custom_guest_info_custom`) uses the plan's exact `guest_itp_path="quickice/data/custom/etoh.itp"` and asserts against `Path("quickice/data/custom/etoh.itp")` — `Path` equality is structural and no file I/O happens in the helper, so cwd is irrelevant. Test 3 (`test_run_export_step_custom_hydrate`) uses the absolute `ETOH_ITP` constant because the ITP copy (`copy_custom_guest_itp` → `src.read_text()`) actually reads the file, so cwd-independence matters. This mirrors the established convention in `tests/test_cli/test_itp_helpers_custom_guest.py` (which also uses absolute `ETOH_ITP`).
- **`HydrateStructure` built manually (no GenIce2):** 2-water + 1-ethanol system (17 atoms) with `molecule_index = [MoleculeIndex(0,4,"water"), MoleculeIndex(4,4,"water"), MoleculeIndex(8,9,"etoh_e2e")]` and `config.guest_type="etoh_e2e"` so the `custom_guest_info["mol_type"]` lookup in `write_interface_gro_file` (line 1236: `m.mol_type == custom_guest_info["mol_type"]`) fires and chunks the 9-atom ethanol by `count=9` (NOT the `count_guest_atoms` heuristic that miscounted ethanol as 5 — P3 fix from plan 41-04). Same pattern as `simple_hydrate_structure` in `tests/test_output/conftest.py` and the manual construction in `tests/test_cli/test_itp_helpers_custom_guest.py`.
- **Keep the existing `except (OSError, ValueError)` handler:** AGENTS.md forbids bare `except Exception` in `pipeline.py`. The plan's must_haves explicitly require "No bare `except Exception` introduced". The existing handler at lines 844-847 (now shifted by the helper insertion) is kept AS-IS — `_build_custom_guest_info` cannot raise (it uses `getattr` guards), and the writers' `validate_gro_residue_name` raises `ValueError` (caught) and `OSError` propagates from I/O (caught). No new exception types introduced.

## Deviations from Plan

None - plan executed exactly as written. The two code changes (the `_build_custom_guest_info` helper body and the 5-line threading in the hydrate branch) were implemented verbatim from the plan's specified snippets, with the single documented simplification of reusing the top-level `Path` import (the plan explicitly said "check the top of pipeline.py; `Path` is already imported ... Reuse the top-level import; do NOT re-import if already present" — so this is plan-sanctioned, not a deviation). The 4 tests mirror the plan's 4 named tests with the specified assertions.

## Issues Encountered
None - the plan's code references were accurate (pipeline.py:785-821 hydrate branch, the `except (OSError, ValueError)` handler, the `copy_itp_files_for_structure` call). The verification command `python -c "...m._run_export_step..."` in the plan needed `m.CLIPipeline._run_export_step` (a method, not a module attribute) — corrected in the verification run, but this is a typo in the plan's verification snippet, not a code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `_build_custom_guest_info` is importable and tested; `CLIPipeline._run_export_step` now passes `custom_guest_info` to both `write_interface_*` writers. The CLI hydrate export path for custom guests is fully wired (writers 41-04/41-05 + ITP copy 41-07 + threading 41-08).
- Plan 41-11 (CLI custom-guest grompp e2e) can now exercise the full CLI export path (`_run_export_step` → writers + `copy_itp_files_for_structure`) on a custom ethanol hydrate and run `gmx grompp` to validate the `.gro`/`.top`/`.itp` triple is internally consistent — the untracked `tests/test_e2e_custom_guest_cli_grompp.py` stub already present in the working tree is the 41-11 starting point.
- The built-in ch4 path is verified unchanged (`test_run_export_step_builtin_ch4_regression`); no blockers for downstream plans.
- All 204 existing `pipeline or export`-tagged tests pass — no regression in the CLI pipeline, GROMACS writers, or e2e export chains.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-05*
