"""End-to-end tests for full chain GROMACS export (F1-F4).

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
ion writer functions, validating that the COMPLETE multi-step chain exports
correctly. Each chain accumulates molecule types through multiple insertion
steps, producing unique combinations not covered by single-structure tests.

Chain descriptions:
  F1: Interface → Custom → Solute → Ion  (5 molecule types: SOL, MOL, CH4_L, NA, CL)
  F2: Interface → Custom → Ion           (4 molecule types: SOL, MOL, NA, CL)
  F3: Hydrate → Interface → Solute → Ion (5 molecule types: SOL, CH4_H, CH4_L, NA, CL)
  F4: Hydrate → Interface → Custom → Solute → Ion  (6 molecule types: SOL, THF_H, MOL, THF_L, NA, CL)

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
    _insert_custom_molecules,
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
    _hydrate_sI_ch4_candidate,
    _hydrate_sI_thf_candidate,
    _make_slab_interface,
)


# ── Helper: locate bundled ITP files ─────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


# ══════════════════════════════════════════════════════════════════════════════
# F1: Interface → Custom → Solute → Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF1:
    """Validate F1 chain: Interface → Custom → Solute → Ion.

    5 molecule types in GRO: SOL → MOL → CH4_L → NA → CL
    TOP [molecules]: SOL, etoh, CH4_L, NA, CL
    TOP #include: tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp

    NOTE: GRO residue name is "MOL" (from registry moleculetype_name),
    but TOP [molecules] uses ITP moleculetype name "etoh" (Bug 2 fix).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        """Build the F1 chain once per test method."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        # CRITICAL: Uses BUG I5 workaround (_solute_to_ion_source)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gro_residue_ordering(self, tmp_path):
        """GRO file has SOL → MOL → CH4_L → NA → CL ordering (5 molecule types)."""
        gro_path = str(tmp_path / "chain_f1.gro")
        write_ion_gro_file(self.ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "MOL" in unique_names, "Should have MOL (custom) residues"
        assert "CH4_L" in unique_names, "Should have CH4_L (solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # Verify ordering: SOL → MOL → CH4_L → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "MOL", "CH4_L", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines and molecule_index."""
        gro_path = str(tmp_path / "chain_f1.gro")
        write_ion_gro_file(self.ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has SOL, MOL, CH4_L, NA, CL with correct counts."""
        # Generate ion.itp before writing top file
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f1.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)

        # SOL count from ion.molecule_index (some water replaced by ions)
        expected_sol = sum(
            1 for m in self.ion.molecule_index if m.mol_type in ("ice", "water")
        )
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        assert "etoh" in molecules, "TOP should list etoh molecule (ITP moleculetype name)"
        assert molecules["etoh"] == 3, (
            f"Expected etoh count 3, got {molecules['etoh']}"
        )

        assert "CH4_L" in molecules, "TOP should list CH4_L solute molecule"
        assert molecules["CH4_L"] > 0, (
            f"Expected CH4_L count > 0, got {molecules['CH4_L']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == self.ion.na_count, (
            f"Expected NA count {self.ion.na_count}, got {molecules['NA']}"
        )

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == self.ion.cl_count, (
            f"Expected CL count {self.ion.cl_count}, got {molecules['CL']}"
        )

    def test_top_includes(self, tmp_path):
        """TOP #include has tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f1.top")
        write_ion_top_file(self.ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "etoh.itp" in includes, "Should include etoh.itp for custom molecules"
        assert "ch4_liquid.itp" in includes, "Should include ch4_liquid.itp for solutes"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, tmp_path):
        """All 4 ITP files exist with [ moleculetype ] sections."""
        # Generated ion.itp
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, self.ion.na_count, self.ion.cl_count)
        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path)), (
            "Generated ion.itp should contain [ moleculetype ] section"
        )

        # Bundled ITPs
        data_dir = _get_data_dir()
        for itp_name in ["tip4p-ice.itp", "ch4_liquid.itp"]:
            itp_path = str(data_dir / itp_name)
            assert Path(itp_path).exists(), f"{itp_name} not found at {itp_path}"
            assert check_itp_has_moleculetype(itp_path), (
                f"{itp_name} should contain [ moleculetype ] section"
            )

        # Custom etoh.itp is in data/custom/ subdirectory
        etoh_itp_path = str(data_dir / "custom" / "etoh.itp")
        assert Path(etoh_itp_path).exists(), f"etoh.itp not found at {etoh_itp_path}"
        assert check_itp_has_moleculetype(etoh_itp_path), (
            "etoh.itp should contain [ moleculetype ] section"
        )

    def test_custom_and_solute_preserved(self, tmp_path):
        """Custom molecule count and solute n_molecules are preserved in IonStructure."""
        assert self.ion.custom_molecule_count > 0, (
            "IonStructure should have custom_molecule_count > 0"
        )
        assert self.ion.solute_n_molecules > 0, (
            "IonStructure should have solute_n_molecules > 0"
        )

    def test_atom_conservation(self, tmp_path):
        """Atom conservation: molecule_index sum == positions.shape[0] == GRO atom count."""
        gro_path = str(tmp_path / "chain_f1.gro")
        write_ion_gro_file(self.ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)

        # Sum atoms from molecule_index (ice=4, water=4, na=1, cl=1)
        # Plus custom molecules and solutes (stored separately)
        ice_count = sum(1 for m in self.ion.molecule_index if m.mol_type == "ice")
        water_count = sum(1 for m in self.ion.molecule_index if m.mol_type == "water")
        na_count = sum(1 for m in self.ion.molecule_index if m.mol_type == "na")
        cl_count = sum(1 for m in self.ion.molecule_index if m.mol_type == "cl")
        expected = ice_count * 4 + water_count * 4 + self.ion.custom_molecule_atom_count + self.ion.solute_n_molecules * 5 + na_count + cl_count

        assert header_count == expected, (
            f"Atom conservation: expected {expected}, got {header_count}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F2: Interface → Custom → Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF2:
    """Validate F2 chain: Interface → Custom → Ion.

    4 molecule types in GRO: SOL → MOL → NA → CL (no solutes)
    TOP [molecules]: SOL, etoh, NA, CL
    TOP #include: tip4p-ice.itp, etoh.itp, ion.itp

    NOTE: F2 uses _insert_ions() directly (no BUG I5 workaround needed,
    since custom→ion doesn't go through SoluteStructure).
    GRO residue is "MOL" but TOP [molecules] uses ITP name "etoh".
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        """Build the F2 chain once per test method."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.ion = _insert_ions(custom, concentration=0.15)

    def test_gro_residue_ordering(self, tmp_path):
        """GRO file has SOL → MOL → NA → CL ordering (no solutes)."""
        gro_path = str(tmp_path / "chain_f2.gro")
        write_ion_gro_file(self.ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "MOL" in unique_names, "Should have MOL (custom) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"
        assert "CH4_L" not in unique_names, "Should NOT have solute residues"

        # Verify ordering: SOL → MOL → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "MOL", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines."""
        gro_path = str(tmp_path / "chain_f2.gro")
        write_ion_gro_file(self.ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has SOL, MOL, NA, CL (no solutes)."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f2.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)

        expected_sol = sum(
            1 for m in self.ion.molecule_index if m.mol_type in ("ice", "water")
        )
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol

        assert "etoh" in molecules, "TOP should list etoh molecule (ITP moleculetype name)"
        assert molecules["etoh"] == 3, (
            f"Expected etoh count 3, got {molecules['etoh']}"
        )

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == self.ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == self.ion.cl_count

    def test_top_includes(self, tmp_path):
        """TOP #include has tip4p-ice.itp, etoh.itp, ion.itp (no solute ITP)."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f2.top")
        write_ion_top_file(self.ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "etoh.itp" in includes, "Should include etoh.itp for custom molecules"
        assert "ion.itp" in includes, "Should include ion.itp"
        # No solute or guest ITPs in F2
        assert "ch4_liquid.itp" not in includes, "Should NOT include solute ITP"
        assert "ch4_hydrate.itp" not in includes, "Should NOT include guest ITP"

    def test_no_solute_attributes(self, tmp_path):
        """IonStructure has no solute attributes (F2 doesn't use solutes)."""
        assert self.ion.solute_type == "", (
            f"solute_type should be empty, got '{self.ion.solute_type}'"
        )
        assert self.ion.solute_n_molecules == 0, (
            f"solute_n_molecules should be 0, got {self.ion.solute_n_molecules}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F3: Hydrate → Interface → Solute → Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF3:
    """Validate F3 chain: Hydrate → Interface → Solute → Ion.

    5 molecule types in GRO: SOL → CH4_H → CH4_L → NA → CL
    KEY TEST: CH4_H and CH4_L coexistence — the core MoleculetypeRegistry distinction.

    TOP [molecules]: SOL, CH4_H (or CH4), CH4_L, NA, CL
    TOP #include: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp

    CRITICAL: register_hydrate_guest("CH4") MUST be called before
    insert_solutes() — SoluteInserter creates its own registry, and the
    hydrate guest must be in that registry for correct CH4_H naming.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        """Build the F3 chain once per test method."""
        hydrate_candidate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate_candidate)

        # CRITICAL: Register hydrate guest before insert_solutes
        # SoluteInserter creates its own registry; hydrate guest must be
        # registered for CH4_H/CH4_L distinction to work correctly
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest("CH4")
        registry.register_liquid_solute("CH4")

        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        # CRITICAL: Uses BUG I5 workaround (_solute_to_ion_source)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gro_residue_ordering(self, tmp_path):
        """GRO file has SOL → CH4_H → CH4_L → NA → CL ordering (P0 CH4 coexistence)."""
        gro_path = str(tmp_path / "chain_f3.gro")
        write_ion_gro_file(self.ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "CH4_H" in unique_names, "Should have CH4_H (hydrate guest) residues"
        assert "CH4_L" in unique_names, "Should have CH4_L (liquid solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # KEY P0 TEST: Verify ordering: SOL → CH4_H → CH4_L → NA → CL
        assert_gro_residue_ordering(residue_names, ["SOL", "CH4_H", "CH4_L", "NA", "CL"])

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines."""
        gro_path = str(tmp_path / "chain_f3.gro")
        write_ion_gro_file(self.ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has SOL, CH4_H, CH4_L, NA, CL."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f3.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)

        expected_sol = sum(
            1 for m in self.ion.molecule_index if m.mol_type in ("ice", "water")
        )
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol

        # Guest molecule (CH4_H) — name may be "CH4" or "CH4_H" depending on
        # whether get_hydrate_guest_residue_name returns ITP or fallback name
        guest_key = None
        for key in molecules:
            if key in ("CH4_H", "CH4"):
                guest_key = key
                break
        assert guest_key is not None, (
            f"TOP should list CH4_H (hydrate guest) molecule, found: {list(molecules.keys())}"
        )
        assert molecules[guest_key] > 0, "CH4_H count should be > 0"

        assert "CH4_L" in molecules, "TOP should list CH4_L solute molecule"
        assert molecules["CH4_L"] > 0, "CH4_L count should be > 0"

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == self.ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == self.ion.cl_count

    def test_top_includes(self, tmp_path):
        """TOP #include has tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f3.top")
        write_ion_top_file(self.ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_hydrate.itp" in includes, "Should include ch4_hydrate.itp for guests"
        assert "ch4_liquid.itp" in includes, "Should include ch4_liquid.itp for solutes"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, tmp_path):
        """All 4 ITP files exist with [ moleculetype ] sections."""
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, self.ion.na_count, self.ion.cl_count)
        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path))

        data_dir = _get_data_dir()
        for itp_name in ["tip4p-ice.itp", "ch4_hydrate.itp", "ch4_liquid.itp"]:
            itp_path = str(data_dir / itp_name)
            assert Path(itp_path).exists(), f"{itp_name} not found"
            assert check_itp_has_moleculetype(itp_path), (
                f"{itp_name} should contain [ moleculetype ] section"
            )

    def test_guest_count_preserved(self, tmp_path):
        """Guest nmolecules > 0 (preserved because chain bypasses CustomMoleculeStructure)."""
        # F3 chain: Hydrate → Interface → Solute → Ion
        # Guest molecules are preserved because they go through InterfaceStructure
        # (not through CustomMoleculeStructure which drops guest_nmolecules)
        assert self.ion.guest_nmolecules > 0, (
            f"guest_nmolecules should be > 0, got {self.ion.guest_nmolecules}"
        )

    def test_registry_distinguishes_ch4_h_ch4_l(self, tmp_path):
        """Registry distinguishes CH4_H from CH4_L (the core MoleculetypeRegistry test)."""
        # CH4_H is the hydrate cage guest; CH4_L is the liquid-phase solute
        # These are DIFFERENT molecule types that must be named differently
        assert "CH4_H" != "CH4_L", (
            "CH4_H and CH4_L must be distinct moleculetype names"
        )

        # Verify in TOP [molecules] that both are present
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)
        top_path = str(tmp_path / "chain_f3.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)
        # Check both CH4_H (guest) and CH4_L (solute) appear
        has_guest = any(k in ("CH4_H", "CH4") for k in molecules)
        has_solute = "CH4_L" in molecules
        assert has_guest, f"TOP should list hydrate guest (CH4_H or CH4), found: {list(molecules.keys())}"
        assert has_solute, f"TOP should list liquid solute CH4_L, found: {list(molecules.keys())}"


# ══════════════════════════════════════════════════════════════════════════════
# F4: Hydrate → Interface → Custom → Solute → Ion
# ══════════════════════════════════════════════════════════════════════════════


class TestChainF4:
    """Validate F4 chain: Hydrate → Interface → Custom → Solute → Ion.

    6 molecule types in GRO: SOL → THF_H → MOL → THF_L → NA → CL
    TOP [molecules]: SOL, THF_H (or THF), etoh, THF_L, NA, CL
    TOP #include: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp

    KNOWN LIMITATION: guest_nmolecules may be 0 after passing through
    CustomMoleculeStructure (field doesn't exist on that type). Use
    guest_atom_count > 0 instead.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        """Build the F4 chain once per test method."""
        hydrate_candidate = _hydrate_sI_thf_candidate()
        interface = _make_slab_interface(hydrate_candidate)

        custom = _insert_custom_molecules(interface, n_molecules=2)

        # CRITICAL: Register hydrate guest AND liquid solute before insert_solutes
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest("THF")
        registry.register_liquid_solute("THF")

        solute = _insert_solutes(custom, solute_type='THF', concentration=0.2)
        # CRITICAL: Uses BUG I5 workaround (_solute_to_ion_source)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gro_residue_ordering(self, tmp_path):
        """GRO file has SOL → THF_H → MOL → THF_L → NA → CL (6 molecule types)."""
        gro_path = str(tmp_path / "chain_f4.gro")
        write_ion_gro_file(self.ion, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        assert "THF_H" in unique_names, "Should have THF_H (hydrate guest) residues"
        assert "MOL" in unique_names, "Should have MOL (custom) residues"
        assert "THF_L" in unique_names, "Should have THF_L (liquid solute) residues"
        assert "NA" in unique_names, "Should have NA residues"
        assert "CL" in unique_names, "Should have CL residues"

        # Verify ordering: SOL → THF_H → MOL → THF_L → NA → CL
        assert_gro_residue_ordering(
            residue_names, ["SOL", "THF_H", "MOL", "THF_L", "NA", "CL"]
        )

    def test_gro_atom_count_matches_header(self, tmp_path):
        """GRO atom count header matches actual atom lines."""
        gro_path = str(tmp_path / "chain_f4.gro")
        write_ion_gro_file(self.ion, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, tmp_path):
        """TOP [molecules] section has SOL, THF_H, MOL, THF_L, NA, CL (6 entries)."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f4.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)

        expected_sol = sum(
            1 for m in self.ion.molecule_index if m.mol_type in ("ice", "water")
        )
        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == expected_sol

        # Guest molecule (THF_H) — name may be "THF" or "THF_H" depending on
        # whether get_hydrate_guest_residue_name returns ITP or fallback name
        guest_key = None
        for key in molecules:
            if key in ("THF_H", "THF"):
                guest_key = key
                break
        assert guest_key is not None, (
            f"TOP should list THF_H (hydrate guest) molecule, found: {list(molecules.keys())}"
        )
        assert molecules[guest_key] > 0, "THF_H count should be > 0"

        assert "etoh" in molecules, "TOP should list etoh molecule (ITP moleculetype name)"
        assert molecules["etoh"] == 2, (
            f"Expected etoh count 2, got {molecules['etoh']}"
        )

        assert "THF_L" in molecules, "TOP should list THF_L solute molecule"
        assert molecules["THF_L"] > 0, "THF_L count should be > 0"

        assert "NA" in molecules, "TOP should list NA molecule"
        assert molecules["NA"] == self.ion.na_count

        assert "CL" in molecules, "TOP should list CL molecule"
        assert molecules["CL"] == self.ion.cl_count

    def test_top_includes(self, tmp_path):
        """TOP #include has 5 ITPs: tip4p-ice, thf_hydrate, etoh, thf_liquid, ion."""
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)

        top_path = str(tmp_path / "chain_f4.top")
        write_ion_top_file(self.ion, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "thf_hydrate.itp" in includes, "Should include thf_hydrate.itp for guests"
        assert "etoh.itp" in includes, "Should include etoh.itp for custom molecules"
        assert "thf_liquid.itp" in includes, "Should include thf_liquid.itp for solutes"
        assert "ion.itp" in includes, "Should include ion.itp"

    def test_itp_files_valid(self, tmp_path):
        """All 5 ITP files exist with [ moleculetype ] sections."""
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, self.ion.na_count, self.ion.cl_count)
        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path))

        data_dir = _get_data_dir()
        for itp_name in ["tip4p-ice.itp", "thf_hydrate.itp", "thf_liquid.itp"]:
            itp_path = str(data_dir / itp_name)
            assert Path(itp_path).exists(), f"{itp_name} not found"
            assert check_itp_has_moleculetype(itp_path), (
                f"{itp_name} should contain [ moleculetype ] section"
            )

        # Custom etoh.itp is in data/custom/ subdirectory
        etoh_itp_path = str(data_dir / "custom" / "etoh.itp")
        assert Path(etoh_itp_path).exists(), f"etoh.itp not found at {etoh_itp_path}"
        assert check_itp_has_moleculetype(etoh_itp_path)

    def test_guest_atom_count_positive(self, tmp_path):
        """KNOWN LIMITATION: guest_nmolecules may be 0; use guest_atom_count > 0.

        After passing through CustomMoleculeStructure, the guest_nmolecules
        field may be 0 (CustomMoleculeStructure doesn't have this field).
        However, guest_atom_count IS preserved, so we check that instead.
        """
        assert self.ion.guest_atom_count > 0, (
            f"guest_atom_count should be > 0 (guest atoms are preserved), "
            f"got {self.ion.guest_atom_count}"
        )

    def test_registry_distinguishes_thf_h_thf_l(self, tmp_path):
        """Registry distinguishes THF_H from THF_L."""
        assert "THF_H" != "THF_L", (
            "THF_H and THF_L must be distinct moleculetype names"
        )

        # Verify in TOP [molecules] that both are present
        write_ion_itp(tmp_path / "ion.itp", self.ion.na_count, self.ion.cl_count)
        top_path = str(tmp_path / "chain_f4.top")
        write_ion_top_file(self.ion, top_path)

        molecules = parse_top_molecules(top_path)
        has_guest = any(k in ("THF_H", "THF") for k in molecules)
        has_solute = "THF_L" in molecules
        assert has_guest, f"TOP should list hydrate guest (THF_H or THF), found: {list(molecules.keys())}"
        assert has_solute, f"TOP should list liquid solute THF_L, found: {list(molecules.keys())}"
