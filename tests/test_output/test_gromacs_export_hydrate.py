"""E2E tests for HydrateGROMACSExporter (Tab 1 — Hydrate).

Tests the hydrate-specific GROMACS exporter which differs from all other
exporters in two key ways:

1. Mock path: QFileDialog is in quickice.gui.hydrate_export (NOT quickice.gui.export)
2. Method signature: export_hydrate(structure, config) takes a HydrateConfig argument

The hydrate exporter uses write_multi_molecule_gro_file and
write_multi_molecule_top_file (multi-molecule writers), and the
MoleculetypeRegistry produces _H suffix names for hydrate guests
(e.g. CH4 → CH4_H).

Water ITP is always "tip4p-ice.itp" (not stem-based like Ice exporter).
Guest ITP uses its original filename (e.g. ch4_hydrate.itp).

Fixtures from conftest.py:
    - simple_hydrate_structure: 2 water + 1 CH4 guest HydrateStructure
    - simple_hydrate_config: minimal HydrateConfig (sI, ch4, 1x1x1)
    - mock_hydrate_save_dialog: factory → (save_path, dialog_patch, mb_patch)
    - mock_cancel_dialog: factory → (dialog_patch, mb_patch)
"""

import sys
from pathlib import Path

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quickice.gui.hydrate_export import HydrateGROMACSExporter

from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    assert_gro_top_consistent,
)


class TestHydrateGROMACSExporter:
    """End-to-end tests for hydrate GROMACS export (Tab 1)."""

    def test_export_creates_all_files(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Export creates .gro, .top, tip4p-ice.itp, and guest .itp files.

        Unlike Ice exporter, the water ITP is always named "tip4p-ice.itp"
        (not stem-based), and the guest ITP uses its original name
        (ch4_hydrate.itp).
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "hydrate_test.gro").exists()
        assert (tmp_path / "hydrate_test.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "ch4_hydrate.itp").exists()

    def test_export_cancelled_returns_false(
        self, simple_hydrate_structure, simple_hydrate_config, mock_cancel_dialog
    ):
        """Cancelled QFileDialog returns False.

        This test validates the CRITICAL mock path difference:
        HydrateGROMACSExporter is in quickice.gui.hydrate_export,
        NOT quickice.gui.export. Using the wrong path would cause
        the real QFileDialog to appear (hanging the test).
        """
        dialog_p, mb_p = mock_cancel_dialog(
            module_path="quickice.gui.hydrate_export"
        )
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is False

    def test_guest_itp_copied(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Guest ITP file (ch4_hydrate.itp) is copied to output directory.

        The copied ITP file must contain a [ moleculetype ] section
        with the CH4_H suffix used for hydrate cage guests.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        tmp_path = Path(save_path).parent
        guest_itp = tmp_path / "ch4_hydrate.itp"
        assert guest_itp.exists()

        content = guest_itp.read_text()
        assert "[ moleculetype ]" in content

    def test_top_file_references_guest_itp(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.top file references the guest ITP and uses MoleculetypeRegistry _H suffix.

        The .top file must:
        - Include #include "ch4_hydrate.itp" (guest ITP reference)
        - Use CH4_H in the [ molecules ] section (registry-registered name
          for hydrate guest, NOT the plain "CH4" name)
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        content = top_path.read_text()

        # The .top must include the guest ITP file
        assert '#include "ch4_hydrate.itp"' in content

        # The [ molecules ] section must use CH4_H (registry suffix)
        assert "CH4_H" in content

    def test_top_file_references_tip4p_ice(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.top file references tip4p-ice.itp and includes SOL water molecule count.

        The .top file must:
        - Include #include "tip4p-ice.itp"
        - Use SOL with the correct water molecule count in [ molecules ]
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        content = top_path.read_text()

        # The .top must include the TIP4P-ICE ITP
        assert '#include "tip4p-ice.itp"' in content

        # The [ molecules ] section must have SOL with water molecule count
        import re

        water_count = simple_hydrate_structure.water_count
        pattern = rf"SOL\s+{water_count}\b"
        assert re.search(pattern, content), (
            f"Expected 'SOL' with count {water_count} in [ molecules ] section. "
            f"Content:\n{content}"
        )

    def test_gro_file_guest_residue_name_has_h_suffix(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.gro file uses CH4_H residue name for hydrate cage guests.

        The .gro file residue names MUST match the .top [ molecules ] section
        and the guest .itp [ moleculetype ] name. For hydrate guests, this
        means the _H suffix (e.g. "CH4_H", not "CH4").

        This is critical because GROMACS matches .gro residue names against
        .top [ molecules ] entries — a mismatch causes a fatal error.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        gro_path = Path(save_path)
        content = gro_path.read_text()

        # The .gro must have CH4_H as residue name for hydrate cage guests
        # (NOT plain "CH4" which would mismatch the .top [ molecules ] entry)
        assert "CH4_H" in content, (
            f"Expected 'CH4_H' residue name in .gro file for hydrate guest. "
            f"Content:\n{content}"
        )

        # Verify the plain "CH4" residue name (without _H) does NOT appear
        # in residue name columns (5-char field at positions 5-10 in each line)
        # Check that no line has "  CH4" as residue name (5-char padded)
        for line in content.splitlines()[2:]:  # Skip title and atom count
            if line and not line.startswith("#") and len(line) >= 10:
                res_name_field = line[5:10].strip()
                if res_name_field == "CH4":
                    pytest.fail(
                        f"Found plain 'CH4' residue name in .gro file (should be 'CH4_H'). "
                        f"Line: {line!r}"
                    )

    def test_gro_top_cross_validation(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Cross-validate .gro and .top consistency for hydrate export.

        Uses assert_gro_top_consistent() which checks:
        1. GRO header atom count == actual atom lines
        2. Every molecule in .top [molecules] appears in .gro residues

        This catches the _H suffix bug: if .gro uses "CH4" but .top
        lists "CH4_H", GROMACS fatal-errors on the mismatch.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_xval.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        gro_path = save_path
        top_path = str(Path(save_path).with_suffix(".top"))

        # Run cross-validation
        assert_gro_top_consistent(gro_path, top_path)

    def test_top_sol_count_matches_water_count(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """SOL count in .top must equal water_count from the structure.

        Regression test for the THF=12 subtraction bug:
        If water_nmolecules were computed as (total_atoms - guest_nmolecules * 12) / 4
        instead of using structure.water_count, THF hydrates would get 2 extra SOL
        molecules (e.g., 138 instead of 136 for SII 1x1x1).

        The .top SOL count MUST match the structure's water_count, which comes
        from molecule_index counting (NOT subtraction).
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_sol_count.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        top_molecules = parse_top_molecules(str(top_path))

        expected_sol = simple_hydrate_structure.water_count
        actual_sol = top_molecules.get("SOL", 0)

        assert actual_sol == expected_sol, (
            f".top SOL count ({actual_sol}) does not match "
            f"structure.water_count ({expected_sol}). "
            f"This indicates water_nmolecules was computed by subtraction "
            f"using incorrect guest atom count instead of molecule_index. "
            f"For THF hydrate SII: (648 - 8*12)/4 = 138 (WRONG), "
            f"should be (648 - 8*13)/4 = 136 or use water_count directly."
        )


# ---------------------------------------------------------------------------
# Phase 42-03: Multi-guest writer unit tests (list[dict] custom_guest_info)
# ---------------------------------------------------------------------------
#
# These tests exercise the four hydrate GROMACS writers with the new
# ``custom_guest_info: list[dict] | None`` API (plan 42-03). They build a
# synthetic mixed HydrateStructure (2 water + 1 built-in CH4 + 1 custom
# ethanol) MANUALLY — no GenIce2 — so each test runs in <1s. The built-in
# CH4 is handled by the registry (hydrate_CH4 → "CH4_H"); the custom ethanol
# is described by a 1-element ``custom_guest_info`` list (mol_type="etoh_mix",
# residue_name="MOL_H", itp_path=quickice/data/custom/etoh.itp).
#
# These tests directly call the writer functions (NOT HydrateGROMACSExporter)
# so the writers are exercised in isolation — no GUI mocking, no grompp.


import numpy as np

from quickice.output.gromacs_writer import (
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


# Path to the bundled ethanol ITP — used as the custom guest's itp_path so
# the atomtypes merge in write_multi_molecule_top_file has a real file to
# parse (oh/ho/hc/c3/h1 atom types).
_ETOH_ITP = Path(__file__).resolve().parent.parent.parent / "quickice" / "data" / "custom" / "etoh.itp"


def _build_mixed_hydrate_structure() -> HydrateStructure:
    """Build a synthetic mixed hydrate: 2 water + 1 CH4 + 1 custom ethanol.

    22 atoms total (no GenIce2 — fast <1s):
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
        - 5 CH4 atoms: 1 × (C, H, H, H, H)        [built-in, mol_type="ch4"]
        - 9 ethanol atoms: 1 × (H, C, H, H, C, H, H, O, H)  [custom, mol_type="etoh_mix"]

    molecule_index order: water, water, ch4, etoh_mix — so the .gro residue
    order is SOL, SOL, CH4_H, MOL_H (matching the .top [molecules] order).
    """
    positions = np.zeros((22, 3))
    # Water (8 atoms)
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    # CH4 (5 atoms)
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]
    # Ethanol (9 atoms)
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

    cell = np.eye(3) * 1.2  # 1.2 nm cubic box

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),
        MoleculeIndex(13, 9, "etoh_mix"),
    ]

    # HydrateConfig with cage_guest_assignments is the Phase 42 explicit API,
    # but for writer unit tests we only need a minimal valid HydrateConfig.
    # Use built-in ch4 as the primary guest_type (validates without custom
    # metadata); the etoh_mix guest is described by custom_guest_info below.
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=config,
        lattice_info=lattice_info,
        report="test",
        guest_count=2,  # 1 CH4 + 1 ethanol
        water_count=2,
    )


def _build_registry_with_ch4_hydrate() -> MoleculetypeRegistry:
    """Build a MoleculetypeRegistry with CH4 registered as a hydrate guest.

    Mirrors what HydrateGROMACSExporter does for the built-in ch4 path: the
    registry maps hydrate_CH4 → "CH4_H" so write_multi_molecule_top_file's
    registry branch produces "CH4_H" in [ molecules ] (matching the .gro
    residue name).
    """
    reg = MoleculetypeRegistry()
    reg.register_hydrate_guest("CH4")
    return reg


def _custom_guest_info_etoh_mix() -> list[dict]:
    """Build the custom_guest_info list for the etoh_mix custom guest.

    A 1-element list (the ch4 built-in is handled by the registry, NOT by
    custom_guest_info — per plan: "ch4 is built-in so not in the list — the
    registry handles it").
    """
    return [
        {
            "mol_type": "etoh_mix",
            "residue_name": "MOL_H",
            "itp_path": _ETOH_ITP,
        }
    ]


class TestMultiGuestWriter:
    """Unit tests for the list[dict] custom_guest_info API (plan 42-03).

    Directly calls write_multi_molecule_gro_file / write_multi_molecule_top_file
    with a synthetic mixed HydrateStructure (2 water + 1 CH4 + 1 ethanol) —
    no GUI, no grompp, fast <1s per test.
    """

    def test_multi_guest_top_has_both_molecules(self, tmp_path):
        """.top [ molecules ] lists BOTH the built-in CH4_H and the custom MOL_H.

        The .top must contain:
        - SOL with count 2 (two water molecules)
        - CH4_H with count 1 (built-in CH4 guest, via the registry)
        - MOL_H with count 1 (custom ethanol guest, via custom_guest_info)

        This validates that the list[dict] custom_guest_info API + the
        custom_by_moltype dict drives res_name resolution for BOTH the
        built-in (registry) path AND the custom path simultaneously.
        """
        structure = _build_mixed_hydrate_structure()
        registry = _build_registry_with_ch4_hydrate()
        custom_guest_info = _custom_guest_info_etoh_mix()

        top_path = tmp_path / "mixed.top"
        write_multi_molecule_top_file(
            structure.molecule_index,
            str(top_path),
            registry=registry,
            custom_guest_info=custom_guest_info,
        )

        assert top_path.exists(), f".top not written: {top_path}"
        top_molecules = parse_top_molecules(str(top_path))

        # SOL (water) — 2 molecules
        assert top_molecules.get("SOL") == 2, (
            f".top [ molecules ] SOL count != 2 (got {top_molecules}). "
            f"Expected 2 water molecules."
        )
        # CH4_H (built-in ch4 via the registry) — 1 molecule
        assert top_molecules.get("CH4_H") == 1, (
            f".top [ molecules ] CH4_H count != 1 (got {top_molecules}). "
            f"Expected 1 built-in CH4 guest (registered via hydrate_CH4 → CH4_H)."
        )
        # MOL_H (custom ethanol via custom_guest_info) — 1 molecule
        assert top_molecules.get("MOL_H") == 1, (
            f".top [ molecules ] MOL_H count != 1 (got {top_molecules}). "
            f"Expected 1 custom ethanol guest (resolved via custom_by_moltype)."
        )
        # No UNK fallback
        assert "UNK" not in top_molecules, (
            f".top [ molecules ] contains 'UNK' (fallback) — a mol_type did not "
            f"resolve via registry OR custom_by_moltype. Molecules: {top_molecules}"
        )

    def test_multi_guest_gro_has_both_residues(self, tmp_path):
        """.gro residue names include BOTH CH4_H (built-in) and MOL_H (custom).

        The .gro residue-name columns must contain:
        - SOL (8 atoms — 2 water × 4 atoms)
        - CH4_H (5 atoms — 1 CH4 × 5 atoms)
        - MOL_H (9 atoms — 1 ethanol × 9 atoms)

        This validates that the list[dict] custom_guest_info API drives
        res_name resolution in write_multi_molecule_gro_file's per-molecule
        loop, so BOTH the built-in ch4 (registry → CH4_H) and the custom
        ethanol (custom_by_moltype → MOL_H) get their correct residue names.
        """
        structure = _build_mixed_hydrate_structure()
        registry = _build_registry_with_ch4_hydrate()
        custom_guest_info = _custom_guest_info_etoh_mix()

        gro_path = tmp_path / "mixed.gro"
        write_multi_molecule_gro_file(
            structure.positions,
            structure.molecule_index,
            structure.cell,
            str(gro_path),
            atom_names=structure.atom_names,
            registry=registry,
            custom_guest_info=custom_guest_info,
        )

        assert gro_path.exists(), f".gro not written: {gro_path}"
        gro_residues = parse_gro_residue_names(str(gro_path))

        # SOL (water) — 8 atom lines (2 mol × 4 atoms)
        assert "SOL" in gro_residues, (
            f".gro missing 'SOL' residue (got {sorted(set(gro_residues))})."
        )
        assert gro_residues.count("SOL") == 8, (
            f".gro has {gro_residues.count('SOL')} 'SOL' residues, expected 8 "
            f"(2 water molecules × 4 atoms). Got: {gro_residues}"
        )
        # CH4_H (built-in ch4 via registry) — 5 atom lines
        assert "CH4_H" in gro_residues, (
            f".gro missing 'CH4_H' residue (got {sorted(set(gro_residues))}). "
            f"Built-in ch4 should resolve via registry → 'CH4_H'."
        )
        assert gro_residues.count("CH4_H") == 5, (
            f".gro has {gro_residues.count('CH4_H')} 'CH4_H' residues, "
            f"expected 5 (1 CH4 molecule × 5 atoms). Got: {gro_residues}"
        )
        # MOL_H (custom ethanol via custom_guest_info) — 9 atom lines
        assert "MOL_H" in gro_residues, (
            f".gro missing 'MOL_H' residue (got {sorted(set(gro_residues))}). "
            f"Custom etoh_mix should resolve via custom_by_moltype → 'MOL_H'."
        )
        assert gro_residues.count("MOL_H") == 9, (
            f".gro has {gro_residues.count('MOL_H')} 'MOL_H' residues, "
            f"expected 9 (1 ethanol molecule × 9 atoms). Got: {gro_residues}"
        )
        # No UNK fallback
        assert "UNK" not in gro_residues, (
            f".gro contains 'UNK' residue (fallback) — a mol_type did not "
            f"resolve via registry OR custom_by_moltype. "
            f"Residues: {sorted(set(gro_residues))}"
        )

        # Cross-validate .gro and .top consistency (also writes the .top)
        top_path = tmp_path / "mixed.top"
        write_multi_molecule_top_file(
            structure.molecule_index,
            str(top_path),
            registry=registry,
            custom_guest_info=custom_guest_info,
        )
        assert_gro_top_consistent(str(gro_path), str(top_path))

    def test_custom_guest_info_list_backward_compat_none(self, tmp_path):
        """custom_guest_info=None produces the same built-in .top as before.

        Guards the None → empty-list equivalence: the atomtypes merge loop
        `for ci in (custom_guest_info or [])` is a no-op when None, and the
        custom_by_moltype dict is empty so the built-in registry/fallback path
        fires unchanged. The resulting .top must list only SOL + CH4_H (no
        MOL_H, no UNK) — identical to the pre-42-03 built-in single-guest .top.
        """
        structure = _build_mixed_hydrate_structure()
        # NOTE: we use the mixed structure but pass custom_guest_info=None.
        # The etoh_mix mol_type will fall through to the "else: UNK" branch
        # (no registry, no custom_guest_info) — this is the expected
        # pre-42-03 behavior for an unknown mol_type. The test asserts that
        # the built-in ch4 path (registry → CH4_H) is byte-identical to the
        # pre-42-03 path, and that None does not crash the writer.
        registry = _build_registry_with_ch4_hydrate()

        top_path = tmp_path / "builtin.top"
        write_multi_molecule_top_file(
            structure.molecule_index,
            str(top_path),
            registry=registry,
            custom_guest_info=None,  # explicit None — must not crash
        )

        assert top_path.exists(), f".top not written: {top_path}"
        top_molecules = parse_top_molecules(str(top_path))

        # Built-in path: SOL + CH4_H present (registry handles ch4)
        assert top_molecules.get("SOL") == 2, (
            f".top SOL count != 2 (got {top_molecules})."
        )
        assert top_molecules.get("CH4_H") == 1, (
            f".top CH4_H count != 1 (got {top_molecules}). "
            f"Built-in ch4 should still resolve via the registry when "
            f"custom_guest_info is None."
        )
        # etoh_mix (unknown to registry + no custom_guest_info) → UNK fallback
        # (pre-42-03 behavior for unknown mol_types — no regression)
        assert top_molecules.get("UNK") == 1, (
            f".top UNK count != 1 (got {top_molecules}). "
            f"etoh_mix with no custom_guest_info should fall through to UNK "
            f"(pre-42-03 behavior — None ≡ empty list)."
        )
        # MOL_H must NOT appear (custom_guest_info=None → no custom resolution)
        assert "MOL_H" not in top_molecules, (
            f".top contains 'MOL_H' with custom_guest_info=None — None should "
            f"be equivalent to an empty list (no custom resolution). "
            f"Molecules: {top_molecules}"
        )

    def test_single_dict_deprecated_warns(self, tmp_path):
        """A legacy single dict emits a DeprecationWarning and is wrapped.

        Phase 42-03 changes the API from dict to list[dict]. 42-05/42-07 will
        update all call sites to pass lists; until then, a missed call site
        passing a single dict gets a DeprecationWarning + 1-element wrap
        (transition safety, NOT silent wrong output). This test asserts the
        warning fires for all four writers.
        """
        structure = _build_mixed_hydrate_structure()
        registry = _build_registry_with_ch4_hydrate()
        # Legacy single dict (NOT wrapped in a list)
        legacy_dict = {
            "mol_type": "etoh_mix",
            "residue_name": "MOL_H",
            "itp_path": _ETOH_ITP,
        }

        # --- write_multi_molecule_gro_file warns --- #
        gro_path = tmp_path / "legacy_gro.gro"
        with pytest.warns(DeprecationWarning, match="list\\[dict\\]"):
            write_multi_molecule_gro_file(
                structure.positions,
                structure.molecule_index,
                structure.cell,
                str(gro_path),
                atom_names=structure.atom_names,
                registry=registry,
                custom_guest_info=legacy_dict,  # legacy single dict
            )
        # The wrap must produce correct output (MOL_H appears, no crash)
        gro_residues = parse_gro_residue_names(str(gro_path))
        assert "MOL_H" in gro_residues, (
            f"Legacy single-dict wrap did not produce 'MOL_H' residues. "
            f"Got: {sorted(set(gro_residues))}"
        )

        # --- write_multi_molecule_top_file warns --- #
        top_path = tmp_path / "legacy_top.top"
        with pytest.warns(DeprecationWarning, match="list\\[dict\\]"):
            write_multi_molecule_top_file(
                structure.molecule_index,
                str(top_path),
                registry=registry,
                custom_guest_info=legacy_dict,  # legacy single dict
            )
        top_molecules = parse_top_molecules(str(top_path))
        assert top_molecules.get("MOL_H") == 1, (
            f"Legacy single-dict wrap did not produce MOL_H in [ molecules ]. "
            f"Got: {top_molecules}"
        )

        # --- write_interface_gro_file warns (build a minimal interface) --- #
        # Reuse the mixed structure's positions/atom_names but wrapped in an
        # InterfaceStructure-shaped object. For the interface writers we need
        # an InterfaceStructure; build a minimal one inline.
        from quickice.structure_generation.types import InterfaceStructure

        iface = InterfaceStructure(
            positions=structure.positions,
            atom_names=structure.atom_names,
            cell=structure.cell,
            ice_atom_count=0,
            water_atom_count=8,
            ice_nmolecules=0,
            water_nmolecules=2,
            mode="slab",
            report="test",
            # Guest region: 5 CH4 + 9 ethanol = 14 atoms, 2 guest molecules
            guest_atom_count=14,
            guest_nmolecules=2,
            molecule_index=structure.molecule_index,
        )
        iface_gro = tmp_path / "legacy_iface.gro"
        with pytest.warns(DeprecationWarning, match="list\\[dict\\]"):
            from quickice.output.gromacs_writer import write_interface_gro_file
            write_interface_gro_file(iface, str(iface_gro), custom_guest_info=legacy_dict)

        # --- write_interface_top_file warns --- #
        iface_top = tmp_path / "legacy_iface.top"
        with pytest.warns(DeprecationWarning, match="list\\[dict\\]"):
            from quickice.output.gromacs_writer import write_interface_top_file
            write_interface_top_file(iface, str(iface_top), custom_guest_info=legacy_dict)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 42-08 Fix 1: structure-driven ITP staging regression test
# ══════════════════════════════════════════════════════════════════════════════
#
# Proves ITP staging is driven by structure.molecule_index (what's actually
# being exported) rather than config.cage_guest_assignments (what the panel
# says). When the user changes the lattice without regenerating,
# config.cage_guest_assignments becomes empty (sTprime has no cage rows) but
# the structure still carries the old mixed guests — driving from structure
# ensures the staged ITPs always match the exported .gro/.top content.
#
# This test would FAIL with the old config-driven code (the ITP staging loop
# is a no-op when cage_guest_assignments is empty → ch4_hydrate.itp +
# thf_hydrate.itp never staged) and PASSES with the structure-driven fix.

from quickice.structure_generation.types import (  # noqa: E402
    GuestDescriptor,
    HydrateLatticeInfo,
)
from quickice.structure_generation.types import GUEST_MOLECULES  # noqa: E402


def _build_mixed_ch4_thf_structure_with_descriptors() -> HydrateStructure:
    """Build a mixed CH4+THF HydrateStructure with guest_descriptors populated.

    26 atoms total (no GenIce2 — fast, deterministic):
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
        - 5 CH4 atoms: 1 × (C, H, H, H, H)            [built-in, mol_type="ch4"]
        - 13 THF atoms: 1 × (O, CA, CA, CB, CB, H×8)   [built-in, mol_type="thf"]

    guest_descriptors is populated as a real Phase 42 generator would
    (one GuestDescriptor per distinct guest mol_type). This is the key
    precondition that selects the structure-driven staging path in
    HydrateGROMACSExporter.export_hydrate.
    """
    positions = np.zeros((26, 3))
    # Water (8 atoms)
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    # CH4 (5 atoms)
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]
    # THF (13 atoms)
    for i in range(13):
        positions[13 + i] = [0.2 + 0.01 * i, 0.2, 0.2]

    atom_names = (
        ["OW", "HW1", "HW2", "MW"] * 2  # 2 water
        + ["C", "H", "H", "H", "H"]  # 1 CH4
        + ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]  # 1 THF
    )

    cell = np.eye(3) * 1.2  # 1.2 nm cubic box

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),
        MoleculeIndex(13, 13, "thf"),
    ]

    # guest_descriptors populated as a real Phase 42 generator would.
    guest_descriptors = [
        GuestDescriptor(
            mol_type="ch4",
            cage_key="small",
            guest_name=GUEST_MOLECULES["ch4"]["name"],
            guest_residue_name="",
            is_custom=False,
            atom_labels=list(GUEST_MOLECULES["ch4"]["atom_labels"]),
            atom_count=GUEST_MOLECULES["ch4"]["atoms"],
        ),
        GuestDescriptor(
            mol_type="thf",
            cage_key="large",
            guest_name=GUEST_MOLECULES["thf"]["name"],
            guest_residue_name="",
            is_custom=False,
            atom_labels=list(GUEST_MOLECULES["thf"]["atom_labels"]),
            atom_count=GUEST_MOLECULES["thf"]["atoms"],
        ),
    ]

    # Config simulating lattice change to sTprime WITHOUT regeneration:
    # sTprime has an empty cage_type_map → HydrateConfig.__post_init__ shim
    # synthesizes an EMPTY cage_guest_assignments dict. This is the exact
    # config/structure desync scenario from Issue 1.
    config = HydrateConfig(
        lattice_type="sTprime",
        guest_type="ch4",  # primary (legacy) — built-in, valid without metadata
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    assert config.cage_guest_assignments == {}, (
        "Test setup precondition: sTprime config must have empty "
        "cage_guest_assignments (simulating lattice change without regen). "
        f"Got: {dict(config.cage_guest_assignments)}"
    )

    # lattice_info reflects the structure's actual lattice (sI) — the structure
    # was generated as sI then the panel was switched to sTprime.
    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=config,
        lattice_info=lattice_info,
        report="test",
        guest_count=2,  # 1 CH4 + 1 THF
        water_count=2,
        guest_descriptors=guest_descriptors,
    )


class TestStructureDrivenItpStaging:
    """Regression tests for Phase 42-08 Fix 1: structure-driven ITP staging.

    The ITP staging loop in HydrateGROMACSExporter.export_hydrate must stage
    guest .itp files based on what's in structure.molecule_index (what the
    .gro/.top writers will reference), not what's in config.cage_guest_assignments
    (what the panel says). This prevents missing-ITP exports when config and
    structure are out of sync (lattice changed without regenerating).
    """

    def test_export_hydrate_stages_itps_from_structure_not_config(
        self, mock_hydrate_save_dialog
    ):
        """Both ch4_hydrate.itp + thf_hydrate.itp are staged even when config
        has empty cage_guest_assignments.

        Builds a mixed HydrateStructure (CH4 + THF in molecule_index, with
        guest_descriptors populated as a real Phase 42 generator would) and
        passes a config with EMPTY cage_guest_assignments (sTprime — simulating
        a lattice change without regeneration). Asserts BOTH built-in guest
        ITPs are staged to the output directory.

        This test would FAIL with the old config-driven code (the staging loop
        iterates the empty config.cage_guest_assignments → no-op → no guest
        ITPs staged) and PASSES with the structure-driven fix (staging iterates
        the structure's unique guest mol_types → both ITPs staged).
        """
        structure = _build_mixed_ch4_thf_structure_with_descriptors()
        # Precondition: the desync scenario is in effect.
        assert structure.config.cage_guest_assignments == {}, (
            "Precondition: config must have empty cage_guest_assignments "
            "(sTprime desync scenario)."
        )
        assert {"ch4", "thf"}.issubset(
            {m.mol_type for m in structure.molecule_index}
        ), "Precondition: structure must carry both ch4 + thf guests."
        assert len(structure.guest_descriptors) == 2, (
            "Precondition: structure must have 2 guest_descriptors (selects "
            "the structure-driven staging path)."
        )

        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("mixed_desync.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(structure, structure.config)

        assert result is True, "export_hydrate should succeed for mixed + desync"
        out_dir = Path(save_path).parent

        # Both built-in guest ITPs must be staged — driven by
        # structure.molecule_index, NOT config.cage_guest_assignments.
        assert (out_dir / "ch4_hydrate.itp").exists(), (
            "ch4_hydrate.itp must be staged even when config.cage_guest_assignments "
            "is empty (structure-driven staging — Phase 42-08 Fix 1). The old "
            "config-driven code would leave this file unstaged → grompp fails."
        )
        assert (out_dir / "thf_hydrate.itp").exists(), (
            "thf_hydrate.itp must be staged even when config.cage_guest_assignments "
            "is empty (structure-driven staging — Phase 42-08 Fix 1). The old "
            "config-driven code would leave this file unstaged → grompp fails."
        )

        # The .top must reference both ITPs (the writers iterate
        # structure.molecule_index, which has both ch4 + thf).
        top_path = out_dir / "mixed_desync.top"
        assert top_path.exists(), f".top not written: {top_path}"
        top_content = top_path.read_text()
        assert "ch4_hydrate.itp" in top_content, (
            ".top must #include ch4_hydrate.itp (driven by structure.molecule_index)."
        )
        assert "thf_hydrate.itp" in top_content, (
            ".top must #include thf_hydrate.itp (driven by structure.molecule_index)."
        )
