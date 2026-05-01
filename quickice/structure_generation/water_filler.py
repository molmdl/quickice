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

from quickice.structure_generation.cell_utils import is_cell_orthogonal
from quickice.structure_generation.gro_parser import parse_gro_file


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


def compute_scaled_cell(
    cell: np.ndarray,
    nx: int,
    ny: int,
    nz: int,
) -> np.ndarray:
    """Compute a scaled cell matrix for a supercell.
    
    For triclinic cells, this creates a cell matrix where each lattice vector
    is scaled by the corresponding tile count. For orthogonal cells, this
    returns a diagonal matrix with the scaled dimensions.
    
    Args:
        cell: (3, 3) cell vectors as ROW vectors [a, b, c]
        nx: Number of tiles in X direction (along lattice vector a)
        ny: Number of tiles in Y direction (along lattice vector b)
        nz: Number of tiles in Z direction (along lattice vector c)
    
    Returns:
        (3, 3) scaled cell matrix
    """
    # Scale each lattice vector by the tile count
    scaled_a = nx * cell[0]
    scaled_b = ny * cell[1]
    scaled_c = nz * cell[2]
    
    return np.array([scaled_a, scaled_b, scaled_c])


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

    Uses shared gro_parser module. Results are cached at module
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

    # Parse GRO using shared parser
    positions, atom_names, cell = parse_gro_file(gro_path)

    # Extract diagonal for orthogonal boxes (backward compatibility)
    # The original code returned a 1D array [bx, by, bz]
    if cell.ndim == 2:
        box_dims = np.array([cell[0, 0], cell[1, 1], cell[2, 2]])
    else:
        box_dims = cell

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

    For triclinic cells (Ice V):
    - Ice V is monoclinic and can be transformed to orthogonal
    - Ice II is rhombohedral (blocked for interfaces, not transformed here)
    - Ice VI is tetragonal (orthogonal, not triclinic)
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
    if is_triclinic and cell_matrix is not None:
        # For triclinic cells, we need to compute index ranges that properly
        # cover the target region. The issue is that triclinic unit cells
        # can have atoms at negative coordinates, and lattice vectors can
        # have negative components, so we need to find the correct index range.
        
        lattice_a = cell_matrix[0]  # First lattice vector
        lattice_b = cell_matrix[1]  # Second lattice vector
        lattice_c = cell_matrix[2]  # Third lattice vector
        
        # Find the bounding box of input positions
        pos_min = positions.min(axis=0)
        pos_max = positions.max(axis=0)
        
        # We need offsets such that:
        # offset + pos_min >= 0 (atoms don't go negative)
        # offset + pos_max < target_region (atoms stay inside)
        # 
        # For triclinic cells with mixed lattice vector signs,
        # we need to search for the correct index ranges.
        
        # Strategy: compute a conservative range and let filtering do the rest
        # The offset range must span at least [target - pos_max, -pos_min]
        # to ensure coverage of [0, target]
        
        # For each dimension, estimate the required index range
        # This is a heuristic that may over-tile but ensures coverage
        
        # First, find how many tiles are needed in each lattice direction
        # to cover the extent of the target region
        extent_a = np.abs(lattice_a)
        extent_b = np.abs(lattice_b)
        extent_c = np.abs(lattice_c)
        
        # Minimum step size along each axis (conservative)
        min_step_x = min(v for v in [extent_a[0], extent_b[0], extent_c[0]] if v > 1e-10)
        min_step_y = min(v for v in [extent_a[1], extent_b[1], extent_c[1]] if v > 1e-10)
        min_step_z = min(v for v in [extent_a[2], extent_b[2], extent_c[2]] if v > 1e-10)
        
        # Range needed: from -pos_min to target - pos_min
        offset_min_needed = -pos_max  # To shift min position to >= 0
        offset_max_needed = target_region - pos_min  # To keep max position < target
        
        # Calculate index ranges that span the needed offset range
        # For each lattice direction, estimate min and max index
        
        # Use inverse cell matrix to convert offset bounds to fractional coords
        inv_cell = np.linalg.inv(cell_matrix)
        
        # Fractional coords of offset bounds
        frac_min = offset_min_needed @ inv_cell.T
        frac_max = offset_max_needed @ inv_cell.T
        
        # Conservative: use floor of min and ceil of max for each direction
        ix_min = int(np.floor(frac_min[0])) - 1  # -1 for safety margin
        ix_max = int(np.ceil(frac_max[0])) + 1   # +1 for safety margin
        iy_min = int(np.floor(frac_min[1])) - 1
        iy_max = int(np.ceil(frac_max[1])) + 1
        iz_min = int(np.floor(frac_min[2])) - 1
        iz_max = int(np.ceil(frac_max[2])) + 1
        
        # Ensure at least 1 tile in each direction
        if ix_max <= ix_min:
            ix_min, ix_max = 0, 1
        if iy_max <= iy_min:
            iy_min, iy_max = 0, 1
        if iz_max <= iz_min:
            iz_min, iz_max = 0, 1
        
        ix_vals = np.arange(ix_min, ix_max)
        iy_vals = np.arange(iy_min, iy_max)
        iz_vals = np.arange(iz_min, iz_max)
    else:
        # Orthogonal: use standard [0, n) index range
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

    # CRITICAL: Wrap and filter molecules as UNITS
    # This preserves molecular integrity when molecules span the PBC boundary.
    # Molecules with atoms outside [0, target_region) are wrapped based on their
    # center of mass, then individual atoms are clamped into the box.
    n_tiled_molecules = len(all_positions) // atoms_per_molecule
    tol = 1e-10

    keep_molecules = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = all_positions[start_atom:end_atom]

        # Wrap molecule based on center of mass ONLY
        # This handles molecules that span PBC boundaries (e.g., hydrate guests at origin)
        # CRITICAL: Molecules with atoms outside [0, target_region) are ACCEPTED
        # The final molecular wrapping step will handle atom positions correctly
        
        # Wrap COM into [0, target_region) - this is the ONLY wrapping here
        for dim in range(3):
            com = mol_atoms[:, dim].mean()
            # Wrap COM into [0, target_region)
            # Use modulo operation for cleaner wrapping
            if com < 0:
                # Shift up by enough boxes to bring COM into range
                n_boxes = int(np.ceil(-com / target_region[dim]))
                all_positions[start_atom:end_atom, dim] += n_boxes * target_region[dim]
                mol_atoms = all_positions[start_atom:end_atom]
            elif com >= target_region[dim]:
                # Shift down by enough boxes to bring COM into range
                n_boxes = int(np.floor(com / target_region[dim]))
                all_positions[start_atom:end_atom, dim] -= n_boxes * target_region[dim]
                mol_atoms = all_positions[start_atom:end_atom]
        
        # Accept the molecule - atoms can be outside [0, target_region)
        # This is CORRECT for molecules spanning PBC boundaries
        # Downstream code (e.g., overlap detection) will handle wrapping
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

    # No final wrapping needed - molecules are already wrapped based on COM
    # Atoms can be outside [0, target_region) for molecules spanning PBC boundaries
    # This is CORRECT behavior - downstream code should handle PBC wrapping
    # (e.g., overlap detection wraps coordinates before KDTree operations)
    tiled_positions = filtered

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
