"""Regression tests for scancode-verified bugs in the solute inserter module.

These tests prevent silent reversion of bug fixes verified by static analysis.

V-03 (HIGH): Solute inserter cKDTree rebuild optimization.
The existing_tree cKDTree should be rebuilt ONLY after a successful
solute placement, not on every loop iteration (including overlap
rejection iterations). Matches the ion_inserter conditional rebuild
pattern (TREE-01 / Plan 08).
"""

import pytest
import numpy as np
from scipy.spatial import cKDTree
from unittest.mock import patch

from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.types import SoluteConfig


class TestTREE03:
    """Regression tests for V-03: solute inserter cKDTree rebuild optimization.

    The existing_tree should be rebuilt ONLY after a successful placement,
    not on every loop iteration (including overlap rejections).

    If these tests fail, someone may have moved the tree rebuild back
    outside the success branch, causing O(iterations) tree rebuilds
    instead of O(placed_molecules) rebuilds.
    """

    def test_solute_tree_sizes_strictly_increasing(self, interface_slab):
        """existing_tree cKDTree rebuild sizes must form a strictly increasing sequence.

        With the V-03 optimization, the tree is rebuilt ONLY after a
        successful solute placement. Each rebuild adds exactly
        n_atoms_per_molecule atoms to combined_tree_data, so the sizes
        of arrays passed to cKDTree form a strictly increasing sequence.

        If reverted, the sizes would have DUPLICATES because the tree
        is rebuilt even on iterations where placement was rejected
        (combined_tree_data unchanged), so the same size appears
        multiple times.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)

        # Track cKDTree call sizes to detect redundant rebuilds
        original_cKDTree = cKDTree
        call_sizes = []

        def tracking_cKDTree(data, *args, **kwargs):
            size = data.shape[0] if hasattr(data, 'shape') else len(data)
            call_sizes.append(size)
            return original_cKDTree(data, *args, **kwargs)

        with patch(
            'quickice.structure_generation.solute_inserter.cKDTree',
            tracking_cKDTree,
        ):
            result = inserter.insert_solutes(interface_slab)

        placed_molecules = result.n_molecules

        # cKDTree is called from three sites in solute_inserter.py:
        # 1. _build_existing_atoms_tree (line 315): initial tree from ice+guest atoms
        #    (thousands of atoms, one call)
        # 2. Conditional rebuild in insert_solutes success branch (line 838):
        #    after each successful placement, growing by CH4_ATOMS_PER_MOLECULE=5
        #    each time — N calls for N placed molecules
        # 3. _remove_overlapping_water (line 370): solute_tree from just the
        #    placed solute positions (one call, size = placed_molecules × 5)
        #
        # With V-03 fix: rebuild calls (site 2) form a strictly increasing
        # sequence. If reverted, rebuild calls have duplicate sizes because
        # the tree is rebuilt even on rejection iterations.

        if placed_molecules == 0:
            # No solutes placed — only the initial tree call (site 1)
            assert len(call_sizes) == 1, (
                f"No solutes placed, but found {len(call_sizes)} cKDTree calls "
                f"with sizes {call_sizes}"
            )
            return

        # Extract the conditional rebuild calls (site 2):
        # These are the calls between the initial tree call and the
        # _remove_overlapping_water call. They form a growing sequence
        # where each entry is larger than the initial tree size (since
        # they add solute atoms to it).
        initial_size = call_sizes[0]
        # The _remove_overlapping_water call is the last call, with a
        # size much smaller than the initial tree (just solute atoms)
        solute_tree_size = placed_molecules * 5  # CH4_ATOMS_PER_MOLECULE = 5

        # Find rebuild calls: they start right after initial call, and
        # each is larger than the initial_size (growing by adding solutes).
        # The last call is the small solute_tree from _remove_overlapping_water.
        rebuild_sizes = [s for s in call_sizes[1:] if s >= initial_size]

        # Rebuild sizes MUST form a strictly increasing sequence
        # Each successful placement adds CH4_ATOMS_PER_MOLECULE=5 atoms
        for i in range(1, len(rebuild_sizes)):
            assert rebuild_sizes[i] > rebuild_sizes[i-1], (
                f"Rebuild sizes not strictly increasing at index {i}: "
                f"{rebuild_sizes[i-1]} -> {rebuild_sizes[i]}. "
                f"Duplicate sizes indicate redundant rebuilds on "
                f"overlap-rejected iterations (V-03 fix may have been reverted). "
                f"Full rebuild sizes: {rebuild_sizes}"
            )

        # Number of rebuilds must equal number of placed molecules
        assert len(rebuild_sizes) == placed_molecules, (
            f"Rebuild count ({len(rebuild_sizes)}) should equal "
            f"placed molecules ({placed_molecules}). "
            f"Extra rebuilds indicate unconditional-per-iteration pattern."
        )

        # Each rebuild should grow by exactly CH4_ATOMS_PER_MOLECULE=5 atoms
        ch4_atoms = 5  # CH4 has 5 atoms
        for i in range(1, len(rebuild_sizes)):
            increment = rebuild_sizes[i] - rebuild_sizes[i-1]
            assert increment == ch4_atoms, (
                f"Expected increment of {ch4_atoms} atoms per CH4 molecule, "
                f"got {increment} at rebuild index {i}"
            )

    def test_no_redundant_rebuilds_on_high_concentration(self, interface_slab):
        """cKDTree call count bounded by placed molecules, not by total attempts.

        With the optimization, total cKDTree calls = 1 (initial tree)
        + N (rebuilds, one per placed molecule) + 1 (solute_tree in
        _remove_overlapping_water). If the optimization is reverted, the
        count would be much higher because the tree is rebuilt on every
        iteration including overlap rejections.

        This test uses a higher concentration (1.0 M) to increase
        overlap rejections, making the difference more pronounced.
        """
        config = SoluteConfig(concentration_molar=1.0, solute_type="CH4", max_attempts=500)
        inserter = SoluteInserter(config=config, seed=42)

        original_cKDTree = cKDTree
        call_sizes = []

        def tracking_cKDTree(data, *args, **kwargs):
            size = data.shape[0] if hasattr(data, 'shape') else len(data)
            call_sizes.append(size)
            return original_cKDTree(data, *args, **kwargs)

        with patch(
            'quickice.structure_generation.solute_inserter.cKDTree',
            tracking_cKDTree,
        ):
            result = inserter.insert_solutes(interface_slab)

        placed_molecules = result.n_molecules

        # Separate calls by type:
        # - Initial tree from _build_existing_atoms_tree (1 call, large)
        # - Rebuilds after successful placements (N calls, growing sequence)
        # - solute_tree from _remove_overlapping_water (1 call, small)
        initial_size = call_sizes[0]
        rebuild_sizes = [s for s in call_sizes[1:] if s >= initial_size]
        rebuild_count = len(rebuild_sizes)

        # Key regression check: rebuild count equals placed count
        # If reverted, rebuild count would be much higher (approaching
        # N × max_attempts per molecule)
        assert rebuild_count == placed_molecules, (
            f"Rebuild count ({rebuild_count}) should equal placed molecules "
            f"({placed_molecules}). Extra rebuilds indicate unconditional "
            f"per-iteration rebuild pattern (V-03 fix may have been reverted)."
        )
