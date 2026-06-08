"""Regression tests for scancode bugs ATOM-01 and RNG-01.

ATOM-01 (MEDIUM): Hardcoded water atom count `// 4` replaced with
WATER_ATOMS_PER_MOLECULE constant from types.py.

RNG-01 (HIGH): Unseeded RNG in CustomMoleculeInserter and
Rotation.random() in both inserters made placement non-reproducible.
Fixed by adding seed parameter and seeding Rotation.random().

These tests verify:
1. WATER_ATOMS_PER_MOLECULE constant exists and is used (no bare `// 4`)
2. Same seed produces identical custom molecule placement
3. Different seeds produce different placements
4. SoluteInserter Rotation.random() is seeded for reproducibility
"""

import re
from pathlib import Path

import numpy as np
import pytest

from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    InterfaceStructure,
    MoleculeIndex,
    SoluteConfig,
    WATER_ATOMS_PER_MOLECULE,
)
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.solute_inserter import SoluteInserter


# ── Source file paths for static analysis ──────────────────────────────────────

_INSERTER_DIR = Path(__file__).parent.parent / "quickice" / "structure_generation"
_CUSTOM_INSERTER_SRC = _INSERTER_DIR / "custom_molecule_inserter.py"
_SOLUTE_INSERTER_SRC = _INSERTER_DIR / "solute_inserter.py"


# ── ATOM-01: Hardcoded water atom count ───────────────────────────────────────


class TestATOM01:
    """Regression tests for ATOM-01: hardcoded `// 4` water atom count."""

    def test_water_atoms_per_molecule_constant_exists(self):
        """WATER_ATOMS_PER_MOLECULE constant is defined and equals 4."""
        assert WATER_ATOMS_PER_MOLECULE == 4, (
            f"Expected WATER_ATOMS_PER_MOLECULE == 4, got {WATER_ATOMS_PER_MOLECULE}"
        )

    def test_no_hardcoded_water_atom_count_in_inserters(self):
        """No bare `// 4` or `count=4` for water atom count in inserter files.

        Searches custom_molecule_inserter.py and solute_inserter.py for
        patterns that indicate hardcoded water atom counts. Any remaining
        bare `// 4` not preceded by WATER_ATOMS_PER_MOLECULE is a bug.
        """
        for src_path in [_CUSTOM_INSERTER_SRC, _SOLUTE_INSERTER_SRC]:
            assert src_path.exists(), f"Source file not found: {src_path}"
            source = src_path.read_text()

            # Find all integer division by 4 that is NOT dividing by the constant
            # Pattern: "// 4" not preceded by "WATER_ATOMS_PER_MOLECULE"
            # We look for any `// 4` that isn't `// WATER_ATOMS_PER_MOLECULE`
            bare_div_4 = re.findall(r'(?<!WATER_ATOMS_PER_MOLECULE)\s*//\s*4\b', source)

            # Filter out comments
            lines = source.splitlines()
            problematic_lines = []
            for i, line in enumerate(lines, 1):
                stripped = line.split('#')[0]  # Remove comments
                if re.search(r'//\s*4\b', stripped) and 'WATER_ATOMS_PER_MOLECULE' not in stripped:
                    problematic_lines.append((i, stripped.strip()))

            assert len(problematic_lines) == 0, (
                f"Found bare `// 4` in {src_path.name} "
                f"(should use WATER_ATOMS_PER_MOLECULE):\n"
                + "\n".join(f"  Line {n}: {s}" for n, s in problematic_lines)
            )


# ── RNG-01: Unseeded RNG in inserters ─────────────────────────────────────────


class TestRNG01:
    """Regression tests for RNG-01: unseeded RNG in CustomMoleculeInserter."""

    @pytest.fixture
    def interface_structure(self):
        """Create a minimal InterfaceStructure for testing."""
        # Create a simple slab interface with ice + water atoms
        ice_atoms = 12  # 4 ice molecules × 3 atoms (TIP3P)
        water_atoms = 16  # 4 water molecules × 4 atoms (TIP4P-ICE)
        total = ice_atoms + water_atoms

        positions = np.zeros((total, 3))
        # Ice at z=0-1
        for i in range(ice_atoms):
            positions[i] = [0.1 * i, 0.1 * i, 0.5]
        # Water at z=2-4
        for i in range(water_atoms):
            positions[i + ice_atoms] = [0.1 * i, 0.1 * i, 3.0]

        atom_names = (
            ["O", "H", "H"] * 4 +  # ice TIP3P
            ["OW", "HW1", "HW2", "MW"] * 4  # water TIP4P-ICE
        )

        return InterfaceStructure(
            positions=positions,
            atom_names=atom_names,
            cell=np.array([[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 5.0]]),
            ice_atom_count=ice_atoms,
            water_atom_count=water_atoms,
            ice_nmolecules=4,
            water_nmolecules=4,
            mode="slab",
            report="test interface",
        )

    @pytest.fixture
    def custom_config(self):
        """Create a CustomMoleculeConfig for testing."""
        data_dir = Path(__file__).parent.parent / "quickice" / "data" / "custom"
        gro_path = data_dir / "etoh.gro"
        itp_path = data_dir / "etoh.itp"
        return CustomMoleculeConfig(
            placement_mode="random",
            gro_path=gro_path,
            itp_path=itp_path,
            molecule_count=1,
            min_separation=0.15,
            max_attempts=100,
        )

    def test_custom_molecule_reproducible_with_seed(
        self, interface_structure, custom_config
    ):
        """Same seed produces identical custom molecule placement (RNG-01)."""
        inserter1 = CustomMoleculeInserter(custom_config, seed=42)
        inserter2 = CustomMoleculeInserter(custom_config, seed=42)

        result1 = inserter1.place_random(interface_structure, n_molecules=1)
        result2 = inserter2.place_random(interface_structure, n_molecules=1)

        # Positions must be exactly equal for same seed
        assert np.array_equal(result1.positions, result2.positions), (
            "Same seed should produce identical positions — seeding is broken"
        )

    def test_custom_molecule_different_without_seed(
        self, interface_structure, custom_config
    ):
        """Different seeds produce different custom molecule placements (RNG-01)."""
        inserter1 = CustomMoleculeInserter(custom_config, seed=1)
        inserter2 = CustomMoleculeInserter(custom_config, seed=2)

        result1 = inserter1.place_random(interface_structure, n_molecules=1)
        result2 = inserter2.place_random(interface_structure, n_molecules=1)

        # Positions should differ for different seeds
        assert not np.array_equal(result1.positions, result2.positions), (
            "Different seeds should produce different positions — seeding is broken"
        )

    def test_solute_reproducible_rotation_with_seed(self):
        """Same seed produces identical rotation matrices in SoluteInserter (RNG-01)."""
        inserter1 = SoluteInserter(seed=42)
        inserter2 = SoluteInserter(seed=42)

        # Generate multiple rotations to verify reproducibility
        matrices1 = [inserter1._generate_random_rotation_matrix() for _ in range(5)]
        matrices2 = [inserter2._generate_random_rotation_matrix() for _ in range(5)]

        for i, (m1, m2) in enumerate(zip(matrices1, matrices2)):
            assert np.allclose(m1, m2), (
                f"Rotation matrix {i} differs for same seed — "
                f"Rotation.random() seeding is broken"
            )
