---
status: verifying
trigger: "Missing ch4_hydrate.itp export in GUI ion tab"
created: 2026-06-16T00:00:00Z
updated: 2026-06-16T00:03:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: All 936 tests pass, including new regression tests for guest_nmolecules=0 scenario
expecting: ch4_hydrate.itp is now correctly copied even when guest_nmolecules=0
next_action: Verify the complete fix is correct and consistent

## Symptoms

expected: ch4_hydrate.itp should be copied to the export directory alongside tip4p-ice.itp, ion.itp, ch4_liquid.itp, etoh.itp
actual: ch4_hydrate.itp is missing from the export directory; only ch4_liquid.itp, etoh.itp, ion.itp, tip4p-ice.itp are present
errors: grompp fails with "ch4_hydrate.itp not found" when processing the #include directive
reproduction: GUI workflow: CH4 hydrate → Interface → Custom (random, by concentration) → Solute (CH4) → Ion → Export GROMACS. Also check CLI pipeline.
started: Always been present — the guest ITP copy logic in IonGROMACSExporter fails when guest_nmolecules > 0 on the IonStructure but the detection/guest copy conditions don't match

## Eliminated

## Evidence

- timestamp: 2026-06-16T00:00:30
  checked: CustomMoleculeStructure fields via Python introspection
  found: CustomMoleculeStructure has NO guest_nmolecules field (only guest_atom_count)
  implication: getattr(custom_structure, 'guest_nmolecules', 0) returns 0, breaking downstream propagation

- timestamp: 2026-06-16T00:00:45
  checked: solute_inserter._remove_overlapping_water() lines 596-618
  found: Creates new InterfaceStructure with guest_nmolecules=getattr(structure, 'guest_nmolecules', 0) which returns 0 for CustomMoleculeStructure
  implication: SoluteStructure.interface_structure gets guest_nmolecules=0

- timestamp: 2026-06-16T00:00:55
  checked: ion_inserter.replace_water_with_ions() lines 472-474
  found: guest_nmolecules = getattr(structure, 'guest_nmolecules', 0) — propagated 0 from interface
  implication: IonStructure.guest_nmolecules == 0 while IonStructure.guest_atom_count > 0

- timestamp: 2026-06-16T00:01:00
  checked: IonGROMACSExporter.export_ion_gromacs() line 340
  found: Condition is `ion_structure.guest_nmolecules > 0 and ion_structure.guest_atom_count > 0` — fails because guest_nmolecules==0
  implication: Guest ITP copy block never executes, even though molecule_index has guest entries and .top file correctly includes ch4_hydrate.itp

- timestamp: 2026-06-16T00:01:05
  checked: write_ion_top_file() lines 1704-1722
  found: Uses guest_count = sum(1 for m in molecule_index if mol_type == "guest") — works correctly
  implication: .top file correctly writes #include "ch4_hydrate.itp" but GUI exporter doesn't copy the file

- timestamp: 2026-06-16T00:01:10
  checked: CLI copy_itp_files_for_structure() ion step lines 395-401
  found: Only checks guest_atom_count > 0 (not guest_nmolecules) — CLI path works correctly
  implication: Bug is GUI-specific due to the different gate condition

- timestamp: 2026-06-16T00:02:00
  checked: _detect_guest_type_from_structure() helper function test
  found: Correctly detects 'ch4' from molecule_index even when guest_nmolecules=0
  implication: Helper function works for both normal and bug conditions

- timestamp: 2026-06-16T00:02:30
  checked: _resolve_guest_nmolecules() helper function test
  found: Correctly resolves guest_nmolecules=1 from interface_structure fallback when CustomMoleculeStructure has guest_nmolecules=0
  implication: SoluteInserter correctly preserves guest_nmolecules through the chain

- timestamp: 2026-06-16T00:03:00
  checked: Full test suite (936 tests)
  found: All 936 tests pass with 0 failures
  implication: Fix is non-breaking and verified

## Resolution

root_cause: CustomMoleculeStructure lacked guest_nmolecules field. When GUI workflow chain hydrate→interface→custom→solute→ion passes a CustomMoleculeStructure to solute_inserter._remove_overlapping_water(), getattr(structure, 'guest_nmolecules', 0) returns 0. This zero propagates through InterfaceStructure→IonStructure, causing IonGROMACSExporter's gate condition (guest_nmolecules > 0 AND guest_atom_count > 0) to fail, skipping the guest ITP copy. Meanwhile write_ion_top_file() uses molecule_index-based detection which correctly finds guest entries.
fix: (1) Added guest_nmolecules field to CustomMoleculeStructure dataclass, set from modified_structure in custom_molecule_inserter place_random/place_custom. (2) Created _detect_guest_type_from_structure() helper in export.py that uses molecule_index-based detection as primary method (consistent with write_ion_top_file), with heuristic fallback. All 4 GUI exporters now use this helper. (3) Added _resolve_guest_nmolecules() static method to SoluteInserter with fallback to interface_structure and molecule_index. (4) Added regression tests for the guest_nmolecules=0 scenario.
verification: All 936 tests pass. New regression tests verify ch4_hydrate.itp is copied when guest_nmolecules=0 but molecule_index has guest entries.
files_changed: [quickice/structure_generation/types.py, quickice/structure_generation/custom_molecule_inserter.py, quickice/structure_generation/solute_inserter.py, quickice/gui/export.py, tests/test_output/test_gromacs_export_ion.py, tests/test_output/test_gromacs_export_solute.py]
