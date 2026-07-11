"""Full CLI cross-tab e2e grompp chain for 4 new guest-bearing lattices.

Plan 45-05 (Wave 2): the CLI half of the full-chain acceptance for the 4 new
guest-bearing lattice types from Phase 39 (sII, c2te, ice1hte, 16). Unlike the
per-branch CLI tests (which exercise each export branch in ISOLATION), this
test runs the FULL CLI workflow chain for each lattice with the BUILT-IN ch4
cage guest:

    hydrate generate (lattice, built-in ch4)
      -> to_candidate -> assemble_slab (interface)
      -> solute insert (CH4 solute from interface)
      -> ion insert (Na/Cl from SOLUTE -- the real CLI workflow order, NOT
         from the interface directly, via ``_insert_ions_from_solute``)
      -> export EACH step (interface / solute / ion)

and asserts grompp-valid output + correct built-in ITP staging
(``ch4_hydrate.itp``, residue ``CH4_H`` -- NOT ``etoh.itp`` / ``MOL_H`` /
``GUE``) at every export link. This MIRRORS ``test_e2e_custom_guest_cross_tab_cli.py``
(the 44.1-20 template) but swaps the single sI custom-ethanol case -> a
parametrized 4-lattice matrix (sII / c2te / ice1hte / 16), all with built-in
``guest_type="ch4"`` (NOT custom).

The integration aspect this test covers (that the per-branch tests do not) is
the solute -> ion hand-off: the ion is built from the SOLUTE (via
``_insert_ions_from_solute`` -> ``_solute_to_ion_source``), NOT from the
interface directly. ``_solute_to_ion_source`` propagates solute (+ custom-
molecule) attributes onto ``solute.interface_structure`` (duck-typing) so
``IonInserter`` can access them. This proves the built-in cage-guest metadata
survives the full hydrate -> interface -> solute -> ion chain so every CLI
export step stages ``ch4_hydrate.itp`` and references ``CH4_H`` in
``[molecules]``.

``@gmx_skipif`` guards CI without gmx: file-consistency assertions
(``assert_itp_completeness`` + ``assert_gro_top_consistent``) always run;
grompp only when gmx is on PATH. The helper ALSO guards the grompp call with
``shutil.which("gmx")`` so file-consistency + guest-residue asserts run
whenever the test runs (belt-and-suspenders with ``@gmx_skipif``).

The test box is 3.0 x 3.0 x 8.0 nm (shortest vector 3.0 nm >= 2*rcoulomb=2.0 nm
in em.mdp -- the grompp PBC "cut-off longer than half the shortest box vector"
rule). The 1x1x1 supercell is sufficient for these 4 non-triclinic guest
lattices (Pitfall 1 only affects the triclinic filled ices c0te/c1te, which
are blocked at the interface and covered by separate plans).

Pitfalls avoided (45-RESEARCH.md):
- Pitfall 4 (GRO atom-number wrap at 100,000): NOT asserted --
  ``assert_gro_top_consistent`` counts atom LINES, not the header, so it is
  robust to the 100,000 wrap (cosmetic; grompp still rc=0).
- Pitfall 5 (guest counts vary by lattice/version): do NOT assert exact
  guest/solute/ion counts -- assert ``> 0`` only.
- Ion built from SOLUTE (real CLI workflow order via
  ``_insert_ions_from_solute``), NOT from the interface directly -- this is
  the integration aspect the per-branch tests don't cover.
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
    _insert_solutes,
    _insert_ions_from_solute,
    run_gmx_grompp,
    MDP_PATH,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# -- The 4 new guest-bearing lattices under test ------------------------------
# Water-only lattices (sTprime, 17) are excluded here (no cage guests for the
# built-in ch4 path) -- they are covered by separate plans. sH is covered by
# 45-03. The triclinic filled ices c0te/c1te are blocked at the interface tab
# (covered by separate plans).

_ALL_LATTICES = ("sII", "c2te", "ice1hte", "16")


# -- Module-scoped fixture: build full chains for ALL 4 lattices ONCE ---------


@pytest.fixture(scope="module")
def lattice_chains():
    """Module-scope fixture: the full CLI chain built ONCE for EACH of the 4
    new guest-bearing lattice types, amortizing the GenIce2 + assemble_slab +
    inserter calls (~1-5s each) across all parametrized export cases (per
    AGENTS.md testing guidance).

    Builds the real CLI workflow order for each lattice:
        hydrate (built-in ch4) -> to_candidate -> assemble_slab (interface)
        -> solute insert (CH4 from interface)
        -> ion insert (Na/Cl from SOLUTE -- the real workflow order, NOT from
           the interface directly)

    The ion is built from the SOLUTE (via ``_insert_ions_from_solute`` ->
    ``_solute_to_ion_source``), NOT from the interface directly -- this is the
    key integration aspect that the per-branch CLI tests do not cover.
    ``_solute_to_ion_source`` propagates solute (+ custom-molecule) attributes
    onto ``solute.interface_structure`` (duck-typing) so ``IonInserter`` can
    access them. Because this fixture is module-scoped AND owned by this file
    (not shared with the per-branch test file), that mutation is contained.

    Returns ``dict {lattice_type: SimpleNamespace}`` where each namespace
    carries ``hydrate`` (with ``.config`` -- the built-in ``HydrateConfig`` the
    CLI reads via ``self._hydrate_result.config`` to build
    ``custom_guest_info``; ``_build_custom_guest_info(config)`` returns ``None``
    for built-in ch4 -> ``custom_guest_info=None`` -> built-in path), ``iface``,
    ``solute``, ``ion``, and ``config``.

    All 4 lattices are guest-bearing -> each slab must carry cage guests
    (assert ``> 0``, NOT exact -- Pitfall 5: counts vary by lattice/version).
    """
    chains = {}
    for lattice_type in _ALL_LATTICES:
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",  # BUILT-IN ch4 (NOT custom) -> ch4_hydrate.itp
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
        # All 4 lattices are guest-bearing -> slab must carry cage guests
        # (assert > 0, NOT exact -- Pitfall 5: counts vary by lattice/version).
        assert iface.guest_nmolecules > 0, (
            f"{lattice_type} interface slab should have built-in ch4 cage "
            f"guests"
        )

        # Chain: interface -> solute (CH4) -> ion (Na/Cl from SOLUTE, real
        # CLI workflow order -- NOT from the interface directly).
        solute = _insert_solutes(iface, solute_type="CH4", concentration=0.3)
        assert solute.n_molecules > 0, (
            f"{lattice_type}: solute inserter should place CH4 molecules in "
            f"the water region"
        )
        assert solute.interface_structure is not None, (
            f"{lattice_type}: SoluteStructure.interface_structure must be "
            f"populated for ion chaining"
        )

        ion = _insert_ions_from_solute(solute, concentration=0.15)
        assert (ion.na_count > 0 or ion.cl_count > 0), (
            f"{lattice_type}: ion inserter should place Na+ / Cl- ions in "
            f"the water region"
        )
        # IonStructure (types.py) has NO interface_structure field -- it
        # carries its own guest_atom_count/guest_nmolecules propagated by
        # IonInserter from the source interface (44.1-15). Required for the
        # built-in guest staging block (copy_itp_files_for_structure reads
        # these to stage ch4_hydrate.itp).
        assert ion.guest_atom_count > 0, (
            f"{lattice_type}: IonStructure.guest_atom_count must be "
            f"propagated from the source interface for the built-in guest "
            f"staging block"
        )
        assert ion.guest_nmolecules > 0, (
            f"{lattice_type}: IonStructure.guest_nmolecules must be "
            f"propagated from the source interface for the built-in guest "
            f"staging block"
        )
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            solute=solute,
            ion=ion,
            config=config,
        )
    yield chains


# -- CLI export-step-direct helpers (copied from the 44.1-20 template) --------


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and a single downstream structure set so ``_run_export_step``'s
    priority selection (ion > solute > custom > interface > hydrate > ice)
    picks that branch. All other ``_*_result`` stay at their ``__init__``
    default of ``None``.

    Mirrors the helper in ``tests/test_e2e_custom_guest_cross_tab_cli.py``
    (the 44.1-20 template, lines 155-166).
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


def _assert_step_output(ws, step_name, hydrate, structure, attr,
                        extra_mols=None, extra_itp=None):
    """Export ``structure`` via ``CLIPipeline._run_export_step`` into ``ws``
    and assert file-consistency + grompp + correct BUILT-IN ch4 ITP staging
    (``ch4_hydrate.itp`` + residue ``CH4_H``, NOT ``etoh.itp`` / ``MOL_H`` /
    ``GUE``).

    Adapted from the 44.1-20 template (``test_e2e_custom_guest_cross_tab_cli.py``
    lines 169-260), swapping the custom-guest staging assertions (etoh.itp +
    MOL_H) for the built-in ch4 staging assertions (ch4_hydrate.itp + CH4_H).

    Args:
        ws: Per-step output directory (isolated so each grompp sees only its
            own ITP set).
        step_name: ``"interface"`` / ``"solute"`` / ``"ion"`` -- sets the
            ``.gro``/``.top`` basename + the ``_run_export_step`` branch.
        hydrate: The hydrate structure carrying ``.config`` (the built-in
            ``HydrateConfig`` with ``guest_type="ch4"`` -> ``cgi=None`` -> the
            built-in path stages ``ch4_hydrate.itp`` + references ``CH4_H``).
        structure: The downstream structure to export.
        attr: The ``CLIPipeline`` attribute to set (``"_interface_result"`` etc.).
        extra_mols: Extra molecule names expected in ``[molecules]`` + ``.gro``
            residues beyond SOL + CH4_H (e.g. ``["CH4_L"]``, ``["NA", "CL"]``).
        extra_itp: Extra ITP filenames expected to be staged beyond
            tip4p-ice.itp + ch4_hydrate.itp (e.g. ``["ch4_liquid.itp"]``,
            ``["ion.itp"]``).
    """
    # The subdir does not exist yet -- _run_export_step writes to
    # self._output_dir / f"{step_name}.gro" but does NOT create the dir (only
    # CLIPipeline.execute() does). The per-branch tests pass tmp_path directly
    # (pytest creates it); our per-step subdirs must be mkdir'd here.
    ws.mkdir(parents=True, exist_ok=True)
    pipe = _make_cli_pipeline(ws, hydrate, attr, structure)
    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step should succeed for the {step_name} branch"
    )

    gro = ws / f"{step_name}.gro"
    top = ws / f"{step_name}.top"
    assert gro.exists(), f"{step_name}.gro not written: {gro}"
    assert top.exists(), f"{step_name}.top not written: {top}"
    assert (ws / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"
    # Built-in ch4 guest ITP staged (NOT a custom ITP). The CLI
    # copy_itp_files_for_structure (hydrate_config=built-in) copies the
    # bundled pre-transformed ch4_hydrate.itp for the built-in path.
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"built-in cage-guest ch4_hydrate.itp not staged for the "
        f"{step_name} branch"
    )
    # The staged ch4_hydrate.itp must define the built-in moleculetype CH4_H
    # -- NOT MOL_H (custom-guest path) and NOT GUE/guest.itp (fallback).
    staged_ch4 = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_ch4, (
        f"staged ch4_hydrate.itp missing CH4_H moleculetype -- the built-in "
        f"ITP must define CH4_H"
    )
    assert "MOL_H" not in staged_ch4, (
        f"MOL_H (custom-guest moleculetype) found in staged ch4_hydrate.itp "
        f"-- regression: the built-in path must NOT produce MOL_H"
    )
    if extra_itp:
        for itp in extra_itp:
            assert (ws / itp).exists(), (
                f"{itp} not staged for the {step_name} branch"
            )

    # Stage MDP + file-consistency assertions (always run, even without gmx).
    # assert_gro_top_consistent counts atom LINES, not the .gro header
    # atom-count field, so it is robust to the GRO 100,000 atom-number wrap
    # (Pitfall 4 -- cosmetic, grompp still rc=0).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top), ws)
    assert_gro_top_consistent(str(gro), str(top))

    # gmx grompp -> rc == 0 (topology self-consistent + simulation-ready).
    # Guarded by shutil.which("gmx") so file-consistency + guest-residue
    # asserts run whenever the test runs (belt-and-suspenders with
    # @gmx_skipif on the test).
    if shutil.which("gmx"):
        exit_code, stderr = run_gmx_grompp(
            ws, gro_file=f"{step_name}.gro", top_file=f"{step_name}.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed (CLI {step_name}, built-in ch4):\n{stderr}"
        )

    # [molecules] contains SOL + CH4_H (+ extra mols); NO GUE / MOL_H.
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "CH4_H" in mols, (
        f"expected SOL + CH4_H in [molecules] ({step_name}), got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] ({step_name}, built-in path): "
        f"{mols}"
    )
    assert "MOL_H" not in mols, (
        f"MOL_H must NOT appear in [molecules] ({step_name}, built-in path): "
        f"{mols}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in mols, (
                f"expected {mol} in [molecules] ({step_name}): {mols}"
            )

    # .gro residues contain SOL + CH4_H (+ extra); NO GUE / MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "CH4_H" in gro_res, (
        f"expected SOL + CH4_H in .gro residues ({step_name}), got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues ({step_name}, built-in path): "
        f"{gro_res}"
    )
    assert "MOL_H" not in gro_res, (
        f"MOL_H must NOT appear in .gro residues ({step_name}, built-in "
        f"path): {gro_res}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in gro_res, (
                f"expected {mol} in .gro residues ({step_name}): {gro_res}"
            )


# -- Parametrized CLI full cross-tab (3 branches) + grompp test --------------


@gmx_skipif
@pytest.mark.parametrize("lattice_type", list(_ALL_LATTICES))
def test_lattice_cross_tab_cli_grompp(tmp_path, lattice_chains, lattice_type):
    """gmx grompp exits 0 on the FULL CLI cross-tab chain (Interface -> Solute
    -> Ion -> Export) for each of the 4 new guest-bearing lattice types
    (sII / c2te / ice1hte / 16), all with built-in ``guest_type="ch4"`` (NOT
    custom).

    For each of the 3 CLI export branches (interface / solute / ion), the
    test:
      1. Constructs a ``CLIPipeline`` with ``_hydrate_result`` set to the
         built-in hydrate (carries ``.config`` -- a built-in ``HydrateConfig``
         with ``guest_type="ch4"``) and the downstream structure set on the
         target ``_*_result`` attribute.
      2. Calls ``_run_export_step()`` directly (the export-step-direct approach
         from the 44.1-20 template). ``_run_export_step`` reads
         ``hydrate_config = getattr(self._hydrate_result, "config", None)`` ->
         the built-in ``HydrateConfig``. ``_build_custom_guest_info(config)``
         returns ``None`` for built-in ch4 -> ``custom_guest_info=None`` ->
         built-in residue name (``CH4_H``) + bundled ``ch4_hydrate.itp``
         staged via ``copy_itp_files_for_structure``, byte-identical to the
         pre-44.1 built-in path.
      3. ``_assert_step_output(...)`` asserts the built-in guest ITP is staged
         + referenced (``CH4_H``, ``ch4_hydrate.itp``), NO ``GUE`` / ``MOL_H``
         leak, file consistency passes, and ``gmx grompp`` exits 0.

    The ion is built from the SOLUTE (real CLI workflow order via
    ``_insert_ions_from_solute``), NOT from the interface directly -- the
    integration aspect the per-branch CLI tests don't cover. This proves the
    built-in cage-guest metadata survives the full hydrate -> interface ->
    solute -> ion chain so every CLI export step stages ``ch4_hydrate.itp``
    and references ``CH4_H`` in ``[molecules]``.

    Box is 3.0x3.0x8.0 nm (shortest vector 3.0 nm > 2*rcoulomb=2.0 nm --
    grompp PBC rule). The 1x1x1 supercell is sufficient for these 4
    non-triclinic guest lattices (Pitfall 1 only affects the triclinic filled
    ices c0te/c1te, which are blocked and covered by separate plans).
    """
    chain = lattice_chains[lattice_type]

    # 1) Interface export (SOL + CH4_H; tip4p-ice.itp + ch4_hydrate.itp).
    _assert_step_output(
        tmp_path / "interface", "interface", chain.hydrate, chain.iface,
        "_interface_result",
    )

    # 2) Solute export (SOL + CH4_H + CH4_L; + ch4_liquid.itp).
    _assert_step_output(
        tmp_path / "solute", "solute", chain.hydrate, chain.solute,
        "_solute_result", extra_mols=["CH4_L"], extra_itp=["ch4_liquid.itp"],
    )

    # 3) Ion export (SOL + CH4_H + NA/CL; + ion.itp). Built from SOLUTE (real
    #    CLI workflow order via _insert_ions_from_solute, NOT from the
    #    interface directly). Only assert the ion species actually placed
    #    (Na+ and/or Cl-).
    ion_extras = []
    if chain.ion.na_count > 0:
        ion_extras.append("NA")
    if chain.ion.cl_count > 0:
        ion_extras.append("CL")
    _assert_step_output(
        tmp_path / "ion", "ion", chain.hydrate, chain.ion, "_ion_result",
        extra_mols=ion_extras, extra_itp=["ion.itp"],
    )
