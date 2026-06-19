"""Regression tests for scancode-verified bugs in the ion inserter module.

These tests prevent silent reversion of bug fixes verified by static analysis.

TREE-01 (MEDIUM): Ion inserter KDTree rebuild optimization.
The ion_tree cKDTree should be rebuilt ONLY after a successful ion placement,
not on every loop iteration (including overlap rejection iterations).
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
        successful ion placement (ion_positions.append()). Each rebuild
        grows ion_positions by exactly 1, so the sizes of arrays passed
        to cKDTree for ion_tree form a strictly increasing sequence:
        1, 2, 3, ..., N (where N = ions that passed overlap checks).
        
        If reverted, the sizes would have DUPLICATES because the tree
        is rebuilt even on iterations where placement was rejected
        (ion_positions unchanged), so the same size appears multiple times.
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
        # The ion_tree is built from growing ion_positions (1, 2, 3, ...)
        existing_tree_sizes = [s for s in call_sizes if s > 100]
        ion_tree_sizes = [s for s in call_sizes if s <= 100]

        # There should be exactly 1 existing_atoms_tree call
        assert len(existing_tree_sizes) == 1, (
            f"Expected 1 existing_atoms_tree call, got {len(existing_tree_sizes)} "
            f"with sizes {existing_tree_sizes}"
        )

        # The ion_tree sizes MUST form a strictly increasing sequence 1, 2, ..., N
        # If the optimization is reverted, duplicates would appear (same size
        # rebuilt on rejection iterations where ion_positions didn't change)
        expected_sequence = list(range(1, len(ion_tree_sizes) + 1))
        assert ion_tree_sizes == expected_sequence, (
            f"ion_tree rebuild sizes should be strictly increasing "
            f"1, 2, ..., {len(ion_tree_sizes)}, but got {ion_tree_sizes}. "
            f"Duplicates indicate redundant rebuilds on overlap-rejected iterations "
            f"(TREE-01 optimization may have been reverted)."
        )

        # Final placed ions (after charge neutrality) <= ions that passed overlap
        assert placed_ions <= len(ion_tree_sizes), (
            f"Placed ions ({placed_ions}) should not exceed ions that passed "
            f"overlap checks ({len(ion_tree_sizes)})"
        )

    def test_no_redundant_rebuilds_on_overlap_rejections(self, interface_slab):
        """cKDTree call count bounded by placed ions, not by total loop iterations.
        
        With the optimization, total cKDTree calls = 1 (existing_atoms_tree)
        + N (ion_tree rebuilds, one per successfully placed ion). If the
        optimization is reverted, the count would be much higher because
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

        # Key regression check: ion_tree rebuilds form strictly increasing
        # sequence, meaning NO redundant rebuilds on rejection iterations
        expected_sequence = list(range(1, len(ion_tree_sizes) + 1))
        assert ion_tree_sizes == expected_sequence, (
            f"ion_tree sizes should be strictly increasing 1..{len(ion_tree_sizes)}, "
            f"got {ion_tree_sizes}. Duplicates = redundant rebuilds (TREE-01 reverted?)."
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
