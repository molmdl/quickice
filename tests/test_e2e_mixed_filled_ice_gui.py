"""E2E filled-ice (c2te, ice1hte) single-cage-key GUI hydrate export + grompp.

Plan 45-14 (wave 6). Proves that filled-ice lattices with a SINGLE cage key
(``cage_type_map = {"small": "Ne1"}`` — one entry, NOT "small"+"large" like
sI/sII) produce grompp-valid output through the GUI
``HydrateGROMACSExporter.export_hydrate`` with built-in CH4 in the single
cage.

Purpose: c2te and ice1hte are filled ices (Teeratchanan 2015) with a SINGLE
cage_type_map entry. Unlike sI/sII (which have "small"+"large"), these have
only "small" (mapping to the GenIce2 cage id "Ne1"). The ``cages`` display
dict uses the human-readable key "guest" (the cage NAME), but
``cage_type_map`` (the GenIce2 cage ID mapping used for guest placement) uses
"small". Guest placement goes through ``parse_guest`` (not ``spot_guests``)
per the Phase 39-02 decision — single-entry cage_type_map prevents
double-placement. This test verifies that single-cage-key path works through
the full GUI export chain + grompp.

This complements 45-13 (which tests 2-cage-type lattices sII/16 with mixed
CH4+THF). Here there is only ONE cage key, so "mixed" is about verifying the
single-cage-key path — NOT mixing two different guest types (there's only one
cage to fill).

Pitfall 1 (box-size, CRITICAL — empirically verified): c2te/ice1hte at
1x1x1 have shortest box vectors of ~0.88 nm and ~0.69 nm respectively,
FAR below 2*rcoulomb = 2.0 nm — grompp fatal-errors with "cut-off length
is longer than half the shortest box vector". The plan suggested 2x2x2, but
empirical testing showed 2x2x2 STILL fails (c2te 2x2x2 = 1.76 nm, ice1hte
2x2x2 = 1.38 nm — both < 2.0 nm). Even 3x3x3 fails for ice1hte (2.07 nm —
GROMACS's check is stricter than the simple shortest-vector test for
non-orthogonal cells). The verified minimum supercells are:
  - c2te 3x3x3: shortest = 2.65 nm -> grompp rc=0 (7776 atoms)
  - ice1hte 4x4x4: shortest = 2.76 nm -> grompp rc=0 (6656 atoms)
Using per-lattice supercell sizes (c2te=3x3x3, ice1hte=4x4x4) minimizes atom
count while ensuring grompp passes.

Pitfall 6 (two export paths): the GUI hydrate exporter uses
``write_multi_molecule_*`` (this test); the CLI hydrate branch wraps in an
``InterfaceStructure`` + ``write_interface_*`` (different path, tested
elsewhere). Do NOT conflate the two.

Module-scoped fixture amortizes the GenIce2 calls (~0.1-0.3s each) across
the parametrized cases per AGENTS.md testing guidance.
``QT_QPA_PLATFORM=offscreen`` is required for the GUI exporter (no display).
``QFileDialog.getSaveFileName`` returns ``("", "")`` under offscreen ->
exporter returns False without writing, so inline patching of
``QFileDialog.getSaveFileName`` + ``QMessageBox`` is REQUIRED.
``gmx`` is on PATH so grompp runs (``@gmx_skipif`` skips when absent).
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
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    HYDRATE_LATTICES,
)
from tests.conftest import gmx_skipif  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ══════════════════════════════════════════════════════════════════════════════
# Per-lattice supercell sizes (Pitfall 1 — empirically verified minimums)
# ══════════════════════════════════════════════════════════════════════════════

# c2te 1x1x1 shortest = 0.88 nm, 2x2x2 = 1.76 nm, 3x3x3 = 2.65 nm (PASSES).
# ice1hte 1x1x1 shortest = 0.69 nm, 2x2x2 = 1.38 nm, 3x3x3 = 2.07 nm (FAILS
#   — GROMACS's check is stricter than the simple vector-length test for
#   non-orthogonal cells), 4x4x4 = 2.76 nm (PASSES).
# Using per-lattice minimums minimizes atom count while ensuring grompp rc=0.
_FILLED_ICE_SUPERCELLS = {
    "c2te": (3, 3, 3),
    "ice1hte": (4, 4, 4),
}


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: build c2te + ice1hte single-cage-key hydrate structures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def filled_ice_hydrates():
    """Module-scoped: generate c2te + ice1hte hydrate structures with built-in
    CH4 in the single "small" cage ONCE, amortizing the GenIce2 calls across
    both parametrized GUI export cases.

    CRITICAL: c2te/ice1hte have ``cage_type_map = {"small": "Ne1"}`` — a
    SINGLE key. The ``cages`` display dict uses the human-readable key
    "guest" (the cage NAME), but ``cage_type_map`` (the GenIce2 cage ID
    mapping used for guest placement via ``parse_guest``) uses "small". The
    ``cage_guest_assignments`` dict MUST use "small" as the key (matching
    ``cage_type_map``) — using "guest" produces 0 guests because the hydrate
    generator's ``_run_via_api`` skips cage keys not present in
    ``cage_type_map`` (warning: "cage_key 'guest' not in cage_type_map").

    Per-lattice supercell sizes (Pitfall 1 — empirically verified):
      - c2te 3x3x3: shortest = 2.65 nm > 2.0 nm -> grompp rc=0 (7776 atoms)
      - ice1hte 4x4x4: shortest = 2.76 nm > 2.0 nm -> grompp rc=0 (6656 atoms)
    The plan's suggested 2x2x2 fails for BOTH (c2te=1.76 nm, ice1hte=1.38 nm —
    both < 2.0 nm); ice1hte even fails at 3x3x3 (2.07 nm) due to GROMACS's
    stricter non-orthogonal cell check.

    Returns ``dict {"c2te": SimpleNamespace(hydrate=..., config=...),
    "ice1hte": SimpleNamespace(hydrate=..., config=...)}`` where each
    namespace carries the ``HydrateStructure`` + the ``HydrateConfig`` used
    to generate it (the GUI exporter needs both).
    """
    chains = {}
    for lattice_type in ("c2te", "ice1hte"):
        gen = HydrateStructureGenerator()
        nx, ny, nz = _FILLED_ICE_SUPERCELLS[lattice_type]
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",  # primary (legacy) — ch4 is built-in
            cage_guest_assignments={
                # "small" matches cage_type_map key (NOT "guest" — the cages
                # display dict uses "guest", but cage_type_map uses "small").
                "small": CageGuestAssignment(
                    guest_type="ch4", occupancy=100.0
                ),
            },
            supercell_x=nx,  # Pitfall 1: per-lattice minimum supercell.
            supercell_y=ny,
            supercell_z=nz,
        )
        hydrate = gen.generate(config)
        # Sanity: filled-ice single cage should place CH4 guests.
        assert hydrate.guest_count > 0, (
            f"{lattice_type} filled-ice should have cage guests, "
            f"got guest_count={hydrate.guest_count} (check cage key — "
            f"cage_type_map={HYDRATE_LATTICES[lattice_type]['cage_type_map']})"
        )
        mol_types = {m.mol_type for m in hydrate.molecule_index}
        assert "ch4" in mol_types, (
            f"{lattice_type} should place ch4, got mol_types={mol_types}"
        )
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, config=config
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized GUI hydrate export + grompp test (c2te + ice1hte)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lattice_type", ["c2te", "ice1hte"])
@gmx_skipif
def test_filled_ice_single_cage_gui_grompp(
    tmp_path, filled_ice_hydrates, lattice_type
):
    """gmx grompp exits 0 on a filled-ice (c2te/ice1hte) single-cage-key
    hydrate with built-in CH4 exported via the GUI
    ``HydrateGROMACSExporter.export_hydrate``.

    The GUI path (hydrate_export.py) uses ``write_multi_molecule_gro_file`` /
    ``write_multi_molecule_top_file`` + ``MoleculetypeRegistry``. For these
    filled-ice lattices (single cage_type_map key "small"), GenIce2 places
    CH4 via ``parse_guest`` (the single-cage path from Phase 39-02). The
    exporter registers ``hydrate_CH4`` -> "CH4_H" in the registry and stages
    the bundled ``ch4_hydrate.itp``.

    ``QFileDialog.getSaveFileName`` is mocked (REQUIRED — under
    ``QT_QPA_PLATFORM=offscreen`` it returns ``("", "")`` -> exporter returns
    False without writing). ``QMessageBox`` is mocked to suppress error
    dialogs. The exporter is lazy-imported inside the test (NOT at module
    top level — keeps PySide6 out of the import path per AGENTS.md).

    The exporter derives the .top path from the .gro path via
    ``path.with_name(path.stem + '.top')`` — so mocking getSaveFileName to
    return ``output.gro`` produces ``output.top``. The exporter stages ALL
    ITPs itself (tip4p-ice.itp + ch4_hydrate.itp via transform_guest_itp,
    which is idempotent on the pre-transformed built-in ITPs), so this test
    does NOT call ``_stage_itp_files`` (which would re-stage from
    quickice/data/ and could conflict). Only the MDP is copied for grompp
    (the exporter does not copy an MDP).
    """
    chain = filled_ice_hydrates[lattice_type]
    ws = tmp_path / lattice_type
    ws.mkdir()
    gro_path = ws / "output.gro"
    # The exporter derives: top_path = path.with_name(path.stem + '.top')
    # -> "output.top" when gro is "output.gro".

    # Lazy import: keeps PySide6 out of the module-top import path (AGENTS.md).
    from quickice.gui.hydrate_export import HydrateGROMACSExporter

    with patch(
        "quickice.gui.hydrate_export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.hydrate_export.QMessageBox"):
        exporter = HydrateGROMACSExporter(parent_widget=None)
        ok = exporter.export_hydrate(chain.hydrate, chain.config)
        assert ok is True, (
            "export_hydrate returned False — QFileDialog mock may not have "
            "been picked up, or staging raised"
        )

    top_path = ws / "output.top"

    # Files written by the exporter.
    assert gro_path.exists(), f"output.gro not written in {ws}"
    assert top_path.exists(), f"output.top not written in {ws}"

    # Built-in guest ITP staged by the exporter.
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"built-in guest ITP ch4_hydrate.itp not staged in {ws}"
    )
    # The tip4p-ice.itp water ITP is also staged by the exporter.
    assert (ws / "tip4p-ice.itp").exists(), (
        f"water ITP tip4p-ice.itp not staged in {ws}"
    )

    # .top [molecules] lists CH4_H + SOL (single built-in guest signature).
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, f"SOL not in [molecules]: {mols}"
    assert "CH4_H" in mols, (
        f"CH4_H not in [molecules] (filled-ice single-cage guest): {mols}"
    )

    # .gro residues contain CH4_H + SOL.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert {"SOL", "CH4_H"}.issubset(gro_res), (
        f"expected SOL + CH4_H in .gro residues, got {gro_res}"
    )

    # File consistency (always runs — catches ITP-missing + GRO/TOP mismatch).
    # The exporter already staged all #include'd ITPs, so completeness passes.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH — file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(
            ws, gro_file="output.gro", top_file="output.top"
        )
        assert rc == 0, (
            f"gmx grompp failed (filled-ice {lattice_type} GUI):\n{stderr}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Structural test: verify the single-cage-key constraint
# ══════════════════════════════════════════════════════════════════════════════


def test_filled_ice_cage_type_map_has_single_small_key():
    """Verify that c2te/ice1hte have a SINGLE cage_type_map key ("small"),
    NOT "small"+"large" like sI/sII — the filled-ice single-cage path from
    Phase 39-02 (single-entry cage_type_map prevents double-placement).

    NOTE: the ``cages`` DISPLAY dict uses the human-readable key "guest"
    (the cage NAME), but ``cage_type_map`` (the GenIce2 cage ID mapping used
    for guest placement via ``parse_guest``) uses "small". These are two
    different dicts with different keys — the plan conflated them, but the
    empirical test above proves "small" is the working cage key (using
    "guest" produces 0 guests). This structural test asserts the actual
    code structure.
    """
    for lattice_type in ("c2te", "ice1hte"):
        lattice_info = HYDRATE_LATTICES[lattice_type]
        cage_type_map = lattice_info.get("cage_type_map", {})
        cages = lattice_info.get("cages", {})

        # cage_type_map has exactly ONE key: "small" (maps to "Ne1").
        assert len(cage_type_map) == 1, (
            f"{lattice_type} cage_type_map should have exactly 1 key "
            f"(single cage, prevents double-placement), got "
            f"{len(cage_type_map)}: {cage_type_map}"
        )
        assert "small" in cage_type_map, (
            f"{lattice_type} cage_type_map should have 'small' key "
            f"(the GenIce2 cage ID mapping key), got {cage_type_map}"
        )
        assert cage_type_map["small"] == "Ne1", (
            f"{lattice_type} cage_type_map['small'] should be 'Ne1' "
            f"(GenIce2 cage id), got {cage_type_map['small']}"
        )
        # "large" NOT present (single cage — prevents double-placement).
        assert "large" not in cage_type_map, (
            f"{lattice_type} should NOT have 'large' in cage_type_map "
            f"(single cage — no double-placement), got {cage_type_map}"
        )
        # "guest" NOT present in cage_type_map (it's the cages display key).
        assert "guest" not in cage_type_map, (
            f"{lattice_type} should NOT have 'guest' in cage_type_map "
            f"('guest' is the cages DISPLAY dict key, not the cage_type_map "
            f"GenIce2 mapping key), got {cage_type_map}"
        )

        # The cages DISPLAY dict uses "guest" as the human-readable cage name.
        assert "guest" in cages, (
            f"{lattice_type} cages display dict should have 'guest' key "
            f"(the human-readable cage name), got {cages}"
        )
