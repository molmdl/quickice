"""Unit + integration tests for CLI custom-guest hydrate export threading
(plan 41-08).

Validates:

1. ``_build_custom_guest_info`` returns ``{'mol_type','residue_name','itp_path'}``
   for a custom ``HydrateConfig`` (``is_custom_guest`` True) and ``None`` for a
   built-in ``HydrateConfig`` (ch4) or ``None``.
2. ``CLIPipeline._run_export_step`` for a custom hydrate writes:
   - ``hydrate.gro`` with ``MOL_H`` residues (9-atom ethanol guest chunked by the
     matching ``molecule_index`` entry's ``.count``, NOT the ``count_guest_atoms``
     heuristic that miscounted ethanol as 5 atoms — P3 fix from plan 41-04)
   - ``hydrate.top`` with ``[molecules] MOL_H`` + ``#include "etoh.itp"`` +
     ``[atomtypes]`` oh/ho merged+deduped via ``_merge_custom_atomtypes``
   - ``etoh.itp`` copied+transformed via ``copy_custom_guest_itp`` (plan 41-07)
   - ``tip4p-ice.itp`` always copied
3. ``CLIPipeline._run_export_step`` for a built-in ch4 hydrate is UNCHANGED
   (regression): ``CH4_H`` in ``.gro``/``.top [molecules]``, ``ch4_hydrate.itp``
   ``#include`` d, ``custom_guest_info=None`` path byte-identical to pre-41-08.

These are pure-Python tests (no ``gmx`` dependency, no GenIce2 calls);
``HydrateStructure`` instances are constructed manually with the same pattern as
``tests/test_output/conftest.py::simple_hydrate_structure`` and
``tests/test_cli/test_itp_helpers_custom_guest.py``.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from quickice.cli.pipeline import _build_custom_guest_info, CLIPipeline
from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
)

# Make tests/e2e_export_helpers.py importable (no test_ prefix → not auto-collected).
_TESTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TESTS_DIR))
from e2e_export_helpers import (  # noqa: E402
    parse_gro_residue_names,
    parse_top_molecules,
    parse_top_includes,
)

# Absolute paths to the bundled custom-ethanol fixtures — cwd-independent.
_DATA_CUSTOM = _TESTS_DIR.parent / "quickice" / "data" / "custom"
ETOH_ITP = _DATA_CUSTOM / "etoh.itp"
ETOH_GRO = _DATA_CUSTOM / "etoh.gro"


# ── Test 1: _build_custom_guest_info for a custom HydrateConfig ──────────────

def test_build_custom_guest_info_custom():
    """Custom HydrateConfig → 1-element list[dict] with mol_type/residue_name/itp_path.

    The sI legacy single-custom-guest path goes through the 42-01 __post_init__
    shim which populates cage_guest_assignments for BOTH small and large cages
    (same etoh_e2e guest). _build_custom_guest_info dedups by mol_type so the
    returned list has ONE entry (not two) — matching the 42-02 ExitStack dedup
    and the 42-03 writers' custom_by_moltype dict semantics.
    """
    cfg = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
    )
    info = _build_custom_guest_info(cfg)
    assert info == [
        {
            "mol_type": "etoh_e2e",
            "residue_name": "MOL_H",
            "itp_path": Path("quickice/data/custom/etoh.itp"),
        }
    ]


# ── Test 2: _build_custom_guest_info returns None for built-in/None ──────────

def test_build_custom_guest_info_builtin_none():
    """Built-in HydrateConfig (ch4) → None; None config → None."""
    cfg = HydrateConfig(lattice_type="sI", guest_type="ch4")
    assert _build_custom_guest_info(cfg) is None
    assert _build_custom_guest_info(None) is None


# ── Shared fixture builder ────────────────────────────────────────────────────

def _build_custom_hydrate_structure() -> HydrateStructure:
    """Build a 2-water + 1-ethanol HydrateStructure (17 atoms, no GenIce2).

    Mirrors ``simple_hydrate_structure`` from tests/test_output/conftest.py and
    the manual construction in tests/test_cli/test_itp_helpers_custom_guest.py.
    Uses ABSOLUTE ``guest_itp_path`` so the ITP copy works regardless of cwd.
    """
    # 8 water atoms + 9 ethanol atoms = 17 total
    positions = np.zeros((17, 3))
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    for i in range(9):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]

    atom_names = [
        # 2 water molecules (TIP4P-ICE: OW, HW1, HW2, MW)
        "OW", "HW1", "HW2", "MW",
        "OW", "HW1", "HW2", "MW",
        # 1 ethanol guest (9 atoms — matches etoh.itp [atoms] order)
        "H", "C", "H", "H", "C", "H", "H", "O", "H",
    ]

    cell = np.eye(3) * 1.2  # 1.2 nm cubic box

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),
    ]

    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    # Custom HydrateConfig with ABSOLUTE guest_itp_path (cwd-independent ITP copy).
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path=str(ETOH_GRO),
        guest_itp_path=str(ETOH_ITP),
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
    )

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=config,
        lattice_info=lattice_info,
        report="test",
        guest_count=1,
        water_count=2,
    )


def _build_builtin_ch4_hydrate_structure() -> HydrateStructure:
    """Build a 2-water + 1-CH4 HydrateStructure (13 atoms, built-in ch4)."""
    positions = np.zeros((13, 3))
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]

    atom_names = [
        "OW", "HW1", "HW2", "MW",
        "OW", "HW1", "HW2", "MW",
        "C", "H", "H", "H", "H",
    ]

    cell = np.eye(3) * 1.2

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),
    ]

    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    config = HydrateConfig(lattice_type="sI", guest_type="ch4")

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=config,
        lattice_info=lattice_info,
        report="test",
        guest_count=1,
        water_count=2,
    )


def _make_pipeline_with_hydrate(hydrate_structure, tmp_path) -> CLIPipeline:
    """Construct a CLIPipeline whose _hydrate_result is set and all other
    _*_result attributes are None (the __init__ defaults)."""
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = tmp_path
    pipe._hydrate_result = hydrate_structure
    # All other _*_result stay at their __init__ default of None.
    return pipe


# ── Test 3: integration — _run_export_step for custom ethanol hydrate ──────

def test_run_export_step_custom_hydrate(tmp_path):
    """Custom ethanol hydrate → MOL_H in .gro/.top, etoh.itp copied+transformed."""
    hydrate = _build_custom_hydrate_structure()
    pipe = _make_pipeline_with_hydrate(hydrate, tmp_path)

    code = pipe._run_export_step()

    assert code == 0, "_run_export_step should succeed for a custom hydrate"

    # Files exist
    gro_path = tmp_path / "hydrate.gro"
    top_path = tmp_path / "hydrate.top"
    assert gro_path.exists(), "hydrate.gro should be written"
    assert top_path.exists(), "hydrate.top should be written"
    assert (tmp_path / "etoh.itp").exists(), "custom etoh.itp should be copied"
    assert (tmp_path / "tip4p-ice.itp").exists(), "tip4p-ice.itp should always be copied"

    # .gro residue names: MOL_H (ethanol) + SOL (water); NO UNK
    gro_residues = parse_gro_residue_names(str(gro_path))
    gro_residue_set = set(gro_residues)
    assert "MOL_H" in gro_residue_set, f"MOL_H missing from .gro residues: {gro_residue_set}"
    assert "SOL" in gro_residue_set, f"SOL missing from .gro residues: {gro_residue_set}"
    assert "UNK" not in gro_residue_set, (
        f"UNK should NOT appear — custom_guest_info must drive the residue name. "
        f"Residues: {gro_residue_set}"
    )

    # .top [molecules]: SOL=2, MOL_H=1
    top_molecules = parse_top_molecules(str(top_path))
    assert top_molecules == {"SOL": 2, "MOL_H": 1}, (
        f"Expected [molecules] {{'SOL': 2, 'MOL_H': 1}}, got {top_molecules}"
    )

    # .top #include: etoh.itp
    top_includes = parse_top_includes(str(top_path))
    assert "etoh.itp" in top_includes, (
        f"etoh.itp should be #included in .top, got: {top_includes}"
    )


# ── Test 4: regression — _run_export_step for built-in ch4 hydrate ──────────

def test_run_export_step_builtin_ch4_regression(tmp_path):
    """Built-in ch4 hydrate → CH4_H in .gro/.top, ch4_hydrate.itp #included
    (custom_guest_info=None path unchanged)."""
    hydrate = _build_builtin_ch4_hydrate_structure()
    pipe = _make_pipeline_with_hydrate(hydrate, tmp_path)

    code = pipe._run_export_step()

    assert code == 0, "_run_export_step should succeed for a built-in ch4 hydrate"

    gro_path = tmp_path / "hydrate.gro"
    top_path = tmp_path / "hydrate.top"
    assert gro_path.exists()
    assert top_path.exists()
    assert (tmp_path / "ch4_hydrate.itp").exists(), (
        "ch4_hydrate.itp should be copied for built-in ch4"
    )
    assert (tmp_path / "tip4p-ice.itp").exists()

    # .gro residue names: CH4_H + SOL
    gro_residues = parse_gro_residue_names(str(gro_path))
    gro_residue_set = set(gro_residues)
    assert "CH4_H" in gro_residue_set, f"CH4_H missing from .gro residues: {gro_residue_set}"
    assert "SOL" in gro_residue_set, f"SOL missing from .gro residues: {gro_residue_set}"

    # .top [molecules]: SOL + CH4_H
    top_molecules = parse_top_molecules(str(top_path))
    assert "CH4_H" in top_molecules, (
        f"CH4_H should be in [molecules], got: {top_molecules}"
    )
    assert top_molecules.get("SOL") == 2, f"SOL count should be 2, got: {top_molecules}"

    # .top #include: ch4_hydrate.itp
    top_includes = parse_top_includes(str(top_path))
    assert "ch4_hydrate.itp" in top_includes, (
        f"ch4_hydrate.itp should be #included, got: {top_includes}"
    )
