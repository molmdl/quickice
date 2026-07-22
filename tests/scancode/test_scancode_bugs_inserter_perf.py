"""Regression tests for scancode perf issues PERF-04 and PERF-06.

PERF-04 (LOW): Per-atom Python cKDTree query loop in
``SoluteInserter._check_solute_overlap`` and ``CustomMoleculeInserter._check_overlap``
replaced with a single batched ``existing_tree.query(positions, k=1)`` call.
Result is byte-identical (any overlap -> True, no overlap -> False) but avoids
Python-loop overhead.

PERF-06 (LOW): Per-mol Python append loop in
``SoluteInserter._remove_overlapping_water`` replaced with vectorized boolean-mask
selection ``water_reshaped[~mol_overlaps]``. Kept positions / atom_names / order
match the loop output exactly.

Byte-equivalence strategy
-------------------------
These tests do NOT rely on `git stash` snapshots. Instead they prove byte-equivalence
directly by re-implementing the OLD per-atom / per-mol loop logic inside the test and
asserting the refactored method produces the same result across many seeded random
fixtures. This is stronger than a single golden snapshot because it exercises
thousands of (positions, threshold, mask) combinations.

1. PERF-04 direct: build a cKDTree, generate random solute positions and thresholds,
   compare ``inserter._check_solute_overlap`` / ``_check_overlap`` against a manual
   per-atom loop (the OLD code). Assert equal across many seeds + edge cases.
2. PERF-06 direct: build a water-positions array and a random overlap mask, compare
   the vectorized selection (the NEW code) against a manual per-mol append loop
   (the OLD code). Assert arrays equal and atom-name lists equal.
3. PERF-06 method: invoke ``SoluteInserter._remove_overlapping_water`` on a seeded
   InterfaceStructure fixture and assert the output water positions / atom_names /
   counts match the manual per-mol loop computation done in the test.
4. End-to-end seeded-RNG: run ``SoluteInserter.insert_solutes`` with a fixed seed and
   assert the output is reproducible (n_molecules, positions, atom_names). Combined
   with the direct byte-equivalence tests, this guards the full pipeline.
"""

import numpy as np
import pytest
from pathlib import Path
from scipy.spatial import cKDTree

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
    SoluteConfig,
    WATER_ATOMS_PER_MOLECULE,
)
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter


# ── PERF-04: batch cKDTree query ──────────────────────────────────────────────


def _loop_overlap_check(tree, positions, min_separation):
    """Reference implementation of the OLD per-atom overlap-check loop.

    This is the exact code that lived in ``_check_solute_overlap`` /
    ``_check_overlap`` before PERF-04. Kept here as the byte-equivalence oracle.
    """
    for atom_pos in positions:
        min_dist = tree.query(atom_pos, k=1)[0]
        if min_dist < min_separation:
            return True
    return False


def _make_custom_inserter(tmp_path):
    """Build a minimal CustomMoleculeInserter backed by temp .gro/.itp files.

    The constructor calls ``parse_gro_file`` / ``parse_itp_file``, so we need
    real files. ``_check_overlap`` does not use any instance state, so the
    template content is irrelevant for PERF-04 testing.
    """
    gro_path = tmp_path / "perf04_test.gro"
    gro_path.write_text(
        "PERF04 test\n"
        "    3\n"
        "    1MOL    C1    1   0.000   0.000   0.000\n"
        "    1MOL    H1    2   0.150   0.000   0.000\n"
        "    1MOL    H2    3  -0.150   0.000   0.000\n"
        "   3.0  3.0  3.0\n"
    )
    itp_path = tmp_path / "perf04_test.itp"
    itp_path.write_text(
        "[ moleculetype ]\n"
        "MOL       3\n"
        "\n"
        "[ atoms ]\n"
        "    1   CT      1    MOL    C1    1   0.00  12.01\n"
        "    2   HC      1    MOL    H1    2   0.00   1.008\n"
        "    3   HC      1    MOL    H2    3   0.00   1.008\n"
    )
    config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=gro_path,
        itp_path=itp_path,
        molecule_count=1,
        min_separation=0.3,
        max_attempts=10,
    )
    return CustomMoleculeInserter(config)


class TestPERF04BatchCKDTreeQuery:
    """PERF-04: batch cKDTree query produces identical overlap decisions to the
    per-atom Python loop."""

    @pytest.mark.parametrize("seed", [0, 1, 2, 42, 123, 999])
    def test_solute_inserter_batch_matches_loop(self, seed):
        """``_check_solute_overlap`` matches the per-atom loop on random fixtures."""
        rng = np.random.default_rng(seed)
        n_existing = 50
        existing_positions = rng.uniform(0.0, 5.0, size=(n_existing, 3))
        tree = cKDTree(existing_positions)

        inserter = SoluteInserter()

        for _ in range(20):
            n_atoms = int(rng.integers(1, 10))
            solute_positions = rng.uniform(0.0, 5.0, size=(n_atoms, 3))
            min_separation = float(rng.uniform(0.05, 0.5))

            loop_result = _loop_overlap_check(tree, solute_positions, min_separation)
            batch_result = inserter._check_solute_overlap(
                solute_positions, tree, min_separation
            )

            assert batch_result == loop_result, (
                f"seed={seed}, n_atoms={n_atoms}, sep={min_separation:.4f}: "
                f"loop={loop_result}, batch={batch_result}"
            )

    @pytest.mark.parametrize("seed", [0, 1, 2, 42, 123, 999])
    def test_custom_inserter_batch_matches_loop(self, seed, tmp_path):
        """``_check_overlap`` matches the per-atom loop on random fixtures."""
        rng = np.random.default_rng(seed)
        n_existing = 50
        existing_positions = rng.uniform(0.0, 5.0, size=(n_existing, 3))
        tree = cKDTree(existing_positions)

        inserter = _make_custom_inserter(tmp_path)

        for _ in range(20):
            n_atoms = int(rng.integers(1, 10))
            positions = rng.uniform(0.0, 5.0, size=(n_atoms, 3))
            min_separation = float(rng.uniform(0.05, 0.5))

            loop_result = _loop_overlap_check(tree, positions, min_separation)
            batch_result = inserter._check_overlap(positions, tree, min_separation)

            assert batch_result == loop_result, (
                f"seed={seed}, n_atoms={n_atoms}, sep={min_separation:.4f}: "
                f"loop={loop_result}, batch={batch_result}"
            )

    def test_solute_inserter_edge_cases(self):
        """Edge cases: empty positions, single atom, all-overlap, no-overlap,
        short-circuit-on-first-atom, short-circuit-on-last-atom."""
        existing = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0],
                [2.0, 2.0, 2.0],
            ]
        )
        tree = cKDTree(existing)
        inserter = SoluteInserter()

        # Empty positions: loop returns False (no iterations); batch returns False.
        empty = np.zeros((0, 3))
        assert _loop_overlap_check(tree, empty, 0.2) is False
        assert inserter._check_solute_overlap(empty, tree, 0.2) is False

        # Single atom overlapping.
        single_hit = np.array([[0.1, 0.0, 0.0]])
        assert _loop_overlap_check(tree, single_hit, 0.2) is True
        assert inserter._check_solute_overlap(single_hit, tree, 0.2) is True

        # Single atom not overlapping.
        single_miss = np.array([[10.0, 10.0, 10.0]])
        assert _loop_overlap_check(tree, single_miss, 0.2) is False
        assert inserter._check_solute_overlap(single_miss, tree, 0.2) is False

        # Short-circuit: first atom overlaps, others do not.
        first_hit = np.array(
            [[0.1, 0.0, 0.0], [10.0, 10.0, 10.0], [20.0, 20.0, 20.0]]
        )
        assert _loop_overlap_check(tree, first_hit, 0.2) is True
        assert inserter._check_solute_overlap(first_hit, tree, 0.2) is True

        # Short-circuit: first atom misses, last atom overlaps.
        last_hit = np.array(
            [[10.0, 10.0, 10.0], [20.0, 20.0, 20.0], [1.05, 1.05, 1.05]]
        )
        assert _loop_overlap_check(tree, last_hit, 0.2) is True
        assert inserter._check_solute_overlap(last_hit, tree, 0.2) is True

        # All atoms miss.
        all_miss = np.array(
            [[10.0, 10.0, 10.0], [20.0, 20.0, 20.0], [30.0, 30.0, 30.0]]
        )
        assert _loop_overlap_check(tree, all_miss, 0.2) is False
        assert inserter._check_solute_overlap(all_miss, tree, 0.2) is False

        # All atoms hit.
        all_hit = np.array(
            [[0.05, 0.0, 0.0], [1.05, 1.05, 1.05], [2.05, 2.05, 2.05]]
        )
        assert _loop_overlap_check(tree, all_hit, 0.2) is True
        assert inserter._check_solute_overlap(all_hit, tree, 0.2) is True

    def test_custom_inserter_edge_cases(self, tmp_path):
        """Same edge cases for CustomMoleculeInserter._check_overlap."""
        existing = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0],
                [2.0, 2.0, 2.0],
            ]
        )
        tree = cKDTree(existing)
        inserter = _make_custom_inserter(tmp_path)

        empty = np.zeros((0, 3))
        assert _loop_overlap_check(tree, empty, 0.2) is False
        assert inserter._check_overlap(empty, tree, 0.2) is False

        single_hit = np.array([[0.1, 0.0, 0.0]])
        assert _loop_overlap_check(tree, single_hit, 0.2) is True
        assert inserter._check_overlap(single_hit, tree, 0.2) is True

        all_miss = np.array(
            [[10.0, 10.0, 10.0], [20.0, 20.0, 20.0], [30.0, 30.0, 30.0]]
        )
        assert _loop_overlap_check(tree, all_miss, 0.2) is False
        assert inserter._check_overlap(all_miss, tree, 0.2) is False

        all_hit = np.array(
            [[0.05, 0.0, 0.0], [1.05, 1.05, 1.05], [2.05, 2.05, 2.05]]
        )
        assert _loop_overlap_check(tree, all_hit, 0.2) is True
        assert inserter._check_overlap(all_hit, tree, 0.2) is True

    @pytest.mark.parametrize("seed", [7, 77, 777])
    def test_solute_inserter_end_to_end_seeded_reproducible(self, seed):
        """End-to-end: ``SoluteInserter.insert_solutes`` with a fixed seed produces
        reproducible output (n_molecules, positions, atom_names). Combined with the
        direct byte-equivalence tests above, this guards the full pipeline.
        """
        interface_a = _build_seeded_interface(seed=seed)
        interface_b = _build_seeded_interface(seed=seed)
        config = SoluteConfig(
            concentration_molar=0.5,
            solute_type="CH4",
            max_attempts=200,
            seed=seed,
        )

        inserter_a = SoluteInserter(config=config, seed=seed)
        result_a = inserter_a.insert_solutes(interface_a, config)

        inserter_b = SoluteInserter(config=config, seed=seed)
        result_b = inserter_b.insert_solutes(interface_b, config)

        assert result_a.n_molecules == result_b.n_molecules
        assert result_a.positions.shape == result_b.positions.shape
        np.testing.assert_array_equal(result_a.positions, result_b.positions)
        assert list(result_a.atom_names) == list(result_b.atom_names)
        # Sanity: at least one molecule placed on this fixture (proves the pipeline
        # actually exercised the batch-query overlap check on real placement attempts).
        assert result_a.n_molecules > 0, (
            f"seed={seed}: expected >0 solutes placed, got {result_a.n_molecules}"
        )


# ── Shared fixture builder ────────────────────────────────────────────────────


def _build_seeded_interface(seed=42, n_ice_molecules=20, n_water_molecules=80):
    """Build a deterministic InterfaceStructure for end-to-end inserter tests.

    Layout: ice (3-atom OHH) + water (3-atom OHH). Both regions are placed on a
    regular grid jittered by a seeded RNG so the fixture is deterministic but
    non-trivial (not all on a single point, so overlap checks matter).
    """
    rng = np.random.default_rng(seed)

    ice_positions = []
    for i in range(n_ice_molecules):
        cx = (i % 5) * 0.6 + 0.3
        cy = (i // 5) * 0.6 + 0.3
        cz = 0.3
        ice_positions.append([cx, cy, cz])
        ice_positions.append([cx + 0.095, cy + 0.15, cz])
        ice_positions.append([cx + 0.095, cy - 0.15, cz])

    water_positions = []
    for i in range(n_water_molecules):
        cx = (i % 8) * 0.5 + 0.25 + float(rng.uniform(-0.05, 0.05))
        cy = 3.0 + (i // 8) * 0.5 + 0.25 + float(rng.uniform(-0.05, 0.05))
        cz = 0.25 + float(rng.uniform(-0.05, 0.05))
        water_positions.append([cx, cy, cz])  # O
        water_positions.append([cx + 0.095, cy + 0.15, cz])  # H
        water_positions.append([cx + 0.095, cy - 0.15, cz])  # H

    all_positions = np.array(ice_positions + water_positions, dtype=float)
    atom_names = ["O", "H", "H"] * (n_ice_molecules + n_water_molecules)
    cell = np.eye(3) * 6.0

    return InterfaceStructure(
        positions=all_positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=n_ice_molecules * 3,
        water_atom_count=n_water_molecules * 3,
        ice_nmolecules=n_ice_molecules,
        water_nmolecules=n_water_molecules,
        mode="slab",
        report="Seeded fixture for PERF-04/06 regression tests",
    )


# ── PERF-06: vectorized water removal ─────────────────────────────────────────


def _loop_water_removal(
    structure_positions,
    structure_atom_names,
    water_start,
    n_water_molecules,
    atoms_per_water,
    mol_overlaps,
):
    """Reference implementation of the OLD per-mol water-removal append loop.

    Re-implements the exact code that lived in ``_remove_overlapping_water`` before
    PERF-06. Kept here as the byte-equivalence oracle. Returns
    ``(kept_positions_array, kept_atom_names_list)`` where ``kept_positions_array``
    is the ``np.vstack`` of the per-mol slices (matching the downstream consumer)
    and ``kept_atom_names_list`` is the flat ``.extend`` output.
    """
    water_molecules_to_keep = np.where(~mol_overlaps)[0].tolist()
    kept_water_positions = []
    kept_water_atom_names = []
    for mol_idx in water_molecules_to_keep:
        atom_start = water_start + mol_idx * atoms_per_water
        atom_end = atom_start + atoms_per_water
        kept_water_positions.append(structure_positions[atom_start:atom_end])
        kept_water_atom_names.extend(structure_atom_names[atom_start:atom_end])
    if kept_water_positions:
        kept_positions_arr = np.vstack(kept_water_positions)
    else:
        kept_positions_arr = np.zeros((0, 3))
    return kept_positions_arr, kept_water_atom_names, water_molecules_to_keep


class TestPERF06VectorizedWaterRemoval:
    """PERF-06: vectorized boolean-mask water removal produces identical kept
    positions / atom_names / order to the per-mol Python append loop."""

    @pytest.mark.parametrize("seed", [0, 1, 2, 42, 123, 999])
    def test_vectorized_selection_matches_loop(self, seed):
        """Direct algorithm test: vectorized ``water_reshaped[~mol_overlaps]`` matches
        the per-mol append loop on random fixtures (varying n_molecules,
        atoms_per_water, overlap density).
        """
        rng = np.random.default_rng(seed)
        n_water_molecules = int(rng.integers(10, 100))
        atoms_per_water = int(rng.choice([3, 4]))
        water_start = 0
        n_check_atoms = n_water_molecules * atoms_per_water

        water_positions_all = rng.uniform(0.0, 5.0, size=(n_check_atoms, 3))
        structure_positions = water_positions_all.copy()
        # Atom names: cycle O/H/H (TIP3P) or O/H/H/MW (TIP4P) per molecule.
        if atoms_per_water == 3:
            per_mol_names = ["O", "H", "H"]
        else:
            per_mol_names = ["O", "H", "H", "MW"]
        atom_names = per_mol_names * n_water_molecules

        # Random overlap mask (~30% overlap density).
        overlap_density = float(rng.uniform(0.0, 0.6))
        mol_overlaps = rng.uniform(size=n_water_molecules) < overlap_density

        # OLD: per-mol append loop.
        loop_positions, loop_names, _ = _loop_water_removal(
            structure_positions,
            atom_names,
            water_start,
            n_water_molecules,
            atoms_per_water,
            mol_overlaps,
        )

        # NEW: vectorized boolean-mask selection (mirror the refactor).
        water_reshaped = water_positions_all.reshape(
            n_water_molecules, atoms_per_water, 3
        )
        keep_mask = ~mol_overlaps
        kept_batch = water_reshaped[keep_mask]
        if kept_batch.size > 0:
            batch_positions = kept_batch.reshape(-1, 3)
        else:
            batch_positions = np.zeros((0, 3))
        names_reshaped = np.asarray(atom_names).reshape(
            n_water_molecules, atoms_per_water
        )
        batch_names = names_reshaped[keep_mask].reshape(-1).tolist()

        # Assert byte-identical output (positions, atom_names, order, counts).
        assert batch_positions.shape == loop_positions.shape, (
            f"seed={seed}: shape mismatch batch={batch_positions.shape} "
            f"vs loop={loop_positions.shape}"
        )
        np.testing.assert_array_equal(batch_positions, loop_positions)
        assert batch_names == loop_names, f"seed={seed}: atom-name list mismatch"
        assert len(batch_names) == batch_positions.shape[0]

    def test_vectorized_edge_cases(self):
        """Edge cases: no overlap (keep all), all overlap (keep none), single
        molecule, odd overlap patterns."""
        atoms_per_water = 4
        per_mol_names = ["O", "H", "H", "MW"]

        # No overlap: keep all molecules.
        n = 5
        water_positions_all = np.arange(n * atoms_per_water * 3, dtype=float).reshape(
            n * atoms_per_water, 3
        )
        atom_names = per_mol_names * n
        mol_overlaps = np.zeros(n, dtype=bool)
        loop_pos, loop_names, _ = _loop_water_removal(
            water_positions_all, atom_names, 0, n, atoms_per_water, mol_overlaps
        )
        water_reshaped = water_positions_all.reshape(n, atoms_per_water, 3)
        batch_pos = water_reshaped[~mol_overlaps].reshape(-1, 3)
        batch_names = (
            np.asarray(atom_names).reshape(n, atoms_per_water)[~mol_overlaps]
            .reshape(-1)
            .tolist()
        )
        np.testing.assert_array_equal(batch_pos, loop_pos)
        assert batch_names == loop_names
        assert batch_pos.shape[0] == n * atoms_per_water

        # All overlap: keep none.
        mol_overlaps_all = np.ones(n, dtype=bool)
        loop_pos2, loop_names2, _ = _loop_water_removal(
            water_positions_all, atom_names, 0, n, atoms_per_water, mol_overlaps_all
        )
        batch_pos2 = water_reshaped[~mol_overlaps_all]
        assert batch_pos2.size == 0
        assert loop_pos2.shape == (0, 3)
        assert loop_names2 == []
        batch_names2 = (
            np.asarray(atom_names).reshape(n, atoms_per_water)[~mol_overlaps_all]
            .reshape(-1)
            .tolist()
        )
        assert batch_names2 == []

        # Single molecule, kept.
        n1 = 1
        w1 = water_positions_all[:atoms_per_water]
        mol1 = np.zeros(n1, dtype=bool)
        loop_pos3, loop_names3, _ = _loop_water_removal(
            w1, per_mol_names, 0, n1, atoms_per_water, mol1
        )
        batch_pos3 = w1.reshape(n1, atoms_per_water, 3)[~mol1].reshape(-1, 3)
        np.testing.assert_array_equal(batch_pos3, loop_pos3)

        # Odd pattern: keep molecules 0 and 2, remove 1 and 3.
        mol_odd = np.array([False, True, False, True, True])
        loop_pos4, loop_names4, _ = _loop_water_removal(
            water_positions_all, atom_names, 0, n, atoms_per_water, mol_odd
        )
        batch_pos4 = water_reshaped[~mol_odd].reshape(-1, 3)
        batch_names4 = (
            np.asarray(atom_names).reshape(n, atoms_per_water)[~mol_odd]
            .reshape(-1)
            .tolist()
        )
        np.testing.assert_array_equal(batch_pos4, loop_pos4)
        assert batch_names4 == loop_names4
        assert batch_pos4.shape[0] == 2 * atoms_per_water  # 2 kept molecules

    @pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
    def test_remove_overlapping_water_method_matches_loop(self, seed):
        """Method-level byte-equivalence: invoke
        ``SoluteInserter._remove_overlapping_water`` on a seeded fixture and assert
        the returned structure's kept water positions / atom_names / counts match
        the manual per-mol loop computation done in the test (the OLD code).
        """
        rng = np.random.default_rng(seed)
        n_ice_molecules = 10
        n_water_molecules = 40
        atoms_per_water = 3  # TIP3P fixture (matches _build_seeded_interface)
        ice_atom_count = n_ice_molecules * 3
        water_atom_count = n_water_molecules * atoms_per_water
        water_start = ice_atom_count
        min_separation = 0.25  # nm — chosen so SOME water overlaps but not all

        interface = _build_seeded_interface(
            seed=seed, n_ice_molecules=n_ice_molecules, n_water_molecules=n_water_molecules
        )

        # Place a few solute atoms inside the water region to force overlap removal.
        # Use the seeded RNG to pick water molecule centers and place solute atoms
        # near them (closer than min_separation), guaranteeing overlaps.
        n_solute_atoms = 6
        solute_positions_list = []
        water_mol_indices_to_hit = rng.choice(
            n_water_molecules, size=min(n_solute_atoms, n_water_molecules), replace=False
        )
        for mol_idx in water_mol_indices_to_hit:
            o_idx = water_start + int(mol_idx) * atoms_per_water
            # Place a solute atom very close to this water molecule's O atom.
            solute_positions_list.append(
                interface.positions[o_idx] + rng.uniform(-0.05, 0.05, size=3)
            )
        solute_positions = np.array(solute_positions_list, dtype=float)

        # Compute the expected overlap mask using the SAME cKDTree approach the
        # method uses (the method's mask computation was NOT changed by PERF-06;
        # only the per-mol append loop was vectorized).
        solute_tree = cKDTree(solute_positions)
        n_check_atoms = n_water_molecules * atoms_per_water
        water_positions_all = interface.positions[water_start:water_start + n_check_atoms]
        dists, _ = solute_tree.query(water_positions_all, k=1)
        dists_reshaped = dists.reshape(n_water_molecules, atoms_per_water)
        mol_overlaps = np.any(dists_reshaped < min_separation, axis=1)

        # If no overlap occurred, the method returns the original structure early
        # (removed_count == 0 path). Force a fixture where at least one molecule
        # overlaps so the PERF-06 code path actually runs.
        assert mol_overlaps.any(), (
            f"seed={seed}: fixture must have at least one overlapping water molecule "
            f"to exercise the PERF-06 code path (got 0 overlaps)"
        )

        # OLD: manual per-mol loop (the byte-equivalence oracle).
        expected_kept_pos, expected_kept_names, expected_keep_list = _loop_water_removal(
            interface.positions,
            interface.atom_names,
            water_start,
            n_water_molecules,
            atoms_per_water,
            mol_overlaps,
        )

        # NEW: invoke the refactored method.
        inserter = SoluteInserter()
        result = inserter._remove_overlapping_water(
            interface, solute_positions, min_separation
        )

        # Extract the kept water block from the returned structure.
        result_kept_start = result.ice_atom_count
        result_kept_end = result.ice_atom_count + result.water_atom_count
        result_kept_pos = result.positions[result_kept_start:result_kept_end]
        result_kept_names = list(result.atom_names[result_kept_start:result_kept_end])

        # Assert byte-identical kept water positions / atom_names / counts.
        assert result.water_atom_count == len(expected_kept_names), (
            f"seed={seed}: water_atom_count mismatch method={result.water_atom_count} "
            f"vs loop={len(expected_kept_names)}"
        )
        assert result.water_nmolecules == len(expected_keep_list), (
            f"seed={seed}: water_nmolecules mismatch method={result.water_nmolecules} "
            f"vs loop={len(expected_keep_list)}"
        )
        assert result_kept_pos.shape == expected_kept_pos.shape, (
            f"seed={seed}: kept positions shape mismatch "
            f"method={result_kept_pos.shape} vs loop={expected_kept_pos.shape}"
        )
        np.testing.assert_array_equal(result_kept_pos, expected_kept_pos)
        assert result_kept_names == expected_kept_names, (
            f"seed={seed}: kept atom-names list mismatch"
        )

    @pytest.mark.parametrize("seed", [7, 77, 777])
    def test_insert_solutes_end_to_end_removes_water_reproducibly(self, seed):
        """End-to-end: ``SoluteInserter.insert_solutes`` places solutes and removes
        overlapping water; the resulting water count + positions are reproducible
        across re-runs with the same seed. Combined with the direct byte-equivalence
        tests, this guards the full water-removal pipeline.
        """
        interface_a = _build_seeded_interface(seed=seed)
        interface_b = _build_seeded_interface(seed=seed)
        config = SoluteConfig(
            concentration_molar=1.0,  # higher concentration -> more water removed
            solute_type="CH4",
            max_attempts=300,
            seed=seed,
        )

        inserter_a = SoluteInserter(config=config, seed=seed)
        result_a = inserter_a.insert_solutes(interface_a, config)

        inserter_b = SoluteInserter(config=config, seed=seed)
        result_b = inserter_b.insert_solutes(interface_b, config)

        # Reproducibility: same seed -> identical positions, atom_names, counts.
        assert result_a.n_molecules == result_b.n_molecules
        assert result_a.positions.shape == result_b.positions.shape
        np.testing.assert_array_equal(result_a.positions, result_b.positions)
        assert list(result_a.atom_names) == list(result_b.atom_names)

        # Sanity: solutes were placed and water was removed (the fixture has 80 water
        # molecules; with 1.0 M CH4 in ~6x6x6 nm^3, we expect non-trivial placement).
        assert result_a.n_molecules > 0
        assert result_a.water_nmolecules < 80, (
            f"seed={seed}: expected some water removed, "
            f"got water_nmolecules={result_a.water_nmolecules}"
        )
