"""Data types for structure generation."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Candidate:
    """A single generated ice structure candidate.

    Attributes:
        positions: (N_atoms, 3) coordinates in nm
        atom_names: List of atom names ["O", "H", "H", "O", "H", "H", ...]
        cell: (3, 3) cell vectors in nm, stored as ROW vectors.
            Each row is a lattice vector: [[a_x, a_y, a_z],
                                           [b_x, b_y, b_z],
                                           [c_x, c_y, c_z]].
            This means: new_position = position @ cell.
            Note: VTK uses column vectors (matrix @ position), so transpose
            is needed when passing to VTK's SetLattice().
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
    pocket_shape: str = "sphere"
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
