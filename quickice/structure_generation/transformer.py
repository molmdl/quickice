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

    def _is_diagonal_cell(self, cell: np.ndarray, tol: float = 1e-10) -> bool:
        """Check if cell matrix is diagonal (aligned with coordinate axes).
        
        A diagonal cell has non-zero elements only on the diagonal.
        This is used to determine if vector lengths equal the bounding box extent.
        
        Args:
            cell: (3, 3) cell vectors as ROW vectors
            tol: Tolerance for considering off-diagonal elements as zero
            
        Returns:
            True if cell is diagonal within tolerance
        """
        for i in range(3):
            for j in range(3):
                if i != j and abs(cell[i, j]) > tol:
                    return False
        return True

    def get_cell_dimensions(self, cell: np.ndarray) -> np.ndarray:
        """Get the cell dimensions for tiling purposes.
        
        For a cell aligned with coordinate axes (diagonal matrix), returns the
        diagonal elements which are the actual cell dimensions for tiling.
        
        For any other cell (triclinic OR rotated orthogonal), returns the
        bounding box extent, which is what tiling along coordinate axes requires.
        
        This method is critical for interface generation (slab, pocket, piece modes)
        where we need to tile the ice structure. For a transformed orthogonal cell
        that is rotated in space, the vector lengths are WRONG for tiling - 
        we need the bounding box extent.
        
        Args:
            cell: (3, 3) cell vectors as ROW vectors [a, b, c]
        
        Returns:
            (3,) array of [dx, dy, dz] - the cell dimensions for tiling
        """
        if self._is_diagonal_cell(cell):
            # Diagonal cell (aligned with axes) - use diagonal elements directly
            return np.array([cell[0, 0], cell[1, 1], cell[2, 2]])
        else:
            # Triclinic OR rotated orthogonal - use bounding box extent
            return self.get_cell_extent(cell)

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
            
            # Try 2D transformations in a-c plane
            # H = [[1, 0, n1], [0, 1, 0], [n2, 0, 1]]
            # This transforms a → a + n1*c, c → n2*a + c
            for n1 in range(-20, 21):
                for n2 in range(-20, 21):
                    if n1 == 0 and n2 == 0:
                        continue
                    H = np.array([
                        [1, 0, n1],
                        [0, 1, 0],
                        [n2, 0, 1]
                    ], dtype=int)
                    det = abs(np.linalg.det(H))
                    if det <= max_multiplier:
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

    def _align_cell_to_axes(
        self, positions: np.ndarray, cell: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Rotate a cell to align with coordinate axes.

        For an orthogonal cell (90° angles) that is rotated in space, this
        rotates the cell and all positions so the cell vectors align with
        the coordinate axes. This is essential for correct tiling.

        Args:
            positions: (N, 3) atom positions in nm
            cell: (3, 3) orthogonal cell vectors as ROW vectors

        Returns:
            Tuple of (aligned_positions, aligned_cell) where aligned_cell is diagonal
        """
        # For an orthogonal cell, we can align it by finding the rotation
        # that maps the cell vectors to the coordinate axes.
        # The cell vectors a, b, c should map to [Lx, 0, 0], [0, Ly, 0], [0, 0, Lz]

        # Get cell vector lengths
        a_len = np.linalg.norm(cell[0])
        b_len = np.linalg.norm(cell[1])
        c_len = np.linalg.norm(cell[2])

        # Build the rotation matrix that transforms cell vectors to axes
        # R @ cell[0] = [a_len, 0, 0]
        # R @ cell[1] = [0, b_len, 0]
        # R @ cell[2] = [0, 0, c_len]
        # So R = diag_target @ inv(cell)
        target = np.diag([a_len, b_len, c_len])
        R = target @ np.linalg.inv(cell)

        # Verify the rotation preserves distances (should be true for orthogonal cells)
        # R should be close to an orthogonal matrix (R @ R.T = I)
        # But it might not be exactly orthogonal due to numerical precision
        # Let's use SVD to get the closest orthogonal rotation matrix

        # Actually, for an orthogonal cell (90° angles), the cell vectors are
        # mutually perpendicular, so the transformation to axes is a pure rotation
        # Apply the rotation to positions
        aligned_positions = positions @ R.T  # R.T because R acts on column vectors

        # The aligned cell is diagonal
        aligned_cell = target

        return aligned_positions, aligned_cell

    def apply_transformation(
        self, positions: np.ndarray, cell: np.ndarray, H: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply supercell transformation to positions and cell.

        The transformation replicates the unit cell according to the
        transformation matrix H. For each unit cell copy, atoms are
        placed at the appropriate fractional coordinates.

        IMPORTANT: Molecules are handled as units throughout the transformation
        to preserve molecular integrity. Individual atom handling would break
        molecules when atoms cross PBC boundaries.

        The key insight is that H transforms CELL VECTORS, not positions.
        Positions in Cartesian space should be replicated, not transformed.
        Only the cell vectors are transformed.

        For rotated orthogonal cells (like transformed Ice II), the result
        is additionally aligned with coordinate axes for correct tiling.

        Args:
            positions: (N, 3) atom positions in nm
            cell: (3, 3) cell vectors as ROW vectors in nm
            H: (3, 3) integer transformation matrix

        Returns:
            Tuple of (new_positions, new_cell)
        """
        new_cell = H @ cell

        # Get the multiplier (number of unit cell replicas)
        multiplier = int(abs(np.linalg.det(H)))

        # GenIce ice has 3 atoms per molecule (O, H, H)
        atoms_per_molecule = 3
        n_molecules = len(positions) // atoms_per_molecule

        # Instead of transforming fractional coordinates, we replicate the
        # Cartesian positions and shift them by lattice vector combinations.
        # This preserves molecular geometry exactly.

        # Find all integer combinations that span the supercell
        # For H = [[1,0,-1], [1,-2,1], [1,1,1]], we need to find all
        # lattice vectors v = i*a + j*b + k*c such that v is within the supercell
        H_inv = np.linalg.inv(H)

        # Generate all unit cell offsets
        max_elem = int(np.max(np.abs(H))) + 2

        offsets = []
        for i in range(-max_elem, max_elem + 1):
            for j in range(-max_elem, max_elem + 1):
                for k in range(-max_elem, max_elem + 1):
                    # Check if this lattice vector is within the supercell
                    v_frac = np.array([i, j, k], dtype=float)
                    v_in_super = H_inv @ v_frac
                    if np.all(v_in_super >= -1e-10) and np.all(v_in_super < 1.0 - 1e-10):
                        # Calculate the Cartesian offset
                        offset = i * cell[0] + j * cell[1] + k * cell[2]
                        offsets.append(offset)

        offsets = np.array(offsets) if offsets else np.zeros((1, 3))

        # Replicate molecules for each offset
        new_positions = []

        for mol_idx in range(n_molecules):
            start = mol_idx * atoms_per_molecule
            end = start + atoms_per_molecule
            mol_cart = positions[start:end].copy()

            for offset in offsets:
                # Shift the entire molecule by this offset
                shifted_mol = mol_cart + offset
                new_positions.extend(shifted_mol.tolist())

        new_positions = np.array(new_positions) if new_positions else np.zeros((0, 3))

        # Wrap molecules as units into the supercell
        # For each molecule, we wrap based on the CENTER position
        # and apply the same shift to all atoms in the molecule
        new_cell_inv_T = np.linalg.inv(new_cell.T)
        n_total_molecules = len(new_positions) // atoms_per_molecule

        final_positions = np.zeros_like(new_positions)
        for mol_idx in range(n_total_molecules):
            start = mol_idx * atoms_per_molecule
            end = start + atoms_per_molecule
            mol_cart = new_positions[start:end].copy()
            mol_frac = mol_cart @ new_cell_inv_T

            # Wrap based on center of mass in fractional coordinates
            # This handles molecules that span cell boundaries correctly
            center_frac = mol_frac.mean(axis=0)

            # Compute shift to bring center into [0, 1)
            shift_frac = np.zeros(3)
            for dim in range(3):
                shift_frac[dim] = -np.floor(center_frac[dim])

            # Apply shift
            mol_frac += shift_frac

            # Convert back to Cartesian
            final_positions[start:end] = mol_frac @ new_cell.T

        # CRITICAL: For rotated orthogonal cells, align with coordinate axes
        # This ensures the cell is diagonal, which is required for correct tiling
        if not self._is_diagonal_cell(new_cell):
            final_positions, new_cell = self._align_cell_to_axes(final_positions, new_cell)

            # Re-wrap after alignment to ensure all molecules are inside the aligned cell
            new_cell_inv_T = np.linalg.inv(new_cell.T)
            for mol_idx in range(n_total_molecules):
                start = mol_idx * atoms_per_molecule
                end = start + atoms_per_molecule
                mol_cart = final_positions[start:end].copy()
                mol_frac = mol_cart @ new_cell_inv_T

                # Wrap based on center of mass
                center_frac = mol_frac.mean(axis=0)
                shift_frac = np.zeros(3)
                for dim in range(3):
                    shift_frac[dim] = -np.floor(center_frac[dim])

                mol_frac += shift_frac
                final_positions[start:end] = mol_frac @ new_cell.T

        return final_positions, new_cell

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
