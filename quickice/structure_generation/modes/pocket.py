"""Pocket mode: water cavity in ice matrix.

Creates a water-filled cavity inside an ice matrix at the box center.
Supports two cavity shapes: sphere and cubic.
Ice molecules inside the cavity are removed, water fills the cavity,
and overlapping water molecules at the boundary are removed.

For hydrate->interface conversion:
- Extracts guest molecules from hydrate candidate
- Places guests in the pocket region (center cavity)
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

    Mixed-guest hydrates (Phase 45-14): when ``guest_atom_counts`` has >1
    entry, per-molecule type detection via ``identify_guest_type`` is used
    instead of the single ``guest_type`` (which would miscount other types —
    e.g. guest_type='ch4' returns 5 for THF's 13 atoms → IndexError).
    
    Args:
        atom_names: List of atom names from candidate
        atoms_per_mol: Expected atoms per molecule (4 for TIP4P/hydrate)
        guest_type: Explicit guest molecule type ("ch4" or "thf"). When provided,
            bypasses heuristic detection in count_guest_atoms. IGNORED for
            mixed hydrates (len(guest_atom_counts) > 1).
        guest_atom_count: NEW (44.1) explicit atom count for custom guests.
        guest_atom_counts: NEW (45-14) full dict {mol_type: atom_count}. When
            it has >1 entry, per-molecule type detection is used.
        guest_descriptors: NEW (45-14) list of GuestDescriptor objects for
            identify_guest_type exact-prefix matching.
    """
    water_indices = []
    guest_indices = []

    is_mixed = guest_atom_counts is not None and len(guest_atom_counts) > 1

    i = 0
    n = len(atom_names)
    while i < n:
        if i + atoms_per_mol <= n:
            first_atom = atom_names[i]
            if first_atom == "OW":
                water_indices.extend(range(i, i + atoms_per_mol))
                i += atoms_per_mol
            else:
                if is_mixed:
                    mol_type = identify_guest_type(atom_names, i, guest_descriptors)
                    if (mol_type is not None and guest_atom_counts
                            and mol_type in guest_atom_counts):
                        guest_atoms = guest_atom_counts[mol_type]
                    else:
                        guest_atoms = count_guest_atoms(atom_names, i, guest_type=None)
                else:
                    guest_atoms = count_guest_atoms(
                        atom_names, i,
                        guest_type=guest_type, guest_atom_count=guest_atom_count,
                    )

                if guest_atoms > 0:
                    end_idx = min(i + guest_atoms, n)
                    has_ow = any(atom_names[j] == "OW" for j in range(i, end_idx))

                    if has_ow:
                        water_indices.extend(range(i, end_idx))
                        i = end_idx
                    else:
                        # FIX (45-14): use end_idx (clamped) to avoid OOB.
                        guest_indices.extend(range(i, end_idx))
                        i = end_idx
                else:
                    i += 1
        else:
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
        guest_type: Explicit guest molecule type. IGNORED for mixed hydrates.
        guest_atom_count: NEW (44.1) explicit atom count for custom guests.
        guest_atom_counts: NEW (45-14) full dict {mol_type: atom_count}.
        guest_descriptors: NEW (45-14) list of GuestDescriptor objects.
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
from quickice.structure_generation.errors import InterfaceGenerationError
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


def assemble_pocket(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble pocket interface structure: water cavity in ice matrix.

    Creates a cavity at the box center, removes ice molecules
    inside the cavity, fills the cavity with water, and removes overlapping
    water molecules at the ice-water boundary.

    Supports two cavity shapes:
    - sphere: spherical void with diameter = pocket_diameter
    - cubic: cube with side = pocket_diameter

    IMPORTANT: Box dimensions are adjusted to ensure continuous periodic images.
    The adjustments are reported in the InterfaceStructure.report field.

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with pocket_diameter and pocket_shape.

    Returns:
        InterfaceStructure with ice (outside cavity) + water (in cavity).

    Raises:
        InterfaceGenerationError: If pocket_shape is not valid or if generation fails.
    """
    # Get ice cell dimensions for tiling (bounding box extent)
    # Works for both orthogonal and triclinic cells
    ice_cell_dims = get_cell_extent(candidate.cell)
    
    # Store cell matrix for triclinic-aware tiling
    cell_matrix = candidate.cell

    # Detect atoms per molecule from candidate atom names
    # Handles both GenIce ice (3 atoms) and TIP4P/hydrate (4 atoms)
    atoms_per_mol = detect_atoms_per_molecule(candidate.atom_names)

    # === HYDRATE FIX: Extract guest molecules from hydrate candidates ===
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

        # NEW (45-14): for MIXED hydrates pass the full guest_atom_counts dict +
        # guest_descriptors so _detect_guest_atoms / _count_guest_molecules can
        # detect each molecule's type via identify_guest_type. Single-guest
        # hydrates keep the existing path (is_mixed=False, backward compatible).
        _guest_descriptors = candidate.metadata.get("guest_descriptors", [])

        # Extract guest atoms from candidate positions
        water_indices, guest_indices = _detect_guest_atoms(
            candidate.atom_names, atoms_per_mol,
            guest_type=_guest_type, guest_atom_count=_guest_atom_count,
            guest_atom_counts=guest_atom_counts, guest_descriptors=_guest_descriptors,
        )
        
        if guest_indices:
            raw_guest_positions = candidate.positions[guest_indices].copy()
            guest_atom_names = [candidate.atom_names[i] for i in guest_indices]
            guest_nmolecules = _count_guest_molecules(
                candidate.atom_names, guest_indices,
                guest_type=_guest_type, guest_atom_count=_guest_atom_count,
                guest_atom_counts=guest_atom_counts, guest_descriptors=_guest_descriptors,
            )
            
            # For tiling, use ONLY water-framework atoms
            water_framework_positions = candidate.positions[water_indices]
            water_framework_atom_names = [candidate.atom_names[i] for i in water_indices]

    # ADJUST DIMENSIONS FOR PERIODICITY
    # Round box dimensions to multiples of ice unit cell
    # This ensures continuous periodic images without gaps at boundaries
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_box_z, nz = round_to_periodicity(config.box_z, ice_cell_dims[2])

    # Track adjustments for reporting
    adjustments = []
    if abs(adjusted_box_x - config.box_x) > 0.001:
        adjustments.append(f"  box_x: {config.box_x:.3f} → {adjusted_box_x:.3f} nm ({nx} cells)")
    if abs(adjusted_box_y - config.box_y) > 0.001:
        adjustments.append(f"  box_y: {config.box_y:.3f} → {adjusted_box_y:.3f} nm ({ny} cells)")
    if abs(adjusted_box_z - config.box_z) > 0.001:
        adjustments.append(f"  box_z: {config.box_z:.3f} → {adjusted_box_z:.3f} nm ({nz} cells)")

    # Box dimensions (using adjusted values)
    box_dims = np.array([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Cavity center and radius
    center = box_dims / 2.0
    radius = config.pocket_diameter / 2.0

    # Tile ice to fill entire box (using adjusted dimensions)
    # For hydrate: tile only water-framework (guests extracted separately)
    ice_positions, ice_nmolecules = tile_structure(
        water_framework_positions,
        ice_cell_dims,
        box_dims,
        atoms_per_molecule=atoms_per_mol,  # Detected: 3 for ice, 4 for TIP4P/hydrate
        cell_matrix=cell_matrix  # Triclinic-aware tiling
    )

    if len(ice_positions) == 0:
        raise InterfaceGenerationError(
            "Ice tiling produced zero atoms. Check candidate structure and box dimensions.",
            mode="pocket"
        )

    # Build ice atom names dynamically based on detected atoms per molecule
    # GenIce ice: ["O", "H", "H"], TIP4P/hydrate: ["OW", "HW1", "HW2", "MW"]
    if atoms_per_mol == 4:
        ice_atom_names = ["OW", "HW1", "HW2", "MW"] * ice_nmolecules
    else:
        ice_atom_names = ["O", "H", "H"] * ice_nmolecules

    # Remove ice molecules inside the cavity (shape-dependent)
    # Ice O atoms: indices [0, atoms_per_mol, 2*atoms_per_mol, ...]
    ice_o_positions = ice_positions[::atoms_per_mol]
    
    # Calculate which ice molecules are inside the cavity based on shape
    if config.pocket_shape == "sphere":
        # Spherical cavity: distance from center < radius
        distances = np.linalg.norm(ice_o_positions - center, axis=1)
        ice_inside_cavity = set(np.where(distances < radius)[0])

    elif config.pocket_shape == "cubic":
        # Cubic cavity: |x - cx| < radius, |y - cy| < radius, |z - cz| < radius
        dx = np.abs(ice_o_positions[:, 0] - center[0])
        dy = np.abs(ice_o_positions[:, 1] - center[1])
        dz = np.abs(ice_o_positions[:, 2] - center[2])
        ice_inside_cavity = set(np.where((dx < radius) & (dy < radius) & (dz < radius))[0])

    else:
        raise InterfaceGenerationError(
            f"Unknown pocket shape: '{config.pocket_shape}'. "
            f"Valid shapes: sphere, cubic.",
            mode="pocket"
        )

    # Remove ice molecules inside cavity
    if ice_inside_cavity:
        ice_positions, ice_nmolecules = remove_overlapping_molecules(
            ice_positions,
            ice_inside_cavity,
            atoms_per_molecule=atoms_per_mol  # Detected: 3 for ice, 4 for TIP4P/hydrate
        )
        # Filter ice atom names to match positions (CRITICAL: must use same ice_inside_cavity)
        ice_atom_names = filter_atom_names(
            ice_atom_names,
            ice_inside_cavity,
            atoms_per_molecule=atoms_per_mol
        )

    # OPTIMIZATION: Fill only the bounding box of the cavity instead of entire box
    # For a sphere of radius r centered at (cx, cy, cz):
    #   - Bounding box: [cx-r, cx+r] x [cy-r, cy+r] x [cz-r, cz+r]
    #   - Dimensions: 2r x 2r x 2r
    # This reduces water generation from box volume to (2r)^3,
    # which is much smaller for large boxes with small pockets.
    # Example: 10nm box with 2nm radius pocket -> 1000nm³ reduced to 64nm³ (94% reduction)
    fill_dims = np.array([2 * radius, 2 * radius, 2 * radius])

    # Calculate water density from ice temperature/pressure
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)

    # Fill the bounding box with water (positions start at origin [0, 0, 0])
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        fill_dims,
        target_density=target_water_density
    )

    if len(water_positions) == 0:
        raise InterfaceGenerationError(
            "Water filling produced zero molecules. Check pocket dimensions.",
            mode="pocket"
        )

    # Translate water positions from [0, 2r] to [center-r, center+r]
    # This places the water molecules around the cavity center
    fill_origin = center - radius
    water_positions = water_positions + fill_origin

    # Remove water molecules OUTSIDE the cavity (keep only water IN cavity)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule from TIP4P)
    water_o_positions = water_positions[::4]
    
    # Calculate which water molecules are OUTSIDE the cavity based on shape
    if config.pocket_shape == "sphere":
        # Spherical cavity: distance from center >= radius -> outside
        water_distances = np.linalg.norm(water_o_positions - center, axis=1)
        water_outside = set(np.where(water_distances >= radius)[0])

    elif config.pocket_shape == "cubic":
        # Cubic cavity: outside if any coordinate exceeds half-size
        dx = np.abs(water_o_positions[:, 0] - center[0])
        dy = np.abs(water_o_positions[:, 1] - center[1])
        dz = np.abs(water_o_positions[:, 2] - center[2])
        water_outside = set(np.where((dx >= radius) | (dy >= radius) | (dz >= radius))[0])

    else:
        raise InterfaceGenerationError(
            f"Unknown pocket shape: '{config.pocket_shape}'.",
            mode="pocket"
        )

    # Remove water molecules outside cavity
    if water_outside:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            water_outside,
            atoms_per_molecule=4  # TIP4P: OW, HW1, HW2, MW
        )
        # Filter atom names to match positions (CRITICAL: must use same water_outside)
        water_atom_names = filter_atom_names(
            water_atom_names,
            water_outside,
            atoms_per_molecule=4
        )
        # Invariant: water atom count must be divisible by 4 (TIP4P has 4 atoms/molecule)
        if len(water_positions) % 4 != 0:
            raise ValueError(
                f"Water atom count {len(water_positions)} is not a multiple of 4 "
                f"after water-outside-cavity removal. Molecular integrity error."
            )
        if len(water_atom_names) != len(water_positions):
            raise ValueError(
                f"Atom name count {len(water_atom_names)} != position count {len(water_positions)} "
                f"after water-outside-cavity removal. Inconsistent data."
            )

    # === HYDRATE FIX: Tile and place guests in pocket region ===
    processed_guest_positions = None
    processed_guest_atom_names = []
    original_guest_nmolecules = 0  # Default: no hydrate guests
    
    if is_hydrate and raw_guest_positions is not None and len(raw_guest_positions) > 0:
        # Store initial guest molecule count BEFORE tiling
        original_guest_nmolecules = guest_nmolecules

        # Tile guests in pocket region
        pocket_dims = np.array([2 * radius, 2 * radius, 2 * radius])
        guest_cell_dims = get_cell_extent(candidate.cell)

        # FIX: Guests should be in ICE region, NOT in water cavity!
        # Tile guests in full box (to be with ICE), then remove ones inside cavity
        # Use full box dimensions (same as ice tiling)
        box_guest_dims = box_dims

        # Phase 45-14: MIXED hydrate (guest_type_counts has >1 entry). tile_structure
        # validates len(positions) % atoms_per_molecule == 0 and does molecule-level
        # PBC wrapping — both assume a SINGLE uniform atoms-per-molecule. CH4 (5) +
        # THF (13) = 184 atoms is divisible by neither, so a single tile_structure
        # call would raise ValueError. Fix: separate by type, tile each separately,
        # then remove per-type molecules inside the cavity and concatenate.
        is_mixed = (guest_atom_counts is not None and len(guest_atom_counts) > 1)

        if is_mixed:
            separated = separate_guests_by_type(
                raw_guest_positions, guest_atom_names,
                guest_atom_counts, _guest_descriptors,
            )
            all_kept_parts = []
            all_kept_names = []
            tiled_guest_nmolecules = 0

            for info in separated:
                apm = info["atoms_per_mol"]
                pat = info["atom_names_pattern"]
                src_pos = info["positions"]

                # FIX: Use filter_molecules=False — GenIce2 outputs complete molecules
                # already positioned in cage locations.
                type_pos, type_nmols = tile_structure(
                    src_pos, guest_cell_dims, box_guest_dims,
                    atoms_per_molecule=apm, cell_matrix=cell_matrix,
                    filter_molecules=False,
                )
                if len(type_pos) == 0:
                    continue

                # Remove guests inside cavity (keep ONLY guests in ice region).
                # Guest O atoms: every apm-th atom (first atom of each molecule).
                guest_o_idx = np.arange(0, len(type_pos), apm)
                guest_o_positions = type_pos[guest_o_idx]

                if config.pocket_shape == "sphere":
                    distances = np.linalg.norm(guest_o_positions - center, axis=1)
                    outside_mask = distances >= radius
                elif config.pocket_shape == "cubic":
                    dx = np.abs(guest_o_positions[:, 0] - center[0])
                    dy = np.abs(guest_o_positions[:, 1] - center[1])
                    dz = np.abs(guest_o_positions[:, 2] - center[2])
                    outside_mask = ~((dx < radius) & (dy < radius) & (dz < radius))
                else:
                    distances = np.linalg.norm(guest_o_positions - center, axis=1)
                    outside_mask = distances >= radius

                if not np.any(outside_mask):
                    continue

                keep_mols = np.where(outside_mask)[0]
                for mol_idx in keep_mols:
                    start = mol_idx * apm
                    end = start + apm
                    if end <= len(type_pos):
                        all_kept_parts.append(type_pos[start:end])
                kept_nmols = len(keep_mols)
                all_kept_names.extend(pat * kept_nmols)
                tiled_guest_nmolecules += kept_nmols

            if all_kept_parts:
                tilable_guest_positions = np.vstack(all_kept_parts)
            else:
                tilable_guest_positions = None
                tiled_guest_nmolecules = 0
            processed_guest_atom_names = all_kept_names
        else:
            # Single guest type: existing behavior (unchanged for regression safety).
            # Determine atoms per GUEST molecule (not water framework)
            # NEW (44.1): prefer the explicit guest_atom_count threaded from candidate
            # metadata (44.1-02) for custom guests whose first atom is not Me/C/O
            # (e.g. ethanol starts with "H" -> heuristic below defaults to 1, which
            # fragments multi-atom guests and miscounts molecules). Falls back to the
            # first-atom heuristic for built-in guests. Byte-identical for ch4 (5)
            # and thf (13) since the metadata carries the same values the heuristic
            # would produce.
            if _guest_atom_count is not None:
                guest_atoms_per_mol = _guest_atom_count
            elif guest_atom_names[0] == "Me":
                guest_atoms_per_mol = 1
            elif guest_atom_names[0] == "C":
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
                guest_atoms_per_mol = 1

            # FIX: Use filter_molecules=False for guests because GenIce2 outputs complete molecules
            # already positioned in cage locations. Filtering removes guests that span PBC boundaries.
            tilable_guest_positions, tiled_guest_nmolecules = tile_structure(
                raw_guest_positions,
                guest_cell_dims,
                box_guest_dims,
                atoms_per_molecule=guest_atoms_per_mol,
                cell_matrix=cell_matrix,
                filter_molecules=False  # Don't filter guests - they're already complete molecules
            )

            # Remove guests inside cavity (keep ONLY guests in ice region, outside cavity)
            if len(tilable_guest_positions) > 0 and config.pocket_diameter > 0:
                # Find guest O atoms (first atom of each guest molecule)
                if guest_atoms_per_mol > 0:
                    guest_o_idx = np.arange(0, len(tilable_guest_positions), guest_atoms_per_mol)
                    guest_o_positions = tilable_guest_positions[guest_o_idx]

                    # Calculate distances from center — shape-aware criterion
                    if config.pocket_shape == "sphere":
                        # Spherical cavity: Euclidean distance from center
                        distances = np.linalg.norm(guest_o_positions - center, axis=1)
                        outside_mask = distances >= radius
                    elif config.pocket_shape == "cubic":
                        # Cubic cavity: max of |dx|, |dy|, |dz| from center
                        # Guest is inside cubic cavity if ALL |dx|, |dy|, |dz| < radius
                        # Keep guests OUTSIDE cubic cavity (at least one |d| >= radius)
                        dx = np.abs(guest_o_positions[:, 0] - center[0])
                        dy = np.abs(guest_o_positions[:, 1] - center[1])
                        dz = np.abs(guest_o_positions[:, 2] - center[2])
                        outside_mask = ~((dx < radius) & (dy < radius) & (dz < radius))
                    else:
                        # Unknown shape should have been caught earlier, but handle defensively
                        distances = np.linalg.norm(guest_o_positions - center, axis=1)
                        outside_mask = distances >= radius

                    if not np.any(outside_mask):
                        # No guests outside cavity - tile more aggressively
                        tilable_guest_positions = None
                        tiled_guest_nmolecules = 0
                    else:
                        # Filter to keep only outside-cavity guests
                        # For each kept molecule, keep all its atoms
                        keep_mols = np.where(outside_mask)[0]
                        new_positions = []
                        for mol_idx in keep_mols:
                            start = mol_idx * guest_atoms_per_mol
                            end = start + guest_atoms_per_mol
                            if end <= len(tilable_guest_positions):
                                new_positions.append(tilable_guest_positions[start:end])

                        if new_positions:
                            tilable_guest_positions = np.vstack(new_positions)
                            tiled_guest_nmolecules = len(keep_mols)
                        else:
                            tilable_guest_positions = None
                            tiled_guest_nmolecules = 0

            # FIX: Compute guest atom names based on ACTUAL tiled positions.
            # Ported from slab.py:704-722 (fix-plan T-S1). Previous approach used
            # tiling_factor which assumes tile_structure() returns exactly
            # (tiling_factor * original_guest_nmolecules) molecules; deriving the
            # count from the actual positions length is robust and keeps pocket
            # consistent with slab.py. NOTE: pocket uses filter_molecules=False
            # (line 541) so tile_structure() does not filter here in the normal
            # single-guest path -- this is a consistency/latent fix, not an active
            # bug. Uses tilable_guest_positions (not processed_guest_positions)
            # because processed_guest_positions is assigned later (line 604) and
            # may be None; inside this guard tilable_guest_positions is non-None.
            if original_guest_nmolecules > 0 and tiled_guest_nmolecules > 0:
                atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules
                if atoms_per_guest > 0:
                    actual_guest_nmolecules = len(tilable_guest_positions) // atoms_per_guest
                    guest_pattern = guest_atom_names[:atoms_per_guest]
                    processed_guest_atom_names = guest_pattern * actual_guest_nmolecules
                else:
                    processed_guest_atom_names = []
            else:
                processed_guest_atom_names = []

        if tilable_guest_positions is not None and len(tilable_guest_positions) > 0:
            processed_guest_positions = tilable_guest_positions
        else:
            processed_guest_positions = None

        guest_nmolecules = tiled_guest_nmolecules

    # === GUEST-WATER OVERLAP FIX ===
    # Check for overlaps between water filler and guest molecules after guest tiling.
    # This catches cases where water molecules in the cavity overlap with guests in the ice region.
    # Issue: Water molecules near cavity boundary could overlap with guests positioned just outside cavity.
    # Solution: Detect overlaps with ALL guest atoms (not just first atom) and remove overlapping water molecules.
    if is_hydrate and len(water_positions) > 0 and processed_guest_positions is not None and len(processed_guest_positions) > 0:
        water_o_positions = water_positions[::4]  # Water OW atoms (every 4th atom)
        
        guest_overlap_indices = detect_overlaps(
            processed_guest_positions,  # All guest atoms
            water_o_positions,           # Water OW atoms
            box_dims,
            config.overlap_threshold
        )
        
        # Remove water molecules that overlap with guests
        if guest_overlap_indices:
            water_positions, water_nmolecules = remove_overlapping_molecules(
                water_positions,
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
            if len(water_positions) % 4 != 0:
                raise ValueError(
                    f"Water atom count {len(water_positions)} is not a multiple of 4 "
                    f"after guest-water overlap removal. Molecular integrity error."
                )
            if len(water_atom_names) != len(water_positions):
                raise ValueError(
                    f"Atom name count {len(water_atom_names)} != position count {len(water_positions)} "
                    f"after guest-water overlap removal. Inconsistent data."
                )

    # Detect overlaps between remaining ice and cavity water
    # Ice O atoms: indices [0, atoms_per_mol, 2*atoms_per_mol, ...] (3 or 4 per molecule)
    if len(ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = ice_positions[::atoms_per_mol]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules from cavity water (not ice)
    if overlapping_mol_indices:
        water_positions, water_nmolecules = remove_overlapping_molecules(
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
        if len(water_positions) % 4 != 0:
            raise ValueError(
                f"Water atom count {len(water_positions)} is not a multiple of 4 "
                f"after ice-water overlap removal. Molecular integrity error."
            )
        if len(water_atom_names) != len(water_positions):
            raise ValueError(
                f"Atom name count {len(water_atom_names)} != position count {len(water_positions)} "
                f"after ice-water overlap removal. Inconsistent data."
            )

# === HYDRATE FIX: Combine all positions including guests ===
    # Order: ice (outside cavity), then water (in cavity), then guests LAST (in cavity)
    # This ensures all SOL molecules (ice + water) are contiguous for GROMACS export.
    all_parts = []
    all_names_parts = []
    
    if len(ice_positions) > 0:
        all_parts.append(ice_positions)
        all_names_parts.append(ice_atom_names)
    
    if len(water_positions) > 0:
        all_parts.append(water_positions)
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
    ice_atom_count = len(ice_positions)
    guest_atom_count = len(processed_guest_positions) if processed_guest_positions is not None else 0
    water_atom_count = len(water_positions)

    # Build cell matrix (using adjusted dimensions)
    cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + guest_nmolecules + water_nmolecules
    
    # Include periodicity adjustments in report
    adjustment_report = ""
    if adjustments:
        adjustment_report = (
            f"\n\nPeriodicity adjustments (for continuous images):\n" +
            "\n".join(adjustments)
        )
    
    report = (
        f"Generated pocket interface structure\n"
        f"  Ice molecules: {ice_nmolecules}\n"
        f"  Guest molecules: {guest_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Cavity diameter: {config.pocket_diameter:.2f} nm\n"
        f"  Box: {adjusted_box_x:.2f} x {adjusted_box_y:.2f} x {adjusted_box_z:.2f} nm"
        f"{adjustment_report}"
    )

    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="pocket",
        report=report,
        guest_atom_count=guest_atom_count,
        guest_nmolecules=guest_nmolecules,
        # Phase 45-15: propagate TYPE-LEVEL (tiling-invariant) guest metadata
        # so downstream ion/export can walk mixed-guest (CH4+THF) regions
        # per-molecule. See slab.py for the rationale.
        guest_descriptors=candidate.metadata.get("guest_descriptors", []),
        guest_atom_counts=candidate.metadata.get("guest_atom_counts", {}),
    )
