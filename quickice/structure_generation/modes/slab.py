"""Slab mode: ice-water-ice sandwich along Z-axis.

Creates a three-layer structure:
- Bottom ice: Z = [0, ice_thickness]
- Water: Z = [ice_thickness, ice_thickness + water_thickness]
- Top ice: Z = [ice_thickness + water_thickness, box_z]

For hydrate->interface conversion:
- Extracts guest molecules from hydrate candidate
- Places guests in the water region (middle layer)
- Preserves guest molecules in InterfaceStructure for rendering/export
"""

import numpy as np

# Ice atom names template (GenIce: 3 atoms per molecule)
# Memory note: Creates O(n) list for n molecules (~240KB for 10k molecules).
# Acceptable for typical use. For very large systems (>10k), this is modest overhead.
ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]


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


def _detect_guest_atoms(atom_names: list[str], atoms_per_mol: int = 4) -> tuple[list[int], list[int]]:
    """Detect indices of guest molecules vs water framework in candidate positions.
    
    For hydrate candidates:
    - Water framework atoms: OW, HW1, HW2, MW (TIP4P pattern)
    - Guest atoms: anything else (Me, C, H, etc.)
    
    Args:
        atom_names: List of atom names from candidate
        atoms_per_mol: Expected atoms per molecule (4 for TIP4P/hydrate)
    
    Returns:
        Tuple of (water_framework_atom_indices, guest_atom_indices) as lists
    """
    water_indices = []
    guest_indices = []
    
    i = 0
    while i < len(atom_names):
        # Check first atom of each molecule
        if i + atoms_per_mol <= len(atom_names):
            first_atom = atom_names[i]
            # Water framework: first atom is OW (TIP4P water oxygen)
            if first_atom == "OW":
                water_indices.extend(range(i, i + atoms_per_mol))
                i += atoms_per_mol
            else:
                # This is a guest molecule (united-atom CH4 'Me', all-atom CH4 'C', etc.)
                # Guest can be 1 atom (Me), 5 atoms (CH4 all-atom), or more (THF)
                # Detect based on atom type
                guest_atoms = _count_guest_atoms(atom_names, i)
                guest_indices.extend(range(i, i + guest_atoms))
                i += guest_atoms
        else:
            # Not enough atoms for full molecule - treat as guest
            guest_indices.extend(range(i, len(atom_names)))
            i = len(atom_names)
    
    return water_indices, guest_indices


def _count_guest_atoms(atom_names: list[str], start: int) -> int:
    """Count atoms in a guest molecule starting at index.
    
    Guest types:
    - Me: 1 atom (united-atom methane)
    - C: 5 atoms (all-atom methane: C + 4H)
    - For THF: starts with O or C (13 atoms)
    
    Args:
        atom_names: List of atom names
        start: Starting index
    
    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0
    
    first_atom = atom_names[start]
    
    # United-atom methane (Me) - single carbon
    if first_atom == "Me":
        return 1
    
    # All-atom methane (C + 4H)
    if first_atom == "C":
        count = 0
        i = start
        while i < len(atom_names) and i < start + 5:
            count += 1
            i += 1
        return count
    
    # THF starts with O (oxygen)
    if first_atom == "O":
        # THF has 13 atoms: O, CA, CA, CB, CB, + 8H
        count = 0
        i = start
        while i < len(atom_names) and i < start + 15:  # Max 15 atoms
            count += 1
            i += 1
            # Stop if we hit another O or OW (next molecule)
            if i < len(atom_names) and atom_names[i] in ["O", "OW"]:
                break
        return count
    
    # CO2: starts with C, then O, O
    if first_atom == "C" and start + 2 < len(atom_names):
        if atom_names[start + 1] == "O" and atom_names[start + 2] == "O":
            return 3
    
    # Default: treat as 1 atom guest
    return 1


def _count_guest_molecules(atom_names: list[str], guest_indices: list[int]) -> int:
    """Count the number of distinct guest molecules from guest atom indices.
    
    Args:
        atom_names: Full list of atom names
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
        atoms_in_mol = _count_guest_atoms(atom_names, atom_idx)
        count += 1
        i += atoms_in_mol
    
    return count


from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.water_filler import (
    tile_structure,
    fill_region_with_water,
    round_to_periodicity,
    get_cell_extent,
)
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    filter_atom_names,
)
from quickice.phase_mapping.water_density import water_density_gcm3


def assemble_slab(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble ice-water-ice slab interface structure.

    The ice-water-ice sandwich is stacked along the Z-axis. Ice layers are
    tiled from the candidate ice structure, water fills the middle region,
    and overlapping water molecules are removed.

    IMPORTANT: Box dimensions and ice thickness are adjusted to ensure
    continuous periodic images. The adjustments are reported in the
    InterfaceStructure.report field.

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with mode, box dimensions, thicknesses, etc.

    Returns:
        InterfaceStructure with combined ice + water positions.
        Ice atoms come FIRST, then water atoms.

    Raises:
        InterfaceGenerationError: If generation fails or triclinic cell detected.
    """
    from quickice.structure_generation.errors import InterfaceGenerationError

    # Get ice cell dimensions for tiling (bounding box extent)
    # Works for both orthogonal and triclinic cells
    ice_cell_dims = get_cell_extent(candidate.cell)
    
    # Store cell matrix for triclinic-aware tiling
    cell_matrix = candidate.cell

    # Detect atoms per molecule from candidate atom names
    # Handles both GenIce ice (3 atoms) and TIP4P/hydrate (4 atoms)
    atoms_per_mol = detect_atoms_per_molecule(candidate.atom_names)

    # === HYDRATE FIX: Handle guest positions ===
    # Step 1: Extract guest molecules from hydrate candidates FIRST
    # (We defer tiling/shifting until after dimension adjustments)
    is_hydrate = candidate.metadata.get("original_hydrate", False)
    raw_guest_positions = None
    guest_atom_names = []
    guest_nmolecules = 0
    
    # For hydrate, we need to tile ONLY water-framework atoms (not guests)
    water_framework_positions = candidate.positions
    water_framework_atom_names = candidate.atom_names
    
    if is_hydrate:
        # Extract guest atoms from candidate positions
        water_indices, guest_indices = _detect_guest_atoms(
            candidate.atom_names, atoms_per_mol
        )
        
        if guest_indices:
            # Extract raw guest positions (1 unit cell, needs tiling later)
            raw_guest_positions = candidate.positions[guest_indices].copy()
            guest_atom_names = [candidate.atom_names[i] for i in guest_indices]
            
            # Store initial guest molecule count (will be updated after tiling)
            guest_nmolecules = _count_guest_molecules(candidate.atom_names, guest_indices)
            
            # For ice tiling, use ONLY water-framework atoms
            water_framework_positions = candidate.positions[water_indices]
            water_framework_atom_names = [candidate.atom_names[i] for i in water_indices]
    
    # ADJUST DIMENSIONS FOR PERIODICITY
    # Round box dimensions and ice thickness to multiples of ice unit cell
    # This ensures continuous periodic images without gaps at boundaries
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_ice_thickness, nz_ice = round_to_periodicity(config.ice_thickness, ice_cell_dims[2])

    # Track adjustments for reporting
    adjustments = []
    if abs(adjusted_box_x - config.box_x) > 0.001:
        adjustments.append(f"  box_x: {config.box_x:.3f} → {adjusted_box_x:.3f} nm ({nx} cells)")
    if abs(adjusted_box_y - config.box_y) > 0.001:
        adjustments.append(f"  box_y: {config.box_y:.3f} → {adjusted_box_y:.3f} nm ({ny} cells)")
    if abs(adjusted_ice_thickness - config.ice_thickness) > 0.001:
        adjustments.append(f"  ice_thickness: {config.ice_thickness:.3f} → {adjusted_ice_thickness:.3f} nm ({nz_ice} cells)")

    # Recalculate box_z to match adjusted ice thickness
    # box_z = 2 * ice_thickness + water_thickness
    adjusted_box_z = 2 * adjusted_ice_thickness + config.water_thickness
    if abs(adjusted_box_z - config.box_z) > 0.001:
        adjustments.append(f"  box_z: {config.box_z:.3f} → {adjusted_box_z:.3f} nm (auto-adjusted)")

    # Box dimensions (using adjusted values)
    box_dims = np.array([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Tile ice for bottom layer: fill [adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]
    # For hydrate: tile only water-framework (guests extracted separately)
    bottom_ice_positions, bottom_ice_nmolecules = tile_structure(
        water_framework_positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=atoms_per_mol,  # Detected: 3 for ice, 4 for TIP4P/hydrate
        cell_matrix=cell_matrix  # Triclinic-aware tiling
    )

    # Tile ice for top layer: same target region, then shift Z
    # For hydrate: tile only water-framework (guests extracted separately)
    top_ice_positions, top_ice_nmolecules = tile_structure(
        water_framework_positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=atoms_per_mol,  # Detected: 3 for ice, 4 for TIP4P/hydrate
        cell_matrix=cell_matrix  # Triclinic-aware tiling
    )
    # Shift top layer to Z = [adjusted_ice_thickness + water_thickness, adjusted_box_z]
    top_ice_positions = top_ice_positions.copy()
    top_ice_positions[:, 2] += adjusted_ice_thickness + config.water_thickness

    # PBC wrap check: ensure top ice atoms are within [0, adjusted_box_z)
    # After shift, atoms should be in [adjusted_ice_thickness + water_thickness, adjusted_box_z)
    # but we wrap defensively to handle floating-point precision issues
    # and catch any configuration errors early.
    top_ice_z = top_ice_positions[:, 2]
    if len(top_ice_z) > 0:
        # Check for atoms that would wrap to bottom layer (Z < 0 or Z >= adjusted_box_z)
        below_zero = top_ice_z < 0
        above_boxz = top_ice_z >= adjusted_box_z

        if np.any(below_zero) or np.any(above_boxz):
            # This should never happen if validation is correct, but handle defensively
            from quickice.structure_generation.errors import InterfaceGenerationError
            n_below = np.sum(below_zero)
            n_above = np.sum(above_boxz)
            raise InterfaceGenerationError(
                f"PBC overlap detected: {n_below} top ice atoms have Z < 0, "
                f"{n_above} atoms have Z >= box_z ({adjusted_box_z:.2f} nm). "
                f"This indicates a configuration error: box_z should equal "
                f"2*ice_thickness + water_thickness = {2*adjusted_ice_thickness + config.water_thickness:.2f} nm. "
                f"Got ice_thickness={adjusted_ice_thickness:.2f} nm, water_thickness={config.water_thickness:.2f} nm.",
                mode=config.mode
            )

    # Combine ice positions (bottom + top)
    if len(bottom_ice_positions) > 0 and len(top_ice_positions) > 0:
        combined_ice_positions = np.vstack([bottom_ice_positions, top_ice_positions])
    elif len(bottom_ice_positions) > 0:
        combined_ice_positions = bottom_ice_positions
    elif len(top_ice_positions) > 0:
        combined_ice_positions = top_ice_positions
    else:
        combined_ice_positions = np.zeros((0, 3), dtype=float)

    total_ice_nmolecules = bottom_ice_nmolecules + top_ice_nmolecules

    # Build ice atom names dynamically based on detected atoms per molecule
    # GenIce ice: ["O", "H", "H"], TIP4P/hydrate: ["OW", "HW1", "HW2", "MW"]
    # For hydrate: use water framework pattern (just OW/HW1/HW2/MW, no C/H)
    if atoms_per_mol == 4:
        ice_atom_names = ["OW", "HW1", "HW2", "MW"] * total_ice_nmolecules
    else:
        ice_atom_names = ["O", "H", "H"] * total_ice_nmolecules

    # Calculate water density from ice temperature/pressure
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)

    # Fill water in middle region: [adjusted_box_x, adjusted_box_y, water_thickness]
    # Note: water thickness is NOT adjusted - it's the gap between ice layers
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        np.array([adjusted_box_x, adjusted_box_y, config.water_thickness]),
        target_density=target_water_density
    )

    # Shift water to Z = [adjusted_ice_thickness, adjusted_ice_thickness + water_thickness]
    if len(water_positions) > 0:
        water_positions = water_positions.copy()
        water_positions[:, 2] += adjusted_ice_thickness

    # Detect overlaps between ice O and water O
    # Ice O atoms: indices [0, atoms_per_mol, 2*atoms_per_mol, ...] (3 or 4 atoms per molecule)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule)
    if len(combined_ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = combined_ice_positions[::atoms_per_mol]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules (atoms_per_molecule=4 for TIP4P)
    if overlapping_mol_indices:
        trimmed_water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            overlapping_mol_indices,
            atoms_per_molecule=4
        )
        # Filter atom names to match positions (CRITICAL: must use same overlapping_mol_indices)
        water_atom_names = filter_atom_names(
            water_atom_names,
            overlapping_mol_indices,
            atoms_per_molecule=4
        )
    else:
        trimmed_water_positions = water_positions

    # === HYDRATE FIX: Tile and shift guests to water region (after dimension adjustments) ===
    processed_guest_positions = None
    processed_guest_atom_names = []
    
    if is_hydrate and raw_guest_positions is not None and len(raw_guest_positions) > 0:
        # Calculate water region bounds for tiling guests
        water_region_dims = np.array([
            adjusted_box_x, 
            adjusted_box_y, 
            config.water_thickness
        ])
        
        # Get extent of original guest structure (for tiling)
        guest_cell_dims = get_cell_extent(candidate.cell)
        
        # Tile guests across the water region
        # Use detected atoms per molecule for guest type
        guest_atoms_per_mol = atoms_per_mol
        
        tilable_guest_positions, tiled_guest_nmolecules = tile_structure(
            raw_guest_positions,
            guest_cell_dims,
            water_region_dims,
            atoms_per_molecule=guest_atoms_per_mol,
            cell_matrix=cell_matrix
        )
        
        # Shift guests to water region: Z = [adjusted_ice_thickness, adjusted_ice_thickness + water_thickness]
        if len(tilable_guest_positions) > 0:
            tilable_guest_positions = tilable_guest_positions.copy()
            tilable_guest_positions[:, 2] += adjusted_ice_thickness
        
        processed_guest_positions = tilable_guest_positions
        processed_guest_atom_names = guest_atom_names
        
        # Update guest molecule count to reflect actual tiled count
        guest_nmolecules = tiled_guest_nmolecules

    # === HYDRATE FIX: Combine all positions including guests ===
    # Order: ice FIRST, then guests (in water region), then water
    all_parts = []
    all_names_parts = []
    
    if len(combined_ice_positions) > 0:
        all_parts.append(combined_ice_positions)
        all_names_parts.append(ice_atom_names)
    
    if processed_guest_positions is not None and len(processed_guest_positions) > 0:
        all_parts.append(processed_guest_positions)
        all_names_parts.append(processed_guest_atom_names)
    
    if len(trimmed_water_positions) > 0:
        all_parts.append(trimmed_water_positions)
        all_names_parts.append(water_atom_names)
    
    if all_parts:
        all_positions = np.vstack(all_parts)
        all_atom_names = sum(all_names_parts, [])
    else:
        all_positions = np.zeros((0, 3), dtype=float)
        all_atom_names = []

    # Compute counts
    ice_atom_count = len(combined_ice_positions)
    guest_atom_count = len(processed_guest_positions) if processed_guest_positions is not None else 0
    water_atom_count = len(trimmed_water_positions)

    # Build cell matrix
    # For triclinic phases in slab mode, we output orthogonal cells for now.
    # This is because:
    # 1. Ice atoms are positioned using triclinic lattice vectors
    # 2. Water atoms are positioned in orthogonal space (between ice layers)
    # 3. These two geometries are fundamentally incompatible for a single triclinic cell
    #
    # Future improvement: Transform all atoms to a consistent triclinic space
    cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Build report (gmx solvate convention: molecules present, not removed)
    total_molecules = total_ice_nmolecules + guest_nmolecules + water_nmolecules
    
    # Include periodicity adjustments in report
    adjustment_report = ""
    if adjustments:
        adjustment_report = (
            f"\n\nPeriodicity adjustments (for continuous images):\n" +
            "\n".join(adjustments)
        )
    
    report = (
        f"Generated slab interface structure\n"
        f"  Ice molecules: {total_ice_nmolecules}\n"
        f"  Guest molecules: {guest_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Box: {adjusted_box_x:.2f} x {adjusted_box_y:.2f} x {adjusted_box_z:.2f} nm"
        f"{adjustment_report}"
    )

    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=total_ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="slab",
        report=report,
        guest_atom_count=guest_atom_count,
        guest_nmolecules=guest_nmolecules
    )
