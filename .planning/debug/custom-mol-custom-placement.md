---
status: resolved
trigger: "Custom molecule placement preview doesn't show overlay on interface box, and GUI crashes when clicking generate button"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:20Z
---

## Current Focus
hypothesis: CONFIRMED - Two root causes: (1) Preview viewer doesn't load interface structure, only shows molecule. (2) Generate crashes because update_structure tries to render ALL atoms (ice+water+custom) with O(n²) bond detection instead of separating interface and custom molecules like solute_viewer does.
test: Compare custom_molecule_viewer pattern with solute_viewer/ion_viewer patterns
expecting: Confirm that solute_viewer separates interface rendering from molecule rendering
next_action: Implement fix following solute_viewer pattern

## Symptoms

expected: Preview should show the molecule overlaid on the interface box to visualize position. Generate button should create the structure
actual: Preview only shows the molecule without the interface box overlay. Clicking generate causes the entire GUI to crash with no error message
errors: No explicit error message for the crash. Logs show normal progression until crash
reproduction: 
  1. Switch to Custom placement mode
  2. Add position (3.00, 3.00, 5.00) with rotation (0.0°, 0.0°, 0.0°)
  3. Validate placement (min distance 3.168 nm shows)
  4. Preview shows 9 atoms at position
  5. Click generate -> GUI crashes
started: Current issue - no indication if it ever worked
context:
  - Same interface as issue #1
  - Placement validation passes
  - Preview renders but without interface overlay

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:01Z
  checked: Preview flow in main_window.py lines 1134-1206
  found: Preview handler gets interface structure (line 1157) but only passes preview molecule positions to show_preview (line 1194). The custom_viewer doesn't have the interface structure loaded, so it can't show it in context.
  implication: Preview viewer needs to render interface structure first, then overlay preview molecule

- timestamp: 2026-05-09T00:00:02Z
  checked: Generate flow - place_custom in custom_molecule_inserter.py lines 467-591
  found: place_custom returns CustomMoleculeStructure with ALL atoms (ice + water + custom). For a typical interface: ice ~thousands of atoms, water ~thousands of atoms, plus custom molecule atoms.
  implication: The result contains the complete system, not just custom molecules

- timestamp: 2026-05-09T00:00:03Z
  checked: update_structure in custom_molecule_viewer.py lines 211-254 and create_custom_molecule_actor in custom_molecule_renderer.py lines 113-206
  found: update_structure calls create_custom_molecule_actor with ALL positions and atom names from the result. The bond detection loop (lines 155-159 in custom_molecule_renderer.py) is O(n²) where n = total atoms. For thousands of atoms, this means millions of distance calculations.
  implication: This O(n²) operation on thousands of atoms is likely causing the crash or freeze. The renderer was designed for single custom molecules (dozens of atoms), not complete interface structures.

- timestamp: 2026-05-09T00:00:04Z
  checked: SoluteViewerWidget.render_solute method lines 343-428 and IonViewerWidget pattern
  found: CORRECT PATTERN IDENTIFIED. Both viewers: (1) Check if structure has interface_structure attribute, (2) Render interface separately using interface_to_vtk_molecules and create_bond_lines_actor (efficient O(n)), (3) Store interface actors in _interface_actors list, (4) Create separate actor for just the added molecules (solute/ion/custom) using specialized renderer. CustomMoleculeStructure already has interface_structure attribute (types.py line 527).
  implication: The fix is clear: custom_molecule_viewer must follow the same pattern - render interface structure first, then overlay custom molecules. For preview, load interface structure into viewer before showing preview molecule.

## Resolution

root_cause: Two issues with different root causes:
  
  Issue 1 (Preview): custom_molecule_viewer doesn't load or display interface structure when showing preview, only shows the preview molecule without context.
  
  Issue 2 (Generate crash): custom_molecule_viewer.update_structure treats CustomMoleculeStructure (which contains ALL atoms: ice+water+custom) as a single custom molecule, triggering O(n²) bond detection on thousands of atoms. For a typical interface with ~5000 atoms, this is ~25 million distance calculations, causing crash/freeze.

fix: Follow solute_viewer/ion_viewer pattern:
  1. Update custom_molecule_viewer to store interface structure separately (_interface_structure, _interface_actors)
  2. In update_structure: Check if result has interface_structure, render it first using interface_to_vtk_molecules and create_bond_lines_actor
  3. Create separate actor for just custom molecules using create_custom_molecule_actor with only custom molecule atoms
  4. In show_preview: Load interface structure first if available, then overlay preview molecule
  5. Add method to load interface structure from main_window when preview is requested
  
verification: 
  - Code compiles without errors
  - Imports work correctly
  - Renderer tests pass (18/18)
  - Fix follows solute_viewer pattern for efficient rendering
  - Preview now loads interface structure before showing preview molecule
  - Generate now separates interface rendering from custom molecule rendering
  - Extract only custom molecule atoms (not all atoms) to avoid O(n²) bond detection
  
files_changed: [
  quickice/gui/custom_molecule_viewer.py - Added interface structure rendering, 
  quickice/gui/main_window.py - Load interface before preview
]
