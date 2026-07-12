"""E2E filled-ice (c2te, ice1hte) CLI hydrate-ONLY branch grompp validation.

Closes TEST-08 (Phase 47, plan 47-05): the final remaining test gap in
QuickIce v4.7. Validates that the CLI ``CLIPipeline._run_export_step``
hydrate branch (pipeline.py:886-929) produces grompp-valid output for the
two ORTHORHOMBIC filled-ice lattices (c2te, ice1hte) at their NATIVE
supercells (c2te 3x3x3, ice1hte 4x4x4).

DISTINCT from prior sibling tests (do NOT conflate):
- ``test_e2e_triclinic_hydrate_export.py`` covers the CLI hydrate branch for
  c0te/c1te — TRICLINIC lattices at 4x4x4 (already PASSING).
- ``test_e2e_mixed_filled_ice_gui.py`` covers the GUI hydrate exporter for
  c2te/ice1hte via ``HydrateGROMACSExporter`` (``write_multi_molecule_*`` —
  DIFFERENT writers; already PASSING).
- ``test_e2e_lattice_cross_tab_cli.py::test_lattice_cross_tab_cli_grompp``
  covers the CLI INTERFACE / solute / ion branches for c2te/ice1hte using a
  3x3x8 nm SLAB (assemble_slab — a different cell geometry; already PASSING).

This test exercises the native ORTHORHOMBIC supercell via the hydrate-ONLY
branch — the HydrateStructure -> InterfaceStructure wrapper path
(pipeline.py:886-929) that writes ``hydrate.gro`` / ``hydrate.top`` via
``write_interface_gro_file`` / ``write_interface_top_file`` +
``copy_itp_files_for_structure`` (which stages ``ch4_hydrate.itp``).

Pitfall 1 (box-size, CRITICAL — empirically verified): c2te/ice1hte at
1x1x1 have shortest box vectors of ~0.88 nm and ~0.69 nm respectively,
FAR below 2*rcoulomb = 2.0 nm — grompp fatal-errors with "cut-off length
is longer than half the shortest box vector". The verified minimum
supercells are:
  - c2te 3x3x3: shortest = 2.65 nm -> grompp rc=0
  - ice1hte 4x4x4: shortest = 2.76 nm -> grompp rc=0
2x2x2 fails for BOTH (c2te=1.76 nm, ice1hte=1.38 nm); ice1hte even fails
3x3x3 (2.07 nm) due to GROMACS's stricter non-orthogonal cell check.

Pitfall 2 (cage key "small" not "guest"): c2te/ice1hte have
``cage_type_map = {"small": "Ne1"}`` (the GenIce2 cage ID mapping). The
``cages`` DISPLAY dict uses the human-readable key "guest" (the cage
NAME), but ``cage_type_map`` uses "small". ``cage_guest_assignments`` MUST
use "small" (matching ``cage_type_map``) — using "guest" produces 0
guests. The fixture sanity assert (``hydrate.guest_count > 0``) catches
this.

Pitfall 6 (two export paths): this CLI test uses
``CLIPipeline._run_export_step`` + ``write_interface_*`` writers (the CLI
hydrate branch). Do NOT import ``HydrateGROMACSExporter`` or
``quickice.gui.hydrate_export`` — that would pull PySide6 into the import
path (AGENTS.md lazy-import rule) and test the GUI path instead.

Lazy imports: Import only pytest, shutil, sys, Path, SimpleNamespace,
CLIPipeline, HydrateStructureGenerator, HydrateConfig,
CageGuestAssignment, HYDRATE_LATTICES, gmx_skipif, and the e2e helpers.
NO PySide6/VTK/GenIce2 top-level imports (GenIce2 is lazy-imported inside
HydrateStructureGenerator method bodies — already handled). NO
QT_QPA_PLATFORM env needed (CLI-only test). NO unittest.mock (GUI-only).

Module-scoped fixture amortizes the GenIce2 calls (~0.1-0.3s each for
c2te@3x3x3 + ice1hte@4x4x4) across the 2 parametrized cases per
AGENTS.md testing guidance.
``gmx`` is on PATH so grompp runs (``@gmx_skipif`` skips when absent — the
file-consistency assertions still run before the grompp branch).
"""

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

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
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
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
# Module-scoped fixture: build c2te + ice1hte hydrate structures ONCE
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def filled_ice_hydrates():
    """Module-scoped: generate c2te + ice1hte hydrate structures with built-in
    CH4 in the single "small" cage ONCE, amortizing the GenIce2 calls across
    both parametrized CLI export cases.

    CRITICAL (Pitfall 2 — cage key): c2te/ice1hte have
    ``cage_type_map = {"small": "Ne1"}`` — a SINGLE key. The ``cages`` display
    dict uses the human-readable key "guest" (the cage NAME), but
    ``cage_type_map`` (the GenIce2 cage ID mapping used for guest placement
    via ``parse_guest``) uses "small". The ``cage_guest_assignments`` dict
    MUST use "small" as the key (matching ``cage_type_map``) — using "guest"
    produces 0 guests because the hydrate generator's ``_run_via_api``
    skips cage keys not present in ``cage_type_map`` (warning:
    "cage_key 'guest' not in cage_type_map").

    Per-lattice supercell sizes (Pitfall 1 — empirically verified):
      - c2te 3x3x3: shortest = 2.65 nm > 2.0 nm -> grompp rc=0
      - ice1hte 4x4x4: shortest = 2.76 nm > 2.0 nm -> grompp rc=0
    The plan's suggested 2x2x2 fails for BOTH (c2te=1.76 nm, ice1hte=1.38 nm —
    both < 2.0 nm); ice1hte even fails at 3x3x3 (2.07 nm) due to GROMACS's
    stricter non-orthogonal cell check.

    Returns ``dict {"c2te": SimpleNamespace(hydrate=..., config=...),
    "ice1hte": SimpleNamespace(hydrate=..., config=...)}`` where each
    namespace carries the ``HydrateStructure`` + the ``HydrateConfig`` used
    to generate it (the CLI hydrate branch reads ``hydrate.config`` for ITP
    staging via ``copy_itp_files_for_structure``).
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
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, config=config
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# Shared assertion helper (filled-ice CLI hydrate export)
# ══════════════════════════════════════════════════════════════════════════════


def _assert_filled_ice_hydrate_export(ws, gro_name, top_name):
    """Common assertions for a filled-ice CLI hydrate-only export: files
    written, ch4_hydrate.itp staged with CH4_H moleculetype, CH4_H + SOL in
    [molecules] and .gro residues, file consistency, grompp rc=0.

    Built-in ch4 cage guest -> residue name ``CH4_H`` + bundled
    ``ch4_hydrate.itp`` (pre-transformed). The CLI hydrate branch's
    ``copy_itp_files_for_structure`` stages the ITP itself; only ``em.mdp``
    is copied here (for the grompp run).

    Args:
        ws: Workspace directory (``Path``) containing the exported files.
        gro_name: ``.gro`` filename (relative to ``ws``).
        top_name: ``.top`` filename (relative to ``ws``).
    """
    gro_path = ws / gro_name
    top_path = ws / top_name

    # Files written by the CLI hydrate branch.
    assert gro_path.exists(), f"{gro_name} not written in {ws}"
    assert top_path.exists(), f"{top_name} not written in {ws}"

    # Built-in ch4 hydrate guest ITP staged (ch4_hydrate.itp) by
    # copy_itp_files_for_structure (the CLI hydrate branch's own staging).
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"built-in guest ITP ch4_hydrate.itp not staged in {ws}"
    )
    staged_itp = (ws / "ch4_hydrate.itp").read_text()
    assert "CH4_H" in staged_itp, (
        f"staged ch4_hydrate.itp missing moleculetype CH4_H"
    )

    # .top [molecules] references CH4_H (built-in residue) + SOL.
    mols = parse_top_molecules(str(top_path))
    assert "CH4_H" in mols, (
        f"built-in residue CH4_H not in [molecules]: {mols}"
    )
    assert "SOL" in mols, f"SOL not in [molecules]: {mols}"

    # .gro residues contain CH4_H + SOL.
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res, (
        f"built-in residue CH4_H not in .gro residues: {gro_res}"
    )
    assert "SOL" in gro_res, f"SOL not in .gro residues: {gro_res}"

    # File consistency (always runs — catches ITP-missing + GRO/TOP mismatch).
    # The CLI hydrate branch already staged all #include'd ITPs itself, so
    # completeness passes. Only the MDP is needed for the grompp run.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # gmx grompp (only when gmx is on PATH — file consistency always runs).
    if shutil.which("gmx"):
        rc, stderr = run_gmx_grompp(ws, gro_file=gro_name, top_file=top_name)
        assert rc == 0, (
            f"gmx grompp failed (filled-ice CLI hydrate, {gro_name}):\n{stderr}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized CLI hydrate export + grompp test (c2te + ice1hte)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lattice_type", ["c2te", "ice1hte"])
@gmx_skipif
def test_filled_ice_cli_hydrate_export_grompp(
    tmp_path, filled_ice_hydrates, lattice_type
):
    """CLI ``_run_export_step`` hydrate branch produces grompp-valid output
    for c2te/ice1hte at their native orthorhombic supercells
    (c2te 3x3x3 / ice1hte 4x4x4).

    Only ``_hydrate_result`` is set (NOT ``_interface_result``) so the
    ``_run_export_step`` priority selection
    (ion > solute > custom > interface > hydrate > ice) picks the hydrate
    branch (pipeline.py:886-929). The hydrate branch wraps the
    ``HydrateStructure`` in an ``InterfaceStructure``-compatible wrapper +
    ``write_interface_gro_file`` / ``write_interface_top_file`` +
    ``copy_itp_files_for_structure`` (which stages ``ch4_hydrate.itp`` +
    ``tip4p-ice.itp`` from the bundled data dir). The hydrate carries
    ``.config`` (the ``HydrateConfig`` with ``guest_type="ch4"``) so
    ``copy_itp_files_for_structure`` resolves the built-in ch4 guest ->
    ``ch4_hydrate.itp`` (pre-transformed).

    This is DISTINCT from:
    - ``test_triclinic_hydrate_cli_export_grompp`` (c0te/c1te — TRICLINIC,
      4x4x4 supercell, already covered).
    - ``test_filled_ice_single_cage_gui_grompp`` (c2te/ice1hte — GUI path,
      ``write_multi_molecule_*`` writers, already covered).
    - ``test_lattice_cross_tab_cli_grompp`` (c2te/ice1hte — CLI interface /
      solute / ion branches using a 3x3x8 nm SLAB, a different cell
      geometry; already covered).

    This test covers ONLY the hydrate-only branch via the native
    orthorhombic supercell — the direct hydrate -> export user workflow for
    c2te/ice1hte (which are NOT blocked at the interface tab, unlike
    c0te/c1te).
    """
    chain = filled_ice_hydrates[lattice_type]
    ws = tmp_path / "cli"
    ws.mkdir()

    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = chain.hydrate  # carries .config for ITP staging
    # Only _hydrate_result set -> export priority picks the hydrate branch.

    code = pipe._run_export_step()
    assert code == 0, (
        f"_run_export_step failed (rc={code}) for the hydrate branch "
        f"({lattice_type} {_FILLED_ICE_SUPERCELLS[lattice_type]})"
    )

    # The hydrate branch writes hydrate.gro / hydrate.top to _output_dir.
    _assert_filled_ice_hydrate_export(ws, "hydrate.gro", "hydrate.top")
