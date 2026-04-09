# Deferred UAT Testing: v3.0 Interface Generation

**Created:** 2026-04-09
**Status:** Pending execution
**Purpose:** Comprehensive GUI testing for all v3.0 phases after milestone completion

---

## Overview

This document contains all manual GUI tests for v3.0 phases. Phase 16 passed UAT. Phases 17-21 require testing after all phases are complete.

**Phase Status:**
| Phase | VERIFICATION | UAT |
|-------|--------------|-----|
| 16 Tab Infrastructure | ✓ passed (8/8) | ✓ complete (5/6, 1 minor) |
| 17 Configuration Controls | ✓ passed (12/12) | ⏳ DEFERRED |
| 18 Structure Generation | ✓ passed (7/7) | ⏳ DEFERRED |
| 19 Visualization | ✓ passed (9/9) | ⏳ DEFERRED |
| 20 Export | ✓ passed (12/12) | ⏳ DEFERRED |
| 21 Documentation | ⏳ Pending | ⏳ DEFERRED |

---

## Phase 17: Configuration Controls

**Goal:** Users can configure interface generation parameters through intuitive UI controls

**Requirements:** CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06

### Tests

#### 1. Mode Selection Dropdown
**Steps:**
1. Launch QuickIce: `python -m quickice`
2. Switch to "Interface Construction" tab (Tab 2)
3. Locate the mode dropdown (labeled "Mode:" or similar)

**Expected:**
- Dropdown shows three options: "Slab", "Pocket", "Piece"
- Default selection is "Slab"
- Clicking dropdown reveals all three modes

**Status:** ⏳ Pending

---

#### 2. Mode-Specific Input Panels
**Steps:**
1. Select "Slab" mode
2. Observe visible input fields
3. Select "Pocket" mode
4. Observe visible input fields
5. Select "Piece" mode
6. Observe visible input fields

**Expected:**
- **Slab mode:** Ice thickness input, Water thickness input visible
- **Pocket mode:** Pocket diameter input, Shape selector (sphere) visible
- **Piece mode:** Informational label showing candidate dimensions, no extra inputs needed

**Status:** ⏳ Pending

---

#### 3. Box Size Input Validation
**Steps:**
1. Enter "5.0" in box size field
2. Clear and enter "0.3" (below minimum)
3. Clear and enter "150" (above maximum)
4. Clear and enter "abc" (non-numeric)
5. Clear and enter "5.5" (valid)

**Expected:**
- Valid range: 0.5 - 100 nm
- Below minimum: Shows validation error or red border
- Above maximum: Shows validation error or red border
- Non-numeric: Input rejected or shows error
- Valid values accepted without error

**Status:** ⏳ Pending

---

#### 4. Slab Mode Thickness Inputs
**Steps:**
1. Select "Slab" mode
2. Enter ice thickness: "2.0"
3. Enter water thickness: "3.0"
4. Try invalid values (negative, too large, non-numeric)

**Expected:**
- Both inputs accept values in 0.5-50 nm range
- Validation errors shown for out-of-range values
- Valid values accepted

**Status:** ⏳ Pending

---

#### 5. Pocket Mode Inputs
**Steps:**
1. Select "Pocket" mode
2. Enter pocket diameter: "2.5"
3. Observe shape selector

**Expected:**
- Diameter input accepts 0.5-50 nm range
- Shape selector shows "Sphere" option
- (v3.0: Ellipse not implemented, only sphere available)

**Status:** ⏳ Pending

---

#### 6. Piece Mode Informational Display
**Steps:**
1. Generate ice candidates in Tab 1
2. Select a candidate (note its dimensions)
3. Switch to Tab 2
4. Select "Piece" mode
5. Observe the informational label

**Expected:**
- Label shows dimensions derived from selected candidate
- Example: "Ice dimensions: X × Y × Z nm"
- No manual dimension inputs (derived automatically)

**Status:** ⏳ Pending

---

#### 7. Random Seed Input
**Steps:**
1. Locate seed input field
2. Enter "42"
3. Try "0" (below minimum)
4. Try "1000000" (above maximum)
5. Try "abc" (non-numeric)

**Expected:**
- Valid range: 1 - 999999
- Out-of-range values show validation error
- Non-numeric input rejected
- Valid integer accepted

**Status:** ⏳ Pending

---

#### 8. Tooltips
**Steps:**
1. Hover over each input control
2. Read tooltip text

**Expected:**
- Each input has descriptive tooltip
- Mode selector: Explains geometry types
- Box size: "Simulation box dimensions in nanometers"
- Thickness/diameter: Explains layer/cavity size
- Seed: "Random seed for reproducible generation"

**Status:** ⏳ Pending

---

#### 9. Generate Button Enable/Disable
**Steps:**
1. With no candidate selected, observe Generate button
2. Select a candidate from dropdown
3. Observe Generate button

**Expected:**
- Generate button disabled when no candidate selected
- Generate button enabled when candidate selected
- Button shows enabled/disabled state clearly

**Status:** ⏳ Pending

---

## Phase 18: Structure Generation

**Goal:** Interface structures are correctly generated with ice and water phases assembled according to mode

**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, GEN-07

### Tests

#### 1. Slab Mode Generation
**Steps:**
1. Generate ice candidates in Tab 1 (Ice Ih, 1 atm, 250K)
2. Switch to Tab 2
3. Select candidate from dropdown (e.g., "Rank 1 (ice_Ih)")
4. Configure: Mode=Slab, Box=5.0 nm, Ice thickness=2.0 nm, Water thickness=3.0 nm, Seed=42
5. Click "Generate Interface"
6. Wait for generation to complete

**Expected:**
- Progress panel shows generation steps
- No errors during generation
- Completion message shows
- Report shows:
  - Total atoms generated
  - Ice atom count
  - Water atom count
  - Box dimensions
- Ice atoms + water atoms = total atoms

**Status:** ⏳ Pending

---

#### 2. Pocket Mode Generation
**Steps:**
1. Select a candidate
2. Configure: Mode=Pocket, Box=5.0 nm, Pocket diameter=2.0 nm, Seed=42
3. Click "Generate Interface"
4. Wait for completion

**Expected:**
- Generation completes without error
- Water cavity created inside ice matrix
- Report shows ice atoms (matrix) and water atoms (cavity)
- Cavity size approximately matches requested diameter

**Status:** ⏳ Pending

---

#### 3. Piece Mode Generation
**Steps:**
1. Select a candidate (note its dimensions from Tab 1)
2. Configure: Mode=Piece, Box=6.0 nm, Seed=42
3. Click "Generate Interface"
4. Wait for completion

**Expected:**
- Ice piece dimensions derived from candidate
- Ice crystal embedded in water box
- Report shows ice atoms and surrounding water atoms
- Box dimensions match configuration

**Status:** ⏳ Pending

---

#### 4. Collision Detection (Overlap Resolution)
**Steps:**
1. Configure Slab mode with small box (forces overlap)
2. Use: Box=3.0 nm, Ice thickness=2.0 nm, Water thickness=2.0 nm
3. Generate
4. Check report for overlap resolution info

**Expected:**
- Generation succeeds
- Water atoms near ice boundary removed
- No error about atom overlap
- Report may mention atoms removed for collision

**Status:** ⏳ Pending

---

#### 5. Generation Without Candidate
**Steps:**
1. Clear candidate selection (or don't select one)
2. Click "Generate Interface"

**Expected:**
- Generation does not start
- Error message shown: "Please select an ice candidate first"
- Or: Generate button disabled

**Status:** ⏳ Pending

---

#### 6. Invalid Parameter Prevention
**Steps:**
1. Select a candidate
2. Enter invalid box size (e.g., 0.3)
3. Try to click Generate

**Expected:**
- Generate button disabled or
- Error message shown on click
- Generation does not proceed with invalid parameters

**Status:** ⏳ Pending

---

#### 7. Reproducibility with Seed
**Steps:**
1. Generate with Seed=42
2. Note the atom counts
3. Generate again with same configuration and Seed=42
4. Compare atom counts

**Expected:**
- Same seed produces identical results
- Atom counts match between runs
- (Different seeds should produce different water arrangements)

**Status:** ⏳ Pending

---

#### 8. Progress Panel Updates
**Steps:**
1. Start generation
2. Observe progress panel during generation

**Expected:**
- Progress shows current step
- Status messages update as generation proceeds
- Completion message shows when done
- Elapsed time displayed

**Status:** ⏳ Pending

---

#### 9. Report Panel Content
**Steps:**
1. Generate a structure
2. Observe report panel after completion

**Expected:**
- Report shows:
  - Mode used (Slab/Pocket/Piece)
  - Box dimensions
  - Total atoms
  - Ice atoms count
  - Water atoms count
  - Seed used
  - Generation time
  - Any collision resolution details

**Status:** ⏳ Pending

---

## Phase 19: Visualization

**Goal:** Users can view interface structures in 3D with clear visual distinction between ice and water phases

**Requirements:** VIS-01, VIS-02, VIS-03, VIS-04

### Tests

#### 1. Placeholder Display
**Steps:**
1. Launch QuickIce
2. Switch to Tab 2 before generating any structure
3. Observe the viewer area

**Expected:**
- Placeholder text visible: "Generate a structure to visualize"
- Text is centered
- Background is light gray
- No 3D viewer visible yet

**Status:** ⏳ Pending

---

#### 2. Placeholder During Generation
**Steps:**
1. Start interface generation
2. Observe viewer area while generation is running

**Expected:**
- Placeholder remains visible during generation
- Viewer appears only AFTER generation completes
- (Not: empty viewer during generation)

**Status:** ⏳ Pending

---

#### 3. 3D Viewer Appears After Generation
**Steps:**
1. Generate an interface structure (any mode)
2. Wait for completion
3. Observe viewer area

**Expected:**
- Placeholder disappears
- 3D viewer appears automatically
- Structure is visible in the viewport
- Dark background in viewer

**Status:** ⏳ Pending

---

#### 4. Phase-Distinct Coloring (CRITICAL)
**Steps:**
1. Generate a slab interface (clear separation)
2. Observe the 3D structure
3. Identify ice region vs water region

**Expected:**
- **Ice atoms: CYAN** (light blue-green, RGB ~0.0, 0.8, 0.8)
- **Water atoms: CORNFLOWER BLUE** (medium blue, RGB ~0.39, 0.58, 0.93)
- Two colors are distinctly different
- Can clearly see ice region vs water region
- For slab: Ice layer(s) cyan, water layer blue

**Status:** ⏳ Pending

---

#### 5. Bond Rendering (Lines, Not Cylinders)
**Steps:**
1. Generate a structure
2. Zoom in on the structure (scroll wheel or right-click drag)
3. Observe bond appearance

**Expected:**
- Bonds appear as thin 2D lines
- NOT thick 3D cylinders or tubes
- Performance is smooth even with many bonds
- Lines connect O-H atoms within molecules

**Status:** ⏳ Pending

---

#### 6. Default Camera View (Z-Axis Side View)
**Steps:**
1. Generate a slab structure
2. Observe initial camera position
3. Identify vertical axis and stacking direction

**Expected:**
- Default view shows "side view"
- Z-axis is vertical (up-down on screen)
- Camera looks along Y-axis
- For slab mode: Ice and water layers visible as horizontal bands
- Stacking direction (Z) is clear

**Status:** ⏳ Pending

---

#### 7. Unit Cell Boundary Box
**Steps:**
1. Generate a structure
2. Observe the wireframe around the structure

**Expected:**
- Gray wireframe box visible
- Box matches box dimensions from configuration
- Box encompasses all atoms
- Box edges are clean lines, not solid

**Status:** ⏳ Pending

---

#### 8. 3D Mouse Interaction - Rotation
**Steps:**
1. Generate a structure
2. Left-click and drag in the viewer

**Expected:**
- Structure rotates following mouse movement
- Rotation is smooth
- Can rotate to any angle
- Atoms and bonds remain visible during rotation

**Status:** ⏳ Pending

---

#### 9. 3D Mouse Interaction - Pan
**Steps:**
1. Generate a structure
2. Middle-click and drag (or Shift+left-click drag depending on VTK setup)

**Expected:**
- Structure pans (moves) following mouse
- Can pan in any direction
- View stays centered where moved

**Status:** ⏳ Pending

---

#### 10. 3D Mouse Interaction - Zoom
**Steps:**
1. Generate a structure
2. Use scroll wheel (or right-click drag)

**Expected:**
- Scroll up: Zooms in (structure appears larger)
- Scroll down: Zooms out (structure appears smaller)
- Zoom is smooth
- Can zoom in to see individual atoms clearly
- Can zoom out to see entire box

**Status:** ⏳ Pending

---

#### 11. No Hydrogen Bonds Visible
**Steps:**
1. Generate a structure
2. Look for dashed lines between molecules (H-bonds)
3. Compare with Tab 1 viewer (if H-bonds are shown there)

**Expected:**
- NO hydrogen bond lines visible in Tab 2
- Only covalent O-H bonds visible (within molecules)
- H-bonds intentionally hidden (per CONTEXT: too messy with water)

**Status:** ⏳ Pending

---

#### 12. Performance with Large System
**Steps:**
1. Generate a large structure (Box=10nm, large thicknesses)
2. Observe rendering performance
3. Try rotating, zooming

**Expected:**
- Rendering is reasonably smooth
- No significant lag when rotating
- No freezing or crashing
- Line-based bonds help performance

**Status:** ⏳ Pending

---

#### 13. Tab Switching Preserves Viewer State
**Steps:**
1. Generate a structure in Tab 2
2. Rotate to a specific view
3. Switch to Tab 1
4. Switch back to Tab 2
5. Observe viewer state

**Expected:**
- Viewer still shows the generated structure
- Rotation/camera position preserved (Qt widget state)
- No need to regenerate

**Status:** ⏳ Pending

---

## Phase 20: Export

**Goal:** Users can export interface structures as GROMACS simulation files with phase distinction

**Requirements:** EXP-01, EXP-02, EXP-03

**Implementation notes (from VERIFICATION):**
- EXP-02 was OVERRIDDEN by CONTEXT: single SOL molecule type for both ice and water phases (no chain A/B distinction)
- Ice molecules normalized from 3-atom (O, H, H) to 4-atom TIP4P-ICE (OW, HW1, HW2, MW) at export time
- MW virtual site computed using α=0.13458335 (TIP4P-ICE specific)
- Ctrl+I shortcut for interface export (separate from Ctrl+G for Tab 1)

### Tests

#### 1. Export Menu Action and Ctrl+I Shortcut
**Steps:**
1. Generate an interface structure (any mode)
2. Open File menu
3. Locate "Export Interface for GROMACS..." action
4. Press Ctrl+I

**Expected:**
- File menu shows "Export Interface for GROMACS..." below a separator after "Export for GROMACS..." (Tab 1 action)
- Ctrl+I triggers the same export action
- Ctrl+G (Tab 1 export) and Ctrl+I (Tab 2 export) do not conflict

**Status:** ⏳ Pending

---

#### 2. Export Save Dialog
**Steps:**
1. Generate a slab interface structure
2. Click File → "Export Interface for GROMACS..." (or Ctrl+I)
3. Observe save dialog

**Expected:**
- Dialog title: "Export Interface for GROMACS"
- Default filename: "interface_slab.gro" (mode-specific default)
- Filter: "GRO Files (*.gro);;All Files (*)"
- Can choose save location
- Can cancel without error

**Status:** ⏳ Pending

---

#### 3. GRO File Format and 4-Atom Normalization (CRITICAL)
**Steps:**
1. Generate a slab interface structure
2. Export via Ctrl+I
3. Open the .gro file in a text editor
4. Count atoms per molecule in ice section
5. Count atoms per molecule in water section

**Expected:**
- Valid GRO format with title line "Ice/water interface (slab) exported by QuickIce"
- Total atom count = (ice_nmolecules + water_nmolecules) × 4
- ALL molecules written as 4-atom TIP4P-ICE: OW, HW1, HW2, MW
- Ice molecules: MW positions computed (not zero or missing)
- Water molecules: MW positions already present (pass-through)
- Atom names: OW, HW1, HW2, MW (not O, H1, H2)
- Coordinates in nm
- Box dimensions at end match interface cell
- Residue numbering: continuous, ice 1..N_ice, water N_ice+1..N_ice+N_water
- All residues named "SOL"

**Status:** ⏳ Pending

---

#### 4. Single SOL Molecule Type (CRITICAL — Context Override)
**Steps:**
1. Export an interface structure
2. Open .gro file
3. Examine residue names for all atoms
4. Open .top file
5. Examine [molecules] section

**Expected:**
- NO chain identifiers (no chain A/B) — CONTEXT explicitly overrides original EXP-02
- ALL residues named "SOL" (both ice and water phases)
- .top [molecules] section has SINGLE entry: `SOL    {combined_count}`
- Combined count = ice_nmolecules + water_nmolecules
- NOT split into SOL_ice / SOL_water or separate molecule types

**Status:** ⏳ Pending

---

#### 5. TOP File Content
**Steps:**
1. Export an interface structure
2. Open .top file in text editor
3. Examine content

**Expected:**
- Header: "; Generated by QuickIce" with "TIP4P-ICE water model" and "Ice/water interface structure"
- [defaults] section present
- [atomtypes] section present (OW, HW, MW)
- [moleculetype] section: name "SOL", nrexcl = 3
- [atoms] section: 4 atoms (OW, HW1, HW2, MW) with TIP4P-ICE parameters
- [settles] section present
- [virtual_sites3] section with α = 0.13458335
- [exclusions] section present
- [system] name: "Ice/water interface ({mode}) exported by QuickIce"
- [molecules]: SINGLE `SOL    {N}` where N = ice + water count
- `#include "interface_{mode}.itp"` reference

**Status:** ⏳ Pending

---

#### 6. ITP File Content
**Steps:**
1. Export an interface structure
2. Open .itp file in text editor
3. Compare with Tab 1's TIP4P-ICE .itp

**Expected:**
- ITP file is IDENTICAL to Tab 1's TIP4P-ICE force field file
- Copied from bundled quickice/data/tip4p-ice.itp
- Defines OW, HW1, HW2, MW atom types
- Applies to both ice and water molecules (same model)

**Status:** ⏳ Pending

---

#### 7. Export Without Generation (No Crash)
**Steps:**
1. Launch app
2. Do NOT generate any interface structure
3. Press Ctrl+I or click File → "Export Interface for GROMACS..."

**Expected:**
- Warning dialog appears: "No Interface" / "Generate an interface structure first."
- No crash, no exception
- Dialog dismissed cleanly

**Status:** ⏳ Pending

---

#### 8. Export Success Dialog
**Steps:**
1. Generate an interface structure
2. Export via Ctrl+I
3. Choose save location
4. Observe success dialog

**Expected:**
- Information dialog: "Export Complete"
- Shows: "Water model: TIP4P-ICE (Abascal et al. 2005, DOI: 10.1063/1.1931662)"
- Shows: Ice molecules count, Water molecules count, Total count
- Shows: Files generated — interface_{mode}.gro, .top, .itp

**Status:** ⏳ Pending

---

#### 9. Help Dialog Ctrl+I Shortcut
**Steps:**
1. Open Help → Quick Reference (or equivalent)
2. Look for Ctrl+I in shortcuts list
3. Look for Tab 2 workflow steps

**Expected:**
- Shortcuts section lists "Ctrl+I — Export interface for GROMACS"
- Workflow section includes "Tab 2 — Interface Construction" steps
- Step 9: "Export interface for GROMACS (Ctrl+I)"
- Important notes: "Interface GROMACS export uses same TIP4P-ICE model for both ice and water"

**Status:** ⏳ Pending

---

#### 10. Mode-Specific Default Filename
**Steps:**
1. Generate a POCKET mode interface
2. Press Ctrl+I
3. Observe default filename
4. Cancel
5. Generate a PIECE mode interface
6. Press Ctrl+I
7. Observe default filename

**Expected:**
- Pocket mode: default filename "interface_pocket.gro"
- Piece mode: default filename "interface_piece.gro"
- Each mode gets its own default filename

**Status:** ⏳ Pending

---

## Phase 21: Documentation

**Goal:** Updated documentation for v3.0 features

### Tests

#### 1. README Updates
**Steps:**
1. Open README.md
2. Check for v3.0 interface generation documentation

**Expected:**
- Interface generation feature documented
- Two-tab workflow explained
- Three modes (slab, pocket, piece) described
- Export functionality documented

**Status:** ⏳ Pending (after Phase 21 execution)

---

#### 2. In-App Help
**Steps:**
1. Launch QuickIce
2. Look for Help menu or help button
3. Access help content

**Expected:**
- Help menu or button accessible
- Help content includes v3.0 features
- Interface construction workflow explained
- Mode descriptions available

**Status:** ⏳ Pending (after Phase 21 execution)

---

#### 3. Tab 2 Tooltip Help
**Steps:**
1. Switch to Tab 2
2. Hover over each control
3. Read tooltips

**Expected:**
- Each input has helpful tooltip
- Mode selector explains geometry types
- Box size, thickness, diameter explained
- Seed explains reproducibility purpose

**Status:** ⏳ Pending (after Phase 21 execution)

---

## Test Execution Log

After completing all phases, run these tests and record results below:

### Phase 17 Results
| Test | Result | Notes |
|------|--------|-------|
| 1. Mode Selection | ⏳ | |
| 2. Mode-Specific Panels | ⏳ | |
| 3. Box Size Validation | ⏳ | |
| 4. Slab Thickness Inputs | ⏳ | |
| 5. Pocket Inputs | ⏳ | |
| 6. Piece Mode Display | ⏳ | |
| 7. Seed Input | ⏳ | |
| 8. Tooltips | ⏳ | |
| 9. Generate Button State | ⏳ | |

### Phase 18 Results
| Test | Result | Notes |
|------|--------|-------|
| 1. Slab Mode Generation | ⏳ | |
| 2. Pocket Mode Generation | ⏳ | |
| 3. Piece Mode Generation | ⏳ | |
| 4. Collision Detection | ⏳ | |
| 5. No Candidate Error | ⏳ | |
| 6. Invalid Parameter Prevention | ⏳ | |
| 7. Seed Reproducibility | ⏳ | |
| 8. Progress Panel | ⏳ | |
| 9. Report Panel | ⏳ | |

### Phase 19 Results
| Test | Result | Notes |
|------|--------|-------|
| 1. Placeholder Display | ⏳ | |
| 2. Placeholder During Generation | ⏳ | |
| 3. Viewer Appears | ⏳ | |
| 4. Phase Colors (CRITICAL) | ⏳ | |
| 5. Line Bonds | ⏳ | |
| 6. Z-Axis Camera | ⏳ | |
| 7. Unit Cell Box | ⏳ | |
| 8. Rotation | ⏳ | |
| 9. Pan | ⏳ | |
| 10. Zoom | ⏳ | |
| 11. No H-Bonds | ⏳ | |
| 12. Large System Performance | ⏳ | |
| 13. Tab Switching | ⏳ | |

### Phase 20 Results
| Test | Result | Notes |
|------|--------|-------|
| 1. Menu Action + Ctrl+I | ⏳ | |
| 2. Save Dialog | ⏳ | |
| 3. GRO Format + 4-atom Normalization (CRITICAL) | ⏳ | |
| 4. Single SOL Type (CRITICAL — override) | ⏳ | No chain A/B per CONTEXT override |
| 5. TOP File Content | ⏳ | |
| 6. ITP File Content | ⏳ | |
| 7. Export Without Generation | ⏳ | |
| 8. Success Dialog | ⏳ | |
| 9. Help Dialog Ctrl+I | ⏳ | |
| 10. Mode-Specific Default Filename | ⏳ | |

### Phase 21 Results
| Test | Result | Notes |
|------|--------|-------|
| 1. README | ⏳ | |
| 2. In-App Help | ⏳ | |
| 3. Tab 2 Tooltips | ⏳ | |

---

## Summary Template

After all tests complete, fill in:

**Total Tests:** [N]
**Passed:** [N]
**Failed:** [N]
**Skipped:** [N]

**Critical Issues:**
- [List any failed CRITICAL tests]

**Minor Issues:**
- [List any other failed tests]

**Recommendations:**
- [Next steps based on test results]

---

*Created: 2026-04-09*
*To be executed: After Phase 21 completion*
