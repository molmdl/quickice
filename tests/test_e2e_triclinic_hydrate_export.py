"""E2E triclinic filled-ice hydrate-only export @ 4x4x4 (CLI + GUI) + grompp.

Plan 45-09 (wave 3). Proves c0te + c1te triclinic filled-ice lattices at
4x4x4 supercell produce grompp-valid hydrate-only export output through
BOTH the CLI ``_run_export_step`` hydrate branch (wraps HydrateStructure in
InterfaceStructure + ``write_interface_*``) AND the GUI
``HydrateGROMACSExporter.export_hydrate`` (uses ``write_multi_molecule_*``).

Purpose: c0te/c1te are BLOCKED at the interface tab
(``TRICLINIC_HYDRATE_PHASES`` in interface_builder.py), so only
Hydrate -> Export is possible. The 1x1x1 unit cell FAILS grompp
("cut-off length is longer than half the shortest box vector" — shortest
vector ~0.5349-0.6017 nm < 2*rcoulomb = 2.0 nm). The 4x4x4 supercell
expands the shortest vector to ~2.14 nm (c0te) / ~2.41 nm (c1te), both
> 2.0 nm so grompp succeeds (Pitfall 1 — empirically verified for c0te;
c1te inferred from 4*0.6017=2.407 > 2.0).

Pitfall 6 (two export paths): CLI and GUI use DIFFERENT writers.
- CLI: ``_run_export_step`` hydrate branch (pipeline.py:885-928) wraps
  HydrateStructure in an InterfaceStructure-compatible wrapper +
  ``write_interface_gro_file`` / ``write_interface_top_file`` +
  ``copy_itp_files_for_structure``.
- GUI: ``HydrateGROMACSExporter.export_hydrate`` (hydrate_export.py) uses
  ``write_multi_molecule_gro_file`` / ``write_multi_molecule_top_file`` +
  ``MoleculetypeRegistry``.

This test exercises BOTH paths separately (4 cases: c0te/c1te x CLI/GUI).

Module-scoped fixture amortizes the expensive GenIce2 4x4x4 generation
(~5-15s per lattice for c0te/c1te) across the parametrized cases per
AGENTS.md testing guidance.
``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter test (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under
offscreen -> exporter returns False without writing, so inline patching of
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
from quickice.structure_generation.types import HydrateConfig  # noqa: E402
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ── Module-scoped fixture: build c0te + c1te @ 4x4x4 ONCE ──────────────────────


@pytest.fixture(scope="module")
def triclinic_hydrates():
    """Module-scoped: generate c0te + c1te hydrate structures at 4x4x4
    supercell ONCE, amortizing the expensive GenIce2 calls (~5-15s each)
    across all parametrized CLI + GUI export cases.

    CRITICAL (Pitfall 1): MUST use 4x4x4 supercell — NOT 1x1x1. The 1x1x1
    unit cell of c0te (shortest vector ~0.5349 nm) and c1te (shortest
    vector ~0.6017 nm) is SMALLER than 2*rcoulomb = 2.0 nm, so grompp
    fatal-errors with "cut-off length is longer than half the shortest
    box vector". 4x4x4 expands the shortest vector to ~2.14 nm (c0te) and
    ~2.41 nm (c1te), both > 2.0 nm so grompp succeeds.

    Returns ``dict {"c0te": SimpleNamespace(hydrate=..., config=...),
    "c1te": SimpleNamespace(hydrate=..., config=...)}`` where each
    namespace carries the ``HydrateStructure`` (with ``.config``) + the
    ``HydrateConfig`` used to generate it.
    """
    chains = {}
    for lattice_type in ("c0te", "c1te"):
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",
            supercell_x=4,
            supercell_y=4,
            supercell_z=4,
        )
        hydrate = gen.generate(config)
        # Sanity: filled-ice lattices have cage guests (not water-only like
        # sTprime/17) AND water molecules (the ice framework).
        assert hydrate.guest_count > 0, (
            f"{lattice_type} 4x4x4 should have cage guests (filled ice), "
            f"got guest_count={hydrate.guest_count}"
        )
        assert hydrate.water_count > 0, (
            f"{lattice_type} 4x4x4 should have water molecules, "
            f"got water_count={hydrate.water_count}"
        )
        chains[lattice_type] = SimpleNamespace(hydrate=hydrate, config=config)
    yield chains


# ── Shared assertion helper ──────────────────────────────────────────────────


def _assert_hydrate_export(ws, gro_name, top_name):
    """Common assertions for a triclinic hydrate-only export: files written,
    CH4_H residue + ch4_hydrate.itp staged, file consistency, grompp rc=0.

    Built-in ch4 cage guest -> residue name ``CH4_H`` + bundled
    ``ch4_hydrate.itp`` (pre-transformed). Asserts neither ``GUE`` nor
    ``MOL_H`` leak (the built-in path must remain pure built-in).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # Built-in ch4 hydrate guest ITP staged (ch4_hydrate.itp).
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"built-in guest ITP ch4_hydrate.itp not staged in {ws}"
    )
    staged_itp = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_itp, (
        f"staged ch4_hydrate.itp missing moleculetype CH4_H"
    )

    # .top [molecules] references CH4_H (built-in residue, not GUE/MOL_H).
    mols = parse_top_molecules(str(top_path))
    assert "CH4_H" in mols, (
        f"built-in residue CH4_H not in [molecules]: {mols}"
    )
    assert "SOL" in mols, f"SOL not in [molecules]: {mols}"

    # .gro residues contain CH4_H + SOL.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res, (
        f"built-in residue CH4_H not in .gro residues: {gro_res}"
    )
    assert "SOL" in gro_res, f"SOL not in .gro residues: {gro_res}"

    # File consistency (always runs — catches ITP-missing + GRO/TOP mismatch).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH — file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(ws, gro_file=gro_name, top_file=top_name)
        assert rc == 0, (
            f"gmx grompp failed (triclinic hydrate, {gro_name}):\n{stderr}"
        )


# ── CLI hydrate export test ───────────────────────────────────────────────────


@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
@gmx_skipif
def test_triclinic_hydrate_cli_export_grompp(
    tmp_path, triclinic_hydrates, lattice_type
):
    """CLI ``_run_export_step`` hydrate branch produces grompp-valid output
    for c0te/c1te @ 4x4x4 supercell.

    The CLI hydrate branch (pipeline.py:885-928) wraps the HydrateStructure
    in an InterfaceStructure-compatible wrapper + ``write_interface_gro_file``
    / ``write_interface_top_file`` + ``copy_itp_files_for_structure``. This is
    DIFFERENT from the GUI path (Pitfall 6 — tested separately below).

    Only ``_hydrate_result`` is set (NOT ``_interface_result``) so the
    ``_run_export_step`` priority selection (ion > solute > custom >
    interface > hydrate > ice) picks the hydrate branch. The hydrate branch
    writes ``hydrate.gro`` / ``hydrate.top`` to ``_output_dir``.

    The hydrate carries ``.config`` (the ``HydrateConfig`` with
    ``guest_type="ch4"``) so ``copy_itp_files_for_structure`` resolves the
    built-in ch4 guest -> ``ch4_hydrate.itp`` (pre-transformed).
    """
    chain = triclinic_hydrates[lattice_type]
    ws = tmp_path / "cli"
    ws.mkdir()

    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = chain.hydrate  # carries .config for ITP staging
    # Only _hydrate_result set -> export priority picks the hydrate branch.

    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the hydrate branch "
        f"({lattice_type} 4x4x4)"
    )

    # The hydrate branch writes hydrate.gro / hydrate.top to _output_dir.
    _assert_hydrate_export(ws, "hydrate.gro", "hydrate.top")


# ── GUI hydrate export test ───────────────────────────────────────────────────


@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
@gmx_skipif
def test_triclinic_hydrate_gui_export_grompp(
    tmp_path, triclinic_hydrates, lattice_type
):
    """GUI ``HydrateGROMACSExporter.export_hydrate`` produces grompp-valid
    output for c0te/c1te @ 4x4x4 supercell.

    The GUI path (hydrate_export.py) uses ``write_multi_molecule_gro_file`` /
    ``write_multi_molecule_top_file`` + ``MoleculetypeRegistry`` — DIFFERENT
    writers from the CLI hydrate branch (Pitfall 6).

    ``QFileDialog.getSaveFileName`` is mocked (REQUIRED — under
    ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> exporter returns
    False without writing). ``QMessageBox`` is mocked to suppress error
    dialogs. The exporter is lazy-imported inside the test (NOT at module
    top level — keeps PySide6 out of the CLI test's import path per
    AGENTS.md: PySide6/VTK/GenIce2 are imported inside function bodies).
    """
    chain = triclinic_hydrates[lattice_type]
    ws = tmp_path / "gui"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"

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

    _assert_hydrate_export(ws, "output.gro", "output.top")
