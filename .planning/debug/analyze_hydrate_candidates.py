#!/usr/bin/env python3
"""Analyze original hydrate candidates to check for inherent gaps.

This script checks if the original hydrate candidate files have gaps
at periodic boundaries, which could explain gaps in the slab output.
"""

import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quickice.structure_generation.gro_parser import parse_gro_file


def analyze_hydrate_candidate(gro_path: Path):
    """Analyze OW atom positions in hydrate candidate."""
    print(f"\nAnalyzing: {gro_path.name}")
    
    positions, atom_names, cell = parse_gro_file(gro_path)
    
    # Extract box dimensions
    if cell.ndim == 2:
        box_z = cell[2, 2]
        box_x = cell[0, 0]
        box_y = cell[1, 1]
    else:
        box_z = cell[2]
        box_x = cell[0]
        box_y = cell[1]
    
    print(f"  Box: {box_x:.3f} x {box_y:.3f} x {box_z:.3f} nm")
    
    # Find OW atoms
    ow_mask = np.array(atom_names) == "OW"
    ow_positions = positions[ow_mask]
    
    print(f"  OW atoms: {len(ow_positions)}")
    
    # Get Z range
    ow_z_min = ow_positions[:, 2].min()
    ow_z_max = ow_positions[:, 2].max()
    
    # Calculate gaps
    gap_at_z0 = ow_z_min
    gap_at_box_z = box_z - ow_z_max
    
    print(f"  OW Z range: {ow_z_min:.3f} to {ow_z_max:.3f} nm")
    print(f"  Gap at Z=0: {gap_at_z0:.3f} nm")
    print(f"  Gap at Z=box_z: {gap_at_box_z:.3f} nm")
    
    # Also check X and Y
    ow_x_min = ow_positions[:, 0].min()
    ow_x_max = ow_positions[:, 0].max()
    ow_y_min = ow_positions[:, 1].min()
    ow_y_max = ow_positions[:, 1].max()
    
    gap_at_x0 = ow_x_min
    gap_at_box_x = box_x - ow_x_max
    gap_at_y0 = ow_y_min
    gap_at_box_y = box_y - ow_y_max
    
    print(f"  OW X range: {ow_x_min:.3f} to {ow_x_max:.3f} nm (gaps: {gap_at_x0:.3f}, {gap_at_box_x:.3f})")
    print(f"  OW Y range: {ow_y_min:.3f} to {ow_y_max:.3f} nm (gaps: {gap_at_y0:.3f}, {gap_at_box_y:.3f})")
    
    return {
        "box_z": box_z,
        "gap_at_z0": gap_at_z0,
        "gap_at_box_z": gap_at_box_z,
    }


def main():
    """Analyze CH4 and THF hydrate candidates."""
    print("=" * 70)
    print("Analyzing original hydrate candidates for boundary gaps")
    print("=" * 70)
    
    # Check CH4 hydrate
    ch4_hydrate = Path("tmp/ch4/hydrate_sI_ch4_1x1x1.gro")
    if ch4_hydrate.exists():
        analyze_hydrate_candidate(ch4_hydrate)
    else:
        print(f"\nSKIP: {ch4_hydrate} not found")
    
    # Check THF hydrate
    thf_hydrate = Path("tmp/thf/hydrate_sII_thf_1x1x1.gro")
    if thf_hydrate.exists():
        analyze_hydrate_candidate(thf_hydrate)
    else:
        print(f"\nSKIP: {thf_hydrate} not found")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
