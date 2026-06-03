"""End-to-end tests for simple chain export scenarios F5-F7.

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
ion writer functions, validating that exported .gro and .top files are correct
for three simple chain scenarios:

F5: Interface→Ion (minimal chain)
F6: Interface→Solute(CH4)→Ion
F7: Interface→Solute(THF)→Ion

CRITICAL NOTES:
- F5 uses _insert_ions() directly (no BUG I5 workaround needed)
- F6/F7 use _insert_ions_from_solute() with BUG I5 workaround
- Custom molecule residue name is "MOL" (from moleculetype_name), NOT "ETOH"
- THF solute (THF_L) has 13 atoms per molecule, CH4 solute (CH4_L) has 5
- ion.itp must be generated to tmp_path before write_ion_top_file
- SOL counts should come from ion.molecule_index (not original interface counts)

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

# Import parsing helpers and chain-building helpers from the shared module
from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    parse_top_includes,
    check_itp_has_moleculetype,
    assert_gro_residue_ordering,
    _insert_ions,
    _insert_ions_from_solute,
    _insert_solutes,
)


# ── Helper: locate bundled ITP files ─────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


# ── Constants ────────────────────────────────────────────────────────────────

THF_ATOMS_PER_MOLECULE = 13
CH4_ATOMS_PER_MOLECULE = 5


# ══════════════════════════════════════════════════════════════════════════════
# F5: Interface→Ion (minimal chain)
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF5:
    """Validate F5: Interface→Ion export via write_ion_gro_file / write_ion_top_file.

    F5 is the minimal chain: only SOL (ice+water), NA, CL.
    No guests, no custom molecules, no solutes.
    Uses _insert_ions() directly (no BUG I5 workaround needed).

    GRO residue names: SOL→NA→CL (3 molecule types)
    TOP [molecules]: SOL, NA, CL
    TOP #include: ["tip4p-ice.itp", "ion.itp"] (2 ITPs — minimal)
    """

    def test_gro_sol_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL before NA before CL (3 molecule types, no interleaving)."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        gro_path = str(tmp_path / "f5_chain.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"
        assert len(unique_names) == 3, f"Should have exactly 3 molecule types, got {unique_names}"

        # Verify ordering: SOL → NA → CL (no interleaving)
        assert_gro_residue_ordering(residue_names, ["SOL", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        gro_path = str(tmp_path / "f5_chain.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Also verify against IonStructure molecule_index counts
        ice_count = sum(1 for m in ion.molecule_index if m.mol_type == "ice")
        water_count = sum(1 for m in ion.molecule_index if m.mol_type == "water")
        expected = ice_count * 4 + water_count * 4 + ion.na_count + ion.cl_count
        assert header_count == expected, (
            f"Expected {expected} atoms (ice*4 + water*4 + na+cl), got {header_count}"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has SOL, NA, CL counts."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f5_chain.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        # SOL count comes from ion.molecule_index (some water replaced by ions)
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count

    def test_top_includes_minimal_itps(self, interface_slab, tmp_path):
        """TOP #include has exactly 2 ITPs: tip4p-ice.itp and ion.itp (minimal)."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f5_chain.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ion.itp" in includes, "Should include ion.itp"
        assert len(includes) == 2, (
            f"F5 (minimal chain) should have exactly 2 ITPs, got {len(includes)}: {includes}"
        )

    def test_itp_files_valid(self, interface_slab, tmp_path):
        """ITP files exist and have [ moleculetype ] sections."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, ion.na_count, ion.cl_count)

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

    def test_no_guests_custom_solutes(self, interface_slab, tmp_path):
        """F5 chain has no guests, no custom molecules, no solutes."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        assert ion.custom_molecule_count == 0, (
            f"F5 should have no custom molecules, got {ion.custom_molecule_count}"
        )
        assert ion.solute_n_molecules == 0, (
            f"F5 should have no solutes, got {ion.solute_n_molecules}"
        )
        # guest_count from molecule_index
        guest_count = sum(1 for m in ion.molecule_index if m.mol_type == "guest")
        assert guest_count == 0, (
            f"F5 should have no guests, got {guest_count}"
        )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: molecule_index sum == positions.shape[0]; charge neutrality: na==cl."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Atom conservation: sum of molecule_index counts == positions rows
        total_from_index = sum(m.count for m in ion.molecule_index)
        total_positions = ion.positions.shape[0]
        assert total_from_index == total_positions, (
            f"Atom conservation: molecule_index sums to {total_from_index} "
            f"but positions has {total_positions} rows"
        )

        # Charge neutrality: equal Na+ and Cl- counts
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F6: Interface→Solute(CH4)→Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF6:
    """Validate F6: Interface→Solute(CH4)→Ion export.

    CRITICAL: Uses _insert_ions_from_solute() with BUG I5 workaround.
    Without this workaround, IonInserter raises AttributeError.

    Chain: interface_slab → _insert_solutes(CH4, 0.3) → _insert_ions_from_solute(0.15)
    Register: registry.register_liquid_solute("CH4") before insert_solutes

    GRO residue names: SOL→CH4_L→NA→CL (4 molecule types)
    TOP [molecules]: SOL, CH4_L, NA, CL
    TOP #include: ["tip4p-ice.itp", "ch4_liquid.itp", "ion.itp"] (3 ITPs)
    """

    def _build_f6_chain(self, interface_slab):
        """Build F6 chain: Interface→Solute(CH4)→Ion."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        # CRITICAL: Uses BUG I5 workaround
        ion = _insert_ions_from_solute(solute, concentration=0.15)
        return ion, solute

    def test_gro_sol_before_ch4l_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL→CH4_L→NA→CL (4 molecule types, no custom)."""
        ion, solute = self._build_f6_chain(interface_slab)

        gro_path = str(tmp_path / "f6_chain.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "CH4_L" in unique_names, "Should have CH4_L (solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"
        assert len(unique_names) == 4, (
            f"F6 should have exactly 4 molecule types, got {unique_names}"
        )

        # Verify ordering: SOL → CH4_L → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "CH4_L", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        ion, solute = self._build_f6_chain(interface_slab)

        gro_path = str(tmp_path / "f6_chain.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has SOL, CH4_L, NA, CL counts."""
        ion, solute = self._build_f6_chain(interface_slab)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f6_chain.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol

        assert "CH4_L" in molecules, "TOP should list CH4_L solute molecule"
        assert molecules["CH4_L"] == solute.n_molecules, (
            f"Expected CH4_L count {solute.n_molecules}, got {molecules['CH4_L']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count

    def test_top_includes_three_itps(self, interface_slab, tmp_path):
        """TOP #include has exactly 3 ITPs: tip4p-ice.itp, ch4_liquid.itp, ion.itp."""
        ion, solute = self._build_f6_chain(interface_slab)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f6_chain.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_liquid.itp" in includes, "Should include ch4_liquid.itp for solutes"
        assert "ion.itp" in includes, "Should include ion.itp"
        assert len(includes) == 3, (
            f"F6 should have exactly 3 ITPs, got {len(includes)}: {includes}"
        )

    def test_no_custom_molecules(self, interface_slab, tmp_path):
        """F6 chain has no custom molecules."""
        ion, solute = self._build_f6_chain(interface_slab)

        assert ion.custom_molecule_count == 0, (
            f"F6 should have no custom molecules, got {ion.custom_molecule_count}"
        )

    def test_solute_preserved(self, interface_slab, tmp_path):
        """Solute information is preserved in IonStructure after BUG I5 workaround."""
        ion, solute = self._build_f6_chain(interface_slab)

        assert ion.solute_type == "CH4", (
            f"IonStructure.solute_type should be 'CH4', got '{ion.solute_type}'"
        )
        assert ion.solute_n_molecules > 0, (
            f"IonStructure.solute_n_molecules should be > 0, got {ion.solute_n_molecules}"
        )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: molecule_index sum == positions.shape[0]; charge neutrality."""
        ion, solute = self._build_f6_chain(interface_slab)

        # Atom conservation
        total_from_index = sum(m.count for m in ion.molecule_index)
        total_positions = ion.positions.shape[0]
        assert total_from_index == total_positions, (
            f"Atom conservation: molecule_index sums to {total_from_index} "
            f"but positions has {total_positions} rows"
        )

        # Charge neutrality
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F7: Interface→Solute(THF)→Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF7:
    """Validate F7: Interface→Solute(THF)→Ion export.

    CRITICAL: Uses _insert_ions_from_solute() with BUG I5 workaround.

    Chain: interface_slab → _insert_solutes(THF, 0.15) → _insert_ions_from_solute(0.15)
    Register: registry.register_liquid_solute("THF") before insert_solutes

    GRO residue names: SOL→THF_L→NA→CL (4 molecule types)
    TOP [molecules]: SOL, THF_L, NA, CL
    TOP #include: ["tip4p-ice.itp", "thf_liquid.itp", "ion.itp"] (3 ITPs)

    IMPORTANT: THF_L has 13 atoms per molecule (vs CH4_L which has 5).
    """

    def _build_f7_chain(self, interface_slab):
        """Build F7 chain: Interface→Solute(THF)→Ion."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("THF")

        solute = _insert_solutes(interface_slab, solute_type='THF', concentration=0.15)
        # CRITICAL: Uses BUG I5 workaround
        ion = _insert_ions_from_solute(solute, concentration=0.15)
        return ion, solute

    def test_gro_sol_before_thfl_before_na_before_cl(self, interface_slab, tmp_path):
        """GRO file has SOL→THF_L→NA→CL (THF = 5 chars, fits GRO limit)."""
        ion, solute = self._build_f7_chain(interface_slab)

        gro_path = str(tmp_path / "f7_chain.gro")
        write_ion_gro_file(ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "THF_L" in unique_names, "Should have THF_L (solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"
        assert len(unique_names) == 4, (
            f"F7 should have exactly 4 molecule types, got {unique_names}"
        )

        # Verify ordering: SOL → THF_L → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "THF_L", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines."""
        ion, solute = self._build_f7_chain(interface_slab)

        gro_path = str(tmp_path / "f7_chain.gro")
        write_ion_gro_file(ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has SOL, THF_L, NA, CL counts."""
        ion, solute = self._build_f7_chain(interface_slab)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f7_chain.top")
        write_ion_top_file(ion, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        expected_sol = sum(1 for m in ion.molecule_index if m.mol_type in ("ice", "water"))
        assert molecules["SOL"] == expected_sol

        assert "THF_L" in molecules, "TOP should list THF_L solute molecule"
        assert molecules["THF_L"] == solute.n_molecules, (
            f"Expected THF_L count {solute.n_molecules}, got {molecules['THF_L']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == ion.cl_count

    def test_top_includes_three_itps(self, interface_slab, tmp_path):
        """TOP #include has exactly 3 ITPs: tip4p-ice.itp, thf_liquid.itp, ion.itp."""
        ion, solute = self._build_f7_chain(interface_slab)

        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = str(tmp_path / "f7_chain.top")
        write_ion_top_file(ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "thf_liquid.itp" in includes, "Should include thf_liquid.itp for THF solutes"
        assert "ion.itp" in includes, "Should include ion.itp"
        assert len(includes) == 3, (
            f"F7 should have exactly 3 ITPs, got {len(includes)}: {includes}"
        )

    def test_solute_preserved_thf(self, interface_slab, tmp_path):
        """Solute information is preserved in IonStructure with THF type."""
        ion, solute = self._build_f7_chain(interface_slab)

        assert ion.solute_type == "THF", (
            f"IonStructure.solute_type should be 'THF', got '{ion.solute_type}'"
        )
        assert ion.solute_n_molecules > 0, (
            f"IonStructure.solute_n_molecules should be > 0, got {ion.solute_n_molecules}"
        )

    def test_thf_atom_count_per_molecule(self, interface_slab, tmp_path):
        """THF_L has 13 atoms per molecule (not 5 like CH4)."""
        ion, solute = self._build_f7_chain(interface_slab)

        # Each THF_L solute molecule has 13 atoms
        # solute_molecule_indices stores (start, end) tuples relative to solute_positions
        for start, end in ion.solute_molecule_indices:
            atoms_per_mol = end - start
            assert atoms_per_mol == THF_ATOMS_PER_MOLECULE, (
                f"THF_L should have {THF_ATOMS_PER_MOLECULE} atoms per molecule, "
                f"got {atoms_per_mol}"
            )

    def test_atom_conservation_and_charge_neutrality(self, interface_slab, tmp_path):
        """Atom conservation: molecule_index sum == positions.shape[0]; charge neutrality."""
        ion, solute = self._build_f7_chain(interface_slab)

        # Atom conservation
        total_from_index = sum(m.count for m in ion.molecule_index)
        total_positions = ion.positions.shape[0]
        assert total_from_index == total_positions, (
            f"Atom conservation: molecule_index sums to {total_from_index} "
            f"but positions has {total_positions} rows"
        )

        # Charge neutrality
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
        )
