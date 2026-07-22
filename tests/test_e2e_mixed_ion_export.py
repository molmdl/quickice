"""Regression test: mixed built-in hydrate (CH4 + THF) ion->export flow.

Phase 45-15 root-cause fix. Before the fix, exporting a slab interface built
from a MIXED sII hydrate (CH4 in small cages + THF in large cages) through
the ion step produced a structurally INVALID GROMACS export:

  * ``ion_inserter._build_molecule_index_from_structure`` computed a single
    uniform ``guest_atom_count // guest_mols`` (= 6624 // 864 = 7) and
    assigned count=7 to ALL 864 guest molecule_index entries. CH4 has 5
    atoms and THF has 13, so every per-molecule slice was corrupted (THF
    atoms appeared under a ``CH4_H`` resname; garbage ``GUE``/``H2_H``
    resnames appeared from misidentification on wrong-sized slices) and 576
    guest atoms were silently dropped (864 * 7 = 6048 < 6624).
  * ``write_ion_top_file`` detected only the FIRST guest type (ch4) -> the
    .top listed only ``CH4_H 864`` and #included only ``ch4_hydrate.itp``;
    ``THF_H`` was never declared and ``thf_hydrate.itp`` was never staged.
  * ``_stage_hydrate_guest_itps`` staged only the first detected built-in
    type -> ``thf_hydrate.itp`` was missing from the export dir.

The single-guest path (sI all-CH4) was unaffected because the uniform
``guest_atom_count // guest_mols`` = 5 is CORRECT when every guest is CH4.

This test exercises the real GUI export path (hydrate -> slab interface ->
insert_ions -> stage ITPs + write .gro/.top) and asserts GROMACS
consistency: the .gro molecule runs (resname + count) must EXACTLY match
the .top ``[ molecules ]`` section, the .gro atom count must equal the .top
sum (count * atoms-per-moleculetype), both built-in guest .itp files must
be staged + #included, the CH4:THF ratio must match the sII cage ratio
(16:8 = 2:1), and no garbage resnames (GUE/H2_H) may appear.

A single-guest sI all-CH4 regression guard verifies the fix does not break
the previously-working single-component path.
"""

from pathlib import Path
from collections import OrderedDict

import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import (
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.structure_generation.water_filler import get_cell_extent
from quickice.structure_generation.ion_inserter import insert_ions
from quickice.output.guest_info import _stage_hydrate_guest_itps
from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file


# Per-moleculetype atom counts (GROMACS [molecules] convention).
_ATOMS_PER_MOL = {"SOL": 4, "CH4_H": 5, "THF_H": 13, "NA": 1, "CL": 1}


def _slab_config(candidate):
    cell_ext = get_cell_extent(candidate.cell)
    box_x = max(cell_ext[0] * 2, 4.0)
    box_y = max(cell_ext[1] * 2, 4.0)
    ice_thickness = max(cell_ext[2], 2.0)
    water_thickness = 3.0
    box_z = 2 * ice_thickness + water_thickness
    return InterfaceConfig(
        mode="slab", box_x=box_x, box_y=box_y, box_z=box_z,
        seed=42, ice_thickness=ice_thickness, water_thickness=water_thickness,
    )


def _export_to_dir(ion_structure, hydrate_config, tmp_path):
    """Mirror the GUI export_ion_gromacs flow (stage ITPs + write .gro/.top)."""
    gro_path = tmp_path / "ions.gro"
    top_path = tmp_path / "ions.top"
    custom_guest_info, _staged = _stage_hydrate_guest_itps(
        tmp_path, hydrate_config, ion_structure,
        guest_atom_count=getattr(ion_structure, "guest_atom_count", 0),
        guest_nmolecules=getattr(ion_structure, "guest_nmolecules", 0),
    )
    write_ion_gro_file(ion_structure, str(gro_path), custom_guest_info=custom_guest_info)
    write_ion_top_file(ion_structure, str(top_path), custom_guest_info=custom_guest_info)
    return gro_path, top_path


def _parse_gro_mol_runs(gro_path):
    """Return (total_atoms, [(resname, n_molecules), ...]) from a .gro file."""
    with open(gro_path) as f:
        lines = f.readlines()
    total = int(lines[1].strip())
    # atom-runs (resname -> contiguous atom count)
    atom_runs = []
    for i in range(2, 2 + total):
        rn = lines[i][5:10].strip()
        if atom_runs and atom_runs[-1][0] == rn:
            atom_runs[-1] = (rn, atom_runs[-1][1] + 1)
        else:
            atom_runs.append((rn, 1))
    # convert to molecule-runs via per-moleculetype atom count
    mol_runs = []
    resnames_seen = set()
    for rn, atom_cnt in atom_runs:
        apm = _ATOMS_PER_MOL.get(rn)
        assert apm is not None, f"unknown/garbage resname {rn!r} in .gro"
        assert atom_cnt % apm == 0, f"resname {rn}: {atom_cnt} atoms not divisible by {apm}"
        mol_runs.append((rn, atom_cnt // apm))
        resnames_seen.add(rn)
    return total, mol_runs, resnames_seen


def _parse_top_molecules(top_path):
    """Return ordered [(molname, count), ...] from .top [ molecules ]."""
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


@pytest.fixture(scope="module")
def mixed_sii_ion_export(tmp_path_factory):
    """Build mixed sII -> slab -> ion -> export once for the module."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
        },
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5, "thf": 13}

    iface = generate_interface(candidate, _slab_config(candidate))
    # Phase 45-15: type-level guest metadata must be propagated onto the
    # InterfaceStructure so the ion inserter can walk per-molecule.
    assert getattr(iface, "guest_descriptors", None), (
        "InterfaceStructure must carry guest_descriptors for mixed hydrates"
    )
    assert getattr(iface, "guest_atom_counts", None) == {"ch4": 5, "thf": 13}

    ion = insert_ions(iface, 0.5, None, seed=42)

    # The ion molecule_index guest entries must have CORRECT per-molecule
    # counts (5 for CH4, 13 for THF), NOT a single uniform average (7).
    g_counts = sorted({m.count for m in ion.molecule_index if m.mol_type == "guest"})
    assert g_counts == [5, 13], (
        f"mixed-guest molecule_index must have counts 5 and 13, got {g_counts}"
    )
    assert sum(m.count for m in ion.molecule_index if m.mol_type == "guest") == 6624, (
        "no guest atoms may be dropped (864 mols * 7 = 6048 was the bug)"
    )

    tmp_path = tmp_path_factory.mktemp("mixed_ion_export")
    gro_path, top_path = _export_to_dir(ion, config, tmp_path)
    return {
        "tmp_path": tmp_path, "gro": gro_path, "top": top_path,
        "ion": ion, "config": config,
    }


def test_mixed_ion_export_no_garbage_resnames(mixed_sii_ion_export):
    """The .gro must contain only SOL/CH4_H/THF_H/NA/CL — no GUE/H2_H/UNK."""
    _, _, resnames = _parse_gro_mol_runs(mixed_sii_ion_export["gro"])
    bad = resnames & {"GUE", "H2_H", "UNK", "UNK_H"}
    assert not bad, f"garbage resnames present in .gro: {bad}"
    assert {"CH4_H", "THF_H"} <= resnames, (
        f"both CH4_H and THF_H must be present, got {resnames}"
    )


def test_mixed_ion_export_gro_matches_top_molecules(mixed_sii_ion_export):
    """The .gro molecule runs must EXACTLY match the .top [ molecules ] section.

    GROMACS groups consecutive .gro atoms by [ molecules ] entries, so a
    mismatch here is a fatal grompp error. A mixed [CH4][THF][CH4][THF]
    layout must produce 4 run-length [ molecules ] lines, not a single
    grouped total.
    """
    gro_total, gro_runs, _ = _parse_gro_mol_runs(mixed_sii_ion_export["gro"])
    top_runs = _parse_top_molecules(mixed_sii_ion_export["top"])
    assert gro_runs == top_runs, (
        f".gro runs != .top [molecules]:\n gro={gro_runs}\n top={top_runs}"
    )
    # Atom count from .top (count * atoms-per-moleculetype) must equal .gro.
    top_atoms = sum(cnt * _ATOMS_PER_MOL[nm] for nm, cnt in top_runs)
    assert top_atoms == gro_total, (
        f"atom count mismatch: .top={top_atoms} .gro={gro_total}"
    )


def test_mixed_ion_export_run_length_molecules(mixed_sii_ion_export):
    """[ molecules ] must be run-length encoded for the mixed [CH4][THF][CH4][THF] layout."""
    top_runs = _parse_top_molecules(mixed_sii_ion_export["top"])
    # Strip SOL/NA/CL to inspect the guest runs.
    guest_runs = [r for r in top_runs if r[0] in ("CH4_H", "THF_H")]
    # 4 runs (bottom-ch4, bottom-thf, top-ch4, top-thf), alternating types.
    assert len(guest_runs) == 4, f"expected 4 guest runs, got {guest_runs}"
    types_seq = [r[0] for r in guest_runs]
    assert types_seq == ["CH4_H", "THF_H", "CH4_H", "THF_H"], (
        f"guest run types must alternate CH4/THF/CH4/THF, got {types_seq}"
    )


def test_mixed_ion_export_ch4_thf_ratio(mixed_sii_ion_export):
    """CH4:THF molecule ratio must match the sII cage ratio (16:8 = 2:1)."""
    top_runs = _parse_top_molecules(mixed_sii_ion_export["top"])
    n_ch4 = sum(c for nm, c in top_runs if nm == "CH4_H")
    n_thf = sum(c for nm, c in top_runs if nm == "THF_H")
    assert n_ch4 == 2 * n_thf, f"CH4:THF ratio {n_ch4}:{n_thf} != 2:1 (sII 16:8)"
    assert n_ch4 > 0 and n_thf > 0


def test_mixed_ion_export_both_itps_staged_and_included(mixed_sii_ion_export):
    """Both ch4_hydrate.itp and thf_hydrate.itp must be staged + #included."""
    tmp = mixed_sii_ion_export["tmp_path"]
    assert (tmp / "ch4_hydrate.itp").exists(), "ch4_hydrate.itp not staged"
    assert (tmp / "thf_hydrate.itp").exists(), "thf_hydrate.itp not staged"
    top_text = mixed_sii_ion_export["top"].read_text()
    assert '#include "ch4_hydrate.itp"' in top_text
    assert '#include "thf_hydrate.itp"' in top_text


def test_mixed_ion_export_no_dropped_guest_atoms(mixed_sii_ion_export):
    """All 6624 guest atoms (576*5 + 288*13) must be written — none dropped."""
    gro_total, gro_runs, _ = _parse_gro_mol_runs(mixed_sii_ion_export["gro"])
    guest_atoms = sum(
        c * _ATOMS_PER_MOL[rn] for rn, c in gro_runs
        if rn in ("CH4_H", "THF_H")
    )
    assert guest_atoms == 6624, (
        f"guest atoms dropped: got {guest_atoms}, expected 6624 (576*5 + 288*13)"
    )


def test_single_guest_si_all_ch4_ion_export_unchanged(tmp_path_factory):
    """Regression guard: single-guest sI all-CH4 ion export must be unchanged.

    The fix's per-molecule walk must produce the same result as the old
    uniform divisor for single-guest hydrates (all-CH4: walk yields N entries
    of 5 summing to guest_atom_count, exactly matching the uniform 5). The
    .top must list a single CH4_H run (no THF, no run-length fragmentation).
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        cage_occupancy_small=100.0,
        cage_occupancy_large=100.0,
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    iface = generate_interface(candidate, _slab_config(candidate))
    ion = insert_ions(iface, 0.5, None, seed=42)

    # All guest entries must be CH4 (count 5).
    g_counts = sorted({m.count for m in ion.molecule_index if m.mol_type == "guest"})
    assert g_counts == [5], f"single-CH4 guests must all have count 5, got {g_counts}"

    tmp = tmp_path_factory.mktemp("single_ch4_ion_export")
    gro_path, top_path = _export_to_dir(ion, config, tmp)
    gro_total, gro_runs, resnames = _parse_gro_mol_runs(gro_path)
    top_runs = _parse_top_molecules(top_path)

    assert gro_runs == top_runs, (
        f"single-CH4: .gro runs != .top [molecules]:\n gro={gro_runs}\n top={top_runs}"
    )
    assert "THF_H" not in resnames, "single-CH4 export must not contain THF"
    assert "CH4_H" in resnames
    bad = resnames & {"GUE", "H2_H", "UNK", "UNK_H"}
    assert not bad, f"single-CH4: garbage resnames {bad}"
    # Only ONE CH4_H run (all guests contiguous, single type).
    ch4_runs = [r for r in top_runs if r[0] == "CH4_H"]
    assert len(ch4_runs) == 1, f"single-CH4 must be 1 run, got {ch4_runs}"
    top_atoms = sum(c * _ATOMS_PER_MOL[nm] for nm, c in top_runs)
    assert top_atoms == gro_total, "single-CH4: atom count mismatch"
    # thf_hydrate.itp must NOT be staged for a single-CH4 hydrate.
    assert not (tmp / "thf_hydrate.itp").exists(), (
        "thf_hydrate.itp must not be staged for single-CH4"
    )
    assert (tmp / "ch4_hydrate.itp").exists()
