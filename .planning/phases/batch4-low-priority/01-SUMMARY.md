---
phase: batch4-low-priority
plan: 01
subsystem: code-quality
tags: [bugfix, thf, logging, imports, citations, thread-safety, iapws, gromacs]
requires: [batch3-medium]
provides: [17-low-priority-fixes]
affects: []
tech-stack:
  added: []
  patterns: [lru_cache, threading.Lock, double-check-locking]
key-files:
  created: []
  modified:
    - quickice/structure_generation/types.py
    - quickice/output/gromacs_writer.py
    - quickice/utils/molecule_utils.py
    - quickice/gui/main_window.py
    - quickice/structure_generation/hydrate_generator.py
    - quickice/structure_generation/gromacs_ion_export.py
    - quickice/structure_generation/ion_inserter.py
    - quickice/ranking/scorer.py
    - quickice/ranking/types.py
    - docs/ranking.md
    - quickice/phase_mapping/water_density.py
    - quickice/phase_mapping/ice_ih_density.py
    - quickice/structure_generation/water_filler.py
    - quickice/structure_generation/molecule_validator.py
    - quickice/structure_generation/itp_parser.py
decisions: []
duration: 219
completed: 2026-05-22
---

# Phase Batch 4 Plan 01: LOW Priority Fixes Summary

**One-liner:** Fixed 17 LOW priority issues: THF atom count (12→13), debug logging levels, dead imports, scientific citations, thread-safe caching, BOM handling.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix THF atom counts and formula comments (Issues 21, 22, 23) | f217c6d | types.py, gromacs_writer.py, molecule_utils.py |
| 2 | Fix debug logging, dead imports, and scientific metadata (Issues 24-31) | 95a6b8c | main_window.py, gromacs_writer.py, hydrate_generator.py, gromacs_ion_export.py, ion_inserter.py, scorer.py, types.py, ranking.md |
| 3 | Fix warnings, thread safety, and fragile code (Issues 32-37) | 9fa898f | water_density.py, ice_ih_density.py, water_filler.py, hydrate_generator.py, molecule_validator.py, itp_parser.py |

## Changes by Issue

### Issues 21, 22, 23: THF atom count and formula
- THF = C4H8O = 4C + 8H + 1O = 13 atoms (was incorrectly 12 or C5H8O=14)
- Fixed 4 occurrences in types.py, 1 in gromacs_writer.py, 1 in molecule_utils.py

### Issue 24: Debug logging at INFO level
- Changed 10 `logger.info("[Water Count Debug]")` calls to `logger.debug()` in main_window.py
- Left 2 `logger.warning()` calls unchanged (legitimate warnings)

### Issue 25: Dead import MOLECULE_TYPE_INFO in gromacs_writer.py
- Removed unused MOLECULE_TYPE_INFO from import line

### Issue 26: Dead import MOLECULE_TYPE_INFO in hydrate_generator.py
- Removed MOLECULE_TYPE_INFO from multi-line import block

### Issue 27: Missing Madrid2019_085 header in ion.itp
- Added `; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)` header before `[ moleculetype ]`

### Issue 28: Ion parameters source comment
- Added `# Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)` before Physical constants section
- Updated AVOGADRO comment to include `(CODATA 2017)`

### Issue 29: AVOGADRO constant inconsistency
- Changed `6.022e23` → `6.02214076e23` in scorer.py to match CODATA 2017 and ion_inserter.py

### Issue 30: Missing citations in ranking/types.py
- Added `Petrenko & Whitworth, 1999, Physics of Ice` citation to ideal_oo_distance
- Changed `cutoff for H-bond detection` → `cutoff for O-O neighbor detection (common PBC cutoff)`

### Issue 31: Missing citation in docs/ranking.md
- Changed `typical hydrogen bond length` → `Petrenko & Whitworth, 1999, Physics of Ice`

### Issue 32: Suppressed IAPWS extrapolation warnings
- Added `logger.debug()` call after IAPWS95 calculation to log when extrapolated values are used

### Issue 33: Fallback density warning improvement
- Changed ice_ih_density.py fallback warning to include actual conditions (273.15K, 0.1MPa) and "approximate" note

### Issue 34: Water template cache thread safety
- Replaced module-level `_water_template_cache` variable with `@lru_cache(maxsize=1)` decorator
- Removed `global` statement, early-return cache check, and manual cache assignment
- Updated docstring to mention @lru_cache

### Issue 35: GenIce2 thread safety
- Added `import threading` and `_genice_lock = threading.Lock()`
- Refactored `_ensure_genice_import()` with double-check locking pattern
- Removed `global _genice_lib, _gromacs_format, _lattice_modules_loaded` statement

### Issue 36: Expand GENERIC_RESIDUE_NAMES
- Added 6 PDB generic names: DRG, API, HET, UNL, LIG1, MOL1

### Issue 37: ITP parser BOM and line ending normalization
- Added BOM stripping (`content.lstrip('\ufeff')`)
- Added line ending normalization (`\r\n` → `\n`, `\r` → `\n`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ITP parser indentation error**

- **Found during:** Task 3 verification
- **Issue:** BOM/line-ending normalization code was inserted with wrong indentation (8 spaces instead of 4)
- **Fix:** Corrected indentation to match surrounding function body
- **Files modified:** quickice/structure_generation/itp_parser.py
- **Commit:** 9fa898f (fixed inline before commit)

## Verification Results

- All 14 modified files pass `ast.parse()` syntax check
- `import quickice` succeeds without errors
- No references to THF having 12 atoms or formula C5H8O remain
- No `logger.info("[Water Count Debug]")` calls remain
- No `MOLECULE_TYPE_INFO` references in gromacs_writer.py or hydrate_generator.py
- Madrid2019_085 header present in both gromacs_ion_export.py and ion_inserter.py
- AVOGADRO = 6.02214076e23 in scorer.py
- Petrenko citations in ranking/types.py and docs/ranking.md
- lru_cache on load_water_template(), no _water_template_cache references
- threading.Lock in hydrate_generator.py
- GENERIC_RESIDUE_NAMES includes all 11 names
- BOM stripping and line ending normalization in itp_parser.py
- Test suite: 412 passed, 4 failed (pre-existing failures), 2 skipped
