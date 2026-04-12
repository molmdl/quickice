"""Tests for triclinic cell transformation."""

import numpy as np
import pytest

from quickice.structure_generation.transformer_types import TransformationResult, TransformationStatus
from quickice.structure_generation.transformer import TriclinicTransformer
from quickice.structure_generation.types import Candidate


class TestCellAngleCalculation:
    """Tests for get_cell_angles method."""

    def test_orthogonal_cell_returns_90_degrees(self):
        """Test Case 9: get_cell_angles() computes correct angles for orthogonal cell."""
        transformer = TriclinicTransformer()
        # Orthogonal cubic cell
        cell = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        alpha, beta, gamma = transformer.get_cell_angles(cell)
        
        assert abs(alpha - 90.0) < 0.01
        assert abs(beta - 90.0) < 0.01
        assert abs(gamma - 90.0) < 0.01

    def test_rhombohedral_cell_returns_obtuse_angles(self):
        """Test Case 9: get_cell_angles() for rhombohedral (Ice II-like) cell."""
        transformer = TriclinicTransformer()
        # Ice II rhombohedral cell (α=β=γ≈113°)
        # Construct from known angle: a=b=c, α=β=γ=113°
        angle_rad = np.radians(113.0)
        a = 1.0
        # For rhombohedral: a = b = c, all angles equal
        cos_angle = np.cos(angle_rad)
        sin_angle = np.sin(angle_rad)
        
        cell = np.array([
            [a, 0, 0],
            [a * cos_angle, a * sin_angle, 0],
            [a * cos_angle, a * (cos_angle - cos_angle**2) / sin_angle, 
             a * np.sqrt(1 - cos_angle**2 - ((cos_angle - cos_angle**2) / sin_angle)**2)]
        ])
        
        # Normalize cell for consistency
        cell = cell * 0.5  # nm scale
        
        alpha, beta, gamma = transformer.get_cell_angles(cell)
        
        # All angles should be approximately 113°
        assert abs(alpha - 113.0) < 0.5
        assert abs(beta - 113.0) < 0.5
        assert abs(gamma - 113.0) < 0.5

    def test_monoclinic_cell_returns_tilted_beta(self):
        """Test Case 9: get_cell_angles() for monoclinic (Ice V-like) cell."""
        transformer = TriclinicTransformer()
        # Ice V monoclinic cell (α=γ=90°, β≈109°)
        beta = np.radians(109.0)
        cell = np.array([
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.3 * np.cos(beta), 0.0, 0.3 * np.sin(beta)]
        ])
        
        alpha, beta_angle, gamma = transformer.get_cell_angles(cell)
        
        # alpha and gamma should be ~90°, beta should be ~109°
        assert abs(alpha - 90.0) < 0.5
        assert abs(beta_angle - 109.0) < 0.5
        assert abs(gamma - 90.0) < 0.5


class TestTriclinicDetection:
    """Tests for is_triclinic method."""

    def test_orthogonal_cell_not_triclinic(self):
        """Test Case 1: is_triclinic() returns False for orthogonal cell (90°, 90°, 90°)."""
        transformer = TriclinicTransformer()
        cell = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        
        assert transformer.is_triclinic(cell) is False

    def test_rhombohedral_cell_is_triclinic(self):
        """Test Case 2: is_triclinic() returns True for Ice II cell (113°, 113°, 113°)."""
        transformer = TriclinicTransformer()
        # Construct rhombohedral cell with 113° angles
        angle_rad = np.radians(113.0)
        a = 0.5
        cos_angle = np.cos(angle_rad)
        sin_angle = np.sin(angle_rad)
        
        cell = np.array([
            [a, 0, 0],
            [a * cos_angle, a * sin_angle, 0],
            [a * cos_angle, a * (cos_angle - cos_angle**2) / sin_angle, 
             a * np.sqrt(max(0, 1 - cos_angle**2 - ((cos_angle - cos_angle**2) / sin_angle)**2))]
        ])
        
        assert transformer.is_triclinic(cell) is True

    def test_monoclinic_cell_is_triclinic(self):
        """Test Case 3: is_triclinic() returns True for Ice V cell (90°, 109°, 90°)."""
        transformer = TriclinicTransformer()
        # Ice V-like monoclinic cell
        beta = np.radians(109.0)
        cell = np.array([
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.3 * np.cos(beta), 0.0, 0.3 * np.sin(beta)]
        ])
        
        assert transformer.is_triclinic(cell) is True

    def test_near_orthogonal_not_triclinic(self):
        """Test Case 4: is_triclinic() returns False for near-orthogonal (89.95°, 90.05°, 90.0°)."""
        transformer = TriclinicTransformer()
        # Construct cell with small deviations from 90°
        # Using slight perturbations
        cell = np.array([
            [0.5, 0.0001, 0.0],  # Small non-zero y component
            [0.0, 0.5, 0.0001],  # Small non-zero z component
            [0.0001, 0.0, 0.5]   # Small non-zero x component
        ])
        
        # These create angles close to but not exactly 90°
        # Should be within 0.1° tolerance
        assert transformer.is_triclinic(cell) is False


class TestCellExtentCalculation:
    """Tests for get_cell_extent method."""

    def test_orthogonal_cell_extent(self):
        """Test Case 10: get_cell_extent() computes bounding box correctly for orthogonal cell."""
        transformer = TriclinicTransformer()
        cell = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0]
        ])
        
        extent = transformer.get_cell_extent(cell)
        
        assert extent[0] == pytest.approx(1.0, abs=0.01)
        assert extent[1] == pytest.approx(2.0, abs=0.01)
        assert extent[2] == pytest.approx(3.0, abs=0.01)

    def test_triclinic_cell_extent(self):
        """Test Case 10: get_cell_extent() for triclinic cell."""
        transformer = TriclinicTransformer()
        # Triclinic cell where extent != diagonal
        cell = np.array([
            [1.0, 0.5, 0.0],
            [0.5, 1.0, 0.0],
            [0.0, 0.5, 1.0]
        ])
        
        extent = transformer.get_cell_extent(cell)
        
        # Extent should be the bounding box, not just diagonal
        # For this cell, extent should be > diagonal elements
        assert extent[0] > 1.0  # x extent > cell[0,0]
        assert extent[1] > 1.0  # y extent > cell[1,1]


class TestTransformationResult:
    """Tests for TransformationResult dataclass."""

    def test_skipped_status(self):
        """Test TransformationResult with SKIPPED status."""
        result = TransformationResult(
            status=TransformationStatus.SKIPPED,
            cell=np.eye(3),
            positions=np.zeros((10, 3)),
            multiplier=1,
            message="Cell already orthogonal"
        )
        
        assert result.status == TransformationStatus.SKIPPED
        assert result.multiplier == 1
        assert "orthogonal" in result.message

    def test_transformed_status(self):
        """Test TransformationResult with TRANSFORMED status."""
        result = TransformationResult(
            status=TransformationStatus.TRANSFORMED,
            cell=np.eye(3) * 2,
            positions=np.zeros((30, 3)),
            multiplier=3,
            message="Ice II: transformed from rhombohedral to orthogonal"
        )
        
        assert result.status == TransformationStatus.TRANSFORMED
        assert result.multiplier == 3
        assert result.positions.shape == (30, 3)


class TestTransformIfNeeded:
    """Tests for transform_if_needed method."""

    def test_orthogonal_cell_unchanged(self):
        """Test Case 5: transform_if_needed() returns original for orthogonal cell."""
        transformer = TriclinicTransformer()
        
        candidate = Candidate(
            positions=np.zeros((100, 3)),
            atom_names=["O", "H", "H"] * 33 + ["O"],
            cell=np.eye(3) * 0.5,
            nmolecules=34,
            phase_id="ice_ih",
            seed=42
        )
        
        result = transformer.transform_if_needed(candidate)
        
        assert result.status == TransformationStatus.SKIPPED
        assert result.multiplier == 1
        np.testing.assert_array_equal(result.cell, candidate.cell)
        np.testing.assert_array_equal(result.positions, candidate.positions)

    def test_ice_ii_transformation_produces_orthogonal(self):
        """Test Case 6: transform_if_needed() produces orthogonal cell for Ice II."""
        transformer = TriclinicTransformer()
        
        # Create Ice II-like rhombohedral cell
        angle_rad = np.radians(113.0)
        a = 0.5
        cos_angle = np.cos(angle_rad)
        sin_angle = np.sin(angle_rad)
        
        cell = np.array([
            [a, 0, 0],
            [a * cos_angle, a * sin_angle, 0],
            [a * cos_angle, a * (cos_angle - cos_angle**2) / sin_angle, 
             a * np.sqrt(max(0, 1 - cos_angle**2 - ((cos_angle - cos_angle**2) / sin_angle)**2))]
        ])
        
        candidate = Candidate(
            positions=np.zeros((12, 3)),  # 4 water molecules
            atom_names=["O", "H", "H"] * 4,
            cell=cell,
            nmolecules=4,
            phase_id="ice_ii",
            seed=42
        )
        
        result = transformer.transform_if_needed(candidate)
        
        assert result.status == TransformationStatus.TRANSFORMED
        
        # Check that result is orthogonal (all angles ~90°)
        alpha, beta, gamma = transformer.get_cell_angles(result.cell)
        assert abs(alpha - 90.0) < 0.1
        assert abs(beta - 90.0) < 0.1
        assert abs(gamma - 90.0) < 0.1

    def test_ice_v_transformation_produces_orthogonal(self):
        """Test Case 7: transform_if_needed() produces orthogonal cell for Ice V."""
        transformer = TriclinicTransformer()
        
        # Ice V-like monoclinic cell
        beta = np.radians(109.0)
        cell = np.array([
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.3 * np.cos(beta), 0.0, 0.3 * np.sin(beta)]
        ])
        
        candidate = Candidate(
            positions=np.zeros((12, 3)),  # 4 water molecules
            atom_names=["O", "H", "H"] * 4,
            cell=cell,
            nmolecules=4,
            phase_id="ice_v",
            seed=42
        )
        
        result = transformer.transform_if_needed(candidate)
        
        assert result.status == TransformationStatus.TRANSFORMED
        
        # Check that result is orthogonal (all angles ~90°)
        alpha, beta_angle, gamma = transformer.get_cell_angles(result.cell)
        assert abs(alpha - 90.0) < 0.1
        assert abs(beta_angle - 90.0) < 0.1
        assert abs(gamma - 90.0) < 0.1


class TestDensityPreservation:
    """Tests for density preservation during transformation."""

    def test_transformation_preserves_density(self):
        """Test Case 8: Transformation preserves density within 1%."""
        transformer = TriclinicTransformer()
        
        # Create a more realistic test with actual atom positions
        angle_rad = np.radians(113.0)
        a = 0.5
        cos_angle = np.cos(angle_rad)
        sin_angle = np.sin(angle_rad)
        
        cell = np.array([
            [a, 0, 0],
            [a * cos_angle, a * sin_angle, 0],
            [a * cos_angle, a * (cos_angle - cos_angle**2) / sin_angle, 
             a * np.sqrt(max(0, 1 - cos_angle**2 - ((cos_angle - cos_angle**2) / sin_angle)**2))]
        ])
        
        # Generate some pseudo-random positions within the cell
        np.random.seed(42)
        frac_pos = np.random.rand(12, 3)  # 4 molecules, 3 atoms each
        positions = frac_pos @ cell.T
        
        candidate = Candidate(
            positions=positions,
            atom_names=["O", "H", "H"] * 4,
            cell=cell,
            nmolecules=4,
            phase_id="ice_ii",
            seed=42
        )
        
        # Calculate original density
        orig_volume = np.abs(np.linalg.det(cell))
        # Water molecular mass ~18 g/mol, assume 4 molecules
        # Density = mass / volume (simplified: use molecule count ratio)
        orig_nmol_per_vol = candidate.nmolecules / orig_volume
        
        result = transformer.transform_if_needed(candidate)
        
        # Calculate transformed density
        new_volume = np.abs(np.linalg.det(result.cell))
        new_nmol_per_vol = result.positions.shape[0] / 3 / new_volume  # Assuming 3 atoms per molecule
        
        # Check density preservation within 1%
        relative_error = abs(new_nmol_per_vol - orig_nmol_per_vol) / orig_nmol_per_vol
        assert relative_error < 0.01, f"Density relative error {relative_error:.4f} exceeds 1%"
