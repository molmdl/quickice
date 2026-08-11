"""Reproduction script for SII mixed GUI export regression (Issues 1, 3, 4).

Mimics the EXACT GUI flow (not isolated writer calls) to expose the gap
between pytest (passes) and the user's actual GUI exports (fail).

Run:
    QT_QPA_PLATFORM=offscreen python tests/repro_sii_mixed_gui_regression.py
"""
import sys
import shutil
import traceback
from pathlib import Path
from collections import Counter, defaultdict
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.types import (
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
    IonConfig,
    SoluteConfig,
    CustomMoleculeConfig,
)
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.gui.export import InterfaceGROMACSExporter, IonGROMACSExporter

from e2e_export_helpers import (
    ETOH_GRO, ETOH_ITP, MDP_PATH,
    run_gmx_grompp, parse_top_includes, parse_top_molecules,
    parse_gro_atom_count, parse_gro_residue_names,
    _liquid_volume_nm3,
)

OUT = Path("/tmp/repro_sii_mixed_gui")
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True, exist_ok=True)
shutil.copy(MDP_PATH, OUT / "em.mdp")


def _parse_gro_residue_summary(gro_path):
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
            "multiset": dict(Counter(a for e in entries for a in e)),
        }
    return out


def _export_interface(iface, config, tmp, gro_name):
    gro_path = tmp / gro_name
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(iface, hydrate_config=config)
    top_path = gro_path.with_name(gro_path.stem + ".top")
    return gro_path, top_path, ok


def _export_ion(ion_struct, config, tmp, gro_name):
    gro_path = tmp / gro_name
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = IonGROMACSExporter(parent_widget=None)
        try:
            ok = exporter.export_ion_gromacs(ion_struct, hydrate_config=config)
        except Exception as e:
            print(f"      [export_ion_gromacs raised] {e}")
            return gro_path, None, False, str(e)
    top_path = gro_path.with_name(gro_path.stem + ".top")
    return gro_path, top_path, ok, None


# ─── Issue 3: mixed built-in CH4+THF slab INTERFACE export ─────────────────

def repro_issue3():
    print("\n=== ISSUE 3: mixed built-in CH4+THF slab interface export ===")
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
    print(f"  candidate.guest_atom_counts = {candidate.metadata.get('guest_atom_counts')}")

    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=5.13629, box_y=5.13629, box_z=10.57382,
        seed=42, ice_thickness=5.13629, water_thickness=5.43753,
    ))
    print(f"  iface.guest_atom_counts = {iface.guest_atom_counts}")
    print(f"  iface.guest_descriptors = {iface.guest_descriptors}")
    print(f"  iface.guest_nmolecules = {iface.guest_nmolecules}, guest_atom_count = {iface.guest_atom_count}")

    tmp = OUT / "issue3"
    tmp.mkdir(exist_ok=True)
    gro_path, top_path, ok = _export_interface(iface, config, tmp, "interface_slab.gro")
    print(f"  export ok = {ok}")

    summary = _parse_gro_residue_summary(gro_path)
    print(f"  .gro residues: { {k: v['n_molecules'] for k,v in summary.items()} }")
    ch4_h = summary.get("CH4_H", {})
    thf_h = summary.get("THF_H", {})
    print(f"  CH4_H: n_mols={ch4_h.get('n_molecules')}, atom_dist={ch4_h.get('atom_dist')}, multiset={ch4_h.get('multiset')}")
    print(f"  THF_H: n_mols={thf_h.get('n_molecules')}, atom_dist={thf_h.get('atom_dist')}")
    top_mols = parse_top_molecules(top_path)
    print(f"  .top [molecules]: {top_mols}")
    print(f"  .top #includes: {parse_top_includes(top_path)}")

    has_thf_in_ch4h = ch4_h and ("O" in (ch4_h.get("multiset") or {}) or "CA" in (ch4_h.get("multiset") or {}))
    if has_thf_in_ch4h:
        print("  >>> BUG CONFIRMED: THF atoms mislabeled as CH4_H (built-in branch single-type detection)")
    rc, stderr = run_gmx_grompp(tmp, gro_file="interface_slab.gro", top_file="interface_slab.top")
    print(f"  gmx grompp rc={rc}")
    if rc != 0:
        print(f"  >>> grompp FAILED (Issue 3 confirmed)")
    return rc == 0 and not has_thf_in_ch4h


# ─── Issue 1: full chain CH4+THF + custom mol(etoh) + solute(ch4) + ion ──────

def repro_issue1():
    print("\n=== ISSUE 1: full chain CH4+THF + custom mol(etoh) + solute(ch4) + ion ===")
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
    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=5.13629, box_y=5.13629, box_z=10.57382,
        seed=42, ice_thickness=5.13629, water_thickness=5.43753,
    ))
    print(f"  [slab] guest_descriptors={iface.guest_descriptors}, guest_atom_counts={iface.guest_atom_counts}")

    # Custom molecule insertion (etoh) — mimics Custom tab
    cm_config = CustomMoleculeConfig(
        placement_mode="random", gro_path=ETOH_GRO, itp_path=ETOH_ITP,
        molecule_count=3,
    )
    cm_inserter = CustomMoleculeInserter(cm_config)
    custom_struct = cm_inserter.place_random(iface, 3)
    iface_after_custom = custom_struct.interface_structure
    print(f"  [after custom] guest_descriptors={getattr(iface_after_custom, 'guest_descriptors', '<MISSING>')}, guest_atom_counts={getattr(iface_after_custom, 'guest_atom_counts', '<MISSING>')}")

    # Solute insertion (ch4) — mimics Solute tab
    sol_config = SoluteConfig(concentration_molar=0.3, solute_type="CH4")
    sol_inserter = SoluteInserter(config=sol_config, seed=42)
    solute_struct = sol_inserter.insert_solutes(iface_after_custom, sol_config)
    iface_after_solute = solute_struct.interface_structure
    print(f"  [after solute] guest_descriptors={getattr(iface_after_solute, 'guest_descriptors', '<MISSING>')}, guest_atom_counts={getattr(iface_after_solute, 'guest_atom_counts', '<MISSING>')}")

    # Prepare ion source (mimics main_window _on_insert_ions Solute source)
    ion_source = iface_after_solute
    ion_source.solute_type = solute_struct.solute_type
    ion_source.solute_positions = solute_struct.positions
    ion_source.solute_atom_names = solute_struct.atom_names
    ion_source.solute_n_molecules = solute_struct.n_molecules
    ion_source.solute_molecule_indices = solute_struct.molecule_indices
    ion_source.solute_registry = solute_struct.registry
    if hasattr(solute_struct, 'custom_molecule_count') and solute_struct.custom_molecule_count > 0:
        ion_source.custom_molecule_count = solute_struct.custom_molecule_count
        ion_source.custom_molecule_atom_count = solute_struct.custom_molecule_atom_count
        ion_source.custom_molecule_positions = solute_struct.custom_molecule_positions
        ion_source.custom_molecule_atom_names = solute_struct.custom_molecule_atom_names
        ion_source.custom_molecule_moleculetype = solute_struct.custom_molecule_moleculetype
        ion_source.custom_gro_path = solute_struct.gro_path
        ion_source.custom_itp_path = solute_struct.itp_path

    # Ion insertion
    ion_config = IonConfig(concentration_molar=0.15)
    ion_inserter = IonInserter(config=ion_config, seed=42)
    volume = _liquid_volume_nm3(ion_source)
    ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)
    ion_struct = ion_inserter.replace_water_with_ions(ion_source, ion_pairs)

    # Inspect ion_struct molecule_index cage-guest labels
    cage_labels = Counter(m.mol_type for m in ion_struct.molecule_index if m.mol_type in ("guest", "ch4", "thf", "co2", "h2") or m.mol_type not in ("water", "ice", "custom", "solute", "na", "cl"))
    print(f"  [ion_struct] cage-guest mol_types: {dict(cage_labels)}")

    tmp = OUT / "issue1"
    tmp.mkdir(exist_ok=True)
    gro_path, top_path, ok, err = _export_ion(ion_struct, config, tmp, "ions_full_chain.gro")
    if err and "h2" in err.lower():
        print(f"  >>> BUG CONFIRMED: 'h2' error raised (Issue 1): {err}")
        return False
    if not ok:
        print(f"  >>> export failed: {err}")
        return False
    rc, stderr = run_gmx_grompp(tmp, gro_file=gro_path.name, top_file=top_path.name)
    print(f"  gmx grompp rc={rc}")
    if rc != 0:
        print(f"  >>> grompp FAILED")
    return rc == 0


# ─── Issue 4: full chain CH4+custom_ethanol_cage + custom mol + solute + ion ──

def repro_issue4():
    print("\n=== ISSUE 4: full chain CH4+custom_ethanol_cage + custom mol + solute + ion ===")
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="etoh_mix",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
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
    print(f"  candidate.guest_atom_counts = {candidate.metadata.get('guest_atom_counts')}")
    iface = assemble_slab(candidate, InterfaceConfig(
        mode="slab", box_x=5.13629, box_y=5.13629, box_z=10.57382,
        seed=42, ice_thickness=5.13629, water_thickness=5.43753,
    ))
    print(f"  [slab] guest_descriptors count={len(iface.guest_descriptors)}, guest_atom_counts={iface.guest_atom_counts}")

    # Custom molecule (etoh)
    cm_config = CustomMoleculeConfig(
        placement_mode="random", gro_path=ETOH_GRO, itp_path=ETOH_ITP,
        molecule_count=3,
    )
    cm_inserter = CustomMoleculeInserter(cm_config)
    custom_struct = cm_inserter.place_random(iface, 3)
    iface_after_custom = custom_struct.interface_structure
    print(f"  [after custom] guest_descriptors count={len(getattr(iface_after_custom, 'guest_descriptors', []))}, guest_atom_counts={getattr(iface_after_custom, 'guest_atom_counts', '<MISSING>')}")

    # Solute (ch4)
    sol_config = SoluteConfig(concentration_molar=0.3, solute_type="CH4")
    sol_inserter = SoluteInserter(config=sol_config, seed=42)
    solute_struct = sol_inserter.insert_solutes(iface_after_custom, sol_config)
    iface_after_solute = solute_struct.interface_structure
    print(f"  [after solute] guest_descriptors count={len(getattr(iface_after_solute, 'guest_descriptors', []))}, guest_atom_counts={getattr(iface_after_solute, 'guest_atom_counts', '<MISSING>')}")

    # Ion source
    ion_source = iface_after_solute
    ion_source.solute_type = solute_struct.solute_type
    ion_source.solute_positions = solute_struct.positions
    ion_source.solute_atom_names = solute_struct.atom_names
    ion_source.solute_n_molecules = solute_struct.n_molecules
    ion_source.solute_molecule_indices = solute_struct.molecule_indices
    ion_source.solute_registry = solute_struct.registry
    if hasattr(solute_struct, 'custom_molecule_count') and solute_struct.custom_molecule_count > 0:
        ion_source.custom_molecule_count = solute_struct.custom_molecule_count
        ion_source.custom_molecule_atom_count = solute_struct.custom_molecule_atom_count
        ion_source.custom_molecule_positions = solute_struct.custom_molecule_positions
        ion_source.custom_molecule_atom_names = solute_struct.custom_molecule_atom_names
        ion_source.custom_molecule_moleculetype = solute_struct.custom_molecule_moleculetype
        ion_source.custom_gro_path = solute_struct.gro_path
        ion_source.custom_itp_path = solute_struct.itp_path

    # Ion insertion
    ion_config = IonConfig(concentration_molar=0.15)
    ion_inserter = IonInserter(config=ion_config, seed=42)
    volume = _liquid_volume_nm3(ion_source)
    ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)
    ion_struct = ion_inserter.replace_water_with_ions(ion_source, ion_pairs)

    cage_labels = Counter(m.mol_type for m in ion_struct.molecule_index if m.mol_type in ("guest", "ch4", "thf", "co2", "h2", "etoh_mix") or m.mol_type not in ("water", "ice", "custom", "solute", "na", "cl"))
    print(f"  [ion_struct] cage-guest mol_types: {dict(cage_labels)}")

    tmp = OUT / "issue4"
    tmp.mkdir(exist_ok=True)
    gro_path, top_path, ok, err = _export_ion(ion_struct, config, tmp, "ions_mol_chain.gro")
    if not ok:
        print(f"  >>> export failed: {err}")
        return False

    summary = _parse_gro_residue_summary(gro_path)
    mol_h = summary.get("MOL_H", {})
    ch4_h = summary.get("CH4_H", {})
    print(f"  .gro MOL_H: n_mols={mol_h.get('n_molecules')}, atom_dist={mol_h.get('atom_dist')}, multiset={mol_h.get('multiset')}")
    print(f"  .gro CH4_H: n_mols={ch4_h.get('n_molecules')}")
    top_mols = parse_top_molecules(top_path)
    print(f"  .top [molecules]: {top_mols}")
    rc, stderr = run_gmx_grompp(tmp, gro_file=gro_path.name, top_file=top_path.name)
    print(f"  gmx grompp rc={rc}")
    if rc != 0:
        molh_atoms = mol_h.get('total_atoms', 0)
        molh_n = mol_h.get('n_molecules', 0)
        if molh_n and mol_h.get('atom_dist') and 6 in mol_h['atom_dist']:
            print(f"  >>> BUG CONFIRMED: MOL_H has 6-atom fragmentation (Issue 4): {molh_n} mols × 6 = {molh_atoms}")
    return rc == 0


if __name__ == "__main__":
    results = {}
    try:
        results["issue3"] = repro_issue3()
    except Exception:
        print(f"  >>> EXCEPTION in issue3:\n{traceback.format_exc()}")
        results["issue3"] = False
    try:
        results["issue1"] = repro_issue1()
    except Exception:
        print(f"  >>> EXCEPTION in issue1:\n{traceback.format_exc()}")
        results["issue1"] = False
    try:
        results["issue4"] = repro_issue4()
    except Exception:
        print(f"  >>> EXCEPTION in issue4:\n{traceback.format_exc()}")
        results["issue4"] = False
    print(f"\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL (bug reproduced)'}")
