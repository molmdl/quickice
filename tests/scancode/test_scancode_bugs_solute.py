"""Regression tests for scancode-verified bugs in the solute inserter module.

These tests prevent silent reversion of bug fixes verified by static analysis.

V-03 (HIGH): Solute inserter cKDTree rebuild optimization.
The existing_tree cKDTree should be rebuilt ONLY after a successful
solute placement, not on every loop iteration (including overlap
rejection iterations). Matches the ion_inserter conditional rebuild
pattern (TREE-01 / Plan 08).

PERF-02 (MEDIUM, follow-up): The existing_tree is now rebuilt in BATCHES
(every ``_SOLUTE_BATCH_SIZE`` successful placements) rather than after
every single placement. The V-03 invariant still holds: the tree is
rebuilt ONLY after successful placement (never on overlap rejection),
so the main-tree rebuild sizes are still strictly increasing with NO
duplicates. The sizes now jump by ``_SOLUTE_BATCH_SIZE *
n_atoms_per_molecule`` (e.g. 8 * 5 = 40) instead of 5, and a small
``buffer_tree`` (cKDTree of the current batch, rebuilt per successful
placement) handles recent placements not yet merged into the main tree.
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

        With the V-03 optimization, the main tree is rebuilt ONLY after a
        successful solute placement. PERF-02 batches the main tree rebuild
        (every ``_SOLUTE_BATCH_SIZE`` placements), so the main-tree sizes
        jump by ``_SOLUTE_BATCH_SIZE * n_atoms_per_molecule`` (e.g. 40 for
        CH4 with batch size 8) instead of 5. But the key invariant —
        STRICTLY INCREASING, NO DUPLICATES — is preserved.

        If V-03 is reverted (rebuild on every iteration including
        rejections), the main-tree sizes would have DUPLICATES because the
        tree is rebuilt even when no new solute was placed.
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

        # cKDTree is called from several sites in solute_inserter.py:
        # 1. _build_existing_atoms_tree: initial tree from ice+guest atoms
        #    (thousands of atoms, one call)
        # 2. PERF-02 buffer_tree rebuild: per successful placement, small
        #    (current batch's atoms, <= _SOLUTE_BATCH_SIZE * A)
        # 3. PERF-02 main tree batch rebuild: per _SOLUTE_BATCH_SIZE
        #    successful placements, growing (base + placed atoms)
        # 4. _remove_overlapping_water: solute_tree from just the placed
        #    solute positions (one call, size = placed_molecules * A)
        #
        # With V-03 + PERF-02: main-tree rebuild calls (site 3) form a
        # strictly increasing sequence. If V-03 is reverted, rebuild calls
        # have duplicate sizes because the tree is rebuilt even on
        # rejection iterations.

        if placed_molecules == 0:
            # No solutes placed — only the initial tree call (site 1)
            assert len(call_sizes) == 1, (
                f"No solutes placed, but found {len(call_sizes)} cKDTree calls "
                f"with sizes {call_sizes}"
            )
            return

        # Extract the main-tree batch rebuild calls (site 3):
        # These are calls with size >= initial_size (the main tree always
        # includes the base existing atoms, so its size >= initial_size).
        # Buffer tree calls (site 2) have small sizes (<= _SOLUTE_BATCH_SIZE * A),
        # and the solute_tree call (site 4) has size = placed_molecules * A
        # (which is < initial_size for typical fixtures).
        initial_size = call_sizes[0]
        rebuild_sizes = [s for s in call_sizes[1:] if s >= initial_size]

        # Rebuild sizes MUST be strictly increasing with NO duplicates.
        # PERF-02 batches the rebuild (sizes jump by _SOLUTE_BATCH_SIZE * A,
        # e.g. 40), but the key invariant — strictly increasing, no
        # duplicates — is preserved. If V-03 is reverted (rebuild on every
        # iteration including rejections), duplicates would appear (same
        # size rebuilt on a rejection iteration where no new solute was
        # placed).
        assert len(rebuild_sizes) == len(set(rebuild_sizes)), (
            f"Main-tree rebuild sizes have duplicates: {rebuild_sizes}. "
            f"Duplicates indicate redundant rebuilds on overlap-rejected "
            f"iterations (V-03 fix may have been reverted)."
        )
        for i in range(1, len(rebuild_sizes)):
            assert rebuild_sizes[i] > rebuild_sizes[i - 1], (
                f"Main-tree rebuild sizes not strictly increasing at index "
                f"{i}: {rebuild_sizes[i-1]} -> {rebuild_sizes[i]}. "
                f"A non-increasing step means a rebuild happened without new "
                f"placements (V-03 reverted?). Full rebuild sizes: {rebuild_sizes}"
            )

        # The number of main-tree rebuilds must be bounded by the number
        # of placed molecules (PERF-02 batches the rebuild, so the count is
        # ceil(placed_molecules / _SOLUTE_BATCH_SIZE), which is <= placed_molecules).
        assert len(rebuild_sizes) <= placed_molecules, (
            f"Main-tree rebuild count ({len(rebuild_sizes)}) should not exceed "
            f"placed molecules ({placed_molecules}). Extra rebuilds indicate "
            f"unconditional per-iteration rebuild pattern (V-03 reverted?)."
        )

    def test_no_redundant_rebuilds_on_high_concentration(self, interface_slab):
        """cKDTree call count bounded by placed molecules, not by total attempts.

        With the V-03 + PERF-02 optimization, total cKDTree calls = 1 (initial
        tree) + M (buffer_tree rebuilds, one per successful placement) +
        ceil(M / _SOLUTE_BATCH_SIZE) (main-tree batch rebuilds) + 1 (solute_tree
        in _remove_overlapping_water). If V-03 is reverted, the count would be
        much higher because the tree is rebuilt on every iteration including
        overlap rejections.

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
        # - PERF-02 buffer_tree rebuilds (M calls, small sizes <= B*A)
        # - PERF-02 main-tree batch rebuilds (ceil(M/B) calls, growing sizes)
        # - solute_tree from _remove_overlapping_water (1 call, small)
        initial_size = call_sizes[0]
        rebuild_sizes = [s for s in call_sizes[1:] if s >= initial_size]

        # Key regression check: main-tree rebuild sizes are strictly
        # increasing with NO duplicates (PERF-02 batches the rebuild, but
        # the strictly-increasing no-duplicates property is preserved).
        assert len(rebuild_sizes) == len(set(rebuild_sizes)), (
            f"Main-tree rebuild sizes have duplicates: {rebuild_sizes}. "
            f"Duplicates = redundant rebuilds (V-03 reverted?)."
        )
        for i in range(1, len(rebuild_sizes)):
            assert rebuild_sizes[i] > rebuild_sizes[i - 1], (
                f"Main-tree rebuild sizes not strictly increasing at index "
                f"{i}: {rebuild_sizes}. V-03 reverted?"
            )

        # Total cKDTree calls must be bounded by placed molecules, not by
        # total attempts. With V-03 + PERF-02, total calls = 1 + M +
        # ceil(M/B) + 1 < 2*M + 2 (for B >= 2). If V-03 is reverted, total
        # calls approach M * max_attempts (much higher).
        total_calls = len(call_sizes)
        # Upper bound: 2 * placed_molecules + 2 (1 initial + M buffer +
        # ceil(M/B) main + 1 solute_tree, all bounded by 2*M + 2 for B >= 2).
        # Use a generous bound of 3 * placed_molecules + 2 to allow for
        # the buffer tree and main tree rebuilds.
        max_optimized_calls = 3 * placed_molecules + 2 if placed_molecules > 0 else 1
        assert total_calls <= max_optimized_calls, (
            f"Total cKDTree calls ({total_calls}) should be bounded by "
            f"{max_optimized_calls} (3 * placed_molecules + 2, allowing for "
            f"buffer tree + main tree rebuilds). If V-03 is reverted, total "
            f"calls approach placed_molecules * max_attempts."
        )
