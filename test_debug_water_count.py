#!/usr/bin/env python3
"""Debug test to investigate water replacement count not showing.

This test simulates the exact workflow:
1. Create interface structure
2. Create custom molecule config
3. Insert custom molecules
4. Check water replacement count
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


def test_workflow():
    """Test the exact workflow from main_window.py _on_custom_finished."""
    print("\n" + "="*60)
    print("DEBUG: Testing water replacement count workflow")
    print("="*60 + "\n")
    
    # Create test interface
    interface = create_test_interface()
    original_water_count = interface.water_nmolecules
    print(f"[1] Created interface: {interface.ice_nmolecules} ice + {interface.water_nmolecules} water")
    
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
        print(f"[2] Config: {config.molecule_count} molecules, min_separation={config.min_separation}")
        
        # Create inserter and insert molecules
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 10)
        print(f"[3] Inserted {result.custom_molecule_count} custom molecules")
        print(f"    Total atoms in result: {len(result.positions)}")
        
        # Now simulate the _on_custom_finished logic
        print("\n[4] Simulating _on_custom_finished logic:")
        
        # This is what main_window.py does:
        _current_interface_result = interface  # Simulates self._current_interface_result
        
        # Check what result has
        print(f"    result has interface_structure? {hasattr(result, 'interface_structure')}")
        if hasattr(result, 'interface_structure'):
            print(f"    result.interface_structure is None? {result.interface_structure is None}")
            if result.interface_structure is not None:
                print(f"    result.interface_structure.water_nmolecules: {result.interface_structure.water_nmolecules}")
        
        # Calculate water molecules replaced (exact code from main_window.py lines 1147-1152)
        if _current_interface_result is not None:
            print(f"\n    _current_interface_result.water_nmolecules: {_current_interface_result.water_nmolecules}")
            modified_water_count = result.interface_structure.water_nmolecules
            water_replaced = original_water_count - modified_water_count
            print(f"    Calculation: {original_water_count} - {modified_water_count} = {water_replaced}")
        else:
            water_replaced = 0
            print(f"    _current_interface_result is None, water_replaced = 0")
        
        # Log success message (line 1155-1158)
        print(f"\n[5] Would log: 'Custom molecule insertion complete: {result.custom_molecule_count} molecules, {len(result.positions)} total atoms (ice+water+custom)'")
        
        # Log water replacement count (line 1161-1164)
        if water_replaced > 0:
            print(f"[6] Would log: 'Replaced {water_replaced} overlapping liquid water molecules'")
        else:
            print(f"[6] Water replaced is 0 - NO MESSAGE WOULD BE SHOWN")
            print(f"    This is the issue!")
        
        print("\n" + "="*60)
        
    finally:
        # Cleanup
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


def test_zero_water_replacement():
    """Test case where NO water is replaced."""
    print("\n" + "="*60)
    print("DEBUG: Testing case with NO water replacement")
    print("="*60 + "\n")
    
    # Create test interface
    interface = create_test_interface()
    original_water_count = interface.water_nmolecules
    print(f"[1] Created interface: {interface.ice_nmolecules} ice + {interface.water_nmolecules} water")
    
    # Create test molecule files
    gro_path = create_test_molecule_gro()
    itp_path = create_test_molecule_itp()
    
    try:
        # Create config with VERY SMALL min_separation to avoid overlaps
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=1,  # Just 1 molecule
            min_separation=0.001,  # Very small separation
            max_attempts=100
        )
        print(f"[2] Config: {config.molecule_count} molecules, min_separation={config.min_separation} (very small)")
        
        # Create inserter and insert molecules
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 1)
        print(f"[3] Inserted {result.custom_molecule_count} custom molecules")
        
        # Check water replacement
        modified_water_count = result.interface_structure.water_nmolecules
        water_replaced = original_water_count - modified_water_count
        print(f"    Water replaced: {water_replaced}")
        
        if water_replaced == 0:
            print(f"\n[4] NO water replaced - message would NOT be shown")
            print(f"    This might be the user's scenario!")
        
        print("\n" + "="*60)
        
    finally:
        # Cleanup
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    test_workflow()
    test_zero_water_replacement()
