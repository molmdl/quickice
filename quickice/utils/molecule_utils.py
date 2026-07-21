"""Molecule utility functions for atom counting and indexing.

This module provides consolidated utility functions for:
- Counting atoms in guest molecules (supports Me, CH4, THF, H2)
- Identifying guest molecule types from atom names (mixed hydrates)
- Separating mixed guest atoms into per-type groups (mixed hydrates)

These functions were consolidated from duplicate implementations across:
- quickice/structure_generation/modes/pocket.py
- quickice/structure_generation/modes/slab.py
- quickice/structure_generation/modes/piece.py
- quickice/output/gromacs_writer.py
- quickice/structure_generation/hydrate_generator.py
- quickice/structure_generation/ion_inserter.py
"""

import numpy as np

# Guest molecule atom counts — single source of truth for explicit guest_type lookup.
# These mirror the values in quickice.structure_generation.types.MOLECULE_TYPE_INFO.
CH4_ATOMS_PER_MOLECULE: int = 5   # All-atom methane: C + 4H
THF_ATOMS_PER_MOLECULE: int = 13  # Tetrahydrofuran: O + 2CA + 2CB + 8H


def identify_guest_type(
    atom_names: list[str],
    start: int,
    guest_descriptors: list | None = None,
) -> str | None:
    """Identify the guest molecule type from atom names at ``start``.

    Used for MIXED-guest hydrates where multiple guest types coexist (e.g.
    CH4 in small cages + THF in large cages). For single-guest hydrates the
    caller already knows the type; this function is only needed when
    ``guest_type_counts`` has more than one entry and the per-molecule type
    must be detected from atom names.

    Detection order (first match wins):
    1. Exact prefix match against each ``GuestDescriptor.atom_labels`` —
       the most reliable path (metadata-driven, matches what GenIce2 emits).
    2. Heuristic type detection mirroring the count path in
       ``count_guest_atoms``: C-first or H-first with the 1C+4H pattern →
       ``"ch4"``; O-first → ``"thf"``. Robust for the two built-in guests
       QuickIce supports, and tolerant of GenIce2 atom reordering
       (H-first vs C-first methane).

    Args:
        atom_names: Full list of atom names from the candidate.
        start: Starting index of the molecule to identify.
        guest_descriptors: Optional list of ``GuestDescriptor`` objects
            (from ``Candidate.metadata["guest_descriptors"]``). Each carries
            ``mol_type``, ``atom_labels`` and ``atom_count`` for one guest
            type. When supplied, exact ``atom_labels`` prefix match is tried
            first (handles custom guests the heuristic cannot identify).

    Returns:
        The guest ``mol_type`` string (e.g. ``"ch4"``, ``"thf"``, custom
        slug) or ``None`` if the type cannot be determined.
    """
    if start >= len(atom_names):
        return None

    # 1. Exact prefix match against guest_descriptors' atom_labels.
    # This handles built-in AND custom guests uniformly when the
    # descriptor list is available (always populated by to_candidate()).
    if guest_descriptors:
        for desc in guest_descriptors:
            labels = list(getattr(desc, "atom_labels", []) or [])
            n = len(labels)
            if n == 0 or start + n > len(atom_names):
                continue
            if list(atom_names[start:start + n]) == labels:
                return getattr(desc, "mol_type", None)

    # 2. Heuristic type detection (mirrors count_guest_atoms logic).
    # Robust for the two built-in guests (ch4, thf) and tolerant of
    # GenIce2 atom reordering. Returns None for unknown patterns so the
    # caller can fall back to the heuristic count.
    sample = atom_names[start:min(start + 15, len(atom_names))]
    if not sample:
        return None
    first_atom = sample[0]

    # Built-in guests never start with water atom names.
    if first_atom in ("OW", "HW1", "HW2", "MW"):
        return None

    # CH4: C-first or H-first with the 1C + 4H pattern.
    if first_atom == "C" or (first_atom == "H" and len(sample) >= 5):
        c_count = sum(1 for a in sample if a == "C")
        h_count = sum(1 for a in sample if a == "H")
        if c_count >= 1 and h_count >= 4 and (c_count + h_count) >= 5:
            return "ch4"

    # THF: O-first (GenIce2 emits O, CA, CA, CB, CB, H×8).
    if first_atom == "O":
        return "thf"

    return None


def count_guest_atoms(
    atom_names: list[str],
    start: int,
    guest_type: str | None = None,
    guest_atom_count: int | None = None,
) -> int:
    """Count atoms in a guest molecule starting at index.

    When guest_type is provided, returns the atom count directly without
    relying on heuristics. When guest_type is None, falls back to heuristic
    pattern matching on atom names.

    Supported guest types with explicit guest_type:
    - "ch4": 5 atoms (all-atom methane: C + 4H)
    - "thf": 13 atoms (tetrahydrofuran: O, CA, CA, CB, CB, H×8)

    Custom guests (Phase 44.1): pass ``guest_atom_count`` explicitly so any
    non-builtin guest molecule (ethanol=9, etc.) is counted correctly instead
    of falling through to the ch4/thf heuristic, which miscounts custom atoms
    and causes an IndexError in interface generation (slab/pocket/piece tiling).

    Heuristic detection (guest_type=None) handles:
    - Me: 1 atom (united-atom methane)
    - C-first CH4: 5 atoms (C, H, H, H, H)
    - H-first CH4: 5 atoms (H, H, H, H, C — GenIce2 output)
    - THF: 13 atoms (starts with O, or C/CA/CB with O in sample)
    - H2: 2 atoms

    Args:
        atom_names: List of atom names in guest region
        start: Starting index within atom_names
        guest_type: Explicit guest molecule type ("ch4" or "thf").
            When provided, bypasses heuristic detection entirely.
            When None (default), uses heuristic atom-name pattern matching.
        guest_atom_count: Explicit atom count for a custom (non-ch4/thf/None)
            guest. Takes priority over the heuristic for custom guests only;
            ignored when guest_type is "ch4", "thf", or None so the built-in
            explicit path and the heuristic fallback stay byte-identical.

    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0

    # NEW (44.1): explicit atom count for custom guests (non-ch4/thf/None).
    # Takes priority over the ch4/thf heuristic. Prevents IndexError from
    # miscounting custom guest atoms in interface generation.
    if guest_atom_count is not None and guest_type not in ("ch4", "thf", None):
        return guest_atom_count

    # Explicit guest_type: return atom count directly, no heuristic needed
    if guest_type is not None:
        if guest_type == "ch4":
            return CH4_ATOMS_PER_MOLECULE
        elif guest_type == "thf":
            return THF_ATOMS_PER_MOLECULE
        # Unknown guest_type: fall through to heuristic as a safety net

    # --- HEURISTIC FALLBACK ---
    # This path is used when guest_type is None (unknown).
    # It correctly identifies CH4 and THF — the only guest molecules QuickIce
    # currently supports. If new guest types are added, this heuristic must be
    # updated, or callers should pass guest_type explicitly.
    #
    # WARNING: The heuristic assumes any C-starting molecule with an O atom in
    # the sample window is THF (13 atoms). This would misidentify CO2, methanol,
    # acetone, etc. as THF. Since QuickIce only supports CH4 and THF guests,
    # this is not a current bug, but would become one if new guest types are added.

    # Strategy: look at the next several atoms to determine molecule type
    # Check up to 15 atoms ahead to identify the pattern
    sample = atom_names[start:min(start + 15, len(atom_names))]

    if not sample:
        return 0

    first_atom = sample[0]

    if first_atom in ["OW", "HW1", "HW2", "MW"]:
        return 0

    if first_atom == "Me":
        return 1

    # All-atom methane: C + 4H = 5 atoms
    # GenIce2 may output as: H, H, H, H, C (H first) or C, H, H, H, H (C first)
    if first_atom == "C" or (first_atom == "H" and len(sample) >= 5):
        # Check if this looks like CH4
        # Count C and H atoms in the sample
        c_count = sum(1 for a in sample if a == 'C')
        h_count = sum(1 for a in sample if a == 'H')

        # CH4 has exactly 1 C and 4 H
        if c_count >= 1 and h_count >= 4 and (c_count + h_count) >= 5:
            # Return 5 atoms for CH4
            # Find where the 5-atom group ends
            count = 0
            c_found = 0
            h_found = 0
            for atom in sample:
                if atom == 'C' and c_found == 0:
                    c_found += 1
                    count += 1
                elif atom == 'H' and h_found < 4:
                    h_found += 1
                    count += 1
                if count >= 5:
                    break
            return max(count, 5)  # At least 5 for CH4

    # THF: C4H8O = 13 atoms
    # Atoms: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    # Note: Carbon atoms can be named C, CA, or CB
    if first_atom == "O":
        # THF starts with O and has 13 atoms
        return 13
    
    if first_atom in ["C", "CA", "CB"]:
        # Check if this looks like THF (has O in next few atoms)
        if start + 1 < len(atom_names):
            next_atoms = atom_names[start:start + 15]
            if 'O' in next_atoms:
                # THF has O, return 13
                return 13
        # Just carbon - might be CH4 or another type, handled elsewhere

    # H2: two hydrogen atoms
    if first_atom == "H":
        # Check if next atom is also H (H2 molecule)
        if len(sample) >= 2 and sample[1] == 'H':
            return 2
        # Otherwise might be CH4 with H first - but we handled that above
        # Default: assume single H atom
        return 1

    # Default: treat as 1 atom guest
    return 1


def separate_guests_by_type(
    guest_positions: "np.ndarray",
    guest_atom_names: list[str],
    guest_atom_counts: dict[str, int],
    guest_descriptors: list | None = None,
) -> list[dict]:
    """Separate mixed guest atoms into per-type groups.

    Walks ``guest_atom_names`` molecule-by-molecule (using
    ``identify_guest_type`` + ``guest_atom_counts`` to determine each
    molecule's stride) and groups atoms by ``mol_type``. Required for
    MIXED cage-occupancy hydrates (e.g. CH4 in small cages + THF in large
    cages) because ``tile_structure`` validates ``len(positions) %
    atoms_per_molecule == 0`` and does molecule-level PBC wrapping — both
    assume a SINGLE uniform atoms-per-molecule, which is violated when
    CH4 (5 atoms) and THF (13 atoms) coexist (184 total atoms is divisible
    by neither 5 nor 13).

    Callers tile each returned group SEPARATELY with its own
    ``atoms_per_molecule`` and concatenate the results.

    Args:
        guest_positions: (N, 3) array of ALL guest atom positions (from
            ``candidate.positions[guest_indices]``).
        guest_atom_names: Full list of guest atom names (from
            ``[candidate.atom_names[i] for i in guest_indices]``).
        guest_atom_counts: ``{mol_type: atom_count}`` dict from
            ``Candidate.metadata["guest_atom_counts"]``.
        guest_descriptors: List of ``GuestDescriptor`` objects from
            ``Candidate.metadata["guest_descriptors"]`` (used by
            ``identify_guest_type`` for exact atom_labels matching).

    Returns:
        List of dicts (one per guest type), each with keys:
            - ``mol_type``: guest type string (e.g. "ch4", "thf")
            - ``positions``: (N_type, 3) array of this type's atoms
            - ``atom_names``: full list of this type's atom names
            - ``atom_names_pattern``: one molecule's atom names (for
              replication after tiling)
            - ``nmolecules``: number of molecules of this type
            - ``atoms_per_mol``: atoms per molecule of this type
    """
    groups: dict[str, dict] = {}
    i = 0
    n = len(guest_atom_names)
    while i < n:
        mol_type = identify_guest_type(guest_atom_names, i, guest_descriptors)
        if mol_type is not None and mol_type in guest_atom_counts:
            atoms_per_mol = guest_atom_counts[mol_type]
        else:
            # Unknown type: fall back to the heuristic count.
            atoms_per_mol = count_guest_atoms(guest_atom_names, i, guest_type=None)

        if atoms_per_mol <= 0 or i + atoms_per_mol > n:
            # Cannot make progress — stop to avoid a silent infinite loop.
            break

        if mol_type is None:
            mol_type = "_unknown_{}".format(atoms_per_mol)

        if mol_type not in groups:
            groups[mol_type] = {
                "mol_type": mol_type,
                "positions": [],
                "atom_names": [],
                "atom_names_pattern": list(guest_atom_names[i:i + atoms_per_mol]),
                "nmolecules": 0,
                "atoms_per_mol": atoms_per_mol,
            }

        groups[mol_type]["positions"].append(
            guest_positions[i:i + atoms_per_mol]
        )
        groups[mol_type]["atom_names"].extend(
            guest_atom_names[i:i + atoms_per_mol]
        )
        groups[mol_type]["nmolecules"] += 1
        i += atoms_per_mol

    # Convert per-molecule position lists to stacked arrays.
    result = []
    for info in groups.values():
        if info["positions"]:
            info["positions"] = np.vstack(info["positions"])
        else:
            info["positions"] = np.zeros((0, 3), dtype=float)
        result.append(info)
    return result

