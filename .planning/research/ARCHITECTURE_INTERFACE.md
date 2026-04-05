# Research Summary: Liquid-Solid Interface Generation for QuickIce

**Domain:** Computational chemistry / Ice structure visualization
**Researched:** 2026-04-05
**Overall confidence:** MEDIUM

## Executive Summary

This research addresses adding liquid-solid (ice-water) interface generation capability to QuickIce. The core finding is that **GenIce2 does not support interface generation** — it is purely an ice crystal generator. Three viable approaches exist for implementing this feature: rule-based structure assembly, pre-generated configuration libraries, and simplified MD-based relaxation. The simplest path forward is rule-based assembly, which can leverage existing GenIce output combined with procedurally-generated liquid-like water layers.

Key architectural implications:
- No changes to existing GenIce integration required
- New `InterfaceGenerator` service layer needed
- VTK visualization already supports multiple molecule types/regions
- Estimated complexity: 3/5 (moderate)

## Key Findings

### Stack
QuickIce uses GenIce2 for ice generation. GenIce2 does NOT support liquid-solid interfaces — it generates pure crystalline ice structures only. This is a fundamental limitation of the library's design (see PyPI documentation confirming it generates "hydrogen-disordered ice structures" only).

### Architecture
The existing MVVM architecture (MainViewModel → Workers → Structure Generation) can be extended with a new `InterfaceGenerator` service. The key changes are:
- New module in `structure_generation/` for interface assembly
- Updated worker to handle interface generation workflow
- Minor enhancements to VTK viewer for phase differentiation

### Critical Pitfall
**Don't attempt to modify GenIce2** for interface support — this would require fundamental changes to its graph-based hydrogen bond network generation. Instead, build interface generation as a layer on top of existing GenIce output.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Interface Structure Assembly** — Rule-based generation combining ice + liquid layers
2. **Phase 2: Visualization Enhancements** — Color-coding phases in VTK viewer  
3. **Phase 3: Configuration Library** — Pre-generated interface structures for common cases

**Phase ordering rationale:**
- Phase 1 provides core functionality with minimal complexity
- Phase 2 adds user-facing value (visual clarity)
- Phase 3 enables optimization for frequently-used configurations

**Research flags for phases:**
- Phase 1: Likely needs validation testing (are generated interfaces physically reasonable?)
- Phase 2: Standard VTK development, unlikely to need research
- Phase 3: Optional optimization, can defer based on user feedback

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified GenIce2 capabilities via PyPI and GitHub docs |
| Features | MEDIUM | Interface generation approaches identified, but implementation details need refinement |
| Architecture | HIGH | Clear extension path from existing architecture |
| Pitfalls | HIGH | GenIce2 limitation confirmed, no risk of misdirected effort |

## Gaps to Address

- **Interface validation**: Need to verify generated interfaces are physically reasonable (may need consultation with domain experts or comparison with published MD simulations)
- **Performance**: Rule-based approach may produce artifacts; may need MD relaxation step for production use
- **Phase diagram integration**: Current phase mapping works for pure ice; need to consider if interface regions have different T,P stability

---

# Detailed Research: ARCHITECTURE_INTERFACE.md

## 1. Scientific Approaches for Liquid-Solid Interface Generation

### 1.1 Overview

The ice-water interface represents a fundamental boundary in computational ice science, where crystalline order transitions to disordered liquid. Three primary approaches exist for generating such interfaces:

### 1.2 Approach 1: Rule-Based Structure Assembly (Recommended for MVP)

**Description:** Procedurally combine pre-generated ice structures with liquid-like water layers using geometric rules.

**Implementation:**
1. Generate ice phase structure using GenIce2 (existing functionality)
2. Generate liquid-like water configuration (randomized positions, realistic density)
3. Stack layers with specified interface orientation
4. Apply simple geometric constraints at interface (hydrogen bond connectivity)

**Pros:**
- No external dependencies beyond GenIce2
- Fast generation (seconds)
- Fully controllable parameters
- Suitable for visualization and educational use

**Cons:**
- May not represent true equilibrium interface
- Requires careful parameter tuning
- Hydrogen bonding at interface may be unrealistic

**Complexity:** Low-Medium
**Scientific validity:** Moderate (good for visualization, limited for research)

### 1.3 Approach 2: Pre-Generated Configuration Library

**Description:** Curate a set of known interface structures from published MD simulations or experiments.

**Implementation:**
1. Identify common interface types (Ih/water, Ic/water, etc.)
2. Extract representative configurations from literature
3. Store as template structures in application data
4. Allow parameter interpolation (temperature, pressure effects)

**Pros:**
- Scientifically validated configurations
- High fidelity to real systems
- Fast lookup-based generation

**Cons:**
- Limited coverage of ice phases and conditions
- Requires manual curation effort
- May have licensing/copyright considerations

**Complexity:** Low
**Scientific validity:** High (if properly curated)

**Sources needed:**
- Published MD simulation trajectories
- Neutron/X-ray diffraction data
- Computational chemistry literature

### 1.4 Approach 3: Minimal MD Minimization

**Description:** Use short molecular dynamics simulation to relax rule-generated or library-based interfaces.

**Implementation:**
1. Generate initial interface structure (Approach 1 or 2)
2. Run short energy minimization (100-1000 steps)
3. Optionally run brief NPT equilibration (10-100 ps)
4. Extract final coordinates

**Pros:**
- Physically realistic interface geometry
- Handles hydrogen bond optimization automatically
- Can adapt to different water models

**Cons:**
- Requires MD software (OpenMM, LAMMPS, GROMACS)
- Significantly longer generation time
- More complex dependency management
- Results may vary with water model choice

**Complexity:** High
**Scientific validity:** High

### 1.5 Recommendation

**For v2.1 (MVP):** Use Approach 1 (Rule-Based Assembly)
- Simplest implementation
- No new dependencies
- Sufficient for visualization use case

**For v2.2+:** Consider Approach 2 (Configuration Library) as enhancement
- Higher scientific validity
- Reasonable curation effort
- Better for research-oriented users

**Avoid for now:** Approach 3 (MD Minimization)
- Adds significant complexity
- New dependency requirements
- Better served by dedicated MD software

---

## 2. GenIce2 Interface Capabilities Assessment

### 2.1 Verified Capabilities

Based on research of official GenIce2 documentation (PyPI and GitHub):

| Capability | Supported | Notes |
|------------|-----------|-------|
| Pure ice generation | ✅ Yes | Primary function |
| Multiple ice phases | ✅ Yes | 12+ phases including Ih, Ic, II-VI, XII, XVI, XVII |
| Hydrogen disorder | ✅ Yes | Built-in depolarization algorithm |
| Clathrate hydrates | ✅ Yes | sI, sII, sH with guest molecules |
| Filled ices | ✅ Yes | C0, C1, C2 structures |
| Liquid water | ❌ No | Not designed for this |
| Ice-water interface | ❌ No | Not designed for this |
| Amorphous ice | Partial | Can add noise, not true amorphous |

### 2.2 GenIce2 Architecture Limitations

GenIce2 uses a seven-stage pipeline:
1. Cell repetition
2. Random graph generation
3. Apply ice rules (Bernal-Fowler constraints)
4. Depolarize (ensure zero net dipole)
5. Determine water orientations
6. Place atoms in water molecules
7. Place guest atoms

This pipeline is fundamentally incompatible with liquid water generation because:
- **Stage 3-4:** Ice rule enforcement assumes crystalline network
- **Stage 5:** Water orientation determined by crystal symmetry
- Liquid water lacks long-range order

### 2.3 Conclusion

**Do NOT attempt to extend GenIce2 for interface generation.** Instead, build interface generation as a post-processing layer that:
1. Uses GenIce2 to generate the solid phase
2. Independently generates liquid phase configuration
3. Assembles them into interface structure

---

## 3. Geometric and Physical Constraints

### 3.1 Interface Geometry Considerations

| Constraint | Value/Range | Notes |
|------------|-------------|-------|
| Ice Ih lattice constants | a=4.5Å, c=7.3Å | Standard hexagonal ice |
| Water molecule size | ~2.8Å diameter | TIP3P model basis |
| Typical interface width | 3-10 Å | Depends on temperature |
| Liquid water density | 1.0 g/cm³ | At standard conditions |
| Ice Ih density | 0.92 g/cm³ | At 273 K, 1 atm |

### 3.2 Physical Constraints for Interface Generation

1. **Density transition:** Ice to water involves ~8% density change
2. **Molecular orientation:** Ice molecules have fixed orientations; liquid molecules are disordered
3. **Hydrogen bonding:** Interface region may have under-coordinated water molecules
4. **Surface premelting:** Thin liquid-like layer exists on ice surface above ~-10°C
5. **Crystal orientation:** Interface energy depends on crystallographic face (basal, prismatic, etc.)

### 3.3 Recommended Parameters for MVP

```
Interface Configuration:
├── Ice phase: User-selected (Ih, Ic, etc.)
├── Ice thickness: 2-10 unit cells (configurable)
├── Liquid thickness: Match ice or specified
├── Interface orientation: [001], [100], or [110] for Ih
└── Boundary conditions: Periodic in X-Z, solid in Y
```

---

## 4. Visualization Challenges and Solutions

### 4.1 Same Viewport vs. Separate Regions

**Recommendation:** Single viewport with visual differentiation

The existing VTK viewer in QuickIce can already handle:
- Multiple molecule types (O, H atoms)
- Unit cell boundary visualization
- Ball-and-stick, stick, and VDW representations

**Required enhancements:**
1. **Phase coloring:** Different colors for ice vs. liquid regions
   - Ice: Blue/cyan tones (existing style)
   - Liquid: Modified tone or transparency
   
2. **Region boundaries:** Visual indicator of interface location
   - Optional dashed line or plane
   - Toggle-able in UI

3. **Molecule differentiation:**
   - Ice: Ordered crystalline positions
   - Liquid: More variable, potentially smaller spheres

### 4.2 Implementation Approach

The VTK molecular viewer (`molecular_viewer.py`) already supports:
- Multiple rendering styles
- Atom coloring by element
- Cell boundary boxes
- Hydrogen bond visualization

**Minimal changes needed:**
1. Add phase identifier to atom data (ice vs. liquid)
2. Add color mapping based on phase
3. Add interface plane visualization (optional)

---

## 5. Integration with Existing MVVM Architecture

### 5.1 Current Architecture

```
MainViewModel (gui/viewmodel.py)
    │
    ├── start_generation(temperature, pressure, nmolecules)
    │   Creates GenerationWorker in QThread
    │   Emits: generation_started, progress, status, complete, error
    │
    └── get_last_ranking_result()
        Returns: RankingResult with candidates
```

```
GenerationWorker (gui/workers.py)
    │
    ├── Runs in QThread
    ├── Uses: Phase mapping → Structure generation → Ranking
    └── Emits progress/status to MainViewModel
```

```
Structure Generation (structure_generation/)
    │
    ├── generator.py: IceStructureGenerator wraps GenIce2
    ├── mapper.py: Phase lookup and supercell calculation
    └── types.py: Candidate, GenerationResult data classes
```

### 5.2 Proposed Architecture Extension

```
New: InterfaceGenerator (structure_generation/interface.py)
    │
    ├── generate_interface(ice_phase, nmolecules_ice, nmolecules_liquid)
    │   ├── 1. Generate ice structure (existing GenIce path)
    │   ├── 2. Generate liquid configuration (new)
    │   ├── 3. Assemble interface structure
    │   └── 4. Return InterfaceCandidate
    │
    └── generate_from_template(template_name, parameters)
        └── Uses pre-generated configuration library
```

**Integration with MainViewModel:**
- Add new signal: `interface_generation_started`, `interface_generation_complete`
- Add new method: `start_interface_generation(ice_phase, ice_molecules, liquid_molecules)`
- Create new worker: `InterfaceGenerationWorker`

### 5.3 Data Flow Changes

```
Existing Flow:
  User Input (T, P, N) → MainViewModel → GenerationWorker 
    → IceStructureGenerator → GenIce2 → Candidates → Ranking → ViewModel → View

Proposed Flow (Interface):
  User Input (ice_phase, ice_N, liquid_N) → MainViewModel → InterfaceWorker
    → InterfaceGenerator 
      → IceStructureGenerator (ice) + LiquidGenerator (liquid) 
      → InterfaceAssembler → InterfaceCandidate → ViewModel → View
```

---

## 6. New Components Needed

### 6.1 Module: `structure_generation/interface.py`

**Responsibilities:**
- Interface structure generation logic
- Liquid water configuration generation
- Interface assembly and validation

**Key classes:**
```python
class InterfaceConfig:
    ice_phase: str          # "ice_ih", "ice_ic", etc.
    ice_molecules: int      # Number in solid phase
    liquid_molecules: int   # Number in liquid phase
    interface_orientation: str  # "001", "100", "110"
    template: Optional[str] # Pre-generated template name

class InterfaceCandidate:
    positions: np.ndarray   # Combined atomic positions
    atom_types: list[str]   # ["O", "H", "O", "H", ...]
    cell: np.ndarray        # Unit cell vectors
    phase_regions: list[dict]  # Ice vs liquid region definitions
    metadata: dict          # Generation parameters

class InterfaceGenerator:
    def generate(config: InterfaceConfig) -> InterfaceCandidate:
        # Main generation method
```

### 6.2 Module: `structure_generation/liquid.py`

**Responsibilities:**
- Liquid water configuration generation
- Different generation strategies (random, ordered, etc.)

**Key classes:**
```python
class LiquidGenerator:
    def generate_random(n_molecules: int, density: float, cell: np.ndarray) -> np.ndarray:
        """Generate random water positions in box"""
    
    def generate_grid(n_molecules: int, density: float) -> np.ndarray:
        """Generate grid-based initial positions"""
```

### 6.3 Worker: `gui/workers.py` addition

```python
class InterfaceGenerationWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)  # InterfaceCandidate
    error = Signal(str)
    
    def __init__(self, config: InterfaceConfig):
        # Store configuration
```

### 6.4 ViewModel: `gui/viewmodel.py` addition

```python
class MainViewModel:
    # New signals
    interface_generation_started = Signal()
    interface_generation_complete = Signal(object)
    interface_error = Signal(str)
    
    # New method
    def start_interface_generation(self, ice_phase: str, ice_n: int, liquid_n: int):
        # Create InterfaceGenerationWorker, run in thread
```

---

## 7. Visualization Approach

### 7.1 Same Viewport Display

**Primary recommendation:** Single viewport with phase coloring

**Implementation:**
1. Extend atom data structure to include phase identifier
2. Add color mapping:
   - Ice phase: Existing blue/cyan tones
   - Liquid phase: Slightly modified (e.g., more transparent or different hue)
3. Optional: Interface boundary plane visualization

### 7.2 VTK Implementation Details

Current viewer supports:
- `add_molecule_positions()` - Add atoms with positions and colors
- `add_bonds()` - Hydrogen bond visualization
- `show_cell_boundary()` - Unit cell box

**Enhancements needed:**
```python
# Pseudocode for interface visualization
def add_interface_structure(candidate: InterfaceCandidate, viewer):
    # Phase 1: Add ice atoms (blue)
    ice_atoms = candidate.get_atoms_by_phase("ice")
    viewer.add_molecules(ice_atoms, color=(0.2, 0.5, 0.9))
    
    # Phase 2: Add liquid atoms (lighter blue/transparent)
    liquid_atoms = candidate.get_atoms_by_phase("liquid")
    viewer.add_molecules(liquid_atoms, color=(0.4, 0.7, 1.0), opacity=0.8)
    
    # Phase 3: Add interface boundary (optional)
    if candidate.has_interface_plane():
        viewer.add_plane(candidate.interface_plane, style="dashed")
```

### 7.3 UI Considerations

**New controls needed:**
1. Phase selection (ice type)
2. Ice layer thickness (molecules or unit cells)
3. Liquid layer thickness
4. Interface orientation (for crystalline phases)
5. Template selection (if using library approach)
6. Toggle: Show/hide interface boundary
7. Toggle: Show ice/liquid differentiation

---

## 8. Use Case Value Assessment

### 8.1 Primary Use Cases

| Use Case | Value | Priority |
|----------|-------|----------|
| Visualization of freezing front | High | Primary |
| Educational demonstrations | High | Primary |
| Interface structure exploration | Medium | Secondary |
| Comparison with MD simulations | Medium | Secondary |
| Research-grade interface generation | Low | Future |

### 8.2 Scientific Value

1. **Freezing front visualization:** Users can see how ice/water boundary appears
2. **Phase diagram extension:** Could visualize stability regions
3. **Hypothesis testing:** Quick generation for conceptual models
4. **Publication-quality figures:** Clean, configurable visualization

### 8.3 Limitations to Communicate

- **Not for MD simulation:** Interfaces are geometric constructs, not dynamics
- **Not for energy calculations:** No force field evaluation
- **Not for property prediction:** Interface properties not computed
- **Validation needed:** Users should verify against published structures for research

---

## 9. Complexity Rating and Effort Estimation

### 9.1 Complexity Assessment

| Aspect | Rating | Rationale |
|--------|--------|-----------|
| Algorithm complexity | 2/5 | Rule-based assembly is straightforward |
| Integration complexity | 3/5 | New module, but follows existing patterns |
| Visualization complexity | 2/5 | Minor VTK enhancements |
| Testing complexity | 3/5 | Need validation against known structures |
| Documentation | 3/5 | New concepts to explain |
| **Overall** | **3/5** | Moderate complexity |

### 9.2 Effort Estimation

| Task | Estimated Effort | Notes |
|------|------------------|-------|
| Interface module development | 2-3 days | Core generation logic |
| Liquid generator module | 1-2 days | Water configuration |
| Worker/ViewModel integration | 1 day | Standard patterns |
| VTK visualization updates | 1-2 days | Color mapping, plane |
| UI controls | 1 day | New input controls |
| Testing | 2-3 days | Validation, edge cases |
| Documentation | 1-2 days | User guide updates |
| **Total** | **9-14 days** | ~2-3 weeks |

### 9.3 Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| GenIce2 | ✅ Already used | No change |
| NumPy | ✅ Already used | No change |
| VTK | ✅ Already used | Minor enhancement |
| PySide6 | ✅ Already used | No change |
| spglib | ✅ Already used | No change |

**No new external dependencies required** for MVP implementation.

---

## 10. Implementation Roadmap

### Phase 1: Core Interface Generation (Week 1-2)

**Goals:**
- Implement InterfaceGenerator class
- Implement LiquidGenerator class  
- Create InterfaceCandidate data structure
- Basic integration with generation worker

**Deliverables:**
- Working CLI command (optional)
- Basic interface generation in GUI

### Phase 2: Visualization Enhancement (Week 2-3)

**Goals:**
- Phase-based coloring in VTK viewer
- Interface boundary visualization
- UI controls for interface parameters

**Deliverables:**
- Full visualization in main viewport
- User-adjustable parameters

### Phase 3: Validation and Refinement (Week 3-4)

**Goals:**
- Test with known interface structures
- Refine generation parameters
- Documentation and examples

**Deliverables:**
- Validated output
- User documentation
- Example configurations

---

## 11. Sources

### Verified Sources (HIGH Confidence)

1. **GenIce2 PyPI documentation** — Confirmed ice-only generation
   - https://pypi.org/project/GenIce/
   - https://github.com/genice-dev/GenIce2

2. **GenIce2 GitHub repository** — Architecture details
   - https://github.com/vitroid/GenIce
   - https://github.com/genice-dev/GenIce2

### Technical References (MEDIUM Confidence)

3. **Ice structure literature** — Interface background
   - del Rosso et al. (2016) "New porous water ice..." Nature Communications
   - Various ice phase definitions and properties

### Domain Context (MEDIUM Confidence)

4. **QuickIce project context** — Current architecture
   - ViewModel pattern in gui/viewmodel.py
   - Structure generation in structure_generation/generator.py
   - VTK visualization in gui/molecular_viewer.py

---

## 12. Open Questions

1. **Validation approach:** How should we validate generated interfaces are physically reasonable?
   - Options: Compare with MD snapshots, expert review, ignore for MVP

2. **Interface orientation:** Should we expose crystallographic orientation to users?
   - Trade-off: More parameters vs. scientific flexibility

3. **Template library:** Is there sufficient published interface data to create a template library?
   - Requires literature survey

4. **Long-term direction:** Should we eventually add MD relaxation option?
   - Depends on user feedback and research needs