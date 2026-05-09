#!/usr/bin/env python
"""Test to verify MoleculeIndex construction has correct count values."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
)
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
import numpy as np


def test_molecule_index_count_values():
    """Verify MoleculeIndex.count field has correct values (not end_idx)."""
    
    # Create a simple interface structure
    # Ice: 2 molecules, 8 atoms (4 atoms per ice molecule for TIP4P)
    # Water: 3 molecules, 12 atoms
    ice_positions = np.random.rand(8, 3) * 2.0
    water_positions = np.random.rand(12, 3) * 2.0 + 2.0
    
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ["OW", "HW1", "HW2", "MW"] * 5  # 5 water molecules total
    
    interface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 4.0,
        ice_atom_count=8,
        water_atom_count=12,
        guest_atom_count=0,
        ice_nmolecules=2,
        water_nmolecules=3,
        molecule_index=None,
        mode='slab',
        report='test'
    )
    
    # Create a simple custom molecule GRO file
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom molecule GRO (ethanol-like: 3 atoms)
        gro_path = Path(tmpdir) / "custom.gro"
        itp_path = Path(tmpdir) / "custom.itp"
        
        with open(gro_path, 'w') as f:
            f.write("Custom molecule\n")
            f.write("  3\n")
            # GRO format: %5d%5s%5s%5d%8.3f%8.3f%8.3f
            f.write("    1 CUST   C1    1   0.000   0.000   0.000\n")
            f.write("    1 CUST   O2    2   0.100   0.000   0.000\n")
            f.write("    1 CUST   H3    3   0.200   0.000   0.000\n")
            f.write("   1.00000   1.00000   1.00000\n")
        
        with open(itp_path, 'w') as f:
            f.write('[ moleculetype ]\n')
            f.write('; Name      nrexcl\n')
            f.write('CUSTOM         3\n')
            f.write('\n')
            f.write('[ atoms ]\n')
            f.write('; nr   type  resnr residue  atom   cgnr     charge       mass\n')
            f.write('   1   CT      1    CUSTOM    C1     1    -0.18      12.01\n')
            f.write('   2   OH      1    CUSTOM    O2     1    -0.60      16.00\n')
            f.write('   3   HO      1    CUSTOM    H3     1     0.42       1.008\n')
        
        # Create config
        config = CustomMoleculeConfig(
            gro_path=gro_path,
            itp_path=itp_path,
            placement_mode="random",
            molecule_count=2,
            min_separation=0.2,
            max_attempts=100
        )
        
        # Create inserter
        inserter = CustomMoleculeInserter(config)
        
        # Place molecules
        result = inserter.place_random(interface, n_molecules=2)
        
        # Check molecule_index has correct count values
        print("\nChecking molecule_index.count values...")
        
        ice_molecules = [m for m in result.molecule_index if m.mol_type == "ice"]
        water_molecules = [m for m in result.molecule_index if m.mol_type == "water"]
        custom_molecules = [m for m in result.molecule_index if m.mol_type == "custom"]
        
        # Ice should have count=4 (TIP4P ice has 4 atoms)
        for mol in ice_molecules:
            assert mol.count == 4, f"Ice molecule count should be 4, got {mol.count}"
            print(f"  Ice: start_idx={mol.start_idx}, count={mol.count} ✓")
        
        # Water should have count=4 (TIP4P water has 4 atoms)
        for mol in water_molecules:
            assert mol.count == 4, f"Water molecule count should be 4, got {mol.count}"
            print(f"  Water: start_idx={mol.start_idx}, count={mol.count} ✓")
        
        # Custom should have count=3 (our test molecule has 3 atoms)
        for mol in custom_molecules:
            assert mol.count == 3, f"Custom molecule count should be 3, got {mol.count}"
            print(f"  Custom: start_idx={mol.start_idx}, count={mol.count} ✓")
        
        # Verify indices are sequential
        all_molecules = result.molecule_index
        for i in range(len(all_molecules) - 1):
            mol1 = all_molecules[i]
            mol2 = all_molecules[i + 1]
            expected_next_start = mol1.start_idx + mol1.count
            assert mol2.start_idx == expected_next_start, \
                f"Molecule indices not sequential: {mol1} -> {mol2}"
        
        print("\n✓ All molecule_index.count values are correct!")
        print(f"  Total molecules: {len(all_molecules)}")
        print(f"  Ice: {len(ice_molecules)}, Water: {len(water_molecules)}, Custom: {len(custom_molecules)}")
        
        return True


if __name__ == "__main__":
    try:
        test_molecule_index_count_values()
        print("\n✅ TEST PASSED: MoleculeIndex construction is correct")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
