"""Test script to verify water replacement during solute insertion."""

import numpy as np
from quickice.structure_generation.types import SoluteConfig, InterfaceStructure
from quickice.structure_generation.solute_inserter import SoluteInserter


def create_test_interface():
    """Create a test interface structure with ice and water."""
    # Create ice atoms (10 molecules, 3 atoms each = 30 atoms)
    n_ice_molecules = 10
    ice_positions = []
    for i in range(n_ice_molecules):
        # Each molecule has O, H, H
        ice_positions.append([i * 0.3, 0, 0])  # O
        ice_positions.append([i * 0.3 + 0.1, 0.1, 0])  # H
        ice_positions.append([i * 0.3 + 0.1, -0.1, 0])  # H
    
    # Create water atoms (100 molecules, 4 atoms each = 400 atoms for TIP4P)
    n_water_molecules = 100
    water_positions = []
    for i in range(n_water_molecules):
        # Place in liquid region (y > 5 nm)
        x = (i % 10) * 0.3
        y = 5.0 + (i // 10) * 0.3
        z = 0.0
        # TIP4P water: OW, HW1, HW2, MW
        water_positions.append([x, y, z])  # OW
        water_positions.append([x + 0.1, y + 0.1, z])  # HW1
        water_positions.append([x + 0.1, y - 0.1, z])  # HW2
        water_positions.append([x + 0.015, y, z])  # MW (virtual site)
    
    all_positions = np.array(ice_positions + water_positions)
    
    # Atom names
    atom_names = ["O", "H", "H"] * n_ice_molecules
    atom_names += ["OW", "HW1", "HW2", "MW"] * n_water_molecules
    
    # Cell
    cell = np.eye(3) * 10.0  # 10 nm box
    
    # Create InterfaceStructure
    interface = InterfaceStructure(
        positions=all_positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=n_ice_molecules * 3,
        water_atom_count=n_water_molecules * 4,
        ice_nmolecules=n_ice_molecules,
        water_nmolecules=n_water_molecules,
        mode="slab",
        report="Test interface for water replacement",
    )
    
    return interface


def test_water_replacement():
    """Test that water molecules are removed when solutes are inserted."""
    print("=" * 60)
    print("Testing water replacement during solute insertion")
    print("=" * 60)
    
    # Create test interface
    interface = create_test_interface()
    print(f"\nOriginal interface:")
    print(f"  Ice molecules: {interface.ice_nmolecules}")
    print(f"  Water molecules: {interface.water_nmolecules}")
    print(f"  Water atom count: {interface.water_atom_count}")
    
    # Insert solutes with high concentration
    config = SoluteConfig(
        concentration_molar=5.0,  # High concentration to ensure overlap
        solute_type="CH4",
        min_separation=0.3,  # 3 Å
        max_attempts=1000,
        seed=42,
    )
    
    inserter = SoluteInserter(config)
    solute_structure = inserter.insert_solutes(interface, config)
    
    print(f"\nSolute insertion result:")
    print(f"  Solutes placed: {solute_structure.n_molecules}")
    print(f"  Solute atoms: {len(solute_structure.positions)}")
    
    # Check the modified interface
    modified_interface = solute_structure.interface_structure
    print(f"\nModified interface:")
    print(f"  Ice molecules: {modified_interface.ice_nmolecules}")
    print(f"  Water molecules: {modified_interface.water_nmolecules}")
    print(f"  Water atom count: {modified_interface.water_atom_count}")
    
    # Verify water was removed
    water_removed = interface.water_nmolecules - modified_interface.water_nmolecules
    print(f"\nWater molecules removed: {water_removed}")
    
    if water_removed > 0:
        print("✓ SUCCESS: Water molecules were removed during solute insertion")
        return True
    else:
        print("✗ FAILURE: No water molecules were removed")
        return False


if __name__ == "__main__":
    success = test_water_replacement()
    exit(0 if success else 1)
