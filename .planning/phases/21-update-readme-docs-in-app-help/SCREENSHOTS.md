# Screenshots Needed for v3.0 Documentation

**Created:** 2026-04-09
**Status:** Pending capture
**Location:** docs/images/

---

## Priority 1: Essential (for README.md)

### 1. quickice-v3-gui.png
**Purpose:** Replace quickice-gui.png with v3.0 showing two tabs
**Content:**
- Full QuickIce window
- Both tabs visible in tab bar: "Ice Generation" and "Interface Construction"
- Phase diagram visible in Tab 1
- Dual viewport visible

**Dimensions:** ~1200x800 px
**Used in:** README.md line 85 (replace existing reference)

---

## Priority 2: Important (for gui-guide.md Tab 2 section)

### 2. tab2-slab-interface.png
**Purpose:** Show generated slab interface in Tab 2 viewer
**Content:**
- Tab 2 selected (Interface Construction tab)
- Slab mode interface generated
- 3D viewer showing phase-distinct colors (ice=cyan, water=cornflower blue)
- Unit cell boundary box visible
- Report panel showing generation results

**Dimensions:** ~1000x700 px
**Used in:** gui-guide.md "Interface Construction (Tab 2)" section

---

### 3. tab2-pocket-interface.png
**Purpose:** Show pocket mode water cavity
**Content:**
- Tab 2 with Pocket mode selected
- Generated pocket interface visible
- Water cavity (cornflower blue) inside ice matrix (cyan)
- Cross-section view preferred if possible

**Dimensions:** ~1000x700 px
**Used in:** gui-guide.md "Interface Modes" section

---

### 4. tab2-piece-interface.png
**Purpose:** Show piece mode ice crystal in water
**Content:**
- Tab 2 with Piece mode selected
- Ice crystal (cyan) embedded in water box (cornflower blue)
- Shows dimensions derived from candidate

**Dimensions:** ~1000x700 px
**Used in:** gui-guide.md "Interface Modes" section

---

## Priority 3: Helpful (for gui-guide.md configuration section)

### 5. tab2-controls-slab.png
**Purpose:** Show Tab 2 configuration controls for Slab mode
**Content:**
- Tab 2 control panel
- Mode dropdown showing "Slab" selected
- Box dimension inputs
- Ice thickness and Water thickness inputs visible
- Seed input

**Dimensions:** ~400x600 px (control panel only)
**Used in:** gui-guide.md "Mode-Specific Parameters > Slab Parameters" section

---

### 6. tab2-controls-pocket.png
**Purpose:** Show Tab 2 configuration controls for Pocket mode
**Content:**
- Tab 2 control panel
- Mode dropdown showing "Pocket" selected
- Pocket diameter input visible
- Shape selector visible

**Dimensions:** ~400x500 px (control panel only)
**Used in:** gui-guide.md "Mode-Specific Parameters > Pocket Parameters" section

---

### 7. tab2-controls-piece.png
**Purpose:** Show Tab 2 configuration controls for Piece mode
**Content:**
- Tab 2 control panel
- Mode dropdown showing "Piece" selected
- Informational label showing candidate dimensions
- No extra parameter inputs (derived)

**Dimensions:** ~400x400 px (control panel only)
**Used in:** gui-guide.md "Mode-Specific Parameters > Piece Parameters" section

---

## Priority 4: Nice to Have

### 8. export-interface-menu.png
**Purpose:** Show Ctrl+I export menu action
**Content:**
- File menu dropdown
- "Export for GROMACS..." (Tab 1) visible
- Separator
- "Export Interface for GROMACS..." (Tab 2) visible
- Shortcut hints (Ctrl+G, Ctrl+I)

**Dimensions:** ~300x200 px (menu only)
**Used in:** gui-guide.md "Export for GROMACS" section

---

### 9. help-dialog-v3.png
**Purpose:** Show updated help dialog with Tab 2 workflow
**Content:**
- Help → Quick Reference dialog
- Tab 1 and Tab 2 workflow steps visible
- Mode descriptions visible in Tab 2 steps

**Dimensions:** ~500x400 px
**Used in:** gui-guide.md or help documentation

---

## Capture Instructions

### Prerequisites
1. Launch QuickIce: `python -m quickice`
2. Generate ice candidates in Tab 1 (Ice Ih, 250K, 1 atm, 1000 molecules recommended)
3. Switch to Tab 2

### For Slab Interface Screenshot
1. Tab 2 → Mode: Slab
2. Box: 5.0 nm
3. Ice thickness: 2.0 nm
4. Water thickness: 3.0 nm
5. Seed: 42
6. Generate Interface
7. Wait for completion
8. Take screenshot of full window or 3D viewer area

### For Pocket Interface Screenshot
1. Tab 2 → Mode: Pocket
2. Box: 5.0 nm
3. Pocket diameter: 2.0 nm
4. Seed: 42
5. Generate Interface
6. Take screenshot

### For Piece Interface Screenshot
1. Tab 2 → Mode: Piece
2. Box: 6.0 nm
3. Seed: 42
4. Generate Interface
5. Take screenshot

### For Control Panel Screenshots
1. Switch to desired mode
2. Crop screenshot to show only control panel (left side)
3. Ensure all inputs are visible and tooltips readable if needed

---

## Image Format

- **Format:** PNG (lossless)
- **Naming:** lowercase-with-hyphens.png
- **Location:** docs/images/
- **Max file size:** Aim for < 200KB per image (optimize if larger)

---

## After Capture

1. Add images to `docs/images/`
2. Reference in gui-guide.md using relative path: `images/filename.png`
3. Update README.md main screenshot reference if replacing quickice-gui.png
4. Commit with: `git add docs/images/*.png && git commit -m "docs: add v3.0 Tab 2 screenshots"`

---

## Summary

| Priority | Screenshot | Purpose |
|----------|------------|---------|
| 1 | quickice-v3-gui.png | Main README image (two tabs visible) |
| 2 | tab2-slab-interface.png | Slab mode visualization |
| 2 | tab2-pocket-interface.png | Pocket mode visualization |
| 2 | tab2-piece-interface.png | Piece mode visualization |
| 3 | tab2-controls-slab.png | Slab configuration inputs |
| 3 | tab2-controls-pocket.png | Pocket configuration inputs |
| 3 | tab2-controls-piece.png | Piece configuration (info label) |
| 4 | export-interface-menu.png | Ctrl+I menu action |
| 4 | help-dialog-v3.png | Updated help dialog |

**Total:** 9 screenshots
**Essential:** 1 (main GUI)
**Important:** 3 (three modes visualization)
**Helpful:** 3 (control panels)
**Nice to have:** 2 (export menu, help dialog)

---

*Created: 2026-04-09*
