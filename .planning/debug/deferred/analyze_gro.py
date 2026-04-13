#!/usr/bin/env python
"""Analyze the error GRO files to find empty regions."""

import numpy as np

def parse_gro_file(filepath):
    """Parse GRO file and return positions and box dimensions."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # First line is comment
    # Second line is number of atoms
    n_atoms = int(lines[1].strip())
    
    # Parse atom positions
    positions = []
    for i in range(2, 2 + n_atoms):
        line = lines[i]
        # GRO format: residue#, residue name, atom name, atom#, x, y, z
        # Positions start at column 20, each 8 characters
        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        positions.append([x, y, z])
    
    positions = np.array(positions)
    
    # Last line is box dimensions
    box_line = lines[-1].strip().split()
    box = np.array([float(v) for v in box_line])
    
    return positions, box

def analyze_distribution(positions, box, name="File"):
    """Analyze the distribution of atoms in the box."""
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    
    print(f"Number of atoms: {len(positions)}")
    print(f"Box dimensions: {box[0]:.3f} x {box[1]:.3f} x {box[2]:.3f} nm")
    
    print(f"\nX range: {positions[:, 0].min():.3f} to {positions[:, 0].max():.3f} nm")
    print(f"Y range: {positions[:, 1].min():.3f} to {positions[:, 1].max():.3f} nm")
    print(f"Z range: {positions[:, 2].min():.3f} to {positions[:, 2].max():.3f} nm")
    
    # Check for empty regions
    x_bins = np.linspace(0, box[0], 21)
    y_bins = np.linspace(0, box[1], 21)
    z_bins = np.linspace(0, box[2], 21)
    
    # 3D histogram
    hist_3d, _ = np.histogramdd(positions, bins=[x_bins, y_bins, z_bins])
    
    empty_bins = np.where(hist_3d == 0)
    total_bins = hist_3d.size
    empty_count = len(empty_bins[0])
    
    print(f"\n3D distribution (20x20x20 bins):")
    print(f"  Total bins: {total_bins}")
    print(f"  Empty bins: {empty_count} ({empty_count/total_bins*100:.1f}%)")
    print(f"  Occupied bins: {total_bins - empty_count} ({(total_bins-empty_count)/total_bins*100:.1f}%)")
    
    # Check for large empty regions
    if empty_count > 0:
        print(f"\n  Empty bin locations (first 10):")
        for i in range(min(10, len(empty_bins[0]))):
            x_idx = empty_bins[0][i]
            y_idx = empty_bins[1][i]
            z_idx = empty_bins[2][i]
            x_range = (x_bins[x_idx], x_bins[x_idx+1])
            y_range = (y_bins[y_idx], y_bins[y_idx+1])
            z_range = (z_bins[z_idx], z_bins[z_idx+1])
            print(f"    X: [{x_range[0]:.2f}, {x_range[1]:.2f}], Y: [{y_range[0]:.2f}, {y_range[1]:.2f}], Z: [{z_range[0]:.2f}, {z_range[1]:.2f}]")
    
    # XY projection (ignore Z)
    xy_hist, _, _ = np.histogram2d(positions[:, 0], positions[:, 1], bins=[20, 20], 
                                    range=[[0, box[0]], [0, box[1]]])
    xy_empty = np.where(xy_hist == 0)
    print(f"\nXY projection (20x20 bins):")
    print(f"  Empty bins: {len(xy_empty[0])} / {xy_hist.size} ({len(xy_empty[0])/xy_hist.size*100:.1f}%)")
    
    # XZ projection
    xz_hist, _, _ = np.histogram2d(positions[:, 0], positions[:, 2], bins=[20, 20],
                                    range=[[0, box[0]], [0, box[2]]])
    xz_empty = np.where(xz_hist == 0)
    print(f"\nXZ projection (20x20 bins):")
    print(f"  Empty bins: {len(xz_empty[0])} / {xz_hist.size} ({len(xz_empty[0])/xz_hist.size*100:.1f}%)")
    
    # YZ projection
    yz_hist, _, _ = np.histogram2d(positions[:, 1], positions[:, 2], bins=[20, 20],
                                    range=[[0, box[1]], [0, box[2]]])
    yz_empty = np.where(yz_hist == 0)
    print(f"\nYZ projection (20x20 bins):")
    print(f"  Empty bins: {len(yz_empty[0])} / {yz_hist.size} ({len(yz_empty[0])/yz_hist.size*100:.1f}%)")
    
    return hist_3d, empty_count

def main():
    print("="*60)
    print("GRO FILE ANALYSIS")
    print("="*60)
    
    # Analyze error files
    files = [
        ("tmp/interface_pocket_err.gro", "Pocket Error"),
        ("tmp/interface_slab_err.gro", "Slab Error"),
        ("tmp/interface_slab.gro", "Slab (non-error)"),
    ]
    
    for filepath, name in files:
        try:
            positions, box = parse_gro_file(filepath)
            analyze_distribution(positions, box, name)
        except Exception as e:
            print(f"\nError reading {filepath}: {e}")


if __name__ == "__main__":
    main()