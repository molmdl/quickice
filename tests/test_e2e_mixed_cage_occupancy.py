"""End-to-end test for mixed cage occupancy hydrate generation (Phase 42 plan 42-02).

Tests the full mixed-occupancy pipeline:
    HydrateStructureGenerator().generate(HydrateConfig(...cage_guest_assignments...))
        -> HydrateStructure with DIFFERENT guest types in DIFFERENT cage types.

Specifically: sI 2x2x2 with CH4 in small cages + custom ethanol (etoh_mix) in
large cages. GenIce2 natively supports mixed occupancy (verified in research
POC): sI 2x2x2 -> 16 CH4 (small) + 48 MOL (large).

Covers:
    * Mixed occupancy generates with both guest types placed (CH4 in small,
      custom ethanol in large).
    * _build_molecule_index distinguishes the two guest types by mol_type
      (resname_to_moltype dict — Pattern 4).
    * sys.modules is clean after generation (ExitStack cleanup — Pitfall 5).
    * HydrateStructure.guest_descriptors is populated with one entry per cage
      assignment (2 entries: small=ch4, large=etoh_mix).

Uses a UNIQUE guest_type ("etoh_mix") to avoid sys.modules key collisions
with other test modules (test_e2e_custom_guest_hydrate.py uses "etoh_e2e").
Module-scoped fixture amortizes the ~3-5s GenIce2 call.
"""

import sys

import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import (
    CageGuestAssignment,
    HydrateConfig,
    HydrateStructure,
)


# Unique guest_type for this test module — avoids sys.modules key collisions
# with other test modules that register custom guests (e.g.
# test_e2e_custom_guest_hydrate.py uses "etoh_e2e").
_GUEST_TYPE_CUSTOM = "etoh_mix"
_GUEST_RESIDUE_NAME = "MOL"
_GUEST_GRO_PATH = "quickice/data/custom/etoh.gro"
_GUEST_ITP_PATH = "quickice/data/custom/etoh.itp"
_GUEST_ATOM_LABELS = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
_GUEST_ATOM_COUNT = 9


@pytest.fixture(scope="module")
def mixed_si_hydrate():
    """Generate a real sI 2x2x2 hydrate with mixed cage occupancy.

    CH4 (built-in) in small cages + custom ethanol (etoh_mix) in large cages.
    Module-scoped to amortize the ~3-5s GenIce2 call across all tests in this
    module.

    The ExitStack (invoked inside generate()) registers the synthetic etoh_mix
    Molecule in sys.modules before generate_ice() runs and cleans it up
    afterward (ExitStack finally) — so by the time this fixture returns,
    sys.modules no longer contains the custom guest key.

    sI unit cell: 2 small (5^12) + 6 large (5^12 6^2) cages. 2x2x2 supercell
    = 8 unit cells -> 16 small + 48 large cages. At 100% occupancy ->
    16 CH4 + 48 MOL (matches the research POC).
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",  # primary (legacy) — ch4 is built-in
        supercell_x=2,
        supercell_y=2,
        supercell_z=2,
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(
                guest_type=_GUEST_TYPE_CUSTOM,
                occupancy=100.0,
                guest_residue_name=_GUEST_RESIDUE_NAME,
                guest_gro_path=_GUEST_GRO_PATH,
                guest_itp_path=_GUEST_ITP_PATH,
                guest_atom_labels=list(_GUEST_ATOM_LABELS),
                guest_atom_count=_GUEST_ATOM_COUNT,
            ),
        },
    )
    return gen.generate(config)


class TestMixedOccupancyPlacesBothGuestTypes:
    """Verify mixed occupancy places both guest types in their respective cages."""

    def test_mixed_places_both_guest_types(self, mixed_si_hydrate):
        """Mixed sI should place both CH4 (small) and etoh_mix (large).

        guest_count > 0 proves at least one guest was placed. The
        molecule_index should contain BOTH 'ch4' and 'etoh_mix' mol_types
        (distinguished by resname_to_moltype — Pattern 4), proving the two
        guest types were placed in their respective cage types and identified
        correctly.
        """
        structure = mixed_si_hydrate

        assert isinstance(structure, HydrateStructure)
        assert structure.guest_count > 0, (
            "Mixed hydrate should have at least one guest molecule placed"
        )

        mol_types = {m.mol_type for m in structure.molecule_index}
        assert "ch4" in mol_types, (
            f"Expected 'ch4' (small-cage guest) in mol_types, got {mol_types}"
        )
        assert _GUEST_TYPE_CUSTOM in mol_types, (
            f"Expected '{_GUEST_TYPE_CUSTOM}' (large-cage custom guest) in "
            f"mol_types, got {mol_types}"
        )
        assert "water" in mol_types, (
            f"Expected 'water' in mol_types, got {mol_types}"
        )


class TestMixedCh4Count16:
    """Verify exact guest counts for sI 2x2x2 mixed occupancy."""

    def test_mixed_ch4_count_16(self, mixed_si_hydrate):
        """sI 2x2x2 with 100% CH4-small + 100% etoh_mix-large -> 16 CH4 + 48 MOL.

        sI unit cell: 2 small + 6 large cages. 2x2x2 = 8 unit cells ->
        16 small + 48 large cages. At 100% occupancy: 16 CH4 + 48 etoh_mix.
        This matches the research's verified POC exactly.
        """
        structure = mixed_si_hydrate

        ch4_count = sum(1 for m in structure.molecule_index if m.mol_type == "ch4")
        custom_count = sum(
            1 for m in structure.molecule_index if m.mol_type == _GUEST_TYPE_CUSTOM
        )

        assert ch4_count == 16, (
            f"Expected 16 CH4 molecules (2 small/unit_cell * 8 unit_cells), "
            f"got {ch4_count}"
        )
        assert custom_count == 48, (
            f"Expected 48 {_GUEST_TYPE_CUSTOM} molecules (6 large/unit_cell * "
            f"8 unit_cells), got {custom_count}"
        )


class TestSysModulesCleanAfterMixed:
    """Verify sys.modules cleanup after mixed-occupancy generation (Pitfall 5)."""

    def test_sysmodules_clean_after_mixed(self, mixed_si_hydrate):
        """sys.modules should NOT contain the custom guest key after generation.

        The ExitStack (replacing the single custom_guest_module context manager
        for multi-guest) removes the synthetic etoh_mix module from sys.modules
        after generate_ice() completes, preventing stale pollution that could
        shadow built-in guests on the next run. This is Phase 40 success
        criteria #5, extended to the multi-guest ExitStack path in Phase 42.
        """
        sys_modules_key = f"genice2.molecules.{_GUEST_TYPE_CUSTOM}"
        assert sys_modules_key not in sys.modules, (
            f"Stale custom guest module '{sys_modules_key}' left in sys.modules "
            f"after mixed-occupancy generation — ExitStack cleanup failed "
            f"(Pitfall 5 / success criteria #5 violation)"
        )


class TestGuestDescriptorsPopulated:
    """Verify HydrateStructure.guest_descriptors is populated for mixed occupancy."""

    def test_guest_descriptors_populated(self, mixed_si_hydrate):
        """guest_descriptors should have 2 entries (one per cage assignment).

        The 2 descriptors should have mol_types matching {'ch4', 'etoh_mix'}
        and cage_keys matching {'small', 'large'}. Each descriptor records
        the per-cage guest assignment (Phase 42 GuestDescriptor).
        """
        structure = mixed_si_hydrate

        assert len(structure.guest_descriptors) == 2, (
            f"Expected 2 guest_descriptors (one per cage assignment), "
            f"got {len(structure.guest_descriptors)}"
        )

        mol_types = {gd.mol_type for gd in structure.guest_descriptors}
        assert mol_types == {"ch4", _GUEST_TYPE_CUSTOM}, (
            f"Expected guest_descriptors mol_types {{'ch4', '{_GUEST_TYPE_CUSTOM}'}}, "
            f"got {mol_types}"
        )

        cage_keys = {gd.cage_key for gd in structure.guest_descriptors}
        assert cage_keys == {"small", "large"}, (
            f"Expected guest_descriptors cage_keys {{'small', 'large'}}, "
            f"got {cage_keys}"
        )

        # The custom descriptor should be flagged is_custom=True with the
        # correct residue name and atom labels/count.
        custom_desc = next(
            gd for gd in structure.guest_descriptors if gd.mol_type == _GUEST_TYPE_CUSTOM
        )
        assert custom_desc.is_custom is True
        assert custom_desc.guest_residue_name == _GUEST_RESIDUE_NAME
        assert custom_desc.atom_labels == _GUEST_ATOM_LABELS
        assert custom_desc.atom_count == _GUEST_ATOM_COUNT

        # The built-in ch4 descriptor should be flagged is_custom=False.
        ch4_desc = next(
            gd for gd in structure.guest_descriptors if gd.mol_type == "ch4"
        )
        assert ch4_desc.is_custom is False
