# Architecture Patterns — Polycrystalline Builder Integration

**Domain:** QuickIce GUI architecture integration for polycrystalline builder
**Researched:** 2026-06-28

## Recommended Architecture

### Overall Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MainWindow                                                                  │
│                                                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ QTabWidget (7 tabs now)                                                 │ │
│ │ ┌────┬────┬────┬────┬────┬────┬─────────────────────────────────────┐ │ │
│ │ │Ice │Hyd │Int │Cust│Sol │Ion │ Polycrystal Builder (NEW Tab 6)   │ │ │
│ │ └────┴────┴────┴────┴────┴────┼─────────────────────────────────────┤ │ │
│ │                                │                                      │ │ │
│ │                                │ ┌──────────────┐┌───────────────┐  │ │ │
│ │                                │ │ Left Panel   ││ Right Panel   │  │ │ │
│ │                                │ │              ││ (QSplitter)   │  │ │ │
│ │                                │ │ Box Dims     ││               │  │ │ │
│ │                                │ │ Shape Tools  ││ ┌───────────┐│  │ │ │
│ │                                │ │ Region List  ││ │ 2D Editor ││  │ │ │
│ │                                │ │ Phase Assign ││ │QGraphicsVw││  │ │ │
│ │                                │ │ [Generate]   ││ └───────────┘│  │ │ │
│ │                                │ │ Progress     ││ ┌───────────┐│  │ │ │
│ │                                │ │ Log          ││ │ 3D Preview││  │ │ │
│ │                                │ │              ││ │ VTK       ││  │ │ │
│ │                                │ └──────────────┘│ └───────────┘│  │ │ │
│ │                                │                 └───────────────┘  │ │ │
│ │                                └──────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ _current_result  _current_interface_result  _current_hydrate_result        │
│ _current_solute_result  _current_custom_molecule_result  _current_ion_result│
│ _current_polycrystal_result (NEW)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Updated Cross-Tab Data Flow

```
Tab 0 (Ice)  ──candidates──▶  Tab 2 (Interface)  ──InterfaceStructure──▶  Tab 3 (Custom)
Tab 1 (Hydrate) ──HydrateStructure──▶  Tab 2 (Interface)
Tab 2 (Interface)  ──InterfaceStructure──▶  Tab 4 (Solute) ──▶ Tab 5 (Ion) ──▶ Export

Tab 6 (Polycrystal) ──PolycrystalStructure──▶  Tab 4 (Solute) ──▶ Tab 5 (Ion) ──▶ Export
         │                          │
         │  .to_interface_structure() │
         └────────────────────────────┘
```

The polycrystal tab produces a `PolycrystalStructure` that is **convertible** to `InterfaceStructure` via a `.to_interface_structure()` method. This allows the existing Solute → Ion → Export pipeline to consume polycrystal results without any changes to those tabs.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `PolycrystalPanel` (QWidget, Tab 6) | Tab container: left config panel + right split view | MainWindow (signals) |
| `ShapeEditor` (QGraphicsView) | 2D shape drawing, selection, editing | RegionModel (shape data), VTKPreview |
| `ShapeScene` (QGraphicsScene) | Item management, selection, z-order | ShapeEditor, QUndoStack |
| `RegionModel` | List of PhaseRegion (shapely Polygon + Z-range + phase_type) | ShapeEditor, VTKPreview, PhaseAssignPanel |
| `VTKPreview` (QVTKRenderWindowInteractor) | 3D translucent region preview + final structure preview | RegionModel (pre-generation), PolycrystalStructure (post-generation) |
| `PhaseAssignPanel` | Phase type dropdowns, Z-range spinboxes per region | RegionModel |
| `PolycrystalWorker` (QObject) | Background thread for multi-region generation | MainWindow (via ViewModel signals) |
| `PolycrystalConfig` (dataclass) | Region list + box dims + global settings | GUI → Core engine |
| `PolycrystalStructure` (dataclass) | Multi-phase result with per-region metadata | Core engine → GUI → Export |
| `PolycrystalGROMACSExporter` | Multi-phase GROMACS .gro/.top export | PolycrystalStructure |

### Data Flow: Generation Request

```
User draws regions in ShapeEditor
    ↓
RegionModel stores list of PhaseRegion
    ↓
User clicks "Generate Polycrystal"
    ↓
PolycrystalPanel emits generate_requested(RegionModel)
    ↓
MainWindow._on_polycrystal_generate():
    1. Build PolycrystalConfig from RegionModel
    2. Check candidates available (Tab 0 for ice phases, Tab 1 for hydrate phases)
    3. Create PolycrystalWorker(config)
    4. worker.moveToThread(thread)
    5. thread.start()
    ↓
PolycrystalWorker.run():
    For each region i in N:
        1. Check QThread.currentThread().isInterruptionRequested()
        2. status.emit(f"Generating region {i+1}/{N}: {region.phase_type}...")
        3. progress.emit( i * 100 // N )
        4. Generate crystal supercell (GenIce2) or hydrate (HydrateStructureGenerator)
        5. If rotation: apply rotation matrix
        6. Clip molecules by COM membership in polygon
        7. status.emit(f"Clipping molecules to region boundary...")
    Assemble all regions:
        8. Detect inter-region overlaps (cKDTree)
        9. Apply buffer zone strategy (remove overlapping molecules from BOTH sides)
        10. Fill remaining space with liquid water
        11. Resolve water-crystal overlaps (reuse overlap_resolver)
    ↓
    finished.emit(PolycrystalGenerationResult(success=True, result=PolycrystalStructure))
    ↓
MainWindow._on_polycrystal_generation_complete(result):
    1. self._current_polycrystal_result = result
    2. Update polycrystal panel VTK viewer
    3. Update solute panel with liquid volume
    4. Update ion panel with liquid volume
    5. Enable polycrystal source in solute/ion source dropdowns
```

### Data Flow: Post-Generation → Downstream Tabs

```
PolycrystalStructure produced by PolycrystalWorker
    ↓
MainWindow._current_polycrystal_result = polycrystal_structure
    ↓
┌──────────────────────────────────────────────────────────┐
│ Tab 4 (Solute):                                          │
│   Source dropdown adds "Polycrystal" option              │
│   When selected:                                         │
│     interface = polycrystal_structure.to_interface_structure()  │
│     SoluteInserter.insert_solutes(interface, config)    │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ Tab 5 (Ion):                                             │
│   Source dropdown adds "Polycrystal" option (via Solute) │
│   When selected:                                         │
│     Same as current Solute→Ion flow                      │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ Export:                                                   │
│   PolycrystalGROMACSExporter:                            │
│   .gro file: atoms in order (ice regions, water, guests) │
│   .top file: per-region moleculetypes + [molecules]      │
└──────────────────────────────────────────────────────────┘
```

## New Dataclasses

### PolycrystalConfig

```python
@dataclass
class PolycrystalConfig:
    """Configuration for polycrystalline structure generation.
    
    Attributes:
        box_x, box_y, box_z: Simulation box dimensions (nm)
        regions: List of PhaseRegion definitions
        overlap_threshold: O-O distance threshold for overlap detection (nm)
        buffer_width: Grain boundary buffer zone width (nm)
        seed: Random seed for reproducibility
    """
    box_x: float
    box_y: float
    box_z: float
    regions: list[PhaseRegion]
    overlap_threshold: float = 0.25  # nm
    buffer_width: float = 0.5  # nm
    seed: int = 42
    
    @classmethod
    def from_region_model(cls, model: RegionModel) -> "PolycrystalConfig":
        """Create config from GUI RegionModel."""
        ...
```

### PolycrystalStructure

```python
@dataclass
class PolycrystalStructure:
    """Result of polycrystalline structure generation.
    
    Contains the full multi-phase structure plus per-region metadata.
    Convertible to InterfaceStructure for downstream compatibility.
    
    Attributes:
        positions: (N_atoms, 3) all atom positions in nm
        atom_names: Atom names for all atoms
        cell: (3, 3) box cell vectors in nm (ROW vectors)
        molecule_index: List of MoleculeIndex for ALL molecules
        regions: List of RegionResult (per-region metadata after generation)
        total_ice_nmolecules: Total ice molecules across all regions
        total_water_nmolecules: Liquid water molecules (fill + buffer zones)
        total_guest_nmolecules: Guest molecules across all hydrate regions
        report: Generation report string
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]
    regions: list[RegionResult]
    total_ice_nmolecules: int
    total_water_nmolecules: int
    total_guest_nmolecules: int
    report: str
    
    def to_interface_structure(self) -> InterfaceStructure:
        """Convert to InterfaceStructure for downstream pipeline compatibility.
        
        Groups atoms as: ice atoms first, then water atoms, then guest atoms.
        This matches InterfaceStructure's expected ordering.
        """
        # Split molecule_index into ice/water/guest groups
        # Reorder positions accordingly
        # Return InterfaceStructure with:
        #   ice_atom_count = sum of all ice-region atoms
        #   water_atom_count = sum of all water atoms
        #   guest_atom_count = sum of all guest atoms
        ...
```

### RegionResult

```python
@dataclass
class RegionResult:
    """Per-region metadata after polycrystal generation.
    
    Attributes:
        region_id: Matches PhaseRegion.region_id
        phase_type: Crystal phase (e.g., "ice_ih", "hydrate_sI")
        n_molecules: Number of molecules in this region
        n_atoms: Number of atoms in this region
        rotation_applied: Euler angles applied (degrees)
        boundary_type: "same_phase", "buffer_zone", or "overlap_removed"
    """
    region_id: int
    phase_type: str
    n_molecules: int
    n_atoms: int
    rotation_applied: tuple[float, float, float] = (0.0, 0.0, 0.0)
    boundary_type: str = "buffer_zone"
```

## Patterns to Follow

### Pattern 1: Tab as Self-Contained Panel Widget

**What:** Each tab is a single QWidget subclass (e.g., `InterfacePanel`, `HydratePanel`, `SolutePanel`) that owns its entire UI: inputs, buttons, progress panel, log, and viewer.

**When:** For the polycrystal builder tab — follow the exact pattern of existing tabs.

**Example:** (from existing code)
```python
# main_window.py line ~200-221
self.interface_panel = InterfacePanel()
self.hydrate_panel = HydratePanel()
self.solute_panel = SolutePanel()
self.custom_molecule_panel = CustomMoleculePanel()
self.ion_panel = IonPanel()

self.tab_widget.addTab(self.interface_panel, "Interface Construction")
self.tab_widget.addTab(self.hydrate_panel, "Hydrate Generation")
# ...
```

**For polycrystal:** `self.polycrystal_panel = PolycrystalPanel()` — same pattern.

### Pattern 2: Worker as QObject + moveToThread

**What:** Background workers use QObject subclass + moveToThread(QThread), NOT QThread subclass directly.

**When:** For PolycrystalWorker — follow `GenerationWorker`, `InterfaceGenerationWorker`, `CustomMoleculeWorker` pattern.

**Why:** The AGENTS.md says `HydrateWorker` subclasses QThread directly and is NOT to be "fixed." But the newer workers (workers.py, custom_molecule_worker.py) use the QObject+moveToThread pattern. For new code, use the newer pattern.

**Example:**
```python
class PolycrystalWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)  # PolycrystalGenerationResult
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, config: PolycrystalConfig):
        super().__init__()
        self._config = config
    
    def run(self):
        try:
            for i, region in enumerate(self._config.regions):
                if QThread.currentThread().isInterruptionRequested():
                    self.cancelled.emit()
                    return
                self.status.emit(f"Region {i+1}/{len(self._config.regions)}: {region.phase_type}")
                self.progress.emit(int(i / len(self._config.regions) * 80))
                # Generate, clip, rotate...
            
            self.status.emit("Resolving inter-region boundaries...")
            # Buffer zone, overlap resolve, water fill...
            
            self.progress.emit(100)
            self.finished.emit(PolycrystalGenerationResult(success=True, result=structure))
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(PolycrystalGenerationResult(success=False, error=str(e)))
```

### Pattern 3: Source Dropdown Extension

**What:** When a new tab produces a structure that downstream tabs can consume, add it as a "Source" option in the downstream tab's source dropdown.

**When:** For polycrystal → solute/ion integration.

**Example:** (existing pattern from solute_panel.py)
```python
# Current sources: "Interface", "Custom Molecule"
# Add: "Polycrystal"

class SolutePanel:
    def get_current_source(self):
        # Returns "Interface", "Custom Molecule", or "Polycrystal"
        return self.source_combo.currentText()
```

**In MainWindow:**
```python
def _on_insert_solutes(self):
    current_source = self.solute_panel.get_current_source()
    if current_source == "Polycrystal":
        if self._current_polycrystal_result is None:
            # Warn: "Generate polycrystal first"
            return
        interface = self._current_polycrystal_result.to_interface_structure()
        # ... same as current Interface source flow
```

### Pattern 4: Two-Panel Horizontal Layout

**What:** Each tab uses a two-panel horizontal layout: narrow left config panel + wide right panel for viewer(s).

**When:** For PolycrystalPanel — matches InterfacePanel, HydratePanel, SolutePanel.

**Example:** (from interface_panel.py)
```python
top_layout = QHBoxLayout(self)
top_layout.setContentsMargins(20, 20, 20, 20)
# Left: config controls (stretch=2)
# Right: mode params + viewer (stretch=3)
top_layout.addLayout(left_layout, stretch=2)
top_layout.addLayout(right_layout, stretch=3)
```

**For polycrystal:** Right panel gets QSplitter with 2D editor (top) + 3D preview (bottom), or horizontal splitter (2D left | 3D right) as recommended by shape-gui research.

### Pattern 5: VTK Availability Guard

**What:** All VTK-dependent viewers check `_VTK_AVAILABLE` at import time and provide fallback widgets.

**When:** For PolycrystalViewer — follow the exact pattern from interface_panel.py and hydrate_viewer.py.

**Example:** (from interface_panel.py lines 28-43)
```python
_VTK_AVAILABLE = False
try:
    if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
        _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
    else:
        _VTK_AVAILABLE = True
    if _VTK_AVAILABLE:
        from quickice.gui.polycrystal_viewer import PolycrystalViewerWidget
except Exception:
    _VTK_AVAILABLE = False
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Polycrystal as Interface Sub-Mode

**What:** Adding "Polycrystal" as a 4th mode in the Interface tab's QStackedWidget (alongside Slab, Pocket, Piece).

**Why bad:** 
- The Interface tab has no QGraphicsView — would need to add one just for polycrystal mode
- The Interface tab's right column is already a QStackedWidget of mode-specific params + viewer
- Adding a shape editor + 2D/3D split view + region list + phase assignment panel would completely dominate the tab
- Mode switching would destroy the shape editor state (QUndoStack, region model)
- User confusion: "Which mode should I use?" — slab and polycrystal have overlapping capabilities but very different UX
- Code organization: 500+ lines of polycrystal-specific code in interface_panel.py would bloat it beyond maintainability

**Instead:** New dedicated tab. Keep Interface tab for simple single-phase interfaces.

### Anti-Pattern 2: PolycrystalStructure as InterfaceStructure Subclass

**What:** Making `PolycrystalStructure` inherit from `InterfaceStructure`.

**Why bad:** 
- InterfaceStructure has many duck-typed attributes (solute_type, custom_molecule_positions, etc.) that are set at runtime by downstream workflows. Subclassing creates a fragile coupling.
- PolycrystalStructure has fundamentally different metadata (per-region breakdown, boundary info) that InterfaceStructure doesn't understand.
- InterfaceStructure's atom ordering (ice → water → guest) is a constraint that PolycrystalStructure may not naturally satisfy (multi-region structures have interleaved ice/water/guest atoms).

**Instead:** Separate dataclass with `.to_interface_structure()` conversion method. This decouples the two types while enabling downstream compatibility.

### Anti-Pattern 3: Shared QUndoStack Between Tabs

**What:** Making the polycrystal shape editor's undo stack accessible from other tabs.

**Why bad:** Undo/redo context should be scoped to the active editor. Cross-tab undo would be confusing (Ctrl+Z in solute tab undoes a shape change).

**Instead:** QUndoStack lives on PolycrystalPanel only. MainWindow's Edit menu can add "Undo (Polycrystal)" action when Tab 6 is active, but the stack itself is owned by PolycrystalPanel.

### Anti-Pattern 4: Synchronous Generation in Main Thread

**What:** Running polycrystal generation synchronously in the GUI thread because "it's only a few regions."

**Why bad:** Multi-region generation with GenIce2 calls + overlap resolution + water filling takes 0.3–30s (per poly-gen scalability analysis). Even 0.3s is enough to cause visible UI freezing.

**Instead:** Always use QThread-based worker for generation, even for single-region generation.

### Anti-Pattern 5: Polycrystal Result as Duck-Typed Attributes on InterfaceStructure

**What:** Adding `._polycrystal_regions`, `._polycrystal_boundary_info` etc. as runtime attributes on an InterfaceStructure (extending the existing CP-01 pattern).

**Why bad:** CP-01 was a pragmatic shortcut for simple attribute forwarding (solute_type, custom_molecule_positions). Polycrystal metadata is complex (list of RegionResult objects) and belongs in its own typed dataclass, not as loose attributes on a different structure.

**Instead:** Use `_current_polycrystal_result` as a separate attribute on MainWindow. Conversion to InterfaceStructure is explicit via `.to_interface_structure()`.

## Multi-Phase VTK Rendering Architecture

### Phase Color Scheme

```python
# Per-phase color constants for VTK rendering
PHASE_COLORS = {
    "liquid":      (0.39, 0.58, 0.93),   # Cornflower blue (existing water color)
    "ice_Ih":      (0.0,  0.8,  0.8),     # Cyan (existing ice color)
    "ice_II":      (0.3,  0.5,  0.9),     # Periwole blue
    "ice_III":     (0.5,  0.6,  0.9),     # Slate blue
    "ice_V":       (0.4,  0.7,  0.9),     # Sky blue
    "ice_VI":      (0.2,  0.4,  0.8),     # Dark blue
    "hydrate_sI":  (0.2,  0.8,  0.2),     # Green
    "hydrate_sII": (0.8,  0.8,  0.0),     # Yellow
    "hydrate_sH":  (0.8,  0.5,  0.0),     # Orange
    "guest":       (0.8,  0.8,  0.8),     # Gray (existing guest color)
    "buffer_zone": (0.6,  0.6,  0.6),     # Light gray (disordered water)
}
```

### Rendering Pipeline

```
PolycrystalStructure
    ↓
For each region in structure.regions:
    1. Extract positions for molecules belonging to this region
    2. Create bond-line actor with PHASE_COLORS[region.phase_type]
    3. Add actor to renderer
    ↓
For liquid water (not in any region):
    4. Create bond-line actor with WATER_COLOR
    5. Add actor to renderer
    ↓
For guest molecules (in hydrate regions):
    6. Create ball-and-stick actor with GUEST_COLOR
    7. Add actor to renderer
    ↓
Create unit cell actor
    ↓
Add phase color legend widget (QLabel with colored dots)
    ↓
Auto-fit camera
```

### VTK Actor Group Naming Convention

```python
# Track actors by phase region for visibility toggling
self._region_actors: dict[int, vtkActor] = {}     # region_id → bond actor
self._water_actor: vtkActor | None = None          # Liquid water
self._guest_actors: dict[str, vtkActor] = {}       # guest_type → ball-and-stick actor
self._unit_cell_actor: vtkActor | None = None
```

## GROMACS Export Architecture

### Per-Region Moleculetype Tracking

For polycrystalline structures, the GROMACS `.top` file needs per-region moleculetypes when:
1. Multiple hydrate regions have different guest types (e.g., sI with CH4 + sII with THF)
2. The user needs to distinguish molecules from different grain orientations (advanced use case, not MVP)

**MVP approach:** All ice regions share the same moleculetype "SOL". All hydrate regions share per-guest-type moleculetypes ("CH4_H", "THF_H"). This matches existing export behavior and is sufficient for MD simulations (all TIP4P-ICE water is parameterized identically regardless of crystal orientation).

**Enhanced approach (post-MVP):** Per-region moleculetypes like "SOL_G1", "SOL_G2" etc. for tracking grain membership. This enables per-grain analysis in MD trajectories but requires modifying the GROMACS export pipeline.

### `.top` File Structure for Multi-Phase Polycrystal

```
[ defaults ]
1     2     yes     0.5     0.8333

[ atomtypes ]
; TIP4P-ICE water
OW_ice  OW_ice  8  15.9994  0.0  A  3.16680e-1  8.82110e-1
HW_ice  HW_ice  1   1.0080  0.0  A  0.0          0.0
MW      MW      0   0.0000  0.0  V  0.0          0.0
; CH4 (GAFF2) — shared by all hydrate regions with CH4 guests
c3      c3      6  12.0107  0.0  A  3.39771e-1  4.51035e-1
hc      hc      1   1.0079  0.0  A  2.60018e-1  8.70272e-2
; THF (GAFF2) — for hydrate regions with THF guests
os      os      8  15.9994  0.0  A  3.15610e-1  3.03758e-1
c5      c5      6  12.0107  0.0  A  3.39771e-1  4.51035e-1
h1      h1      1   1.0079  0.0  A  2.42200e-1  8.70272e-2

#include "tip4p-ice.itp"
#include "ch4_hydrate.itp"     ; For CH4 guest in hydrate cages
#include "thf_hydrate.itp"     ; For THF guest in hydrate cages (if present)

[ system ]
Polycrystalline ice system

[ molecules ]
;   Compound       #mols
SOL              12000    ; All TIP4P-ICE water (ice + liquid)
CH4_H              80     ; CH4 guests in hydrate cages
THF_H              10     ; THF guests in hydrate cages (if present)
```

Note: The `[molecules]` section groups all TIP4P-ICE water as "SOL" regardless of phase. This is correct because the water model is the same in all phases — only the atomic arrangement differs.

## TabIndex Enum Update

```python
# constants.py — updated
class TabIndex(IntEnum):
    ICE = 0
    HYDRATE = 1
    INTERFACE = 2
    CUSTOM = 3
    SOLUTE = 4
    ION = 5
    POLYCRYSTAL = 6  # NEW
```

## Sources

- QuickIce `main_window.py`: Direct code analysis — tab structure, signal connections, worker pattern (HIGH confidence)
- QuickIce `workers.py`: Direct code analysis — GenerationWorker, InterfaceGenerationWorker pattern (HIGH confidence)
- QuickIce `viewmodel.py`: Direct code analysis — MVVM pattern, signal forwarding (HIGH confidence)
- QuickIce `types.py`: Direct code analysis — all dataclass definitions, InterfaceStructure atom ordering (HIGH confidence)
- QuickIce `interface_panel.py`: Direct code analysis — two-column layout, QStackedWidget mode switching (HIGH confidence)
- QuickIce `interface_viewer.py`: Direct code analysis — VTK rendering pipeline (HIGH confidence)
- QuickIce `export.py`: Direct code analysis — export handler pattern (HIGH confidence)
- QuickIce `gromacs_writer.py`: Direct code analysis — write_multi_molecule_top_file, atomtype dedup, [molecules] section (HIGH confidence)
- QuickIce `hydrate_worker.py`: Direct code analysis — QThread subclass pattern (HIGH confidence)
- QuickIce `custom_molecule_worker.py`: Direct code analysis — QObject+moveToThread pattern (HIGH confidence)
- QuickIce `moleculetype_registry.py`: Direct code analysis — _H/_L suffix naming (HIGH confidence)
- AGENTS.md: CP-01 decision, worker threading guidance (HIGH confidence)
- Wave 1 shape-gui/ARCHITECTURE.md: PhaseRegion data model, QGraphicsView pattern (HIGH confidence)
- Wave 1 poly-gen/ARCHITECTURE.md: Generate-Clip-Resolve pipeline (HIGH confidence)
- Wave 1 phase-boundary/SUMMARY.md: Three-tier boundary strategy (HIGH confidence)
