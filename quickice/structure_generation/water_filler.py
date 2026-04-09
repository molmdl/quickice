"""Water template loading and structure tiling for interface generation.

This module provides utilities to load the bundled TIP4P water template
(tip4p.gro), tile structures to fill target regions using cell periodicity,
and fill arbitrary rectangular regions with water molecules.
"""

import math
from pathlib import Path
from typing import Optional

import numpy as np

# Number of atoms per TIP4P water molecule (OW, HW1, HW2, MW)
ATOMS_PER_WATER_MOLECULE = 4

# Module-level cache for water template (never changes)
_water_template_cache: Optional[tuple[np.ndarray, list[str], np.ndarray]] = None


def load_water_template() -> tuple[np.ndarray, list[str], np.ndarray]:
    """Load the bundled TIP4P water template from tip4p.gro.

    Reads and parses the GRO file following the same format as
    IceStructureGenerator._parse_gro(). Results are cached at module
    level since the template never changes.

    Returns:
        Tuple of (positions, atom_names, box_dims):
            - positions: (864, 3) atom positions in nm
            - atom_names: 864 entries ["OW", "HW1", "HW2", "MW", ...]
            - box_dims: [1.86824, 1.86824, 1.86824] box dimensions in nm
    """
    global _water_template_cache

    if _water_template_cache is not None:
        return _water_template_cache

    # Locate the bundled tip4p.gro file
    gro_path = Path(__file__).parent.parent / "data" / "tip4p.gro"

    with open(gro_path, "r") as f:
        gro_string = f.read()

    # Parse GRO format (same logic as IceStructureGenerator._parse_gro)
    lines = gro_string.strip().split("\n")

    # Parse number of atoms
    n_atoms = int(lines[1])

    # Parse atom positions and names
    positions = np.zeros((n_atoms, 3), dtype=float)
    atom_names = []

    for i in range(n_atoms):
        line = lines[2 + i]
        atom_name = line[10:15].strip()
        atom_names.append(atom_name)

        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        positions[i] = [x, y, z]

    # Parse cell dimensions (last line)
    cell_line = lines[-1].split()
    if len(cell_line) == 3:
        # Orthogonal box
        box_dims = np.array([float(v) for v in cell_line])
    else:
        # Non-orthogonal box - extract diagonal for v3.0
        box_dims = np.array([float(cell_line[0]), float(cell_line[1]), float(cell_line[2])])

    # Cache the result
    _water_template_cache = (positions, atom_names, box_dims)

    return positions, atom_names, box_dims


def tile_structure(
    positions: np.ndarray,
    cell_dims: np.ndarray,
    target_region: np.ndarray,
    atoms_per_molecule: Optional[int] = None,
) -> tuple[np.ndarray, int]:
    """Tile a structure to fill a target rectangular region using cell periodicity.

    Replicates the input structure by shifting copies along each axis to
    cover the target region. Atoms that fall outside the target region are
    filtered out. Positions are wrapped into the target region using modulo.

    Works for ice (3 atoms/molecule from GenIce) or water (4 atoms/molecule
    from tip4p.gro). The caller is responsible for replicating atom_names.

    Args:
        positions: (N, 3) atom positions in nm.
        cell_dims: [a, b, c] cell dimensions in nm (orthogonal box diagonal).
            We only support orthogonal boxes for v3.0.
        target_region: [lx, ly, lz] target region dimensions in nm.
        atoms_per_molecule: Number of atoms per molecule (optional).
            - For TIP4P water: 4 (OW, HW1, HW2, MW)
            - For GenIce ice: 3 (O, H, H)
            If None, will attempt to infer from total atom count (deprecated,
            may produce incorrect results for ambiguous cases).

    Returns:
        Tuple of (tiled_positions, n_molecules):
            - tiled_positions: (M, 3) positions of atoms within target region
            - n_molecules: number of molecules in the tiled result

    Raises:
        ValueError: If atoms_per_molecule cannot be determined and heuristic fails.
    """
    if len(positions) == 0:
        return np.zeros((0, 3), dtype=float), 0

    lx, ly, lz = target_region
    a, b, c = cell_dims

    # Calculate tiling counts (ceil to ensure full coverage)
    nx = math.ceil(lx / a) if a > 0 else 1
    ny = math.ceil(ly / b) if b > 0 else 1
    nz = math.ceil(lz / c) if c > 0 else 1

    # Determine atoms_per_molecule
    # This must be done BEFORE tiling to correctly filter molecules
    n_original_atoms = len(positions)

    if atoms_per_molecule is None:
        # Heuristic inference (deprecated - may produce incorrect results)
        import warnings

        if n_original_atoms % 3 == 0 and n_original_atoms % 4 != 0:
            atoms_per_molecule = 3
            warnings.warn(
                f"Inferred atoms_per_molecule=3 from {n_original_atoms} atoms. "
                "Pass atoms_per_molecule explicitly to avoid ambiguity.",
                DeprecationWarning,
                stacklevel=2
            )
        elif n_original_atoms % 4 == 0 and n_original_atoms % 3 != 0:
            atoms_per_molecule = 4
            warnings.warn(
                f"Inferred atoms_per_molecule=4 from {n_original_atoms} atoms. "
                "Pass atoms_per_molecule explicitly to avoid ambiguity.",
                DeprecationWarning,
                stacklevel=2
            )
        elif n_original_atoms % 4 == 0 and n_original_atoms % 3 == 0:
            # Ambiguous case - cannot determine safely
            raise ValueError(
                f"Cannot determine atoms_per_molecule: {n_original_atoms} atoms is "
                f"divisible by both 3 and 4. Pass atoms_per_molecule explicitly "
                f"(3 for ice, 4 for TIP4P water)."
            )
        else:
            # Cannot determine - refuse to guess
            raise ValueError(
                f"Cannot determine atoms_per_molecule: {n_original_atoms} atoms is "
                f"not divisible by 3 or 4. Pass atoms_per_molecule explicitly."
            )
    else:
        # Validate that atoms_per_molecule divides evenly
        if n_original_atoms % atoms_per_molecule != 0:
            raise ValueError(
                f"Invalid atoms_per_molecule={atoms_per_molecule}: "
                f"{n_original_atoms} atoms is not evenly divisible by {atoms_per_molecule}."
            )

    n_original_molecules = n_original_atoms // atoms_per_molecule

    # Vectorized tiling: generate all offsets at once and use broadcasting
    # Create grid of indices for all tile positions
    ix_vals = np.arange(nx)
    iy_vals = np.arange(ny)
    iz_vals = np.arange(nz)
    
    # Generate all (ix, iy, iz) combinations using meshgrid
    ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')
    
    # Compute all offsets at once: shape (nx*ny*nz, 3)
    offsets = np.stack([
        ix_grid.ravel() * a,
        iy_grid.ravel() * b,
        iz_grid.ravel() * c
    ], axis=1)
    
    # Broadcast positions with all offsets
    # positions: (N, 3) -> (1, N, 3)
    # offsets: (M, 3) -> (M, 1, 3)
    # Result: (M, N, 3) -> reshape to (M*N, 3)
    n_tiles = nx * ny * nz
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)

    # CRITICAL: Filter at MOLECULE boundaries, not individual atoms
    # This prevents incomplete molecules that cause index overflow bugs
    tol = 1e-10

    # Count total molecules in tiled structure
    n_tiled_molecules = len(all_positions) // atoms_per_molecule

    # Check each molecule: keep only if ALL its atoms are inside target region
    keep_molecules = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = all_positions[start_atom:end_atom]

        # Check if ALL atoms of this molecule are inside target region
        all_inside_x = np.all(mol_atoms[:, 0] < lx - tol)
        all_inside_y = np.all(mol_atoms[:, 1] < ly - tol)
        all_inside_z = np.all(mol_atoms[:, 2] < lz - tol)

        if all_inside_x and all_inside_y and all_inside_z:
            keep_molecules.append(mol_idx)

    if not keep_molecules:
        return np.zeros((0, 3), dtype=float), 0

    # Build keep mask for atoms of complete molecules
    keep_mask = np.zeros(len(all_positions), dtype=bool)
    for mol_idx in keep_molecules:
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        keep_mask[start_atom:end_atom] = True

    filtered = all_positions[keep_mask]

    # Wrap positions into target region using modulo
    # This handles edge cases where atoms fall exactly on box boundary
    tiled_positions = filtered % target_region

    # Molecule count is exact (no truncation needed)
    n_molecules = len(keep_molecules)

    return tiled_positions, n_molecules


def fill_region_with_water(
    region_dims: np.ndarray,
    overlap_threshold_nm: float = 0.25,
) -> tuple[np.ndarray, list[str], int]:
    """Fill a rectangular region with TIP4P water molecules.

    Convenience function that loads the water template, tiles it into
    the specified region, and returns positions, atom names, and
    molecule count.

    Args:
        region_dims: [lx, ly, lz] region dimensions in nm.
        overlap_threshold_nm: O-O overlap threshold in nm (default 0.25 nm = 2.5 Å).
            Used for informational purposes; actual overlap removal is done
            by the caller using overlap_resolver functions.

    Returns:
        Tuple of (positions, atom_names, nmolecules):
            - positions: (N, 3) water atom positions in nm
            - atom_names: list of atom names ["OW", "HW1", "HW2", "MW", ...]
            - nmolecules: number of water molecules in the region
    """
    # Load water template
    template_positions, template_atom_names, template_box = load_water_template()

    # Tile water into the target region
    tiled_positions, n_molecules = tile_structure(
        template_positions, template_box, region_dims,
        atoms_per_molecule=ATOMS_PER_WATER_MOLECULE
    )

    if n_molecules == 0:
        return tiled_positions, [], 0

    # Replicate atom names for each tile copy
    # The tile_structure function filters atoms, so we need to know
    # how many complete molecules we have
    n_atoms = n_molecules * ATOMS_PER_WATER_MOLECULE

    # Trim positions to exact molecule boundaries (in case of rounding)
    tiled_positions = tiled_positions[:n_atoms]

    # Replicate atom names: one template's worth per molecule
    all_atom_names = template_atom_names * n_molecules

    return tiled_positions, all_atom_names, n_molecules
