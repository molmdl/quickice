"""E2E sH full cross-tab (GUI 4 exporters + CLI 3 branches) + grompp.

Plan 45-06 (Wave 2). Proves that sH (triclinic-but-allowed, ~4480 guests
through the 3x3x8 nm slab) passes ``gmx grompp`` (rc=0) through the FULL GUI
+ CLI tab chain.

Purpose: sH is separated from the fast lattices (45-04/05, which cover
sII/c2te/ice1hte/16) because it is SLOW -- the sH unit cell is small, so the
3x3x8 nm slab tiles it many times, producing ~4480 cage guests + ~50k
waters (~54k atoms). Solute / ion insertion + grompp on this large system
takes ~10-30s per test (Pitfall 5 from 45-RESEARCH.md). This plan tests BOTH
the GUI (4 exporters: Interface / Solute / Custom Molecule / Ion) AND the
CLI (3 branches: interface / solute / ion) full chains for sH only, sharing
a module-scoped fixture that amortizes the expensive GenIce2 sH generation
+ 4x ``assemble_slab`` + 4 inserters across both tests.

This file COMBINES:
  - The GUI pattern from ``tests/test_e2e_builtin_cross_tab_regression.py``
    (the 44.1-22 template, also used by 45-04): Pattern 2 (fresh
    ``assemble_slab`` per inserter) + Pattern 3 (inline ``QFileDialog`` +
    ``QMessageBox`` mock) + ``hydrate_config=None`` (built-in ch4 path).
  - The CLI pattern from ``tests/test_e2e_custom_guest_cross_tab_cli.py``
    (the 44.1-20 template, also used by 45-05): Pattern 4
    (``_make_cli_pipeline`` + ``_run_export_step`` direct) + ion built from
    SOLUTE (real CLI workflow order via ``_insert_ions_from_solute``).

sH uses the BUILT-IN ``guest_type="ch4"`` (NOT custom), so the built-in path
(``hydrate_config=None`` for GUI / ``hydrate.config`` for CLI) stages the
bundled ``ch4_hydrate.itp`` and references ``CH4_H`` (NOT ``GUE`` or
``MOL_H`` -- those would indicate the custom-guest / fallback path leaked).

Pitfalls avoided (45-RESEARCH.md):
  - Pitfall 4 (GRO atom-number wrap at 100,000): NOT asserted --
    ``assert_gro_top_consistent`` counts atom LINES, not the header atom-
    count field, so it is robust to the 100,000 wrap (cosmetic; grompp
    still rc=0). sH interface ~54k atoms is under 100k but the wrap is
    irrelevant either way.
  - Pitfall 5 (sH huge guest count): do NOT assert exact guest/solute/ion
    counts -- assert ``> 0`` only. sH produces ~4480 guests through the
    3x3x8 slab (version-dependent). Generous ``--timeout=300`` is REQUIRED.
  - Ion inserter mutates ``iface.molecule_index`` (``ion_inserter.py:259``):
    fresh ``assemble_slab`` per inserter (Pattern 2) prevents cross-
    contamination of the solute / custom exporters' interface references.

``gmx`` is on PATH so grompp runs. ``@gmx_skipif`` skips the whole test when
``gmx`` is absent; the helper ALSO guards the grompp call with
``shutil.which("gmx")`` so file-consistency + guest-residue asserts run
whenever the test runs (belt-and-suspenders).

Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2*rcoulomb=2.0 nm -- grompp
PBC rule). The 1x1x1 supercell is sufficient for sH: sH is triclinic BUT
explicitly allowed (NOT in ``TRICLINIC_HYDRATE_PHASES`` which only blocks
c0te/c1te), and the 3x3x8 slab box satisfies the cut-off rule.
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
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ── Module-scoped fixture: build the sH full chain ONCE ──────────────────────


@pytest.fixture(scope="module")
def sH_chain():
    """Module-scoped: build the FULL sH chain (hydrate -> 4x fresh slab ->
    solute / custom / ion-from-interface / ion-from-solute) ONCE, amortizing
    the SLOW GenIce2 sH generation + 4x ``assemble_slab`` + 4 inserters
    across BOTH the GUI (4 exporters) and CLI (3 branches) tests.

    sH is SLOW (Pitfall 5): the small sH unit cell tiles many times in the
    3x3x8 nm slab, producing ~4480 cage guests + ~50k waters (~54k atoms).
    The module fixture builds this ONCE; each test then just exports +
    grompps the pre-built structures (fast relative to the fixture).

    Pattern 2 (fresh ``assemble_slab`` per inserter): the ion inserter
    mutates ``iface.molecule_index`` (``ion_inserter.py:259``). Each inserter
    gets its OWN fresh ``assemble_slab`` (deterministic with ``seed=42``) so
    the solute / custom exporters' ``interface_structure.molecule_index``
    reference is NOT cross-contaminated by the ion inserter's mutation.
    Mirrors ``test_e2e_lattice_cross_tab_gui.py`` (45-04) lines 168-215.

    The custom-molecule inserter uses a RENAMED copy of the bundled ethanol
    data (``cmet.gro`` / ``cmet.itp`` with ``[ moleculetype ]`` renamed
    ``etoh`` -> ``MOL``). This avoids a PRE-EXISTING ``.gro``/``.top``
    moleculetype-name mismatch (the registry default is ``MOL`` but the raw
    ``etoh.itp`` moleculetype is ``etoh`` -> ``assert_gro_top_consistent``
    would fail on the name mismatch). The rename is a test-setup detail; it
    does NOT affect the sH cross-tab behavior being tested. For the built-in
    ch4 cage guest, the cage-guest ITP (``ch4_hydrate.itp``) does NOT collide
    with the custom-molecule ITP (``cmet.itp``) -- no filename collision.
    Copied from ``test_e2e_builtin_cross_tab_regression.py:109-124``.

    Returns a ``SimpleNamespace`` carrying:
      - ``hydrate`` (with ``.config`` -- the built-in ``HydrateConfig`` the
        CLI reads via ``self._hydrate_result.config``; ``_build_custom_guest_info``
        returns ``None`` for built-in ch4 -> built-in path).
      - ``iface`` (for the GUI Interface exporter + CLI interface branch).
      - ``solute`` (for the GUI Solute exporter + CLI solute branch).
      - ``custom`` (for the GUI Custom Molecule exporter only).
      - ``ion`` (GUI ion, built from a FRESH interface -- like the 44.1-22
        / 45-04 built-in template; for the GUI Ion exporter).
      - ``ion_cli`` (CLI ion, built from the SOLUTE via
        ``_insert_ions_from_solute`` -- real CLI workflow order; for the CLI
        ion branch).
      - ``config`` (the ``HydrateConfig`` used).

    All 4 fresh slabs carry cage guests (assert ``> 0``, NOT exact -- Pitfall
    5: sH has ~4480, version-dependent). The fixture cleans up the cmet temp
    dir on teardown.
    """
    # Build renamed cmet.gro / cmet.itp in a module-level temp dir (the
    # LIQUID custom molecule for the Custom Molecule tab, NOT the cage
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

    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",  # BUILT-IN ch4 (NOT custom) -> ch4_hydrate.itp
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()

    # Fresh assemble_slab per inserter (Pattern 2 -- ion mutates
    # iface.molecule_index). Deterministic with seed=42 so all 4 slabs are
    # byte-identical until an inserter mutates its own copy.
    _slab_cfg = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    iface = assemble_slab(candidate, _slab_cfg)
    iface_solute = assemble_slab(candidate, _slab_cfg)
    iface_custom = assemble_slab(candidate, _slab_cfg)
    iface_ion = assemble_slab(candidate, _slab_cfg)

    # sH produces a LARGE guest count (~4480 through the 3x3x8 slab) -- do
    # NOT assert exact count (version-dependent); assert > 0 only (Pitfall 5).
    assert iface.guest_nmolecules > 0, (
        "sH interface slab should have built-in ch4 cage guests"
    )
    assert iface_solute.guest_nmolecules > 0, (
        "sH solute-source slab should have built-in ch4 cage guests"
    )
    assert iface_custom.guest_nmolecules > 0, (
        "sH custom-source slab should have built-in ch4 cage guests"
    )
    assert iface_ion.guest_nmolecules > 0, (
        "sH ion-source slab should have built-in ch4 cage guests"
    )

    # Run the inserters to produce the derived structures. Each inserter
    # returns a NEW structure, never mutating its input iface (V-17) -- but
    # the ion inserter DOES mutate the interface_structure.molecule_index it
    # RECEIVES (in-place), which is why each inserter gets its OWN fresh slab
    # (Pattern 2).
    solute = _insert_solutes(
        iface_solute, solute_type="CH4", concentration=0.3
    )
    assert solute.n_molecules > 0, (
        "sH: solute inserter should place CH4 molecules in the water region"
    )
    assert solute.interface_structure is not None, (
        "sH: SoluteStructure.interface_structure must be populated for ion "
        "chaining"
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

    # GUI ion: built from a FRESH interface (like the 44.1-22 / 45-04
    # built-in template). The ion inserter mutates iface_ion.molecule_index
    # (a separate fresh slab, so iface / iface_solute / iface_custom are
    # NOT contaminated).
    ion_from_iface = _insert_ions(iface_ion, concentration=0.15)
    assert (ion_from_iface.na_count > 0 or ion_from_iface.cl_count > 0), (
        "sH: GUI ion inserter should place Na+ / Cl- ions in the water region"
    )
    # IonStructure (types.py) has NO interface_structure field -- it carries
    # its own guest_atom_count/guest_nmolecules propagated by IonInserter
    # from the source interface (44.1-15). Required for the built-in guest
    # staging block (copy_itp_files_for_structure reads these to stage
    # ch4_hydrate.itp).
    assert ion_from_iface.guest_atom_count > 0, (
        "sH: GUI IonStructure.guest_atom_count must be propagated from the "
        "source interface for the built-in guest staging block"
    )
    assert ion_from_iface.guest_nmolecules > 0, (
        "sH: GUI IonStructure.guest_nmolecules must be propagated from the "
        "source interface for the built-in guest staging block"
    )

    # CLI ion: built from the SOLUTE (real CLI workflow order via
    # _insert_ions_from_solute -> _solute_to_ion_source, NOT from the
    # interface directly). _solute_to_ion_source propagates solute
    # attributes onto solute.interface_structure (duck-typing) so
    # IonInserter can access them. This is the integration aspect the
    # per-branch CLI tests don't cover (mirrors 44.1-20 / 45-05).
    ion_from_solute = _insert_ions_from_solute(solute, concentration=0.15)
    assert (ion_from_solute.na_count > 0 or ion_from_solute.cl_count > 0), (
        "sH: CLI ion inserter should place Na+ / Cl- ions in the water region"
    )
    assert ion_from_solute.guest_atom_count > 0, (
        "sH: CLI IonStructure.guest_atom_count must be propagated from the "
        "source interface for the built-in guest staging block"
    )
    assert ion_from_solute.guest_nmolecules > 0, (
        "sH: CLI IonStructure.guest_nmolecules must be propagated from the "
        "source interface for the built-in guest staging block"
    )

    yield SimpleNamespace(
        hydrate=hydrate,
        iface=iface,
        solute=solute,
        custom=custom,
        ion=ion_from_iface,        # GUI ion (from fresh interface)
        ion_cli=ion_from_solute,    # CLI ion (from solute, real workflow)
        config=config,
    )
    shutil.rmtree(cmet_dir, ignore_errors=True)


# ── Shared assertion helper --------------------------------------------------


def _assert_sH_export(ws, gro_name, top_name, extra_mols=None, extra_itp=None):
    """Common assertions for an sH export through one GUI exporter or CLI
    branch: files written, built-in guest ITP staged + referenced, file
    consistency, and ``gmx grompp`` rc==0 when ``gmx`` is on PATH.

    sH uses the built-in ch4 guest, so the built-in path
    (``hydrate_config=None`` for GUI / ``hydrate.config`` for CLI) stages
    ``ch4_hydrate.itp`` and the ``.top`` references ``CH4_H`` (NOT ``GUE`` or
    ``MOL_H`` -- those would indicate the custom-guest / fallback path
    leaked).

    Asserts (per plan):
      - ``CH4_H`` in ``[molecules]`` AND in .gro residues.
      - ``ch4_hydrate.itp`` staged in the workspace (defines ``CH4_H``,
        NOT ``MOL_H``).
      - ``GUE`` / ``MOL_H`` NOT in mols / residues (built-in path).
      - ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (always
        run -- catches ITP-missing + GRO/TOP mismatch).
      - ``gmx grompp`` rc==0 when ``gmx`` is on PATH.
      - ``extra_mols`` (e.g. ``["CH4_L"]``, ``["NA", "CL"]``) in mols +
        .gro residues when provided (CLI per-branch).
      - ``extra_itp`` (e.g. ``["ch4_liquid.itp"]``, ``["ion.itp"]``) staged
        when provided (CLI per-branch).

    Does NOT assert exact guest/solute/ion counts (Pitfall 5 -- sH has ~4480
    guests, version-dependent); does NOT assert atom-number exactness in the
    .gro header (Pitfall 4 -- GRO wraps at 100,000; assert_gro_top_consistent
    counts LINES, not the header).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
        extra_mols: Optional extra molecule names expected in
            ``[molecules]`` + ``.gro`` residues beyond SOL + CH4_H
            (e.g. ``["CH4_L"]``, ``["NA", "CL"]``). Used by the CLI test.
        extra_itp: Optional extra ITP filenames expected to be staged beyond
            tip4p-ice.itp + ch4_hydrate.itp (e.g. ``["ch4_liquid.itp"]``,
            ``["ion.itp"]``). Used by the CLI test.
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the exporter / CLI branch.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # Built-in guest ITP staged (NOT a custom ITP). The GUI exporter's
    # _stage_hydrate_guest_itps (hydrate_config=None built-in path) / the
    # CLI copy_itp_files_for_structure (hydrate_config=built-in) copies the
    # bundled pre-transformed ch4_hydrate.itp.
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"sH: built-in guest ITP ch4_hydrate.itp not staged in {ws} -- "
        f"regression: the built-in path must stage ch4_hydrate.itp"
    )
    staged_itp = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_itp, (
        "sH: staged ch4_hydrate.itp missing moleculetype CH4_H -- the "
        "built-in ITP must define CH4_H"
    )
    assert "MOL_H" not in staged_itp, (
        "sH: MOL_H (custom-guest moleculetype) found in staged "
        "ch4_hydrate.itp -- regression: the built-in path must NOT produce "
        "MOL_H"
    )

    # Extra ITP files staged (CLI per-branch: ch4_liquid.itp / ion.itp).
    if extra_itp:
        for itp in extra_itp:
            assert (ws / itp).exists(), (
                f"sH: {itp} not staged in {ws} for this branch"
            )

    # .top [molecules] references the built-in residue name (NOT GUE/MOL_H).
    mols = parse_top_molecules(str(top_path))
    assert "CH4_H" in mols, f"sH: CH4_H not in [molecules]: {mols}"
    assert mols["CH4_H"] > 0, (
        f"sH: CH4_H molecule count not > 0: {mols['CH4_H']}"
    )
    assert "GUE" not in mols, (
        f"sH: GUE in [molecules] (fallback leaked): {mols}"
    )
    assert "MOL_H" not in mols, (
        f"sH: MOL_H in [molecules] (custom-guest path leaked): {mols}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in mols, (
                f"sH: expected {mol} in [molecules]: {mols}"
            )

    # .gro residues contain the built-in residue name (NOT GUE/MOL_H).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res, f"sH: CH4_H not in .gro residues: {gro_res}"
    assert "GUE" not in gro_res, (
        f"sH: GUE in .gro residues (fallback leaked): {gro_res}"
    )
    assert "MOL_H" not in gro_res, (
        f"sH: MOL_H in .gro residues (custom-guest path leaked): {gro_res}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in gro_res, (
                f"sH: expected {mol} in .gro residues: {gro_res}"
            )

    # File consistency (always runs -- catches ITP-missing + GRO/TOP
    # mismatch). assert_gro_top_consistent counts atom LINES, not the .gro
    # header atom-count field, so it is robust to the GRO 100,000
    # atom-number wrap (Pitfall 4 -- cosmetic, grompp still rc=0).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH -- file consistency always runs).
    # Guarded by shutil.which("gmx") so file-consistency + guest-residue
    # asserts run whenever the test runs (belt-and-suspenders with
    # @gmx_skipif on the test).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(ws, gro_file=gro_name, top_file=top_name)
        assert rc == 0, (
            f"sH: gmx grompp failed ({gro_name}):\n{stderr}"
        )


# ── CLI export-step-direct helper (copied from the 44.1-20 / 45-05 template) ─


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and a single downstream structure set so ``_run_export_step``'s
    priority selection (ion > solute > custom > interface > hydrate > ice)
    picks that branch. All other ``_*_result`` stay at their ``__init__``
    default of ``None``.

    Mirrors the helper in ``tests/test_e2e_custom_guest_cross_tab_cli.py``
    (the 44.1-20 template, lines 155-166) and ``test_e2e_lattice_cross_tab_cli.py``
    (45-05, lines 207-221).
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


# ── GUI full cross-tab (4 exporters) + grompp test ───────────────────────────


@gmx_skipif
def test_sH_cross_tab_gui_grompp(tmp_path, sH_chain):
    """gmx grompp exits 0 on the FULL GUI cross-tab chain (Interface -> Solute
    -> Custom Molecule -> Ion -> Export) for sH with built-in
    ``guest_type="ch4"`` and ``hydrate_config=None`` (the built-in ch4 path).

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
      4. ``_assert_sH_export(...)``: built-in guest ITP staged + referenced
         (CH4_H, ch4_hydrate.itp), NO GUE/MOL_H leak, file consistency
         passes, and ``gmx grompp`` exits 0.
      5. Asserts the per-exporter ITP is staged (ch4_liquid.itp for solute,
         cmet.itp for custom-molecule, ion.itp for ion).

    MIRRORS ``test_e2e_builtin_cross_tab_regression.py`` (44.1-22) lines
    287-367 and ``test_e2e_lattice_cross_tab_gui.py`` (45-04) lines 406-493,
    swapping the parametrized lattices -> sH only (the single slow lattice).

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2*rcoulomb=2.0 nm --
    grompp PBC rule). sH is triclinic BUT explicitly allowed (NOT in
    ``TRICLINIC_HYDRATE_PHASES``); the 1x1x1 supercell + 3x3x8 slab satisfy
    the cut-off rule.

    Pattern 2 (fresh ``assemble_slab`` per inserter) is applied in the
    module-scoped fixture so the ion inserter's mutation of
    ``iface.molecule_index`` does NOT cross-contaminate the solute / custom
    exporters' interface references.
    """
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
            sH_chain.iface, hydrate_config=None
        )
        assert ok is True, (
            "sH: export_interface_gromacs returned False -- QFileDialog mock "
            "may not have been picked up, or staging raised"
        )
    _assert_sH_export(ws, "output.gro", "output.top")

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
            sH_chain.solute, hydrate_config=None
        )
        assert ok is True, (
            "sH: export_solute_gromacs returned False -- QFileDialog mock "
            "may not have been picked up, or staging raised"
        )
    _assert_sH_export(ws, "output.gro", "output.top")
    # Solute ITP (ch4_liquid.itp) copied by the exporter.
    assert (ws / "ch4_liquid.itp").exists(), (
        "sH: solute ITP (ch4_liquid.itp) not copied by the solute exporter"
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
            sH_chain.custom, hydrate_config=None
        )
        assert ok is True, (
            "sH: export_custom_molecule_gromacs returned False -- QFileDialog "
            "mock may not have been picked up, or staging raised"
        )
    _assert_sH_export(ws, "output.gro", "output.top")
    # Custom-molecule ITP (cmet.itp) copied by the exporter (atomtypes
    # commented).
    assert (ws / "cmet.itp").exists(), (
        "sH: custom molecule ITP (cmet.itp) not copied by the custom exporter"
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
        ok = exporter.export_ion_gromacs(
            sH_chain.ion, hydrate_config=None
        )
        assert ok is True, (
            "sH: export_ion_gromacs returned False -- QFileDialog mock may "
            "not have been picked up, or staging raised"
        )
    _assert_sH_export(ws, "output.gro", "output.top")
    # Ion ITP (ion.itp) written by write_ion_itp.
    assert (ws / "ion.itp").exists(), (
        "sH: ion ITP (ion.itp) not written by write_ion_itp"
    )


# ── CLI full cross-tab (3 branches) + grompp test ────────────────────────────


@gmx_skipif
def test_sH_cross_tab_cli_grompp(tmp_path, sH_chain):
    """gmx grompp exits 0 on the FULL CLI cross-tab chain (Interface -> Solute
    -> Ion -> Export) for sH with built-in ``guest_type="ch4"`` (NOT custom).

    For each of the 3 CLI export branches (interface / solute / ion), the
    test:
      1. Constructs a ``CLIPipeline`` with ``_hydrate_result`` set to the
         built-in sH hydrate (carries ``.config`` -- a built-in
         ``HydrateConfig`` with ``guest_type="ch4"``) and the downstream
         structure set on the target ``_*_result`` attribute.
      2. Calls ``_run_export_step()`` directly (the export-step-direct
         approach from the 44.1-20 template). ``_run_export_step`` reads
         ``hydrate_config = getattr(self._hydrate_result, "config", None)``
         -> the built-in ``HydrateConfig``. ``_build_custom_guest_info(config)``
         returns ``None`` for built-in ch4 -> ``custom_guest_info=None`` ->
         built-in residue name (``CH4_H``) + bundled ``ch4_hydrate.itp``
         staged via ``copy_itp_files_for_structure``, byte-identical to the
         pre-44.1 built-in path.
      3. ``_assert_sH_export(...)`` asserts the built-in guest ITP is staged
         + referenced (``CH4_H``, ``ch4_hydrate.itp``), NO ``GUE`` / ``MOL_H``
         leak, file consistency passes, and ``gmx grompp`` exits 0.

    The ion is built from the SOLUTE (real CLI workflow order via
    ``_insert_ions_from_solute``, NOT from the interface directly) -- the
    integration aspect the per-branch CLI tests don't cover. This proves the
    built-in cage-guest metadata survives the full sH hydrate -> interface ->
    solute -> ion chain so every CLI export step stages ``ch4_hydrate.itp``
    and references ``CH4_H`` in ``[molecules]``.

    MIRRORS ``test_e2e_custom_guest_cross_tab_cli.py`` (44.1-20) lines
    263-298 and ``test_e2e_lattice_cross_tab_cli.py`` (45-05) lines
    353-417, swapping the parametrized lattices -> sH only.

    No ``QFileDialog`` mocking is needed -- the CLI pipeline writes files
    directly to ``self._output_dir`` (no dialog).
    """
    hydrate = sH_chain.hydrate

    # 1) Interface export (SOL + CH4_H; tip4p-ice.itp + ch4_hydrate.itp).
    # _run_export_step writes to self._output_dir / f"{step_name}.gro" but
    # does NOT create the dir (only CLIPipeline.execute() does). The per-
    # branch tests pass tmp_path directly (pytest creates it); our per-step
    # subdirs must be mkdir'd here (mirrors 45-05 _assert_step_output).
    ws = tmp_path / "interface"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(
        ws, hydrate, "_interface_result", sH_chain.iface
    )
    code = pipe._run_export_step()
    assert code == 0, (
        "sH: _run_export_step failed (rc={}) for the interface branch".format(
            code
        )
    )
    _assert_sH_export(ws, "interface.gro", "interface.top")

    # 2) Solute export (SOL + CH4_H + CH4_L; + ch4_liquid.itp).
    ws = tmp_path / "solute"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(
        ws, hydrate, "_solute_result", sH_chain.solute
    )
    code = pipe._run_export_step()
    assert code == 0, (
        "sH: _run_export_step failed (rc={}) for the solute branch".format(
            code
        )
    )
    _assert_sH_export(
        ws, "solute.gro", "solute.top",
        extra_mols=["CH4_L"], extra_itp=["ch4_liquid.itp"],
    )

    # 3) Ion export (SOL + CH4_H + NA/CL; + ion.itp). Built from SOLUTE (real
    #    CLI workflow order via _insert_ions_from_solute, NOT from the
    #    interface directly). Only assert the ion species actually placed
    #    (Na+ and/or Cl-).
    ion_extras = []
    if sH_chain.ion_cli.na_count > 0:
        ion_extras.append("NA")
    if sH_chain.ion_cli.cl_count > 0:
        ion_extras.append("CL")
    ws = tmp_path / "ion"
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(
        ws, hydrate, "_ion_result", sH_chain.ion_cli
    )
    code = pipe._run_export_step()
    assert code == 0, (
        "sH: _run_export_step failed (rc={}) for the ion branch".format(code)
    )
    _assert_sH_export(
        ws, "ion.gro", "ion.top",
        extra_mols=ion_extras, extra_itp=["ion.itp"],
    )
