"""Unit tests for custom guest residue name in write_interface_gro_file.

Phase 41-04 (EXPORT-04 + EXPORT-05 / P3): When a hydrate system has a custom
guest molecule (e.g. ethanol with `mol_type == "etoh_e2e"`), the interface
GRO writer must:
  1. Emit the caller-supplied residue name (e.g. "MOL_H") instead of falling
     through to "UNK" (which is what `detect_guest_type_from_atoms` returning
     None produces — ethanol is not ch4/thf/co2/h2).
  2. Chunk the guest atoms by the `molecule_index` entry's `count` (9 for
     ethanol) instead of using the `count_guest_atoms` heuristic, which
     miscounts ethanol as 5 atoms (one C followed by H-pattern).

The `custom_guest_info` dict has the shape:
    {"mol_type": str, "residue_name": str, "itp_path": Path}
`itp_path` is unused by this GRO writer (it is consumed by the TOP writers
for the atomtypes merge) but is kept on the dict for a single consistent API
across plans 41-02..41-05.
"""

import sys
from pathlib import Path

import numpy as np

from quickice.output.gromacs_writer import write_interface_gro_file
from quickice.structure_generation.types import InterfaceStructure, MoleculeIndex

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e2e_export_helpers import parse_gro_residue_names, parse_gro_atom_count  # noqa: E402


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


def test_custom_guest_writes_mol_h(tmp_path):
    """Custom guest mol_type must emit residue name from custom_guest_info.

    The 9 guest atoms must all carry residue "MOL_H"; "UNK" must NOT appear
    anywhere; the 8 water atoms must carry "SOL".
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_custom.gro"
    write_interface_gro_file(iface, str(out_path), custom_guest_info=custom_guest_info)

    residue_names = parse_gro_residue_names(str(out_path))

    # Total atom lines: 8 water + 9 guest = 17
    assert len(residue_names) == 17, (
        f"Expected 17 atom lines (8 water + 9 guest), got {len(residue_names)}"
    )

    # The 8 water atoms carry "SOL"
    water_residues = residue_names[:8]
    assert all(r == "SOL" for r in water_residues), (
        f"Water atoms should carry 'SOL', got {water_residues}"
    )

    # The 9 guest atoms all carry "MOL_H"
    guest_residues = residue_names[8:]
    assert all(r == "MOL_H" for r in guest_residues), (
        f"Guest atoms should carry 'MOL_H', got {guest_residues}"
    )

    # "UNK" must be absent
    assert "UNK" not in residue_names, (
        "'UNK' residue name written for custom guest — P3 bug present"
    )


def test_custom_guest_atom_count(tmp_path):
    """GRO header atom count must be 8 + 9 = 17 (NOT 8 + 5 = 13).

    The `count_guest_atoms` heuristic miscounts ethanol as 5 atoms (one C
    followed by an H pattern). The metadata-driven path must chunk by the
    molecule_index entry's count (9) so the 9-atom ethanol is written as one
    whole molecule.
    """
    iface, custom_guest_info = _build_custom_guest_iface()
    out_path = tmp_path / "out_count.gro"
    write_interface_gro_file(iface, str(out_path), custom_guest_info=custom_guest_info)

    header_count = parse_gro_atom_count(str(out_path))
    assert header_count == 17, (
        f"Header atom count should be 17 (8 water + 9 guest), got {header_count}"
    )

    # Also verify actual atom lines match header (not 13)
    residue_names = parse_gro_residue_names(str(out_path))
    actual_atom_lines = len(residue_names)
    assert actual_atom_lines == 17, (
        f"Actual atom lines should be 17, got {actual_atom_lines} "
        f"(count_guest_atoms heuristic would yield 13)"
    )


def test_custom_branch_skips_detect(tmp_path, monkeypatch):
    """Custom branch must NOT call detect_guest_type_from_atoms (P3 / EXPORT-05).

    Monkeypatch detect_guest_type_from_atoms to raise AssertionError; the
    custom branch should never invoke it. If the call succeeds without
    raising, the custom branch is correctly bypassing the heuristic.
    """
    iface, custom_guest_info = _build_custom_guest_iface()

    def boom(_atom_names):
        raise AssertionError("detect_guest_type_from_atoms should not be called")

    monkeypatch.setattr(
        "quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom
    )

    out_path = tmp_path / "out_no_detect.gro"
    # Must NOT raise — proves the custom branch skips detect_guest_type_from_atoms
    write_interface_gro_file(iface, str(out_path), custom_guest_info=custom_guest_info)

    # Sanity: file was actually written
    assert out_path.exists(), "GRO file was not written"
    residue_names = parse_gro_residue_names(str(out_path))
    assert len(residue_names) == 17, (
        f"Expected 17 atom lines, got {len(residue_names)}"
    )


def test_builtin_ch4_unchanged(tmp_path, interface_with_ch4_guests):
    """Built-in ch4 path (no custom_guest_info) must remain byte-unchanged.

    The interface_with_ch4_guests fixture has a guest MoleculeIndex with
    mol_type "guest" (not "ch4"). The built-in path uses
    detect_guest_type_from_atoms which detects "ch4" from atom names
    (C, H, H, H, H) -> residue "CH4_H". This test guards the regression
    boundary: the built-in path is untouched by the P3 fix.
    """
    iface = interface_with_ch4_guests
    out_path = tmp_path / "builtin_ch4.gro"
    write_interface_gro_file(iface, str(out_path))

    residue_names = parse_gro_residue_names(str(out_path))

    # Built-in path produces "CH4_H" for ch4 guests
    assert "CH4_H" in residue_names, (
        f"Built-in ch4 path should produce 'CH4_H' residue, got {set(residue_names)}"
    )
    # SOL is always present for water/ice
    assert "SOL" in residue_names, (
        f"Built-in path should produce 'SOL' for water/ice, got {set(residue_names)}"
    )
    # "UNK" must be absent (ch4 is detected by the heuristic)
    assert "UNK" not in residue_names, (
        "'UNK' residue name written for built-in ch4 — built-in path regressed"
    )
