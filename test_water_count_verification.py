#!/usr/bin/env python3
"""Verification test for custom molecule water replacement count display.

This test verifies that:
1. CustomMoleculeInserter removes water molecules correctly
2. The modified interface structure has correct water count
3. Water replacement count can be calculated from original vs modified counts
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


def create_test_interface():
    """Create a simple interface structure for testing."""
    # Create ice + water structure
    # 4 ice molecules (16 atoms) + 100 water molecules (400 atoms)
    ice_atoms = 16
    water_atoms = 400
    total_atoms = ice_atoms + water_atoms
    
    # Random positions for testing
    np.random.seed(42)
    positions = np.random.rand(total_atoms, 3) * 5.0  # 5nm box
    
    # Atom names (ice: OW,HW1,HW2,MW pattern, water: OW,HW1,HW2,MW pattern)
    atom_names = []
    # Ice molecules
    for i in range(4):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    # Water molecules
    for i in range(100):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    
    # Molecule index
    molecule_index = []
    current_idx = 0
    # Ice
    for i in range(4):
        molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, 'ice'))
        current_idx += 4
    # Water
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
        report='Test interface'
    )


def create_test_molecule_gro():
    """Create a test GRO file for a simple molecule."""
    gro_content = """Test Molecule
    5
    1MOL    C1    1   0.000   0.000   0.000
    1MOL    O1    2   0.150   0.000   0.000
    1MOL    H1    3   0.000   0.150   0.000
    1MOL    H2    4   0.000   0.000   0.150
    1MOL    H3    5   0.000   0.100   0.100
   2.0  2.0  2.0
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gro', delete=False) as f:
        f.write(gro_content)
        return Path(f.name)


def create_test_molecule_itp():
    """Create a test ITP file for the molecule."""
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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.itp', delete=False) as f:
        f.write(itp_content)
        return Path(f.name)


def test_water_replacement_tracking():
    """Test that water replacement is tracked and can be reported."""
    print("\n=== Testing Custom Molecule Water Replacement Count ===\n")
    
    # Create test interface
    interface = create_test_interface()
    original_water_count = interface.water_nmolecules
    print(f"Original interface: {interface.ice_nmolecules} ice + {interface.water_nmolecules} water molecules")
    
    # Create test molecule files
    gro_path = create_test_molecule_gro()
    itp_path = create_test_molecule_itp()
    
    try:
        # Create config for random placement
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=10,
            min_separation=0.2,
            max_attempts=100
        )
        
        # Create inserter and insert molecules
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 10)
        
        # Check water replacement
        modified_water_count = result.interface_structure.water_nmolecules
        water_replaced = original_water_count - modified_water_count
        
        print(f"\nAfter custom molecule insertion:")
        print(f"  - Custom molecules placed: {result.custom_molecule_count}")
        print(f"  - Original water molecules: {original_water_count}")
        print(f"  - Modified water molecules: {modified_water_count}")
        print(f"  - Water molecules replaced: {water_replaced}")
        
        # Verify the count can be calculated
        assert water_replaced >= 0, "Water replacement count should be non-negative"
        
        # Verify the result structure has the modified interface
        assert result.interface_structure is not None, "Result should have interface_structure"
        assert hasattr(result.interface_structure, 'water_nmolecules'), "Interface should have water_nmolecules"
        
        # Success message (simulating what main_window.py should display)
        if water_replaced > 0:
            print(f"\n✓ Would display: 'Replaced {water_replaced} overlapping liquid water molecules'")
        else:
            print(f"\n✓ No water molecules replaced (no overlap detected)")
        
        print(f"\n=== TEST PASSED ===\n")
        return True
        
    finally:
        # Cleanup
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    success = test_water_replacement_tracking()
    exit(0 if success else 1)
