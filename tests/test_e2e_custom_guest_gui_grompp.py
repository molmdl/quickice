"""End-to-end GROMACS grompp validation for the GUI custom-guest hydrate path.

Proves EXPORT-06 (GUI half) for plan 41-10: ``gmx grompp`` exits 0 on a
custom ethanol guest hydrate exported via the GUI multi-molecule writers
(``write_multi_molecule_gro_file`` + ``write_multi_molecule_top_file`` with
``custom_guest_info``), with the custom ITP staged via the transformed-staging
helper ``_stage_custom_guest_itp`` (plan 41-09).

The writers (fixed by plans 41-02 / 41-03) emit:
  - ``.gro`` with ``MOL_H`` residues for the 9-atom ethanol guest
  - ``.top`` with ``[molecules] MOL_H`` + ``[atomtypes]`` oh/ho merged+deduped
    + ``#include "etoh.itp"``

``_stage_custom_guest_itp`` overwrites the under-transformed etoh.itp
(moleculetype ``etoh``) with the fully-transformed copy (moleculetype
``MOL_H``, ``[atoms]`` resname ``MOL_H``), making the staged ITP internally
consistent with the ``.top [molecules] MOL_H`` entry — the prerequisite for
``gmx grompp`` to succeed.

The CLI half of EXPORT-06 is plan 41-11. This test follows the established
repo convention (call writers directly + ``_stage_itp_files`` +
``run_gmx_grompp``) used by ``tests/test_e2e_gmx_validation.py``.
``gmx`` IS on PATH so this test runs (not skipped).
"""

import sys
import shutil
from pathlib import Path

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.types import MoleculeIndex  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _stage_itp_files,
    _stage_custom_guest_itp,
    run_gmx_grompp,
    MDP_PATH,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ══════════════════════════════════════════════════════════════════════════════
# GUI custom-guest hydrate grompp (EXPORT-06, GUI half)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_gui_grompp_passes(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI multi-molecule writers (write_multi_molecule_gro_file +
    write_multi_molecule_top_file with custom_guest_info).

    Builds a tiny synthetic 2-water + 1-custom-ethanol-guest system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 9 ethanol atoms = 17
    atoms.  Stages tip4p-ice.itp + the transformed etoh.itp (moleculetype
    MOL_H), then runs gmx grompp.
    """
    # Synthetic 2-water + 1-ethanol-guest system (17 atoms total).
    positions = np.zeros((17, 3))
    positions[:, 0] = np.linspace(0.01, 0.17, 17)
    atom_names = [
        "OW", "HW1", "HW2", "MW",  # water 1
        "OW", "HW1", "HW2", "MW",  # water 2
        "H", "C", "H", "H", "C", "H", "H", "O", "H",  # ethanol (9 atoms)
    ]
    # Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp); 3.0 nm gives a
    # comfortable margin and matches the repo's interface-test box convention.
    cell = np.eye(3) * 3.0
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
    ]
    cgi = {
        "mol_type": "etoh_e2e",
        "residue_name": "MOL_H",
        "itp_path": Path("quickice/data/custom/etoh.itp"),
    }
    itp_files = {"etoh_e2e": "etoh.itp"}

    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(gro),
        "custom guest hydrate",
        atom_names=atom_names,
        custom_guest_info=cgi,
    )
    write_multi_molecule_top_file(
        molecule_index,
        str(top),
        "custom guest hydrate",
        itp_files=itp_files,
        custom_guest_info=cgi,
    )

    # Stage MDP + ITPs (repo convention: writers don't copy ITPs; staging does)
    shutil.copy(MDP_PATH, ws / "em.mdp")
    _stage_itp_files(str(top), ws)  # tip4p-ice.itp + etoh.itp (etoh under-transformed)
    _stage_custom_guest_itp(  # overwrite etoh.itp -> moleculetype MOL_H
        ws, Path("quickice/data/custom/etoh.itp"), "MOL"
    )

    # All #include'd ITPs present in the workspace.
    assert_itp_completeness(str(top), ws)
    # GRO residues <-> TOP [molecules] cross-check.
    assert_gro_top_consistent(str(gro), str(top))

    # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert exit_code == 0, f"gmx grompp failed (GUI custom guest):\n{stderr}"

    # .top [molecules] lists SOL + MOL_H.
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )

    # .gro residues contain SOL + MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )
