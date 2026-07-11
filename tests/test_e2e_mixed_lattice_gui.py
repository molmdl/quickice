"""E2E mixed built-in cage occupancy (CH4 + THF) with sII/16 through the GUI
HydrateGROMACSExporter.export_hydrate + gmx grompp.

Plan 45-13 (wave 6). Proves that mixed BUILT-IN occupancy (CH4 in small cages
+ THF in large cages) with the two-cage-type lattices sII and 16 (both have
``cage_type_map = {"small": "12", "large": "16"}``) produces grompp-valid
output through the GUI ``HydrateGROMACSExporter.export_hydrate`` — which uses
``write_multi_molecule_gro_file`` / ``write_multi_molecule_top_file`` (the
multi-molecule writers that handle mixed guests via ``molecule_index`` +
``MoleculetypeRegistry`` registering BOTH ``hydrate_CH4`` and ``hydrate_THF``).

Purpose: extends mixed occupancy testing beyond sI (the only lattice tested
in 42-05/42-07). sII and 16 both have small + large cage types, so mixed
built-in (CH4 small + THF large) is well-defined for them.

Pitfall 2 (single-guest-stream): the CLI ``write_interface_*`` path picks ONE
guest type for the whole guest region via ``detect_guest_type_from_atoms`` —
it CANNOT emit a mixed ``[molecules]`` block with both ``CH4_H`` and
``THF_H``. This test therefore exercises the GUI multi-molecule writers (NOT
the CLI interface writers) — the same writers the GUI
``HydrateGROMACSExporter.export_hydrate`` uses. The CLI mixed built-in
limitation is documented in ``tests/test_cli/test_mixed_cage_cli.py`` and is
out of scope here.

Pitfall 1 (box-size): sII/16 at 1x1x1 have a shortest box vector of
~1.7121 nm, which is SMALLER than 2*rcoulomb = 2.0 nm — grompp fatal-errors
with "cut-off length is longer than half the shortest box vector". The
2x2x2 supercell expands the shortest vector to ~3.4242 nm (> 2.0 nm) so
grompp succeeds. Generation is fast (~0.1s). This mirrors the 4x4x4 fix
used for the triclinic filled-ice lattices in test_e2e_triclinic_hydrate_export
(the same Pitfall 1, applied to sII/16 hydrate-only export).

Pitfall 6 (two export paths): the GUI hydrate exporter uses
``write_multi_molecule_*`` (this test); the CLI hydrate branch wraps in an
``InterfaceStructure`` + ``write_interface_*`` (different path, tested
elsewhere). Do NOT conflate the two.

Module-scoped fixture amortizes the GenIce2 calls (~0.1s each at 2x2x2)
across the parametrized cases per AGENTS.md testing guidance.
``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter (no display).
``QFileDialog.getSaveFileName`` returns ``("", "")`` under offscreen ->
exporter returns False without writing, so inline patching of
``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED.
``gmx`` is on PATH so grompp runs (``@gmx_skipif`` skips when absent).
"""

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
)
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: build sII + 16 mixed built-in (CH4 small + THF large)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def mixed_hydrates():
    """Module-scoped: generate sII + 16 mixed built-in hydrate structures
    (CH4 in small cages + THF in large cages) ONCE, amortizing the GenIce2
    calls across both parametrized GUI export cases.

    Both lattices have ``cage_type_map = {"small": "12", "large": "16"}`` —
    two distinct cage ids, so GenIce2's ``parse_guest`` "Cage type already
    specified" assert never fires when called once per cage key (Pattern 2
    in hydrate_generator._run_via_api). GenIce2 places CH4 in the 16 small
    cages + THF in the 8 large cages per unit cell.

    CRITICAL (Pitfall 1): uses 2x2x2 supercell — NOT 1x1x1. The 1x1x1 unit
    cell of sII/16 (shortest vector ~1.7121 nm) is SMALLER than 2*rcoulomb
    = 2.0 nm, so grompp fatal-errors with "cut-off length is longer than
    half the shortest box vector". 2x2x2 expands the shortest vector to
    ~3.4242 nm (> 2.0 nm) so grompp succeeds. Generation is fast (~0.1s).

    Returns ``dict {"sII": SimpleNamespace(hydrate=..., config=...),
    "16": SimpleNamespace(hydrate=..., config=...)}`` where each namespace
    carries the ``HydrateStructure`` + the ``HydrateConfig`` used to
    generate it (the GUI exporter needs both).
    """
    chains = {}
    for lattice_type in ("sII", "16"):
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",  # primary (legacy) — ch4 is built-in
            cage_guest_assignments={
                "small": CageGuestAssignment(
                    guest_type="ch4", occupancy=100.0
                ),
                "large": CageGuestAssignment(
                    guest_type="thf", occupancy=100.0
                ),
            },
            supercell_x=2,  # Pitfall 1: 1x1x1 box (1.71 nm) < 2.0 nm -> grompp
            supercell_y=2,  # fatal "cut-off longer than half shortest vector".
            supercell_z=2,  # 2x2x2 -> 3.42 nm > 2.0 nm (generation ~0.1s).
        )
        hydrate = gen.generate(config)
        # Sanity: mixed built-in should place BOTH guest types.
        assert hydrate.guest_count > 0, (
            f"{lattice_type} mixed built-in should have cage guests, "
            f"got guest_count={hydrate.guest_count}"
        )
        mol_types = {m.mol_type for m in hydrate.molecule_index}
        assert "ch4" in mol_types and "thf" in mol_types, (
            f"{lattice_type} mixed built-in should place BOTH ch4 + thf, "
            f"got mol_types={mol_types}"
        )
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, config=config
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized GUI hydrate export + grompp test (sII + 16)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lattice_type", ["sII", "16"])
@gmx_skipif
def test_mixed_builtin_lattice_gui_grompp(
    tmp_path, mixed_hydrates, lattice_type
):
    """gmx grompp exits 0 on a mixed built-in (CH4 small + THF large) hydrate
    for sII/16 exported via the GUI ``HydrateGROMACSExporter.export_hydrate``.

    The GUI path (hydrate_export.py) uses ``write_multi_molecule_gro_file`` /
    ``write_multi_molecule_top_file`` + ``MoleculetypeRegistry`` — the
    multi-molecule writers that handle mixed built-in via per-``mol_type``
    resolution (registering BOTH ``hydrate_CH4`` -> "CH4_H" AND
    ``hydrate_THF`` -> "THF_H"). This is the defining property of mixed
    built-in cage occupancy (Pitfall 2: the CLI ``write_interface_*`` path
    cannot do this — it picks ONE guest type for the whole guest region).

    ``QFileDialog.getSaveFileName`` is mocked (REQUIRED — under
    ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> exporter returns
    False without writing). ``QMessageBox`` is mocked to suppress error
    dialogs. The exporter is lazy-imported inside the test (NOT at module
    top level — keeps PySide6 out of the import path per AGENTS.md).

    The exporter derives the .top path from the .gro path via
    ``path.with_name(path.stem + '.top')`` — so mocking getSaveFileName to
    return ``output.gro`` produces ``output.top``. The exporter stages ALL
    ITPs itself (tip4p-ice.itp + ch4_hydrate.itp + thf_hydrate.itp via
    transform_guest_itp, which is idempotent on the pre-transformed built-in
    ITPs), so this test does NOT call ``_stage_itp_files`` (which would
    re-stage from quickice/data/ and could conflict). Only the MDP is copied
    for grompp (the exporter does not copy an MDP).
    """
    chain = mixed_hydrates[lattice_type]
    ws = tmp_path / lattice_type
    ws.mkdir()
    gro_path = ws / "output.gro"
    # The exporter derives: top_path = path.with_name(path.stem + '.top')
    # -> "output.top" when gro is "output.gro".

    # Lazy import: keeps PySide6 out of the module-top import path (AGENTS.md).
    from quickice.gui.hydrate_export import HydrateGROMACSExporter

    with patch(
        "quickice.gui.hydrate_export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.hydrate_export.QMessageBox"):
        exporter = HydrateGROMACSExporter(parent_widget=None)
        ok = exporter.export_hydrate(chain.hydrate, chain.config)
        assert ok is True, (
            "export_hydrate returned False — QFileDialog mock may not have "
            "been picked up, or staging raised"
        )

    top_path = ws / "output.top"

    # Files written by the exporter.
    assert gro_path.exists(), f"output.gro not written in {ws}"
    assert top_path.exists(), f"output.top not written in {ws}"

    # BOTH built-in guest ITPs staged by the exporter (mixed built-in
    # signature: both ch4_hydrate.itp AND thf_hydrate.itp present).
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"built-in guest ITP ch4_hydrate.itp not staged in {ws}"
    )
    assert (ws / "thf_hydrate.itp").exists(), (
        f"built-in guest ITP thf_hydrate.itp not staged in {ws}"
    )
    # The tip4p-ice.itp water ITP is also staged by the exporter.
    assert (ws / "tip4p-ice.itp").exists(), (
        f"water ITP tip4p-ice.itp not staged in {ws}"
    )

    # .top [molecules] lists BOTH CH4_H + THF_H (the mixed-occupancy
    # signature — proves the multi-molecule writers emit BOTH guest entries).
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, f"SOL not in [molecules]: {mols}"
    assert "CH4_H" in mols, (
        f"CH4_H not in [molecules] (mixed built-in small-cage guest): {mols}"
    )
    assert "THF_H" in mols, (
        f"THF_H not in [molecules] (mixed built-in large-cage guest): {mols}"
    )

    # .gro residues contain BOTH CH4_H + THF_H (+ SOL).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert {"SOL", "CH4_H", "THF_H"}.issubset(gro_res), (
        f"expected SOL + CH4_H + THF_H in .gro residues, got {gro_res}"
    )

    # File consistency (always runs — catches ITP-missing + GRO/TOP mismatch).
    # The exporter already staged all #include'd ITPs, so completeness passes.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH — file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(
            ws, gro_file="output.gro", top_file="output.top"
        )
        assert rc == 0, (
            f"gmx grompp failed (mixed built-in {lattice_type} GUI):\n{stderr}"
        )
