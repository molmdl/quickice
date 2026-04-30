"""Piece mode: ice crystal embedded in water box.

Centers an ice crystal inside a water box. The ice piece dimensions
are derived from the candidate cell, and overlapping water molecules
are removed.

This module also handles hydrate->interface conversion:
- Extracts guest molecules from hydrate candidate
- Places guests around ice piece (same as ice, near interface)
- Preserves guest molecules in InterfaceStructure for rendering/export
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


def _detect_guest_atoms(atom_names: list[str], atoms_perMol: int = 4) -> tuple[list[int], list[int]]:
    """Detect indices of guest molecules vs water framework in candidate positions.
    
    For hydrate candidates:
    - Water framework atoms: OW, HW1, HW2, MW (TIP4P pattern)
    - Guest atoms: anything else (Me, C, H, etc.)
    
    Args:
        atom_names: List of atom names from candidate
        atoms_perMol: Expected atoms per molecule (4 for TIP4P/hydrate)
    
    Returns:
        Tuple of (water_framework_atom_indices, guest_atom_indices) as lists
    """
    water_indices = []
    guest_indices = []
    
    i = 0
    while i < len(atom_names):
        # Check first atom of each molecule
        if i + atoms_perMol <= len(atom_names):
            first_atom = atom_names[i]
            # Water framework: first atom is OW (TIP4P water oxygen)
            if first_atom == "OW":
                water_indices.extend(range(i, i + atoms_perMol))
                i += atoms_perMol
            else:
                # This is a guest molecule (united-atom CH4 'Me', all-atom CH4 'C', etc.)
                # Guest can be 1 atom (Me), 5 atoms (CH4 all-atom), or more (THF)
                # Detect based on atom type
                guest_atoms = _count_guest_atoms(atom_names, i)
                guest_indices.extend(range(i, i + guest_atoms))
                i += guest_atoms
        else:
            # Not enough atoms for full molecule - treat remaining as guest
            guest_indices.extend(range(i, len(atom_names)))
            i = len(atom_names)
    
    return water_indices, guest_indices


def _count_guest_atoms(atom_names: list[str], start: int) -> int:
    """Count atoms in a guest molecule starting at index.
    
    Guest types:
    - Me: 1 atom (united-atom methane)
    - C: 5 atoms (all-atom methane: C + 4H)
    - For THF: starts with O or C (13 atoms total with H)
    """
    if start >= len(atom_names):
        return 0
    
    first_atom = atom_names[start]
    
    # United-atom methane (Me) - single carbon
    if first_atom == "Me":
        return 1
    
    # All-atom methane (C + 4H)
    if first_atom == "C":
        # Count up to 5 atoms (C + up to 4H)
        count = 0
        i = start
        while i < len(atom_names) and i < start + 5:
            count += 1
            i += 1
        return count
    
    # THF (starts with O or C, 12-13 atoms)
    if first_atom in ["O", "C"]:
        # Try to count all atoms in this molecule (looking for next O or start pattern)
        # Or count up to 20 atoms (generous upper bound for THF + H)
        count = 0
        i = start
        # Simple approach: count all atoms until we hit OW (water) or run out
        while i < len(atom_names):
            if atom_names[i] == "OW":
                break
            count += 1
            i += 1
            # Safety limit
            if count > 20:
                break
        return max(count, 1)
    
    # Default: treat as 1 atom guest
    return 1


def _count_guest_molecules(atom_names: list[str], guest_indices: list[int]) -> int:
    """Count the number of distinct guest molecules from guest atom indices.
    
    The guest_indices list contains all atom indices belonging to guests.
    Since atoms are grouped by molecule (not by type), we need to count
    how many distinct molecules exist in this list.
    
    Args:
        atom_names: Full list of atom names (for counting atoms per molecule)
        guest_indices: List of atom indices belonging to guests
    
    Returns:
        Number of distinct guest molecules
    """
    if not guest_indices:
        return 0
    
    count = 0
    i = 0
    while i < len(guest_indices):
        atom_idx = guest_indices[i]
        # Count atoms in this molecule using _count_guest_atoms
        atoms_in_mol = _count_guest_atoms(atom_names, atom_idx)
        count += 1
        i += atoms_in_mol
    
    return count


def assemble_piece(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble piece interface structure: ice centered in water box.

    The ice piece is centered in the water box. Overlapping water molecules
    are removed. The ice piece dimensions are derived from the candidate cell.

    For hydrate->interface conversion:
    - Also extracts and preserves guest molecules from candidate
    - Guests are placed in the middle layer (ice-water interface region)
    - Guest molecules are preserved in output for rendering/export

    For v3.0, only orthogonal boxes are supported (cube/rectangular prism).

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
                  OR hydrate candidate with metadata["original_hydrate"] = True
        config: Interface configuration with box dimensions.

    Returns:
        InterfaceStructure with ice (centered) + guest + water positions.
        If hydrate: preserves guest molecules in ice_atom_count + guest_atoms structure

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

    # === HYDRATE FIX: Extract guest molecules from candidate ===
    # Check if this is a hydrate candidate (from hydrate->interface flow)
    is_hydrate = candidate.metadata.get("original_hydrate", False)
    guest_positions = None
    guest_atom_names = []
    guest_nmolecules = 0
    
    # For hydrate, we need to tile ONLY water-framework atoms (not guests)
    # Store water-framework-only positions for tiling
    water_framework_positions = candidate.positions
    water_framework_atom_names = candidate.atom_names
    
    if is_hydrate:
        # Extract guest atoms from candidate positions
        # Water framework = OW-based, Guest = anything else (Me, C, etc.)
        water_indices, guest_indices = _detect_guest_atoms(
            candidate.atom_names, atoms_per_mol
        )
        
        if guest_indices:
            # Extract guest positions - center them in the box
            guest_positions = candidate.positions[guest_indices].copy()
            guest_atom_names = [candidate.atom_names[i] for i in guest_indices]
            
            # Count guest MOLECULES, not atoms
            # Each unique starting index is a different molecule
            # Since _detect_guest_atoms returns consecutive atom indices per molecule,
            # we count how many distinct molecules by counting the starts
            guest_nmolecules = _count_guest_molecules(candidate.atom_names, guest_indices)
            
            # Translate guest to box center (same as ice)
            guest_center = np.mean(guest_positions, axis=0)
            box_center = box_dims / 2.0
            offset = box_center - guest_center
            guest_positions = guest_positions + offset
            
            # For tiling, use ONLY water-framework atoms (filtered)
            # This prevents tile_structure from failing with mixed atom types
            water_framework_positions = candidate.positions[water_indices]
            water_framework_atom_names = [candidate.atom_names[i] for i in water_indices]
    
    # Tile ice to fill piece region (essentially just the candidate itself)
    # For hydrate: use water-framework-only positions (guests removed)
    tiled_ice_positions, ice_nmolecules = tile_structure(
        water_framework_positions,
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
    # Use water_framework_atom_names if hydrate (to avoid guest atom types)
    ice_atom_names = []
    pattern_source = water_framework_atom_names if is_hydrate else candidate.atom_names
    pattern_start = pattern_source[:atoms_per_mol]
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

    # === HYDRATE FIX: Combine: ice (centered) + water + guest ===
    # Order: ice first, then water, then guest LAST (all in same positions array)
    # This ensures all SOL molecules (ice + water) are contiguous for GROMACS export.
    all_parts = []
    all_names_parts = []
    
    if len(centered_ice_positions) > 0:
        all_parts.append(centered_ice_positions)
        all_names_parts.append(ice_atom_names)
    
    if len(water_positions) > 0:
        all_parts.append(water_positions)
        all_names_parts.append(water_atom_names)
    
    if guest_positions is not None and len(guest_positions) > 0:
        all_parts.append(guest_positions)
        all_names_parts.append(guest_atom_names)
    
    if all_parts:
        all_positions = np.vstack(all_parts)
        all_atom_names = sum(all_names_parts, [])
    else:
        all_positions = np.zeros((0, 3), dtype=float)
        all_atom_names = []

    # Compute counts
    # For hydrate: ice + guest atoms = ice_atom_count + guest atoms (combined for rendering)
    ice_atom_count = len(centered_ice_positions)
    guest_atom_count = len(guest_positions) if guest_positions is not None else 0
    water_atom_count = len(water_positions)

    # Build cell matrix
    cell = np.diag([config.box_x, config.box_y, config.box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + guest_nmolecules + water_nmolecules
    report_lines = [
        f"Generated piece interface structure",
        f"  Ice molecules: {ice_nmolecules}",
        f"  Guest molecules: {guest_nmolecules}",
        f"  Water molecules: {water_nmolecules}",
        f"  Total molecules: {total_molecules}",
        f"  Ice piece: {ice_dims[0]:.2f} x {ice_dims[1]:.2f} x {ice_dims[2]:.2f} nm",
        f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm",
    ]
    report = "\n".join(report_lines)
    
    # Return InterfaceStructure with proper atom separation
    # ice = water framework atoms only (OW-based)
    # guest = guest molecules (Me, C, etc.)
    # water = water box molecules (OW-based, TIP4P)
    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,  # Ice (hydrate water framework) atom count
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="piece",
        report=report,
        guest_atom_count=guest_atom_count,  # Guest atoms (default 0)
        guest_nmolecules=guest_nmolecules  # Guest molecule count (default 0)
    )