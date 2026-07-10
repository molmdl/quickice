"""Full CLI cross-tab e2e grompp chain for a custom guest hydrate.

Plan 44.1-20: the CLI integration acceptance test for Phase 44.1. Unlike the
per-branch tests in ``tests/test_e2e_custom_guest_cli_grompp.py`` (44.1-17)
which exercise each export branch (interface / custom / solute / ion) in
ISOLATION from a shared interface, this test runs the FULL CLI workflow chain
for a custom ethanol guest:

    hydrate generate (sI custom ethanol)
      -> to_candidate -> assemble_slab (interface)
      -> solute insert (CH4 solute from interface)
      -> ion insert (Na/Cl from SOLUTE -- the real workflow order, NOT from
         the interface directly)
      -> export EACH step (interface / solute / ion)

and asserts grompp-valid output + correct ITP staging (MOL_H, not GUE) at
every export link. This is the end-to-end CLI integration test that the
per-branch tests individually cannot provide: it verifies the solute->ion
hand-off (ion built from solute via ``_solute_to_ion_source``) preserves the
custom cage-guest metadata end-to-end so that the ion export still stages
``etoh.itp`` (moleculetype ``MOL_H``) and references ``MOL_H`` in
``[molecules]``.

``@gmx_skipif`` guards CI without gmx: file-consistency assertions
(``assert_itp_completeness`` + ``assert_gro_top_consistent``) always run;
grompp only when gmx is on PATH.

The test box is 3.0 x 3.0 x 8.0 nm (shortest vector 3.0 nm >= 3.0 nm, the
repo convention for grompp's PBC "cut-off longer than half the shortest box
vector" rule -- rcoulomb=rvdw=1.0 nm in em.mdp, so 3.0 > 2*1.0).
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
    ETOH_GRO,
    ETOH_ITP,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ══════════════════════════════════════════════════════════════════════════════
# Full CLI chain custom-guest e2e grompp (44.1-20)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def _full_chain_structures():
    """Module-scope fixture: the full custom-ethanol CLI chain built ONCE.

    Builds the real CLI workflow order:
        hydrate (sI custom ethanol) -> to_candidate -> assemble_slab (interface)
        -> solute insert (CH4 from interface) -> ion insert (Na/Cl from SOLUTE)

    The ion is built from the SOLUTE (via ``_insert_ions_from_solute`` ->
    ``_solute_to_ion_source``), NOT from the interface directly -- this is the
    key integration aspect that the per-branch tests (44.1-17) do not cover.
    ``_solute_to_ion_source`` propagates solute (+ custom-molecule) attributes
    onto ``solute.interface_structure`` (duck-typing) so ``IonInserter`` can
    access them. Because this fixture is module-scoped AND owned by this file
    (not shared with the per-branch test file), that mutation is contained.

    Returns ``(hydrate, iface, solute, ion)``. ``hydrate`` carries ``.config``
    (the HydrateConfig the CLI reads via ``self._hydrate_result.config`` to
    build ``custom_guest_info``). Uses ABSOLUTE ``guest_gro_path`` /
    ``guest_itp_path`` (via ETOH_GRO/ETOH_ITP) so ITP staging is CWD-independent,
    matching the convention in ``test_e2e_custom_guest_cli_grompp.py``.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
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
    # Custom ethanol (9 atoms/mol) threaded through slab (44.1-05).
    assert iface.guest_nmolecules > 0, "custom ethanol slab should have guests"
    assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
        f"custom ethanol slab guest_atom_count={iface.guest_atom_count} != "
        f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
    )

    # Chain: interface -> solute (CH4) -> ion (Na/Cl from SOLUTE, real workflow)
    solute = _insert_solutes(iface, solute_type='CH4', concentration=0.3)
    assert solute.n_molecules > 0, (
        "solute inserter should place CH4 molecules in the water region"
    )
    assert solute.interface_structure is not None, (
        "SoluteStructure.interface_structure must be populated for ion chaining"
    )

    ion = _insert_ions_from_solute(solute, concentration=0.15)
    assert (ion.na_count > 0 or ion.cl_count > 0), (
        "ion inserter should place Na+ / Cl- ions in the water region"
    )
    # IonStructure (types.py) has NO interface_structure field -- it carries
    # its own guest_atom_count/guest_nmolecules propagated by IonInserter from
    # the source interface (44.1-15). Required for the custom-guest staging block.
    assert ion.guest_atom_count > 0, (
        "IonStructure.guest_atom_count must be propagated from the source "
        "interface for the custom-guest staging block"
    )
    assert ion.guest_nmolecules > 0, (
        "IonStructure.guest_nmolecules must be propagated from the source "
        "interface for the custom-guest staging block"
    )
    return hydrate, iface, solute, ion


def _make_cli_pipeline(output_dir, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and a single downstream structure set so ``_run_export_step``'s
    priority selection (ion > solute > custom > interface > hydrate > ice)
    picks that branch. All other ``_*_result`` stay at their ``__init__``
    default of ``None``.
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = output_dir
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


def _assert_step_output(ws, step_name, hydrate, structure, attr,
                        extra_mols=None, extra_itp=None):
    """Export ``structure`` via ``CLIPipeline._run_export_step`` into ``ws``
    and assert file-consistency + grompp + correct ITP staging (MOL_H, not GUE).

    Args:
        ws: Per-step output directory (isolated so each grompp sees only its
            own ITP set).
        step_name: ``"interface"`` / ``"solute"`` / ``"ion"`` -- sets the
            ``.gro``/``.top`` basename + the ``_run_export_step`` branch.
        hydrate: The hydrate structure carrying ``.config`` (for cgi threading).
        structure: The downstream structure to export.
        attr: The ``CLIPipeline`` attribute to set (``"_interface_result"`` etc.).
        extra_mols: Extra molecule names expected in ``[molecules]`` + ``.gro``
            residues beyond SOL + MOL_H (e.g. ``["CH4_L"]``, ``["NA", "CL"]``).
        extra_itp: Extra ITP filenames expected to be staged beyond
            tip4p-ice.itp + etoh.itp (e.g. ``["ch4_liquid.itp"]``, ``["ion.itp"]``).
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
    assert (ws / "etoh.itp").exists(), (
        "cage-guest etoh.itp not staged by the custom-guest block"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H) --
    # NOT the under-transformed source (moleculetype etoh) and NOT GUE/guest.itp.
    staged_etoh = (ws / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp missing MOL_H moleculetype -- copy_custom_guest_itp "
        "was not applied by the custom-guest staging block"
    )
    if extra_itp:
        for itp in extra_itp:
            assert (ws / itp).exists(), (
                f"{itp} not staged for the {step_name} branch"
            )

    # Stage MDP + file-consistency assertions (always run, even without gmx).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top), ws)
    assert_gro_top_consistent(str(gro), str(top))

    # gmx grompp -> rc == 0 (topology self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file=f"{step_name}.gro", top_file=f"{step_name}.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (CLI {step_name} custom guest):\n{stderr}"
    )

    # [molecules] contains SOL + MOL_H (+ extra mols); NO GUE.
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules] ({step_name}), got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] ({step_name}, custom_guest_info "
        f"not threaded): {mols}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in mols, (
                f"expected {mol} in [molecules] ({step_name}): {mols}"
            )

    # .gro residues contain SOL + MOL_H (+ extra); NO GUE.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues ({step_name}), got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues ({step_name}, "
        f"custom_guest_info not threaded): {gro_res}"
    )
    if extra_mols:
        for mol in extra_mols:
            assert mol in gro_res, (
                f"expected {mol} in .gro residues ({step_name}): {gro_res}"
            )


@gmx_skipif
def test_custom_guest_cli_full_chain_grompp(tmp_path, _full_chain_structures):
    """Full CLI chain: custom ethanol hydrate -> interface -> solute -> ion -> export.

    Exports EACH step (interface / solute / ion) to its own isolated subdir and
    asserts grompp-valid output + correct ITP staging (MOL_H, not GUE) at every
    link. The ion is built from the SOLUTE (real CLI workflow order), not the
    interface directly -- the integration aspect the per-branch tests
    (44.1-17) don't cover. This proves the custom cage-guest metadata survives
    the full hydrate -> interface -> solute -> ion chain so every export step
    stages ``etoh.itp`` (MOL_H) and references ``MOL_H`` in ``[molecules]``.
    """
    hydrate, iface, solute, ion = _full_chain_structures

    # 1) Interface export (SOL + MOL_H; tip4p-ice.itp + etoh.itp).
    _assert_step_output(
        tmp_path / "interface", "interface", hydrate, iface, "_interface_result",
    )

    # 2) Solute export (SOL + MOL_H + CH4_L; + ch4_liquid.itp).
    _assert_step_output(
        tmp_path / "solute", "solute", hydrate, solute, "_solute_result",
        extra_mols=["CH4_L"], extra_itp=["ch4_liquid.itp"],
    )

    # 3) Ion export (SOL + MOL_H + NA/CL; + ion.itp). Built from SOLUTE.
    #    Only assert the ion species actually placed (Na+ and/or Cl-).
    ion_extras = []
    if ion.na_count > 0:
        ion_extras.append("NA")
    if ion.cl_count > 0:
        ion_extras.append("CL")
    _assert_step_output(
        tmp_path / "ion", "ion", hydrate, ion, "_ion_result",
        extra_mols=ion_extras, extra_itp=["ion.itp"],
    )
