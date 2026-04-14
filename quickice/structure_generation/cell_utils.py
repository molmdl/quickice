"""Cell matrix utilities for crystal structure analysis.

Shared utilities for checking cell properties across the structure
generation pipeline.
"""
import numpy as np


def is_cell_orthogonal(cell: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if a cell matrix represents an orthogonal (rectangular) box.

    An orthogonal cell has non-zero elements only on the diagonal.
    Triclinic cells have off-diagonal elements representing tilt.

    This function uses off-diagonal element tolerance, which is numerically
    stable and avoids edge cases with angle computation.

    Args:
        cell: (3, 3) cell matrix where each row is a lattice vector.
            For example, a cubic 1nm box has cell = [[1, 0, 0], [0, 1, 0], [0, 0, 1]].
        tol: Tolerance for considering off-diagonal elements as zero.
            Default 1e-10 is suitable for numerical precision.

    Returns:
        True if the cell is orthogonal (diagonal matrix within tolerance).
        False if the cell is triclinic (non-zero off-diagonal elements).

    Examples:
        >>> import numpy as np
        >>> # Orthogonal cubic cell
        >>> cell = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        >>> is_cell_orthogonal(cell)
        True
        >>> # Triclinic cell (Ice V, monoclinic)
        >>> cell = np.array([[1.0, 0.1, 0.0], [0.0, 1.0, 0.0], [0.0, 0.2, 1.0]])
        >>> is_cell_orthogonal(cell)
        False

    Note:
        The tolerance is applied to the magnitude of off-diagonal elements.
        A cell with off-diagonal elements < tol is considered orthogonal.
        The default tolerance (1e-10) is much stricter than the old
        angle-based tolerance (0.1° ~ 1.7e-3 rad).
    """
    off_diagonal = cell.copy()
    np.fill_diagonal(off_diagonal, 0)
    return np.allclose(off_diagonal, 0, atol=tol)