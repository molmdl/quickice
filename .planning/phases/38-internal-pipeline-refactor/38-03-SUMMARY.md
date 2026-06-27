---
phase: 38
plan: 03
subsystem: output
tags: [gro-format, validation, residue-name, overflow-prevention, ValueError]
requires: []
provides: [validate_gro_residue_name(), GRO overflow validation at all write entry points]
affects: [38-04]
tech-stack:
  added: []
  patterns: [fail-fast validation at write entry points]
key-files:
  created: [tests/test_gro_resname_validation.py]
  modified: [quickice/output/gromacs_writer.py, tests/test_output/test_gromacs_export_ion.py]
decisions:
  - Validation rejects overlong names (ValueError) rather than silently truncating — callers must fix upstream
  - validate_gro_residue_name() checks only length, not content (special chars allowed if ≤5)
  - Context strings in error messages identify which writer/branch produced the invalid name
  - Empty MoleculetypeRegistry fallback (source.upper()) can produce >5 char names — now caught instead of truncated
duration: "24m"
completed: 2026-06-27
---

# Phase 38 Plan 03: GRO Residue Name Overflow Validation Summary

Added `validate_gro_residue_name()` that raises ValueError for residue names exceeding the 5-character GRO format limit, replacing all silent truncation and preventing overflow at every GRO write entry point.

## One-liner

validate_gro_residue_name() enforces 5-char GRO limit at 10 write sites, replacing 5 silent truncation sites and preventing format string overflow

## What was done

### Task 1: Add validate_gro_residue_name() + replace all truncation/overflow sites

- Added `validate_gro_residue_name()` function after imports (line 24) that raises ValueError with clear message including the offending name, its length, the 5-char limit, and optional context
- Replaced 5 truncation sites (`res_name[:5]`, `solute_res_name[:5]`, `moleculetype_name[:5]`) with validation calls:
  - `write_ion_gro_file`: custom molecule residue name + solute residue name
  - `write_custom_molecule_gro_file`: moleculetype_name
  - `write_solute_gro_file`: custom molecule residue name + solute residue name
- Added validation before 5 GRO format string sites (`:<5s`) that previously lacked any overflow protection:
  - `write_multi_molecule_gro_file`: res_name after registry/fallback lookup
  - `write_interface_gro_file`: guest_res_name
  - `write_ion_gro_file`: guest_res_name
  - `write_custom_molecule_gro_file`: guest_res_name
  - `write_solute_gro_file`: guest_res_name
- Created `tests/test_gro_resname_validation.py` with 26 tests covering direct validation, error messages, edge cases, _H suffix convention, and integration with write_multi_molecule_gro_file

### Task 2: Verify no regressions + edge case coverage

- Ran full test suite (1068+ tests) — no regressions
- Fixed 1 test regression: `test_gromacs_export_ion::test_solute_itp_copied_when_solutes_present` was passing an empty MoleculetypeRegistry that returned `LIQUID_CH4` (10 chars) via fallback; previously silently truncated to `LIQUI`, now correctly raises ValueError. Fixed by properly registering the solute (`_make_registry_with_liquid_solute()`)
- Added 3 additional edge case tests: _L suffix convention (CH4_L, THF_L pass; overlong fails)
- All 29 validation tests pass; full suite (1071 tests) passes

## Verification

1. `python -m pytest tests/test_gro_resname_validation.py -v` — 29 tests pass ✓
2. `python -m pytest -x --timeout=120` — 1071 pass, no regressions ✓
3. `grep -n 'res_name\[:5\]' quickice/output/gromacs_writer.py` — no matches (all truncation removed) ✓
4. `grep -n 'validate_gro_residue_name' quickice/output/gromacs_writer.py` — 11 matches (1 def + 10 calls) ✓
5. Names >5 chars raise ValueError, names ≤5 pass ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ion export test relying on silent truncation**

- **Found during:** Task 2 (regression testing)
- **Issue:** `test_gromacs_export_ion::test_solute_itp_copied_when_solutes_present` passed an empty `MoleculetypeRegistry()` as `solute_registry`. When `get_gromacs_name("liquid_CH4")` was called on an unregistered key, it returned `"LIQUID_CH4"` (10 chars) via fallback. The old code silently truncated this to `"LIQUI"`. The new validation correctly raises ValueError.
- **Fix:** Added `_make_registry_with_liquid_solute()` helper that properly registers the solute in the registry (producing "CH4_L" = 5 chars), and used it in the test.
- **Files modified:** `tests/test_output/test_gromacs_export_ion.py`
- **Commit:** 66be66e

## Decisions Made

1. **Reject-and-report vs. truncate:** Validation raises ValueError rather than truncating. The truncation behavior was masking bugs upstream (e.g., empty registries producing 10-char fallback names). Callers must fix the name at the source.
2. **Validation only checks length:** Content validation (banning spaces, special chars, etc.) is not the validator's responsibility — only the 5-char GRO format width matters.
3. **Context strings identify the call site:** Each validation call includes a context like "Custom molecule residue name" or "Solute residue name" to help users identify which writer/branch produced the invalid name.

## Next Phase Readiness

- [x] All GRO write entry points now have validation
- [x] No silent truncation or overflow anywhere in GRO writing
- [x] _H and _L suffix naming conventions (≤5 chars) confirmed working
- [x] Full test suite passes
- No blockers for Plan 04
