---
phase: 12-packaging
plan: 02
subsystem: packaging
tags: [pyinstaller, executable, tarball, distribution, bundling]

# Dependency graph
requires:
  - phase: 12-01
    provides: PyInstaller dev dependency, license files, pinned versions
provides:
  - Standalone Linux executable (29MB)
  - Bundled libraries (5,045 files in _internal/)
  - Distribution tarball (286MB)
affects: [release, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns: [onedir-bundling, collect-all-hook]

key-files:
  created:
    - quickice-v2.0.0-linux-x86_64.tar.gz
  modified:
    - quickice-gui.spec (build-time, gitignored)

key-decisions:
  - "Use PyInstaller --onedir for faster startup and easier debugging"
  - "Use collect_all() hook for comprehensive package bundling"
  - "Include all license files in tarball for compliance"

patterns-established:
  - "Pattern: Use collect_all() for packages with data files (iapws, matplotlib, genice2)"
  - "Pattern: Bundle all dependency licenses with distribution tarball"

# Metrics
duration: 5 min
completed: 2026-04-04
---

# Phase 12 Plan 02: Build Linux Executable Summary

**Linux standalone executable built with PyInstaller, packaged into distribution tarball with documentation and licenses**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-03T20:31:11Z
- **Completed:** 2026-04-03T20:36:19Z
- **Tasks:** 4 (3 from previous session + 1 continuation)
- **Files modified:** 1 (tarball created)

## Accomplishments

- Fixed PyInstaller spec file to use collect_all() for comprehensive package bundling
- Built Linux executable with all dependencies bundled (29MB executable + 5,045 library files)
- Verified GUI launches successfully with 3D viewer functional
- Assembled distribution tarball (286MB) with executable, docs, and license compliance files

## Task Commits

Each task was committed atomically:

1. **Task 1: Activate conda environment** - No commit (verification step, user confirmed)
2. **Task 2: Build Linux executable** - `4359427` (feat: build/assemble scripts)
   - Spec file fix applied during build (quickice-gui.spec - gitignored)
3. **Task 3: Verify executable launch** - No commit (verification step, user confirmed)
4. **Task 4: Assemble distribution tarball** - `c2feb94` (feat: distribution tarball)

**Plan metadata:** (docs: complete plan)

## Files Created/Modified

- `quickice-v2.0.0-linux-x86_64.tar.gz` - Distribution tarball (286MB)
- `quickice-gui.spec` - PyInstaller spec with collect_all() hooks (gitignored)
- `dist/quickice-gui/quickice-gui` - Built executable (gitignored)
- `dist/quickice-gui/_internal/` - Bundled libraries (gitignored)

## Decisions Made

- Used `collect_all()` hook pattern for packages with data files (iapws, matplotlib, genice2)
- Selected `--onedir` mode for faster startup vs `--onefile` single binary
- Included all license files (MIT, LGPL-3.0, BSD-3-Clause, PSF-2.0) in tarball

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing library bundling in PyInstaller build**

- **Found during:** Task 2 (Build Linux executable)
- **Issue:** Initial spec file had empty `datas=[]` and `hiddenimports=[]`, causing FileNotFoundError for iapws/VERSION and missing GenIce2 plugins
- **Fix:** Updated `quickice-gui.spec` to use `collect_all()` for iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib
- **Files modified:** quickice-gui.spec
- **Verification:** Executable launches without errors, 3D viewer functional
- **Committed in:** 4359427

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix essential for correct executable build. No scope creep.

## Issues Encountered

- Build artifacts are gitignored by design (large binary files)
- Spec file is gitignored (regenerated on each build)

## User Setup Required

None - standalone executable runs without Python installation.

## Next Phase Readiness

- Linux executable tarball ready for distribution
- Windows build can be triggered via GitHub Actions workflow
- Release v2.0.0 ready to proceed

---
*Phase: 12-packaging*
*Completed: 2026-04-04*
