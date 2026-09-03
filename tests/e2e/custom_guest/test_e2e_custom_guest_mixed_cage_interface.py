"""Regression test: MIXED built-in+custom cage-guest INTERFACE export flow.

Follow-up to the 29085047 fix (which fixed the Ion + Solute writers for mixed
built-in+custom cage guests). The Interface writer
(``write_interface_gro_file`` / ``write_interface_top_file``) had the SAME
bug class but was deferred in 29085047 (the latent gap noted in that commit's
message: "Not changed: interface_writer.py ... To be fixed in a follow-up
commit"). This test exercises the fix.

Before this fix, exporting a slab interface built from a MIXED sII hydrate
(CH4 built-in in small cages + ethanol custom in large cages) through the
INTERFACE tab produced a structurally INVALID GROMACS export:

  * ``write_interface_gro_file`` custom branch: when ``custom_guest_info`` was
    supplied, it resolved a SINGLE ``atoms_per_mol`` stride
    (``guest_atom_count // guest_nmolecules`` — the FLOOR of the average,
    e.g. 152//24=6 for sII 2:1 CH4+ethanol) and a SINGLE residue name (MOL_H)
    for ALL cage guests. The 5-atom CH4 guests got MOL_H and were walked with
    the wrong stride -> misaligned atoms + mislabeled residues.
  * ``write_interface_top_file``: declared only ``MOL_H`` in ``[ molecules ]``
    and ``#include`` d only ``etoh.itp`` — never ``CH4_H`` or
    ``ch4_hydrate.itp``.
  * The interface path has NO ``molecule_index`` (slab/piece builders set
    ``guest_descriptors`` + ``guest_atom_counts`` instead), so the
    ``next(m for m in iface.molecule_index ...)`` lookup returned ``None`` and
    fell back to the broken average-stride.

The fix mirrors the 29085047 ion_writer pattern, adapted to the interface's
descriptor-driven data model (``iter_guest_molecules`` with
``guest_descriptors`` + ``guest_atom_counts`` instead of ``molecule_index``).
When BOTH a built-in AND a custom cage guest are present (detected via
``guest_atom_counts``), the GRO walks per-molecule (built-in ch4 -> CH4_H +
reorder; custom ethanol -> MOL_H + no reorder) and the TOP run-length encodes
``[ molecules ]`` as ``(resname, count)`` runs, ``#include`` s BOTH ITPs, and
writes BOTH atomtypes blocks. The single-custom (only ethanol) and pure-built-
in (CH4/THF only) paths stay byte-identical — the new code only activates when
BOTH are present.

This test exercises the real GUI interface export path (hydrate -> slab
interface -> InterfaceGROMACSExporter) and asserts GROMACS consistency:
  * gmx grompp exits 0;
  * the .gro has BOTH CH4_H (5-atom) and MOL_H (9-atom) residues (not all
    MOL_H, not all CH4_H);
  * the .top ``[ molecules ]`` declares both CH4_H and MOL_H (run-length
    encoded in molecule order);
  * the .top ``#include``s both ``ch4_hydrate.itp`` (built-in) and
    ``etoh.itp`` (custom);
  * the CH4:ethanol molecule ratio matches the sII small:large cage ratio
    (16:8 = 2:1);
  * the .gro molecule runs EXACTLY match the .top ``[ molecules ]`` section.

Two regression guards verify the fix does not break the previously-working
paths:
  * single-custom-ethanol (only MOL_H, no CH4_H, byte-identical);
  * pure-built-in CH4 (only CH4_H, no MOL_H, byte-identical).
"""

import shutil
from collections import Counter, defaultdict
from unittest.mock import patch

import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import InterfaceGROMACSExporter  # noqa: E402
from tests.e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    parse_top_includes,
    run_gmx_grompp,
)

# Per-moleculetype atom counts (GROMACS [molecules] convention). Interface
# export writes ice SOL + water SOL + cage guests only (no solute/ion).
_ATOMS_PER_MOL = {"SOL": 4, "CH4_H": 5, "MOL_H": 9}


def _parse_gro_residue_summary(gro_path):
    """Return {resname: {"n_molecules": count, "atom_dist": {n_atoms: n_mols}}}.

    Groups consecutive atom lines by (res_seq, res_name) into residues, then
    by res_name. ``atom_dist`` maps atoms-per-residue -> number of residues
    with that count (catches the 5-atom CH4_H vs 9-atom MOL_H distinction).
    Mirrors test_e2e_custom_guest_mixed_cage.py.
    """
    with open(gro_path) as f:
        lines = f.read().splitlines()
    natom = int(lines[1].strip())
    residues = defaultdict(list)
    for ln in lines[2:2 + natom]:
        residues[(int(ln[0:5]), ln[5:10].strip())].append(ln[10:15].strip())
    by_name = defaultdict(list)
    for (rs, rn), atoms in residues.items():
        by_name[rn].append(atoms)
    out = {}
    for rn, entries in by_name.items():
        out[rn] = {
            "n_molecules": len(entries),
            "atom_dist": dict(Counter(len(a) for a in entries)),
            "total_atoms": sum(len(a) for a in entries),
        }
    return out


def _parse_top_molecules_runs(top_path):
    """Return ordered [(molname, count), ...] from .top [ molecules ] (runs)."""
    runs = []
    in_mol = False
    for line in open(top_path):
        s = line.strip()
        if s == "[ molecules ]":
            in_mol = True
            continue
        if in_mol:
            if not s or s.startswith(";"):
                continue
            if s.startswith("["):
                break
            parts = s.split()
            runs.append((parts[0], int(parts[1])))
    return runs


def _export_interface(iface, config, tmp, gro_name, top_name):
    """Export an interface via InterfaceGROMACSExporter (mock QFileDialog)."""
    gro_path = tmp / gro_name
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(iface, hydrate_config=config)
        assert ok is True, "InterfaceGROMACSExporter.export_interface_gromacs returned False"
    top_path = gro_path.with_name(gro_path.stem + ".top")
    return gro_path, top_path


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: mixed CH4(small) + ethanol-custom(large) sII hydrate
# -> slab interface -> InterfaceGROMACSExporter export (ONCE per module).
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def mixed_builtin_custom_interface_export(tmp_path_factory):
    """Build the mixed CH4+ethanol hydrate -> slab -> INTERFACE export.

    Mirrors the real UAT workflow (Hydrate -> Interface -> Export from Interface
    tab) and the ``tests/repro_molh_mixed.py`` reproduction script (minus the
    solute/ion steps — the interface path writes ice+water+guests only).
    Amortizes the GenIce2 generation across all test functions in this module.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="etoh_mix",  # custom guest type for ethanol (large cage)
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        cage_guest_assignments={
            "small": CageGuestAssignment(
                guest_type="ch4", occupancy=100.0,
            ),
            "large": CageGuestAssignment(
                guest_type="etoh_mix", guest_residue_name="MOL",
                guest_gro_path="quickice/data/custom/etoh.gro",
                guest_itp_path="quickice/data/custom/etoh.itp",
                guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
                guest_atom_count=9, occupancy=100.0,
            ),
        },
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    # Metadata must carry BOTH guest types (ch4 + etoh_mix).
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5, "etoh_mix": 9}

    # Slab interface (box >= 3.0 nm for grompp PBC; mirrors repro_molh_mixed).
    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=5.13629, box_y=5.13629, box_z=10.57382,
        seed=42, ice_thickness=5.13629, water_thickness=5.43753,
    ))
    assert iface.guest_nmolecules > 0, "mixed slab should have cage guests"
    assert iface.guest_atom_counts == {"ch4": 5, "etoh_mix": 9}

    # Export via the GUI InterfaceGROMACSExporter (mock QFileDialog — the real
    # UAT path). Stages ITPs + writes .gro/.top via _stage_hydrate_guest_itps.
    tmp = tmp_path_factory.mktemp("mixed_builtin_custom_interface_export")
    gro_path, top_path = _export_interface(
        iface, config, tmp, "iface_mix.gro", "iface_mix.top"
    )

    return {
        "tmp": tmp, "gro": gro_path, "top": top_path,
        "iface": iface, "config": config,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tests: mixed built-in+custom cage-guest INTERFACE export
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_mixed_interface_grompp_exit_zero(mixed_builtin_custom_interface_export):
    """gmx grompp must exit 0 on the mixed CH4+ethanol INTERFACE export.

    Before the fix, grompp failed with 'number of coordinates ... does not
    match topology' because the .gro was walked with the wrong (average-floor)
    stride and all guests labeled MOL_H, while the .top expected a single
    MOL_H count. After the fix, the .gro has CH4_H (5-atom) + MOL_H (9-atom)
    residues and the .top declares both with their correct ITPs -> atom counts
    match.
    """
    tmp = mixed_builtin_custom_interface_export["tmp"]
    shutil.copy(MDP_PATH, tmp / "em.mdp")
    rc, stderr = run_gmx_grompp(
        tmp, gro_file="iface_mix.gro", top_file="iface_mix.top"
    )
    assert rc == 0, (
        f"gmx grompp failed on mixed CH4+ethanol interface export:\n{stderr}"
    )


def test_mixed_interface_gro_has_both_resnames(mixed_builtin_custom_interface_export):
    """The .gro must contain BOTH CH4_H (5-atom) and MOL_H (9-atom) residues.

    Before the fix, ALL cage guests were labeled MOL_H (the custom residue
    name) and walked with the average-floor stride. After the fix, built-in
    ch4 -> CH4_H (5-atom) and custom ethanol -> MOL_H (9-atom).
    """
    summary = _parse_gro_residue_summary(mixed_builtin_custom_interface_export["gro"])
    assert "CH4_H" in summary, (
        f"mixed .gro must contain CH4_H (built-in small-cage guests), "
        f"got resnames={sorted(summary)}"
    )
    assert "MOL_H" in summary, (
        f"mixed .gro must contain MOL_H (custom large-cage guests), "
        f"got resnames={sorted(summary)}"
    )
    # CH4_H residues must be 5-atom (not 9 — the old mislabeling wrote 5-atom
    # CH4 fragments under MOL_H with the wrong stride).
    assert summary["CH4_H"]["atom_dist"] == {5: summary["CH4_H"]["n_molecules"]}, (
        f"CH4_H residues must all be 5-atom, got dist="
        f"{summary['CH4_H']['atom_dist']}"
    )
    # MOL_H residues must be 9-atom (custom ethanol).
    assert summary["MOL_H"]["atom_dist"] == {9: summary["MOL_H"]["n_molecules"]}, (
        f"MOL_H residues must all be 9-atom (custom ethanol), got dist="
        f"{summary['MOL_H']['atom_dist']}"
    )
    # No garbage resnames.
    bad = set(summary) & {"GUE", "UNK", "UNK_H", "H2_H"}
    assert not bad, f"garbage resnames in mixed .gro: {bad}"


def test_mixed_interface_top_declares_both_molecules(mixed_builtin_custom_interface_export):
    """The .top [ molecules ] must declare BOTH CH4_H and MOL_H (as runs).

    Before the fix, the .top declared only 'MOL_H {count}' (single line) —
    the CH4 cage guests were never declared as CH4_H. After the fix, the
    [ molecules ] section is run-length encoded matching the .gro layout
    (bottom [CH4_H][MOL_H] + top [CH4_H][MOL_H]).
    """
    runs = _parse_top_molecules_runs(mixed_builtin_custom_interface_export["top"])
    guest_runs = [r for r in runs if r[0] in ("CH4_H", "MOL_H")]
    run_names = [r[0] for r in guest_runs]
    assert "CH4_H" in run_names, (
        f".top [molecules] must declare CH4_H, got guest runs={guest_runs}"
    )
    assert "MOL_H" in run_names, (
        f".top [molecules] must declare MOL_H, got guest runs={guest_runs}"
    )
    # GUE/UNK must never appear (would mean custom_guest_info was not threaded
    # or the per-molecule type was lost).
    assert "GUE" not in run_names and "UNK" not in run_names, (
        f"garbage resname in .top [molecules]: {guest_runs}"
    )


def test_mixed_interface_top_includes_both_itps(mixed_builtin_custom_interface_export):
    """The .top must #include BOTH ch4_hydrate.itp (built-in) and etoh.itp (custom)."""
    includes = parse_top_includes(str(mixed_builtin_custom_interface_export["top"]))
    assert "ch4_hydrate.itp" in includes, (
        f".top must #include ch4_hydrate.itp (built-in CH4_H), got {includes}"
    )
    assert "etoh.itp" in includes, (
        f".top must #include etoh.itp (custom MOL_H), got {includes}"
    )
    # Both ITPs must be staged in the export dir (by _stage_hydrate_guest_itps,
    # already fixed in 29085047 — config-driven, stages both when mixed).
    tmp = mixed_builtin_custom_interface_export["tmp"]
    assert (tmp / "ch4_hydrate.itp").exists(), (
        "ch4_hydrate.itp not staged by _stage_hydrate_guest_itps"
    )
    assert (tmp / "etoh.itp").exists(), (
        "etoh.itp (transformed, MOL_H) not staged by _stage_hydrate_guest_itps"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H).
    staged_etoh = (tmp / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype — "
        "transform_guest_itp was not applied"
    )


def test_mixed_interface_ch4_ethanol_ratio(mixed_builtin_custom_interface_export):
    """CH4:ethanol molecule ratio must match sII small:large (16:8 = 2:1)."""
    summary = _parse_gro_residue_summary(mixed_builtin_custom_interface_export["gro"])
    n_ch4 = summary.get("CH4_H", {}).get("n_molecules", 0)
    n_etoh = summary.get("MOL_H", {}).get("n_molecules", 0)
    assert n_ch4 > 0 and n_etoh > 0, (
        f"both CH4_H and MOL_H must be present, got CH4_H={n_ch4} MOL_H={n_etoh}"
    )
    assert n_ch4 == 2 * n_etoh, (
        f"CH4:ethanol ratio {n_ch4}:{n_etoh} != 2:1 (sII small:large 16:8)"
    )


def test_mixed_interface_gro_matches_top_molecules(mixed_builtin_custom_interface_export):
    """The .gro molecule runs must EXACTLY match the .top [ molecules ] section.

    GROMACS groups consecutive .gro atoms by [ molecules ] entries, so a
    mismatch here is a fatal grompp error. The mixed [CH4_H][MOL_H][CH4_H][MOL_H]
    layout (bottom+top ice layers) must produce matching run-length entries.
    Mirrors the proven comparison in test_e2e_custom_guest_mixed_cage.py.
    """
    gro_path = mixed_builtin_custom_interface_export["gro"]
    top_path = mixed_builtin_custom_interface_export["top"]

    # Build .gro molecule-run sequence: parse atom lines, group consecutive
    # atoms by resname into atom-runs, then convert to molecule-runs via the
    # per-moleculetype atom count.
    with open(gro_path) as f:
        lines = f.readlines()
    gro_total = int(lines[1].strip())
    atom_runs = []
    for i in range(2, 2 + gro_total):
        rn = lines[i][5:10].strip()
        if atom_runs and atom_runs[-1][0] == rn:
            atom_runs[-1] = (rn, atom_runs[-1][1] + 1)
        else:
            atom_runs.append((rn, 1))
    gro_mol_runs = []
    for rn, atom_cnt in atom_runs:
        apm = _ATOMS_PER_MOL.get(rn)
        assert apm is not None, f"unknown/garbage resname {rn!r} in .gro"
        assert atom_cnt % apm == 0, (
            f"resname {rn}: {atom_cnt} atoms not divisible by {apm}"
        )
        gro_mol_runs.append((rn, atom_cnt // apm))

    top_mol_runs = _parse_top_molecules_runs(top_path)

    assert gro_mol_runs == top_mol_runs, (
        f".gro runs != .top [molecules]:\n gro={gro_mol_runs}\n top={top_mol_runs}"
    )
    # Atom count from .top (count * atoms-per-moleculetype) must equal .gro.
    top_atoms = sum(cnt * _ATOMS_PER_MOL[nm] for nm, cnt in top_mol_runs
                    if nm in _ATOMS_PER_MOL)
    assert top_atoms == gro_total, (
        f"atom count mismatch: .top={top_atoms} .gro={gro_total}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Regression guard: single-custom-ethanol (no built-in) must stay byte-identical
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_single_custom_ethanol_interface_no_builtin_still_only_mol_h(tmp_path_factory):
    """Regression guard: single-custom-ethanol interface (no built-in) -> only MOL_H.

    The fix's new mixed-case code only activates when BOTH a built-in AND a
    custom cage guest are present. The pure single-custom path (only ethanol,
    no built-in) must stay byte-identical: only MOL_H residues (no CH4_H),
    grompp rc=0, .top declares only MOL_H + #includes only etoh.itp.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    # Single-custom: only etoh_e2e in the metadata (no ch4/thf).
    assert candidate.metadata["guest_atom_counts"] == {"etoh_e2e": 9}

    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=3.0, box_y=3.0, box_z=8.0,
        seed=42, ice_thickness=2.0, water_thickness=4.0,
    ))
    assert iface.guest_nmolecules > 0

    tmp = tmp_path_factory.mktemp("single_custom_ethanol_interface")
    gro_path, top_path = _export_interface(
        iface, config, tmp, "iface.gro", "iface.top"
    )

    summary = _parse_gro_residue_summary(gro_path)
    # Only MOL_H (no CH4_H — no built-in cage guests in this config).
    assert "MOL_H" in summary, (
        f"single-custom .gro must have MOL_H, got {sorted(summary)}"
    )
    assert "CH4_H" not in summary, (
        f"single-custom .gro must NOT have CH4_H (no built-in cage guests), "
        f"got resnames={sorted(summary)}"
    )
    # All MOL_H residues must be 9-atom (custom ethanol, no fragmentation).
    assert summary["MOL_H"]["atom_dist"] == {9: summary["MOL_H"]["n_molecules"]}, (
        f"single-custom MOL_H must all be 9-atom, got dist="
        f"{summary['MOL_H']['atom_dist']}"
    )

    # .top [molecules] must declare only MOL_H (no CH4_H) for cage guests.
    runs = _parse_top_molecules_runs(top_path)
    guest_runs = [r for r in runs if r[0] in ("CH4_H", "MOL_H", "GUE", "UNK")]
    assert all(r[0] == "MOL_H" for r in guest_runs), (
        f"single-custom .top guest runs must be only MOL_H, got {guest_runs}"
    )

    # .top must #include etoh.itp but NOT ch4_hydrate.itp (no built-in).
    includes = parse_top_includes(str(top_path))
    assert "etoh.itp" in includes
    assert "ch4_hydrate.itp" not in includes, (
        f"single-custom .top must NOT #include ch4_hydrate.itp (no built-in "
        f"CH4 cage guests), got {includes}"
    )

    # grompp must pass.
    shutil.copy(MDP_PATH, tmp / "em.mdp")
    rc, stderr = run_gmx_grompp(tmp, gro_file="iface.gro", top_file="iface.top")
    assert rc == 0, f"single-custom interface grompp failed:\n{stderr}"


# ══════════════════════════════════════════════════════════════════════════════
# Regression guard: pure-built-in CH4 (no custom) must stay byte-identical
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_pure_builtin_ch4_interface_still_only_ch4_h(tmp_path_factory):
    """Regression guard: pure-built-in CH4 interface (no custom) -> only CH4_H.

    The fix's new mixed-case code only activates when BOTH a built-in AND a
    custom cage guest are present. The pure-built-in path (CH4 only, no custom)
    must stay byte-identical: custom_guest_info is None (no custom cage
    assignments), so the built-in branch runs unchanged — only CH4_H residues
    (no MOL_H), grompp rc=0, .top declares only CH4_H + #includes only
    ch4_hydrate.itp.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    # Pure built-in: only ch4 in the metadata (no custom).
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5}

    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=3.0, box_y=3.0, box_z=8.0,
        seed=42, ice_thickness=2.0, water_thickness=4.0,
    ))
    assert iface.guest_nmolecules > 0

    tmp = tmp_path_factory.mktemp("pure_builtin_ch4_interface")
    gro_path, top_path = _export_interface(
        iface, config, tmp, "iface.gro", "iface.top"
    )

    summary = _parse_gro_residue_summary(gro_path)
    # Only CH4_H (no MOL_H — no custom cage guests in this config).
    assert "CH4_H" in summary, (
        f"pure-built-in .gro must have CH4_H, got {sorted(summary)}"
    )
    assert "MOL_H" not in summary, (
        f"pure-built-in .gro must NOT have MOL_H (no custom cage guests), "
        f"got resnames={sorted(summary)}"
    )
    # All CH4_H residues must be 5-atom (built-in methane, no fragmentation).
    assert summary["CH4_H"]["atom_dist"] == {5: summary["CH4_H"]["n_molecules"]}, (
        f"pure-built-in CH4_H must all be 5-atom, got dist="
        f"{summary['CH4_H']['atom_dist']}"
    )

    # .top [molecules] must declare only CH4_H (no MOL_H) for cage guests.
    runs = _parse_top_molecules_runs(top_path)
    guest_runs = [r for r in runs if r[0] in ("CH4_H", "MOL_H", "GUE", "UNK")]
    assert all(r[0] == "CH4_H" for r in guest_runs), (
        f"pure-built-in .top guest runs must be only CH4_H, got {guest_runs}"
    )

    # .top must #include ch4_hydrate.itp but NOT etoh.itp (no custom).
    includes = parse_top_includes(str(top_path))
    assert "ch4_hydrate.itp" in includes
    assert "etoh.itp" not in includes, (
        f"pure-built-in .top must NOT #include etoh.itp (no custom cage "
        f"guests), got {includes}"
    )

    # grompp must pass.
    shutil.copy(MDP_PATH, tmp / "em.mdp")
    rc, stderr = run_gmx_grompp(tmp, gro_file="iface.gro", top_file="iface.top")
    assert rc == 0, f"pure-built-in interface grompp failed:\n{stderr}"
