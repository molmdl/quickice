# Quick Task 019: Remove Old Custom Molecule Preview

**Created:** 2026-05-10
**Status:** pending
**Priority:** high
**Estimated effort:** 1 hour, ~100 lines removed

---

## Objective

Remove the old preview system from Custom Molecule Custom mode, keeping only the Phase 34.5 "Validate & Preview" functionality.

**Problem:** Two preview systems coexist and conflict:
1. **OLD** - "Preview All Positions" button + "Click to preview" column (causes conflicts)
2. **NEW** - "Validate & Preview" button (Phase 34.5, semi-transparent rendering)

When both are used, the UI crashes due to shared viewer state.

---

## Background

**Current state:**
- `preview_requested` signal - previews single position from table
- `preview_all_requested` signal - previews all positions from "Preview All Positions" button
- "Preview All Positions" button (lines 561-570)
- "Click to preview" column in position table (lines 820-822)
- Both use same "Clear Preview" button as new validation preview

**New preview (Phase 34.5) - KEEP:**
- "Validate & Preview" button validates single position before adding
- Semi-transparent rendering (opacity 0.6)
- Clearer workflow: validate → add → generate

---

## Implementation Plan

### Task 1: Remove Old Preview UI Elements (30 min)

**File:** `quickice/gui/custom_molecule_panel.py`

Remove:
1. **Signal declarations** (lines 57-58):
   ```python
   preview_requested = Signal(tuple, tuple)  # REMOVE
   preview_all_requested = Signal(list)  # REMOVE
   ```

2. **"Preview All Positions" button** (lines 561-570):
   - Remove button creation
   - Remove layout addition

3. **"Click to preview" column** from position table:
   - Change column count from 7 to 6 (line 544)
   - Remove "Preview" from header labels (line 545)
   - Remove preview column item creation (lines 820-822)

### Task 2: Remove Old Preview Methods (15 min)

**File:** `quickice/gui/custom_molecule_panel.py`

Remove methods:
1. `_on_preview_all_clicked()` (lines 955-986)
2. Preview column click handling in `_on_position_table_clicked()` (lines 839-843)

### Task 3: Remove Signal Connections (10 min)

**File:** `quickice/gui/custom_molecule_panel.py`

Remove from `_setup_connections()`:
- `self.preview_all_button.clicked.connect(...)` (line 600)

**File:** `quickice/gui/main_window.py`

Remove signal connections:
- `self.custom_molecule_panel.preview_requested.connect(...)` (line 295)
- `self.custom_molecule_panel.preview_all_requested.connect(...)` (line 296)

Remove handler methods:
- `_on_custom_molecule_preview_requested()` (line 1284+)
- `_on_custom_molecule_preview_all_requested()` (line 1363+)

### Task 4: Update Table Click Handler (5 min)

**File:** `quickice/gui/custom_molecule_panel.py`

Update `_on_position_table_clicked()`:
- Remove column 6 (preview column) check
- Keep load-into-input-fields functionality (columns 0-5)

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `quickice/gui/custom_molecule_panel.py` | Remove old preview UI, signals, methods | -80 |
| `quickice/gui/main_window.py` | Remove signal connections and handlers | -60 |

**Total:** ~140 lines removed

---

## Testing

### Manual Testing

1. Launch GUI: `python quickice/gui/main_window.py`
2. Create an interface structure
3. Upload custom molecule files
4. Switch to Custom mode
5. Verify "Preview All Positions" button is gone
6. Verify position table has 6 columns (no "Preview" column)
7. Test "Validate & Preview" button works correctly
8. Add position, verify table row shows correct data
9. Click table row, verify loads into input fields (no preview action)
10. Generate and verify correct output

### Edge Cases

- Table row selection still works
- Clear Preview button still works for validation preview
- No crashes when using validation preview + generate

---

## Success Criteria

- [ ] "Preview All Positions" button removed
- [ ] "Click to preview" column removed from position table
- [ ] `preview_requested` and `preview_all_requested` signals removed
- [ ] Old preview handler methods removed from main_window.py
- [ ] "Validate & Preview" button works correctly
- [ ] Table row click loads position into input fields
- [ ] No crashes when using validation + generate
- [ ] Manual testing confirms clean workflow

---

## Reference Files

- `quickice/gui/custom_molecule_panel.py` - Contains old preview code
- `quickice/gui/main_window.py` - Contains old preview handlers
- Phase 34.5 implementation - Validate & Preview functionality
