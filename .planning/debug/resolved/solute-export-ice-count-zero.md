---
status: resolved
trigger: "When exporting solute tab via Ctrl-S, the dialog reports Ice: 0 molecules but the actual .gro/.top files contain ice molecules"
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED
test: All tests pass, new regression test added
expecting: Dialog now shows correct ice count
next_action: Archive session

## Symptoms

expected: Dialog should show correct ice molecule count (non-zero) when exporting a solute structure that contains ice
actual: Dialog shows "Ice: 0 molecules" even though the exported .gro file contains ice molecules (SOL 3501 = ice + water)
errors: No error thrown — export succeeds, files are correct, just the dialog message is wrong
reproduction: In GUI: ice (ih) → slab interface → custom mol (random) → solute → Ctrl-S export current tab (solute)
started: Unknown if ever worked correctly

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-06-19T00:00:00Z
  checked: Exported .gro file
  found: 14288 atoms, 3501 SOL molecules (ice+water combined), 19 CH4_L, 21 etoh
  implication: Ice molecules ARE physically present in exported structure

- timestamp: 2026-06-19T00:00:00Z
  checked: Export dialog code in main_window.py:1746-1760
  found: Gets ice_count from `interface.ice_nmolecules if interface else 0`, where interface = solute_structure.interface_structure
  implication: Bug is either interface_structure is None, or ice_nmolecules is 0 on it

- timestamp: 2026-06-19T00:00:00Z
  checked: Dialog output
  found: Ice: 0, Water: 1965, CH4: 19; 3501 - 1965 = 1536 missing ice molecules
  implication: Water count works but ice count doesn't

- timestamp: 2026-06-19T00:00:00Z
  checked: .top file content
  found: "3501 SOL (ice+water) + 21 custom molecules + 19 CH4 solutes"; [molecules] section has SOL 3501
  implication: Top file correctly reports combined SOL count

- timestamp: 2026-06-19T00:00:01Z
  checked: CustomMoleculeStructure class definition (types.py:589-628)
  found: CustomMoleculeStructure has ice_atom_count but NOT ice_nmolecules or water_nmolecules fields. It has interface_structure which holds the original InterfaceStructure
  implication: When getattr(structure, 'ice_nmolecules', 0) is called on a CustomMoleculeStructure, it returns 0 (the default)

- timestamp: 2026-06-19T00:00:01Z
  checked: SoluteInserter._remove_overlapping_water() (solute_inserter.py:498, 652)
  found: Both branches use `ice_nmolecules=getattr(structure, 'ice_nmolecules', 0)` which returns 0 for CustomMoleculeStructure
  implication: The resulting InterfaceStructure stored in SoluteStructure.interface_structure has ice_nmolecules=0, causing the dialog to show "Ice: 0 molecules"

- timestamp: 2026-06-19T00:00:01Z
  checked: _remove_overlapping_water() already has fallback pattern for mode/report fields
  found: Lines 485-490 and 639-644 already use `getattr(structure.interface_structure, 'mode', 'slab')` as fallback
  implication: Same pattern should be applied to ice_nmolecules — consistent with existing code style

## Resolution

root_cause: CustomMoleculeStructure lacks ice_nmolecules field. When SoluteInserter._remove_overlapping_water() uses getattr(structure, 'ice_nmolecules', 0) on a CustomMoleculeStructure, it returns 0 instead of falling back to the original InterfaceStructure's ice_nmolecules via structure.interface_structure. The resulting InterfaceStructure in SoluteStructure.interface_structure therefore has ice_nmolecules=0, causing the export dialog to show "Ice: 0 molecules".
fix: Added _resolve_ice_nmolecules() static method (mirrors existing _resolve_guest_nmolecules) that falls back to structure.interface_structure.ice_nmolecules when the structure itself lacks the field. Replaced both getattr(structure, 'ice_nmolecules', 0) calls in _remove_overlapping_water() with self._resolve_ice_nmolecules(structure). Also made the dialog code defensive with getattr() instead of direct attribute access.
verification: All 66+ existing tests pass. New regression test test_ice_nmolecules_preserved_from_custom_molecule_structure passes. Manual verification with CustomMoleculeStructure → SoluteInserter path confirms ice_nmolecules preserved correctly.
files_changed: [quickice/structure_generation/solute_inserter.py, quickice/gui/main_window.py, tests/test_solute_insertion.py, tests/test_e2e_solute_export.py]
