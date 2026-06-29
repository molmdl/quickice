"""Tests for metadata-driven _build_molecule_index.

Validates:
- CH4 identified from HydrateConfig.guest_atom_labels (not hardcoded pattern)
- THF identified from HydrateConfig.guest_atom_labels (not hardcoded pattern)
- THF residue grouping when residue_names match guest_type.upper()
- Guest identified BEFORE water (THF "O" not misidentified as 3-site water)
- config=None preserves backward-compatible pattern matching
- Unknown atom types produce "unknown" MoleculeIndex with warning
"""

import logging

import numpy as np
import pytest

from quickice.structure_generation.types import (
    HydrateConfig,
    MoleculeIndex,
)
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_generator() -> HydrateStructureGenerator:
    """Create a generator instance for testing (no GenIce2 import needed)."""
    return HydrateStructureGenerator()


def _make_positions(n_atoms: int) -> np.ndarray:
    """Create dummy positions array of given size."""
    return np.zeros((n_atoms, 3), dtype=np.float64)


# ── CH4 identification via metadata ──────────────────────────────────────

class TestCH4MetadataIdentification:
    """CH4 identified from HydrateConfig.guest_atom_labels, not hardcoded patterns."""

    def test_ch4_identification(self):
        """All-atom methane (C, H, H, H, H) identified via config metadata."""
        gen = _make_generator()
        atom_names = ["OW", "HW1", "HW2", "MW", "C", "H", "H", "H", "H", "OW", "HW1", "HW2", "MW"]
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="ch4")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=config
        )

        assert len(molecule_index) == 3
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 5, "ch4")
        assert molecule_index[2] == MoleculeIndex(9, 4, "water")

    def test_ch4_multiple_guests(self):
        """Multiple CH4 molecules identified via metadata."""
        gen = _make_generator()
        # 2 water + 2 CH4 + 1 water
        atom_names = [
            "OW", "HW1", "HW2", "MW",          # water 0
            "C", "H", "H", "H", "H",           # ch4 0
            "OW", "HW1", "HW2", "MW",          # water 1
            "C", "H", "H", "H", "H",           # ch4 1
            "OW", "HW1", "HW2", "MW",          # water 2
        ]
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="ch4")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=config
        )

        assert len(molecule_index) == 5
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 5, "ch4")
        assert molecule_index[2] == MoleculeIndex(9, 4, "water")
        assert molecule_index[3] == MoleculeIndex(13, 5, "ch4")
        assert molecule_index[4] == MoleculeIndex(18, 4, "water")


# ── THF identification via metadata ─────────────────────────────────────

class TestTHFMetadataIdentification:
    """THF identified from HydrateConfig.guest_atom_labels, not hardcoded patterns."""

    def test_thf_identification(self):
        """THF (13 atoms) identified via atom-label sequence matching."""
        gen = _make_generator()
        # TIP4P water + THF + TIP4P water
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        atom_names = ["OW", "HW1", "HW2", "MW"] + thf_labels + ["OW", "HW1", "HW2", "MW"]
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="thf")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=config
        )

        assert len(molecule_index) == 3
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 13, "thf")
        assert molecule_index[2] == MoleculeIndex(17, 4, "water")


# ── THF residue grouping ────────────────────────────────────────────────

class TestTHFResidueGrouping:
    """THF identified by residue grouping when residue_names available."""

    def test_thf_residue_grouping(self):
        """THF grouped by residue_seq_nums when residue name matches guest_type.upper()."""
        gen = _make_generator()
        # 2 water + 1 THF (13 atoms, residue "THF", seq num 3) + 1 water
        n_water = 3
        n_thf = 1
        thf_atom_count = 13
        total_atoms = n_water * 4 + n_thf * thf_atom_count

        atom_names = []
        residue_names = []
        residue_seq_nums = []

        # Water 1 (residue SOL, seq 1)
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
        residue_names.extend(["SOL", "SOL", "SOL", "SOL"])
        residue_seq_nums.extend([1, 1, 1, 1])

        # THF (residue THF, seq 2) — GenIce2 output format
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        atom_names.extend(thf_labels)
        residue_names.extend(["THF"] * thf_atom_count)
        residue_seq_nums.extend([2] * thf_atom_count)

        # Water 2 (residue SOL, seq 3)
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
        residue_names.extend(["SOL", "SOL", "SOL", "SOL"])
        residue_seq_nums.extend([3, 3, 3, 3])

        # Water 3 (residue SOL, seq 4)
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
        residue_names.extend(["SOL", "SOL", "SOL", "SOL"])
        residue_seq_nums.extend([4, 4, 4, 4])

        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="thf")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, residue_names, residue_seq_nums, config=config
        )

        assert len(molecule_index) == 4
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 13, "thf")
        assert molecule_index[2] == MoleculeIndex(17, 4, "water")
        assert molecule_index[3] == MoleculeIndex(21, 4, "water")

    def test_thf_multiple_residue_groups(self):
        """Multiple THF molecules grouped by distinct residue seq nums."""
        gen = _make_generator()
        thf_atom_count = 13
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]

        atom_names = []
        residue_names = []
        residue_seq_nums = []

        # Water 1 (seq 1)
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
        residue_names.extend(["SOL"] * 4)
        residue_seq_nums.extend([1] * 4)

        # THF 1 (seq 2)
        atom_names.extend(thf_labels)
        residue_names.extend(["THF"] * thf_atom_count)
        residue_seq_nums.extend([2] * thf_atom_count)

        # THF 2 (seq 3)
        atom_names.extend(thf_labels)
        residue_names.extend(["THF"] * thf_atom_count)
        residue_seq_nums.extend([3] * thf_atom_count)

        # Water 2 (seq 4)
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
        residue_names.extend(["SOL"] * 4)
        residue_seq_nums.extend([4] * 4)

        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="thf")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, residue_names, residue_seq_nums, config=config
        )

        assert len(molecule_index) == 4
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 13, "thf")
        assert molecule_index[2] == MoleculeIndex(17, 13, "thf")
        assert molecule_index[3] == MoleculeIndex(30, 4, "water")


# ── Guest identified before water ────────────────────────────────────────

class TestGuestBeforeWater:
    """Guest molecules checked BEFORE water patterns to avoid misidentification."""

    def test_thf_o_not_misidentified_as_water(self):
        """THF's first atom 'O' must be identified as THF, not 3-site water.

        This is the KEY correctness property: without metadata-driven priority,
        THF's oxygen atom would match the 3-site water pattern (O, H, H).
        With metadata, guest is checked first, so THF's "O" is correctly
        identified as a guest signature atom.
        """
        gen = _make_generator()
        # Just THF atoms (no water) — the "O" at index 0 could be mistaken
        # for 3-site water if water check happens first
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        atom_names = thf_labels
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="thf")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=config
        )

        assert len(molecule_index) == 1
        assert molecule_index[0] == MoleculeIndex(0, 13, "thf")
        assert molecule_index[0].mol_type != "water"

    def test_thf_between_water_not_misidentified(self):
        """THF surrounded by water — the O at start of THF is guest, not water."""
        gen = _make_generator()
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        atom_names = ["OW", "HW1", "HW2", "MW"] + thf_labels + ["OW", "HW1", "HW2", "MW"]
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="thf")

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=config
        )

        # No molecule should be misidentified as 3-site water
        for mol in molecule_index:
            if mol.mol_type == "water":
                # Water must be TIP4P (4 atoms), not 3-site (3 atoms)
                # because THF's O was correctly caught by guest check
                assert mol.count == 4, "Water should be TIP4P, not 3-site"


# ── Backward compatibility (config=None) ─────────────────────────────────

class TestConfigNoneBackwardCompat:
    """config=None preserves existing pattern-matching behavior."""

    def test_config_none_tip4p_water(self):
        """TIP4P water identified with config=None (pattern matching)."""
        gen = _make_generator()
        atom_names = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        positions = _make_positions(len(atom_names))

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=None
        )

        assert len(molecule_index) == 2
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 4, "water")

    def test_config_none_ch4_pattern_matching(self):
        """CH4 identified by hardcoded C+4H pattern with config=None."""
        gen = _make_generator()
        atom_names = ["C", "H", "H", "H", "H"]
        positions = _make_positions(len(atom_names))

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=None
        )

        assert len(molecule_index) == 1
        assert molecule_index[0] == MoleculeIndex(0, 5, "ch4")

    def test_config_none_thf_residue_matching(self):
        """THF identified by hardcoded residue check with config=None."""
        gen = _make_generator()
        thf_atom_count = 13
        thf_labels = ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        atom_names = thf_labels
        residue_names = ["THF"] * thf_atom_count
        residue_seq_nums = [1] * thf_atom_count
        positions = _make_positions(len(atom_names))

        molecule_index = gen._build_molecule_index(
            atom_names, positions, residue_names, residue_seq_nums, config=None
        )

        assert len(molecule_index) == 1
        assert molecule_index[0] == MoleculeIndex(0, 13, "thf")

    def test_config_none_ions(self):
        """Ions identified with config=None."""
        gen = _make_generator()
        atom_names = ["OW", "HW1", "HW2", "MW", "NA", "CL"]
        positions = _make_positions(len(atom_names))

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=None
        )

        assert len(molecule_index) == 3
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 1, "na")
        assert molecule_index[2] == MoleculeIndex(5, 1, "cl")

    def test_config_none_united_atom_methane(self):
        """United-atom methane (Me) identified with config=None."""
        gen = _make_generator()
        atom_names = ["Me"]
        positions = _make_positions(len(atom_names))

        molecule_index = gen._build_molecule_index(
            atom_names, positions, config=None
        )

        assert len(molecule_index) == 1
        assert molecule_index[0] == MoleculeIndex(0, 1, "ch4")


# ── Unknown atom handling ────────────────────────────────────────────────

class TestUnknownAtomWarning:
    """Unknown atom types produce 'unknown' MoleculeIndex with warning."""

    def test_unknown_atom_type(self, caplog):
        """Unrecognized atom produces (i, 1, 'unknown') with warning."""
        gen = _make_generator()
        atom_names = ["OW", "HW1", "HW2", "MW", "XX", "OW", "HW1", "HW2", "MW"]
        positions = _make_positions(len(atom_names))
        config = HydrateConfig(guest_type="ch4")

        with caplog.at_level(logging.WARNING, logger="quickice.structure_generation.hydrate_generator"):
            molecule_index = gen._build_molecule_index(
                atom_names, positions, config=config
            )

        assert len(molecule_index) == 3
        assert molecule_index[0] == MoleculeIndex(0, 4, "water")
        assert molecule_index[1] == MoleculeIndex(4, 1, "unknown")
        assert molecule_index[2] == MoleculeIndex(5, 4, "water")

        # Verify warning was emitted via logging
        unknown_warnings = [
            r for r in caplog.records
            if "Unknown atom type" in r.message or "unknown" in r.message.lower()
        ]
        assert len(unknown_warnings) > 0, "Expected warning about unknown atom type"
