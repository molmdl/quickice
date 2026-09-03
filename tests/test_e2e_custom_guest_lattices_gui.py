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
from unittest.mock import patch

import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.gui.export import (  # noqa: E402
    CustomMoleculeGROMACSExporter,
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
)
from tests.e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)
from tests.e2e_chain_fixtures import (  # noqa: E402
    CUSTOM_GUEST_LATTICES,
    custom_guest_chains,
)


# The 4 non-sI custom-guest lattices under test (canonical set defined in
# tests/e2e_chain_fixtures.py and shared with the fixture + CLI sibling).


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
@pytest.mark.parametrize("lattice_type", list(CUSTOM_GUEST_LATTICES))
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


# ══════════════════════════════════════════════════════════════════════════════
# Downstream exports (Solute / Custom-Molecule / Ion tabs) × 4 non-sI lattices
# ══════════════════════════════════════════════════════════════════════════════


def _assert_mol_h_count_parity(
    gro_path, top_path, expected_molecules, atoms_per_guest, ctx
):
    """Assert MOL_H molecule-count parity: .top [molecules] == .gro residues
    == slab-truncated guest count.

    THE standing regression guard for the UAT Issue 3 config-vs-structure
    count desync class (slab truncation + config-derived counts): a
    config-derived guest count in ``.top [molecules]`` (full-lattice guest
    count, e.g. ``MOL_H 864``) diverging from the slab-truncated ``.gro``
    residue count (e.g. ``MOL_H 576``). The writers must derive the MOL_H
    count from the STRUCTURE (slab-truncated ``guest_nmolecules``), never
    from a config-derived value. Asserted in EVERY downstream export case.

    The .gro molecule count is derived from ATOM-level residue entries
    (``parse_gro_residue_names`` yields one entry PER ATOM) divided by the
    atoms-per-molecule (``config.guest_atom_count`` — the molecular formula
    size from the config, NOT a config-derived molecule count). Divisibility
    is asserted so partial/mangled molecules cannot pass.

    Args:
        gro_path: Exported ``.gro`` file path.
        top_path: Exported ``.top`` file path.
        expected_molecules: Slab-truncated guest molecule count
            (``iface.guest_nmolecules`` — the shared slab truth; all 4
            per-inserter interfaces are deterministic-identical, seed=42).
        atoms_per_guest: Atoms per cage-guest molecule
            (``config.guest_atom_count`` == 9 for ethanol).
        ctx: ``"{lattice_type}/{exporter_id}"`` for failure messages.
    """
    top_count = parse_top_molecules(str(top_path)).get("MOL_H", 0)
    gro_atoms = parse_gro_residue_names(str(gro_path)).count("MOL_H")
    assert top_count > 0, (
        f"[{ctx}] MOL_H missing or zero in .top [molecules] "
        f"(cage guest dropped from the downstream export)"
    )
    assert gro_atoms > 0, (
        f"[{ctx}] MOL_H residues missing in .gro "
        f"(cage guest dropped from the downstream export)"
    )
    assert gro_atoms % atoms_per_guest == 0, (
        f"[{ctx}] MOL_H atom count {gro_atoms} not divisible by "
        f"atoms-per-molecule {atoms_per_guest} -- partial/mangled guest "
        f"molecules in .gro"
    )
    gro_count = gro_atoms // atoms_per_guest
    assert top_count == gro_count == expected_molecules, (
        f"[{ctx}] MOL_H molecule-count desync (UAT Issue 3 signature): "
        f".top [molecules]={top_count}, .gro MOL_H molecules={gro_count} "
        f"({gro_atoms} atoms // {atoms_per_guest}), "
        f"slab-truncated guest_nmolecules={expected_molecules} -- "
        f"writers must derive counts from the structure, not the config"
    )


# Each case: (exporter_id, exporter_class, structure_attr, expected_molecules,
#             extra_expected_itps)
# - expected_molecules: subset that MUST appear in .top [molecules] + .gro
#   residues (SOL + MOL_H always; plus exporter-specific molecules).
# - extra_expected_itps: ITPs the exporter writes/copies beyond the always-
#   present tip4p-ice.itp + etoh.itp (MOL_H).
#
# NOTE on the ion case: expected_molecules includes CH4_L + extra ITPs
# include ch4_liquid.itp because THIS file's ion chain is built from the
# SOLUTE (``_insert_ions_from_solute`` — the real cross-tab flow, Tab 3 ->
# Tab 4, per the plan), so the IonStructure carries the CH4 solutes (and the
# exporter stages ch4_liquid.itp when solute_n_molecules > 0). The 44.1-19
# template's ion case used ``_insert_ions`` on a solute-free interface,
# hence no CH4_L there. NA / CL are asserted conditionally (only when
# placed).
_DOWNSTREAM_EXPORT_CASES = [
    pytest.param(
        "solute",
        SoluteGROMACSExporter,
        "solute",
        {"SOL", "MOL_H", "CH4_L"},
        ("ch4_liquid.itp",),
        id="solute",
    ),
    pytest.param(
        "custom_molecule",
        CustomMoleculeGROMACSExporter,
        "custom",
        {"SOL", "MOL_H", "MOL"},
        ("cmet.itp",),
        id="custom_molecule",
    ),
    pytest.param(
        "ion",
        IonGROMACSExporter,
        "ion",
        {"SOL", "MOL_H", "CH4_L"},  # NA / CL asserted conditionally below
        ("ch4_liquid.itp", "ion.itp"),
        id="ion",
    ),
]


@gmx_skipif
@pytest.mark.parametrize(
    "exporter_id,exporter_class,structure_attr,expected_molecules,"
    "extra_expected_itps",
    _DOWNSTREAM_EXPORT_CASES,
)
@pytest.mark.parametrize("lattice_type", list(CUSTOM_GUEST_LATTICES))
def test_custom_guest_lattice_downstream_export_grompp(
    custom_guest_chains,
    tmp_path,
    lattice_type,
    exporter_id,
    exporter_class,
    structure_attr,
    expected_molecules,
    extra_expected_itps,
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate with each of the 4
    non-sI lattices (sII, c2te, ice1hte, 16) exported via EACH of the 3
    downstream GUI exporters (Solute / Custom-Molecule / Ion), called with the
    CUSTOM ``hydrate_config`` (the 44.1-09/11/13/15 exporter signature).

    Phase 48.3 plan 48.3-10: closes the UAT Issue 3 intersection cell —
    custom cage guest × non-sI lattice × downstream tabs (previously only the
    interface export was covered for non-sI lattices; built-in guests got the
    full chain). Mirrors ``test_e2e_custom_guest_cross_tab_gui.py``'s
    per-exporter pattern (QFileDialog patched at
    ``quickice.gui.export.QFileDialog.getSaveFileName``, QMessageBox patched,
    ``hydrate_config=config`` threaded).

    Flow (each of the 12 parametrized cases):
      1. ``ws = tmp_path / lattice_type`` (unique per case — pytest gives
         each parametrized invocation its own ``tmp_path``).
      2. Mock ``QFileDialog.getSaveFileName`` (under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> exporter
         returns False without writing) + ``QMessageBox``. The exporter
         calls getSaveFileName ONCE for the .gro path; .top is derived from
         ``path.stem``.
      3. ``ok = exporter.export_{exporter_id}_gromacs(structure,
         hydrate_config=chain.config)`` -- passes the CUSTOM config (NOT
         None) so ``_stage_hydrate_guest_itps`` builds ``custom_guest_info``
         with ``MOL_H`` + stages the transformed ``etoh.itp`` (moleculetype
         MOL_H, [atomtypes] commented, [atoms] resname MOL_H).
      4. ``assert ok is True``.
      5. Shared assertions: files + staged ITPs exist; expected molecules in
         ``.top [molecules]`` + ``.gro`` residues (no ``GUE``);
         ``_assert_mol_h_count_parity`` (the UAT Issue 3 desync guard);
         ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (always);
         ``gmx grompp`` rc == 0 (when gmx present).

    Key assertion: for each lattice × exporter, the export stages the
    transformed ``etoh.itp`` (moleculetype ``MOL_H``) + the ``.top``
    references ``MOL_H`` (not ``GUE``) + the MOL_H molecule count agrees
    between ``.top [molecules]`` and the ``.gro`` residues (== the
    slab-truncated ``guest_nmolecules``) + ``gmx grompp`` exits 0.
    """
    chain = custom_guest_chains[lattice_type]
    structure = getattr(chain, structure_attr)
    ws = tmp_path / lattice_type
    ws.mkdir()

    # 1-2. Mock QFileDialog + QMessageBox so the exporter runs end-to-end
    #      without a real GUI. getSaveFileName is called ONCE (single
    #      return_value patch suffices -- matches plans 44.1-09/11/13/15
    #      and the 44.1-19 template).
    gro_path = ws / "output.gro"
    top_path = ws / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = exporter_class(parent_widget=None)
        export_method = getattr(exporter, f"export_{exporter_id}_gromacs")
        # Pass the CUSTOM config (NOT None) so _stage_hydrate_guest_itps
        # reads config.is_custom_guest -> True -> builds custom_guest_info
        # with MOL_H + stages the transformed etoh.itp.
        ok = export_method(structure, hydrate_config=chain.config)
        assert ok is True, (
            f"[{lattice_type}/{exporter_id}] export_{exporter_id}_gromacs "
            f"returned False -- export failed (QFileDialog mock may not have "
            f"been picked up, or staging raised)"
        )

    # 3. Files written by the exporter (writers + ITP staging).
    assert gro_path.exists(), (
        f"[{lattice_type}/{exporter_id}] .gro not written: {gro_path}"
    )
    assert top_path.exists(), (
        f"[{lattice_type}/{exporter_id}] .top not written: {top_path}"
    )
    assert (ws / "tip4p-ice.itp").exists(), (
        f"[{lattice_type}/{exporter_id}] water ITP (tip4p-ice.itp) not "
        f"staged by the exporter"
    )
    assert (ws / "etoh.itp").exists(), (
        f"[{lattice_type}/{exporter_id}] custom guest ITP (etoh.itp) not "
        f"staged by _stage_hydrate_guest_itps"
    )
    for itp in extra_expected_itps:
        assert (ws / itp).exists(), (
            f"[{lattice_type}/{exporter_id}] expected ITP '{itp}' not "
            f"written/copied by the exporter"
        )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh). Prerequisite for grompp:
    # .top [molecules] lists MOL_H -> #include'd ITP must define MOL_H.
    staged_etoh = (ws / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        f"[{lattice_type}/{exporter_id}] staged etoh.itp is missing the "
        f"MOL_H moleculetype -- transform_guest_itp was not applied by "
        f"_stage_hydrate_guest_itps"
    )

    # 4. .top [molecules] + .gro residues contain the expected molecules
    #    (SOL + MOL_H always; plus exporter-specific). GUE must NEVER appear
    #    (would mean custom_guest_info was NOT threaded to the writers).
    mols = parse_top_molecules(str(top_path))
    for mol in expected_molecules:
        assert mol in mols, (
            f"[{lattice_type}/{exporter_id}] expected '{mol}' in "
            f"[molecules], got {mols}"
        )
    assert "GUE" not in mols, (
        f"[{lattice_type}/{exporter_id}] GUE must NOT appear in [molecules] "
        f"(custom_guest_info not threaded): {mols}"
    )
    # Ion case: NA / CL asserted conditionally (only when ions were placed).
    if exporter_id == "ion":
        if chain.ion.na_count > 0:
            assert "NA" in mols, (
                f"[{lattice_type}/ion] expected NA in [molecules] "
                f"(na_count>0), got {mols}"
            )
        if chain.ion.cl_count > 0:
            assert "CL" in mols, (
                f"[{lattice_type}/ion] expected CL in [molecules] "
                f"(cl_count>0), got {mols}"
            )

    gro_res_names = parse_gro_residue_names(str(gro_path))
    gro_res = set(gro_res_names)
    for mol in expected_molecules:
        assert mol in gro_res, (
            f"[{lattice_type}/{exporter_id}] expected '{mol}' in .gro "
            f"residues, got {gro_res}"
        )
    assert "GUE" not in gro_res, (
        f"[{lattice_type}/{exporter_id}] GUE must NOT appear in .gro "
        f"residues (custom_guest_info not threaded): {gro_res}"
    )
    if exporter_id == "ion":
        if chain.ion.na_count > 0:
            assert "NA" in gro_res, (
                f"[{lattice_type}/ion] expected NA in .gro residues "
                f"(na_count>0), got {gro_res}"
            )
        if chain.ion.cl_count > 0:
            assert "CL" in gro_res, (
                f"[{lattice_type}/ion] expected CL in .gro residues "
                f"(cl_count>0), got {gro_res}"
            )

    # 5. MOL_H count parity (ALWAYS) -- the UAT Issue 3 desync regression
    #    guard: .top [molecules] count == .gro residue-molecule count ==
    #    slab-truncated guest_nmolecules.
    _assert_mol_h_count_parity(
        gro_path,
        top_path,
        chain.iface.guest_nmolecules,
        chain.config.guest_atom_count,
        f"{lattice_type}/{exporter_id}",
    )

    # 6. Stage the MDP for grompp + run file-consistency assertions (always
    #    run -- catches _H suffix + missing-molecule bugs even without gmx).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 7. Run gmx grompp -- must exit 0 (topology self-consistent + sim-ready).
    #    The test is @gmx_skipif so this block only runs when gmx IS on PATH;
    #    the shutil.which guard is a harmless defensive check matching the
    #    file's existing convention.
    if shutil.which("gmx"):
        exit_code, stderr = run_gmx_grompp(
            ws, gro_file="output.gro", top_file="output.top"
        )
        assert exit_code == 0, (
            f"[{lattice_type}/{exporter_id}] gmx grompp failed (custom "
            f"ethanol {exporter_class.__name__}):\n{stderr}"
        )
