"""Test water atom count invariant after overlap removal.

Verifies that after any overlap removal step, the water atom count is
always divisible by 4 (TIP4P has 4 atoms per water molecule: OW, HW1, HW2, MW).

This invariant was added in Batch 3 (FRAG-02) as assertions in slab.py.
These tests verify the invariant holds for the underlying functions that
slab.py calls, ensuring the overlap resolver cannot produce partial molecules.

Two levels of testing:
1. Direct: remove_overlapping_molecules + filter_atom_names (no GenIce2 needed)
2. Guest detection: _detect_guest_atoms with mock atom name lists
"""

import numpy as np
import pytest

from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    filter_atom_names,
)
from quickice.structure_generation.modes.slab import _detect_guest_atoms


class TestWaterAtomCountDivisibleByFour:
    """Invariant: water atom count % 4 == 0 after overlap removal.

    TIP4P water has 4 atoms per molecule (OW, HW1, HW2, MW).
    remove_overlapping_molecules always removes whole molecules, so
    if input atom count is divisible by 4, output must be too.
    """

    def _make_water_positions(self, n_molecules: int) -> np.ndarray:
        """Create n_molecules water molecule positions (4 atoms each).

        Each molecule's OW is placed at (i, 0, 0) with small offsets
        for HW1, HW2, MW to give realistic-ish positions.
        """
        positions = []
        for i in range(n_molecules):
            x = float(i)
            positions.append([x, 0.0, 0.0])       # OW
            positions.append([x + 0.08, 0.06, 0.0])  # HW1
            positions.append([x - 0.08, 0.06, 0.0])  # HW2
            positions.append([x, 0.015, 0.0])      # MW
        return np.array(positions)

    def test_no_overlap_count_divisible_by_4(self):
        """No overlap removal: count should stay divisible by 4."""
        positions = self._make_water_positions(10)
        overlapping = set()
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n_remaining == 10

    def test_remove_one_molecule_count_divisible_by_4(self):
        """After removing 1 molecule, count should still be divisible by 4."""
        positions = self._make_water_positions(10)
        overlapping = {3}
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert len(result) == 36  # 9 molecules * 4 atoms
        assert n_remaining == 9

    def test_remove_multiple_molecules_count_divisible_by_4(self):
        """After removing multiple scattered molecules, count divisible by 4."""
        positions = self._make_water_positions(20)
        overlapping = {0, 5, 10, 19}
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n_remaining == 16
        assert len(result) == 64

    def test_remove_all_molecules_count_is_zero(self):
        """After removing all molecules, count is 0 (trivially divisible by 4)."""
        positions = self._make_water_positions(5)
        overlapping = {0, 1, 2, 3, 4}
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) == 0
        assert len(result) % 4 == 0

    def test_remove_odd_number_of_molecules_from_even_total(self):
        """Remove 3 molecules from 10: remaining 7 * 4 = 28 atoms."""
        positions = self._make_water_positions(10)
        overlapping = {1, 4, 7}
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n_remaining == 7

    def test_large_overlap_removal_invariant(self):
        """Large-scale: remove half of 100 molecules, invariant holds."""
        positions = self._make_water_positions(100)
        overlapping = set(range(0, 100, 2))  # Remove every even-indexed molecule
        result, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n_remaining == 50
        assert len(result) == 200

    def test_consecutive_overlap_removals_invariant(self):
        """Two rounds of overlap removal: invariant holds after each.

        This simulates the two-phase overlap removal in slab.py:
        1. Ice-water overlap removal
        2. Guest-water overlap removal (applied to already-trimmed positions)
        """
        positions = self._make_water_positions(20)

        # Phase 1: remove some molecules (ice-water overlap)
        overlapping1 = {2, 5, 8}
        result1, n1 = remove_overlapping_molecules(
            positions, overlapping1, atoms_per_molecule=4
        )
        assert len(result1) % 4 == 0, (
            f"After ice-water overlap removal: {len(result1)} not divisible by 4"
        )

        # Phase 2: remove more molecules from remaining (guest-water overlap)
        # Note: indices are now relative to the trimmed array
        overlapping2 = {0, 3}
        result2, n2 = remove_overlapping_molecules(
            result1, overlapping2, atoms_per_molecule=4
        )
        assert len(result2) % 4 == 0, (
            f"After guest-water overlap removal: {len(result2)} not divisible by 4"
        )


class TestAtomNamesConsistentAfterRemoval:
    """After overlap removal, atom_names length must match positions length."""

    def _make_water_data(self, n_molecules: int):
        """Create positions and atom_names for n water molecules."""
        positions = []
        for i in range(n_molecules):
            x = float(i)
            positions.append([x, 0.0, 0.0])
            positions.append([x + 0.08, 0.06, 0.0])
            positions.append([x - 0.08, 0.06, 0.0])
            positions.append([x, 0.015, 0.0])
        positions = np.array(positions)
        atom_names = ["OW", "HW1", "HW2", "MW"] * n_molecules
        return positions, atom_names

    def test_positions_and_atom_names_same_length_after_removal(self):
        """Filtered positions and filtered atom_names must have same length."""
        positions, atom_names = self._make_water_data(10)
        overlapping = {2, 5, 8}

        filtered_positions, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        filtered_names = filter_atom_names(
            atom_names, overlapping, atoms_per_molecule=4
        )

        assert len(filtered_positions) == len(filtered_names), (
            f"Length mismatch: positions={len(filtered_positions)}, "
            f"atom_names={len(filtered_names)}"
        )

    def test_atom_names_divisible_by_4_after_removal(self):
        """Filtered atom_names length must be divisible by 4."""
        _, atom_names = self._make_water_data(10)
        overlapping = {1, 3, 7}

        filtered_names = filter_atom_names(
            atom_names, overlapping, atoms_per_molecule=4
        )

        assert len(filtered_names) % 4 == 0, (
            f"Filtered atom_names length {len(filtered_names)} not divisible by 4"
        )

    def test_two_phase_removal_consistent(self):
        """After two overlap removal phases, positions and names stay consistent."""
        positions, atom_names = self._make_water_data(20)

        # Phase 1: ice-water overlap
        overlapping1 = {0, 5, 10, 15}
        filtered_pos1, n1 = remove_overlapping_molecules(
            positions, overlapping1, atoms_per_molecule=4
        )
        filtered_names1 = filter_atom_names(
            atom_names, overlapping1, atoms_per_molecule=4
        )
        assert len(filtered_pos1) == len(filtered_names1)
        assert len(filtered_pos1) % 4 == 0

        # Phase 2: guest-water overlap (indices relative to phase 1 result)
        overlapping2 = {1, 3}
        filtered_pos2, n2 = remove_overlapping_molecules(
            filtered_pos1, overlapping2, atoms_per_molecule=4
        )
        filtered_names2 = filter_atom_names(
            filtered_names1, overlapping2, atoms_per_molecule=4
        )
        assert len(filtered_pos2) == len(filtered_names2)
        assert len(filtered_pos2) % 4 == 0


class TestGuestDetectionDoesNotCorruptWaterCount:
    """_detect_guest_atoms must not misclassify water molecules as guests.

    If water molecules are misclassified as guests and removed from the
    water array, the remaining water atom count might not be divisible by 4.
    """

    def test_pure_water_all_classified_as_water(self):
        """Pure TIP4P water: all atoms should be water, no guests."""
        atom_names = ["OW", "HW1", "HW2", "MW"] * 10  # 10 water molecules
        water_indices, guest_indices = _detect_guest_atoms(atom_names, atoms_per_mol=4)

        # All 40 atoms should be water
        assert len(water_indices) == 40
        assert len(guest_indices) == 0

    def test_water_with_ch4_guest_correct_separation(self):
        """Water + CH4 guest: water atoms stay water, guest atoms are guest.

        8 water molecules (32 atoms) + 2 CH4 (10 atoms) = 42 total.
        """
        # 8 water molecules
        water_names = ["OW", "HW1", "HW2", "MW"] * 8
        # 2 CH4 molecules (C-first format: C + 4H each)
        guest_names = ["C", "H", "H", "H", "H"] * 2
        atom_names = water_names + guest_names

        water_indices, guest_indices = _detect_guest_atoms(atom_names, atoms_per_mol=4)

        # Water: 8 molecules * 4 atoms = 32 indices
        assert len(water_indices) == 32
        # Guest: 2 CH4 * 5 atoms = 10 indices
        assert len(guest_indices) == 10

        # Water count must be divisible by 4
        assert len(water_indices) % 4 == 0

    def test_water_with_me_guest_correct_separation(self):
        """Water + united-atom Me (1-atom) guests: correct separation.

        10 water molecules (40 atoms) + 3 Me (3 atoms) = 43 total.
        """
        water_names = ["OW", "HW1", "HW2", "MW"] * 10
        # Insert Me guests between water molecules
        atom_names = (
            water_names[:20]  # 5 water molecules
            + ["Me", "Me", "Me"]  # 3 Me guest atoms
            + water_names[20:]   # 5 more water molecules
        )

        water_indices, guest_indices = _detect_guest_atoms(atom_names, atoms_per_mol=4)

        # Water indices should all be divisible by... actually we just check count
        assert len(water_indices) % 4 == 0, (
            f"Water atom count {len(water_indices)} not divisible by 4 "
            f"after guest detection"
        )

    def test_no_ow_misclassified_as_guest(self):
        """Water molecules starting with OW are never classified as guests.

        Even if they appear at unexpected positions, OW-prefixed molecules
        should always be classified as water.
        """
        atom_names = ["OW", "HW1", "HW2", "MW"] * 5
        water_indices, guest_indices = _detect_guest_atoms(atom_names, atoms_per_mol=4)

        # Verify NO water atom is in guest_indices
        for idx in water_indices:
            assert idx not in guest_indices, (
                f"Atom at index {idx} ({atom_names[idx]}) classified as both "
                f"water AND guest"
            )

        # Verify no OW atoms in guest list
        guest_atom_names = [atom_names[i] for i in guest_indices]
        assert "OW" not in guest_atom_names, (
            f"OW atom found in guest classification: {guest_atom_names}"
        )

    def test_water_count_divisible_after_complex_mix(self):
        """Complex mixture: water count invariant holds regardless of guests.

        Pattern: water, guest, water, guest, water — interleaved.
        """
        # 3 water blocks of 4 molecules each, with Me guests in between
        atom_names = (
            ["OW", "HW1", "HW2", "MW"] * 4   # 4 water molecules
            + ["Me"]                            # 1 Me guest
            + ["OW", "HW1", "HW2", "MW"] * 4   # 4 water molecules
            + ["Me"]                            # 1 Me guest
            + ["OW", "HW1", "HW2", "MW"] * 4   # 4 water molecules
        )

        water_indices, guest_indices = _detect_guest_atoms(atom_names, atoms_per_mol=4)

        # Water: 12 molecules * 4 atoms = 48
        assert len(water_indices) % 4 == 0, (
            f"Water atom count {len(water_indices)} not divisible by 4"
        )
        assert len(water_indices) == 48


class TestDetectOverlapsProducesValidMoleculeIndices:
    """detect_overlaps should produce indices that, when used with
    remove_overlapping_molecules, maintain the divisible-by-4 invariant."""

    def test_overlapping_molecules_near_ice_surface(self):
        """Simulate ice-water overlap: some water molecules near ice O atoms.

        Create ice O positions and water O positions with some overlapping.
        The detected overlap indices should produce valid molecule removal.
        """
        # Ice oxygens: 3 atoms along X
        ice_o = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
        ])

        # Water oxygens: 5 molecules, 2 overlap with ice (indices 0 and 2)
        water_o = np.array([
            [0.01, 0.0, 0.5],   # Overlaps with ice O at [0,0,0]
            [5.0, 0.0, 0.5],    # No overlap
            [1.02, 0.0, 0.5],   # Overlaps with ice O at [1,0,0]
            [6.0, 0.0, 0.5],    # No overlap
            [7.0, 0.0, 0.5],    # No overlap
        ])

        box = np.array([10.0, 10.0, 10.0])
        threshold = 0.25  # nm

        overlapping = detect_overlaps(ice_o, water_o, box, threshold)

        # Overlapping indices should be valid molecule indices
        for idx in overlapping:
            assert 0 <= idx < 5, f"Invalid molecule index: {idx}"

        # If we remove overlapping molecules, count should be divisible by 4
        n_water_molecules = 5
        water_positions = np.zeros((n_water_molecules * 4, 3))
        water_atom_names = ["OW", "HW1", "HW2", "MW"] * n_water_molecules

        filtered_pos, n_remaining = remove_overlapping_molecules(
            water_positions, overlapping, atoms_per_molecule=4
        )
        filtered_names = filter_atom_names(
            water_atom_names, overlapping, atoms_per_molecule=4
        )

        assert len(filtered_pos) % 4 == 0
        assert len(filtered_pos) == len(filtered_names)

    def test_no_false_positives_from_overlaps(self):
        """Non-overlapping positions should produce empty overlap set."""
        ice_o = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        water_o = np.array([[5.0, 5.0, 5.0], [6.0, 6.0, 6.0], [7.0, 7.0, 7.0]])
        box = np.array([10.0, 10.0, 10.0])

        overlapping = detect_overlaps(ice_o, water_o, box, threshold_nm=0.25)
        assert len(overlapping) == 0

        # No overlap -> no removal -> count stays divisible by 4
        n_water = 3
        water_positions = np.zeros((n_water * 4, 3))
        result, n = remove_overlapping_molecules(
            water_positions, overlapping, atoms_per_molecule=4
        )
        assert len(result) % 4 == 0
        assert n == n_water
