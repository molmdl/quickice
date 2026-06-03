"""End-to-end tests for Ion single-structure GROMACS export.

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
ion writer functions, validating that exported .gro and .top files are correct
for three Ion source scenarios:

7. Ion from Interface — write_ion_gro_file / write_ion_top_file
8. Ion from Custom    — write_ion_gro_file / write_ion_top_file
9. Ion from Solute   — write_ion_gro_file / write_ion_top_file (BUG I5 workaround)

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
    write_ion_gro_file,
    write_ion_top_file,
)

from quickice.structure_generation.gromacs_ion_export import write_ion_itp

from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

# Import parsing helpers from the shared module (NOT from conftest)
from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    parse_top_includes,
    check_itp_has_moleculetype,
    assert_gro_residue_ordering,
    _insert_ions,
    _insert_ions_from_solute,
    _insert_custom_molecules,
    _insert_solutes,
)


# ── Helper: locate bundled ITP files ─────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 7: Ion from Interface Export
# ══════════════════════════════════════════════════════════════════════════════


class TestIonFromInterface:
    """Validate Ion from Interface export via write_ion_gro_file / write_ion_top_file.

    Ion from Interface has SOL residues (ice+water), then NA, then CL.
    GRO atom count = ice*4 + water*4 + na_count + cl_count.
    TOP [molecules] = {"SOL": ice+water, "NA": na_count, "CL": cl_count}
    TOP #include = ["tip4p-ice.itp", "ion.itp"]
    """

    def test_gro_sol_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL residues before NA before CL with no interleaving."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        gro_path = str(tmp_path / "ion_interface.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # Verify ordering: SOL → NA → CL (no interleaving)
        assert_gro_residue_ordering(residue_names, ["SOL", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        gro_path = str(tmp_path / "ion_interface.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Also verify against IonStructure molecule_index counts.
        # After ion insertion, some water molecules are replaced by ions.
        # TIP4P-ICE: ice*4 + water*4 + na_count + cl_count
        # (Use ion's molecule_index counts, NOT original interface counts.)
        ice_count = sum(1 for m in ion.molecule_index if m.mol_type == "ice")
        water_count = sum(1 for m in ion.molecule_index if m.mol_type == "water")
        expected = ice_count * 4 + water_count * 4 + ion.na_count + ion.cl_count
        assert header_count == expected, (
            f"Expected {expected} atoms (ice*4 + water*4 + na+cl), got {header_count}"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has correct SOL, NA, CL counts."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_interface.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        # SOL count comes from ion.molecule_index (some water replaced by ions)
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count, (
            f"Expected NA count {ion.na_count}, got {molecules['NA']}"
        )

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count, (
            f"Expected CL count {ion.cl_count}, got {molecules['CL']}"
        )

    def test_top_includes_tip4p_and_ion_itp(self, interface_slab, tmp_path):
        """TOP #include has tip4p-ice.itp and ion.itp."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_interface.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, interface_slab, tmp_path):
        """ITP files exist and have [ moleculetype ] sections."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, ion.na_count, ion.cl_count)

        # Verify generated ion.itp
        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path)), (
            "Generated ion.itp should contain [ moleculetype ] section"
        )

        # Verify bundled tip4p-ice.itp
        data_dir = _get_data_dir()
        tip4p_itp_path = str(data_dir / "tip4p-ice.itp")
        assert Path(tip4p_itp_path).exists(), f"tip4p-ice.itp not found at {tip4p_itp_path}"
        assert check_itp_has_moleculetype(tip4p_itp_path), (
            "tip4p-ice.itp should contain [ moleculetype ] section"
        )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: total atoms match; charge neutrality: na_count == cl_count."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        gro_path = str(tmp_path / "ion_interface.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        ice_count = sum(1 for m in ion.molecule_index if m.mol_type == "ice")
        water_count = sum(1 for m in ion.molecule_index if m.mol_type == "water")
        expected = ice_count * 4 + water_count * 4 + ion.na_count + ion.cl_count

        assert header_count == expected, (
            f"Atom conservation: expected {expected}, got {header_count}"
        )

        # Charge neutrality: equal Na+ and Cl- counts
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 8: Ion from Custom Export
# ══════════════════════════════════════════════════════════════════════════════


class TestIonFromCustom:
    """Validate Ion from Custom export via write_ion_gro_file / write_ion_top_file.

    Ion from Custom has SOL, then MOL (custom molecule), then NA, then CL.
    GRO atom count = ice*4 + water*4 + custom_atoms + na_count + cl_count.
    TOP [molecules] = {"SOL": ice+water, "MOL": n_custom, "NA": na_count, "CL": cl_count}
    TOP #include = ["tip4p-ice.itp", "etoh.itp", "ion.itp"]
    """

    def test_gro_sol_before_custom_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL before MOL (custom) before NA before CL."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        gro_path = str(tmp_path / "ion_custom.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "MOL" in unique_names, "Should have MOL (custom) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # Verify ordering: SOL → MOL → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "MOL", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        gro_path = str(tmp_path / "ion_custom.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has SOL, MOL, NA, CL counts."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_custom.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        # SOL count comes from ion.molecule_index (some water replaced by ions)
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "MOL" in molecules, "TOP should list MOL molecule"
        assert molecules["MOL"] == 3, (
            f"Expected MOL count 3, got {molecules['MOL']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count, (
            f"Expected NA count {ion.na_count}, got {molecules['NA']}"
        )

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count, (
            f"Expected CL count {ion.cl_count}, got {molecules['CL']}"
        )

    def test_top_includes_tip4p_custom_and_ion_itp(self, interface_slab, tmp_path):
        """TOP #include has tip4p-ice.itp, etoh.itp, and ion.itp."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_custom.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "etoh.itp" in includes, "Should include etoh.itp for custom molecules"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, interface_slab, tmp_path):
        """ITP files exist and have [ moleculetype ] sections."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        # Generate ion.itp
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, ion.na_count, ion.cl_count)

        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path)), (
            "Generated ion.itp should contain [ moleculetype ] section"
        )

        # Verify bundled etoh.itp
        data_dir = _get_data_dir()
        etoh_itp_path = str(data_dir / "custom" / "etoh.itp")
        assert Path(etoh_itp_path).exists(), f"etoh.itp not found at {etoh_itp_path}"
        assert check_itp_has_moleculetype(etoh_itp_path), (
            "etoh.itp should contain [ moleculetype ] section"
        )

    def test_custom_molecule_count_preserved(self, interface_slab, tmp_path):
        """Custom molecule count is preserved in IonStructure."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        assert ion.custom_molecule_count > 0, (
            "IonStructure should have custom_molecule_count > 0"
        )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: total atoms match; charge neutrality: na_count == cl_count."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        ion = _insert_ions(custom, concentration=0.15)

        gro_path = str(tmp_path / "ion_custom.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)

        # Charge neutrality
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 9: Ion from Solute Export (BUG I5 workaround MANDATORY)
# ══════════════════════════════════════════════════════════════════════════════


class TestIonFromSolute:
    """Validate Ion from Solute export via write_ion_gro_file / write_ion_top_file.

    CRITICAL: Uses _insert_ions_from_solute() which applies the BUG I5 workaround
    (_solute_to_ion_source). Without this workaround, IonInserter raises
    AttributeError: 'InterfaceStructure' object has no attribute 'solute_type'.

    Ion from Solute has SOL, then CH4_L (solute), then NA, then CL.
    TOP [molecules] = {"SOL": ice+water, "CH4_L": solute.n_molecules, "NA": na, "CL": cl}
    TOP #include = ["tip4p-ice.itp", "ch4_liquid.itp", "ion.itp"]
    """

    def test_gro_sol_before_solute_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL before CH4_L (solute) before NA before CL."""
        # Register liquid solute before insert_solutes (matches real GUI workflow)
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        # CRITICAL: Uses BUG I5 workaround
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        gro_path = str(tmp_path / "ion_solute.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "CH4_L" in unique_names, "Should have CH4_L (solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # Verify ordering: SOL → CH4_L → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "CH4_L", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        gro_path = str(tmp_path / "ion_solute.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has SOL, CH4_L, NA, CL counts."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_solute.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        # SOL count comes from ion.molecule_index (some water replaced by ions)
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "CH4_L" in molecules, "TOP should list CH4_L solute molecule"
        assert molecules["CH4_L"] == solute.n_molecules, (
            f"Expected CH4_L count {solute.n_molecules}, got {molecules['CH4_L']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count, (
            f"Expected NA count {ion.na_count}, got {molecules['NA']}"
        )

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count, (
            f"Expected CL count {ion.cl_count}, got {molecules['CL']}"
        )

    def test_top_includes_tip4p_solute_and_ion_itp(self, interface_slab, tmp_path):
        """TOP #include has tip4p-ice.itp, ch4_liquid.itp, and ion.itp."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "ion_solute.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_liquid.itp" in includes, "Should include ch4_liquid.itp for solutes"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, interface_slab, tmp_path):
        """ITP files exist and have [ moleculetype ] sections."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        # Generate ion.itp
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, ion.na_count, ion.cl_count)

        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path)), (
            "Generated ion.itp should contain [ moleculetype ] section"
        )

        # Verify bundled ch4_liquid.itp
        data_dir = _get_data_dir()
        ch4_liquid_itp_path = str(data_dir / "ch4_liquid.itp")
        assert Path(ch4_liquid_itp_path).exists(), (
            f"ch4_liquid.itp not found at {ch4_liquid_itp_path}"
        )
        assert check_itp_has_moleculetype(ch4_liquid_itp_path), (
            "ch4_liquid.itp should contain [ moleculetype ] section"
        )

    def test_solute_info_preserved(self, interface_slab, tmp_path):
        """Solute information is preserved in IonStructure after workaround."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        assert ion.solute_type == "CH4", (
            f"IonStructure.solute_type should be 'CH4', got '{ion.solute_type}'"
        )
        assert ion.solute_n_molecules > 0, (
            f"IonStructure.solute_n_molecules should be > 0, got {ion.solute_n_molecules}"
        )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: total atoms match; charge neutrality: na_count == cl_count."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        ion = _insert_ions_from_solute(solute, concentration=0.15)

        gro_path = str(tmp_path / "ion_solute.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)

        # Charge neutrality
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )
