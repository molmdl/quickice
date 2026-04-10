---
phase: 004-interface-viewer-improvements
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/interface_viewer.py
  - quickice/gui/interface_panel.py
  - quickice/structure_generation/modes/pocket.py
  - quickice/structure_generation/interface_builder.py
  - quickice/structure_generation/types.py
autonomous: true

must_haves:
  truths:
    - "Interface 3D viewer shows only bond lines, no atom spheres — unobstructed view of structure"
    - "Pocket type dropdown shows Sphere, Rectangular, Cubic, Hexagonal — no misleading Ellipsoid option"
    - "All four pocket types generate valid interface structures"
    - "Mode-specific parameters appear at top right of Interface tab, 3D viewer is taller"
  artifacts:
    - path: "quickice/gui/interface_viewer.py"
      provides: "Bond-only rendering (no atom spheres)"
    - path: "quickice/gui/interface_panel.py"
      provides: "Updated pocket shapes + relocated parameters panel"
    - path: "quickice/structure_generation/modes/pocket.py"
      provides: "Rectangular, cubic, hexagonal cavity generation"
    - path: "quickice/structure_generation/types.py"
      provides: "Updated pocket_shape docstring and validation"
  key_links:
    - from: "quickice/gui/interface_panel.py"
      to: "quickice/structure_generation/types.py"
      via: "get_configuration() pocket_shape value"
      pattern: "pocket_shape"
    - from: "quickice/structure_generation/modes/pocket.py"
      to: "quickice/structure_generation/types.py"
      via: "config.pocket_shape dispatch"
      pattern: "pocket_shape.*=="
---

<objective>
Three improvements to the Interface tab viewer:

1. **Remove atom spheres** from the interface 3D viewer. Currently `_create_phase_actor` renders small spheres via vtkMoleculeMapper. These block the view when many atoms are present. Remove atom sphere rendering — keep only bond lines for clarity.

2. **Update pocket type options**. The dropdown currently shows "Sphere" and "Ellipsoid", but Ellipsoid is not implemented and misleading. Replace with: Sphere, Rectangular, Cubic, Hexagonal. Implement all four cavity geometries in pocket.py.

3. **Move mode-specific parameters to top right** of Interface tab. Currently the stacked widget (slab/pocket/piece parameters) is above the 3D viewer, consuming vertical space. Relocate it to the top-right area so the 3D viewer can be taller.

Purpose: Improve clarity and usability of the Interface Construction tab.
Output: Cleaner 3D visualization, accurate pocket type options, better layout.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@quickice/gui/interface_viewer.py
@quickice/gui/interface_panel.py
@quickice/structure_generation/modes/pocket.py
@quickice/structure_generation/interface_builder.py
@quickice/structure_generation/types.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove atom spheres from interface 3D viewer</name>
  <files>quickice/gui/interface_viewer.py</files>
  <action>
In `set_interface_structure()`, remove the creation and addition of `_ice_actor` and `_water_actor` (the atom sphere actors from `_create_phase_actor`). Keep only the bond line actors (`_ice_bond_actor`, `_water_bond_actor`) and `_unit_cell_actor`.

Specific changes in interface_viewer.py:
1. In `set_interface_structure()`: Remove the two lines that create phase actors:
   - `self._ice_actor = self._create_phase_actor(ice_mol, ICE_COLOR)` → delete
   - `self._water_actor = self._create_phase_actor(water_mol, WATER_COLOR)` → delete
   - Remove `self.renderer.AddActor(self._ice_actor)` and `self.renderer.AddActor(self._water_actor)`
2. In `_clear_actors()`: Remove the ice_actor and water_actor removal blocks (they no longer exist)
3. In `__init__()`: Remove `self._ice_actor` and `self._water_actor` from state tracking
4. Remove the `_create_phase_actor()` method entirely (no longer needed — bond actors use `create_bond_lines_actor` from vtk_utils.py directly)
5. Update the class docstring to remove references to `_ice_actor` and `_water_actor` attributes
6. The `interface_to_vtk_molecules()` call is still needed because bonds are extracted from the vtkMolecule objects. Keep that call and the bond extraction logic.

The viewer should now show ONLY bond lines (cyan for ice, cornflower blue for water) plus the unit cell wireframe. No atom spheres at all.
  </action>
  <verify>grep -c "_create_phase_actor\|_ice_actor\|_water_actor" quickice/gui/interface_viewer.py returns 0</verify>
  <done>Interface 3D viewer renders only bond lines and unit cell — no atom spheres</done>
</task>

<task type="auto">
  <name>Task 2: Update pocket types and implement all four cavity geometries</name>
  <files>quickice/gui/interface_panel.py, quickice/structure_generation/modes/pocket.py, quickice/structure_generation/interface_builder.py, quickice/structure_generation/types.py</files>
  <action>
**2a. Update pocket shape dropdown in interface_panel.py:**
- In `_create_pocket_panel()`: Change `self.pocket_shape_combo.addItems(["Sphere", "Ellipsoid"])` to `self.pocket_shape_combo.addItems(["Sphere", "Rectangular", "Cubic", "Hexagonal"])`
- Update tooltip from "Cavity shape: sphere or ellipsoid" to "Cavity shape: sphere, rectangular prism, cube, or hexagonal prism"
- Update the HelpIcon text from mentioning ellipsoid to describe the four shapes

**2b. Update types.py:**
- Change `pocket_shape: str = "sphere"` docstring to mention all four shapes
- Keep the field type as `str` — the valid values are now: "sphere", "rectangular", "cubic", "hexagonal"

**2c. Update interface_builder.py validation (around line 202-212):**
- Replace the `if config.pocket_shape != "sphere"` check with validation that `config.pocket_shape` is in `{"sphere", "rectangular", "cubic", "hexagonal"}`
- Update the error message to list the four valid shapes

**2d. Implement cavity geometries in pocket.py `assemble_pocket()`:**
- Replace the single `if config.pocket_shape != "sphere"` check with a dispatch that handles all four shapes
- The key difference between shapes is HOW molecules are classified as "inside cavity" (currently uses `distances < radius` for sphere). For each shape:

**Sphere** (existing — keep as-is):
- `distances = np.linalg.norm(ice_o_positions - center, axis=1)`
- `inside = distances < radius`

**Rectangular** (rectangular prism with dimensions = pocket_diameter in all 3 axes):
- Half-sizes: `hx = hy = hz = radius` (since diameter = 2*radius)
- `inside = (|x - cx| < hx) & (|y - cy| < hy) & (|z - cz| < hz)`

**Cubic** (same as rectangular but side = pocket_diameter):
- Same as rectangular since diameter defines the single side length
- `inside = (|x - cx| < radius) & (|y - cy| < radius) & (|z - cz| < radius)`

**Hexagonal** (hexagonal prism with diameter = 2*radius, extruded along Z with height = pocket_diameter):
- In XY plane: regular hexagon inscribed in circle of `radius`, centered at (cx, cy)
- Hexagonal containment test: `max(|x-cx|, |y-cy|/sqrt(3) + |x-cx|/2) < radius` ... actually use the standard hex test:
  - For a flat-topped hexagon: `inside_xy = (|y-cy| < radius * sqrt(3)/2) and (|x-cx| + |y-cy|/(2*sqrt(3)) < radius)` ... 
  
  Actually, use the simpler and correct approach for a pointy-top hexagonal prism:
  - XY: check if point is inside regular hexagon with circumradius = radius
  - Z: check if `|z - cz| < radius` (height = diameter)
  
  Hexagon containment (circumradius R, pointy-top orientation):
  ```python
  dx = abs(x - cx)
  dy = abs(y - cy)
  inside_xy = (dy <= R * sqrt(3)/2) and (R * sqrt(3)/2 - dy >= dx - R/2)  # simplified: not quite right
  ```
  
  Use the standard hexagonal containment test for circumradius R:
  ```python
  import math
  dx = abs(ice_o_positions[:, 0] - center[0])
  dy = abs(ice_o_positions[:, 1] - center[1])
  # Pointy-top hexagon with circumradius R
  # Containment: |y| <= R*sqrt(3)/2 AND |x| <= R - |y|/(2*sqrt(3)) ... 
  # Actually simpler: for a regular hexagon with circumradius R,
  # a point is inside if it satisfies the half-plane constraints.
  # Use: max(|x|, |x|/2 + |y|*sqrt(3)/2) <= R  (flat-top)
  # Or equivalently for pointy-top: max(|y|, |y|/2 + |x|*sqrt(3)/2) <= R
  hex_check = np.maximum(dy, dy/2 + dx * math.sqrt(3)/2)
  inside_xy = hex_check <= radius
  inside_z = np.abs(ice_o_positions[:, 2] - center[2]) < radius
  ice_inside_cavity = set(np.where(inside_xy & inside_z)[0])
  ```

For water molecules: apply the SAME shape test to `water_o_positions` to determine which water molecules are outside the cavity (to be removed). Currently water outside sphere uses `water_distances >= radius`. Replace with the same shape test: water molecules outside the shape get removed.

The `fill_region_with_water()` call uses `fill_dims` to fill a bounding box. Keep this as-is for all shapes — the bounding box approach works for all four shapes. The water-trimming step (removing water outside the cavity) handles the shape correctly.

For rectangular/cubic: `fill_dims = np.array([2*radius, 2*radius, 2*radius])` (same as sphere — already correct)
For hexagonal: `fill_dims = np.array([2*radius, 2*radius, 2*radius])` (bounding box of hexagon = diameter cube)

IMPORTANT: All four shapes use the SAME `fill_region_with_water(fill_dims)` approach. The only difference is the containment test for both ice removal and water trimming.
  </action>
  <verify>python -c "from quickice.structure_generation.modes.pocket import assemble_pocket; from quickice.structure_generation.types import InterfaceConfig; print('import OK')" && grep -q "rectangular\|cubic\|hexagonal" quickice/structure_generation/modes/pocket.py && grep -q "Hexagonal" quickice/gui/interface_panel.py</verify>
  <done>Four pocket types (Sphere, Rectangular, Cubic, Hexagonal) available in UI and all generate valid cavity structures. Ellipsoid references removed.</done>
</task>

<task type="auto">
  <name>Task 3: Move mode-specific parameters to top right of Interface tab</name>
  <files>quickice/gui/interface_panel.py</files>
  <action>
Restructure the `_setup_ui()` layout in `InterfacePanel` so the mode-specific parameter panel (the QStackedWidget containing slab/pocket/piece panels) appears at the top right, and the 3D viewer takes up the remaining (taller) space below.

Current layout (vertical, top to bottom):
- Title, mode selector, box dimensions, seed, stacked_widget (mode params), candidate selection, buttons, progress, info, viewer_stack

New layout structure:
- Use a top-level `QHBoxLayout` splitting the panel into LEFT and RIGHT columns
- LEFT column (QVBoxLayout): Title, mode selector, box dimensions, seed, candidate selection, buttons, progress, info — all the configuration controls
- RIGHT column (QVBoxLayout): The stacked_widget (mode params) at the TOP of the right column, then the viewer_stack taking remaining vertical space with `stretch=1`

This way:
1. Mode-specific parameters are always visible at top-right (no scrolling needed)
2. The 3D viewer occupies the full remaining height on the right side
3. Configuration controls stay on the left, organized as before

Implementation:
1. In `_setup_ui()`, replace the single `QVBoxLayout(self)` with a `QHBoxLayout(self)` as the top-level layout
2. Create a `QVBoxLayout` for the left column, add all existing controls (title through info panel)
3. Create a `QVBoxLayout` for the right column, add the stacked_widget first, then the viewer_stack with `stretch=1`
4. Add both columns to the top-level horizontal layout with appropriate stretch factors (left: 0/fixed-width, right: 1/expanding) — the left column should NOT stretch, the right column should fill remaining space
5. Set the left column layout's maximum width or use a fixed proportion (e.g., left takes ~40%, right takes ~60%) using stretch factors on the top-level QHBoxLayout: `top_layout.addLayout(left_layout, 2)` and `top_layout.addLayout(right_layout, 3)`
6. Remove the `layout.addStretch()` at the bottom of the left column — the right column's viewer should fill space instead
7. The `layout.addSpacing(15)` before the stacked_widget should be removed (stacked_widget moved to right column)
8. Move `self.stacked_widget` and `self._viewer_stack` (with the placeholder/viewer) to the right column layout

IMPORTANT: Ensure the `_setup_connections()` method still works — the mode_combo → stacked_widget connection doesn't change. The candidate_dropdown, refresh_btn, generate_btn signals all still work since the widgets themselves haven't changed, just their layout positions.
  </action>
  <verify>python -c "from quickice.gui.interface_panel import InterfacePanel; print('import OK')" && grep -q "QHBoxLayout" quickice/gui/interface_panel.py</verify>
  <done>Interface tab has two-column layout: left column for configuration controls, right column with mode-specific parameters on top and taller 3D viewer below</done>
</task>

</tasks>

<verification>
1. Run `python -c "from quickice.gui.interface_panel import InterfacePanel; from quickice.gui.interface_viewer import InterfaceViewerWidget; print('imports OK')"` — no import errors
2. Verify no atom sphere actors in interface_viewer.py: `grep -c "_ice_actor\|_water_actor\|_create_phase_actor" quickice/gui/interface_viewer.py` returns 0
3. Verify no ellipsoid references: `grep -ic "ellipsoid\|epsloid" quickice/gui/interface_panel.py quickice/structure_generation/modes/pocket.py quickice/structure_generation/interface_builder.py` returns 0 for all files
4. Verify pocket types exist: `grep -c "Hexagonal\|Rectangular\|Cubic" quickice/gui/interface_panel.py` returns positive
5. Verify two-column layout: `grep -c "QHBoxLayout" quickice/gui/interface_panel.py` returns positive
</verification>

<success_criteria>
- Interface 3D viewer shows only bond lines (no atom spheres)
- Pocket type dropdown offers Sphere, Rectangular, Cubic, Hexagonal (no Ellipsoid)
- All four pocket types can generate interface structures without errors
- Interface tab has two-column layout with mode parameters at top-right and taller 3D viewer
- No import errors in any modified modules
</success_criteria>

<output>
After completion, create `.planning/quick/004-interface-viewer-improvements/004-SUMMARY.md`
</output>
