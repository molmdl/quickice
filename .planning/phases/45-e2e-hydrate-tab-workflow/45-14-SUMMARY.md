---
phase: 45-e2e-hydrate-tab-workflow
plan: 14
subsystem: testing
tags: [grompp, filled-ice, c2te, ice1hte, hydrate-export, gui, single-cage-key, parse_guest]

# Dependency graph
requires:
  - phase: 39-02
    provides: Filled-ice single-cage-key path (parse_guest for guest placement; single-entry cage_type_map prevents double-placement)
  - phase: 42-05
    provides: GUI HydrateGROMACSExporter.export_hydrate with write_multi_molecule_* writers + MoleculetypeRegistry
  - phase: 45-13
    provides: Mixed built-in (CH4+THF) 2-cage-type lattice GUI hydrate export grompp test pattern (template for this test)
provides:
  - E2E proof that filled-ice lattices (c2te, ice1hte) with single cage_type_map key produce grompp-valid GUI hydrate export
  - Structural test verifying the single-cage-key ("small") constraint for filled ices
  - Empirically verified per-lattice minimum supercell sizes for grompp (c2te=3x3x3, ice1hte=4x4x4)
affects: [47-05, 48, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-lattice supercell sizing for grompp box-size rule (c2te 3x3x3, ice1hte 4x4x4 — 2x2x2 fails both)"
    - "cage_type_map key distinction: 'small' is the GenIce2 cage ID mapping key; 'guest' is the cages display dict key (different dicts, different keys)"

key-files:
  created:
    - tests/test_e2e_mixed_filled_ice_gui.py
  modified: []

key-decisions:
  - "cage_guest_assignments uses 'small' key (matching cage_type_map), NOT 'guest' (the cages display dict key) — using 'guest' produces 0 guests"
  - "Per-lattice supercell: c2te=3x3x3 (shortest 2.65nm), ice1hte=4x4x4 (shortest 2.76nm) — both > 2.0nm for grompp"
  - "ice1hte 3x3x3 (2.07nm) still fails grompp despite >2.0nm — GROMACS's check is stricter than simple shortest-vector for non-orthogonal cells"

patterns-established:
  - "Filled-ice single-cage-key GUI export test: module-scoped fixture + parametrized GUI exporter + structural cage_type_map test"
  - "Per-lattice supercell dict pattern for mixed supercell requirements across parametrized lattices"

# Metrics
duration: 1 min
completed: 2026-07-11
---

# Phase 45 Plan 14: Filled-Ice Single-Cage-Key GUI Hydrate Export Grompp Summary

**Filled-ice lattices c2te (3x3x3) and ice1hte (4x4x4) with single "small" cage key produce grompp-valid output via GUI HydrateGROMACSExporter.export_hydrate with built-in CH4**

## Performance

- **Duration:** 1 min
- **Started:** 2026-07-11T14:57:36Z
- **Completed:** 2026-07-11T14:59:19Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Proved c2te and ice1hte (filled ices with single cage_type_map key "small" -> "Ne1") produce grompp-valid output through the GUI HydrateGROMACSExporter.export_hydrate with built-in CH4
- Verified the single-cage-key path (Phase 39-02 parse_guest) works through the full GUI export chain (.gro + .top + ch4_hydrate.itp + tip4p-ice.itp + grompp rc=0)
- Added structural test confirming cage_type_map has exactly ONE key ("small") — NOT "small"+"large" like sI/sII, and NOT "guest" (which is the cages display dict key)
- Empirically determined per-lattice minimum supercell sizes for grompp: c2te=3x3x3 (7776 atoms), ice1hte=4x4x4 (6656 atoms)

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Write + verify filled-ice single-cage-key GUI hydrate export grompp test** - `6fa1e33` (test)

## Files Created/Modified
- `tests/test_e2e_mixed_filled_ice_gui.py` - E2E test: module-scoped fixture for c2te+ice1hte (per-lattice supercells), parametrized GUI hydrate export + grompp, structural cage_type_map test

## Decisions Made
- Used "small" as the cage_guest_assignments key (matching cage_type_map), NOT "guest" — the plan incorrectly claimed cage_type_map uses "guest"; empirical testing proved "guest" produces 0 guests while "small" works correctly. The "guest" key exists in the cages DISPLAY dict (human-readable cage name), but cage_type_map (GenIce2 cage ID mapping) uses "small".
- Used per-lattice supercell sizes (c2te=3x3x3, ice1hte=4x4x4) instead of the plan's suggested 2x2x2 — empirical testing showed 2x2x2 fails grompp for BOTH lattices (c2te 2x2x2=1.76nm, ice1hte 2x2x2=1.38nm, both <2.0nm). ice1hte even fails at 3x3x3 (2.07nm) due to GROMACS's stricter non-orthogonal cell check.
- Structural test asserts "small" in cage_type_map (NOT "guest") and "guest" in cages (the display dict) — reflecting the actual two-dict structure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's cage_type_map key claim was factually wrong**
- **Found during:** Task 1 (empirical verification before writing test)
- **Issue:** Plan stated `cage_type_map = {"guest": "Ne1"}` for c2te/ice1hte and instructed to use "guest" as the cage_guest_assignments key. Actual code has `cage_type_map = {"small": "Ne1"}`. Using "guest" produces 0 guests (warning: "cage_key 'guest' not in cage_type_map for c2te; skipping"). The plan conflated two different dicts: `cages` (display info, uses "guest" key) and `cage_type_map` (GenIce2 cage ID mapping, uses "small" key).
- **Fix:** Used "small" as the cage_guest_assignments key (matching cage_type_map). Structural test asserts "small" in cage_type_map and "guest" in cages (the correct dict for each key). Test file documents this distinction clearly.
- **Files modified:** tests/test_e2e_mixed_filled_ice_gui.py (test only, no source changes)
- **Verification:** c2te with "small" key -> guest_count=864 (3x3x3); c2te with "guest" key -> guest_count=0. grompp rc=0 only with "small" key.
- **Committed in:** 6fa1e33

**2. [Rule 3 - Blocking] Plan's suggested 2x2x2 supercell fails grompp for both lattices**
- **Found during:** Task 1 (empirical box-size verification)
- **Issue:** Plan suggested using 2x2x2 supercell if 1x1x1 fails grompp (Pitfall 1). Empirical testing showed 2x2x2 STILL fails for BOTH: c2te 2x2x2 shortest=1.76nm (<2.0nm), ice1hte 2x2x2 shortest=1.38nm (<2.0nm). Even 3x3x3 fails for ice1hte (shortest=2.07nm — GROMACS's check is stricter than simple shortest-vector for non-orthogonal cells).
- **Fix:** Used per-lattice minimum supercells: c2te=3x3x3 (shortest=2.65nm, grompp rc=0), ice1hte=4x4x4 (shortest=2.76nm, grompp rc=0). Defined `_FILLED_ICE_SUPERCELLS` dict mapping lattice -> supercell tuple.
- **Files modified:** tests/test_e2e_mixed_filled_ice_gui.py (test only, no source changes)
- **Verification:** grompp rc=0 for c2te 3x3x3 and ice1hte 4x4x4 (empirically verified before writing test).
- **Committed in:** 6fa1e33

---

**Total deviations:** 2 auto-fixed (1 bug in plan's factual claims, 1 blocking supercell size)
**Impact on plan:** Both auto-fixes necessary for correct test execution. No source code changes (test-only plan). No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Filled-ice single-cage-key GUI hydrate export grompp path now verified for c2te and ice1hte
- Complements 45-13 (2-cage-type lattices sII/16 with CH4+THF mixed)
- Phase 47-05 (filled-ice grompp) gap partially addressed (GUI path for c2te/ice1hte)
- Remaining: CLI hydrate export for filled ices (c0te/c1te at 4x4x4, c2te/ice1hte), and full tab chain through solute/ion/custom tabs

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
