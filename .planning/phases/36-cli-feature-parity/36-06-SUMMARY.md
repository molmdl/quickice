---
phase: 36
plan: 06
subsystem: cli
tags: [hydrate, HydrateStructure, source-step, guest_count, water_count, to_candidate]
requires: [36-05]
provides: [hydrate-source-branch]
affects: [36-07, 36-08, 36-09]
tech-stack:
  added: []
  patterns: [hydrate-branch-in-source-step, guest_type-lower-normalization]
key-files:
  created: []
  modified: [quickice/cli/pipeline.py]
decisions:
  - guest_type .lower() normalization — CLI parser uses uppercase CH4/THF but HydrateConfig validates against lowercase
  - guest_count/water_count (NOT guest_nmolecules/water_nmolecules) — HydrateStructure uses different naming from InterfaceStructure
  - Inline try/except ImportError for science deps — pipeline.py must work without optional packages
  - hydrate→candidate via to_candidate() when --interface also set — enables hydrate→interface workflow
  - Comment wording avoids literal "guest_nmolecules" string — prevents false-positive verification check
duration: 49s
completed: 2026-06-14
---

# Phase 36 Plan 06: Hydrate Source Step Summary

**One-liner:** Added hydrate generation branch to `_run_source_step()` with correct HydrateStructure attribute references (guest_count/water_count, .lower() normalization, to_candidate() conversion).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Add hydrate branch to _run_source_step with correct HydrateStructure attributes | e79daa9 | quickice/cli/pipeline.py |

## What Changed

### quickice/cli/pipeline.py

- **Added hydrate branch** at the top of `_run_source_step()`: when `--hydrate` flag is set, generates a `HydrateStructure` via `HydrateStructureGenerator` with `HydrateConfig`
- **guest_type .lower() normalization**: CLI args use uppercase (`CH4`, `THF`) but `HydrateConfig` validates against lowercase (`ch4`, `thf`) — `.lower()` call ensures compatibility
- **Correct HydrateStructure attribute names**: Uses `guest_count` and `water_count` (NOT `guest_nmolecules`/`water_nmolecules` which don't exist on `HydrateStructure`)
- **hydrate→candidate path**: When `--interface` is also set, calls `self._hydrate_result.to_candidate()` to convert the hydrate to an ice `Candidate` for downstream interface generation
- **Early return**: Hydrate branch returns 0 immediately, skipping the ice candidate generation below
- **Ice candidate guard**: Existing ice candidate code now runs only when `self._ice_candidate is None` (i.e., hydrate branch didn't already set it)

## HydrateStructure Attribute Mapping

| HydrateStructure field | Type | Used in pipeline.py |
|------------------------|------|---------------------|
| `guest_count` | `int` | Yes — progress report |
| `water_count` | `int` | Yes — progress report |
| `positions` | `ndarray` | Via to_candidate() |
| `atom_names` | `list[str]` | Via to_candidate() |
| `cell` | `ndarray` | Via to_candidate() |
| `molecule_index` | `list[MoleculeIndex]` | Via to_candidate() |
| `to_candidate()` | method | Yes — hydrate→interface bridge |

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None.
