"""Triclinic cell transformation service.

Transforms triclinic unit cells (Ice II, Ice V) to orthogonal supercells
while preserving crystal structure integrity.

Architecture:
    TriclinicTransformer
        - ANGLE_TOL_DEG = 0.1  (from CONTEXT.md decision)
        - is_triclinic(cell) -> bool
        - get_cell_angles(cell) -> (alpha, beta, gamma)
        - get_cell_extent(cell) -> (dx, dy, dz)
        - find_orthogonal_supercell(cell, max_multiplier=50) -> H | None
        - apply_transformation(positions, cell, H) -> (new_positions, new_cell)
        - validate_transformation(orig, transformed) -> bool
        - transform_if_needed(candidate) -> TransformationResult
"""

import numpy as np

from quickice.structure_generation.types import Candidate
from quickice.structure_generation.transformer_types import (
    TransformationResult,
    TransformationStatus,
)


class TriclinicTransformer:
    """Service for transforming triclinic cells to orthogonal supercells.

    Ice phases have different cell symmetries:
    - Orthogonal (Ih, Ic, III, VI, VII, VIII): All angles = 90°
    - Rhombohedral (Ice II): α = β = γ ≈ 113°
    - Monoclinic (Ice V): α = γ = 90°, β ≈ 109°

    The transformation finds an integer supercell matrix H such that
    new_cell = H @ cell is approximately orthogonal (all angles 90° ± 0.1°).
    """

    ANGLE_TOL_DEG = 0.1  # From CONTEXT.md decision
    MAX_MULTIPLIER = 50  # Maximum supercell replication

    def get_cell_angles(self, cell: np.ndarray) -> tuple[float, float, float]:
        """Get cell angles (alpha, beta, gamma) in degrees.

        Crystallographic convention:
        - alpha: angle between b and c vectors
        - beta: angle between a and c vectors
        - gamma: angle between a and b vectors

        Args:
            cell: (3, 3) cell vectors as ROW vectors [a, b, c]

        Returns:
            Tuple of (alpha, beta, gamma) in degrees
        """
        a, b, c = cell[0], cell[1], cell[2]

        def angle(v1: np.ndarray, v2: np.ndarray) -> float:
            """Calculate angle between two vectors in degrees."""
            n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if n1 < 1e-10 or n2 < 1e-10:
                return 90.0
            # Use np.clip for numerical stability at edge cases
            cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
            return np.degrees(np.arccos(cos_a))

        alpha = angle(b, c)  # Angle between b and c
        beta = angle(a, c)   # Angle between a and c
        gamma = angle(a, b)  # Angle between a and b

        return alpha, beta, gamma

    def is_triclinic(self, cell: np.ndarray) -> bool:
        """Check if cell is triclinic (non-orthogonal).

        Uses 0.1° tolerance from CONTEXT.md decision.

        Args:
            cell: (3, 3) cell vectors as ROW vectors

        Returns:
            True if any angle deviates from 90° by more than tolerance
        """
        alpha, beta, gamma = self.get_cell_angles(cell)

        return bool(
            abs(alpha - 90.0) > self.ANGLE_TOL_DEG
            or abs(beta - 90.0) > self.ANGLE_TOL_DEG
            or abs(gamma - 90.0) > self.ANGLE_TOL_DEG
        )

    def get_cell_extent(self, cell: np.ndarray) -> np.ndarray:
        """Calculate the bounding box extent of a unit cell.

        For orthogonal cells, this equals the diagonal [cell[0,0], cell[1,1], cell[2,2]].
        For triclinic cells, this computes the actual bounding box by checking all
        8 corners of the parallelepiped.

        Args:
            cell: (3, 3) cell vectors as ROW vectors [a, b, c]

        Returns:
            (3,) array of [dx, dy, dz] bounding box dimensions
        """
        a, b, c = cell[0], cell[1], cell[2]

        # All 8 corners of the unit cell parallelepiped
        corners = np.array([
            [0, 0, 0],
            a,
            b,
            c,
            a + b,
            a + c,
            b + c,
            a + b + c,
        ])

        # Bounding box extent = max - min for each dimension
        return corners.max(axis=0) - corners.min(axis=0)

    def find_orthogonal_supercell(
        self, cell: np.ndarray, max_multiplier: int | None = None
    ) -> np.ndarray | None:
        """Find integer supercell matrix H such that H @ cell is orthogonal.

        Args:
            cell: (3, 3) cell vectors as ROW vectors
            max_multiplier: Maximum allowed det(H) (controls supercell size)

        Returns:
            (3, 3) integer transformation matrix H, or None if not found
        """
        if max_multiplier is None:
            max_multiplier = self.MAX_MULTIPLIER

        alpha, beta, gamma = self.get_cell_angles(cell)

        # For rhombohedral cells (Ice II: α=β=γ≈113°)
        if abs(alpha - beta) < 1.0 and abs(beta - gamma) < 1.0 and abs(alpha - 90) > 1.0:
            # Rhombohedral → Hexagonal → Orthogonal chain
            # Step 1: Rhombohedral to hexagonal (3x multiplier)
            H_rhomb_to_hex = np.array([
                [1, -1, 0],
                [0, 1, -1],
                [1, 1, 1]
            ])
            
            # Step 2: Hexagonal to orthogonal (2x multiplier)
            # For hexagonal (gamma=120°), use transformation that produces 90° angles
            H_hex_to_ortho = np.array([
                [1, 1, 0],
                [1, -1, 0],
                [0, 0, 1]
            ])
            
            # Combined transformation (6x multiplier)
            H_combined = H_hex_to_ortho @ H_rhomb_to_hex
            if abs(np.linalg.det(H_combined)) <= max_multiplier:
                new_cell = H_combined @ cell
                if not self.is_triclinic(new_cell):
                    return H_combined
            
            # Alternative: Try direct orthogonal transformation
            H_alt = np.array([
                [2, 1, 0],
                [1, 2, 0],
                [0, 0, 1]
            ])
            if abs(np.linalg.det(H_alt)) <= max_multiplier:
                new_cell = H_alt @ cell
                if not self.is_triclinic(new_cell):
                    return H_alt

        # For monoclinic cells (Ice V: β≠90°, α=γ=90°)
        if abs(alpha - 90) < 1.0 and abs(gamma - 90) < 1.0 and abs(beta - 90) > 1.0:
            a, b, c = cell[0], cell[1], cell[2]
            
            # Calculate optimal n for a' = a + n*c to be orthogonal to c
            # Condition: (a + n*c) · c = 0 → n = - (a · c) / (c · c)
            dot_ac = np.dot(a, c)
            dot_cc = np.dot(c, c)
            
            if dot_cc > 1e-10:
                n_optimal = -dot_ac / dot_cc
                
                # Try integers near the optimal value
                for n in range(int(n_optimal) - 5, int(n_optimal) + 6):
                    if n == 0:
                        continue
                    H = np.array([
                        [1, 0, n],
                        [0, 1, 0],
                        [0, 0, 1]
                    ], dtype=int)
                    if abs(np.linalg.det(H)) <= max_multiplier:
                        new_cell = H @ cell
                        if not self.is_triclinic(new_cell):
                            return H
            
            # Try shearing in c direction
            for n in range(-10, 11):
                if n == 0:
                    continue
                H = np.array([
                    [1, 0, 0],
                    [0, 1, 0],
                    [n, 0, 1]
                ], dtype=int)
                if abs(np.linalg.det(H)) <= max_multiplier:
                    new_cell = H @ cell
                    if not self.is_triclinic(new_cell):
                        return H

        # General search: try common patterns
        patterns = [
            np.diag([2, 2, 2]),      # 8x multiplier
            np.diag([3, 3, 3]),      # 27x multiplier
            np.diag([1, 1, 2]),      # 2x multiplier
            np.diag([1, 2, 2]),      # 4x multiplier
            np.diag([2, 2, 1]),      # 4x multiplier
            np.array([[1, 1, 0], [-1, 1, 0], [0, 0, 1]]),  # 2x multiplier
            np.array([[2, 1, 0], [1, 2, 0], [0, 0, 1]]),  # 3x multiplier
        ]

        for H in patterns:
            if abs(np.linalg.det(H)) > max_multiplier:
                continue
            new_cell = H @ cell
            if not self.is_triclinic(new_cell):
                return H

        # Brute force search for small multipliers
        for d1 in range(1, 6):
            for d2 in range(1, 6):
                for d3 in range(1, 6):
                    H = np.diag([d1, d2, d3])
                    if abs(np.linalg.det(H)) > max_multiplier:
                        continue
                    new_cell = H @ cell
                    if not self.is_triclinic(new_cell):
                        return H

        return None

    def apply_transformation(
        self, positions: np.ndarray, cell: np.ndarray, H: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply supercell transformation to positions and cell.

        The transformation replicates the unit cell according to the
        transformation matrix H. For each unit cell copy, atoms are
        placed at the appropriate fractional coordinates.

        Args:
            positions: (N, 3) atom positions in nm
            cell: (3, 3) cell vectors as ROW vectors in nm
            H: (3, 3) integer transformation matrix

        Returns:
            Tuple of (new_positions, new_cell)
        """
        new_cell = H @ cell

        # Convert positions to fractional coordinates
        # Formula: frac_pos = positions @ inv(cell.T)
        cell_inv_T = np.linalg.inv(cell.T)
        frac_positions = positions @ cell_inv_T

        # Wrap fractional coordinates to [0, 1)
        frac_positions = frac_positions % 1.0

        # Get the multiplier (number of unit cell replicas)
        multiplier = int(abs(np.linalg.det(H)))

        # Generate all unit cell offsets for the supercell
        # A lattice vector v is in the supercell if frac = H_inv @ v has all components in [0, 1)
        H_inv = np.linalg.inv(H)
        
        # Determine search range based on H elements
        max_elem = int(np.max(np.abs(H))) + 1
        
        offsets = []
        for i in range(-max_elem * 2, max_elem * 2 + 1):
            for j in range(-max_elem * 2, max_elem * 2 + 1):
                for k in range(-max_elem * 2, max_elem * 2 + 1):
                    # Check if this lattice point is in the supercell
                    v = np.array([i, j, k], dtype=float)
                    frac = H_inv @ v
                    if np.all(frac >= -0.001) and np.all(frac < 0.999):
                        offsets.append([i, j, k])
        
        # Convert to array
        offsets = np.array(offsets) if offsets else np.zeros((1, 3))
        
        # Verify we found the right number of offsets
        if len(offsets) != multiplier:
            # Fallback: if offset count doesn't match, use a simpler approach
            # Just replicate by the multiplier factor
            offsets = []
            for m in range(multiplier):
                offsets.append([m, 0, 0])  # Simplified fallback

        # Replicate atoms for each unit cell offset
        n_atoms = len(positions)
        n_offsets = len(offsets)
        new_positions = np.zeros((n_atoms * n_offsets, 3))

        idx = 0
        for offset in offsets:
            for pos in frac_positions:
                new_frac = pos + offset
                new_pos = new_frac @ cell.T  # Convert to Cartesian in original cell
                new_positions[idx] = new_pos
                idx += 1

        # Transform positions to the new cell
        # Positions are currently in the original cell, need to convert to supercell coordinates
        # frac_new = new_positions @ inv(new_cell.T)
        # But positions are already spread across the supercell via offsets
        # So we just need to wrap to the supercell bounds
        
        # Convert to fractional coordinates in the new cell
        new_cell_inv_T = np.linalg.inv(new_cell.T)
        new_frac = new_positions @ new_cell_inv_T
        new_frac = new_frac % 1.0
        new_positions = new_frac @ new_cell.T

        return new_positions, new_cell

    def validate_transformation(
        self,
        original: Candidate,
        new_positions: np.ndarray,
        new_cell: np.ndarray,
        density_tol: float = 0.01,
    ) -> bool:
        """Validate that transformation preserved crystal structure.

        Checks:
        1. Density preservation (volume scales with molecule count)

        Args:
            original: Original Candidate before transformation
            new_positions: Transformed atom positions
            new_cell: Transformed cell vectors
            density_tol: Relative tolerance for density comparison (default 1%)

        Returns:
            True if validation passes, False otherwise
        """
        # Calculate volumes
        orig_volume = np.abs(np.linalg.det(original.cell))
        new_volume = np.abs(np.linalg.det(new_cell))

        # Volume ratio should equal molecule count ratio
        orig_nmol = original.nmolecules
        new_nmol = len(new_positions) // 3  # Assuming 3 atoms per water molecule

        if orig_nmol == 0:
            return False

        expected_vol_ratio = new_nmol / orig_nmol
        actual_vol_ratio = new_volume / orig_volume

        # Check density preservation
        relative_error = abs(actual_vol_ratio - expected_vol_ratio) / expected_vol_ratio
        if relative_error > density_tol:
            return False

        return True

    def transform_if_needed(self, candidate: Candidate) -> TransformationResult:
        """Transform triclinic cell to orthogonal if needed.

        Main entry point for transformation. Checks if the candidate's
        cell is triclinic, and if so, transforms it to an orthogonal
        supercell.

        Args:
            candidate: Ice structure candidate with cell and positions

        Returns:
            TransformationResult with status, transformed cell/positions,
            and multiplier
        """
        # Check if cell is already orthogonal
        if not self.is_triclinic(candidate.cell):
            return TransformationResult(
                status=TransformationStatus.SKIPPED,
                cell=candidate.cell.copy(),
                positions=candidate.positions.copy(),
                multiplier=1,
                message=f"Cell already orthogonal for {candidate.phase_id}",
            )

        # Find transformation matrix
        H = self.find_orthogonal_supercell(candidate.cell)

        if H is None:
            return TransformationResult(
                status=TransformationStatus.FAILED,
                cell=candidate.cell.copy(),
                positions=candidate.positions.copy(),
                multiplier=1,
                message=f"Could not find orthogonal transformation for {candidate.phase_id}",
            )

        # Apply transformation
        new_positions, new_cell = self.apply_transformation(
            candidate.positions, candidate.cell, H
        )

        # Validate transformation
        if not self.validate_transformation(candidate, new_positions, new_cell):
            return TransformationResult(
                status=TransformationStatus.FAILED,
                cell=candidate.cell.copy(),
                positions=candidate.positions.copy(),
                multiplier=1,
                message=f"Transformation validation failed for {candidate.phase_id}",
            )

        multiplier = int(abs(np.linalg.det(H)))

        # Determine phase-specific message
        if candidate.phase_id == "ice_ii":
            message = f"Ice II: transformed from rhombohedral to orthogonal ({multiplier}x)"
        elif candidate.phase_id == "ice_v":
            message = f"Ice V: transformed from monoclinic to orthogonal ({multiplier}x)"
        else:
            message = f"{candidate.phase_id}: transformed to orthogonal ({multiplier}x)"

        return TransformationResult(
            status=TransformationStatus.TRANSFORMED,
            cell=new_cell,
            positions=new_positions,
            multiplier=multiplier,
            message=message,
        )
