---
status: resolved
trigger: "solute-interface-missing-custom"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:30:00Z
---

## Current Focus

hypothesis: _remove_overlapping_water() creates InterfaceStructure without custom molecule attributes, and main_window.py extracts custom positions using wrong structure reference
test: Fix _remove_overlapping_water to preserve custom molecule attributes from input structure
expecting: Custom molecule info preserved through the workflow chain
next_action: Modify _remove_overlapping_water to check for and preserve custom molecule attributes

## Symptoms

expected: solute_structure.interface_structure should preserve custom molecules from the input interface
actual: solute_structure.interface_structure is created by solute_inserter._remove_overlapping_water() which only has ice + water (no custom molecules)
errors: No error, but custom molecules lost in data flow
reproduction: Workflow: Interface → Custom → Solute → Ion, then export at Ion tab
started: Unknown - architectural issue in data flow

root_cause_analysis:
  Workflow: Interface → Custom → Solute → Ion
  1. Custom molecules inserted → CustomMoleculeStructure with interface_structure (original interface)
  2. Solute inserted from custom → SoluteStructure with interface_structure from _remove_overlapping_water()
  3. Ion inserted from solute → uses solute_structure.interface_structure (no custom molecules!)
  
  Line 854 in main_window.py: `interface = solute_structure.interface_structure`
  This interface has no custom molecules because SoluteStructure.interface_structure is created fresh by solute_inserter.

  Lines 873-883 try to add custom molecule info to this interface, but the positions/atoms are extracted from `custom_structure.positions` which are from the ORIGINAL interface, not the current structure.

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:01:00Z
  checked: SoluteStructure class definition (types.py lines 424-444)
  found: SoluteStructure has interface_structure attribute that stores InterfaceStructure
  implication: Interface structure is created by solute_inserter and stored in SoluteStructure

- timestamp: 2026-05-09T00:01:30Z
  checked: solute_inserter._remove_overlapping_water() (lines 342-516)
  found: Creates new InterfaceStructure with only ice + water + guest atoms (lines 425-452)
         Does NOT check for or preserve custom molecule attributes from input structure
         Returns InterfaceStructure at line 501-514 with ice_atom_count, water_atom_count, guest_atom_count only
  implication: Custom molecules are completely lost when _remove_overlapping_water processes CustomMoleculeStructure

- timestamp: 2026-05-09T00:02:00Z
  checked: main_window.py lines 873-883
  found: Attempts to extract custom molecule positions using:
         custom_structure.positions[interface.ice_atom_count + interface.water_atom_count + interface.guest_atom_count:]
         This uses interface (NEW structure from _remove_overlapping_water) indices but custom_structure.positions (ORIGINAL structure)
  implication: Wrong reference! The NEW interface has different water_atom_count (some removed), but code extracts from ORIGINAL custom_structure.positions

- timestamp: 2026-05-09T00:10:00Z
  checked: solute_inserter._remove_overlapping_water implementation details
  found: The method treats custom molecules as "guests" when processing CustomMoleculeStructure
         Lines 438-440: guest_positions = structure.positions[ice_atom_count + water_atom_count:]
         This includes custom molecules but doesn't track them separately
         CustomMoleculeStructure has: ice + water + guests + custom molecules
         But guest_atom_count = 0 for custom molecules
  implication: Custom molecules are physically in the positions array but not tracked with separate attributes

- timestamp: 2026-05-09T00:15:00Z
  checked: CustomMoleculeStructure attributes vs InterfaceStructure
  found: CustomMoleculeStructure lacks: water_nmolecules, ice_nmolecules, guest_nmolecules, mode, report
         These are InterfaceStructure-specific attributes
  implication: solute_inserter needs to use getattr() to handle both structure types

- timestamp: 2026-05-09T00:20:00Z
  checked: Test verification (test_custom_solute_fix.py)
  found: When passing CustomMoleculeStructure to solute_inserter:
         - Custom molecules preserved in positions array (216 total atoms: 196 ice+water+guests + 20 custom)
         - All custom molecule attributes preserved (count, positions, atom_names, moleculetype, paths)
         - Test passes all verification checks
  implication: Fix is working correctly when CustomMoleculeStructure is passed to solute_inserter

## Resolution

root_cause: _remove_overlapping_water() in solute_inserter.py creates new InterfaceStructure without preserving custom molecule attributes from input CustomMoleculeStructure. When solutes are inserted from custom molecules, main_window.py passed custom_structure.interface_structure (ice + water only) instead of the full CustomMoleculeStructure, and _remove_overlapping_water created a fresh InterfaceStructure with only ice + water + guest atoms, losing all custom molecule information. Then in main_window.py lines 873-883, the code tried to extract custom molecules from the ORIGINAL custom_structure using indices from the NEW interface, which was incorrect.

fix: 
  1. Modified solute_inserter._remove_overlapping_water() (lines 437-590) to:
     - Detect if input structure has custom_molecule_atom_count (CustomMoleculeStructure)
     - Separate guests from custom molecules when present
     - Include custom molecules in the new positions array
     - Add custom molecule entries to molecule_index
     - Set custom molecule attributes on new InterfaceStructure
     - Use getattr() for attributes that differ between InterfaceStructure and CustomMoleculeStructure
  
  2. Modified main_window.py _on_insert_solutes() (line 1017) to:
     - Pass full CustomMoleculeStructure to solute_inserter instead of just interface_structure
  
  3. Modified main_window.py _on_insert_ions() (lines 873-883) to:
     - Remove redundant custom molecule extraction (now handled by _remove_overlapping_water)

verification: 
  - Test test_custom_solute_fix.py: PASSED - Custom molecules preserved when passing CustomMoleculeStructure to solute_inserter
  - Test test_workflow_e2e.py: PASSED - Complete workflow verified (Interface → Custom → Solute → Ion)
  - Custom molecules preserved in positions array with correct atom counts
  - All custom molecule attributes accessible for downstream processing (ion insertion, export)
files_changed: [quickice/structure_generation/solute_inserter.py, quickice/gui/main_window.py]
