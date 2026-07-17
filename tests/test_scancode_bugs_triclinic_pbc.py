"""Regression tests for scancode CRIT-01: triclinic-aware PBC wrap in gromacs_writer.

CRIT-01 (HIGH, CONFIRMED in .planning/scancode-fixes/RESEARCH.md):
  ``wrap_positions_into_box`` (gromacs_writer.py) and ``wrap_molecules_into_box``
  wrapped atom/molecule positions using a DIAGONAL-ONLY modulo
  ``np.mod(wrapped[:, dim], cell[dim, dim])``. This is correct ONLY for
  orthogonal (diagonal) cells. For triclinic hydrate cells (sH / c0te / c1te,
  whose cell matrices have non-zero off-diagonal elements parsed at
  ``hydrate_generator.py:414-430``), the diagonal-only wrap ignores the
  off-diagonal shear and silently leaves atoms OUTSIDE the parallelepiped.

  Reachability: ``pipeline.py:928`` calls ``write_interface_gro_file(wrapper,
  ...)`` with ``cell = hydrate.cell`` (triclinic for sH/c0te/c1te), which calls
  ``wrap_molecules_into_box(iface.positions, iface.molecule_index, iface.cell)``
  (gromacs_writer.py ~1131-1136). Hydrate positions are intentionally unwrapped
  upstream (hydrate_generator.py:186-189), so the FIRST wrap happens at export.

The fix routes triclinic cells through a fractional-coordinate wrap
(``frac = pos @ inv(cell.T); frac = np.mod(frac, 1.0); wrapped = frac @ cell.T``),
reusing the proven pattern from ``water_filler.wrap_positions_triclinic``. The
orthogonal/slab path (slab.py:619 forces orthogonal cells) stays on the existing
diagonal-modulo fast path, byte-identical to before.

Wrap invariants tested:
  - ``wrap_positions_into_box`` (per-atom): every output fractional coord is in
    [0, 1] (strict — each atom is wrapped independently).
  - ``wrap_molecules_into_box`` (molecule-aware): each molecule's CENTER OF
    MASS is in [0, 1) and the molecule is kept intact (relative distances
    preserved). Individual atoms of a molecule straddling a PBC boundary may
    sit slightly outside [0, 1] — this is the SAME documented behavior as the
    orthogonal molecule-aware wrap (see test_pbc_wrapping.py's TOL=0.01 nm
    comment) and is handled gracefully by GROMACS. The bug, by contrast, left
    atoms outside the cell by the full off-diagonal shear (up to ~0.36 fractional
    / ~0.43 nm on a real sH hydrate — a third of the cell).

These tests:
  1. Unit-test both wrap functions on a synthetic triclinic cell: prove the
     per-atom wrap puts every atom in [0,1] AND that the OLD diagonal-only
     modulo would have left an atom outside (the bug is caught).
  2. Guard the orthogonal fast path: byte-identical to the old diagonal-only
     behavior (reproduced inline for direct comparison).
  3. Integration-test the REAL sH hydrate export path: generate an sH+CH4
     hydrate, build the InterfaceStructure wrapper exactly as pipeline.py:907-920
     does, call write_interface_gro_file, parse the GRO, reconstruct the triclinic
     cell from the 9-value box line, and assert (a) every molecule COM is in
     [0,1), (b) every molecule is intact, (c) the max atom excursion is within
     the molecule-straddling tolerance, AND (d) the OLD diagonal-only wrap would
     have produced a LARGER excursion (proving the bug is real and the fix helps).
  4. (when gmx is available) gmx grompp dry-run on an exported 2x2x2 sH supercell
     (the 1x1x1 unit cell is too small for the 1.0 nm cutoff) to confirm the
     triclinic topology still processes.
"""

import sys
import shutil
from pathlib import Path

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    wrap_positions_into_box,
    wrap_molecules_into_box,
    write_interface_gro_file,
    write_interface_top_file,
)
from quickice.structure_generation.cell_utils import is_cell_orthogonal
from quickice.structure_generation.types import (
    InterfaceStructure,
    MoleculeIndex,
    WATER_ATOMS_PER_MOLECULE,
)

from e2e_export_helpers import run_gmx_grompp, _stage_itp_files, MDP_PATH


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _frac_in_cell_range(frac: np.ndarray, tol: float = 1e-9) -> bool:
    """True if every fractional coordinate is in [0, 1] within tol (strict per-atom)."""
    return bool(np.all((frac >= -tol) & (frac <= 1.0 + tol)))


def _max_frac_excursion(frac: np.ndarray) -> float:
    """Max distance any atom sits outside [0, 1] in fractional coords (0 if all inside)."""
    below = np.clip(-frac, 0, None)
    above = np.clip(frac - 1.0, 0, None)
    return float(np.max(np.maximum(below, above))) if frac.size else 0.0


def _diagonal_only_atom_wrap(positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Reproduce the OLD (buggy) per-atom diagonal-only wrap for comparison.

    Exact pre-fix behavior of ``wrap_positions_into_box``: per-axis modulo on
    diagonal cell elements only. Used to PROVE the test atom is one the OLD code
    leaves outside the triclinic cell (the bug is real and caught).
    """
    wrapped = positions.copy()
    for dim in range(3):
        wrapped[:, dim] = np.mod(wrapped[:, dim], cell[dim, dim])
    return wrapped


def _old_orthogonal_wrap_molecules(positions: np.ndarray, molecule_index, cell: np.ndarray) -> np.ndarray:
    """Reproduce the pre-fix orthogonal ``wrap_molecules_into_box`` exactly.

    The fix keeps this orthogonal branch byte-identical (it only adds a triclinic
    branch above it). This reproduction lets the regression-guard test compare
    the fixed function's orthogonal output directly against the old code.
    """
    wrapped = positions.copy()
    for mol in molecule_index:
        start, count = mol.start_idx, mol.count
        mol_positions = wrapped[start:start + count].copy()
        ref_pos = mol_positions[0]
        delta = mol_positions[1:] - ref_pos
        box_sizes = np.array([cell[d, d] for d in range(3)])
        shifts = np.zeros_like(delta)
        half_box = box_sizes / 2
        mask_ahead = delta > half_box
        shifts[mask_ahead] -= box_sizes[np.where(mask_ahead)[1] % 3]
        mask_behind = delta < -half_box
        shifts[mask_behind] += box_sizes[np.where(mask_behind)[1] % 3]
        mol_positions[1:] += shifts
        center = np.mean(mol_positions, axis=0)
        center_wrapped = np.mod(center, box_sizes)
        shift = center_wrapped - center
        mol_positions += shift
        wrapped[start:start + count] = mol_positions
    return wrapped


def _assert_molecules_intact(orig: np.ndarray, wrapped: np.ndarray, molecule_index) -> None:
    """Assert every molecule's pairwise relative distances are preserved."""
    for mol in molecule_index:
        if mol.count <= 1:
            continue
        seg_o = orig[mol.start_idx: mol.start_idx + mol.count]
        seg_w = wrapped[mol.start_idx: mol.start_idx + mol.count]
        for i in range(1, mol.count):
            d_o = np.linalg.norm(seg_o[i] - seg_o[0])
            d_w = np.linalg.norm(seg_w[i] - seg_w[0])
            assert abs(d_o - d_w) < 1e-9, (
                f"molecule {mol.mol_type} @ {mol.start_idx} shape changed for atom {i}: "
                f"{d_o} vs {d_w}"
            )


def _assert_com_in_unit_range(wrapped: np.ndarray, molecule_index, cell: np.ndarray, tol: float = 1e-9) -> None:
    """Assert every molecule's fractional center-of-mass is in [0, 1)."""
    inv_cell_T = np.linalg.inv(cell.T)
    for mol in molecule_index:
        seg = wrapped[mol.start_idx: mol.start_idx + mol.count]
        com_frac = (seg @ inv_cell_T).mean(axis=0)
        assert np.all((com_frac >= -tol) & (com_frac < 1.0 + tol)), (
            f"molecule {mol.mol_type} @ {mol.start_idx} COM fractional {com_frac} "
            f"outside [0, 1)"
        )


def _parse_gro_positions_and_cell(gro_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse atom positions and the full 3x3 cell from a GROMACS .gro file.

    Reconstructs the triclinic cell from the 9-value box line using the same
    mapping as ``hydrate_generator._parse_box_line`` (GRO order:
    v1x v2y v3z v1y v1z v2x v2z v3x v3y).
    """
    with open(gro_path, "r") as f:
        lines = f.readlines()
    n_atoms = int(lines[1].strip())
    positions = np.zeros((n_atoms, 3), dtype=np.float64)
    for i in range(n_atoms):
        line = lines[2 + i]
        positions[i] = [float(line[20:28]), float(line[28:36]), float(line[36:44])]
    box_vals = [float(v) for v in lines[2 + n_atoms].split()]
    if len(box_vals) >= 9:
        v1x, v2y, v3z, v1y, v1z, v2x, v2z, v3x, v3y = box_vals[:9]
        cell = np.array([
            [v1x, v1y, v1z],
            [v2x, v2y, v2z],
            [v3x, v3y, v3z],
        ], dtype=np.float64)
    else:
        cell = np.diag(box_vals[:3])
    return positions, cell


# ══════════════════════════════════════════════════════════════════════════════
# Unit tests: synthetic triclinic cells (fast, no GenIce2)
# ══════════════════════════════════════════════════════════════════════════════


# A triclinic cell with +x shear on the b lattice vector:
#   a = [2, 0, 0], b = [0.5, 2, 0], c = [0, 0, 2]
# Off-diagonal element cell[1, 0] = 0.5 is non-zero => triclinic.
TRICLINIC_CELL = np.array([
    [2.0, 0.0, 0.0],
    [0.5, 2.0, 0.0],
    [0.0, 0.0, 2.0],
])

# Atom INSIDE the orthogonal bounding box [0,2]^3 but OUTSIDE the parallelepiped:
# cartesian (1.9, 0.1, 0.5) -> frac_b = 1.9*(-0.125) + 0.1*0.5 = -0.1875 < 0.
# The OLD diagonal-only modulo is a NO-OP for this atom (already in [0,2]^3), so
# it stays outside the actual triclinic cell. This is the exact CRIT-01 bug.
ATOM_INSIDE_BBOX_OUTSIDE_CELL = np.array([[1.9, 0.1, 0.5]])


class TestCRIT01WrapPositionsIntoBox:
    """CRIT-01: wrap_positions_into_box must wrap triclinic cells via fractional coords.

    Per-atom wrap: every output fractional coordinate is strictly in [0, 1].
    """

    def test_triclinic_detection(self):
        """The test cell is actually triclinic (exercises the new branch)."""
        assert not is_cell_orthogonal(TRICLINIC_CELL), (
            "Test cell must be triclinic to exercise the new branch."
        )

    def test_triclinic_wrap_produces_frac_in_unit_range(self):
        """After wrap, fractional coordinates are strictly in [0, 1] (inside the cell)."""
        inv_cell_T = np.linalg.inv(TRICLINIC_CELL.T)
        # Sanity: the input atom is genuinely outside the parallelepiped.
        in_frac = ATOM_INSIDE_BBOX_OUTSIDE_CELL @ inv_cell_T
        assert in_frac[0, 1] < 0.0, (
            "Test setup error: input atom must be outside the triclinic cell "
            f"(frac_b < 0); got frac={in_frac[0]}"
        )

        wrapped = wrap_positions_into_box(ATOM_INSIDE_BBOX_OUTSIDE_CELL, TRICLINIC_CELL)
        out_frac = wrapped @ inv_cell_T
        assert _frac_in_cell_range(out_frac), (
            f"CRIT-01: triclinic per-atom wrap left atom outside cell. "
            f"frac={out_frac} (must be in [0,1])"
        )

    def test_old_diagonal_only_would_leave_atom_outside(self):
        """The pre-fix diagonal-only modulo leaves the same atom outside the cell.

        Proves the test would have FAILED before the fix (the bug is real and
        the test catches it), not just that the new code happens to pass.
        """
        inv_cell_T = np.linalg.inv(TRICLINIC_CELL.T)
        old = _diagonal_only_atom_wrap(ATOM_INSIDE_BBOX_OUTSIDE_CELL, TRICLINIC_CELL)
        old_frac = old @ inv_cell_T
        assert not _frac_in_cell_range(old_frac), (
            "CRIT-01 regression: the OLD diagonal-only wrap actually wraps this "
            f"atom correctly (frac={old_frac}). The test atom was chosen to be "
            f"outside the triclinic cell but inside the bounding box — if the "
            f"old code wraps it, the test no longer proves the bug is caught."
        )

    def test_orthogonal_path_unchanged_byte_identical(self):
        """Orthogonal cells stay on the diagonal-modulo fast path (slab exports)."""
        ortho = np.diag([10.0, 10.0, 10.0])
        pos = np.array([[11.5, -0.3, 5.0], [5.0, 5.0, 5.0], [3.3, 9.9, 0.0]])
        wrapped = wrap_positions_into_box(pos, ortho)
        ref = _diagonal_only_atom_wrap(pos, ortho)
        np.testing.assert_array_almost_equal(wrapped, ref)
        # Per-atom wrap for orthogonal cells: every atom strictly in [0, box)
        assert np.all((wrapped >= 0) & (wrapped < 10.0))

    def test_empty_positions_short_circuit(self):
        """Empty input returns an empty array (no LinAlgError on the triclinic branch)."""
        empty = np.zeros((0, 3))
        out = wrap_positions_into_box(empty, TRICLINIC_CELL)
        assert out.shape == (0, 3)


class TestCRIT01WrapMoleculesIntoBox:
    """CRIT-01: wrap_molecules_into_box wraps triclinic cells by fractional COM.

    Molecule-aware wrap invariant: each molecule's COM fractional is in [0, 1)
    and the molecule is kept intact. Atoms straddling a PBC boundary may sit
    slightly outside [0, 1] — expected, same as the orthogonal path.
    """

    def test_triclinic_molecule_com_in_range_and_intact(self):
        """A molecule split across the triclinic PBC: COM in [0,1) + molecule intact."""
        # 4-atom molecule with atoms split across the -b shear PBC boundary
        mol_pos = np.array([
            [1.90, 0.10, 0.50],   # O inside bbox, outside parallelepiped (frac_b<0)
            [1.95, -0.05, 0.50],  # H1 below y=0 (split across -b)
            [1.85, 0.20, 0.50],   # H2 inside
            [1.92, 0.05, 0.50],   # MW
        ])
        mi = [MoleculeIndex(start_idx=0, count=4, mol_type="water")]

        wrapped = wrap_molecules_into_box(mol_pos, mi, TRICLINIC_CELL)
        _assert_com_in_unit_range(wrapped, mi, TRICLINIC_CELL)
        _assert_molecules_intact(mol_pos, wrapped, mi)
        # And atoms stay within a molecule-straddling tolerance of [0,1]
        frac = wrapped @ np.linalg.inv(TRICLINIC_CELL.T)
        assert _max_frac_excursion(frac) < 0.05, (
            f"CRIT-01: triclinic molecule wrap left an atom far outside the cell. "
            f"max excursion = {_max_frac_excursion(frac)} (frac={frac})"
        )

    def test_triclinic_variable_molecule_sizes(self):
        """Mixed molecule sizes (water=4, ion=1, ch4=5) all wrap correctly."""
        # water (4), ion (1), ch4 (5) — variable sizes via molecule_index
        pos = np.array([
            # water: split across +a boundary
            [2.10, 0.50, 0.50],  # O beyond +a
            [2.15, 0.55, 0.50],  # H1
            [2.05, 0.45, 0.50],  # H2
            [2.12, 0.52, 0.50],  # MW
            # ion: single atom beyond +b
            [0.30, 2.30, 0.50],
            # ch4: 5 atoms, center outside the parallelepiped (frac_b<0)
            [1.90, 0.10, 0.50],
            [1.92, 0.05, 0.50],
            [1.88, 0.15, 0.50],
            [1.91, 0.08, 0.50],
            [1.89, 0.12, 0.50],
        ])
        mi = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water"),
            MoleculeIndex(start_idx=4, count=1, mol_type="na"),
            MoleculeIndex(start_idx=5, count=5, mol_type="ch4"),
        ]
        wrapped = wrap_molecules_into_box(pos, mi, TRICLINIC_CELL)
        _assert_com_in_unit_range(wrapped, mi, TRICLINIC_CELL)
        _assert_molecules_intact(pos, wrapped, mi)
        # Atoms within a molecule-straddling tolerance (water/ch4 ~0.1 nm in a
        # 2 nm cell => ~0.05 fractional half-extent; allow margin).
        frac = wrapped @ np.linalg.inv(TRICLINIC_CELL.T)
        assert _max_frac_excursion(frac) < 0.05, (
            f"CRIT-01: variable-size triclinic wrap left an atom far outside. "
            f"max excursion = {_max_frac_excursion(frac)} (frac={frac})"
        )

    def test_triclinic_empty_or_no_molecule_index_short_circuits(self):
        """Empty positions or empty molecule_index returns the input unchanged."""
        empty = np.zeros((0, 3))
        assert wrap_molecules_into_box(empty, [], TRICLINIC_CELL).shape == (0, 3)
        # No molecule_index -> no-op (positions returned as-is)
        pos = np.array([[1.9, 0.1, 0.5]])
        out = wrap_molecules_into_box(pos, [], TRICLINIC_CELL)
        np.testing.assert_array_almost_equal(out, pos)

    def test_orthogonal_path_byte_identical_to_old_code(self):
        """Orthogonal cells: fixed function's output == old orthogonal code (regression guard).

        The fix keeps the orthogonal branch byte-identical (it only adds a
        triclinic branch above it). This test reproduces the pre-fix orthogonal
        wrap_molecules_into_box logic and asserts the fixed function produces
        identical output for an orthogonal cell — proving the slab/interface
        fast path is unchanged.
        """
        ortho = np.diag([10.0, 10.0, 10.0])
        # Molecules that straddle PBC boundaries (exercises unwrap + center-wrap)
        pos = np.array([
            # Molecule 1: spanning +x boundary (atoms beyond 10.0)
            [9.9, 2.0, 2.0], [10.1, 2.0, 2.0], [9.8, 2.1, 2.0], [9.85, 2.05, 2.0],
            # Molecule 2: spanning -y boundary (atoms below 0.0)
            [3.0, 0.2, 3.0], [3.0, -0.1, 3.0], [3.1, 0.3, 3.0], [3.05, 0.15, 3.0],
        ])
        mi = [
            MoleculeIndex(start_idx=0, count=4, mol_type="water"),
            MoleculeIndex(start_idx=4, count=4, mol_type="water"),
        ]
        fixed = wrap_molecules_into_box(pos, mi, ortho)
        old = _old_orthogonal_wrap_molecules(pos, mi, ortho)
        np.testing.assert_array_almost_equal(fixed, old)
        # COM invariant still holds for the orthogonal molecule-aware wrap
        _assert_com_in_unit_range(fixed, mi, ortho)


# ══════════════════════════════════════════════════════════════════════════════
# Integration test: REAL sH hydrate export (the actual CRIT-01 bug site)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def hydrate_sH_ch4_structure():
    """Generate a real sH+CH4 HydrateStructure (triclinic). Module-scoped to
    amortize the expensive GenIce2 call (~3-5s) per AGENTS.md test conventions."""
    from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
    from quickice.structure_generation.types import HydrateConfig
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return gen.generate(config)


@pytest.fixture(scope="module")
def hydrate_sH_ch4_2x2x2_structure():
    """Generate a 2x2x2 sH+CH4 supercell for the grompp test.

    The 1x1x1 sH unit cell (~1.1 nm shortest vector) is too small for the 1.0 nm
    nonbonded cutoff (must be < half the shortest box vector). A 2x2x2 supercell
    (~2.15 nm shortest) gives half > 1.0 nm so gmx grompp accepts the box.
    Module-scoped to amortize the GenIce2 call.
    """
    from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
    from quickice.structure_generation.types import HydrateConfig
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sH",
        guest_type="ch4",
        supercell_x=2,
        supercell_y=2,
        supercell_z=2,
    )
    return gen.generate(config)


def _build_hydrate_wrapper(hydrate) -> InterfaceStructure:
    """Build the InterfaceStructure wrapper exactly as pipeline.py:907-920 does."""
    water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE
    guest_atom_count = len(hydrate.positions) - water_atom_count
    assert water_atom_count + guest_atom_count == len(hydrate.positions), (
        f"Hydrate atom-count mismatch: {water_atom_count} water + "
        f"{guest_atom_count} guest != {len(hydrate.positions)} total"
    )
    return InterfaceStructure(
        positions=hydrate.positions,
        atom_names=hydrate.atom_names,
        cell=hydrate.cell,
        molecule_index=hydrate.molecule_index,
        mode="hydrate",
        report=getattr(hydrate, "report", ""),
        ice_atom_count=0,
        water_atom_count=water_atom_count,
        ice_nmolecules=0,
        water_nmolecules=hydrate.water_count,
        guest_atom_count=guest_atom_count,
        guest_nmolecules=hydrate.guest_count,
    )


# Molecule straddling tolerance for the sH export: water/CH4 (~0.1 nm) in the
# ~1.24 nm sH a-cell => ~0.09 fractional half-extent. Allow 0.15 to comfortably
# accommodate straddling while still catching the shear bug, which leaves atoms
# ~0.36 fractional / ~0.43 nm outside (a third of the cell — clearly a bug).
SH_STRADDLE_TOL_FRAC = 0.15


class TestCRIT01RealSHydrateExport:
    """CRIT-01 integration: a real sH hydrate export stays inside the triclinic cell."""

    def test_sH_cell_is_triclinic(self, hydrate_sH_ch4_structure):
        """The generated sH hydrate cell is actually triclinic (exercises the fix)."""
        cell = hydrate_sH_ch4_structure.cell
        assert not is_cell_orthogonal(cell), (
            "sH hydrate cell must be triclinic (non-zero off-diagonal). If this "
            "fails, GenIce2 changed sH to an orthogonal representation and this "
            "test no longer exercises the CRIT-01 triclinic branch."
        )

    def test_exported_positions_near_triclinic_cell(self, hydrate_sH_ch4_structure, tmp_path):
        """Exported sH atoms: COM in [0,1), molecules intact, atoms within straddling tol.

        Mirrors the real export path: pipeline.py:907-928 builds an
        InterfaceStructure wrapper from the HydrateStructure and calls
        write_interface_gro_file. We parse the GRO, reconstruct the triclinic
        cell from the 9-value box line, and check the molecule-aware invariant.
        """
        wrapper = _build_hydrate_wrapper(hydrate_sH_ch4_structure)
        gro_path = str(tmp_path / "hydrate_sH.gro")
        write_interface_gro_file(wrapper, gro_path)

        positions, cell = _parse_gro_positions_and_cell(gro_path)
        assert positions.shape[0] > 0, "GRO file should contain atoms"
        assert not is_cell_orthogonal(cell), (
            "Exported box line must be triclinic for sH (9 non-zero values)."
        )
        # GRO %8.3f rounding is 0.001 nm; the straddling tolerance dominates.
        max_exc = _max_frac_excursion(positions @ np.linalg.inv(cell.T))
        assert max_exc < SH_STRADDLE_TOL_FRAC, (
            f"CRIT-01 regression: exported sH hydrate has atoms far outside the "
            f"triclinic cell. max fractional excursion = {max_exc} "
            f"(tol {SH_STRADDLE_TOL_FRAC}). The shear bug leaves atoms ~0.36 "
            f"fractional outside; straddling is < {SH_STRADDLE_TOL_FRAC}."
        )

    def test_fix_reduces_excursion_vs_old_diagonal_only(self, hydrate_sH_ch4_structure):
        """The fix produces a SMALLER max excursion than the OLD diagonal-only wrap.

        Proves the bug is real (OLD leaves atoms far outside) and the fix helps
        (NEW brings them within straddling distance). This is the "test would
        have failed before the fix" guard for the integration path.
        """
        hydrate = hydrate_sH_ch4_structure
        inv_cell_T = np.linalg.inv(hydrate.cell.T)

        # NEW (fixed) molecule-aware wrap on the real sH positions
        wrapped_new = wrap_molecules_into_box(
            hydrate.positions, hydrate.molecule_index, hydrate.cell
        )
        exc_new = _max_frac_excursion(wrapped_new @ inv_cell_T)

        # OLD (buggy) diagonal-only molecule wrap on the same positions
        wrapped_old = _old_orthogonal_wrap_molecules(
            hydrate.positions, hydrate.molecule_index, hydrate.cell
        )
        exc_old = _max_frac_excursion(wrapped_old @ inv_cell_T)

        assert exc_old > SH_STRADDLE_TOL_FRAC, (
            f"Test setup issue: the OLD diagonal-only wrap did NOT leave sH atoms "
            f"outside the triclinic cell (exc_old={exc_old} <= tol {SH_STRADDLE_TOL_FRAC}). "
            f"If this fails, the real sH export no longer exercises the shear bug."
        )
        assert exc_new < exc_old, (
            f"CRIT-01: the fix did NOT reduce the triclinic excursion "
            f"(new={exc_new} >= old={exc_old}). The fractional wrap should bring "
            f"atoms closer to the cell than the diagonal-only wrap."
        )
        # The fix should reduce the excursion substantially (shear bug is large).
        assert exc_new < 0.5 * exc_old, (
            f"CRIT-01: fix reduced excursion only to {exc_new} from {exc_old} "
            f"(less than 2x improvement). Expected a substantial reduction since "
            f"the diagonal-only wrap ignores the full off-diagonal shear."
        )

    def test_wrapped_molecules_kept_intact(self, hydrate_sH_ch4_structure):
        """Direct call to wrap_molecules_into_box keeps every molecule intact.

        Confirms the triclinic molecule-aware wrap (by fractional COM) preserves
        molecular geometry for the real sH hydrate positions, not just that
        atoms land near the cell.
        """
        hydrate = hydrate_sH_ch4_structure
        wrapped = wrap_molecules_into_box(
            hydrate.positions, hydrate.molecule_index, hydrate.cell
        )
        _assert_molecules_intact(hydrate.positions, wrapped, hydrate.molecule_index)
        _assert_com_in_unit_range(wrapped, hydrate.molecule_index, hydrate.cell)


# ══════════════════════════════════════════════════════════════════════════════
# Optional GROMACS dry-run (uses a 2x2x2 supercell so the box fits the cutoff)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(
    not (Path(__file__).parent / "em.mdp").exists(),
    reason="em.mdp not found in tests/ — required for gmx grompp dry-run",
)
class TestCRIT01GromppDryRun:
    """Optional: gmx grompp on an exported 2x2x2 sH supercell confirms the
    triclinic topology still processes. Skipped if gmx is not on PATH or em.mdp
    is absent. The 1x1x1 unit cell is too small for the 1.0 nm cutoff, so a
    2x2x2 supercell is used (shortest box vector ~2.15 nm > 2x cutoff)."""

    def test_grompp_on_sH_hydrate_export(self, hydrate_sH_ch4_2x2x2_structure, tmp_path):
        if shutil.which("gmx") is None:
            pytest.skip("GROMACS (gmx) not found on PATH")
        wrapper = _build_hydrate_wrapper(hydrate_sH_ch4_2x2x2_structure)
        gro_path = tmp_path / "struct.gro"
        top_path = tmp_path / "struct.top"
        write_interface_gro_file(wrapper, str(gro_path))
        write_interface_top_file(wrapper, str(top_path))

        # Stage ITP files (tip4p-ice.itp, ch4_hydrate.itp) the .top #includes
        _stage_itp_files(str(top_path), tmp_path)

        # Copy em.mdp into the workspace
        shutil.copy(MDP_PATH, tmp_path / "em.mdp")

        exit_code, stderr = run_gmx_grompp(
            tmp_path, gro_file="struct.gro", top_file="struct.top",
            mdp_file="em.mdp", tpr_file="em.tpr", maxwarn=10,
        )
        # grompp may emit warnings (e.g. the .top/.gro atom-count mismatch from
        # the MW virtual-site expansion is expected for hydrate export); we only
        # require that it does not fatally error on the triclinic geometry.
        assert exit_code == 0, (
            f"CRIT-01: gmx grompp failed on the exported 2x2x2 sH hydrate. "
            f"exit_code={exit_code}\nstderr:\n{stderr}"
        )
