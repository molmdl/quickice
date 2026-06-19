"""Regression test for missing guest attrs in IonInserter Path 1 early return.

BUG: The first early-return path in IonInserter.replace_water_with_ions()
(the "no water molecules found" path, when _build_molecule_index_from_structure()
returns None) was missing guest_nmolecules and guest_atom_count when constructing
IonStructure, while Paths 2 and 3 included them.

This test creates a structure that:
1. Has guest molecules (guest_nmolecules > 0, guest_atom_count > 0)
2. Has NO molecule_index (empty list)
3. Lacks ice_atom_count attribute (so _build_molecule_index_from_structure returns None)
→ This triggers Path 1, the "no water molecules found" early return

Before the fix: IonStructure would have guest_nmolecules=0, guest_atom_count=0 (defaults)
After the fix: guest attrs are correctly propagated via getattr(structure, 'guest_nmolecules', 0)
"""

import numpy as np
import pytest

from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.types import (
    IonConfig,
    IonStructure,
    MoleculeIndex,
)


def _make_structure_without_molecule_index(
    guest_nmolecules=3, guest_atom_count=15
) -> IonStructure:
    """Create an IonStructure with guests but no molecule_index and no ice_atom_count.

    This structure will trigger Path 1 in replace_water_with_ions() because:
    - molecule_index is empty (falsy)
    - No ice_atom_count attribute → _build_molecule_index_from_structure() returns None
    """
    # Just some dummy positions and atom names for guests only
    positions = np.random.rand(guest_atom_count, 3) * 5.0
    atom_names = ["C", "H", "H", "H", "H"] * guest_nmolecules

    structure = IonStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.diag([5.0, 5.0, 5.0]),
        molecule_index=[],  # Empty → triggers "no molecule_index" branch
        na_count=0,
        cl_count=0,
        report="test structure",
        guest_nmolecules=guest_nmolecules,
        guest_atom_count=guest_atom_count,
    )
    return structure


class TestPath1GuestAttrPropagation:
    """Regression tests for guest attribute propagation in Path 1 early return."""

    def test_path1_preserves_guest_nmolecules(self):
        """Path 1 (no water found) should propagate guest_nmolecules."""
        structure = _make_structure_without_molecule_index(
            guest_nmolecules=3, guest_atom_count=15
        )
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        # This hits Path 1: _build_molecule_index_from_structure returns None
        # because the IonStructure lacks ice_atom_count
        result = inserter.replace_water_with_ions(structure, ion_pairs=5)

        assert result.guest_nmolecules == 3, (
            f"Path 1 should propagate guest_nmolecules=3, got {result.guest_nmolecules}. "
            f"This means guest attrs were omitted from the IonStructure constructor "
            f"in the 'no water molecules found' early-return path."
        )

    def test_path1_preserves_guest_atom_count(self):
        """Path 1 (no water found) should propagate guest_atom_count."""
        structure = _make_structure_without_molecule_index(
            guest_nmolecules=3, guest_atom_count=15
        )
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        result = inserter.replace_water_with_ions(structure, ion_pairs=5)

        assert result.guest_atom_count == 15, (
            f"Path 1 should propagate guest_atom_count=15, got {result.guest_atom_count}. "
            f"This means guest attrs were omitted from the IonStructure constructor "
            f"in the 'no water molecules found' early-return path."
        )

    def test_path1_zero_guests_when_absent(self):
        """Path 1 should default to 0 when source structure has no guest attrs."""
        # Create structure WITHOUT guest attrs set (uses IonStructure defaults of 0)
        positions = np.random.rand(4, 3) * 5.0
        atom_names = ["OW", "HW1", "HW2", "MW"]

        structure = IonStructure(
            positions=positions,
            atom_names=atom_names,
            cell=np.diag([5.0, 5.0, 5.0]),
            molecule_index=[],
            na_count=0,
            cl_count=0,
            report="test",
            # guest_nmolecules and guest_atom_count default to 0
        )
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        result = inserter.replace_water_with_ions(structure, ion_pairs=5)

        assert result.guest_nmolecules == 0
        assert result.guest_atom_count == 0

    def test_path1_report_message(self):
        """Path 1 should include the 'no water molecules found' report."""
        structure = _make_structure_without_molecule_index()
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        result = inserter.replace_water_with_ions(structure, ion_pairs=5)

        assert "no water molecules found" in result.report

    def test_path1_zero_ions(self):
        """Path 1 should return zero ions (no water to replace)."""
        structure = _make_structure_without_molecule_index()
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        result = inserter.replace_water_with_ions(structure, ion_pairs=5)

        assert result.na_count == 0
        assert result.cl_count == 0

    def test_path2_guest_attrs_still_work(self):
        """Verify Path 2 (zero ion pairs) still propagates guest attrs.

        This ensures the fix for Path 1 didn't break Path 2.
        """
        # Create structure with molecule_index but no water molecules
        # This won't hit Path 1 (molecule_index exists), and with ion_pairs=0
        # it hits Path 2.
        structure = IonStructure(
            positions=np.random.rand(20, 3) * 5.0,
            atom_names=["C", "H", "H", "H", "H"] * 4,
            cell=np.diag([5.0, 5.0, 5.0]),
            molecule_index=[
                MoleculeIndex(start_idx=i * 5, count=5, mol_type="guest")
                for i in range(4)
            ],
            na_count=0,
            cl_count=0,
            report="test",
            guest_nmolecules=4,
            guest_atom_count=20,
        )
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        result = inserter.replace_water_with_ions(structure, ion_pairs=0)

        assert result.guest_nmolecules == 4
        assert result.guest_atom_count == 20
        assert "0 ion pairs" in result.report or "concentration too low" in result.report
