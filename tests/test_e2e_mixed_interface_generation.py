"""Regression test: interface generation from MIXED-component hydrate.

Phase 45-14 root-cause fix. Before the fix, generating an interface from a
mixed built-in hydrate (CH4 in small cages + THF in large cages) crashed
with ``IndexError: index 728 is out of bounds for axis 0 with size 728``
in ALL three interface modes (slab, pocket, piece).

Root cause: all three modes extracted only ONE guest type via
``next(iter(guest_type_counts))`` (e.g. "ch4") and passed it to
``count_guest_atoms(guest_type="ch4")``, which short-circuits and returns
5 for EVERY guest molecule — including THF which has 13 atoms. The 5-vs-13
miscount desynced the walking index in ``_detect_guest_atoms``; compounding
the bug, the guest branch used the UNCLAMPED ``range(i, i + guest_atoms)``
instead of the clamped ``end_idx``, producing an out-of-bounds index 728 on
a 728-element array (136 water * 4 + 16 ch4 * 5 + 8 thf * 13 = 728).

A secondary issue: ``tile_structure`` validates
``len(positions) % atoms_per_molecule == 0`` and does molecule-level PBC
wrapping — both assume a SINGLE uniform atoms-per-molecule. CH4 (5) + THF
(13) = 184 guest atoms is divisible by neither 5 nor 13, so a single
``tile_structure`` call would raise ValueError. The fix tiles each guest
type SEPARATELY with its own atoms_per_molecule.

The single-guest path (e.g. sI all-CH4) was unaffected because
``count_guest_atoms(guest_type="ch4")`` = 5 is CORRECT for every molecule,
so no desync occurred. This asymmetry (mixed fails, single works) is the
defining property of the bug.

This test builds a real mixed sII hydrate (CH4 small + THF large, 1x1x1)
via ``HydrateStructureGenerator``, converts to candidate, and generates
interfaces in all three modes — verifying:
    * No IndexError (the crash is gone).
    * Both CH4 and THF guests are preserved in the output.
    * The CH4:THF molecule ratio matches the sII cage ratio (16:8 = 2:1).
    * positions and atom_names lengths are consistent.

Module-scoped fixture amortizes the GenIce2 call (~0.1s at 1x1x1).
"""

import numpy as np
import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import (
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.structure_generation.water_filler import get_cell_extent


@pytest.fixture(scope="module")
def mixed_sii_candidate():
    """Build a mixed sII hydrate (CH4 small + THF large) and convert to candidate.

    sII unit cell: 16 small (5^12) + 8 large (5^12 6^4) cages, 136 water
    molecules. At 100% occupancy: 16 CH4 (5 atoms each = 80) + 8 THF (13
    atoms each = 104) + 136 water (4 atoms each = 544) = 728 total atoms.

    Module-scoped to amortize the GenIce2 call across all three mode tests.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",  # primary (legacy)
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
        },
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    # Sanity: the mixed hydrate must carry BOTH guest types.
    assert candidate.metadata["guest_type_counts"] == {"ch4": 16, "thf": 8}, (
        "mixed sII should have 16 ch4 + 8 thf guests, got "
        f"{candidate.metadata['guest_type_counts']}"
    )
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5, "thf": 13}, (
        "mixed sII guest_atom_counts should be ch4=5, thf=13, got "
        f"{candidate.metadata['guest_atom_counts']}"
    )
    # 136 water * 4 + 16 ch4 * 5 + 8 thf * 13 = 544 + 80 + 104 = 728
    assert candidate.positions.shape == (728, 3), (
        f"mixed sII 1x1x1 should have 728 atoms, got {candidate.positions.shape}"
    )
    return candidate


def _count_guest_molecules_by_type(atom_names, start, length):
    """Count CH4 and THF guest molecules in a guest atom-name segment.

    Returns (n_ch4, n_thf). CH4 = 5 atoms (C, H, H, H, H); THF = 13 atoms
    (O, CA, CA, CB, CB, H*8). Walks the segment molecule-by-molecule.
    """
    n_ch4 = 0
    n_thf = 0
    i = start
    end = start + length
    while i < end:
        if i + 5 <= end and atom_names[i] == "C" and atom_names[i + 1] == "H":
            n_ch4 += 1
            i += 5
        elif i + 13 <= end and atom_names[i] == "O":
            n_thf += 1
            i += 13
        else:
            i += 1
    return n_ch4, n_thf


def _interface_configs(candidate):
    """Build one InterfaceConfig per mode, sized to the candidate cell."""
    cell_ext = get_cell_extent(candidate.cell)
    box_x = max(cell_ext[0] * 2, 4.0)
    box_y = max(cell_ext[1] * 2, 4.0)
    ice_thickness = max(cell_ext[2], 2.0)
    water_thickness = 3.0
    box_z_slab = 2 * ice_thickness + water_thickness
    return {
        "slab": InterfaceConfig(
            mode="slab", box_x=box_x, box_y=box_y, box_z=box_z_slab,
            seed=42, ice_thickness=ice_thickness, water_thickness=water_thickness,
        ),
        "pocket": InterfaceConfig(
            mode="pocket", box_x=box_x, box_y=box_y, box_z=box_z_slab,
            seed=42, pocket_diameter=1.5, pocket_shape="sphere",
        ),
        "piece": InterfaceConfig(
            mode="piece",
            box_x=box_x + cell_ext[0],
            box_y=box_y + cell_ext[1],
            box_z=box_z_slab + cell_ext[2],
            seed=42,
        ),
    }


@pytest.mark.parametrize("mode", ["slab", "pocket", "piece"])
def test_mixed_hydrate_interface_no_indexerror(mode, mixed_sii_candidate):
    """Mixed sII (CH4+THF) interface generation must not raise IndexError.

    This is the direct regression test for the reported bug: all three modes
    failed with ``index 728 is out of bounds for axis 0 with size 728``.
    """
    candidate = mixed_sii_candidate
    configs = _interface_configs(candidate)
    # Must not raise.
    result = generate_interface(candidate, configs[mode])
    assert result is not None
    assert len(result.positions) > 0
    # positions and atom_names must have the same length (no corruption).
    assert result.positions.shape[0] == len(result.atom_names), (
        f"{mode}: positions ({result.positions.shape[0]}) != atom_names "
        f"({len(result.atom_names)}) — data corruption"
    )


@pytest.mark.parametrize("mode", ["slab", "pocket", "piece"])
def test_mixed_hydrate_interface_preserves_both_guest_types(mode, mixed_sii_candidate):
    """Both CH4 and THF guest molecules must be preserved in the interface.

    The CH4:THF molecule ratio must match the sII cage ratio (16:8 = 2:1)
    for slab/piece (no cavity removal). Pocket removes guests inside the
    cavity, so the ratio is checked to be >= 1 ch4 and >= 1 thf (both types
    survive, even if some are removed).
    """
    candidate = mixed_sii_candidate
    configs = _interface_configs(candidate)
    result = generate_interface(candidate, configs[mode])

    assert result.guest_atom_count > 0, f"{mode}: no guest atoms in result"
    guest_start = result.ice_atom_count + result.water_atom_count
    n_ch4, n_thf = _count_guest_molecules_by_type(
        result.atom_names, guest_start, result.guest_atom_count
    )
    expected_guest_atoms = n_ch4 * 5 + n_thf * 13
    assert expected_guest_atoms == result.guest_atom_count, (
        f"{mode}: guest_atom_count={result.guest_atom_count} but counted "
        f"{n_ch4} ch4 ({n_ch4 * 5} atoms) + {n_thf} thf ({n_thf * 13} atoms) "
        f"= {expected_guest_atoms} — molecule fragmentation"
    )
    # Both guest types must be present.
    assert n_ch4 > 0, f"{mode}: no CH4 guests preserved (got {n_ch4})"
    assert n_thf > 0, f"{mode}: no THF guests preserved (got {n_thf})"

    if mode in ("slab", "piece"):
        # slab and piece tile guests uniformly (no cavity removal), so the
        # CH4:THF ratio must match the sII unit cell ratio (16:8 = 2:1).
        assert n_ch4 == 2 * n_thf, (
            f"{mode}: CH4:THF ratio {n_ch4}:{n_thf} != 2:1 (sII cage ratio). "
            f"Expected 2 ch4 per 1 thf (16 small : 8 large cages)."
        )


def test_single_guest_hydrate_interface_still_works():
    """Regression guard: single-guest sI all-CH4 hydrate must still work.

    The fix adds a mixed-guest code path (is_mixed = len(guest_atom_counts) > 1).
    Single-guest hydrates have len(guest_atom_counts) == 1, so is_mixed is
    False and the existing single-guest_type path is used unchanged. This test
    verifies no regression on the single-guest path.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        cage_occupancy_small=100.0,
        cage_occupancy_large=100.0,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    # Single-guest hydrate: only ch4.
    assert candidate.metadata["guest_type_counts"] == {"ch4": 8}, (
        f"sI all-CH4 should have 8 ch4 guests, got "
        f"{candidate.metadata['guest_type_counts']}"
    )
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5}

    cell_ext = get_cell_extent(candidate.cell)
    box_x = max(cell_ext[0] * 2, 4.0)
    box_y = max(cell_ext[1] * 2, 4.0)
    ice_thickness = max(cell_ext[2], 2.0)
    water_thickness = 3.0
    box_z = 2 * ice_thickness + water_thickness
    result = generate_interface(candidate, InterfaceConfig(
        mode="slab", box_x=box_x, box_y=box_y, box_z=box_z,
        seed=42, ice_thickness=ice_thickness, water_thickness=water_thickness,
    ))
    assert result.guest_atom_count > 0, "single-CH4 slab should have guest atoms"
    assert result.positions.shape[0] == len(result.atom_names)
    # All guests should be CH4 (no THF).
    guest_start = result.ice_atom_count + result.water_atom_count
    n_ch4, n_thf = _count_guest_molecules_by_type(
        result.atom_names, guest_start, result.guest_atom_count
    )
    assert n_thf == 0, f"single-CH4 hydrate should have 0 THF, got {n_thf}"
    assert n_ch4 > 0, f"single-CH4 hydrate should have CH4 guests, got {n_ch4}"
