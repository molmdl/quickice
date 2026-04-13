# Architecture Research: QuickIce v4.0 Molecule Insertion

**Domain:** Molecular dynamics ice structure generation — adding molecule insertion (hydrate + ion) to existing MVVM GUI application
**Researched:** 2026-04-14
**Confidence:** HIGH (direct codebase analysis + verified GenIce2 API + VTK multi-actor testing)

---

## System Overview

QuickIce v4.0 adds two new tabs to the existing 4-tab layout and extends three subsystems (generation, visualization, export). The architecture must preserve the MVVM pattern, avoid disrupting existing tabs, and allow new molecule types to flow through the same data pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Presentation (GUI) Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ Tab 1    │  │ Tab 2    │  │ Tab 3        │  │ Tab 4                │    │
│  │ Ice Gen  │  │ Hydrate  │  │ Interface    │  │ Insert to Liquid     │    │
│  │ (EXIST)  │  │ (NEW)    │  │ (EXIST)      │  │ (NEW)                │    │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └──────────┬───────────┘    │
│       │              │               │                      │                │
├───────┴──────────────┴───────────────┴──────────────────────┴────────────────┤
│                        ViewModel Layer                                      │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐   │
│  │ MainViewModel        │  │ HydrateViewModel    │  │ InsertViewModel   │   │
│  │ (EXIST, extended)    │  │ (NEW)               │  │ (NEW)              │   │
│  └──────────┬───────────┘  └──────────┬──────────┘  └──────────┬────────┘   │
│             │                         │                         │             │
├─────────────┴─────────────────────────┴─────────────────────────┴─────────────┤
│                        Worker Layer (QThread)                               │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐          │
│  │ Generation-  │  │ Hydrate-         │  │ Insertion-              │          │
│  │ Worker       │  │ Worker           │  │ Worker                  │          │
│  │ (EXIST)       │  │ (NEW)            │  │ (NEW)                   │          │
│  └──────┬───────┘  └────────┬─────────┘  └────────────┬───────────┘          │
│         │                   │                          │                      │
├─────────┴───────────────────┴──────────────────────────┴───────────────────────┤
│                        Domain Layer                                          │
│  ┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │ phase_mapping/   │  │ structure_generation/│  │ ranking/                 │  │
│  │ (EXIST, unchanged)│  │ generator.py (EXTEND)│  │ (EXIST, unchanged)       │  │
│  │                 │  │ hydrate_gen.py (NEW)  │  │                         │  │
│  │                 │  │ ion_inserter.py (NEW) │  │                         │  │
│  │                 │  │ overlap_resolver.py   │  │                         │  │
│  │                 │  │ (EXIST, reused)       │  │                         │  │
│  └─────────────────┘  └──────────────────────┘  └─────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │ gui/vtk_utils.py│  │ gui/molecular_       │  │ output/                  │  │
│  │ (EXTEND)        │  │ viewer.py (EXTEND)  │  │ gromacs_writer.py        │  │
│  │                 │  │ interface_viewer.py  │  │ (EXTEND for multi-type)  │  │
│  └─────────────────┘  │ (EXTEND)            │  └─────────────────────────┘  │
│                       └─────────────────────┘                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                        Data Layer                                           │
│  ┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │ Candidate       │  │ HydrateResult      │  │ InsertedStructure        │  │
│  │ (EXIST)         │  │ (NEW)              │  │ (NEW, extends            │  │
│  │                 │  │                     │  │  InterfaceStructure)     │  │
│  └─────────────────┘  └─────────────────────┘  └─────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────────┐                               │
│  │ Interface-     │  │ MoleculeType        │                               │
│  │ Structure      │  │ (NEW enum/flag)     │                               │
│  │ (EXIST, unchanged)│  │                     │                               │
│  └─────────────────┘  └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Existing Architecture (v3.5)

### Current Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `MainWindow` | Tab assembly, signal routing, export menus | `gui/main_window.py` |
| `MainViewModel` | Worker lifecycle, state management, signal forwarding | `gui/viewmodel.py` |
| `GenerationWorker` | Ice generation pipeline on QThread | `gui/workers.py` |
| `InterfaceGenerationWorker` | Interface generation pipeline on QThread | `gui/workers.py` |
| `InputPanel` | T/P/N inputs with validation | `gui/view.py` |
| `InterfacePanel` | Interface mode controls, candidate dropdown | `gui/interface_panel.py` |
| `MolecularViewerWidget` | VTK ball-and-stick for single candidate | `gui/molecular_viewer.py` |
| `InterfaceViewerWidget` | VTK line-based viewer for ice+water interface | `gui/interface_viewer.py` |
| `DualViewerWidget` | Side-by-side candidate comparison | `gui/dual_viewer.py` |
| `vtk_utils` | Candidate→vtkMolecule, H-bond detection, unit cell | `gui/vtk_utils.py` |
| `IceStructureGenerator` | GenIce2 wrapper, GRO parsing, supercell calculation | `structure_generation/generator.py` |
| `overlap_resolver` | PBC-aware cKDTree collision detection | `structure_generation/overlap_resolver.py` |
| `GROMACSExporter` | File dialog, .gro/.top/.itp write orchestration | `gui/export.py` |
| `InterfaceGROMACSExporter` | Interface-specific GROMACS export | `gui/export.py` |

### Current Data Flow

```
Tab 1: Ice Generation
  User → InputPanel(T,P,N) → MainWindow → MainViewModel.start_generation()
    → GenerationWorker(T,P,N) → lookup_phase() → generate_candidates() → rank_candidates()
    → ranked_candidates_ready signal → DualViewerWidget.set_candidates()

Tab 3 (current Tab 2): Interface Construction
  User → InterfacePanel(mode,box,thickness) → MainWindow → MainViewModel.start_interface_generation()
    → InterfaceGenerationWorker(candidate,config) → generate_interface()
    → interface_generation_complete signal → InterfaceViewerWidget.set_interface_structure()

Cross-tab: Tab 1._current_result → Tab 3 InterfacePanel.candidate_dropdown
```

### Current Data Types

| Type | Purpose | Key Fields |
|------|---------|------------|
| `Candidate` | Single ice structure | `positions`, `atom_names`, `cell`, `nmolecules`, `phase_id`, `seed`, `metadata` |
| `GenerationResult` | Multiple candidates | `candidates`, `requested_nmolecules`, `actual_nmolecules`, `phase_id` |
| `InterfaceConfig` | Interface parameters | `mode`, `box_x/y/z`, `seed`, `ice_thickness`, `water_thickness`, `overlap_threshold` |
| `InterfaceStructure` | Combined ice+water result | `positions`, `atom_names`, `cell`, `ice_atom_count`, `water_atom_count`, `mode`, `report` |
| `RankedCandidate` | Scored candidate | `candidate`, `energy_score`, `density_score`, `combined_score`, `rank` |
| `RankingResult` | All ranked candidates | `ranked_candidates` |

### Key Architectural Constraints

1. **MVVM signal/slot pattern**: View → ViewModel → Worker → signal → View. No direct domain calls from View.
2. **QThread worker-object pattern**: Workers are QObjects moved to QThread (NOT subclassing QThread).
3. **GenIce2 global state**: `np.random` state saved/restored around each generation call. Sequential only.
4. **Unit convention**: All positions in nm. PDB exports convert to Å (×10). GROMACS stays in nm.
5. **VTK availability check**: `_VTK_AVAILABLE` flag at import time; graceful degradation.
6. **Single SOL molecule type**: Current GROMACS export writes one `[moleculetype]` for all water.

---

## New Architecture (v4.0)

### Tab 2: Molecules to Ice (Hydrate Generation)

#### New Components

| Component | Responsibility | Type | File |
|-----------|----------------|------|------|
| `HydratePanel` | UI for hydrate lattice selection, guest molecule, occupancy | NEW | `gui/hydrate_panel.py` |
| `HydrateViewModel` (in `MainViewModel`) | Worker lifecycle for hydrate generation | EXTEND | `gui/viewmodel.py` |
| `HydrateGenerationWorker` | Hydrate generation on QThread | NEW | `gui/workers.py` |
| `HydrateStructureGenerator` | GenIce2 hydrate API wrapper | NEW | `structure_generation/hydrate_gen.py` |
| `HydrateResult` | Hydrate generation output | NEW | `structure_generation/types.py` |
| `HydrateViewerWidget` | VTK viewer for hydrate structures (ice + guests) | NEW | `gui/hydrate_viewer.py` |
| `HydrateGROMACSExporter` | Multi-type GROMACS export for hydrates | NEW | `gui/export.py` |

#### Data Flow — Tab 2

```
Tab 2: Molecules to Ice
  User → HydratePanel(lattice, guest, occupancy, supercell) → MainWindow
    → MainViewModel.start_hydrate_generation()
    → HydrateGenerationWorker(lattice, guests, density, supercell)
      → HydrateStructureGenerator.generate_all()
        → GenIce(lattice, density, reshape=supercell).generate_ice(formatter, water, guests=...)
        → _parse_gro_multi_molecule()  [EXTEND existing _parse_gro]
      → ranked_candidates or direct HydrateResult
    → hydrate_generation_complete signal → HydrateViewerWidget.set_hydrate_structure()
```

**Key difference from Tab 1:** Hydrate generation does NOT use phase lookup. The user selects a hydrate lattice type directly (CS1/sI, CS2/sII, HS3/sH) and a guest molecule. GenIce2's hydrate lattice modules already know the correct unit cell and cage positions — no T→P→phase mapping needed.

**Key difference from Tab 1 ranking:** Hydrate structures have deterministic guest placement (cages are filled according to occupancy). The concept of "ranking" multiple candidates with different seeds is less meaningful for hydrates because the lattice geometry is fixed. Instead, Tab 2 generates ONE hydrate structure per configuration. Optional: multiple supercell sizes for system size selection.

#### HydrateResult Data Type

```python
@dataclass
class HydrateResult:
    """Result of hydrate structure generation.
    
    Unlike GenerationResult (10 candidates), hydrate generation produces
    a single structure per configuration because cage occupancy is deterministic.
    
    Attributes:
        positions: (N_atoms, 3) all atom positions in nm (water + guest atoms)
        atom_names: Atom names for all atoms (e.g., ["OW", "HW1", "HW2", "MW", "C", "H", ...])
        molecule_types: List of MoleculeType flags per atom (e.g., ["water", "water", ..., "guest", ...])
        cell: (3, 3) cell vectors in nm
        water_nmolecules: Number of water molecules in hydrate framework
        guest_nmolecules: Number of guest molecule instances
        guest_molecule_name: Name of guest molecule (e.g., "ch4", "co2")
        lattice_name: GenIce2 lattice name (e.g., "CS1", "CS2")
        report: Generation report string
    """
    positions: np.ndarray
    atom_names: list[str]
    molecule_types: list[str]  # Per-atom type: "water", "guest"
    cell: np.ndarray
    water_nmolecules: int
    guest_nmolecules: int
    guest_molecule_name: str
    lattice_name: str
    report: str
```

#### Integration Points — Tab 2

| Integration Point | Existing Component | Change Required |
|---|---|---|
| Tab insertion | `MainWindow._setup_ui()` | Insert new tab at index 1 (before current Tab 2) |
| Worker lifecycle | `MainViewModel` | Add hydrate signals + `start_hydrate_generation()` |
| GRO parsing | `IceStructureGenerator._parse_gro()` | Extend to handle multi-residue GRO (SOL + CH4, etc.) |
| VTK visualization | `vtk_utils.py` | Add `hydrate_to_vtk_molecules()` returning water + guest mols |
| GROMACS export | `gromacs_writer.py` | Add `write_hydrate_gro_file()`, `write_hydrate_top_file()` |
| Bundled data | `quickice/data/` | Add `ions-na-cl.itp`, `ch4.itp`, `co2.itp` |
| Menu bar | `MainWindow._create_menu_bar()` | Add "Export Hydrate for GROMACS..." action with shortcut |

---

### Tab 4: Insert to Liquid (Ion + Molecule Insertion)

#### New Components

| Component | Responsibility | Type | File |
|-----------|----------------|------|------|
| `InsertPanel` | UI for NaCl concentration, custom molecule upload, placement mode | NEW | `gui/insert_panel.py` |
| `InsertViewModel` (in `MainViewModel`) | Worker lifecycle for insertion | EXTEND | `gui/viewmodel.py` |
| `InsertionWorker` | Ion/molecule insertion on QThread | NEW | `gui/workers.py` |
| `IonInserter` | NaCl concentration calculation, random ion placement | NEW | `structure_generation/ion_inserter.py` |
| `MoleculeInserter` | Custom molecule placement (random + custom COM) | NEW | `structure_generation/molecule_inserter.py` |
| `InsertedStructure` | Interface + ions/molecules result | NEW | `structure_generation/types.py` |
| `InsertViewerWidget` | VTK viewer with 4+ molecule types | NEW | `gui/insert_viewer.py` |
| `InsertGROMACSExporter` | Multi-type GROMACS export | NEW | `gui/export.py` |

#### Data Flow — Tab 4

```
Tab 4: Insert to Liquid
  User → InsertPanel(NaCl concentration, or .gro/.itp file paths) → MainWindow
    → MainViewModel.start_insertion()
    → InsertionWorker(interface_structure, insertion_config)
      → IonInserter.insert_nacl(interface_structure, concentration)
        → Calculate ion count from concentration + volume
        → Generate random positions in liquid region (z > ice_atom_count boundary)
        → Detect overlaps with existing water molecules via cKDTree
        → Remove overlapping water molecules (whole molecules only)
        → Add Na+ and Cl- atoms to structure
      → OR MoleculeInserter.insert_molecule(interface_structure, gro_path, placement)
        → Parse .gro file for molecule coordinates
        → Place at random or user-specified COM
        → Detect overlaps via cKDTree
        → Remove overlapping water molecules
        → Add molecule atoms to structure
    → insertion_complete signal → InsertViewerWidget.set_inserted_structure()
```

**Key dependency:** Tab 4 requires an `InterfaceStructure` from Tab 3 (current Tab 2). It reads `ice_atom_count` to know which atoms are in the ice phase (untouchable) vs liquid phase (replaceable).

**Reused component:** `overlap_resolver.py` — The existing `detect_overlaps()` and `remove_overlapping_molecules()` functions work for ion insertion. Ion positions are tested against liquid water oxygens, and overlapping water molecules are removed wholesale.

#### InsertedStructure Data Type

```python
@dataclass
class InsertedStructure:
    """Result of ion/molecule insertion into an interface structure.
    
    Extends InterfaceStructure with additional molecule type information
    and per-atom type tagging for multi-actor VTK visualization.
    
    Attributes:
        positions: (N_atoms, 3) all atom positions in nm (ice + water + ions + molecules)
        atom_names: Atom names for all atoms (e.g., ["OW", "HW1", "HW2", "MW", "Na", "Cl", ...])
        molecule_types: Per-atom type flag (e.g., "ice_water", "liquid_water", "ion", "guest")
        cell: (3, 3) cell vectors in nm
        ice_atom_count: Boundary between ice and liquid (same as InterfaceStructure)
        water_atom_count: Number of liquid water atoms (may decrease after ion replacement)
        ion_atom_count: Number of ion atoms added (0 if no ions)
        molecule_atom_count: Number of custom molecule atoms (0 if none)
        ice_nmolecules: Number of ice molecules
        water_nmolecules: Number of remaining liquid water molecules
        ion_counts: Dict of ion counts {"Na": n_na, "Cl": n_cl}
        guest_molecules: List of guest molecule names inserted
        mode: Original interface mode
        report: Generation report string
    """
    positions: np.ndarray
    atom_names: list[str]
    molecule_types: list[str]
    cell: np.ndarray
    ice_atom_count: int
    water_atom_count: int
    ion_atom_count: int = 0
    molecule_atom_count: int = 0
    ice_nmolecules: int = 0
    water_nmolecules: int = 0
    ion_counts: dict = field(default_factory=dict)
    guest_molecules: list = field(default_factory=list)
    mode: str = ""
    report: str = ""
```

#### Integration Points — Tab 4

| Integration Point | Existing Component | Change Required |
|---|---|---|
| Tab insertion | `MainWindow._setup_ui()` | Add as Tab 4 (after Interface Construction) |
| Cross-tab data | `MainViewModel._last_interface_result` | Read `InterfaceStructure` from Tab 3 |
| Collision detection | `overlap_resolver.py` | Reuse `detect_overlaps()` and `remove_overlapping_molecules()` |
| VTK visualization | `vtk_utils.py` | Add `inserted_to_vtk_molecules()` returning 4+ vtkMolecule objects |
| GROMACS export | `gromacs_writer.py` | Add `write_inserted_gro_file()`, `write_inserted_top_file()` |
| Menu bar | `MainWindow._create_menu_bar()` | Add "Export Inserted for GROMACS..." action |

---

### 3D Viewer Enhancements

#### Multi-Actor Architecture

The current viewer architecture uses a single `vtkMoleculeMapper` + `vtkActor` per phase:
- `MolecularViewerWidget` (Tab 1): 1 mapper/actor pair, 1 molecule type
- `InterfaceViewerWidget` (Tab 3): 2 mapper/actor pairs (ice bonds + water bonds as line actors)

For v4.0, we need per-molecule-type rendering with distinct styles:

```python
# Molecule type → VTK actor configuration
MOLECULE_TYPE_STYLES = {
    "ice_water":     {"style": "lines",  "color": (0.0, 0.8, 0.8)},     # Cyan
    "liquid_water":  {"style": "lines",  "color": (0.39, 0.58, 0.93)},  # Cornflower blue
    "ion_na":        {"style": "vdw",    "color": (1.0, 1.0, 0.0)},     # Yellow
    "ion_cl":        {"style": "vdw",    "color": (0.0, 1.0, 0.0)},     # Green
    "guest_small":   {"style": "ball_and_stick", "color": (1.0, 0.5, 0.0)},  # Orange
    "guest_large":   {"style": "stick",  "color": (0.8, 0.0, 0.8)},     # Magenta
}
```

#### New VTK Utility Functions

| Function | Purpose | File |
|----------|---------|------|
| `hydrate_to_vtk_molecules(result)` | Split hydrate into water + guest vtkMolecule objects | `vtk_utils.py` |
| `inserted_to_vtk_molecules(result)` | Split inserted structure into ice + water + ions + guests | `vtk_utils.py` |
| `create_multi_actor_viewer(molecules_dict, styles)` | Create renderer with per-type actors | NEW in viewer utility |

Each function returns a dict of `{molecule_type: vtkMolecule}`, and the viewer creates one `vtkMoleculeMapper` + `vtkActor` per entry with the appropriate style and color from `MOLECULE_TYPE_STYLES`.

#### Per-Type Visibility and Style Controls

```python
class MoleculeTypeControls(QWidget):
    """Widget for toggling visibility and selecting styles per molecule type.
    
    Creates one row per molecule type:
    [✓] Ice Water    [Lines ▼]  [■ Color]
    [✓] Liquid Water  [Lines ▼]  [■ Color]
    [✓] Na⁺ Ions     [VDW ▼]    [■ Color]
    [✓] Cl⁻ Ions     [VDW ▼]    [■ Color]
    [✓] CH₄ Guest    [Ball&Stick ▼] [■ Color]
    """
```

This widget is shared across Tab 2 (hydrate viewer) and Tab 4 (insert viewer).

---

### GROMACS Export Extensions

#### Current Export Pattern (SOL only)

The current `write_interface_top_file()` writes:
```
[ moleculetype ]
SOL             3
#include "tip4p-ice.itp"
[ molecules ]
SOL             N_total
```

#### New Export Pattern (Multi-type)

```python
# .top file structure for inserted structure:
[ moleculetype ]
SOL             3
#include "tip4p-ice.itp"

[ moleculetype ]
NA              1
#include "ions-na-cl.itp"

[ moleculetype ]
CL              1
#include "ions-na-cl.itp"

[ moleculetype ]           # Only if guest molecules present
CH4            3
#include "ch4.itp"

[ system ]
QuickIce Inserted Structure

[ molecules ]
SOL            {n_water}
NA             {n_na}
CL             {n_cl}
CH4            {n_ch4}    # Only if present
```

#### New Data Files to Bundle

| File | Purpose | Location |
|------|---------|----------|
| `ions-na-cl.itp` | Na⁺ and Cl⁻ topology (Joung-Cheatham) | `quickice/data/ions-na-cl.itp` |
| `ch4.itp` | Methane topology (OPLS-AA) | `quickice/data/ch4.itp` |
| `co2.itp` | Carbon dioxide topology | `quickice/data/co2.itp` |

These follow the existing pattern of `tip4p-ice.itp` (bundled in `quickice/data/`).

---

## Component Boundaries

### Clear Boundaries

| Boundary | Protocol | Rationale |
|----------|----------|-----------|
| Tab UI → ViewModel | Qt signals/slots | MVVM pattern: no direct domain calls from View |
| ViewModel → Worker | QObject.moveToThread(QThread) | Existing pattern: worker-object, not QThread subclass |
| Worker → Domain | Direct function calls in `run()` | Existing pattern: import inside run() for thread safety |
| Domain → GenIce2 | Python API call | Existing: `GenIce(lattice, density).generate_ice(formatter, water)` |
| Domain → cKDTree | Function call with numpy arrays | Existing: `detect_overlaps(positions, threshold, box)` |
| VTK utils → Data types | Function accepting dataclass | Existing: `candidate_to_vtk_molecule(Candidate)` |
| GROMACS writer → Data types | Function accepting dataclass | Existing: `write_gro_file(Candidate)` |

### New Boundaries

| Boundary | Protocol | Rationale |
|----------|----------|-----------|
| HydratePanel → MainWindow | Qt signals (like InterfacePanel) | Consistent MVVM pattern |
| InsertPanel → MainWindow | Qt signals (like InterfacePanel) | Consistent MVVM pattern |
| HydrateStructureGenerator → GenIce2 | GenIce API with `guests` parameter | New: hydrate lattice + guest molecule |
| IonInserter → overlap_resolver | Function call | Reuse existing cKDTree functions |
| Multi-actor viewer → vtk_utils | Dict of vtkMolecule objects | New pattern for per-type rendering |

### Cross-Tab Data Flow

```
Tab 1 (Ice Gen) ──→ Tab 3 (Interface): candidate dropdown (EXISTING)
Tab 3 (Interface) ──→ Tab 4 (Insert): InterfaceStructure reference (NEW)
Tab 2 (Hydrate)  ──→ None: standalone, no dependency on other tabs
Tab 4 (Insert)   ──→ None: reads from Tab 3 but doesn't produce data for others
```

**Tab 4 dependency on Tab 3:** The `InsertPanel` needs a dropdown populated with results from Tab 3, mirroring the existing pattern where Tab 3 (current Tab 2) gets candidates from Tab 1. The `MainViewModel` stores `_last_interface_result` which Tab 4 reads.

**Tab 2 independence:** Hydrate generation uses GenIce2 directly with different lattice types (CS1, CS2, HS3). It does NOT need a `Candidate` from Tab 1 or an `InterfaceStructure` from Tab 3.

---

## Architectural Patterns

### Pattern 1: Worker-Object per Tab

**What:** Each tab has its own Worker class for background computation, managed by MainViewModel.

**When to use:** Every tab that does computation (generation, insertion, export).

**Trade-offs:** Clean separation but MainViewModel grows. The alternative (one ViewModel per tab) was considered and rejected because tabs share data (candidates, interface results) and the MainViewModel already acts as the central state holder.

**Example (existing pattern to follow):**
```python
# In MainViewModel:
self._hydrate_worker = None
self._hydrate_thread = None
self._is_hydrate_generating = False

# Signals
hydrate_generation_started = Signal()
hydrate_generation_progress = Signal(int)
hydrate_generation_status = Signal(str)
hydrate_generation_complete = Signal(object)  # HydrateResult
hydrate_generation_error = Signal(str)
hydrate_generation_cancelled = Signal()
hydrate_ui_enabled_changed = Signal(bool)

def start_hydrate_generation(self, lattice, guests, supercell):
    # Same pattern as start_interface_generation()
    ...
```

### Pattern 2: Dataclass per Structure Type

**What:** Each structure type has a dedicated dataclass with clear field semantics.

**When to use:** Whenever a new output structure is created (HydrateResult, InsertedStructure).

**Trade-offs:** More types to maintain but clear contracts between components. Each viewer knows exactly what fields to expect.

**Example:**
```python
# Each structure type has its own dataclass:
Candidate           → Tab 1 (ice generation)
InterfaceStructure   → Tab 3 (interface construction)
HydrateResult        → Tab 2 (hydrate generation) [NEW]
InsertedStructure    → Tab 4 (ion/molecule insertion) [NEW]
```

### Pattern 3: Per-Type VTK Actor Dictionary

**What:** Instead of a fixed number of actors, create a dict of `{molecule_type: (mapper, actor)}` pairs. Each type gets independent visibility, style, and color control.

**When to use:** Any viewer that renders multi-type molecular systems (hydrates, inserted structures).

**Trade-offs:** More complex setup but enables per-type toggling and styling without rebuilding the scene. The alternative (rebuild entire scene on style change) is simpler but causes flicker and performance loss for large systems.

**Example:**
```python
# Instead of fixed actors:
self._ice_bond_actor = ...
self._water_bond_actor = ...

# Use a dictionary:
self._type_actors = {}  # molecule_type → vtkActor
self._type_mappers = {}  # molecule_type → vtkMoleculeMapper

def set_structure(self, result):
    molecules = inserted_to_vtk_molecules(result)  # returns dict
    for mol_type, vtk_mol in molecules.items():
        mapper = vtkMoleculeMapper()
        style = MOLECULE_TYPE_STYLES[mol_type]["style"]
        apply_style(mapper, style)
        mapper.SetInputData(vtk_mol)
        
        actor = vtkActor()
        actor.SetMapper(mapper)
        self._type_actors[mol_type] = actor
        self._type_mappers[mol_type] = mapper
        self.renderer.AddActor(actor)
```

### Pattern 4: Existing Overlap Resolver Reuse

**What:** Reuse `overlap_resolver.detect_overlaps()` and `remove_overlapping_molecules()` for ion placement, not just ice-water overlap removal.

**When to use:** Tab 4 ion insertion — place ions at random positions, check overlaps with existing water, remove overlapping water molecules.

**Trade-offs:** The existing functions assume O-O distance checks (atoms_per_molecule=3 or 4). For ions (single atoms, atoms_per_molecule=1), we need a thin wrapper that:
1. Extracts water O positions from the liquid region of InterfaceStructure
2. Generates random ion positions
3. Calls `detect_overlaps(ion_positions, water_o_positions, box_dims, threshold)`
4. Calls `remove_overlapping_molecules(all_positions, overlapping_set, atoms_per_molecule=4)`

**Example:**
```python
# IonInserter.insert_nacl(interface_structure, concentration)
def insert_nacl(self, iface: InterfaceStructure, concentration_mol_per_L: float) -> InsertedStructure:
    # 1. Calculate number of ion pairs from concentration and box volume
    box_volume_nm3 = iface.cell[0,0] * iface.cell[1,1] * iface.cell[2,2]
    box_volume_L = box_volume_nm3 * 1e-24  # nm³ → L
    n_ion_pairs = int(round(concentration_mol_per_L * box_volume_L * 6.022e23))
    
    # 2. Extract liquid water O positions (past ice_atom_count boundary)
    water_start = iface.ice_atom_count
    water_positions = iface.positions[water_start:]
    # Every 4th atom is O (OW, HW1, HW2, MW pattern)
    water_o_positions = water_positions[::4]
    
    # 3. Generate random Na+ positions in liquid region
    na_positions = self._random_positions_in_box(n_ion_pairs, iface.cell)
    cl_positions = self._random_positions_in_box(n_ion_pairs, iface.cell)
    
    # 4. Detect overlaps and remove water molecules
    na_overlaps = detect_overlaps(water_o_positions, na_positions, box_dims, threshold=0.25)
    cl_overlaps = detect_overlaps(water_o_positions, cl_positions, box_dims, threshold=0.25)
    all_overlaps = na_overlaps | cl_overlaps
    
    # 5. Remove overlapping water molecules (whole molecules)
    filtered_water, n_remaining = remove_overlapping_molecules(
        water_positions, all_overlaps, atoms_per_molecule=4
    )
    
    # 6. Build InsertedStructure
    ...
```

### Pattern 5: GenIce2 Hydrate API Wrapper

**What:** A new `HydrateStructureGenerator` that wraps GenIce2's hydrate-specific API, separate from `IceStructureGenerator`.

**When to use:** Tab 2 hydrate generation. Unlike ice generation (which uses phase lookup + GenIce2 lattice), hydrate generation uses GenIce2's `guests` parameter.

**Trade-offs:** Separate generator class rather than extending `IceStructureGenerator`. Rationale: hydrate generation has different inputs (lattice type, not phase; guest molecules, not just water), different output (mixed residue types), and different workflow (no phase lookup, no ranking). A single class trying to handle both would violate SRP.

**Example:**
```python
class HydrateStructureGenerator:
    """Generate clathrate hydrate structures using GenIce2."""
    
    def __init__(self, lattice_name: str, density: float, supercell_matrix=None):
        self.lattice_name = lattice_name  # e.g., "CS1", "CS2", "HS3"
        self.density = density
        self.supercell_matrix = supercell_matrix or [1, 1, 1]
    
    def generate(self, guests: dict, seed: int = None) -> HydrateResult:
        """Generate a single hydrate structure.
        
        Args:
            guests: Dict of cage_type → {molecule_name: occupancy}
                    e.g., {'12': {'ch4': 1.0}, '14': {'ch4': 1.0}}
            seed: Random seed for reproducibility
        """
        # Save/restore random state (same as IceStructureGenerator)
        original_state = np.random.get_state()
        if seed is not None:
            np.random.seed(seed)
        
        lattice = safe_import("lattice", self.lattice_name).Lattice()
        ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
        water = safe_import("molecule", "tip3p").Molecule()
        formatter = safe_import("format", "gromacs").Format()
        
        gro_string = ice.generate_ice(
            formatter=formatter, water=water, depol="strict",
            guests=guests
        )
        
        np.random.set_state(original_state)
        
        # Parse multi-molecule GRO output
        return self._parse_hydrate_gro(gro_string, guests)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Extending IceStructureGenerator for Hydrates

**What people do:** Add hydrate parameters to `IceStructureGenerator.__init__()` and `generate_all()` with conditional branches for `is_hydrate`.

**Why it's wrong:** The two generators have fundamentally different workflows — ice uses phase lookup and ranking; hydrates use lattice selection and deterministic cage filling. Merging them creates a god class with confusing conditionals.

**Do this instead:** Create a separate `HydrateStructureGenerator` class that follows the same pattern (GRO parsing, numpy arrays, GenIce2 API) but with hydrate-specific inputs and outputs.

### Anti-Pattern 2: Single-Actor VTK for Multi-Type Systems

**What people do:** Combine all molecule types into one `vtkMolecule` and try to color atoms individually using scalar arrays.

**Why it's wrong:** VTK's `vtkMoleculeMapper` renders ALL atoms with one style (one representation mode, one bond radius, one atom scale). You can't have VDW spheres for ions and lines for water in the same mapper. The per-atom coloring approach only works for same-style different-color, not different-style different-type.

**Do this instead:** Use one `vtkMoleculeMapper` + `vtkActor` per molecule type. Each type gets its own style (VDW for ions, lines for water, ball-and-stick for guests). Visibility toggling is trivial: `actor.SetVisibility(False)`.

### Anti-Pattern 3: Modifying InterfaceStructure In-Place

**What people do:** Add ion atoms directly to `InterfaceStructure.positions` and modify `atom_names`, hoping the downstream viewers and exporters will handle it.

**Why it's wrong:** `InterfaceStructure` is a dataclass designed for ice+water two-phase systems. It has `ice_atom_count` and `water_atom_count` fields that don't accommodate ion atoms. Modifying it in place breaks the ice/water boundary tracking and violates the immutability contract that viewers rely on.

**Do this instead:** Create a new `InsertedStructure` dataclass that contains the original `InterfaceStructure` data plus insertion metadata (ion positions, molecule positions, removal indices). This preserves the original structure and makes it easy to render per-type visualization.

### Anti-Pattern 4: GRO Parser That Assumes All Atoms Are Water

**What people do:** Modify `_parse_gro()` to return `(positions, atom_names)` and assume calling code will figure out which atoms belong to which molecule type.

**Why it's wrong:** The current `_parse_gro()` returns flat arrays where all atoms are assumed to be water (O, H, H pattern). Hydrate GRO output contains multiple residue types (SOL, CH4, CO2). The parser needs to return residue information alongside atom positions.

**Do this instead:** Create `_parse_gro_multi_molecule()` that returns `(positions, atom_names, residue_names, residue_ids)`. This new function handles mixed residue GRO files. The existing `_parse_gro()` remains unchanged for Tab 1 ice generation.

### Anti-Pattern 5: GenIce2 Cation/Anion for Tab 4

**What people do:** Use GenIce2's `cations={water_idx: 'one'}` and `anions={water_idx: 'one'}` parameters to insert NaCl ions.

**Why it's wrong:** GenIce2's cation/anion system replaces water molecules in the ice lattice by index, which is meant for ionic substitution in crystal structures. Tab 4 needs concentration-based ion placement in the liquid phase of an interface, where we don't have water molecule indices — we have a concentration (mol/L) and a box volume.

**Do this instead:** Implement custom `IonInserter` that:
1. Computes number of ion pairs from concentration × volume × Avogadro's number
2. Places ions at random positions in the liquid region (z > ice boundary)
3. Uses `cKDTree` to detect overlaps with water oxygens
4. Removes overlapping water molecules (whole molecules only)
5. Returns an `InsertedStructure` with ions added and water removed

---

## Suggested Build Order

Based on dependencies and incremental testability:

### Phase 1: Data Types + GRO Parser Extension

**Why first:** All downstream components (generators, viewers, exporters) need the data types and multi-molecule GRO parser.

**Delivers:**
- `HydrateResult` dataclass in `types.py`
- `InsertedStructure` dataclass in `types.py`
- `MoleculeType` enum/flag for per-atom tagging
- `_parse_gro_multi_molecule()` in `generator.py`
- `MoleculeTypeStyles` constant dict for VTK styling

**Tests:** Unit tests for multi-molecule GRO parsing (use actual GenIce2 hydrate output), dataclass field validation.

### Phase 2: Tab 4 — Ion Insertion (NaCl)

**Why before Tab 2:** Ion insertion reuses existing infrastructure (InterfaceStructure from Tab 3, cKDTree from overlap_resolver). It's the simpler of the two new features because it doesn't require a new generation pipeline.

**Delivers:**
- `IonInserter` class in `structure_generation/ion_inserter.py`
- `InsertPanel` UI (NaCl concentration input, candidate dropdown from Tab 3)
- `InsertionWorker` in `gui/workers.py`
- Hydrate/insert signals in `MainViewModel`
- `InsertViewerWidget` with 4-actor rendering (ice, water, Na+, Cl-)
- `inserted_to_vtk_molecules()` in `vtk_utils.py`
- `InsertGROMACSExporter` with multi-type .top file
- Bundled `ions-na-cl.itp` data file
- Tab 4 insertion in `MainWindow`

**Tests:** Integration test: generate interface (Tab 3) → insert 0.5 mol/L NaCl → verify ion count, overlap removal, GROMACS export validity.

### Phase 3: Tab 2 — Hydrate Generation

**Why after Tab 4:** Hydrate generation requires a completely new generation pipeline (GenIce2 hydrate API, not phase lookup). It also needs multi-molecule GRO export, which Phase 2 establishes the pattern for.

**Delivers:**
- `HydrateStructureGenerator` class in `structure_generation/hydrate_gen.py`
- `HydratePanel` UI (lattice dropdown, guest selection, occupancy, supercell)
- `HydrateGenerationWorker` in `gui/workers.py`
- `HydrateViewerWidget` with 2-actor rendering (water + guest)
- `hydrate_to_vtk_molecules()` in `vtk_utils.py`
- `HydrateGROMACSExporter` with guest molecule .itp
- Bundled `ch4.itp` and `co2.itp` data files
- Tab 2 insertion in `MainWindow`

**Tests:** Integration test: generate CS1 + CH₄ hydrate → verify cage occupancy, guest positions, GROMACS export validity.

### Phase 4: Custom Molecule Upload + Display Controls

**Why last:** Both Tab 2 and Tab 4 need custom molecule support. Building it last allows the basic features to stabilize first.

**Delivers:**
- Custom .gro/.itp file upload dialogs
- Custom molecule placement modes (random, specified COM)
- `MoleculeTypeControls` widget for per-type visibility/style/color
- `.itp` file bundling in GROMACS export
- Custom molecule validation (atom count, overlap check)

**Tests:** End-to-end test: upload custom .gro → insert into interface → export GROMACS → verify topology.

### Phase Ordering Rationale

1. **Data types first** — All phases depend on these; they're self-contained and low-risk.
2. **Tab 4 before Tab 2** — Tab 4 reuses more existing code (InterfaceStructure, cKDTree, overlap_resolver). Tab 2 requires a new GenIce2 API path. Proving the multi-actor viewer and multi-type export pattern with simpler ion insertion first reduces risk for the more complex hydrate path.
3. **Custom molecules last** — File upload, parsing, and validation add complexity. Get the basic flows working first with built-in molecules (NaCl for Tab 4, CH₄/CO₂ for Tab 2).

---

## Scalability Considerations

| Concern | At 100 molecules | At 10K molecules | At 1M molecules |
|---------|------------------|------------------|------------------|
| cKDTree overlap detection | <1ms | ~10ms | ~100ms |
| VTK rendering (multi-actor) | Smooth | Acceptable | May need LOD |
| GRO file parsing | <1ms | ~5ms | ~50ms |
| GenIce2 hydrate generation | ~1s | ~5s | ~30s |
| NaCl ion placement | <1ms | ~5ms | ~50ms |

### Scaling Priorities

1. **First bottleneck:** VTK rendering with >5 actors for >100K atoms. Solution: Use `vtkMoleculeMapper.RenderAtomsOff()` for water (lines-only mode) and only render atoms for ions and guests.
2. **Second bottleneck:** GenIce2 generation time for large hydrate supercells. Solution: This is inherent to GenIce2; show progress bar and allow cancellation.

---

## Sources

- **QuickIce codebase (v3.5):** `gui/main_window.py`, `gui/viewmodel.py`, `gui/workers.py`, `gui/interface_panel.py`, `gui/interface_viewer.py`, `gui/vtk_utils.py`, `gui/molecular_viewer.py`, `gui/export.py`, `structure_generation/generator.py`, `structure_generation/types.py`, `structure_generation/overlap_resolver.py`, `output/gromacs_writer.py` — All HIGH confidence (direct code analysis)
- **GenIce2 source code:** `genice2/genice.py` — GenIce class, `guests` parameter, `cations`/`anions` parameters — HIGH confidence
- **GenIce2 lattice plugins:** `CS1.py`, `CS2.py` — Hydrate structures with cage data — HIGH confidence
- **GenIce2 molecule plugins:** `ch4.py`, `co2.py`, `H2.py`, `thf.py`, `one.py` — Guest molecule definitions — HIGH confidence
- **VTK 9.5.2 API:** `vtkMoleculeMapper`, `vtkActor` — Multi-actor rendering verified — HIGH confidence
- **Joung & Cheatham (2008):** Ion parameters for TIP4P-ICE compatibility — HIGH confidence (standard published parameters)

---
*Architecture research for: QuickIce v4.0 Molecule Insertion*
*Researched: 2026-04-14*