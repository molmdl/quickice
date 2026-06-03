"""End-to-end tests for Custom Molecule single-structure GROMACS export.

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
writer functions, validating that exported .gro and .top files are correct.

Scenario 4: Custom Molecule Export
- Uses real GenIce2-generated interface slab
- Inserts custom ethanol molecules via CustomMoleculeInserter
- Exports via write_custom_molecule_gro_file / write_custom_molecule_top_file
- Validates: GRO residues, atom count, TOP molecules, TOP includes,
  ITP existence, atom conservation

Uses conftest.py fixtures for real GenIce2-generated structures.
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
# (avoids conftest.py import which is unreliable in pytest)
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
)

# Import parsing helpers from the shared module (NOT from conftest)
from e2e_export_helpers import (
    _insert_custom_molecules,
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    parse_top_includes,
    check_itp_has_moleculetype,
    assert_gro_residue_ordering,
    ETOH_ITP,
)


# ── Helper: locate bundled ITP files ─────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


def _get_custom_data_dir() -> Path:
    """Get the path to quickice/data/custom/ directory."""
    return _get_data_dir() / "custom"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 4: Custom Molecule Export
# ══════════════════════════════════════════════════════════════════════════════


class TestCustomMoleculeExport:
    """Validate Custom Molecule export via write_custom_molecule_gro_file / write_custom_molecule_top_file.

    Custom molecule system has SOL (ice+water) + custom residue molecules.
    The moleculetype_name comes from MoleculetypeRegistry.register_custom_molecule()
    which defaults to "MOL" (not the ITP moleculetype name "etoh").

    GRO residue ordering: SOL before custom residue (no interleaving).
    GRO atom count = ice_nmolecules*4 + water_nmolecules*4 + custom_molecule_count*atoms_per_mol.
    TOP [molecules] = {"SOL": ice+water, "MOL": custom_molecule_count}
    TOP #include = ["tip4p-ice.itp", "etoh.itp"] (custom ITP uses original filename)
    """

    @pytest.fixture(autouse=True)
    def _build_custom(self, interface_slab):
        """Build custom molecule structure for all tests in this class."""
        self.custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.mol_name = self.custom.moleculetype_name  # "MOL" from registry

    def test_gro_sol_before_custom_residues(self, tmp_path):
        """GRO file has SOL residues before custom molecule residues with no interleaving."""
        gro_path = str(tmp_path / "custom.gro")
        write_custom_molecule_gro_file(self.custom, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert self.mol_name in unique_names, (
            f"Should have {self.mol_name} residues, got {unique_names}"
        )

        # Verify ordering: SOL before custom molecule (no interleaving)
        assert_gro_residue_ordering(residue_names, ["SOL", self.mol_name])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines.

        Expected = ice_nmolecules*4 + water_nmolecules*4 + custom_molecule_count*atoms_per_mol
        (ice uses TIP4P-ICE 3->4 expansion, custom molecules have variable atom count)
        """
        gro_path = str(tmp_path / "custom.gro")
        write_custom_molecule_gro_file(self.custom, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Verify expected count
        # SOL molecules from molecule_index
        sol_count = sum(1 for m in self.custom.molecule_index if m.mol_type in ("ice", "water"))
        # For ice: each molecule becomes 4 atoms; for water: already 4 atoms
        sol_atoms = sum(4 if m.mol_type == "ice" else m.count
                        for m in self.custom.molecule_index if m.mol_type in ("ice", "water"))
        custom_atoms = self.custom.custom_molecule_atom_count
        expected = sol_atoms + custom_atoms

        assert header_count == expected, (
            f"Expected {expected} atoms (sol={sol_atoms} + custom={custom_atoms}), "
            f"got {header_count}"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has correct SOL and custom molecule counts."""
        top_path = str(tmp_path / "custom.top")
        write_custom_molecule_top_file(self.custom, top_path)

        molecules = parse_top_molecules(top_path)

        # SOL count = ice + water from molecule_index
        sol_count = sum(1 for m in self.custom.molecule_index if m.mol_type in ("ice", "water"))
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == sol_count, (
            f"Expected SOL count {sol_count}, got {molecules['SOL']}"
        )

        # Custom molecule count
        assert self.mol_name in molecules, (
            f"Expected {self.mol_name} in [molecules], got {list(molecules.keys())}"
        )
        assert molecules[self.mol_name] == self.custom.custom_molecule_count, (
            f"Expected {self.mol_name} count {self.custom.custom_molecule_count}, "
            f"got {molecules[self.mol_name]}"
        )

    def test_top_includes_tip4p_ice_and_custom_itp(self, tmp_path):
        """TOP #include has tip4p-ice.itp and custom molecule ITP (original filename)."""
        top_path = str(tmp_path / "custom.top")
        write_custom_molecule_top_file(self.custom, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        # Custom ITP uses original filename from itp_path.name
        custom_itp_name = self.custom.itp_path.name
        assert custom_itp_name in includes, (
            f"Should include {custom_itp_name}, got {includes}"
        )

    def test_custom_itp_has_moleculetype(self):
        """Bundled custom molecule ITP exists and has [ moleculetype ] section."""
        itp_path = str(ETOH_ITP)

        assert Path(itp_path).exists(), f"Custom ITP not found at {itp_path}"
        assert check_itp_has_moleculetype(itp_path), (
            "Custom ITP should contain [ moleculetype ] section"
        )

    def test_tip4p_ice_itp_has_moleculetype(self):
        """Bundled tip4p-ice.itp exists and has [ moleculetype ] section."""
        data_dir = _get_data_dir()
        itp_path = str(data_dir / "tip4p-ice.itp")

        assert Path(itp_path).exists(), f"tip4p-ice.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(itp_path), (
            "tip4p-ice.itp should contain [ moleculetype ] section"
        )

    def test_atom_conservation(self, tmp_path):
        """Atom conservation: total atoms from molecule_index == GRO output positions.

        The writer expands ice 3->4 atoms, so output count differs from
        positions.shape[0]. We verify the OUTPUT atom count matches
        what molecule_index implies.
        """
        gro_path = str(tmp_path / "custom.gro")
        write_custom_molecule_gro_file(self.custom, gro_path)

        header_count = parse_gro_atom_count(gro_path)

        # Count atoms from molecule_index (accounting for ice 3->4 expansion)
        total_atoms = 0
        for mol in self.custom.molecule_index:
            if mol.mol_type == "ice":
                total_atoms += 4  # TIP4P-ICE: 3->4 expansion
            else:
                total_atoms += mol.count

        assert header_count == total_atoms, (
            f"Atom conservation: expected {total_atoms} atoms from molecule_index, "
            f"got {header_count} in GRO output"
        )
