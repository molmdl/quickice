#!/usr/bin/env python3
"""Debug test to understand why water replacement might not be happening.

This test simulates the exact workflow:
1. Create interface with liquid water
2. Insert custom molecules in random mode
3. Check water replacement count
"""

import numpy as np
from pathlib import Path
import tempfile

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
    MoleculeIndex,
)
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter


def create_interface_with_liquid_water():
    """Create an interface with ice and liquid water regions."""
    # Create a simple interface with ice and water
    ice_atoms = 16  # 4 ice molecules (4 atoms each for TIP4P)
    water_atoms = 400  # 100 water molecules (4 atoms each for TIP4P)
    
    np.random.seed(42)
    
    # Create positions: ice at bottom, water on top
    ice_positions = np.random.rand(ice_atoms, 3) * 5.0
    ice_positions[:, 2] = ice_positions[:, 2] * 0.5  # Ice in lower half (z < 2.5 nm)
    
    water_positions = np.random.rand(water_atoms, 3) * 5.0
    water_positions[:, 2] = 2.5 + water_positions[:, 2] * 0.5  # Water in upper half (z > 2.5 nm)
    
    positions = np.vstack([ice_positions, water_positions])
    
    # Create atom names
    atom_names = []
    for i in range(4):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])  # Ice
    for i in range(100):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])  # Water
    
    # Create molecule_index
    molecule_index = []
    current_idx = 0
    for i in range(4):
        molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, 'ice'))
        current_idx += 4
    for i in range(100):
        molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, 'water'))
        current_idx += 4
    
    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 5.0,
        ice_atom_count=ice_atoms,
        water_atom_count=water_atoms,
        guest_atom_count=0,
        ice_nmolecules=4,
        water_nmolecules=100,
        molecule_index=molecule_index,
        mode='slab',
        report='Test interface with liquid water'
    )


def create_test_molecule_files():
    """Create test GRO and ITP files for a simple molecule."""
    gro_content = """Test Molecule
    5
    1MOL    C1    1   0.000   0.000   0.000
    1MOL    O1    2   0.150   0.000   0.000
    1MOL    H1    3   0.000   0.150   0.000
    1MOL    H2    4   0.000   0.000   0.150
    1MOL    H3    5   0.000   0.100   0.100
   2.0  2.0  2.0
"""
    gro_path = Path(tempfile.mktemp(suffix='.gro'))
    with open(gro_path, 'w') as f:
        f.write(gro_content)
    
    itp_content = """[ moleculetype ]
; Name  nrexcl
MOL       3

[ atoms ]
;   nr  type  resnr residue  atom  cgnr  charge  mass
    1   CT      1    MOL    C1    1   0.00  12.01
    2   OH      1    MOL    O1    2  -0.50  16.00
    3   HO      1    MOL    H1    3   0.50   1.008
    4   HO      1    MOL    H2    4   0.50   1.008
    5   HO      1    MOL    H3    5   0.50   1.008

[ bonds ]
;  ai    aj funct
    1     2     1
    1     3     1
    1     4     1
    1     5     1
"""
    itp_path = Path(tempfile.mktemp(suffix='.itp'))
    with open(itp_path, 'w') as f:
        f.write(itp_content)
    
    return gro_path, itp_path


def test_water_replacement():
    """Test water replacement in random mode."""
    print("\n" + "="*70)
    print("WATER REPLACEMENT DEBUG TEST")
    print("="*70)
    
    # Create interface with liquid water
    print("\n[1] Creating interface with liquid water...")
    interface = create_interface_with_liquid_water()
    print(f"    Ice: {interface.ice_nmolecules} molecules ({interface.ice_atom_count} atoms)")
    print(f"    Water: {interface.water_nmolecules} molecules ({interface.water_atom_count} atoms)")
    print(f"    Liquid region z-range: {interface.positions[interface.ice_atom_count:, 2].min():.2f} - {interface.positions[interface.ice_atom_count:, 2].max():.2f} nm")
    
    # Create test molecule files
    print("\n[2] Creating test molecule files...")
    gro_path, itp_path = create_test_molecule_files()
    print(f"    GRO: {gro_path}")
    print(f"    ITP: {itp_path}")
    
    try:
        # Configure custom molecule insertion
        print("\n[3] Configuring custom molecule insertion...")
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=10,
            min_separation=0.3  # Default
        )
        print(f"    Molecules to insert: {config.molecule_count}")
        print(f"    Min separation: {config.min_separation} nm")
        
        # Insert molecules
        print("\n[4] Inserting custom molecules...")
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, config.molecule_count)
        
        # Check results
        print("\n[5] Checking results...")
        print(f"    Custom molecules inserted: {result.custom_molecule_count}")
        print(f"    Total atoms: {len(result.positions)}")
        print(f"    Result has interface_structure: {hasattr(result, 'interface_structure')}")
        
        if hasattr(result, 'interface_structure') and result.interface_structure is not None:
            print(f"    Interface structure water_nmolecules: {result.interface_structure.water_nmolecules}")
            
            # Calculate water replacement
            original_water = interface.water_nmolecules
            modified_water = result.interface_structure.water_nmolecules
            water_replaced = original_water - modified_water
            
            print("\n[6] Water replacement calculation:")
            print(f"    Original water molecules: {original_water}")
            print(f"    Modified water molecules: {modified_water}")
            print(f"    Water molecules replaced: {water_replaced}")
            
            if water_replaced > 0:
                print(f"\n    ✓ SUCCESS: {water_replaced} water molecules replaced!")
            else:
                print(f"\n    ✗ ISSUE: No water molecules replaced!")
                print(f"    This might indicate a problem with overlap detection or molecule placement")
        else:
            print("    ✗ ERROR: No interface_structure in result!")
    
    finally:
        # Cleanup
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)
    
    print("\n" + "="*70)


if __name__ == '__main__':
    test_water_replacement()
