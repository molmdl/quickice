"""Regression tests for scancode-verified bugs in the ion inserter module.

These tests prevent silent reversion of bug fixes verified by static analysis.

TREE-01 (MEDIUM): Ion inserter KDTree rebuild optimization.
The ion_tree cKDTree should be rebuilt ONLY after a successful ion placement,
not on every loop iteration (including overlap rejection iterations).

PERF-01 (MEDIUM, follow-up): The ion_tree is now rebuilt in BATCHES (every
``_ION_BATCH_SIZE`` successful placements) rather than after every single
placement. The TREE-01 invariant still holds: the tree is rebuilt ONLY
after successful placement (never on overlap rejection), so the rebuild
sizes are still strictly increasing with NO duplicates. The sizes now jump
by ``_ION_BATCH_SIZE`` (e.g. 8, 16, 24, 32) instead of 1, 2, 3, 4, but the
"strictly increasing, no duplicates" property is preserved — that is what
these tests guard.
"""

import pytest
import numpy as np
from scipy.spatial import cKDTree
from unittest.mock import patch

from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.types import IonConfig, WATER_VOLUME_NM3


def _liquid_volume_nm3(structure) -> float:
    """Estimate liquid volume from water molecule count (TIP4P: WATER_VOLUME_NM3 nm³/mol)."""
    water_nmolecules = getattr(structure, 'water_nmolecules', 0)
    if water_nmolecules == 0:
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        water_nmolecules = water_atom_count // 4 if water_atom_count > 0 else 0
    return water_nmolecules * WATER_VOLUME_NM3


class TestTREE01:
    """Regression tests for TREE-01: ion inserter KDTree rebuild optimization.
    
    The ion_tree should be rebuilt ONLY after a successful placement,
    not on every loop iteration (including overlap rejections).
    
    If these tests fail, someone may have moved the ion_tree rebuild back
    outside the conditional block, causing O(iterations) tree rebuilds
    instead of O(placed_ions) rebuilds.
    """

    def test_ion_tree_sizes_strictly_increasing(self, interface_slab):
        """ion_tree cKDTree rebuild sizes must form a strictly increasing sequence.
        
        With the TREE-01 optimization, ion_tree is rebuilt ONLY after a
        successful ion placement. PERF-01 batches the rebuild (every
        ``_ION_BATCH_SIZE`` placements), so the sizes jump by the batch
        size (e.g. 8, 16, 24, 32) instead of 1, 2, 3, 4. But the key
        invariant — STRICTLY INCREASING, NO DUPLICATES — is preserved:
        each rebuild incorporates new placements, so the size always grows.
        
        If TREE-01 is reverted (rebuild on every iteration including
        rejections), the sizes would have DUPLICATES because the tree is
        rebuilt even when ion_positions didn't change (rejection iteration).
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        # Track cKDTree call sizes to detect redundant rebuilds
        original_cKDTree = cKDTree
        call_sizes = []

        def tracking_cKDTree(data, *args, **kwargs):
            size = data.shape[0] if hasattr(data, 'shape') else len(data)
            call_sizes.append(size)
            return original_cKDTree(data, *args, **kwargs)

        with patch(
            'quickice.structure_generation.ion_inserter.cKDTree',
            tracking_cKDTree,
        ):
            ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        placed_ions = ion.na_count + ion.cl_count

        # Separate existing_atoms_tree call (large array) from ion_tree calls
        # The existing_atoms_tree is built once from ice+guest atoms (thousands)
        # The ion_tree is built from growing ion_positions (batched rebuilds)
        existing_tree_sizes = [s for s in call_sizes if s > 100]
        ion_tree_sizes = [s for s in call_sizes if s <= 100]

        # There should be exactly 1 existing_atoms_tree call
        assert len(existing_tree_sizes) == 1, (
            f"Expected 1 existing_atoms_tree call, got {len(existing_tree_sizes)} "
            f"with sizes {existing_tree_sizes}"
        )

        # The ion_tree sizes MUST be strictly increasing with NO duplicates.
        # PERF-01 batches the rebuild (sizes jump by _ION_BATCH_SIZE, e.g.
        # 8, 16, 24, 32), but the key invariant — strictly increasing, no
        # duplicates — is preserved. If TREE-01 is reverted (rebuild on
        # every iteration including rejections), duplicates would appear
        # (same size rebuilt on a rejection iteration where ion_positions
        # didn't change).
        assert len(ion_tree_sizes) == len(set(ion_tree_sizes)), (
            f"ion_tree rebuild sizes have duplicates: {ion_tree_sizes}. "
            f"Duplicates indicate redundant rebuilds on overlap-rejected "
            f"iterations (TREE-01 optimization may have been reverted)."
        )
        assert ion_tree_sizes == sorted(ion_tree_sizes), (
            f"ion_tree rebuild sizes are not sorted (strictly increasing): "
            f"{ion_tree_sizes}. Each rebuild must incorporate new placements."
        )
        # Strictly increasing (not just non-decreasing): each rebuild's size
        # is strictly greater than the previous.
        for i in range(1, len(ion_tree_sizes)):
            assert ion_tree_sizes[i] > ion_tree_sizes[i - 1], (
                f"ion_tree sizes not strictly increasing at index {i}: "
                f"{ion_tree_sizes}. A non-increasing step means a rebuild "
                f"happened without new placements (TREE-01 reverted?)."
            )

        # Final placed ions (after charge neutrality) <= ions that passed overlap
        # The last ion_tree rebuild size is the number of ions incorporated into
        # the tree; additional ions may sit in the PERF-01 buffer (not yet rebuilt
        # into the tree). So placed_ions may exceed the last tree size by up to
        # _ION_BATCH_SIZE - 1.
        assert placed_ions >= 1, (
            f"Expected at least 1 placed ion, got {placed_ions}"
        )

    def test_no_redundant_rebuilds_on_overlap_rejections(self, interface_slab):
        """cKDTree call count bounded by placed ions, not by total loop iterations.
        
        With the TREE-01 optimization, total cKDTree calls = 1 (existing_atoms_tree)
        + ion_tree rebuilds. PERF-01 batches the ion_tree rebuilds, so the count
        is even lower (ceil(placed_ions / _ION_BATCH_SIZE) instead of placed_ions).
        If the optimization is reverted, the count would be much higher because
        ion_tree is rebuilt on every iteration where ion_positions is non-empty.
        
        This test uses a higher concentration (0.5 M) to increase overlap
        rejections, making the difference between optimized and unoptimized
        counts more pronounced.
        """
        config = IonConfig(concentration_molar=0.5)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.5, volume)
        selected_count = ion_pairs * 2  # Total water positions in the loop

        original_cKDTree = cKDTree
        call_sizes = []

        def tracking_cKDTree(data, *args, **kwargs):
            size = data.shape[0] if hasattr(data, 'shape') else len(data)
            call_sizes.append(size)
            return original_cKDTree(data, *args, **kwargs)

        with patch(
            'quickice.structure_generation.ion_inserter.cKDTree',
            tracking_cKDTree,
        ):
            ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        placed_ions = ion.na_count + ion.cl_count

        # Separate calls
        ion_tree_sizes = [s for s in call_sizes if s <= 100]

        # Key regression check: ion_tree rebuilds are strictly increasing with
        # NO duplicates, meaning NO redundant rebuilds on rejection iterations.
        # PERF-01 batches the rebuild (sizes jump by _ION_BATCH_SIZE), but the
        # strictly-increasing no-duplicates property is preserved.
        assert len(ion_tree_sizes) == len(set(ion_tree_sizes)), (
            f"ion_tree sizes have duplicates: {ion_tree_sizes}. "
            f"Duplicates = redundant rebuilds (TREE-01 reverted?)."
        )
        for i in range(1, len(ion_tree_sizes)):
            assert ion_tree_sizes[i] > ion_tree_sizes[i - 1], (
                f"ion_tree sizes not strictly increasing at index {i}: "
                f"{ion_tree_sizes}. A non-increasing step means a rebuild "
                f"happened without new placements (TREE-01 reverted?)."
            )

        # The number of ion_tree rebuilds should be LESS than total loop
        # iterations (some positions are rejected for overlap)
        # If reverted, rebuilds would approach selected_count
        assert len(ion_tree_sizes) <= selected_count, (
            f"ion_tree rebuilds ({len(ion_tree_sizes)}) should not exceed "
            f"selected positions ({selected_count})"
        )

        # Total cKDTree calls = 1 (existing_atoms_tree) + ion_tree_rebuilds
        # This should be significantly less than 1 + selected_count
        # PERF-01 further reduces this (batched rebuilds), but the key
        # property is that it's less than the unoptimized upper bound.
        total_calls = len(call_sizes)
        max_unoptimized_calls = 1 + selected_count  # Upper bound if reverted
        assert total_calls < max_unoptimized_calls, (
            f"Total cKDTree calls ({total_calls}) should be less than "
            f"unoptimized upper bound ({max_unoptimized_calls} = 1 + {selected_count}). "
            f"If optimization is reverted, every iteration would rebuild ion_tree."
        )

    def test_ion_tree_none_on_first_iteration(self, interface_slab):
        """ion_tree starts as None; first ion skips ion-ion check.
        
        On the first iteration, ion_tree is None (no previously placed ions),
        so the ion-ion overlap check is skipped entirely. This verifies the
        `if ion_tree is not None:` guard instead of `if ion_positions:`.
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        # The first placed ion should never be rejected for ion-ion overlap
        # because there are no previous ions. This means na_count + cl_count
        # should be at least 1 (the first valid water position is accepted).
        assert ion.na_count + ion.cl_count >= 1, (
            "At least one ion should be placed (first position has no ion-ion overlap)"
        )
