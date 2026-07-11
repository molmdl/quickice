"""E2E GUI full cross-tab (4 exporters) + grompp for 4 new guest lattices.

Plan 45-04 (Wave 2). Proves that the 4 new guest-bearing lattice types from
Phase 39 (sII, c2te, ice1hte, 16) produce grompp-valid output through the
FULL GUI tab chain: Interface -> Solute -> Custom Molecule -> Ion -> Export
(all 4 GUI exporters) with ``hydrate_config=None`` (the built-in ch4 path).

Purpose: Wave 1 (45-01/02/03) proved the interface export alone works for
the new lattices. This extends to the FULL chain -- solute insertion, custom
molecule insertion, ion insertion -- proving the new lattice structures
survive ALL downstream tabs and produce grompp-valid output at each. This
MIRRORS ``tests/test_e2e_builtin_cross_tab_regression.py`` (the 44.1-22
template) but swaps the 2-guest (ch4/thf) parametrization -> 4-lattice
(sII/c2te/ice1hte/16) parametrization, all with built-in guest_type="ch4".
Water-only lattices (sTprime, 17) are excluded here (no guests for the
solute/ion context) -- they are covered by 45-07.

Module-scoped fixture amortizes the GenIce2 + slab calls (~1-5s per lattice)
across all parametrized export cases (per AGENTS.md testing guidance).

Pattern 2 (fresh ``assemble_slab`` per inserter) is used because the ion
inserter mutates ``iface.molecule_index`` (``ion_inserter.py:259``). Giving
each inserter its OWN fresh slab (deterministic with ``seed=42``) prevents
the solute / custom exporters' ``interface_structure.molecule_index``
reference from being cross-contaminated by the ion inserter's mutation.

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter tests (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under
offscreen -> the exporter returns ``False`` without writing files. Inline
patching of ``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED
(Pattern 3 from 45-RESEARCH.md; the ``mock_save_dialog`` fixture from
``tests/test_output/conftest.py`` is directory-scoped and NOT available to
root-level test files).

``gmx`` is on PATH so grompp runs. The ``@gmx_skipif`` decorator skips the
whole test when ``gmx`` is absent; the helper also guards the grompp call
with ``shutil.which("gmx")`` so file-consistency + guest-residue asserts run
whenever the test runs.

Pitfalls avoided (45-RESEARCH.md):
- Pitfall 4 (GRO atom-number wrap at 100,000): NOT asserted --
  ``assert_gro_top_consistent`` counts atom LINES, not the header, so it
  is robust to the 100,000 wrap (cosmetic; grompp still rc=0).
- Pitfall 5 (guest counts vary by lattice/version): do NOT assert exact
  guest/solute/ion counts -- assert ``> 0`` only.
- Ion inserter mutates iface.molecule_index: fresh ``assemble_slab`` per
  inserter (Pattern 2) prevents cross-contamination.
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
from tests.conftest import gmx_skipif  # noqa: E402
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


# -- The 4 new guest-bearing lattices under test ------------------------------

_ALL_LATTICES = ("sII", "c2te", "ice1hte", "16")


# -- Module-scoped fixture: build full chains for ALL 4 lattices ONCE ---------


@pytest.fixture(scope="module")
def lattice_chains():
    """Module-scoped: build the full chain (hydrate -> fresh iface per
    inserter -> solute / custom / ion) for EACH of the 4 new guest-bearing
    lattice types ONCE, amortizing the GenIce2 + assemble_slab calls
    (~1-5s each) across all parametrized export cases.

    Pattern 2 (fresh ``assemble_slab`` per inserter): the ion inserter mutates
    ``iface.molecule_index`` (``ion_inserter.py:259``). Each inserter gets its
    OWN fresh ``assemble_slab`` (deterministic with ``seed=42``) so the
    solute / custom exporters' ``interface_structure.molecule_index``
    reference is NOT cross-contaminated by the ion inserter's mutation.

    The custom-molecule inserter uses a RENAMED copy of the bundled ethanol
    data (``cmet.gro`` / ``cmet.itp`` with ``[ moleculetype ]`` renamed
    ``etoh`` -> ``MOL``). This avoids a PRE-EXISTING ``.gro``/``.top``
    moleculetype-name mismatch (the registry default is ``MOL`` but the raw
    ``etoh.itp`` moleculetype is ``etoh`` -> ``assert_gro_top_consistent``
    would fail on the name mismatch). The rename is a test-setup detail; it
    does NOT affect the lattice cross-tab behavior being tested. For the
    built-in ch4 cage guest, the cage-guest ITP (``ch4_hydrate.itp``) does
    NOT collide with the custom-molecule ITP (``cmet.itp``) -- no filename
    collision.

    Returns ``dict {lattice_type: SimpleNamespace}`` where each namespace
    carries ``hydrate`` (with ``.config``), ``iface`` (for the interface
    exporter), ``solute``, ``custom``, ``ion`` (the 4 downstream structures
    the 4 GUI exporters consume), and ``config`` (the ``HydrateConfig``
    used).
    """
    # Build renamed cmet.gro / cmet.itp in a module-level temp dir (shared
    # across all 4 lattices -- it is the LIQUID custom molecule, not the cage
    # guest). Mirrors test_e2e_builtin_cross_tab_regression.py:109-124.
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

        # Fresh assemble_slab per inserter (Pattern 2 -- ion mutates
        # iface.molecule_index). Deterministic with seed=42 so all 4 slabs
        # are byte-identical until an inserter mutates its own copy.
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
        iface_solute = assemble_slab(
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
        iface_custom = assemble_slab(
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
        iface_ion = assemble_slab(
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
        # All 4 lattices are guest-bearing -> each slab must carry cage
        # guests (assert > 0, NOT exact -- Pitfall 5: counts vary by
        # lattice/version).
        assert iface.guest_nmolecules > 0, (
            f"{lattice_type} interface slab should have cage guests"
        )
        assert iface_solute.guest_nmolecules > 0, (
            f"{lattice_type} solute-source slab should have cage guests"
        )
        assert iface_custom.guest_nmolecules > 0, (
            f"{lattice_type} custom-source slab should have cage guests"
        )
        assert iface_ion.guest_nmolecules > 0, (
            f"{lattice_type} ion-source slab should have cage guests"
        )

        # Run the 3 inserters to produce the derived structures. Each
        # inserter returns a NEW structure, never mutating its input iface
        # (V-17) -- but the ion inserter DOES mutate the
        # interface_structure.molecule_index it RECEIVES (in-place), which
        # is why each inserter gets its OWN fresh slab (Pattern 2).
        solute = _insert_solutes(
            iface_solute, solute_type="CH4", concentration=0.3
        )
        cm_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=cmet_gro,
            itp_path=cmet_itp,
            molecule_count=1,
        )
        custom = CustomMoleculeInserter(cm_config, seed=42).place_random(
            iface_custom, 1
        )
        ion = _insert_ions(iface_ion, concentration=0.15)

        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            solute=solute,
            custom=custom,
            ion=ion,
            config=config,
        )
    yield chains
    shutil.rmtree(cmet_dir, ignore_errors=True)


# -- Shared assertion helper -------------------------------------------------


def _assert_lattice_export(ws, gro_name, top_name, lattice_type):
    """Common assertions for a lattice GUI export through one of the 4 GUI
    exporters: files written, built-in guest ITP staged + referenced, file
    consistency, and ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    All 4 lattices (sII / c2te / ice1hte / 16) use the built-in ch4 guest,
    so the built-in path (``hydrate_config=None``) stages
    ``ch4_hydrate.itp`` and the ``.top`` references ``CH4_H`` (NOT ``GUE``
    or ``MOL_H`` -- those would indicate the custom-guest / fallback path
    leaked).

    Asserts (per plan):
      - ``CH4_H`` in ``[molecules]`` AND in .gro residues.
      - ``ch4_hydrate.itp`` staged in the workspace.
      - ``GUE`` / ``MOL_H`` NOT in mols / residues (built-in path).
      - ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (always
        run -- catches ITP-missing + GRO/TOP mismatch).
      - ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    Does NOT assert exact guest/solute/ion counts (Pitfall 5 -- counts vary
    by lattice/version); does NOT assert atom-number exactness in the .gro
    header (Pitfall 4 -- GRO wraps at 100,000; assert_gro_top_consistent
    counts LINES, not the header).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
        lattice_type: One of the 4 lattice types being tested.
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the exporter.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # Built-in guest ITP staged (NOT a custom ITP). The GUI exporter's
    # _stage_hydrate_guest_itps (hydrate_config=None built-in path) copies
    # the bundled pre-transformed ch4_hydrate.itp.
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"{lattice_type}: built-in guest ITP ch4_hydrate.itp not staged in "
        f"{ws} -- regression: the built-in path must stage ch4_hydrate.itp"
    )
    staged_itp = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_itp, (
        f"{lattice_type}: staged ch4_hydrate.itp missing moleculetype CH4_H "
        f"-- the built-in ITP must define CH4_H"
    )
    assert "MOL_H" not in staged_itp, (
        f"{lattice_type}: MOL_H (custom-guest moleculetype) found in staged "
        f"ch4_hydrate.itp -- regression: the built-in path must NOT produce "
        f"MOL_H"
    )

    # .top [molecules] references the built-in residue name (NOT GUE/MOL_H).
    mols = parse_top_molecules(str(top_path))
    assert "CH4_H" in mols, (
        f"{lattice_type}: CH4_H not in [molecules]: {mols}"
    )
    assert mols["CH4_H"] > 0, (
        f"{lattice_type}: CH4_H molecule count not > 0: {mols['CH4_H']}"
    )
    assert "GUE" not in mols, (
        f"{lattice_type}: GUE in [molecules] (fallback leaked): {mols}"
    )
    assert "MOL_H" not in mols, (
        f"{lattice_type}: MOL_H in [molecules] (custom-guest path leaked): "
        f"{mols}"
    )

    # .gro residues contain the built-in residue name (NOT GUE/MOL_H).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res, (
        f"{lattice_type}: CH4_H not in .gro residues: {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"{lattice_type}: GUE in .gro residues (fallback leaked): {gro_res}"
    )
    assert "MOL_H" not in gro_res, (
        f"{lattice_type}: MOL_H in .gro residues (custom-guest path leaked): "
        f"{gro_res}"
    )

    # File consistency (always runs -- catches ITP-missing + GRO/TOP
    # mismatch). assert_gro_top_consistent counts atom LINES, not the .gro
    # header atom-count field, so it is robust to the GRO 100,000
    # atom-number wrap (Pitfall 4 -- cosmetic, grompp still rc=0).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH -- file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(
            ws, gro_file=gro_name, top_file=top_name
        )
        assert rc == 0, (
            f"gmx grompp failed (lattice {lattice_type}, {gro_name}):\n"
            f"{stderr}"
        )


# -- Parametrized GUI full cross-tab (4 exporters) + grompp test -------------


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_ALL_LATTICES))
def test_lattice_cross_tab_gui_grompp(tmp_path, lattice_chains, lattice_type):
    """gmx grompp exits 0 on the FULL GUI cross-tab chain (Interface -> Solute
    -> Custom Molecule -> Ion -> Export) for each of the 4 new guest-bearing
    lattice types (sII / c2te / ice1hte / 16), all with built-in
    guest_type="ch4" and ``hydrate_config=None`` (the built-in ch4 path).

    For each of the 4 GUI exporters (interface / solute / custom-molecule /
    ion), the test:
      1. Mocks ``QFileDialog.getSaveFileName`` (REQUIRED -- under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> the
         exporter returns ``False`` without writing files) + ``QMessageBox``
         (Pattern 3 from 45-RESEARCH.md).
      2. Calls the exporter method with ``hydrate_config=None`` (the
         built-in default -- NO custom config -> stages ch4_hydrate.itp,
         references CH4_H).
      3. Asserts the exporter returned ``True``.
      4. ``_assert_lattice_export(...)``: built-in guest ITP staged +
         referenced (CH4_H, ch4_hydrate.itp), NO GUE/MOL_H leak, file
         consistency passes, and ``gmx grompp`` exits 0.

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm --
    grompp PBC rule). The 1x1x1 supercell is sufficient for these 4
    non-triclinic guest lattices (Pitfall 1 only affects the triclinic
    filled ices c0te/c1te, which are blocked and covered by separate plans).

    Pattern 2 (fresh ``assemble_slab`` per inserter) is applied in the
    module-scoped fixture so the ion inserter's mutation of
    ``iface.molecule_index`` does NOT cross-contaminate the solute / custom
    exporters' interface references.
    """
    chain = lattice_chains[lattice_type]

    # -- 1. Interface exporter (Interface tab) -------------------------------
    ws = tmp_path / "interface"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(
            chain.iface, hydrate_config=None
        )
        assert ok is True, (
            f"export_interface_gromacs returned False for {lattice_type} -- "
            f"QFileDialog mock may not have been picked up, or staging raised"
        )
    _assert_lattice_export(ws, "output.gro", "output.top", lattice_type)

    # -- 2. Solute exporter (Solute tab) -------------------------------------
    ws = tmp_path / "solute"
    ws.mkdir()
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = SoluteGROMACSExporter(parent_widget=None)
        ok = exporter.export_solute_gromacs(
            chain.solute, hydrate_config=None
        )
        assert ok is True, (
            f"export_solute_gromacs returned False for {lattice_type} -- "
            f"QFileDialog mock may not have been picked up, or staging raised"
        )
    _assert_lattice_export(ws, "output.gro", "output.top", lattice_type)
    # Solute ITP (ch4_liquid.itp) copied by the exporter.
    assert (ws / "ch4_liquid.itp").exists(), (
        f"{lattice_type}: solute ITP (ch4_liquid.itp) not copied by the "
        f"solute exporter"
    )

    # -- 3. Custom-molecule exporter (Custom Molecule tab) ------------------
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
            f"export_custom_molecule_gromacs returned False for "
            f"{lattice_type} -- QFileDialog mock may not have been picked "
            f"up, or staging raised"
        )
    _assert_lattice_export(ws, "output.gro", "output.top", lattice_type)
    # Custom-molecule ITP (cmet.itp) copied by the exporter (atomtypes
    # commented).
    assert (ws / "cmet.itp").exists(), (
        f"{lattice_type}: custom molecule ITP (cmet.itp) not copied by the "
        f"custom exporter"
    )

    # -- 4. Ion exporter (Ion tab) -------------------------------------------
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
            f"export_ion_gromacs returned False for {lattice_type} -- "
            f"QFileDialog mock may not have been picked up, or staging raised"
        )
    _assert_lattice_export(ws, "output.gro", "output.top", lattice_type)
    # Ion ITP (ion.itp) written by write_ion_itp.
    assert (ws / "ion.itp").exists(), (
        f"{lattice_type}: ion ITP (ion.itp) not written by write_ion_itp"
    )
