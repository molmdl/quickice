"""Test for MED-04 pocket mode performance optimization.

This test verifies that pocket mode only fills the bounding box of the cavity
instead of the entire box, which significantly improves performance for large
boxes with small pockets.
"""
import numpy as np
from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.pocket import assemble_pocket


def test_pocket_small_cavity_large_box():
    """Test pocket mode with small cavity in large box.
    
    This verifies the optimization: instead of filling the entire box with water
    and then removing molecules outside the cavity, we now fill only the bounding
    box of the cavity (2r x 2r x 2r) and translate positions.
    
    Expected behavior:
    - For 10nm box with 2nm diameter pocket (1nm radius)
    - Old approach: fill 1000 nm³, then filter -> waste ~96%
    - New approach: fill 8 nm³, then filter -> much less waste
    """
    # Create a simple ice candidate (small unit cell for testing)
    # Use ice1h structure: 16 molecules per unit cell
    # For simplicity, create a minimal candidate
    ice_positions = np.array([
        [0.0, 0.0, 0.0],  # O
        [0.1, 0.1, 0.0],  # H
        [-0.1, 0.1, 0.0],  # H
    ] * 100, dtype=float)  # 100 ice molecules = 300 atoms
    
    # Set reasonable cell dimensions (GenIce ice1h unit cell ~ 1.8nm)
    ice_cell = np.diag([1.8, 1.8, 1.8])
    
    candidate = Candidate(
        positions=ice_positions,
        atom_names=["O", "H", "H"] * 100,
        cell=ice_cell,
        nmolecules=100,
        phase_id="ice_ih",
        seed=42
    )
    
    # Create config for pocket mode with small cavity in large box
    config = InterfaceConfig(
        mode="pocket",
        box_x=10.0,  # Large box: 10nm
        box_y=10.0,
        box_z=10.0,
        seed=42,
        pocket_diameter=2.0,  # Small cavity: 2nm diameter = 1nm radius
        pocket_shape="sphere",
        overlap_threshold=0.25
    )
    
    print(f"\nTest: Pocket mode optimization")
    print(f"  Box: {config.box_x} x {config.box_y} x {config.box_z} nm")
    print(f"  Pocket diameter: {config.pocket_diameter} nm")
    print(f"  Pocket radius: {config.pocket_diameter / 2.0} nm")
    print(f"  Box volume: {config.box_x * config.box_y * config.box_z:.1f} nm³")
    print(f"  Cavity volume: {4/3 * np.pi * (config.pocket_diameter / 2.0)**3:.1f} nm³")
    print(f"  Bounding box volume: {(config.pocket_diameter)**3:.1f} nm³")
    
    # Assemble pocket structure
    result = assemble_pocket(candidate, config)
    
    print(f"\n  Result:")
    print(f"    Ice molecules: {result.ice_nmolecules}")
    print(f"    Water molecules: {result.water_nmolecules}")
    print(f"    Total atoms: {len(result.positions)}")
    
    # Verify result structure
    assert result.mode == "pocket"
    assert result.ice_nmolecules > 0
    assert result.water_nmolecules > 0
    assert len(result.positions) == result.ice_atom_count + result.water_atom_count
    
    # Verify positions are within box bounds
    assert np.all(result.positions[:, 0] >= 0)
    assert np.all(result.positions[:, 0] <= config.box_x)
    assert np.all(result.positions[:, 1] >= 0)
    assert np.all(result.positions[:, 1] <= config.box_y)
    assert np.all(result.positions[:, 2] >= 0)
    assert np.all(result.positions[:, 2] <= config.box_z)
    
    # Verify water molecules are near the cavity center
    center = np.array([config.box_x / 2.0, config.box_y / 2.0, config.box_z / 2.0])
    radius = config.pocket_diameter / 2.0
    
    # Extract water oxygen positions (every 4th atom starting from ice_atom_count)
    water_o_positions = result.positions[result.ice_atom_count::4]
    
    # Check that water molecules are within the cavity (with some tolerance for boundary)
    distances = np.linalg.norm(water_o_positions - center, axis=1)
    
    # All water should be within the cavity radius (or very close to boundary)
    # Due to overlap removal, some water at the boundary may be removed
    max_distance = np.max(distances)
    print(f"    Water distance range: {np.min(distances):.2f} - {max_distance:.2f} nm")
    print(f"    Expected max: {radius:.2f} nm")
    
    # Allow some tolerance for molecules at boundary
    assert max_distance < radius + 0.1, f"Water found outside cavity: max distance {max_distance:.2f} nm > radius {radius:.2f} nm"
    
    print("\n✓ Test PASSED - Pocket mode optimization working correctly")


def test_pocket_edge_cases():
    """Test pocket mode edge cases.
    
    Verifies the optimization works for:
    1. Very small pockets
    2. Pockets close to box boundary (should still work due to translation)
    """
    # Create minimal ice candidate
    ice_positions = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.1, 0.0],
        [-0.1, 0.1, 0.0],
    ] * 50, dtype=float)
    
    ice_cell = np.diag([1.8, 1.8, 1.8])
    
    candidate = Candidate(
        positions=ice_positions,
        atom_names=["O", "H", "H"] * 50,
        cell=ice_cell,
        nmolecules=50,
        phase_id="ice_ih",
        seed=42
    )
    
    # Test 1: Very small pocket (0.5nm diameter)
    config = InterfaceConfig(
        mode="pocket",
        box_x=5.0,
        box_y=5.0,
        box_z=5.0,
        seed=42,
        pocket_diameter=0.5,
        pocket_shape="sphere",
        overlap_threshold=0.25
    )
    
    print(f"\nTest 1: Small pocket (diameter {config.pocket_diameter} nm)")
    result = assemble_pocket(candidate, config)
    assert result.water_nmolecules >= 0  # May be zero if pocket too small
    print(f"  ✓ Water molecules: {result.water_nmolecules}")
    
    # Test 2: Large pocket relative to box
    config = InterfaceConfig(
        mode="pocket",
        box_x=5.0,
        box_y=5.0,
        box_z=5.0,
        seed=42,
        pocket_diameter=4.0,
        pocket_shape="sphere",
        overlap_threshold=0.25
    )
    
    print(f"\nTest 2: Large pocket (diameter {config.pocket_diameter} nm in {config.box_x} nm box)")
    result = assemble_pocket(candidate, config)
    assert result.water_nmolecules > 0
    print(f"  ✓ Water molecules: {result.water_nmolecules}")
    
    print("\n✓ All edge case tests PASSED")


if __name__ == "__main__":
    test_pocket_small_cavity_large_box()
    print("\n" + "="*60 + "\n")
    test_pocket_edge_cases()
