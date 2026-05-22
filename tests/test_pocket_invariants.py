"""Test structural invariants for pocket mode after overlap removal.

Verifies that the FRAG-02 assertions added to pocket.py hold:
1. Water atom count divisible by 4 after each overlap removal phase
2. Atom names length matches positions length after each overlap removal phase

These tests call assemble_pocket() end-to-end with various configurations
to ensure the assertions are triggered and pass under normal operation.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.pocket import assemble_pocket


def create_mock_ice_candidate(n_molecules: int = 96, cell_dim: float = 0.9) -> Candidate:
    """Create a mock Ice Ih candidate with configurable molecule count and cell dimensions.

    Uses simple cubic lattice with 3 atoms per molecule (O, H, H).
    Positions are all positive within [0, cell_dim) per dimension.
    """
    grid = int(np.ceil(n_molecules ** (1/3)))
    positions = []
    atom_names = []
    spacing_x = cell_dim / grid
    spacing_y = cell_dim / grid
    spacing_z = cell_dim / grid
    for i in range(n_molecules):
        ix = i % grid
        iy = (i // grid) % grid
        iz = i // (grid * grid)
        x = ix * spacing_x
        y = iy * spacing_y
        z = iz * spacing_z
        positions.extend([
            [x, y, z],
            [x + 0.1, y, z + 0.05],
            [x + 0.05, y + 0.1, z + 0.1]
        ])
        atom_names.extend(["O", "H", "H"])

    positions = np.array(positions)
    cell = np.diag([cell_dim, cell_dim, cell_dim])

    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_molecules,
        phase_id="ice_ih",
        seed=42,
        metadata={"temperature": 273.15, "pressure": 0.101325}
    )


def create_mock_hydrate_candidate(n_water: int = 32, n_guest: int = 4, cell_dim: float = 0.9) -> Candidate:
    """Create a mock hydrate candidate with TIP4P water framework + Me guests.

    TIP4P: 4 atoms per molecule (OW, HW1, HW2, MW).
    Guests: 1 atom each (Me = united-atom methane).
    """
    grid = int(np.ceil(n_water ** (1/3)))
    positions = []
    atom_names = []
    spacing = cell_dim / grid

    for i in range(n_water):
        ix = i % grid
        iy = (i // grid) % grid
        iz = i // (grid * grid)
        x = 0.05 + ix * spacing
        y = 0.05 + iy * spacing
        z = 0.05 + iz * spacing
        positions.extend([
            [x, y, z],
            [x + 0.07, y, z + 0.05],
            [x + 0.05, y + 0.07, z + 0.03],
            [x, y + 0.15, z + 0.05]
        ])
        atom_names.extend(["OW", "HW1", "HW2", "MW"])

    for i in range(n_guest):
        x = 0.3 + (i * 0.2)
        y = 0.3 + (i * 0.2)
        z = 0.3 + (i * 0.2)
        positions.append([x, y, z])
        atom_names.append("Me")

    positions = np.array(positions)
    cell = np.diag([cell_dim, cell_dim, cell_dim])

    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id="ice_ih",
        seed=42,
        metadata={
            "temperature": 273.15,
            "pressure": 0.101325,
            "original_hydrate": True
        }
    )


class TestPocketInvariantSphere:
    """Verify assertions hold for sphere pocket shape."""

    def test_sphere_standard_diameter(self):
        """Sphere pocket with standard 1.0nm diameter — assertions must hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        # If we got here, all 3 assertion blocks passed
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_sphere_large_diameter(self):
        """Sphere pocket with 2.0nm diameter — more ice removed, assertions still hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=2.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_sphere_hydrate_candidate(self):
        """Sphere pocket with hydrate candidate — guest-water overlap assertions hold."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0


class TestPocketInvariantCubic:
    """Verify assertions hold for cubic pocket shape."""

    def test_cubic_standard_diameter(self):
        """Cubic pocket with 1.0nm diameter — assertions must hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_cubic_large_diameter(self):
        """Cubic pocket with 2.0nm diameter — more overlap boundary, assertions still hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=2.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_cubic_hydrate_candidate(self):
        """Cubic pocket with hydrate candidate — guest-water overlap assertions hold."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0


class TestPocketInvariantSizeExtremes:
    """Verify assertions hold for pocket size extremes."""

    def test_near_boundary_pocket(self):
        """Pocket diameter close to box size (4.0nm in 5.0nm box) — thin ice shell, assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=128, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=5.0, box_z=5.0,
            seed=42, pocket_diameter=4.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_small_pocket_sphere(self):
        """Small sphere pocket (0.5nm diameter) — few water molecules, assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=0.5, pocket_shape="sphere"
        )
        # Note: small pockets may produce 0 water molecules after filling + filtering
        # which is valid (0 % 4 == 0), or may raise InterfaceGenerationError
        # Either outcome means assertions work correctly
        try:
            result = assemble_pocket(candidate, config)
            assert len(result.atom_names) == len(result.positions)
            assert result.water_atom_count % 4 == 0
        except Exception as e:
            # If fill_region_with_water returns 0 molecules, we get an error — that's OK
            assert "zero" in str(e).lower() or "Water filling" in str(e) or "pocket" in str(e).lower()

    def test_small_pocket_cubic(self):
        """Small cubic pocket (0.5nm diameter) — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=0.5, pocket_shape="cubic"
        )
        try:
            result = assemble_pocket(candidate, config)
            assert len(result.atom_names) == len(result.positions)
            assert result.water_atom_count % 4 == 0
        except Exception as e:
            assert "zero" in str(e).lower() or "Water filling" in str(e) or "pocket" in str(e).lower()


class TestPocketInvariantRectangularBox:
    """Verify assertions hold for non-cubic boxes."""

    def test_rectangular_box_sphere(self):
        """Rectangular box (5x3x3) with sphere pocket — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0

    def test_rectangular_box_cubic(self):
        """Rectangular box (5x3x3) with cubic pocket — assertions hold."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0
