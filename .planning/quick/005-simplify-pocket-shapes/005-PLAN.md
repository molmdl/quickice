---
phase: 005-simplify-pocket-shapes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/interface_panel.py
  - quickice/structure_generation/types.py
  - quickice/structure_generation/interface_builder.py
  - quickice/structure_generation/modes/pocket.py
autonomous: true

must_haves:
  truths:
    - "Pocket shape dropdown shows only Sphere and Cubic options"
    - "Generating with pocket_shape=sphere or pocket_shape=cubic succeeds"
    - "Passing pocket_shape=rectangular or pocket_shape=hexagonal raises InterfaceGenerationError"
  artifacts:
    - path: "quickice/gui/interface_panel.py"
      provides: "Pocket shape combo with only Sphere and Cubic"
    - path: "quickice/structure_generation/types.py"
      provides: "Updated pocket_shape docstring"
    - path: "quickice/structure_generation/interface_builder.py"
      provides: "Validation with only sphere and cubic as valid shapes"
    - path: "quickice/structure_generation/modes/pocket.py"
      provides: "Only sphere and cubic containment checks"
  key_links:
    - from: "quickice/gui/interface_panel.py"
      to: "quickice/structure_generation/interface_builder.py"
      via: "pocket_shape value flows through InterfaceConfig"
      pattern: "pocket_shape"
---

<objective>
Remove rectangular and hexagonal pocket cavity shapes, keeping only sphere and cubic.

Purpose: Rectangular and cubic are IDENTICAL in implementation (same containment check: |dx|<r & |dy|<r & |dz|<r), making rectangular redundant. Hexagonal adds complexity the user wants removed. Simplify to two distinct, meaningful shapes: sphere (round void) and cubic (cube-shaped void).

Output: Four files updated with rectangular and hexagonal options removed from UI, validation, implementation, and types.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@quickice/gui/interface_panel.py
@quickice/structure_generation/types.py
@quickice/structure_generation/interface_builder.py
@quickice/structure_generation/modes/pocket.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove rectangular and hexagonal from UI and types</name>
  <files>quickice/gui/interface_panel.py, quickice/structure_generation/types.py</files>
  <action>
In `quickice/gui/interface_panel.py`:
- Line 172: Update pocket_diameter_input tooltip from "sphere/rectangular/cubic/hexagonal" to "sphere/cubic"
- Line 188: Change `self.pocket_shape_combo.addItems(["Sphere", "Rectangular", "Cubic", "Hexagonal"])` to `self.pocket_shape_combo.addItems(["Sphere", "Cubic"])`
- Line 189: Update pocket_shape_combo tooltip from mentioning all four shapes to just "Cavity shape: sphere or cube"
- Line 191: Update HelpIcon text from describing all four shapes to just "Shape of the water cavity. Sphere creates a round void. Cubic creates a cube-shaped void."

In `quickice/structure_generation/types.py`:
- Line 89: Change `pocket_shape: str = "sphere"  # Valid values: "sphere", "rectangular", "cubic", "hexagonal"` to `pocket_shape: str = "sphere"  # Valid values: "sphere", "cubic"`
  </action>
  <verify>grep -n "rectangular\|hexagonal\|Hexagonal\|Rectangular" quickice/gui/interface_panel.py quickice/structure_generation/types.py — should return NO matches</verify>
  <done>No references to rectangular or hexagonal remain in UI or types files</done>
</task>

<task type="auto">
  <name>Task 2: Remove rectangular and hexagonal from validation and implementation</name>
  <files>quickice/structure_generation/interface_builder.py, quickice/structure_generation/modes/pocket.py</files>
  <action>
In `quickice/structure_generation/interface_builder.py`:
- Line 203: Change `valid_shapes = {"sphere", "rectangular", "cubic", "hexagonal"}` to `valid_shapes = {"sphere", "cubic"}`
- Lines 206-208: Update error message from "Valid shapes are: sphere, rectangular, cubic, hexagonal." to "Valid shapes are: sphere and cubic."

In `quickice/structure_generation/modes/pocket.py`:
- Lines 4-6 (module docstring): Remove "four" and list only sphere and cubic. Change "Supports four cavity shapes" to "Supports two cavity shapes"
- Lines 34-38 (function docstring): Update the shapes list to only sphere and cubic. Remove rectangular and hexagonal entries.
- Lines 94-100: Remove the entire `elif config.pocket_shape == "rectangular":` block (ice removal)
- Lines 102-107: Keep the `elif config.pocket_shape == "cubic":` block as-is
- Lines 109-121: Remove the entire `elif config.pocket_shape == "hexagonal":` block (ice removal)
- Line 126: Update error message valid shapes from "sphere, rectangular, cubic, hexagonal" to "sphere, cubic"
- Lines 179-184: Remove the entire `elif config.pocket_shape == "rectangular":` block (water removal)
- Lines 186-191: Keep the `elif config.pocket_shape == "cubic":` block as-is
- Lines 193-201: Remove the entire `elif config.pocket_shape == "hexagonal":` block (water removal)
- Remove `import math` at line 10 if no longer used (hexagonal was the only consumer of math.sqrt)
  </action>
  <verify>grep -n "rectangular\|hexagonal" quickice/structure_generation/interface_builder.py quickice/structure_generation/modes/pocket.py — should return NO matches. Also verify `import math` is removed from pocket.py if unused.</verify>
  <done>No references to rectangular or hexagonal in validation or implementation; math import removed if unused</done>
</task>

</tasks>

<verification>
grep -rn "rectangular\|hexagonal" quickice/gui/interface_panel.py quickice/structure_generation/types.py quickice/structure_generation/interface_builder.py quickice/structure_generation/modes/pocket.py
# Should return zero matches

python -c "from quickice.structure_generation.interface_builder import validate_interface_config; from quickice.structure_generation.types import InterfaceConfig; import numpy as np; c = type('C', (), {'positions': np.zeros((3,3)), 'cell': np.eye(3), 'phase_id': 'ice_ih'})(); cfg = InterfaceConfig(mode='pocket', box_x=5, box_y=5, box_z=5, seed=1, pocket_diameter=2, pocket_shape='sphere'); validate_interface_config(cfg, c); print('sphere OK')"
# Should print "sphere OK"

python -c "from quickice.structure_generation.interface_builder import validate_interface_config; from quickice.structure_generation.types import InterfaceConfig; import numpy as np; c = type('C', (), {'positions': np.zeros((3,3)), 'cell': np.eye(3), 'phase_id': 'ice_ih'})(); cfg = InterfaceConfig(mode='pocket', box_x=5, box_y=5, box_z=5, seed=1, pocket_diameter=2, pocket_shape='cubic'); validate_interface_config(cfg, c); print('cubic OK')"
# Should print "cubic OK"

python -c "from quickice.structure_generation.interface_builder import validate_interface_config; from quickice.structure_generation.types import InterfaceConfig; import numpy as np; c = type('C', (), {'positions': np.zeros((3,3)), 'cell': np.eye(3), 'phase_id': 'ice_ih'})(); cfg = InterfaceConfig(mode='pocket', box_x=5, box_y=5, box_z=5, seed=1, pocket_diameter=2, pocket_shape='rectangular'); validate_interface_config(cfg, c)" 2>&1 | grep -i "invalid"
# Should show invalid pocket shape error
</verification>

<success_criteria>
- Pocket shape dropdown contains exactly two options: Sphere and Cubic
- rectangular and hexagonal strings absent from all four files
- sphere and cubic pocket shapes still generate correctly
- rectangular and hexagonal shapes are rejected by validation
</success_criteria>

<output>
After completion, create `.planning/quick/005-simplify-pocket-shapes/005-SUMMARY.md`
</output>
