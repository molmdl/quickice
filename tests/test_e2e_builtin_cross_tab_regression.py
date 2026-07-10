"""Regression guard: built-in ch4 + thf through ALL tabs (GUI + CLI).

Plan 44.1-22 (wave 5). Proves the ``hydrate_config=None`` (built-in) path
through all 4 GUI exporters + the CLI export branches is unaffected by the
44.1 custom-guest refactor.

Purpose: every exporter change in 44.1 MUST keep the ``hydrate_config=None``
(or no custom assignment) path identical to pre-44.1 behavior. The
``custom_guest_info=None`` default keeps the built-in ch4/thf path. This
test guards against regression of the built-in path through all 4 GUI
exporters (interface / solute / custom-molecule / ion) + the CLI export
branches.

Key assertion: the built-in guest ITP (``ch4_hydrate.itp`` /
``thf_hydrate.itp``) is staged (NOT a custom ITP), and the ``.top`` references
the built-in residue name (``CH4_H`` / ``THF_H``), NOT ``GUE`` or ``MOL_H``.
This confirms the ``hydrate_config=None`` default path is the pre-44.1
built-in behavior.

Module-scoped fixture amortizes the GenIce2 + inserter calls (~3-5s each)
across the parametrized cases (per AGENTS.md testing guidance).

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter tests (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under offscreen
→ the exporter returns ``False`` without writing files. Inline patching of
``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED (the
``mock_save_dialog`` fixture from ``tests/test_output/conftest.py`` is
directory-scoped and NOT available to root-level test files).
``gmx`` is on PATH so grompp runs (not skipped).
"""

import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.custom_molecule_inserter import (  # noqa: E402
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (  # noqa: E402
    CustomMoleculeConfig,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import (  # noqa: E402
    CustomMoleculeGROMACSExporter,
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
)
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _insert_solutes,
    _insert_ions,
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ── Built-in guest → expected residue name + staged ITP filename ──────────────

_GUEST_RESIDUE = {"ch4": "CH4_H", "thf": "THF_H"}
_GUEST_ITP = {"ch4": "ch4_hydrate.itp", "thf": "thf_hydrate.itp"}


# ── Module-scoped fixture: build ch4 + thf full chains ONCE ───────────────────


@pytest.fixture(scope="module")
def built_in_chains():
    """Module-scoped: build the full chain (hydrate → iface → solute / custom /
    ion) for BOTH ch4 and thf ONCE, amortizing the GenIce2 + inserter calls
    (~3-5s each) across all parametrized cases.

    Returns ``dict {"ch4": SimpleNamespace, "thf": SimpleNamespace}`` where each
    namespace carries ``hydrate`` (with ``.config``), ``iface``, ``solute``,
    ``custom``, ``ion`` — the 4 downstream structures the 4 GUI exporters + 4
    CLI branches consume.

    The custom-molecule inserter uses a RENAMED copy of the bundled ethanol
    data (``cmet.gro`` / ``cmet.itp`` with ``[ moleculetype ]`` renamed
    ``etoh`` → ``MOL``). This avoids a PRE-EXISTING ``.gro``/``.top`` moleculetype-
    name mismatch (the registry default is ``MOL`` but the raw ``etoh.itp``
    moleculetype is ``etoh`` → ``assert_gro_top_consistent`` would fail on the
    name mismatch). The rename is a test-setup detail; it does NOT affect the
    44.1 regression being tested (built-in cage-guest ITP staging). For the
    built-in ch4/thf cage guest, the cage-guest ITP (``ch4_hydrate.itp`` /
    ``thf_hydrate.itp``) does NOT collide with the custom-molecule ITP
    (``cmet.itp``) — no filename collision (unlike the 44.1-13 custom-cage-guest
    test where both used ``etoh.itp``).
    """
    # Build renamed cmet.gro / cmet.itp in a module-level temp dir.
    cmet_dir = Path(tempfile.mkdtemp(prefix="quickice_cmet_"))
    cmet_gro = cmet_dir / "cmet.gro"
    cmet_itp = cmet_dir / "cmet.itp"
    shutil.copy(ETOH_GRO, cmet_gro)
    cmet_lines = ETOH_ITP.read_text().splitlines(keepends=True)
    _in_moltype = False
    for i, line in enumerate(cmet_lines):
        if "[ moleculetype ]" in line:
            _in_moltype = True
        elif _in_moltype and line.strip() and not line.strip().startswith(";"):
            # First non-comment non-empty line after [ moleculetype ] is the
            # moleculetype name ("etoh       3"); rename "etoh" -> "MOL".
            cmet_lines[i] = line.replace("etoh", "MOL", 1)
            break
    cmet_itp.write_text("".join(cmet_lines))

    chains = {}
    for guest_type in ("ch4", "thf"):
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type="sI",
            guest_type=guest_type,
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
        # Built-in guests must survive the slab assembly.
        assert iface.guest_nmolecules > 0, (
            f"built-in {guest_type} slab should have cage guests"
        )
        # Run the 3 inserters to produce the derived structures (each returns
        # a NEW structure, never mutating the input iface — V-17).
        solute = _insert_solutes(iface, solute_type="CH4", concentration=0.3)
        cm_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=cmet_gro,
            itp_path=cmet_itp,
            molecule_count=1,
        )
        custom = CustomMoleculeInserter(cm_config, seed=42).place_random(iface, 1)
        ion = _insert_ions(iface, concentration=0.15)
        chains[guest_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            solute=solute,
            custom=custom,
            ion=ion,
        )
    yield chains
    shutil.rmtree(cmet_dir, ignore_errors=True)


# ── Shared assertion helper ──────────────────────────────────────────────────


def _assert_builtin_export(ws, gro_name, top_name, guest_type):
    """Common assertions for a built-in export: ITP staged, residue name,
    file consistency, grompp.

    Asserts the built-in guest ITP (``ch4_hydrate.itp`` / ``thf_hydrate.itp``)
    is staged (NOT a custom ITP), the ``.top`` references the built-in residue
    name (``CH4_H`` / ``THF_H``, NOT ``GUE`` or ``MOL_H``), and ``gmx grompp``
    exits 0 when ``gmx`` is on PATH.

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
        guest_type: ``"ch4"`` or ``"thf"``.
    """
    expected_res = _GUEST_RESIDUE[guest_type]
    expected_itp = _GUEST_ITP[guest_type]
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # Built-in guest ITP staged (NOT a custom ITP). The helper
    # _stage_hydrate_guest_itps (GUI) / copy_itp_files_for_structure (CLI)
    # copies the bundled pre-transformed {guest_type}_hydrate.itp for the
    # hydrate_config=None built-in path.
    assert (ws / expected_itp).exists(), (
        f"built-in guest ITP {expected_itp} not staged in {ws} — "
        f"regression: the built-in path must stage {expected_itp}"
    )
    staged_itp = (ws / expected_itp).read_text()
    assert expected_res in staged_itp, (
        f"staged {expected_itp} missing moleculetype {expected_res} — "
        f"the built-in ITP must define {expected_res}"
    )
    assert "MOL_H" not in staged_itp, (
        f"MOL_H (custom-guest moleculetype) found in staged {expected_itp} — "
        f"regression: the built-in path must NOT produce MOL_H"
    )

    # .top [molecules] references the built-in residue name (NOT GUE/MOL_H).
    mols = parse_top_molecules(str(top_path))
    assert expected_res in mols, (
        f"built-in residue {expected_res} not in [molecules]: {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE in [molecules] (custom_guest_info fallback leaked): {mols}"
    )
    assert "MOL_H" not in mols, (
        f"MOL_H in [molecules] (custom-guest path leaked): {mols}"
    )

    # .gro residues contain the built-in residue name (NOT GUE/MOL_H).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert expected_res in gro_res, (
        f"built-in residue {expected_res} not in .gro residues: {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE in .gro residues (custom_guest_info fallback leaked): {gro_res}"
    )
    assert "MOL_H" not in gro_res, (
        f"MOL_H in .gro residues (custom-guest path leaked): {gro_res}"
    )

    # File consistency (always runs — catches ITP-missing + GRO/TOP mismatch).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH — file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(
            ws, gro_file=gro_name, top_file=top_name
        )
        assert rc == 0, (
            f"gmx grompp failed (built-in {guest_type}, {gro_name}):\n{stderr}"
        )


# ── GUI regression test ───────────────────────────────────────────────────────


@pytest.mark.parametrize("guest_type", ["ch4", "thf"])
def test_builtin_cross_tab_gui_regression(tmp_path, built_in_chains, guest_type):
    """Built-in ch4/thf through all 4 GUI exporters with ``hydrate_config=None``
    still exports grompp-valid output (no regression from the 44.1 refactor).

    For each of the 4 GUI exporters (interface / solute / custom-molecule /
    ion), the test:
      1. Mocks ``QFileDialog.getSaveFileName`` (REQUIRED — under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` → exporter
         returns ``False`` without writing files) + ``QMessageBox``.
      2. Calls the exporter method with ``hydrate_config=None`` (the built-in
         default — NO custom config).
      3. Asserts the built-in guest ITP is staged, the ``.top`` references the
         built-in residue name (``CH4_H`` / ``THF_H``, NOT ``GUE`` / ``MOL_H``),
         file consistency passes, and ``gmx grompp`` exits 0.

    This proves the built-in path through all GUI tabs is unaffected by the
    44.1 exporter changes (which added the ``hydrate_config`` param + the
    ``_stage_hydrate_guest_itps`` helper call). The ``hydrate_config=None``
    default → ``custom_guest_info=None`` → built-in ITP copy byte-identical to
    pre-44.1 behavior.
    """
    chain = built_in_chains[guest_type]

    # ── 1. Interface exporter (Interface tab) ────────────────────────────
    ws = tmp_path / "interface"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(chain.iface, hydrate_config=None)
        assert ok is True, (
            "export_interface_gromacs returned False — QFileDialog mock may "
            "not have been picked up, or staging raised"
        )
    _assert_builtin_export(ws, "output.gro", "output.top", guest_type)

    # ── 2. Solute exporter (Solute tab) ───────────────────────────────────
    ws = tmp_path / "solute"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = SoluteGROMACSExporter(parent_widget=None)
        ok = exporter.export_solute_gromacs(chain.solute, hydrate_config=None)
        assert ok is True, (
            "export_solute_gromacs returned False — QFileDialog mock may not "
            "have been picked up, or staging raised"
        )
    _assert_builtin_export(ws, "output.gro", "output.top", guest_type)
    # Solute ITP (ch4_liquid.itp) copied by the exporter.
    assert (ws / "ch4_liquid.itp").exists(), (
        "solute ITP (ch4_liquid.itp) not copied by the solute exporter"
    )

    # ── 3. Custom-molecule exporter (Custom Molecule tab) ────────────────
    ws = tmp_path / "custom_mol"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)
        ok = exporter.export_custom_molecule_gromacs(
            chain.custom, hydrate_config=None
        )
        assert ok is True, (
            "export_custom_molecule_gromacs returned False — QFileDialog mock "
            "may not have been picked up, or staging raised"
        )
    _assert_builtin_export(ws, "output.gro", "output.top", guest_type)
    # Custom-molecule ITP (cmet.itp) copied by the exporter (atomtypes commented).
    assert (ws / "cmet.itp").exists(), (
        "custom molecule ITP (cmet.itp) not copied by the custom exporter"
    )

    # ── 4. Ion exporter (Ion tab) ────────────────────────────────────────
    ws = tmp_path / "ion"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = IonGROMACSExporter(parent_widget=None)
        ok = exporter.export_ion_gromacs(chain.ion, hydrate_config=None)
        assert ok is True, (
            "export_ion_gromacs returned False — QFileDialog mock may not "
            "have been picked up, or staging raised"
        )
    _assert_builtin_export(ws, "output.gro", "output.top", guest_type)
    # Ion ITP (ion.itp) written by write_ion_itp.
    assert (ws / "ion.itp").exists(), (
        "ion ITP (ion.itp) not written by write_ion_itp"
    )


# ── CLI regression test ───────────────────────────────────────────────────────


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and the downstream structure set on ``_<downstream_attr>_result``
    so the ``_run_export_step`` priority selection picks that branch.

    All other ``_*_result`` stay at their ``__init__`` default of ``None``.
    Mirrors the helper in ``tests/test_e2e_custom_guest_cli_grompp.py``.
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


@pytest.mark.parametrize("guest_type", ["ch4", "thf"])
def test_builtin_cross_tab_cli_regression(tmp_path, built_in_chains, guest_type):
    """Built-in ch4/thf through all 4 CLI export branches still exports
    grompp-valid output (no regression from the 44.1 refactor).

    For each of the 4 CLI export branches (interface / solute / custom-molecule
    / ion), the test:
      1. Constructs a ``CLIPipeline`` with ``_hydrate_result`` set to the
         built-in hydrate (carries ``.config`` — a built-in ``HydrateConfig``
         with ``guest_type`` = ``"ch4"`` / ``"thf"``) and the downstream
         structure set on the target ``_*_result`` attribute.
      2. Calls ``_run_export_step()`` directly (the export-step-direct approach
         from plan 17's tests). ``_run_export_step`` reads
         ``hydrate_config = getattr(self._hydrate_result, "config", None)`` →
         the built-in ``HydrateConfig``. ``_build_custom_guest_info(config)``
         returns ``None`` for built-in → ``custom_guest_info=None`` → built-in
         residue name (``CH4_H`` / ``THF_H``), byte-identical to pre-44.1.
      3. Asserts the built-in guest ITP is staged, the ``.top`` references the
         built-in residue name (``CH4_H`` / ``THF_H``, NOT ``GUE`` / ``MOL_H``),
         file consistency passes, and ``gmx grompp`` exits 0.

    No ``QFileDialog`` mocking is needed — the CLI pipeline writes files
    directly to ``self._output_dir`` (no dialog).
    """
    chain = built_in_chains[guest_type]
    hydrate = chain.hydrate

    # The 4 CLI export branches: (step_name, downstream_attr, structure).
    branches = [
        ("interface", "_interface_result", chain.iface),
        ("solute", "_solute_result", chain.solute),
        ("custom", "_custom_result", chain.custom),
        ("ion", "_ion_result", chain.ion),
    ]

    for step_name, attr, struct in branches:
        ws = tmp_path / step_name
        ws.mkdir()
        pipe = _make_cli_pipeline(ws, hydrate, attr, struct)
        code = pipe._run_export_step()
        assert code == 0, (
            f"_run_export_step failed (rc={code}) for the {step_name} branch "
            f"(built-in {guest_type})"
        )
        # Each branch writes {step_name}.gro / {step_name}.top to _output_dir.
        _assert_builtin_export(
            ws, f"{step_name}.gro", f"{step_name}.top", guest_type
        )
        # Additional per-branch ITP checks.
        if step_name == "solute":
            assert (ws / "ch4_liquid.itp").exists(), (
                "solute ITP (ch4_liquid.itp) not staged by the CLI solute branch"
            )
        elif step_name == "custom":
            assert (ws / "cmet.itp").exists(), (
                "custom molecule ITP (cmet.itp) not staged by the CLI custom branch"
            )
        elif step_name == "ion":
            assert (ws / "ion.itp").exists(), (
                "ion ITP (ion.itp) not written by the CLI ion branch"
            )
