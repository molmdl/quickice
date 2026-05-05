---
status: resolved
trigger: "Multiple issues: (1) no water replacement count in log, (2) THF bonds wrong in liquid phase, (3) ion panel solute source not showing solutes"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:30:00Z
---

## Current Focus
hypothesis: ALL THREE ROOT CAUSES FOUND. Ready to fix.
test: Apply fixes to each issue
expecting: All three issues resolved
next_action: Fix Issue 1 (water replacement count logging in main_window.py)

## Symptoms
expected:
1. User should see log message showing how many liquid water molecules were replaced by solute insertion
2. THF molecules should have correct bonds in both hydrate layer and liquid phase
3. Ion panel "solute" source should show solute molecules and use them for ion insertion

actual:
1. No feedback in log showing water replacement count (water IS being replaced, but no user-facing message)
2. THF in hydrate layer looks correct, but THF in liquid phase (from solute insertion) has wrong bonds
3. Ion panel selecting "solute" source gives similar results to "interface" - solutes not visible

errors: No errors visible
reproduction:
1. Insert solute and check log/console
2. Generate hydrate -> interface -> insert THF, compare hydrate THF bonds vs liquid THF bonds
3. Insert solute, then go to ion tab, select "solute" source

started: Just discovered after previous fixes

## Eliminated

## Evidence
- timestamp: 2026-05-05T00:05:00Z
  checked: solute_inserter.py lines 436-439
  found: _remove_overlapping_water() DOES log water replacement count using logger.info()
  implication: Log message exists but user can't see it - need to check UI logging

- timestamp: 2026-05-05T00:06:00Z
  checked: solute_renderer.py lines 139-145 vs hydrate_renderer.py lines 229-235
  found: solute_renderer.py detects bonds across ALL atoms at once. hydrate_renderer.py uses _build_vtk_molecule_from_molecule() to detect bonds WITHIN each molecule separately
  implication: ROOT CAUSE FOR ISSUE 2: Bonds detected between different THF molecules in liquid phase

- timestamp: 2026-05-05T00:07:00Z
  checked: SoluteStructure class definition (types.py line 414)
  found: SoluteStructure has molecule_indices: list[tuple[int, int]] that tracks which atoms belong to which molecule
  implication: Fix for Issue 2 is to use molecule_indices to detect bonds per-molecule like hydrate_renderer.py does

- timestamp: 2026-05-05T00:10:00Z
  checked: main_window.py lines 890, 907-909
  found: _on_insert_solutes() logs start/success to solute_panel.log_message() but does NOT log water replacement count. Logger.info() messages from solute_inserter.py don't appear in UI.
  implication: ROOT CAUSE FOR ISSUE 1: Need to calculate water replacement count in main_window.py and log it

- timestamp: 2026-05-05T00:11:00Z
  checked: InterfaceStructure definition (types.py line 264)
  found: InterfaceStructure has water_nmolecules: int field
  implication: Can calculate water replacement as: original_interface.water_nmolecules - solute_structure.interface_structure.water_nmolecules

- timestamp: 2026-05-05T00:12:00Z
  checked: main_window.py lines 823, 849-853
  found: _on_insert_ions() always uses self._current_interface_result, does NOT check source dropdown (Interface/Solute/Custom Molecule)
  implication: ROOT CAUSE FOR ISSUE 3: Ion insertion ignores source selection

- timestamp: 2026-05-05T00:13:00Z
  checked: ion_panel.py line 49
  found: ion_panel stores _current_source but has no getter method
  implication: Need to add get_current_source() method to ion_panel.py

## Resolution
root_cause: THREE ISSUES:
1. Water replacement count logged via logger.info() but not shown in UI panel
2. solute_renderer.py detects bonds across all molecules instead of per-molecule
3. ion insertion ignores source dropdown, always uses interface structure
fix: 
1. Added water replacement count logging in main_window.py._on_insert_solutes() - calculates difference between original and modified water counts
2. Modified solute_renderer.py.create_solute_actor() to accept molecule_indices parameter and detect bonds per-molecule; updated solute_viewer.py to pass molecule_indices
3. Added get_current_source() method to ion_panel.py; modified main_window.py._on_insert_ions() to check source and use appropriate structure (Interface/Solute, Custom Molecule not supported)
verification: 
- All custom test_fixes.py tests passed
- test_structure_generation.py: 59 passed
- test_solute_insertion.py: 9 passed, 2 skipped
- All imports successful
files_changed: 
- quickice/gui/main_window.py
- quickice/gui/solute_renderer.py
- quickice/gui/solute_viewer.py
- quickice/gui/ion_panel.py
