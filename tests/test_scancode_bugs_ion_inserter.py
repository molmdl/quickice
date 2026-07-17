"""Regression tests for scancode-verified bugs in the ion inserter module.

These tests prevent silent reversion of bug fixes verified by static analysis
(see .planning/scancode-fixes/RESEARCH.md and PLAN.md, Group 2).

CRIT-02 (HIGH): Ion Na/Cl alternation must use a placement counter, not the
``enumerate`` loop index. A water candidate rejected for overlap (the two
``continue`` guards in ``replace_water_with_ions``) still advances the
``enumerate`` index ``i``, so keying parity off ``i`` (``if i % 2 == 0``)
flips Na/Cl parity for every subsequently PLACED ion, producing same-charge
clustering. The fix uses a ``placed_count`` counter incremented ONLY on
successful placement (``if placed_count % 2 == 0``).

SUSP-01 (MEDIUM): The 3-atom GenIce fallback miscount. See
``TestSUSP01ThreeAtomGenIceFallback`` (added with the SUSP-01 fix).
"""

import numpy as np
import pytest
from types import SimpleNamespace

from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.types import MoleculeIndex


# ── CRIT-02: alternation parity uses placement counter, not enumerate index ──


class TestCRIT02AlternationParity:
    """Na/Cl must strictly alternate by PLACEMENT order.

    A candidate rejected for overlap must NOT flip the Na/Cl parity of any
    subsequently placed ion. Before the fix, parity keyed off the
    ``enumerate`` index ``i`` (``if i % 2 == 0``); a rejected candidate still
    advanced ``i``, flipping parity for all later placed ions.
    """

    @staticmethod
    def _build_structure_with_overlap_rejections():
        """Build a deterministic structure where 2 of 6 selected waters are
        rejected for overlap with ice atoms.

        Layout (1-atom molecules for simplicity; the inserter only needs the
        first atom -- the oxygen -- for placement and overlap checks):

            molecule_index / positions:
              ice0  at [1.0, 0, 0]   (mol_type="ice")   -- rejects W1
              ice1  at [2.0, 0, 0]   (mol_type="ice")   -- rejects W3
              W0    at [5.0, 0, 0]   (mol_type="water") -- valid
              W1    at [1.1, 0, 0]   (mol_type="water") -- REJECTED (0.1 < 0.3 nm from ice0)
              W2    at [6.0, 0, 0]   (mol_type="water") -- valid
              W3    at [2.1, 0, 0]   (mol_type="water") -- REJECTED (0.1 < 0.3 nm from ice1)
              W4    at [7.0, 0, 0]   (mol_type="water") -- valid
              W5    at [8.0, 0, 0]   (mol_type="water") -- valid

        With ``ion_pairs=3`` -> 6 waters selected. With the RNG shuffle
        neutralised (identity), ``selected = [0, 1, 2, 3, 4, 5]`` maps to
        ``[W0, W1, W2, W3, W4, W5]``. W1 (enumerate i=1) and W3 (i=3) are
        rejected for overlap; W0, W2, W4, W5 are placed.

        EXPECTED with the fix (placement-order parity):
            W0 -> Na (placed_count=0), W1 REJECTED, W2 -> Cl (placed_count=1),
            W3 REJECTED, W4 -> Na (placed_count=2), W5 -> Cl (placed_count=3)
            => 2 Na + 2 Cl, no charge-neutrality trim, ions = [Na, Cl, Na, Cl].

        BEFORE the fix (enumerate-index parity, ``if i % 2 == 0``):
            i=0 W0 -> Na, i=1 W1 REJECTED, i=2 W2 -> Na (BUG: should be Cl),
            i=3 W3 REJECTED, i=4 W4 -> Na (BUG), i=5 W5 -> Cl
            => 3 Na + 1 Cl -> charge-neutrality trim removes 2 Na
            => 1 Na + 1 Cl, ions = [Na, Cl] (only 2 ions, and the wrong ones).

        The assertions below distinguish the two: the fix yields 4 alternating
        ions at [5,6,7,8]; the bug yields only 2 ions at [5,8].
        """
        positions = np.array([
            [1.0, 0.0, 0.0],   # ice0
            [2.0, 0.0, 0.0],   # ice1
            [5.0, 0.0, 0.0],   # W0  (valid)
            [1.1, 0.0, 0.0],   # W1  (rejected: 0.1 nm from ice0)
            [6.0, 0.0, 0.0],   # W2  (valid)
            [2.1, 0.0, 0.0],   # W3  (rejected: 0.1 nm from ice1)
            [7.0, 0.0, 0.0],   # W4  (valid)
            [8.0, 0.0, 0.0],   # W5  (valid)
        ])
        atom_names = ["O"] * 8  # No MW -> all ice atoms included in overlap check
        cell = np.diag([10.0, 10.0, 10.0])
        molecule_index = [
            MoleculeIndex(start_idx=0, count=1, mol_type="ice"),    # ice0
            MoleculeIndex(start_idx=1, count=1, mol_type="ice"),    # ice1
            MoleculeIndex(start_idx=2, count=1, mol_type="water"),  # W0
            MoleculeIndex(start_idx=3, count=1, mol_type="water"),  # W1
            MoleculeIndex(start_idx=4, count=1, mol_type="water"),  # W2
            MoleculeIndex(start_idx=5, count=1, mol_type="water"),  # W3
            MoleculeIndex(start_idx=6, count=1, mol_type="water"),  # W4
            MoleculeIndex(start_idx=7, count=1, mol_type="water"),  # W5
        ]
        # SimpleNamespace is sufficient: replace_water_with_ions reads
        # positions/atom_names/cell/molecule_index directly and uses
        # getattr(..., default) for the optional solute_*/custom_*/guest_* attrs.
        return SimpleNamespace(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            molecule_index=molecule_index,
        )

    def test_rejected_candidate_does_not_flip_parity(self):
        """A water rejected for overlap must not change which ion the next
        PLACED ion gets. Placed ions must strictly alternate Na, Cl, Na, Cl.

        Before the CRIT-02 fix this fails: the bug yields 1 Na + 1 Cl (only
        2 ions, after the charge-neutrality trim removes the excess Na
        produced by the flipped parity), instead of 2 Na + 2 Cl (4 ions).
        """
        structure = self._build_structure_with_overlap_rejections()
        inserter = IonInserter(seed=42)
        # Neutralise the RNG shuffle so `selected` stays in natural order
        # [0, 1, 2, 3, 4, 5] -> [W0, W1, W2, W3, W4, W5]. This makes the test
        # fully deterministic and pins the rejected candidates at enumerate
        # indices 1 and 3 (the exact positions that expose the parity bug).
        inserter.rng.shuffle = lambda seq: None  # identity: leave order unchanged

        # ion_pairs=3 -> 6 waters selected (all of them here).
        result = inserter.replace_water_with_ions(structure, ion_pairs=3)

        # The 2 overlap rejections (W1, W3) must NOT reduce the count via trim:
        # with placement-order parity, 4 of 6 are placed as 2 Na + 2 Cl
        # (balanced -> no charge-neutrality trim).
        assert result.na_count == 2, (
            f"Expected 2 Na (W0, W4 placed); got {result.na_count}. "
            f"Before the fix, enumerate-index parity produced 3 Na + 1 Cl "
            f"and the trim removed 2 Na -> 1 Na."
        )
        assert result.cl_count == 2, (
            f"Expected 2 Cl (W2, W5 placed); got {result.cl_count}. "
            f"Before the fix, enumerate-index parity produced 1 Cl after trim."
        )

        # Ion molecule types (in placement/molecule_index order) must strictly
        # alternate Na, Cl, Na, Cl. Before the fix this is ["na", "cl"] (only
        # 2 ions remain after trimming the excess Na produced by flipped parity).
        ion_mols = [m for m in result.molecule_index if m.mol_type in ("na", "cl")]
        ion_types = [m.mol_type for m in ion_mols]
        assert ion_types == ["na", "cl", "na", "cl"], (
            f"Placed ions must strictly alternate Na, Cl, Na, Cl by placement "
            f"order; got {ion_types}. A rejected candidate flipped the parity "
            f"(CRIT-02): the enumerate index `i` was used instead of a placement "
            f"counter."
        )

        # The rejected waters (W1 at [1.1,0,0], W3 at [2.1,0,0]) must NOT appear
        # as ions, and the valid waters must be placed in order at [5,6,7,8].
        # The first 2 entries of result.positions are the kept ice atoms
        # (ice0 [1,0,0], ice1 [2,0,0]); the remaining are the placed ions.
        ion_positions = result.positions[2:]
        expected_ion_positions = np.array([
            [5.0, 0.0, 0.0],  # W0 -> Na
            [6.0, 0.0, 0.0],  # W2 -> Cl
            [7.0, 0.0, 0.0],  # W4 -> Na
            [8.0, 0.0, 0.0],  # W5 -> Cl
        ])
        assert np.allclose(ion_positions, expected_ion_positions), (
            f"Expected ions at {expected_ion_positions.tolist()} (the valid "
            f"waters W0,W2,W4,W5 in placement order); got "
            f"{ion_positions.tolist()}. Before the fix, the bug kept only "
            f"W0 and W5 (Na at [5,0,0], Cl at [8,0,0]) after trimming the "
            f"excess Na produced by the flipped parity."
        )

        # Sanity: the rejected waters' positions must NOT be present as ions.
        all_positions = result.positions
        for rejected in ([1.1, 0.0, 0.0], [2.1, 0.0, 0.0]):
            assert not np.any(np.all(np.isclose(all_positions, rejected), axis=1)), (
                f"Rejected water at {rejected} must not appear as a placed ion."
            )

    def test_alternation_holds_with_zero_rejections(self):
        """With NO overlap rejections, the placement counter and the enumerate
        index agree, so the result is identical to the legacy behavior. This
        guards the common path (no rejections) is unchanged by the fix.
        """
        # 4 waters, all far from any ice and from each other -> no rejections.
        positions = np.array([
            [5.0, 0.0, 0.0],   # ice0 (far away, won't reject anything)
            [1.0, 0.0, 0.0],   # W0
            [2.0, 0.0, 0.0],   # W1
            [3.0, 0.0, 0.0],   # W2
            [4.0, 0.0, 0.0],   # W3
        ])
        molecule_index = [
            MoleculeIndex(start_idx=0, count=1, mol_type="ice"),
            MoleculeIndex(start_idx=1, count=1, mol_type="water"),
            MoleculeIndex(start_idx=2, count=1, mol_type="water"),
            MoleculeIndex(start_idx=3, count=1, mol_type="water"),
            MoleculeIndex(start_idx=4, count=1, mol_type="water"),
        ]
        structure = SimpleNamespace(
            positions=positions,
            atom_names=["O"] * 5,
            cell=np.diag([10.0, 10.0, 10.0]),
            molecule_index=molecule_index,
        )
        inserter = IonInserter(seed=7)
        inserter.rng.shuffle = lambda seq: None  # deterministic order

        result = inserter.replace_water_with_ions(structure, ion_pairs=2)

        # 4 waters, no rejections -> 2 Na + 2 Cl, strictly alternating.
        assert result.na_count == 2
        assert result.cl_count == 2
        ion_types = [m.mol_type for m in result.molecule_index
                     if m.mol_type in ("na", "cl")]
        assert ion_types == ["na", "cl", "na", "cl"]
