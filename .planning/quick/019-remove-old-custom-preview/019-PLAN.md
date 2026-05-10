---
phase: 019
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/custom_molecule_panel.py
  - quickice/gui/main_window.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "Old Preview All Positions button is removed"
    - "Preview column is removed from position table (6 columns instead of 7)"
    - "Validate & Preview button works correctly for single molecule preview"
    - "Clear Preview button works for validation preview"
    - "No crashes when using validation preview + generate"
  artifacts:
    - path: "quickice/gui/custom_molecule_panel.py"
      provides: "Custom molecule panel without old preview system"
      contains: "Validate & Preview"
    - path: "quickice/gui/main_window.py"
      provides: "Main window without old preview handlers"
      contains: "_on_custom_molecule_preview_cleared"
  key_links:
    - from: "CustomMoleculePanel.validate_button"
      to: "_on_validate_clicked"
      via: "clicked signal"
      pattern: "validate_button.clicked.connect"
    - from: "CustomMoleculePanel.clear_preview_button"
      to: "_on_clear_preview_clicked"
      via: "clicked signal"
      pattern: "clear_preview_button.clicked.connect"
---

<objective>
Remove old preview system from Custom Molecule Custom mode that conflicts with Phase 34.5 validation preview.

Purpose: Two preview systems coexist and crash when used together. The old system (Preview All button + preview column) conflicts with the new Validate & Preview button from Phase 34.5.

Output: Clean custom molecule panel with only Validate & Preview functionality.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/019-remove-old-custom-preview/task.md
</context>

<tasks>

<task type="auto">
  <name>Remove old preview UI from custom_molecule_panel.py</name>
  <files>quickice/gui/custom_molecule_panel.py</files>
  <action>
Remove old preview system components:

1. **Remove signal declaration** (line 58):
   - Remove: `preview_all_requested = Signal(list)`
   - KEEP: `preview_requested = Signal(tuple, tuple)` (used by Validate & Preview button)

2. **Update position table columns** (lines 549-552):
   - Change: `self.position_table.setColumnCount(7)` → `self.position_table.setColumnCount(6)`
   - Change header labels from `["X (nm)", "Y (nm)", "Z (nm)", "α (°)", "β (°)", "γ (°)", "Preview"]`
   - To: `["X (nm)", "Y (nm)", "Z (nm)", "α (°)", "β (°)", "γ (°)"]`

3. **Remove Preview All Positions button** (lines 561-570):
   - Remove the entire `preview_all_row` layout and button creation
   - Remove `self.preview_all_button` widget

4. **Remove signal connection** (line 600):
   - Remove: `self.preview_all_button.clicked.connect(self._on_preview_all_clicked)`

5. **Remove preview column from table update** (lines 920-923):
   - Remove the preview item creation:
     ```python
     preview_item = QTableWidgetItem("Click to preview")
     preview_item.setForeground(Qt.blue)
     self.position_table.setItem(i, 6, preview_item)
     ```

6. **Remove preview button enable/disable** (line 926):
   - Remove: `self.preview_all_button.setEnabled(len(self.positions_added) > 0)`

7. **Remove preview column click handling** (lines 940-944):
   - Remove the `if column == 6:` block from `_on_position_table_clicked()`
   - Keep the `else:` block that loads position into input fields

8. **Remove _on_preview_all_clicked method** (lines 955-986):
   - Remove the entire method

Why: Old preview system conflicts with Phase 34.5 validation preview due to shared viewer state. The new Validate & Preview button provides better workflow (validate before add).
  </action>
  <verify>
    - File reads without syntax errors
    - No references to preview_all_button or preview_all_requested
    - Position table has 6 columns
    - _on_preview_all_clicked method does not exist
  </verify>
  <done>
    - Old preview UI elements removed from custom_molecule_panel.py
    - Position table shows 6 columns (X, Y, Z, α, β, γ)
    - No "Preview All Positions" button
    - No "Click to preview" column
  </done>
</task>

<task type="auto">
  <name>Remove old preview handlers from main_window.py</name>
  <files>quickice/gui/main_window.py</files>
  <action>
Remove old preview system handlers:

1. **Remove signal connection** (line 296):
   - Remove: `self.custom_molecule_panel.preview_all_requested.connect(self._on_custom_molecule_preview_all_requested)`
   - KEEP: `self.custom_molecule_panel.preview_requested.connect(...)` (used by Validate & Preview)

2. **Remove _on_custom_molecule_preview_all_requested method** (lines 1362-1441):
   - Remove the entire method

Why: Removing the signal and handler eliminates the old preview functionality. The preview_requested signal remains because it's used by the new Validate & Preview button (Phase 34.5).
  </action>
  <verify>
    - File reads without syntax errors
    - No reference to preview_all_requested signal connection
    - _on_custom_molecule_preview_all_requested method does not exist
  </verify>
  <done>
    - Old preview handlers removed from main_window.py
    - preview_requested signal connection remains (for Validate & Preview button)
    - preview_cleared signal connection remains (for Clear Preview button)
  </done>
</task>

<task type="auto">
  <name>Test custom molecule preview workflow</name>
  <files></files>
  <action>
Manual testing to verify the fix:

1. Launch GUI: `python quickice/gui/main_window.py`

2. Create an interface structure:
   - Go to Tab 0 (Ice Generation)
   - Click on phase diagram to select T/P
   - Click Generate
   
3. Upload custom molecule files:
   - Go to Tab 3 (Custom Molecule)
   - Click "Upload .gro File" (use test file: tests/data/etoh.gro)
   - Click "Upload .itp File" (use test file: tests/data/etoh.itp)

4. Test Custom mode:
   - Switch to "Custom" mode in placement dropdown
   - Verify "Preview All Positions" button is GONE
   - Verify position table has 6 columns (no Preview column)

5. Test Validate & Preview workflow:
   - Enter position (e.g., 1.0, 1.0, 2.0)
   - Click "Validate & Preview" button
   - Verify validation result appears in status
   - Verify preview shows in 3D viewer
   - Click "Clear Preview" button
   - Verify preview clears

6. Test table row selection:
   - Add a position to the list
   - Click on the row in the table
   - Verify position loads into input fields (no preview action)

7. Test no crashes:
   - Use Validate & Preview, then clear preview
   - Add position to list
   - Click Generate
   - Verify no crashes
  </action>
  <verify>
    - GUI launches without errors
    - "Preview All Positions" button not visible
    - Position table has 6 columns
    - Validate & Preview button works
    - Clear Preview button works
    - Table row click loads position into inputs
    - No crashes during complete workflow
  </verify>
  <done>
    - Old preview system completely removed
    - Validate & Preview workflow functional
    - No crashes or conflicts
  </done>
</task>

</tasks>

<verification>
- No references to preview_all_button in custom_molecule_panel.py
- No references to preview_all_requested signal
- Position table has 6 columns (X, Y, Z, α, β, γ)
- _on_preview_all_clicked method removed
- _on_custom_molecule_preview_all_requested method removed
- Validate & Preview button works correctly
- Clear Preview button works correctly
- Manual testing passes without crashes
</verification>

<success_criteria>
- Old "Preview All Positions" button removed
- Old "Click to preview" table column removed
- preview_all_requested signal removed
- Old preview handler methods removed
- Phase 34.5 Validate & Preview functionality intact
- Clear Preview button functional
- No crashes when using validation preview + generate
</success_criteria>

<output>
After completion, create `.planning/quick/019-remove-old-custom-preview/019-SUMMARY.md`
</output>
