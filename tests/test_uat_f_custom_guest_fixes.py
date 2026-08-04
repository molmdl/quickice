"""Tests for UAT-F custom guest / custom molecule fixes (2026-08-04).

Two independent bugs found during UAT Workflow F:

Issue 1: validate_custom_guest_files didn't check ITP [atoms] resname vs GRO
  resname — etoh_long_name.itp (ITP resname "ETHANOL") paired with etoh.gro
  (GRO resname "MOL") passed validation silently. Fixed by adding atom_resname
  to ITPMoleculeInfo + a mismatch check in validate_custom_guest_files.
  (Tested in tests/test_custom_guest_bridge.py::test_validate_rejects_itp_resname_mismatch)

Issue 2: GUI exporters staged the custom molecule ITP to a colliding basename
  (both "etoh.itp"), and the 3 top-file writers each emitted TWO
  #include "etoh.itp" lines -> grompp "moleculetype etoh redefined". Fixed by
  detecting the collision in the exporters, renaming the custom molecule ITP
  copy to "{stem}_L.itp" (mirroring the _H/_L convention), and passing the
  renamed name to the writers via a new custom_molecule_itp_name kwarg.
"""

import os

# Ensure headless Qt works for the import of quickice.gui.export.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest


# ── Issue 2: _resolve_custom_molecule_itp_name helper ──────────────────────


class TestResolveCustomMoleculeItpName:
    """Tests for the collision detection + rename helper (UAT-F Issue 2 fix).

    The helper detects when the custom molecule ITP basename collides with a
    cage-guest ITP basename (both "etoh.itp") and renames the custom molecule
    copy to "{stem}_L.itp" (e.g. "etoh_L.itp"), mirroring the built-in _H/_L
    convention (ch4_hydrate.itp / ch4_liquid.itp).
    """

    def test_no_collision_returns_original_name_no_rename(self):
        """When the custom molecule ITP basename is NOT in the staged guest
        ITPs, the helper returns the original name and None (no rename needed).
        """
        from quickice.gui.export import _resolve_custom_molecule_itp_name

        dest_name, itp_name_for_include = _resolve_custom_molecule_itp_name(
            "/some/path/etoh.itp",
            staged_guest_itps={"ch4_hydrate.itp": "/output/ch4_hydrate.itp"},
        )
        assert dest_name == "etoh.itp"
        assert itp_name_for_include is None

    def test_collision_renames_to_stem_L_suffix(self):
        """When the custom molecule ITP basename collides with a staged
        cage-guest ITP, the helper renames to "{stem}_L{suffix}" (e.g.
        "etoh_L.itp") and returns the renamed name for the #include.
        """
        from quickice.gui.export import _resolve_custom_molecule_itp_name

        dest_name, itp_name_for_include = _resolve_custom_molecule_itp_name(
            "/some/path/etoh.itp",
            staged_guest_itps={"etoh.itp": "/output/etoh.itp"},
        )
        assert dest_name == "etoh_L.itp"
        assert itp_name_for_include == "etoh_L.itp"

    def test_empty_staged_guest_itps_no_collision(self):
        """When no cage-guest ITPs are staged (empty dict), no collision."""
        from quickice.gui.export import _resolve_custom_molecule_itp_name

        dest_name, itp_name_for_include = _resolve_custom_molecule_itp_name(
            "/some/path/etoh.itp",
            staged_guest_itps={},
        )
        assert dest_name == "etoh.itp"
        assert itp_name_for_include is None

    def test_none_staged_guest_itps_no_collision(self):
        """When staged_guest_itps is None (no hydrate config), no collision."""
        from quickice.gui.export import _resolve_custom_molecule_itp_name

        dest_name, itp_name_for_include = _resolve_custom_molecule_itp_name(
            "/some/path/etoh.itp",
            staged_guest_itps=None,
        )
        assert dest_name == "etoh.itp"
        assert itp_name_for_include is None

    def test_built_in_guest_itp_no_collision_with_custom(self):
        """Built-in cage-guest ITP (ch4_hydrate.itp) does NOT collide with a
        custom molecule ITP (etoh.itp) — different basenames by design.
        """
        from quickice.gui.export import _resolve_custom_molecule_itp_name

        dest_name, itp_name_for_include = _resolve_custom_molecule_itp_name(
            "/some/path/etoh.itp",
            staged_guest_itps={"ch4_hydrate.itp": "/output/ch4_hydrate.itp"},
        )
        assert dest_name == "etoh.itp"
        assert itp_name_for_include is None


# ── Issue 2: writer custom_molecule_itp_name kwarg ──────────────────────────


class TestWriterCustomMoleculeItpNameKwarg:
    """Tests that the 3 top-file writers honor the custom_molecule_itp_name
    kwarg for the custom molecule #include statement (UAT-F Issue 2 fix).

    When the exporter detects a basename collision and renames the custom
    molecule ITP copy to "etoh_L.itp", it passes custom_molecule_itp_name=
    "etoh_L.itp" to the writer. The writer must emit #include "etoh_L.itp"
    (not the original basename "etoh.itp") to match the staged filename.
    """

    def test_write_custom_molecule_top_file_uses_renamed_include(self, tmp_path):
        """write_custom_molecule_top_file emits #include "{custom_molecule_itp_name}"
        when the kwarg is provided (collision rename path).
        """
        from quickice.output.custom_writer import write_custom_molecule_top_file
        from quickice.structure_generation.types import (
            CustomMoleculeStructure, MoleculeIndex,
        )
        import numpy as np

        # Minimal CustomMoleculeStructure: 1 SOL, no guests, with an ITP path.
        itp_path = tmp_path / "etoh.itp"
        itp_path.write_text(
            "[ moleculetype ]\n; name nrexcl\netoh 3\n"
            "[ atoms ]\n; type res resname atom cgnr charge mass\n"
            "  1 hc 1 etoh H 1 0.0 1.0\n"
        )
        structure = CustomMoleculeStructure(
            positions=np.zeros((4, 3)),
            atom_names=["OW", "HW1", "HW2", "MW"],
            cell=np.eye(3) * 3.0,
            molecule_index=[MoleculeIndex(0, 4, "water")],
            ice_atom_count=0,
            water_atom_count=4,
            custom_molecule_atom_count=0,
            ice_nmolecules=0,
            water_nmolecules=1,
            itp_path=itp_path,
            moleculetype_name="etoh",
        )
        top_path = tmp_path / "custom.top"
        write_custom_molecule_top_file(
            structure, str(top_path),
            custom_guest_info=None,
            custom_molecule_itp_name="etoh_L.itp",
        )
        content = top_path.read_text()
        assert '#include "etoh_L.itp"' in content, (
            f"expected #include etoh_L.itp (renamed), got content:\n{content}"
        )
        assert '#include "etoh.itp"' not in content, (
            f"should NOT have the original basename #include (collision), "
            f"got content:\n{content}"
        )

    def test_write_custom_molecule_top_file_default_uses_basename(self, tmp_path):
        """write_custom_molecule_top_file emits #include "{itp_path.name}" when
        custom_molecule_itp_name is None (no collision, default path).
        """
        from quickice.output.custom_writer import write_custom_molecule_top_file
        from quickice.structure_generation.types import (
            CustomMoleculeStructure, MoleculeIndex,
        )
        import numpy as np

        itp_path = tmp_path / "etoh.itp"
        itp_path.write_text(
            "[ moleculetype ]\n; name nrexcl\netoh 3\n"
            "[ atoms ]\n; type res resname atom cgnr charge mass\n"
            "  1 hc 1 etoh H 1 0.0 1.0\n"
        )
        structure = CustomMoleculeStructure(
            positions=np.zeros((4, 3)),
            atom_names=["OW", "HW1", "HW2", "MW"],
            cell=np.eye(3) * 3.0,
            molecule_index=[MoleculeIndex(0, 4, "water")],
            ice_atom_count=0,
            water_atom_count=4,
            custom_molecule_atom_count=0,
            ice_nmolecules=0,
            water_nmolecules=1,
            itp_path=itp_path,
            moleculetype_name="etoh",
        )
        top_path = tmp_path / "custom.top"
        write_custom_molecule_top_file(
            structure, str(top_path),
            custom_guest_info=None,
            custom_molecule_itp_name=None,
        )
        content = top_path.read_text()
        assert '#include "etoh.itp"' in content, (
            f"expected #include etoh.itp (default basename), got:\n{content}"
        )
