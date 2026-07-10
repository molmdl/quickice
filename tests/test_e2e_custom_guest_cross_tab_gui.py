"""Full-chain GUI cross-tab e2e grompp test for a custom guest hydrate.

Phase 44.1 acceptance test (plan 44.1-19). Exercises the ENTIRE GUI export
workflow for a custom ethanol guest through ALL 4 GROMACS exporters
(interface -> solute -> custom-molecule -> ion) called with
``hydrate_config``, asserting grompp-valid output at every step.

This complements the per-exporter tests in
``tests/test_e2e_custom_guest_gui_grompp.py`` (plans 44.1-09 / 11 / 13 / 15),
each of which independently builds its own hydrate + interface.  This file
builds the hydrate (GenIce2) ONCE via a module-scoped fixture, then derives a
fresh interface per inserter (the ion inserter mutates
``iface.molecule_index`` at ``ion_inserter.py:259``, so each inserter gets its
own unmutated interface to avoid cross-contaminating the solute exporter's
``interface_structure.molecule_index`` reference), then runs each exporter
end-to-end via QFileDialog mocking.

Key assertion (the phase's core goal): EVERY export step stages the custom
ITP (``etoh.itp`` transformed to moleculetype ``MOL_H``) + the ``.top``
references ``MOL_H`` (not ``GUE``) + ``#include`` the transformed
``etoh.itp`` (not the non-existent ``guest.itp``).

``gmx`` IS on PATH so grompp runs (file-consistency always; grompp when gmx
present).  Marked ``@gmx_skipif`` so CI without gmx still runs file-consistency.
"""

import sys
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

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
from e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _insert_ions,
    _insert_solutes,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_includes,
    parse_top_molecules,
    run_gmx_grompp,
)


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: build hydrate (GenIce2) ONCE + fresh interface per
# inserter + all 3 inserter structures.
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def custom_guest_chain(tmp_path_factory):
    """Build the custom-ethanol-guest hydrate + slab interface + the 3 inserter
    structures (solute / custom-molecule / ion) ONCE per module.

    Amortizes the GenIce2 generation (``HydrateStructureGenerator.generate``)
    across the 4 parametrized export cases (per AGENTS.md testing guidance).
    A FRESH interface is derived per inserter via ``assemble_slab`` (the ion
    inserter mutates ``iface.molecule_index`` at ``ion_inserter.py:259``;
    giving each inserter its own unmutated interface avoids cross-
    contaminating the solute exporter's ``interface_structure.molecule_index``
    reference).  ``assemble_slab`` is deterministic with ``seed=42`` so every
    interface is identical.  All inserters return NEW structures (V-17
    compliant).

    Returns a dict with keys:
        config -- HydrateConfig (custom ethanol, etoh_e2e / MOL / 9 atoms)
        iface  -- InterfaceStructure (slab, 3x3x8 nm box >= 3.0 nm for PBC)
        solute -- SoluteStructure (CH4 solutes in the water region)
        custom -- CustomMoleculeStructure (1 renamed cmet molecule)
        ion    -- IonStructure (Na+ / Cl- in the water region)
    """
    # 1. Generate a real custom ethanol hydrate (sI 1x1x1, fast).  GenIce2 is
    #    the expensive call; amortized across all 4 parametrized cases.
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()

    # 2. Helper: derive a fresh slab interface from the shared candidate.
    #    Box 3x3x8 nm: shortest vector 3.0 nm > 2 * cutoff (1.0 nm) for grompp
    #    PBC rule (rcoulomb=rvdw=1.0 nm in em.mdp).  Deterministic (seed=42).
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

    # One interface for the interface exporter + one fresh interface per
    # inserter (ion inserter mutates iface.molecule_index -> isolation).
    iface = _make_iface()
    iface_solute = _make_iface()
    iface_custom = _make_iface()
    iface_ion = _make_iface()

    # Custom ethanol (9 atoms/mol) threaded correctly through slab (44.1-05).
    assert iface.guest_nmolecules > 0, "custom ethanol slab should have guests"
    assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
        f"custom ethanol slab guest_atom_count={iface.guest_atom_count} != "
        f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
    )

    # 3. SoluteStructure: CH4 solutes placed in the water region.
    #    SoluteInserter creates its own registry internally; it does NOT
    #    mutate the source interface (only reads via getattr).
    solute = _insert_solutes(iface_solute, solute_type='CH4', concentration=0.3)
    assert solute.n_molecules > 0, "solute inserter should place CH4 molecules"
    assert solute.interface_structure is not None, (
        "SoluteStructure.interface_structure must be populated for staging"
    )

    # 4. IonStructure: Na+ / Cl- replace water in the water region.
    #    IonInserter creates its own molecule_index internally (literal
    #    "guest" entries, ion_inserter.py:150-153) and propagates
    #    guest_atom_count / guest_nmolecules from the source interface
    #    (ion_inserter.py:243/287/312/538).  NOTE: replace_water_with_ions
    #    mutates iface_ion.molecule_index (ion_inserter.py:259) when the
    #    interface has no molecule_index (real GenIce2 data); isolated to
    #    iface_ion so the solute exporter's interface_structure ref is safe.
    ion = _insert_ions(iface_ion, concentration=0.15)
    assert (ion.na_count > 0 or ion.cl_count > 0), (
        "ion inserter should place Na+ / Cl- ions"
    )
    assert ion.guest_atom_count > 0, (
        "IonStructure.guest_atom_count must be propagated from the interface"
    )
    assert ion.guest_nmolecules > 0, (
        "IonStructure.guest_nmolecules must be propagated from the interface"
    )

    # 5. CustomMoleculeStructure: 1 custom molecule placed in the water region.
    #    Use a RENAMED COPY (cmet.gro/cmet.itp, moleculetype "MOL") to avoid
    #    the etoh.itp filename collision between the cage guest (staged as
    #    MOL_H via etoh.itp) and the custom molecule (copied with atomtypes
    #    commented).  Same workaround as plan 44.1-13.  The renamed copy lives
    #    in a module-scoped temp dir (the inserter needs the files to exist at
    #    fixture-setup time; function-scoped tmp_path is not yet available).
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

    cm_config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=cmet_gro,
        itp_path=cmet_itp,
        molecule_count=1,
    )
    inserter = CustomMoleculeInserter(cm_config, seed=42)
    custom = inserter.place_random(iface_custom, 1)
    assert custom.custom_molecule_count > 0, (
        "custom molecule inserter should place 1 molecule in the water region"
    )
    assert custom.guest_atom_count > 0, (
        "CustomMoleculeStructure.guest_atom_count must be propagated from the "
        "interface for the staging helper's presence gate"
    )

    return {
        "config": config,
        "iface": iface,
        "solute": solute,
        "custom": custom,
        "ion": ion,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized full-chain GUI export grompp (4 exporters)
# ══════════════════════════════════════════════════════════════════════════════

# Each case: (exporter_id, exporter_class, structure_key, expected_molecules,
#             extra_expected_itps)
# - expected_molecules: subset that MUST appear in .top [molecules] + .gro
#   residues (SOL + MOL_H always; plus exporter-specific molecules).
# - extra_expected_itps: ITPs the exporter writes/copies beyond the always-
#   present tip4p-ice.itp + etoh.itp (MOL_H).
_EXPORT_CASES = [
    pytest.param(
        "interface",
        InterfaceGROMACSExporter,
        "iface",
        {"SOL", "MOL_H"},
        (),
        id="interface",
    ),
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
        {"SOL", "MOL_H"},  # NA / CL asserted conditionally below
        ("ion.itp",),
        id="ion",
    ),
]


@gmx_skipif
@pytest.mark.parametrize(
    "exporter_id,exporter_class,structure_key,expected_molecules,"
    "extra_expected_itps",
    _EXPORT_CASES,
)
def test_custom_guest_gui_full_chain_grompp(
    custom_guest_chain,
    tmp_path,
    exporter_id,
    exporter_class,
    structure_key,
    expected_molecules,
    extra_expected_itps,
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via EACH of
    the 4 GUI exporters (interface / solute / custom-molecule / ion) called
    with ``hydrate_config``.

    Phase 44.1 GUI INTEGRATION acceptance test (plan 44.1-19).  The per-
    exporter tests in ``tests/test_e2e_custom_guest_gui_grompp.py`` (plans
    44.1-09 / 11 / 13 / 15) each independently build their own hydrate +
    interface; this test builds the hydrate (GenIce2) ONCE via a module-scoped
    fixture (amortizing the GenIce2 call across the 4 parametrized cases), then
    runs each exporter end-to-end via QFileDialog mocking.

    Flow (each parametrized case):
      1. ``exporter = {ExporterClass}(parent_widget=None)``.
      2. Mock ``QFileDialog.getSaveFileName`` (under
         ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` which makes the
         exporter return ``False`` without writing files) + ``QMessageBox``.
         The exporter calls ``getSaveFileName`` ONCE for the .gro path; .top
         is derived from ``path.stem``.
      3. ``ok = exporter.export_*_gromacs(structure, hydrate_config=config)``
         calls the shared helper ``_stage_hydrate_guest_itps`` (plan 44.1-08)
         which builds ``custom_guest_info`` from the config, transforms +
         writes ``etoh.itp`` (moleculetype ``MOL_H``, ``[atomtypes]``
         commented, ``[atoms]`` resname ``MOL_H``), and threads
         ``custom_guest_info`` to the writers.
      4. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (file
         consistency always runs).
      5. ``gmx grompp`` -> ``rc == 0`` (topology self-consistent + sim-ready).
      6. ``.top [molecules]`` + ``.gro`` residues contain ``SOL`` + ``MOL_H``
         (not ``GUE``) + exporter-specific molecules; ``.top`` ``#include``s
         ``etoh.itp`` (not the non-existent ``guest.itp``).

    Key assertion: EVERY export step stages the custom ITP + the ``.top``
    references ``MOL_H`` (not ``GUE``) + ``#include`` the transformed
    ``etoh.itp`` (not ``guest.itp``).
    """
    config = custom_guest_chain["config"]
    structure = custom_guest_chain[structure_key]

    # 1-2. Mock QFileDialog + QMessageBox so the exporter runs end-to-end
    #      without a real GUI.  getSaveFileName is called ONCE (single
    #      return_value patch suffices -- matches plans 44.1-09/11/13/15).
    gro_path = tmp_path / "output.gro"
    top_path = tmp_path / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = exporter_class(parent_widget=None)
        if exporter_id == "interface":
            ok = exporter.export_interface_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "solute":
            ok = exporter.export_solute_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "custom_molecule":
            ok = exporter.export_custom_molecule_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "ion":
            ok = exporter.export_ion_gromacs(
                structure, hydrate_config=config
            )
        else:  # pragma: no cover - exhaustive dispatcher
            raise AssertionError(f"unknown exporter_id: {exporter_id}")
        assert ok is True, (
            f"[{exporter_id}] export_{exporter_id}_gromacs returned False -- "
            f"export failed (QFileDialog mock may not have been picked up, or "
            f"staging raised)"
        )

    # 3. Files written by the exporter (writers + ITP staging).
    assert gro_path.exists(), f"[{exporter_id}] .gro not written: {gro_path}"
    assert top_path.exists(), f"[{exporter_id}] .top not written: {top_path}"
    assert (tmp_path / "tip4p-ice.itp").exists(), (
        f"[{exporter_id}] water ITP (tip4p-ice.itp) not staged by the exporter"
    )
    assert (tmp_path / "etoh.itp").exists(), (
        f"[{exporter_id}] custom guest ITP (etoh.itp) not staged by "
        f"_stage_hydrate_guest_itps"
    )
    for itp in extra_expected_itps:
        assert (tmp_path / itp).exists(), (
            f"[{exporter_id}] expected ITP '{itp}' not written/copied by the "
            f"exporter"
        )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh).  Prerequisite for grompp:
    # .top [molecules] lists MOL_H -> #include'd ITP must define MOL_H.
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        f"[{exporter_id}] staged etoh.itp is missing the MOL_H moleculetype "
        f"-- transform_guest_itp was not applied by _stage_hydrate_guest_itps"
    )

    # 4. Stage the MDP for grompp + run file-consistency assertions.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 5. Run gmx grompp -- must exit 0 (topology self-consistent + sim-ready).
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"[{exporter_id}] gmx grompp failed (GUI {exporter_class.__name__} "
        f"custom guest):\n{stderr}"
    )

    # 6. .top [molecules] + .gro residues contain the expected molecules
    #    (SOL + MOL_H always; plus exporter-specific).  GUE must NEVER appear
    #    (would mean custom_guest_info was NOT threaded to the writers).
    mols = parse_top_molecules(str(top_path))
    for mol in expected_molecules:
        assert mol in mols, (
            f"[{exporter_id}] expected '{mol}' in [molecules], got {mols}"
        )
    assert "GUE" not in mols, (
        f"[{exporter_id}] GUE must NOT appear in [molecules] "
        f"(custom_guest_info not threaded): {mols}"
    )
    # Ion case: NA / CL asserted conditionally (only when ions were placed).
    if exporter_id == "ion":
        ion_struct = custom_guest_chain["ion"]
        if ion_struct.na_count > 0:
            assert "NA" in mols, (
                f"[ion] expected NA in [molecules] (na_count>0), got {mols}"
            )
        if ion_struct.cl_count > 0:
            assert "CL" in mols, (
                f"[ion] expected CL in [molecules] (cl_count>0), got {mols}"
            )

    gro_res = set(parse_gro_residue_names(str(gro_path)))
    for mol in expected_molecules:
        assert mol in gro_res, (
            f"[{exporter_id}] expected '{mol}' in .gro residues, got {gro_res}"
        )
    assert "GUE" not in gro_res, (
        f"[{exporter_id}] GUE must NOT appear in .gro residues "
        f"(custom_guest_info not threaded): {gro_res}"
    )
    if exporter_id == "ion":
        ion_struct = custom_guest_chain["ion"]
        if ion_struct.na_count > 0:
            assert "NA" in gro_res, (
                f"[ion] expected NA in .gro residues (na_count>0), got {gro_res}"
            )
        if ion_struct.cl_count > 0:
            assert "CL" in gro_res, (
                f"[ion] expected CL in .gro residues (cl_count>0), got {gro_res}"
            )

    # 7. Key assertion: .top #includes the transformed etoh.itp (NOT the
    #    non-existent guest.itp).  This is the plan's must-have: "the .top
    #    references MOL_H (not GUE) + #include the transformed etoh.itp
    #    (not guest.itp)".
    includes = parse_top_includes(str(top_path))
    assert "etoh.itp" in includes, (
        f"[{exporter_id}] .top must #include 'etoh.itp' (the transformed "
        f"custom guest ITP), got {includes}"
    )
    assert "guest.itp" not in includes, (
        f"[{exporter_id}] .top must NOT #include the non-existent "
        f"'guest.itp' (custom_guest_info not threaded), got {includes}"
    )
