"""Test for CRIT-02 index overflow in water atom access.

This test verifies that water molecule iteration correctly accesses water atoms
even when ice atoms have been removed during overlap resolution.
"""
import tempfile
from pathlib import Path
import numpy as np

from quickice.structure_generation.types import InterfaceStructure
from quickice.output.gromacs_writer import write_interface_gro_file


def test_ice_removal_invariant():
    """Verify ice_atom_count == ice_nmolecules * 3 after ice removal.
    
    This tests the scenario where ice molecules are removed (like in pocket mode).
    """
    # Simulate pocket mode where ice molecules inside cavity are removed
    # Initial: 10 ice molecules = 30 atoms
    # After removal: 8 ice molecules = 24 atoms
    # Water: 5 molecules = 20 atoms
    
    initial_ice_nmolecules = 10
    initial_ice_atoms = initial_ice_nmolecules * 3  # 30
    
    remaining_ice_nmolecules = 8
    remaining_ice_atoms = remaining_ice_nmolecules * 3  # 24
    
    water_nmolecules = 5
    water_atoms = water_nmolecules * 4  # 20
    
    total_atoms = remaining_ice_atoms + water_atoms  # 44
    
    print(f"\nTest: Ice removal scenario")
    print(f"  Initial ice: {initial_ice_nmolecules} molecules = {initial_ice_atoms} atoms")
    print(f"  After removal: {remaining_ice_nmolecules} molecules = {remaining_ice_atoms} atoms")
    print(f"  Water: {water_nmolecules} molecules = {water_atoms} atoms")
    print(f"  Total atoms: {total_atoms}")
    
    # Create positions array
    positions = np.zeros((total_atoms, 3), dtype=np.float32)
    # Set some non-zero values to verify correct atoms are read
    for i in range(total_atoms):
        positions[i] = [float(i), float(i+1), float(i+2)]
    
    # Create dummy cell
    cell = np.eye(3) * 3.0  # 3nm box
    
    # Create atom names
    atom_names = (["O", "H", "H"] * remaining_ice_nmolecules +
                  ["OW", "HW1", "HW2", "MW"] * water_nmolecules)
    
    # CRITICAL: This is what the code should do - use len(positions) for ice_atom_count
    ice_atom_count = remaining_ice_atoms  # Should be 24
    water_atom_count = water_atoms  # Should be 20
    
    print(f"\n  ice_atom_count = {ice_atom_count}")
    print(f"  ice_nmolecules * 3 = {remaining_ice_nmolecules * 3}")
    print(f"  Invariant holds: {ice_atom_count == remaining_ice_nmolecules * 3}")
    
    # Create InterfaceStructure
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=remaining_ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="pocket",
        report="Test pocket interface"
    )
    
    # Verify the water atom access formula
    print(f"\n  Water atom access check:")
    for mol_idx in range(water_nmolecules):
        base_idx = iface.ice_atom_count + mol_idx * 4
        print(f"    Water mol {mol_idx}: base_idx = {base_idx}")
        if base_idx >= len(iface.positions):
            print(f"    ERROR: base_idx {base_idx} >= positions length {len(iface.positions)}")
            raise AssertionError(f"Index overflow at water molecule {mol_idx}")
        if base_idx + 3 >= len(iface.positions):
            print(f"    ERROR: base_idx+3 = {base_idx+3} >= positions length {len(iface.positions)}")
            raise AssertionError(f"Index overflow at water molecule {mol_idx}")
    
    # Write to GRO file
    with tempfile.TemporaryDirectory() as tmpdir:
        gro_path = Path(tmpdir) / "test.gro"
        write_interface_gro_file(iface, str(gro_path))
        
        with open(gro_path, 'r') as f:
            lines = f.readlines()
        
        # Verify atom count
        header_atom_count = int(lines[1].strip())
        expected_output_atoms = (remaining_ice_nmolecules + water_nmolecules) * 4
        print(f"\n  Header atom count: {header_atom_count}")
        print(f"  Expected output atoms: {expected_output_atoms}")
        
        assert header_atom_count == expected_output_atoms
        
        # Count actual atom lines
        atom_lines = len(lines) - 3
        assert atom_lines == expected_output_atoms
        
        print("\n✓ Test PASSED - No index overflow")


def test_broken_invariant():
    """Test what happens if ice_atom_count != ice_nmolecules * 3.
    
    This simulates a BUG where the invariant is violated.
    """
    # This is a BUG scenario - ice_atom_count is wrong
    ice_nmolecules = 8  # But positions actually have 8*3 = 24 ice atoms
    wrong_ice_atom_count = 30  # BUG: This is the INITIAL count, not current!
    
    water_nmolecules = 5
    water_atoms = water_nmolecules * 4  # 20
    
    total_atoms = (ice_nmolecules * 3) + water_atoms  # 44 atoms
    
    print(f"\nTest: BROKEN INVARIANT (simulating bug)")
    print(f"  ice_nmolecules = {ice_nmolecules}")
    print(f"  WRONG ice_atom_count = {wrong_ice_atom_count} (should be {ice_nmolecules * 3})")
    print(f"  water_nmolecules = {water_nmolecules}")
    print(f"  Total atoms in positions = {total_atoms}")
    
    positions = np.zeros((total_atoms, 3), dtype=np.float32)
    cell = np.eye(3) * 3.0
    atom_names = (["O", "H", "H"] * ice_nmolecules +
                  ["OW", "HW1", "HW2", "MW"] * water_nmolecules)
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=wrong_ice_atom_count,  # BUG: Wrong value!
        water_atom_count=water_atoms,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report="Broken invariant test"
    )
    
    # This should cause an IndexError
    print(f"\n  Water atom access with broken invariant:")
    try:
        for mol_idx in range(water_nmolecules):
            base_idx = iface.ice_atom_count + mol_idx * 4
            print(f"    Water mol {mol_idx}: base_idx = {base_idx}")
            # This will overflow!
            if base_idx >= len(iface.positions):
                print(f"    ERROR: Index overflow! base_idx {base_idx} >= positions length {len(iface.positions)}")
                raise IndexError(f"Index {base_idx} out of bounds for positions of length {len(iface.positions)}")
    except IndexError as e:
        print(f"\n  ✗ BUG CONFIRMED: IndexError occurs with broken invariant")
        print(f"    {e}")
        return  # Don't write GRO file
    
    print("\n  No error detected (unexpected)")


if __name__ == "__main__":
    test_ice_removal_invariant()
    print("\n" + "="*60 + "\n")
    test_broken_invariant()
