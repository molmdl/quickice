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

from quickice.utils.molecule_utils import (
    count_guest_atoms,
    identify_guest_type,
    separate_guests_by_type,
)

# Ice atom names template (GenIce: 3 atoms per molecule)
# Memory note: Creates O(n) list for n molecules (~240KB for 10k molecules).
# Acceptable for typical use. For very large systems (>10k), this is modest overhead.
ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]


def _detect_guest_atoms(
    atom_names: list[str],
    atoms_per_mol: int = 4,
    guest_type: str | None = None,
    guest_atom_count: int | None = None,
    guest_atom_counts: dict[str, int] | None = None,
    guest_descriptors: list | None = None,
) -> tuple[list[int], list[int]]:
    """Detect indices of guest molecules vs water framework in candidate positions.
    
    For hydrate candidates:
    - Water framework atoms: OW, HW1, HW2, MW (TIP4P pattern)
    - Guest atoms: anything else (Me, C, H, etc.)
    
    IMPORTANT: Water molecules (starting with OW) are NEVER classified as guests,
    even if they appear at unexpected positions. This prevents misclassification
    of water molecules as guest molecules.

    Mixed-guest hydrates (Phase 45-14): when ``guest_atom_counts`` is supplied
    with more than one entry (e.g. {'ch4': 5, 'thf': 13}), the per-molecule guest
    type is detected via ``identify_guest_type`` and the atom count is looked up
    from the dict. This is REQUIRED for mixed cage occupancy (CH4 in small cages
    + THF in large cages): passing a single ``guest_type`` would make
    ``count_guest_atoms`` return that type's count for EVERY molecule
    (e.g. guest_type='ch4' returns 5 for THF which has 13 atoms), desyncing the
    walking index and producing an out-of-bounds IndexError.
    
    Args:
        atom_names: List of atom names from candidate
        atoms_per_mol: Expected atoms per molecule (4 for TIP4P/hydrate)
        guest_type: Explicit guest molecule type ("ch4" or "thf"). When provided,
            bypasses heuristic detection in count_guest_atoms for correct, explicit
            identification. When None, falls back to heuristic atom-name matching.
            IGNORED for mixed hydrates (len(guest_atom_counts) > 1) — per-molecule
            detection via identify_guest_type is used instead.
        guest_atom_count: NEW (44.1) explicit atom count for custom (non-ch4/thf)
            guests. Threaded to count_guest_atoms so custom ethanol (9 atoms) is
            counted correctly instead of falling through the ch4/thf heuristic
            (which miscounts custom atoms -> IndexError). Ignored for ch4/thf/None.
        guest_atom_counts: NEW (45-14) full dict {mol_type: atom_count} from
            Candidate.metadata. When it has >1 entry (mixed hydrate), per-molecule
            type detection is used instead of the single guest_type. Fixes the
            mixed CH4+THF IndexError (count_guest_atoms(guest_type='ch4') returned
            5 for THF's 13 atoms, desyncing the index).
        guest_descriptors: NEW (45-14) list of GuestDescriptor objects from
            Candidate.metadata, used by identify_guest_type for exact atom_labels
            prefix matching (handles custom guests the heuristic cannot identify).
    
    Returns:
        Tuple of (water_framework_atom_indices, guest_atom_indices) as lists
    """
    water_indices = []
    guest_indices = []

    # Mixed hydrate: >1 entry in guest_atom_counts means per-molecule type
    # detection is REQUIRED (a single guest_type would miscount other types).
    is_mixed = guest_atom_counts is not None and len(guest_atom_counts) > 1

    i = 0
    n = len(atom_names)
    while i < n:
        # Check first atom of each molecule
        if i + atoms_per_mol <= n:
            first_atom = atom_names[i]
            # Water framework: first atom is OW (TIP4P water oxygen)
            if first_atom == "OW":
                water_indices.extend(range(i, i + atoms_per_mol))
                i += atoms_per_mol
            else:
                # This is a guest molecule (united-atom CH4 'Me', all-atom CH4 'C', etc.)
                # Guest can be 1 atom (Me), 5 atoms (CH4 all-atom), or more (THF)
                if is_mixed:
                    # Mixed hydrate: detect type per molecule, look up count from dict.
                    mol_type = identify_guest_type(atom_names, i, guest_descriptors)
                    if (mol_type is not None and guest_atom_counts
                            and mol_type in guest_atom_counts):
                        guest_atoms = guest_atom_counts[mol_type]
                    else:
                        # Unknown type: fall back to the heuristic count.
                        guest_atoms = count_guest_atoms(atom_names, i, guest_type=None)
                else:
                    guest_atoms = count_guest_atoms(
                        atom_names, i,
                        guest_type=guest_type, guest_atom_count=guest_atom_count,
                    )

                # SAFEGUARD: Check if the detected "guest" is actually a water molecule
                # that was misidentified due to counting errors
                if guest_atoms > 0:
                    # Check if any atoms in this range are OW (water oxygen)
                    # If so, this is NOT a guest - it's water
                    end_idx = min(i + guest_atoms, n)
                    has_ow = any(atom_names[j] == "OW" for j in range(i, end_idx))

                    if has_ow:
                        # This is actually a water molecule - add to water_indices
                        # and skip to the next OW to re-sync
                        water_indices.extend(range(i, end_idx))
                        i = end_idx
                    else:
                        # Legitimate guest - add to guest_indices.
                        # FIX (45-14): use end_idx (clamped) instead of i + guest_atoms
                        # to avoid out-of-bounds when the stride would exceed n.
                        # The previous `range(i, i + guest_atoms)` produced index n
                        # for an array of size n (off-by-one) when the miscounted
                        # walking index landed at n - atoms_per_mol + 1.
                        guest_indices.extend(range(i, end_idx))
                        i = end_idx
                else:
                    # No atoms detected - skip 1 to avoid infinite loop
                    i += 1
        else:
            # Not enough atoms for full molecule - treat as guest
            guest_indices.extend(range(i, n))
            i = n

    return water_indices, guest_indices


def _count_guest_molecules(
    atom_names: list[str],
    guest_indices: list[int],
    guest_type: str | None = None,
    guest_atom_count: int | None = None,
    guest_atom_counts: dict[str, int] | None = None,
    guest_descriptors: list | None = None,
) -> int:
    """Count the number of distinct guest molecules from guest atom indices.
    
    Args:
        atom_names: Full list of atom names from candidate
        guest_indices: Indices of guest atoms (from _detect_guest_atoms)
        guest_type: Explicit guest molecule type ("ch4" or "thf") threaded to
            count_guest_atoms. When None, falls back to heuristic. IGNORED for
            mixed hydrates (len(guest_atom_counts) > 1).
        guest_atom_count: NEW (44.1) explicit atom count for custom guests,
            threaded to count_guest_atoms so the per-molecule stride is correct.
        guest_atom_counts: NEW (45-14) full dict {mol_type: atom_count}. When it
            has >1 entry, per-molecule type detection is used (see
            _detect_guest_atoms docstring).
        guest_descriptors: NEW (45-14) list of GuestDescriptor objects for
            identify_guest_type exact-prefix matching.
    """
    if not guest_indices:
        return 0

    is_mixed = guest_atom_counts is not None and len(guest_atom_counts) > 1

    count = 0
    i = 0
    while i < len(guest_indices):
        atom_idx = guest_indices[i]
        if is_mixed:
            mol_type = identify_guest_type(atom_names, atom_idx, guest_descriptors)
            if (mol_type is not None and guest_atom_counts
                    and mol_type in guest_atom_counts):
                atoms_in_mol = guest_atom_counts[mol_type]
            else:
                atoms_in_mol = count_guest_atoms(atom_names, atom_idx, guest_type=None)
        else:
            atoms_in_mol = count_guest_atoms(
                atom_names, atom_idx,
                guest_type=guest_type, guest_atom_count=guest_atom_count,
            )
        count += 1
        i += atoms_in_mol

    return count


from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure, detect_atoms_per_molecule
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
        # Extract guest type from candidate metadata for explicit identification
        # (avoids fragile heuristic in count_guest_atoms)
        guest_type_counts = candidate.metadata.get("guest_type_counts", {})
        # QuickIce hydrates have a single guest type; extract it
        _guest_type = next(iter(guest_type_counts), None) if guest_type_counts else None

        # NEW (44.1): explicit atom count for custom guests (prevents IndexError).
        # to_candidate() populates "guest_atom_counts" as {mol_type: atom_count}
        # (44.1-02). For built-in ch4/thf this maps to 5/13 (ignored by
        # count_guest_atoms since guest_type is "ch4"/"thf"). For custom guests
        # (e.g. etoh_e2e=9) this short-circuits the ch4/thf heuristic so the
        # per-molecule stride is correct.
        guest_atom_counts = candidate.metadata.get("guest_atom_counts", {})
        _guest_atom_count = guest_atom_counts.get(_guest_type) if _guest_type else None

        # NEW (45-14): for MIXED hydrates (guest_type_counts has >1 entry, e.g.
        # CH4 in small cages + THF in large cages) a single guest_type cannot
        # represent every molecule — count_guest_atoms(guest_type='ch4') would
        # return 5 for THF's 13 atoms, desyncing the walking index and causing
        # an out-of-bounds IndexError. Pass the full guest_atom_counts dict +
        # guest_descriptors so _detect_guest_atoms / _count_guest_molecules can
        # detect each molecule's type via identify_guest_type and look up the
        # correct atom count. For single-guest hydrates the dict has 1 entry,
        # is_mixed is False, and the existing single-guest_type path is used
        # unchanged (backward compatible).
        _guest_descriptors = candidate.metadata.get("guest_descriptors", [])

        # Extract guest atoms from candidate positions
        water_indices, guest_indices = _detect_guest_atoms(
            candidate.atom_names, atoms_per_mol,
            guest_type=_guest_type, guest_atom_count=_guest_atom_count,
            guest_atom_counts=guest_atom_counts, guest_descriptors=_guest_descriptors,
        )
        
        if guest_indices:
            # Extract raw guest positions (1 unit cell, needs tiling later)
            raw_guest_positions = candidate.positions[guest_indices].copy()
            guest_atom_names = [candidate.atom_names[i] for i in guest_indices]
            
            # Store initial guest molecule count (will be updated after tiling)
            guest_nmolecules = _count_guest_molecules(
                candidate.atom_names, guest_indices,
                guest_type=_guest_type, guest_atom_count=_guest_atom_count,
                guest_atom_counts=guest_atom_counts, guest_descriptors=_guest_descriptors,
            )
            
            # For ice tiling, use ONLY water-framework atoms
            water_framework_positions = candidate.positions[water_indices]
            water_framework_atom_names = [candidate.atom_names[i] for i in water_indices]
    
    # ADJUST DIMENSIONS FOR PERIODICITY
    # Round box dimensions and ice thickness to multiples of ice unit cell
    # This ensures continuous periodic images without gaps at boundaries
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_ice_thickness, nz_ice = round_to_periodicity(config.ice_thickness, ice_cell_dims[2])
    
    # Adjust water thickness to multiples of water template cell
    # This prevents overwrapping that causes overlapping water molecules
    # CRITICAL: Water template cell is scaled by density, so we must calculate the scaled dimension
    from quickice.structure_generation.water_filler import (
        TEMPLATE_DENSITY_GCM3,
        load_water_template
    )
    
    # Get water template cell dimension
    _, _, water_template_box = load_water_template()
    water_template_cell = water_template_box[0]  # Assuming cubic template
    
    # Calculate water density and scaled cell dimension
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)
    scale = (TEMPLATE_DENSITY_GCM3 / target_water_density) ** (1.0 / 3.0)
    scaled_water_cell = water_template_cell * scale
    
    # CRITICAL FIX: Do NOT adjust box_x and box_y to water cell periodicity!
    # Box dimensions should be multiples of ICE cell dimensions only.
    # This ensures continuous periodic images for ice/hydrate framework.
    # Water layer can tile into any box dimensions (doesn't need perfect periodicity).
    #
    # Previous code adjusted box dimensions to multiples of BOTH ice and water cells,
    # which created a conflict because:
    # - Ice cells are non-cubic (e.g., 2.35×2.21×2.71 nm)
    # - Water template is cubic (1.87 nm)
    # This forced box dimensions to water cell periodicity, breaking ice PBC.
    # See: ice-hydrate-regression debug session for details.
    
    # Adjust water thickness to multiple of scaled cell
    adjusted_water_thickness, nz_water = round_to_periodicity(config.water_thickness, scaled_water_cell)

    # Track adjustments for reporting
    adjustments = []
    if abs(adjusted_box_x - config.box_x) > 0.001:
        adjustments.append(f"  box_x: {config.box_x:.3f} → {adjusted_box_x:.3f} nm ({nx} cells)")
    if abs(adjusted_box_y - config.box_y) > 0.001:
        adjustments.append(f"  box_y: {config.box_y:.3f} → {adjusted_box_y:.3f} nm ({ny} cells)")
    if abs(adjusted_ice_thickness - config.ice_thickness) > 0.001:
        adjustments.append(f"  ice_thickness: {config.ice_thickness:.3f} → {adjusted_ice_thickness:.3f} nm ({nz_ice} cells)")
    if abs(adjusted_water_thickness - config.water_thickness) > 0.001:
        adjustments.append(f"  water_thickness: {config.water_thickness:.3f} → {adjusted_water_thickness:.3f} nm ({nz_water} cells)")

    # Recalculate box_z to match adjusted ice and water thickness
    # box_z = 2 * ice_thickness + water_thickness
    adjusted_box_z = 2 * adjusted_ice_thickness + adjusted_water_thickness
    if abs(adjusted_box_z - config.box_z) > 0.001:
        adjustments.append(f"  box_z: {config.box_z:.3f} → {adjusted_box_z:.3f} nm (auto-adjusted)")

    # Box dimensions (using adjusted values)
    box_dims = np.array([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Tile ice for bottom layer: fill [adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]
    # For hydrate: tile only water-framework (guests extracted separately)
    # FIX: Use filter_molecules=False to preserve ice molecules that span PBC boundaries
    # This ensures continuous periodic images without gaps at Z=0 and Z=box_z
    bottom_ice_positions, bottom_ice_nmolecules = tile_structure(
        water_framework_positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=atoms_per_mol,  # Detected: 3 for ice, 4 for TIP4P/hydrate
        cell_matrix=cell_matrix,  # Triclinic-aware tiling
        filter_molecules=False  # Don't filter - keep molecules spanning PBC
    )

    # Tile ice for top layer: same target region, then shift Z
    # For hydrate: tile only water-framework (guests extracted separately)
    # FIX: Use filter_molecules=False to preserve ice molecules that span PBC boundaries
    # This ensures continuous periodic images without gaps at Z=0 and Z=box_z
    top_ice_positions, top_ice_nmolecules = tile_structure(
        water_framework_positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=atoms_per_mol,  # Detected: 3 for ice, 4 for TIP4P/hydrate
        cell_matrix=cell_matrix,  # Triclinic-aware tiling
        filter_molecules=False  # Don't filter - keep molecules spanning PBC
    )
    # Shift top layer to Z = [adjusted_ice_thickness + water_thickness, adjusted_box_z]
    top_ice_positions = top_ice_positions.copy()
    top_ice_positions[:, 2] += adjusted_ice_thickness + adjusted_water_thickness

    # PBC wrap: wrap molecules that span the boundary after shifting
    # After shift, atoms should be in [adjusted_ice_thickness + water_thickness, adjusted_box_z)
    # but tile_structure() allows atoms outside [0, target_region), so some may exceed box_z.
    # Wrap molecules as whole units to preserve molecular integrity.
    if len(top_ice_positions) > 0:
        n_molecules = len(top_ice_positions) // atoms_per_mol
        for mol_idx in range(n_molecules):
            start = mol_idx * atoms_per_mol
            end = start + atoms_per_mol
            mol_atoms = top_ice_positions[start:end]
            # Calculate center of mass Z
            com_z = mol_atoms[:, 2].mean()
            # If COM is outside [0, box_z), shift the entire molecule
            if com_z < 0:
                # Shift up by one box
                top_ice_positions[start:end, 2] += adjusted_box_z
            elif com_z >= adjusted_box_z:
                # Shift down by one box
                top_ice_positions[start:end, 2] -= adjusted_box_z

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

    # Fill water in middle region: [adjusted_box_x, adjusted_box_y, adjusted_water_thickness]
    # Water thickness is adjusted to water template cell periodicity to prevent overwrapping
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        np.array([adjusted_box_x, adjusted_box_y, adjusted_water_thickness]),
        target_density=target_water_density
    )

    # Shift water to Z = [adjusted_ice_thickness, adjusted_ice_thickness + adjusted_water_thickness]
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
        # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
        if len(trimmed_water_positions) % 4 != 0:
            raise ValueError(
                f"Water atom count {len(trimmed_water_positions)} is not a multiple of 4 "
                f"after ice-water overlap removal. Molecular integrity error."
            )
    else:
        trimmed_water_positions = water_positions

    # === HYDRATE FIX: Tile guests in ICE regions, NOT water region ===
    # Guests should be IN the hydrate (ice) layers, distributed in both bottom and top ice
    # Bottom ice: Z = [0, ice_thickness], Top ice: Z = [ice_thickness + water_thickness, box_z]
    processed_guest_positions = None
    processed_guest_atom_names = []
    original_guest_nmolecules = 0  # Default: no hydrate guests

    if is_hydrate and raw_guest_positions is not None and len(raw_guest_positions) > 0:
        # Store initial guest molecule count BEFORE tiling (for atom name expansion)
        original_guest_nmolecules = guest_nmolecules

        # Get extent of original guest structure (for tiling)
        guest_cell_dims = get_cell_extent(candidate.cell)

        # FIX: Tile guests SEPARATELY for bottom and top ice layers
        # This ensures proper spatial distribution matching the ice framework tiling
        ice_region_dims = np.array([
            adjusted_box_x,
            adjusted_box_y,
            adjusted_ice_thickness
        ])

        # Phase 45-14: MIXED hydrate (guest_type_counts has >1 entry, e.g.
        # CH4 in small cages + THF in large cages). tile_structure validates
        # len(positions) % atoms_per_molecule == 0 and does molecule-level PBC
        # wrapping, BOTH of which assume a SINGLE uniform atoms-per-molecule.
        # CH4 (5 atoms) + THF (13 atoms) = 184 atoms is divisible by neither
        # 5 nor 13, so a single tile_structure call would raise ValueError.
        # Fix: separate guests by type and tile each type with its own
        # atoms_per_molecule, then concatenate. The single-guest path
        # (is_mixed=False) keeps the existing single-tile behavior unchanged.
        is_mixed = (guest_atom_counts is not None and len(guest_atom_counts) > 1)

        if is_mixed:
            separated = separate_guests_by_type(
                raw_guest_positions, guest_atom_names,
                guest_atom_counts, _guest_descriptors,
            )
            all_bottom_parts = []
            all_top_parts = []
            all_bottom_names = []
            all_top_names = []
            bottom_guest_nmolecules = 0
            top_guest_nmolecules = 0

            for info in separated:
                apm = info["atoms_per_mol"]
                pat = info["atom_names_pattern"]
                src_pos = info["positions"]

                # Tile guests for BOTTOM ice layer (Z = [0, ice_thickness])
                # filter_molecules=False: GenIce2 outputs complete molecules
                # already positioned in cage locations; filtering would
                # remove guests that span PBC boundaries.
                bot_pos, bot_nmols = tile_structure(
                    src_pos, guest_cell_dims, ice_region_dims,
                    atoms_per_molecule=apm, cell_matrix=cell_matrix,
                    filter_molecules=False,
                )
                if len(bot_pos) > 0:
                    all_bottom_parts.append(bot_pos)
                    bottom_guest_nmolecules += bot_nmols
                    all_bottom_names.extend(pat * bot_nmols)

                # Tile guests for TOP ice layer, shift Z, wrap as whole molecules
                top_pos, top_nmols = tile_structure(
                    src_pos, guest_cell_dims, ice_region_dims,
                    atoms_per_molecule=apm, cell_matrix=cell_matrix,
                    filter_molecules=False,
                )
                if len(top_pos) > 0:
                    top_pos = top_pos.copy()
                    top_pos[:, 2] += adjusted_ice_thickness + adjusted_water_thickness
                    # Wrap each top-layer molecule as a unit to keep all
                    # atoms together after the Z shift.
                    n_top = len(top_pos) // apm
                    for mi in range(n_top):
                        s = mi * apm
                        e = s + apm
                        com_z = top_pos[s:e, 2].mean()
                        if com_z < 0:
                            top_pos[s:e, 2] += adjusted_box_z
                        elif com_z >= adjusted_box_z:
                            top_pos[s:e, 2] -= adjusted_box_z
                    all_top_parts.append(top_pos)
                    top_guest_nmolecules += top_nmols
                    all_top_names.extend(pat * top_nmols)

            # Combine bottom + top across all guest types
            bottom_guest_positions = (
                np.vstack(all_bottom_parts) if all_bottom_parts
                else np.zeros((0, 3), dtype=float)
            )
            top_guest_positions = (
                np.vstack(all_top_parts) if all_top_parts
                else np.zeros((0, 3), dtype=float)
            )

            all_guest_parts = []
            total_guest_nmolecules = 0
            if len(bottom_guest_positions) > 0:
                all_guest_parts.append(bottom_guest_positions)
                total_guest_nmolecules += bottom_guest_nmolecules
            if len(top_guest_positions) > 0:
                all_guest_parts.append(top_guest_positions)
                total_guest_nmolecules += top_guest_nmolecules
            if all_guest_parts:
                tilable_guest_positions = np.vstack(all_guest_parts)
                tiled_guest_nmolecules = total_guest_nmolecules
            else:
                tilable_guest_positions = np.zeros((0, 3), dtype=float)
                tiled_guest_nmolecules = 0

            processed_guest_positions = tilable_guest_positions
            # Atom names follow the same bottom-then-top order as positions.
            processed_guest_atom_names = all_bottom_names + all_top_names
            guest_nmolecules = tiled_guest_nmolecules
        else:
            # Single guest type: existing behavior (unchanged for regression safety).
            # Determine atoms per GUEST molecule (not water framework)
            # Guests can have different atom counts than water framework
            # Me = 1 atom, CH4 = 5 atoms, THF = 13+ atoms
            if raw_guest_positions is not None and len(raw_guest_positions) > 0:
                # Detect from first guest atom type
                if guest_atom_names[0] == "Me":
                    guest_atoms_per_mol = 1
                elif guest_atom_names[0] == "C":
                    # Could be CH4 (5 atoms) or CO2 (3 atoms) - detect from second atom
                    if len(guest_atom_names) >= 2 and guest_atom_names[1] == "O":
                        guest_atoms_per_mol = 3  # CO2
                    else:
                        guest_atoms_per_mol = 5  # CH4
                elif guest_atom_names[0] == "O":
                    # THF or similar - calculate atoms per guest molecule
                    # guest_atom_names contains all guest atoms, need to divide by number of molecules
                    if original_guest_nmolecules > 0:
                        guest_atoms_per_mol = len(guest_atom_names) // original_guest_nmolecules
                    else:
                        # Fallback: THF typically has 13 atoms
                        guest_atoms_per_mol = 13
                else:
                    guest_atoms_per_mol = 1  # Default
            else:
                guest_atoms_per_mol = 4  # Fallback

            # Tile guests for BOTTOM ice layer (Z = [0, ice_thickness])
            # FIX: Use filter_molecules=False for guests because GenIce2 outputs complete molecules
            # already positioned in cage locations. Filtering removes guests that span PBC boundaries.
            bottom_guest_positions, bottom_guest_nmolecules = tile_structure(
                raw_guest_positions,
                guest_cell_dims,
                ice_region_dims,
                atoms_per_molecule=guest_atoms_per_mol,
                cell_matrix=cell_matrix,
                filter_molecules=False  # Don't filter guests - they're already complete molecules
            )

            # Tile guests for TOP ice layer (same dimensions), then shift Z
            top_guest_positions, top_guest_nmolecules = tile_structure(
                raw_guest_positions,
                guest_cell_dims,
                ice_region_dims,
                atoms_per_molecule=guest_atoms_per_mol,
                cell_matrix=cell_matrix,
                filter_molecules=False  # Don't filter guests - they're already complete molecules
            )

            # Shift top guests to their actual position
            # Top ice starts at Z = adjusted_ice_thickness + adjusted_water_thickness
            if len(top_guest_positions) > 0:
                top_guest_positions = top_guest_positions.copy()
                top_guest_positions[:, 2] += adjusted_ice_thickness + adjusted_water_thickness

                # Wrap top guests as whole molecules after shifting
                # The shift can cause molecules near the boundary to span PBC
                # Wrap each molecule as a unit to keep all atoms together
                n_top_molecules = len(top_guest_positions) // guest_atoms_per_mol
                for mol_idx in range(n_top_molecules):
                    start = mol_idx * guest_atoms_per_mol
                    end = start + guest_atoms_per_mol
                    mol_atoms = top_guest_positions[start:end]
                    # Calculate center of mass Z
                    com_z = mol_atoms[:, 2].mean()
                    # If COM is outside [0, box_z), shift the entire molecule
                    if com_z < 0:
                        # Shift up by one box
                        top_guest_positions[start:end, 2] += adjusted_box_z
                    elif com_z >= adjusted_box_z:
                        # Shift down by one box
                        top_guest_positions[start:end, 2] -= adjusted_box_z

            # Combine bottom and top guests
            all_guest_parts = []
            total_guest_nmolecules = 0

            if len(bottom_guest_positions) > 0:
                all_guest_parts.append(bottom_guest_positions)
                total_guest_nmolecules += bottom_guest_nmolecules

            if len(top_guest_positions) > 0:
                all_guest_parts.append(top_guest_positions)
                total_guest_nmolecules += top_guest_nmolecules

            if all_guest_parts:
                tilable_guest_positions = np.vstack(all_guest_parts)
                tiled_guest_nmolecules = total_guest_nmolecules
            else:
                tilable_guest_positions = np.zeros((0, 3), dtype=float)
                tiled_guest_nmolecules = 0


            processed_guest_positions = tilable_guest_positions

            # FIX: Compute guest atom names based on ACTUAL tiled positions
            # Previous approach used tiling_factor which assumes tile_structure() returns
            # exactly (tiling_factor * original_guest_nmolecules) molecules.
            # But tile_structure() FILTERS molecules at boundaries (water_filler.py lines 488-500),
            # causing processed_guest_atom_names to be SHORTER than processed_guest_positions.
            # FIX: Use actual length of processed_guest_positions to compute atom names.
            if len(processed_guest_positions) > 0 and original_guest_nmolecules > 0:
                # Calculate atoms per guest molecule in the original structure
                atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules

                if atoms_per_guest > 0:
                    # Calculate actual number of guest molecules in tiled positions
                    actual_guest_nmolecules = len(processed_guest_positions) // atoms_per_guest

                    # Repeat the guest atom names pattern for each actual molecule
                    # Use only the first (atoms_per_guest) atoms from guest_atom_names
                    # to handle the case where guest_atom_names might have irregular length
                    guest_pattern = guest_atom_names[:atoms_per_guest]
                    processed_guest_atom_names = guest_pattern * actual_guest_nmolecules
                else:
                    processed_guest_atom_names = []
            else:
                processed_guest_atom_names = []

            # Update guest molecule count to reflect actual tiled count
            # Use actual count from positions, not tiled_guest_nmolecules (which may be filtered)
            if len(processed_guest_positions) > 0 and original_guest_nmolecules > 0:
                atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules
                guest_nmolecules = len(processed_guest_positions) // atoms_per_guest if atoms_per_guest > 0 else 0
            else:
                guest_nmolecules = 0

        # === GUEST-WATER OVERLAP FIX ===
        # Check for overlaps between water filler and guest molecules after guest tiling.
        # This catches cases where water molecules near boundaries overlap with guests in ice regions.
        # Issue: water filler near upper boundary (Z ~ 7.3 nm) overlaps with CH4 guests at top ice boundary (Z = 7.326 nm).
        # Solution: Detect overlaps with ALL guest atoms (not just C) and remove overlapping water molecules.
        if is_hydrate and len(trimmed_water_positions) > 0 and len(processed_guest_positions) > 0:
            water_o_positions = trimmed_water_positions[::4]  # Water OW atoms (every 4th atom)
            
            guest_overlap_indices = detect_overlaps(
                processed_guest_positions,  # All guest atoms
                water_o_positions,           # Water OW atoms
                box_dims,
                config.overlap_threshold
            )
            
            # Remove water molecules that overlap with guests
            if guest_overlap_indices:
                trimmed_water_positions, water_nmolecules = remove_overlapping_molecules(
                    trimmed_water_positions,
                    guest_overlap_indices,
                    atoms_per_molecule=4
                )
                # Filter atom names to match positions
                water_atom_names = filter_atom_names(
                    water_atom_names,
                    guest_overlap_indices,
                    atoms_per_molecule=4
                )
                # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
                if len(trimmed_water_positions) % 4 != 0:
                    raise ValueError(
                        f"Water atom count {len(trimmed_water_positions)} is not a multiple of 4 "
                        f"after guest-water overlap removal. Molecular integrity error."
                    )

    # === HYDRATE FIX: Combine all positions including guests ===
    # Order: ice FIRST, then water, then guests LAST
    # This ensures all SOL molecules (ice + water) are contiguous in GRO file,
    # matching GROMACS requirement that molecules of same type be grouped together.
    # Guest molecules come after all water molecules.
    all_parts = []
    all_names_parts = []
    
    if len(combined_ice_positions) > 0:
        all_parts.append(combined_ice_positions)
        all_names_parts.append(ice_atom_names)
    
    if len(trimmed_water_positions) > 0:
        all_parts.append(trimmed_water_positions)
        all_names_parts.append(water_atom_names)
    
    if processed_guest_positions is not None and len(processed_guest_positions) > 0:
        all_parts.append(processed_guest_positions)
        all_names_parts.append(processed_guest_atom_names)
    
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
        guest_nmolecules=guest_nmolecules,
        # Phase 45-15: propagate TYPE-LEVEL (tiling-invariant) guest metadata
        # so downstream ion/export can walk mixed-guest (CH4+THF) regions
        # per-molecule. candidate.metadata carries the base unit cell's
        # descriptors/atom-counts (type-level, unchanged by tiling).
        guest_descriptors=candidate.metadata.get("guest_descriptors", []),
        guest_atom_counts=candidate.metadata.get("guest_atom_counts", {}),
    )
