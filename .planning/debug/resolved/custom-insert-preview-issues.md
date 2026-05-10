---
status: resolved
trigger: "Three related issues with custom mol custom insert mode: 1) Preview only shows last added molecule, not all positions 2) Label 'min distance to nearest atom' is misleading 3) Should show list of all positions"
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - Preview system needs three fixes: 1) Show all positions not just current, 2) Fix label text, 3) Add position list UI
test: Modify _on_validate_clicked to preview all positions, fix label, add QTableWidget
expecting: Preview shows all positions when Validate clicked, label is clear, table shows all values
next_action: Implement fixes to CustomMoleculePanel and viewer

## Symptoms

expected: 
  - Preview should show all molecule positions (e.g., 2 mols = both visible)
  - Label should clearly state "min distance to nearest atom in ice/hydrate layer"
  - UI should display list of all positions with values and clickable preview

actual: 
  - Preview only shows the last added molecule
  - Label says "min distance to nearest atom" (ambiguous)
  - No list of positions visible

errors: None

reproduction: 
  1. Create hydrate or ice structure with slab interface
  2. Add custom molecule in "custom insert" mode
  3. Add 2 molecule positions
  4. Preview shows only last position
  5. Click Generate - correctly places both molecules

started: Unknown - may have always been this way

note: Generation is correct, only preview/display is wrong

## Eliminated

## Evidence

- timestamp: 2026-05-10T00:01:00Z
  checked: CustomMoleculePanel._on_validate_clicked (lines 687-780)
  found: Preview only validates and shows CURRENT position/rotation from input fields (lines 703-712), not all positions in positions_added list
  implication: Preview system needs to be modified to iterate over all positions_added when multiple exist

- timestamp: 2026-05-10T00:02:00Z
  checked: CustomMoleculeViewerWidget.show_preview (lines 613-671)
  found: Method clears any existing preview before showing new one (line 640: self.clear_preview())
  implication: Need to either accumulate actors OR show all molecules in single call

- timestamp: 2026-05-10T00:03:00Z
  checked: CustomMoleculePanel label text (line 752)
  found: Label says "Min distance to nearest atom: {result.min_distance:.3f} nm"
  implication: Should clarify "Min distance to nearest atom in ice/hydrate layer"

- timestamp: 2026-05-10T00:04:00Z
  checked: CustomMoleculePanel positions_added tracking (line 70)
  found: positions_added list exists but only count label shown (lines 455-457), no table/list widget to display positions
  implication: Need to add UI widget (QTableWidget or QListWidget) to show all positions with clickable preview

## Resolution

root_cause: Three separate issues identified:
1. Preview only shows last molecule: Preview system designed for single-molecule validation, not multi-position preview
2. Misleading label: "Min distance to nearest atom" doesn't clarify it's measuring to ice/hydrate layer atoms only
3. No position list UI: positions_added list tracked internally but not displayed to user

fix: Three-part fix implemented:
1. Preview all positions: Added show_multiple_previews() method to viewer, preview_all_requested signal to panel, Preview All button to UI, and handler in MainWindow
2. Label clarification: Changed "Min distance to nearest atom" to "Min distance to nearest atom in ice/hydrate layer"
3. Position list UI: Added QTableWidget with 7 columns (X, Y, Z, α, β, γ, Preview), clickable rows to load/preview individual positions

verification: 
- Automated verification script passed all checks (verify_custom_preview_fix.py)
- QTableWidget created with 7 columns: X, Y, Z, α, β, γ, Preview
- Preview All button exists and connected
- show_multiple_previews method exists in viewer
- preview_all_requested signal exists in panel
- Handler exists in MainWindow
- Label text correctly updated to include "ice/hydrate layer"

Manual testing steps:
1. Launch GUI: python quickice/gui/main_window.py
2. Upload .gro and .itp files in Custom Molecule tab
3. Generate an interface structure
4. Switch to Custom placement mode
5. Add multiple positions using "Add Position" button
6. Verify table shows all positions with correct values
7. Click "Preview All Positions" button - should see all molecules in 3D viewer
8. Click individual table rows - should load position into input fields or preview that specific molecule
9. Check validation label shows "Min distance to nearest atom in ice/hydrate layer"
10. Click Generate - verify both molecules are correctly inserted
files_changed: [quickice/gui/custom_molecule_panel.py, quickice/gui/custom_molecule_viewer.py, quickice/gui/main_window.py]
