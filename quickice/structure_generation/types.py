"""Data types for structure generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np


# Molecule type information: atom count, residue name, typical charge
MOLECULE_TYPE_INFO: dict[str, dict[str, Any]] = {
    "ice":   {"atoms": 4, "res_name": "SOL", "description": "Ice (TIP4P-ICE: OW, HW1, HW2, MW)"},
    "water": {"atoms": 4, "res_name": "SOL", "description": "Water (TIP4P-ICE: OW, HW1, HW2, MW)"},
    "na":    {"atoms": 1, "res_name": "NA",  "description": "Sodium ion"},
    "cl":    {"atoms": 1, "res_name": "CL",  "description": "Chloride ion"},
    "ch4":   {"atoms": 5, "res_name": "CH4", "description": "Methane"},
    "thf":   {"atoms": 13, "res_name": "THF", "description": "Tetrahydrofuran"},
}

# Default atoms per water molecule (TIP4P-ICE: OW, HW1, HW2, MW)
# Used as fallback when molecule count is unavailable
WATER_ATOMS_PER_MOLECULE: int = 4

# Volume per TIP4P-ICE water molecule in nm³ (liquid phase, ~1 bar, 300K)
#
# Derivation: TIP4P-ICE liquid water at ~300K/1bar has density ≈ 0.997 g/cm³.
# V_molecule = M / (ρ × N_A) = 18.015 g/mol / (0.997 g/cm³ × 6.022e23 /mol)
#           = 30.0 Å³ = 0.0300 nm³
# The value 0.0299 nm³ (= 1/33.4 molecules/nm³) is consistent with the
# TIP4P-ICE model's liquid-phase density at ambient conditions.
#
# Reference: Abascal, J. L. F., Sanz, E., García Fernández, R., & Vega, C.
# (2005). A potential model for the phase diagram of TIP4P water.
# J. Chem. Phys. 122, 234511. DOI: 10.1063/1.1931662
#
# For TIP4P-ICE specifically: Abascal, J. L. F., & Vega, C. (2005).
# A general purpose model for the condensed phases of water: TIP4P/2005.
# J. Chem. Phys. 123, 234505. DOI: 10.1063/1.2121600
WATER_VOLUME_NM3: float = 0.0299


def detect_atoms_per_molecule(atom_names: list[str]) -> int:
    """Detect atoms per molecule from atom names pattern.

    Handles:
    - Ice (GenIce): 3 atoms per molecule (O, H, H)
    - TIP4P/hydrate: 4 atoms per molecule (OW, HW1, HW2, MW)

    Args:
        atom_names: List of atom names from candidate

    Returns:
        Atoms per molecule (3 for ice, 4 for TIP4P)
    """
    if len(atom_names) >= 4:
        # Check first atom for TIP4P pattern (OW at index 0)
        if atom_names[0] == "OW":
            return 4
    return 3  # Default to GenIce ice (3 atoms)


@dataclass
class MoleculeIndex:
    """Tracks molecule position in atom array.
    
    Enables handling of variable atoms-per-molecule:
    - ions (1 atom): Na, Cl
    - ice (4 atoms): OW, HW1, HW2, MW (TIP4P-ICE)
    - water (4 atoms): OW, HW1, HW2, MW (TIP4P)
    - CH4 (5 atoms): C + 4H
    - THF (13 atoms): C4H8O (4C + 8H + 1O)
    
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
            "large": {"name": "5¹²6²", "count_per_unit_cell": 6, "guest_fits": ["ch4", "thf"]},
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
        "genice_name": "sH",
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
        "atoms": 13,
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
        positions: (N_atoms, 3) combined ice + water + guest atom positions in nm.
            Ice atoms come FIRST, then water, then guest atoms LAST.
        atom_names: Atom names for all atoms (ice names, then water names, then guest names)
        cell: (3, 3) box cell vectors in nm, stored as ROW vectors.
            Each row is a lattice vector. See Candidate.cell for details.
        ice_atom_count: Number of ice atoms (marks split between ice and water)
        water_atom_count: Number of water atoms
        ice_nmolecules: Number of ice molecules
        water_nmolecules: Number of water molecules
        mode: Interface mode used
        report: gmx solvate-like generation report string
        guest_atom_count: Number of guest atoms (0 if no guests, marks split between water and guests)
        molecule_index: List of MoleculeIndex entries tracking each molecule's
            position in the positions array. Populated when multiple molecule
            types are present. For backward compatibility, existing code using
            ice_atom_count still works without using this field.
        guest_nmolecules: Number of guest molecules (0 if no guests)
        solute_type: Solute type ("CH4" or "THF") if solutes were inserted
        solute_positions: (N_solute_atoms, 3) solute atom positions in nm
        solute_atom_names: Solute atom names
        solute_n_molecules: Number of solute molecules
        solute_molecule_indices: List of (start, end) tuples for each solute molecule
        solute_registry: MoleculetypeRegistry with solute moleculetype registered
        custom_molecule_count: Number of custom molecules placed
        custom_molecule_atom_count: Number of custom molecule atoms
        custom_molecule_positions: (N_custom_atoms, 3) custom molecule positions in nm
        custom_molecule_atom_names: Custom molecule atom names
        custom_molecule_moleculetype: GROMACS moleculetype name for custom molecules
        custom_gro_path: Path to custom molecule .gro file
        custom_itp_path: Path to custom molecule .itp file

    Note:
        Ice candidates from GenIce use 3 atoms per molecule (O, H, H).
        Hydrate ice uses 4 atoms per molecule (OW, HW1, HW2, MW).
        Water from tip4p.gro uses 4 atoms per molecule (OW, HW1, HW2, MW).
        Guest molecules vary (CH4: 5 atoms, THF: 13 atoms).
        The InterfaceStructure stores them combined with ice_atom_count,
        water_atom_count, and guest_atom_count marking the boundaries.
        Do NOT normalize atom counts.
        
    Ordering (after commit 90afe86):
        positions[0:ice_atom_count] = ice atoms
        positions[ice_atom_count:ice_atom_count+water_atom_count] = water atoms
        positions[ice_atom_count+water_atom_count:] = guest atoms
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
    guest_atom_count: int = 0
    molecule_index: list = field(default_factory=list)
    guest_nmolecules: int = 0
    # Solute attributes (populated when solute insertion targets this interface)
    solute_type: str = ""
    solute_positions: np.ndarray | None = None
    solute_atom_names: list[str] | None = None
    solute_n_molecules: int = 0
    solute_molecule_indices: list[tuple[int, int]] | None = None
    solute_registry: Any = None  # MoleculetypeRegistry (avoid circular import)
    # Custom molecule attributes (populated when custom molecule insertion targets this interface)
    custom_molecule_count: int = 0
    custom_molecule_atom_count: int = 0
    custom_molecule_positions: np.ndarray | None = None
    custom_molecule_atom_names: list[str] | None = None
    custom_molecule_moleculetype: str = ""
    custom_gro_path: Any = None  # Path (avoid circular import)
    custom_itp_path: Any = None  # Path (avoid circular import)


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
        guest_nmolecules: Number of guest molecules (from input interface)
        guest_atom_count: Number of guest atoms (from input interface)
        solute_type: Solute type ("CH4" or "THF") if solutes were present in source
        solute_positions: (N_solute_atoms, 3) solute atom positions in nm
        solute_atom_names: Solute atom names
        solute_n_molecules: Number of solute molecules
        solute_molecule_indices: List of (start, end) tuples for each solute molecule
        solute_registry: MoleculetypeRegistry with solute moleculetype registered
        custom_molecule_count: Number of custom molecules (from input interface)
        custom_molecule_atom_count: Number of custom molecule atoms
        custom_molecule_positions: (N_custom_atoms, 3) custom molecule atom positions in nm
        custom_molecule_atom_names: Custom molecule atom names
        custom_molecule_moleculetype: GROMACS moleculetype name for custom molecules
        custom_gro_path: Path to custom molecule .gro file
        custom_itp_path: Path to custom molecule .itp file
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]
    na_count: int
    cl_count: int
    report: str
    guest_nmolecules: int = 0
    guest_atom_count: int = 0
    # Solute attributes (populated when source was SoluteStructure)
    solute_type: str = ""
    solute_positions: np.ndarray | None = None
    solute_atom_names: list[str] | None = None
    solute_n_molecules: int = 0
    solute_molecule_indices: list[tuple[int, int]] | None = None
    solute_registry: Any = None  # MoleculetypeRegistry (avoid circular import)
    # Custom molecule attributes (populated when source had custom molecules)
    custom_molecule_count: int = 0
    custom_molecule_atom_count: int = 0
    custom_molecule_positions: np.ndarray | None = None
    custom_molecule_atom_names: list[str] | None = None
    custom_molecule_moleculetype: str = ""
    custom_gro_path: Any = None  # Path (avoid circular import)
    custom_itp_path: Any = None  # Path (avoid circular import)


@dataclass
class SoluteConfig:
    """Configuration for solute insertion.
    
    Attributes:
        concentration_molar: Solute concentration in mol/L (M)
        solute_type: Solute type ("CH4" or "THF")
        max_attempts: Maximum placement attempts per molecule
        min_separation: Minimum separation distance in nm
        seed: Random seed for reproducibility (optional)
    """
    concentration_molar: float = 0.1
    solute_type: str = "CH4"
    max_attempts: int = 1000
    min_separation: float = 0.3
    seed: int | None = None
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.concentration_molar < 0:
            raise ValueError(f"concentration_molar must be >= 0, got {self.concentration_molar}")
        if self.solute_type not in ("CH4", "THF"):
            raise ValueError(f"solute_type must be 'CH4' or 'THF', got {self.solute_type}")
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.min_separation <= 0:
            raise ValueError(f"min_separation must be > 0, got {self.min_separation}")


@dataclass
class SoluteStructure:
    """Result of solute insertion.
    
    Attributes:
        positions: (N_atoms, 3) solute atom positions in nm
        atom_names: Solute atom names
        cell: (3, 3) box cell vectors in nm (from interface structure)
        solute_type: Solute type ("CH4" or "THF")
        n_molecules: Number of molecules placed
        molecule_indices: List of (start, end) tuples for each molecule in positions array
        registry: MoleculetypeRegistry with CH4_L/THF_L registered
        interface_structure: Original InterfaceStructure (ice + water) that solutes were inserted into
        ice_nmolecules: Number of ice molecules (from source interface structure)
        water_nmolecules: Number of water molecules (from source interface structure, after overlap removal)
        custom_molecule_count: Number of custom molecules (from input interface)
        custom_molecule_atom_count: Number of custom molecule atoms
        custom_molecule_positions: (N_custom_atoms, 3) custom molecule atom positions in nm
        custom_molecule_atom_names: Custom molecule atom names
        custom_molecule_moleculetype: GROMACS moleculetype name for custom molecules
        custom_gro_path: Path to custom molecule .gro file
        custom_itp_path: Path to custom molecule .itp file
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    solute_type: str
    n_molecules: int
    molecule_indices: list[tuple[int, int]]
    registry: Any  # MoleculetypeRegistry (avoid circular import)
    interface_structure: Any = None  # InterfaceStructure (avoid circular import)
    # Ice/water molecule counts (from source interface structure)
    ice_nmolecules: int = 0
    water_nmolecules: int = 0
    # Custom molecule attributes (populated when source had custom molecules)
    custom_molecule_count: int = 0
    custom_molecule_atom_count: int = 0
    custom_molecule_positions: np.ndarray | None = None
    custom_molecule_atom_names: list[str] | None = None
    custom_molecule_moleculetype: str = ""
    custom_gro_path: Any = None  # Path (avoid circular import)
    custom_itp_path: Any = None  # Path (avoid circular import)


@dataclass
class CustomMoleculeConfig:
    """Configuration for custom molecule placement.
    
    Attributes:
        placement_mode: "random" or "custom"
        gro_path: Path to custom molecule .gro file
        itp_path: Path to custom molecule .itp file
        molecule_count: Number of molecules to place (for random mode)
        positions: List of (x, y, z) center-of-mass positions in nm (for custom mode)
        rotations: List of (alpha, beta, gamma) Euler angles in degrees (for custom mode)
        min_separation: Minimum separation distance in nm (for random mode)
        max_attempts: Maximum placement attempts per molecule (for random mode)
    """
    placement_mode: str
    gro_path: Path
    itp_path: Path
    molecule_count: int | None = None
    positions: list[tuple[float, float, float]] | None = None
    rotations: list[tuple[float, float, float]] | None = None
    min_separation: float = 0.3
    max_attempts: int = 1000
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.placement_mode not in ("random", "custom"):
            raise ValueError(
                f"placement_mode must be 'random' or 'custom', got {self.placement_mode}"
            )
        
        if self.placement_mode == "random":
            if self.molecule_count is None:
                raise ValueError("molecule_count must be set for random mode")
            if self.molecule_count < 1:
                raise ValueError(f"molecule_count must be >= 1, got {self.molecule_count}")
            if self.positions is not None or self.rotations is not None:
                raise ValueError("positions/rotations should not be set for random mode")
        else:  # custom mode
            if self.positions is None or self.rotations is None:
                raise ValueError("positions and rotations must be set for custom mode")
            if len(self.positions) != len(self.rotations):
                raise ValueError(
                    f"positions and rotations must have same length, "
                    f"got {len(self.positions)} vs {len(self.rotations)}"
                )
            if self.molecule_count is not None:
                raise ValueError("molecule_count should not be set for custom mode")
        
        if not (0.1 <= self.min_separation <= 1.0):
            raise ValueError(
                f"min_separation={self.min_separation} nm outside reasonable range [0.1, 1.0] nm"
            )
        
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")


@dataclass
class CustomMoleculeStructure:
    """Result of custom molecule insertion into interface structure.
    
    Contains COMPLETE system: ice + water + custom molecules.
    Follows IonStructure pattern for consistency with downstream workflows.
    
    Attributes:
        positions: (N_atoms, 3) ALL atom positions in nm (ice + water + custom)
        atom_names: ALL atom names (ice + water + custom atoms)
        cell: (3, 3) box cell vectors in nm
        molecule_index: List of MoleculeIndex for ALL molecules (ice, water, custom)
        ice_atom_count: Number of ice atoms from source interface
        water_atom_count: Number of water atoms from source interface
        custom_molecule_atom_count: Number of custom molecule atoms
        guest_atom_count: Number of guest atoms (0 for pure interface)
        guest_nmolecules: Number of guest molecules (0 for pure interface)
        ice_nmolecules: Number of ice molecules (from source interface structure)
        water_nmolecules: Number of water molecules (from source interface structure, after overlap removal)
        config: Original CustomMoleculeConfig
        moleculetype_name: GROMACS moleculetype name (e.g., "CUSTOM_MOL_1")
        gro_path: Original .gro file path
        itp_path: Original .itp file path
        residue_name: Final residue name (from ITP if override accepted, else from GRO)
        custom_molecule_count: Number of molecules placed
        interface_structure: Original InterfaceStructure (ice + water) for downstream use
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    molecule_index: list[MoleculeIndex]  # Changed from list[tuple[int, int]]
    ice_atom_count: int
    water_atom_count: int
    custom_molecule_atom_count: int
    guest_atom_count: int = 0
    guest_nmolecules: int = 0
    ice_nmolecules: int = 0
    water_nmolecules: int = 0
    config: CustomMoleculeConfig | None = None
    moleculetype_name: str = ""
    gro_path: Path | None = None
    itp_path: Path | None = None
    residue_name: str = ""
    custom_molecule_count: int = 0
    interface_structure: Any = None  # InterfaceStructure (avoid circular import)


@dataclass
class PlacementValidationResult:
    """Result of single-molecule placement validation.
    
    Attributes:
        is_valid: True if placement is valid (within bounds + no overlap)
        within_bounds: True if position is in liquid region
        has_overlap: True if molecule overlaps with existing atoms
        min_distance: Minimum distance to nearest existing atom (nm)
        nearest_atom_type: Element of nearest atom (for user feedback), or None
        error_message: Human-readable error or None if valid
    """
    is_valid: bool
    within_bounds: bool
    has_overlap: bool
    min_distance: float
    nearest_atom_type: str | None
    error_message: str | None


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

    def to_candidate(self) -> Candidate:
        """Convert hydrate structure to ice Candidate for interface generation.

        Preserves BOTH water framework and guest molecules from the hydrate.
        The hydrate lattice becomes the candidate structure that will be used
        to create the ice/water interface, preserving all guest molecules.

        Returns:
            Candidate with hydrate water framework AND guest molecule positions,
            using hydrate's lattice type as phase_id. Total molecules = water_count + guest_count.
        """
        # Extract all molecule positions (water framework + guest molecules)
        # molecule_index contains (start_idx, count, mol_type) for each molecule
        all_positions = []
        all_atom_names = []
        guest_types = []  # Track guest types for metadata

        for idx in self.molecule_index:
            start_idx = idx.start_idx
            count = idx.count
            mol_type = idx.mol_type
            # Include ALL molecules: water framework AND guest molecules
            all_positions.append(self.positions[start_idx:start_idx + count])
            all_atom_names.extend(self.atom_names[start_idx:start_idx + count])
            # Track guest types (not water)
            if mol_type != "water":
                guest_types.append(mol_type)

        if not all_positions:
            raise ValueError(
                "Cannot convert empty hydrate structure to candidate. "
                "Hydrate has no molecules."
            )

        # Concatenate all positions (water + guests together)
        all_positions = np.vstack(all_positions)

        # Count unique guest types for metadata
        guest_type_counts = {}
        for gtype in guest_types:
            guest_type_counts[gtype] = guest_type_counts.get(gtype, 0) + 1

        # Use lattice info to create a descriptive phase_id
        lattice_id = self.config.lattice_type
        phase_id = f"hydrate_{lattice_id}"

        # Calculate total molecules (water + guests)
        total_molecules = self.water_count + self.guest_count

        return Candidate(
            positions=np.array(all_positions),
            atom_names=list(all_atom_names),
            cell=self.cell.copy(),
            nmolecules=total_molecules,
            phase_id=phase_id,
            seed=self.config.supercell_x * 100 + self.config.supercell_y * 10 + self.config.supercell_z,
            metadata={
                "lattice_type": lattice_id,
                "lattice_description": self.lattice_info.description,
                "water_count": self.water_count,
                "guest_count": self.guest_count,
                "guest_type_counts": guest_type_counts,
                "original_hydrate": True,
            }
        )
