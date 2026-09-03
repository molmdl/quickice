"""End-to-end regression test for sH large-cage guest placement (Phase 42 plan 42-00).

Proves the sH ``cage_type_map`` bug fix: before the fix the sH large-cage id was
``"16"`` (an sII large-cage id that does not exist in the sH lattice), so
``parse_guest(guests, "16=ch4*1.0")`` silently placed ZERO large-cage guests.
After the fix the sH large-cage id is ``"20"`` (the real GenIce2 sH large-cage
id), so ``parse_guest(guests, "20=ch4*1.0")`` places guests in sH large cages.

These tests run GenIce2 in-memory (no GROMACS needed) and use module-scoped
fixtures to amortize the per-call cost. They are NOT marked ``@gmx_skipif``.

Empirical counts (GenIce2 ``sH`` 1x1x1 supercell):
    The GenIce2 ``sH`` lattice returns a cell containing TWO crystallographic
    sH unit cells (68 waters = 34 * 2), i.e. 6 small + 4 medium + 2 large cages.
    Only small + large are routed by ``HydrateStructureGenerator`` today (medium
    occupancy routing lands in later Phase 42 plans), so:
        * large-only (100%) -> 2 guests   (was 0 before the fix)
        * small-only (100%) -> 6 guests
        * small+large (100%) -> 8 guests  (== 6 + 2, proving independence)
    These values were verified empirically at execution time and replace the
    research-estimated 10/30/40 figures in the plan, which assumed a single
    crystallographic unit cell. See 42-00-SUMMARY.md "Deviations from Plan".
"""

import pytest

from quickice.structure_generation import HydrateConfig, HydrateStructureGenerator


@pytest.fixture(scope="module")
def sh_large_ch4():
    """sH 1x1x1 hydrate with CH4 at 100% large occupancy, 0% small.

    Module-scoped to amortize the GenIce2 call across all tests in this module.
    """
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",
        cage_occupancy_small=0.0,
        cage_occupancy_large=100.0,
    )
    return HydrateStructureGenerator().generate(config)


@pytest.fixture(scope="module")
def sh_small_ch4():
    """sH 1x1x1 hydrate with CH4 at 100% small occupancy, 0% large.

    Module-scoped to amortize the GenIce2 call. Independent from sh_large_ch4
    so the two occupancy axes can be compared without cross-contamination.
    """
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",
        cage_occupancy_small=100.0,
        cage_occupancy_large=0.0,
    )
    return HydrateStructureGenerator().generate(config)


def test_sh_large_places_guests(sh_large_ch4):
    """sH large-only occupancy places exactly 2 guests (was 0 before the fix).

    Before the cage_type_map fix, ``parse_guest`` was handed cage id ``"16"``,
    which does not exist in the sH lattice, so it silently placed 0 guests.
    After the fix it is handed ``"20"`` and places the 2 large cages present in
    the GenIce2 sH 1x1x1 cell (2 crystallographic unit cells -> 2 large cages).
    """
    assert sh_large_ch4.guest_count == 2


def test_sh_small_only_places_more(sh_small_ch4, sh_large_ch4):
    """sH small-only places exactly 6 guests, more than large-only's 2.

    The GenIce2 sH 1x1x1 cell holds 6 small cages (3 per unit cell * 2 cells)
    and 2 large cages (1 per unit cell * 2 cells). Small-only placing 6 while
    large-only places 2 proves small and large are independent cage types, not
    the same cage counted twice.
    """
    assert sh_small_ch4.guest_count == 6
    assert sh_small_ch4.guest_count > sh_large_ch4.guest_count


def test_sh_large_more_than_zero(sh_large_ch4):
    """Silent-zero bug sentinel: sH large occupancy must place >0 guests.

    This is the value-agnostic regression guard. Before the cage_type_map fix
    this assertion failed (guest_count was 0); it must remain >0 forever so
    any future regression that re-introduces a wrong cage id is caught even if
    the exact cage multiplicity changes across GenIce2 versions.
    """
    assert sh_large_ch4.guest_count > 0
