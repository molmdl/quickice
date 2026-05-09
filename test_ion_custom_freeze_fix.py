#!/usr/bin/env python
"""Test to verify ion insertion after custom molecule insertion works correctly.

This test reproduces the freeze bug:
1. Create interface structure
2. Insert custom molecules using random mode
3. Insert ions using the modified interface structure

The bug was in molecule_index calculation in CustomMoleculeInserter:
- Used ice_atom_count // 3 instead of ice_nmolecules
- Used MoleculeIndex(current_idx, current_idx + 4, "ice") instead of MoleculeIndex(start_idx=current_idx, count=4, mol_type="ice")

This caused molecule_index misalignment, leading to freeze when ion_inserter tried to access water molecules.
"""

import numpy as np
from pathlib import Path
import tempfile

from quickice.structure_generation.types import (
    InterfaceStructure,
    CustomMoleculeConfig,
    MoleculeIndex,
)
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.ion_inserter import IonInserter, insert_ions


def create_test_interface():
    """Create a test interface structure with ice + water."""
    # Create a simple interface with 10 ice molecules (40 atoms for TIP4P-ICE) and 20 water molecules
    ice_nmolecules = 10
    water_nmolecules = 20
    
    # Ice: 4 atoms per molecule (OW, HW1, HW2, MW)
    ice_atoms_per_mol = 4
    ice_atom_count = ice_nmolecules * ice_atoms_per_mol
    
    # Water: 4 atoms per molecule (TIP4P)
    water_atoms_per_mol = 4
    water_atom_count = water_nmolecules * water_atoms_per_mol
    
    # Total atoms
    total_atoms = ice_atom_count + water_atom_count
    
    # Create positions
    positions = np.random.rand(total_atoms, 3) * 5.0  # 5 nm box
    
    # Create atom names
    atom_names = []
    for _ in range(ice_nmolecules):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    for _ in range(water_nmolecules):
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    
    # Create molecule_index
    molecule_index = []
    current_idx = 0
    
    # Ice molecules
    for _ in range(ice_nmolecules):
        molecule_index.append(MoleculeIndex(
            start_idx=current_idx,
            count=ice_atoms_per_mol,
            mol_type="ice"
        ))
        current_idx += ice_atoms_per_mol
    
    # Water molecules
    for _ in range(water_nmolecules):
        molecule_index.append(MoleculeIndex(
            start_idx=current_idx,
            count=water_atoms_per_mol,
            mol_type="water"
        ))
        current_idx += water_atoms_per_mol
    
    # Create cell
    cell = np.eye(3) * 5.0  # 5 nm cubic box
    
    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="slab",
        report="Test interface structure",
        molecule_index=molecule_index
    )


def test_ion_insertion_after_custom_molecules():
    """Test that ion insertion works after custom molecule insertion."""
    print("\n" + "="*60)
    print("Testing Ion Insertion After Custom Molecule Insertion")
    print("="*60)
    
    # 1. Create interface structure
    print("\n1. Creating interface structure...")
    interface = create_test_interface()
    print(f"   ✓ Interface created: {interface.ice_nmolecules} ice molecules ({interface.ice_atom_count} atoms)")
    print(f"   ✓                     {interface.water_nmolecules} water molecules ({interface.water_atom_count} atoms)")
    
    # 2. Create custom molecule GRO/ITP files
    print("\n2. Creating custom molecule template...")
    with tempfile.TemporaryDirectory() as tmpdir:
        gro_path = Path(tmpdir) / "custom.gro"
        itp_path = Path(tmpdir) / "custom.itp"
        
        # Create simple custom molecule GRO file (methane-like: 1 carbon)
        # GRO format: exact column alignment needed
        with open(gro_path, 'w') as f:
            f.write("Custom molecule\n")
            f.write("1\n")
            # Format: resnum(5)resname(5)atomname(5)atomnum(5)x(8)y(8)z(8)
            # Each field is exactly 5 characters, left-padded for numbers, left-aligned for names
            f.write("    1CUSTM    C    1   0.000   0.000   0.000\n")
            f.write("   1.000   1.000   1.000\n")
        
        # Create ITP file
        with open(itp_path, 'w') as f:
            f.write("[ moleculetype ]\n")
            f.write("; Name      nrexcl\n")
            f.write("CUSTOM      3\n\n")
            f.write("[ atoms ]\n")
            f.write("; nr  type  resnr  residue  atom  cgnr  charge  mass\n")
            f.write("   1   C      1    CUSTOM    C    1   0.0  12.01\n")
        
        # 3. Configure and insert custom molecules
        print("\n3. Inserting custom molecules (random mode)...")
        config = CustomMoleculeConfig(
            placement_mode="random",
            molecule_count=5,
            gro_path=gro_path,
            itp_path=itp_path,
            min_separation=0.3,
            max_attempts=100
        )
        
        inserter = CustomMoleculeInserter(config)
        custom_structure = inserter.place_random(interface, n_molecules=5)
        
        print(f"   ✓ Custom molecules inserted: {custom_structure.custom_molecule_count}")
        print(f"   ✓ Modified interface: {custom_structure.interface_structure.ice_nmolecules} ice, "
              f"{custom_structure.interface_structure.water_nmolecules} water")
        
        # Verify molecule_index is correct
        print("\n4. Verifying molecule_index...")
        modified_interface = custom_structure.interface_structure
        
        if modified_interface.molecule_index:
            # Check ice molecules
            ice_indices = [m for m in modified_interface.molecule_index if m.mol_type == "ice"]
            print(f"   ✓ Ice molecules in index: {len(ice_indices)}")
            
            # Check that ice indices cover correct range
            if ice_indices:
                last_ice_idx = ice_indices[-1]
                ice_end = last_ice_idx.start_idx + last_ice_idx.count
                print(f"   ✓ Ice indices cover atoms 0 to {ice_end}")
                print(f"   ✓ Actual ice_atom_count: {modified_interface.ice_atom_count}")
                
                if ice_end != modified_interface.ice_atom_count:
                    print(f"   ✗ MISMATCH: ice indices end at {ice_end} but ice_atom_count is {modified_interface.ice_atom_count}")
                    return False
                else:
                    print("   ✓ Ice molecule_index matches ice_atom_count")
            
            # Check water molecules
            water_indices = [m for m in modified_interface.molecule_index if m.mol_type == "water"]
            print(f"   ✓ Water molecules in index: {len(water_indices)}")
            
            if water_indices:
                # Water should start right after ice
                first_water_idx = water_indices[0]
                print(f"   ✓ Water indices start at {first_water_idx.start_idx}")
                print(f"   ✓ Expected start: {modified_interface.ice_atom_count}")
                
                if first_water_idx.start_idx != modified_interface.ice_atom_count:
                    print(f"   ✗ MISMATCH: water starts at {first_water_idx.start_idx} but should start at {modified_interface.ice_atom_count}")
                    return False
                else:
                    print("   ✓ Water molecule_index starts correctly after ice")
        
        # 4. Insert ions using the modified interface structure
        print("\n5. Inserting ions into custom molecule structure...")
        try:
            ion_structure = insert_ions(
                modified_interface,
                concentration_molar=0.15,
                liquid_volume_nm3=None  # Let it calculate from cell
            )
            
            print(f"   ✓ Ion insertion completed successfully!")
            print(f"   ✓ Inserted {ion_structure.na_count} Na+ and {ion_structure.cl_count} Cl- ions")
            print(f"   ✓ No freeze/hang occurred!")
            
            return True
            
        except Exception as e:
            print(f"   ✗ Ion insertion failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_ion_insertion_after_custom_molecules()
    
    print("\n" + "="*60)
    if success:
        print("✓ TEST PASSED: Ion insertion works after custom molecules")
        print("✓ Bug fix verified - no freeze/hang occurred")
    else:
        print("✗ TEST FAILED: Ion insertion still has issues")
    print("="*60 + "\n")
    
    exit(0 if success else 1)
