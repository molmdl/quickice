---
phase: e2e-compute-export
plan: 02
subsystem: testing
tags: [gromacs, export, gro, top, itp, custom-molecule, solute, e2e, bridge-test, real-data]

# Dependency graph
requires:
  - phase: e2e-compute-export-01
    provides: e2e_export_helpers.py (parsing + chain-building), conftest.py fixtures, test pattern
provides:
  - Custom molecule single-structure export bridge tests (7 tests)
  - Solute single-structure export bridge tests (14 tests across 2 scenarios)
  - Bugfix: write_custom_molecule_gro_file ice 3→4 atom expansion
  - Bugfix: write_solute_gro_file empty molecule_index fallback
  - Bugfix: write_solute_top_file empty molecule_index fallback
affects: [e2e-compute-export-03, e2e-compute-export-04, e2e-compute-export-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - molecule_index fallback: use ice_nmolecules/water_nmolecules when molecule_index is empty
    - SOL atom count from molecule_index: sum(4 if ice else count) for ice+water molecules

key-files:
  created:
    - tests/test_e2e_custom_export.py
    - tests/test_e2e_solute_export.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "Moleculetype_name is MOL (registry default), not ETOH (ITP moleculetype name)"
  - "Compute expected counts from molecule_index when populated, ice_nmolecules/water_nmolecules as fallback"
  - "SoluteInserter properly populates SoluteStructure.registry — no pre-registration needed for CH4"

patterns-established:
  - "GRO atom count = header validation + molecule_index cross-check for SOL atom verification"
  - "Autouse fixtures for structure building to avoid per-test recomputation"

# Metrics
duration: 11min
completed: 2026-06-03
---

# Phase e2e-compute-export Plan 02: Custom & Solute Export Bridge Tests Summary

**21 bridge tests validating custom molecule (SOL→MOL) and solute (SOL→CH4_L, SOL→MOL→CH4_L) export pipelines against real GenIce2 data, with 3 writer bugfixes for empty molecule_index and ice 3→4 expansion**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-03T14:49:17Z
- **Completed:** 2026-06-03T14:59:59Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 7 custom molecule export bridge tests covering GRO residues, atom count, TOP molecules, TOP includes, ITP existence, and atom conservation
- 14 solute export bridge tests (2 scenarios: from Interface, from Custom) covering 3-type residue ordering, molecule propagation, ITP includes
- Fixed 3 bugs in gromacs_writer.py exposed by real GenIce2 data (synthetic test fixtures masked these)
- All 5 must-haves verified: SOL→custom, SOL→solute, SOL→custom→solute, atom count header, TOP molecules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Custom Molecule export bridge tests** - `2e88696` (feat) — includes 3 bugfixes in gromacs_writer.py
2. **Task 2: Create Solute export bridge tests** - `e260f1e` (feat)

## Files Created/Modified
- `tests/test_e2e_custom_export.py` - 7 tests for custom molecule GRO/TOP export validation (SOL→MOL ordering, atom counts, ITP includes)
- `tests/test_e2e_solute_export.py` - 14 tests for solute GRO/TOP export validation (2 scenarios: interface source, custom source)
- `quickice/output/gromacs_writer.py` - Fixed 3 bugs: ice 3→4 expansion in custom writer, empty molecule_index fallback in solute GRO/TOP writers

## Decisions Made
- **moleculetype_name is "MOL" not "ETOH"**: The MoleculetypeRegistry.register_custom_molecule() defaults to "MOL" as the user_name. The plan incorrectly assumed "ETOH" from the ITP file's moleculetype name. Tests match actual registry behavior.
- **Expected count computation from molecule_index**: When molecule_index is populated (solute-from-custom path), ice_nmolecules/water_nmolecules may be unreliable (ice_nmolecules=0 for modified interface). Tests use molecule_index counts when available, nmolecules as fallback.
- **SoluteInserter registry is self-populating**: SoluteInserter calls register_liquid_solute() internally, so no pre-registration is needed. The SoluteStructure.registry correctly resolves "liquid_CH4" → "CH4_L".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed write_custom_molecule_gro_file not expanding ice 3→4 atoms**
- **Found during:** Task 1 (custom molecule export test)
- **Issue:** Writer wrote raw 3-atom ice molecules (O, H, H) instead of TIP4P-ICE 4-atom format (OW, HW1, HW2, MW). Header said 4 atoms per ice molecule but only 3 were written, causing atom count mismatch.
- **Fix:** Added ice 3→4 expansion in write_custom_molecule_gro_file, matching write_interface_gro_file and write_solute_gro_file patterns
- **Files modified:** quickice/output/gromacs_writer.py
- **Verification:** GRO header count matches parsed atom lines; existing test_gromacs_export_custom.py still passes
- **Committed in:** 2e88696 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed write_solute_gro_file failing with empty molecule_index**
- **Found during:** Task 1 (preparing solute tests, discovered via exploration)
- **Issue:** Real GenIce2-generated InterfaceStructures have empty molecule_index. The writer iterated over molecule_index for SOL molecules, resulting in zero SOL atoms written. Only solute atoms appeared in GRO output.
- **Fix:** Added fallback: when molecule_index is empty, build synthetic molecule entries from ice_nmolecules and water_nmolecules counts, mirroring write_interface_gro_file's approach. Also added fallback for guest molecules and atom-by-atom position wrapping.
- **Files modified:** quickice/output/gromacs_writer.py
- **Verification:** Solute-from-interface GRO now contains SOL + CH4_L; all existing tests still pass
- **Committed in:** 2e88696 (Task 1 commit)

**3. [Rule 1 - Bug] Fixed write_solute_top_file failing with empty molecule_index**
- **Found during:** Task 1 (same root cause as Bug 2)
- **Issue:** sol_count computed from empty molecule_index was 0, so TOP [molecules] section had no SOL entry. Guest type detection also failed when molecule_index was empty.
- **Fix:** Added fallback: sol_count = ice_nmolecules + water_nmolecules when molecule_index is empty; guest type detection from atom_names in guest region as fallback
- **Files modified:** quickice/output/gromacs_writer.py
- **Verification:** Solute TOP now has SOL + CH4_L; existing test_gromacs_export_solute.py still passes
- **Committed in:** 2e88696 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All auto-fixes were necessary for correctness. The bugs were masked by synthetic test fixtures with populated molecule_index. Real GenIce2 data exposed them. No scope creep.

## Issues Encountered
- **moleculetype_name discrepancy**: Plan expected "ETOH" but actual code uses "MOL" from MoleculetypeRegistry default. Tests adapted to match actual behavior. This is not a bug — it's how the registry works — but the plan's expectations were wrong.
- **ice_nmolecules=0 in modified interface**: When SoluteInserter removes overlapping water from a CustomMoleculeStructure source, the resulting modified InterfaceStructure reports ice_nmolecules=0 (though ice atoms are present). This appears to be an inconsistency in how SoluteInserter constructs the modified interface. Tests work around it by using molecule_index when available.

## Next Phase Readiness
- Plan 03 (Hydrate candidate export) can proceed using established patterns
- Plan 04 and 05 can leverage the empty molecule_index fallback pattern
- The ice 3→4 expansion fix may need to be checked in write_ion_gro_file (Plan 05)
- Key insight for future plans: always verify atom count = header when testing with real data

---
*Phase: e2e-compute-export*
*Completed: 2026-06-03*
