"""End-to-end tests for custom molecule upload & insertion (Workflow 5).

Tests the custom molecule pipeline: GRO/ITP validation → random/custom placement
with overlap checking and water removal → complete system assembly.

Uses shared conftest.py fixtures (interface_slab, interface_hydrate_slab)
and real etoh.gro/etoh.itp test data for authentic end-to-end coverage.
"""

import numpy as np
import pytest
from pathlib import Path
from scipy.spatial import cKDTree

from quickice.structure_generation.custom_molecule_inserter import (
    CustomMoleculeInserter,
    InsertionError,
)
from quickice.structure_generation.molecule_validator import (
    validate_custom_molecule,
    ValidationResult,
    GENERIC_RESIDUE_NAMES,
)
from quickice.structure_generation.itp_parser import parse_itp_file, ITPMoleculeInfo
from quickice.structure_generation.gro_parser import (
    parse_gro_file,
    extract_residue_name_from_gro,
)
from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    CustomMoleculeStructure,
    PlacementValidationResult,
)


# ── Test data paths ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"
ETOH_ATOM_COUNT = 9  # Ethanol has 9 atoms


# ── Helper: write minimal GRO file ───────────────────────────────────────────

def write_minimal_gro(path: Path, atom_count: int, residue_name: str = "MOL",
                      positions: np.ndarray | None = None) -> None:
    """Write a minimal GRO file for testing.

    Args:
        path: Output file path
        atom_count: Number of atoms
        residue_name: Residue name (5 chars max)
        positions: Optional (N, 3) positions; defaults to small random values
    """
    if positions is None:
        rng = np.random.default_rng(42)
        positions = rng.uniform(0.0, 0.5, size=(atom_count, 3))

    lines = ["test_molecule", f"  {atom_count:<5d}"]
    for i in range(atom_count):
        x, y, z = positions[i]
        atom_name = "X"  # Generic atom name
        lines.append(
            f"    1{residue_name:<5s}{atom_name:<5s}{i + 1:5d}"
            f"{x:8.3f}{y:8.3f}{z:8.3f}"
        )
    lines.append("   1.00000   1.00000   1.00000")
    path.write_text("\n".join(lines) + "\n")


def write_minimal_itp(path: Path, molecule_name: str = "testmol",
                      atom_count: int = 9, include_atomtypes: bool = True) -> None:
    """Write a minimal ITP file for testing.

    Args:
        path: Output file path
        molecule_name: Moleculetype name
        atom_count: Number of atoms
        include_atomtypes: Whether to include [ atomtypes ] section
    """
    lines = []
    if include_atomtypes:
        lines.extend([
            "[ atomtypes ]",
            "; name  at.num  mass  charge  ptype  sigma  epsilon",
            "hc    1  1.008  0.0  A  0.26  0.087",
        ])
        lines.append("")
    lines.extend([
        "[ moleculetype ]",
        "; Name  nrexcl",
        f"{molecule_name}    3",
        "",
        "[ atoms ]",
        ";  Index  type  residue  resname  atom  cgnr  charge  mass",
    ])
    for i in range(1, atom_count + 1):
        lines.append(
            f"     {i}     hc         1      MOL     H              {i}    0.0    1.008"
        )
    path.write_text("\n".join(lines) + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Validation tests (Workflow 5a)
# ══════════════════════════════════════════════════════════════════════════════


class TestCustomMoleculeValidation:
    """Tests for GRO/ITP file validation (Workflow 5a)."""

    def test_validate_etoh_molecule_valid(self):
        """Valid etoh.gro + etoh.itp should pass validation with no errors.

        The etoh files are the canonical test data with 9 atoms and
        matching GRO/ITP consistency.
        """
        itp_info = parse_itp_file(ETOH_ITP)
        result = validate_custom_molecule(ETOH_GRO, itp_info)

        assert result.is_valid is True, f"Valid etoh should pass: {result.errors}"
        assert result.errors == [], f"Valid etoh should have no errors: {result.errors}"
        assert result.gro_atom_count == ETOH_ATOM_COUNT, (
            f"Expected {ETOH_ATOM_COUNT} atoms, got {result.gro_atom_count}"
        )

    def test_validate_atom_count_mismatch(self, tmp_path):
        """GRO file with wrong atom count should fail validation.

        Atom count mismatch is a BLOCKING error — the GRO and ITP must
        agree on the number of atoms.
        """
        # Create GRO with 10 atoms (ITP says 9)
        wrong_count_gro = tmp_path / "wrong.gro"
        write_minimal_gro(wrong_count_gro, atom_count=10, residue_name="MOL")

        itp_info = parse_itp_file(ETOH_ITP)
        result = validate_custom_molecule(wrong_count_gro, itp_info)

        assert result.is_valid is False, "Atom count mismatch should be blocking"
        assert any("atom count mismatch" in e.lower() for e in result.errors), (
            f"Expected 'atom count mismatch' in errors, got: {result.errors}"
        )

    def test_validate_generic_residue_name_no_mismatch(self, tmp_path):
        """Generic residue names (MOL, UNK, etc.) should NOT trigger mismatch warning.

        These are placeholder names commonly used in computational chemistry
        and are expected to differ from the ITP moleculetype name.
        """
        # Create GRO with generic residue name "MOL"
        generic_gro = tmp_path / "generic.gro"
        write_minimal_gro(generic_gro, atom_count=9, residue_name="MOL")

        itp_info = parse_itp_file(ETOH_ITP)
        result = validate_custom_molecule(generic_gro, itp_info)

        # "MOL" is in GENERIC_RESIDUE_NAMES, so mismatch should NOT be flagged
        assert result.residue_name_mismatch is False, (
            f"Generic residue name 'MOL' should not trigger mismatch warning. "
            f"GRO: '{result.gro_residue_name}', ITP: '{result.itp_residue_name}'"
        )

    def test_validate_real_residue_name_mismatch(self, tmp_path):
        """Non-generic residue name that differs from ITP should trigger mismatch.

        When a GRO file uses a specific (non-generic) residue name that
        differs from the ITP moleculetype name, the user should be warned.
        """
        # Create GRO with a specific, non-generic residue name
        mismatch_gro = tmp_path / "mismatch.gro"
        write_minimal_gro(mismatch_gro, atom_count=9, residue_name="XXX_CUSTOM")

        # Note: "XXX_CUSTOM" is NOT in GENERIC_RESIDUE_NAMES
        itp_info = parse_itp_file(ETOH_ITP)  # moleculetype name is "etoh"
        result = validate_custom_molecule(mismatch_gro, itp_info)

        assert result.residue_name_mismatch is True, (
            f"Non-generic residue name 'XXX_CUSTOM' differs from ITP name 'etoh' "
            f"and should trigger mismatch warning"
        )

    def test_validate_itp_without_atomtypes_warning(self, tmp_path):
        """ITP without [ atomtypes ] section should produce a warning but not block.

        Missing atomtypes means the user must provide atom type parameters
        separately in the force field file — this is advisory, not blocking.
        """
        no_atomtypes_itp = tmp_path / "no_atomtypes.itp"
        write_minimal_itp(no_atomtypes_itp, molecule_name="testmol",
                          atom_count=9, include_atomtypes=False)

        # Create matching GRO (9 atoms)
        matching_gro = tmp_path / "match.gro"
        write_minimal_gro(matching_gro, atom_count=9, residue_name="MOL")

        itp_info = parse_itp_file(no_atomtypes_itp)
        result = validate_custom_molecule(matching_gro, itp_info)

        # Should still be valid (atomtypes is warning-only)
        assert result.is_valid is True, (
            f"Missing atomtypes should be warning-only, not blocking: {result.errors}"
        )
        # Should have a warning mentioning atomtypes
        assert any("atomtypes" in w.lower() for w in result.warnings), (
            f"Expected 'atomtypes' in warnings, got: {result.warnings}"
        )

    def test_parse_non_gro_file_raises_error(self):
        """Attempting to parse a non-existent GRO file should raise an error.

        parse_gro_file should raise FileNotFoundError for missing files.
        """
        with pytest.raises((FileNotFoundError, ValueError)):
            parse_gro_file(Path("nonexistent_file.txt"))


# ══════════════════════════════════════════════════════════════════════════════
# Random placement tests (Workflow 5b)
# ══════════════════════════════════════════════════════════════════════════════


class TestRandomPlacement:
    """Tests for random molecule placement in liquid region (Workflow 5b)."""

    def test_random_placement_produces_custom_structure(self, interface_slab):
        """place_random() should produce a CustomMoleculeStructure with correct molecule count.

        Placing 3 ethanol molecules should give custom_molecule_count == 3
        and custom_molecule_atom_count == 3 * 9 = 27.
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        assert isinstance(custom, CustomMoleculeStructure)
        assert custom.custom_molecule_count == 3, (
            f"Expected 3 molecules, got {custom.custom_molecule_count}"
        )
        assert custom.positions.shape[0] > 0, "Should have atoms"
        assert custom.custom_molecule_atom_count == 3 * ETOH_ATOM_COUNT, (
            f"Expected {3 * ETOH_ATOM_COUNT} custom atoms, got {custom.custom_molecule_atom_count}"
        )

    def test_random_placement_molecules_in_liquid_region(self, interface_slab):
        """Placed molecules should have center-of-mass within liquid region bounds.

        The liquid region is defined by water atom positions between ice
        and guest boundaries. Each molecule's COM must fall within the
        z-range (and x/y-range) of the liquid region.
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=5,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 5)

        # Get liquid region bounds from original interface
        ice_count = interface_slab.ice_atom_count
        water_count = interface_slab.water_atom_count
        liquid_positions = interface_slab.positions[ice_count:ice_count + water_count]
        liquid_min = liquid_positions.min(axis=0)
        liquid_max = liquid_positions.max(axis=0)

        # Extract custom molecule positions from the complete system
        custom_start = custom.ice_atom_count + custom.water_atom_count + custom.guest_atom_count
        custom_positions = custom.positions[custom_start:]

        # Check each molecule's center of mass
        atoms_per_mol = ETOH_ATOM_COUNT
        for i in range(5):
            mol_start = i * atoms_per_mol
            mol_end = mol_start + atoms_per_mol
            mol_positions = custom_positions[mol_start:mol_end]
            com = mol_positions.mean(axis=0)

            # COM should be within (or very near) liquid region bounds
            # Allow small tolerance for edge placements
            tolerance = 0.2  # nm — molecules extend beyond COM
            for dim in range(3):
                assert com[dim] >= liquid_min[dim] - tolerance, (
                    f"Molecule {i} COM[{dim}] = {com[dim]:.3f} < liquid_min[{dim}] = {liquid_min[dim]:.3f}"
                )
                assert com[dim] <= liquid_max[dim] + tolerance, (
                    f"Molecule {i} COM[{dim}] = {com[dim]:.3f} > liquid_max[{dim}] = {liquid_max[dim]:.3f}"
                )

    def test_random_placement_no_ice_overlap(self, interface_slab):
        """Custom molecule atoms should maintain min_separation from ice atoms.

        Uses cKDTree to verify minimum distance between any custom atom
        and any ice atom exceeds the configured min_separation threshold.
        """
        min_sep = 0.3  # nm
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
            min_separation=min_sep,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        # Build KDTree from ice atoms
        ice_positions = custom.positions[:custom.ice_atom_count]
        ice_tree = cKDTree(ice_positions)

        # Check each custom molecule atom
        custom_start = custom.ice_atom_count + custom.water_atom_count + custom.guest_atom_count
        custom_positions = custom.positions[custom_start:]

        for atom_pos in custom_positions:
            dist, _ = ice_tree.query(atom_pos, k=1)
            assert dist >= min_sep, (
                f"Custom atom too close to ice: distance = {dist:.4f} nm < {min_sep} nm"
            )

    def test_random_placement_water_removal(self, interface_slab):
        """Water atoms should decrease after custom molecule insertion.

        The _remove_overlapping_water() logic replaces water molecules
        that overlap with placed custom molecules.
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        assert custom.water_atom_count < interface_slab.water_atom_count, (
            f"Water atoms should decrease after molecule insertion: "
            f"{custom.water_atom_count} >= {interface_slab.water_atom_count}"
        )

    def test_random_placement_complete_system(self, interface_slab):
        """Total atom count should equal ice + water + guest + custom atoms.

        The complete system positions array must contain exactly the sum
        of all component atom counts.
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        expected_total = (
            custom.ice_atom_count
            + custom.water_atom_count
            + custom.guest_atom_count
            + custom.custom_molecule_atom_count
        )
        actual_total = len(custom.positions)

        assert actual_total == expected_total, (
            f"Atom count mismatch: {actual_total} positions vs "
            f"{expected_total} expected "
            f"(ice={custom.ice_atom_count}, water={custom.water_atom_count}, "
            f"guest={custom.guest_atom_count}, custom={custom.custom_molecule_atom_count})"
        )

    def test_molecule_count_from_concentration(self, interface_slab):
        """calculate_molecule_count(C, V) should return a positive integer.

        Uses the interface slab's water molecules to estimate liquid volume
        (water_nmolecules × 0.0299 nm³ per molecule).
        """
        # Estimate liquid volume: N_water × V_per_molecule
        liquid_volume_nm3 = interface_slab.water_nmolecules * 0.0299

        count = CustomMoleculeInserter.calculate_molecule_count(1.0, liquid_volume_nm3)

        assert isinstance(count, int), f"Should return int, got {type(count)}"
        assert count > 0, f"At 1.0 M with {liquid_volume_nm3:.1f} nm³, count should be > 0"

    def test_concentration_roundtrip(self, interface_slab):
        """Concentration roundtrip: C → N → C₂ should satisfy |C₂ - C| < 0.01.

        Verifies that calculate_molecule_count and calculate_concentration
        are inverse operations within rounding tolerance.
        """
        liquid_volume_nm3 = interface_slab.water_nmolecules * 0.0299
        C = 0.5  # mol/L

        count = CustomMoleculeInserter.calculate_molecule_count(C, liquid_volume_nm3)
        C2 = CustomMoleculeInserter.calculate_concentration(count, liquid_volume_nm3)

        assert abs(C2 - C) < 0.01, (
            f"Concentration roundtrip failed: C={C}, count={count}, C2={C2}, "
            f"|C2-C|={abs(C2 - C):.4f}"
        )
