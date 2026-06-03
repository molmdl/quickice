---
phase: e2e-compute-export
plan: 01
subsystem: export-bridge-testing
tags: [gromacs, e2e, export, parsing, conftest, tip4p-ice, hydrate]
requires:
  - e2e-api-workflow (112 tests, computation pipeline validated)
  - e2e-export-test (30+ tests, export pipeline with mock fixtures)
provides:
  - e2e_export_helpers.py (6 parsing functions + 9 chain-building helpers + 2 constants)
  - test_e2e_ice_interface_export.py (3 test classes, 16 test methods)
  - Bridge validation: real GenIce2 structures → GROMACS writer output
affects:
  - e2e-compute-export-02 (hydrate candidate export tests)
  - e2e-compute-export-03 (custom molecule export tests)
  - e2e-compute-export-04 (solute export tests)
  - e2e-compute-export-05 (ion export tests)
tech-stack:
  added: []
  patterns: [shared-test-helpers-module, sys.path-insert-for-test-imports, alpha-char-filter-for-gro-parsing]
key-files:
  created:
    - tests/e2e_export_helpers.py
    - tests/test_e2e_ice_interface_export.py
  modified: []
key-decisions:
  - decision: "write_top_file uses inline [moleculetype] not #include directives"
    rationale: "write_top_file writes the full SOL molecule definition inline; only write_interface_top_file and later writers use #include. Test adjusted to match actual behavior."
    context: "Plan assumed #include for ice candidate TOP, but write_top_file predates the #include pattern"
  - decision: "parse_gro_residue_names requires alpha chars in residue name"
    rationale: "Box vector lines (e.g., '1.56457...') have numeric values in columns [5:10] that get misparsed as residue names. Added check: residue names must contain at least one alphabetic character."
    context: "Bug discovered during test execution"
patterns-established:
  - name: e2e_export_helpers module
    description: "Shared parsing and chain-building helpers for all e2e compute-export test files, avoiding conftest.py import unreliability"
  - name: sys.path.insert for test imports
    description: "Test files add their own directory to sys.path to import e2e_export_helpers, since pytest doesn't auto-add tests/ to path"
  - name: GRO residue name alpha filter
    description: "Filter box vector lines by requiring at least one alphabetic character in parsed residue name"
duration: 334
completed: 2026-06-03
---

# Phase e2e-compute-export Plan 01: Shared Helpers + Ice/Interface Export Tests Summary

## One-liner

Shared parsing/chain helpers module + 16 e2e tests validating Ice Candidate, Interface (no guests), and Interface+Hydrate Guest GROMACS exports with real GenIce2 structures

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create shared test helpers module | 3248c0e | tests/e2e_export_helpers.py |
| 2 | Create Ice/Interface single-structure export validation tests | 6c348f9 | tests/test_e2e_ice_interface_export.py, tests/e2e_export_helpers.py |

## Test Results

**16 tests pass** across 3 test classes:

- `TestIceCandidateExport` (6 tests): GRO SOL-only residues, atom count header match, TOP molecules section, inline [moleculetype], ITP existence, atom conservation
- `TestInterfaceExport` (4 tests): GRO SOL-only residues, atom count header match, TOP molecules section, #include tip4p-ice.itp
- `TestInterfaceHydrateExport` (6 tests): SOL before guest residues, atom count header match, TOP molecules+guests, #include hydrate ITP, ITP existence, no SOL/guest interleaving

## Must-Haves Verified

| Truth | Status |
|-------|--------|
| Ice candidate exported via write_gro_file produces valid .gro with only SOL residues | ✓ Verified |
| Interface structure exported produces .gro with SOL before guests | ✓ Verified |
| Interface+hydrate structure exported produces .gro with SOL before CH4 guest residues | ✓ Verified |
| GRO atom count header matches actual atom lines for ice, interface, and hydrate-interface exports | ✓ Verified |
| TOP [molecules] section lists correct molecule type counts for every export level | ✓ Verified |

## Key Findings

1. **write_top_file uses inline definition, NOT #include** — The older ice candidate writer writes [moleculetype], [atoms], [settles], etc. inline in the .top file. Only write_interface_top_file and later writers use `#include "tip4p-ice.itp"`. This is an architectural difference between the original writer and the later multi-molecule writers.

2. **TIP4P-ICE 3→4 expansion confirmed** — Ice candidate with nmolecules=128 produces 512 atoms in .gro file (128*4), confirming the MW virtual site expansion at export time.

3. **CH4_H residue name** — Hydrate guest residue name is "CH4_H" (5 chars, fits GRO 5-char limit), matching ch4_hydrate.itp [moleculetype] definition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed parse_gro_residue_names box vector misdetection**

- **Found during:** Task 2 test execution
- **Issue:** Box vector line at end of .gro file (e.g., "   1.56457   1.47072...") has numeric values in columns [5:10] that get misparsed as residue name "56457"
- **Fix:** Added `any(c.isalpha() for c in res_name)` check — residue names must contain at least one alphabetic character. Box vector lines contain only numbers.
- **Files modified:** tests/e2e_export_helpers.py
- **Commit:** 6c348f9

**2. [Rule 1 - Bug] Adjusted test for write_top_file inline format**

- **Found during:** Task 2 test execution
- **Issue:** Plan assumed write_top_file uses `#include "tip4p-ice.itp"`, but it actually writes the SOL molecule definition inline (no #include directives)
- **Fix:** Changed test_top_includes_tip4p_ice to test_top_has_moleculetype_inline, checking for inline [moleculetype] section instead of #include directives
- **Files modified:** tests/test_e2e_ice_interface_export.py
- **Commit:** 6c348f9

## Decisions Made

| Decision | Rationale | Context |
|----------|-----------|---------|
| sys.path.insert for e2e_export_helpers import | pytest doesn't auto-add tests/ to sys.path; conftest import is unreliable | All bridge test files will use this pattern |
| Alpha-char filter for GRO residue parsing | Box vector lines have numeric-only content in [5:10] columns | Prevents false positive residue names from box vectors |
| write_top_file inline vs #include distinction | write_top_file writes full definition inline; later writers use #include | Test reflects actual writer behavior |

## Next Phase Readiness

- ✓ All parsing helpers available for subsequent plans (02-05)
- ✓ Chain-building helpers ready for custom/solute/ion export tests
- ✓ sys.path.insert pattern established for future test files
- ⚠ Future plans should account for write_top_file vs write_interface_top_file format difference
