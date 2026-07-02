"""End-to-end tests for custom guest hydrate generation (Phase 40 plan 40-05).

Tests the full custom-guest pipeline:
    HydrateStructureGenerator().generate(HydrateConfig(...custom guest...))
        -> HydrateStructure with guests placed in cage positions via GenIce2.

Covers:
    * Custom guest (ethanol, .gro + .itp) placed in sI cages (not at origin).
    * _build_molecule_index identifies the custom guest by guest_residue_name
      (no "unknown" molecules for a valid custom guest).
    * sys.modules is clean after generation (no stale pollution — the
      custom_guest_module context manager's try/finally cleanup works).
    * Built-in ch4/thf generation is unchanged (no regression).

Uses a UNIQUE guest_type per test module ("etoh_e2e") to avoid sys.modules
key collisions with other test modules (e.g. test_custom_guest_bridge.py uses
"etoh_test_*" slugs). Module-scoped fixture amortizes the ~3-5s GenIce2 call.
"""

import sys

import numpy as np
import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import HydrateConfig, HydrateStructure


# Unique guest_type for this test module — avoids sys.modules key collisions
# with other test modules that register custom guests (e.g. test_custom_guest_bridge).
_GUEST_TYPE = "etoh_e2e"
_GUEST_RESIDUE_NAME = "MOL"
_GUEST_GRO_PATH = "quickice/data/custom/etoh.gro"
_GUEST_ITP_PATH = "quickice/data/custom/etoh.itp"
_GUEST_ATOM_LABELS = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
_GUEST_ATOM_COUNT = 9


@pytest.fixture(scope="module")
def custom_guest_hydrate():
    """Generate a real sI hydrate with a custom ethanol guest.

    Module-scoped to amortize the ~3-5s GenIce2 call across all tests in this
    module that use it. Mirrors the conftest.py hydrate_sI_ch4_structure
    fixture pattern (HydrateStructureGenerator().generate(HydrateConfig(...))).

    The custom_guest_module context manager (invoked inside generate())
    registers the synthetic Molecule in sys.modules before generate_ice()
    runs and cleans it up afterward (try/finally) — so by the time this
    fixture returns, sys.modules no longer contains the custom guest key.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type=_GUEST_TYPE,
        guest_residue_name=_GUEST_RESIDUE_NAME,
        guest_gro_path=_GUEST_GRO_PATH,
        guest_itp_path=_GUEST_ITP_PATH,
        guest_atom_labels=list(_GUEST_ATOM_LABELS),
        guest_atom_count=_GUEST_ATOM_COUNT,
    )
    return gen.generate(config)


class TestCustomGuestPlacedInCages:
    """Verify custom guest molecules are actually placed in hydrate cages."""

    def test_custom_guest_placed_in_cages(self, custom_guest_hydrate):
        """Custom guest hydrate should have guests + water + valid positions.

        guest_count > 0 proves at least one ethanol was placed in a cage.
        water_count > 0 proves the water framework was built.
        Total atoms == len(positions) proves no atoms were dropped.
        """
        structure = custom_guest_hydrate

        assert isinstance(structure, HydrateStructure)
        assert structure.guest_count > 0, (
            "Custom guest hydrate should have at least 1 guest molecule placed"
        )
        assert structure.water_count > 0, (
            "Custom guest hydrate should have water molecules in the framework"
        )

        # Positions array valid
        assert len(structure.positions) > 0
        assert structure.positions.ndim == 2
        assert structure.positions.shape[1] == 3

        # Total atoms == len(positions) (molecule_index covers every position)
        total_atoms_from_index = sum(m.count for m in structure.molecule_index)
        assert total_atoms_from_index == len(structure.positions), (
            f"Sum of molecule_index counts ({total_atoms_from_index}) != "
            f"total positions ({len(structure.positions)})"
        )


class TestCustomGuestMoleculeIndexIdentified:
    """Verify _build_molecule_index identifies the custom guest (not 'unknown')."""

    def test_custom_guest_molecule_index_identified(self, custom_guest_hydrate):
        """molecule_index should contain the custom guest type, not 'unknown'.

        This verifies the guest_residue_name-based residue grouping (40-05
        Task 2) correctly identifies custom guest molecules. The mol_type is
        set to config.guest_type (e.g. "etoh_e2e"), NOT guest_residue_name
        ("MOL") and NOT "unknown".
        """
        structure = custom_guest_hydrate

        assert structure.molecule_index, "molecule_index should be non-empty"

        # Custom guest identified by guest_type (not "unknown")
        assert any(m.mol_type == _GUEST_TYPE for m in structure.molecule_index), (
            f"Expected mol_type '{_GUEST_TYPE}' in molecule_index; "
            f"got {set(m.mol_type for m in structure.molecule_index)}"
        )

        # No "unknown" molecules for a valid custom guest
        assert not any(m.mol_type == "unknown" for m in structure.molecule_index), (
            "Valid custom guest should not produce 'unknown' molecules — "
            "indicates _build_molecule_index failed to identify the guest"
        )

        # Water also present
        assert any(m.mol_type == "water" for m in structure.molecule_index), (
            "Custom guest hydrate should also have water molecules"
        )


class TestSysModulesCleanAfterGeneration:
    """Verify sys.modules cleanup (success criteria #5: no stale pollution)."""

    def test_sys_modules_clean_after_generation(self, custom_guest_hydrate):
        """sys.modules should NOT contain the custom guest key after generation.

        The custom_guest_module context manager (try/finally) removes the
        synthetic module from sys.modules after generate_ice() completes,
        preventing stale pollution that could shadow built-in guests on the
        next run. This is Phase 40 success criteria #5.
        """
        # The fixture already generated and cleaned up. Verify the key is
        # absent — the context manager's finally block should have popped it.
        sys_modules_key = f"genice2.molecules.{_GUEST_TYPE}"
        assert sys_modules_key not in sys.modules, (
            f"Stale custom guest module '{sys_modules_key}' left in sys.modules "
            f"after generation — context manager cleanup failed (success "
            f"criteria #5 violation)"
        )


class TestCustomGuestPositionsNotAllAtOrigin:
    """Verify guest atoms are placed at cage centers (not clustered at origin)."""

    def test_custom_guest_positions_not_all_at_origin(self, custom_guest_hydrate):
        """Guest atom positions should NOT all be at/near the origin.

        GenIce2's arrange() adds the cage-center position to the (centered)
        sites_, so guests are placed at cage centers — not clustered at
        (0,0,0). This verifies the centering + placement worked. sI cage
        centers are ~1.2 nm apart, so max |position| should be well above
        0.1 nm.
        """
        structure = custom_guest_hydrate

        # Collect all guest atom positions from molecule_index
        guest_positions = []
        for mol in structure.molecule_index:
            if mol.mol_type == _GUEST_TYPE:
                start = mol.start_idx
                end = start + mol.count
                guest_positions.append(structure.positions[start:end])

        assert guest_positions, "No custom guest molecules found in molecule_index"

        all_guest_positions = np.vstack(guest_positions)
        max_abs = float(np.abs(all_guest_positions).max())

        assert max_abs > 0.1, (
            f"Custom guest atoms appear clustered at origin (max |pos| = "
            f"{max_abs:.4f} nm <= 0.1 nm). GenIce2 arrange() should place "
            f"guests at cage centers, not at (0,0,0). This indicates the "
            f"molecule centering (sites_ = positions - centroid) or cage "
            f"placement failed."
        )


class TestCustomGuestResidueNameInOutput:
    """Verify the custom guest's atom signature appears in the output."""

    def test_custom_guest_residue_name_in_output(self, custom_guest_hydrate):
        """Guest molecule atom_names should match the expected 9-atom signature.

        GenIce2 outputs the custom guest with Molecule.name_ as the GRO
        residue and Molecule.labels_ as the atom names. _parse_gro_result
        extracts atom_names, so each guest molecule's atom_names should
        match the configured guest_atom_labels (["H","C","H","H","C","H",
        "H","O","H"] for ethanol).
        """
        structure = custom_guest_hydrate

        guest_molecules = [
            m for m in structure.molecule_index if m.mol_type == _GUEST_TYPE
        ]
        assert guest_molecules, "No custom guest molecules in molecule_index"

        # Each guest molecule's atom_names should match the expected signature
        for mol in guest_molecules:
            start = mol.start_idx
            end = start + mol.count
            mol_atom_names = structure.atom_names[start:end]
            assert mol_atom_names == _GUEST_ATOM_LABELS, (
                f"Guest molecule at index {start} has atom_names "
                f"{mol_atom_names}, expected {_GUEST_ATOM_LABELS}"
            )

        # Also verify the guest_atom_count is correct (9 atoms per ethanol)
        for mol in guest_molecules:
            assert mol.count == _GUEST_ATOM_COUNT, (
                f"Guest molecule at index {mol.start_idx} has {mol.count} "
                f"atoms, expected {_GUEST_ATOM_COUNT}"
            )


class TestBuiltinCh4StillGenerates:
    """Regression test: built-in ch4 generation unchanged (no regression)."""

    def test_builtin_ch4_still_generates(self):
        """Built-in ch4 hydrate should still generate with guests + water.

        Verifies the 40-05 changes (generate() branching on
        config.is_custom_guest, _build_molecule_index using
        guest_residue_name) did not break the built-in path. For ch4,
        guest_residue_name="" -> "" or guest_type.upper() -> "CH4" (same as
        before, backward compatible).
        """
        gen = HydrateStructureGenerator()
        config = HydrateConfig(lattice_type="sI", guest_type="ch4")
        structure = gen.generate(config)

        assert structure.guest_count > 0, "Built-in ch4 should have guests"
        assert structure.water_count > 0, "Built-in ch4 should have water"

        mol_types = set(m.mol_type for m in structure.molecule_index)
        assert "ch4" in mol_types, f"Expected 'ch4' in mol_types, got {mol_types}"
        assert "unknown" not in mol_types, (
            f"Built-in ch4 should not produce 'unknown' molecules, got {mol_types}"
        )


class TestBuiltinThfStillGenerates:
    """Regression test: built-in thf generation unchanged (no regression)."""

    def test_builtin_thf_still_generates(self):
        """Built-in thf hydrate should still generate with guests + water.

        THF is the critical regression test because its first atom is "O"
        (which collides with 3-site water "O"). The 40-05 _build_molecule_index
        change must not break THF identification via residue grouping
        (guest_res_name = "" or "thf".upper() = "THF", matching GenIce2's
        output residue).
        """
        gen = HydrateStructureGenerator()
        config = HydrateConfig(lattice_type="sI", guest_type="thf")
        structure = gen.generate(config)

        assert structure.guest_count > 0, "Built-in thf should have guests"
        assert structure.water_count > 0, "Built-in thf should have water"

        mol_types = set(m.mol_type for m in structure.molecule_index)
        assert "thf" in mol_types, f"Expected 'thf' in mol_types, got {mol_types}"
        assert "unknown" not in mol_types, (
            f"Built-in thf should not produce 'unknown' molecules, got {mol_types}"
        )
