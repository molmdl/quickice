"""E2E CLI interface export + grompp for 6 new lattice types (Phase 45-02).

Plan 45-02 (Wave 1 foundation, CLI half). Proves that the 6 non-blocked new
lattice types from Phase 39 (sII, c2te, ice1hte, sTprime, 16, 17) produce
grompp-valid output at the Interface tab CLI export step via
``CLIPipeline._run_export_step`` (the interface branch -- Pattern 4: construct
the pipeline, set ``_hydrate_result`` + ``_interface_result``, call
``_run_export_step()`` directly, NOT full ``execute()``).

Purpose: the CLI half of the Wave 1 foundation. The GUI path is tested in
45-01 (``test_e2e_lattice_interface_gui.py``); this tests the CLI
``_run_export_step`` interface branch. Both paths use
``write_interface_gro_file`` / ``write_interface_top_file`` but the CLI path
goes through ``CLIPipeline._run_export_step`` (Pattern 4 from
45-RESEARCH.md: construct ``CLIPipeline(args=SimpleNamespace())``, set
``_output_dir`` + ``_hydrate_result`` + ``_interface_result``, call
``_run_export_step()`` directly).

The research (45-RESEARCH.md) empirically verified 8/10 lattices pass
interface grompp (rc=0), but NO test proves this today through the CLI
``_run_export_step`` interface branch -- all existing CLI cross-tab e2e
tests use sI only (``test_e2e_builtin_cross_tab_regression.py``). This
closes that gap for the 6 non-triclinic new lattices (c0te/c1te are blocked
at the interface tab by design via ``TRICLINIC_HYDRATE_PHASES``; they are
covered by separate triclinic plans).

``CLIPipeline._run_export_step`` reads ``hydrate_config = getattr(
self._hydrate_result, "config", None)`` → the built-in ``HydrateConfig``
(``guest_type="ch4"``) → ``_build_custom_guest_info(config)`` returns
``None`` → built-in path. ``copy_itp_files_for_structure`` stages
``ch4_hydrate.itp`` for built-in ch4 (and stages nothing for water-only
lattices, which have ``guest_nmolecules == 0``). For water-only lattices
(sTprime, 17) the generator's water-only skip drops cages entirely so the
resulting hydrate has ``guest_nmolecules == 0``.

Module-scoped fixture amortizes the GenIce2 + ``assemble_slab`` calls
(~1-5s per lattice) across all parametrized cases (per AGENTS.md testing
guidance). Identical fixture to 45-01 (each test module owns its own).

No ``QFileDialog`` / ``QMessageBox`` patching is needed -- the CLI pipeline
writes files directly to ``self._output_dir`` (no dialog).

``gmx`` is on PATH so grompp runs. The ``@gmx_skipif`` decorator skips the
whole test when ``gmx`` is absent; the helper also guards the grompp call
with ``shutil.which("gmx")`` so file-consistency + guest-residue asserts run
whenever the test runs.

Pitfalls avoided (45-RESEARCH.md):
- Pitfall 1 (triclinic box-size): N/A -- c0te/c1te are blocked, not tested
  here. The 6 lattices here use a 3.0x3.0x8.0 nm slab box (shortest vector
  3.0 nm > 2x rcoulomb=2.0 nm -- grompp PBC rule).
- Pitfall 4 (GRO atom-number wrap at 100,000): NOT asserted --
  ``assert_gro_top_consistent`` counts atom LINES, not the header, so it
  is robust to the 100,000 wrap (cosmetic; grompp still rc=0).
- Pitfall 5 (guest counts vary by lattice/version): do NOT assert exact
  guest counts -- assert ``> 0`` for guest lattices, ``== 0`` for
  water-only.
- Pitfall 6 (two hydrate export paths): this test exercises the CLI
  ``_run_export_step`` interface branch (``write_interface_*``), NOT the
  GUI ``HydrateGROMACSExporter`` (``write_multi_molecule_*``). The 45-01
  GUI test covers the GUI path; these are SEPARATE code paths.
"""

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

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
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    run_gmx_grompp,
    assert_itp_completeness,
    assert_gro_top_consistent,
    parse_top_molecules,
    parse_gro_residue_names,
)


# -- Lattice classification ---------------------------------------------------

# Lattices WITH cage guests (built-in ch4). Water-only lattices ignore the
# guest_type="ch4" in the generator (the water-only skip in
# hydrate_generator.py drops cages entirely), so the resulting hydrate has
# guest_nmolecules == 0.
_LATTICES_WITH_GUESTS = frozenset(("sII", "c2te", "ice1hte", "16"))
_LATTICES_WATER_ONLY = frozenset(("sTprime", "17"))
_ALL_LATTICES = ("sII", "c2te", "ice1hte", "sTprime", "16", "17")


# -- Module-scoped fixture: build chains for ALL 6 lattices ONCE -------------


@pytest.fixture(scope="module")
def lattice_chains():
    """Module-scoped: build the hydrate -> interface chain for EACH of the 6
    non-blocked new lattice types ONCE, amortizing the GenIce2 + assemble_slab
    calls (~1-5s each) across all parametrized export cases.

    For water-only lattices (sTprime, 17) ``guest_type="ch4"`` is ignored by
    the generator (the water-only skip drops cages), so the resulting hydrate
    has ``guest_nmolecules == 0``.

    Returns ``dict {lattice_type: SimpleNamespace}`` where each namespace
    carries ``hydrate`` (with ``.config``), ``iface`` (the assembled slab
    interface), and ``config`` (the ``HydrateConfig`` used). The CLI
    ``_run_export_step`` reads ``hydrate_config = getattr(
    self._hydrate_result, "config", None)`` so the chain MUST carry the
    hydrate (with ``.config``) -- NOT just the interface.
    """
    chains = {}
    for lattice_type in _ALL_LATTICES:
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
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
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            config=config,
        )
    yield chains


# -- CLI pipeline helper (Pattern 4) -----------------------------------------


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and the downstream structure set on ``_<downstream_attr>_result``
    so the ``_run_export_step`` priority selection picks that branch.

    All other ``_*_result`` stay at their ``__init__`` default of ``None``.
    Mirrors the helper in ``tests/test_e2e_builtin_cross_tab_regression.py``
    (lines 373-385) and ``tests/test_e2e_custom_guest_cli_grompp.py``.

    Args:
        output_dir: Workspace directory (``Path``) where the CLI pipeline
            writes its export files (``_output_dir``).
        hydrate: The ``HydrateStructure`` (carries ``.config`` -- a built-in
            ``HydrateConfig`` with ``guest_type="ch4"``). ``_run_export_step``
            reads ``hydrate_config = getattr(self._hydrate_result, "config",
            None)`` -> ``_build_custom_guest_info(config)`` returns ``None``
            for built-in -> built-in path byte-identical to pre-44.1.
        downstream_attr: The ``_*_result`` attribute name to set (e.g.
            ``"_interface_result"`` for the interface branch).
        downstream_struct: The downstream structure to set on that attribute
            (e.g. the assembled slab ``InterfaceStructure``).

    Returns:
        The constructed ``CLIPipeline`` (NOT yet executed).
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


# -- Shared assertion helper -------------------------------------------------


def _assert_lattice_cli_export(ws, step_name, lattice_type, chain):
    """Common assertions for a CLI lattice export: files written, ITP
    completeness, GRO/TOP consistency, guest-residue presence/absence, and
    ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    Branches on ``lattice_type``:
      - Guest lattices (sII, c2te, ice1hte, 16): asserts ``CH4_H`` is in
        ``[molecules]`` AND in the .gro residues, ``ch4_hydrate.itp`` is
        staged, and the guest molecule count is ``> 0`` (NOT an exact count
        -- Pitfall 5: counts vary by lattice/version).
      - Water-only lattices (sTprime, 17): asserts NO guest residue (no
        ``CH4_H``, no ``GUE``) in mols/residues and ``SOL`` is present.

    The CLI writes ``{step_name}.gro`` / ``{step_name}.top`` (the GUI 45-01
    test writes ``output.gro`` / ``output.top`` via QFileDialog mock); this
    helper takes ``step_name`` so it can be reused for the other CLI branches
    in later plans (solute / custom / ion).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        step_name: The CLI step name (e.g. ``"interface"``); the files are
            ``{step_name}.gro`` / ``{step_name}.top``.
        lattice_type: One of the 6 lattice types being tested.
        chain: ``SimpleNamespace`` with ``hydrate``, ``iface``, ``config``
            (carried for downstream assertions / future extension).
    """
    gro_name = f"{step_name}.gro"
    top_name = f"{step_name}.top"
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the CLI pipeline to _output_dir.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # File consistency (always runs -- catches missing-ITP + GRO/TOP mismatch).
    # NOTE: assert_gro_top_consistent counts atom LINES, not the .gro header
    # atom-count field, so it is robust to the GRO 100,000 atom-number wrap
    # (Pitfall 4 -- cosmetic, grompp still rc=0).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    mols = parse_top_molecules(str(top_path))
    gro_res = set(parse_gro_residue_names(str(gro_path)))

    if lattice_type in _LATTICES_WITH_GUESTS:
        # Built-in ch4 guest: residue CH4_H staged + referenced.
        assert (ws / "ch4_hydrate.itp").exists(), (
            f"{lattice_type}: built-in guest ITP ch4_hydrate.itp not staged"
        )
        assert "CH4_H" in mols, (
            f"{lattice_type}: CH4_H not in [molecules]: {mols}"
        )
        assert "CH4_H" in gro_res, (
            f"{lattice_type}: CH4_H not in .gro residues: {gro_res}"
        )
        # Guest count > 0 (NOT exact -- Pitfall 5: counts vary by
        # lattice/version).
        assert mols["CH4_H"] > 0, (
            f"{lattice_type}: CH4_H molecule count not > 0: {mols['CH4_H']}"
        )
        # No custom-guest / fallback residue leaked.
        assert "GUE" not in mols, (
            f"{lattice_type}: GUE in [molecules] (fallback leaked): {mols}"
        )
        assert "GUE" not in gro_res, (
            f"{lattice_type}: GUE in .gro residues (fallback leaked): {gro_res}"
        )
        assert "MOL_H" not in mols, (
            f"{lattice_type}: MOL_H in [molecules] (custom path leaked): {mols}"
        )
    elif lattice_type in _LATTICES_WATER_ONLY:
        # Water-only: no guest residue / guest ITP at all; SOL present.
        assert "CH4_H" not in mols, (
            f"{lattice_type} (water-only): CH4_H in [molecules]: {mols}"
        )
        assert "GUE" not in mols, (
            f"{lattice_type} (water-only): GUE in [molecules]: {mols}"
        )
        assert "CH4_H" not in gro_res, (
            f"{lattice_type} (water-only): CH4_H in .gro residues: {gro_res}"
        )
        assert "GUE" not in gro_res, (
            f"{lattice_type} (water-only): GUE in .gro residues: {gro_res}"
        )
        assert "SOL" in mols, (
            f"{lattice_type} (water-only): SOL not in [molecules]: {mols}"
        )
        assert "SOL" in gro_res, (
            f"{lattice_type} (water-only): SOL not in .gro residues: {gro_res}"
        )
    else:  # pragma: no cover - defensive
        raise AssertionError(f"unhandled lattice_type {lattice_type!r}")

    # gmx grompp (only when gmx is on PATH -- file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(
            ws, gro_file=gro_name, top_file=top_name
        )
        assert rc == 0, (
            f"gmx grompp failed (lattice {lattice_type}, {gro_name}):\n{stderr}"
        )


# -- Parametrized CLI interface export + grompp test -------------------------


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_ALL_LATTICES))
def test_lattice_interface_cli_export_grompp(
    tmp_path, lattice_chains, lattice_type
):
    """gmx grompp exits 0 on the interface export via the CLI
    ``CLIPipeline._run_export_step`` (interface branch -- Pattern 4) for
    each of the 6 non-blocked new lattice types (sII / c2te / ice1hte /
    sTprime / 16 / 17).

    Flow (each parametrized case):
      1. ``_make_cli_pipeline(ws, chain.hydrate, "_interface_result",
         chain.iface)`` -- constructs a ``CLIPipeline`` with
         ``_output_dir``=ws, ``_hydrate_result``=hydrate (carries
         ``.config``), ``_interface_result``=iface so the ``_run_export_step``
         priority selection picks the interface branch.
      2. ``pipe._run_export_step()`` -- the interface branch calls
         ``write_interface_gro_file(structure, gro_path,
         custom_guest_info=cgi)`` + ``write_interface_top_file(structure,
         top_path, custom_guest_info=cgi)`` where ``cgi =
         _build_custom_guest_info(hydrate_config)`` (``None`` for built-in
         ch4). Then ``copy_itp_files_for_structure`` stages ``ch4_hydrate.itp``
         for built-in ch4 lattices (and stages nothing for water-only).
      3. ``assert code == 0``.
      4. ``_assert_lattice_cli_export(...)``: file-consistency (always
         runs), guest-residue presence/absence by lattice class, and
         ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    No ``QFileDialog`` / ``QMessageBox`` mocking is needed -- the CLI
    pipeline writes files directly to ``self._output_dir`` (no dialog).

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm --
    grompp PBC rule). The 1x1x1 supercell is sufficient for these 6
    non-triclinic lattices (Pitfall 1 only affects the triclinic filled
    ices c0te/c1te, which are blocked and covered by separate plans).
    """
    chain = lattice_chains[lattice_type]

    ws = tmp_path / "interface"
    ws.mkdir()
    pipe = _make_cli_pipeline(ws, chain.hydrate, "_interface_result", chain.iface)
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the interface branch "
        f"(lattice {lattice_type})"
    )
    _assert_lattice_cli_export(ws, "interface", lattice_type, chain)
