"""Water template loading and structure tiling for interface generation.

This module provides utilities to load the bundled TIP4P water template
(tip4p.gro), tile structures to fill target regions using cell periodicity,
and fill arbitrary rectangular regions with water molecules.

Supports density scaling for water molecules to match target density
from IAPWS calculations.
"""

import math
from pathlib import Path
from typing import Optional

import numpy as np


# === Triclinic Cell Utilities ===

def get_cell_extent(cell: np.ndarray) -> np.ndarray:
    """Calculate the bounding box extent of a unit cell.
    
    For orthogonal cells, this equals [cell[0,0], cell[1,1], cell[2,2]].
    For triclinic cells, this computes the actual bounding box by checking
    all 8 corners of the parallelepiped.
    
    Args:
        cell: (3, 3) cell vectors as ROW vectors [a, b, c]
    
    Returns:
        (3,) array of [dx, dy, dz] bounding box dimensions
    """
    a, b, c = cell[0], cell[1], cell[2]
    
    # All 8 corners of the unit cell parallelepiped
    corners = np.array([
        [0, 0, 0],
        a,
        b,
        c,
        a + b,
        a + c,
        b + c,
        a + b + c,
    ])
    
    # Bounding box extent = max - min for each dimension
    return corners.max(axis=0) - corners.min(axis=0)


def is_cell_orthogonal(cell: np.ndarray, angle_tol: float = 0.1) -> bool:
    """Check if cell is orthogonal (all angles 90° within tolerance).
    
    Args:
        cell: (3, 3) cell vectors as ROW vectors
        angle_tol: Tolerance in degrees (default 0.1°)
    
    Returns:
        True if all angles are 90° ± angle_tol
    """
    a, b, c = cell[0], cell[1], cell[2]
    
    def angle(v1, v2):
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-10 or n2 < 1e-10:
            return 90.0
        cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        return np.degrees(np.arccos(cos_a))
    
    alpha = angle(b, c)  # Angle between b and c
    beta = angle(a, c)   # Angle between a and c
    gamma = angle(a, b)  # Angle between a and b
    
    return (
        abs(alpha - 90.0) <= angle_tol
        and abs(beta - 90.0) <= angle_tol
        and abs(gamma - 90.0) <= angle_tol
    )


def wrap_positions_triclinic(
    positions: np.ndarray,
    cell: np.ndarray,
    atoms_per_molecule: int,
) -> np.ndarray:
    """Wrap positions into a triclinic cell using fractional coordinates.
    
    For triclinic cells, we wrap molecules as units (based on center of mass)
    to preserve molecular integrity.
    
    Args:
        positions: (N, 3) atom positions in nm
        cell: (3, 3) cell vectors as ROW vectors
        atoms_per_molecule: Number of atoms per molecule
    
    Returns:
        (N, 3) wrapped positions
    """
    if len(positions) == 0:
        return positions
    
    # Inverse of cell transpose for fractional coordinate conversion
    inv_cell_T = np.linalg.inv(cell.T)
    
    n_molecules = len(positions) // atoms_per_molecule
    wrapped = np.zeros_like(positions)
    
    for mol_idx in range(n_molecules):
        start = mol_idx * atoms_per_molecule
        end = start + atoms_per_molecule
        mol = positions[start:end].copy()
        
        # Convert to fractional coordinates
        mol_frac = mol @ inv_cell_T
        
        # Wrap center of mass into [0, 1)
        com_frac = mol_frac.mean(axis=0)
        shift_frac = -np.floor(com_frac)
        
        # Apply shift
        mol_frac += shift_frac
        
        # Convert back to Cartesian
        wrapped[start:end] = mol_frac @ cell.T
    
    return wrapped


# Number of atoms per TIP4P water molecule (OW, HW1, HW2, MW)
ATOMS_PER_WATER_MOLECULE = 4

# Water atom names template for ONE molecule
WATER_ATOM_NAMES_TEMPLATE = ["OW", "HW1", "HW2", "MW"]

# Template density in g/cm³ calculated from tip4p.gro:
# 216 molecules in 1.86824³ nm³ box
# Density = (216 molecules * 18.01528 g/mol) / (6.02214076e23 molecules/mol * 1.86824³ * 1e-21 cm³)
# = 3891.3 g / (6.022e23 * 6.52 nm³ * 1e-21 cm³/nm³) = 3891.3 g / 3924 cm³ ≈ 0.991 g/cm³
TEMPLATE_DENSITY_GCM3 = 0.991

# Module-level cache for water template (never changes)
_water_template_cache: Optional[tuple[np.ndarray, list[str], np.ndarray]] = None


def round_to_periodicity(
    target_dim: float,
    cell_dim: float,
    min_multiplier: int = 1,
) -> tuple[float, int]:
    """Round a target dimension to the nearest multiple of cell periodicity.
    
    Ensures continuous periodic images by adjusting dimensions to exact
    multiples of the ice unit cell dimensions.
    
    Args:
        target_dim: Target dimension in nm (e.g., box_x, ice_thickness).
        cell_dim: Ice unit cell dimension in nm.
        min_multiplier: Minimum number of unit cells (default 1).
    
    Returns:
        Tuple of (adjusted_dim, n_cells):
            - adjusted_dim: Dimension rounded up to nearest multiple of cell_dim.
            - n_cells: Number of unit cells in the adjusted dimension.
    
    Example:
        >>> round_to_periodicity(5.0, 0.893)  # box_x=5.0nm, ice cell=0.893nm
        (5.358, 6)  # Adjusted to 6 unit cells = 6 * 0.893 = 5.358 nm
    """
    if cell_dim <= 0:
        return target_dim, min_multiplier
    
    # Calculate how many unit cells needed (round up for continuous coverage)
    n_cells = max(min_multiplier, math.ceil(target_dim / cell_dim))
    
    # Adjusted dimension is exact multiple of cell dimension
    adjusted_dim = n_cells * cell_dim
    
    return adjusted_dim, n_cells


def scale_positions_for_density(
    positions: np.ndarray,
    template_density: float,
    target_density: float,
) -> np.ndarray:
    """Scale molecular positions to achieve target density.

    Density is proportional to (spacing)^(-3) in 3D, so:
    scale = (template_density / target_density)^(1/3)

    This scales the unit cell dimensions to achieve the desired density
    while preserving molecular geometry.

    Args:
        positions: (N, 3) array of atom positions in nm.
        template_density: Density of original template in g/cm³.
        target_density: Desired density in g/cm³.

    Returns:
        Scaled positions array (same shape as input).

    Raises:
        ValueError: If template_density or target_density is not positive.
    """
    if template_density <= 0:
        raise ValueError(f"template_density must be positive, got {template_density}")
    if target_density <= 0:
        raise ValueError(f"target_density must be positive, got {target_density}")

    scale = (template_density / target_density) ** (1.0 / 3.0)
    return positions * scale


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
    cell_matrix: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, int]:
    """Tile a structure to fill a target rectangular region using cell periodicity.

    Replicates the input structure by shifting copies along each axis to
    cover the target region. Atoms that fall outside the target region are
    filtered out. Positions are wrapped into the target region using modulo.

    Works for ice (3 atoms/molecule from GenIce) or water (4 atoms/molecule
    from tip4p.gro). The caller is responsible for replicating atom_names.

    For triclinic cells (Ice II, Ice V, Ice VI):
    - cell_matrix: (3, 3) array of lattice vectors as ROW vectors [a, b, c]
    - Tiling uses lattice vectors for offsets instead of coordinate axes
    - PBC wrapping uses fractional coordinates via wrap_positions_triclinic()

    For orthogonal cells:
    - cell_matrix can be omitted (defaults to None)
    - Tiling uses coordinate axes
    - PBC wrapping uses standard modulo

    Args:
        positions: (N, 3) atom positions in nm.
        cell_dims: [a, b, c] cell dimensions in nm (bounding box extent).
            Use get_cell_extent() to calculate this for any cell shape.
        target_region: [lx, ly, lz] target region dimensions in nm.
        atoms_per_molecule: Number of atoms per molecule (optional).
            - For TIP4P water: 4 (OW, HW1, HW2, MW)
            - For GenIce ice: 3 (O, H, H)
            If None, will attempt to infer from total atom count (deprecated,
            may produce incorrect results for ambiguous cases).
        cell_matrix: (3, 3) cell vectors as ROW vectors [a, b, c] (optional).
            Required for triclinic cells to enable lattice-vector tiling.
            For orthogonal cells, this can be omitted.

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

    # Determine if we need triclinic-aware tiling
    is_triclinic = False
    if cell_matrix is not None:
        is_triclinic = not is_cell_orthogonal(cell_matrix)

    # Vectorized tiling: generate all offsets at once and use broadcasting
    # Create grid of indices for all tile positions
    ix_vals = np.arange(nx)
    iy_vals = np.arange(ny)
    iz_vals = np.arange(nz)
    
    # Generate all (ix, iy, iz) combinations using meshgrid
    ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')
    
    # Compute all offsets at once: shape (nx*ny*nz, 3)
    # For triclinic cells, offsets are along lattice vectors (cell_matrix rows)
    # For orthogonal cells, offsets are along coordinate axes (cell_dims)
    if is_triclinic and cell_matrix is not None:
        # Triclinic: use lattice vectors for offsets
        lattice_a = cell_matrix[0]  # First lattice vector
        lattice_b = cell_matrix[1]  # Second lattice vector
        lattice_c = cell_matrix[2]  # Third lattice vector
        offsets = np.stack([
            ix_grid.ravel() * lattice_a[0] + iy_grid.ravel() * lattice_b[0] + iz_grid.ravel() * lattice_c[0],
            ix_grid.ravel() * lattice_a[1] + iy_grid.ravel() * lattice_b[1] + iz_grid.ravel() * lattice_c[1],
            ix_grid.ravel() * lattice_a[2] + iy_grid.ravel() * lattice_b[2] + iz_grid.ravel() * lattice_c[2],
        ], axis=1)
    else:
        # Orthogonal: use coordinate axes
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
    # Also filter out molecules that span the PBC boundary (atoms outside [0, target_region))
    tol = 1e-10

    # Count total molecules in tiled structure
    n_tiled_molecules = len(all_positions) // atoms_per_molecule

    # Check each molecule: keep only if ALL its atoms are inside target region
    # AND all atoms are >= 0 (lower bound check)
    # This filters out molecules that span the PBC boundary of the original unit cell
    keep_molecules = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = all_positions[start_atom:end_atom]

        # Check if ALL atoms of this molecule are inside target region [0, target_region)
        all_inside_x = np.all((mol_atoms[:, 0] >= 0) & (mol_atoms[:, 0] < lx - tol))
        all_inside_y = np.all((mol_atoms[:, 1] >= 0) & (mol_atoms[:, 1] < ly - tol))
        all_inside_z = np.all((mol_atoms[:, 2] >= 0) & (mol_atoms[:, 2] < lz - tol))

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

    # CRITICAL: Wrap molecules as UNITS, not individual atoms
    # This preserves molecular integrity when molecules span the PBC boundary
    # Without this, atoms of the same molecule could end up on opposite sides
    # of the box (e.g., O at Y=0.1, H at Y=1.9 in a 2.0 nm box), causing
    # bonds to appear 1.8 nm long instead of the correct 0.1 nm.
    #
    # After filtering, all atoms should already be in [0, target_region).
    # The wrapping here is a safety measure for edge cases (e.g., floating point
    # precision issues, or molecules very close to boundary).
    #
    # For triclinic cells, use fractional coordinate wrapping.
    # For orthogonal cells, use standard coordinate-axis wrapping.
    if is_triclinic and cell_matrix is not None:
        # Build target cell matrix for wrapping (orthogonal box)
        target_cell = np.diag(target_region)
        # Use triclinic wrapping with the target orthogonal box
        tiled_positions = wrap_positions_triclinic(filtered, target_cell, atoms_per_molecule)
    else:
        # Orthogonal wrapping (standard coordinate-axis modulo)
        tiled_positions = np.zeros_like(filtered)
        n_filtered_molecules = len(filtered) // atoms_per_molecule

        for mol_idx in range(n_filtered_molecules):
            start_atom = mol_idx * atoms_per_molecule
            end_atom = start_atom + atoms_per_molecule
            mol_atoms = filtered[start_atom:end_atom].copy()

            # Calculate shift based on minimum position across all atoms
            # This handles any edge cases where atoms might be slightly outside [0, target_region)
            shift = np.zeros(3)
            for dim in range(3):
                min_pos = mol_atoms[:, dim].min()
                max_pos = mol_atoms[:, dim].max()
                
                # Only shift if atoms are actually outside [0, target_region)
                if min_pos < 0:
                    # Shift up to bring minimum into range
                    shift[dim] = -np.floor(min_pos / target_region[dim]) * target_region[dim]
                elif max_pos >= target_region[dim]:
                    # Shift down to bring maximum into range
                    shift[dim] = -np.ceil(max_pos / target_region[dim]) * target_region[dim] + target_region[dim]

            # Apply shift to all atoms in the molecule
            shifted = mol_atoms + shift
            
            # Second pass: ensure all atoms are within [0, target_region)
            # This handles edge cases where the first shift pushed atoms out the other side
            # (e.g., shifting up for negative atoms pushed positive atoms over the boundary)
            for dim in range(3):
                min_pos = shifted[:, dim].min()
                max_pos = shifted[:, dim].max()
                
                if min_pos < 0:
                    # Atoms are still negative after first shift - shift up by one box
                    shifted[:, dim] += target_region[dim]
                elif max_pos >= target_region[dim]:
                    # Atoms are too high after first shift - shift down by one box
                    shifted[:, dim] -= target_region[dim]
            
            tiled_positions[start_atom:end_atom] = shifted

    # Molecule count is exact (no truncation needed)
    n_molecules = len(keep_molecules)

    return tiled_positions, n_molecules


def fill_region_with_water(
    region_dims: np.ndarray,
    target_density: Optional[float] = None,
) -> tuple[np.ndarray, list[str], int]:
    """Fill a rectangular region with TIP4P water molecules.

    Convenience function that loads the water template, tiles it into
    the specified region, and returns positions, atom names, and
    molecule count.

    Supports density scaling: if target_density is provided, positions
    are scaled to match the target density using the cube root formula:
    scale = (template_density / target_density)^(1/3)

    Args:
        region_dims: [lx, ly, lz] region dimensions in nm.
        target_density: Target water density in g/cm³. If None, uses the
            template density (~0.991 g/cm³) without scaling.

    Returns:
        Tuple of (positions, atom_names, nmolecules):
            - positions: (N, 3) water atom positions in nm
            - atom_names: list of atom names ["OW", "HW1", "HW2", "MW", ...]
            - nmolecules: number of water molecules in the region
    """
    # Load water template
    template_positions, template_atom_names, template_box = load_water_template()

    # Apply density scaling if target_density is specified
    if target_density is not None:
        scaled_positions = scale_positions_for_density(
            template_positions,
            TEMPLATE_DENSITY_GCM3,
            target_density
        )
        # Scale box dimensions by same factor for correct tiling
        scale = (TEMPLATE_DENSITY_GCM3 / target_density) ** (1.0 / 3.0)
        scaled_box = template_box * scale
    else:
        scaled_positions = template_positions
        scaled_box = template_box

    # Tile water into the target region
    tiled_positions, n_molecules = tile_structure(
        scaled_positions, scaled_box, region_dims,
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
    # Use the constant template for ONE molecule, not the full template which may have many
    all_atom_names = WATER_ATOM_NAMES_TEMPLATE * n_molecules

    return tiled_positions, all_atom_names, n_molecules
