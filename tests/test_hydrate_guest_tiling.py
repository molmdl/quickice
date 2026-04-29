"""Test guest molecule tiling in hydrate interface generation.

Verifies that when generating a hydrate interface with slab mode,
guest molecules are properly tiled in BOTH ice layers (bottom and top),
not just one layer with incorrect splitting.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.modes.slab import assemble_slab


def create_sI_hydrate_candidate():
    """Create a mock sI hydrate candidate with water framework and CH4 guests.
    
    sI hydrate has:
    - Cubic unit cell ~1.2 nm
    - Water framework: TIP4P style (OW, HW1, HW2, MW) x 46 molecules per unit cell
    - Guest molecules: CH4 (C + 4H) at cage centers
      sI has 2 small cages (5^12) and 6 large cages (5^12 6^2) per unit cell
      = 8 guest sites per unit cell
    """
    # sI hydrate unit cell (simplified - just need the structure)
    # Cell dimensions
    cell = np.array([
        [1.2, 0.0, 0.0],
        [0.0, 1.2, 0.0],
        [0.0, 0.0, 1.2]
    ])
    
    # Create water framework (46 molecules * 4 atoms = 184 atoms)
    # Simplified: just create a grid of water molecules
    water_positions = []
    water_atom_names = []
    
    n_water = 46  # sI has 46 water molecules per unit cell
    for i in range(n_water):
        # Simple grid positions (not realistic, but good for testing)
        x = 0.1 + (i % 6) * 0.2
        y = 0.1 + ((i // 6) % 6) * 0.2
        z = 0.1 + (i // 36) * 0.2
        
        water_positions.extend([
            [x, y, z],           # OW
            [x + 0.07, y, z + 0.05],  # HW1
            [x + 0.05, y + 0.07, z + 0.03],  # HW2
            [x, y + 0.15, z + 0.05]  # MW
        ])
        water_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Create guest molecules (8 CH4 per unit cell = 8 * 5 = 40 atoms)
    # sI has 2 small + 6 large cages = 8 guest sites
    guest_positions = []
    guest_atom_names = []
    
    # Guest positions (fractional coordinates in unit cell, converted to Cartesian)
    # Small cages: (0.125, 0.125, 0.125) and (0.875, 0.875, 0.875)
    # Large cages: 6 positions at face centers
    guest_frac_positions = [
        [0.125, 0.125, 0.125],  # Small cage 1
        [0.875, 0.875, 0.875],  # Small cage 2
        [0.5, 0.5, 0.0],       # Large cage 1
        [0.5, 0.0, 0.5],       # Large cage 2
        [0.0, 0.5, 0.5],       # Large cage 3
        [0.5, 0.5, 1.0],       # Large cage 4
        [0.5, 1.0, 0.5],       # Large cage 5
        [1.0, 0.5, 0.5],       # Large cage 6
    ]
    
    for frac_pos in guest_frac_positions:
        # Convert fractional to Cartesian
        cart_pos = np.array(frac_pos) * 1.2  # Multiply by cell dimension
        
        # CH4: C + 4H (5 atoms)
        # C at center
        guest_positions.append(cart_pos)
        guest_atom_names.append("C")
        
        # H at tetrahedral positions (simplified)
        for j in range(4):
            h_pos = cart_pos + np.array([
                0.05 * np.cos(2 * np.pi * j / 4),
                0.05 * np.sin(2 * np.pi * j / 4),
                0.05 * (-1)**j
            ])
            guest_positions.append(h_pos)
            guest_atom_names.append("H")
    
    # Combine water framework and guests
    all_positions = np.array(water_positions + guest_positions)
    all_atom_names = water_atom_names + guest_atom_names
    
    return Candidate(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        nmolecules=n_water,  # Just water molecules
        phase_id="sI_hydrate",
        seed=42,
        metadata={
            "temperature": 273.15,
            "pressure": 0.101325,
            "original_hydrate": True
        }
    )


def test_slab_hydrate_guest_tiling():
    """Test that guests are properly tiled in BOTH ice layers.
    
    Bug: Previously, guests were tiled only for one layer, then split 50/50
    and shifted. This caused incomplete coverage.
    
    Fix: Now tile guests SEPARATELY for bottom and top ice layers.
    """
    candidate = create_sI_hydrate_candidate()
    
    # Configure slab mode
    # Box: 3.6 x 3.6 x 7.2 nm (3 unit cells each direction for ice)
    # Ice thickness: 1.2 nm (1 unit cell)
    # Water thickness: 4.8 nm
    config = InterfaceConfig(
        mode="slab",
        box_x=3.6,
        box_y=3.6,
        box_z=7.2,
        seed=42,
        ice_thickness=1.2,
        water_thickness=4.8
    )
    
    iface = assemble_slab(candidate, config)
    
    # Verify basic structure
    assert len(iface.positions) == len(iface.atom_names), \
        f"MISMATCH: positions={len(iface.positions)}, atom_names={len(iface.atom_names)}"
    
    # Check that we have guest molecules
    assert iface.guest_nmolecules > 0, "No guest molecules generated!"
    
    # Extract guest positions (they come after ice positions)
    # In the output: [ice_positions, guest_positions, water_positions]
    ice_atoms = iface.ice_atom_count
    guest_atoms = iface.guest_atom_count
    
    guest_start = ice_atoms
    guest_end = ice_atoms + guest_atoms
    
    guest_positions = iface.positions[guest_start:guest_end]
    
    # Check Z-distribution of guest molecules
    # Guests should be in TWO regions:
    # 1. Bottom ice: Z ~ [0, ice_thickness]
    # 2. Top ice: Z ~ [ice_thickness + water_thickness, box_z]
    
    # With our fix, we tile separately for each layer
    ice_thickness = config.ice_thickness
    water_thickness = config.water_thickness
    box_z = config.box_z
    
    bottom_ice_z_max = ice_thickness
    top_ice_z_min = ice_thickness + water_thickness
    
    # Count guests in each region
    z_coords = guest_positions[:, 2]
    
    bottom_guests = guest_positions[z_coords < (bottom_ice_z_max + 0.1)]
    top_guests = guest_positions[z_coords >= (top_ice_z_min - 0.1)]
    
    # Calculate molecules (CH4 = 5 atoms per molecule)
    guest_atoms_per_mol = 5  # CH4
    bottom_guest_mols = len(bottom_guests) // guest_atoms_per_mol
    top_guest_mols = len(top_guests) // guest_atoms_per_mol
    
    print(f"\nGuest distribution test:")
    print(f"  Bottom ice region (Z < {bottom_ice_z_max:.1f}): {bottom_guest_mols} molecules")
    print(f"  Top ice region (Z >= {top_ice_z_min:.1f}): {top_guest_mols} molecules")
    print(f"  Total guest molecules: {iface.guest_nmolecules}")
    
    # Verify we have guests in BOTH layers
    assert bottom_guest_mols > 0, \
        f"No guest molecules in bottom ice layer! (Z < {bottom_ice_z_max})"
    assert top_guest_mols > 0, \
        f"No guest molecules in top ice layer! (Z >= {top_ice_z_min})"
    
    # Verify the counts are reasonable (should be similar for symmetric layers)
    # Allow some tolerance due to tiling rounding
    min_expected = min(bottom_guest_mols, top_guest_mols)
    max_expected = max(bottom_guest_mols, top_guest_mols)
    
    # The ratio should be reasonable (not 10:1 or worse)
    if max_expected > 0:
        ratio = min_expected / max_expected
        assert ratio > 0.5, \
            f"Uneven distribution: bottom={bottom_guest_mols}, top={top_guest_mols} (ratio={ratio:.2f})"


def test_slab_hydrate_guest_z_coverage():
    """Test that guests cover the ENTIRE ice region in Z.
    
    Bug: The old code only tiled guests for one ice_thickness, then split.
    This meant some cells in the ice region had no guests.
    
    Fix: Tile separately for each layer with proper dimensions.
    """
    candidate = create_sI_hydrate_candidate()
    
    config = InterfaceConfig(
        mode="slab",
        box_x=3.6,
        box_y=3.6,
        box_z=7.2,
        seed=42,
        ice_thickness=1.2,
        water_thickness=4.8
    )
    
    iface = assemble_slab(candidate, config)
    
    # Get guest positions
    ice_atoms = iface.ice_atom_count
    guest_atoms = iface.guest_atom_count
    
    guest_positions = iface.positions[ice_atoms:ice_atoms + guest_atoms]
    
    # Check Z-distribution within each ice layer
    # There should be guests throughout the layer, not just at one Z-level
    z_coords = guest_positions[:, 2]
    
    # Define layer boundaries
    bottom_min = 0.0
    bottom_max = config.ice_thickness
    top_min = config.ice_thickness + config.water_thickness
    top_max = config.box_z
    
    # Check bottom layer coverage
    bottom_mask = (z_coords >= bottom_min) & (z_coords < bottom_max)
    bottom_z = z_coords[bottom_mask]
    
    if len(bottom_z) > 0:
        z_range = bottom_z.max() - bottom_z.min()
        print(f"\nBottom layer guest Z-range: {bottom_z.min():.3f} to {bottom_z.max():.3f} (span: {z_range:.3f} nm)")
        
        # Should span most of the ice layer (at least 80% of ice_thickness)
        expected_span = config.ice_thickness * 0.8
        assert z_range >= expected_span, \
            f"Bottom layer guests don't cover enough Z-range: {z_range:.3f} < {expected_span:.3f}"
    
    # Check top layer coverage
    top_mask = (z_coords >= top_min) & (z_coords < top_max)
    top_z = z_coords[top_mask]
    
    if len(top_z) > 0:
        z_range = top_z.max() - top_z.min()
        print(f"Top layer guest Z-range: {top_z.min():.3f} to {top_z.max():.3f} (span: {z_range:.3f} nm)")
        
        # Should span most of the ice layer
        expected_span = config.ice_thickness * 0.8
        assert z_range >= expected_span, \
            f"Top layer guests don't cover enough Z-range: {z_range:.3f} < {expected_span:.3f}"


if __name__ == "__main__":
    test_slab_hydrate_guest_tiling()
    test_slab_hydrate_guest_z_coverage()
    print("\nAll tests passed!")
