---
phase: quick-018
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/custom_molecule_panel.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "User can delete a selected position from the list"
    - "User receives warning when adding overlapping position"
    - "User can choose to add overlapping position anyway"
    - "Delete button is disabled when no row selected"
    - "Position count updates correctly after delete"
    - "Overlap uses center-to-center distance (0.25 nm default)"
  artifacts:
    - path: "quickice/gui/custom_molecule_panel.py"
      provides: "Delete button and overlap detection for custom positions"
      contains: "_delete_selected_position"
      contains: "_check_overlap_with_existing_positions"
  key_links:
    - from: "position_table.itemSelectionChanged"
      to: "delete_position_button.setEnabled"
      via: "_on_position_selection_changed"
    - from: "_add_position"
      to: "_check_overlap_with_existing_positions"
      via: "overlap check before adding"
    - from: "overlap warning dialog"
      to: "user choice"
      via: "QMessageBox.warning with Yes/No"
---

<objective>
Add delete functionality and overlap detection to Custom Molecule Custom mode.

Purpose: Enable users to manage position list by removing unwanted entries and prevent accidental overlapping positions.

Output: Enhanced CustomMoleculePanel with delete button and overlap warning.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@quickice/gui/custom_molecule_panel.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Delete Functionality</name>
  <files>quickice/gui/custom_molecule_panel.py</files>
  <action>
Add delete button and selection handling to CustomMoleculePanel:

1. **Add delete button UI** in `_create_custom_controls()` after "Add Position" button (around line 540):
   - QPushButton("Delete Selected") with tooltip "Remove selected position from list"
   - Initially disabled (enabled when row selected)
   - Add to same row as "Add Position" button

2. **Connect selection signal** in `_setup_connections()`:
   - Connect `self.position_table.itemSelectionChanged` to `_on_position_selection_changed()`
   - Connect delete button to `_delete_selected_position()`

3. **Implement `_on_position_selection_changed()`** method:
   - Check if any rows selected via `len(self.position_table.selectedItems()) > 0`
   - Enable/disable delete button accordingly

4. **Implement `_delete_selected_position()`** method:
   - Get selected row via `selected_rows[0].row()`
   - Remove from `self.positions_added[row]`
   - Call `_update_position_table()` to refresh display
   - Update `position_count_label` with new count
   - Log message with deleted position coordinates
   - Disable delete button after deletion

Reference existing patterns:
- Table row access pattern (line 808-817 in `_update_position_table()`)
- Position/rotation tuple structure (line 789-790 in `_add_position()`)
- Message logging pattern (line 798-799)
</action>
  <verify>
Manual GUI test:
1. Launch GUI: `python quickice/gui/main_window.py`
2. Create interface structure, upload custom molecule files
3. Switch to Custom mode, add 2-3 positions
4. Click on a table row → verify "Delete Selected" button enables
5. Click "Delete Selected" → verify row removed and count updates
6. Click elsewhere (no selection) → verify button disables
</verify>
  <done>
- Delete button appears in Custom mode UI
- Button disabled when no row selected
- Button enabled when row selected
- Clicking delete removes selected row from table and positions_added list
- Position count label updates correctly
- Log shows deletion message
</done>
</task>

<task type="auto">
  <name>Task 2: Add Overlap Detection</name>
  <files>quickice/gui/custom_molecule_panel.py</files>
  <action>
Add overlap detection with warning dialog:

1. **Implement `_check_overlap_with_existing_positions()`** method:
   - Parameters: `position: tuple[float, float, float]`, `min_separation: float = 0.25`
   - Returns: `tuple[bool, int | None]` (has_overlap, overlapping_row_index)
   - Loop through `self.positions_added`
   - Calculate center-to-center distance: `np.sqrt((x1-x2)² + (y1-y2)² + (z1-z2)²)`
   - Return `(True, i)` if distance < min_separation
   - Return `(False, None)` if no overlap found

2. **Update `_add_position()`** method (around line 774):
   - After parsing position and rotation (lines 777-787)
   - Call `has_overlap, overlap_row = self._check_overlap_with_existing_positions(position)`
   - If overlap detected:
     - Show `QMessageBox.warning()` with title "Overlap Detected"
     - Message: "This position overlaps with position {overlap_row + 1}.\n\nAdd anyway? (Molecules may overlap)"
     - Buttons: `QMessageBox.Yes | QMessageBox.No`, default to `QMessageBox.No`
     - If user clicks No, return early (don't add position)
   - Continue with existing add logic if no overlap or user approves

Import requirements:
- Already has `import numpy as np` (line 19)
- Already has `QMessageBox` imported (line 25)

Reference patterns:
- QMessageBox.warning pattern from `_show_residue_mismatch_dialog()` (lines 691-718)
- Distance calculation from SoluteInserter._check_molecule_overlap() (solute_inserter.py:347-406)
</action>
  <verify>
Manual GUI test:
1. Add position (1.0, 1.0, 1.0)
2. Try to add same position again → verify warning dialog appears
3. Click "No" → verify position NOT added (count unchanged)
4. Try again, click "Yes" → verify position added (count increases)
5. Add position (1.1, 1.0, 1.0) → verify warning (within 0.25 nm of first)
6. Add position (3.0, 3.0, 3.0) → verify NO warning (no overlap)
</verify>
  <done>
- Overlap warning shown for positions within 0.25 nm of existing positions
- Warning dialog shows which position it overlaps with
- User can choose "Yes" to add anyway or "No" to cancel
- Non-overlapping positions add without warning
- Center-to-center distance calculation works correctly
</done>
</task>

</tasks>

<verification>
Run GUI and manually verify:
1. Delete functionality works correctly
2. Overlap detection triggers appropriately
3. Both features integrate smoothly without breaking existing functionality
</verification>

<success_criteria>
- Delete button enables/disables correctly based on selection
- Delete removes selected row and updates count
- Overlap warning appears for overlapping positions
- User can override overlap warning
- All manual test scenarios pass
- No regressions in existing Custom mode functionality
</success_criteria>

<output>
After completion, create `.planning/quick/018-custom-mol-delete-and-overlap/018-SUMMARY.md`
</output>
