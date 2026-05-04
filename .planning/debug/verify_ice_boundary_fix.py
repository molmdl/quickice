#!/usr/bin/env python3
"""Verify that ice molecules extend to periodic boundaries without gaps.

This script checks that the fix for missing ice molecules at periodic boundaries
works correctly. The fix uses filter_molecules=False for ice tiling.
"""

import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.gro_parser import parse_gro_file


def analyze_ice_boundaries(gro_path: Path, tolerance: float = 0.01):
    """Analyze ice OW atom positions at periodic boundaries.
    
    Returns:
        Dict with box_z, ow_z_min, ow_z_max, gap_at_z0, gap_at_box_z
    """
    # Read GRO file
    positions, atom_names, cell = parse_gro_file(gro_path)
    
    # Extract box dimensions (assuming orthogonal cell)
    if cell.ndim == 2:
        box_z = cell[2, 2]
    else:
        box_z = cell[2]
    
    # Find OW atoms (water oxygens from ice/hydrate framework)
    # Note: In hydrate slab, ice atoms come first
    ow_mask = np.array(atom_names) == "OW"
    ow_positions = positions[ow_mask]
    
    if len(ow_positions) == 0:
        print(f"  WARNING: No OW atoms found!")
        return None
    
    # Get Z range
    ow_z_min = ow_positions[:, 2].min()
    ow_z_max = ow_positions[:, 2].max()
    
    # Calculate gaps
    gap_at_z0 = ow_z_min
    gap_at_box_z = box_z - ow_z_max
    
    return {
        "box_z": box_z,
        "ow_z_min": ow_z_min,
        "ow_z_max": ow_z_max,
        "gap_at_z0": gap_at_z0,
        "gap_at_box_z": gap_at_box_z,
        "n_ow": len(ow_positions)
    }


def test_hydrate_slab_boundaries():
    """Test that ice molecules extend to periodic boundaries in hydrate slab mode."""
    print("=" * 70)
    print("Testing ice boundary coverage in hydrate slab mode")
    print("=" * 70)
    
    # Test both CH4 and THF hydrates
    test_cases = [
        ("CH4 sI hydrate", "tmp/ch4/slab/interface_slab.gro"),
        ("THF sII hydrate", "tmp/thf/slab/interface_slab.gro"),
    ]
    
    all_passed = True
    
    for name, gro_path in test_cases:
        print(f"\n{name}:")
        print(f"  File: {gro_path}")
        
        gro_file = Path(gro_path)
        if not gro_file.exists():
            print(f"  SKIP: File not found")
            continue
        
        result = analyze_ice_boundaries(gro_file)
        
        if result is None:
            print(f"  ERROR: Could not analyze file")
            all_passed = False
            continue
        
        # Print results
        print(f"  Box Z: {result['box_z']:.3f} nm")
        print(f"  OW Z range: {result['ow_z_min']:.3f} to {result['ow_z_max']:.3f} nm")
        print(f"  Gap at Z=0: {result['gap_at_z0']:.3f} nm")
        print(f"  Gap at Z=box_z: {result['gap_at_box_z']:.3f} nm")
        print(f"  Number of OW atoms: {result['n_ow']}")
        
        # Check if gaps are acceptable (should be < 0.02 nm for good coverage)
        max_gap = max(result['gap_at_z0'], result['gap_at_box_z'])
        tolerance = 0.02  # 0.02 nm = 0.2 Å
        
        if max_gap < tolerance:
            print(f"  ✓ PASS: Gaps are within tolerance ({tolerance:.3f} nm)")
        else:
            print(f"  ✗ FAIL: Gaps exceed tolerance ({tolerance:.3f} nm)")
            print(f"         Maximum gap: {max_gap:.3f} nm")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(test_hydrate_slab_boundaries())
