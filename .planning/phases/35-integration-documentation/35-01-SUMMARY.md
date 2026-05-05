---
phase: 35-integration-documentation
plan: 01
subsystem: ui
tags: [keyboard-shortcuts, gromacs-export, molecule-ordering, integration-tests]

# Dependency graph
requires:
  - phase: 34-custom-molecule-upload
    provides: Custom molecule GROMACS export infrastructure
provides:
  - Unified Ctrl+S keyboard shortcut for GROMACS export from active tab
  - Molecule ordering verification tests
  - .itp bundling verification
affects:
  - User workflow for all tabs (Ice, Hydrate, Interface, Solute, Custom, Ion)
  - GROMACS export consistency

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Unified keyboard shortcut pattern (Ctrl+S routes to tab-specific exporter)
    - Molecule ordering verification via .gro file parsing

key-files:
  created:
    - tests/test_gromacs_molecule_ordering.py
  modified:
    - quickice/gui/main_window.py

key-decisions:
  - "Ctrl+S for unified export (Qt standard 'Save' action)"
  - "Hydrate shortcut changed from Ctrl+E to Ctrl+H"
  - "Export As... submenu for tab-specific exports"
  - "Mock data for molecule ordering tests (no real GenIce calls)"

patterns-established:
  - "Pattern 1: Unified keyboard shortcut routing via currentIndex() switch"
  - "Pattern 2: GROMACS molecule ordering verification via .gro file parsing"

# Metrics
duration: 40min
completed: 2026-05-05
---

# Phase 35 Plan 01: Unified Export & Molecule Ordering Summary

**Unified Ctrl+S keyboard shortcut for GROMACS export across all tabs, with molecule ordering verification tests ensuring scientific correctness**

## Performance

- **Duration:** 40 min
- **Started:** 2026-05-05T09:29:00Z
- **Completed:** 2026-05-05T10:09:39Z
- **Tasks:** 2 (auto tasks), 1 checkpoint
- **Files modified:** 2 (main_window.py, test_gromacs_molecule_ordering.py)

## Accomplishments
- Implemented unified Ctrl+S shortcut that exports from currently active tab
- Changed Hydrate export shortcut from Ctrl+E to Ctrl+H (more intuitive)
- Added "Export As..." submenu with all tab-specific exports for discoverability
- Created comprehensive molecule ordering tests (4 passing tests)
- Verified .itp file bundling in GROMACS exports

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement unified export shortcut** - `bee6132` (feat)
   - Added _on_export_current_tab() method
   - Updated Ctrl+S from Save PDB to Export GROMACS
   - Changed Hydrate shortcut to Ctrl+H
   - Created Export As... submenu

2. **Task 2: Create molecule ordering tests** - `07ac480` (test)
   - test_solute_molecule_ordering: SOL → CH4 ordering
   - test_custom_molecule_ordering: SOL → custom molecules ordering
   - test_combined_ordering: SOL → CH4 → custom molecules ordering
   - test_itp_bundling: .itp file verification

**Plan metadata:** To be committed (docs: complete plan)

## Files Created/Modified
- `quickice/gui/main_window.py` - Unified Ctrl+S export shortcut, hydrate Ctrl+H shortcut, Export As... submenu
- `tests/test_gromacs_molecule_ordering.py` - 4 tests verifying GROMACS export molecule ordering

## Decisions Made

1. **Ctrl+S for unified export** - Qt standard "Save" action, reduces cognitive load
2. **Hydrate shortcut Ctrl+H** - More intuitive than Ctrl+E (H for hydrate)
3. **Export As... submenu** - Keeps tab-specific shortcuts for users who prefer explicit association
4. **Mock data for tests** - Faster test execution without real GenIce calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

User noted during checkpoint approval:
- Found a missing function (details to be investigated in follow-up)
- Documentation may need redo
- User asked whether to add a phase before this and replan

**Recommendation:** These issues should be investigated before proceeding with documentation-heavy phases (35-02 to 35-06). Consider a quick fix phase if the missing function is critical.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ✓ Unified export shortcut implemented and verified
- ✓ Molecule ordering tests passing
- ✓ .itp bundling verified
- ⚠️ User identified potential issues (missing function, documentation concerns)
- ⚠️ Consider addressing user's concerns before proceeding to documentation phases

**Recommendation:** User should determine if missing function issue requires a dedicated fix phase before continuing with Phase 35 documentation work.

---
*Phase: 35-integration-documentation*
*Completed: 2026-05-05*
