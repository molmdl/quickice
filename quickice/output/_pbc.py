"""PBC wrapping helpers (Group 1 CRIT-01 triclinic-aware).

Extracted from ``gromacs_writer.py`` (Phase 48.1, Wave 1). All function bodies
are byte-identical to the pre-refactor source — only the file path changed.

CRITICAL: preserves the Group 1 CRIT-01 triclinic PBC fix. The
``is_cell_orthogonal`` import from ``quickice.structure_generation.cell_utils``
MUST remain present (do NOT inline the orthogonality check).
"""

import logging

import numpy as np

from quickice.structure_generation.cell_utils import is_cell_orthogonal

logger = logging.getLogger(__name__)


def wrap_positions_into_box(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Wrap positions into the simulation box [0, cell[i,i]).
    
    For molecules spanning PBC boundaries, some atoms may be outside [0, boxsize).
    This function wraps each coordinate individually into the box for GRO file output.
    
    For orthogonal (diagonal) cells, each axis is wrapped independently via
    ``np.mod(pos[:, dim], cell[dim, dim])`` — this is the fast path used by slab
    interface exports (slab.py forces orthogonal cells).
    
    For triclinic cells (non-zero off-diagonal elements, e.g. sH/c0te/c1te hydrate
    cells parsed at hydrate_generator.py:414-430), the diagonal-only modulo would
    ignore the off-diagonal shear and leave atoms outside the parallelepiped. The
    triclinic branch wraps via fractional coordinates (``frac = pos @ inv(cell.T)``,
    ``frac = np.mod(frac, 1.0)``, ``wrapped = frac @ cell.T``), reusing the proven
    pattern from ``water_filler.wrap_positions_triclinic`` (CRIT-01 fix).
    
    Args:
        positions: (N, 3) atom positions in nm
        cell: (3, 3) cell vectors as ROW vectors
    
    Returns:
        (N, 3) positions wrapped into the cell (orthogonal: [0, cell[i,i));
        triclinic: fractional coords in [0, 1))
    """
    wrapped = positions.copy()
    if len(wrapped) == 0:
        return wrapped
    # Triclinic cells: wrap via fractional coordinates (handles off-diagonal shear).
    if not is_cell_orthogonal(cell):
        inv_cell_T = np.linalg.inv(cell.T)
        frac = wrapped @ inv_cell_T
        frac = np.mod(frac, 1.0)
        return frac @ cell.T
    # Orthogonal cells: per-axis diagonal modulo (fast path — correct for slabs).
    for dim in range(3):
        # Wrap using modulo: coord % box_size
        # np.mod handles negative numbers correctly
        wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])
    return wrapped


def wrap_molecules_into_box(
    positions: np.ndarray,
    molecule_index: list,
    cell: np.ndarray
) -> np.ndarray:
    """Wrap positions into simulation box keeping molecules intact.
    
    Unlike wrap_positions_into_box which wraps each atom independently,
    this function wraps molecules as whole units to prevent splitting
    molecules across periodic boundary conditions.
    
    For each molecule:
    1. Detect if atoms are split across PBC (distance > box_size/2)
    2. Unwrap atoms to be together in same periodic image
    3. Wrap the whole molecule into [0, box_size)
    
    For orthogonal (diagonal) cells, the unwrap + center-wrap use the diagonal
    box sizes ``cell[d, d]`` (fast path used by slab interface exports, which
    force orthogonal cells at slab.py:619).
    
    For triclinic cells (non-zero off-diagonal elements, e.g. sH/c0te/c1te
    hydrate cells parsed at hydrate_generator.py:414-430), the diagonal-only
    unwrap/center-wrap would ignore the off-diagonal shear and leave atoms
    outside the parallelepiped. The triclinic branch wraps each molecule by its
    fractional center-of-mass: ``frac = mol @ inv(cell.T)``; shift all atoms by
    ``-floor(com_frac)``; ``wrapped = frac @ cell.T``. This handles unwrap AND
    wrap in one step and naturally accounts for the triclinic shear, reusing the
    proven pattern from ``water_filler.wrap_positions_triclinic`` (CRIT-01 fix).
    
    Args:
        positions: (N, 3) atom positions in nm
        molecule_index: List of MoleculeIndex objects defining molecule boundaries
        cell: (3, 3) cell vectors as ROW vectors
    
    Returns:
        (N, 3) positions with molecules wrapped as whole units
    """
    wrapped = positions.copy()
    if len(wrapped) == 0 or not molecule_index:
        return wrapped

    # Triclinic cells: wrap each molecule by fractional center-of-mass, reusing
    # the proven water_filler.wrap_positions_triclinic pattern (adapted for
    # variable-size molecule_index: ice/water=4, ch4=5, thf=13, na/cl=1).
    # Handles unwrap + wrap in one step; accounts for off-diagonal shear.
    if not is_cell_orthogonal(cell):
        inv_cell_T = np.linalg.inv(cell.T)
        for mol in molecule_index:
            start = mol.start_idx
            count = mol.count
            mol_frac = wrapped[start:start + count] @ inv_cell_T
            # Shift the whole molecule by the integer fractional offset that
            # brings its center of mass into [0, 1). -np.floor(com) is the
            # standard PBC image selector (identical to water_filler.py:121).
            com_frac = mol_frac.mean(axis=0)
            shift_frac = -np.floor(com_frac)
            mol_frac = mol_frac + shift_frac
            wrapped[start:start + count] = mol_frac @ cell.T
        return wrapped

    # Orthogonal cells: diagonal-only unwrap + center-wrap (fast path — correct
    # for slab interfaces forced orthogonal at slab.py:619).
    for mol in molecule_index:
        start = mol.start_idx
        count = mol.count
        
        # Get positions for this molecule
        mol_positions = wrapped[start:start + count].copy()
        
        # Step 1: Unwrap atoms that are split across PBC (vectorized)
        ref_pos = mol_positions[0]
        
        # Compute delta from reference for all atoms at once
        delta = mol_positions[1:] - ref_pos
        
        # Get box sizes for all 3 dimensions
        box_sizes = np.array([cell[d, d] for d in range(3)])
        
        # Compute unwrapping shifts: vectorized across all atoms and dimensions
        shifts = np.zeros_like(delta)
        half_box = box_sizes / 2
        
        # Atoms "ahead" (delta > box/2) → shift back
        mask_ahead = delta > half_box
        shifts[mask_ahead] -= box_sizes[np.where(mask_ahead)[1] % 3]
        
        # Atoms "behind" (delta < -box/2) → shift forward
        mask_behind = delta < -half_box
        shifts[mask_behind] += box_sizes[np.where(mask_behind)[1] % 3]
        
        # Apply shifts to unwrap all atoms at once
        mol_positions[1:] += shifts
        
        # Step 2: Wrap the whole molecule into [0, box_size) using center
        center = np.mean(mol_positions, axis=0)
        
        # Vectorized center wrapping
        center_wrapped = np.mod(center, box_sizes)
        shift = center_wrapped - center
        
        # Apply shift to all atoms in molecule
        mol_positions += shift
        
        # Store wrapped positions
        wrapped[start:start + count] = mol_positions
    
    return wrapped
