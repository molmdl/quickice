"""Unit tests for custom guest residue name in write_multi_molecule_gro_file.

Phase 41-02 (EXPORT-04): When a hydrate system has a custom guest molecule
(e.g. ethanol with `mol_type == "etoh_e2e"`), the GRO writer must emit the
caller-supplied residue name (e.g. "MOL_H") instead of falling through to
"UNK". This keeps the `.gro` residue names consistent with the `.top
[molecules]` entry (which uses the same `_H`-suffixed name) so `gmx grompp`
does not FATAL.

The `custom_guest_info` dict has the shape:
    {"mol_type": str, "residue_name": str, "itp_path": Path}
`itp_path` is unused by this GRO writer (it is consumed by the TOP writers
for the atomtypes merge) but is kept on the dict for a single consistent API
across plans 41-02..41-05.
"""

import sys
from pathlib import Path

import numpy as np

from quickice.output.gromacs_writer import write_multi_molecule_gro_file
from quickice.structure_generation.types import MoleculeIndex
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e2e_export_helpers import parse_gro_residue_names  # noqa: E402


# ── Synthetic custom-guest system (no GenIce2) ──────────────────────────────
# 2 water molecules (TIP4P: 4 atoms each: OW/HW1/HW2/MW = 8 atoms)
# 1 custom ethanol guest (9 atoms: H C H H C H H O H)
# Total = 17 atoms.


def _build_custom_guest_system():
    """Build a tiny synthetic 2-water + 1-custom-ethanol-guest system in memory."""
    positions = np.zeros((17, 3))
    atom_names = (
        ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
    )
    cell = np.eye(3) * 2.0
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
    ]
    custom_guest_info = {
        "mol_type": "etoh_e2e",
        "residue_name": "MOL_H",
        "itp_path": Path("quickice/data/custom/etoh.itp"),
    }
    return positions, atom_names, cell, molecule_index, custom_guest_info


def test_custom_guest_writes_mol_h(tmp_path):
    """Custom guest mol_type must emit residue name from custom_guest_info.

    The 9 guest atoms (mol.count == 9) must all carry residue "MOL_H", and
    "UNK" must NOT appear anywhere (the previous fall-through behaviour).
    """
    positions, atom_names, cell, molecule_index, custom_guest_info = (
        _build_custom_guest_system()
    )
    out_path = tmp_path / "out_custom.gro"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(out_path),
        atom_names=atom_names,
        custom_guest_info=custom_guest_info,
    )

    residue_names = parse_gro_residue_names(str(out_path))

    # Total atom lines: 8 water + 9 guest = 17
    assert len(residue_names) == 17, (
        f"Expected 17 atom lines, got {len(residue_names)}: {residue_names}"
    )

    # The 9 guest atoms (last 9 entries) must all be "MOL_H"
    guest_residues = residue_names[-9:]
    assert all(r == "MOL_H" for r in guest_residues), (
        f"Expected all 9 guest residues to be 'MOL_H', got {guest_residues}"
    )

    # "MOL_H" must be present; "UNK" must NOT appear
    assert "MOL_H" in residue_names, f"'MOL_H' absent: {residue_names}"
    assert "UNK" not in residue_names, (
        f"'UNK' present in custom-guest output (fall-through bug): {residue_names}"
    )


def test_water_still_sol(tmp_path):
    """Built-in water path must still emit "SOL" residues (no regression)."""
    positions, atom_names, cell, molecule_index, custom_guest_info = (
        _build_custom_guest_system()
    )
    out_path = tmp_path / "out_water.gro"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(out_path),
        atom_names=atom_names,
        custom_guest_info=custom_guest_info,
    )

    residue_names = parse_gro_residue_names(str(out_path))

    # The first 8 atoms (2 water molecules x 4 atoms) must be "SOL"
    water_residues = residue_names[:8]
    assert all(r == "SOL" for r in water_residues), (
        f"Expected 8 'SOL' water residues, got {water_residues}"
    )
    assert "SOL" in residue_names, f"'SOL' absent: {residue_names}"


def test_builtin_ch4_unchanged_without_custom_info(tmp_path):
    """Built-in CH4 hydrate path must remain unchanged when custom_guest_info is None.

    Builds a 1-water + 1-CH4 system and registers the hydrate guest via
    MoleculetypeRegistry. With NO custom_guest_info, the writer must use the
    registry path → "CH4_H" residues for the guest and "SOL" for water.
    "UNK" must not appear.
    """
    # 1 water (4 atoms) + 1 ch4 (5 atoms: C/H/H/H/H) = 9 atoms total
    positions = np.zeros((9, 3))
    atom_names = ["OW", "HW1", "HW2", "MW", "C", "H", "H", "H", "H"]
    cell = np.eye(3) * 2.0
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 5, "ch4"),
    ]

    registry = MoleculetypeRegistry()
    registry.register_hydrate_guest("CH4")

    out_path = tmp_path / "out_ch4.gro"
    # No custom_guest_info → defaults to None → built-in/registry path
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(out_path),
        atom_names=atom_names,
        registry=registry,
    )

    residue_names = parse_gro_residue_names(str(out_path))

    assert len(residue_names) == 9, (
        f"Expected 9 atom lines, got {len(residue_names)}: {residue_names}"
    )
    assert "CH4_H" in residue_names, (
        f"'CH4_H' absent (registry path broken): {residue_names}"
    )
    assert "SOL" in residue_names, f"'SOL' absent: {residue_names}"
    assert "UNK" not in residue_names, (
        f"'UNK' present for built-in guest (regression): {residue_names}"
    )


def test_custom_residue_passes_validate():
    """The custom residue name 'MOL_H' must satisfy the 5-char GRO limit.

    This is a belt-and-braces explicit assertion; tests 1-2 implicitly prove
    no ValueError is raised when the writer calls validate_gro_residue_name.
    """
    assert len("MOL_H") <= 5
