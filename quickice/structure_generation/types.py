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
        cell: (3, 3) cell vectors in nm
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
