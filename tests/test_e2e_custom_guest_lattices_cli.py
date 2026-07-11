"""E2E grompp test for a custom ethanol guest hydrate with non-sI lattices
through the CLI interface export.

Phase 45 plan 45-11. Proves that a custom ethanol guest hydrate with the 4
non-sI lattices that support custom guests (sII, c2te, ice1hte, 16) produces
grompp-valid output through the CLI Interface tab export
(``CLIPipeline._run_export_step`` called with ``_hydrate_result`` carrying
``.config`` so ``_build_custom_guest_info`` builds a ``list[dict]`` with
``MOL_H`` + ``copy_itp_files_for_structure`` stages the transformed
``etoh.itp``).

MIRRORS ``tests/test_e2e_custom_guest_cross_tab_cli.py`` (the 44.1-20 template)
but swaps sI -> parametrized 4 lattices and tests ONLY the interface export
branch (not the full interface -> solute -> ion chain — keep it focused and
small). The GUI half is 45-10 (``test_e2e_custom_guest_lattices_gui.py``);
this is the CLI half of Wave 4. Generation of custom ethanol with
sII/c2te/ice1hte/16 was verified OK in Phase 45 RESEARCH, but NOT through
interface + CLI export + grompp — this test closes that gap (Gap 6, CLI side).

CLI ``_run_export_step`` reads ``hydrate_config = getattr(self._hydrate_result,
"config", None)`` -> ``_build_custom_guest_info(config)`` returns a
``list[dict]`` for custom guests (``{'mol_type': 'etoh_e2e', 'residue_name':
'MOL_H', 'itp_path': Path(etoh.itp)}``) -> ``custom_guest_info`` threaded to
``write_interface_gro_file`` / ``write_interface_top_file``. ``copy_itp_files_for_structure``
dispatches on ``config.is_custom_guest`` -> copies + transforms the custom
``etoh.itp`` (41-07 custom branch, moleculetype ``MOL_H``).

Key assertion (the plan's core goal): for each lattice, the CLI export stages
the custom ITP (``etoh.itp`` transformed to moleculetype ``MOL_H``) + the
``.top`` references ``MOL_H`` (not ``GUE``) + ``gmx grompp`` exits 0.

``@gmx_skipif`` guards CI without gmx: file-consistency assertions
(``assert_itp_completeness`` + ``assert_gro_top_consistent``) always run;
grompp only when gmx is on PATH.

The test box is 3.0 x 3.0 x 8.0 nm (shortest vector 3.0 nm > 2 * rcoulomb =
2.0 nm in ``em.mdp``, satisfying grompp's PBC "cut-off longer than half the
shortest box vector" rule).
"""

import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
)
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    run_gmx_grompp,
    MDP_PATH,
    ETOH_GRO,
    ETOH_ITP,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
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
def custom_guest_chains():
    """Build the custom-ethanol-guest hydrate + slab interface ONCE per lattice.

    Amortizes the GenIce2 generation (``HydrateStructureGenerator.generate``)
    across the 4 parametrized export cases (per AGENTS.md testing guidance —
    GenIce2 is ~3-5s per lattice). Each lattice builds an independent
    ``HydrateConfig`` (same custom ethanol guest, different ``lattice_type``)
    -> gen -> candidate -> ``assemble_slab``.

    Box 3x3x8 nm: shortest vector 3.0 nm > 2 * cutoff (1.0 nm) for the grompp
    PBC rule (``rcoulomb=rvdw=1.0`` nm in ``em.mdp``). Deterministic
    (``seed=42``).

    MIRRORS the 44.1-20 template's custom ethanol config (lines 95-106),
    swapping ``lattice_type``. Use ETOH_GRO/ETOH_ITP absolute paths from
    e2e_export_helpers (CWD-independent). ``guest_residue_name="MOL"`` (3 chars)
    so the _H suffix yields ``"MOL_H"`` (5 chars, passes the GRO fixed-width
    limit).

    Returns a dict keyed by ``lattice_type`` ->
    ``SimpleNamespace(hydrate=hydrate, iface=iface, config=config)``. The
    ``hydrate`` carries ``.config`` (the custom HydrateConfig) so the CLI
    ``_run_export_step`` can read it via ``self._hydrate_result.config`` to
    build ``custom_guest_info``.
    """
    chains = {}
    for lattice_type in _LATTICES:
        gen = HydrateStructureGenerator()
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
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, iface=iface, config=config,
        )
    yield chains


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
@pytest.mark.parametrize("lattice_type", list(_LATTICES))
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
