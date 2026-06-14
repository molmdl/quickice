---
phase: 36
plan: 03
subsystem: cli
tags: [pipeline, execute, fail-fast, stubs, csv-parser, progress-reporting]
requires: [36-01]
provides: [CLIPipeline-class, execute-method, _get_source_structure, _parse_positions_csv, step-stubs]
affects: [36-04, 36-05, 36-06, 36-07, 36-08, 36-09, 36-10, 36-11]
tech-stack:
  added: [csv]
  patterns: [ordered-step-pipeline, fail-fast-execution, source-name-resolution]
key-files:
  created: [quickice/cli/pipeline.py]
  modified: []
decisions:
  - id: D1
    choice: "Step stubs return exit code 1 with report_progress message"
    rationale: "Stubs clearly indicate not-yet-implemented status; replaced incrementally by Plans 05-08"
  - id: D2
    choice: "_parse_positions_csv is a @staticmethod"
    rationale: "No instance state needed; callable without instantiating CLIPipeline; matches testing pattern"
  - id: D3
    choice: "_get_source_structure raises ValueError for unknown names"
    rationale: "Fail-fast on programmer error (wrong source name) rather than silently returning None"
  - id: D4
    choice: "report_progress prints to stderr with [PROGRESS] prefix"
    rationale: "Stderr for diagnostics allows stdout redirection for data; prefix enables grep filtering"
  - id: D5
    choice: "No GUI imports in pipeline.py"
    rationale: "CLI module works without PySide6/VTK; matches itp_helpers.py pattern"
---

# Phase 36 Plan 03: CLIPipeline Scaffold Summary

**One-liner:** CLIPipeline class with execute() running 6 ordered steps fail-fast, _get_source_structure() source resolver, _parse_positions_csv() static CSV parser, and step stubs returning exit code 1.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create CLIPipeline scaffold with execute(), helpers, and stubs | edd6d5e | quickice/cli/pipeline.py |

## What Was Built

### Task 1: CLIPipeline scaffold with execute(), helpers, and stubs

Created `quickice/cli/pipeline.py` with the complete pipeline class scaffold:

**Module-level:**
- `report_progress(message: str)` — prints `[PROGRESS] {message}` to stderr
- `logger = logging.getLogger(__name__)` for structured logging

**CLIPipeline class:**
- `__init__(args)` — stores argparse.Namespace and initializes 7 result slots (`_interface_result`, `_hydrate_result`, `_custom_result`, `_solute_result`, `_ion_result`, `_ice_candidate`, `_output_dir`)
- `execute() -> int` — orchestrates 6 steps in order with fail-fast semantics:
  1. Create output directory with `mkdir(parents=True, exist_ok=True)`
  2. Check `--no-overwrite` guard (skips if output dir already has files)
  3. Source step (if `--interface` or `--hydrate`)
  4. Interface step (if `--interface`)
  5. Custom molecule step (if `--custom-gro`)
  6. Solute step (if `--solute-type`)
  7. Ion step (if `--ion-concentration`)
  8. Export step (always runs as final step)
- `_get_source_structure(source_name: str)` — maps "interface"/"custom"/"solute" to stored results; raises ValueError for unknown names
- `_parse_positions_csv(filepath) -> tuple[list[tuple], list[tuple]]` — static method that:
  - Skips `#` comment lines and blank rows
  - Validates 6 columns per row (x, y, z, alpha, beta, gamma)
  - Parses as float, returns (positions, rotations) tuples
  - Raises FileNotFoundError for missing files, ValueError for wrong columns or non-numeric values
- 6 step stubs (`_run_source_step`, `_run_interface_step`, `_run_custom_step`, `_run_solute_step`, `_run_ion_step`, `_run_export_step`) — each returns 1 with `report_progress("... not yet implemented")`

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Step stubs return exit code 1 with report_progress | Clear not-yet-implemented status; replaced incrementally by Plans 05-08 |
| D2 | _parse_positions_csv is a @staticmethod | No instance state needed; testable without CLIPipeline instance |
| D3 | _get_source_structure raises ValueError for unknown names | Fail-fast on programmer error rather than silent None |
| D4 | report_progress prints to stderr with [PROGRESS] prefix | Stderr for diagnostics; prefix enables grep filtering |
| D5 | No GUI imports in pipeline.py | CLI module works without PySide6/VTK |

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

- **Unblocked:** Plan 04 (CLI main entry point can reference CLIPipeline)
- **Unblocked:** Plans 05-08 (step stubs can be replaced with real implementations)
- **Ready:** `_get_source_structure()` enables source resolution for solute/ion steps
- **Ready:** `_parse_positions_csv()` enables custom placement CSV parsing in Plan 05
