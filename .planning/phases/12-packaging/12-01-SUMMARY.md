---
phase: 12-packaging
plan: 01
subsystem: packaging
tags: [pyinstaller, licenses, github-actions, windows, distribution]

# Dependency graph
requires:
  - phase: 13-documentation
    provides: Complete documentation (README.md, docs/gui-guide.md) for packaging
provides:
  - PyInstaller dependency verified in requirements-dev.txt
  - Complete license compliance files for all bundled dependencies
  - Windows build workflow for user-controlled executable creation
affects: [12-02 (Linux build), future releases]

# Tech tracking
tech-stack:
  added: [pyinstaller>=6.0 (dev dependency)]
  patterns: [license compliance for LGPL-3.0 bundled Qt]

key-files:
  created: [licenses/LGPL-3.0.txt, licenses/BSD-3-Clause.txt, licenses/PSF-2.0.txt, licenses/MIT.txt, .github/workflows/build-windows.yml]
  modified: []

key-decisions:
  - "PyInstaller as dev-only dependency (not in environment.yml)"
  - "License files from SPDX repository for plain text format"
  - "Windows workflow with manual trigger (not auto-executed)"

patterns-established:
  - "License compliance: Collect all bundled dependency licenses before distribution"

# Metrics
duration: 2 min
completed: 2026-04-03
---

# Phase 12 Plan 01: Packaging Infrastructure Summary

**PyInstaller dev dependency verified, LGPL-3.0/BSD-3-Clause/PSF-2.0/MIT licenses collected, Windows GitHub Actions workflow created for user-controlled builds**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T15:31:39Z
- **Completed:** 2026-04-03T15:33:40Z
- **Tasks:** 3 (1 verification, 2 file creation)
- **Files modified:** 5 created

## Accomplishments

- PyInstaller `>=6.0` confirmed as dev dependency in requirements-dev.txt
- Complete license compliance: LGPL-3.0 (Qt), BSD-3-Clause (VTK/NumPy/SciPy), PSF-2.0 (Matplotlib), MIT (GenIce2)
- Windows build workflow with manual trigger, conda environment setup, PyInstaller build, license/doc bundling

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify PyInstaller in dev dependencies** - Verification only (no files modified)
2. **Task 2: Collect bundled dependency license files** - `a4992ae` (feat)
3. **Task 3: Create Windows build GitHub Actions workflow** - `9dc151e` (feat)

**Plan metadata:** (pending)

_Note: Task 1 was verification only - PyInstaller already present in requirements-dev.txt_

## Files Created/Modified

- `licenses/LGPL-3.0.txt` - LGPL-3.0 license for PySide6/Qt (165 lines, critical for distribution)
- `licenses/BSD-3-Clause.txt` - BSD-3-Clause license for VTK, NumPy, SciPy (11 lines)
- `licenses/PSF-2.0.txt` - PSF-2.0 license for Matplotlib (47 lines)
- `licenses/MIT.txt` - MIT license for GenIce2 (21 lines)
- `.github/workflows/build-windows.yml` - Windows build automation workflow (56 lines)

## Decisions Made

- **PyInstaller positioning**: Kept as dev-only dependency (requirements-dev.txt, not environment.yml) - users building executable install dev dependencies separately
- **License sources**: Used SPDX repository for plain text format (opensource.org URLs returned HTML)
- **Workflow trigger**: Manual workflow_dispatch (user explicitly runs when needed, not auto-triggered)
- **Build mode**: PyInstaller `--onedir` (not `--onefile`) for faster startup and easier debugging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**License download format issue:**
- opensource.org URLs returned HTML pages instead of plain text
- **Resolution**: Used SPDX GitHub repository (raw.githubusercontent.com) for plain text license files
- Successfully downloaded all four license files with valid content

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Packaging infrastructure ready for Task 2 (Linux executable build)
- All license files collected and verified
- Windows workflow provided for users (not executed in this phase)
- Ready for 12-02-PLAN.md (Build Linux executable and assemble distribution tarball)

---
*Phase: 12-packaging*
*Plan: 01*
*Completed: 2026-04-03*