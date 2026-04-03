# Screenshots Checklist for Phase 13 Documentation

**Created:** 2026-04-03
**Status:** Ready for user to capture
**Directory:** `docs/images/`

---

## Screenshots Required

| # | Filename | Location | What to Show |
|---|----------|----------|--------------|
| 1 | `quickice-gui.png` | README.md (line 84), docs/gui-guide.md (line 37) | Main GUI window with phase diagram and 3D viewer showing generated structure |
| 2 | `phase-diagram.png` | docs/gui-guide.md (line 90) | Interactive phase diagram with clickable regions, marker visible |
| 3 | `3d-viewer.png` | docs/gui-guide.md (line 123) | Single viewport showing ice structure with ball-and-stick representation |
| 4 | `dual-viewport.png` | docs/gui-guide.md (line 126) | Dual viewport comparison showing two candidate structures side-by-side |
| 5 | `export-menu.png` | docs/gui-guide.md (line 152) | File menu dropdown showing export options (Save PDB, Save Diagram, Save Viewport) |

---

## Screenshot Details

### 1. quickice-gui.png (Hero Screenshot)

**Purpose:** Main showcase image for README and GUI guide introduction

**What to capture:**
- Full QuickIce GUI window
- Left panel: Phase diagram with a selected point (marker visible)
- Right panel: Input fields populated, 3D viewer showing generated ice structure
- Window title bar visible
- Progress bar not visible (structure already generated)

**Tips:**
- Use realistic values: T=250K, P=1000 bar, molecules=96
- Generate an Ice Ih or Ice Ic structure (common, renders well)
- Position window at reasonable size (not maximized, not too small)
- Use screenshot tool that captures window decorations (title bar, borders)

**Where it appears:**
- README.md line 84: Hero image after GUI Usage section
- docs/gui-guide.md line 37: Getting Started section

---

### 2. phase-diagram.png

**Purpose:** Show interactive phase diagram feature

**What to capture:**
- Phase diagram canvas only (not entire GUI window)
- All 12 ice phases + liquid + vapor regions visible
- Click marker at a selected T,P point
- Axis labels visible (Temperature K, Pressure bar)
- Phase labels visible (Ice Ih, Ice II, etc.)

**Tips:**
- Click on a clear ice phase region (Ice Ih at ~250K, 1000 bar)
- Ensure marker is visible (red cross or circle)
- Crop to diagram canvas only (remove splitter, input panel)
- High enough resolution to read phase labels

**Where it appears:**
- docs/gui-guide.md line 90: Interactive Phase Diagram section

---

### 3. 3d-viewer.png

**Purpose:** Show molecular visualization capabilities

**What to capture:**
- Single 3D viewport (not dual viewport)
- Ball-and-stick representation (default)
- Oxygen atoms red, hydrogen atoms white
- H-bonds visible as dashed lines (toggle on)
- Good viewing angle (rotated to show structure clearly)

**Tips:**
- Use same structure as hero screenshot (consistent)
- Rotate to show interesting angle (not default front view)
- Enable H-bonds (dashed lines)
- Disable unit cell wireframe (cleaner image)
- Capture just the 3D viewport, not entire window

**Where it appears:**
- docs/gui-guide.md line 123: 3D Molecular Viewer section

---

### 4. dual-viewport.png

**Purpose:** Show candidate comparison feature

**What to capture:**
- Both viewports visible in split layout
- Left viewport: Rank #1 candidate (best score)
- Right viewport: Rank #2 candidate
- Different orientations (rotate each slightly differently)
- Candidate labels visible if shown in UI

**Tips:**
- Generate structure at conditions with multiple valid candidates (Ice Ih region)
- Rotate each viewport to different angle
- Ensure both structures are clearly visible
- Capture both viewports with the splitter

**Where it appears:**
- docs/gui-guide.md line 126: Dual Viewport Layout section

---

### 5. export-menu.png

**Purpose:** Show File menu export options

**What to capture:**
- File menu dropdown expanded
- All export actions visible:
  - Save PDB (left viewer)
  - Save PDB (right viewer)
  - Save Phase Diagram
  - Save Viewport Screenshot
- Menu shortcuts visible (Ctrl+S, Ctrl+D, etc.)
- Menu positioned over GUI (context visible)

**Tips:**
- Click File menu to expand dropdown
- Ensure all options are visible in screenshot
- Include keyboard shortcuts in capture
- Capture with GUI window as background (context)

**Where it appears:**
- docs/gui-guide.md line 152: Export Options section

---

## Screenshot Workflow

### Step 1: Prepare Environment

```bash
# Launch QuickIce GUI
python -m quickice.gui
```

### Step 2: Generate Test Structure

1. Set Temperature: 250 K
2. Set Pressure: 1000 bar
3. Set Molecule Count: 96
4. Click Generate (or press Enter)
5. Wait for generation to complete

### Step 3: Capture Screenshots

1. **quickice-gui.png** - Full window capture
2. **phase-diagram.png** - Crop to diagram canvas
3. **3d-viewer.png** - Single viewport with H-bonds
4. **dual-viewport.png** - Both viewports visible
5. **export-menu.png** - File menu dropdown

### Step 4: Save Screenshots

Save all screenshots to: `docs/images/`

```bash
docs/images/
├── .gitkeep
├── quickice-gui.png
├── phase-diagram.png
├── 3d-viewer.png
├── dual-viewport.png
└── export-menu.png
```

### Step 5: Verify Placement

After saving, verify documentation renders images correctly:

```bash
# Check README renders hero image
cat README.md | grep -A 1 "quickice-gui.png"

# Check gui-guide renders all images
cat docs/gui-guide.md | grep -A 1 "\.png"
```

---

## Screenshot Tools

### Linux

- **GNOME Screenshot:** `gnome-screenshot -a` (select area)
- **Spectacle (KDE):** `spectacle -r` (rectangular region)
- **Flameshot:** `flameshot gui` (annotation support)
- **Import (ImageMagick):** `import screenshot.png` (click window)

### macOS

- **Command+Shift+4:** Selection screenshot
- **Command+Shift+4+Space:** Window screenshot
- **Command+Shift+3:** Full screen

### Windows

- **Snipping Tool:** Built-in Windows tool
- **Snip & Sketch:** Win+Shift+S
- **Greenshot:** Third-party tool with annotations

---

## Image Format & Resolution

**Format:** PNG (lossless, clear text rendering)

**Resolution:**
- Minimum: 1280x720 for viewport screenshots
- Recommended: 1920x1080 for hero screenshot
- DPI: 96 (screen resolution)

**File size:**
- Target: 200-500 KB per image (compressed PNG)
- Use PNG compression tools if files are large:
  ```bash
  # Optimize PNG (if needed)
  optipng -o7 docs/images/*.png
  ```

---

## After Screenshots Captured

Once all screenshots are saved to `docs/images/`:

1. **Git add and commit:**
   ```bash
   git add docs/images/*.png
   git commit -m "docs(13): add GUI screenshots for documentation"
   ```

2. **Update TODO comments** (optional):
   - README.md line 87: Remove/update TODO about standalone executable
   - docs/gui-guide.md line 21: Remove/update TODO

3. **Proceed to Phase 12** (Packaging):
   - Screenshots will be included in standalone distribution
   - Documentation is now complete with visual references

---

## Checklist

Use this checklist to track screenshot capture progress:

- [ ] `quickice-gui.png` - Main GUI window with phase diagram and 3D viewer
- [ ] `phase-diagram.png` - Phase diagram canvas with marker
- [ ] `3d-viewer.png` - Single viewport with ball-and-stick and H-bonds
- [ ] `dual-viewport.png` - Side-by-side candidate comparison
- [ ] `export-menu.png` - File menu dropdown with export options

---

*Created for Phase 13 - Update README and Documentation*
*Screenshots to be captured after Phase 13, before/during Phase 12 packaging*
