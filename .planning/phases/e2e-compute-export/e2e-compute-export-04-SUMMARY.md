---
phase: e2e-compute-export
plan: 04
subsystem: export-bridge-testing
tags: [gromacs, e2e, export, chain, ion, solute, custom, hydrate, guest, moleculetype-registry, bug-I5-workaround, CH4-coexistence, THF-coexistence]
requires:
  - e2e-compute-export-01 (shared helpers + ice/interface export tests)
  - e2e-compute-export-02 (custom + solute export tests + gromacs_writer bugfixes)
  - e2e-compute-export-03 (ion export tests + ITP baseline + IonInserter fix)
provides:
  - test_e2e_chain_export_1.py (4 test classes, 26 test methods)
  - CustomMoleculeInserter guest molecule_index build fix
  - Bridge validation: F1-F4 full chain → GROMACS writer output
affects:
  - e2e-compute-export-05 (simple chain + cross-chain invariant tests F5-F7)
tech-stack:
  added: []
  patterns: [guest-molecule-index-build-when-empty, hydrate-guest-registration-before-solute-insertion, CH4_H-CH4_L-coexistence-assertion, guest_atom_count-as-guest-preservation-indicator]
key-files:
  created:
    - tests/test_e2e_chain_export_1.py
  modified:
    - quickice/structure_generation/custom_molecule_inserter.py
key-decisions:
  - decision: "Build guest MoleculeIndex entries when source molecule_index is empty but guest_atom_count > 0"
    rationale: "Freshly generated interfaces have empty molecule_index. CustomMoleculeInserter tried to copy guest entries from source molecule_index, found none, and silently omitted guests from the output. This caused THF_H and CH4_H guest molecules to be absent from downstream GROMACS exports."
    context: "Rule 1 deviation — bug exposed by F4 chain test"
  - decision: "Custom molecule residue name is MOL (not ETOH) in all chain tests"
    rationale: "Plan specified ETOH in some must-haves but actual residue name is MOL (from moleculetype_name in registry). Follows established pattern from Plans 02+03."
    context: "Consistent with accumulated decisions in STATE.md"
  - decision: "Use guest_atom_count > 0 for F4 guest preservation instead of guest_nmolecules"
    rationale: "After passing through CustomMoleculeStructure, guest_nmolecules may be 0 (field doesn't exist on CustomMoleculeStructure). guest_atom_count IS preserved."
    context: "Known limitation documented in plan and STATE.md"
  - decision: "Register hydrate guest before insert_solutes in F3/F4 chains"
    rationale: "SoluteInserter creates its own MoleculetypeRegistry. The hydrate guest must be registered in that registry for correct CH4_H/THF_H naming. Without this, the guest would get a generic name instead of the hydrate-specific name."
    context: "Matches real GUI workflow where hydrate tab registers guests first"
duration: 598
completed: 2026-06-03
---

# Phase e2e-compute-export Plan 04: Full Chain Export Tests F1-F4 Summary

## One-liner

26 e2e bridge tests validating full multi-step chain exports (F1-F4) with CH4_H/CH4_L and THF_H/THF_L coexistence, plus CustomMoleculeInserter guest molecule_index build bugfix

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create full chain export tests F1-F4 | 82f010c | tests/test_e2e_chain_export_1.py |
| 1 | Fix guest molecule_index build in CustomMoleculeInserter | b77e0fc | quickice/structure_generation/custom_molecule_inserter.py |

## Test Results

**26 tests pass** across 4 test classes:

- `TestChainF1` (7 tests): Interface→Custom→Solute→Ion chain. SOL→MOL→CH4_L→NA→CL ordering, atom count header match, TOP molecules (SOL, MOL, CH4_L, NA, CL), TOP #includes (tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp), ITP validity, custom+solute preservation, atom conservation
- `TestChainF2` (4 tests): Interface→Custom→Ion chain. SOL→MOL→NA→CL ordering, atom count header match, TOP molecules, TOP #includes (tip4p-ice.itp, etoh.itp, ion.itp — no solute ITP), no solute attributes
- `TestChainF3` (7 tests): Hydrate→Interface→Solute→Ion chain. SOL→CH4_H→CH4_L→NA→CL P0 coexistence ordering, atom count header match, TOP molecules (SOL, CH4_H/CH4, CH4_L, NA, CL), TOP #includes (tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp), ITP validity, guest_nmolecules > 0, registry distinguishes CH4_H != CH4_L
- `TestChainF4` (8 tests): Hydrate→Interface→Custom→Solute→Ion chain. SOL→THF_H→MOL→THF_L→NA→CL 6-molecule-type ordering, atom count header match, TOP molecules (SOL, THF_H/THF, MOL, THF_L, NA, CL), TOP #includes (tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp), ITP validity, guest_atom_count > 0 (known limitation), registry distinguishes THF_H != THF_L

## Must-Haves Verified

| Truth | Status |
|-------|--------|
| F1 chain export produces .gro with SOL→MOL→CH4_L→NA→CL ordering | ✓ Verified (plan said ETOH, actual is MOL) |
| F2 chain export produces .gro with SOL→MOL→NA→CL ordering | ✓ Verified (plan said ETOH, actual is MOL) |
| F3 chain export produces .gro with SOL→CH4_H→CH4_L→NA→CL ordering | ✓ Verified — P0 CH4 coexistence test |
| F4 chain export produces .gro with guest→custom→solute→NA→CL ordering | ✓ Verified (THF_H→MOL→THF_L→NA→CL) |
| All chain exports produce .top [molecules] sections listing every molecule type | ✓ Verified — all 4 chains have correct molecule entries |

## Key Findings

1. **CustomMoleculeInserter drops guest molecule_index entries** — When the source interface has `guest_atom_count > 0` but empty `molecule_index` (normal for freshly generated interfaces), the CustomMoleculeInserter's code at lines 682-688 tries to copy guest entries from `structure.molecule_index` but finds none. The guest atoms remain in positions/atom_names but are invisible to downstream GROMACS writers. Fixed by building guest MoleculeIndex entries from `guest_nmolecules` and `guest_atom_count` when no entries are found in the source.

2. **CH4_H/CH4_L coexistence validated (P0)** — The F3 chain (Hydrate→Interface→Solute→Ion) produces GRO files with both CH4_H (hydrate cage guest) and CH4_L (liquid-phase solute) residues, confirming the core MoleculetypeRegistry distinction works correctly through the full pipeline.

3. **THF_H/THF_L coexistence validated** — The F4 chain (Hydrate→Interface→Custom→Solute→Ion) produces GRO files with both THF_H and THF_L, but only when the guest molecule_index build fix is applied. Without the fix, THF_H was completely absent from the output.

4. **BUG I5 workaround confirmed for multi-step chains** — F1, F3, and F4 all use `_insert_ions_from_solute()` which applies the `_solute_to_ion_source()` workaround. The workaround correctly propagates solute attributes and custom molecule attributes through the chain.

5. **F2 (Custom→Ion) needs no BUG I5 workaround** — Since F2 goes directly from custom to ion (bypassing solutes), it uses `_insert_ions()` directly without the workaround.

6. **guest_nmolecules vs guest_atom_count in F4** — After passing through CustomMoleculeStructure, `guest_nmolecules` may be 0 (the field doesn't exist on CustomMoleculeStructure). However, `guest_atom_count` IS preserved. With the molecule_index fix, guest molecules now correctly appear in the output regardless of which count field is 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed guest molecule_index build in CustomMoleculeInserter**

- **Found during:** Task 1 test execution (TestChainF4)
- **Issue:** CustomMoleculeInserter tried to copy guest entries from `structure.molecule_index` but freshly generated interfaces have empty molecule_index. Guest atoms (THF_H, CH4_H) were present in positions but absent from molecule_index, making them invisible to GROMACS writers.
- **Fix:** Added fallback in all 3 locations (place_random, place_custom, _remove_overlapping_water): when `guest_atom_count > 0` but no "guest" entries found in source molecule_index, build guest MoleculeIndex entries from `guest_nmolecules` and `guest_atom_count` counts.
- **Files modified:** quickice/structure_generation/custom_molecule_inserter.py (3 locations)
- **Commit:** b77e0fc

**2. [Rule 1 - Bug] Corrected ETOH → MOL residue name in test assertions**

- **Found during:** Task 1 test creation
- **Issue:** Plan's must_haves specified "ETOH" as the custom molecule residue name, but actual residue name is "MOL" (from moleculetype_name in registry, not the ITP file's moleculetype name).
- **Fix:** Used "MOL" in all test assertions consistent with established pattern from Plans 02+03.
- **Files modified:** tests/test_e2e_chain_export_1.py
- **Commit:** 82f010c

## Decisions Made

| Decision | Rationale | Context |
|----------|-----------|---------|
| Build guest MoleculeIndex when source is empty | Freshly generated interfaces have empty molecule_index; guests must be reconstructed from counts | Rule 1 deviation — bug fix |
| MOL residue name (not ETOH) | moleculetype_name from registry defaults to "MOL" | Consistent with Plans 02+03 |
| guest_atom_count > 0 for F4 | guest_nmolecules may be 0 after CustomMoleculeStructure | Known limitation, documented |
| Register hydrate guest before insert_solutes | SoluteInserter creates its own registry; hydrate guest must be in it | Matches real GUI workflow |

## Next Phase Readiness

- ✓ F1-F4 full chain exports validated with real GenIce2 data
- ✓ CH4_H/CH4_L coexistence validated (P0 test in F3)
- ✓ THF_H/THF_L coexistence validated (F4, after bugfix)
- ✓ Guest molecule_index build bug fixed in CustomMoleculeInserter
- ✓ 26 new bridge tests, 57 existing tests all pass (no regression)
- ✓ Plan 05 (F5-F7 + cross-chain invariants) already complete
- ⚠ e2e-compute-export phase is now COMPLETE (all 5 plans done)
