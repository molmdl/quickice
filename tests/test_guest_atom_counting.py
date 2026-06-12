"""Regression tests for GUEST-01: count_guest_atoms dead code and heuristic fix.

GUEST-01 (MEDIUM→LOW): count_guest_atoms() in molecule_utils.py had:
1. Dead CO2 handler (lines 102-104) that was unreachable because line 84-90
   intercepted any C-starting molecule with O atoms first (returning 13 for THF).
2. Fragile heuristic that assumes any C-starting molecule with O is THF.

The fix:
1. Removed dead CO2 code (unreachable return 3 for C+O pattern)
2. Added explicit `guest_type` parameter to count_guest_atoms() so callers
   that already know the guest type can pass it directly
3. Added guest_type parameter to _detect_guest_atoms() and _count_guest_molecules()
   in slab.py, pocket.py, piece.py; callers now extract guest_type from
   candidate metadata and pass it explicitly
4. Added comment on heuristic fallback warning about the THF assumption

These tests verify:
- Explicit guest_type returns correct atom counts
- Heuristic fallback still works for CH4 and THF
- _detect_guest_atoms correctly passes guest_type through
- Dead CO2 code is gone (no return 3 path exists)
"""

import pytest

from quickice.utils.molecule_utils import (
    count_guest_atoms,
    CH4_ATOMS_PER_MOLECULE,
    THF_ATOMS_PER_MOLECULE,
)
from quickice.structure_generation.modes.slab import (
    _detect_guest_atoms as slab_detect_guest_atoms,
    _count_guest_molecules as slab_count_guest_molecules,
)
from quickice.structure_generation.modes.pocket import (
    _detect_guest_atoms as pocket_detect_guest_atoms,
    _count_guest_molecules as pocket_count_guest_molecules,
)
from quickice.structure_generation.modes.piece import (
    _detect_guest_atoms as piece_detect_guest_atoms,
    _count_guest_molecules as piece_count_guest_molecules,
)


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════


class TestGuestAtomConstants:
    """Verify exported constants match expected values."""

    def test_ch4_atoms_per_molecule(self):
        """CH4 has 5 atoms: C + 4H."""
        assert CH4_ATOMS_PER_MOLECULE == 5

    def test_thf_atoms_per_molecule(self):
        """THF has 13 atoms: O + 2CA + 2CB + 8H."""
        assert THF_ATOMS_PER_MOLECULE == 13


# ══════════════════════════════════════════════════════════════════════════════
# Explicit guest_type parameter
# ══════════════════════════════════════════════════════════════════════════════


class TestExplicitGuestType:
    """Verify that guest_type parameter bypasses heuristics correctly."""

    def test_ch4_guest_type_returns_5(self):
        """guest_type='ch4' returns 5 regardless of atom names."""
        # Even with THF-like atom names, ch4 guest_type should return 5
        assert count_guest_atoms(["O", "CA", "CA"], 0, guest_type="ch4") == 5

    def test_thf_guest_type_returns_13(self):
        """guest_type='thf' returns 13 regardless of atom names."""
        # Even with CH4-like atom names, thf guest_type should return 13
        assert count_guest_atoms(["C", "H", "H"], 0, guest_type="thf") == 13

    def test_guest_type_with_realistic_ch4_atoms(self):
        """guest_type='ch4' with realistic CH4 atom names returns 5."""
        atoms = ["C", "H", "H", "H", "H"]
        assert count_guest_atoms(atoms, 0, guest_type="ch4") == 5

    def test_guest_type_with_realistic_thf_atoms(self):
        """guest_type='thf' with realistic THF atom names returns 13."""
        atoms = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        assert count_guest_atoms(atoms, 0, guest_type="thf") == 13

    def test_unknown_guest_type_falls_through(self):
        """Unknown guest_type falls through to heuristic (not an error)."""
        # "co2" is not a recognized guest_type, so it falls through to heuristic
        # The heuristic for C-first with O in sample returns 13 (THF)
        result = count_guest_atoms(["C", "O", "O"], 0, guest_type="co2")
        assert result == 13  # Heuristic fallback: C+O → THF


# ══════════════════════════════════════════════════════════════════════════════
# Heuristic fallback (guest_type=None)
# ══════════════════════════════════════════════════════════════════════════════


class TestHeuristicFallback:
    """Verify heuristic detection works for supported guest types when guest_type=None."""

    def test_ch4_c_first_heuristic(self):
        """CH4 with C-first ordering (C, H, H, H, H) returns 5."""
        atoms = ["C", "H", "H", "H", "H", "OW"]  # OW marks end
        assert count_guest_atoms(atoms, 0) == 5

    def test_ch4_h_first_heuristic(self):
        """CH4 with H-first ordering (H, H, H, H, C) returns 5 — GenIce2 output."""
        atoms = ["H", "H", "H", "H", "C", "OW"]
        assert count_guest_atoms(atoms, 0) == 5

    def test_thf_o_first_heuristic(self):
        """THF starting with O returns 13."""
        atoms = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        assert count_guest_atoms(atoms, 0) == 13

    def test_thf_c_first_heuristic(self):
        """THF starting with C/CA/CB that has O in sample returns 13."""
        atoms = ["CA", "CA", "CB", "CB", "H", "H", "O", "H", "H", "H", "H", "H", "H"]
        assert count_guest_atoms(atoms, 0) == 13

    def test_me_united_atom_heuristic(self):
        """United-atom Me (1 atom) returns 1."""
        assert count_guest_atoms(["Me"], 0) == 1

    def test_h2_molecule_heuristic(self):
        """H2 molecule (H, H) returns 2."""
        assert count_guest_atoms(["H", "H"], 0) == 2

    def test_water_atom_returns_zero(self):
        """Water atoms (OW, HW1, HW2, MW) return 0 — not guest atoms."""
        assert count_guest_atoms(["OW"], 0) == 0
        assert count_guest_atoms(["HW1"], 0) == 0
        assert count_guest_atoms(["HW2"], 0) == 0
        assert count_guest_atoms(["MW"], 0) == 0

    def test_guest_type_none_is_default(self):
        """guest_type=None produces same result as not passing guest_type."""
        atoms = ["C", "H", "H", "H", "H"]
        assert count_guest_atoms(atoms, 0, guest_type=None) == count_guest_atoms(atoms, 0)


# ══════════════════════════════════════════════════════════════════════════════
# Dead CO2 code removal verification
# ══════════════════════════════════════════════════════════════════════════════


class TestDeadCO2CodeRemoved:
    """Verify that the unreachable CO2 handler (return 3) no longer exists.

    Before the fix, molecule_utils.py had this dead code at lines 102-104:
        if first_atom == "C" and any(a == 'O' for a in sample[:3]):
            return 3  # C + O + O

    This was unreachable because the earlier block at lines 84-90 already
    intercepted any C/CA/CB-first molecule with O atoms, returning 13 (THF).
    The fix removed this dead code.
    """

    def test_co2_pattern_never_returns_3(self):
        """C + O + O pattern never returns 3 (the dead CO2 code is gone).

        The heuristic for C-first with O in sample now returns 13 (THF
        assumption). This is documented as a known limitation of the
        heuristic. Callers should pass guest_type explicitly if they
        need correct identification of non-CH4/non-THF guests.
        """
        result = count_guest_atoms(["C", "O", "O"], 0)
        assert result != 3, (
            "GUEST-01 regression: count_guest_atoms returned 3 for C+O+O pattern. "
            "The dead CO2 handler should have been removed."
        )

    def test_c_first_with_o_returns_thf_count(self):
        """C-first molecule with O in sample returns 13 (THF assumption).

        This is the documented behavior of the heuristic fallback.
        It would misidentify CO2 as THF, but QuickIce only supports
        CH4 and THF guests, so this is not a current bug.
        """
        result = count_guest_atoms(["C", "O", "O", "OW"], 0)
        assert result == 13  # Heuristic: C + O → assumed THF


# ══════════════════════════════════════════════════════════════════════════════
# _detect_guest_atoms with guest_type parameter
# ══════════════════════════════════════════════════════════════════════════════


class TestDetectGuestAtomsWithGuestType:
    """Verify _detect_guest_atoms passes guest_type through correctly."""

    # Test data: 2 water molecules + 1 CH4 guest
    CH4_CANDIDATE = ["OW", "HW1", "HW2", "MW", "C", "H", "H", "H", "H", "OW", "HW1", "HW2", "MW"]

    # Test data: 2 water molecules + 1 THF guest
    THF_CANDIDATE = [
        "OW", "HW1", "HW2", "MW",
        "O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H",
        "OW", "HW1", "HW2", "MW",
    ]

    @pytest.mark.parametrize("detect_fn", [
        slab_detect_guest_atoms,
        pocket_detect_guest_atoms,
        piece_detect_guest_atoms,
    ])
    def test_ch4_guest_type_detection(self, detect_fn):
        """_detect_guest_atoms with guest_type='ch4' correctly identifies CH4 guests."""
        water_idx, guest_idx = detect_fn(
            self.CH4_CANDIDATE, atoms_per_mol=4, guest_type="ch4"
        )
        # Water at indices 0-3, 9-12; Guest at indices 4-8
        assert water_idx == [0, 1, 2, 3, 9, 10, 11, 12]
        assert guest_idx == [4, 5, 6, 7, 8]

    @pytest.mark.parametrize("detect_fn", [
        slab_detect_guest_atoms,
        pocket_detect_guest_atoms,
        piece_detect_guest_atoms,
    ])
    def test_thf_guest_type_detection(self, detect_fn):
        """_detect_guest_atoms with guest_type='thf' correctly identifies THF guests."""
        water_idx, guest_idx = detect_fn(
            self.THF_CANDIDATE, atoms_per_mol=4, guest_type="thf"
        )
        # Water at indices 0-3, 17-20; Guest at indices 4-16 (13 atoms)
        assert water_idx == [0, 1, 2, 3, 17, 18, 19, 20]
        assert guest_idx == list(range(4, 17))

    @pytest.mark.parametrize("detect_fn", [
        slab_detect_guest_atoms,
        pocket_detect_guest_atoms,
        piece_detect_guest_atoms,
    ])
    def test_guest_type_none_backward_compatible(self, detect_fn):
        """_detect_guest_atoms with guest_type=None (default) works as before."""
        water_idx, guest_idx = detect_fn(
            self.CH4_CANDIDATE, atoms_per_mol=4
        )
        # Should produce same result regardless of whether guest_type is None or not passed
        water_idx2, guest_idx2 = detect_fn(
            self.CH4_CANDIDATE, atoms_per_mol=4, guest_type=None
        )
        assert water_idx == water_idx2
        assert guest_idx == guest_idx2


# ══════════════════════════════════════════════════════════════════════════════
# _count_guest_molecules with guest_type parameter
# ══════════════════════════════════════════════════════════════════════════════


class TestCountGuestMoleculesWithGuestType:
    """Verify _count_guest_molecules passes guest_type through correctly."""

    CH4_GUEST_INDICES = [4, 5, 6, 7, 8]  # 1 CH4 molecule (5 atoms)
    THF_GUEST_INDICES = list(range(4, 17))  # 1 THF molecule (13 atoms)

    # 2 CH4 molecules back-to-back
    TWO_CH4_ATOMS = ["OW", "HW1", "HW2", "MW", "C", "H", "H", "H", "H", "C", "H", "H", "H", "H", "OW", "HW1", "HW2", "MW"]
    TWO_CH4_INDICES = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

    @pytest.mark.parametrize("count_fn", [
        slab_count_guest_molecules,
        pocket_count_guest_molecules,
        piece_count_guest_molecules,
    ])
    def test_count_ch4_with_guest_type(self, count_fn):
        """_count_guest_molecules with guest_type='ch4' counts correctly."""
        result = count_fn(
            ["C", "H", "H", "H", "H"],  # Atom names don't matter for guest_type
            self.CH4_GUEST_INDICES,
            guest_type="ch4",
        )
        assert result == 1

    @pytest.mark.parametrize("count_fn", [
        slab_count_guest_molecules,
        pocket_count_guest_molecules,
        piece_count_guest_molecules,
    ])
    def test_count_thf_with_guest_type(self, count_fn):
        """_count_guest_molecules with guest_type='thf' counts correctly."""
        result = count_fn(
            ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"],
            self.THF_GUEST_INDICES,
            guest_type="thf",
        )
        assert result == 1

    @pytest.mark.parametrize("count_fn", [
        slab_count_guest_molecules,
        pocket_count_guest_molecules,
        piece_count_guest_molecules,
    ])
    def test_count_two_ch4_molecules(self, count_fn):
        """_count_guest_molecules counts 2 CH4 molecules with guest_type='ch4'."""
        result = count_fn(
            self.TWO_CH4_ATOMS,
            self.TWO_CH4_INDICES,
            guest_type="ch4",
        )
        assert result == 2

    @pytest.mark.parametrize("count_fn", [
        slab_count_guest_molecules,
        pocket_count_guest_molecules,
        piece_count_guest_molecules,
    ])
    def test_count_heuristic_fallback(self, count_fn):
        """_count_guest_molecules with guest_type=None uses heuristic."""
        result = count_fn(
            self.TWO_CH4_ATOMS,
            self.TWO_CH4_INDICES,
            guest_type=None,
        )
        assert result == 2  # Heuristic correctly identifies both CH4 molecules


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for count_guest_atoms."""

    def test_start_beyond_list_length(self):
        """Start index beyond list length returns 0."""
        assert count_guest_atoms(["C", "H"], 5) == 0
        assert count_guest_atoms(["C", "H"], 5, guest_type="ch4") == 0

    def test_empty_atom_names(self):
        """Empty atom_names list returns 0."""
        assert count_guest_atoms([], 0) == 0
        assert count_guest_atoms([], 0, guest_type="ch4") == 0

    def test_start_at_list_length(self):
        """Start index exactly at list length returns 0."""
        assert count_guest_atoms(["C", "H"], 2) == 0

    def test_single_me_atom_with_guest_type(self):
        """Me (united-atom) still works with guest_type=None (heuristic)."""
        # guest_type="ch4" would return 5, but Me is actually 1 atom
        # The heuristic correctly returns 1 for "Me"
        assert count_guest_atoms(["Me"], 0) == 1
