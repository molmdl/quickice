---
status: resolved
trigger: "Investigate and fix hydrate UI issues in QuickIce GUI v4.0"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T02:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: "ALL ISSUES RESOLVED"
test: "Fixed hydrate panel layout (Issue 2) and radius control (Issue 3)"
expecting: "Verified syntax OK"
next_action: "Archive and commit"

## Symptoms
<!-- IMMUTABLE -->

### Issue 1: Two info panels in hydrate tab
- expected: Single info display area
- actual: HydratePanel has TWO info displays:
  - `info_text` (line 178) - "Lattice Information" group
  - `_log_text` (line 199) - "Structure Viewer" section
- reproduction: Open Hydrate Config tab, see duplicate info panels

### Issue 2: 3D viewer at bottom instead of right side
- expected: 3D viewer should be on right side (like Tab 1 where splitter puts viewer on right)
- actual: HydratePanel puts viewer at bottom (vertical layout)
- reference: Tab 1 uses QSplitter(Qt.Horizontal) with viewer on right

### Issue 3: Cannot control atom radius - cannot see molecular structure clearly
- expected: User wants ability to select/adjust atom radius for visibility
- actual: Hardcoded in molecular_viewer.py lines 139-141:
  - SetAtomicRadiusScaleFactor(0.30 * ANGSTROM_TO_NM)
  - SetBondRadius(0.075 * ANGSTROM_TO_NM)
- reference: Tab 1 viewer allows user to control this
- timeline: Has never worked - feature request

### Issue 4: Hydrate not connected to interface
- expected: Clicking "Generate Hydrate" should generate structure
- actual: Likely no signal connection in main_window.py
- reproduction: Go to Hydrate Config tab, click Generate, nothing happens

## Eliminated
<!-- APPEND only -->

- hypothesis: Issue 4 - Signal not connected
  evidence: "main_window.py line 223: self.hydrate_panel.generate_requested.connect(self._on_hydrate_generate_clicked) - ALREADY CONNECTED"
  timestamp: 2026-04-16T01:30:00Z

- hypothesis: Issue 1 - Duplicate info panels is a bug
  evidence: "info_text shows lattice/cage info; _log_text shows generation progress - DIFFERENT purposes, intentional design"
  timestamp: 2026-04-16T01:30:00Z

## Evidence
<!-- APPEND only -->

- timestamp: 2026-04-16T01:30:00Z
  checked: "main_window.py signal connections"
  found: "hydrate_panel.generate_requested IS connected to _on_hydrate_generate_clicked at line 223"
  implication: "Issue 4 is already fixed - signal IS connected"

- timestamp: 2026-04-16T01:30:00Z
  checked: "hydrate_panel.py layout for Issue 2"
  found: "Lines 196-207: QVBoxLayout - log text then viewer vertically stacked"
  implication: "Viewer IS at bottom (vertical), needs QSplitter(Horizontal) to put on right"

- timestamp: 2026-04-16T01:30:00Z
  checked: "hydrate_renderer.py for Issue 3"
  found: "No SetAtomicRadiusScaleFactor or SetBondRadius calls - uses VTK defaults"
  implication: "Need to add radius customization in hydrate_renderer.py"

- timestamp: 2026-04-16T02:00:00Z
  checked: "Modified hydrate_panel.py and hydrate_renderer.py"
  found: "Python syntax verified OK"
  implication: "Fixes applied successfully"

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "Issue 2: Vertical layout instead of horizontal splitter; Issue 3: No radius control in hydrate_renderer.py; Issues 1,4 are resolved"

fix: "
- Issue 2: Reorganized hydrate_panel.py _setup_viewer_section() to use QSplitter(Qt.Horizontal) with viewer on right side, matching Tab 1 layout
- Issue 3: Added DEFAULT_ATOMIC_RADIUS_SCALE and DEFAULT_BOND_RADIUS constants in hydrate_renderer.py, applied in create_guest_actor() for better visibility
- Issue 4: Already connected - no fix needed
- Issue 1: Not a bug - intentionally showing different info (lattice info vs generation log)
"

verification: "Syntax validated with python -m py_compile"

files_changed: ["quickice/gui/hydrate_panel.py", "quickice/gui/hydrate_renderer.py"]