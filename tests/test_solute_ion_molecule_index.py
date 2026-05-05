"""Test that molecule_index is correctly updated after solute water removal.

This test verifies the fix for the IndexError that occurred when:
1. Insert solute (removes some water molecules)
2. Insert ions (tries to access molecule_index indices that were not updated)

The bug was that molecule_index was copied from the original structure
without updating the indices to match the new reduced positions array.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import (
    InterfaceStructure,
    SoluteConfig,
    MoleculeIndex,
)
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.ion_inserter import IonInserter, IonConfig


def create_test_interface_with_molecule_index():
    """Create a test InterfaceStructure with molecule_index populated."""
    # Create a simple structure:
    # - 10 ice molecules (4 atoms each = 40 atoms)
    # - 20 water molecules (4 atoms each = 80 atoms)
    # - 5 guest molecules (5 atoms each = 25 atoms)
    # Total: 145 atoms
    
    ice_nmolecules = 10
    water_nmolecules = 20
    guest_nmolecules = 5
    atoms_per_ice = 4
    atoms_per_water = 4
    atoms_per_guest = 5
    
    ice_atom_count = ice_nmolecules * atoms_per_ice
    water_atom_count = water_nmolecules * atoms_per_water
    guest_atom_count = guest_nmolecules * atoms_per_guest
    total_atoms = ice_atom_count + water_atom_count + guest_atom_count
    
    # Create positions
    positions = np.zeros((total_atoms, 3))
    atom_names = []
    molecule_index = []
    
    # Add ice molecules
    for i in range(ice_nmolecules):
        start = i * atoms_per_ice
        positions[start:start+atoms_per_ice] = np.random.rand(atoms_per_ice, 3) * 2.0
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
        molecule_index.append(MoleculeIndex(
            start_idx=start,
            count=atoms_per_ice,
            mol_type='ice',
        ))
    
    # Add water molecules
    for i in range(water_nmolecules):
        start = ice_atom_count + i * atoms_per_water
        positions[start:start+atoms_per_water] = np.random.rand(atoms_per_water, 3) * 2.0 + 3.0
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
        molecule_index.append(MoleculeIndex(
            start_idx=start,
            count=atoms_per_water,
            mol_type='water',
        ))
    
    # Add guest molecules
    for i in range(guest_nmolecules):
        start = ice_atom_count + water_atom_count + i * atoms_per_guest
        positions[start:start+atoms_per_guest] = np.random.rand(atoms_per_guest, 3) * 2.0 + 6.0
        atom_names.extend(['C', 'H', 'H', 'H', 'H'])
        molecule_index.append(MoleculeIndex(
            start_idx=start,
            count=atoms_per_guest,
            mol_type='guest',
        ))
    
    cell = np.eye(3) * 10.0  # 10 nm box
    
    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode='test',
        report='Test structure',
        guest_atom_count=guest_atom_count,
        molecule_index=molecule_index,
        guest_nmolecules=guest_nmolecules,
    )


def test_molecule_index_after_solute_water_removal():
    """Test that molecule_index is correctly updated after water removal."""
    # Create test structure
    interface = create_test_interface_with_molecule_index()
    
    # Insert solutes (this will remove some water molecules)
    config = SoluteConfig(
        solute_type='CH4',
        concentration_molar=1.0,  # High concentration to ensure water removal
        min_separation=0.3,
        max_attempts=100,
    )
    
    inserter = SoluteInserter(config=config, seed=42)
    solute_structure = inserter.insert_solutes(interface, config)
    
    # Get the modified interface structure
    modified_interface = solute_structure.interface_structure
    
    # Verify molecule_index is present and valid
    assert hasattr(modified_interface, 'molecule_index')
    assert modified_interface.molecule_index is not None
    
    # Verify that molecule_index indices are within bounds
    positions_size = len(modified_interface.positions)
    for mol in modified_interface.molecule_index:
        assert mol.start_idx < positions_size, \
            f"molecule_index has start_idx={mol.start_idx} but positions has only {positions_size} atoms"
        assert mol.start_idx + mol.count <= positions_size, \
            f"molecule_index entry ends at {mol.start_idx + mol.count} but positions has only {positions_size} atoms"
    
    # Verify molecule counts
    ice_count = sum(1 for mol in modified_interface.molecule_index if mol.mol_type == 'ice')
    water_count = sum(1 for mol in modified_interface.molecule_index if mol.mol_type == 'water')
    guest_count = sum(1 for mol in modified_interface.molecule_index if mol.mol_type == 'guest')
    
    assert ice_count == interface.ice_nmolecules, "Ice molecule count should be unchanged"
    assert water_count == modified_interface.water_nmolecules, "Water molecule count should match"
    assert guest_count == interface.guest_nmolecules, "Guest molecule count should be unchanged"
    
    print(f"✓ molecule_index validated: {ice_count} ice, {water_count} water, {guest_count} guest")
    print(f"  Total positions: {positions_size}")
    print(f"  Expected atoms: {modified_interface.ice_atom_count + modified_interface.water_atom_count + modified_interface.guest_atom_count}")


def test_ion_insertion_after_solute():
    """Test the full workflow: insert solute then insert ions."""
    # Create test structure
    interface = create_test_interface_with_molecule_index()
    
    # Step 1: Insert solutes
    solute_config = SoluteConfig(
        solute_type='CH4',
        concentration_molar=0.5,
        min_separation=0.3,
        max_attempts=100,
    )
    
    solute_inserter = SoluteInserter(config=solute_config, seed=42)
    solute_structure = solute_inserter.insert_solutes(interface, solute_config)
    
    # Step 2: Insert ions using the modified interface
    modified_interface = solute_structure.interface_structure
    
    ion_config = IonConfig(concentration_molar=0.1)
    ion_inserter = IonInserter(config=ion_config, seed=42)
    
    # This should NOT raise IndexError
    try:
        ion_structure = ion_inserter.replace_water_with_ions(
            modified_interface,
            ion_pairs=2
        )
        print(f"✓ Ion insertion succeeded: {ion_structure.na_count} Na+, {ion_structure.cl_count} Cl-")
    except IndexError as e:
        pytest.fail(f"IndexError during ion insertion after solute: {e}")


if __name__ == "__main__":
    test_molecule_index_after_solute_water_removal()
    test_ion_insertion_after_solute()
    print("\n✓ All tests passed!")
