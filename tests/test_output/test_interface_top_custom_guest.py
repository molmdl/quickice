"""Unit tests for custom guest metadata in write_interface_top_file.

Phase 41-05 (EXPORT-01 + EXPORT-03 + EXPORT-05 / P3): When a hydrate system
has a custom guest molecule (e.g. ethanol with `mol_type == "etoh_e2e"`), the
interface TOP writer must:

  1. Emit `custom_guest_info["residue_name"]` (e.g. "MOL_H") in `[ molecules ]`
     with the correct count (EXPORT-01). Today the writer calls
     `detect_guest_type_from_atoms`, which returns None for ethanol, so the
     `if guest_type:` gate at the `[ molecules ]` block omits the guest
     entirely (and the CH4 fallback atomtypes block is written instead of the
     real guest atomtypes).
  2. Merge the custom guest atomtypes via `_merge_custom_atomtypes`
     (oh/ho written, hc/c3/h1 deduped against water/GAFF2) instead of writing
     the CH4 fallback block (EXPORT-03).
  3. `#include` the custom guest `.itp` filename (e.g. "etoh.itp").
  4. NOT call `detect_guest_type_from_atoms` (P3 / EXPORT-05) — the custom
     branch is metadata-driven.

The `custom_guest_info` dict has the shape:
    {"mol_type": str, "residue_name": str, "itp_path": Path}
identical to plans 41-02/41-03/41-04. `itp_path` is consumed here for the
atomtypes merge + the `#include` filename.

The built-in ch4 path (no `custom_guest_info`) must remain byte-unchanged:
`[ molecules ]` lists `CH4_H` and `#include "ch4_hydrate.itp"`.
"""

import re
import sys
from pathlib import Path

import numpy as np
import pytest

from quickice.output.gromacs_writer import write_interface_top_file
from quickice.structure_generation.types import InterfaceStructure, MoleculeIndex

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e2e_export_helpers import parse_top_molecules, parse_top_includes  # noqa: E402


# ── Synthetic custom-guest InterfaceStructure (no GenIce2) ──────────────────
# 2 water molecules (TIP4P: 4 atoms each: OW/HW1/HW2/MW = 8 atoms)
# 1 custom ethanol guest (9 atoms: H C H H C H H O H)
# Total = 17 atoms. 0 ice.


def _build_custom_guest_iface():
    """Build a tiny synthetic 0-ice + 2-water + 1-custom-ethanol InterfaceStructure."""
    atom_names = (
        ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
    )
    positions = np.zeros((17, 3))
    positions[:, 0] = np.linspace(0.01, 0.17, 17)
    cell = np.eye(3) * 2.0
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
    ]
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=0,
        water_atom_count=8,
        ice_nmolecules=0,
        water_nmolecules=2,
        mode="hydrate",
        report="test",
        guest_atom_count=9,
        guest_nmolecules=1,
        molecule_index=molecule_index,
    )
    custom_guest_info = {
        "mol_type": "etoh_e2e",
        "residue_name": "MOL_H",
        "itp_path": Path("quickice/data/custom/etoh.itp"),
    }
    return iface, custom_guest_info


def _read_atomtypes_block(top_path):
    """Return the concatenated text of the [ atomtypes ] block."""
    in_block = False
    lines = []
    with open(top_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("["):
                section = stripped.strip("[] \t").lower()
                in_block = (section == "atomtypes")
                continue
            if in_block:
                # Stop on blank-line boundary? No — keep collecting until next section.
                lines.append(line)
    # Trim trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()
    return "".join(lines)


def test_molecules_has_mol_h(tmp_path):
    """`[ molecules ]` must list `MOL_H` with count 1 (and SOL with count 2).

    Today the writer calls `detect_guest_type_from_atoms` which returns None
    for ethanol, so the `if guest_type:` gate at the `[ molecules ]` block
    omits the guest entirely. With `custom_guest_info`, the custom branch
    must write `custom_guest_info["residue_name"]` directly.
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_mol.top"
    write_interface_top_file(
        iface, str(out_path), custom_guest_info=custom_guest_info
    )

    molecules = parse_top_molecules(str(out_path))
    assert molecules.get("SOL") == 2, (
        f"Expected SOL=2, got {molecules.get('SOL')} (full: {molecules})"
    )
    assert molecules.get("MOL_H") == 1, (
        f"Expected MOL_H=1, got {molecules.get('MOL_H')} (full: {molecules})"
    )
    assert "UNK" not in molecules, (
        f"'UNK' must NOT appear in [ molecules ]; got {molecules}"
    )


def test_atomtypes_has_oh_ho(tmp_path):
    """`[ atomtypes ]` must include lines starting with `oh` and `ho`.

    The CH4 fallback only writes `c3`/`hc`. The custom merge must add the
    ethanol-specific atomtypes `oh` and `ho` from `etoh.itp`.
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_at.top"
    write_interface_top_file(
        iface, str(out_path), custom_guest_info=custom_guest_info
    )

    block = _read_atomtypes_block(out_path)
    assert re.search(r"^oh\b", block, re.MULTILINE), (
        f"[ atomtypes ] block missing 'oh' atomtype (ethanol oxygen):\n{block}"
    )
    assert re.search(r"^ho\b", block, re.MULTILINE), (
        f"[ atomtypes ] block missing 'ho' atomtype (ethanol hydroxyl H):\n{block}"
    )


def test_atomtypes_dedup(tmp_path):
    """`hc`, `c3`, `h1` each appear at most once in `[ atomtypes ]`.

    `_merge_custom_atomtypes` dedups against the pre-seeded `written` dict
    (water + GAFF2). The CH4 fallback writes a second copy of `c3`/`hc`,
    which the custom branch must NOT do.
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_dup.top"
    write_interface_top_file(
        iface, str(out_path), custom_guest_info=custom_guest_info
    )

    block = _read_atomtypes_block(out_path)
    for name in ("hc", "c3", "h1"):
        matches = re.findall(rf"^{name}\b", block, re.MULTILINE)
        assert len(matches) <= 1, (
            f"atomtype '{name}' appears {len(matches)} times in [ atomtypes ] "
            f"(expected <= 1 after dedup):\n{block}"
        )


def test_includes_etoh_itp(tmp_path):
    """`#include` directives must list `etoh.itp` and `tip4p-ice.itp`.

    The custom `.itp` filename is the basename of
    `custom_guest_info["itp_path"]`.
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_inc.top"
    write_interface_top_file(
        iface, str(out_path), custom_guest_info=custom_guest_info
    )

    includes = parse_top_includes(str(out_path))
    assert "tip4p-ice.itp" in includes, (
        f"Missing #include 'tip4p-ice.itp' (got {includes})"
    )
    assert "etoh.itp" in includes, (
        f"Missing #include 'etoh.itp' for custom guest (got {includes})"
    )


def test_custom_branch_skips_detect(tmp_path, monkeypatch):
    """Custom branch must NOT call detect_guest_type_from_atoms (P3 / EXPORT-05).

    Monkeypatch detect_guest_type_from_atoms to raise AssertionError; the
    custom branch must never invoke it.
    """
    iface, custom_guest_info = _build_custom_guest_iface()

    def boom(*args, **kwargs):
        raise AssertionError("detect_guest_type_from_atoms should not be called")

    monkeypatch.setattr(
        "quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom
    )

    out_path = tmp_path / "out_no_detect.top"
    # Must NOT raise — proves the custom branch bypasses detect_guest_type_from_atoms
    write_interface_top_file(
        iface, str(out_path), custom_guest_info=custom_guest_info
    )

    # Sanity: file was actually written
    assert out_path.exists(), "TOP file was not written"


def test_builtin_ch4_regression(tmp_path, interface_with_ch4_guests):
    """Built-in ch4 path (no custom_guest_info) must remain byte-unchanged.

    The interface_with_ch4_guests fixture has a guest MoleculeIndex with
    mol_type "guest" (not "ch4"). The built-in path uses
    detect_guest_type_from_atoms which detects "ch4" from atom names
    (C, H, H, H, H) -> residue "CH4_H", #include "ch4_hydrate.itp".
    This test guards the regression boundary: the built-in path is untouched
    by the P3 fix.
    """
    iface = interface_with_ch4_guests
    out_path = tmp_path / "builtin_ch4.top"
    write_interface_top_file(iface, str(out_path))

    molecules = parse_top_molecules(str(out_path))
    assert "CH4_H" in molecules, (
        f"Built-in ch4 path should produce 'CH4_H' residue, got {molecules}"
    )
    assert "SOL" in molecules, (
        f"Built-in path should produce 'SOL' for water/ice, got {molecules}"
    )
    assert "UNK" not in molecules, (
        f"'UNK' must NOT appear for built-in ch4, got {molecules}"
    )

    includes = parse_top_includes(str(out_path))
    assert "ch4_hydrate.itp" in includes, (
        f"Built-in ch4 path should #include 'ch4_hydrate.itp', got {includes}"
    )
    assert "tip4p-ice.itp" in includes, (
        f"Built-in path should #include 'tip4p-ice.itp', got {includes}"
    )
