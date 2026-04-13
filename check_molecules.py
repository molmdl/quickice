#!/usr/bin/env python
"""Check if InterfaceStructure has ice molecules."""

import numpy as np

def parse_gro_header(filepath):
    """Parse GRO file header to check for ice vs water."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # First line is comment
    comment = lines[0].strip()
    
    # Second line is number of atoms
    n_atoms = int(lines[1].strip())
    
    # Check molecule types by looking at residue numbers
    # Ice molecules should be numbered 1 to ice_nmolecules
    # Water molecules should be numbered ice_nmolecules+1 to ice_nmolecules+water_nmolecules
    
    # Count distinct residue numbers
    residues = set()
    for i in range(2, min(2 + n_atoms, len(lines))):  # First 100 atoms
        line = lines[i]
        res_num = int(line[:5])
        residues.add(res_num)
    
    return {
        'comment': comment,
        'n_atoms': n_atoms,
        'residue_range': (min(residues) if residues else 0, max(residues) if residues else 0),
        'n_residues': len(residues)
    }

def main():
    files = [
        ("tmp/interface_pocket_err.gro", "Pocket Error"),
        ("tmp/interface_slab_err.gro", "Slab Error"),
        ("tmp/interface_slab.gro", "Slab (non-error)"),
    ]
    
    for filepath, name in files:
        info = parse_gro_header(filepath)
        print(f"\n{name}:")
        print(f"  Comment: {info['comment']}")
        print(f"  Atoms: {info['n_atoms']}")
        print(f"  Residue range: {info['residue_range'][0]} to {info['residue_range'][1]}")
        print(f"  Distinct residues: {info['n_residues']}")
        
        # If n_atoms / 4 = n_residues, all molecules are water (4 atoms per molecule)
        # If n_atoms / 4 > n_residues, there might be ice + water
        
        molecules_from_atoms = info['n_atoms'] // 4
        print(f"  Molecules (from atoms/4): {molecules_from_atoms}")
        
        if molecules_from_atoms == info['n_residues']:
            print(f"  → All molecules are 4-atom (water only, no ice!)")
        else:
            print(f"  → Has both ice (3-atom) and water (4-atom)")


if __name__ == "__main__":
    main()