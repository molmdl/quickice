"""E2E grompp test for a custom ethanol guest hydrate with non-sI lattices
through the CLI interface export AND all 3 downstream CLI export branches.

Phase 45 plan 45-11 (interface export) + Phase 48.3 plan 48.3-11 (custom /
solute / ion export branches). Proves that a custom ethanol guest hydrate with
the 4 non-sI lattices that support custom guests (sII, c2te, ice1hte, 16)
produces grompp-valid output through the CLI Interface tab export AND the 3
downstream CLI export branches (``CLIPipeline._run_export_step`` called with
``_custom_result`` / ``_solute_result`` / ``_ion_result`` set — the Pattern-4
export-branch invocation). The ``_custom_result`` branch was NEVER run for
non-sI lattices before this plan (45-VERIFICATION Gap 1, CLI half — G1).

MIRRORS ``tests/e2e/custom_guest/test_e2e_custom_guest_cross_tab_cli.py`` (the 44.1-20
template) but swaps sI -> parametrized 4 lattices. 48.3-11 mirrors 48.3-10
(the GUI half, ``tests/e2e/custom_guest/test_e2e_custom_guest_lattices_gui.py``) on the CLI side:
the module fixture builds the 3 downstream inserter structures per lattice
(fresh ``assemble_slab`` interface per inserter — the ion inserter mutates
``molecule_index``, 44.1-19 discipline) and adds 12 parametrized
grompp-validated cases (4 lattices × 3 downstream branches). CLI and GUI
export paths are distinct code (``quickice.cli.pipeline`` vs
``quickice.gui.export``) — sibling pairs stay split (48.2 constraint), so
GUI and CLI regressions are caught independently.

CLI ``_run_export_step`` reads ``hydrate_config = getattr(self._hydrate_result,
"config", None)`` -> ``_build_custom_guest_info(config)`` returns a
``list[dict]`` for custom guests (``{'mol_type': 'etoh_e2e', 'residue_name':
'MOL_H', 'itp_path': Path(etoh.itp)}``) -> ``custom_guest_info=cgi`` threaded
to the per-branch writers (``write_custom_molecule_*`` / ``write_solute_*`` /
``write_ion_*``). ``copy_itp_files_for_structure`` stages the transformed
``etoh.itp`` (moleculetype ``MOL_H``) for every branch via the 44.1-17
custom-guest staging block + branch-specific ITPs (``cmet.itp`` for the
liquid custom molecule, ``ch4_liquid.itp`` for CH4 solutes, generated
``ion.itp``).

Key assertions (per lattice × branch):
  1. The CLI export stages the custom ITP (``etoh.itp`` transformed to
     moleculetype ``MOL_H``) + the ``.top`` references ``MOL_H`` (not
     ``GUE``) + ``gmx grompp`` exits 0.
  2. MOL_H molecule-count parity between ``.top [molecules]`` and ``.gro``
     residues (== the slab-truncated ``guest_nmolecules``) — the standing
     regression guard for the config-vs-structure count desync class
     (UAT Issue 3: ``[molecules] MOL_H 864`` vs ``.gro 576``).

``@gmx_skipif`` guards CI without gmx: file-consistency assertions
(``assert_itp_completeness`` + ``assert_gro_top_consistent``) always run;
grompp only when gmx is on PATH.

No PySide6/VTK imports: ``_run_export_step`` is in-process and Qt-free
(AGENTS.md — CLI tests must stay Qt-free).

The test box is 3.0 x 3.0 x 8.0 nm (shortest vector 3.0 nm > 2 * rcoulomb =
2.0 nm in ``em.mdp``, satisfying grompp's PBC "cut-off longer than half the
shortest box vector" rule).
"""

import shutil
from types import SimpleNamespace

import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from tests.e2e_export_helpers import (  # noqa: E402
    run_gmx_grompp,
    MDP_PATH,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)
from tests.e2e_chain_fixtures import (  # noqa: E402
    CUSTOM_GUEST_LATTICES,
    custom_guest_chains,
)


# The 4 non-sI custom-guest lattices under test (canonical set defined in
# tests/e2e_chain_fixtures.py and shared with the fixture + GUI sibling).


# ══════════════════════════════════════════════════════════════════════════════
# CLI pipeline construction helper
# ══════════════════════════════════════════════════════════════════════════════


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and a single downstream structure set so ``_run_export_step``'s
    priority selection (ion > solute > custom > interface > hydrate > ice)
    picks that branch. All other ``_*_result`` stay at their ``__init__``
    default of ``None``.

    COPIED from the 44.1-20 template (``test_e2e_custom_guest_cross_tab_cli.py``
    lines 155-166) — the established CLI export-branch test pattern.
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


# ══════════════════════════════════════════════════════════════════════════════
# Shared assertion helper
# ══════════════════════════════════════════════════════════════════════════════


def _assert_custom_cli_export(ws, step_name):
    """Assert a custom-ethanol-guest CLI interface export is grompp-valid.

    Checks (per the plan's must-haves):
      1. ``{step_name}.gro`` + ``{step_name}.top`` files exist.
      2. ``tip4p-ice.itp`` exists (the water-model ITP, always staged).
      3. ``etoh.itp`` exists AND is the TRANSFORMED copy (moleculetype
         ``MOL_H``) — the custom guest ITP after ``copy_itp_files_for_structure``
         (41-07 custom branch) applies ``transform_guest_itp``.
      4. ``.top [molecules]`` + ``.gro`` residues contain ``SOL`` + ``MOL_H``
         (not ``GUE`` — would mean ``custom_guest_info`` was NOT threaded).
      5. File consistency: ``assert_itp_completeness`` +
         ``assert_gro_top_consistent``.
      6. ``gmx grompp`` exits 0 (when gmx on PATH).
    """
    gro_path = ws / f"{step_name}.gro"
    top_path = ws / f"{step_name}.top"

    # 1. Files written by _run_export_step (writers + ITP staging).
    assert gro_path.exists(), f"{step_name}.gro not written: {gro_path}"
    assert top_path.exists(), f"{step_name}.top not written: {top_path}"

    # 2. tip4p-ice.itp always staged (water model ITP).
    assert (ws / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"

    # 3. The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    #    not the raw source ITP (moleculetype etoh). transform_guest_itp was
    #    applied by copy_itp_files_for_structure (41-07 custom branch).
    etoh_path = ws / "etoh.itp"
    assert etoh_path.exists(), (
        "custom guest ITP (etoh.itp) not staged by copy_itp_files_for_structure "
        "(41-07 custom branch)"
    )
    staged_etoh = etoh_path.read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype -- "
        "transform_guest_itp was not applied by copy_itp_files_for_structure"
    )

    # 4. .top [molecules] + .gro residues contain SOL + MOL_H; GUE must NEVER
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

    # 5. Stage the MDP for grompp + run file-consistency assertions (always
    #    run — catches _H suffix + missing-molecule bugs even without gmx).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 6. Run gmx grompp -- must exit 0 (topology self-consistent + sim-ready).
    #    The test is @gmx_skipif so this block only runs when gmx IS on PATH;
    #    the shutil.which guard is a harmless defensive check matching the
    #    plan's instruction.
    if shutil.which("gmx"):
        exit_code, stderr = run_gmx_grompp(
            ws, gro_file=f"{step_name}.gro", top_file=f"{step_name}.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed (custom ethanol CLI interface export):\n{stderr}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized CLI interface export + grompp (4 non-sI lattices)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(CUSTOM_GUEST_LATTICES))
def test_custom_guest_lattice_cli_interface_export_grompp(
    custom_guest_chains, tmp_path, lattice_type
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate with each of the 4
    non-sI lattices (sII, c2te, ice1hte, 16) exported via the CLI Interface tab
    (``CLIPipeline._run_export_step`` interface branch with ``_hydrate_result``
    carrying the CUSTOM ``.config``).

    Phase 45 plan 45-11 acceptance test. MIRRORS the 44.1-20 template
    (``test_e2e_custom_guest_cross_tab_cli.py``) but swaps sI -> parametrized 4
    lattices and tests ONLY the interface export branch (not the full
    interface -> solute -> ion chain). The GUI half is 45-10.

    Flow (each parametrized case):
      1. ``ws = tmp_path / lattice_type`` (mkdir).
      2. ``pipe = _make_cli_pipeline(ws, chain.hydrate, "_interface_result",
         chain.iface)`` -- ``hydrate`` carries ``.config`` (the custom
         HydrateConfig) so ``_run_export_step`` reads it via
         ``getattr(self._hydrate_result, "config", None)`` ->
         ``_build_custom_guest_info(config)`` returns a ``list[dict]`` with
         ``{'mol_type': 'etoh_e2e', 'residue_name': 'MOL_H', 'itp_path':
         Path(etoh.itp)}``.
      3. ``code = pipe._run_export_step()`` -- assert ``code == 0``.
      4. ``_assert_custom_cli_export(ws, "interface")`` -- files exist, SOL +
         MOL_H (not GUE), transformed etoh.itp staged, file consistency, grompp
         rc == 0.

    Key assertion: for each lattice, the CLI export stages the transformed
    ``etoh.itp`` (moleculetype ``MOL_H``) + the ``.top`` references ``MOL_H``
    (not ``GUE``) + ``gmx grompp`` exits 0. No ``GUE`` fallback confirms
    ``custom_guest_info`` was correctly threaded via ``hydrate_config``.
    """
    chain = custom_guest_chains[lattice_type]
    ws = tmp_path / lattice_type
    ws.mkdir()

    # 2. Construct the CLI pipeline with _hydrate_result=chain.hydrate (carries
    #    .config) + _interface_result=chain.iface so _run_export_step's priority
    #    selection picks the interface branch.
    pipe = _make_cli_pipeline(
        ws, chain.hydrate, "_interface_result", chain.iface
    )

    # 3. Run the export step — must succeed (writers + ITP staging).
    code = pipe._run_export_step()
    assert code == 0, (
        f"[{lattice_type}] _run_export_step should succeed for the interface "
        f"branch with a custom guest"
    )

    # 4. Shared assertions: files exist, SOL + MOL_H (not GUE), transformed
    #    etoh.itp staged, file consistency, grompp rc == 0.
    _assert_custom_cli_export(ws, "interface")


# ══════════════════════════════════════════════════════════════════════════════
# Downstream CLI export branches (custom / solute / ion) × 4 non-sI lattices
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
            (``iface.guest_nmolecules`` — the shared slab truth; all 3
            per-inserter interfaces are deterministic-identical, seed=42).
        atoms_per_guest: Atoms per cage-guest molecule
            (``config.guest_atom_count`` == 9 for ethanol).
        ctx: ``"{lattice_type}/{branch_id}"`` for failure messages.
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


def _assert_cli_downstream_export(
    ws, step_name, chain, expected_molecules, extra_expected_itps, ctx
):
    """Assert a downstream CLI export (custom / solute / ion branch) is
    grompp-valid with correct custom-guest staging.

    Checks (per the plan's must-haves):
      1. ``{step_name}.gro`` + ``{step_name}.top`` files exist.
      2. ``tip4p-ice.itp`` (always) + ``etoh.itp`` staged AND the staged
         copy is the TRANSFORMED one (moleculetype ``MOL_H``) + branch-
         specific ITPs exist (``cmet.itp`` / ``ch4_liquid.itp`` /
         ``ion.itp``).
      3. ``.top [molecules]`` contains the expected molecules (no ``GUE``);
         NA / CL asserted conditionally for the ion branch (only when
         ions were placed).
      4. ``.gro`` residues contain the expected molecules (no ``GUE``);
         NA / CL conditional for the ion branch.
      5. MOL_H count parity (``_assert_mol_h_count_parity`` — the UAT
         Issue 3 desync guard).
      6. File consistency: ``assert_itp_completeness`` +
         ``assert_gro_top_consistent`` (always).
      7. ``gmx grompp`` exits 0 (when gmx on PATH).
    """
    gro_path = ws / f"{step_name}.gro"
    top_path = ws / f"{step_name}.top"

    # 1. Files written by _run_export_step (writers + ITP staging).
    assert gro_path.exists(), f"[{ctx}] {step_name}.gro not written: {gro_path}"
    assert top_path.exists(), f"[{ctx}] {step_name}.top not written: {top_path}"

    # 2. Always-staged ITPs: tip4p-ice.itp (water model) + etoh.itp (custom
    #    cage guest, staged by the 44.1-17 custom-guest block in
    #    copy_itp_files_for_structure). The staged etoh.itp must be the
    #    TRANSFORMED copy (moleculetype MOL_H), not the raw source ITP
    #    (moleculetype etoh). Prerequisite for grompp: .top [molecules]
    #    lists MOL_H -> #include'd ITP must define MOL_H.
    assert (ws / "tip4p-ice.itp").exists(), (
        f"[{ctx}] water ITP (tip4p-ice.itp) not staged"
    )
    etoh_path = ws / "etoh.itp"
    assert etoh_path.exists(), (
        f"[{ctx}] custom guest ITP (etoh.itp) not staged by "
        f"copy_itp_files_for_structure (44.1-17 custom-guest block)"
    )
    staged_etoh = etoh_path.read_text()
    assert "MOL_H" in staged_etoh, (
        f"[{ctx}] staged etoh.itp is missing the MOL_H moleculetype -- "
        f"transform_guest_itp was not applied by copy_itp_files_for_structure"
    )
    for itp in extra_expected_itps:
        assert (ws / itp).exists(), (
            f"[{ctx}] expected ITP '{itp}' not staged/copied for the "
            f"{step_name} branch"
        )

    # 3. .top [molecules]: expected molecules + #include of etoh.itp (the
    #    cage guest ITP); GUE must NEVER appear (would mean custom_guest_info
    #    was NOT threaded to the writers).
    top_text = top_path.read_text()
    assert '#include "etoh.itp"' in top_text, (
        f"[{ctx}] {step_name}.top does not #include etoh.itp (cage guest "
        f"molecule definition missing): {top_text!r}"
    )
    mols = parse_top_molecules(str(top_path))
    for mol in expected_molecules:
        assert mol in mols, f"[{ctx}] expected '{mol}' in [molecules], got {mols}"
    assert "GUE" not in mols, (
        f"[{ctx}] GUE must NOT appear in [molecules] (custom_guest_info not "
        f"threaded): {mols}"
    )
    # Ion branch: NA / CL asserted conditionally (only when ions were placed).
    if step_name == "ion":
        if chain.ion.na_count > 0:
            assert "NA" in mols, f"[{ctx}] expected NA in [molecules] (na_count>0), got {mols}"
        if chain.ion.cl_count > 0:
            assert "CL" in mols, f"[{ctx}] expected CL in [molecules] (cl_count>0), got {mols}"

    # 4. .gro residues: expected molecules; GUE must NEVER appear.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    for mol in expected_molecules:
        assert mol in gro_res, f"[{ctx}] expected '{mol}' in .gro residues, got {gro_res}"
    assert "GUE" not in gro_res, (
        f"[{ctx}] GUE must NOT appear in .gro residues (custom_guest_info "
        f"not threaded): {gro_res}"
    )
    if step_name == "ion":
        if chain.ion.na_count > 0:
            assert "NA" in gro_res, f"[{ctx}] expected NA in .gro residues (na_count>0), got {gro_res}"
        if chain.ion.cl_count > 0:
            assert "CL" in gro_res, f"[{ctx}] expected CL in .gro residues (cl_count>0), got {gro_res}"

    # 5. MOL_H count parity (ALWAYS) -- the UAT Issue 3 desync regression
    #    guard: .top [molecules] count == .gro residue-molecule count ==
    #    slab-truncated guest_nmolecules.
    _assert_mol_h_count_parity(
        gro_path,
        top_path,
        chain.iface.guest_nmolecules,
        chain.config.guest_atom_count,
        ctx,
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
            ws, gro_file=f"{step_name}.gro", top_file=f"{step_name}.top"
        )
        assert exit_code == 0, (
            f"[{ctx}] gmx grompp failed (CLI {step_name} branch, custom "
            f"ethanol guest):\n{stderr}"
        )


# Each case: (branch_id, result_attr, expected_molecules, extra_expected_itps)
# - branch_id: the ``custom_guest_chains`` structure attribute + the
#   ``_run_export_step`` branch basename (``custom.gro`` / ``solute.gro`` /
#   ``ion.gro``).
# - result_attr: the ``CLIPipeline`` attribute set for the Pattern-4
#   export-branch invocation (ion > solute > custom > interface priority; one
#   ``_*_result`` per ``_run_export_step`` call).
# - expected_molecules: subset that MUST appear in ``.top [molecules]`` +
#   ``.gro`` residues (SOL + MOL_H always; plus branch-specific molecules).
#   The custom branch is the ONLY one carrying the liquid custom molecule
#   ``MOL`` (the cmet-renamed etoh copy; the solute/ion chains are built from
#   custom-free interfaces). ``CH4_L`` appears in solute + ion because the
#   ion chain is built from the SOLUTE (real cross-tab flow, Tab 3 -> Tab 4,
#   CP-01) so the IonStructure carries the CH4 solutes.
# - extra_expected_itps: ITPs the CLI export stages beyond the always-present
#   tip4p-ice.itp + etoh.itp (MOL_H). ``cmet.itp`` = the custom molecule ITP
#   basename (copied with [atomtypes] commented by the custom branch);
#   ``ch4_liquid.itp`` = CH4 solutes (solute branch / ion-from-solute chain);
#   ``ion.itp`` = generated by the ion branch.
#
# NOTE: this is the CLI-side mirror of 48.3-10's ``_DOWNSTREAM_EXPORT_CASES``
# (GUI exporters); the function name carries the ``_cli_`` infix so the
# path-stripped GATE-IDs never collide with the GUI file's.
_DOWNSTREAM_BRANCH_CASES = [
    pytest.param(
        "custom",
        "_custom_result",
        {"SOL", "MOL_H", "MOL"},
        ("etoh.itp", "cmet.itp"),
        id="custom",
    ),
    pytest.param(
        "solute",
        "_solute_result",
        {"SOL", "MOL_H", "CH4_L"},
        ("etoh.itp", "ch4_liquid.itp"),
        id="solute",
    ),
    pytest.param(
        "ion",
        "_ion_result",
        {"SOL", "MOL_H", "CH4_L"},  # NA / CL asserted conditionally below
        ("etoh.itp", "ch4_liquid.itp", "ion.itp"),
        id="ion",
    ),
]


@gmx_skipif
@pytest.mark.parametrize(
    "branch_id,result_attr,expected_molecules,extra_expected_itps",
    _DOWNSTREAM_BRANCH_CASES,
)
@pytest.mark.parametrize("lattice_type", list(CUSTOM_GUEST_LATTICES))
def test_custom_guest_lattice_cli_downstream_export_grompp(
    custom_guest_chains,
    tmp_path,
    lattice_type,
    branch_id,
    result_attr,
    expected_molecules,
    extra_expected_itps,
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate with each of the 4
    non-sI lattices (sII, c2te, ice1hte, 16) exported via EACH of the 3
    downstream CLI export branches (custom / solute / ion), invoked as the
    Pattern-4 export-branch call (``CLIPipeline._run_export_step`` with ONE
    ``_<branch>_result`` set — priority selection ion > solute > custom >
    interface picks that branch).

    Phase 48.3 plan 48.3-11: closes the CLI half of Gap 1 (G1) — the
    ``_custom_result`` branch was NEVER run for non-sI lattices before this
    plan (45-VERIFICATION). Mirrors 48.3-10's GUI downstream tests
    (``test_e2e_custom_guest_lattices_gui.py``) and the 44.1-20 template's
    Pattern-4 invocation (``_make_cli_pipeline`` + one ``_result`` set per
    ``_run_export_step`` call, ``_output_dir`` to a tmp_path subdir —
    in-process, so tmp_path is allowed and stays Qt-free).

    Flow (each of the 12 parametrized cases):
      1. ``ws = tmp_path / lattice_type`` (pytest gives each parametrized
         invocation its own ``tmp_path``).
      2. ``pipe = _make_cli_pipeline(ws, chain.hydrate, result_attr,
         structure)`` -- ``hydrate`` carries the CUSTOM ``.config`` so
         ``_run_export_step`` builds ``cgi`` via
         ``_build_custom_guest_info`` and threads
         ``custom_guest_info=cgi`` to the per-branch writers.
      3. ``code = pipe._run_export_step()`` -- assert ``code == 0``.
      4. ``_assert_cli_downstream_export`` -- files + staged ITPs exist
         (transformed ``etoh.itp`` with moleculetype ``MOL_H`` +
         branch-specific ITPs); expected molecules in ``.top [molecules]``
         + ``.gro`` residues (no ``GUE``; NA/CL conditional for ion);
         ``_assert_mol_h_count_parity`` (the UAT Issue 3 desync guard);
         ``assert_itp_completeness`` + ``assert_gro_top_consistent``
         (always); ``gmx grompp`` rc == 0 (when gmx present).

    Key assertion: for each lattice × branch, the CLI export stages the
    transformed ``etoh.itp`` (moleculetype ``MOL_H``) + the ``.top``
    references ``MOL_H`` (not ``GUE``) + the MOL_H molecule count agrees
    between ``.top [molecules]`` and the ``.gro`` residues (== the
    slab-truncated ``guest_nmolecules``) + ``gmx grompp`` exits 0.
    """
    chain = custom_guest_chains[lattice_type]
    structure = getattr(chain, branch_id)
    ctx = f"{lattice_type}/{branch_id}"
    ws = tmp_path / lattice_type
    ws.mkdir()

    # 2. Construct the CLI pipeline with _hydrate_result=chain.hydrate (carries
    #    .config) + exactly ONE downstream _result set so _run_export_step's
    #    priority selection picks this branch (Pattern-4 invocation).
    pipe = _make_cli_pipeline(ws, chain.hydrate, result_attr, structure)

    # 3. Run the export step — must succeed (writers + ITP staging).
    code = pipe._run_export_step()
    assert code == 0, (
        f"[{ctx}] _run_export_step should succeed for the {branch_id} "
        f"branch with a custom cage guest"
    )

    # 4. Shared assertions: files + staged ITPs, expected molecules in .top
    #    [molecules] + .gro residues (no GUE), MOL_H count parity, file
    #    consistency, grompp rc == 0.
    _assert_cli_downstream_export(
        ws, branch_id, chain, expected_molecules, extra_expected_itps, ctx
    )
