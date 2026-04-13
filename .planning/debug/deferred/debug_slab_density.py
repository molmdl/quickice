#!/usr/bin/env python
"""Investigate why Ice II slab has lower than expected density."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def main():
    print("="*60)
    print("SLAB MODE DENSITY INVESTIGATION")
    print("="*60)
    
    # Generate candidates
    print("\nGenerating Ice II candidate...")
    phase_info_ii = {
        "phase_id": "ice_ii",
        "phase_name": "Ice II",
        "density": 1.18,
        "temperature": 238,
        "pressure": 300,
    }
    result_ii = generate_candidates(phase_info_ii, nmolecules=50, n_candidates=1)
    ice_ii = result_ii.candidates[0]
    extent_ii = get_cell_extent(ice_ii.cell)
    
    print(f"Ice II unit cell extent: {extent_ii}")
    print(f"Ice II molecules in unit cell: {len(ice_ii.positions) // 3}")
    print(f"Ice II unit cell volume: {np.abs(np.linalg.det(ice_ii.cell)):.3f} nm³")
    print(f"Ice II density in unit cell: {len(ice_ii.positions)//3 / np.abs(np.linalg.det(ice_ii.cell)):.3f} molecules/nm³")
    
    print("\nGenerating Ice V candidate...")
    phase_info_v = {
        "phase_id": "ice_v",
        "phase_name": "Ice V",
        "density": 1.24,
        "temperature": 253,
        "pressure": 500,
    }
    result_v = generate_candidates(phase_info_v, nmolecules=50, n_candidates=1)
    ice_v = result_v.candidates[0]
    extent_v = get_cell_extent(ice_v.cell)
    
    print(f"Ice V unit cell extent: {extent_v}")
    print(f"Ice V molecules in unit cell: {len(ice_v.positions) // 3}")
    print(f"Ice V unit cell volume: {np.abs(np.linalg.det(ice_v.cell)):.3f} nm³")
    print(f"Ice V density in unit cell: {len(ice_v.positions)//3 / np.abs(np.linalg.det(ice_v.cell)):.3f} molecules/nm³")
    
    # Generate slab interfaces
    config = InterfaceConfig(
        mode="slab",
        box_x=5.0,
        box_y=5.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    
    print("\n" + "="*60)
    print("SLAB INTERFACE GENERATION")
    print("="*60)
    
    print(f"\nRequested config:")
    print(f"  box_x: {config.box_x} nm")
    print(f"  box_y: {config.box_y} nm")
    print(f"  box_z: {config.box_z} nm")
    print(f"  ice_thickness: {config.ice_thickness} nm")
    print(f"  water_thickness: {config.water_thickness} nm")
    
    # Generate Ice II slab
    print("\nGenerating Ice II slab...")
    interface_ii = generate_interface(ice_ii, config)
    print(interface_ii.report)
    
    box_ii = [interface_ii.cell[0, 0], interface_ii.cell[1, 1], interface_ii.cell[2, 2]]
    ice_vol_ii = box_ii[0] * box_ii[1] * 2 * config.ice_thickness  # Two ice layers
    
    # Adjusted ice thickness from report
    # The box is adjusted for periodicity, so the actual ice thickness differs
    # Find the adjusted ice thickness from the box dimensions
    # box_z = 2 * ice_thickness + water_thickness
    adjusted_ice_thickness_ii = (box_ii[2] - config.water_thickness) / 2
    ice_vol_adjusted_ii = box_ii[0] * box_ii[1] * 2 * adjusted_ice_thickness_ii
    
    print(f"\nIce II slab analysis:")
    print(f"  Adjusted box: {box_ii[0]:.3f} x {box_ii[1]:.3f} x {box_ii[2]:.3f} nm")
    print(f"  Adjusted ice thickness: {adjusted_ice_thickness_ii:.3f} nm")
    print(f"  Ice volume (2 layers): {ice_vol_adjusted_ii:.1f} nm³")
    print(f"  Ice molecules: {interface_ii.ice_nmolecules}")
    print(f"  Ice density: {interface_ii.ice_nmolecules / ice_vol_adjusted_ii:.3f} molecules/nm³")
    
    # Expected density from unit cell
    expected_density_ii = len(ice_ii.positions)//3 / np.abs(np.linalg.det(ice_ii.cell))
    print(f"  Expected density (from unit cell): {expected_density_ii:.3f} molecules/nm³")
    print(f"  Actual/Expected ratio: {interface_ii.ice_nmolecules / ice_vol_adjusted_ii / expected_density_ii:.3f}")
    
    # Generate Ice V slab
    print("\nGenerating Ice V slab...")
    interface_v = generate_interface(ice_v, config)
    print(interface_v.report)
    
    box_v = [interface_v.cell[0, 0], interface_v.cell[1, 1], interface_v.cell[2, 2]]
    adjusted_ice_thickness_v = (box_v[2] - config.water_thickness) / 2
    ice_vol_adjusted_v = box_v[0] * box_v[1] * 2 * adjusted_ice_thickness_v
    
    print(f"\nIce V slab analysis:")
    print(f"  Adjusted box: {box_v[0]:.3f} x {box_v[1]:.3f} x {box_v[2]:.3f} nm")
    print(f"  Adjusted ice thickness: {adjusted_ice_thickness_v:.3f} nm")
    print(f"  Ice volume (2 layers): {ice_vol_adjusted_v:.1f} nm³")
    print(f"  Ice molecules: {interface_v.ice_nmolecules}")
    print(f"  Ice density: {interface_v.ice_nmolecules / ice_vol_adjusted_v:.3f} molecules/nm³")
    
    expected_density_v = len(ice_v.positions)//3 / np.abs(np.linalg.det(ice_v.cell))
    print(f"  Expected density (from unit cell): {expected_density_v:.3f} molecules/nm³")
    print(f"  Actual/Expected ratio: {interface_v.ice_nmolecules / ice_vol_adjusted_v / expected_density_v:.3f}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    actual_ratio_ii = interface_ii.ice_nmolecules / ice_vol_adjusted_ii / expected_density_ii
    actual_ratio_v = interface_v.ice_nmolecules / ice_vol_adjusted_v / expected_density_v
    
    print(f"\nIce II: Actual/Expected density ratio: {actual_ratio_ii:.3f}")
    print(f"Ice V: Actual/Expected density ratio: {actual_ratio_v:.3f}")
    
    if abs(actual_ratio_ii - 1.0) > 0.1:
        print(f"\n⚠ Ice II density is {abs(actual_ratio_ii - 1.0)*100:.1f}% off from expected!")
    
    if abs(actual_ratio_v - 1.0) > 0.1:
        print(f"\n⚠ Ice V density is {abs(actual_ratio_v - 1.0)*100:.1f}% off from expected!")


if __name__ == "__main__":
    main()