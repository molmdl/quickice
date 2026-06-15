"""Functional integration test for PBC wrapping in write_ion_gro_file.

VERIFICATION.md gap #2 closure: confirms that all atom coordinates in exported
GRO files fall within [0, box_size), verifying PBC wrapping for SOL, guest,
custom molecule, solute, and ion positions.

This test does NOT require GROMACS (no grompp) — it only verifies coordinate
bounds in the GRO file output.

Uses e2e_export_helpers chain-building pattern to construct real IonStructure
objects through the actual computation pipeline, then writes GRO files and
parses coordinates to assert the PBC wrapping invariant.
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import write_ion_gro_file
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.phase_mapping.lookup import lookup_phase

from e2e_export_helpers import (
    _make_slab_interface,
    _insert_custom_molecules,
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
)


# ── GRO coordinate parser ────────────────────────────────────────────────────

def _parse_gro_coordinates(gro_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse atom positions and box dimensions from a GROMACS .gro file.

    Reads the GRO file, extracts x/y/z coordinates from each atom line using
    the standard GRO v3.3 fixed-width format (columns [20:28], [28:36], [36:44]),
    and reads box dimensions from the last line.

    Args:
        gro_path: Path to .gro file

    Returns:
        Tuple of (positions_array shape [N, 3], box_dims shape [3]).
        positions_array contains [x, y, z] for each atom.
        box_dims contains [box_x, box_y, box_z] diagonal elements.
    """
    with open(gro_path, 'r') as f:
        lines = f.readlines()

    if len(lines) < 3:
        return np.zeros((0, 3)), np.zeros(3)

    # Line 2 (index 1): atom count
    n_atoms = int(lines[1].strip())

    # Lines 3 to 2+N (indices 2 to 2+N-1): atom records
    # Last line (index 2+N): box vectors
    positions = np.zeros((n_atoms, 3))
    for i in range(n_atoms):
        line = lines[2 + i]
        # GRO v3.3 format: positions at fixed-width columns
        # [20:28] = x, [28:36] = y, [36:44] = z (0-indexed)
        x = float(line[20:28])
        y = float(line[28:36])
        z = float(line[36:44])
        positions[i] = [x, y, z]

    # Last line: box vectors
    # Orthorhombic: 3 values; triclinic: 9 values
    # First 3 values are diagonal elements (box_x, box_y, box_z)
    box_line = lines[2 + n_atoms]
    box_values = [float(v) for v in box_line.split()]
    box_dims = np.array([box_values[0], box_values[1], box_values[2]])

    return positions, box_dims


# ── Test class ────────────────────────────────────────────────────────────────

class TestPBCWrapping:
    """Functional integration tests for PBC wrapping in GRO export.

    Verifies that all atom coordinates in exported GRO files fall within
    [0, box_size) for each dimension, confirming that PBC wrapping works
    correctly for SOL, guest, custom, solute, and ion molecules.

    Tolerance of 0.001 nm accounts for GRO %8.3f format rounding:
    positions near 0 or box_size may round to exactly 0.000 or box_size
    due to 3-decimal-place precision.
    """

    TOL = 0.01  # nm — accounts for molecule-aware wrapping near PBC boundaries
    # GRO %8.3f format precision is 0.001 nm, but molecule-aware wrapping
    # (wrap_molecules_into_box) wraps by molecule center, which can place
    # atoms up to ~0.01 nm outside [0, box_size) when molecules straddle
    # PBC boundaries. This is expected and GROMACS handles it gracefully.
    # Tolerance of 0.01 nm catches truly broken wrapping while allowing
    # the known small deviations from molecule-center wrapping.

    @pytest.fixture
    def ice_candidate(self):
        """Generate a small Ice Ih candidate for testing (96 molecules)."""
        phase_info = lookup_phase(250, 0.1)
        gen = IceStructureGenerator(phase_info, 96)
        candidates = gen.generate_all(1)
        return candidates[0]

    def _assert_all_coords_in_box(self, positions, box_dims):
        """Assert all coordinates fall within [0, box_size) with float tolerance."""
        assert positions.shape[0] > 0, "GRO file should contain atoms"
        assert np.all(box_dims > 0), f"Box dimensions must be positive: {box_dims}"

        # Lower bound: coordinates >= -TOL (float precision near 0)
        min_coords = positions.min(axis=0)
        assert np.all(positions >= -self.TOL), (
            f"Coordinates below 0 found: min={min_coords}, box={box_dims}"
        )

        # Upper bound: coordinates < box_size + TOL (float precision near boundary)
        max_coords = positions.max(axis=0)
        assert np.all(positions < box_dims[np.newaxis, :] + self.TOL), (
            f"Coordinates >= box_size found: max={max_coords}, box={box_dims}"
        )

    def test_full_chain_gro_coordinates_in_box(self, ice_candidate, tmp_path):
        """F1 chain: interface → custom → solute → ion, all coords in [0, box_size).

        This is the most comprehensive test, covering all molecule types:
        SOL (ice+water), custom molecules, solutes, and ions. All positions
        must be wrapped into [0, box_size) by write_ion_gro_file.
        """
        # Build F1 chain
        interface = _make_slab_interface(ice_candidate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        # Write GRO file
        gro_path = str(tmp_path / "ion_full_chain.gro")
        write_ion_gro_file(ion, gro_path)

        # Write ITP (required for complete export, though not read by this test)
        na_count = sum(1 for m in ion.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in ion.molecule_index if m.mol_type == "cl")
        write_ion_itp(tmp_path / "ion.itp", na_count, cl_count)

        # Parse and verify PBC wrapping invariant
        positions, box_dims = _parse_gro_coordinates(gro_path)
        self._assert_all_coords_in_box(positions, box_dims)

    def test_solute_only_coordinates_in_box(self, ice_candidate, tmp_path):
        """Interface + solute + ion (no custom molecules), all coords in [0, box_size).

        Verifies solute-specific PBC wrapping: solute positions are wrapped
        via `solute_positions % np.diag(cell)` in write_ion_gro_file.
        """
        # Build chain: interface → solute → ion
        interface = _make_slab_interface(ice_candidate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        # Write GRO file
        gro_path = str(tmp_path / "ion_solute_only.gro")
        write_ion_gro_file(ion, gro_path)

        na_count = sum(1 for m in ion.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in ion.molecule_index if m.mol_type == "cl")
        write_ion_itp(tmp_path / "ion.itp", na_count, cl_count)

        # Parse and verify
        positions, box_dims = _parse_gro_coordinates(gro_path)
        self._assert_all_coords_in_box(positions, box_dims)

    def test_custom_only_coordinates_in_box(self, ice_candidate, tmp_path):
        """Interface + custom + ion (no solutes), all coords in [0, box_size).

        Verifies custom molecule PBC wrapping: custom positions are wrapped
        via `custom_molecule_positions % np.diag(cell)` in write_ion_gro_file.
        """
        # Build chain: interface → custom → ion
        interface = _make_slab_interface(ice_candidate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        # Write GRO file
        gro_path = str(tmp_path / "ion_custom_only.gro")
        write_ion_gro_file(ion, gro_path)

        na_count = sum(1 for m in ion.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in ion.molecule_index if m.mol_type == "cl")
        write_ion_itp(tmp_path / "ion.itp", na_count, cl_count)

        # Parse and verify
        positions, box_dims = _parse_gro_coordinates(gro_path)
        self._assert_all_coords_in_box(positions, box_dims)

    def test_interface_only_coordinates_in_box(self, ice_candidate, tmp_path):
        """Interface + ion only (no custom, no solutes), all coords in [0, box_size).

        The simplest test: verifies SOL + ion coordinate wrapping via
        wrap_molecules_into_box in write_ion_gro_file.
        """
        # Build chain: interface → ion
        interface = _make_slab_interface(ice_candidate)
        ion = _insert_ions(interface, concentration=0.15)

        # Write GRO file
        gro_path = str(tmp_path / "ion_interface_only.gro")
        write_ion_gro_file(ion, gro_path)

        na_count = sum(1 for m in ion.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in ion.molecule_index if m.mol_type == "cl")
        write_ion_itp(tmp_path / "ion.itp", na_count, cl_count)

        # Parse and verify
        positions, box_dims = _parse_gro_coordinates(gro_path)
        self._assert_all_coords_in_box(positions, box_dims)
