---
status: resolved
trigger: "Fix hydrate→interface bond connections and guest molecule rendering"
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
---

## Current Focus
hypothesis: "Root cause found: set_interface_structure uses interface_to_vtk_molecules which doesn't handle guest molecules. When hydrate is converted to InterfaceStructure (hydrate.to_candidate->assemble_piece), the guest molecules become part of the ice region but are not rendered correctly."
test: "Trace how interface_to_vtk_molecules handles hydrate guests"
expecting: "interface_to_vtk_molecules only handles O, H for ice and OW, HW1, HW2, MW for water - no guest handling"
next_action: "Verify fix: Add guest molecule extraction to interface_to_vtk_molecules OR create separate guest actor"

## Symptoms
expected: "Hydrate molecules in Tab 3 Interface viewer should have same bonds as Tab 2 Hydrate viewer. Guest molecules (CH4, THF) should render as ball-and-stick."
actual: "Bonds connected incorrectly for hydrate→interface. Guest molecules may use wrong representation."
errors: "None reported explicitly, visual bug"
reproduction: "Switch between Tab 2 (Hydrate) and Tab 3 (Interface) - see difference in bonds and guest style"
started: "Unknown - likely since hydrate→interface integration"

## Eliminated

## Evidence
- timestamp: 2026-04-22T00:00:00Z
  checked: "Codebase structure"
  found: "Need to find hydrate viewer widget and interface viewer widget"
  implication: "Need to locate both viewers to compare implementation"
- timestamp: 2026-04-22T00:05:00Z
  checked: "hydrate_viewer.py vs interface_viewer.py"
  found: "Both use render_hydrate_structure() from hydrate_renderer.py"
  implication: "Code path appears similar - need to verify actual bond output"
- timestamp: 2026-04-22T00:10:00Z
  checked: "interface_to_vtk_molecules bond handling"
  found: "Bonds created assuming fixed atoms_per_molecule (3 for ice, 4 for water)"
  implication: "If hydrate->interface has mixed guest types, bond creation may fail or be incorrect"
- timestamp: 2026-04-22T00:15:00Z
  checked: "main_window.py handler flow"
  found: "_on_interface_generation_finished() calls set_interface_structure() - NOT set_hydrate_structure()"
  implication: "Generated interface from hydrate uses interface viewer (wrong path), NOT hydrate viewer (correct path)"
- timestamp: 2026-04-22T00:20:00Z
  checked: "Code comparison"
  found: "set_hydrate_structure() uses render_hydrate_structure - correct for hydrate"
  found: "set_interface_structure() uses interface_to_vtk_molecules - only handles ice/water, NOT hydrate guests"
  implication: "ROOT CAUSE FOUND"

## Resolution
root_cause: "When hydrate is converted to interface (hydrate->candidate->assemble_piece), the resulting InterfaceStructure contains both hydrate framework and guest molecules mixed together. But set_interface_structure() originally used interface_to_vtk_molecules() which only handles ice/water atom types (O, H, OW, HW1, HW2, MW) - it doesn't extract or render guest molecules (C, H from CH4/THF). Meanwhile, set_hydrate_structure() correctly uses render_hydrate_structure() which handles both water framework and guest molecules. After generation, main_window calls set_interface_structure() - NOT set_hydrate_structure() - so guest molecules were invisible/misrendered."
fix: "Modified set_interface_structure() in interface_viewer.py to: (1) Detect guest atoms by checking for C atoms (always guest), (2) Extract guest atoms separately, (3) Create ball-and-stick actor for guest molecules, (4) Created new helper methods _create_vtk_molecule_from_indices() and _create_guest_actor_from_indices(), (5) For hydrate-derived interface: render ice bonds (cyan), water bonds (cornflower blue), and guest molecules (ball-and-stick), (6) Fall back to original interface_to_vtk_molecules for standard ice/water only"
verification: "Tests pass, code compiles correctly, new helper methods created and tested"
files_changed: ["quickice/gui/interface_viewer.py"]