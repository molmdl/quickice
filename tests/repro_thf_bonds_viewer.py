"""Repro for THF bonds viewer issue 2.

Tests:
1. The _count_guest_atoms_for_rendering heuristic with MIXED CH4+THF orderings
   (the failing case: THF followed by CH4 — "O" heuristic doesn't stop at "C").
2. A REAL SII mixed CH4+THF slab interface to confirm molecule_index is EMPTY
   (slab.py doesn't populate it) -> forces the broken heuristic fallback.
3. interface_to_vtk_molecules bond count on the real slab -> confirm 0 or wrong.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from quickice.gui.vtk_utils import (
    interface_to_vtk_molecules,
    _count_guest_atoms_for_rendering,
)

THF = ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8   # 13 atoms
CH4 = ["C", "H", "H", "H", "H"]                    # 5 atoms


def test_heuristic_mixed():
    print("=" * 70)
    print("TEST 1: heuristic _count_guest_atoms_for_rendering (mixed CH4+THF)")
    print("=" * 70)

    # Case A: THF followed by CH4 (the suspected failing case)
    seq_a = THF + CH4 + THF + CH4
    print(f"\nCase A: [THF][CH4][THF][CH4]  (len={len(seq_a)})")
    pos = 0
    mols = []
    while pos < len(seq_a):
        n = _count_guest_atoms_for_rendering(seq_a, pos)
        mols.append((pos, n, seq_a[pos:pos + n]))
        pos += n
    print(f"  Heuristic split: {[(s, n) for s, n, _ in mols]}")
    for s, n, atoms in mols:
        is_thf = atoms[:1] == ["O"]
        ok = (is_thf and n == 13) or (not is_thf and n == 5)
        print(f"    idx={s} count={n} {'THF' if is_thf else 'CH4'} atoms={atoms[:3]}... "
              f"{'OK' if ok else '*** WRONG ***'}")
    counts = [n for _, n, _ in mols]
    if counts == [13, 5, 13, 5]:
        print("  -> Case A: heuristic CORRECT (THF=13, CH4=5)")
    else:
        print(f"  -> Case A: heuristic BROKEN! got {counts}, expected [13,5,13,5]")

    # Case B: CH4 followed by THF
    seq_b = CH4 + THF + CH4 + THF
    print(f"\nCase B: [CH4][THF][CH4][THF]  (len={len(seq_b)})")
    pos = 0
    mols = []
    while pos < len(seq_b):
        n = _count_guest_atoms_for_rendering(seq_b, pos)
        mols.append((pos, n, seq_b[pos:pos + n]))
        pos += n
    print(f"  Heuristic split: {[(s, n) for s, n, _ in mols]}")
    for s, n, atoms in mols:
        is_thf = atoms[:1] == ["O"]
        ok = (is_thf and n == 13) or (not is_thf and n == 5)
        print(f"    idx={s} count={n} {'THF' if is_thf else 'CH4'} atoms={atoms[:3]}... "
              f"{'OK' if ok else '*** WRONG ***'}")
    counts = [n for _, n, _ in mols]
    if counts == [5, 13, 5, 13]:
        print("  -> Case B: heuristic CORRECT (CH4=5, THF=13)")
    else:
        print(f"  -> Case B: heuristic BROKEN! got {counts}, expected [5,13,5,13]")

    # Case C: pure THF (the prior test case - should work)
    seq_c = THF + THF
    print(f"\nCase C: [THF][THF]  (len={len(seq_c)}, prior-test case)")
    pos = 0
    mols = []
    while pos < len(seq_c):
        n = _count_guest_atoms_for_rendering(seq_c, pos)
        mols.append((pos, n, seq_c[pos:pos + n]))
        pos += n
    counts = [n for _, n, _ in mols]
    print(f"  Heuristic split: {[(s, n) for s, n, _ in mols]}")
    if counts == [13, 13]:
        print("  -> Case C: heuristic CORRECT (pure THF works, as in prior test)")
    else:
        print(f"  -> Case C: heuristic BROKEN! got {counts}, expected [13,13]")


def test_real_sii_mixed_slab():
    print("\n" + "=" * 70)
    print("TEST 2: REAL SII mixed CH4+THF slab -> molecule_index + bonds")
    print("=" * 70)
    from e2e_export_helpers import _make_slab_interface
    print("  (building SII mixed candidate inline)")
    from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
    from quickice.structure_generation.types import HydrateConfig, CageGuestAssignment
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",
        supercell_x=1, supercell_y=1, supercell_z=1,
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
        },
    )
    structure = gen.generate(config)
    candidate = structure.to_candidate()

    iface = _make_slab_interface(candidate)

    print(f"\n  InterfaceStructure:")
    print(f"    ice_atom_count   = {iface.ice_atom_count}")
    print(f"    water_atom_count = {iface.water_atom_count}")
    print(f"    guest_atom_count = {iface.guest_atom_count}")
    print(f"    guest_nmolecules = {iface.guest_nmolecules}")
    print(f"    molecule_index   = {iface.molecule_index}  (len={len(iface.molecule_index)})")
    print(f"    guest_atom_counts= {getattr(iface, 'guest_atom_counts', 'N/A')}")
    print(f"    guest_descriptors= {getattr(iface, 'guest_descriptors', 'N/A')[:3] if getattr(iface,'guest_descriptors',[]) else 'N/A'}")

    guest_start = iface.ice_atom_count + iface.water_atom_count
    guest_end = guest_start + iface.guest_atom_count
    guest_names = iface.atom_names[guest_start:guest_end]
    print(f"\n  Guest region [start={guest_start}, end={guest_end}]: {len(guest_names)} atoms")
    print(f"  First 40 guest atom names: {guest_names[:40]}")
    # count distinct first-atoms of each molecule-sized chunk
    print(f"  Distinct guest atom names: {sorted(set(guest_names))}")

    # Which branch does interface_to_vtk_molecules take?
    # (After the fix, it uses guest_descriptors when molecule_index is empty.)
    if iface.molecule_index:
        print(f"\n  BRANCH: molecule_index path (len={len(iface.molecule_index)})")
    elif getattr(iface, 'guest_descriptors', None):
        print(f"\n  BRANCH: guest_descriptors path (molecule_index empty, "
              f"{len(iface.guest_descriptors)} descriptors) -- the FIX")
    else:
        print(f"\n  BRANCH: FALLBACK heuristic path (no molecule_index, no descriptors)")

    # Now call interface_to_vtk_molecules and inspect bonds
    ice_mol, water_mol, guest_mol = interface_to_vtk_molecules(iface)
    print(f"\n  interface_to_vtk_molecules result:")
    print(f"    guest_mol is None? {guest_mol is None}")
    if guest_mol is not None:
        n_atoms = guest_mol.GetNumberOfAtoms()
        n_bonds = guest_mol.GetNumberOfBonds()
        print(f"    guest_mol atoms = {n_atoms} (expected {iface.guest_atom_count})")
        print(f"    guest_mol bonds = {n_bonds}")
        # For SII mixed (small 100% CH4, large 100% THF) 1x1x1 slab:
        #   256 CH4 * 4 (C-H) + 128 THF * 13 (5 ring + 8 C-H) = 2688 bonds.
        # The broken heuristic produced 2291; the fix produces 2688.
        # We don't hard-code 2688 here (counts may vary with slab thickness);
        # the dedicated regression test (test_thf_bonds_viewer_issue2.py) pins
        # the exact count for this specific structure.
        if n_bonds == 0:
            print(f"    *** NO BONDS CREATED -- bug reproduced ***")
        elif n_bonds < iface.guest_nmolecules * 6:
            print(f"    *** LOW BOND COUNT -- partial reproduction (heuristic miscount) ***")
        else:
            print(f"    bonds look plausible (~{n_bonds}) -- FIX VERIFIED")


if __name__ == "__main__":
    test_heuristic_mixed()
    test_real_sii_mixed_slab()
