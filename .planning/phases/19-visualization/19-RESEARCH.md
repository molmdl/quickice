# Phase 19: Visualization - Research

**Researched:** 2026-04-09
**Domain:** VTK 3D molecular visualization with phase-colored ice-water interface structures
**Confidence:** HIGH

## Summary

This phase adds a VTK-based 3D viewer to Tab 2 (Interface Construction) that displays ice-water interface structures with clear visual distinction between ice and water phases. The existing codebase already has a fully functional `MolecularViewerWidget` for Tab 1 and utility functions in `vtk_utils.py`. However, the interface visualization has fundamentally different requirements: two-phase coloring (not CPK element coloring), line-based bonds (not ball-and-stick cylinders), no hydrogen bonds (hidden in Tab 2), and a specific camera orientation showing the slab stacking direction.

The recommended approach is a **new `InterfaceViewerWidget` class** using a **two-actor architecture** — one actor per phase (ice and water), each with its own `vtkMoleculeMapper` for atoms (RenderBondsOff) and separate `vtkPolyData` line actors for covalent bonds. This cleanly separates phase coloring, avoids complexity with scalar-based coloring, and renders bonds as true 2D lines for performance.

**Primary recommendation:** Create a new `InterfaceViewerWidget` with two-actor phase coloring (ice=cyan, water=cornflower blue), atoms as small spheres, bonds as 2D lines, and a Z-vertical camera for slab visualization.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| VTK | 9.5.2 | 3D rendering | Already in project, provides vtkMoleculeMapper, QVTKRenderWindowInteractor |
| PySide6 | 6.10.2 | Qt widget integration | Already in project, provides QWidget, layouts, signals |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | — | Position array manipulation | InterfaceStructure.positions manipulation for vtkMolecule creation |
| vtkmodules.all | — | VTK classes (vtkMolecule, vtkPolyData, etc.) | All VTK object creation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Two-actor architecture | Single actor + scalar coloring | Scalar approach: fewer actors but less control over per-phase bond color; scalar/LUT interaction with vtkMoleculeMapper's internal glyph mappers is less predictable |
| Separate line actors for bonds | vtkMoleculeMapper cylinders (thin) | Cylinders: still 3D geometry (slow for large systems); lines are true 2D (fast), matches VIS-02 |
| New InterfaceViewerWidget | Reuse MolecularViewerWidget | MolecularViewerWidget is tightly coupled to Candidate/RankedCandidate, has ball-and-stick modes, h-bond toggles — too different from interface needs |

**Installation:**
```bash
# Already installed — no new dependencies needed
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/gui/
├── interface_viewer.py     # NEW: InterfaceViewerWidget (Tab 2 viewer)
├── vtk_utils.py            # EXTEND: add interface_to_vtk_molecules(), create_bond_lines_actor()
├── interface_panel.py      # MODIFY: integrate viewer widget, replace placeholder
├── molecular_viewer.py     # UNCHANGED: Tab 1 viewer (reference only)
├── dual_viewer.py          # UNCHANGED: Tab 1 dual viewer (reference only)
└── main_window.py          # MODIFY: connect interface_generation_complete to viewer
```

### Pattern 1: Two-Actor Phase Coloring
**What:** Separate vtkMoleculeMapper + vtkActor pairs for ice and water phases
**When to use:** When two distinct groups of atoms need different uniform colors
**Example:**
```python
# Source: VTK 9.5.2 vtkMoleculeMapper API (verified)
# Ice actor — all ice atoms rendered as cyan spheres
ice_mapper = vtkMoleculeMapper()
ice_mapper.SetInputData(ice_mol)
ice_mapper.SetAtomColorModeToSingleColor()
ice_mapper.SetAtomColor(0, 204, 204)  # Cyan (0.0, 0.8, 0.8) as uint8
ice_mapper.SetBondColorModeToSingleColor()
ice_mapper.SetBondColor(0, 204, 204)
ice_mapper.RenderBondsOff()  # Bonds rendered separately as lines
ice_mapper.SetAtomicRadiusTypeToUnitRadius()
ice_mapper.SetAtomicRadiusScaleFactor(0.2 * ANGSTROM_TO_NM)  # Small spheres

ice_actor = vtkActor()
ice_actor.SetMapper(ice_mapper)

# Water actor — all water atoms rendered as cornflower blue spheres
water_mapper = vtkMoleculeMapper()
water_mapper.SetInputData(water_mol)
water_mapper.SetAtomColorModeToSingleColor()
water_mapper.SetAtomColor(100, 148, 237)  # Cornflower blue as uint8
water_mapper.SetBondColorModeToSingleColor()
water_mapper.SetBondColor(100, 148, 237)
water_mapper.RenderBondsOff()
water_mapper.SetAtomicRadiusTypeToUnitRadius()
water_mapper.SetAtomicRadiusScaleFactor(0.2 * ANGSTROM_TO_NM)

water_actor = vtkActor()
water_actor.SetMapper(water_mapper)
```

### Pattern 2: Line-Based Bond Rendering
**What:** Bonds rendered as 2D line cells in vtkPolyData instead of 3D cylinders
**When to use:** Performance requirement with large systems (VIS-02)
**Example:**
```python
# Source: Existing create_hbond_actor() pattern in vtk_utils.py (verified)
from vtkmodules.all import vtkPoints, vtkCellArray, vtkPolyData, vtkPolyDataMapper, vtkActor
import numpy as np

def create_bond_lines_actor(bond_pairs, color_rgb, line_width=1.5):
    """Create a VTK actor rendering bonds as 2D lines.
    
    Args:
        bond_pairs: List of (pos1, pos2) tuples, each (x,y,z) in nm
        color_rgb: (r, g, b) tuple, floats 0-1
        line_width: Width in pixels
    """
    points = vtkPoints()
    lines = vtkCellArray()
    
    for p1, p2 in bond_pairs:
        id1 = points.InsertNextPoint(p1[0], p1[1], p1[2])
        id2 = points.InsertNextPoint(p2[0], p2[1], p2[2])
        lines.InsertNextCell(2)
        lines.InsertCellPoint(id1)
        lines.InsertCellPoint(id2)
    
    polydata = vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetLines(lines)
    
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color_rgb)
    actor.GetProperty().SetLineWidth(line_width)
    
    return actor
```

### Pattern 3: InterfaceStructure → vtkMolecule Conversion (Split by Phase)
**What:** Convert InterfaceStructure into two separate vtkMolecule objects
**When to use:** InterfaceStructure has ice atoms first, water atoms second, split at ice_atom_count
**Example:**
```python
# Source: Derived from existing candidate_to_vtk_molecule() in vtk_utils.py
# Key: InterfaceStructure has ice_atom_count marking the boundary

def interface_to_vtk_molecules(iface):
    """Convert InterfaceStructure to (ice_mol, water_mol) pair.
    
    Ice atoms come FIRST in positions/atom_names, water atoms follow.
    ice_atom_count marks the split point.
    MW virtual sites (atomic number 0) are skipped.
    """
    ice_mol = vtkMolecule()
    ice_mol.Initialize()
    
    water_mol = vtkMolecule()
    water_mol.Initialize()
    
    atomic_numbers = {
        "O": 8, "H": 1, "OW": 8, "HW1": 1, "HW2": 1, "MW": None
    }
    
    # Split: ice atoms [0..ice_atom_count), water atoms [ice_atom_count..)
    ice_indices = []  # Track visible atom indices in ice_mol
    water_indices = []  # Track visible atom indices in water_mol
    
    for i, (name, pos) in enumerate(zip(iface.atom_names, iface.positions)):
        atomic_num = atomic_numbers.get(name)
        if atomic_num is None:  # Skip MW virtual sites
            continue
        
        if i < iface.ice_atom_count:
            idx = ice_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
            ice_indices.append(idx)
        else:
            idx = water_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
            water_indices.append(idx)
    
    # Add O-H bonds for each molecule (3 visible atoms per water)
    # Ice: TIP3P style (O, H, H) × ice_nmolecules
    for mol_idx in range(iface.ice_nmolecules):
        o_idx = ice_indices[mol_idx * 3]
        h1_idx = ice_indices[mol_idx * 3 + 1]
        h2_idx = ice_indices[mol_idx * 3 + 2]
        ice_mol.AppendBond(o_idx, h1_idx, 1)
        ice_mol.AppendBond(o_idx, h2_idx, 1)
    
    # Water: TIP4P style (OW, HW1, HW2) × water_nmolecules (MW already skipped)
    for mol_idx in range(iface.water_nmolecules):
        o_idx = water_indices[mol_idx * 3]
        h1_idx = water_indices[mol_idx * 3 + 1]
        h2_idx = water_indices[mol_idx * 3 + 2]
        water_mol.AppendBond(o_idx, h1_idx, 1)
        water_mol.AppendBond(o_idx, h2_idx, 1)
    
    return ice_mol, water_mol
```

### Pattern 4: Z-Axis Camera Setup (Side View for Slab Interfaces)
**What:** Position camera to show slab stacking direction (Z) as vertical
**When to use:** Default view when interface structure loads
**Example:**
```python
# Source: VTK camera API (verified with VTK 9.5.2)
import math

def set_side_view_camera(renderer):
    """Set camera for side view of slab interface.
    
    Z-axis is vertical (slab stacking direction).
    Camera looks perpendicular to Z so both ice and water
    layers are visible.
    """
    bounds = renderer.ComputeVisiblePropBounds()
    center_x = (bounds[0] + bounds[1]) / 2
    center_y = (bounds[2] + bounds[3]) / 2
    center_z = (bounds[4] + bounds[5]) / 2
    diagonal = math.sqrt(
        (bounds[1] - bounds[0]) ** 2 +
        (bounds[3] - bounds[2]) ** 2 +
        (bounds[5] - bounds[4]) ** 2
    )
    
    camera = renderer.GetActiveCamera()
    camera.SetPosition(center_x, center_y + diagonal, center_z)
    camera.SetFocalPoint(center_x, center_y, center_z)
    camera.SetViewUp(0, 0, 1)  # Z is vertical
```

### Anti-Patterns to Avoid
- **Using scalar coloring on vtkMoleculeMapper for phase distinction**: The interaction between `ScalarVisibilityOn()` and `vtkMoleculeMapper`'s internal AtomGlyphMapper/BondGlyphMapper is unpredictable. Two separate actors with `SingleColor` mode is cleaner and more reliable.
- **Rendering bonds as thin cylinders via vtkMoleculeMapper**: Still 3D geometry (slow). Use `vtkPolyData` with line cells for true 2D lines.
- **Subclassing MolecularViewerWidget**: It's coupled to Candidate/RankedCandidate, ball-and-stick modes, h-bond toggles, and color-by-property. Interface visualization needs none of these.
- **Reusing Tab 1's DualViewerWidget**: VIS-01 requires single viewport, not dual.
- **Showing hydrogen bonds in Tab 2**: Explicitly overridden by CONTEXT — water makes H-bonds too messy.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VTK molecule conversion | Custom atom-by-atom vtkMolecule builder | `candidate_to_vtk_molecule()` pattern from vtk_utils.py | Existing pattern handles TIP3P/TIP4P naming, MW skip, bond creation — adapt for InterfaceStructure |
| Dashed line rendering | Custom dash pattern generator | `create_hbond_actor()` pattern from vtk_utils.py | Has manual dash splitting workaround for VTK OpenGL2 stipple bug — NOT needed for Tab 2 (H-bonds hidden), but the line cell creation pattern is the basis for bond line actors |
| Unit cell box | Custom wireframe box | `create_unit_cell_actor()` from vtk_utils.py | Already handles orthogonal cells from cell matrix |
| VTK-Qt widget integration | Custom QWidget + VTK embed | `QVTKRenderWindowInteractor` | Already used in MolecularViewerWidget, handles Qt event loop integration |

**Key insight:** The existing vtk_utils.py and MolecularViewerWidget provide proven patterns for VTK-Qt integration, molecule conversion, and actor creation. The interface viewer should follow these same patterns but adapted for two-phase coloring and line-based bonds.

## Common Pitfalls

### Pitfall 1: MW Virtual Site Not Skipped
**What goes wrong:** MW atoms (atomic number 0, massless virtual site in TIP4P) are included in the vtkMolecule, causing rendering artifacts or invalid atom types
**Why it happens:** InterfaceStructure includes MW in positions/atom_names for water molecules (4 atoms per molecule: OW, HW1, HW2, MW)
**How to avoid:** Skip atoms with name "MW" during vtkMolecule construction, same as existing `candidate_to_vtk_molecule()` logic
**Warning signs:** Atoms rendered at origin or with atomic number 0; bond indices misaligned

### Pitfall 2: Bond Index Misalignment After MW Skip
**What goes wrong:** O-H bonds connect wrong atoms because MW atoms were skipped but bond indices weren't adjusted
**Why it happens:** After skipping MW, the visible atom indices shift. The code must track only visible atom indices when creating bonds.
**How to avoid:** Use the `atom_indices` list pattern from `candidate_to_vtk_molecule()` — only track indices of atoms actually added to vtkMolecule, then use those indices for bond creation. With 3 visible atoms per water (after MW skip), bonds are at indices [n*3, n*3+1, n*3+2].
**Warning signs:** Bonds connecting atoms that shouldn't be bonded; visual spaghetti

### Pitfall 3: ice_atom_count Doesn't Match After MW Skip
**What goes wrong:** `ice_atom_count` from InterfaceStructure counts ALL atoms including MW. Using it directly to split ice/water gives wrong boundary when MW atoms are present.
**Why it happens:** Ice uses TIP3P (3 atoms/molecule: O, H, H — no MW). Water uses TIP4P (4 atoms/molecule: OW, HW1, HW2, MW — has MW). The ice_atom_count is correct for the FULL array but MW must be skipped during visualization.
**How to avoid:** Don't use ice_atom_count as a direct index into the visible-atom array. Instead, iterate through all atoms and check `i < ice_atom_count` to determine phase, then skip MW atoms. This correctly handles the MW skew.
**Warning signs:** Some water atoms colored as ice or vice versa; phase boundary in wrong position

### Pitfall 4: vtkMoleculeMapper Scalar Coloring Doesn't Work as Expected
**What goes wrong:** Setting `ScalarVisibilityOn()` + `SetColorModeToMapScalars()` on vtkMoleculeMapper doesn't properly color atom glyphs or affects bonds unexpectedly
**Why it happens:** vtkMoleculeMapper has internal AtomGlyphMapper and BondGlyphMapper. The interaction between scalar visibility and the internal glyph mappers is complex and not well-documented.
**How to avoid:** Use `SetAtomColorModeToSingleColor()` with explicit `SetAtomColor()` per actor. This is predictable and doesn't depend on scalar array propagation.
**Warning signs:** All atoms same color; bonds colored differently from atoms; intermittent coloring

### Pitfall 5: VTK Camera ResetCamera() Overrides Custom View
**What goes wrong:** Calling `ResetCamera()` after setting custom camera position/orientation undoes the custom view
**Why it happens:** `ResetCamera()` auto-positions the camera to frame all actors, which may change view direction and up vector
**How to avoid:** Set camera position/orientation AFTER `ResetCamera()`, or set camera manually without calling `ResetCamera()`. For the side view: call `ResetCamera()` first (to get bounds/center), then manually set position, focal point, and view up.
**Warning signs:** Camera shows default VTK view (looking down Z with Y up) instead of desired side view

### Pitfall 6: Poor Color Distinction Between Ice and Water
**What goes wrong:** Cyan and blue are too similar on dark background, users can't easily distinguish phases
**Why it happens:** Both cyan and blue have similar luminance (≈0.55). Their distinction is purely by hue (green-blue vs purple-blue), which can be hard to see at a glance.
**How to avoid:** Use cornflower blue (0.39, 0.58, 0.93) which has the best RGB distance from both cyan (0.466) and dark background (0.714). Consider slightly different atom sizes between phases for additional visual cue (larger for ice O, smaller for water O). Adding a unit cell boundary can also help spatially separate the phases.
**Warning signs:** Users ask "which part is ice?"; phase boundary not immediately obvious

### Pitfall 7: Performance Degradation with Large Systems
**What goes wrong:** Rendering becomes slow/frozen with thousands of atoms
**Why it happens:** vtkMoleculeMapper renders each atom as a 3D sphere (glyph3D) and each bond as a 3D cylinder — expensive for large systems
**How to avoid:** (1) Use `RenderBondsOff()` on mappers and render bonds as 2D lines (much faster). (2) Use `SetAtomicRadiusTypeToUnitRadius()` with small scale factor instead of VDW radii. (3) Consider `RenderAtomsOff()` above a configurable threshold (e.g., >5000 atoms) and use point-based rendering instead.
**Warning signs:** Frame rate drops below 10 fps; UI becomes unresponsive

## Code Examples

### Complete InterfaceViewerWidget Structure
```python
# Source: Derived from existing MolecularViewerWidget pattern (verified)
# Location: quickice/gui/interface_viewer.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.all import (
    vtkRenderer, vtkInteractorStyleTrackballCamera, vtkMoleculeMapper, vtkActor,
)
from quickice.structure_generation.types import InterfaceStructure
from quickice.gui.vtk_utils import (
    interface_to_vtk_molecules, create_bond_lines_actor, create_unit_cell_actor,
)

# Color constants (RGB floats 0-1)
ICE_COLOR = (0.0, 0.8, 0.8)         # Cyan
WATER_COLOR = (0.39, 0.58, 0.93)    # Cornflower blue
BOND_LINE_WIDTH = 1.5               # Pixels

# Unit conversion (same as molecular_viewer.py)
ANGSTROM_TO_NM = 0.1

class InterfaceViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_structure = None
        self._ice_actor = None
        self._water_actor = None
        self._ice_bond_actor = None
        self._water_bond_actor = None
        self._unit_cell_actor = None
        self._setup_vtk()
    
    def _setup_vtk(self):
        """Set up VTK rendering pipeline (same pattern as MolecularViewerWidget)."""
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.vtk_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.render_window = self.vtk_widget.GetRenderWindow()
        self.renderer = vtkRenderer()
        self.renderer.SetBackground(0.1, 0.2, 0.4)  # Dark blue (same as Tab 1)
        self.render_window.AddRenderer(self.renderer)
        
        self.interactor = self.render_window.GetInteractor()
        self.style = vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(self.style)
        self.vtk_widget.Initialize()
    
    def set_interface_structure(self, structure: InterfaceStructure):
        """Load and display an interface structure."""
        self._clear_actors()
        self._current_structure = structure
        
        # Convert to two vtkMolecules
        ice_mol, water_mol = interface_to_vtk_molecules(structure)
        
        # Create atom actors (spheres only, bonds off)
        self._ice_actor = self._create_phase_actor(ice_mol, ICE_COLOR)
        self._water_actor = self._create_phase_actor(water_mol, WATER_COLOR)
        
        # Create bond line actors
        ice_bonds = self._extract_bonds(ice_mol)
        water_bonds = self._extract_bonds(water_mol)
        self._ice_bond_actor = create_bond_lines_actor(ice_bonds, ICE_COLOR, BOND_LINE_WIDTH)
        self._water_bond_actor = create_bond_lines_actor(water_bonds, WATER_COLOR, BOND_LINE_WIDTH)
        
        # Add all actors
        self.renderer.AddActor(self._ice_actor)
        self.renderer.AddActor(self._water_actor)
        self.renderer.AddActor(self._ice_bond_actor)
        self.renderer.AddActor(self._water_bond_actor)
        
        # Set camera: side view with Z vertical
        self._set_side_view_camera()
        
        self.render_window.Render()
```

### Bond Extraction from vtkMolecule
```python
# Source: VTK vtkMolecule API (verified with VTK 9.5.2)

def _extract_bonds(self, mol):
    """Extract bond pairs from vtkMolecule for line rendering.
    
    Returns list of (pos1, pos2) tuples for create_bond_lines_actor().
    """
    bonds = []
    for i in range(mol.GetNumberOfBonds()):
        bond = mol.GetBond(i)
        id1 = bond.GetBeginAtomId()
        id2 = bond.GetEndAtomId()
        pos1 = mol.GetAtom(id1).GetPosition()
        pos2 = mol.GetAtom(id2).GetPosition()
        bonds.append((
            (pos1[0], pos1[1], pos1[2]),
            (pos2[0], pos2[1], pos2[2]),
        ))
    return bonds
```

### Phase Actor Creation
```python
# Source: VTK vtkMoleculeMapper API (verified with VTK 9.5.2)

def _create_phase_actor(self, mol, color_rgb):
    """Create a vtkActor with vtkMoleculeMapper for one phase.
    
    Renders atoms as small spheres, bonds OFF (rendered separately).
    """
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(mol)
    
    # Uniform color for all atoms in this phase
    mapper.SetAtomColorModeToSingleColor()
    r, g, b = [int(c * 255) for c in color_rgb]
    mapper.SetAtomColor(r, g, b)
    
    # Bonds rendered separately as lines
    mapper.RenderBondsOff()
    
    # Small sphere size for performance
    mapper.SetAtomicRadiusTypeToUnitRadius()
    mapper.SetAtomicRadiusScaleFactor(0.2 * ANGSTROM_TO_NM)
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    return actor
```

### Integration in InterfacePanel (Replacing Placeholder)
```python
# Source: InterfacePanel pattern (verified from codebase)
# In InterfacePanel._setup_ui():

# Replace the placeholder_label section with:
self._viewer_stack = QStackedWidget()
self._placeholder_label = QLabel("Generate a structure to visualize")
self._placeholder_label.setAlignment(Qt.AlignCenter)
self._placeholder_label.setStyleSheet("font-size: 14px; color: #666; ...")
self._viewer_stack.addWidget(self._placeholder_label)  # Page 0

self._interface_viewer = InterfaceViewerWidget()
self._viewer_stack.addWidget(self._interface_viewer)  # Page 1

layout.addWidget(self._viewer_stack, stretch=1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ball-and-stick cylinder bonds | Line-based bond rendering | Phase 19 (VIS-02) | 10-100x faster for large systems; VTK cylinder rendering is expensive per bond |
| CPK element coloring | Phase-based uniform coloring | Phase 19 (VIS-03) | Clear ice/water distinction; trade-off: loses O/H visual distinction within phase |
| Dual viewport (Tab 1) | Single viewport (Tab 2) | Phase 19 (VIS-01) | Simpler widget; interface needs one view, not comparison |
| H-bond dashed lines (Tab 1) | H-bonds hidden (Tab 2) | Phase 19 (CONTEXT override) | Water phase makes H-bonds too numerous/messy; users view them in Tab 1 |

**Deprecated/outdated:**
- VTK `SetLineStipplePattern()`: Does NOT work in OpenGL2 backend (only legacy OpenGL). The existing `create_hbond_actor()` already works around this with manual dash segments. Not relevant for Tab 2 since H-bonds are hidden.

## Open Questions

1. **O/H visual distinction within each phase**
   - What we know: CONTEXT says "OpenCode's discretion." Using `SingleColor` mode makes all atoms in a phase the same color.
   - What's unclear: Whether users need to distinguish O from H atoms within a phase
   - Recommendation: Start with `SingleColor` (all ice=cyan, all water=blue). If O/H distinction is needed later, add scalar coloring per phase actor using vtkLookupTable (O=darker shade, H=lighter shade of phase color). This is a low-risk enhancement.

2. **Performance threshold for simplification**
   - What we know: CONTEXT says "OpenCode's discretion — may simplify rendering above a threshold." `vtkMoleculeMapper.UseFastSettings()` sets UnitRadius with scale 0.6.
   - What's unclear: What atom count triggers simplification, and what simplification looks like
   - Recommendation: Start with small spheres + lines for all sizes. If performance issues arise at >5000 atoms, add option to switch to `RenderAtomsOff()` + point-based rendering. Monitor frame rate and log warnings.

3. **Whether Tab 2 should share Tab 1's VTK render window**
   - What we know: CONTEXT says "OpenCode's discretion." Shared render window saves GPU memory; separate widget is simpler architecture.
   - Recommendation: Separate widget. The data lifecycle is different (Tab 1 shows candidates, Tab 2 shows interface structure), camera settings differ, and coupling would add complexity for minimal gain.

## Sources

### Primary (HIGH confidence)
- VTK 9.5.2 installed in project — verified vtkMoleculeMapper API (AtomColorMode, BondColorMode, RenderBondsOff, SetAtomColor, UseFastSettings, SetAtomicRadiusTypeToUnitRadius)
- Existing codebase: `quickice/gui/molecular_viewer.py` — full MolecularViewerWidget implementation
- Existing codebase: `quickice/gui/vtk_utils.py` — candidate_to_vtk_molecule(), create_hbond_actor(), create_unit_cell_actor()
- Existing codebase: `quickice/gui/interface_panel.py` — InterfacePanel with placeholder
- Existing codebase: `quickice/structure_generation/types.py` — InterfaceStructure dataclass

### Secondary (MEDIUM confidence)
- VTK 9.6 nightly docs (vtkMoleculeMapper class reference) — confirmed API matches 9.5.2
- Color contrast analysis — verified with Python computation (luminance, contrast ratio, RGB distance)

### Tertiary (LOW confidence)
- None — all findings verified against installed VTK or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — VTK 9.5.2 and PySide6 6.10.2 already installed and used
- Architecture: HIGH — two-actor pattern follows existing codebase conventions, verified against VTK API
- Pitfalls: HIGH — MW skip and bond index alignment are verified from existing candidate_to_vtk_molecule() logic
- Colors: MEDIUM — contrast analysis is quantitative but perceptual experience may differ; cornflower blue recommended based on computed metrics

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable: VTK and PySide6 versions locked in project)
