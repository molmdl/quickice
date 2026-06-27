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
    WATER_VOLUME_NM3,
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

    def test_validate_generic_residue_name_triggers_dialog(self, tmp_path):
        """Generic residue names (MOL, UNK, etc.) should trigger a dialog choice.

        These are placeholder names commonly used in computational chemistry
        and are expected to differ from the ITP moleculetype name.
        The validator should flag the mismatch so a dialog can be offered,
        but also set is_generic_residue_name=True to indicate the appropriate
        dialog message.
        """
        # Create GRO with generic residue name "MOL"
        generic_gro = tmp_path / "generic.gro"
        write_minimal_gro(generic_gro, atom_count=9, residue_name="MOL")

        itp_info = parse_itp_file(ETOH_ITP)
        result = validate_custom_molecule(generic_gro, itp_info)

        # "MOL" is in GENERIC_RESIDUE_NAMES, so mismatch IS flagged (to offer dialog)
        assert result.residue_name_mismatch is True, (
            f"Generic residue name 'MOL' should trigger mismatch flag for dialog. "
            f"GRO: '{result.gro_residue_name}', ITP: '{result.itp_residue_name}'"
        )
        assert result.is_generic_residue_name is True, (
            f"'MOL' should be flagged as a generic residue name"
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
        (water_nmolecules × WATER_VOLUME_NM3 nm³ per molecule).
        """
        # Estimate liquid volume: N_water × V_per_molecule
        liquid_volume_nm3 = interface_slab.water_nmolecules * WATER_VOLUME_NM3

        count = CustomMoleculeInserter.calculate_molecule_count(1.0, liquid_volume_nm3)

        assert isinstance(count, int), f"Should return int, got {type(count)}"
        assert count > 0, f"At 1.0 M with {liquid_volume_nm3:.1f} nm³, count should be > 0"

    def test_concentration_roundtrip(self, interface_slab):
        """Concentration roundtrip: C → N → C₂ should satisfy |C₂ - C| < 0.01.

        Verifies that calculate_molecule_count and calculate_concentration
        are inverse operations within rounding tolerance.
        """
        liquid_volume_nm3 = interface_slab.water_nmolecules * WATER_VOLUME_NM3
        C = 0.5  # mol/L

        count = CustomMoleculeInserter.calculate_molecule_count(C, liquid_volume_nm3)
        C2 = CustomMoleculeInserter.calculate_concentration(count, liquid_volume_nm3)

        assert abs(C2 - C) < 0.01, (
            f"Concentration roundtrip failed: C={C}, count={count}, C2={C2}, "
            f"|C2-C|={abs(C2 - C):.4f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Custom placement tests (Workflow 5c)
# ══════════════════════════════════════════════════════════════════════════════


class TestCustomPlacement:
    """Tests for user-specified molecule placement (Workflow 5c)."""

    def test_custom_placement_at_valid_position(self, interface_slab):
        """Valid position in liquid region should pass validation.

        A position well within the liquid region should be within_bounds
        and is_valid.
        """
        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            positions=[(1.5, 1.5, 4.0)],
            rotations=[(0, 0, 0)],
        )
        inserter = CustomMoleculeInserter(config)

        result = inserter.validate_single_placement(
            interface_slab, (1.5, 1.5, 4.0), (0, 0, 0)
        )

        assert isinstance(result, PlacementValidationResult)
        assert result.within_bounds is True, (
            f"Position (1.5, 1.5, 4.0) should be within liquid region: "
            f"error='{result.error_message}'"
        )
        assert result.is_valid is True, (
            f"Valid position should pass validation: error='{result.error_message}'"
        )

    def test_custom_placement_out_of_bounds(self, interface_slab):
        """Position in ice region (z near 0) should be out of bounds.

        The liquid region starts after the ice layer. A position at
        z ≈ 0 should be in the ice region, not the liquid region.
        """
        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            positions=[(0.5, 0.5, 0.1)],
            rotations=[(0, 0, 0)],
        )
        inserter = CustomMoleculeInserter(config)

        result = inserter.validate_single_placement(
            interface_slab, (0.5, 0.5, 0.1), (0, 0, 0)
        )

        assert result.within_bounds is False, (
            f"Position in ice region should be out of bounds"
        )
        assert result.is_valid is False, (
            f"Out-of-bounds position should fail validation"
        )

    def test_custom_placement_overlap_detected(self, interface_slab):
        """Position overlapping with ice atoms should detect overlap.

        A position very close to the ice region (0.1, 0.1, 0.1) will
        either be out of bounds or will overlap with ice atoms.
        """
        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            positions=[(0.1, 0.1, 0.1)],
            rotations=[(0, 0, 0)],
        )
        inserter = CustomMoleculeInserter(config)

        result = inserter.validate_single_placement(
            interface_slab, (0.1, 0.1, 0.1), (0, 0, 0)
        )

        # Position (0.1, 0.1, 0.1) is in ice region → either out of bounds or overlap
        assert result.has_overlap is True or result.within_bounds is False, (
            f"Position in ice region should trigger overlap or be out of bounds. "
            f"within_bounds={result.within_bounds}, has_overlap={result.has_overlap}"
        )

    def test_custom_placement_no_interface_returns_invalid(self, interface_slab):
        """validate_single_placement with no liquid region should return invalid.

        A structure with water_atom_count == 0 has no liquid region,
        making custom placement impossible.
        """
        # Create a synthetic structure with no water
        from quickice.structure_generation.types import InterfaceStructure

        no_water_structure = InterfaceStructure(
            positions=interface_slab.positions[:interface_slab.ice_atom_count],
            atom_names=interface_slab.atom_names[:interface_slab.ice_atom_count],
            cell=interface_slab.cell,
            ice_atom_count=interface_slab.ice_atom_count,
            water_atom_count=0,
            ice_nmolecules=interface_slab.ice_nmolecules,
            water_nmolecules=0,
            mode="slab",
            report="",
            guest_atom_count=0,
            guest_nmolecules=0,
        )

        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            positions=[(1.5, 1.5, 4.0)],
            rotations=[(0, 0, 0)],
        )
        inserter = CustomMoleculeInserter(config)

        result = inserter.validate_single_placement(
            no_water_structure, (1.5, 1.5, 4.0), (0, 0, 0)
        )

        assert result.is_valid is False, (
            "No liquid region should make placement invalid"
        )
        assert result.error_message is not None, "Should have error message"
        assert "liquid" in result.error_message.lower() or "no " in result.error_message.lower(), (
            f"Error message should mention no liquid region: '{result.error_message}'"
        )

    def test_place_custom_with_user_positions(self, interface_slab):
        """place_custom() should produce structure with user-specified molecules.

        Placing 1 ethanol at (1.5, 1.5, 4.0) should yield
        custom_molecule_count == 1 and correct complete system atom counts.
        """
        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            positions=[(1.5, 1.5, 4.0)],
            rotations=[(0, 0, 0)],
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_custom(
            interface_slab,
            positions=[(1.5, 1.5, 4.0)],
            rotations=[(0, 0, 0)],
        )

        assert isinstance(custom, CustomMoleculeStructure)
        assert custom.custom_molecule_count == 1, (
            f"Expected 1 molecule, got {custom.custom_molecule_count}"
        )
        assert custom.custom_molecule_atom_count == ETOH_ATOM_COUNT, (
            f"Expected {ETOH_ATOM_COUNT} custom atoms, got {custom.custom_molecule_atom_count}"
        )

        # Verify complete system atom counts sum correctly
        expected_total = (
            custom.ice_atom_count
            + custom.water_atom_count
            + custom.guest_atom_count
            + custom.custom_molecule_atom_count
        )
        actual_total = len(custom.positions)
        assert actual_total == expected_total, (
            f"Atom count mismatch: {actual_total} positions vs {expected_total} expected"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Edge case tests
# ══════════════════════════════════════════════════════════════════════════════


class TestCustomMoleculeEdgeCases:
    """Edge case tests for custom molecule workflow."""

    def test_custom_molecule_moleculetype_registration(self, interface_slab):
        """After place_random(), moleculetype_name should be registered in the registry.

        CustomMoleculeInserter registers each placed molecule type with
        MoleculetypeRegistry, producing a name like "CUSTOM_MOL_1".
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=2,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 2)

        # moleculetype_name should be set
        assert custom.moleculetype_name, "moleculetype_name should not be empty"
        assert "CUSTOM" in custom.moleculetype_name.upper() or "MOL" in custom.moleculetype_name.upper(), (
            f"Expected moleculetype name containing CUSTOM/MOL, got '{custom.moleculetype_name}'"
        )

        # Registry should have the registered type
        assert inserter.registry is not None, "Registry should not be None"
        # The registry should have at least one custom moleculetype registered
        custom_keys = [k for k in inserter.registry._registered if k.startswith("custom_")]
        assert len(custom_keys) >= 1, (
            f"Registry should have registered custom moleculetype, "
            f"keys: {list(inserter.registry._registered.keys())}"
        )

    def test_custom_molecule_from_hydrate_interface(self, interface_hydrate_slab):
        """Custom molecule placement on hydrate interface should preserve guests.

        The interface_hydrate_slab fixture has guest molecules (CH4 from
        hydrate). After custom molecule insertion, guests should still be
        present and custom molecules correctly placed.
        """
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=2,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_hydrate_slab, 2)

        # Guests should be preserved
        assert custom.guest_atom_count > 0, (
            f"Guest atoms should be preserved from hydrate interface, "
            f"got guest_atom_count={custom.guest_atom_count}"
        )

        # Custom molecules should be placed
        assert custom.custom_molecule_count == 2, (
            f"Expected 2 custom molecules, got {custom.custom_molecule_count}"
        )
        assert custom.custom_molecule_atom_count == 2 * ETOH_ATOM_COUNT, (
            f"Expected {2 * ETOH_ATOM_COUNT} custom atoms, got {custom.custom_molecule_atom_count}"
        )

        # Complete system should have all components
        expected_total = (
            custom.ice_atom_count
            + custom.water_atom_count
            + custom.guest_atom_count
            + custom.custom_molecule_atom_count
        )
        actual_total = len(custom.positions)
        assert actual_total == expected_total, (
            f"Atom count mismatch on hydrate interface: "
            f"{actual_total} positions vs {expected_total} expected"
        )
