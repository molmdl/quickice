"""Test atom_names filtering for interface generation.

Verifies that filter_atom_names correctly removes atom names for molecules
that are removed by remove_overlapping_molecules, maintaining consistency
between positions and atom_names arrays.
"""

import numpy as np
import pytest

from quickice.structure_generation.overlap_resolver import (
    remove_overlapping_molecules,
    filter_atom_names,
)


class TestFilterAtomNames:
    """Test the filter_atom_names function."""

    def test_no_overlap_returns_same_list(self):
        """When no molecules overlap, atom_names should be unchanged."""
        atom_names = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        overlapping = set()
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        assert result == atom_names

    def test_remove_middle_molecule(self):
        """Removing a molecule in the middle should correctly filter atom_names."""
        # 3 water molecules: indices 0, 1, 2
        atom_names = [
            "OW", "HW1", "HW2", "MW",  # molecule 0
            "OW", "HW1", "HW2", "MW",  # molecule 1
            "OW", "HW1", "HW2", "MW",  # molecule 2
        ]
        # Remove molecule 1 (indices 4-7)
        overlapping = {1}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        expected = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]  # molecules 0 and 2
        assert result == expected

    def test_remove_first_molecule(self):
        """Removing the first molecule should correctly filter atom_names."""
        atom_names = [
            "OW", "HW1", "HW2", "MW",  # molecule 0
            "OW", "HW1", "HW2", "MW",  # molecule 1
        ]
        overlapping = {0}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        expected = ["OW", "HW1", "HW2", "MW"]  # molecule 1
        assert result == expected

    def test_remove_last_molecule(self):
        """Removing the last molecule should correctly filter atom_names."""
        atom_names = [
            "OW", "HW1", "HW2", "MW",  # molecule 0
            "OW", "HW1", "HW2", "MW",  # molecule 1
        ]
        overlapping = {1}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        expected = ["OW", "HW1", "HW2", "MW"]  # molecule 0
        assert result == expected

    def test_remove_multiple_molecules(self):
        """Removing multiple scattered molecules should correctly filter atom_names."""
        atom_names = [
            "OW", "HW1", "HW2", "MW",  # molecule 0
            "OW", "HW1", "HW2", "MW",  # molecule 1
            "OW", "HW1", "HW2", "MW",  # molecule 2
            "OW", "HW1", "HW2", "MW",  # molecule 3
            "OW", "HW1", "HW2", "MW",  # molecule 4
        ]
        # Remove molecules 1 and 3
        overlapping = {1, 3}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        expected = [
            "OW", "HW1", "HW2", "MW",  # molecule 0
            "OW", "HW1", "HW2", "MW",  # molecule 2
            "OW", "HW1", "HW2", "MW",  # molecule 4
        ]
        assert result == expected

    def test_ice_atoms_3_per_molecule(self):
        """Filter should work for ice molecules (3 atoms per molecule)."""
        atom_names = [
            "O", "H", "H",  # molecule 0
            "O", "H", "H",  # molecule 1
            "O", "H", "H",  # molecule 2
        ]
        # Remove molecule 1
        overlapping = {1}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=3)
        expected = ["O", "H", "H", "O", "H", "H"]  # molecules 0 and 2
        assert result == expected

    def test_consistency_with_positions(self):
        """Positions and atom_names should be consistent after filtering."""
        # Create test positions for 4 water molecules
        positions = np.array([
            [0.0, 0.0, 0.0],  # OW molecule 0
            [0.1, 0.0, 0.0],  # HW1 molecule 0
            [-0.1, 0.0, 0.0],  # HW2 molecule 0
            [0.0, 0.0, 0.0],  # MW molecule 0
            [1.0, 0.0, 0.0],  # OW molecule 1
            [1.1, 0.0, 0.0],  # HW1 molecule 1
            [0.9, 0.0, 0.0],  # HW2 molecule 1
            [1.0, 0.0, 0.0],  # MW molecule 1
            [2.0, 0.0, 0.0],  # OW molecule 2
            [2.1, 0.0, 0.0],  # HW1 molecule 2
            [1.9, 0.0, 0.0],  # HW2 molecule 2
            [2.0, 0.0, 0.0],  # MW molecule 2
            [3.0, 0.0, 0.0],  # OW molecule 3
            [3.1, 0.0, 0.0],  # HW1 molecule 3
            [2.9, 0.0, 0.0],  # HW2 molecule 3
            [3.0, 0.0, 0.0],  # MW molecule 3
        ])
        atom_names = ["OW", "HW1", "HW2", "MW"] * 4
        
        # Remove molecules 1 and 3 (the ones at positions 1.0 and 3.0)
        overlapping = {1, 3}
        
        # Filter both positions and atom_names
        filtered_positions, n_remaining = remove_overlapping_molecules(
            positions, overlapping, atoms_per_molecule=4
        )
        filtered_atom_names = filter_atom_names(
            atom_names, overlapping, atoms_per_molecule=4
        )
        
        # Check consistency: same number of atoms
        assert len(filtered_positions) == len(filtered_atom_names)
        assert len(filtered_positions) == 8  # 2 molecules * 4 atoms
        assert n_remaining == 2
        
        # Check that the correct molecules remain (molecules 0 and 2)
        # Molecule 0 positions: indices 0-3
        # Molecule 2 positions: indices 8-11
        expected_positions = np.array([
            [0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [-0.1, 0.0, 0.0], [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0], [2.1, 0.0, 0.0], [1.9, 0.0, 0.0], [2.0, 0.0, 0.0],
        ])
        np.testing.assert_array_almost_equal(filtered_positions, expected_positions)
        
        expected_names = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        assert filtered_atom_names == expected_names

    def test_invalid_molecule_index_out_of_range(self):
        """Invalid molecule indices should be ignored."""
        atom_names = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        # Index 5 is out of range (only 2 molecules)
        overlapping = {0, 5}
        result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        # Only molecule 0 should be removed, index 5 ignored
        expected = ["OW", "HW1", "HW2", "MW"]
        assert result == expected


class TestSlicingBugComparison:
    """Demonstrate the bug that was fixed: slicing vs filtering."""

    def test_slicing_takes_first_molecules_wrong(self):
        """Show that slicing [:n*4] would incorrectly take first molecules.
        
        Use molecule-numbered labels to clearly show which molecules are kept.
        """
        # This is what the OLD buggy code did:
        # Use numbered labels to clearly identify molecules
        atom_names = [
            "OW0", "HW1_0", "HW2_0", "MW0",  # molecule 0
            "OW1", "HW1_1", "HW2_1", "MW1",  # molecule 1 (should be removed)
            "OW2", "HW1_2", "HW2_2", "MW2",  # molecule 2 (should remain)
        ]
        # Remove molecule 1 (index 1)
        overlapping = {1}
        
        # OLD BUGGY approach: just slice
        # After removal, n_molecules = 2, so [:2*4] = [:8]
        buggy_result = atom_names[:8]  # This takes molecules 0 and 1, not 0 and 2!
        
        # This is WRONG because it takes the first 2 molecules
        # but molecule 1 was removed, not molecule 2
        assert buggy_result == [
            "OW0", "HW1_0", "HW2_0", "MW0",  # molecule 0
            "OW1", "HW1_1", "HW2_1", "MW1",  # molecule 1 (WRONG! This was supposed to be removed)
        ]
        
        # CORRECT approach: filter with mask
        correct_result = filter_atom_names(atom_names, overlapping, atoms_per_molecule=4)
        assert correct_result == [
            "OW0", "HW1_0", "HW2_0", "MW0",  # molecule 0
            "OW2", "HW1_2", "HW2_2", "MW2",  # molecule 2 (CORRECT!)
        ]
        
        # The buggy result has wrong molecules!
        # Buggy has OW1 (molecule 1), correct has OW2 (molecule 2)
        assert buggy_result != correct_result
        assert "OW1" in buggy_result  # Buggy wrongly includes molecule 1
        assert "OW2" not in buggy_result  # Buggy wrongly excludes molecule 2
        assert "OW1" not in correct_result  # Correct excludes molecule 1
        assert "OW2" in correct_result  # Correct includes molecule 2