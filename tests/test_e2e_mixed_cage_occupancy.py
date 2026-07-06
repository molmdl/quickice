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


# ══════════════════════════════════════════════════════════════════════════════
# Phase 42-05: GUI mixed-guest grompp e2e (MIXED-04, GUI path)
# ══════════════════════════════════════════════════════════════════════════════
#
# Proves ``gmx grompp`` exits 0 on a mixed hydrate (built-in CH4 + custom
# ethanol) exported via the GUI multi-molecule writers
# (``write_multi_molecule_gro_file`` + ``write_multi_molecule_top_file`` with a
# ``custom_guest_info`` LIST + ``MoleculetypeRegistry``), with ITPs staged via
# ``_stage_itp_files`` + ``_stage_custom_guest_itp``.  Closes MIXED-04 for the
# GUI path (the CLI half is plan 42-07).
#
# Pattern: synthetic 2-water + 1-CH4 + 1-ethanol system (22 atoms, no GenIce2,
# <1s) → write_multi_molecule_* (custom_guest_info list + registry) → stage
# ITPs → assert_itp_completeness + assert_gro_top_consistent → run_gmx_grompp
# (exit 0).  Mirrors the 41-10 single-custom-guest pattern, extended to mixed
# occupancy (built-in CH4 via registry + custom ethanol via custom_guest_info
# fire in the SAME .gro/.top).

import shutil
from pathlib import Path

import numpy as np

# Add tests/ directory to sys.path for e2e_export_helpers import.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.types import MoleculeIndex  # noqa: E402
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _stage_itp_files,
    _stage_custom_guest_itp,
    run_gmx_grompp,
    MDP_PATH,
    ETOH_ITP,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


@gmx_skipif
def test_mixed_gui_grompp_passes(tmp_path):
    """gmx grompp exits 0 on a mixed hydrate (CH4 + custom ethanol) exported
    via the GUI multi-molecule writers (write_multi_molecule_gro_file +
    write_multi_molecule_top_file with a custom_guest_info LIST + registry).

    Builds a tiny synthetic 2-water + 1-CH4 + 1-ethanol system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 5 CH4 atoms + 9
    ethanol atoms = 22 atoms.  Stages tip4p-ice.itp + ch4_hydrate.itp +
    the transformed etoh.itp (moleculetype MOL_H), then runs gmx grompp.

    The built-in CH4 resolves via the registry (hydrate_CH4 -> "CH4_H"); the
    custom ethanol resolves via custom_guest_info (etoh_mix -> "MOL_H").
    Both fire in the SAME .gro/.top — the defining property of mixed cage
    occupancy (MIXED-04, GUI path).
    """
    # Synthetic 2-water + 1-CH4 + 1-ethanol system (22 atoms total).
    # molecule_index start indices (per plan, "adjust start indices
    # carefully — water 0-7, ch4 8-12, etoh 13-21"):
    #   water 1: atoms 0-3   (start=0,  count=4)
    #   water 2: atoms 4-7   (start=4,  count=4)
    #   CH4:     atoms 8-12  (start=8,  count=5)
    #   ethanol: atoms 13-21 (start=13, count=9)
    positions = np.zeros((22, 3))
    # Water (8 atoms: 2 × OW,HW1,HW2,MW)
    for i in range(8):
        positions[i] = [0.01 * (i + 1), 0.01 * (i + 1), 0.01 * (i + 1)]
    # CH4 (5 atoms: C,H,H,H,H) — built-in, handled by registry
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]
    # Ethanol (9 atoms: H,C,H,H,C,H,H,O,H) — custom, handled by custom_guest_info
    for i in range(9):
        positions[13 + i] = [0.2 + 0.01 * i, 0.2, 0.2]

    atom_names = [
        # water mol 1
        "OW", "HW1", "HW2", "MW",
        # water mol 2
        "OW", "HW1", "HW2", "MW",
        # CH4 guest (built-in)
        "C", "H", "H", "H", "H",
        # ethanol guest (custom, matches etoh.itp [ atoms ] order)
        "H", "C", "H", "H", "C", "H", "H", "O", "H",
    ]

    # Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp); 3.0 nm gives a
    # comfortable margin (STATE [41-10] lesson: grompp rejects box exactly at
    # 2*cutoff; cutoff 1.0 nm < half the shortest box vector must be strict).
    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),        # built-in -> registry -> "CH4_H"
        MoleculeIndex(13, 9, "etoh_mix"),  # custom -> custom_guest_info -> "MOL_H"
    ]

    # Registry with the built-in CH4 registered (hydrate_CH4 -> "CH4_H").
    registry = MoleculetypeRegistry()
    registry.register_hydrate_guest("CH4")

    # custom_guest_info LIST (Phase 42 API): one entry per custom guest.
    # ch4 is built-in so NOT in the list — the registry handles it.
    custom_guest_info = [
        {
            "mol_type": "etoh_mix",
            "residue_name": "MOL_H",
            "itp_path": Path(ETOH_ITP),
        }
    ]
    # itp_files maps mol_type -> itp filename so the writer emits the correct
    # #include for each guest (ch4 -> ch4_hydrate.itp, etoh_mix -> etoh.itp).
    itp_files = {
        "ch4": "ch4_hydrate.itp",
        "etoh_mix": "etoh.itp",
    }

    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(gro),
        "mixed guest hydrate",
        atom_names=atom_names,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )
    write_multi_molecule_top_file(
        molecule_index,
        str(top),
        "mixed guest hydrate",
        itp_files=itp_files,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )

    # Stage MDP + ITPs (repo convention: writers don't copy ITPs; staging does).
    # _stage_itp_files stages tip4p-ice.itp + ch4_hydrate.itp + etoh.itp
    # (etoh under-transformed: moleculetype 'etoh', atomtypes commented out).
    # _stage_custom_guest_itp overwrites etoh.itp with the fully-transformed
    # copy (moleculetype 'MOL_H', [atoms] resname 'MOL_H') — the prerequisite
    # for gmx grompp to succeed.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    _stage_itp_files(str(top), ws)
    _stage_custom_guest_itp(ws, Path(ETOH_ITP), "MOL")

    # All #include'd ITPs present in the workspace.
    assert_itp_completeness(str(top), ws)
    # GRO residues <-> TOP [molecules] cross-check.
    assert_gro_top_consistent(str(gro), str(top))

    # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert exit_code == 0, f"gmx grompp failed (mixed GUI):\n{stderr}"

    # .top [molecules] lists SOL + CH4_H + MOL_H (the mixed-occupancy signature).
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "CH4_H" in mols and "MOL_H" in mols, (
        f"expected SOL + CH4_H + MOL_H in [molecules], got {mols}"
    )

    # .gro residues contain SOL + CH4_H + MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert {"SOL", "CH4_H", "MOL_H"}.issubset(gro_res), (
        f"expected SOL + CH4_H + MOL_H in .gro residues, got {gro_res}"
    )
