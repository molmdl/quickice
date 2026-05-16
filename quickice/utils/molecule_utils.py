"""Molecule utility functions for atom counting and indexing.

This module provides consolidated utility functions for:
- Counting atoms in guest molecules (supports Me, CH4, THF, CO2, H2)

These functions were consolidated from duplicate implementations across:
- quickice/structure_generation/modes/pocket.py
- quickice/structure_generation/modes/slab.py
- quickice/structure_generation/modes/piece.py
- quickice/output/gromacs_writer.py
- quickice/structure_generation/hydrate_generator.py
- quickice/structure_generation/ion_inserter.py
"""


def count_guest_atoms(atom_names: list[str], start: int) -> int:
    """Count atoms in a guest molecule starting at index.

    Handles multiple guest types:
    - Me: 1 atom (united-atom methane)
    - C: 5 atoms (all-atom methane: C + 4H) - C-first format
    - H: 5 atoms (all-atom methane: H, H, H, H, C) - H-first format (GenIce2 output)
    - H: 2 atoms (H2 molecule)
    - THF: 13 atoms (starts with O or C)
    
    Args:
        atom_names: List of atom names in guest region
        start: Starting index within atom_names
    
    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0

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

    # THF: C5H8O = 14 atoms, but GenIce2 outputs 13 atoms (some versions)
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
        # Just carbon - might be CH4 or CO2, handled elsewhere

    # H2: two hydrogen atoms
    if first_atom == "H":
        # Check if next atom is also H (H2 molecule)
        if len(sample) >= 2 and sample[1] == 'H':
            return 2
        # Otherwise might be CH4 with H first - but we handled that above
        # Default: assume single H atom
        return 1

    # CO2: C and O atoms
    if first_atom == "C" and any(a == 'O' for a in sample[:3]):
        return 3  # C + O + O

    # Default: treat as 1 atom guest
    return 1

