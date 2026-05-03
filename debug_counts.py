"""Debug to understand remaining 27 duplicates after fix."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

import math

def debug_tile_counts():
    """Debug the tile count calculation."""
    
    print("=" * 70)
    print("DEBUG: Tile count calculation with fix")
    print("=" * 70)
    
    cell_dims = np.array([2.46, 2.46, 1.2])
    target_region = np.array([7.451, 7.451, 3.601])
    
    lx, ly, lz = target_region
    a, b, c = cell_dims
    
    tolerance = 0.05  # 5% tolerance
    
    def calc_tile_count(target_dim, cell_dim):
        """Calculate number of tiles needed, avoiding over-tiling."""
        if cell_dim <= 0:
            return 1
        
        ratio = target_dim / cell_dim
        
        # Check if target is within tolerance of an exact multiple
        rounded = round(ratio)
        if rounded >= 1:
            exact_dim = rounded * cell_dim
            if target_dim > 0 and abs(target_dim - exact_dim) / target_dim < tolerance:
                return rounded
        
        return max(1, math.ceil(ratio))
    
    print(f"\nTarget dimensions: {target_region}")
    print(f"Cell dimensions: {cell_dims}")
    print(f"Tolerance: {tolerance}")
    
    # X dimension
    print(f"\n{'='*70}")
    print("X DIMENSION")
    print(f"{'='*70}")
    ratio_x = lx / a
    rounded_x = round(ratio_x)
    exact_x = rounded_x * a
    diff_x = abs(lx - exact_x)
    rel_diff_x = diff_x / lx
    
    print(f"  target_x = {lx:.6f} nm")
    print(f"  cell_x = {a:.6f} nm")
    print(f"  ratio = {ratio_x:.6f}")
    print(f"  rounded = {rounded_x}")
    print(f"  exact_dim = {exact_x:.6f} nm")
    print(f"  difference = {diff_x:.6f} nm")
    print(f"  relative difference = {rel_diff_x:.6f} ({rel_diff_x*100:.3f}%)")
    print(f"  tolerance = {tolerance} ({tolerance*100}%)")
    print(f"  Within tolerance? {rel_diff_x < tolerance}")
    nx = calc_tile_count(lx, a)
    print(f"  → Tile count: {nx}")
    
    # Y dimension
    print(f"\n{'='*70}")
    print("Y DIMENSION")
    print(f"{'='*70}")
    ratio_y = ly / b
    rounded_y = round(ratio_y)
    exact_y = rounded_y * b
    diff_y = abs(ly - exact_y)
    rel_diff_y = diff_y / ly
    
    print(f"  target_y = {ly:.6f} nm")
    print(f"  cell_y = {b:.6f} nm")
    print(f"  ratio = {ratio_y:.6f}")
    print(f"  rounded = {rounded_y}")
    print(f"  exact_dim = {exact_y:.6f} nm")
    print(f"  difference = {diff_y:.6f} nm")
    print(f"  relative difference = {rel_diff_y:.6f} ({rel_diff_y*100:.3f}%)")
    print(f"  tolerance = {tolerance} ({tolerance*100}%)")
    print(f"  Within tolerance? {rel_diff_y < tolerance}")
    ny = calc_tile_count(ly, b)
    print(f"  → Tile count: {ny}")
    
    # Z dimension
    print(f"\n{'='*70}")
    print("Z DIMENSION")
    print(f"{'='*70}")
    ratio_z = lz / c
    rounded_z = round(ratio_z)
    exact_z = rounded_z * c
    diff_z = abs(lz - exact_z)
    rel_diff_z = diff_z / lz
    
    print(f"  target_z = {lz:.6f} nm")
    print(f"  cell_z = {c:.6f} nm")
    print(f"  ratio = {ratio_z:.6f}")
    print(f"  rounded = {rounded_z}")
    print(f"  exact_dim = {exact_z:.6f} nm")
    print(f"  difference = {diff_z:.6f} nm")
    print(f"  relative difference = {rel_diff_z:.6f} ({rel_diff_z*100:.3f}%)")
    print(f"  tolerance = {tolerance} ({tolerance*100}%)")
    print(f"  Within tolerance? {rel_diff_z < tolerance}")
    nz = calc_tile_count(lz, c)
    print(f"  → Tile count: {nz}")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Tile counts: nx={nx}, ny={ny}, nz={nz}")
    print(f"Total tiles: {nx*ny*nz}")
    print(f"Coverage: x=[0, {nx*a:.6f}), y=[0, {ny*b:.6f}), z=[0, {nz*c:.6f})")
    print(f"Target:   x=[0, {lx:.6f}), y=[0, {ly:.6f}), z=[0, {lz:.6f})")
    print(f"Overflow: x={nx*a - lx:.6f} nm, y={ny*b - ly:.6f} nm, z={nz*c - lz:.6f} nm")

if __name__ == "__main__":
    debug_tile_counts()
