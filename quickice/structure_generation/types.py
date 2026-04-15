"""Data types for structure generation."""

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


# Molecule type information: atom count, residue name, typical charge
MOLECULE_TYPE_INFO: dict[str, dict[str, Any]] = {
    "ice":   {"atoms": 3, "res_name": "SOL", "description": "Ice (TIP3P: O, H, H)"},
    "water": {"atoms": 4, "res_name": "SOL", "description": "Water (TIP4P-ICE: OW, HW1, HW2, MW)"},
    "na":    {"atoms": 1, "res_name": "NA",  "description": "Sodium ion"},
    "cl":    {"atoms": 1, "res_name": "CL",  "description": "Chloride ion"},
    "ch4":   {"atoms": 5, "res_name": "CH4", "description": "Methane"},
    "thf":   {"atoms": 12, "res_name": "THF", "description": "Tetrahydrofuran"},
}


@dataclass
class MoleculeIndex:
    """Tracks molecule position in atom array.
    
    Enables handling of variable atoms-per-molecule:
    - ions (1 atom): Na, Cl
    - ice (3 atoms): O, H, H
    - water (4 atoms): OW, HW1, HW2, MW (TIP4P)
    - CH4 (5 atoms): C + 4H
    - THF (12 atoms): C4O + 8H
    
    Attributes:
        start_idx: First atom index in positions array (0-based)
        count: Number of atoms in this molecule
        mol_type: Molecule type string ('ice', 'water', 'na', 'cl', 'ch4', 'thf')
    """
    start_idx: int
    count: int
    mol_type: str


# Hydrate lattice types with GenIce2 lattice names
HYDRATE_LATTICES: dict[str, dict[str, Any]] = {
    "sI": {
        "genice_name": "CS1",  # GenIce2 lattice name
        "description": "Structure I hydrate",
        "cages": {
            "small": {"name": "5¹²", "count_per_unit_cell": 2, "guest_fits": ["ch4"]},
            "large": {"name": "5¹²6⁴", "count_per_unit_cell": 6, "guest_fits": ["ch4", "thf"]},
        },
        "unit_cell_molecules": 46,  # Water molecules in unit cell
    },
    "sII": {
        "genice_name": "CS2",
        "description": "Structure II hydrate",
        "cages": {
            "small": {"name": "5¹²", "count_per_unit_cell": 16, "guest_fits": ["ch4"]},
            "large": {"name": "5¹²6⁴", "count_per_unit_cell": 8, "guest_fits": ["ch4", "thf"]},
        },
        "unit_cell_molecules": 136,
    },
    "sH": {
        "genice_name": "CS3",
        "description": "Structure H hydrate",
        "cages": {
            "small": {"name": "5¹²", "count_per_unit_cell": 3, "guest_fits": ["ch4"]},
            "medium": {"name": "4³5⁶6³", "count_per_unit_cell": 2, "guest_fits": ["ch4"]},
            "large": {"name": "5¹²6⁸", "count_per_unit_cell": 1, "guest_fits": ["thf"]},
        },
        "unit_cell_molecules": 34,
    },
}


# Guest molecule types with display info
GUEST_MOLECULES: dict[str, dict[str, Any]] = {
    "ch4": {
        "name": "Methane",
        "formula": "CH₄",
        "atoms": 5,
        "description": "Methane guest molecule",
        "force_field": "GAFF/GAFF2",
    },
    "thf": {
        "name": "Tetrahydrofuran",
        "formula": "C₄H₈O",
        "atoms": 12,
        "description": "THF guest molecule (structure stabilizer)",
        "force_field": "GAFF/GAFF2",
    },
}


@dataclass
class Candidate:
    """A single generated ice structure candidate.

    Attributes:
        positions: (N_atoms, 3) coordinates in nm from GenIce. For triclinic phases (Ice II, Ice V),
            this contains the native triclinic cell positions.
        atom_names: List of atom names ["O", "H", "H", "O", "H", "H", ...]
        cell: (3, 3) cell vectors in nm, stored as ROW vectors.
            Each row is a lattice vector: [[a_x, a_y, a_z],
                                           [b_x, b_y, b_z],
                                           [c_x, c_y, c_z]].
            This means: new_position = position @ cell.
            Note: VTK uses column vectors (matrix @ position), so transpose
            is needed when passing to VTK's SetLattice().
            For triclinic phases, this is the native triclinic cell from GenIce.
        nmolecules: Actual number of water molecules
        phase_id: Phase identifier (e.g., "ice_ih")
        seed: Random seed used for generation
        metadata: Additional info from Phase 2 (density, T, P)
    """

    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    nmolecules: int
    phase_id: str
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of generating multiple candidates.

    Attributes:
        candidates: List of generated Candidate objects
        requested_nmolecules: Number of molecules requested by user
        actual_nmolecules: Actual number generated (may differ due to supercell)
        phase_id: Phase identifier
        phase_name: Human-readable phase name
        density: Density in g/cm³
        was_rounded: True if actual_nmolecules != requested_nmolecules
    """

    candidates: list[Candidate]
    requested_nmolecules: int
    actual_nmolecules: int
    phase_id: str
    phase_name: str
    density: float
    was_rounded: bool


@dataclass
class InterfaceConfig:
    """Configuration for interface generation.

    Captures all generation parameters from the UI.

    Attributes:
        mode: Interface mode ("slab", "pocket", or "piece")
        box_x: Box X dimension in nm
        box_y: Box Y dimension in nm
        box_z: Box Z dimension in nm
        seed: Random seed for reproducibility
        ice_thickness: Ice layer thickness in nm (slab mode)
        water_thickness: Water layer thickness in nm (slab mode)
        pocket_diameter: Cavity diameter in nm (pocket mode)
        pocket_shape: Cavity shape (pocket mode)
        overlap_threshold: O-O distance threshold in nm (default 0.25 nm = 2.5 Å).
            Must be in range [0.1, 1.0] nm to catch unit mismatches.
    """

    mode: str
    box_x: float
    box_y: float
    box_z: float
    seed: int
    ice_thickness: float = 0.0
    water_thickness: float = 0.0
    pocket_diameter: float = 0.0
    pocket_shape: str = "sphere"  # Valid values: "sphere", "cubic"
    overlap_threshold: float = 0.25  # 0.25 nm = 2.5 Å

    def __post_init__(self):
        """Validate configuration parameters after initialization."""
        # Validate overlap_threshold to catch unit mismatches
        if not (0.1 <= self.overlap_threshold <= 1.0):
            raise ValueError(
                f"overlap_threshold={self.overlap_threshold} nm is outside reasonable range [0.1, 1.0] nm. "
                f"This suggests a unit mismatch. "
                f"If you have a value in Angstrom, divide by 10 to get nm "
                f"(e.g., 2.5 Å → 0.25 nm). "
                f"Default: 0.25 nm (2.5 Å) for typical O-O overlap detection."
            )

    @classmethod
    def from_dict(cls, d: dict) -> "InterfaceConfig":
        """Create InterfaceConfig from dictionary.

        Maps the dict from InterfacePanel.get_configuration() to dataclass fields.

        Args:
            d: Dictionary with configuration parameters

        Returns:
            InterfaceConfig instance
        """
        return cls(
            mode=d["mode"],
            box_x=d["box_x"],
            box_y=d["box_y"],
            box_z=d["box_z"],
            seed=d["seed"],
            ice_thickness=d.get("ice_thickness", 0.0),
            water_thickness=d.get("water_thickness", 0.0),
            pocket_diameter=d.get("pocket_diameter", 0.0),
            pocket_shape=d.get("pocket_shape", "sphere"),
            # overlap_threshold not exposed in UI, use default
            overlap_threshold=0.25,
        )


@dataclass
class InterfaceStructure:
    """Result of interface structure generation.

    Stores combined ice + water positions with phase distinction.

    Attributes:
        positions: (N_atoms, 3) combined ice + water atom positions in nm.
            Ice atoms come FIRST, then water atoms.
        atom_names: Atom names for all atoms (ice names then water names)
        cell: (3, 3) box cell vectors in nm, stored as ROW vectors.
            Each row is a lattice vector. See Candidate.cell for details.
        ice_atom_count: Number of ice atoms (marks split between ice and water)
        water_atom_count: Number of water atoms
        ice_nmolecules: Number of ice molecules
        water_nmolecules: Number of water molecules
        mode: Interface mode used
        report: gmx solvate-like generation report string
        molecule_index: List of MoleculeIndex entries tracking each molecule's
            position in the positions array. Populated when multiple molecule
            types are present. For backward compatibility, existing code using
            ice_atom_count still works without using this field.

    Note:
        Ice candidates from GenIce use 3 atoms per molecule (O, H, H).
        Water from tip4p.gro uses 4 atoms per molecule (OW, HW1, HW2, MW).
        The InterfaceStructure stores them combined with ice_atom_count marking
        the boundary. Do NOT normalize atom counts—that is an export concern.
    """

    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    ice_atom_count: int
    water_atom_count: int
    ice_nmolecules: int
    water_nmolecules: int
    mode: str
    report: str
    molecule_index: list = field(default_factory=list)


@dataclass
class HydrateConfig:
    """Configuration for hydrate structure generation.
    
    Captures all parameters for hydrate lattice generation.
    
    Attributes:
        lattice_type: Hydrate lattice type ('sI', 'sII', 'sH')
        guest_type: Guest molecule type ('ch4', 'thf')
        cage_occupancy_small: Occupancy percentage for small cages (0-100)
        cage_occupancy_large: Occupancy percentage for large cages (0-100)
        supercell_x: Supercell repetition in X direction
        supercell_y: Supercell repetition in Y direction
        supercell_z: Supercell repetition in Z direction
    """
    lattice_type: str = "sI"
    guest_type: str = "ch4"
    cage_occupancy_small: float = 100.0
    cage_occupancy_large: float = 100.0
    supercell_x: int = 1
    supercell_y: int = 1
    supercell_z: int = 1
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.lattice_type not in HYDRATE_LATTICES:
            raise ValueError(f"Unknown lattice type: {self.lattice_type}")
        if self.guest_type not in GUEST_MOLECULES:
            raise ValueError(f"Unknown guest type: {self.guest_type}")
        if not (0.0 <= self.cage_occupancy_small <= 100.0):
            raise ValueError(f"cage_occupancy_small must be 0-100, got {self.cage_occupancy_small}")
        if not (0.0 <= self.cage_occupancy_large <= 100.0):
            raise ValueError(f"cage_occupancy_large must be 0-100, got {self.cage_occupancy_large}")
        if self.supercell_x < 1 or self.supercell_y < 1 or self.supercell_z < 1:
            raise ValueError("Supercell dimensions must be >= 1")
    
    @classmethod
    def from_dict(cls, d: dict) -> "HydrateConfig":
        """Create HydrateConfig from dictionary (UI input)."""
        return cls(
            lattice_type=d.get("lattice_type", "sI"),
            guest_type=d.get("guest_type", "ch4"),
            cage_occupancy_small=d.get("cage_occupancy_small", 100.0),
            cage_occupancy_large=d.get("cage_occupancy_large", 100.0),
            supercell_x=d.get("supercell_x", 1),
            supercell_y=d.get("supercell_y", 1),
            supercell_z=d.get("supercell_z", 1),
        )
    
    def get_genice_lattice_name(self) -> str:
        """Get GenIce2 lattice name for this configuration."""
        return HYDRATE_LATTICES[self.lattice_type]["genice_name"]


@dataclass
class IonConfig:
    """Configuration for ion insertion.
    
    Attributes:
        concentration_molar: NaCl concentration in mol/L (M)
    """
    concentration_molar: float = 0.0
    
    def __post_init__(self):
        if self.concentration_molar < 0:
            raise ValueError(f"concentration_molar must be >= 0, got {self.concentration_molar}")


@dataclass
class IonStructure:
    """Result of ion insertion.
    
    Attributes:
        positions: (N_atoms, 3) atom positions in nm (water + ions)
        atom_names: Atom names for all atoms
        cell: (3, 3) box cell vectors in nm
        molecule_index: List of MoleculeIndex for each molecule
        na_count: Number of Na+ ions placed
        cl_count: Number of Cl- ions placed
        report: Generation report string
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]
    na_count: int
    cl_count: int
    report: str


@dataclass
class HydrateLatticeInfo:
    """Display information for a hydrate lattice type.
    
    Used to show lattice info in UI when user selects lattice type.
    
    Attributes:
        lattice_type: Hydrate lattice type ('sI', 'sII', 'sH')
        description: Human-readable description
        cage_types: List of cage type names (e.g., ["5¹²", "5¹²6⁴"])
        cage_counts: Dict mapping cage type to count per unit cell
        unit_cell_molecules: Water molecules in unit cell
        total_cages: Total number of cages per unit cell
    """
    lattice_type: str
    description: str
    cage_types: list[str]
    cage_counts: dict[str, int]
    unit_cell_molecules: int
    total_cages: int
    
    @classmethod
    def from_lattice_type(cls, lattice_type: str) -> "HydrateLatticeInfo":
        """Create HydrateLatticeInfo from lattice type string."""
        if lattice_type not in HYDRATE_LATTICES:
            raise ValueError(f"Unknown lattice type: {lattice_type}")
        
        lattice = HYDRATE_LATTICES[lattice_type]
        cage_types = []
        cage_counts = {}
        total_cages = 0
        
        for cage_size, cage_info in lattice["cages"].items():
            cage_types.append(cage_info["name"])
            cage_counts[cage_info["name"]] = cage_info["count_per_unit_cell"]
            total_cages += cage_info["count_per_unit_cell"]
        
        return cls(
            lattice_type=lattice_type,
            description=lattice["description"],
            cage_types=cage_types,
            cage_counts=cage_counts,
            unit_cell_molecules=lattice["unit_cell_molecules"],
            total_cages=total_cages,
        )


@dataclass
class HydrateStructure:
    """Result of hydrate structure generation.
    
    Stores hydrate structure with water framework and guest molecules.
    
    Attributes:
        positions: (N_atoms, 3) combined water + guest atom positions in nm
        atom_names: Atom names for all atoms
        cell: (3, 3) box cell vectors in nm
        molecule_index: List of MoleculeIndex for each molecule
        config: HydrateConfig used for generation
        lattice_info: HydrateLatticeInfo from generation
        report: Generation report string
        guest_count: Number of guest molecules placed
        water_count: Number of water molecules in framework
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]
    config: HydrateConfig
    lattice_info: HydrateLatticeInfo
    report: str
    guest_count: int
    water_count: int
