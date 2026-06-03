"""End-to-end tests for Ice + Interface single-structure GROMACS export.

Bridges the computation pipeline (real GenIce2 structures) with the GROMACS
writer functions, validating that exported .gro and .top files are correct.

Three scenarios:
1. Ice Candidate Export — write_gro_file / write_top_file
2. Interface (no guests) Export — write_interface_gro_file / write_interface_top_file
3. Interface + Hydrate Guests Export — write_interface_gro_file / write_interface_top_file

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
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    get_hydrate_guest_residue_name,
)

# Import parsing helpers from the shared module (NOT from conftest)
from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    parse_top_includes,
    check_itp_has_moleculetype,
    assert_gro_residue_ordering,
)


# ── Helper: locate bundled ITP files ─────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1: Ice Candidate Export
# ══════════════════════════════════════════════════════════════════════════════


class TestIceCandidateExport:
    """Validate Ice Candidate export via write_gro_file / write_top_file.

    Ice candidate has only SOL residues (TIP4P-ICE water model).
    GRO atom count = nmolecules * 4 (3→4 expansion: OW, HW1, HW2, MW).
    TOP [molecules] = {"SOL": nmolecules}
    TOP #include = ["tip4p-ice.itp"]
    """

    def test_gro_only_sol_residues(self, ice_ih_candidate, tmp_path):
        """GRO file contains only SOL residue names for ice candidate."""
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert unique_names == {"SOL"}, (
            f"Ice candidate GRO should have only SOL residues, got {unique_names}"
        )

    def test_gro_atom_count_matches_header(self, ice_ih_candidate, tmp_path):
        """GRO atom count header matches actual atom lines.

        TIP4P-ICE: nmolecules * 4 atoms (OW, HW1, HW2, MW virtual site).
        """
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        # Also verify the count matches nmolecules * 4 (TIP4P-ICE expansion)
        expected_atoms = ice_ih_candidate.nmolecules * 4
        assert header_count == expected_atoms, (
            f"Expected {expected_atoms} atoms (nmolecules={ice_ih_candidate.nmolecules} * 4), "
            f"got {header_count}"
        )

    def test_top_molecules_section(self, ice_ih_candidate, tmp_path):
        """TOP [molecules] section has correct SOL count."""
        top_path = str(tmp_path / "ice.top")
        write_top_file(ice_ih_candidate, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        assert molecules["SOL"] == ice_ih_candidate.nmolecules, (
            f"Expected SOL count {ice_ih_candidate.nmolecules}, got {molecules['SOL']}"
        )

    def test_top_has_moleculetype_inline(self, ice_ih_candidate, tmp_path):
        """TOP file has [ moleculetype ] section inline (write_top_file writes inline, no #include)."""
        top_path = str(tmp_path / "ice.top")
        write_top_file(ice_ih_candidate, top_path)

        with open(top_path) as f:
            content = f.read()

        # write_top_file writes the SOL molecule definition inline
        # (no #include directives unlike write_interface_top_file)
        assert "[ moleculetype ]" in content, (
            "Ice TOP should have [ moleculetype ] section inline"
        )

        # No guest ITP for plain ice
        guest_refs = [line for line in content.split('\n')
                      if 'hydrate' in line.lower() and '#include' in line]
        assert len(guest_refs) == 0, (
            f"Ice candidate should not reference hydrate ITPs, got {guest_refs}"
        )

    def test_tip4p_ice_itp_has_moleculetype(self):
        """Bundled tip4p-ice.itp exists and has [ moleculetype ] section."""
        data_dir = _get_data_dir()
        itp_path = str(data_dir / "tip4p-ice.itp")

        assert Path(itp_path).exists(), f"tip4p-ice.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(itp_path), (
            "tip4p-ice.itp should contain [ moleculetype ] section"
        )

    def test_atom_conservation(self, ice_ih_candidate, tmp_path):
        """Atom conservation: positions count matches molecules * atoms_per_molecule."""
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)

        # The writer expands 3→4 atoms, so we check the output
        header_count = parse_gro_atom_count(gro_path)
        expected = ice_ih_candidate.nmolecules * 4  # TIP4P-ICE: 4 atoms per molecule

        assert header_count == expected, (
            f"Atom conservation: expected {expected} (nmolecules * 4), got {header_count}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 2: Interface (no guests) Export
# ══════════════════════════════════════════════════════════════════════════════


class TestInterfaceExport:
    """Validate Interface (no guests) export via write_interface_gro_file / write_interface_top_file.

    Interface from Ice Ih has only SOL residues (ice + water both SOL).
    GRO atom count = ice_nmolecules * 4 + water_nmolecules * 4.
    TOP [molecules] = {"SOL": ice_nmolecules + water_nmolecules}
    TOP #include = ["tip4p-ice.itp"] (no guest ITP since no guests)
    """

    def test_gro_only_sol_residues(self, interface_slab, tmp_path):
        """GRO file contains only SOL residue names for interface (no guests)."""
        gro_path = str(tmp_path / "interface.gro")
        write_interface_gro_file(interface_slab, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert unique_names == {"SOL"}, (
            f"Interface (no guests) GRO should have only SOL residues, got {unique_names}"
        )

    def test_gro_atom_count_matches_header(self, interface_slab, tmp_path):
        """GRO atom count header matches actual atom lines.

        Interface: ice_nmolecules * 4 + water_nmolecules * 4
        (ice uses TIP4P-ICE 3→4 expansion, water is already 4 atoms)
        """
        gro_path = str(tmp_path / "interface.gro")
        write_interface_gro_file(interface_slab, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

        expected_atoms = interface_slab.ice_nmolecules * 4 + interface_slab.water_nmolecules * 4
        assert header_count == expected_atoms, (
            f"Expected {expected_atoms} atoms "
            f"(ice={interface_slab.ice_nmolecules}*4 + water={interface_slab.water_nmolecules}*4), "
            f"got {header_count}"
        )

    def test_top_molecules_section(self, interface_slab, tmp_path):
        """TOP [molecules] section has combined SOL count for ice + water."""
        top_path = str(tmp_path / "interface.top")
        write_interface_top_file(interface_slab, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        expected_sol = interface_slab.ice_nmolecules + interface_slab.water_nmolecules
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol} "
            f"(ice={interface_slab.ice_nmolecules} + water={interface_slab.water_nmolecules}), "
            f"got {molecules['SOL']}"
        )

    def test_top_includes_tip4p_ice_only(self, interface_slab, tmp_path):
        """TOP #include has only tip4p-ice.itp (no guest ITP for non-hydrate interface)."""
        top_path = str(tmp_path / "interface.top")
        write_interface_top_file(interface_slab, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        # No guest ITP since no guests
        guest_itps = [inc for inc in includes if "hydrate" in inc]
        assert len(guest_itps) == 0, (
            f"Interface without guests should not include hydrate ITPs, got {guest_itps}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3: Interface + Hydrate Guests Export
# ══════════════════════════════════════════════════════════════════════════════


class TestInterfaceHydrateExport:
    """Validate Interface + Hydrate Guests export.

    Interface from hydrate sI+CH4 candidate has SOL + CH4_H residues.
    GRO residue ordering: SOL before guest residues (no interleaving).
    TOP [molecules] = {"SOL": ice+water, guest_res_name: guest_nmolecules}
    TOP #include = ["tip4p-ice.itp", "ch4_hydrate.itp"]
    """

    def test_gro_sol_before_guest_residues(self, interface_hydrate_slab, tmp_path):
        """GRO file has SOL residues before guest residues with no interleaving."""
        gro_path = str(tmp_path / "hydrate_interface.gro")
        write_interface_gro_file(interface_hydrate_slab, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)

        assert "SOL" in unique_names, "Should have SOL residues"
        # Should have at least one guest residue type
        guest_names = unique_names - {"SOL"}
        assert len(guest_names) > 0, (
            f"Hydrate interface should have guest residues, got only {unique_names}"
        )

        # Verify ordering: SOL before guests (no interleaving)
        expected_order = ["SOL"] + sorted(guest_names)
        assert_gro_residue_ordering(residue_names, expected_order)

    def test_gro_atom_count_matches_header(self, interface_hydrate_slab, tmp_path):
        """GRO atom count header matches actual atom lines for hydrate interface."""
        gro_path = str(tmp_path / "hydrate_interface.gro")
        write_interface_gro_file(interface_hydrate_slab, gro_path)

        header_count = parse_gro_atom_count(gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        actual_atom_lines = len(residue_names)

        assert header_count == actual_atom_lines, (
            f"GRO header says {header_count} atoms but found {actual_atom_lines} atom lines"
        )

    def test_top_molecules_section(self, interface_hydrate_slab, tmp_path):
        """TOP [molecules] section has correct SOL and guest counts."""
        top_path = str(tmp_path / "hydrate_interface.top")
        write_interface_top_file(interface_hydrate_slab, top_path)

        molecules = parse_top_molecules(top_path)

        assert "SOL" in molecules, "TOP should list SOL molecule"
        expected_sol = interface_hydrate_slab.ice_nmolecules + interface_hydrate_slab.water_nmolecules
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )

        # Guest molecule type should be present
        # CH4 hydrate guest residue name from ITP file
        guest_res_name = get_hydrate_guest_residue_name("ch4")
        assert guest_res_name in molecules, (
            f"Expected guest molecule '{guest_res_name}' in [molecules], got {list(molecules.keys())}"
        )
        assert molecules[guest_res_name] == interface_hydrate_slab.guest_nmolecules, (
            f"Expected {guest_res_name} count {interface_hydrate_slab.guest_nmolecules}, "
            f"got {molecules[guest_res_name]}"
        )

    def test_top_includes_hydrate_itp(self, interface_hydrate_slab, tmp_path):
        """TOP #include includes both tip4p-ice.itp and ch4_hydrate.itp."""
        top_path = str(tmp_path / "hydrate_interface.top")
        write_interface_top_file(interface_hydrate_slab, top_path)

        includes = parse_top_includes(top_path)

        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_hydrate.itp" in includes, "Should include ch4_hydrate.itp for CH4 guests"

    def test_ch4_hydrate_itp_has_moleculetype(self):
        """Bundled ch4_hydrate.itp exists and has [ moleculetype ] section."""
        data_dir = _get_data_dir()
        itp_path = str(data_dir / "ch4_hydrate.itp")

        assert Path(itp_path).exists(), f"ch4_hydrate.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(itp_path), (
            "ch4_hydrate.itp should contain [ moleculetype ] section"
        )

    def test_no_sol_guest_interleaving(self, interface_hydrate_slab, tmp_path):
        """No SOL residue appears after any guest residue (no interleaving)."""
        gro_path = str(tmp_path / "hydrate_interface.gro")
        write_interface_gro_file(interface_hydrate_slab, gro_path)

        residue_names = parse_gro_residue_names(gro_path)
        unique_names = set(residue_names)
        guest_names = unique_names - {"SOL"}

        # After any guest residue type appears, no SOL should follow
        seen_guest = False
        for name in residue_names:
            if name in guest_names:
                seen_guest = True
            elif name == "SOL" and seen_guest:
                pytest.fail(
                    f"SOL residue found after guest residue — molecules are interleaved! "
                    f"Guest types: {guest_names}"
                )
