# Quick Task 018: Custom Molecule Delete & Overlap Detection

**Created:** 2026-05-10
**Status:** pending
**Priority:** high
**Estimated effort:** 2-3 hours, ~150 lines

---

## Objective

Add two features to Custom Molecule Custom mode:
1. **Delete functionality** - Remove molecules from the position list
2. **Overlap detection** - Warn when adding a position that overlaps with existing planned molecules

---

## Background

**Problem:** Users can click "Add Position" multiple times for the same position, creating duplicate/overlapping entries with no way to remove them.

**Current state:**
- Position list is a QTableWidget (line 543)
- No delete button or right-click menu
- No overlap check between custom molecules in the list

**Reference:** `SoluteInserter._check_molecule_overlap()` (solute_inserter.py:347-406) provides overlap checking between molecules.

---

## Implementation Plan

### Task 1: Add Delete Button and Logic (1 hour)

**File:** `quickice/gui/custom_molecule_panel.py`

1. **Add delete button** after "Add Position" button:
   ```python
   self.delete_position_button = QPushButton("Delete Selected")
   self.delete_position_button.setToolTip("Remove selected position from list")
   self.delete_position_button.setEnabled(False)  # Enabled when row selected
   ```

2. **Wire up delete functionality:**
   - Connect button to `_delete_selected_position()`
   - Connect table selection change to enable/disable delete button
   - Remove selected row from `self.positions_added`
   - Update table and count label

3. **Implementation:**
   ```python
   def _delete_selected_position(self):
       """Delete the selected position from the list."""
       selected_rows = self.position_table.selectedItems()
       if not selected_rows:
           return
       
       row = selected_rows[0].row()
       if 0 <= row < len(self.positions_added):
           position, rotation = self.positions_added[row]
           del self.positions_added[row]
           self._update_position_table()
           self.position_count_label.setText(f"Positions added: {len(self.positions_added)}")
           self.log_message(f"Deleted position {row + 1}: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
           self.delete_position_button.setEnabled(False)
   ```

### Task 2: Add Overlap Detection (1-1.5 hours)

**File:** `quickice/gui/custom_molecule_panel.py`

1. **Add overlap check method** - Check if new position overlaps with existing positions:
   ```python
   def _check_overlap_with_existing_positions(
       self,
       position: tuple[float, float, float],
       min_separation: float = 0.25
   ) -> tuple[bool, int | None]:
       """Check if position overlaps with already-added custom molecules.
       
       Uses center-to-center distance check (simplified).
       
       Args:
           position: (x, y, z) position to check
           min_separation: Minimum allowed distance (default 0.25 nm)
           
       Returns:
           (has_overlap, overlapping_row_index)
       """
       for i, (existing_pos, _) in enumerate(self.positions_added):
           dist = np.sqrt(
               (position[0] - existing_pos[0])**2 +
               (position[1] - existing_pos[1])**2 +
               (position[2] - existing_pos[2])**2
           )
           if dist < min_separation:
               return True, i
       
       return False, None
   ```

2. **Update `_add_position()`** to check overlap before adding:
   ```python
   def _add_position(self):
       # ... existing validation ...
       
       # Check overlap with existing positions
       has_overlap, overlap_row = self._check_overlap_with_existing_positions(position)
       
       if has_overlap:
           reply = QMessageBox.warning(
               self,
               "Overlap Detected",
               f"This position overlaps with position {overlap_row + 1}.\n\n"
               f"Add anyway? (Molecules may overlap)",
               QMessageBox.Yes | QMessageBox.No,
               QMessageBox.No
           )
           if reply == QMessageBox.No:
               return
       
       # ... add to list ...
   ```

### Task 3: Wire Up Selection Change (30 min)

Connect table selection to enable delete button:
```python
self.position_table.itemSelectionChanged.connect(self._on_position_selection_changed)

def _on_position_selection_changed(self):
    """Enable/disable delete button based on selection."""
    has_selection = len(self.position_table.selectedItems()) > 0
    self.delete_position_button.setEnabled(has_selection)
```

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `quickice/gui/custom_molecule_panel.py` | Add delete button, overlap check, wire signals | +80 |

**Total:** ~80 lines

---

## Testing

### Manual Testing

1. Launch GUI: `python quickice/gui/main_window.py`
2. Create an interface structure
3. Upload custom molecule files
4. Switch to Custom mode
5. Add multiple positions (some overlapping)
6. Verify overlap warning appears
7. Click on a table row, verify "Delete Selected" enables
8. Click delete, verify row removed
9. Verify "Positions added" count updates correctly

### Edge Cases

- Delete with no selection (button disabled)
- Delete last position
- Overlap detection with same exact position
- Overlap detection with nearby position (within 0.25 nm)

---

## Success Criteria

- [ ] Delete button appears in Custom mode
- [ ] Delete button disabled when no row selected
- [ ] Delete button enabled when row selected
- [ ] Clicking delete removes selected row
- [ ] Position count updates after delete
- [ ] Overlap warning shown for overlapping positions
- [ ] User can choose to add anyway or cancel
- [ ] Manual testing confirms correct behavior

---

## Reference Files

- `quickice/gui/custom_molecule_panel.py` - Current position table implementation
- `quickice/structure_generation/solute_inserter.py` - Overlap check pattern (lines 347-406)
- `quickice/structure_generation/custom_molecule_inserter.py` - validate_single_placement for reference
