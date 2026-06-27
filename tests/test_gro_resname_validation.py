"""Tests for GRO residue name validation.

Validates that validate_gro_residue_name() correctly enforces the 5-character
GRO format limit for residue names, and that GRO writer functions raise
ValueError for overlong residue names instead of silently truncating.
"""

import pytest
import numpy as np

from quickice.output.gromacs_writer import (
    validate_gro_residue_name,
    write_multi_molecule_gro_file,
)
from quickice.structure_generation.types import MoleculeIndex


# ---------------------------------------------------------------------------
# Direct validation tests
# ---------------------------------------------------------------------------

class TestValidateGroResidueName:
    """Tests for validate_gro_residue_name() function."""

    # -- Valid names (1-5 chars) pass without error --

    @pytest.mark.parametrize("name", ["C", "NA", "SOL", "CH4", "CH4_H"])
    def test_valid_names_pass(self, name):
        """Names with 1-5 characters should pass validation."""
        validate_gro_residue_name(name)

    def test_single_char_passes(self):
        """Single character name should pass."""
        validate_gro_residue_name("A")

    def test_three_char_passes(self):
        """Three character name (typical hydrate base) should pass."""
        validate_gro_residue_name("THF")

    def test_five_char_passes(self):
        """Exactly 5 characters should pass (GRO limit boundary)."""
        validate_gro_residue_name("CH4_H")

    def test_empty_string_passes(self):
        """Empty string (len=0) should pass — still ≤5."""
        validate_gro_residue_name("")

    # -- Overlong names (6+ chars) raise ValueError --

    @pytest.mark.parametrize("name", ["CH4_HX", "ETHANOL", "VERYLONG"])
    def test_overlong_names_rejected(self, name):
        """Names exceeding 5 characters should raise ValueError."""
        with pytest.raises(ValueError, match="5-character GRO format limit"):
            validate_gro_residue_name(name)

    def test_six_char_fails(self):
        """Exactly 6 characters should fail (boundary +1)."""
        with pytest.raises(ValueError):
            validate_gro_residue_name("CH4_HX")

    # -- Error message content --

    def test_validation_message_mentions_name(self):
        """Error message should mention the offending residue name."""
        with pytest.raises(ValueError, match="ETHANOL"):
            validate_gro_residue_name("ETHANOL")

    def test_validation_message_mentions_length(self):
        """Error message should mention the name's length."""
        with pytest.raises(ValueError, match="7 chars"):
            validate_gro_residue_name("ETHANOL")

    def test_validation_message_mentions_limit(self):
        """Error message should mention the 5-character limit."""
        with pytest.raises(ValueError, match="5-character GRO format limit"):
            validate_gro_residue_name("TOOLONG")

    # -- Context string --

    def test_context_included_in_message(self):
        """Context string should appear in error message when provided."""
        with pytest.raises(ValueError, match="Custom molecule:"):
            validate_gro_residue_name("ETHANOL", context="Custom molecule")

    def test_no_context_still_works(self):
        """Validation should work without context string."""
        with pytest.raises(ValueError, match="GRO residue name"):
            validate_gro_residue_name("ETHANOL")

    # -- Edge cases --

    def test_special_characters_only_length_matters(self):
        """Validation only checks length, not content — underscores, spaces, etc."""
        validate_gro_residue_name("A_B_C")  # 5 chars with underscores — passes
        with pytest.raises(ValueError):
            validate_gro_residue_name("A_B_CD")  # 6 chars — fails

    def test_unicode_counted_by_codepoint(self):
        """Python len() counts Unicode codepoints, not bytes."""
        # Each emoji is 1 codepoint in Python len()
        validate_gro_residue_name("🔥🔥🔥")  # 3 codepoints — passes
        with pytest.raises(ValueError):
            validate_gro_residue_name("🔥🔥🔥🔥🔥🔥")  # 6 codepoints — fails

    # -- _H suffix convention for hydrate guests --

    def test_ch4_h_suffix_passes(self):
        """CH4 (3 chars) + _H suffix = CH4_H (5 chars) passes."""
        validate_gro_residue_name("CH4_H")

    def test_thf_h_suffix_passes(self):
        """THF (3 chars) + _H suffix = THF_H (5 chars) passes."""
        validate_gro_residue_name("THF_H")

    def test_co2_h_suffix_passes(self):
        """CO2 (3 chars) + _H suffix = CO2_H (5 chars) passes."""
        validate_gro_residue_name("CO2_H")

    def test_h2_h_suffix_passes(self):
        """H2 (2 chars) + _H suffix = H2_H (4 chars) passes."""
        validate_gro_residue_name("H2_H")

    def test_overlong_base_name_fails(self):
        """A 4-char base + _H = 6 chars would fail — base names must be ≤3."""
        with pytest.raises(ValueError):
            validate_gro_residue_name("ETHA_H")  # 6 chars


# ---------------------------------------------------------------------------
# Integration test: GRO writer rejects overlong residue names
# ---------------------------------------------------------------------------

class TestGroWriterValidation:
    """Spot-check that GRO writer functions reject overlong residue names."""

    def test_multi_molecule_gro_rejects_overlong_resname(self, tmp_path):
        """write_multi_molecule_gro_file should raise ValueError for >5 char residue name."""
        from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
        
        # Create a registry and inject a >5 char GROMACS name to trigger validation
        registry = MoleculetypeRegistry()
        registry._registered["hydrate_CH4"] = "ETHANOL_H"  # 8 chars — exceeds limit
        
        positions = np.zeros((4, 3))
        molecule_index = [MoleculeIndex(mol_type="ch4", start_idx=0, count=4)]

        with pytest.raises(ValueError, match="5-character GRO format limit"):
            write_multi_molecule_gro_file(
                positions=positions,
                molecule_index=molecule_index,
                cell=np.eye(3) * 2.0,
                filepath=str(tmp_path / "test.gro"),
                registry=registry,
            )
