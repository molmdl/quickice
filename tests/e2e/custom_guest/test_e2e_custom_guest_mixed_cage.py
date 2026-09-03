"""Regression test: MIXED built-in+custom cage-guest ion->export flow.

Issue 3 (molh-atom-drop-origin). Before this fix, exporting a slab interface
built from a MIXED sII hydrate (CH4 built-in in small cages + ethanol custom
in large cages) through the ion step produced a structurally INVALID GROMACS
export:

  * ``ion_inserter._build_molecule_index_from_structure`` labeled ALL cage
    guests ``mol_type="guest"``, DISCARDING the per-molecule type yielded by
    ``iter_guest_molecules`` (which correctly identifies ch4 vs custom
    ethanol via descriptor ``atom_labels`` matching).
  * ``write_ion_gro_file`` / ``write_ion_top_file``: when ``custom_active``
    (custom guest present), the writers fell back to
    ``next(iter(custom_by_moltype.values()))`` (the first custom = MOL_H) for
    ANY guest mol_type not in ``custom_by_moltype`` — including the built-in
    CH4 entries -> ALL 864 CH4 (5-atom) cage guests got MOL_H while the .top
    #included only ``etoh.itp`` (9 atoms/MOL_H) -> gmx grompp atom-count
    mismatch (expects 1296x9=11664, gets 864x5 + 432x9 = 8208).
  * ``_stage_hydrate_guest_itps`` staged ONLY the custom ITP (etoh.itp), not
    the built-in ``ch4_hydrate.itp``, when ``custom_guest_info`` was non-empty.
  * ``detect_guest_type_from_atoms`` MISIDENTIFIES ethanol as ch4 (both have
    C+H; ``_get_molecule_atoms`` grabs only the first 5 atoms C+4H and misses
    the O), so the writers CANNOT use atom-name detection to distinguish CH4
    from ethanol in the mixed case — they MUST use the per-molecule mol_type.

The fix preserves the per-molecule cage-guest ``mol_type`` through the ion
inserter so the writers can distinguish built-in (CH4 -> CH4_H) from custom
(ethanol -> MOL_H) cage guests, then declares each with its correct residue
name + ITP. The single-custom-guest path (only ethanol, no built-in) and the
mixed-built-in path (CH4+THF, no custom) stay byte-identical — the new code
only activates when BOTH a built-in AND a custom cage guest are present.

This test exercises the real GUI export path (hydrate -> slab interface ->
solute -> ion -> stage ITPs + write .gro/.top via IonGROMACSExporter) and
asserts GROMACS consistency:
  * gmx grompp exits 0;
  * the .gro has BOTH CH4_H (5-atom) and MOL_H (9-atom) residues (not all
    MOL_H);
  * the .top ``[ molecules ]`` declares both CH4_H and MOL_H (run-length
    encoded in molecule order);
  * the .top ``#include``s both ``ch4_hydrate.itp`` (built-in) and
    ``etoh.itp`` (custom);
  * the CH4:ethanol molecule ratio matches the sII small:large cage ratio
    (16:8 = 2:1);
  * no garbage resnames (GUE/UNK) appear.

A single-custom-ethanol regression guard verifies the fix does not break the
previously-working single-custom path (only MOL_H, no CH4_H, byte-identical).
The mixed-built-in CH4+THF path is covered by ``test_e2e_mixed_ion_export.py``.

Also hosts the mixed-occupancy GUI multi-molecule writers grompp test
(``test_mixed_gui_grompp_passes``, 42-05 MIXED-04 provenance) ported from
tests/test_e2e_mixed_cage_occupancy.py by 48.3-17 (that file was renamed to
tests/test_hydrate_mixed_placement.py for its 4 GenIce2 placement siblings) --
same concern: mixed cage export + grompp (list-form ``custom_guest_info`` +
registry writers-direct path, no GenIce2).
"""

import shutil
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.moleculetype_registry import (  # noqa: E402
    MoleculetypeRegistry,
)
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
    MoleculeIndex,
)
from quickice.gui.export import IonGROMACSExporter  # noqa: E402
from tests.e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _insert_ions,
    _insert_solutes,
    _stage_custom_guest_itp,
    _stage_itp_files,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_includes,
    parse_top_molecules,
    run_gmx_grompp,
)

# Per-moleculetype atom counts (GROMACS [molecules] convention).
# Includes CH4_L (the liquid solute) so the .gro/.top run comparison covers it.
_ATOMS_PER_MOL = {"SOL": 4, "CH4_H": 5, "MOL_H": 9, "CH4_L": 5, "NA": 1, "CL": 1}


def _parse_gro_residue_summary(gro_path):
    """Return {resname: {"n_molecules": count, "atom_dist": {n_atoms: n_mols}}}.

    Groups consecutive atom lines by (res_seq, res_name) into residues, then
    by res_name. ``atom_dist`` maps atoms-per-residue -> number of residues
    with that count (catches the 5-atom CH4_H vs 9-atom MOL_H distinction).
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


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: mixed CH4(small) + ethanol-custom(large) sII hydrate
# -> slab -> solute -> ion -> GUI IonGROMACSExporter export (ONCE per module).
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def mixed_builtin_custom_export(tmp_path_factory):
    """Build the mixed CH4+ethanol hydrate -> slab -> solute -> ion -> export.

    Mirrors the real UAT workflow (Hydrate -> Interface -> Custom -> Solute ->
    Ion -> Export from Ion tab) and the ``tests/repro_molh_mixed.py``
    reproduction script. Amortizes the GenIce2 generation across all test
    functions in this module.
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
    def _make_iface():
        return assemble_slab(candidate, InterfaceConfig(
            mode="slab", box_x=5.13629, box_y=5.13629, box_z=10.57382,
            seed=42, ice_thickness=5.13629, water_thickness=5.43753,
        ))

    iface = _make_iface()
    assert iface.guest_nmolecules > 0, "mixed slab should have cage guests"
    assert iface.guest_atom_counts == {"ch4": 5, "etoh_mix": 9}

    # Solute (CH4 in the liquid region) + ion insertion (NaCl).
    solute = _insert_solutes(iface, solute_type='CH4', concentration=0.3)
    iface_ion = _make_iface()
    iface_ion.solute_type = solute.solute_type
    iface_ion.solute_positions = solute.positions
    iface_ion.solute_atom_names = solute.atom_names
    iface_ion.solute_n_molecules = solute.n_molecules
    iface_ion.solute_molecule_indices = solute.molecule_indices
    iface_ion.solute_registry = solute.registry
    ion = _insert_ions(iface_ion, concentration=0.15)

    # The ion molecule_index must carry per-molecule mol_types (ch4/etoh_mix)
    # AND the CORRECT per-molecule counts (5 for CH4, 9 for ethanol) — the
    # fix preserves the per-molecule type from iter_guest_molecules.
    cage_mol_types = Counter(
        m.mol_type for m in ion.molecule_index
        if m.mol_type not in ("water", "ice", "na", "cl", "solute", "custom")
    )
    assert "ch4" in cage_mol_types, (
        f"ion molecule_index must label built-in CH4 cage guests 'ch4', "
        f"got mol_types={dict(cage_mol_types)}"
    )
    assert "etoh_mix" in cage_mol_types, (
        f"ion molecule_index must label custom ethanol cage guests "
        f"'etoh_mix', got mol_types={dict(cage_mol_types)}"
    )

    # Export via the GUI IonGROMACSExporter (mock QFileDialog — the real UAT
    # path). Stages ITPs + writes .gro/.top via _stage_hydrate_guest_itps.
    tmp = tmp_path_factory.mktemp("mixed_builtin_custom_export")
    gro_path = tmp / "ions_mix.gro"
    top_path = tmp / "ions_mix.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = IonGROMACSExporter(parent_widget=None)
        ok = exporter.export_ion_gromacs(ion, hydrate_config=config)
        assert ok is True, "IonGROMACSExporter.export_ion_gromacs returned False"

    return {
        "tmp": tmp, "gro": gro_path, "top": top_path,
        "ion": ion, "config": config,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tests: mixed built-in+custom cage-guest ion export
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_mixed_builtin_custom_grompp_exit_zero(mixed_builtin_custom_export):
    """gmx grompp must exit 0 on the mixed CH4+ethanol ion export.

    This is the core UAT assertion: before the fix, grompp failed with
    'number of coordinates ... does not match topology' because the .gro
    had 864×5+432×9=8208 MOL_H atoms but the .top expected 1296×9=11664
    (etoh.itp defines MOL_H with 9 atoms). After the fix, the .gro has
    CH4_H (5-atom) + MOL_H (9-atom) residues and the .top declares both
    with their correct ITPs -> atom counts match.
    """
    tmp = mixed_builtin_custom_export["tmp"]
    shutil.copy(MDP_PATH, tmp / "em.mdp")
    rc, stderr = run_gmx_grompp(
        tmp, gro_file="ions_mix.gro", top_file="ions_mix.top"
    )
    assert rc == 0, (
        f"gmx grompp failed on mixed CH4+ethanol ion export:\n{stderr}"
    )


def test_mixed_builtin_custom_gro_has_both_resnames(mixed_builtin_custom_export):
    """The .gro must contain BOTH CH4_H (5-atom) and MOL_H (9-atom) residues.

    Before the fix, ALL 1296 cage guests were labeled MOL_H (the custom
    residue name), so 864 CH4 (5-atom) cage guests got MOL_H. After the fix,
    built-in CH4 -> CH4_H and custom ethanol -> MOL_H.
    """
    summary = _parse_gro_residue_summary(mixed_builtin_custom_export["gro"])
    assert "CH4_H" in summary, (
        f"mixed .gro must contain CH4_H (built-in small-cage guests), "
        f"got resnames={sorted(summary)}"
    )
    assert "MOL_H" in summary, (
        f"mixed .gro must contain MOL_H (custom large-cage guests), "
        f"got resnames={sorted(summary)}"
    )
    # CH4_H residues must be 5-atom (not 9 — the old mislabeling wrote
    # 5-atom CH4 fragments under MOL_H).
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


def test_mixed_builtin_custom_top_declares_both_molecules(mixed_builtin_custom_export):
    """The .top [ molecules ] must declare BOTH CH4_H and MOL_H (as runs).

    Before the fix, the .top declared only 'MOL_H {count}' (single line) —
    the 864 CH4 cage guests were never declared as CH4_H. After the fix,
    the [ molecules ] section is run-length encoded: CH4_H run + MOL_H run
    (per ice layer: bottom [CH4_H][MOL_H] + top [CH4_H][MOL_H]).
    """
    runs = _parse_top_molecules_runs(mixed_builtin_custom_export["top"])
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


def test_mixed_builtin_custom_top_includes_both_itps(mixed_builtin_custom_export):
    """The .top must #include BOTH ch4_hydrate.itp (built-in) and etoh.itp (custom)."""
    includes = parse_top_includes(str(mixed_builtin_custom_export["top"]))
    assert "ch4_hydrate.itp" in includes, (
        f".top must #include ch4_hydrate.itp (built-in CH4_H), got {includes}"
    )
    assert "etoh.itp" in includes, (
        f".top must #include etoh.itp (custom MOL_H), got {includes}"
    )
    # Both ITPs must be staged in the export dir.
    tmp = mixed_builtin_custom_export["tmp"]
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


def test_mixed_builtin_custom_ch4_ethanol_ratio(mixed_builtin_custom_export):
    """CH4:ethanol molecule ratio must match sII small:large (16:8 = 2:1)."""
    summary = _parse_gro_residue_summary(mixed_builtin_custom_export["gro"])
    n_ch4 = summary.get("CH4_H", {}).get("n_molecules", 0)
    n_etoh = summary.get("MOL_H", {}).get("n_molecules", 0)
    assert n_ch4 > 0 and n_etoh > 0, (
        f"both CH4_H and MOL_H must be present, got CH4_H={n_ch4} MOL_H={n_etoh}"
    )
    assert n_ch4 == 2 * n_etoh, (
        f"CH4:ethanol ratio {n_ch4}:{n_etoh} != 2:1 (sII small:large 16:8)"
    )


def test_mixed_builtin_custom_gro_matches_top_molecules(mixed_builtin_custom_export):
    """The .gro molecule runs must EXACTLY match the .top [ molecules ] section.

    GROMACS groups consecutive .gro atoms by [ molecules ] entries, so a
    mismatch here is a fatal grompp error. The mixed [CH4_H][MOL_H][CH4_H][MOL_H]
    layout (bottom+top ice layers) must produce matching run-length entries.
    Mirrors the proven comparison in test_e2e_mixed_ion_export.py.
    """
    gro_path = mixed_builtin_custom_export["gro"]
    top_path = mixed_builtin_custom_export["top"]

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
def test_single_custom_ethanol_no_builtin_still_only_mol_h(tmp_path_factory):
    """Regression guard: single-custom-ethanol (no built-in) -> only MOL_H.

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
    ion = _insert_ions(iface, concentration=0.15)

    tmp = tmp_path_factory.mktemp("single_custom_ethanol")
    gro_path = tmp / "ions.gro"
    top_path = tmp / "ions.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = IonGROMACSExporter(parent_widget=None)
        ok = exporter.export_ion_gromacs(ion, hydrate_config=config)
        assert ok is True

    summary = _parse_gro_residue_summary(gro_path)
    # Only MOL_H (no CH4_H — no built-in cage guests in this config).
    assert "MOL_H" in summary, f"single-custom .gro must have MOL_H, got {sorted(summary)}"
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
    rc, stderr = run_gmx_grompp(tmp, gro_file="ions.gro", top_file="ions.top")
    assert rc == 0, f"single-custom grompp failed:\n{stderr}"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 42-05: GUI mixed-guest grompp e2e (MIXED-04, GUI path)
# ══════════════════════════════════════════════════════════════════════════════
#
# Ported verbatim from tests/test_e2e_mixed_cage_occupancy.py by 48.3-17
# (that file was renamed to tests/test_hydrate_mixed_placement.py for its 4
# GenIce2 placement siblings; this writers-direct grompp test shares THIS
# file's concern: mixed cage export + grompp).
#
# Proves ``gmx grompp`` exits 0 on a mixed hydrate (built-in CH4 + custom
# ethanol) exported via the GUI multi-molecule writers
# (``write_multi_molecule_gro_file`` + ``write_multi_molecule_top_file`` with a
# ``custom_guest_info`` LIST + ``MoleculetypeRegistry``), with ITPs staged via
# ``_stage_itp_files`` + ``_stage_custom_guest_itp``.  Closes MIXED-04 for the
# GUI path (the CLI half is plan 42-07).
#
# Pattern: synthetic 2-water + 1-CH4 + 1-ethanol system (22 atoms, no GenIce2,
# <1s) → write_multi_molecule_* (custom_guest_info list + registry) → stage
# ITPs → assert_itp_completeness + assert_gro_top_consistent → run_gmx_grompp
# (exit 0).  Mirrors the 41-10 single-custom-guest pattern, extended to mixed
# occupancy (built-in CH4 via registry + custom ethanol via custom_guest_info
# fire in the SAME .gro/.top).


@gmx_skipif
def test_mixed_gui_grompp_passes(tmp_path):
    """gmx grompp exits 0 on a mixed hydrate (CH4 + custom ethanol) exported
    via the GUI multi-molecule writers (write_multi_molecule_gro_file +
    write_multi_molecule_top_file with a custom_guest_info LIST + registry).

    Builds a tiny synthetic 2-water + 1-CH4 + 1-ethanol system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 5 CH4 atoms + 9
    ethanol atoms = 22 atoms.  Stages tip4p-ice.itp + ch4_hydrate.itp +
    the transformed etoh.itp (moleculetype MOL_H), then runs gmx grompp.

    The built-in CH4 resolves via the registry (hydrate_CH4 -> "CH4_H"); the
    custom ethanol resolves via custom_guest_info (etoh_mix -> "MOL_H").
    Both fire in the SAME .gro/.top — the defining property of mixed cage
    occupancy (MIXED-04, GUI path).
    """
    # Synthetic 2-water + 1-CH4 + 1-ethanol system (22 atoms total).
    # molecule_index start indices (per plan, "adjust start indices
    # carefully — water 0-7, ch4 8-12, etoh 13-21"):
    #   water 1: atoms 0-3   (start=0,  count=4)
    #   water 2: atoms 4-7   (start=4,  count=4)
    #   CH4:     atoms 8-12  (start=8,  count=5)
    #   ethanol: atoms 13-21 (start=13, count=9)
    positions = np.zeros((22, 3))
    # Water (8 atoms: 2 × OW,HW1,HW2,MW)
    for i in range(8):
        positions[i] = [0.01 * (i + 1), 0.01 * (i + 1), 0.01 * (i + 1)]
    # CH4 (5 atoms: C,H,H,H,H) — built-in, handled by registry
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]
    # Ethanol (9 atoms: H,C,H,H,C,H,H,O,H) — custom, handled by custom_guest_info
    for i in range(9):
        positions[13 + i] = [0.2 + 0.01 * i, 0.2, 0.2]

    atom_names = [
        # water mol 1
        "OW", "HW1", "HW2", "MW",
        # water mol 2
        "OW", "HW1", "HW2", "MW",
        # CH4 guest (built-in)
        "C", "H", "H", "H", "H",
        # ethanol guest (custom, matches etoh.itp [ atoms ] order)
        "H", "C", "H", "H", "C", "H", "H", "O", "H",
    ]

    # Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp); 3.0 nm gives a
    # comfortable margin (STATE [41-10] lesson: grompp rejects box exactly at
    # 2*cutoff; cutoff 1.0 nm < half the shortest box vector must be strict).
    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),        # built-in -> registry -> "CH4_H"
        MoleculeIndex(13, 9, "etoh_mix"),  # custom -> custom_guest_info -> "MOL_H"
    ]

    # Registry with the built-in CH4 registered (hydrate_CH4 -> "CH4_H").
    registry = MoleculetypeRegistry()
    registry.register_hydrate_guest("CH4")

    # custom_guest_info LIST (Phase 42 API): one entry per custom guest.
    # ch4 is built-in so NOT in the list — the registry handles it.
    custom_guest_info = [
        {
            "mol_type": "etoh_mix",
            "residue_name": "MOL_H",
            "itp_path": Path(ETOH_ITP),
        }
    ]
    # itp_files maps mol_type -> itp filename so the writer emits the correct
    # #include for each guest (ch4 -> ch4_hydrate.itp, etoh_mix -> etoh.itp).
    itp_files = {
        "ch4": "ch4_hydrate.itp",
        "etoh_mix": "etoh.itp",
    }

    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(gro),
        "mixed guest hydrate",
        atom_names=atom_names,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )
    write_multi_molecule_top_file(
        molecule_index,
        str(top),
        "mixed guest hydrate",
        itp_files=itp_files,
        registry=registry,
        custom_guest_info=custom_guest_info,
    )

    # Stage MDP + ITPs (repo convention: writers don't copy ITPs; staging does).
    # _stage_itp_files stages tip4p-ice.itp + ch4_hydrate.itp + etoh.itp
    # (etoh under-transformed: moleculetype 'etoh', atomtypes commented out).
    # _stage_custom_guest_itp overwrites etoh.itp with the fully-transformed
    # copy (moleculetype 'MOL_H', [atoms] resname 'MOL_H') — the prerequisite
    # for gmx grompp to succeed.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    _stage_itp_files(str(top), ws)
    _stage_custom_guest_itp(ws, Path(ETOH_ITP), "MOL")

    # All #include'd ITPs present in the workspace.
    assert_itp_completeness(str(top), ws)
    # GRO residues <-> TOP [molecules] cross-check.
    assert_gro_top_consistent(str(gro), str(top))

    # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert exit_code == 0, f"gmx grompp failed (mixed GUI):\n{stderr}"

    # .top [molecules] lists SOL + CH4_H + MOL_H (the mixed-occupancy signature).
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "CH4_H" in mols and "MOL_H" in mols, (
        f"expected SOL + CH4_H + MOL_H in [molecules], got {mols}"
    )

    # .gro residues contain SOL + CH4_H + MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert {"SOL", "CH4_H", "MOL_H"}.issubset(gro_res), (
        f"expected SOL + CH4_H + MOL_H in .gro residues, got {gro_res}"
    )
