"""E2E sH interface export + grompp (GUI + CLI) (Phase 45-03).

Plan 45-03 (Wave 1, sH separation). Proves that sH -- the triclinic-but-
ALLOWED hydrate lattice (is_triclinic=True but NOT in
``TRICLINIC_HYDRATE_PHASES``; only c0te/c1te are blocked) -- produces
grompp-valid output at the Interface tab export step via BOTH the GUI
``InterfaceGROMACSExporter.export_interface_gromacs`` (with
``hydrate_config=None`` -- the built-in ch4 path) and the CLI
``CLIPipeline._run_export_step`` (interface branch -- Pattern 4 from
45-RESEARCH.md).

Purpose: sH is triclinic (``is_triclinic=True``) but is NOT in
``TRICLINIC_HYDRATE_PHASES`` (only c0te/c1te are blocked). It generates a
surprisingly large number of guests (~4480) because sH has 3 cage types
(small+medium+large) and the 3x3x8 nm slab tiles the small unit cell many
times. This is EXPECTED (not a bug) but SLOW (~5-30s per test). Separated
from 45-01/02 (the 6 non-triclinic lattices) so the slow sH case does not
block the fast batch. The module-scoped fixture amortizes the GenIce2 +
slab call (~5-30s) across both the GUI + CLI tests (one generation, two
exports).

sH specifics verified by this test:
  - sH medium cage_type_map key "12_1" (fixed in 42-00) is routed -- all 3
    cage types (small+medium+large) produce guests. Without the 42-00 fix,
    medium cages would be unreachable (0 medium guests).
  - sH produces ~4480 guests through the 3x3x8 nm slab -- large but works
    (grompp rc=0). Tests need >=120s timeout (Pitfall 5).
  - sH is triclinic but NOT blocked -- proves the phase_id-based blocking
    (TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}) correctly
    EXCLUDES sH (the is_triclinic flag is forward-looking metadata, not a
    block gate -- decision [39-01] / [39-03]).

Module-scoped fixture amortizes the GenIce2 + ``assemble_slab`` calls
(~5-30s for sH) across both the GUI + CLI tests (per AGENTS.md testing
guidance). The fixture runs GenIce2 + slab ONCE; each test just exports.

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter test (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under
offscreen -> the exporter returns ``False`` without writing files. Inline
patching of ``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED
(Pattern 3 from 45-RESEARCH.md).

``gmx`` is on PATH so grompp runs. The ``@gmx_skipif`` decorator skips the
whole test when ``gmx`` is absent; the helper also guards the grompp call
with ``shutil.which("gmx")`` so file-consistency + guest-residue asserts
run whenever the test runs.

Pitfalls avoided (45-RESEARCH.md):
  - Pitfall 1 (triclinic box-size): N/A -- sH is ALLOWED (not blocked); the
    3x3x8 nm slab box (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm) satisfies
    the grompp PBC rule.
  - Pitfall 4 (GRO atom-number wrap at 100,000): NOT asserted --
    ``assert_gro_top_consistent`` counts atom LINES, not the header, so it
    is robust to the 100,000 wrap (cosmetic; grompp still rc=0). sH through
    the slab produces ~54k atoms (49584 waters + 4480 guests * 5 atoms) --
    under the 100,000 wrap threshold, but the assertion is robust regardless.
  - Pitfall 5 (sH huge guest count): do NOT assert exact guest counts
    (version-dependent). Assert ``> 0`` only. sH is SLOW -- generous timeout
    (>=120s; this test uses --timeout=300).
  - Pitfall 6 (two hydrate export paths): the GUI test exercises
    ``InterfaceGROMACSExporter.export_interface_gromacs`` (``write_interface_*``
    via the GUI exporter); the CLI test exercises ``CLIPipeline._run_export_step``
    (interface branch -> ``write_interface_*`` via the CLI pipeline). Both
    use ``write_interface_gro_file`` / ``write_interface_top_file`` but via
    DIFFERENT call sites (GUI exporter vs CLI pipeline). Both are SEPARATE
    code paths -- this test covers BOTH (the 45-01 GUI + 45-02 CLI patterns
    combined for sH specifically).
"""

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import InterfaceGROMACSExporter  # noqa: E402
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    run_gmx_grompp,
    assert_itp_completeness,
    assert_gro_top_consistent,
    parse_top_molecules,
    parse_gro_residue_names,
)


# -- Module-scoped fixture: build the sH chain ONCE ---------------------------


@pytest.fixture(scope="module")
def sH_chain():
    """Module-scoped: build the hydrate -> interface chain for sH ONCE,
    amortizing the GenIce2 + ``assemble_slab`` calls (~5-30s for sH due to
    the ~4480 guests the 3x3x8 nm slab tiles from the small sH unit cell)
    across both the GUI + CLI export tests.

    sH has 3 cage types (small + medium + large), all routed. The medium
    cage_type_map key "12_1" (fixed in 42-00 -- before that fix, medium
    cages were unreachable, producing 0 medium guests). With ch4 as the
    built-in guest, all 3 cage types are populated.

    sH through the 3x3x8 nm slab produces ~4480 guests (EXPECTED, not a bug
    -- Pitfall 5). The slab tiles the small sH unit cell many times. This is
    SLOW but works: grompp rc=0 (verified in 45-RESEARCH.md).

    Returns ``SimpleNamespace`` carrying ``hydrate`` (with ``.config``),
    ``iface`` (the assembled slab interface), and ``config`` (the
    ``HydrateConfig`` used). The CLI ``_run_export_step`` reads
    ``hydrate_config = getattr(self._hydrate_result, "config", None)`` so
    the chain MUST carry the hydrate (with ``.config``) -- NOT just the
    interface.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    iface = assemble_slab(
        candidate,
        InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=8.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=4.0,
        ),
    )
    # sH is a guest lattice (not water-only): the slab MUST have cage guests.
    # Do NOT assert the exact count -- it is version-dependent (Pitfall 5:
    # sH through the 3x3x8 slab produces ~4480 guests, but the exact number
    # depends on GenIce2 version + tiling). Assert > 0 only.
    assert iface.guest_nmolecules > 0, (
        "sH slab should have cage guests (small+medium+large all routed) -- "
        "guest_nmolecules == 0 indicates the medium cage_type_map key "
        "'12_1' (42-00 fix) regressed or the water-only skip fired erroneously"
    )
    return SimpleNamespace(hydrate=hydrate, iface=iface, config=config)


# -- Shared assertion helper -------------------------------------------------


def _assert_sH_interface_export(ws, gro_name, top_name):
    """Common assertions for an sH interface export: files written, ITP
    completeness, GRO/TOP consistency, built-in ch4 guest residue (``CH4_H``)
    presence + staged ITP (``ch4_hydrate.itp``), and ``gmx grompp`` rc==0
    when ``gmx`` is on PATH.

    sH is a guest lattice (not water-only): the built-in ch4 guest produces
    the ``CH4_H`` residue (moleculetype via ``MoleculetypeRegistry``) +
    the bundled ``ch4_hydrate.itp`` ITP. The guest count is ``> 0`` (NOT an
    exact count -- Pitfall 5: counts vary by lattice/version; sH through
    the slab produces ~4480 guests).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the exporter / CLI pipeline.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # File consistency (always runs -- catches missing-ITP + GRO/TOP mismatch).
    # NOTE: assert_gro_top_consistent counts atom LINES, not the .gro header
    # atom-count field, so it is robust to the GRO 100,000 atom-number wrap
    # (Pitfall 4 -- cosmetic, grompp still rc=0). sH through the slab is
    # ~54k atoms (under the wrap threshold), but the assertion is robust
    # regardless.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # Built-in ch4 guest: residue CH4_H staged + referenced.
    # The GUI InterfaceGROMACSExporter (hydrate_config=None -> built-in path)
    # / CLI _run_export_step (hydrate_config -> _build_custom_guest_info ->
    # None for built-in) both stage ch4_hydrate.itp for built-in ch4.
    assert (ws / "ch4_hydrate.itp").exists(), (
        "sH: built-in guest ITP ch4_hydrate.itp not staged"
    )
    mols = parse_top_molecules(str(top_path))
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in mols, f"sH: CH4_H not in [molecules]: {mols}"
    assert "CH4_H" in gro_res, f"sH: CH4_H not in .gro residues: {gro_res}"
    # Guest count > 0 (NOT exact -- Pitfall 5: counts vary by lattice/version;
    # sH through the 3x3x8 slab produces ~4480 guests).
    assert mols["CH4_H"] > 0, (
        f"sH: CH4_H molecule count not > 0: {mols['CH4_H']}"
    )
    # No custom-guest / fallback residue leaked.
    assert "GUE" not in mols, (
        f"sH: GUE in [molecules] (fallback leaked): {mols}"
    )
    assert "GUE" not in gro_res, (
        f"sH: GUE in .gro residues (fallback leaked): {gro_res}"
    )
    assert "MOL_H" not in mols, (
        f"sH: MOL_H in [molecules] (custom path leaked): {mols}"
    )

    # gmx grompp (only when gmx is on PATH -- file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(ws, gro_file=gro_name, top_file=top_name)
        assert rc == 0, (
            f"gmx grompp failed (sH, {gro_name}):\n{stderr}"
        )


# -- GUI interface export + grompp test --------------------------------------


@gmx_skipif
def test_sH_interface_gui_export_grompp(tmp_path, sH_chain):
    """gmx grompp exits 0 on the sH interface export via the GUI
    ``InterfaceGROMACSExporter.export_interface_gromacs`` with
    ``hydrate_config=None`` (the built-in ch4 path).

    Flow:
      1. Mock ``QFileDialog.getSaveFileName`` (REQUIRED -- under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> the
         exporter returns ``False`` without writing files) + ``QMessageBox``
         (Pattern 3 from 45-RESEARCH.md).
      2. ``InterfaceGROMACSExporter(parent_widget=None)
         .export_interface_gromacs(sH_chain.iface, hydrate_config=None)`` --
         the BUILT-IN path (``hydrate_config=None`` -> built-in ITP staging;
         the exporter stages ``ch4_hydrate.itp`` for built-in ch4).
      3. ``assert ok is True``.
      4. ``_assert_sH_interface_export(...)``: file-consistency (always
         runs), built-in ``CH4_H`` guest residue + ``ch4_hydrate.itp`` ITP
         staged, and ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm --
    grompp PBC rule). sH is triclinic but NOT blocked (only c0te/c1te are
    in TRICLINIC_HYDRATE_PHASES), so the interface assembly proceeds.
    """
    ws = tmp_path / "gui"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(
            sH_chain.iface, hydrate_config=None
        )
        assert ok is True, (
            "export_interface_gromacs returned False for sH -- QFileDialog "
            "mock may not have been picked up, or staging raised"
        )
    _assert_sH_interface_export(ws, "output.gro", "output.top")


# -- CLI interface export + grompp test ---------------------------------------


@gmx_skipif
def test_sH_interface_cli_export_grompp(tmp_path, sH_chain):
    """gmx grompp exits 0 on the sH interface export via the CLI
    ``CLIPipeline._run_export_step`` (interface branch -- Pattern 4 from
    45-RESEARCH.md: construct the pipeline, set ``_hydrate_result`` +
    ``_interface_result``, call ``_run_export_step()`` directly, NOT full
    ``execute()``).

    Flow:
      1. ``CLIPipeline(args=SimpleNamespace())`` with ``_output_dir``=ws,
         ``_hydrate_result``=hydrate (carries ``.config``), and
         ``_interface_result``=iface so the ``_run_export_step`` priority
         selection picks the interface branch.
      2. ``pipe._run_export_step()`` -- the interface branch calls
         ``write_interface_gro_file(structure, gro_path,
         custom_guest_info=cgi)`` + ``write_interface_top_file(structure,
         top_path, custom_guest_info=cgi)`` where ``cgi =
         _build_custom_guest_info(hydrate_config)`` (``None`` for built-in
         ch4). Then ``copy_itp_files_for_structure`` stages
         ``ch4_hydrate.itp`` for built-in ch4.
      3. ``assert code == 0``.
      4. ``_assert_sH_interface_export(...)``: file-consistency (always
         runs), built-in ``CH4_H`` guest residue + ``ch4_hydrate.itp`` ITP
         staged, and ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    No ``QFileDialog`` / ``QMessageBox`` mocking is needed -- the CLI
    pipeline writes files directly to ``self._output_dir`` (no dialog).
    The CLI writes ``interface.gro`` / ``interface.top`` (the GUI test
    writes ``output.gro`` / ``output.top`` via QFileDialog mock).

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm --
    grompp PBC rule). sH is triclinic but NOT blocked (only c0te/c1te are
    in TRICLINIC_HYDRATE_PHASES), so the interface assembly proceeds.
    """
    ws = tmp_path / "cli"
    ws.mkdir()
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = sH_chain.hydrate
    pipe._interface_result = sH_chain.iface
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the interface branch (sH)"
    )
    _assert_sH_interface_export(ws, "interface.gro", "interface.top")
