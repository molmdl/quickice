"""Molecule utility functions for atom counting and indexing.

This module provides consolidated utility functions for:
- Counting atoms in guest molecules (supports Me, CH4, THF, H2)

These functions were consolidated from duplicate implementations across:
- quickice/structure_generation/modes/pocket.py
- quickice/structure_generation/modes/slab.py
- quickice/structure_generation/modes/piece.py
- quickice/output/gromacs_writer.py
- quickice/structure_generation/hydrate_generator.py
- quickice/structure_generation/ion_inserter.py
"""

# Guest molecule atom counts — single source of truth for explicit guest_type lookup.
# These mirror the values in quickice.structure_generation.types.MOLECULE_TYPE_INFO.
CH4_ATOMS_PER_MOLECULE: int = 5   # All-atom methane: C + 4H
THF_ATOMS_PER_MOLECULE: int = 13  # Tetrahydrofuran: O + 2CA + 2CB + 8H


def count_guest_atoms(atom_names: list[str], start: int, guest_type: str | None = None) -> int:
    """Count atoms in a guest molecule starting at index.

    When guest_type is provided, returns the atom count directly without
    relying on heuristics. When guest_type is None, falls back to heuristic
    pattern matching on atom names.

    Supported guest types with explicit guest_type:
    - "ch4": 5 atoms (all-atom methane: C + 4H)
    - "thf": 13 atoms (tetrahydrofuran: O, CA, CA, CB, CB, H×8)

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

    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0

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

