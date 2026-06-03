"""End-to-end tests for ice structure generation (Workflow 2).

Tests the ice generation pipeline: lookup_phase → IceStructureGenerator → Candidate.
Covers all 6 orthogonal ice phases and structural invariants.
"""

import numpy as np
import pytest

from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.types import Candidate

# Re-use phase conditions from conftest (kept here for self-contained parametrize)
PHASE_CONDITIONS = {
    "ice_ih": (250, 0.1),
    "ice_ic": (100, 0.1),
    "ice_iii": (250, 300),
    "ice_vi": (250, 700),
    "ice_vii": (300, 2500),
    "ice_viii": (100, 5000),
}


class TestIceIhGeneration:
    """Tests for the baseline Ice Ih generation path."""

    def test_ice_ih_generation_produces_valid_candidate(self, ice_ih_candidate):
        """Ice Ih generation should produce a valid Candidate with correct fields."""
        candidate = ice_ih_candidate

        # Must be a Candidate instance
        assert isinstance(candidate, Candidate)

        # positions shape: (N_atoms, 3)
        assert candidate.positions.ndim == 2
        assert candidate.positions.shape[1] == 3
        assert len(candidate.positions) > 0

        # cell shape: (3, 3)
        assert candidate.cell.shape == (3, 3)

        # Positive molecule count
        assert candidate.nmolecules > 0

        # Correct phase_id
        assert candidate.phase_id == "ice_ih"

        # All positions finite
        assert np.all(np.isfinite(candidate.positions))


class TestAllOrthogonalPhases:
    """Tests for all 6 orthogonal ice phases supported by GenIce."""

    @pytest.mark.parametrize(
        "phase_id",
        ["ice_ih", "ice_ic", "ice_iii", "ice_vi", "ice_vii", "ice_viii"],
    )
    def test_all_orthogonal_phases_generate_successfully(self, phase_id):
        """Each orthogonal ice phase should generate a valid structure."""
        T, P = PHASE_CONDITIONS[phase_id]
        phase_info = lookup_phase(T, P)

        # Verify lookup returns expected phase
        assert phase_info["phase_id"] == phase_id, (
            f"lookup_phase({T}, {P}) returned {phase_info['phase_id']}, expected {phase_id}"
        )

        # Generate with small target (96 molecules)
        gen = IceStructureGenerator(phase_info, 96)
        candidates = gen.generate_all(1, base_seed=42)

        # Must produce at least 1 candidate
        assert len(candidates) >= 1

        candidate = candidates[0]

        # Structural invariants
        assert candidate.positions.ndim == 2
        assert candidate.positions.shape[1] == 3
        assert candidate.cell.shape == (3, 3)
        assert candidate.nmolecules > 0
        assert candidate.phase_id == phase_id
        assert np.all(np.isfinite(candidate.positions))
        assert len(candidate.atom_names) == len(candidate.positions)

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "phase_id",
        ["ice_vii", "ice_viii"],
    )
    def test_high_pressure_phases_generate(self, phase_id):
        """High-pressure phases (VII, VIII) should still generate correctly.

        Marked slow because these use larger GenIce unit cells.
        """
        T, P = PHASE_CONDITIONS[phase_id]
        phase_info = lookup_phase(T, P)
        gen = IceStructureGenerator(phase_info, 96)
        candidates = gen.generate_all(1, base_seed=42)
        assert len(candidates) >= 1
        assert candidates[0].phase_id == phase_id


class TestIceCandidateAtomCount:
    """Tests for atom count consistency with water model."""

    def test_ice_candidate_has_correct_atom_count(self, ice_ih_candidate):
        """TIP3P ice should have 3 atoms per molecule (O, H, H).

        GenIce generates ice with TIP3P water model (3 atoms: O, H, H).
        The total atom count should equal nmolecules * 3.
        """
        candidate = ice_ih_candidate
        atoms_per_molecule = 3  # TIP3P: O, H, H
        expected_atoms = candidate.nmolecules * atoms_per_molecule

        assert len(candidate.positions) == expected_atoms, (
            f"Expected {expected_atoms} atoms ({candidate.nmolecules} mol × {atoms_per_molecule} atoms), "
            f"got {len(candidate.positions)}"
        )

        # atom_names length must match positions length
        assert len(candidate.atom_names) == len(candidate.positions), (
            f"atom_names length ({len(candidate.atom_names)}) != "
            f"positions length ({len(candidate.positions)})"
        )


class TestIceCellVolume:
    """Tests for cell matrix properties."""

    def test_ice_cell_has_positive_volume(self, ice_ih_candidate):
        """Cell determinant should be positive (right-handed cell)."""
        candidate = ice_ih_candidate
        volume = np.linalg.det(candidate.cell)
        assert volume > 0, f"Cell volume (det) = {volume}, expected > 0"


class TestIcePositionsInCell:
    """Tests for atom positions within cell boundaries."""

    def test_ice_positions_within_cell(self, ice_ih_candidate):
        """All atom positions should be within or near the cell boundaries.

        Uses fractional coordinates: positions @ cell_inv should be in [0, 1) + tolerance.
        GenIce may place atoms slightly outside [0, L) due to rounding, so
        we allow a small tolerance.
        """
        candidate = ice_ih_candidate
        cell = candidate.cell

        # Convert to fractional coordinates
        cell_inv = np.linalg.inv(cell)
        frac_coords = candidate.positions @ cell_inv

        # Allow small numerical tolerance (GenIce can have atoms at ~1.00001)
        tolerance = 0.01
        assert np.all(frac_coords >= -tolerance), (
            f"Some atoms have fractional coords < -{tolerance}: "
            f"min = {frac_coords.min():.6f}"
        )
        assert np.all(frac_coords <= 1.0 + tolerance), (
            f"Some atoms have fractional coords > 1+{tolerance}: "
            f"max = {frac_coords.max():.6f}"
        )
