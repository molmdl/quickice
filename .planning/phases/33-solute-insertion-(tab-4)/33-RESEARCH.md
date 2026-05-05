# Phase 33: Solute Insertion (Tab 4) - Research

**Researched:** 2026-05-05
**Domain:** Solute insertion into liquid water with GROMACS topology
**Confidence:** HIGH

## Summary

This phase implements solute (THF, CH₄) insertion into liquid water regions of interface structures. The research reveals that ion insertion provides an excellent pattern to follow: synchronous operation, concentration-based molecule count calculation, all-atom overlap checking with cKDTree, and partial success handling with specific error messages. Key differences for solutes: (1) need rotation matrices for random orientation, (2) use bundled GAFF2 ITP files from quickice/data/, (3) need MoleculetypeRegistry for CH4_LIQ/THF_LIQ naming, (4) render with ball_and_stick style matching hydrate guests.

**Primary recommendation:** Follow ion insertion pattern closely. Add rotation matrix code for random orientation. Reuse cKDTree overlap checking. Use hydrate guest rendering style for visualization.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | - | Array operations | Positions, rotations |
| scipy.spatial.cKDTree | - | All-atom overlap checking | Efficient O(n log n) distance queries |
| PySide6 | 6.10.2 | GUI components | Tab, signals, worker threads |
| VTK | 9.5.2 | 3D visualization | vtkMoleculeMapper for ball-and-stick |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| random | stdlib | Random position/rotation | Placement randomization |
| dataclasses | stdlib | Type-safe data structures | SoluteConfig, SoluteStructure |

### Existing Modules to Reuse
| Module | Purpose | Location |
|--------|---------|----------|
| IonInserter | Overlap checking pattern, concentration calculation | quickice/structure_generation/ion_inserter.py |
| ITPParser | Parse bundled solute .itp files | quickice/structure_generation/itp_parser.py |
| MoleculetypeRegistry | Unique GROMACS naming (CH4_LIQ, THF_LIQ) | quickice/structure_generation/moleculetype_registry.py |
| HydrateRenderer | Ball-and-stick rendering pattern | quickice/gui/hydrate_renderer.py |

**Installation:**
```bash
# No new dependencies needed - all modules exist
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── structure_generation/
│   ├── solute_inserter.py          # NEW: Core insertion logic
│   ├── types.py                     # Add SoluteConfig, SoluteStructure
│   └── moleculetype_registry.py     # Reuse for CH4_LIQ/THF_LIQ naming
├── gui/
│   ├── solute_panel.py              # NEW: Tab UI (follow ion_panel.py)
│   ├── solute_viewer.py             # NEW: 3D viewer (follow ion_viewer.py)
│   ├── solute_renderer.py           # NEW: Rendering (follow hydrate_renderer.py)
│   └── main_window.py               # Add solute tab at position 3
└── data/
    ├── ch4.itp                      # Bundled GAFF2 parameters (EXISTS)
    └── thf.itp                      # Bundled GAFF2 parameters (EXISTS)
```

### Pattern 1: Concentration-Based Molecule Count
**What:** Calculate molecule count from mol/L concentration and liquid volume
**When to use:** User inputs concentration, system calculates how many molecules to insert
**Example:**
```python
# From ion_inserter.py (lines 136-169)
AVOGADRO = 6.02214076e23  # mol^-1

def calculate_molecule_count(
    concentration_molar: float,
    liquid_volume_nm3: float,
) -> int:
    """Calculate number of molecules from concentration and volume.
    
    Uses: N = C_M × V_L × NA
    
    Where:
        - C_M = concentration in mol/L (molarity)
        - V_L = liquid volume in nm³ converted to L (× 1e-24)
        - NA = Avogadro's number
    """
    # Convert nm³ to L: 1 nm³ = 1e-24 L
    volume_liters = liquid_volume_nm3 * 1e-24
    
    # Calculate molecules from molarity
    n_molecules = concentration_molar * volume_liters * AVOGADRO
    
    return int(round(n_molecules))
```

### Pattern 2: All-Atom Overlap Checking with cKDTree
**What:** Check all atoms (not just center-of-mass) against existing structure to prevent overlap
**When to use:** Placing solute molecules with complex geometry (THF ring, CH₄ tetrahedron)
**Example:**
```python
# From ion_inserter.py (lines 274-340)
from scipy.spatial import cKDTree

# Build tree from existing atoms (ice + guest + water to replace)
# IMPORTANT: Exclude MW atoms (virtual sites) to avoid false positives
existing_atoms = []
for mol in structure.molecule_index:
    if mol.mol_type in ("ice", "guest", "water"):
        start = mol.start_idx
        end = start + mol.count
        for atom_idx in range(start, end):
            atom_name = structure.atom_names[atom_idx]
            if atom_name != "MW":  # Exclude massless virtual sites
                existing_atoms.append(structure.positions[atom_idx])

if existing_atoms:
    existing_tree = cKDTree(np.array(existing_atoms))
    
    # For each atom in solute molecule, check distance
    for atom_pos in solute_molecule_positions:
        min_dist = existing_tree.query(atom_pos, k=1)[0]
        if min_dist < MIN_SEPARATION:
            # Too close - try different position
            continue  # Skip this placement attempt
```

### Pattern 3: Random Position and Rotation Generation
**What:** Generate random position in liquid region, random rotation matrix for orientation
**When to use:** Placing solute molecules with random orientation
**Example:**
```python
import numpy as np
from scipy.spatial.transform import Rotation

def generate_random_position(
    liquid_region_bounds: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    """Generate random position within liquid region bounds.
    
    Args:
        liquid_region_bounds: (min_coords, max_coords) in nm
        
    Returns:
        Random (x, y, z) position in nm
    """
    min_coords, max_coords = liquid_region_bounds
    return np.random.uniform(min_coords, max_coords)

def generate_random_rotation_matrix() -> np.ndarray:
    """Generate random 3x3 rotation matrix using quaternion.
    
    Returns:
        (3, 3) rotation matrix for molecule orientation
    """
    # Use scipy Rotation for numerically stable random rotation
    rotation = Rotation.random()
    return rotation.as_matrix()

def rotate_molecule(
    molecule_positions: np.ndarray,
    rotation_matrix: np.ndarray,
    center: np.ndarray
) -> np.ndarray:
    """Rotate molecule around its center.
    
    Args:
        molecule_positions: (N_atoms, 3) positions in nm
        rotation_matrix: (3, 3) rotation matrix
        center: Center point for rotation (e.g., center of mass)
        
    Returns:
        Rotated positions
    """
    # Translate to origin
    centered = molecule_positions - center
    
    # Apply rotation (positions @ rotation_matrix.T)
    rotated = centered @ rotation_matrix.T
    
    # Translate back
    return rotated + center
```

### Pattern 4: Partial Success Handling
**What:** Continue placing molecules even if some fail, report exact count at end
**When to use:** Overlap checking may reject placement attempts
**Example:**
```python
# From ion_inserter.py (lines 406-415)
requested_molecules = n_molecules
placed_molecules = 0

for i in range(n_molecules):
    for attempt in range(max_attempts):
        # Try to place molecule
        position = generate_random_position(...)
        rotation = generate_random_rotation_matrix()
        
        # Check overlap
        if not has_overlap(position, rotation):
            place_molecule(position, rotation)
            placed_molecules += 1
            break
    else:
        # Max attempts reached without success
        continue

# Generate specific error message
if placed_molecules < requested_molecules:
    report = (
        f"Solute insertion: placed {placed_molecules} of {requested_molecules} "
        f"{solute_type} molecules. "
        f"Try lower concentration or larger liquid region."
    )
```

### Pattern 5: Tab UI Layout (Follow Ion Panel)
**What:** Horizontal split with left (config) and right (viewer + log) columns
**When to use:** All insertion/configuration tabs
**Example:**
```python
# From ion_panel.py (lines 52-115)
def _setup_ui(self):
    """Setup UI with horizontal layout."""
    main_layout = QHBoxLayout(self)
    
    # === LEFT COLUMN: Configuration Controls ===
    left_layout = QVBoxLayout()
    
    # Concentration input group
    conc_group = self._create_concentration_group()
    left_layout.addWidget(conc_group)
    
    # Molecule count display group
    count_group = self._create_molecule_count_group()
    left_layout.addWidget(count_group)
    
    # Insert button
    self.insert_button = QPushButton("Insert Solutes")
    left_layout.addWidget(self.insert_button)
    
    # === RIGHT COLUMN: Viewer Section ===
    right_layout = QVBoxLayout()
    
    # Log panel
    log_group = QGroupBox("Status Log")
    self._log_text = QTextEdit()
    right_layout.addWidget(log_group)
    
    # 3D viewer
    self.solute_viewer = SoluteViewerWidget()
    right_layout.addWidget(self.solute_viewer, stretch=1)
    
    # Add columns (left gets 2/5, right gets 3/5)
    main_layout.addLayout(left_layout, stretch=2)
    main_layout.addLayout(right_layout, stretch=3)
```

### Anti-Patterns to Avoid
- **Don't use center-of-mass overlap checking**: Solute molecules have complex geometry (THF ring), must check all atoms
- **Don't place in ice region**: Only place in liquid (positions[ice_atom_count:])
- **Don't ignore MW atoms in overlap check**: MW atoms are virtual sites, very close to O atoms, will cause false positives if included
- **Don't block UI during placement**: Ion insertion is synchronous (fast enough), but solute insertion may be slower - consider QThread worker if placement takes >1 second

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concentration to molecule count | Custom formula | IonInserter.calculate_ion_pairs() pattern | Proven formula: N = C × V × NA |
| Overlap checking | Distance loops | scipy.spatial.cKDTree | O(n log n) vs O(n²), handles PBC |
| Random rotation | Euler angles | scipy.spatial.transform.Rotation | Numerically stable, avoids gimbal lock |
| GROMACS naming | String manipulation | MoleculetypeRegistry | Ensures uniqueness, handles conflicts |
| ITP parsing | Regex from scratch | parse_itp_file() | Handles GROMACS format quirks |
| Ball-and-stick rendering | Custom VTK setup | hydrate_renderer.py pattern | Proven bond detection, CPK colors |

**Key insight:** Ion insertion already solved concentration calculation and overlap checking. Hydrate rendering solved ball-and-stick visualization. Reuse these patterns.

## Common Pitfalls

### Pitfall 1: Including MW Atoms in Overlap Check
**What goes wrong:** MW (massless virtual site) atoms are placed ~0.015 nm from oxygen atoms. Including them causes false overlap detection, rejecting valid placements.
**Why it happens:** MW atoms are in the positions array for TIP4P water models.
**How to avoid:** Filter out MW atoms before building cKDTree (see ion_inserter.py lines 300-304)
**Warning signs:** Very few molecules placed despite reasonable concentration

### Pitfall 2: Placing Solutes in Ice Region
**What goes wrong:** Solutes appear in ice phase instead of liquid water
**Why it happens:** Not respecting ice_atom_count boundary
**How to avoid:** Only sample positions from liquid region (positions[ice_atom_count:ice_atom_count + water_atom_count])
**Warning signs:** Solutes visible in ice structure, unexpected cluster positions

### Pitfall 3: Not Handling Partial Success
**What goes wrong:** User sees "0 molecules placed" when some could have been placed
**Why it happens:** First failure aborts entire insertion
**How to avoid:** Continue after max attempts, report "placed N of M molecules"
**Warning signs:** Binary success/failure, no partial count

### Pitfall 4: Unit Confusion in Concentration
**What goes wrong:** Off by 10²⁴ factor (nm³ vs L)
**Why it happens:** Forgetting to convert nm³ to liters
**How to avoid:** Use conversion factor 1e-24 (1 nm³ = 1e-24 L)
**Warning signs:** Molecule count is astronomically wrong

### Pitfall 5: Rotation Around Wrong Center
**What goes wrong:** Molecule translates while rotating instead of rotating in place
**Why it happens:** Rotating around origin instead of molecule center
**How to avoid:** Translate to origin → rotate → translate back (see Pattern 3)
**Warning signs:** Molecules appear stretched or displaced from intended positions

## Code Examples

### Concentration to Molecule Count
```python
# Source: ion_inserter.py lines 136-169
AVOGADRO = 6.02214076e23  # mol^-1

def calculate_molecule_count(
    concentration_molar: float,
    liquid_volume_nm3: float,
) -> int:
    """Calculate number of molecules from concentration and volume.
    
    Args:
        concentration_molar: Solute concentration in mol/L
        liquid_volume_nm3: Liquid region volume in nm³
        
    Returns:
        Number of molecules to insert
    """
    # Convert nm³ to L
    volume_liters = liquid_volume_nm3 * 1e-24
    
    # Calculate molecules
    n_molecules = concentration_molar * volume_liters * AVOGADRO
    
    return int(round(n_molecules))
```

### All-Atom Overlap Checking
```python
# Source: ion_inserter.py lines 274-340
from scipy.spatial import cKDTree

def build_existing_atoms_tree(
    structure: InterfaceStructure,
    exclude_water: bool = False
) -> cKDTree | None:
    """Build cKDTree from existing atoms for overlap checking.
    
    Args:
        structure: InterfaceStructure with molecule_index
        exclude_water: If True, exclude water molecules (for replacement)
        
    Returns:
        cKDTree of atom positions, or None if no atoms
    """
    existing_positions = []
    
    for mol in structure.molecule_index:
        # Skip water if replacing water with solutes
        if exclude_water and mol.mol_type == "water":
            continue
            
        start = mol.start_idx
        end = start + mol.count
        
        # Filter out MW atoms (virtual sites)
        for atom_idx in range(start, end):
            atom_name = structure.atom_names[atom_idx]
            if atom_name != "MW":
                existing_positions.append(structure.positions[atom_idx])
    
    if existing_positions:
        return cKDTree(np.array(existing_positions))
    return None

def check_solute_overlap(
    solute_positions: np.ndarray,
    existing_tree: cKDTree,
    min_separation: float = 0.3
) -> bool:
    """Check if solute molecule overlaps with existing atoms.
    
    Args:
        solute_positions: (N_atoms, 3) positions for solute molecule
        existing_tree: cKDTree of existing atoms
        min_separation: Minimum allowed distance in nm (default 0.3 nm = 3 Å)
        
    Returns:
        True if overlap detected, False if placement is valid
    """
    for atom_pos in solute_positions:
        min_dist = existing_tree.query(atom_pos, k=1)[0]
        if min_dist < min_separation:
            return True
    return False
```

### Random Rotation Matrix Generation
```python
# Source: scipy.spatial.transform.Rotation documentation
from scipy.spatial.transform import Rotation
import numpy as np

def generate_random_rotation_matrix() -> np.ndarray:
    """Generate random 3x3 rotation matrix.
    
    Uses uniform random quaternion for unbiased rotation.
    
    Returns:
        (3, 3) rotation matrix
    """
    rotation = Rotation.random()
    return rotation.as_matrix()

def rotate_molecule_around_center(
    positions: np.ndarray,
    rotation_matrix: np.ndarray,
) -> np.ndarray:
    """Rotate molecule around its center of mass.
    
    Args:
        positions: (N_atoms, 3) positions in nm
        rotation_matrix: (3, 3) rotation matrix
        
    Returns:
        Rotated positions
    """
    # Calculate center
    center = positions.mean(axis=0)
    
    # Translate to origin
    centered = positions - center
    
    # Apply rotation
    rotated = centered @ rotation_matrix.T
    
    # Translate back
    return rotated + center
```

### Ball-and-Stick Rendering (Hydrate Guest Pattern)
```python
# Source: hydrate_renderer.py lines 391-484
from vtkmodules.all import vtkMoleculeMapper, vtkMolecule, vtkActor, vtkMatrix3x3
import numpy as np

# CPK coloring
CPK_COLORS = {
    "C": (0.6, 0.6, 0.6),   # Carbon - gray
    "O": (1.0, 0.0, 0.0),   # Oxygen - red
    "H": (1.0, 1.0, 1.0),   # Hydrogen - white
}

# Bond detection threshold
BOND_DISTANCE_THRESHOLD = 0.16  # nm

def create_solute_actor(
    positions: np.ndarray,
    atom_names: list[str],
    cell: np.ndarray,
    mode: str = "ball_and_stick"
) -> vtkActor:
    """Create VTK actor for solute molecules with ball-and-stick rendering.
    
    Args:
        positions: (N_atoms, 3) positions in nm
        atom_names: List of atom names (C, O, H, etc.)
        cell: (3, 3) unit cell vectors
        mode: Rendering mode ("vdw", "ball_and_stick", "stick")
        
    Returns:
        vtkActor with solute molecules rendered
    """
    molecule = vtkMolecule()
    
    # Add atoms
    atom_ids = []
    for pos, name in zip(positions, atom_names):
        element = get_element_from_atom_name(name)
        if element is None:
            continue
        
        atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
        atom_id = molecule.AppendAtom(
            atomic_number,
            float(pos[0]), float(pos[1]), float(pos[2])
        )
        atom_ids.append(atom_id)
    
    # Detect bonds
    visible_positions = positions[:len(atom_ids)]
    for i in range(len(atom_ids)):
        for j in range(i + 1, len(atom_ids)):
            dist = np.linalg.norm(visible_positions[i] - visible_positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
    
    # Set lattice for PBC
    lattice_matrix = vtkMatrix3x3()
    cell_transposed = cell.T
    for i in range(3):
        for j in range(3):
            lattice_matrix.SetElement(i, j, float(cell_transposed[i, j]))
    molecule.SetLattice(lattice_matrix)
    
    # Create mapper
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    
    if mode == "ball_and_stick":
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetAtomicRadiusScaleFactor(0.025)  # 0.25 Å = 0.025 nm
        mapper.SetBondRadius(0.0075)  # 0.075 Å = 0.0075 nm
    
    mapper.SetRenderAtoms(True)
    mapper.SetRenderBonds(True)
    mapper.SetBondColor(180, 180, 180)  # Gray bonds
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor
```

### MoleculetypeRegistry Usage
```python
# Source: moleculetype_registry.py
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

# Initialize registry
registry = MoleculetypeRegistry()

# Register liquid solute (gets _LIQ suffix)
ch4_liq_name = registry.register_liquid_solute('CH4')
# Returns: 'CH4_LIQ'

thf_liq_name = registry.register_liquid_solute('THF')
# Returns: 'THF_LIQ'

# Use in GROMACS export
gromacs_name = registry.get_gromacs_name('liquid_CH4')
# Returns: 'CH4_LIQ'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Center-of-mass overlap check | All-atom overlap check | Ion insertion | Accurate placement for complex molecules |
| Hardcoded molecule type names | MoleculetypeRegistry | Phase 32 | Unique naming (CH4_HYD vs CH4_LIQ) |
| Manual bond detection | Distance-based auto-detection | Hydrate rendering | Automatic bonds for any molecule |
| Single thread placement | (Ion: still synchronous) | - | Ion insertion is fast enough (< 1 sec) |

**Deprecated/outdated:**
- Euler angles for rotation: Use scipy Rotation.random() instead for numerical stability

## Open Questions

### 1. Should Solute Insertion Use Worker Thread?
**What we know:** Ion insertion is synchronous (runs directly in main_window.py)
**What's unclear:** Will solute insertion (with rotation, multiple attempts) be slow enough to freeze UI?
**Recommendation:** Start with synchronous approach like ion insertion. If placement takes > 1 second for typical cases, add QThread worker following hydrate_worker.py pattern.

### 2. What is Reasonable Concentration Range?
**What we know:** Ion panel uses 0.0-5.0 M range (ion_panel.py line 124)
**What's unclear:** What are realistic ranges for THF and CH₄ solutes?
**Recommendation:** Research typical solubility limits:
- CH₄ in water: ~0.001-0.01 M at STP
- THF in water: Miscible (any concentration)
Set panel range to 0.0-2.0 M initially, add validation warning if user exceeds solubility.

### 3. Should wt% Unit Option Be Implemented?
**What we know:** CONTEXT.md mentions "mol/L or wt% unit options in dropdown selector"
**What's unclear:** Is this required for Phase 33 or deferred?
**Recommendation:** Implement mol/L only for Phase 33 (simpler, matches ion panel). Add wt% as enhancement if users request it. Conversion requires knowing solute molecular weight.

### 4. Max Attempts Before Failure
**What we know:** CONTEXT.md specifies "Maximum 1000 attempts per molecule"
**What's unclear:** Is 1000 sufficient for all liquid region sizes?
**Recommendation:** Implement 1000 as configurable parameter. Log warning if approaching max attempts frequently (indicates concentration too high for liquid volume).

## Sources

### Primary (HIGH confidence)
- quickice/structure_generation/ion_inserter.py - Overlap checking, concentration calculation, partial success pattern
- quickice/gui/ion_panel.py - Tab layout, UI structure, concentration input
- quickice/gui/hydrate_renderer.py - Ball-and-stick rendering, CPK colors, bond detection
- quickice/structure_generation/moleculetype_registry.py - Unique GROMACS naming
- quickice/data/ch4.itp - Bundled CH₄ ITP file with GAFF2 parameters
- quickice/data/thf.itp - Bundled THF ITP file with GAFF2 parameters

### Secondary (MEDIUM confidence)
- quickice/gui/main_window.py - Tab integration, signal connections
- quickice/structure_generation/types.py - Data structures (InterfaceStructure, IonConfig pattern)
- quickice/structure_generation/itp_parser.py - ITP file parsing
- quickice/gui/export.py - GROMACS export patterns

### Tertiary (LOW confidence)
- scipy.spatial.transform.Rotation documentation - Random rotation matrix generation (external source, not codebase)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Ion insertion provides proven patterns for overlap checking and concentration calculation
- Architecture: HIGH - Tab layout, UI structure, and data flow match existing ion/hydrate patterns
- Pitfalls: HIGH - Documented from actual code (MW atoms, ice_atom_count boundary, unit conversion)

**Research date:** 2026-05-05
**Valid until:** 30 days (stable patterns, but check for Phase 35 ion tab position changes)
