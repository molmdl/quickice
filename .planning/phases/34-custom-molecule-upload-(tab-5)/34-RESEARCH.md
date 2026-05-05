# Phase 34: Custom Molecule Upload - Research

**Researched:** 2026-05-05
**Domain:** GROMACS file parsing, custom molecule validation, VTK rendering, PySide6 UI patterns
**Confidence:** HIGH

## Summary

Phase 34 builds on existing infrastructure from Phases 32 and 33 to enable custom molecule upload via .gro/.itp file pairs. The GRO parser, ITP parser, molecule validator, and MoleculetypeRegistry already exist. The SoluteInserter pattern provides a template for custom molecule insertion with overlap checking.

Key findings:
- **GRO parsing**: Already implemented in `gro_parser.py` with fixed-width column parsing (positions, atom names, cell)
- **GRO residue name**: Located in columns 6-10 (0-indexed: 5-9), must be extracted for validation
- **ITP parsing**: Already implemented in `itp_parser.py` with regex-based molecule name, atom count, and atom types extraction
- **Validation**: `molecule_validator.py` checks atom count consistency, needs residue name validation added
- **Placement modes**: Random (reuse SoluteInserter pattern) and Custom (new implementation with position/rotation inputs)
- **Overlap checking**: All-atom checking with cKDTree from scipy, VDW radii-based separation (0.3 nm minimum)
- **Rendering**: Reuse ball-and-stick pattern from `solute_renderer.py` with distinct colors for custom molecules
- **Export**: Copy custom .itp to output directory (pattern established in export.py)

**Primary recommendation:** Extend existing GRO parser to extract residue names, enhance molecule validator with residue name consistency checks, create CustomMoleculeInserter adapting SoluteInserter pattern with two placement modes.

## Standard Stack

The established libraries/tools for this domain (all already in codebase):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | 6.10.2 | File dialogs, UI controls | Existing GUI framework |
| VTK | 9.5.2 | 3D molecule rendering | Established renderer with vtkMoleculeMapper |
| numpy | - | Position arrays, matrix operations | Standard array library |
| scipy | - | cKDTree for overlap checking, Rotation for orientations | Optimized spatial data structures, rotation matrices |
| pathlib | - | File path handling | Python standard library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| QFileDialog | 6.10.2 | .gro/.itp file selection | User file upload |
| QMessageBox | 6.10.2 | Validation error dialogs | Error presentation |
| QComboBox | 6.10.2 | Placement mode selection | Random vs Custom mode |
| QDoubleSpinBox | 6.10.2 | Numeric inputs | Concentration, rotation angles |
| QLineEdit | 6.10.2 | Position text fields | X, Y, Z coordinates |

### Existing Infrastructure (Don't Rebuild)
| Component | Location | Purpose |
|-----------|----------|---------|
| GRO parser | `quickice/structure_generation/gro_parser.py` | Parse .gro files (positions, atom names, cell) |
| ITP parser | `quickice/structure_generation/itp_parser.py` | Parse .itp files (molecule name, atom count, types) |
| Molecule validator | `quickice/structure_generation/molecule_validator.py` | Validate GRO/ITP consistency |
| MoleculetypeRegistry | `quickice/structure_generation/moleculetype_registry.py` | Unique GROMACS naming (CUSTOM_MOL_1, etc.) |
| SoluteInserter | `quickice/structure_generation/solute_inserter.py` | Overlap checking, rotation, placement template |
| SoluteRenderer | `quickice/gui/solute_renderer.py` | Ball-and-stick rendering template |
| Export pattern | `quickice/gui/export.py` | GROMACS export with .itp copying |

**Installation:**
All dependencies already installed (PySide6, VTK, numpy, scipy).

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── structure_generation/
│   ├── gro_parser.py (ENHANCE: add residue name extraction)
│   ├── itp_parser.py (EXISTS: no changes needed)
│   ├── molecule_validator.py (ENHANCE: add residue name validation)
│   ├── moleculetype_registry.py (EXISTS: already supports custom molecules)
│   ├── custom_molecule_inserter.py (NEW: random/custom placement)
│   └── types.py (ENHANCE: add CustomMoleculeConfig, CustomMoleculeStructure)
├── gui/
│   ├── custom_molecule_panel.py (NEW: file upload, placement controls)
│   ├── custom_molecule_worker.py (NEW: background validation/insertion)
│   ├── custom_molecule_renderer.py (NEW: distinct rendering style)
│   └── custom_molecule_viewer.py (NEW: 3D viewer widget)
└── output/
    └── gromacs_writer.py (ENHANCE: handle custom .itp bundling)
```

### Pattern 1: GRO Residue Name Extraction
**What:** Extract residue name from GRO file atom records for validation
**When to use:** When validating GRO/ITP consistency (CUSTOM-04)
**Example:**
```python
# Source: Based on gro_parser.py existing pattern
def extract_residue_name_from_gro(gro_path: Path) -> str | None:
    """Extract residue name from first atom line in GRO file.
    
    GRO format (fixed-width columns):
        - Columns 1-5: Residue number (integer)
        - Columns 6-10: Residue name (5 characters)
        - Columns 11-15: Atom name (5 characters)
    
    Args:
        gro_path: Path to .gro file
        
    Returns:
        Residue name (e.g., "MOL", "CH4") or None if file invalid
    """
    with open(gro_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 3:
        return None
    
    # First atom line is at index 2 (after title and atom count)
    first_atom_line = lines[2]
    
    # Extract residue name from columns 6-10 (0-indexed: 5-9)
    residue_name = first_atom_line[5:10].strip()
    
    return residue_name if residue_name else None
```

### Pattern 2: Molecule Validation with Residue Name Check
**What:** Validate GRO/ITP consistency including residue name matching
**When to use:** After both .gro and .itp files uploaded (CUSTOM-03, CUSTOM-04)
**Example:**
```python
# Source: Extends molecule_validator.py existing pattern
from dataclasses import dataclass
from typing import List

@dataclass
class ValidationResult:
    """Result of GRO/ITP consistency validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    residue_name_mismatch: bool = False  # NEW: flag for dialog trigger
    gro_residue_name: str | None = None
    itp_residue_name: str | None = None

def validate_custom_molecule(
    gro_path: Path,
    itp_info: ITPMoleculeInfo
) -> ValidationResult:
    """Validate GRO file consistency with ITP file.
    
    Checks:
    1. Atom count matches between GRO and ITP
    2. Residue name consistency (warn if mismatch, allow override)
    3. [ atomtypes ] section presence (warning if missing)
    
    Args:
        gro_path: Path to .gro file
        itp_info: Parsed ITP information
        
    Returns:
        ValidationResult with detailed error/warning messages
    """
    errors = []
    warnings = []
    
    # Parse GRO file
    try:
        positions, atom_names, cell = parse_gro_file(gro_path)
        gro_atom_count = len(positions)
        gro_residue_name = extract_residue_name_from_gro(gro_path)
    except Exception as e:
        errors.append(f"Failed to parse GRO file: {e}")
        return ValidationResult(False, errors, warnings)
    
    # Check atom count (BLOCKING)
    if gro_atom_count != itp_info.atom_count:
        errors.append(
            f"Atom count mismatch:\n"
            f"  GRO file has {gro_atom_count} atoms\n"
            f"  ITP file defines {itp_info.atom_count} atoms"
        )
    
    # Check residue name (NON-BLOCKING, triggers dialog)
    residue_name_mismatch = False
    itp_residue_name = itp_info.molecule_name
    
    if gro_residue_name and itp_residue_name:
        if gro_residue_name != itp_residue_name:
            residue_name_mismatch = True
            warnings.append(
                f"Residue name mismatch:\n"
                f"  GRO file uses '{gro_residue_name}'\n"
                f"  ITP file uses '{itp_residue_name}'\n"
                f"User must choose to proceed or re-select files."
            )
    
    # Check [ atomtypes ] section (warning)
    if not itp_info.has_atomtypes_section:
        warnings.append(
            f"Missing [ atomtypes ] section in ITP file.\n"
            f"User must provide atom type parameters separately."
        )
    
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        residue_name_mismatch=residue_name_mismatch,
        gro_residue_name=gro_residue_name,
        itp_residue_name=itp_residue_name
    )
```

### Pattern 3: Custom Molecule Placement (Two Modes)
**What:** Random placement with overlap checking OR custom position/rotation
**When to use:** After validation, user selects placement mode (CUSTOM-07, CUSTOM-08)
**Example:**
```python
# Source: Adapts SoluteInserter pattern from solute_inserter.py
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

@dataclass
class CustomMoleculeConfig:
    """Configuration for custom molecule placement."""
    placement_mode: str  # "random" or "custom"
    positions: List[Tuple[float, float, float]] | None = None  # For custom mode
    rotations: List[Tuple[float, float, float]] | None = None  # Euler angles (α, β, γ) in degrees
    min_separation: float = 0.3  # nm
    max_attempts: int = 1000  # For random mode

class CustomMoleculeInserter:
    """Handles custom molecule placement with two modes.
    
    Mode 1 (Random): Random positions in liquid region, random rotations,
                     all-atom overlap checking (reuses SoluteInserter pattern)
    
    Mode 2 (Custom): User-specified positions and rotations (Euler angles),
                     no overlap checking (user responsibility)
    """
    
    def __init__(self, config: CustomMoleculeConfig):
        self.config = config
        self.registry = MoleculetypeRegistry()
    
    def _euler_to_rotation_matrix(
        self,
        alpha: float,
        beta: float,
        gamma: float
    ) -> np.ndarray:
        """Convert Euler angles (α, β, γ) to rotation matrix.
        
        Uses ZXZ convention (common in crystallography).
        
        Args:
            alpha: First rotation around Z-axis (degrees)
            beta: Second rotation around X-axis (degrees)
            gamma: Third rotation around Z-axis (degrees)
            
        Returns:
            (3, 3) rotation matrix
        """
        # Use scipy Rotation for robust conversion
        # ZXZ Euler angles = 'zxz' extrinsic = 'zyz' intrinsic
        rotation = Rotation.from_euler('ZXZ', [alpha, beta, gamma], degrees=True)
        return rotation.as_matrix()
    
    def place_random(
        self,
        template_positions: np.ndarray,
        structure: InterfaceStructure,
        n_molecules: int
    ) -> List[np.ndarray]:
        """Place molecules randomly with overlap checking.
        
        Reuses SoluteInserter pattern:
        - Build cKDTree from existing atoms (exclude MW virtual sites)
        - Sample random positions in liquid region bounds
        - Generate random rotations using Rotation.random()
        - Check all-atom overlaps with min_separation threshold
        
        Args:
            template_positions: Template molecule positions (centered at origin)
            structure: InterfaceStructure with ice + water
            n_molecules: Number of molecules to place
            
        Returns:
            List of placed molecule positions (each N_atoms x 3)
        """
        # Implementation mirrors SoluteInserter.insert_solutes()
        # Build tree, sample positions, rotate, translate, check overlaps
        pass
    
    def place_custom(
        self,
        template_positions: np.ndarray,
        positions: List[Tuple[float, float, float]],
        rotations: List[Tuple[float, float, float]]
    ) -> List[np.ndarray]:
        """Place molecules at user-specified positions with rotations.
        
        No overlap checking (user responsibility).
        
        Args:
            template_positions: Template molecule positions (centered at origin)
            positions: List of (x, y, z) center-of-mass positions in nm
            rotations: List of (α, β, γ) Euler angles in degrees
            
        Returns:
            List of placed molecule positions (each N_atoms x 3)
        """
        placed = []
        
        for com, euler_angles in zip(positions, rotations):
            # Get rotation matrix from Euler angles
            rot_matrix = self._euler_to_rotation_matrix(*euler_angles)
            
            # Rotate template around origin
            center = template_positions.mean(axis=0)
            centered = template_positions - center
            rotated = centered @ rot_matrix.T
            
            # Translate to COM position
            placed_positions = rotated + np.array(com)
            placed.append(placed_positions)
        
        return placed
```

### Pattern 4: File Upload UI with Validation Feedback
**What:** Separate upload buttons for .gro and .itp with immediate validation status
**When to use:** User interface for custom molecule upload (CUSTOM-01, CUSTOM-02)
**Example:**
```python
# Source: Pattern from export.py QFileDialog usage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Signal

class CustomMoleculePanel(QWidget):
    """Panel for custom molecule upload and placement configuration.
    
    Layout:
    - File Upload Section (separate .gro and .itp buttons)
    - Validation Status Section (shows errors/warnings)
    - Placement Mode Section (Random vs Custom)
    - Position/Rotation Inputs (visible when Custom mode selected)
    """
    
    files_uploaded = Signal(bool)  # Emitted when both files valid
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gro_path = None
        self.itp_path = None
        self.itp_info = None
        self.validation_result = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup file upload buttons with validation status."""
        layout = QVBoxLayout(self)
        
        # GRO file upload
        gro_layout = QHBoxLayout()
        self.gro_button = QPushButton("Upload .gro File")
        self.gro_button.clicked.connect(self._upload_gro)
        self.gro_status = QLabel("No file selected")
        gro_layout.addWidget(self.gro_button)
        gro_layout.addWidget(self.gro_status)
        layout.addLayout(gro_layout)
        
        # ITP file upload
        itp_layout = QHBoxLayout()
        self.itp_button = QPushButton("Upload .itp File")
        self.itp_button.clicked.connect(self._upload_itp)
        self.itp_status = QLabel("No file selected")
        itp_layout.addWidget(self.itp_button)
        itp_layout.addWidget(self.itp_status)
        layout.addLayout(itp_layout)
        
        # Validation status display
        self.validation_label = QLabel("")
        layout.addWidget(self.validation_label)
    
    def _upload_gro(self):
        """Handle GRO file selection."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select GRO File",
            "",
            "GRO Files (*.gro);;All Files (*)"
        )
        
        if filepath:
            self.gro_path = Path(filepath)
            self.gro_status.setText(self.gro_path.name)
            self._validate_files()
    
    def _upload_itp(self):
        """Handle ITP file selection."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select ITP File",
            "",
            "ITP Files (*.itp);;All Files (*)"
        )
        
        if filepath:
            self.itp_path = Path(filepath)
            try:
                self.itp_info = parse_itp_file(self.itp_path)
                self.itp_status.setText(
                    f"{self.itp_path.name} ({self.itp_info.atom_count} atoms)"
                )
                self._validate_files()
            except Exception as e:
                self.itp_status.setText(f"Error: {e}")
                self.itp_info = None
    
    def _validate_files(self):
        """Validate both files when uploaded."""
        if self.gro_path and self.itp_info:
            self.validation_result = validate_custom_molecule(
                self.gro_path, self.itp_info
            )
            
            # Show validation status
            if self.validation_result.is_valid:
                if self.validation_result.residue_name_mismatch:
                    # Show dialog for residue name mismatch
                    self._show_residue_mismatch_dialog()
                else:
                    self.validation_label.setText("✓ Files validated successfully")
                    self.validation_label.setStyleSheet("color: green;")
                    self.files_uploaded.emit(True)
            else:
                self.validation_label.setText(
                    "✗ Validation failed:\n" + "\n".join(self.validation_result.errors)
                )
                self.validation_label.setStyleSheet("color: red;")
                self.files_uploaded.emit(False)
    
    def _show_residue_mismatch_dialog(self):
        """Show dialog asking if ITP residue name should override."""
        reply = QMessageBox.question(
            self,
            "Residue Name Mismatch",
            f"GRO file uses residue name '{self.validation_result.gro_residue_name}'\n"
            f"ITP file uses residue name '{self.validation_result.itp_residue_name}'\n\n"
            f"Use ITP residue name? (Select 'No' to re-upload files)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Accept ITP residue name, proceed
            self.validation_label.setText(
                f"✓ Files validated (using ITP residue name: "
                f"{self.validation_result.itp_residue_name})"
            )
            self.validation_label.setStyleSheet("color: green;")
            self.files_uploaded.emit(True)
        else:
            # Reject, require re-upload
            self.validation_label.setText(
                "Residue name mismatch. Please upload matching files."
            )
            self.validation_label.setStyleSheet("color: orange;")
            self.files_uploaded.emit(False)
```

### Pattern 5: Custom Molecule Rendering with Distinct Style
**What:** Render custom molecules with different colors to distinguish from predefined molecules
**When to use:** Visualizing custom molecules in 3D viewer (CUSTOM-11, VIS-02)
**Example:**
```python
# Source: Adapts solute_renderer.py pattern
from vtkmodules.all import vtkMoleculeMapper, vtkMolecule, vtkActor

# Distinct colors for custom molecules (different from CH4/THF)
CUSTOM_MOLECULE_COLORS: dict[str, tuple[float, float, float]] = {
    "CUSTOM_MOL_1": (0.8, 0.4, 0.8),  # Purple
    "CUSTOM_MOL_2": (0.4, 0.8, 0.8),  # Cyan
    "CUSTOM_MOL_3": (0.8, 0.8, 0.4),  # Yellow
    "default": (0.8, 0.6, 0.4),       # Orange (fallback)
}

def create_custom_molecule_actor(
    positions: np.ndarray,
    atom_names: list[str],
    cell: np.ndarray,
    moleculetype_name: str,
    mode: str = "ball_and_stick"
) -> vtkActor | None:
    """Create VTK actor for custom molecule with distinct coloring.
    
    Args:
        positions: (N_atoms, 3) positions in nm
        atom_names: List of atom names
        cell: (3, 3) unit cell vectors in nm
        moleculetype_name: GROMACS moleculetype name (e.g., "CUSTOM_MOL_1")
        mode: Rendering mode
        
    Returns:
        vtkActor with custom molecule rendered
    """
    molecule = vtkMolecule()
    
    # Add atoms (skip MW virtual sites)
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
    for i in range(len(atom_ids)):
        for j in range(i + 1, len(atom_ids)):
            dist = np.linalg.norm(positions[i] - positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
    
    # Set lattice
    lattice_matrix = vtkMatrix3x3()
    cell_transposed = cell.T
    for i in range(3):
        for j in range(3):
            lattice_matrix.SetElement(i, j, float(cell_transposed[i, j]))
    molecule.SetLattice(lattice_matrix)
    
    # Create mapper
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    mapper.UseBallAndStickSettings()
    mapper.SetAtomicRadiusTypeToVDWRadius()
    mapper.SetAtomicRadiusScaleFactor(0.25 * ANGSTROM_TO_NM)
    mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)
    mapper.SetBondColor(180, 180, 180)
    
    # Get distinct color for this custom molecule
    color = CUSTOM_MOLECULE_COLORS.get(
        moleculetype_name,
        CUSTOM_MOLECULE_COLORS["default"]
    )
    
    # Note: VTK uses per-atom colors, but we can set a global color
    # by using the mapper's atom color array
    mapper.SetRenderAtoms(True)
    mapper.SetRenderBonds(True)
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor
```

### Anti-Patterns to Avoid
- **Rebuilding GRO/ITP parsers**: Use existing parsers, only extend for residue name extraction
- **Skipping validation**: Always validate atom count and residue name consistency
- **Ignoring overlap checking**: Random placement MUST use all-atom overlap checking
- **Re-implementing rotation matrices**: Use scipy Rotation class for Euler angle conversion
- **Custom bond detection**: Use existing BOND_DISTANCE_THRESHOLD (0.16 nm) from solute_renderer.py

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO file parsing | Custom regex parser | `gro_parser.parse_gro_file()` | Handles triclinic cells, fixed-width columns correctly |
| ITP file parsing | String splitting | `itp_parser.parse_itp_file()` | Handles comments, sections, atom types extraction |
| GROMACS naming | Manual counters | `MoleculetypeRegistry.register_custom_molecule()` | Avoids name collisions, tracks reserved names |
| Overlap checking | Distance loops | `scipy.spatial.cKDTree` | O(N log N) vs O(N²), handles large systems efficiently |
| Rotation matrices | Manual trigonometry | `scipy.spatial.transform.Rotation` | Numerically stable, handles all conventions |
| Bond detection | Distance matrix | `BOND_DISTANCE_THRESHOLD = 0.16` from solute_renderer.py | Established threshold for covalent bonds |
| File dialogs | Custom widget | `QFileDialog.getOpenFileName()` | Native OS dialogs, filter support |

**Key insight:** GROMACS file formats have subtle edge cases (triclinic cells, fixed-width columns, section delimiters) that existing parsers handle correctly.

## Common Pitfalls

### Pitfall 1: GRO Residue Name Extraction Column Misalignment
**What goes wrong:** Extracting residue name from wrong columns (e.g., columns 1-5 instead of 6-10)
**Why it happens:** GRO format uses 0-indexed vs 1-indexed columns in documentation
**How to avoid:** Use columns 5-9 (0-indexed), which map to columns 6-10 (1-indexed spec)
**Warning signs:** Residue name contains numbers or is empty, validation fails unexpectedly

### Pitfall 2: Ignoring MW Virtual Sites in Overlap Checking
**What goes wrong:** False positive overlaps with TIP4P water MW atoms (placed ~0.015 nm from oxygen)
**Why it happens:** MW atoms are massless virtual sites in TIP4P models
**How to avoid:** Exclude atoms named "MW" from overlap checking tree (see SoluteInserter._build_existing_atoms_tree())
**Warning signs:** Overlap detected for valid placements, placement fails after few attempts

### Pitfall 3: Euler Angle Convention Confusion
**What goes wrong:** Rotation doesn't match expected orientation
**Why it happens:** Multiple Euler angle conventions (ZXZ, ZYZ, extrinsic vs intrinsic)
**How to avoid:** Use scipy Rotation.from_euler('ZXZ', [alpha, beta, gamma], degrees=True) and document convention in UI
**Warning signs:** Molecule appears rotated incorrectly, user-specified orientations don't match preview

### Pitfall 4: Missing [ atomtypes ] Section in Custom ITP
**What goes wrong:** GROMACS grompp fails with "atomtype not found" error
**Why it happens:** User provides molecule ITP without atom type definitions
**How to avoid:** Check for [ atomtypes ] section during validation, warn user they must provide separate atomtypes file
**Warning signs:** Validation shows warning, export succeeds but GROMACS run fails

### Pitfall 5: Residue Name Mismatch Handling
**What goes wrong:** GRO residue name doesn't match ITP moleculetype name, causing GROMACS errors
**Why it happens:** User generated GRO and ITP from different sources
**How to avoid:** Validate residue name consistency, show dialog with override option (ITP name takes precedence)
**Warning signs:** GRO has "MOL" but ITP has "ETHANOL", validation shows mismatch warning

### Pitfall 6: Custom Placement Without Liquid Region Detection
**What goes wrong:** User places molecule outside liquid region (in ice or outside box)
**Why it happens:** UI shows placement controls before detecting liquid region bounds
**How to avoid:** Require liquid region detection before showing placement controls, constrain XYZ inputs to liquid bounds
**Warning signs:** Molecule placed in ice region, invalid GROMACS structure

## Code Examples

Verified patterns from existing codebase:

### GRO Parsing (Existing)
```python
# Source: quickice/structure_generation/gro_parser.py
from pathlib import Path
import numpy as np

def parse_gro_file(filepath: Path | str) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Load and parse GRO file.
    
    Returns:
        Tuple of (positions, atom_names, cell):
            - positions: (N_atoms, 3) array in nm
            - atom_names: List of atom names
            - cell: (3, 3) cell vectors in nm
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"GRO file not found: {filepath}")
    
    with open(filepath, "r") as f:
        gro_string = f.read()
    
    lines = gro_string.strip().split("\n")
    n_atoms = int(lines[1])
    
    positions = np.zeros((n_atoms, 3), dtype=float)
    atom_names = []
    
    for i in range(n_atoms):
        line = lines[2 + i]
        atom_name = line[10:15].strip()  # Columns 11-15
        atom_names.append(atom_name)
        
        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        positions[i] = [x, y, z]
    
    # Parse cell (handles triclinic)
    cell_line = lines[-1].split()
    if len(cell_line) == 3:
        cell = np.diag([float(v) for v in cell_line])
    else:
        v1x, v2y, v3z = float(cell_line[0]), float(cell_line[1]), float(cell_line[2])
        v1y, v1z, v2x, v2z, v3x, v3y = [float(v) for v in cell_line[3:9]]
        cell = np.array([
            [v1x, v1y, v1z],
            [v2x, v2y, v2z],
            [v3x, v3y, v3z]
        ])
    
    return positions, atom_names, cell
```

### ITP Parsing (Existing)
```python
# Source: quickice/structure_generation/itp_parser.py
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ITPMoleculeInfo:
    """Parsed information from ITP file."""
    molecule_name: str
    atom_count: int
    atom_types: List[str]
    has_atomtypes_section: bool

def parse_itp_file(filepath: Path) -> ITPMoleculeInfo:
    """Parse GROMACS .itp topology file."""
    if not filepath.exists():
        raise FileNotFoundError(f"ITP file not found: {filepath}")
    
    content = filepath.read_text()
    
    # Extract moleculetype name
    mol_match = re.search(
        r'\[\s*moleculetype\s*\]\s*\n\s*;.*?\n\s*(\w+)',
        content,
        re.IGNORECASE | re.DOTALL
    )
    
    if not mol_match:
        mol_match = re.search(
            r'\[\s*moleculetype\s*\]\s*\n\s*(\w+)',
            content,
            re.IGNORECASE
        )
    
    if not mol_match:
        raise ValueError(f"Missing [ moleculetype ] section in {filepath.name}")
    
    molecule_name = mol_match.group(1)
    
    # Extract atoms section
    atoms_match = re.search(
        r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    
    if not atoms_match:
        raise ValueError(f"Missing [ atoms ] section in {filepath.name}")
    
    atoms_section = atoms_match.group(1)
    atom_lines = [
        line for line in atoms_section.split('\n')
        if line.strip() and not line.strip().startswith(';')
    ]
    
    atom_types = []
    for line in atom_lines:
        fields = line.split()
        if len(fields) >= 2:
            atom_types.append(fields[1])  # Atom type is second column
    
    atom_count = len(atom_types)
    
    # Check for [ atomtypes ] section
    has_atomtypes = bool(re.search(
        r'\[\s*atomtypes\s*\]',
        content,
        re.IGNORECASE
    ))
    
    return ITPMoleculeInfo(
        molecule_name=molecule_name,
        atom_count=atom_count,
        atom_types=atom_types,
        has_atomtypes_section=has_atomtypes
    )
```

### Moleculetype Registry Usage (Existing)
```python
# Source: quickice/structure_generation/moleculetype_registry.py
class MoleculetypeRegistry:
    """Registry for unique GROMACS moleculetype naming."""
    
    RESERVED_NAMES = {
        "SOL", "NA", "CL", "CH4", "THF", "CO2", "H2",
        "CH4_HYD", "CH4_LIQ", "THF_HYD", "THF_LIQ"
    }
    
    def register_custom_molecule(self, user_name: str = "MOL") -> str:
        """Register custom molecule with unique name.
        
        Returns:
            Unique molecule name (e.g., 'MOL', 'MOL_1', 'MOL_2')
            
        Example:
            >>> registry.register_custom_molecule('MOL')
            'MOL'
            >>> registry.register_custom_molecule('MOL')
            'MOL_1'
        """
        if user_name.upper() in self.RESERVED_NAMES:
            raise ValueError(f"Cannot use reserved name '{user_name}'")
        
        existing_names = set(self._registered.values())
        
        if user_name not in existing_names:
            self._counter += 1
            source_key = f"custom_{self._counter}"
            self._registered[source_key] = user_name
            return user_name
        
        # Name collision - increment counter
        counter = 1
        while f"{user_name}_{counter}" in existing_names:
            counter += 1
        
        unique_name = f"{user_name}_{counter}"
        self._counter += 1
        source_key = f"custom_{self._counter}"
        self._registered[source_key] = unique_name
        return unique_name
```

### Overlap Checking with cKDTree (Existing)
```python
# Source: quickice/structure_generation/solute_inserter.py
from scipy.spatial import cKDTree

def _build_existing_atoms_tree(
    structure: InterfaceStructure,
    exclude_water: bool = False,
) -> cKDTree | None:
    """Build cKDTree from existing atoms for overlap checking.
    
    Note:
        Excludes MW atoms (virtual sites) to avoid false positives.
        MW atoms are massless virtual sites in TIP4P water models,
        placed very close (~0.015 nm) to oxygen atoms.
    """
    existing_positions = []
    
    # Add atoms, excluding MW virtual sites
    for i in range(len(structure.positions)):
        atom_name = structure.atom_names[i] if i < len(structure.atom_names) else ""
        if atom_name != "MW":
            existing_positions.append(structure.positions[i])
    
    if existing_positions:
        return cKDTree(np.array(existing_positions))
    return None

def _check_overlap(
    positions: np.ndarray,
    existing_tree: cKDTree,
    min_separation: float,
) -> bool:
    """Check if molecule overlaps with existing atoms.
    
    Args:
        positions: (N_atoms, 3) positions for molecule
        existing_tree: cKDTree of existing atoms
        min_separation: Minimum allowed distance in nm
        
    Returns:
        True if overlap detected, False if placement is valid
    """
    for atom_pos in positions:
        min_dist = existing_tree.query(atom_pos, k=1)[0]
        if min_dist < min_separation:
            return True
    return False
```

### GROMACS Export with ITP Copying (Existing)
```python
# Source: quickice/gui/export.py (adapted pattern)
from pathlib import Path
import shutil

def export_custom_molecule_gromacs(
    gro_path: Path,
    custom_itp_path: Path,
    output_dir: Path,
    moleculetype_name: str
) -> tuple[Path, Path]:
    """Export custom molecule with bundled ITP file.
    
    Args:
        gro_path: Path to custom molecule .gro file
        custom_itp_path: Path to custom molecule .itp file
        output_dir: Output directory for GROMACS files
        moleculetype_name: GROMACS moleculetype name (e.g., "CUSTOM_MOL_1")
        
    Returns:
        Tuple of (output_gro_path, output_top_path)
    """
    # Copy custom .itp to output directory
    output_itp = output_dir / custom_itp_path.name
    shutil.copy(custom_itp_path, output_itp)
    
    # Generate .gro file with correct residue names
    # (use moleculetype_name as residue name in GRO)
    output_gro = output_dir / f"{moleculetype_name}.gro"
    # ... write GRO file ...
    
    # Generate .top file with #include for custom ITP
    output_top = output_dir / f"{moleculetype_name}.top"
    top_content = f"""; Custom molecule topology
#include "{custom_itp_path.name}"

[ molecules ]
; Compound        nmols
{moleculetype_name}              1
"""
    output_top.write_text(top_content)
    
    return output_gro, output_top
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual distance checking (O(N²)) | cKDTree spatial indexing (O(N log N)) | Phase 33 | Efficient overlap checking for 10k+ atoms |
| Quaternions for rotation | scipy Rotation class | Phase 33 | Supports all conventions, numerically stable |
| Separate .itp for each molecule | Shared tip4p-ice.itp | Phase 33 | Cleaner export structure |
| Hardcoded CH4/THF | MoleculetypeRegistry pattern | Phase 32 | Extensible to custom molecules |

**Deprecated/outdated:**
- Direct distance loops for overlap checking: Use cKDTree instead
- Manual rotation matrix calculation: Use scipy Rotation class
- Separate ITP files for each molecule instance: Share common topologies

## Open Questions

Things that couldn't be fully resolved:

1. **Default molecule count for Random mode**
   - What we know: SoluteInserter calculates from concentration, but custom molecules may not have concentration
   - What's unclear: Should Random mode use concentration (with default 0.1 M?) or explicit count?
   - Recommendation: Add "Molecule Count" input field for Random mode (easier for users)

2. **Position input format for Custom mode**
   - What we know: Text fields for X, Y, Z (from CONTEXT.md)
   - What's unclear: Should inputs be QLineEdit or QDoubleSpinBox? QLineEdit allows flexible input but needs validation
   - Recommendation: Use QDoubleSpinBox with range [0, box_dimension] for type safety, default to liquid region center

3. **Multiple custom molecules of same type**
   - What we know: MoleculetypeRegistry generates unique names (MOL, MOL_1, MOL_2)
   - What's unclear: Should each uploaded file create a new moleculetype, or can user reuse same file?
   - Recommendation: Each upload creates new moleculetype (simpler), allow "Reset" button to start fresh

4. **Liquid region bounds detection**
   - What we know: SoluteInserter calculates liquid bounds from water atom positions
   - What's unclear: Should we use water atom bounding box or box dimensions? Water atoms may not fill entire box
   - Recommendation: Use water atom bounds (min/max coordinates) for realistic placement constraints

## Sources

### Primary (HIGH confidence)
- GRO parser implementation: `quickice/structure_generation/gro_parser.py` - verified parsing logic
- ITP parser implementation: `quickice/structure_generation/itp_parser.py` - verified regex patterns
- Molecule validator implementation: `quickice/structure_generation/molecule_validator.py` - validation pattern
- MoleculetypeRegistry implementation: `quickice/structure_generation/moleculetype_registry.py` - naming logic
- SoluteInserter implementation: `quickice/structure_generation/solute_inserter.py` - overlap checking, rotation, placement
- SoluteRenderer implementation: `quickice/gui/solute_renderer.py` - ball-and-stick rendering pattern
- Export pattern: `quickice/gui/export.py` - GROMACS export with ITP copying
- PySide6 QFileDialog usage: Multiple examples in export.py

### Secondary (MEDIUM confidence)
- GROMACS file format documentation: https://manual.gromacs.org/current/reference-manual/file-formats.html
- GRO residue name column specification: Verified via test script (columns 6-10, 1-indexed)
- scipy Rotation documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html
- VTK molecule rendering: https://vtk.org/doc/nightly/html/classvtkMoleculeMapper.html

### Tertiary (LOW confidence)
- None - all findings verified with codebase or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components exist in codebase
- Architecture: HIGH - Patterns established in Phase 33, clear adaptation path
- Pitfalls: HIGH - Identified from existing codebase edge cases (MW sites, GRO columns, residue names)

**Research date:** 2026-05-05
**Valid until:** 30 days (stable architecture, established patterns)
