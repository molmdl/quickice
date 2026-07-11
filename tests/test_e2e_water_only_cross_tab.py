"""E2E water-only (sTprime, 17) cross-tab (solute/ion) + grompp -- verify no
crash on ``guest_nmolecules=0`` (Pitfall 3).

Plan 45-07 (Wave 2). Proves that the 2 water-only lattice types from Phase 39
(sTprime, 17) -- which carry ``guest_nmolecules=0`` and ``guest_atom_count=0``
through the slab interface -- produce grompp-valid output through the FULL
tab chain: Interface -> Solute -> Ion -> Export (3 GUI exporters + 3 CLI
branches), with NO crash from the solute/ion inserters on the empty-guest
interface.

Purpose: Pitfall 3 (from 45-RESEARCH.md). sTprime and 17 are water-only --
the generator skips cage-guest placement entirely
(``hydrate_generator.py:291-310`` ``if not is_water_only``), so the resulting
``InterfaceStructure`` has ``guest_nmolecules=0`` / ``guest_atom_count=0``.
The interface export alone was verified OK (45-01/45-03: SOL only, grompp
rc=0, no guest ITP staged -- the no-guest gate at ``guest_info.py:250``
``if guest_atom_count <= 0 or guest_nmolecules <= 0: return None, {}``
correctly skips guest ITP staging). BUT the solute/ion inserters' behavior
with ``guest_nmolecules=0`` was UNVERIFIED -- risk: IndexError, KeyError, or
empty ``#include ""`` in .top. This plan VERIFIES no crash. The research
indicates the no-guest gate correctly returns None / {} so no crash is
expected; this test PROVES it.

Water-only lattices have NO cage guests. The .top should have SOL (+ CH4_L
for solute + NA/CL for ion), NO CH4_H, NO ch4_hydrate.itp.

The Custom Molecule tab is SKIPPED (per plan): there is no cage-guest
context for the custom-molecule inserter to interact with -- it inserts in
the water region, same as any lattice. Focus on solute/ion which are the
Pitfall 3 risk.

This MIRRORS ``tests/test_e2e_lattice_cross_tab_gui.py`` (45-04, the 4-GUI-
exporter template) for the GUI half and
``tests/test_e2e_lattice_cross_tab_cli.py`` (45-05, the 3-CLI-branch
template) for the CLI half, but with the water-only-specific assertions:
  - ``guest_nmolecules == 0`` and ``guest_atom_count == 0`` on the interface
    (KEY water-only verification at fixture time).
  - solute/ion inserters MUST NOT crash (the KEY Pitfall 3 assertion --
    ``solute.n_molecules > 0`` and ``ion.na_count > 0 or ion.cl_count > 0``
    prove the inserters ran to completion on the empty-guest interface).
  - NO ``ch4_hydrate.itp`` staged (no cage guest -> the no-guest gate fires).
  - NO ``CH4_H`` / ``GUE`` / ``MOL_H`` in ``[molecules]`` or .gro residues
    (water-only: SOL + solute/ion species only).
  - ``tip4p-ice.itp`` always staged (the water ITP is structural).

Module-scoped fixture amortizes the GenIce2 + slab + inserter calls (~1-5s
per lattice) across all parametrized export cases (per AGENTS.md testing
guidance). Pattern 2 (fresh ``assemble_slab`` per inserter) is used because
the ion inserter mutates ``iface.molecule_index`` (``ion_inserter.py:259``)
-- giving each inserter its OWN fresh slab (deterministic with ``seed=42``)
prevents cross-contamination of the solute exporter's
``interface_structure.molecule_index`` reference.

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter tests (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under
offscreen -> the exporter returns ``False`` without writing files. Inline
patching of ``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED
(Pattern 3 from 45-RESEARCH.md; the ``mock_save_dialog`` fixture from
``tests/test_output/conftest.py`` is directory-scoped and NOT available to
root-level test files).

``gmx`` is on PATH so grompp runs. The ``@gmx_skipif`` decorator skips the
whole test when ``gmx`` is absent; the helper ALSO guards the grompp call
with ``shutil.which("gmx")`` so file-consistency + guest-residue asserts run
whenever the test runs (belt-and-suspenders with ``@gmx_skipif``).
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
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import (  # noqa: E402
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
)
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _insert_solutes,
    _insert_ions,
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# -- The 2 water-only lattice types under test --------------------------------
# sTprime (Ice XVI) and 17 (Ice XVII) have ``is_water_only=True`` in
# HYDRATE_LATTICES -> the generator skips cage-guest placement entirely
# (hydrate_generator.py:291-310 ``if not is_water_only``). guest_type="ch4"
# is IGNORED for water-only lattices (the generator water-only skip).

_WATER_ONLY_LATTICES = ("sTprime", "17")


# -- Module-scoped fixture: build full chains for BOTH water-only lattices -----


@pytest.fixture(scope="module")
def water_only_chains():
    """Module-scoped: build the full chain (hydrate -> fresh iface per inserter
    -> solute / ion) for EACH of the 2 water-only lattice types (sTprime, 17)
    ONCE, amortizing the GenIce2 + assemble_slab calls (~1-5s each) across all
    parametrized export cases.

    Pattern 2 (fresh ``assemble_slab`` per inserter): the ion inserter mutates
    ``iface.molecule_index`` (``ion_inserter.py:259``). Each inserter gets its
    OWN fresh ``assemble_slab`` (deterministic with ``seed=42``) so the solute
    exporter's ``interface_structure.molecule_index`` reference is NOT
    cross-contaminated by the ion inserter's mutation.

    KEY water-only verification (Pitfall 3 -- the whole point of this plan):
      - ``hydrate.guest_count == 0`` (water-only -- no guests placed).
      - ``iface.guest_nmolecules == 0`` and ``iface.guest_atom_count == 0``
        (water-only through slab).
      - ``solute = _insert_solutes(iface_solute, ...)`` MUST NOT CRASH on
        ``guest_nmolecules=0``. Assert ``solute.n_molecules > 0`` (solute
        inserted in the water region -- the solute inserter places in the
        water region, independent of cage guests).
      - ``ion = _insert_ions(iface_ion, ...)`` MUST NOT CRASH on
        ``guest_nmolecules=0``. Assert ``ion.na_count > 0 or ion.cl_count > 0``
        (ions inserted in the water region).

    The Custom Molecule tab is SKIPPED (per plan): there is no cage-guest
    context for the custom-molecule inserter to interact with -- it inserts
    in the water region, same as any lattice. Focus on solute/ion which are
    the Pitfall 3 risk.

    Returns ``dict {lattice_type: SimpleNamespace}`` where each namespace
    carries ``hydrate`` (with ``.config`` -- the water-only ``HydrateConfig``
    with ``guest_type="ch4"`` IGNORED by the generator's water-only skip),
    ``iface`` (for the interface exporter), ``solute``, ``ion`` (the 3
    downstream structures the GUI exporters + CLI branches consume), and
    ``config``.
    """
    chains = {}
    for lattice_type in _WATER_ONLY_LATTICES:
        gen = HydrateStructureGenerator()
        # guest_type="ch4" is IGNORED for water-only lattices (the generator
        # water-only skip at hydrate_generator.py:291-310). It is still
        # required by HydrateConfig.__post_init__ (guest_type is a required
        # field; the water-only skip is downstream of config validation).
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        hydrate = gen.generate(config)
        # Water-only -- no cage guests placed (the generator skip).
        assert hydrate.guest_count == 0, (
            f"{lattice_type}: water-only lattice should have guest_count==0 "
            f"(got {hydrate.guest_count}) -- the generator water-only skip "
            f"(hydrate_generator.py:291-310) should have prevented guest "
            f"placement"
        )
        candidate = hydrate.to_candidate()

        # Fresh assemble_slab per inserter (Pattern 2 -- ion mutates
        # iface.molecule_index). Deterministic with seed=42 so all 3 slabs
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
        # KEY water-only assertion (Pitfall 3): the slab interface must
        # carry ZERO cage guests for BOTH the interface exporter and the
        # solute/ion inserters' source interfaces.
        assert iface.guest_nmolecules == 0, (
            f"{lattice_type}: water-only interface slab should have "
            f"guest_nmolecules==0 (got {iface.guest_nmolecules}) -- the "
            f"water-only lattice must carry no cage guests through the slab"
        )
        assert iface.guest_atom_count == 0, (
            f"{lattice_type}: water-only interface slab should have "
            f"guest_atom_count==0 (got {iface.guest_atom_count})"
        )
        assert iface_solute.guest_nmolecules == 0, (
            f"{lattice_type}: water-only solute-source slab should have "
            f"guest_nmolecules==0"
        )
        assert iface_solute.guest_atom_count == 0, (
            f"{lattice_type}: water-only solute-source slab should have "
            f"guest_atom_count==0"
        )
        assert iface_ion.guest_nmolecules == 0, (
            f"{lattice_type}: water-only ion-source slab should have "
            f"guest_nmolecules==0"
        )
        assert iface_ion.guest_atom_count == 0, (
            f"{lattice_type}: water-only ion-source slab should have "
            f"guest_atom_count==0"
        )

        # KEY Pitfall 3 assertion: solute inserter MUST NOT CRASH on
        # guest_nmolecules=0. The solute inserter places CH4 molecules in
        # the water region (independent of cage guests), so it should still
        # place solutes. Assert > 0 (NOT exact -- counts vary by lattice/
        # version, Pitfall 5).
        solute = _insert_solutes(
            iface_solute, solute_type="CH4", concentration=0.3
        )
        assert solute.n_molecules > 0, (
            f"{lattice_type}: solute inserter should place CH4 molecules in "
            f"the water region even with guest_nmolecules=0 (Pitfall 3 -- "
            f"solute insertion is in the water region, independent of cage "
            f"guests)"
        )

        # KEY Pitfall 3 assertion: ion inserter MUST NOT CRASH on
        # guest_nmolecules=0. The ion inserter replaces water molecules with
        # Na+/Cl- in the water region (independent of cage guests), so it
        # should still place ions. Assert > 0 (NOT exact).
        ion = _insert_ions(iface_ion, concentration=0.15)
        assert (ion.na_count > 0 or ion.cl_count > 0), (
            f"{lattice_type}: ion inserter should place Na+ / Cl- ions in "
            f"the water region even with guest_nmolecules=0 (Pitfall 3 -- "
            f"ion replacement is in the water region, independent of cage "
            f"guests)"
        )

        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            solute=solute,
            ion=ion,
            config=config,
        )
    yield chains


# -- Shared water-only export assertion helper --------------------------------


def _assert_water_only_export(
    ws, gro_name, top_name, extra_mols=None, extra_itp=None
):
    """Common assertions for a water-only export through one of the 3 GUI
    exporters or 3 CLI branches: files written, NO cage-guest ITP staged, SOL
    (+ extras) referenced, file consistency, and ``gmx grompp`` rc==0 when
    ``gmx`` is on PATH.

    Water-only lattices (sTprime, 17) have NO cage guests. The .top should
    have SOL (+ CH4_L for solute + NA/CL for ion), NO CH4_H, NO
    ch4_hydrate.itp. The no-guest gate (``guest_info.py:250`` for GUI /
    ``itp_helpers.py`` ``if guest_atom_count > 0`` for CLI) correctly skips
    guest ITP staging for the ``guest_atom_count=0`` water-only interface.

    Asserts (per plan):
      - Files exist (``.gro``, ``.top``).
      - ``SOL`` in ``[molecules]`` AND in .gro residues.
      - NO guest residue: ``CH4_H`` NOT in mols, ``GUE`` NOT in mols /
        residues (no cage guest -> no guest residue should appear).
      - NO ``ch4_hydrate.itp`` in ws (no cage guest -> the no-guest gate
        fires -> no guest ITP staged; only water + solute/ion ITPs).
      - ``tip4p-ice.itp`` exists (the water ITP is structural, always staged).
      - If ``extra_mols``: assert each present (e.g. ``CH4_L`` for solute,
        ``NA`` / ``CL`` for ion).
      - If ``extra_itp``: assert each exists (e.g. ``ch4_liquid.itp``,
        ``ion.itp``).
      - ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (always
        run -- catches ITP-missing + GRO/TOP mismatch).
      - ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    Does NOT assert exact solute/ion counts (Pitfall 5 -- counts vary by
    lattice/version); does NOT assert atom-number exactness in the .gro
    header (Pitfall 4 -- GRO wraps at 100,000; ``assert_gro_top_consistent``
    counts LINES, not the header).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
        extra_mols: Extra molecule names expected in ``[molecules]`` + ``.gro``
            residues beyond SOL (e.g. ``["CH4_L"]``, ``["NA", "CL"]``).
        extra_itp: Extra ITP filenames expected to be staged beyond
            ``tip4p-ice.itp`` (e.g. ``["ch4_liquid.itp"]``, ``["ion.itp"]``).
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the exporter / CLI branch.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # tip4p-ice.itp is structural -- always staged (the water ITP).
    assert (ws / "tip4p-ice.itp").exists(), (
        f"tip4p-ice.itp not staged in {ws} -- the water ITP is structural "
        f"and must always be staged"
    )

    # NO ch4_hydrate.itp staged (water-only -> no cage guest -> the no-guest
    # gate fires -> no guest ITP staged). This is the KEY water-only
    # assertion: a cage-guest ITP leaking into a water-only export would
    # indicate the no-guest gate (guest_info.py:250 / itp_helpers.py
    # ``if guest_atom_count > 0``) is broken.
    assert not (ws / "ch4_hydrate.itp").exists(), (
        f"ch4_hydrate.itp staged in {ws} for a water-only lattice -- the "
        f"no-guest gate (guest_info.py:250 / itp_helpers.py) should have "
        f"prevented cage-guest ITP staging for guest_atom_count=0"
    )

    # .top [molecules] contains SOL (+ extras); NO CH4_H / GUE / MOL_H.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, (
        f"SOL not in [molecules] (water-only should have SOL): {mols}"
    )
    assert "CH4_H" not in mols, (
        f"CH4_H in [molecules] (cage-guest residue leaked into water-only "
        f"export): {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE in [molecules] (custom_guest_info fallback leaked into "
        f"water-only export): {mols}"
    )
    assert "MOL_H" not in mols, (
        f"MOL_H in [molecules] (custom-guest path leaked into water-only "
        f"export): {mols}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in mols, (
                f"expected {mol} in [molecules] (water-only + {mol}): {mols}"
            )

    # .gro residues contain SOL (+ extras); NO CH4_H / GUE / MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res, (
        f"SOL not in .gro residues (water-only should have SOL): {gro_res}"
    )
    assert "CH4_H" not in gro_res, (
        f"CH4_H in .gro residues (cage-guest residue leaked into water-only "
        f"export): {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE in .gro residues (custom_guest_info fallback leaked into "
        f"water-only export): {gro_res}"
    )
    assert "MOL_H" not in gro_res, (
        f"MOL_H in .gro residues (custom-guest path leaked into water-only "
        f"export): {gro_res}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in gro_res, (
                f"expected {mol} in .gro residues (water-only + {mol}): "
                f"{gro_res}"
            )

    # Extra ITPs (solute liquid / ion) staged if expected.
    if extra_itp:
        for itp in extra_itp:
            assert (ws / itp).exists(), (
                f"{itp} not staged in {ws} for the water-only export"
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
            f"gmx grompp failed (water-only, {gro_name}):\n{stderr}"
        )


# -- Parametrized GUI full cross-tab (3 exporters) + grompp test --------------


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_WATER_ONLY_LATTICES))
def test_water_only_cross_tab_gui_grompp(
    tmp_path, water_only_chains, lattice_type
):
    """gmx grompp exits 0 on the FULL GUI cross-tab chain (Interface -> Solute
    -> Ion -> Export) for each of the 2 water-only lattice types (sTprime /
    17), all with ``guest_type="ch4"`` (IGNORED by the generator water-only
    skip) and ``hydrate_config=None`` (the built-in default -> the no-guest
    gate fires -> no cage-guest ITP staged).

    KEY Pitfall 3 assertion: the solute/ion inserters MUST NOT CRASH on
    ``guest_nmolecules=0``. The module-scoped fixture already proved this at
    fixture-build time (``solute.n_molecules > 0`` and
    ``ion.na_count > 0 or ion.cl_count > 0``); this test proves the EXPORT
    step also succeeds on the resulting structures.

    For each of the 3 GUI exporters (interface / solute / ion -- NO custom,
    since there's no cage guest to customize), the test:
      1. Mocks ``QFileDialog.getSaveFileName`` (REQUIRED -- under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> the
         exporter returns ``False`` without writing files) + ``QMessageBox``
         (Pattern 3 from 45-RESEARCH.md).
      2. Calls the exporter method with ``hydrate_config=None`` (the
         built-in default -- NO custom config -> the no-guest gate fires ->
         no cage-guest ITP staged, SOL (+ solute/ion) only).
      3. Asserts the exporter returned ``True``.
      4. ``_assert_water_only_export(...)``: SOL (+ extras), NO CH4_H /
         GUE / MOL_H, NO ch4_hydrate.itp, tip4p-ice.itp staged, file
         consistency passes, and ``gmx grompp`` exits 0.

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2x rcoulomb=2.0 nm --
    grompp PBC rule). The 1x1x1 supercell is sufficient for these 2
    non-triclinic water-only lattices (Pitfall 1 only affects the triclinic
    filled ices c0te/c1te, which are blocked and covered by separate plans).

    The Custom Molecule tab is SKIPPED (per plan): there is no cage-guest
    context for the custom-molecule inserter to interact with -- it inserts
    in the water region, same as any lattice. Focus on solute/ion which are
    the Pitfall 3 risk.
    """
    chain = water_only_chains[lattice_type]

    # -- 1. Interface exporter (Interface tab) -------------------------------
    # Water-only: SOL only, no cage guest. tip4p-ice.itp staged, NO
    # ch4_hydrate.itp.
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
            f"export_interface_gromacs returned False for {lattice_type} "
            f"(water-only) -- QFileDialog mock may not have been picked up, "
            f"or staging raised"
        )
    _assert_water_only_export(ws, "output.gro", "output.top")

    # -- 2. Solute exporter (Solute tab) -------------------------------------
    # Water-only + solute: SOL + CH4_L, no cage guest. tip4p-ice.itp +
    # ch4_liquid.itp staged, NO ch4_hydrate.itp.
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
            f"export_solute_gromacs returned False for {lattice_type} "
            f"(water-only) -- QFileDialog mock may not have been picked up, "
            f"or staging raised"
        )
    _assert_water_only_export(
        ws, "output.gro", "output.top",
        extra_mols=["CH4_L"], extra_itp=["ch4_liquid.itp"],
    )

    # -- 3. Ion exporter (Ion tab) -------------------------------------------
    # Water-only + ion: SOL + NA/CL, no cage guest. tip4p-ice.itp + ion.itp
    # staged, NO ch4_hydrate.itp.
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
            f"export_ion_gromacs returned False for {lattice_type} "
            f"(water-only) -- QFileDialog mock may not have been picked up, "
            f"or staging raised"
        )
    # Only assert the ion species actually placed (Na+ and/or Cl-).
    ion_extras = []
    if chain.ion.na_count > 0:
        ion_extras.append("NA")
    if chain.ion.cl_count > 0:
        ion_extras.append("CL")
    _assert_water_only_export(
        ws, "output.gro", "output.top",
        extra_mols=ion_extras, extra_itp=["ion.itp"],
    )


# -- CLI export-step-direct helpers (copied from the 45-05 template) ----------


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and a single downstream structure set so ``_run_export_step``'s
    priority selection (ion > solute > custom > interface > hydrate > ice)
    picks that branch. All other ``_*_result`` stay at their ``__init__``
    default of ``None``.

    Mirrors the helper in ``tests/test_e2e_lattice_cross_tab_cli.py``
    (the 45-05 template, lines 207-221).
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


# -- Parametrized CLI full cross-tab (3 branches) + grompp test --------------


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_WATER_ONLY_LATTICES))
def test_water_only_cross_tab_cli_grompp(
    tmp_path, water_only_chains, lattice_type
):
    """gmx grompp exits 0 on the FULL CLI cross-tab chain (Interface -> Solute
    -> Ion -> Export) for each of the 2 water-only lattice types (sTprime /
    17), all with ``guest_type="ch4"`` (IGNORED by the generator water-only
    skip).

    KEY Pitfall 3 assertion: the solute/ion inserters MUST NOT CRASH on
    ``guest_nmolecules=0``. The module-scoped fixture already proved this at
    fixture-build time; this test proves the CLI EXPORT step also succeeds
    on the resulting structures.

    For each of the 3 CLI export branches (interface / solute / ion), the
    test:
      1. Constructs a ``CLIPipeline`` with ``_hydrate_result`` set to the
         water-only hydrate (carries ``.config`` -- a ``HydrateConfig`` with
         ``guest_type="ch4"`` IGNORED by the generator water-only skip) and
         the downstream structure set on the target ``_*_result`` attribute.
      2. Calls ``_run_export_step()`` directly (the export-step-direct
         approach from the 45-05 template). ``_run_export_step`` reads
         ``hydrate_config = getattr(self._hydrate_result, "config", None)`` ->
         the water-only ``HydrateConfig``. ``_build_custom_guest_info(config)``
         returns ``None`` for built-in ch4 -> ``custom_guest_info=None``.
         ``copy_itp_files_for_structure`` checks
         ``if guest_atom_count > 0`` before staging a cage-guest ITP -> for
         water-only (``guest_atom_count=0``) it skips the cage-guest ITP,
         staging only tip4p-ice.itp (+ solute/ion ITPs).
      3. ``_assert_water_only_export(...)`` asserts SOL (+ extras), NO CH4_H
         / GUE / MOL_H, NO ch4_hydrate.itp, tip4p-ice.itp staged, file
         consistency passes, and ``gmx grompp`` exits 0.

    No ``QFileDialog`` mocking is needed -- the CLI pipeline writes files
    directly to ``self._output_dir`` (no dialog).
    """
    chain = water_only_chains[lattice_type]
    hydrate = chain.hydrate

    # 1) Interface export (SOL only; tip4p-ice.itp). Water-only -> no cage
    #    guest -> the no-guest gate fires -> NO ch4_hydrate.itp staged.
    ws = tmp_path / "interface"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(ws, hydrate, "_interface_result", chain.iface)
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the interface branch "
        f"(water-only {lattice_type})"
    )
    _assert_water_only_export(ws, "interface.gro", "interface.top")

    # 2) Solute export (SOL + CH4_L; tip4p-ice.itp + ch4_liquid.itp). Built
    #    from the interface (no cage guest -> no ch4_hydrate.itp).
    ws = tmp_path / "solute"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(ws, hydrate, "_solute_result", chain.solute)
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the solute branch "
        f"(water-only {lattice_type})"
    )
    _assert_water_only_export(
        ws, "solute.gro", "solute.top",
        extra_mols=["CH4_L"], extra_itp=["ch4_liquid.itp"],
    )

    # 3) Ion export (SOL + NA/CL; tip4p-ice.itp + ion.itp). Built from the
    #    interface (no cage guest -> no ch4_hydrate.itp). Only assert the
    #    ion species actually placed (Na+ and/or Cl-).
    ws = tmp_path / "ion"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(ws, hydrate, "_ion_result", chain.ion)
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the ion branch "
        f"(water-only {lattice_type})"
    )
    ion_extras = []
    if chain.ion.na_count > 0:
        ion_extras.append("NA")
    if chain.ion.cl_count > 0:
        ion_extras.append("CL")
    _assert_water_only_export(
        ws, "ion.gro", "ion.top",
        extra_mols=ion_extras, extra_itp=["ion.itp"],
    )
