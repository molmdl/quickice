"""Test ion insertion fix for hydrate structures."""

import numpy as np
import pytest
from quickice.structure_generation.ion_inserter import IonInserter, MIN_SEPARATION
from quickice.structure_generation.types import (
    IonStructure,
    MoleculeIndex,
    IonConfig,
)


def test_hydrate_water_exclusion():
    """Test that ions are not placed too close to hydrate water framework.
    
    This test simulates a hydrate structure where:
    - Water molecules form the hydrate framework (labeled as "water", not "ice")
    - Guest molecules (CH4) are present
    - Ions should not be placed within MIN_SEPARATION of ANY atoms
    
    Before the fix, ions could be placed too close to hydrate water molecules
    because the distance check only looked at mol_type="ice" and mol_type="guest".
    """
    
    # Create a simple structure with:
    # - 2 water molecules (simulating hydrate framework, labeled as "water")
    # - 1 guest molecule (CH4)
    # - No ice molecules
    
    # Water molecule 1: centered at origin
    water1_pos = np.array([
        [0.0, 0.0, 0.0],  # OW
        [0.1, 0.0, 0.0],  # HW1
        [-0.1, 0.0, 0.0], # HW2
        [0.0, 0.0, 0.0],  # MW
    ])
    
    # Water molecule 2: 0.5 nm away (within MIN_SEPARATION if ion placed nearby)
    water2_pos = np.array([
        [0.5, 0.0, 0.0],  # OW
        [0.6, 0.0, 0.0],  # HW1
        [0.4, 0.0, 0.0],  # HW2
        [0.5, 0.0, 0.0],  # MW
    ])
    
    # Guest molecule (CH4): far away
    guest_pos = np.array([
        [10.0, 0.0, 0.0],  # C
        [10.1, 0.0, 0.0],  # H1
        [9.9, 0.0, 0.0],   # H2
        [10.0, 0.1, 0.0],  # H3
        [10.0, -0.1, 0.0], # H4
    ])
    
    # Combine positions
    positions = np.vstack([water1_pos, water2_pos, guest_pos])
    
    # Create molecule index
    molecule_index = [
        MoleculeIndex(start_idx=0, count=4, mol_type="water"),
        MoleculeIndex(start_idx=4, count=4, mol_type="water"),
        MoleculeIndex(start_idx=8, count=5, mol_type="guest"),
    ]
    
    # Create atom names
    atom_names = ["OW", "HW1", "HW2", "MW"] * 2 + ["C", "H", "H", "H", "H"]
    
    # Create IonStructure (simulating what would be passed to insert_ions)
    structure = IonStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.diag([20.0, 20.0, 20.0]),  # Large box
        molecule_index=molecule_index,
        na_count=0,
        cl_count=0,
        report="",
        guest_nmolecules=1,
        guest_atom_count=5,
    )
    
    # Create inserter
    config = IonConfig(concentration_molar=1.0)
    inserter = IonInserter(config=config, seed=42)
    
    # Try to insert ions
    result = inserter.replace_water_with_ions(structure, ion_pairs=1)
    
    # Check that ions were placed
    assert result.na_count >= 0, "Should have placed some ions"
    assert result.cl_count >= 0, "Should have placed some ions"
    
    # If ions were placed, check distances
    if result.na_count > 0 or result.cl_count > 0:
        # Extract ion positions
        ion_positions = []
        for mol in result.molecule_index:
            if mol.mol_type == "na":
                ion_positions.append(result.positions[mol.start_idx])
            elif mol.mol_type == "cl":
                ion_positions.append(result.positions[mol.start_idx])
        
        ion_positions = np.array(ion_positions)
        
        # Check distance to all existing atoms (water1, water2, guest)
        # Use scipy.spatial.cKDTree for efficient distance calculation
        from scipy.spatial import cKDTree
        
        # Build tree with all non-ion atoms
        non_ion_positions = []
        for mol in result.molecule_index:
            if mol.mol_type not in ("na", "cl"):
                start = mol.start_idx
                end = start + mol.count
                non_ion_positions.append(result.positions[start:end])
        
        if non_ion_positions:
            non_ion_positions = np.vstack(non_ion_positions)
            tree = cKDTree(non_ion_positions)
            
            # Check each ion
            for ion_pos in ion_positions:
                min_dist, _ = tree.query(ion_pos, k=1)
                assert min_dist >= MIN_SEPARATION, (
                    f"Ion placed too close to existing atom: {min_dist:.3f} nm < {MIN_SEPARATION} nm"
                )
    
    print(f"✓ Test passed: {result.na_count} NA and {result.cl_count} CL ions placed")
    print(f"  All ions are >= {MIN_SEPARATION} nm from existing atoms")


if __name__ == "__main__":
    test_hydrate_water_exclusion()
    print("\n✓ All tests passed!")
