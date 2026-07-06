"""CLI mixed cage occupancy tests (plan 42-07).

Covers the Phase 42 CLI surface for mixed cage occupancy:

1. ``test_mixed_cli_built_in_grompp`` (``@gmx_skipif``): proves ``gmx grompp``
   exits 0 on a mixed built-in (CH4 + THF) hydrate exported via the multi-
   molecule writers (``write_multi_molecule_gro_file`` +
   ``write_multi_molecule_top_file``) with a ``MoleculetypeRegistry``
   registering BOTH ``hydrate_CH4`` and ``hydrate_THF``. The CLI ``--cage-guest``
   flag builds the ``HydrateConfig.cage_guest_assignments`` for mixed built-in
   guests (validated by ``test_cage_guest_flag_builds_assignments`` below); the
   grompp here closes MIXED-04 for the CLI path (built-in-only per the plan).

2. ``test_build_custom_guest_info_returns_list``: unit test asserting
   ``_build_custom_guest_info(config)`` returns a 1-element list for an
   explicit Phase 42 API config with one custom + one built-in assignment
   (only the custom entry appears — built-ins are handled by the registry),
   and ``None`` for an all-built-in config.

3. ``test_cage_guest_flag_builds_assignments``: arg-parsing + config-build
   test. Parses ``--cage-guest small=CH4:60 --cage-guest large=THF:100`` via
   ``create_parser``, calls the module-level ``_parse_cage_guest_args`` helper
   (extracted in plan 42-07), builds a ``HydrateConfig``, and asserts the
   per-cage ``guest_type`` and ``occupancy`` round-trip correctly.

Note (deviation from plan's literal text): the plan's Task 2 suggests testing
the mixed built-in grompp via the CLI interface writers (``write_interface_*``).
However, those writers carry a single guest stream and use
``detect_guest_type_from_atoms`` to pick ONE guest type for the whole guest
region — they cannot emit a mixed ``[molecules]`` block with both ``CH4_H``
and ``THF_H``. The multi-molecule writers (used by the GUI
``HydrateGROMACSExporter``) DO handle mixed built-in via ``molecule_index`` +
``registry`` (per-``mol_type`` resolution), so test 1 uses them to validate
the mixed built-in grompp outcome that the CLI ``--cage-guest`` feature
enables. The CLI parser/pipeline building of ``cage_guest_assignments`` is
validated by test 3; the CLI export path itself (``_run_export_step`` →
``write_interface_*``) remains single-guest-stream and is covered by the
existing 41-08 tests (``test_run_export_step_*``).
"""

import sys
import shutil
from pathlib import Path

import numpy as np
import pytest

# Make tests/e2e_export_helpers.py importable (no test_ prefix → not auto-collected).
_TESTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TESTS_DIR))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.cli.parser import create_parser  # noqa: E402
from quickice.cli.pipeline import (  # noqa: E402
    _build_custom_guest_info,
    _parse_cage_guest_args,
)
from quickice.output.gromacs_writer import (  # noqa: E402
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    MoleculeIndex,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    ETOH_ITP,
    MDP_PATH,
    _stage_itp_files,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)


# ══════════════════════════════════════════════════════════════════════════════
# Test 1: CLI mixed built-in (CH4 + THF) grompp e2e
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_mixed_cli_built_in_grompp(tmp_path):
    """gmx grompp exits 0 on a mixed built-in (CH4 + THF) hydrate exported via
    the multi-molecule writers with a registry registering BOTH guests.

    Builds a tiny synthetic 2-water + 1-CH4 + 1-THF system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 5 CH4 atoms + 13 THF
    atoms = 26 atoms.  Stages tip4p-ice.itp + ch4_hydrate.itp + thf_hydrate.itp
    (all built-in — no custom-guest ITP transform needed), then runs
    gmx grompp.

    The built-in CH4 resolves via the registry (hydrate_CH4 -> "CH4_H"); the
    built-in THF resolves via the registry (hydrate_THF -> "THF_H"). Both
    fire in the SAME .gro/.top — the defining property of mixed built-in cage
    occupancy (MIXED-04, CLI path).

    Uses the multi-molecule writers (write_multi_molecule_*) rather than the
    CLI interface writers (write_interface_*) because the latter carry a
    single guest stream and use ``detect_guest_type_from_atoms`` which picks
    ONE guest type for the whole guest region — they cannot emit a mixed
    ``[molecules]`` block with both ``CH4_H`` and ``THF_H``. The multi-molecule
    writers (used by the GUI HydrateGROMACSExporter) DO handle mixed built-in
    via ``molecule_index`` + ``registry`` (per-mol_type resolution). See the
    module docstring for the full rationale.
    """
    # Synthetic 2-water + 1-CH4 + 1-THF system (26 atoms total).
    # molecule_index start indices:
    #   water 1: atoms 0-3   (start=0,  count=4)
    #   water 2: atoms 4-7  (start=4,  count=4)
    #   CH4:     atoms 8-12 (start=8,  count=5)
    #   THF:     atoms 13-25 (start=13, count=13)
    positions = np.zeros((26, 3))
    # Water (8 atoms: 2 × OW,HW1,HW2,MW)
    for i in range(8):
        positions[i] = [0.01 * (i + 1), 0.01 * (i + 1), 0.01 * (i + 1)]
    # CH4 (5 atoms: C,H,H,H,H) — built-in, handled by registry
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]
    # THF (13 atoms: O,CA,CA,CB,CB,H,H,H,H,H,H,H,H) — built-in, registry
    for i in range(13):
        positions[13 + i] = [0.2 + 0.01 * i, 0.2, 0.2]

    atom_names = [
        # water mol 1
        "OW", "HW1", "HW2", "MW",
        # water mol 2
        "OW", "HW1", "HW2", "MW",
        # CH4 guest (built-in, matches ch4_hydrate.itp [atoms] order: C,H,H,H,H)
        "C", "H", "H", "H", "H",
        # THF guest (built-in, matches thf_hydrate.itp [atoms] order:
        # O,CA,CA,CB,CB,H,H,H,H,H,H,H,H)
        "O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H",
    ]

    # Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp); 3.0 nm gives a
    # comfortable margin (STATE [41-10] lesson: grompp rejects box exactly at
    # 2*cutoff; cutoff 1.0 nm < half the shortest box vector must be strict).
    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),    # built-in -> registry -> "CH4_H"
        MoleculeIndex(13, 13, "thf"),  # built-in -> registry -> "THF_H"
    ]

    # Registry with BOTH built-in guests registered as hydrate guests so the
    # writers resolve ch4 -> "CH4_H" and thf -> "THF_H" in .gro/.top.
    registry = MoleculetypeRegistry()
    registry.register_hydrate_guest("CH4")
    registry.register_hydrate_guest("THF")

    # itp_files maps mol_type -> itp filename so the writer emits the correct
    # #include for each built-in guest (ch4 -> ch4_hydrate.itp,
    # thf -> thf_hydrate.itp). Both ITPs are bundled in quickice/data/.
    itp_files = {
        "ch4": "ch4_hydrate.itp",
        "thf": "thf_hydrate.itp",
    }

    # No custom_guest_info: both ch4 and thf are built-in (handled by the
    # registry). This is the "Mixed CLI built-in" path (per the plan, the
    # CLI surface is built-in-only for v4.7; full custom CLI is deferred).
    custom_guest_info = None

    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(gro),
        "mixed built-in guest hydrate (CLI)",
        atom_names=atom_names,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )
    write_multi_molecule_top_file(
        molecule_index,
        str(top),
        "mixed built-in guest hydrate (CLI)",
        itp_files=itp_files,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )

    # Stage MDP + ITPs (repo convention: writers don't copy ITPs; staging does).
    # _stage_itp_files stages tip4p-ice.itp + ch4_hydrate.itp + thf_hydrate.itp
    # (all built-in — no custom-guest ITP transform needed).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    _stage_itp_files(str(top), ws)

    # All #include'd ITPs present in the workspace.
    assert_itp_completeness(str(top), ws)
    # GRO residues <-> TOP [molecules] cross-check.
    assert_gro_top_consistent(str(gro), str(top))

    # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert exit_code == 0, f"gmx grompp failed (mixed CLI built-in):\n{stderr}"

    # .top [molecules] lists SOL + CH4_H + THF_H (the mixed-occupancy signature).
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "CH4_H" in mols and "THF_H" in mols, (
        f"expected SOL + CH4_H + THF_H in [molecules], got {mols}"
    )

    # .gro residues contain SOL + CH4_H + THF_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert {"SOL", "CH4_H", "THF_H"}.issubset(gro_res), (
        f"expected SOL + CH4_H + THF_H in .gro residues, got {gro_res}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Test 2: _build_custom_guest_info returns list[dict] | None (Phase 42 API)
# ══════════════════════════════════════════════════════════════════════════════


def test_build_custom_guest_info_returns_list():
    """_build_custom_guest_info returns a 1-element list for an explicit Phase
    42 API config with one custom + one built-in assignment (only the custom
    entry appears — built-ins are handled by the MoleculetypeRegistry), and
    ``None`` for an all-built-in config.

    The config uses ``cage_guest_assignments`` (the Phase 42 explicit API):
    - small: ch4 (built-in) — excluded from the list (registry handles it)
    - large: etoh_mix (custom) — included as a 1-element list

    For all-built-in (ch4 + thf both via registry), the helper returns ``None``
    (no custom entries).
    """
    # Config with mixed built-in (ch4) + custom (etoh_mix).
    mixed_config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",  # primary (legacy) — built-in
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(
                guest_type="etoh_mix",
                occupancy=100.0,
                guest_residue_name="MOL",
                guest_gro_path="quickice/data/custom/etoh.gro",
                guest_itp_path="quickice/data/custom/etoh.itp",
                guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
                guest_atom_count=9,
            ),
        },
    )

    info = _build_custom_guest_info(mixed_config)
    # Only the custom entry appears — ch4 is built-in (excluded).
    assert info == [
        {
            "mol_type": "etoh_mix",
            "residue_name": "MOL_H",
            "itp_path": Path("quickice/data/custom/etoh.itp"),
        }
    ], (
        f"Expected 1-element list with etoh_mix entry, got {info}"
    )

    # All-built-in config (ch4 + thf both built-in) -> None.
    all_builtin_config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",  # primary (legacy) — built-in
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=60.0),
            "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
        },
    )
    assert _build_custom_guest_info(all_builtin_config) is None, (
        "All-built-in config should yield None (no custom entries for the list)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Test 3: --cage-guest flag builds correct cage_guest_assignments
# ══════════════════════════════════════════════════════════════════════════════


def test_cage_guest_flag_builds_assignments():
    """Parse ``--cage-guest small=CH4:60 --cage-guest large=THF:100`` via
    ``create_parser``, call the module-level ``_parse_cage_guest_args`` helper
    (extracted in plan 42-07), build a ``HydrateConfig``, and assert the
    per-cage ``guest_type`` and ``occupancy`` round-trip correctly through
    ``HydrateConfig.__post_init__``.

    The legacy ``--guest``/``--cage-occupancy-small/large`` fields are also
    passed (defaults), but the explicit ``cage_guest_assignments`` dict
    overrides them per the 42-01 ``__post_init__`` logic.
    """
    parser = create_parser()
    args = parser.parse_args([
        "--temperature", "270",
        "--pressure", "0.1",
        "--hydrate",
        "--lattice-type", "sI",
        "--cage-guest", "small=CH4:60",
        "--cage-guest", "large=THF:100",
    ])

    # The parser collects repeatable --cage-guest into a list.
    assert args.cage_guest == ["small=CH4:60", "large=THF:100"], (
        f"Expected args.cage_guest list, got {args.cage_guest!r}"
    )

    # Module-level helper parses the list into a dict[str, CageGuestAssignment]
    # (the same call the pipeline's _run_source_step makes).
    assignments = _parse_cage_guest_args(args, args.lattice_type)
    assert set(assignments.keys()) == {"small", "large"}, (
        f"Expected keys {{small, large}}, got {set(assignments.keys())}"
    )

    # Build HydrateConfig (the 42-01 __post_init__ auto-populates built-in
    # metadata per-assignment from GUEST_MOLECULES when guest_atom_labels empty).
    config = HydrateConfig(
        lattice_type=args.lattice_type,
        cage_guest_assignments=assignments,
        guest_type=getattr(args, "guest", "CH4").lower(),
        cage_occupancy_small=getattr(args, "cage_occupancy_small", 100.0),
        cage_occupancy_large=getattr(args, "cage_occupancy_large", 100.0),
        supercell_x=getattr(args, "supercell_x", 1),
        supercell_y=getattr(args, "supercell_y", 1),
        supercell_z=getattr(args, "supercell_z", 1),
    )

    # Per-cage guest_type + occupancy round-trip correctly.
    assert config.cage_guest_assignments["small"].guest_type == "ch4", (
        f"Expected small.guest_type == 'ch4', got "
        f"{config.cage_guest_assignments['small'].guest_type!r}"
    )
    assert config.cage_guest_assignments["small"].occupancy == 60.0, (
        f"Expected small.occupancy == 60.0, got "
        f"{config.cage_guest_assignments['small'].occupancy}"
    )
    assert config.cage_guest_assignments["large"].guest_type == "thf", (
        f"Expected large.guest_type == 'thf', got "
        f"{config.cage_guest_assignments['large'].guest_type!r}"
    )
    assert config.cage_guest_assignments["large"].occupancy == 100.0, (
        f"Expected large.occupancy == 100.0, got "
        f"{config.cage_guest_assignments['large'].occupancy}"
    )

    # __post_init__ auto-populated built-in metadata per-assignment
    # (42-01 single source of truth): ch4 -> 5 atoms, thf -> 13 atoms.
    assert config.cage_guest_assignments["small"].guest_atom_count == 5, (
        "Expected ch4 (small) atom_count == 5 (auto-populated from "
        "GUEST_MOLECULES)"
    )
    assert config.cage_guest_assignments["large"].guest_atom_count == 13, (
        "Expected thf (large) atom_count == 13 (auto-populated from "
        "GUEST_MOLECULES)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Test 4: legacy --guest/--cage-occupancy-* still work (deprecated aliases)
# ══════════════════════════════════════════════════════════════════════════════


def test_legacy_guest_flags_still_work():
    """Legacy ``--guest CH4 --cage-occupancy-small 50 --cage-occupancy-large 80``
    (no ``--cage-guest``) still builds a valid HydrateConfig via the 42-01
    ``__post_init__`` legacy shim (synthesizes ``cage_guest_assignments`` from
    the legacy fields when the dict is empty).

    The deprecated aliases are kept for backward compat (per plan: "do NOT
    remove — backward compat"). This test guards against accidental removal.
    """
    parser = create_parser()
    args = parser.parse_args([
        "--temperature", "270",
        "--pressure", "0.1",
        "--hydrate",
        "--lattice-type", "sI",
        "--guest", "CH4",
        "--cage-occupancy-small", "50",
        "--cage-occupancy-large", "80",
    ])

    # No --cage-guest -> args.cage_guest is None.
    assert args.cage_guest is None, (
        f"Expected args.cage_guest is None (no --cage-guest), got {args.cage_guest!r}"
    )
    # Legacy fields are parsed unchanged.
    assert args.guest == "CH4"
    assert args.cage_occupancy_small == 50.0
    assert args.cage_occupancy_large == 80.0

    # _parse_cage_guest_args returns {} when args.cage_guest is None — the
    # pipeline then passes cage_guest_assignments={} to HydrateConfig, which
    # triggers the __post_init__ legacy shim synthesizing from the legacy fields.
    assignments = _parse_cage_guest_args(args, args.lattice_type)
    assert assignments == {}, (
        f"Expected empty dict for legacy args, got {assignments}"
    )

    config = HydrateConfig(
        lattice_type=args.lattice_type,
        cage_guest_assignments=assignments,  # {} -> legacy shim
        guest_type=args.guest.lower(),
        cage_occupancy_small=args.cage_occupancy_small,
        cage_occupancy_large=args.cage_occupancy_large,
        supercell_x=getattr(args, "supercell_x", 1),
        supercell_y=getattr(args, "supercell_y", 1),
        supercell_z=getattr(args, "supercell_z", 1),
    )

    # Legacy shim synthesized small + large from the legacy fields.
    assert set(config.cage_guest_assignments.keys()) == {"small", "large"}, (
        f"Legacy shim should synthesize small+large, got "
        f"{set(config.cage_guest_assignments.keys())}"
    )
    assert config.cage_guest_assignments["small"].guest_type == "ch4"
    assert config.cage_guest_assignments["small"].occupancy == 50.0
    assert config.cage_guest_assignments["large"].guest_type == "ch4"
    assert config.cage_guest_assignments["large"].occupancy == 80.0
