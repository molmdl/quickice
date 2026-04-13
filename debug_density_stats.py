#!/usr/bin/env python
"""Compare molecule density between Ice II and Ice V interfaces."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def analyze_density_stats(positions, box_dims, name="Interface"):
    """Calculate density statistics."""
    if len(positions) == 0:
        return None
    
    # Molecule density (molecules per nm^3)
    volume = box_dims[0] * box_dims[1] * box_dims[2]
    n_molecules = len(positions) // 3  # Ice has 3 atoms per molecule
    density = n_molecules / volume
    
    # Position statistics
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    pos_range = pos_max - pos_min
    
    # Effective volume (from position range)
    effective_volume = pos_range[0] * pos_range[1] * pos_range[2]
    effective_density = n_molecules / effective_volume if effective_volume > 0 else 0
    
    # Coverage percentages
    x_coverage = pos_range[0] / box_dims[0] * 100
    y_coverage = pos_range[1] / box_dims[1] * 100
    z_coverage = pos_range[2] / box_dims[2] * 100
    
    return {
        'name': name,
        'n_molecules': n_molecules,
        'volume': volume,
        'density': density,
        'effective_volume': effective_volume,
        'effective_density': effective_density,
        'x_coverage': x_coverage,
        'y_coverage': y_coverage,
        'z_coverage': z_coverage,
        'pos_min': pos_min,
        'pos_max': pos_max,
    }


def main():
    print("="*60)
    print("DENSITY COMPARISON: Ice II vs Ice V")
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
    
    print("Generating Ice V candidate...")
    phase_info_v = {
        "phase_id": "ice_v",
        "phase_name": "Ice V",
        "density": 1.24,
        "temperature": 253,
        "pressure": 500,
    }
    result_v = generate_candidates(phase_info_v, nmolecules=50, n_candidates=1)
    ice_v = result_v.candidates[0]
    
    # Test configurations
    configs = [
        ("slab", InterfaceConfig(mode="slab", box_x=5.0, box_y=5.0, box_z=8.0, seed=42, ice_thickness=2.0, water_thickness=4.0)),
        ("pocket", InterfaceConfig(mode="pocket", box_x=4.0, box_y=4.0, box_z=4.0, seed=42, pocket_diameter=2.0, pocket_shape="sphere")),
    ]
    
    for mode_name, config in configs:
        print(f"\n{'='*60}")
        print(f"{mode_name.upper()} MODE")
        print(f"{'='*60}")
        
        # Generate Ice II interface
        interface_ii = generate_interface(ice_ii, config)
        ice_pos_ii = interface_ii.positions[:interface_ii.ice_atom_count]
        box_ii = [interface_ii.cell[0, 0], interface_ii.cell[1, 1], interface_ii.cell[2, 2]]
        
        # Generate Ice V interface
        interface_v = generate_interface(ice_v, config)
        ice_pos_v = interface_v.positions[:interface_v.ice_atom_count]
        box_v = [interface_v.cell[0, 0], interface_v.cell[1, 1], interface_v.cell[2, 2]]
        
        # Analyze
        stats_ii = analyze_density_stats(ice_pos_ii, box_ii, "Ice II")
        stats_v = analyze_density_stats(ice_pos_v, box_v, "Ice V")
        
        print(f"\nIce II:")
        print(f"  Box: {box_ii[0]:.2f} x {box_ii[1]:.2f} x {box_ii[2]:.2f} nm")
        print(f"  Molecules: {stats_ii['n_molecules']}")
        print(f"  Density: {stats_ii['density']:.3f} molecules/nm³")
        print(f"  Effective density: {stats_ii['effective_density']:.3f} molecules/nm³")
        print(f"  Coverage: X={stats_ii['x_coverage']:.1f}%, Y={stats_ii['y_coverage']:.1f}%, Z={stats_ii['z_coverage']:.1f}%")
        
        print(f"\nIce V:")
        print(f"  Box: {box_v[0]:.2f} x {box_v[1]:.2f} x {box_v[2]:.2f} nm")
        print(f"  Molecules: {stats_v['n_molecules']}")
        print(f"  Density: {stats_v['density']:.3f} molecules/nm³")
        print(f"  Effective density: {stats_v['effective_density']:.3f} molecules/nm³")
        print(f"  Coverage: X={stats_v['x_coverage']:.1f}%, Y={stats_v['y_coverage']:.1f}%, Z={stats_v['z_coverage']:.1f}%")
        
        # Compare densities
        print(f"\nComparison:")
        density_ratio = stats_ii['density'] / stats_v['density']
        print(f"  Ice II/Ice V density ratio: {density_ratio:.3f}")
        
        effective_density_ratio = stats_ii['effective_density'] / stats_v['effective_density']
        print(f"  Ice II/Ice V effective density ratio: {effective_density_ratio:.3f}")
        
        # The target densities from phase info
        print(f"\n  Target densities:")
        print(f"    Ice II: 1.18 g/cm³")
        print(f"    Ice V: 1.24 g/cm³")
        print(f"    Ratio: {1.18/1.24:.3f}")
        
        # Check if densities match expected ratio
        expected_ratio = 1.18 / 1.24
        actual_ratio = density_ratio
        if abs(actual_ratio - expected_ratio) < 0.05:
            print(f"  ✓ Density ratio matches expected ({actual_ratio:.3f} ≈ {expected_ratio:.3f})")
        else:
            print(f"  ✗ Density ratio differs from expected ({actual_ratio:.3f} vs {expected_ratio:.3f})")


if __name__ == "__main__":
    main()