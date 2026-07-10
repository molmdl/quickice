"""End-to-end acceptance test for the Pitfall 6 relaxation (plan 44.1-01).

Proves the CORE goal of phase 44.1 — "the same custom guest can be assigned to
multiple cages (aggregating like ch4)" — works end-to-end through the full
hydrate → interface → export → grompp chain:

  1. The SAME custom guest (``etoh_e2e``) is assigned to BOTH the small AND
     the large cages of an sI hydrate (``cage_guest_assignments`` with two
     entries sharing the same ``guest_type`` / ``guest_residue_name`` /
     gro/itp paths / atom_labels / atom_count). Pre-44.1-01 this raised
     ``ValueError`` from ``HydrateConfig.__post_init__`` (the Pitfall 6
     over-restriction); 44.1-01 relaxed the check to reject ONLY different
     guest_types sharing a residue name.
  2. ``HydrateStructureGenerator().generate(config)`` succeeds (no ValueError)
     and produces a ``HydrateStructure`` with the custom guest placed in BOTH
     cage types.
  3. ``hydrate.to_candidate()`` → ``assemble_slab(...)`` → ``InterfaceStructure``
     (no IndexError — plans 44.1-02/03/05 thread the custom guest_atom_count=9
     through the slab mode). ``iface.guest_nmolecules`` is the AGGREGATED count
     across both cages (like ch4-in-all-cages), and
     ``iface.guest_atom_count == 9 * iface.guest_nmolecules``.
  4. ``_build_custom_guest_info(config)`` (neutral helper, plan 44.1-04) returns
     a list with EXACTLY ONE entry — the same ``etoh_e2e`` is deduped by
     ``mol_type`` (both cages aggregate to ONE moleculetype, like ch4).
  5. ``write_interface_gro_file`` + ``write_interface_top_file`` (with the
     1-entry ``custom_guest_info`` list) emit a ``.gro`` with ``MOL_H`` residues
     and a ``.top`` whose ``[ molecules ]`` section lists EXACTLY ONE ``MOL_H``
     entry whose count is the AGGREGATED ``iface.guest_nmolecules`` (both cages
     summed) — mirroring ch4-in-all-cages which produces one ``CH4_H`` line.
  6. ``gmx grompp`` exits 0 (topology self-consistent + simulation-ready) when
     ``gmx`` is on PATH (``@gmx_skipif`` skips gracefully otherwise).

This is the acceptance test for the core 44.1 goal: it proves the engine
relaxation (44.1-01) + GUI auto-clear removal (44.1-18) + interface exporter
wiring (44.1-09) work together — the same custom guest in 2 cages aggregates
to one ``MOL_H`` moleculetype exactly like ch4-in-all-cages, all the way to
grompp-valid GROMACS output.

Plan: 44.1-21 (wave 4). Depends on 44.1-01 (engine relaxation),
44.1-18 (GUI auto-clear removal), 44.1-09 (interface exporter wiring).
"""

import shutil
import sys
from pathlib import Path

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_interface_gro_file,
    write_interface_top_file,
)
from quickice.output.guest_info import _build_custom_guest_info  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
)
from e2e_export_helpers import (  # noqa: E402
    _stage_custom_guest_itp,
    _stage_itp_files,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
    MDP_PATH,
)


# ── Shared custom-guest metadata (same as tests/test_e2e_custom_guest_hydrate.py)
_GUEST_TYPE = "etoh_e2e"
_GUEST_RESIDUE_NAME = "MOL"
_GUEST_GRO_PATH = "quickice/data/custom/etoh.gro"
_GUEST_ITP_PATH = "quickice/data/custom/etoh.itp"
_GUEST_ATOM_LABELS = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
_GUEST_ATOM_COUNT = 9


def _build_two_cage_config() -> HydrateConfig:
    """Build an sI HydrateConfig with the SAME custom guest in BOTH cages.

    This is the SAFE case the Pitfall 6 relaxation (44.1-01) allows: a single
    custom guest (``etoh_e2e``) assigned to both small and large cages
    aggregates into ONE ``MOL_H`` moleculetype exactly like ch4-in-all-cages.
    Pre-44.1-01 this raised ``ValueError`` from ``HydrateConfig.__post_init__``.
    """
    return HydrateConfig(
        lattice_type="sI",
        cage_guest_assignments={
            "small": CageGuestAssignment(
                guest_type=_GUEST_TYPE,
                occupancy=100.0,
                guest_residue_name=_GUEST_RESIDUE_NAME,
                guest_gro_path=_GUEST_GRO_PATH,
                guest_itp_path=_GUEST_ITP_PATH,
                guest_atom_labels=list(_GUEST_ATOM_LABELS),
                guest_atom_count=_GUEST_ATOM_COUNT,
            ),
            "large": CageGuestAssignment(
                guest_type=_GUEST_TYPE,
                occupancy=100.0,
                guest_residue_name=_GUEST_RESIDUE_NAME,
                guest_gro_path=_GUEST_GRO_PATH,
                guest_itp_path=_GUEST_ITP_PATH,
                guest_atom_labels=list(_GUEST_ATOM_LABELS),
                guest_atom_count=_GUEST_ATOM_COUNT,
            ),
        },
    )


def _count_molecule_lines(top_path: str, molecule_name: str) -> int:
    """Count raw [ molecules ] lines starting with ``molecule_name``.

    ``parse_top_molecules`` returns a ``dict`` so duplicate keys would be
    collapsed (last value wins). To rigorously prove the .top has EXACTLY ONE
    ``MOL_H`` line (not two separate lines that happened to aggregate in the
    dict), this helper counts the raw lines inside the ``[ molecules ]``
    section that start with ``molecule_name``.

    Args:
        top_path: Path to the .top file.
        molecule_name: Molecule name to count (e.g. "MOL_H").

    Returns:
        Number of [ molecules ] lines starting with ``molecule_name``.
    """
    count = 0
    in_molecules = False
    with open(top_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("["):
                section = stripped.strip("[] \t").lower()
                in_molecules = (section == "molecules")
                continue
            if not in_molecules:
                continue
            if not stripped or stripped.startswith(";") or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if parts and parts[0] == molecule_name:
                count += 1
    return count


# ══════════════════════════════════════════════════════════════════════════════
# 2-cage custom-guest full-chain e2e grompp (Pitfall 6 relaxation acceptance)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_same_custom_two_cages_full_chain_grompp(tmp_path):
    """Same custom guest in 2 cages → hydrate → interface → export → grompp OK.

    This is the ACCEPTANCE TEST for the core 44.1 goal. The SAME custom guest
    (``etoh_e2e``) assigned to BOTH small+large cages generates a hydrate (no
    ValueError — 44.1-01 relaxed Pitfall 6), assembles into an interface (no
    IndexError — 44.1-02/03/05 thread guest_atom_count=9), and exports via the
    interface writers to grompp-valid GROMACS output with EXACTLY ONE
    ``MOL_H`` moleculetype aggregating both cages' molecule counts (mirrors
    ch4-in-all-cages which produces one ``CH4_H`` line).

    Flow:
      1. Build a HydrateConfig with the same etoh_e2e in both small AND large
         cages (both guest_residue_name="MOL", same gro/itp paths, same
         atom_labels, guest_atom_count=9). Pre-44.1-01 this raised ValueError.
      2. HydrateStructureGenerator().generate(config) — assert NO ValueError
         raised (plan 01 allows the same guest_type in multiple cages).
      3. hydrate.to_candidate() → assemble_slab(box 3.0×3.0×8.0 nm, ice 2.0 +
         water 4.0) → InterfaceStructure. Assert no crash, guest_nmolecules > 0,
         guest_atom_count == 9 * guest_nmolecules (both cages aggregated).
      4. _build_custom_guest_info(config) — assert a list with EXACTLY 1 entry
         (the same etoh_e2e deduped by mol_type, like ch4).
      5. write_interface_gro_file + write_interface_top_file with the 1-entry
         custom_guest_info list. Stage the custom ITP via
         _stage_custom_guest_itp (transforms etoh.itp → moleculetype MOL_H) +
         _stage_itp_files (stages tip4p-ice.itp + the under-transformed etoh.itp
         which _stage_custom_guest_itp then overwrites).
      6. assert_itp_completeness + assert_gro_top_consistent (file consistency
         always runs, even when gmx is unavailable).
      7. run_gmx_grompp → rc == 0 (when gmx available; else skipped).
      8. Assert the .top [ molecules ] has EXACTLY ONE MOL_H line whose count
         == iface.guest_nmolecules (both cages aggregated into one moleculetype,
         mirroring ch4-in-all-cages).

    Box size: 3.0 × 3.0 × 8.0 nm so grompp's PBC rule (cutoff 1.0 nm < half the
    shortest box vector = 1.5 nm) is satisfied — matches the repo's
    interface-test box convention (see test_e2e_custom_guest_gui_grompp.py).
    """
    # ── 1. Build the 2-cage config (same etoh_e2e in BOTH cages) ─────────────
    config = _build_two_cage_config()
    # Pre-44.1-01 this raised ValueError("Duplicate guest_residue_name ...");
    # 44.1-01 relaxed the check to reject ONLY different guest_types sharing a
    # residue name. Constructing the config here proves the engine allows it.
    assert len(config.cage_guest_assignments) == 2, (
        "expected both small + large cage assignments, got "
        f"{len(config.cage_guest_assignments)}"
    )
    both_custom = all(
        a.is_custom_guest for a in config.cage_guest_assignments.values()
    )
    assert both_custom, "both cage assignments must be custom (etoh_e2e)"
    # Both cages share the same guest_type (the aggregation key, like ch4).
    guest_types = {a.guest_type for a in config.cage_guest_assignments.values()}
    assert guest_types == {_GUEST_TYPE}, (
        f"both cages must use the same guest_type {_GUEST_TYPE!r}, got {guest_types}"
    )

    # ── 2. Generate the hydrate — assert NO ValueError raised (44.1-01) ─────
    gen = HydrateStructureGenerator()
    hydrate = gen.generate(config)  # would raise pre-44.1-01
    assert hydrate.guest_count > 0, (
        "2-cage custom ethanol hydrate should place guests in BOTH cage types"
    )

    # ── 3. to_candidate() → assemble_slab() → InterfaceStructure ───────────
    # 44.1-02 carries guest_descriptors + guest_atom_counts in candidate
    # metadata; 44.1-05 threads guest_atom_count=9 through slab mode so the
    # 9-atom ethanol is counted correctly (no IndexError, no miscount).
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
    # guest_nmolecules is the AGGREGATED count across BOTH cages (like
    # ch4-in-all-cages which sums small+large cage counts into one number).
    assert iface.guest_nmolecules > 0, (
        "2-cage custom ethanol slab should have aggregated guest molecules"
    )
    # Each ethanol is 9 atoms; total guest atoms must be 9 * nmolecules.
    assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
        f"2-cage slab guest_atom_count={iface.guest_atom_count} != "
        f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
    )

    # ── 4. _build_custom_guest_info — EXACTLY 1 entry (deduped by mol_type) ─
    # Both cages share the same guest_type (etoh_e2e), so the dedup-by-mol_type
    # in _build_custom_guest_info collapses them to ONE entry — exactly like
    # ch4-in-all-cages produces one CH4_H moleculetype. Pre-44.1-01 the engine
    # rejected the config before this point; now the builder runs and dedups.
    cgi = _build_custom_guest_info(config)
    assert cgi is not None, (
        "_build_custom_guest_info returned None for a 2-cage custom config — "
        "expected a 1-element list (both cages deduped to one moleculetype)"
    )
    assert isinstance(cgi, list), (
        f"_build_custom_guest_info should return a list, got {type(cgi)}"
    )
    assert len(cgi) == 1, (
        f"_build_custom_guest_info should return EXACTLY 1 entry (the same "
        f"etoh_e2e deduped by mol_type — both cages aggregate to one "
        f"moleculetype like ch4), got {len(cgi)} entries: {cgi}"
    )
    assert cgi[0]["mol_type"] == _GUEST_TYPE, (
        f"custom_guest_info[0]['mol_type'] should be {_GUEST_TYPE!r}, "
        f"got {cgi[0]['mol_type']!r}"
    )
    assert cgi[0]["residue_name"] == f"{_GUEST_RESIDUE_NAME}_H", (
        f"custom_guest_info[0]['residue_name'] should be "
        f"{_GUEST_RESIDUE_NAME}_H, got {cgi[0]['residue_name']!r}"
    )

    # ── 5. Export: write .gro + .top, stage ITPs (built-in + transformed) ───
    gro_path = tmp_path / "two_cages.gro"
    top_path = tmp_path / "two_cages.top"
    write_interface_gro_file(iface, str(gro_path), custom_guest_info=cgi)
    write_interface_top_file(iface, str(top_path), custom_guest_info=cgi)

    # Stage the MDP for grompp.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    # _stage_itp_files stages every #include'd ITP from the data dir:
    #   - tip4p-ice.itp (water, no transformation needed)
    #   - etoh.itp (custom guest, but UNDER-transformed — moleculetype "etoh",
    #     [atoms] resname "MOL"; needs the _H suffix to match the .top [molecules]
    #     MOL_H entry).
    _stage_itp_files(str(top_path), tmp_path)
    # _stage_custom_guest_itp OVERWRITES the under-transformed etoh.itp with the
    # fully-transformed copy (moleculetype "MOL_H", [atomtypes] commented,
    # [atoms] resname "MOL_H") via the reused transform_guest_itp — the
    # prerequisite for grompp: the .top [molecules] lists MOL_H, so the #include'd
    # ITP must define moleculetype MOL_H.
    _stage_custom_guest_itp(
        tmp_path, Path(_GUEST_ITP_PATH), _GUEST_RESIDUE_NAME
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh).
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype — transform_guest_itp "
        "was not applied by _stage_custom_guest_itp"
    )

    # ── 6. File-consistency assertions (always run, even if gmx absent) ─────
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # ── 7. gmx grompp → rc == 0 (when gmx available; @gmx_skipif else) ──────
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="two_cages.gro", top_file="two_cages.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (2-cage custom guest full chain):\n{stderr}"
    )

    # ── 8. EXACTLY ONE MOL_H in [molecules] aggregating BOTH cages ──────────
    # Mirrors ch4-in-all-cages which produces ONE CH4_H line whose count is the
    # sum of small+large cage guests. The 2-cage custom path must do the same:
    # one MOL_H line whose count == iface.guest_nmolecules (aggregated).
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols, f"expected SOL in [molecules], got {mols}"
    assert "MOL_H" in mols, (
        f"expected MOL_H in [molecules] (2-cage aggregation), got {mols}"
    )
    # The MOL_H count must equal the AGGREGATED iface.guest_nmolecules (both
    # cages summed into one moleculetype). This is the aggregation proof.
    assert mols["MOL_H"] == iface.guest_nmolecules, (
        f"MOL_H count {mols['MOL_H']} != aggregated guest_nmolecules "
        f"{iface.guest_nmolecules} — both cages should aggregate to ONE "
        f"moleculetype like ch4-in-all-cages"
    )
    # Rigorously prove EXACTLY ONE MOL_H line in [molecules] (parse_top_molecules
    # returns a dict so duplicate keys would collapse; counting raw lines proves
    # the .top literally has one MOL_H entry, not two that aggregated in the
    # dict). This is the "exactly ONE MOL_H moleculetype entry" requirement.
    mol_h_lines = _count_molecule_lines(str(top_path), "MOL_H")
    assert mol_h_lines == 1, (
        f"expected EXACTLY ONE MOL_H line in [molecules] (both cages aggregated "
        f"into one moleculetype like ch4), got {mol_h_lines} lines"
    )
    # GUE must NOT appear (custom_guest_info was threaded — no detect_guest_type
    # fallback to the GUE/UNK residue name).
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )

    # .gro residues must contain SOL + MOL_H (the 9-atom ethanol chunk written
    # with the MOL_H residue name from custom_guest_info).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )
