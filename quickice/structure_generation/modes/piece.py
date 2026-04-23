"""Piece mode: ice crystal embedded in water box.

Centers an ice crystal inside a water box. The ice piece dimensions
are derived from the candidate cell, and overlapping water molecules
are removed.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.water_filler import (
    tile_structure,
    fill_region_with_water,
    get_cell_extent,
)
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    filter_atom_names,
)
from quickice.phase_mapping.water_density import water_density_gcm3


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


def assemble_piece(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble piece interface structure: ice centered in water box.

    The ice piece is centered in the water box. Overlapping water molecules
    are removed. The ice piece dimensions are derived from the candidate cell.

    For v3.0, only orthogonal boxes are supported (cube/rectangular prism).

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with box dimensions.

    Returns:
        InterfaceStructure with ice (centered) + water positions.

    Raises:
        InterfaceGenerationError: If box is smaller than ice piece or generation fails.
    """
    # Get ice piece dimensions for positioning (bounding box extent)
    # Works for both orthogonal and triclinic cells
    ice_dims = get_cell_extent(candidate.cell)
    
    # Store cell matrix for triclinic-aware tiling
    cell_matrix = candidate.cell

    # Validate: box dimensions must be larger than ice piece
    if config.box_x <= ice_dims[0]:
        raise InterfaceGenerationError(
            f"Box X dimension ({config.box_x:.2f} nm) must be larger than ice piece X ({ice_dims[0]:.2f} nm). "
            f"\n\nThe ice crystal is centered in the water box. The box must have extra space "
            f"around the ice for water molecules. "
            f"\n\nHow to fix: Increase box X to at least {ice_dims[0] + 1.0:.2f} nm.",
            mode="piece"
        )
    if config.box_y <= ice_dims[1]:
        raise InterfaceGenerationError(
            f"Box Y dimension ({config.box_y:.2f} nm) must be larger than ice piece Y ({ice_dims[1]:.2f} nm). "
            f"\n\nThe ice crystal is centered in the water box. The box must have extra space "
            f"around the ice for water molecules. "
            f"\n\nHow to fix: Increase box Y to at least {ice_dims[1] + 1.0:.2f} nm.",
            mode="piece"
        )
    if config.box_z <= ice_dims[2]:
        raise InterfaceGenerationError(
            f"Box Z dimension ({config.box_z:.2f} nm) must be larger than ice piece Z ({ice_dims[2]:.2f} nm). "
            f"\n\nThe ice crystal is centered in the water box. The box must have extra space "
            f"around the ice for water molecules. "
            f"\n\nHow to fix: Increase box Z to at least {ice_dims[2] + 1.0:.2f} nm.",
            mode="piece"
        )

    # Box dimensions
    box_dims = np.array([config.box_x, config.box_y, config.box_z])

    # Detect atoms per molecule from candidate atom names
    # Handles both GenIce ice (3 atoms: O, H, H) and TIP4P/hydrate (4 atoms: OW, HW1, HW2, MW)
    atoms_per_mol = detect_atoms_per_molecule(candidate.atom_names)

    # Tile ice to fill piece region (essentially just the candidate itself)
    tiled_ice_positions, ice_nmolecules = tile_structure(
        candidate.positions,
        ice_dims,
        ice_dims,
        atoms_per_molecule=atoms_per_mol,
        cell_matrix=cell_matrix  # Triclinic-aware tiling
    )

    if len(tiled_ice_positions) == 0:
        raise InterfaceGenerationError(
            "Ice tiling produced zero atoms. Check candidate structure.",
            mode="piece"
        )

    # Center the ice piece in the box
    offset = box_dims / 2.0 - ice_dims / 2.0
    centered_ice_positions = tiled_ice_positions + offset

    # Build ice atom names from candidate's atom pattern (dynamically detected)
    # For ice: ["O", "H", "H"] repeating
    # For hydrate/TIP4P: ["OW", "HW1", "HW2", "MW"] repeating
    ice_atom_names = []
    pattern_start = candidate.atom_names[:atoms_per_mol]
    for _ in range(ice_nmolecules):
        ice_atom_names.extend(pattern_start)

    # Calculate water density from ice temperature/pressure
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)

    # Fill entire box with water
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        box_dims,
        target_density=target_water_density
    )

    # Detect overlaps between centered ice O and water O
    # Ice O atoms: indices [0, atoms_per_mol, 2*atoms_per_mol, ...]
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule)
    if len(centered_ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = centered_ice_positions[::atoms_per_mol]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules
    if overlapping_mol_indices:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            overlapping_mol_indices,
            atoms_per_molecule=4  # TIP4P: OW, HW1, HW2, MW
        )
        # Filter atom names to match positions (CRITICAL: must use same overlapping_mol_indices)
        water_atom_names = filter_atom_names(
            water_atom_names,
            overlapping_mol_indices,
            atoms_per_molecule=4
        )

    # Combine: ice (centered) FIRST, then water
    if len(centered_ice_positions) > 0 and len(water_positions) > 0:
        all_positions = np.vstack([centered_ice_positions, water_positions])
    elif len(centered_ice_positions) > 0:
        all_positions = centered_ice_positions
    elif len(water_positions) > 0:
        all_positions = water_positions
    else:
        all_positions = np.zeros((0, 3), dtype=float)

    # Combine atom names
    all_atom_names = ice_atom_names + water_atom_names

    # Compute counts
    ice_atom_count = len(centered_ice_positions)
    water_atom_count = len(water_positions)

    # Build cell matrix
    cell = np.diag([config.box_x, config.box_y, config.box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + water_nmolecules
    
    # Extract guest type counts from candidate metadata if present (from hydrate conversion)
    guest_type_counts = {}
    if hasattr(candidate, 'metadata') and candidate.metadata:
        guest_type_counts = candidate.metadata.get("guest_type_counts", {})
    
    # Add guest info to report if present
    if guest_type_counts:
        guest_report = ", ".join(f"{count} {gtype}" for gtype, count in guest_type_counts.items())
        report = (
            f"Generated piece interface structure\n"
            f"  Ice molecules: {ice_nmolecules}\n"
            f"  Water molecules: {water_nmolecules}\n"
            f"  Guest molecules: {guest_report}\n"
            f"  Total molecules: {total_molecules}\n"
            f"  Ice piece: {ice_dims[0]:.2f} x {ice_dims[1]:.2f} x {ice_dims[2]:.2f} nm\n"
            f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm"
        )
    else:
        report = (
            f"Generated piece interface structure\n"
            f"  Ice molecules: {ice_nmolecules}\n"
            f"  Water molecules: {water_nmolecules}\n"
            f"  Total molecules: {total_molecules}\n"
            f"  Ice piece: {ice_dims[0]:.2f} x {ice_dims[1]:.2f} x {ice_dims[2]:.2f} nm\n"
            f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm"
        )

    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="piece",
        report=report,
        guest_type_counts=guest_type_counts
    )
