---
status: resolved
trigger: "In the 'custom -> solute' workflow, the 'estimated no. of solute' display always shows zero, even though the actual generation works correctly and inserts the correct number of molecules."
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED - When CustomMoleculeStructure is set, the liquid volume is not being calculated and passed to SolutePanel
test: Compare main_window.py handling for Interface vs Custom Molecule sources
expecting: Found that Interface calls set_liquid_volume() but Custom Molecule does not
next_action: Implement fix in main_window.py to set liquid volume for Custom Molecule source

## Symptoms

expected: The estimated count should show the calculated number of solute molecules based on concentration and liquid volume
actual: Always shows 0, regardless of concentration or volume settings
errors: None
reproduction: 
  1. Create hydrate or ice structure
  2. Add custom molecules
  3. Add solute with specific concentration (e.g., 0.1 M)
  4. Observe 'estimated no. of solute' display - shows 0
  5. Click Generate - inserts correct number of molecules (so calculation works)
started: Unknown when this started
comparison: The actual generation calculates correctly, only the preview estimate is wrong

## Eliminated

## Evidence

- timestamp: 2026-05-10T00:00:30Z
  checked: SolutePanel._update_preview() method (solute_panel.py:309-320)
  found: Preview checks `if self._liquid_volume_nm3 <= 0:` and returns early with "No liquid volume"
  implication: The liquid volume is the key variable for preview calculation

- timestamp: 2026-05-10T00:00:45Z
  checked: main_window.py interface generation handler (lines 620-632)
  found: When Interface is generated: `liquid_vol = result.water_nmolecules * 0.0299` then `self.solute_panel.set_liquid_volume(liquid_vol)`
  implication: Interface source correctly sets liquid volume for solute panel

- timestamp: 2026-05-10T00:00:55Z
  checked: main_window.py custom molecule generation handler (lines 1193-1200)
  found: When Custom Molecule is generated: `self.solute_panel.set_custom_molecule_structure(result)` but NO call to `set_liquid_volume()`
  implication: Custom Molecule source does NOT set liquid volume, leaving it at default 0.0

- timestamp: 2026-05-10T00:01:10Z
  checked: SoluteInserter.insert_solutes() method (solute_inserter.py:642-650)
  found: Actual insertion correctly handles both InterfaceStructure and CustomMoleculeStructure by calculating `water_nmolecules` from `water_atom_count` if needed
  implication: Actual generation works because it calculates volume on-the-fly, but preview relies on pre-set `_liquid_volume_nm3` attribute

- timestamp: 2026-05-10T00:01:20Z
  checked: CustomMoleculeStructure definition (types.py:505-542)
  found: Has `water_atom_count` attribute and `interface_structure` reference
  implication: Can calculate liquid volume from CustomMoleculeStructure.water_atom_count using same formula as Interface

## Resolution

root_cause: When CustomMoleculeStructure is generated and passed to SolutePanel, the main_window.py does not call set_liquid_volume() with the calculated liquid volume from the custom molecule structure's water atoms. This leaves SolutePanel._liquid_volume_nm3 at 0.0, causing the preview calculation to show "No liquid volume" or 0 molecules, even though the actual insertion works correctly by calculating volume on-the-fly.

fix: In main_window.py, after calling set_custom_molecule_structure(result) on solute_panel (line 1194), calculate the liquid volume from result.water_atom_count and call set_liquid_volume() with that value. Use the same formula as for Interface: `liquid_vol = (result.water_atom_count // 4) * 0.0299` where // 4 converts atoms to molecules (TIP4P has 4 atoms per molecule), then multiply by 0.0299 nm³ per molecule.

verification: 
  - Created test_custom_solute_estimate_fix.py that verifies the fix
  - Test 1: Reproduces the bug - shows 0 molecules when liquid volume not set
  - Test 2: Verifies fix - shows correct molecule count (1 molecule) when liquid volume is set
  - Test 3: Verifies actual insertion still works correctly
  - All tests pass ✅
files_changed: 
  - quickice/gui/main_window.py: Added liquid volume calculation and set_liquid_volume() calls for Custom Molecule source
