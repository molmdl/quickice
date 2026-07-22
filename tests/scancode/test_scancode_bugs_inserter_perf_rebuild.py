"""Regression tests for scancode PERF-01/02/03: batch cKDTree rebuild.

PERF-01 (MEDIUM): ``quickice/structure_generation/ion_inserter.py`` rebuilt
``cKDTree(np.array(ion_positions))`` after EVERY successful ion placement
(O(k^2 log k) total).

PERF-02 (MEDIUM): ``quickice/structure_generation/solute_inserter.py`` did
``combined_tree_data = np.vstack([combined_tree_data, solute_positions])``
followed by ``existing_tree = cKDTree(combined_tree_data)`` after EVERY
successful solute placement (O(N) vstack + O(N log N) rebuild per
placement).

PERF-03 (MEDIUM): ``quickice/structure_generation/custom_molecule_inserter.py``
had the same vstack + per-placement rebuild pattern as PERF-02.

The fix pre-allocates the positions array (avoids O(N) vstack/copy per
placement) and batches the cKDTree rebuild (rebuilds only every
``_BATCH_SIZE`` successful placements instead of every placement).
Recent placements not yet merged into the tree are checked via a direct
numpy distance scan against a small buffer. The cKDTree conditional
rebuild rule (AGENTS.md) is preserved: the tree is rebuilt ONLY after
successful placement (never on overlap rejection); the batch just
amortizes the rebuild over multiple successful placements.

Byte-equivalence strategy
-------------------------
The batch + buffer approach is byte-equivalent to the per-placement
rebuild IFF the overlap DECISION is identical at every candidate. The
decision is identical because:

1. The union of (tree placements) and (buffer placements) equals all
   placements so far — the same set the per-placement tree contained.
2. ``min(tree_dist, buffer_dist) < threshold`` is equivalent to
   ``all_placements_tree.query(pos)[0] < threshold``.
3. ``cKDTree.query`` and ``np.linalg.norm`` produce byte-identical
   Euclidean distances (verified in
   ``test_ckdtree_numpy_distance_byte_equivalence`` across 1000 random
   fixtures — max_diff == 0.0).

The end-to-end golden-snapshot tests below capture the SHA256 of the
output positions from the pre-fix per-placement rebuild code. If the
batch+buffer refactor changes any placement decision, the positions
change and the SHA256 mismatches — proving byte-equivalence by
exhaustion on the seeded fixture.
"""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.spatial import cKDTree

from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
    MoleculeIndex,
    SoluteConfig,
)


# ── Shared fixture builder ────────────────────────────────────────────────────


def _build_seeded_interface(seed=42, n_ice_molecules=20, n_water_molecules=80):
    """Build a deterministic InterfaceStructure for end-to-end inserter tests.

    Same layout as ``test_scancode_bugs_inserter_perf._build_seeded_interface``:
    ice (3-atom OHH) + water (3-atom OHH). Both regions are placed on a regular
    grid jittered by a seeded RNG so the fixture is deterministic but non-trivial.
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
        water_positions.append([cx, cy, cz])
        water_positions.append([cx + 0.095, cy + 0.15, cz])
        water_positions.append([cx + 0.095, cy - 0.15, cz])
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
        report="Seeded fixture for PERF-01/02/03 regression tests",
    )


def _sha256(arr: np.ndarray) -> str:
    """Stable SHA256 of a numpy array's raw bytes.

    Unlike ``hash(bytes)``, ``hashlib.sha256`` is NOT subject to
    PYTHONHASHSEED randomization — the digest is identical across
    processes and Python versions for the same input bytes.
    """
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _build_ion_fixture():
    """Build a deterministic structure for IonInserter with overlap rejections.

    Layout: 5 ice atoms (some near water to cause overlap rejections) + 30
    water molecules. With ``ion_pairs=10`` (20 waters selected) and seed=42,
    the inserter rejects 2 candidates for overlap with ice and places 18
    ions (9 Na + 9 Cl), exercising the batch+buffer path over multiple
    successful placements and rejections.
    """
    rng = np.random.default_rng(123)
    positions = []
    atom_names = []
    molecule_index = []
    ice_pos = [
        [1.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [3.0, 0.0, 0.0],
        [4.0, 0.0, 0.0],
        [5.0, 0.0, 0.0],
    ]
    for i, p in enumerate(ice_pos):
        positions.append(p)
        atom_names.append("O")
        molecule_index.append(MoleculeIndex(start_idx=i, count=1, mol_type="ice"))
    water_start = len(positions)
    for i in range(30):
        cx = 0.5 + (i % 6) * 0.5 + float(rng.uniform(-0.02, 0.02))
        cy = 1.0 + (i // 6) * 0.5 + float(rng.uniform(-0.02, 0.02))
        cz = float(rng.uniform(0.0, 0.5))
        if i in (0, 6, 12):
            cx = ice_pos[i // 6][0] + 0.05  # very close to ice -> rejection
        positions.append([cx, cy, cz])
        atom_names.append("O")
        molecule_index.append(
            MoleculeIndex(start_idx=water_start + i, count=1, mol_type="water")
        )
    positions = np.array(positions, dtype=float)
    return SimpleNamespace(
        positions=positions,
        atom_names=atom_names,
        cell=np.diag([10.0, 10.0, 10.0]),
        molecule_index=molecule_index,
    )


def _make_custom_inserter(tmp_path):
    """Build a minimal CustomMoleculeInserter backed by temp .gro/.itp files."""
    gro_path = tmp_path / "perf03_test.gro"
    gro_path.write_text(
        "PERF03 test\n"
        "    3\n"
        "    1MOL    C1    1   0.000   0.000   0.000\n"
        "    1MOL    H1    2   0.150   0.000   0.000\n"
        "    1MOL    H2    3  -0.150   0.000   0.000\n"
        "   3.0  3.0  3.0\n"
    )
    itp_path = tmp_path / "perf03_test.itp"
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
        molecule_count=5,
        min_separation=0.3,
        max_attempts=300,
    )
    return CustomMoleculeInserter(config=config, seed=0), config


# ── Foundational: cKDTree vs numpy distance byte-equivalence ──────────────────


class TestCKDTreeNumpyDistanceByteEquivalence:
    """The batch+buffer approach uses numpy for the buffer check while the
    per-placement rebuild used cKDTree.query. These must produce byte-identical
    overlap decisions. This test verifies the foundation across many fixtures.
    """

    @pytest.mark.parametrize("seed", list(range(20)))
    def test_ckdtree_numpy_distance_identical(self, seed):
        """cKDTree.query[pos, k=1][0] == np.min(np.linalg.norm(points - pos, axis=1))
        across many random fixtures. The min distance is byte-identical (not
        just close) because both compute sqrt(sum((a-b)^2)) over 3 elements in
        the same order.
        """
        rng = np.random.default_rng(seed)
        n = int(rng.integers(1, 100))
        points = rng.uniform(0.0, 10.0, size=(n, 3))
        tree = cKDTree(points)
        for _ in range(50):
            query = rng.uniform(0.0, 10.0, size=3)
            tree_dist = float(tree.query(query, k=1)[0])
            numpy_dist = float(np.min(np.linalg.norm(points - query, axis=1)))
            # Byte-identical (not just close): the overlap decision
            # (dist < threshold) must agree for every threshold.
            assert tree_dist == numpy_dist, (
                f"seed={seed}, n={n}: tree={tree_dist!r} != numpy={numpy_dist!r}"
            )

    @pytest.mark.parametrize("seed", list(range(20)))
    def test_ckdtree_numpy_overlap_decision_identical(self, seed):
        """For a range of thresholds, the overlap decision (dist < threshold)
        is identical between cKDTree and numpy across many fixtures."""
        rng = np.random.default_rng(seed)
        n = int(rng.integers(1, 100))
        points = rng.uniform(0.0, 10.0, size=(n, 3))
        tree = cKDTree(points)
        for _ in range(50):
            query = rng.uniform(0.0, 10.0, size=3)
            tree_dist = float(tree.query(query, k=1)[0])
            numpy_dist = float(np.min(np.linalg.norm(points - query, axis=1)))
            for threshold in (0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0):
                assert (tree_dist < threshold) == (numpy_dist < threshold), (
                    f"seed={seed}, threshold={threshold}: "
                    f"tree={tree_dist!r}, numpy={numpy_dist!r} disagree"
                )


# ── PERF-01: ion inserter batch rebuild ───────────────────────────────────────


class TestPERF01IonInserterBatchRebuild:
    """PERF-01: the ion inserter's cKDTree is rebuilt in batches rather than
    per-placement. The output (positions, counts, atom_names, ordering) must
    be byte-identical to the pre-fix per-placement rebuild."""

    def test_ion_inserter_golden_snapshot(self):
        """End-to-end: run IonInserter on a deterministic fixture with a fixed
        seed and assert the output matches the golden baseline captured from
        the pre-fix per-placement rebuild code.

        Fixture: 5 ice atoms + 30 water molecules; ion_pairs=10 (20 waters
        selected); seed=42. Expected: 9 Na + 9 Cl (2 candidates rejected for
        overlap with ice), positions shape (33, 3).

        The SHA256 was captured from the per-placement rebuild code BEFORE
        the PERF-01 refactor. If the batch+buffer refactor changes any
        placement decision, the positions change and the SHA256 mismatches.
        """
        structure = _build_ion_fixture()
        inserter = IonInserter(seed=42)
        result = inserter.replace_water_with_ions(structure, ion_pairs=10)

        # Counts must match the golden baseline.
        assert result.na_count == 9, (
            f"na_count mismatch: expected 9, got {result.na_count}"
        )
        assert result.cl_count == 9, (
            f"cl_count mismatch: expected 9, got {result.cl_count}"
        )
        # Shape must match.
        assert result.positions.shape == (33, 3), (
            f"positions shape mismatch: expected (33, 3), "
            f"got {result.positions.shape}"
        )
        # Atom names must match (15 O + 18 alternating NA/CL).
        expected_atom_names = (
            ["O"] * 15
            + ["NA", "CL"] * 9
        )
        assert list(result.atom_names) == expected_atom_names, (
            f"atom_names mismatch: expected {expected_atom_names}, "
            f"got {list(result.atom_names)}"
        )
        # SHA256 of positions must match the golden baseline (byte-equivalence).
        expected_sha = (
            "c8201a8f498f9a8b8820ecea4f979053ebf86cf18c9e8050e9256f213d445b31"
        )
        actual_sha = _sha256(result.positions)
        assert actual_sha == expected_sha, (
            f"positions SHA256 mismatch: expected {expected_sha}, "
            f"got {actual_sha}. The batch+buffer refactor changed the "
            f"placement decisions — byte-equivalence is broken."
        )

    def test_ion_inserter_reproducible_across_instances(self):
        """Same seed -> identical output across independent instances. This
        guards against any nondeterminism introduced by the batch+buffer
        refactor (e.g. buffer ordering, batch boundary effects)."""
        structure = _build_ion_fixture()
        result_a = IonInserter(seed=42).replace_water_with_ions(structure, ion_pairs=10)
        structure2 = _build_ion_fixture()
        result_b = IonInserter(seed=42).replace_water_with_ions(structure2, ion_pairs=10)
        assert result_a.na_count == result_b.na_count
        assert result_a.cl_count == result_b.cl_count
        np.testing.assert_array_equal(result_a.positions, result_b.positions)
        assert list(result_a.atom_names) == list(result_b.atom_names)


# ── PERF-02: solute inserter batch rebuild ────────────────────────────────────


class TestPERF02SoluteInserterBatchRebuild:
    """PERF-02: the solute inserter's vstack + per-placement cKDTree rebuild
    is replaced with pre-allocation + batched rebuild. The output must be
    byte-identical to the pre-fix code."""

    @pytest.mark.parametrize(
        "seed, expected_n, expected_water, expected_sha",
        [
            (
                7,
                3,
                73,
                "54bfb060282841beaa6d8194cf3847fff913de97c6b954aa58840a347ca44a28",
            ),
            (
                77,
                3,
                72,
                "4c2498692925574273674f9c9fa551bae31190ac402f3a308ae0aad7feae44da",
            ),
            (
                777,
                3,
                73,
                "c4278247272d58c83b6b78ab9a4c73340e0e5852f1d7c123ff75b5f7f0bf2c64",
            ),
        ],
    )
    def test_solute_inserter_golden_snapshot(
        self, seed, expected_n, expected_water, expected_sha
    ):
        """End-to-end: run SoluteInserter on a seeded fixture and assert the
        output matches the golden baseline captured from the pre-fix
        per-placement vstack+rebuild code.

        Fixture: 20 ice molecules + 80 water molecules; concentration=2.0 M
        CH4; max_attempts=300. Expected: 3 CH4 molecules placed (15 atoms),
        with some water molecules removed for overlap.

        The SHA256 was captured from the per-placement rebuild code BEFORE
        the PERF-02 refactor. If the pre-allocate + batch refactor changes
        any placement decision, the positions change and the SHA256
        mismatches.
        """
        interface = _build_seeded_interface(seed=seed)
        config = SoluteConfig(
            concentration_molar=2.0,
            solute_type="CH4",
            max_attempts=300,
            seed=seed,
        )
        inserter = SoluteInserter(config=config, seed=seed)
        result = inserter.insert_solutes(interface, config)

        # Counts must match the golden baseline.
        assert result.n_molecules == expected_n, (
            f"seed={seed}: n_molecules mismatch: expected {expected_n}, "
            f"got {result.n_molecules}"
        )
        assert result.water_nmolecules == expected_water, (
            f"seed={seed}: water_nmolecules mismatch: expected {expected_water}, "
            f"got {result.water_nmolecules}"
        )
        # Shape: 3 CH4 * 5 atoms = 15.
        assert result.positions.shape == (expected_n * 5, 3), (
            f"seed={seed}: positions shape mismatch: expected "
            f"({expected_n * 5}, 3), got {result.positions.shape}"
        )
        # Atom names: 3 * (C, H, H, H, H).
        expected_atom_names = ["C", "H", "H", "H", "H"] * expected_n
        assert list(result.atom_names) == expected_atom_names, (
            f"seed={seed}: atom_names mismatch"
        )
        # SHA256 of positions must match the golden baseline (byte-equivalence).
        actual_sha = _sha256(result.positions)
        assert actual_sha == expected_sha, (
            f"seed={seed}: positions SHA256 mismatch: expected {expected_sha}, "
            f"got {actual_sha}. The pre-allocate + batch refactor changed the "
            f"placement decisions — byte-equivalence is broken."
        )

    @pytest.mark.parametrize("seed", [7, 77, 777])
    def test_solute_inserter_reproducible_across_instances(self, seed):
        """Same seed -> identical output across independent instances."""
        interface_a = _build_seeded_interface(seed=seed)
        interface_b = _build_seeded_interface(seed=seed)
        config = SoluteConfig(
            concentration_molar=2.0,
            solute_type="CH4",
            max_attempts=300,
            seed=seed,
        )
        result_a = SoluteInserter(config=config, seed=seed).insert_solutes(interface_a, config)
        result_b = SoluteInserter(config=config, seed=seed).insert_solutes(interface_b, config)
        assert result_a.n_molecules == result_b.n_molecules
        np.testing.assert_array_equal(result_a.positions, result_b.positions)
        assert list(result_a.atom_names) == list(result_b.atom_names)
        assert result_a.water_nmolecules == result_b.water_nmolecules


# ── PERF-03: custom molecule inserter batch rebuild ───────────────────────────


class TestPERF03CustomMoleculeInserterBatchRebuild:
    """PERF-03: the custom molecule inserter's vstack + per-placement cKDTree
    rebuild is replaced with pre-allocation + batched rebuild. The output must
    be byte-identical to the pre-fix code."""

    @pytest.mark.parametrize(
        "seed, expected_water, expected_sha",
        [
            (
                7,
                68,
                "dd7180ce9f731ed5d54fcb2bc89d496fa6b1e938117447ae8d048eb5d0b01066",
            ),
            (
                77,
                69,
                "c8d0d08fe0bb68b0f8a2c27e1c4483b633a6dd852e264a38132c50e7f82cbfd7",
            ),
            (
                777,
                68,
                "76b27fba74838e352586e14d50cc28872ee516c4cffb12de265e124762a15dd5",
            ),
        ],
    )
    def test_custom_inserter_golden_snapshot(
        self, seed, expected_water, expected_sha, tmp_path
    ):
        """End-to-end: run CustomMoleculeInserter on a seeded fixture and
        assert the output matches the golden baseline captured from the
        pre-fix per-placement vstack+rebuild code.

        Fixture: 20 ice molecules + 80 water molecules; 3-atom custom
        molecule (C1, H1, H2); n_molecules=5; max_attempts=300. The
        CustomMoleculeStructure contains the full structure (ice + remaining
        water + placed custom molecules), so the SHA256 covers the entire
        output.

        The SHA256 was captured from the per-placement rebuild code BEFORE
        the PERF-03 refactor. If the pre-allocate + batch refactor changes
        any placement decision, the positions change and the SHA256
        mismatches.
        """
        interface = _build_seeded_interface(seed=seed)
        inserter, config = _make_custom_inserter(tmp_path)
        inserter.seed = seed
        inserter.rng = __import__("random").Random(seed)
        result = inserter.place_random(interface, n_molecules=5)

        # Water count must match the golden baseline.
        assert result.water_nmolecules == expected_water, (
            f"seed={seed}: water_nmolecules mismatch: expected {expected_water}, "
            f"got {result.water_nmolecules}"
        )
        # Ice is unchanged.
        assert result.ice_atom_count == 60, (
            f"seed={seed}: ice_atom_count mismatch: expected 60, "
            f"got {result.ice_atom_count}"
        )
        # Custom molecules: 5 * 3 atoms = 15.
        assert result.custom_molecule_atom_count == 15, (
            f"seed={seed}: custom_molecule_atom_count mismatch: expected 15, "
            f"got {result.custom_molecule_atom_count}"
        )
        assert result.custom_molecule_count == 5, (
            f"seed={seed}: custom_molecule_count mismatch: expected 5, "
            f"got {result.custom_molecule_count}"
        )
        # SHA256 of the full positions array must match the golden baseline.
        actual_sha = _sha256(result.positions)
        assert actual_sha == expected_sha, (
            f"seed={seed}: positions SHA256 mismatch: expected {expected_sha}, "
            f"got {actual_sha}. The pre-allocate + batch refactor changed the "
            f"placement decisions — byte-equivalence is broken."
        )

    @pytest.mark.parametrize("seed", [7, 77, 777])
    def test_custom_inserter_reproducible_across_instances(self, seed, tmp_path):
        """Same seed -> identical output across independent instances."""
        interface_a = _build_seeded_interface(seed=seed)
        interface_b = _build_seeded_interface(seed=seed)
        inserter_a, config = _make_custom_inserter(tmp_path)
        inserter_a.seed = seed
        inserter_a.rng = __import__("random").Random(seed)
        # Need a fresh tmp_path for the second inserter (GRO/ITP files can be
        # the same content but the inserter reads them at construction).
        inserter_b, _ = _make_custom_inserter(tmp_path)
        inserter_b.seed = seed
        inserter_b.rng = __import__("random").Random(seed)
        result_a = inserter_a.place_random(interface_a, n_molecules=5)
        result_b = inserter_b.place_random(interface_b, n_molecules=5)
        np.testing.assert_array_equal(result_a.positions, result_b.positions)
        assert result_a.water_nmolecules == result_b.water_nmolecules
        assert result_a.custom_molecule_count == result_b.custom_molecule_count
