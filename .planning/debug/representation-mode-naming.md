---
status: resolved
trigger: "Naming is confusing. \"Ball-and-stick\" looks like space-filling VDW, \"sticks\" looks like space-filling VDW with smaller radius. Need to investigate what VTK actually renders for each mode and suggest proper naming."
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - Both modes render VDW spheres at different scales, not traditional ball-and-stick or stick geometry. The naming is misleading.
test: Analyzed VTK default settings and current implementation
expecting: Found root cause - naming doesn't match actual rendering
next_action: Document findings and recommend naming alternatives

## Symptoms
expected: Ball-and-stick should show small spheres connected by cylinders (sticks). Sticks should show just cylinders. Or naming should match what's actually rendered.
actual: Ball-and-stick looks like space-filling VDW spheres. Sticks looks like smaller VDW spheres. Not clear what's actually being rendered.
errors: None - this is a naming/representation mismatch
reproduction: 1) Generate structure 2) Switch to ball-and-stick - looks like VDW spheres 3) Switch to sticks - looks like smaller VDW spheres
started: After sphere/bond size tuning

## Eliminated

## Evidence
- timestamp: 2026-04-02T00:00:00Z
  checked: molecular_viewer.py lines 220-252 (set_representation_mode method)
  found: ball_and_stick mode uses AtomicRadiusScaleFactor=0.15, BondRadius=0.05. stick mode uses AtomicRadiusScaleFactor=0.05, BondRadius=0.05. Both use VDW radii.
  implication: Both modes render VDW-based spheres, just at different sizes. The naming is misleading because neither mode renders traditional ball-and-stick or pure stick geometry.
  
- timestamp: 2026-04-02T00:00:00Z
  checked: VTK vtkMoleculeMapper default settings (via Python inspection)
  found: VTK's UseBallAndStickSettings() defaults: VDWRadius type, scale 0.3, bond 0.075. UseLiquoriceStickSettings() defaults: UnitRadius type, scale 0.15, bond 0.15. UseVDWSpheresSettings() defaults: VDWRadius type, scale 1.0, bond 0.075.
  implication: VTK's "ball-and-stick" preset also uses VDW radii (not covalent). VTK's "liquorice" uses UnitRadius (uniform size), but the code overrides this to VDWRadius, making it just smaller spheres.
  
- timestamp: 2026-04-02T00:00:00Z
  checked: VTK AtomicRadiusType enum values
  found: CovalentRadius=0, VDWRadius=1, UnitRadius=2
  implication: Confirmed that both modes in the code use VDWRadius type (value 1), meaning atom sizes reflect their van der Waals radii, just at different scales.

## Resolution
root_cause: The naming is misleading because both "ball-and-stick" and "stick" modes render van der Waals spheres with cylinders for bonds, differing only in sphere scale factor (0.15 vs 0.05). Traditional ball-and-stick uses much smaller atom spheres (covalent radii or smaller), while true stick/liquorice mode would render only cylinders with no distinct atom spheres. The current naming doesn't reflect what's actually rendered.

**Evidence:**
1. VIEWER-03 requirement states: "stick mode ('liquorice') shows uniform thickness tubes for bonds without distinct atom balls"
2. Current "ball_and_stick" mode: VDWRadius type, scale 0.15, bond radius 0.05 - renders VDW spheres at 15% scale
3. Current "stick" mode: VDWRadius type, scale 0.05, bond radius 0.05 - renders VDW spheres at 5% scale
4. Both modes render spheres AND cylinders, just with different sphere sizes
5. True stick mode should render ONLY cylinders (no spheres), which would require SetRenderAtoms(False) or AtomicRadiusScaleFactor(0.0)

**What VTK actually provides:**
- UseBallAndStickSettings(): VDWRadius type, scale 0.3, bond 0.075 (smaller VDW spheres with bonds)
- UseLiquoriceStickSettings(): UnitRadius type, scale 0.15, bond 0.15 (uniform-size atoms with bonds)
- UseVDWSpheresSettings(): VDWRadius type, scale 1.0, bond 0.075 (full-size VDW spheres with bonds)

**Current naming vs actual rendering:**
- "Ball-and-stick" → renders VDW spheres (scale 0.15) + cylinders → should be called "Small VDW" or "Compact VDW"
- "Stick" → renders VDW spheres (scale 0.05) + cylinders → should be called "Tiny VDW" or "Minimal VDW"

**Alternative fix options:**
1. **Rename modes** to match actual rendering: "Compact VDW" and "Minimal VDW" (or similar)
2. **Fix rendering** to match names: "stick" mode should call SetRenderAtoms(False) to show only bonds
3. **Add third mode**: Add true "VDW Spheres" mode using UseVDWSpheresSettings() with scale 1.0
fix: 
verification: 
files_changed: []
root_cause: 
fix: 
verification: 
files_changed: []
