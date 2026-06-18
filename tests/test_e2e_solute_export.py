"""End-to-end tests for Solute single-structure GROMACS export.

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
writer functions, validating that exported .gro and .top files are correct.

Two scenarios:
5. Solute from Interface Export — interface_slab → _insert_solutes → write_solute_gro/top_file
6. Solute from Custom Export — interface_slab → _insert_custom → _insert_solutes → write_solute_gro/top_file

CRITICAL: Registry MUST be populated before writer use (Pitfall 6).
SoluteInserter creates its own registry internally, so the registry
is properly populated in the SoluteStructure returned by insert_solutes().

IMPORTANT: SoluteStructure stores solute positions SEPARATELY from interface
positions. The writer accesses interface_structure for ice/water positions
and solute_structure.positions for solute atoms.

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
    write_solute_gro_file,
    write_solute_top_file,
)

# Import parsing helpers from the shared module (NOT from conftest)
from e2e_export_helpers import (
    _insert_custom_molecules,
    _insert_solutes,
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
# Scenario 5: Solute from Interface Export
# ══════════════════════════════════════════════════════════════════════════════


class TestSoluteFromInterface:
    """Validate Solute from Interface export.

    Solute from plain interface has SOL (ice+water) + solute residue (CH4_L).
    The solute residue name comes from registry.get_gromacs_name("liquid_CH4")
    which returns "CH4_L" (5 chars, fits GRO 5-char limit exactly).

    GRO residue ordering: SOL before solute (no interleaving).
    GRO atom count = ice*4 + water*4 + n_molecules*5 (CH4 = 5 atoms per molecule).
    TOP [molecules] = {"SOL": ice+water, "CH4_L": n_molecules}
    TOP #include = ["tip4p-ice.itp", "ch4_liquid.itp"]

    Note: interface_structure.molecule_index may be empty for real GenIce2 data.
    The writer uses ice_nmolecules/water_nmolecules as fallback.
    """

    @pytest.fixture(autouse=True)
    def _build_solute(self, interface_slab):
        """Build solute structure from interface for all tests in this class."""
        self.solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        self.interface = self.solute.interface_structure

    def test_gro_sol_before_solute_residues(self, tmp_path):
        """GRO file has SOL residues before solute residues with no interleaving."""
        gro_path = str(tmp_path / "solute.gro")
        write_solute_gro_file(self.solute, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "CH4_L" in unique_names, (
            f"Should have CH4_L residues, got {unique_names}"
        )

        # Verify ordering: SOL before CH4_L (no interleaving)
        assert_gro_residue_ordering(residue_names, ["SOL", "CH4_L"])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines.

        Expected = ice_nmolecules*4 + water_nmolecules*4 + n_molecules*5
        Note: water_nmolecules may differ from original interface because
        SoluteInserter removes overlapping water molecules.
        """
        gro_path = str(tmp_path / "solute.gro")
        write_solute_gro_file(self.solute, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Expected: ice*4 + water*4 + solute molecules * 5 (CH4 has 5 atoms)
        expected = (self.interface.ice_nmolecules * 4 +
                    self.interface.water_nmolecules * 4 +
                    self.solute.n_molecules * 5)
        assert header_count == expected, (
            f"Expected {expected} atoms "
            f"(ice={self.interface.ice_nmolecules}*4 + "
            f"water={self.interface.water_nmolecules}*4 + "
            f"solute={self.solute.n_molecules}*5), "
            f"got {header_count}"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has correct SOL and CH4_L counts."""
        top_path = str(tmp_path / "solute.top")
        write_solute_top_file(self.solute, top_path)

        molecules = parse_top_molecules(top_path)

        expected_sol = self.interface.ice_nmolecules + self.interface.water_nmolecules
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "CH4_L" in molecules, (
            f"Expected CH4_L in [molecules], got {list(molecules.keys())}"
        )
        assert molecules["CH4_L"] == self.solute.n_molecules, (
            f"Expected CH4_L count {self.solute.n_molecules}, "
            f"got {molecules['CH4_L']}"
        )

    def test_top_includes_tip4p_ice_and_solute_itp(self, tmp_path):
        """TOP #include has tip4p-ice.itp and ch4_liquid.itp."""
        top_path = str(tmp_path / "solute.top")
        write_solute_top_file(self.solute, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_liquid.itp" in includes, (
            f"Should include ch4_liquid.itp, got {includes}"
        )

    def test_solute_itp_has_moleculetype(self):
        """Bundled ch4_liquid.itp exists and has [ moleculetype ] section."""
        data_dir = _get_data_dir()
        itp_path = str(data_dir / "ch4_liquid.itp")

        assert Path(itp_path).exists(), f"ch4_liquid.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(itp_path), (
            "ch4_liquid.itp should contain [ moleculetype ] section"
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
        """Atom conservation: GRO output matches expected molecule counts.

        The writer expands ice 3→4 atoms, so we verify the total output
        atom count from the GRO file matches what the molecule counts imply.
        """
        gro_path = str(tmp_path / "solute.gro")
        write_solute_gro_file(self.solute, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        expected = (self.interface.ice_nmolecules * 4 +
                    self.interface.water_nmolecules * 4 +
                    self.solute.n_molecules * 5)

        assert header_count == expected, (
            f"Atom conservation: expected {expected} atoms "
            f"(ice*4 + water*4 + solute*5), got {header_count}"
        )

    def test_solute_positions_pbc_wrapped(self, tmp_path):
        """Solute atom positions must be within PBC box in GRO output.

        Regression test for B NEW-01/11: write_solute_gro_file did not
        PBC-wrap solute_structure.positions, producing invalid GRO files.
        Solute positions are a SEPARATE array from interface.positions,
        so wrap_molecules_into_box does NOT cover them.
        """
        gro_path = str(tmp_path / "solute_pbc_test.gro")
        write_solute_gro_file(self.solute, gro_path)

        # Parse GRO file for solute atom positions
        with open(gro_path) as f:
            lines = f.readlines()

        # Skip title (line 0), atom count (line 1), and box (last line)
        atom_lines = lines[2:-1]

        # Extract box dimensions from last line
        box_line = lines[-1].strip().split()
        box_x, box_y, box_z = float(box_line[0]), float(box_line[1]), float(box_line[2])

        # Find solute atoms (CH4_L or THF_L residue)
        solute_positions = []
        for line in atom_lines:
            res_name = line[5:10].strip()
            if res_name in ("CH4_L", "THF_L", "CH4_P"):
                x = float(line[20:28])
                y = float(line[28:36])
                z = float(line[36:44])
                solute_positions.append((x, y, z))

        assert len(solute_positions) > 0, "No solute atoms found in GRO output"

        # All solute positions must be within [0, box_dim + 0.01)
        tolerance = 0.01  # nm — float precision tolerance at boundaries
        for x, y, z in solute_positions:
            assert -tolerance <= x < box_x + tolerance, f"Solute x={x} outside PBC [0, {box_x})"
            assert -tolerance <= y < box_y + tolerance, f"Solute y={y} outside PBC [0, {box_y})"
            assert -tolerance <= z < box_z + tolerance, f"Solute z={z} outside PBC [0, {box_z})"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 6: Solute from Custom Export
# ══════════════════════════════════════════════════════════════════════════════


class TestSoluteFromCustom:
    """Validate Solute from Custom Molecule export.

    Chain: interface_slab → _insert_custom_molecules(3) → _insert_solutes('CH4', 0.3)
    Result has SOL (ice+water) + custom (MOL) + solute (CH4_L).

    GRO residue ordering: SOL before custom before solute (no interleaving).
    TOP [molecules] = {"SOL": ice+water, "etoh": 3, "CH4_L": n_molecules}
    TOP #include = ["tip4p-ice.itp", "etoh.itp", "ch4_liquid.itp"]

    Custom molecule GRO residue is "MOL" (from moleculetype_name in registry),
    but TOP [molecules] uses ITP moleculetype name "etoh" (Bug 2 fix). The
    custom ITP filename in #include uses the ORIGINAL filename "etoh.itp".

    NOTE: When the source is a CustomMoleculeStructure, the SoluteInserter
    modifies the interface and molecule_index is populated (from CustomMoleculeInserter).
    However, ice_nmolecules/water_nmolecules may be unreliable in this case.
    We compute expected counts from molecule_index when available.
    """

    @pytest.fixture(autouse=True)
    def _build_solute_from_custom(self, interface_slab):
        """Build custom→solute chain for all tests in this class."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.custom_mol_name = custom.moleculetype_name  # "MOL" from registry (GRO residue name)
        self.top_mol_name = "etoh"  # ITP moleculetype name (TOP [molecules] name, Bug 2 fix)
        self.solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.interface = self.solute.interface_structure

    def _sol_atom_count(self):
        """Count total SOL (ice+water) atoms accounting for TIP4P-ICE 3->4 expansion.

        Uses molecule_index when available, falls back to ice_nmolecules/water_nmolecules.
        """
        if self.interface.molecule_index:
            return sum(4 if m.mol_type == "ice" else m.count
                       for m in self.interface.molecule_index
                       if m.mol_type in ("ice", "water"))
        else:
            return self.interface.ice_nmolecules * 4 + self.interface.water_nmolecules * 4

    def _sol_molecule_count(self):
        """Count SOL (ice+water) molecule count.

        Uses molecule_index when available, falls back to ice_nmolecules/water_nmolecules.
        """
        if self.interface.molecule_index:
            return sum(1 for m in self.interface.molecule_index
                       if m.mol_type in ("ice", "water"))
        else:
            return self.interface.ice_nmolecules + self.interface.water_nmolecules

    def test_gro_sol_before_custom_before_solute(self, tmp_path):
        """GRO file has SOL before custom molecule before solute residues (no interleaving)."""
        gro_path = str(tmp_path / "solute_custom.gro")
        write_solute_gro_file(self.solute, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert self.custom_mol_name in unique_names, (
            f"Should have {self.custom_mol_name} residues, got {unique_names}"
        )
        assert "CH4_L" in unique_names, (
            f"Should have CH4_L residues, got {unique_names}"
        )

        # Verify ordering: SOL → custom → CH4_L (no interleaving)
        assert_gro_residue_ordering(residue_names, ["SOL", self.custom_mol_name, "CH4_L"])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines."""
        gro_path = str(tmp_path / "solute_custom.gro")
        write_solute_gro_file(self.solute, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Expected: SOL atoms + custom atoms + solute atoms
        expected = (self._sol_atom_count() +
                    self.solute.custom_molecule_atom_count +
                    self.solute.n_molecules * 5)
        assert header_count == expected, (
            f"Expected {expected} atoms, got {header_count}"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has SOL, custom molecule, and CH4_L counts."""
        top_path = str(tmp_path / "solute_custom.top")
        write_solute_top_file(self.solute, top_path)

        molecules = parse_top_molecules(top_path)

        # SOL count = ice + water
        expected_sol = self._sol_molecule_count()
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        # Custom molecule count (TOP uses ITP moleculetype name "etoh")
        assert self.top_mol_name in molecules, (
            f"Expected {self.top_mol_name} in [molecules], got {list(molecules.keys())}"
        )
        assert molecules[self.top_mol_name] == self.solute.custom_molecule_count, (
            f"Expected {self.top_mol_name} count {self.solute.custom_molecule_count}, "
            f"got {molecules[self.top_mol_name]}"
        )

        # Solute molecule count
        assert "CH4_L" in molecules, (
            f"Expected CH4_L in [molecules], got {list(molecules.keys())}"
        )
        assert molecules["CH4_L"] == self.solute.n_molecules, (
            f"Expected CH4_L count {self.solute.n_molecules}, "
            f"got {molecules['CH4_L']}"
        )

    def test_top_includes_all_itps(self, tmp_path):
        """TOP #include has tip4p-ice.itp, custom ITP, and ch4_liquid.itp in order."""
        top_path = str(tmp_path / "solute_custom.top")
        write_solute_top_file(self.solute, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        # Custom ITP uses original filename from custom_itp_path
        custom_itp_name = Path(self.solute.custom_itp_path).name
        assert custom_itp_name in includes, (
            f"Should include {custom_itp_name}, got {includes}"
        )
        assert "ch4_liquid.itp" in includes, (
            f"Should include ch4_liquid.itp, got {includes}"
        )

        # Verify ordering: tip4p-ice before custom before solute
        tip4p_idx = includes.index("tip4p-ice.itp")
        custom_idx = includes.index(custom_itp_name)
        solute_idx = includes.index("ch4_liquid.itp")
        assert tip4p_idx < custom_idx < solute_idx, (
            f"ITP ordering: tip4p-ice({tip4p_idx}) < custom({custom_idx}) < solute({solute_idx})"
        )

    def test_itp_files_have_moleculetype(self):
        """All referenced ITP files exist and have [ moleculetype ] section."""
        data_dir = _get_data_dir()

        # tip4p-ice.itp
        itp_path = str(data_dir / "tip4p-ice.itp")
        assert Path(itp_path).exists(), f"tip4p-ice.itp not found"
        assert check_itp_has_moleculetype(itp_path), "tip4p-ice.itp needs [ moleculetype ]"

        # ch4_liquid.itp
        itp_path = str(data_dir / "ch4_liquid.itp")
        assert Path(itp_path).exists(), f"ch4_liquid.itp not found"
        assert check_itp_has_moleculetype(itp_path), "ch4_liquid.itp needs [ moleculetype ]"

        # etoh.itp (custom)
        itp_path = str(ETOH_ITP)
        assert Path(itp_path).exists(), f"etoh.itp not found"
        assert check_itp_has_moleculetype(itp_path), "etoh.itp needs [ moleculetype ]"

    def test_custom_molecule_count_preserved(self):
        """Custom molecule count is preserved through solute insertion."""
        assert self.solute.custom_molecule_count == 3, (
            f"Expected custom_molecule_count=3, got {self.solute.custom_molecule_count}"
        )

    def test_atom_conservation(self, tmp_path):
        """Atom conservation: GRO output matches expected molecule counts."""
        gro_path = str(tmp_path / "solute_custom.gro")
        write_solute_gro_file(self.solute, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        expected = (self._sol_atom_count() +
                    self.solute.custom_molecule_atom_count +
                    self.solute.n_molecules * 5)

        assert header_count == expected, (
            f"Atom conservation: expected {expected} atoms "
            f"(SOL + custom + solute*5), got {header_count}"
        )
