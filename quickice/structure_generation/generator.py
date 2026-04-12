"""GenIce-based ice structure generator.

This module provides the IceStructureGenerator class that wraps GenIce's API
to generate physically valid ice structures with diverse hydrogen bond networks.
"""

import time

import numpy as np

from genice2.plugin import safe_import
from genice2.genice import GenIce

from quickice.structure_generation.mapper import (
    get_genice_lattice_name,
    calculate_supercell,
    UNIT_CELL_MOLECULES,
)
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.errors import StructureGenerationError
from quickice.structure_generation.transformer import TriclinicTransformer


class IceStructureGenerator:
    """Generator for ice structure candidates using GenIce.

    This class wraps GenIce's API to generate multiple ice structure candidates
    with different hydrogen bond network configurations (controlled by random seed).

    Attributes:
        phase_id: Phase identifier (e.g., "ice_ih")
        phase_name: Human-readable phase name
        density: Density in g/cm³ from Phase 2 lookup
        nmolecules: Target number of water molecules
        lattice_name: GenIce lattice name
        molecules_per_unit_cell: Molecules in one unit cell
        supercell_matrix: 3x3 supercell matrix
        actual_nmolecules: Actual number of molecules (after supercell rounding)
    """

    def __init__(self, phase_info: dict, nmolecules: int):
        """Initialize the generator with phase info and target molecule count.

        Args:
            phase_info: Dict from lookup_phase() containing:
                - phase_id: Phase identifier
                - phase_name: Human-readable name
                - density: Density in g/cm³
            nmolecules: Target number of water molecules

        Raises:
            UnsupportedPhaseError: If phase is not supported by GenIce
            StructureGenerationError: If initialization fails
        """
        # Extract phase information
        self.phase_id = phase_info["phase_id"]
        self.phase_name = phase_info["phase_name"]
        self.density = phase_info["density"]
        self.nmolecules = nmolecules

        # Get GenIce lattice name
        self.lattice_name = get_genice_lattice_name(self.phase_id)

        # Get molecules per unit cell
        self.molecules_per_unit_cell = UNIT_CELL_MOLECULES[self.lattice_name]

        # Calculate supercell size
        self.supercell_matrix, self.actual_nmolecules = calculate_supercell(
            nmolecules, self.molecules_per_unit_cell
        )

    def _generate_single(self, seed: int) -> Candidate:
        """Generate a single ice structure candidate.

        Args:
            seed: Random seed for hydrogen bond network diversity

        Returns:
            Candidate with generated coordinates and metadata

        Raises:
            StructureGenerationError: If GenIce fails to generate

        Note:
            GenIce internally uses the global np.random state (not the newer
            Generator API). We save and restore the global state around each
            generation call to minimize side effects on external code.

            Thread Safety: This method is NOT thread-safe. Concurrent calls
            from multiple threads would corrupt each other's random state.
            QuickIce is designed for sequential execution and does not support
            concurrent generation.
        """
        try:
            # Save global random state to minimize pollution
            # GenIce uses np.random internally (see genice2/genice.py lines 58, 816, 1072)
            original_state = np.random.get_state()
            np.random.seed(seed)

            # Load lattice
            lattice = safe_import("lattice", self.lattice_name).Lattice()

            # Create GenIce instance with density and supercell
            ice = GenIce(
                lattice, density=self.density, reshape=self.supercell_matrix
            )

            # Load TIP3P water model (3-point: O, H, H)
            # TIP4P produces 4 atoms (OW, HW1, HW2, MW) but our interface modes
            # expect 3 atoms per molecule (O, H, H). Ice is generated with 3-atom
            # TIP3P format and normalized to 4-atom TIP4P-ICE at export time.
            water = safe_import("molecule", "tip3p").Molecule()

            # Load GROMACS formatter
            formatter = safe_import("format", "gromacs").Format()

            # Generate ice structure with strict depolarization
            gro_string = ice.generate_ice(
                formatter=formatter, water=water, depol="strict"
            )

            # Restore global random state to minimize pollution
            np.random.set_state(original_state)

            # Parse GRO output
            positions, atom_names, cell = self._parse_gro(gro_string)

            # Transform triclinic cells to orthogonal (Phase 24)
            # Ice II and Ice V have non-orthogonal cells that need transformation
            transformer = TriclinicTransformer()
            result = transformer.transform_if_needed(
                Candidate(
                    positions=positions,
                    atom_names=atom_names,
                    cell=cell,
                    nmolecules=self.actual_nmolecules,
                    phase_id=self.phase_id,
                    seed=seed,
                )
            )

            # Update positions and cell from transformation
            positions = result.positions
            cell = result.cell

            # Track actual molecules after transformation (may increase due to supercell)
            actual_nmolecules = int(len(positions) / 3)  # 3 atoms per molecule from GenIce

            # Replicate atom_names if transformation increased the number of atoms
            # The supercell transformation replicates the unit cell, so atom_names
            # must also be replicated to match the new positions count
            if result.multiplier > 1:
                atom_names = atom_names * result.multiplier

            # Create candidate with transformation metadata
            candidate = Candidate(
                positions=positions,
                atom_names=atom_names,
                cell=cell,
                nmolecules=actual_nmolecules,
                phase_id=self.phase_id,
                seed=seed,
                metadata={
                    "density": self.density,
                    "phase_name": self.phase_name,
                    "transformation_status": result.status.name,
                    "transformation_multiplier": result.multiplier,
                    "transformation_message": result.message,
                },
            )

            return candidate

        except Exception as e:
            # Wrap any GenIce or internal errors with full context
            raise StructureGenerationError(
                f"Failed to generate ice structure ({type(e).__name__}): {e}"
            ) from e

    def _parse_gro(self, gro_string: str) -> tuple[np.ndarray, list[str], np.ndarray]:
        """Parse GRO format string to extract coordinates.

        GRO format:
            Line 0: Title
            Line 1: Number of atoms
            Lines 2 to N+1: Atom records (residue, atom_name, atom_num, x, y, z)
            Last line: Box dimensions

        Args:
            gro_string: GRO format string from GenIce

        Returns:
            Tuple of (positions, atom_names, cell)
            - positions: (N_atoms, 3) array in nm
            - atom_names: List of atom names ["O", "H", "H", ...]
            - cell: (3, 3) cell vectors in nm
        """
        lines = gro_string.strip().split("\n")

        # Parse number of atoms
        n_atoms = int(lines[1])

        # Parse atom positions and names
        positions = np.zeros((n_atoms, 3), dtype=float)
        atom_names = []

        for i in range(n_atoms):
            # GRO format: fixed-width columns
            # Columns 11-15: atom name
            # Columns 21-28, 29-36, 37-44: x, y, z in nm
            line = lines[2 + i]
            atom_name = line[10:15].strip()
            atom_names.append(atom_name)

            # Parse coordinates (columns are 1-indexed in spec, 0-indexed here)
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
            positions[i] = [x, y, z]

        # Parse cell dimensions (last line)
        # For orthogonal boxes: "v1 v2 v3"
        # For non-orthogonal: "v1x v2y v3z v1y v1z v2x v2z v3x v3y"
        cell_line = lines[-1].split()
        if len(cell_line) == 3:
            # Orthogonal box
            cell = np.diag([float(v) for v in cell_line])
        else:
            # Non-orthogonal box (triclinic)
            # GRO format for triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
            v1x, v2y, v3z = float(cell_line[0]), float(cell_line[1]), float(cell_line[2])
            v1y, v1z, v2x, v2z, v3x, v3y = [float(v) for v in cell_line[3:9]]
            cell = np.array([
                [v1x, v1y, v1z],
                [v2x, v2y, v2z],
                [v3x, v3y, v3z]
            ])

        return positions, atom_names, cell

    def generate_all(self, n_candidates: int = 10, base_seed: int | None = None) -> list[Candidate]:
        """Generate multiple ice structure candidates with diverse seeds.

        Args:
            n_candidates: Number of candidates to generate (default 10)
            base_seed: Base seed for random number generation. If None, uses
                current time to ensure different candidates across batches.
                Specify a seed for reproducibility.

        Returns:
            List of Candidate objects with sequential seeds starting from base_seed

        Raises:
            StructureGenerationError: If generation fails

        Note:
            If base_seed is None (default), each batch uses a different starting
            seed based on the current time, ensuring diversity across calls.
            For reproducibility, specify a base_seed value.
        """
        candidates = []
        if base_seed is None:
            # Use nanosecond time for maximum resolution diversity across batches
            # Modulo keeps seed in reasonable range for random number generators
            base_seed = time.time_ns() % 1000000000

        for i in range(n_candidates):
            seed = base_seed + i
            candidate = self._generate_single(seed)
            candidates.append(candidate)

        return candidates


def generate_candidates(
    phase_info: dict,
    nmolecules: int,
    n_candidates: int = 10,
    base_seed: int | None = None,
) -> GenerationResult:
    """Generate multiple ice structure candidates.

    This is a convenience function that creates a generator instance
    and returns results in a single call.

    Args:
        phase_info: Dict from lookup_phase() containing phase_id, density, etc.
        nmolecules: Target number of water molecules
        n_candidates: Number of candidates to generate (default 10)
        base_seed: Base seed for random number generation. If None, uses
            current time for automatic diversity. Specify a seed for reproducibility.

    Returns:
        GenerationResult with list of candidates and metadata

    Raises:
        UnsupportedPhaseError: If phase not supported by GenIce
        StructureGenerationError: If GenIce fails to generate

    Example:
        >>> from quickice.phase_mapping import lookup_phase
        >>> from quickice.structure_generation import generate_candidates
        >>> phase_info = lookup_phase(273, 0)  # Ice Ih
        >>> result = generate_candidates(phase_info, nmolecules=100)
        >>> len(result.candidates)
        10

        For reproducibility:
        >>> result = generate_candidates(phase_info, nmolecules=100, base_seed=42)
        >>> # Second call with same seed produces identical candidates
        >>> result2 = generate_candidates(phase_info, nmolecules=100, base_seed=42)
        >>> # result and result2 have identical structures
    """
    # Create generator
    generator = IceStructureGenerator(phase_info, nmolecules)

    # Generate candidates
    candidates = generator.generate_all(n_candidates, base_seed)

    # Create result
    result = GenerationResult(
        candidates=candidates,
        requested_nmolecules=nmolecules,
        actual_nmolecules=generator.actual_nmolecules,
        phase_id=generator.phase_id,
        phase_name=generator.phase_name,
        density=generator.density,
        was_rounded=(nmolecules != generator.actual_nmolecules),
    )

    return result
