"""E2E grompp test for a custom ethanol guest hydrate with non-sI lattices.

Phase 45 plan 45-10. Proves that a custom ethanol guest hydrate with the 4
non-sI lattices that support custom guests (sII, c2te, ice1hte, 16) produces
grompp-valid output through the GUI Interface tab export
(``InterfaceGROMACSExporter.export_interface_gromacs`` called with the CUSTOM
``hydrate_config`` so ``_stage_hydrate_guest_itps`` builds
``custom_guest_info`` with ``MOL_H`` + stages the transformed ``etoh.itp``).

MIRRORS ``tests/test_e2e_custom_guest_cross_tab_gui.py`` (the 44.1-19 template)
but swaps sI -> parametrized 4 lattices and tests ONLY the interface export
(not all 4 exporters — keep it focused and small). Generation of custom
ethanol with sII/c2te/ice1hte/16 was verified OK in Phase 45 RESEARCH, but
NOT through interface + export + grompp — this test closes that gap (Gap 6).

Key assertion (the plan's core goal): for each lattice, the export stages the
custom ITP (``etoh.itp`` transformed to moleculetype ``MOL_H``) + the ``.top``
references ``MOL_H`` (not ``GUE``) + ``gmx grompp`` exits 0.

``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter tests (no
display). ``QFileDialog.getSaveFileName`` returns ``("", "")`` under offscreen
-> the exporter returns ``False`` without writing files. Inline patching of
``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED (the
``mock_save_dialog`` fixture from ``tests/test_output/conftest.py`` is
directory-scoped and NOT available to root-level test files).
``gmx`` IS on PATH so grompp runs. Marked ``@gmx_skipif`` so CI without gmx
still collects the test (skipped).
"""

import sys
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
from quickice.gui.export import InterfaceGROMACSExporter  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
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

    Returns a dict keyed by ``lattice_type`` ->
    ``SimpleNamespace(hydrate=hydrate, iface=iface, config=config)``.
    """
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
