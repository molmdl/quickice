"""Regression tests for THF cage-guest bonds in the Custom Molecule / Solute / Ion
3D viewers (Issue 2 — thf-bonds-viewer-issue2).

Root cause: the slab interface mode (modes/slab.py) builds an InterfaceStructure
WITHOUT populating ``molecule_index`` (it defaults to an empty list). The
``interface_to_vtk_molecules`` viewer function therefore fell back to the
fragile ``_count_guest_atoms_for_rendering`` heuristic, whose "O"-first (THF)
branch stops only at the next "O"/"OW" — NOT at "C" (CH4). At THF->CH4 tile
boundaries the heuristic over-counts THF as 15 and destroys the following CH4,
losing cage-guest bonds. The Hydrate tab worked because ``hydrate_renderer``
uses the HydrateStructure's POPULATED ``molecule_index``.

Fix: ``interface_to_vtk_molecules`` now resolves per-molecule guest boundaries
via ``_build_guest_molecule_boundaries`` (molecule_index -> guest_descriptors
-> heuristic), so a slab InterfaceStructure with empty ``molecule_index`` but
populated ``guest_descriptors`` gets correct per-molecule bond detection.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest

from quickice.gui.vtk_utils import (
    _build_guest_molecule_boundaries,
    _count_guest_atoms_for_rendering,
    interface_to_vtk_molecules,
)
from quickice.structure_generation.types import GuestDescriptor, MoleculeIndex

# Atom-name sequences for the built-in guests (must match GUEST_MOLECULES).
CH4_LABELS = ["C", "H", "H", "H", "H"]            # 5 atoms
THF_LABELS = ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8   # 13 atoms


# ── Heuristic limitation (documents WHY the fallback is fragile) ─────────────

def test_heuristic_miscounts_thf_followed_by_ch4():
    """The "O"-first heuristic stops at the next "O"/"OW" but NOT at "C" (CH4).

    This is the root cause of the viewer bug: at a THF->CH4 transition the
    heuristic over-counts THF as 15 (13 THF + 2 CH4 atoms) and then destroys
    the following CH4. This test pins the (broken) heuristic behavior so the
    regression is visible if someone touches the heuristic.
    """
    # [THF][CH4] — the failing transition
    seq = THF_LABELS + CH4_LABELS
    n = _count_guest_atoms_for_rendering(seq, 0)
    # Heuristic over-counts: 13 THF + 2 CH4 atoms = 15 (does not stop at "C")
    assert n == 15, (
        "Heuristic should over-count THF as 15 when followed by CH4 (the bug). "
        f"Got {n}. If this changed, verify _build_guest_molecule_boundaries "
        "still resolves mixed-guest boundaries correctly."
    )

    # [CH4][THF] — CH4 uses a fixed count of 5, which is correct
    n2 = _count_guest_atoms_for_rendering(CH4_LABELS + THF_LABELS, 0)
    assert n2 == 5

    # Pure [THF][THF] — works because each THF is followed by another "O"
    n3 = _count_guest_atoms_for_rendering(THF_LABELS + THF_LABELS, 0)
    assert n3 == 13


# ── Unit test for the fix: _build_guest_molecule_boundaries ──────────────────

def _mock_mixed_iface(molecule_index=None, with_descriptors=True):
    """Build a synthetic InterfaceStructure-like mock with mixed CH4+THF guests.

    Layout: [ice O,H,H][water OW,HW1,HW2,MW][THF, CH4, THF, CH4]
    The guest region has THF->CH4 transitions (the case the heuristic breaks on).
    """
    ice_names = ["O", "H", "H"]
    water_names = ["OW", "HW1", "HW2", "MW"]
    guest_names = THF_LABELS + CH4_LABELS + THF_LABELS + CH4_LABELS  # 13+5+13+5 = 36
    ice_atom_count = len(ice_names)
    water_atom_count = len(water_names)
    guest_atom_count = len(guest_names)
    atom_names = ice_names + water_names + guest_names
    guest_start = ice_atom_count + water_atom_count
    guest_end = guest_start + guest_atom_count
    guest_nmolecules = 4  # 2 THF + 2 CH4

    descriptors = []
    if with_descriptors:
        descriptors = [
            GuestDescriptor(
                mol_type="ch4", cage_key="small", guest_name="Methane",
                guest_residue_name="", is_custom=False,
                atom_labels=list(CH4_LABELS), atom_count=5,
            ),
            GuestDescriptor(
                mol_type="thf", cage_key="large", guest_name="Tetrahydrofuran",
                guest_residue_name="", is_custom=False,
                atom_labels=list(THF_LABELS), atom_count=13,
            ),
        ]

    return SimpleNamespace(
        atom_names=atom_names,
        molecule_index=molecule_index if molecule_index is not None else [],
        guest_descriptors=descriptors,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        guest_atom_count=guest_atom_count,
        guest_nmolecules=guest_nmolecules,
    ), guest_start, guest_end, guest_nmolecules


def test_build_guest_boundaries_uses_descriptors_when_molecule_index_empty():
    """Empty molecule_index + populated guest_descriptors -> descriptor-based
    boundaries (the fix). Mixed [THF, CH4, THF, CH4] resolves to
    [(0,13),(13,18),(18,31),(31,36)] — the heuristic would have broken here."""
    iface, gstart, gend, nmol = _mock_mixed_iface(molecule_index=[], with_descriptors=True)
    bounds = _build_guest_molecule_boundaries(iface, gstart, gend, nmol)
    assert bounds == [(0, 13), (13, 18), (18, 31), (31, 36)], (
        f"Descriptor-based boundaries wrong: {bounds}"
    )


def test_build_guest_boundaries_prefers_molecule_index_when_populated():
    """When molecule_index IS populated, it takes precedence (authoritative)."""
    gstart = 3 + 4  # ice(3) + water(4)
    mi = [
        MoleculeIndex(gstart + 0, 13, "thf"),
        MoleculeIndex(gstart + 13, 5, "ch4"),
        MoleculeIndex(gstart + 18, 13, "thf"),
        MoleculeIndex(gstart + 31, 5, "ch4"),
    ]
    iface, gstart, gend, nmol = _mock_mixed_iface(molecule_index=mi, with_descriptors=True)
    bounds = _build_guest_molecule_boundaries(iface, gstart, gend, nmol)
    assert bounds == [(0, 13), (13, 18), (18, 31), (31, 36)]


def test_build_guest_boundaries_falls_back_to_heuristic_without_descriptors():
    """No molecule_index AND no guest_descriptors -> heuristic fallback
    (backward compatibility for structures built without metadata)."""
    iface, gstart, gend, nmol = _mock_mixed_iface(
        molecule_index=[], with_descriptors=False
    )
    # Replace descriptors with empty list
    iface.guest_descriptors = []
    bounds = _build_guest_molecule_boundaries(iface, gstart, gend, nmol)
    # Heuristic miscounts the THF->CH4 transition, so the result is NOT the
    # clean [(0,13),(13,18),(18,31),(31,36)]. Just assert it produced SOME
    # boundaries (the heuristic degrades rather than crashing).
    assert len(bounds) >= 1
    assert bounds[0] == (0, 13) or bounds[0] == (0, 15)  # first THF or over-count


# ── Integration test: real SII mixed CH4+THF slab -> viewer bonds ────────────

@pytest.fixture(scope="module")
def sii_mixed_slab():
    """Build a real SII mixed (small CH4, large THF) slab interface once.

    Mimics the GUI flow: generate hydrate candidate -> assemble slab interface.
    The slab InterfaceStructure has EMPTY molecule_index but POPULATED
    guest_descriptors (the exact condition that triggered the viewer bug).
    """
    from tests.e2e_export_helpers import _make_slab_interface
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
    candidate = gen.generate(config).to_candidate()
    return _make_slab_interface(candidate)


def test_sii_mixed_slab_has_empty_molecule_index_but_descriptors(sii_mixed_slab):
    """Pin the precondition: slab leaves molecule_index empty but populates
    guest_descriptors (the gap the fix bridges)."""
    iface = sii_mixed_slab
    assert iface.molecule_index == [], (
        "slab.py should leave molecule_index empty (it does not populate it); "
        "if this changed, the viewer may now use the molecule_index path "
        "directly — update this test accordingly."
    )
    assert len(iface.guest_descriptors) >= 2, (
        "slab.py should populate guest_descriptors (ch4 + thf) for a mixed slab"
    )
    mol_types = {d.mol_type for d in iface.guest_descriptors}
    assert {"ch4", "thf"} <= mol_types


def test_sii_mixed_slab_guest_mol_has_correct_bonds(sii_mixed_slab):
    """The viewer (interface_to_vtk_molecules) must produce cage-guest bonds
    for BOTH CH4 and THF in a mixed slab. Before the fix the heuristic produced
    only 2291 bonds (vs the correct 2688 = 256*4 + 128*13); after the fix the
    descriptor-based boundaries yield the full count."""
    iface = sii_mixed_slab
    ice_mol, water_mol, guest_mol = interface_to_vtk_molecules(iface)

    assert guest_mol is not None, "guest_mol should exist (guest_atom_count > 0)"
    assert guest_mol.GetNumberOfAtoms() == iface.guest_atom_count

    n_bonds = guest_mol.GetNumberOfBonds()
    # Correct count: 256 CH4 * 4 (C-H) + 128 THF * 13 (5 ring + 8 C-H) = 2688.
    # The broken heuristic produced 2291. Assert well above the broken value
    # AND equal to the expected count (deterministic for this structure).
    assert n_bonds > 2500, (
        f"Too few guest bonds: {n_bonds}. The broken heuristic produced 2291; "
        "the fix should produce the full per-molecule bond count."
    )
    assert n_bonds == 2688, (
        f"Expected exactly 2688 guest bonds (256 CH4*4 + 128 THF*13), got {n_bonds}."
    )
