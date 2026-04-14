"""GRO format parsing utilities.

Shared parsing logic for GROMACS .gro files used by structure generation
and water template loading.
"""
from pathlib import Path

import numpy as np


def parse_gro_string(gro_string: str) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Parse GRO format string to extract coordinates.

    GRO format:
        Line 0: Title
        Line 1: Number of atoms
        Lines 2 to N+1: Atom records (residue, atom_name, atom_num, x, y, z)
        Last line: Box dimensions

    Args:
        gro_string: GRO format string

    Returns:
        Tuple of (positions, atom_names, cell):
            - positions: (N_atoms, 3) array in nm
            - atom_names: List of atom names ["O", "H", "H", ...]
            - cell: (3, 3) cell vectors in nm (row vectors)

    Note:
        For orthogonal boxes, returns diagonal cell matrix.
        For triclinic boxes, returns full cell matrix.
    """
    lines = gro_string.strip().split("\n")

    # Parse number of atoms
    n_atoms = int(lines[1])

    # Parse atom positions and names
    positions = np.zeros((n_atoms, 3), dtype=float)
    atom_names = []

    for i in range(n_atoms):
        # GRO format: fixed-width columns
        # Columns 11-15: atom name
        # Columns 21-28, 29-36, 37-44: x, y, z in nm
        line = lines[2 + i]
        atom_name = line[10:15].strip()
        atom_names.append(atom_name)

        # Parse coordinates (columns are 1-indexed in spec, 0-indexed here)
        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        positions[i] = [x, y, z]

    # Parse cell dimensions (last line)
    # For orthogonal boxes: "v1 v2 v3"
    # For non-orthogonal: "v1x v2y v3z v1y v1z v2x v2z v3x v3y"
    cell_line = lines[-1].split()
    if len(cell_line) == 3:
        # Orthogonal box
        cell = np.diag([float(v) for v in cell_line])
    else:
        # Non-orthogonal box (triclinic)
        # GRO format: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
        v1x, v2y, v3z = float(cell_line[0]), float(cell_line[1]), float(cell_line[2])
        v1y, v1z, v2x, v2z, v3x, v3y = [float(v) for v in cell_line[3:9]]
        cell = np.array([
            [v1x, v1y, v1z],
            [v2x, v2y, v2z],
            [v3x, v3y, v3z]
        ])

    return positions, atom_names, cell


def parse_gro_file(filepath: Path | str) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Load and parse GRO file.

    Args:
        filepath: Path to .gro file

    Returns:
        Tuple of (positions, atom_names, cell) - same as parse_gro_string

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is invalid
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"GRO file not found: {filepath}")

    with open(filepath, "r") as f:
        gro_string = f.read()

    return parse_gro_string(gro_string)