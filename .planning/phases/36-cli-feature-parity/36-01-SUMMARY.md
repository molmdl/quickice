---
phase: 36
plan: 01
subsystem: cli
tags: [argparse, validation, hydrate, custom-molecule, solute, ion, csv]
requires: []
provides: [parser.py-v4.5-flags, validate_pipeline_args, custom_positions.csv]
affects: [36-03, 36-04, 36-05, 36-06, 36-07, 36-08, 36-09, 36-10, 36-11]
tech-stack:
  added: []
  patterns: [cross-flag-validation, argument-groups-by-pipeline-step]
key-files:
  created: [quickice/data/examples/custom_positions.csv]
  modified: [quickice/cli/parser.py]
decisions:
  - id: D1
    choice: "validate_pipeline_args() calls validate_interface_args() internally"
    rationale: "Single entry point for all validation; callers don't need to remember both"
  - id: D2
    choice: "getattr(args, 'hydrate', False) in validate_interface_args for nmolecules check"
    rationale: "Backward-compatible: if hydrate attribute doesn't exist (pre-v4.5 args), returns False"
  - id: D3
    choice: "Custom placement random validation only when custom_gro is provided"
    rationale: "Prevents false positives: --custom-placement random without --custom-gro is harmless default"
---

# Phase 36 Plan 01: Extend CLI Parser with v4.5 Flag Groups Summary

**One-liner:** Extended parser.py with 5 new argument groups (hydrate, custom molecule, solute, ion, output) plus validate_pipeline_args() with 11 cross-flag validation rules and example CSV file.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend parser.py with v4.5 flag groups and validation | c205724 | quickice/cli/parser.py |
| 2 | Create example CSV file for custom placement mode | a09dc1c | quickice/data/examples/custom_positions.csv |

## What Was Built

### Task 1: Extended parser.py with v4.5 flag groups and validation

Added 5 new argument groups to `create_parser()`:

1. **Hydrate generation** group: `--hydrate`, `--lattice-type` (sI/sII/sH), `--guest` (CH4/THF), `--supercell-x/y/z`, `--cage-occupancy-small/large`
2. **Custom molecule insertion** group: `--custom-gro`, `--custom-itp`, `--custom-placement` (random/custom), `--custom-count`, `--custom-concentration`, `--custom-positions-file`
3. **Solute insertion** group: `--solute-type` (CH4/THF), `--solute-concentration`, `--solute-source` (interface/custom)
4. **Ion insertion** group: `--ion-concentration`, `--ion-source` (interface/custom/solute)
5. **Output options** extension: `--no-overwrite`

Created `validate_pipeline_args()` with 11 cross-flag validation rules, all producing exit code 2:
- `--hydrate` + `--nmolecules` → mutually exclusive
- `--custom-gro` ↔ `--custom-itp` → require each other
- `--custom-gro` requires `--interface`
- `--custom-placement custom` requires `--custom-positions-file`
- `--custom-placement random` requires `--custom-count` or `--custom-concentration` (not both)
- `--solute-type` requires `--solute-concentration`
- `--solute-type` requires `--interface`
- `--solute-source custom` requires `--custom-gro`
- `--ion-concentration` requires `--interface`
- `--ion-source custom` requires `--custom-gro`
- `--ion-source solute` requires `--solute-type`

### Task 2: Created example CSV file

`quickice/data/examples/custom_positions.csv` with:
- 3 data rows, 6 columns (x, y, z, alpha, beta, gamma)
- Comment header with # prefix documenting column format and ZXZ Euler convention
- Parseable with standard csv.reader

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed --hydrate rejected by validate_interface_args nmolecules check**

- **Found during:** Task 1 verification
- **Issue:** `--hydrate` without `--nmolecules` was rejected by `validate_interface_args()` because it only exempted `--interface` from the nmolecules requirement
- **Fix:** Updated nmolecules check in `validate_interface_args()` to use `getattr(args, 'hydrate', False)` to also exempt `--hydrate` mode
- **Files modified:** quickice/cli/parser.py
- **Commit:** c205724

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | validate_pipeline_args() calls validate_interface_args() internally | Single entry point for all validation; callers don't need to remember both |
| D2 | getattr(args, 'hydrate', False) for nmolecules check | Backward-compatible: returns False if hydrate attribute doesn't exist on pre-v4.5 args |
| D3 | Custom placement random validation only when custom_gro is provided | Prevents false positives: --custom-placement random without --custom-gro is harmless default |

## Verification Results

- All 23 existing CLI integration tests pass
- New flags parse to correct Namespace attributes (hydrate, lattice_type, guest, solute_type, ion_source, etc.)
- `validate_pipeline_args()` catches all 11 cross-flag errors with exit code 2
- Example CSV file correctly formatted (3 data rows, 6 columns, comment header)

## Next Phase Readiness

- parser.py provides the complete CLI interface that Plan 03 (pipeline executor) will consume
- All new Namespace attributes documented in `get_arguments()` docstring
- `validate_pipeline_args()` is the single validation entry point for the pipeline executor
