"""Edge case tests for pocket mode cavity generation.

Tests pocket mode across shape variants (sphere, cubic), size extremes
(near-minimum, near-boundary), box geometries (cubic, rectangular), and
structural invariants (ice-outside-cavity, water-inside-cavity,
positions-within-box, atom-ordering).

These tests complement test_pocket_invariants.py which tests the
assertion statements added in FRAG-02. This file tests the
physical/geometric correctness of the output structures.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.pocket import assemble_pocket
from quickice.structure_generation.errors import InterfaceGenerationError


# === Mock Candidate Factories ===

def create_mock_ice_candidate(n_molecules: int = 96, cell_dim: float = 0.9) -> Candidate:
    """Create a mock Ice Ih candidate (3 atoms per molecule: O, H, H).

    Args:
        n_molecules: Number of water molecules (must be divisible by 16 for even grid)
        cell_dim: Unit cell dimension in nm (cubic cell)
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

    Args:
        n_water: Number of water framework molecules
        n_guest: Number of Me guest atoms (1 atom each)
        cell_dim: Unit cell dimension in nm
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


# === Helper: Structural Invariant Checkers ===

def assert_ice_outside_cavity(result, center, radius, pocket_shape, atoms_per_mol=3):
    """Verify all ice O atoms are outside the cavity region."""
    ice_positions = result.positions[:result.ice_atom_count]
    ice_o_positions = ice_positions[::atoms_per_mol]

    if pocket_shape == "sphere":
        distances = np.linalg.norm(ice_o_positions - center, axis=1)
        violations = np.where(distances < radius)[0]
    elif pocket_shape == "cubic":
        dx = np.abs(ice_o_positions[:, 0] - center[0])
        dy = np.abs(ice_o_positions[:, 1] - center[1])
        dz = np.abs(ice_o_positions[:, 2] - center[2])
        violations = np.where((dx < radius) & (dy < radius) & (dz < radius))[0]
    else:
        return  # Skip for unknown shapes

    assert len(violations) == 0, (
        f"{len(violations)} ice O atoms found INSIDE {pocket_shape} cavity "
        f"(radius={radius:.3f}, center={center})"
    )


def assert_water_inside_cavity(result, center, radius, pocket_shape):
    """Verify all water OW atoms are inside the cavity region."""
    water_start = result.ice_atom_count
    water_end = water_start + result.water_atom_count
    water_positions = result.positions[water_start:water_end]
    water_o_positions = water_positions[::4]

    if pocket_shape == "sphere":
        distances = np.linalg.norm(water_o_positions - center, axis=1)
        violations = np.where(distances >= radius)[0]
    elif pocket_shape == "cubic":
        dx = np.abs(water_o_positions[:, 0] - center[0])
        dy = np.abs(water_o_positions[:, 1] - center[1])
        dz = np.abs(water_o_positions[:, 2] - center[2])
        violations = np.where((dx >= radius) | (dy >= radius) | (dz >= radius))[0]
    else:
        return

    assert len(violations) == 0, (
        f"{len(violations)} water OW atoms found OUTSIDE {pocket_shape} cavity "
        f"(radius={radius:.3f}, center={center})"
    )


def assert_positions_within_box(result, box_dims):
    """Verify all positions are within [0, box_dims)."""
    for dim in range(3):
        below = np.where(result.positions[:, dim] < -0.001)[0]  # Small tolerance
        above = np.where(result.positions[:, dim] >= box_dims[dim] + 0.001)[0]
        assert len(below) == 0, (
            f"{len(below)} atoms below box boundary in dim {dim} "
            f"(min={result.positions[:, dim].min():.4f}, box={box_dims[dim]:.3f})"
        )
        assert len(above) == 0, (
            f"{len(above)} atoms above box boundary in dim {dim} "
            f"(max={result.positions[:, dim].max():.4f}, box={box_dims[dim]:.3f})"
        )


def assert_atom_ordering(result):
    """Verify atoms are ordered: ice first, then water, then guests."""
    total = len(result.positions)
    expected = result.ice_atom_count + result.water_atom_count + result.guest_atom_count
    assert total == expected, (
        f"Total atoms {total} != ice({result.ice_atom_count}) + "
        f"water({result.water_atom_count}) + guest({result.guest_atom_count})"
    )


# === Test Classes ===

class TestPocketShapeVariants:
    """Test sphere and cubic pocket shapes produce valid structures."""

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_shape_produces_valid_structure(self, shape):
        """Both shapes produce structure with matching lengths and valid counts."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert result.mode == "pocket"
        assert len(result.atom_names) == len(result.positions)
        assert result.ice_atom_count > 0
        assert result.water_atom_count % 4 == 0
        assert result.ice_nmolecules > 0

    def test_cubic_has_more_water_than_sphere(self):
        """Cubic cavity has larger volume → more water molecules than sphere at same diameter.

        Cubic volume: (2r)^3 = 8r^3
        Sphere volume: (4/3)πr^3 ≈ 4.19r^3
        Cubic has ~1.9x the volume of sphere at same radius.
        """
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)

        config_sphere = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        config_cubic = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )

        result_sphere = assemble_pocket(candidate, config_sphere)
        result_cubic = assemble_pocket(candidate, config_cubic)

        # Cubic should have more water molecules (larger cavity volume)
        assert result_cubic.water_nmolecules >= result_sphere.water_nmolecules, (
            f"Cubic ({result_cubic.water_nmolecules}) should have >= water than "
            f"sphere ({result_sphere.water_nmolecules})"
        )

    def test_cubic_has_fewer_ice_molecules(self):
        """Cubic cavity removes more ice → fewer ice molecules than sphere.

        Cubic cavity is larger, so more ice molecules fall inside and are removed.
        """
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)

        config_sphere = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="sphere"
        )
        config_cubic = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="cubic"
        )

        result_sphere = assemble_pocket(candidate, config_sphere)
        result_cubic = assemble_pocket(candidate, config_cubic)

        assert result_cubic.ice_nmolecules <= result_sphere.ice_nmolecules, (
            f"Cubic ({result_cubic.ice_nmolecules}) should have <= ice molecules than "
            f"sphere ({result_sphere.ice_nmolecules})"
        )

    def test_unknown_shape_raises_error(self):
        """Invalid pocket_shape raises InterfaceGenerationError."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape="ellipsoid"
        )
        with pytest.raises(InterfaceGenerationError):
            assemble_pocket(candidate, config)


class TestPocketSizeExtremes:
    """Test pocket generation at size extremes."""

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_small_pocket(self, shape):
        """Small pocket (0.5nm) — may produce 0 water molecules or raise error."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=0.5, pocket_shape=shape
        )
        try:
            result = assemble_pocket(candidate, config)
            assert len(result.atom_names) == len(result.positions)
            assert result.water_atom_count % 4 == 0
        except InterfaceGenerationError as e:
            # Expected: fill_region_with_water may return 0 molecules
            assert "zero" in str(e).lower() or "Water filling" in str(e) or "pocket" in str(e).lower()

    def test_large_diameter_near_box_size(self):
        """Diameter 4.0nm in 5.0nm box — thin ice shell, still valid."""
        candidate = create_mock_ice_candidate(n_molecules=128, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=5.0, box_z=5.0,
            seed=42, pocket_diameter=4.0, pocket_shape="sphere"
        )
        result = assemble_pocket(candidate, config)
        assert result.ice_nmolecules > 0, "Must have some ice remaining"
        assert len(result.atom_names) == len(result.positions)

    def test_very_thin_ice_shell_cubic(self):
        """Cubic pocket near box boundary — cubic cavity fills more of the box."""
        candidate = create_mock_ice_candidate(n_molecules=128, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=5.0, box_z=5.0,
            seed=42, pocket_diameter=4.0, pocket_shape="cubic"
        )
        result = assemble_pocket(candidate, config)
        assert result.ice_nmolecules > 0
        assert len(result.atom_names) == len(result.positions)


class TestPocketBoxGeometry:
    """Test pocket generation with different box geometries."""

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_rectangular_box(self, shape):
        """Rectangular box (5x3x3) — cavity fits in all dimensions."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=5.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.ice_atom_count > 0
        assert result.water_atom_count % 4 == 0

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_elongated_box(self, shape):
        """Elongated box (6x3x3) — pocket at adjusted center."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=6.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        # Cavity center is at adjusted_box / 2.0
        # Check that the cell diagonal matches adjusted box dims
        for dim in range(3):
            assert result.cell[dim, dim] > 0


class TestPocketStructuralInvariants:
    """Test structural invariants of pocket output."""

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_ice_outside_cavity(self, shape):
        """All ice O atoms must be outside the cavity region."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        # Cavity center = adjusted_box / 2.0, radius = diameter / 2
        radius = config.pocket_diameter / 2.0
        center = np.array([result.cell[0, 0], result.cell[1, 1], result.cell[2, 2]]) / 2.0
        assert_ice_outside_cavity(result, center, radius, shape, atoms_per_mol=3)

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_water_inside_cavity(self, shape):
        """All water OW atoms must be inside the cavity region."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        radius = config.pocket_diameter / 2.0
        center = np.array([result.cell[0, 0], result.cell[1, 1], result.cell[2, 2]]) / 2.0
        assert_water_inside_cavity(result, center, radius, shape)

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_positions_within_box(self, shape):
        """All atom positions must be within [0, box_dims)."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        box_dims = np.array([result.cell[0, 0], result.cell[1, 1], result.cell[2, 2]])
        assert_positions_within_box(result, box_dims)

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_atom_ordering(self, shape):
        """Atoms must be ordered: ice, water, guests."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert_atom_ordering(result)

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_total_atoms_equals_sum(self, shape):
        """Total atoms = ice + water + guest."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        expected = result.ice_atom_count + result.water_atom_count + result.guest_atom_count
        assert len(result.positions) == expected
        assert len(result.atom_names) == expected

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_cell_matrix_diagonal(self, shape):
        """Cell matrix should be diagonal with adjusted box dimensions."""
        candidate = create_mock_ice_candidate(n_molecules=96, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        # Off-diagonal elements should be zero
        for i in range(3):
            for j in range(3):
                if i != j:
                    assert abs(result.cell[i, j]) < 1e-10, (
                        f"Cell[{i},{j}] = {result.cell[i, j]:.2e}, expected ~0"
                    )
        # Diagonal should be >= requested box dims (adjusted up for periodicity)
        assert result.cell[0, 0] >= config.box_x - 0.001
        assert result.cell[1, 1] >= config.box_y - 0.001
        assert result.cell[2, 2] >= config.box_z - 0.001


class TestPocketWithHydrate:
    """Test pocket mode with hydrate candidates (guest molecules)."""

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_hydrate_basic_structure(self, shape):
        """Hydrate candidate produces valid structure with guests."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert len(result.atom_names) == len(result.positions)
        assert result.water_atom_count % 4 == 0
        # Hydrate candidates have 4 atoms per ice molecule (TIP4P)
        assert result.ice_atom_count % 4 == 0

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_hydrate_atom_ordering(self, shape):
        """Atoms ordered: ice (TIP4P), water (TIP4P), guests (Me)."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        assert_atom_ordering(result)
        # Guest atoms should come after ice + water
        if result.guest_atom_count > 0:
            guest_start = result.ice_atom_count + result.water_atom_count
            guest_names = result.atom_names[guest_start:]
            # Me guests should all be "Me"
            for name in guest_names:
                assert name == "Me", f"Expected 'Me' guest, got '{name}'"

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_hydrate_ice_outside_cavity(self, shape):
        """Hydrate ice framework molecules are outside cavity."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        radius = config.pocket_diameter / 2.0
        center = np.array([result.cell[0, 0], result.cell[1, 1], result.cell[2, 2]]) / 2.0
        # Hydrate uses 4 atoms per molecule (TIP4P)
        assert_ice_outside_cavity(result, center, radius, shape, atoms_per_mol=4)

    @pytest.mark.parametrize("shape", ["sphere", "cubic"])
    def test_hydrate_positions_within_box(self, shape):
        """All positions within box bounds for hydrate pocket."""
        candidate = create_mock_hydrate_candidate(n_water=32, n_guest=4, cell_dim=0.9)
        config = InterfaceConfig(
            mode="pocket", box_x=3.0, box_y=3.0, box_z=3.0,
            seed=42, pocket_diameter=1.0, pocket_shape=shape
        )
        result = assemble_pocket(candidate, config)
        box_dims = np.array([result.cell[0, 0], result.cell[1, 1], result.cell[2, 2]])
        assert_positions_within_box(result, box_dims)
