"""Molecule utility functions for atom counting and indexing.

This module provides consolidated utility functions for:
- Counting atoms in guest molecules (supports Me, CH4, THF, CO2, H2)
- Building molecule indices from structure data

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

    # United-atom methane (Me) - single carbon
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


def build_molecule_index(atom_names: list[str], residue_names: list[str] | None = None) -> list:
    """Build molecule index from atom and residue names.
    
    Groups atoms into molecules based on residue boundaries and atom patterns.
    This is a general-purpose function that can be used for:
    - Hydrate structures with guests (CH4, THF)
    - Interface structures (ice + water)
    - Ion structures (ice + water + ions)
    
    Args:
        atom_names: List of atom names
        residue_names: List of residue names (optional, used for guest identification)
    
    Returns:
        List of MoleculeIndex objects with start_idx, count, and mol_type
    """
    from quickice.structure_generation.types import MoleculeIndex
    
    if not atom_names:
        return []
    
    molecule_index = []
    i = 0
    
    # Default empty residue_names if not provided
    if residue_names is None:
        residue_names = [""] * len(atom_names)
    
    while i < len(atom_names):
        atom = atom_names[i]
        residue = residue_names[i] if i < len(residue_names) else ""
        
        # Check for guest molecules (CH4, THF) by residue name
        if residue in ["CH4", "THF", "CO2", "H2"]:
            # Count atoms in this guest molecule
            guest_count = count_guest_atoms(atom_names, i)
            molecule_index.append(MoleculeIndex(i, guest_count, residue.lower()))
            i += guest_count
            continue
        
        # Check for water (TIP4P format: OW, HW1, HW2, MW)
        if atom in ["OW", "O"] and i + 3 < len(atom_names):
            # Check if this is TIP4P (OW, HW1, HW2, MW) or 3-site (O, H, H)
            if atom_names[i+1] in ["HW1", "H"] and atom_names[i+2] in ["HW2", "H"]:
                if i + 3 < len(atom_names) and atom_names[i+3] == "MW":
                    # TIP4P water (4 atoms)
                    molecule_index.append(MoleculeIndex(i, 4, "water"))
                    i += 4
                else:
                    # 3-site water (3 atoms)
                    molecule_index.append(MoleculeIndex(i, 3, "water"))
                    i += 3
                continue
        
        # Check for ions
        if atom in ["NA", "NA+"]:
            molecule_index.append(MoleculeIndex(i, 1, "na"))
            i += 1
            continue
        
        if atom in ["CL", "CL-"]:
            molecule_index.append(MoleculeIndex(i, 1, "cl"))
            i += 1
            continue
        
        # Default: treat as single atom
        molecule_index.append(MoleculeIndex(i, 1, "unknown"))
        i += 1
    
    return molecule_index
