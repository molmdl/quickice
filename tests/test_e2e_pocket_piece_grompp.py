"""Pocket + piece interface export grompp validation — closes G4 (48.3-12).

G4 (RESEARCH-INVENTORY §4): pocket and piece mode exports had ZERO grompp
coverage anywhere before this file — all pre-existing e2e grompp assertions
were slab-shaped (test_cli_pipeline.py's grompp class had exactly 2 slab
tests; test_e2e_gmx_param_validation.py uses _make_slab_interface only).
Pocket/piece are first-class interface modes users select; an export that
only works slab-shaped is not "a real pass of the workflow". Geometry-specific
breakage (cell/PBC shape, molecule ordering in the pocket cavity) would
previously reach grompp only at user runtime.

This module builds pocket + piece interfaces from a REAL hydrate candidate
(sI + built-in ch4 guest — the simplest valid case) via the shared interface
builder (``generate_interface``, mirroring ``e2e_export_helpers._make_pocket_interface``)
and validates the export through BOTH pipeline surfaces:

  - GUI leg: ``InterfaceGROMACSExporter.export_interface_gromacs`` with
    QFileDialog/QMessageBox patched (Pattern B — patch
    ``quickice.gui.export.QFileDialog.getSaveFileName``, the using module's
    namespace).
  - CLI leg: Pattern 4 — ``CLIPipeline`` with ``_interface_result`` set +
    ``_run_export_step``'s interface branch into a per-test tmp_path subdir.

Each leg asserts: files written + ``assert_itp_completeness`` +
``assert_gro_top_consistent`` + ``gmx grompp`` rc == 0 (``@gmx_skipif``
convention: file-consistency always runs; grompp only when gmx is on PATH).

Box-size safety (47-05 empirical finding + 45-RESEARCH Pitfall 1 + STATE
[41-10] lesson: a box EXACTLY at 2x cutoff is rejected): the grompp PBC rule
requires the shortest box vector > 2 x rcoulomb (rcoulomb = rvdw = 1.0 nm in
tests/em.mdp). The module fixture computes and asserts this for BOTH modes as
a pre-test sanity check:

  - pocket: box 3x3x5 nm is rounded UP to ice-cell periodicity multiples by
    ``assemble_pocket`` (sI cell ~1.2 nm -> 3x3x5 becomes ~3.60x3.60x6.00 nm),
    so the shortest vector is ~3.60 nm > 2.0 nm.
  - piece: box is used as configured (3x3x5 nm, must exceed the ~1.2 nm ice
    piece), shortest vector 3.0 nm > 2.0 nm.

Fresh interface per export leg: the fixture returns FACTORIES (the candidate
is module-scoped to amortize the ~3-5s GenIce2 call; assembly from an existing
candidate is cheap and deterministic with seed=42). All inserters return NEW
structures and the ion/solute inserters mutate ``molecule_index`` — this
module runs no inserters, but the fresh-per-leg rule is kept so any future
inserter chaining on these modes cannot cross-contaminate legs.

Species asserts: ``SOL`` + ``CH4_H`` (built-in ch4 hydrate guest, _H suffix
via the built-in staging path) present in .top [molecules] AND .gro residues
for both modes; NO ``GUE``/``UNK`` placeholders.

Runtime: 2 modes x 2 legs x ~1-2s grompp ≈ under 10s total.
"""

import shutil
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.interface_builder import (  # noqa: E402
    generate_interface,
)
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import InterfaceGROMACSExporter  # noqa: E402
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from tests.e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_includes,
    parse_top_molecules,
    run_gmx_grompp,
)


# ── Shared constants ─────────────────────────────────────────────────────────

MODES = ("pocket", "piece")

# ch4 hydrate guest: 5 atoms per molecule (C + 4 H). Test-side constant
# matching the types.py docstring convention ("CH4: 5 atoms"); ch4 is a
# built-in guest, so no module constant exists for it.
CH4_ATOMS_PER_MOLECULE = 5

# Grompp PBC rule (tests/em.mdp): rcoulomb = rvdw = 1.0 nm, so grompp requires
# shortest box vector > 2 * 1.0 nm. A box EXACTLY at 2x cutoff is rejected
# (STATE [41-10] lesson, 45-RESEARCH Pitfall 1).
GROMPP_PBC_MIN_SHORTEST_VECTOR_NM = 2.0

# Box config shared by both modes (sI cell ~1.2 nm -> pocket rounds up to
# ~3.60x3.60x6.00; piece uses 3x3x5 exactly). Both satisfy the PBC rule.
_BOX = {"box_x": 3.0, "box_y": 3.0, "box_z": 5.0}


# ── Module-scoped fixture: candidate ONCE + fresh interface factories ────────


@pytest.fixture(scope="module")
def pocket_piece_fixtures():
    """Module-scoped fixture: sI+ch4 hydrate candidate built ONCE (amortizes
    the ~3-5s GenIce2 call across all parametrized cases per AGENTS.md testing
    guidance) + per-mode interface FACTORIES for fresh interfaces per export
    leg, + the hydrate (carrying ``.config``) for the CLI leg's
    ``_hydrate_result``.

    Pre-test box-size safety: for each mode the fixture builds one interface
    and asserts the grompp PBC rule (shortest box vector > 2 x 1.0 nm rcoulomb)
    with a rule-naming message, BEFORE any test body runs. Pocket boxes are
    rounded UP to ice-cell periodicity multiples by ``assemble_pocket``; piece
    boxes are used as configured — both must clear the rule or every grompp in
    this module would fail for geometry reasons unrelated to the export code
    under test.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()

    def _make_pocket():
        return generate_interface(
            candidate,
            InterfaceConfig(
                mode="pocket",
                seed=42,
                pocket_diameter=2.0,
                pocket_shape="sphere",
                **_BOX,
            ),
        )

    def _make_piece():
        return generate_interface(
            candidate,
            InterfaceConfig(mode="piece", seed=42, **_BOX),
        )

    factories = {"pocket": _make_pocket, "piece": _make_piece}

    # Pre-test box-size sanity: grompp PBC rule (47-05 + 45-RESEARCH Pitfall 1
    # + STATE [41-10]: box exactly at 2x cutoff is REJECTED by grompp).
    for mode in MODES:
        iface = factories[mode]()
        box = np.asarray(iface.cell, dtype=float)
        shortest = float(np.min(np.diag(box)))
        assert shortest > GROMPP_PBC_MIN_SHORTEST_VECTOR_NM, (
            f"{mode} box shortest vector {shortest:.3f} nm violates the grompp "
            f"PBC rule: shortest box vector must be > 2 x rcoulomb "
            f"(2 x 1.0 nm in tests/em.mdp); boxes exactly at 2x cutoff are "
            f"rejected by grompp (47-05 / 45-RESEARCH Pitfall 1 / STATE [41-10]). "
            f"Box diag: {np.diag(box)}"
        )
        # Built-in ch4 guests must survive the pocket/piece assembly (44.1-06/07).
        assert iface.guest_nmolecules > 0, (
            f"{mode} interface should preserve built-in ch4 cage guests "
            f"(guest_nmolecules=0)"
        )
        assert iface.guest_atom_count == CH4_ATOMS_PER_MOLECULE * iface.guest_nmolecules, (
            f"{mode} guest_atom_count={iface.guest_atom_count} != "
            f"{CH4_ATOMS_PER_MOLECULE} * guest_nmolecules={iface.guest_nmolecules}"
        )

    return {"config": config, "hydrate": hydrate, "factories": factories}


# ── Shared export assertion helper ───────────────────────────────────────────


def _assert_gro_box_pbc_rule(gro_path, mode):
    """Assert the exported .gro box line itself satisfies the grompp PBC rule.

    The fixture asserts the structure cell; this asserts what grompp ACTUALLY
    reads (the .gro box vectors written by the writer). GRO box line is either
    3 values (v1x v2y v3z, orthogonal) or 9 values (full matrix); the shortest
    box vector is the min of the diagonal entries.
    """
    with open(gro_path) as f:
        lines = f.read().splitlines()
    box_values = [float(v) for v in lines[-1].split()]
    if len(box_values) >= 9:
        diag = [box_values[0], box_values[4], box_values[8]]
    else:
        diag = box_values[:3]
    shortest = min(diag)
    assert shortest > GROMPP_PBC_MIN_SHORTEST_VECTOR_NM, (
        f"[{mode}] exported .gro box shortest vector {shortest:.3f} nm "
        f"violates the grompp PBC rule (> 2 x rcoulomb = 2 x 1.0 nm in "
        f"tests/em.mdp); box line: {lines[-1]!r}"
    )


def _assert_pocket_piece_export(ws, gro_path, top_path, mode):
    """Shared assertion chain for one pocket/piece export leg.

    Asserts: files written (gro/top/tip4p-ice.itp/ch4_hydrate.itp), ITP
    completeness, gro/top consistency, exported .gro box PBC rule, grompp
    rc == 0, and species (SOL + CH4_H in .top [molecules] AND .gro residues;
    NO GUE/UNK placeholders; ch4_hydrate.itp #included, NOT guest.itp).
    """
    # Files written.
    assert gro_path.exists(), f"[{mode}] .gro not written: {gro_path}"
    assert top_path.exists(), f"[{mode}] .top not written: {top_path}"
    assert (ws / "tip4p-ice.itp").exists(), (
        f"[{mode}] water ITP (tip4p-ice.itp) not staged"
    )
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"[{mode}] built-in ch4 guest ITP (ch4_hydrate.itp) not staged"
    )
    staged_itp = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_itp, (
        f"[{mode}] staged ch4_hydrate.itp missing CH4_H moleculetype"
    )

    # File-consistency assertions (always run, even without gmx).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))
    _assert_gro_box_pbc_rule(gro_path, mode)

    # gmx grompp -> rc == 0 (topology self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file=gro_path.name, top_file=top_path.name
    )
    assert exit_code == 0, (
        f"[{mode}] gmx grompp failed ({mode} interface export):\n{stderr[-500:]}"
    )

    # Species: SOL + CH4_H in .top [molecules]; NO GUE/UNK placeholders.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, f"[{mode}] expected SOL in [molecules], got {mols}"
    assert "CH4_H" in mols, (
        f"[{mode}] expected built-in CH4_H in [molecules], got {mols}"
    )
    assert "GUE" not in mols, f"[{mode}] GUE placeholder in [molecules]: {mols}"
    assert "UNK" not in mols, f"[{mode}] UNK placeholder in [molecules]: {mols}"

    # Species: SOL + CH4_H in .gro residues; NO GUE/UNK placeholders.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res, f"[{mode}] expected SOL in .gro residues, got {gro_res}"
    assert "CH4_H" in gro_res, (
        f"[{mode}] expected built-in CH4_H in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, f"[{mode}] GUE placeholder in .gro residues: {gro_res}"
    assert "UNK" not in gro_res, f"[{mode}] UNK placeholder in .gro residues: {gro_res}"

    # .top #includes the built-in guest ITP (NOT the non-existent guest.itp).
    includes = parse_top_includes(str(top_path))
    assert "tip4p-ice.itp" in includes, f"[{mode}] .top must #include tip4p-ice.itp: {includes}"
    assert "ch4_hydrate.itp" in includes, (
        f"[{mode}] .top must #include ch4_hydrate.itp for ch4 guests: {includes}"
    )
    assert "guest.itp" not in includes, (
        f"[{mode}] .top must NOT #include the non-existent guest.itp: {includes}"
    )


# ── Task 1: fixture smoke (pocket + piece build; box rule; guests) ───────────


@gmx_skipif
@pytest.mark.parametrize("mode", MODES)
def test_pocket_piece_fixture_smoke(pocket_piece_fixtures, mode):
    """Fixture smoke: {mode} interface builds from a real hydrate candidate.

    Verifies (per mode): the interface builder's {mode} assembly succeeds from
    the shared sI+ch4 candidate, the mode attribute round-trips, the grompp
    PBC box rule holds (asserted in the fixture pre-test AND re-asserted here
    on the fresh instance), and built-in ch4 guests survive assembly with a
    consistent 5-atoms-per-molecule count.
    """
    iface = pocket_piece_fixtures["factories"][mode]()
    assert iface.mode == mode, f"expected mode={mode}, got {iface.mode!r}"
    box = np.asarray(iface.cell, dtype=float)
    shortest = float(np.min(np.diag(box)))
    assert shortest > GROMPP_PBC_MIN_SHORTEST_VECTOR_NM, (
        f"{mode} box shortest vector {shortest:.3f} nm violates the grompp "
        f"PBC rule: shortest box vector must be > 2 x rcoulomb "
        f"(2 x 1.0 nm in tests/em.mdp); boxes exactly at 2x cutoff are "
        f"rejected by grompp (47-05 / 45-RESEARCH Pitfall 1 / STATE [41-10]). "
        f"Box diag: {np.diag(box)}"
    )
    assert iface.guest_nmolecules > 0, (
        f"{mode} interface should preserve built-in ch4 cage guests"
    )
    assert iface.guest_atom_count == CH4_ATOMS_PER_MOLECULE * iface.guest_nmolecules, (
        f"{mode} guest_atom_count={iface.guest_atom_count} != "
        f"{CH4_ATOMS_PER_MOLECULE} * guest_nmolecules={iface.guest_nmolecules}"
    )
    assert iface.ice_nmolecules > 0 and iface.water_nmolecules > 0, (
        f"{mode} interface should have both ice and water phases"
    )
