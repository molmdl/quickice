"""Regression tests for PERF-02: cKDTree(boxsize=) optimization in scorer.

PERF-02: Optimize _calculate_oo_distances_pbc to use cKDTree(boxsize=) for
orthorhombic cells (1x memory) instead of 3x3x3 supercell (27x memory),
with triclinic supercell fallback preserved.

Also fixes a pre-existing bug in the supercell approach: the old filter
(i < n_oxygen, i < j_original) missed cross-block PBC pairs where atoms
near opposite PBC boundaries had their canonical ordering flipped across
image blocks. The fix uses set-based canonical pair deduplication.

Test classes:
- TestPERF02IsOrthorhombic: Unit tests for _is_orthorhombic helper
- TestPERF02OrthorhombicBoxsize: Verify boxsize gives same results as supercell
- TestPERF02TriclinicFallback: Verify triclinic cells use supercell fallback
- TestPERF02MemoryImprovement: Verify no 27x memory allocation for orthorhombic
"""

import sys
import tracemalloc

import numpy as np
import pytest
from pathlib import Path

from scipy.spatial import cKDTree

# Add tests/ directory to sys.path for helper imports
sys.path.insert(0, str(Path(__file__).parent))

from quickice.ranking.scorer import _calculate_oo_distances_pbc, _is_orthorhombic


# ══════════════════════════════════════════════════════════════════════════════
# Helper: Build synthetic TIP4P-ICE positions
# ══════════════════════════════════════════════════════════════════════════════


def _make_tip4p_positions(n_molecules: int, cell_dims: np.ndarray):
    """Generate synthetic TIP4P-ICE positions for n_molecules.

    Returns (positions, atom_names) with OW/HW1/HW2/MW pattern.
    Oxygen positions are random within cell; H/M positions are offset from O.
    """
    rng = np.random.default_rng(42)
    # Oxygen positions: random within [0, cell_dim)
    o_positions = rng.random((n_molecules, 3)) * cell_dims

    # Build TIP4P-ICE: each molecule = OW, HW1, HW2, MW
    # H positions offset from O by ~0.0957 nm (O-H bond length)
    # MW offset from O by ~0.0157 nm along bisector
    oh_length = 0.0957  # nm
    om_length = 0.0157  # nm
    hoh_angle = 104.52  # degrees
    half_angle = np.radians(hoh_angle / 2)

    positions = np.zeros((n_molecules * 4, 3))
    atom_names = []

    for mol_idx in range(n_molecules):
        base = mol_idx * 4
        o = o_positions[mol_idx]

        # OW at oxygen position
        positions[base] = o
        atom_names.append('OW')

        # HW1 offset along +x-ish direction
        h1 = o + np.array([oh_length * np.cos(half_angle),
                           oh_length * np.sin(half_angle), 0.0])
        positions[base + 1] = h1
        atom_names.append('HW1')

        # HW2 offset along -x-ish direction
        h2 = o + np.array([oh_length * np.cos(-half_angle),
                           oh_length * np.sin(-half_angle), 0.0])
        positions[base + 2] = h2
        atom_names.append('HW2')

        # MW along bisector
        mw = o + np.array([om_length, 0.0, 0.0])
        positions[base + 3] = mw
        atom_names.append('MW')

    return positions, atom_names


def _calculate_oo_distances_supercell_ref(positions, atom_names, cell, cutoff=0.35):
    """Reference implementation: supercell approach with corrected deduplication.

    Uses set-based canonical pair deduplication instead of the old
    (i < n_oxygen, i < j_original) filter which missed cross-block PBC pairs.
    """
    o_indices = [i for i, name in enumerate(atom_names) if name in ('O', 'OW')]

    if len(o_indices) < 2:
        return np.array([])

    o_positions = positions[o_indices]
    n_oxygen = len(o_indices)

    cell_dims = np.diag(cell)

    # Build 3x3x3 supercell
    supercell_o = []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                offset = np.array([i, j, k]) * cell_dims
                supercell_o.append(o_positions + offset)

    supercell_o = np.vstack(supercell_o)

    tree = cKDTree(supercell_o)
    pairs = tree.query_pairs(cutoff)

    # Set-based deduplication: canonical (min, max) of original atom indices
    seen_pairs = set()
    distances = []
    for i, j in pairs:
        i_orig = i % n_oxygen
        j_orig = j % n_oxygen
        if i_orig != j_orig:
            canonical = (min(i_orig, j_orig), max(i_orig, j_orig))
            if canonical not in seen_pairs:
                seen_pairs.add(canonical)
                dist = np.linalg.norm(supercell_o[j] - supercell_o[i])
                distances.append(dist)

    return np.array(distances)


# ══════════════════════════════════════════════════════════════════════════════
# TestPERF02IsOrthorhombic: Unit tests for the helper function
# ══════════════════════════════════════════════════════════════════════════════


class TestPERF02IsOrthorhombic:
    """Unit tests for _is_orthorhombic helper function."""

    def test_diagonal_cell_is_orthorhombic(self):
        """Diagonal cell with different dimensions is orthorhombic."""
        cell = np.diag([1.0, 2.0, 3.0])
        assert _is_orthorhombic(cell) is True

    def test_nearly_orthorhombic_within_tolerance(self):
        """Cell with negligible off-diagonal elements (1e-12) is orthorhombic."""
        cell = np.array([[1.0, 1e-12, 0],
                         [0, 2.0, 1e-12],
                         [1e-12, 0, 3.0]])
        assert _is_orthorhombic(cell) is True

    def test_triclinic_cell_is_not_orthorhombic(self):
        """Cell with significant off-diagonal elements is not orthorhombic."""
        cell = np.array([[2.0, 0, 0],
                         [0.5, 2.0, 0],
                         [0, 0, 2.0]])
        assert _is_orthorhombic(cell) is False

    def test_identity_matrix_is_orthorhombic(self):
        """Identity matrix (unit cell) is orthorhombic."""
        cell = np.eye(3)
        assert _is_orthorhombic(cell) is True

    def test_ice_ii_like_cell_is_not_orthorhombic(self):
        """Ice II has a triclinic cell with off-diagonal elements."""
        # Ice II: hexagonal-like with tilted axis
        cell = np.array([[1.3, 0, 0],
                         [-0.65, 1.125, 0],
                         [0, 0, 1.25]])
        assert _is_orthorhombic(cell) is False


# ══════════════════════════════════════════════════════════════════════════════
# TestPERF02OrthorhombicBoxsize: Verify boxsize matches supercell
# ══════════════════════════════════════════════════════════════════════════════


class TestPERF02OrthorhombicBoxsize:
    """Verify cKDTree(boxsize=) produces same O-O distances as supercell for orthorhombic cells."""

    def test_cubic_orthorhombic_distances_match(self):
        """Boxsize and supercell produce identical O-O distances for cubic cell."""
        cell_dims = np.array([1.5, 1.5, 1.5])
        cell = np.diag(cell_dims)
        positions, atom_names = _make_tip4p_positions(96, cell_dims)

        # Both approaches should give the same set of O-O distances
        boxsize_dists = _calculate_oo_distances_pbc(positions, atom_names, cell, cutoff=0.35)
        supercell_dists = _calculate_oo_distances_supercell_ref(positions, atom_names, cell, cutoff=0.35)

        assert len(boxsize_dists) > 0, "Should find O-O pairs in cubic cell"
        assert len(boxsize_dists) == len(supercell_dists), (
            f"Pair count mismatch: boxsize={len(boxsize_dists)}, supercell={len(supercell_dists)}"
        )
        np.testing.assert_allclose(
            np.sort(boxsize_dists), np.sort(supercell_dists),
            atol=1e-10,
            err_msg="O-O distances differ between boxsize and supercell for cubic cell"
        )

    def test_noncubic_orthorhombic_distances_match(self):
        """Boxsize and supercell produce identical O-O distances for non-cubic orthorhombic cell."""
        cell_dims = np.array([2.0, 2.0, 3.0])
        cell = np.diag(cell_dims)
        positions, atom_names = _make_tip4p_positions(96, cell_dims)

        boxsize_dists = _calculate_oo_distances_pbc(positions, atom_names, cell, cutoff=0.35)
        supercell_dists = _calculate_oo_distances_supercell_ref(positions, atom_names, cell, cutoff=0.35)

        assert len(boxsize_dists) > 0, "Should find O-O pairs in non-cubic orthorhombic cell"
        assert len(boxsize_dists) == len(supercell_dists), (
            f"Pair count mismatch: boxsize={len(boxsize_dists)}, supercell={len(supercell_dists)}"
        )
        np.testing.assert_allclose(
            np.sort(boxsize_dists), np.sort(supercell_dists),
            atol=1e-10,
            err_msg="O-O distances differ between boxsize and supercell for non-cubic cell"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestPERF02TriclinicFallback: Verify triclinic cells use supercell fallback
# ══════════════════════════════════════════════════════════════════════════════


class TestPERF02TriclinicFallback:
    """Verify triclinic cells use 3x3x3 supercell fallback correctly."""

    def test_triclinic_cell_detected(self):
        """Triclinic cell is correctly identified by _is_orthorhombic."""
        cell = np.array([[2.0, 0, 0],
                         [0.5, 2.0, 0],
                         [0, 0, 2.0]])
        assert _is_orthorhombic(cell) is False

    def test_triclinic_cell_returns_distances(self):
        """_calculate_oo_distances_pbc returns distances for triclinic cell."""
        cell = np.array([[2.0, 0, 0],
                         [0.5, 2.0, 0],
                         [0, 0, 2.0]])
        cell_dims = np.array([2.0, 2.0, 2.0])  # approximate for position generation
        positions, atom_names = _make_tip4p_positions(48, cell_dims)

        distances = _calculate_oo_distances_pbc(positions, atom_names, cell, cutoff=0.35)

        assert isinstance(distances, np.ndarray), "Should return numpy array"
        assert len(distances) > 0, "Should find O-O pairs in triclinic cell"
        assert np.all(distances > 0), "All distances should be positive"
        assert np.all(distances <= 0.35 + 1e-10), "All distances should be within cutoff"

    def test_ice_ii_like_cell_returns_distances(self):
        """Ice II-like triclinic cell returns valid distances."""
        cell = np.array([[1.3, 0, 0],
                         [-0.65, 1.125, 0],
                         [0, 0, 1.25]])
        cell_dims = np.array([1.3, 1.125, 1.25])
        positions, atom_names = _make_tip4p_positions(48, cell_dims)

        distances = _calculate_oo_distances_pbc(positions, atom_names, cell, cutoff=0.35)

        assert isinstance(distances, np.ndarray), "Should return numpy array"
        # With a small cell, might have 0 pairs — that's OK
        assert np.all(distances <= 0.35 + 1e-10), "All distances should be within cutoff"


# ══════════════════════════════════════════════════════════════════════════════
# TestPERF02MemoryImprovement: Verify no 27x memory allocation for orthorhombic
# ══════════════════════════════════════════════════════════════════════════════


class TestPERF02MemoryImprovement:
    """Verify orthorhombic boxsize approach uses significantly less memory than 27x supercell."""

    def test_orthorhombic_memory_under_50mb(self):
        """Orthorhombic boxsize uses < 50 MB for 10000 oxygen atoms.

        With boxsize, we only have 10000 oxygen atoms (no 27x supercell).
        10000 * 3 * 8 bytes = 240 KB for positions, plus KDTree overhead.

        A 27x supercell of 10000 atoms = 270000 * 3 * 8 bytes = ~6.5 MB
        just for positions, plus much larger KDTree.

        The 50 MB limit is generous (accounts for KDTree internals) but
        confirms we don't allocate the 27x supercell (which would need
        significantly more memory for the tree structure on 270k points).
        """
        n_molecules = 10000
        cell_dims = np.array([5.0, 5.0, 5.0])  # large enough box for 10k molecules
        cell = np.diag(cell_dims)
        positions, atom_names = _make_tip4p_positions(n_molecules, cell_dims)

        tracemalloc.start()
        _calculate_oo_distances_pbc(positions, atom_names, cell, cutoff=0.35)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        # A 27x supercell KDTree for 270k atoms would typically use > 100 MB
        # The boxsize approach with 10k atoms should stay well under 50 MB
        assert peak_mb < 50.0, (
            f"Peak memory {peak_mb:.2f} MB exceeds 50 MB limit for orthorhombic. "
            f"This suggests 27x supercell is being allocated instead of boxsize."
        )
