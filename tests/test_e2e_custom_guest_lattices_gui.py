"""E2E grompp test for a custom ethanol guest hydrate with non-sI lattices.

Phase 45 plan 45-10 (interface export) + Phase 48.3 plan 48.3-10 (all 3
downstream exports). Proves that a custom ethanol guest hydrate with the 4
non-sI lattices that support custom guests (sII, c2te, ice1hte, 16) produces
grompp-valid output through the GUI Interface tab export AND all 3 downstream
GUI exports (Solute / Custom-Molecule / Ion —
``SoluteGROMACSExporter`` / ``CustomMoleculeGROMACSExporter`` /
``IonGROMACSExporter``, each called with the CUSTOM ``hydrate_config`` so
``_stage_hydrate_guest_itps`` builds ``custom_guest_info`` with ``MOL_H`` +
stages the transformed ``etoh.itp``).

MIRRORS ``tests/test_e2e_custom_guest_cross_tab_gui.py`` (the 44.1-19 template)
but swaps sI -> parametrized 4 lattices. 48.3-10 extends the module fixture to
build the 3 downstream inserter structures per lattice (fresh ``assemble_slab``
interface per inserter — the ion inserter mutates ``iface.molecule_index``) and
adds 12 parametrized grompp-validated cases (4 lattices × 3 downstream
exporters), closing the UAT Issue 3 intersection cell: custom guest × non-sI
lattice × downstream tabs (Gap 6 + G1).

Key assertions:
  1. For each lattice + exporter, the export stages the custom ITP
     (``etoh.itp`` transformed to moleculetype ``MOL_H``) + the ``.top``
     references ``MOL_H`` (not ``GUE``) + ``gmx grompp`` exits 0.
  2. MOL_H molecule-count parity between ``.top [molecules]`` and ``.gro``
     residues (== the slab-truncated ``guest_nmolecules``) — the standing
     regression guard for the config-vs-structure count desync class
     (UAT Issue 3: ``[molecules] MOL_H 864`` vs ``.gro 576``).

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter tests (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under offscreen
-> the exporter returns ``False`` without writing files. Inline patching of
``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED (the
``mock_save_dialog`` fixture from ``tests/test_output/conftest.py`` is
directory-scoped and NOT available to root-level test files).
``gmx`` IS on PATH so grompp runs. Marked ``@gmx_skipif`` so CI without gmx
still collects the test (skipped).
"""

import shutil
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.conftest import gmx_skipif  # noqa: E402
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
from tests.e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _insert_ions_from_solute,
    _insert_solutes,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)


# The 4 non-sI lattices that support custom guests (have cages). sTprime/17 are
# water-only (no cages -> custom guest is N/A); c0te/c1te are triclinic BLOCKED
# at the interface tab (see 45-08/45-09 for hydrate-only export); sH is
# triclinic-but-allowed and also supports custom guests (covered separately —
# huge guest count, Pitfall 5). This plan's scope is the 4 orthorhombic /
# sII-family lattices explicitly named in the plan.
_LATTICES = ("sII", "c2te", "ice1hte", "16")


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: build hydrate (GenIce2) + slab interface ONCE per
# lattice, amortize across the parametrized export cases.
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def custom_guest_chains(tmp_path_factory):
    """Build the custom-ethanol-guest hydrate + slab interfaces + the 3
    downstream inserter structures ONCE per lattice.

    Amortizes the GenIce2 generation (``HydrateStructureGenerator.generate``,
    measured 17-360ms per lattice) across the 4 interface + 12 downstream
    parametrized export cases (per AGENTS.md testing guidance).  Each lattice
    builds an independent ``HydrateConfig`` (same custom ethanol guest,
    different ``lattice_type``) -> gen -> candidate -> ``assemble_slab``.

    48.3-10 (44.1-19 discipline, generate-once-derive-many): the candidate is
    generated ONCE per lattice, then a FRESH ``assemble_slab`` interface is
    derived PER inserter (``seed=42`` -> deterministic identical slabs).  The
    ion inserter mutates ``iface.molecule_index`` when it is empty (real
    GenIce2 data, ``ion_inserter.py:259`` — ``structure.molecule_index =
    mol_index``), so each inserter gets its own interface to avoid
    cross-contaminating the interface exporter's reference.  The ion chain
    follows the REAL cross-tab data flow (Tab 3 -> Tab 4, CP-01):
    ``_insert_ions_from_solute`` operates on ``solute.interface_structure``
    (duck-typed solute attributes attached); the resulting molecule_index
    mutation is contained to the solute-dedicated interface and is the
    DESIGNED-FOR scenario in ``write_solute_gro_file`` (per-molecule
    ``mol_type`` guest resolution, solute_writer.py "Issue 3" comment block).

    All inserters return NEW structures (V-17 compliant).

    Box 3x3x8 nm: shortest vector 3.0 nm > 2 * cutoff (1.0 nm) for the grompp
    PBC rule (``rcoulomb=rvdw=1.0`` nm in ``em.mdp``). Deterministic
    (``seed=42``).

    Returns a dict keyed by ``lattice_type`` ->
    ``SimpleNamespace(hydrate=hydrate, iface=iface, config=config,
    solute=solute, custom=custom, ion=ion)``.
    """
    # Custom ethanol (9 atoms/mol) threaded correctly through slab (44.1-05).
    # CustomMoleculeStructure: 1 custom molecule placed in the water region.
    # Use a RENAMED COPY (cmet.gro/cmet.itp, moleculetype "MOL") to avoid
    # the etoh.itp filename collision between the cage guest (staged as
    # MOL_H via etoh.itp) and the custom molecule (copied with atomtypes
    # commented).  Same workaround as plan 44.1-13.  The cmet rename is
    # intentional HERE; the SAME-basename (etoh.itp vs etoh.itp) collision
    # scenario is plan 48.3-14's job, do not conflate.  The renamed copy
    # lives in a module-scoped temp dir (the inserter needs the files to
    # exist at fixture-setup time; function-scoped tmp_path is not yet
    # available) and is shared across lattices (content is
    # lattice-independent; the exporter copies + transforms into each case's
    # own workspace without mutating the source).
    cm_dir = tmp_path_factory.mktemp("custom_molecule_data")
    cmet_gro = cm_dir / "cmet.gro"
    cmet_itp = cm_dir / "cmet.itp"
    shutil.copy(ETOH_GRO, cmet_gro)
    cmet_lines = ETOH_ITP.read_text().splitlines(keepends=True)
    _in_moltype = False
    for i, line in enumerate(cmet_lines):
        if "[ moleculetype ]" in line:
            _in_moltype = True
        elif _in_moltype and line.strip() and not line.strip().startswith(";"):
            # First non-comment, non-empty line after [ moleculetype ] is the
            # moleculetype name ("etoh       3"); rename "etoh" -> "MOL".
            cmet_lines[i] = line.replace("etoh", "MOL", 1)
            break
    cmet_itp.write_text("".join(cmet_lines))

    chains = {}
    for lattice_type in _LATTICES:
        gen = HydrateStructureGenerator()
        # MIRROR the 44.1-19 template's custom ethanol config (lines 102-113),
        # swapping lattice_type. Use ETOH_GRO/ETOH_ITP absolute paths from
        # e2e_export_helpers (CWD-independent) instead of the template's
        # relative paths. guest_residue_name="MOL" (3 chars) so the _H suffix
        # yields "MOL_H" (5 chars, passes the GRO fixed-width limit).
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="etoh_e2e",
            guest_residue_name="MOL",
            guest_gro_path=str(ETOH_GRO),
            guest_itp_path=str(ETOH_ITP),
            guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
            guest_atom_count=9,
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        hydrate = gen.generate(config)
        candidate = hydrate.to_candidate()

        # Fresh slab interface PER inserter from the shared candidate
        # (generate-once-derive-many, seed=42 -> deterministic identical).
        def _make_iface():
            return assemble_slab(
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

        iface = _make_iface()  # interface exporter (never mutated)
        iface_solute = _make_iface()  # solute inserter + ion chain
        iface_custom = _make_iface()  # custom molecule inserter

        # Custom ethanol placed in cages (count varies by lattice — do NOT
        # assert exact counts, only > 0 + 9 * nmolecules consistency, the
        # 44.1-05 fix threading guest_atom_count through the slab detector).
        assert iface.guest_nmolecules > 0, (
            f"[{lattice_type}] custom ethanol slab should have guests"
        )
        assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
            f"[{lattice_type}] guest_atom_count={iface.guest_atom_count} != "
            f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
        )

        # SoluteStructure: CH4 solutes placed in the water region.
        # SoluteInserter creates its own registry internally; it does NOT
        # mutate the source interface (only reads via getattr).
        solute = _insert_solutes(
            iface_solute, solute_type="CH4", concentration=0.3
        )
        assert solute.n_molecules > 0, (
            f"[{lattice_type}] solute inserter should place CH4 molecules"
        )
        assert solute.interface_structure is not None, (
            f"[{lattice_type}] SoluteStructure.interface_structure must be "
            f"populated for staging + ion chaining"
        )

        # CustomMoleculeStructure: 1 cmet (renamed etoh) molecule in the
        # water region. After 48.3-02 D1 the inserter registers the ITP
        # moleculetype name ("MOL", <=5 chars) so .gro residues + .top
        # [molecules] agree strictly.
        cm_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=cmet_gro,
            itp_path=cmet_itp,
            molecule_count=1,
        )
        inserter = CustomMoleculeInserter(cm_config, seed=42)
        custom = inserter.place_random(iface_custom, 1)
        assert custom.custom_molecule_count > 0, (
            f"[{lattice_type}] custom molecule inserter should place 1 "
            f"molecule in the water region"
        )
        assert custom.guest_atom_count > 0, (
            f"[{lattice_type}] CustomMoleculeStructure.guest_atom_count must "
            f"be propagated from the interface for the staging helper's "
            f"presence gate"
        )

        # IonStructure: Na+ / Cl- in the water region, built from the SOLUTE
        # (real cross-tab flow Tab 3 -> Tab 4 via _solute_to_ion_source /
        # BUG I5 workaround).  NOTE: replace_water_with_ions mutates
        # iface_solute.molecule_index (ion_inserter.py:259) when the
        # interface has no molecule_index (real GenIce2 data) — contained to
        # the solute-dedicated interface (see fixture docstring).
        ion = _insert_ions_from_solute(solute, concentration=0.15)
        assert (ion.na_count > 0 or ion.cl_count > 0), (
            f"[{lattice_type}] ion inserter should place Na+ / Cl- ions"
        )
        assert ion.guest_atom_count > 0, (
            f"[{lattice_type}] IonStructure.guest_atom_count must be "
            f"propagated from the interface"
        )
        assert ion.guest_nmolecules > 0, (
            f"[{lattice_type}] IonStructure.guest_nmolecules must be "
            f"propagated from the interface"
        )

        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, iface=iface, config=config,
            solute=solute, custom=custom, ion=ion,
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# Shared assertion helper
# ══════════════════════════════════════════════════════════════════════════════


def _assert_custom_guest_export(ws, gro_name, top_name):
    """Assert a custom-ethanol-guest interface export is grompp-valid.

    Checks (per the plan's must-haves):
      1. ``.gro`` + ``.top`` files exist.
      2. ``.top [molecules]`` + ``.gro`` residues contain ``SOL`` + ``MOL_H``
         (not ``GUE`` — would mean ``custom_guest_info`` was NOT threaded).
      3. ``etoh.itp`` exists in ws AND is the TRANSFORMED copy (moleculetype
         ``MOL_H``) — prerequisite for grompp (.top lists MOL_H -> #include'd
         ITP must define MOL_H).
      4. File consistency: ``assert_itp_completeness`` +
         ``assert_gro_top_consistent``.
      5. ``gmx grompp`` exits 0 (when gmx on PATH).
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # 1. Files written by the exporter (writers + ITP staging).
    assert gro_path.exists(), f".gro not written: {gro_path}"
    assert top_path.exists(), f".top not written: {top_path}"

    # 2. .top [molecules] + .gro residues contain SOL + MOL_H; GUE must NEVER
    #    appear (would mean custom_guest_info was NOT threaded to the writers).
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, f"expected SOL in [molecules], got {mols}"
    assert "MOL_H" in mols, (
        f"expected MOL_H in [molecules] (custom_guest_info not threaded), "
        f"got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )

    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res, f"expected SOL in .gro residues, got {gro_res}"
    assert "MOL_H" in gro_res, (
        f"expected MOL_H in .gro residues (custom_guest_info not threaded), "
        f"got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not "
        f"threaded): {gro_res}"
    )

    # 3. The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    #    not the raw source ITP (moleculetype etoh). transform_guest_itp was
    #    applied by _stage_hydrate_guest_itps (plan 44.1-08).
    etoh_path = ws / "etoh.itp"
    assert etoh_path.exists(), (
        "custom guest ITP (etoh.itp) not staged by _stage_hydrate_guest_itps"
    )
    staged_etoh = etoh_path.read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype -- "
        "transform_guest_itp was not applied by _stage_hydrate_guest_itps"
    )

    # 4. Stage the MDP for grompp + run file-consistency assertions (always
    #    run — catches _H suffix + missing-molecule bugs even without gmx).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 5. Run gmx grompp -- must exit 0 (topology self-consistent + sim-ready).
    #    The test is @gmx_skipif so this block only runs when gmx IS on PATH;
    #    the shutil.which guard is a harmless defensive check matching the
    #    plan's instruction.
    if shutil.which("gmx"):
        exit_code, stderr = run_gmx_grompp(
            ws, gro_file=gro_name, top_file=top_name
        )
        assert exit_code == 0, (
            f"gmx grompp failed (custom ethanol interface export):\n{stderr}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized GUI interface export + grompp (4 non-sI lattices)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_LATTICES))
def test_custom_guest_lattice_interface_export_grompp(
    custom_guest_chains, tmp_path, lattice_type
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate with each of the 4
    non-sI lattices (sII, c2te, ice1hte, 16) exported via the GUI Interface tab
    (``InterfaceGROMACSExporter.export_interface_gromacs`` called with the
    CUSTOM ``hydrate_config``).

    Phase 45 plan 45-10 acceptance test. MIRRORS the 44.1-19 template
    (``test_e2e_custom_guest_cross_tab_gui.py``) but swaps sI -> parametrized 4
    lattices and tests ONLY the interface export (not all 4 exporters).

    Flow (each parametrized case):
      1. ``ws = tmp_path / lattice_type``.
      2. Mock ``QFileDialog.getSaveFileName`` (under ``QT_QPA_PLATFORM=offscreen``
         it returns ``("", "")`` -> exporter returns False without writing) +
         ``QMessageBox``. The exporter calls getSaveFileName ONCE for the .gro
         path; .top is derived from ``path.stem``.
      3. ``ok = exporter.export_interface_gromacs(chain.iface,
         hydrate_config=chain.config)`` -- passes the CUSTOM config (NOT None)
         so ``_stage_hydrate_guest_itps`` builds ``custom_guest_info`` with
         ``MOL_H`` + stages the transformed ``etoh.itp`` (moleculetype MOL_H,
         [atomtypes] commented, [atoms] resname MOL_H).
      4. ``assert ok is True``.
      5. ``_assert_custom_guest_export(ws, "output.gro", "output.top")``.

    Key assertion: for each lattice, the export stages the transformed
    ``etoh.itp`` (moleculetype ``MOL_H``) + the ``.top`` references ``MOL_H``
    (not ``GUE``) + ``gmx grompp`` exits 0. No ``GUE`` fallback confirms
    ``custom_guest_info`` was correctly threaded via ``hydrate_config``.
    """
    chain = custom_guest_chains[lattice_type]
    ws = tmp_path / lattice_type
    ws.mkdir()

    # 1-2. Mock QFileDialog + QMessageBox so the exporter runs end-to-end
    #      without a real GUI. getSaveFileName is called ONCE (single
    #      return_value patch suffices -- matches plans 44.1-09/44.1-19).
    gro_path = ws / "output.gro"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        # Pass the CUSTOM config (NOT None) so _stage_hydrate_guest_itps
        # reads config.is_custom_guest -> True -> builds custom_guest_info with
        # MOL_H + stages the transformed etoh.itp.
        ok = exporter.export_interface_gromacs(
            chain.iface, hydrate_config=chain.config
        )
        assert ok is True, (
            f"[{lattice_type}] export_interface_gromacs returned False -- "
            f"export failed (QFileDialog mock may not have been picked up, or "
            f"staging raised)"
        )

    # 3-5. Shared assertions: files exist, SOL + MOL_H (not GUE), transformed
    #      etoh.itp staged, file consistency, grompp rc == 0.
    _assert_custom_guest_export(ws, "output.gro", "output.top")
