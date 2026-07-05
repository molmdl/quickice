"""E2E GUI export test for a CUSTOM guest hydrate (plan 41-06).

Verifies HydrateGROMACSExporter.export_hydrate branches on
``config.is_custom_guest`` and:

* Does NOT call ``_get_hydrate_guest_itp_path`` for the custom guest
  (uses ``config.guest_itp_path`` instead — no FileNotFoundError).
* Threads ``custom_guest_info`` to ``write_multi_molecule_gro_file``
  and ``write_multi_molecule_top_file`` (params added by 41-02 / 41-03).
* Calls ``transform_guest_itp`` with ``config.guest_residue_name`` so
  ``"MOL_H"`` (5 chars) passes ``validate_gro_residue_name`` instead of
  ``"ETOH_E2E_H"`` (8 chars) raising ValueError.

The test builds a minimal ``HydrateStructure`` (2 water + 1 ethanol)
manually — NO GenIce2 — so it stays fast (<<1s).

Fixtures:
    - mock_hydrate_save_dialog: factory from tests/test_output/conftest.py
      (returns (save_path, dialog_patch, mb_patch))

Helpers:
    - parse_gro_residue_names / parse_top_molecules / parse_top_includes
      from tests/e2e_export_helpers.py
"""

import re
import sys
from pathlib import Path

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quickice.gui.hydrate_export import HydrateGROMACSExporter
from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
)

from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_top_molecules,
    parse_top_includes,
)


# ---------------------------------------------------------------------------
# Helpers for parsing the exported ITP / .top atomtypes block
# ---------------------------------------------------------------------------


def _parse_moleculetype_name(itp_text: str) -> str | None:
    """Return the [ moleculetype ] name from an ITP, or None if absent.

    Looks for the ``[ moleculetype ]`` header and returns the first
    non-comment, non-blank token on the following data line.
    """
    lines = itp_text.splitlines()
    in_mt = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and "moleculetype" in stripped.lower():
            in_mt = True
            continue
        if in_mt:
            if not stripped or stripped.startswith(";") or stripped.startswith("#"):
                continue
            return stripped.split()[0]
    return None


def _count_atomtype_occurrences(top_text: str, atomtype_name: str) -> int:
    """Count uncommented data lines in the [ atomtypes ] block whose first
    token equals ``atomtype_name``.

    Walks the .top line-by-line tracking the active ``[ section ]``.  Inside
    ``[ atomtypes ]`` it skips comment / blank lines and counts data lines
    whose first whitespace-separated field equals ``atomtype_name``.
    """
    in_atomtypes = False
    count = 0
    for line in top_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped.strip("[] \t").lower()
            in_atomtypes = (section == "atomtypes")
            continue
        if not in_atomtypes:
            continue
        if not stripped or stripped.startswith(";") or stripped.startswith("#"):
            continue
        # Data line — first field is the atomtype name
        first = stripped.split()[0]
        if first == atomtype_name:
            count += 1
    return count


def _atomtypes_block_uncommented_headers(top_text: str) -> list[str]:
    """Return the list of uncommented ``[ atomtypes ]`` header lines.

    An empty list means the section is fully commented out (or absent).
    Used to confirm the .top writes a single active ``[ atomtypes ]``
    section header (the .top owns the atomtypes for the system).
    """
    headers = []
    for line in top_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and "atomtypes" in stripped.lower():
            headers.append(stripped)
    return headers


def _itp_atomtypes_section_active(itp_text: str) -> bool:
    """Return True if the ITP has an UNcommented ``[ atomtypes ]`` header.

    The transformed custom-guest ITP must have its [ atomtypes ] section
    fully commented out (``; [ atomtypes ]``) because the atomtypes live
    in the main .top file (per AGENTS.md / GROMACS convention).
    """
    for line in itp_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and "atomtypes" in stripped.lower():
            return True  # active (uncommented) header
    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def custom_etoh_config() -> HydrateConfig:
    """HydrateConfig for a custom ethanol guest (sI, 1x1x1).

    Uses the bundled ``quickice/data/custom/etoh.{gro,itp}`` fixtures so the
    test does not depend on cwd (paths resolve from the repo root).
    """
    return HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",          # not in GUEST_MOLECULES -> is_custom_guest
        guest_residue_name="MOL",        # <=3 chars -> "MOL_H" (5) passes validation
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )


@pytest.fixture
def custom_etoh_structure(custom_etoh_config) -> HydrateStructure:
    """Minimal custom hydrate: 2 water + 1 ethanol (17 atoms, no GenIce2).

    Mirrors ``simple_hydrate_structure`` from conftest.py but swaps the
    5-atom CH4 guest for a 9-atom ethanol guest so we exercise the custom
    branch of ``export_hydrate`` (is_custom_guest=True).
    """
    positions = np.zeros((17, 3))
    # Water atoms (8): two TIP4P molecules (OW, HW1, HW2, MW each)
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    # Ethanol guest atoms (9): H, C, H, H, C, H, H, O, H
    for i in range(9):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]

    atom_names = [
        # water mol 1
        "OW", "HW1", "HW2", "MW",
        # water mol 2
        "OW", "HW1", "HW2", "MW",
        # ethanol guest (matches etoh.itp [ atoms ] order)
        "H", "C", "H", "H", "C", "H", "H", "O", "H",
    ]

    cell = np.eye(3) * 1.2  # 1.2 nm cubic box

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),
    ]

    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=custom_etoh_config,
        lattice_info=lattice_info,
        report="test",
        guest_count=1,
        water_count=2,
    )


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestHydrateGROMACSExporterCustomGuest:
    """End-to-end GUI export for a CUSTOM guest hydrate (plan 41-06)."""

    def test_export_custom_guest(
        self,
        custom_etoh_structure,
        custom_etoh_config,
        mock_hydrate_save_dialog,
    ):
        """Custom ethanol hydrate exports .gro/.top/.itp with MOL_H names.

        Asserts the five must-have truths of plan 41-06:
        1. No FileNotFoundError — export succeeds (result is True).
        2. .gro residue names use ``MOL_H`` (not ``UNK``, not ``ETOH_E2E_H``).
        3. .top [ molecules ] lists ``SOL:2, MOL_H:1`` (no ``UNK``).
        4. .top ``#include`` directives reference ``etoh.itp`` and
           ``tip4p-ice.itp``.
        5. Copied ``etoh.itp`` has ``[ moleculetype ] MOL_H`` and a fully
           commented-out ``[ atomtypes ]`` section.
        6. .top ``[ atomtypes ]`` block merges ``oh`` and ``ho`` from the
           custom guest ITP, and ``hc``/``c3``/``h1`` each appear at most
           once (dedup).
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_custom.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                custom_etoh_structure, custom_etoh_config
            )

        # Truth 1: export succeeds (no FileNotFoundError, no ValueError)
        assert result is True, (
            "export_hydrate returned False for a custom guest — the "
            "is_custom_guest branch likely raised an exception (check the "
            "patched QMessageBox.critical call args for the error message)."
        )

        tmp = Path(save_path).parent
        gro_path = tmp / "hydrate_custom.gro"
        top_path = tmp / "hydrate_custom.top"
        etoh_itp_path = tmp / "etoh.itp"
        water_itp_path = tmp / "tip4p-ice.itp"

        # --- All four files exist -----------------------------------------
        assert gro_path.exists(), f"Missing .gro: {gro_path}"
        assert top_path.exists(), f"Missing .top: {top_path}"
        assert etoh_itp_path.exists(), f"Missing copied etoh.itp: {etoh_itp_path}"
        assert water_itp_path.exists(), f"Missing tip4p-ice.itp: {water_itp_path}"

        # --- Truth 2: .gro residue names ----------------------------------
        gro_residues = parse_gro_residue_names(str(gro_path))
        # 9 ethanol atoms -> MOL_H, 8 water atoms -> SOL
        assert "MOL_H" in gro_residues, (
            f".gro missing 'MOL_H' residue (got {sorted(set(gro_residues))}). "
            f"Custom guest should use config.guest_residue_name + '_H'."
        )
        assert gro_residues.count("MOL_H") == 9, (
            f".gro has {gro_residues.count('MOL_H')} 'MOL_H' residues, "
            f"expected 9 (one per ethanol atom). Got: {gro_residues}"
        )
        assert "SOL" in gro_residues, (
            f".gro missing 'SOL' water residue (got {sorted(set(gro_residues))})"
        )
        assert gro_residues.count("SOL") == 8, (
            f".gro has {gro_residues.count('SOL')} 'SOL' residues, "
            f"expected 8 (one per water atom). Got: {gro_residues}"
        )
        assert "UNK" not in gro_residues, (
            f".gro contains 'UNK' residue (fallback name) — custom_guest_info "
            f"was not threaded to write_multi_molecule_gro_file. "
            f"Residues: {sorted(set(gro_residues))}"
        )

        # --- Truth 3: .top [ molecules ] ----------------------------------
        top_molecules = parse_top_molecules(str(top_path))
        assert top_molecules.get("SOL") == 2, (
            f".top [ molecules ] SOL count != 2 (got {top_molecules}). "
            f"Expected 2 water molecules."
        )
        assert top_molecules.get("MOL_H") == 1, (
            f".top [ molecules ] MOL_H count != 1 (got {top_molecules}). "
            f"Expected 1 ethanol guest molecule."
        )
        assert "UNK" not in top_molecules, (
            f".top [ molecules ] contains 'UNK' (fallback name) — "
            f"custom_guest_info was not threaded to write_multi_molecule_top_file. "
            f"Molecules: {top_molecules}"
        )
        # Order-insensitive full equality
        assert top_molecules == {"SOL": 2, "MOL_H": 1}, (
            f".top [ molecules ] != {{'SOL': 2, 'MOL_H': 1}}. "
            f"Got: {top_molecules}"
        )

        # --- Truth 4: .top #include directives ----------------------------
        includes = parse_top_includes(str(top_path))
        assert "etoh.itp" in includes, (
            f".top #include missing 'etoh.itp' (got {includes}). "
            f"Custom guest ITP basename must be preserved."
        )
        assert "tip4p-ice.itp" in includes, (
            f".top #include missing 'tip4p-ice.itp' (got {includes})."
        )

        # --- Truth 5: copied etoh.itp transformed -------------------------
        etoh_text = etoh_itp_path.read_text()

        # 5a. [ moleculetype ] name is MOL_H (regex across the section)
        mt_name = _parse_moleculetype_name(etoh_text)
        assert mt_name == "MOL_H", (
            f"Copied etoh.itp [ moleculetype ] name != 'MOL_H' "
            f"(got {mt_name!r}). transform_guest_itp should rename the "
            f"moleculetype to '{{config.guest_residue_name}}_H' = 'MOL_H'."
        )

        # 5b. [ atomtypes ] section fully commented out (no active header)
        assert not _itp_atomtypes_section_active(etoh_text), (
            "Copied etoh.itp has an UNcommented [ atomtypes ] header — "
            "transform_guest_itp must comment out the section so atomtypes "
            "live only in the main .top file."
        )
        # Confirm the commented header is present (sanity: section existed)
        assert "; [ atomtypes ]" in etoh_text, (
            "Copied etoh.itp missing '; [ atomtypes ]' comment header — "
            "transform_guest_itp did not run comment_out_atomtypes_in_itp."
        )

        # 5c. [ atoms ] resname column is MOL_H (at least one data line)
        # The transformed ITP has 9 atom data lines; check at least one
        # contains 'MOL_H' in the resname (4th whitespace field).
        atoms_match = re.search(
            r"\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)",
            etoh_text,
            re.DOTALL | re.IGNORECASE,
        )
        assert atoms_match, (
            "Copied etoh.itp missing [ atoms ] section — transform_guest_itp "
            "must preserve the [ atoms ] block (only the resname is rewritten)."
        )
        atoms_body = atoms_match.group(1)
        # At least one MOL_H resname in the atoms block
        assert re.search(r"^\s*\d+\s+\S+\s+\d+\s+MOL_H\s+", atoms_body, re.MULTILINE), (
            "Copied etoh.itp [ atoms ] section has no resname 'MOL_H' — "
            "_rewrite_atoms_section_resname did not run with 'MOL_H'.\n"
            f"Atoms block:\n{atoms_body}"
        )

        # --- Truth 6: .top [ atomtypes ] merge + dedup --------------------
        top_text = top_path.read_text()

        # The .top has exactly one active [ atomtypes ] section header
        active_headers = _atomtypes_block_uncommented_headers(top_text)
        assert len(active_headers) == 1, (
            f".top has {len(active_headers)} active [ atomtypes ] headers "
            f"(expected 1). Headers: {active_headers}"
        )

        # oh and ho must be present (merged from etoh.itp — these are NEW
        # types not in TIP4P-ICE water or any built-in guest block)
        for name in ("oh", "ho"):
            count = _count_atomtype_occurrences(top_text, name)
            assert count >= 1, (
                f".top [ atomtypes ] missing '{name}' line — "
                f"_merge_custom_atomtypes did not pull oh/ho from etoh.itp."
            )

        # hc / c3 / h1 each at most once (dedup against any prior block;
        # in this test no built-in guest block fires so each appears
        # exactly once, but "at most once" is the safe contract)
        for name in ("hc", "c3", "h1"):
            count = _count_atomtype_occurrences(top_text, name)
            assert count <= 1, (
                f".top [ atomtypes ] has {count} '{name}' lines — "
                f"_merge_custom_atomtypes dedup failed (each atomtype must "
                f"appear at most once in the main .top)."
            )
