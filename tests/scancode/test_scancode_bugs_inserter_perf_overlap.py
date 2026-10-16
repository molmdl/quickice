"""Scancode perf gate: 48.4 vectorization of the SUSP-06 COM-COM overlap scan.

Audit Finding 2 (Level-1 performance): the ``place_custom`` COM-COM overlap
warning scan at ``custom_molecule_inserter.py:1090-1110`` was an O(n^2)
pure-Python double loop measured at ~117 s (116.95 s isolated loop) at the
``MAX_CSV_ROWS = 10000`` custom-placement CSV cap, stalling the CLI ~2 minutes
for a heuristic *warning-only* notice. The 48.4 fix replaces it with a
finite-filtered ``cKDTree.count_neighbors`` self-query (~11 ms for the scan,
~1-2 s total for ``place_custom``), with O(1) memory even on adversarial
all-identical-points inputs.

Gate ceilings (generous for CI jitter, per the scorer-perf precedent —
``tests/test_scorer_performance.py`` — which uses equivalence + memory
assertions, never tight wall clocks):

- Wall ceiling: 30 s for the full ``place_custom`` at n=10,000. Expected
  post-fix ~1-2 s (linear placement loop + tree build); an O(n^2) regression
  takes ~117 s and fails loudly. Ceiling >= 10x headroom per research
  pitfall 13.
- Memory ceiling: 100 MB peak (tracemalloc — deterministic, jitter-free).
  Expected a few MB; a ``pdist`` regression measured 400 MB transient and
  fails this gate deterministically.

The fixture builders mirror the minimal 3-atom pattern from
``tests/scancode/test_scancode_bugs_inserter_perf.py`` — defined locally
(test-prefixed modules are not importable).
"""

import time
import tracemalloc

import numpy as np

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
)
from quickice.structure_generation.custom_molecule_inserter import (
    CustomMoleculeInserter,
)


def _make_custom_inserter(tmp_path, min_separation=0.3):
    """Build a minimal CustomMoleculeInserter backed by temp .gro/.itp files.

    Same 3-atom C1+2H template pattern as the other scancode inserter fixtures
    (``place_custom`` reads the template via ``parse_gro_file`` in the
    constructor, so real files are required). ``placement_mode="custom"`` with
    placeholder positions/rotations that are overridden per call.
    """
    gro_path = tmp_path / "perf_overlap_test.gro"
    gro_path.write_text(
        "PERF overlap test\n"
        "    3\n"
        "    1MOL    C1    1   0.000   0.000   0.000\n"
        "    1MOL    H1    2   0.150   0.000   0.000\n"
        "    1MOL    H2    3  -0.150   0.000   0.000\n"
        "   5.0  5.0  5.0\n"
    )
    itp_path = tmp_path / "perf_overlap_test.itp"
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
        placement_mode="custom",
        gro_path=gro_path,
        itp_path=itp_path,
        positions=[(0.0, 0.0, 0.0)],
        rotations=[(0.0, 0.0, 0.0)],
        min_separation=min_separation,
    )
    return CustomMoleculeInserter(config)


def _make_minimal_interface(cell_diag=10.0):
    """Build a minimal InterfaceStructure with no ice/water/guests.

    ``place_custom`` only reads ``.cell``, atom counts, ``.positions``,
    ``.atom_names``, ``*_nmolecules`` and ``.molecule_index`` from the
    structure, so an empty structure suffices for the perf gate.
    """
    return InterfaceStructure(
        positions=np.zeros((0, 3), dtype=np.float64),
        atom_names=[],
        cell=np.eye(3) * cell_diag,
        ice_atom_count=0,
        water_atom_count=0,
        ice_nmolecules=0,
        water_nmolecules=0,
        mode="slab",
        report="",
    )


_N_ROWS = 10_000  # the MAX_CSV_ROWS custom-placement CSV cap


def _10k_fixture():
    """Seeded n=10,000 placement fixture (positions in a 50 nm box; some pairs
    will be closer than min_separation, so the scan actually counts pairs)."""
    rng = np.random.default_rng(42)
    positions = rng.uniform(0.0, 50.0, (_N_ROWS, 3)).tolist()
    rotations = [(0.0, 0.0, 0.0)] * _N_ROWS
    return positions, rotations


def test_place_custom_10k_wall_ceiling(tmp_path):
    """Wall-perf gate: the full ``place_custom`` at the 10,000-row CSV cap must
    complete well under 30 s. Pre-fix observed ~117 s (the O(n^2) scan
    dominates); post-fix expected ~1-2 s. The 30 s ceiling gives >= 10x
    headroom for CI jitter while still failing loudly on an O(n^2) regression.
    """
    inserter = _make_custom_inserter(tmp_path)
    iface = _make_minimal_interface()
    positions, rotations = _10k_fixture()

    start = time.perf_counter()
    inserter.place_custom(iface, positions=positions, rotations=rotations)
    elapsed = time.perf_counter() - start
    print(f"place_custom n={_N_ROWS} wall time: {elapsed:.2f}s (ceiling 30s)")

    assert elapsed < 30.0, (
        f"place_custom took {elapsed:.2f}s at n={_N_ROWS} (ceiling 30.0s) — "
        "suspected O(n^2) COM-COM overlap-scan regression (pre-48.4 measured "
        "~117s; post-48.4 expected ~1-2s)"
    )


def test_place_custom_10k_memory_ceiling(tmp_path):
    """Memory-perf gate: peak traced memory for the full ``place_custom`` at
    n=10,000 must stay under ~100 MB. Expected a few MB — a ``pdist``
    regression measured 400 MB transient and fails this gate deterministically
    (tracemalloc is jitter-free, unlike wall clocks).
    """
    inserter = _make_custom_inserter(tmp_path)
    iface = _make_minimal_interface()
    positions, rotations = _10k_fixture()

    tracemalloc.start()
    inserter.place_custom(iface, positions=positions, rotations=rotations)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    peak_mb = peak / (1024 * 1024)
    print(f"place_custom n={_N_ROWS} peak traced memory: {peak_mb:.2f}MB (ceiling 100MB)")

    assert peak < 100 * 1024 * 1024, (
        f"place_custom peak traced memory {peak_mb:.2f}MB at n={_N_ROWS} "
        "(ceiling 100MB) — suspected pdist/pair-set regression "
        "(pdist measured ~400MB transient; query_pairs materializes ~50M "
        "tuples on adversarial inputs)"
    )
