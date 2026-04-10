---
status: investigating
trigger: "CRITICAL USER FEEDBACK: H-bond POSITIONS are wrong - bonds go to middle of hexagons, not O atoms"
created: 2026-04-10T19:30:00
updated: 2026-04-10T20:10:00
---

## Current Focus

hypothesis: H-bond LINE ENDPOINTS are calculated incorrectly - using geometric centers or wrong atom positions instead of actual H and O coordinates
test: Check how create_hbond_actor uses atom positions to draw lines, compare with v2.1.1
expecting: Find mismatch between H-bond data (H->O pairs) and how lines are drawn
next_action: Investigate create_hbond_actor endpoint calculation and compare with v2.1.1

## Symptoms

expected: H-bonds should connect H of one molecule to O of neighboring molecule (proper Ih hexagonal network)
actual: H-bonds form rectangular grid pattern, bonds go to "middle of hexagons" (center of 6-membered rings) instead of O atoms
errors: Wrong H-bond POSITIONS - geometry is incorrect, not a style issue
reproduction: Load ice Ih in tab 1, toggle H-bonds
started: v2.1.1 has minor issue but "much better than current"

## Eliminated

- hypothesis: Custom bond actors in MolecularViewerWidget were causing issues
  evidence: Code reverted to v2.1.1 approach (RenderBondsOff, _bond_actor, _extract_bonds removed)
  timestamp: 2026-04-10T19:25:00

## Evidence

- timestamp: 2026-04-10T20:15:00
  checked: detect_hydrogen_bonds() lines 252-255 in vtk_utils.py
  found: Function returns RAW positions (h_pos, o_pos), not minimum-image corrected positions
  implication: H-bonds crossing periodic boundaries are detected correctly but drawn to wrong positions

- timestamp: 2026-04-10T20:16:00
  checked: v2.1.1 version of detect_hydrogen_bonds
  found: v2.1.1 did NOT use PBC at all - calculated distance as np.linalg.norm(h_pos - o_pos)
  implication: v2.1.1 only detected H-bonds within same image, but positions were correct. dee7802 added PBC distance but forgot to correct positions for drawing.

- timestamp: 2026-04-10T19:30:00
  checked: Current molecular_viewer.py state
  found: RenderBondsOff, _bond_actor, _extract_bonds NOT found (fix applied). SetBondRadius present at lines 141, 252, 263, 274.
  implication: The fix was applied correctly. But user still sees "long dash" lines.

- timestamp: 2026-04-10T19:32:00
  checked: VTK RenderLattice default setting
  found: RenderLattice: True is the default for vtkMoleculeMapper
  implication: VTK is rendering the unit cell wireframe by default. Could this appear as "long dash" lines?

- timestamp: 2026-04-10T19:33:00
  checked: create_hbond_actor dash parameters (vtk_utils.py lines 286-287)
  found: num_dashes = 8, dash_ratio = 0.5 (creates 4 dashes per line)
  implication: H-bonds should appear as "short dotted" lines (8 segments, 4 visible dashes). "Long dash" must come from elsewhere.

- timestamp: 2026-04-10T19:40:00
  checked: VTK MoleculeMapper RenderLattice setting
  found: RenderLattice: True (default), renders unit cell as white wireframe
  implication: Unit cell wireframe appears as SOLID white lines (not dashed). Cannot be "long dash" inter-molecular bonds.

- timestamp: 2026-04-10T19:42:00
  checked: VTK covalent bond rendering
  found: VTK renders bonds as 3D cylinders (not lines), solid tubes with no dash pattern
  implication: Covalent bonds (O-H within molecules) appear as solid 3D cylinders, not "long dash" lines.

- timestamp: 2026-04-10T19:45:00
  checked: H-bond detection on real ice Ih structure (16 molecules)
  found: 32 H-bonds detected (2 per molecule, correct), all distances 0.18-0.19 nm, none > 0.22 nm
  implication: H-bond detection logic is CORRECT. No spurious long-distance bonds detected.

## Resolution

root_cause: detect_hydrogen_bonds() returned raw atom positions without minimum-image correction. When H-bonds cross periodic boundaries, the line was drawn to the wrong periodic image of O (across the box instead of to the nearest neighbor).
fix: Added _pbc_min_image_position() helper function and modified detect_hydrogen_bonds() to return the minimum-image corrected O position for each H-bond, ensuring lines are drawn to the nearest periodic image.
verification: Verified with test case - all 8 H-bonds detected with correct distances (~0.224nm), lines drawn to minimum-image positions. All existing tests pass.
files_changed: [quickice/gui/vtk_utils.py]
