"""End-to-end tests for hydrate structure generation (Workflow 3).

Tests the hydrate generation pipeline:
  HydrateStructureGenerator().generate(HydrateConfig(...)) → HydrateStructure

Covers sI/sII × CH4/THF combinations, to_candidate conversion,
molecule index tracking, guest atom counts, and error handling.
"""

import numpy as np
import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateStructure,
    Candidate,
    MOLECULE_TYPE_INFO,
)


class TestHydrateS1Ch4Generation:
    """Tests for sI + CH4 hydrate — the most common hydrate type."""

    def test_hydrate_sI_ch4_generation(self, hydrate_sI_ch4_structure):
        """sI + CH4 hydrate should have guests, water, positions, and molecule_index."""
        structure = hydrate_sI_ch4_structure

        # Must be a HydrateStructure
        assert isinstance(structure, HydrateStructure)

        # Must have guests and water
        assert structure.guest_count > 0, "sI+CH4 should have guest molecules"
        assert structure.water_count > 0, "sI+CH4 should have water molecules"

        # Positions array valid
        assert len(structure.positions) > 0
        assert structure.positions.ndim == 2
        assert structure.positions.shape[1] == 3

        # molecule_index has ch4 type entries
        mol_types = {m.mol_type for m in structure.molecule_index}
        assert "ch4" in mol_types, f"Expected 'ch4' in molecule types, got {mol_types}"
        assert "water" in mol_types, f"Expected 'water' in molecule types, got {mol_types}"


class TestHydrateS1ThfGeneration:
    """Tests for sI + THF hydrate."""

    def test_hydrate_sI_thf_generation(self, hydrate_sI_thf_structure):
        """sI + THF hydrate should have THF guests with 13 atoms each."""
        structure = hydrate_sI_thf_structure

        assert structure.guest_count > 0
        assert structure.water_count > 0
        assert len(structure.positions) > 0

        # molecule_index has thf type entries
        mol_types = {m.mol_type for m in structure.molecule_index}
        assert "thf" in mol_types, f"Expected 'thf' in molecule types, got {mol_types}"
        assert "water" in mol_types


class TestHydrateS2Ch4Generation:
    """Tests for sII + CH4 hydrate."""

    def test_hydrate_sII_ch4_generation(self, hydrate_sII_ch4_structure):
        """sII + CH4 hydrate should have more cages than sI."""
        structure = hydrate_sII_ch4_structure

        assert structure.guest_count > 0
        assert structure.water_count > 0

        # sII has 24 cages per unit cell vs sI's 8 → more guests
        mol_types = {m.mol_type for m in structure.molecule_index}
        assert "ch4" in mol_types
        assert "water" in mol_types


class TestHydrateS2ThfGeneration:
    """Tests for sII + THF hydrate."""

    def test_hydrate_sII_thf_generation(self, hydrate_sII_thf_structure):
        """sII + THF hydrate should generate successfully."""
        structure = hydrate_sII_thf_structure

        assert structure.guest_count > 0
        assert structure.water_count > 0

        mol_types = {m.mol_type for m in structure.molecule_index}
        assert "thf" in mol_types
        assert "water" in mol_types


class TestHydrateToCandidate:
    """Tests for HydrateStructure.to_candidate() conversion."""

    def test_hydrate_to_candidate_preserves_guests(self, hydrate_sI_ch4_structure):
        """to_candidate() should preserve guest type metadata."""
        structure = hydrate_sI_ch4_structure
        candidate = structure.to_candidate()

        # Must be a Candidate
        assert isinstance(candidate, Candidate)

        # metadata should have guest_type_counts
        assert "guest_type_counts" in candidate.metadata
        guest_counts = candidate.metadata["guest_type_counts"]
        assert "ch4" in guest_counts, f"Expected 'ch4' in guest_type_counts, got {guest_counts}"

        # nmolecules = water_count + guest_count
        expected_molecules = structure.water_count + structure.guest_count
        assert candidate.nmolecules == expected_molecules, (
            f"Expected {expected_molecules} molecules (water+guest), got {candidate.nmolecules}"
        )

    def test_hydrate_to_candidate_has_phase_id(self, hydrate_sI_ch4_structure):
        """to_candidate() should produce phase_id with hydrate lattice type."""
        candidate = hydrate_sI_ch4_structure.to_candidate()
        assert "hydrate" in candidate.phase_id
        assert "sI" in candidate.phase_id

    def test_hydrate_thf_to_candidate_preserves_guests(self, hydrate_sI_thf_structure):
        """THF hydrate to_candidate() should preserve THF guest metadata."""
        candidate = hydrate_sI_thf_structure.to_candidate()
        assert "guest_type_counts" in candidate.metadata
        guest_counts = candidate.metadata["guest_type_counts"]
        assert "thf" in guest_counts, f"Expected 'thf' in guest_type_counts, got {guest_counts}"


class TestHydrateGuestAtomCount:
    """Tests for guest atom count correctness."""

    def test_hydrate_ch4_guest_atom_count_correct(self, hydrate_sI_ch4_structure):
        """CH4 guests should have 5 atoms each (C + 4H)."""
        structure = hydrate_sI_ch4_structure

        ch4_molecules = [m for m in structure.molecule_index if m.mol_type == "ch4"]
        assert len(ch4_molecules) > 0, "No CH4 molecules found"

        # Each CH4 molecule should have 5 atoms
        for mol in ch4_molecules:
            assert mol.count == 5, (
                f"CH4 molecule at index {mol.start_idx} has {mol.count} atoms, expected 5"
            )

        # Total guest atoms = guest_count * 5
        total_guest_atoms = sum(m.count for m in ch4_molecules)
        assert total_guest_atoms == structure.guest_count * 5, (
            f"Total CH4 atoms ({total_guest_atoms}) != "
            f"guest_count * 5 ({structure.guest_count * 5})"
        )

    def test_hydrate_thf_guest_atom_count_correct(self, hydrate_sI_thf_structure):
        """THF guests should have 13 atoms each (C4H8O)."""
        structure = hydrate_sI_thf_structure

        thf_molecules = [m for m in structure.molecule_index if m.mol_type == "thf"]
        assert len(thf_molecules) > 0, "No THF molecules found"

        # Each THF molecule should have 13 atoms
        for mol in thf_molecules:
            assert mol.count == 13, (
                f"THF molecule at index {mol.start_idx} has {mol.count} atoms, expected 13"
            )

        # Total guest atoms = guest_count * 13
        total_guest_atoms = sum(m.count for m in thf_molecules)
        assert total_guest_atoms == structure.guest_count * 13, (
            f"Total THF atoms ({total_guest_atoms}) != "
            f"guest_count * 13 ({structure.guest_count * 13})"
        )


class TestHydrateMoleculeIndex:
    """Tests for molecule_index tracking consistency."""

    def test_hydrate_molecule_index_tracks_all_molecules(self, hydrate_sI_ch4_structure):
        """molecule_index length should equal water_count + guest_count."""
        structure = hydrate_sI_ch4_structure

        expected_count = structure.water_count + structure.guest_count
        actual_count = len(structure.molecule_index)

        assert actual_count == expected_count, (
            f"molecule_index length ({actual_count}) != "
            f"water_count + guest_count ({expected_count})"
        )

        # Each entry should have mol_type in allowed set
        valid_types = {"water", "ch4", "thf", "na", "cl"}
        for mol in structure.molecule_index:
            assert mol.mol_type in valid_types, (
                f"Unexpected mol_type '{mol.mol_type}' in molecule_index"
            )

    def test_hydrate_molecule_index_covers_all_positions(self, hydrate_sI_ch4_structure):
        """molecule_index entries should cover every position in the array."""
        structure = hydrate_sI_ch4_structure

        # Sum of all molecule atom counts should equal total positions
        total_atoms_from_index = sum(m.count for m in structure.molecule_index)
        assert total_atoms_from_index == len(structure.positions), (
            f"Sum of molecule counts ({total_atoms_from_index}) != "
            f"total positions ({len(structure.positions)})"
        )

    def test_hydrate_thf_molecule_index_tracks_all_molecules(self, hydrate_sI_thf_structure):
        """THF hydrate molecule_index should also track all molecules correctly."""
        structure = hydrate_sI_thf_structure

        expected_count = structure.water_count + structure.guest_count
        actual_count = len(structure.molecule_index)

        assert actual_count == expected_count, (
            f"molecule_index length ({actual_count}) != "
            f"water_count + guest_count ({expected_count})"
        )


class TestHydrateInvalidConfig:
    """Tests for invalid configuration error handling."""

    def test_hydrate_invalid_lattice_raises_error(self):
        """Invalid lattice type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown lattice type"):
            HydrateConfig(lattice_type="invalid", guest_type="ch4")

    def test_hydrate_invalid_guest_raises_error(self):
        """Invalid guest type should raise ValueError.

        Since 40-03, a guest_type not in GUEST_MOLECULES is treated as a
        custom guest that requires explicit metadata (guest_residue_name,
        guest_atom_labels, guest_atom_count, guest_gro_path). Constructing
        HydrateConfig with a bare 'invalid_guest' (no required metadata)
        therefore raises a ValueError naming the first missing field
        (guest_residue_name) rather than the legacy 'Unknown guest type'.
        """
        with pytest.raises(ValueError, match="Custom guest_type 'invalid_guest' requires guest_residue_name"):
            HydrateConfig(lattice_type="sI", guest_type="invalid_guest")

    def test_hydrate_negative_occupancy_raises_error(self):
        """Negative cage occupancy should raise ValueError."""
        with pytest.raises(ValueError, match="cage_occupancy_small"):
            HydrateConfig(lattice_type="sI", guest_type="ch4", cage_occupancy_small=-10.0)

    def test_hydrate_zero_supercell_raises_error(self):
        """Zero supercell dimension should raise ValueError."""
        with pytest.raises(ValueError, match="Supercell dimensions"):
            HydrateConfig(lattice_type="sI", guest_type="ch4", supercell_x=0)
