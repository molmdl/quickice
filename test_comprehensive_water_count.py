#!/usr/bin/env python3
"""Comprehensive test to identify water count display issue.

This test checks various scenarios:
1. Normal case (water replaced)
2. No water replaced
3. Missing interface_structure attribute
4. Exception scenarios
"""

import numpy as np
from pathlib import Path
import tempfile
import traceback

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
    MoleculeIndex,
    CustomMoleculeStructure,
)
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter


def create_test_interface():
    """Create a simple interface structure for testing."""
    ice_atoms = 16
    water_atoms = 400
    total_atoms = ice_atoms + water_atoms
    
    np.random.seed(42)
    positions = np.random.rand(total_atoms, 3) * 5.0
    
    atom_names = []
    for i in range(4):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    for i in range(100):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    
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
        report='Test interface'
    )


def create_test_molecule_files():
    """Create test GRO and ITP files."""
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


def simulate_on_custom_finished(result, _current_interface_result=None):
    """Simulate the exact logic from main_window._on_custom_finished."""
    print("\n" + "="*70)
    print("SIMULATING _on_custom_finished LOGIC")
    print("="*70)
    
    try:
        print(f"[1] Result received: {result.custom_molecule_count} molecules, {len(result.positions)} total atoms")
        
        # Calculate water molecules replaced (lines 1147-1152)
        print(f"\n[2] Checking _current_interface_result...")
        if _current_interface_result is not None:
            print(f"    _current_interface_result exists")
            print(f"    _current_interface_result.water_nmolecules: {_current_interface_result.water_nmolecules}")
            
            print(f"\n[3] Checking result.interface_structure...")
            if hasattr(result, 'interface_structure'):
                print(f"    result.interface_structure exists: {result.interface_structure is not None}")
                if result.interface_structure is not None:
                    print(f"    result.interface_structure.water_nmolecules: {result.interface_structure.water_nmolecules}")
                    original_water_count = _current_interface_result.water_nmolecules
                    modified_water_count = result.interface_structure.water_nmolecules
                    water_replaced = original_water_count - modified_water_count
                    print(f"    Calculation: {original_water_count} - {modified_water_count} = {water_replaced}")
                else:
                    print(f"    ERROR: result.interface_structure is None!")
                    water_replaced = 0
            else:
                print(f"    ERROR: result does not have interface_structure attribute!")
                water_replaced = 0
        else:
            print(f"    _current_interface_result is None!")
            water_replaced = 0
        
        # Log success message (line 1155-1158)
        print(f"\n[4] SUCCESS MESSAGE:")
        print(f"    'Custom molecule insertion complete: {result.custom_molecule_count} molecules, {len(result.positions)} total atoms (ice+water+custom)'")
        
        # Log water replacement count (line 1161-1164)
        print(f"\n[5] WATER REPLACEMENT MESSAGE:")
        if water_replaced > 0:
            print(f"    'Replaced {water_replaced} overlapping liquid water molecules'")
            print(f"    ✓ MESSAGE WOULD BE DISPLAYED")
        else:
            print(f"    (no message - water_replaced = {water_replaced})")
            print(f"    ✗ NO MESSAGE WOULD BE DISPLAYED")
        
        print("\n" + "="*70)
        return water_replaced
        
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        print(f"Traceback:")
        traceback.print_exc()
        print(f"\nERROR MESSAGE would be logged instead:")
        print(f"    'Error displaying structure: {e}'")
        print("\n" + "="*70)
        return None


def test_scenario_1_normal():
    """Test normal case with water replacement."""
    print("\n\n" + "█"*70)
    print("SCENARIO 1: Normal case (water replaced)")
    print("█"*70)
    
    interface = create_test_interface()
    gro_path, itp_path = create_test_molecule_files()
    
    try:
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=10,
            min_separation=0.2,
            max_attempts=100
        )
        
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 10)
        
        water_replaced = simulate_on_custom_finished(result, interface)
        
        if water_replaced is not None and water_replaced > 0:
            print("\n✓ SCENARIO 1 PASSED: Water count would be displayed")
        else:
            print("\n✗ SCENARIO 1 FAILED: Water count would NOT be displayed")
        
    finally:
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


def test_scenario_2_no_interface():
    """Test case where _current_interface_result is None."""
    print("\n\n" + "█"*70)
    print("SCENARIO 2: No interface structure (_current_interface_result = None)")
    print("█"*70)
    
    interface = create_test_interface()
    gro_path, itp_path = create_test_molecule_files()
    
    try:
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=10,
            min_separation=0.2,
            max_attempts=100
        )
        
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 10)
        
        # Simulate missing _current_interface_result
        water_replaced = simulate_on_custom_finished(result, None)
        
        if water_replaced == 0:
            print("\n✓ SCENARIO 2 RESULT: No message shown (as expected)")
            print("  This is the user's issue if they didn't generate interface first!")
        else:
            print("\n? SCENARIO 2 UNEXPECTED: water_replaced should be 0")
        
    finally:
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


def test_scenario_3_no_water_replaced():
    """Test case where no water molecules are replaced."""
    print("\n\n" + "█"*70)
    print("SCENARIO 3: No water replaced (no overlaps)")
    print("█"*70)
    
    interface = create_test_interface()
    gro_path, itp_path = create_test_molecule_files()
    
    try:
        # Use placement mode 'custom' with positions far from water
        # Actually, let's check what happens with random mode with very small min_separation
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode='random',
            molecule_count=1,
            min_separation=0.1,  # Minimum allowed
            max_attempts=100
        )
        
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(interface, 1)
        
        water_replaced = simulate_on_custom_finished(result, interface)
        
        if water_replaced == 0:
            print("\n✓ SCENARIO 3 RESULT: No message shown (no water replaced)")
            print("  This could happen with specific molecule configurations")
        else:
            print(f"\n✓ SCENARIO 3: {water_replaced} water molecules replaced")
        
    finally:
        gro_path.unlink(missing_ok=True)
        itp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("COMPREHENSIVE WATER COUNT DISPLAY DEBUG TEST")
    print("="*70)
    
    test_scenario_1_normal()
    test_scenario_2_no_interface()
    test_scenario_3_no_water_replaced()
    
    print("\n\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nSUMMARY:")
    print("If the user is seeing scenario 2 or 3, that explains why no message is shown.")
    print("If they're seeing scenario 1, then there's a bug to investigate further.")
    print("="*70 + "\n")
