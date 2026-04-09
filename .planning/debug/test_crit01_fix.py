"""Verification test for CRIT-01 atom count fix.

This test verifies that write_interface_gro_file calculates the correct
atom count when exporting interface structures.
"""
import tempfile
from pathlib import Path
import numpy as np

from quickice.structure_generation.types import InterfaceStructure
from quickice.output.gromacs_writer import write_interface_gro_file


def test_interface_atom_count():
    """Verify atom count in GRO header matches actual atoms written."""
    # Create a minimal interface structure
    # Ice: 2 molecules × 3 atoms = 6 atoms
    # Water: 3 molecules × 4 atoms = 12 atoms
    # Total: 18 atoms
    # But after normalization: (2+3) × 4 = 20 atoms (each molecule outputs as 4-atom TIP4P-ICE)

    ice_nmolecules = 2
    water_nmolecules = 3
    ice_atom_count = ice_nmolecules * 3  # 6
    water_atom_count = water_nmolecules * 4  # 12
    total_atoms = ice_atom_count + water_atom_count  # 18

    # Create positions array (18 atoms × 3 coords)
    positions = np.zeros((total_atoms, 3), dtype=np.float32)

    # Create dummy cell
    cell = np.eye(3) * 2.0  # 2nm box

    # Create dummy atom names
    atom_names = (["O", "H", "H"] * ice_nmolecules +
                  ["OW", "HW1", "HW2", "MW"] * water_nmolecules)

    # Create InterfaceStructure
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report="Test interface"
    )

    # Write to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        gro_path = Path(tmpdir) / "test.gro"
        write_interface_gro_file(iface, str(gro_path))

        # Read back and check
        with open(gro_path, 'r') as f:
            lines = f.readlines()

        # Line 0: Title
        # Line 1: Atom count
        header_atom_count = int(lines[1].strip())

        # Expected: Each ice molecule gets MW added (4 atoms each)
        # Each water molecule already has 4 atoms
        expected_output_atoms = (ice_nmolecules + water_nmolecules) * 4

        print(f"\nTest configuration:")
        print(f"  Ice molecules: {ice_nmolecules} × 3 atoms = {ice_atom_count} atoms")
        print(f"  Water molecules: {water_nmolecules} × 4 atoms = {water_atom_count} atoms")
        print(f"  Input total: {total_atoms} atoms")
        print(f"  Output total: {expected_output_atoms} atoms (after normalization)")
        print(f"  Header shows: {header_atom_count} atoms")

        assert header_atom_count == expected_output_atoms, \
            f"Header atom count {header_atom_count} != expected {expected_output_atoms}"

        # Count actual atom lines (exclude title, atom count, and box)
        atom_lines = len(lines) - 3  # title, count, box
        assert atom_lines == expected_output_atoms, \
            f"Actual atom lines {atom_lines} != expected {expected_output_atoms}"

        print("\n✓ Atom count verification PASSED")
        print(f"  Header correctly shows {header_atom_count} atoms")
        print(f"  File contains {atom_lines} atom lines")


if __name__ == "__main__":
    test_interface_atom_count()
