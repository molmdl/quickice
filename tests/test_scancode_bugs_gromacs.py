"""Regression tests for scancode-verified bugs in gromacs_writer.py.

BUG-05 (CRITICAL): HW1 Z-coordinate copy-paste error in write_custom_molecule_gro_file()
MW-01 (HIGH): Atom-level wrapping in write_ice_gro_file() splits molecules at PBC
DEFLT-01 (HIGH): fudgeLJ/fudgeQQ inconsistency across TOP writers

Each test class verifies that its respective bug is fixed and cannot regress.
"""

import re
import sys

import numpy as np
import pytest
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    compute_mw_position,
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_multi_molecule_top_file,
    write_ion_top_file,
    write_ion_gro_file,
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
    write_solute_gro_file,
    write_solute_top_file,
    wrap_molecules_into_box,
    MoleculeIndex,
)
from quickice.structure_generation.types import (
    Candidate,
    InterfaceStructure,
    IonStructure,
    IonConfig,
    MoleculeIndex as MoleculeIndexType,
)

from e2e_export_helpers import (
    _insert_custom_molecules,
    _insert_ions,
    _insert_solutes,
    _solute_to_ion_source,
    ETOH_GRO,
    ETOH_ITP,
)


# ══════════════════════════════════════════════════════════════════════════════
# BUG-05: HW1 Z-coordinate copy-paste error
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG05:
    """Regression tests for BUG-05: HW1 Z-coordinate uses h2_pos[2] instead of h1_pos[2].

    Before the fix, write_custom_molecule_gro_file() output HW1 Z as h2_pos[2],
    silently copying HW2's Z-coordinate for HW1. When h1_pos[2] != h2_pos[2],
    both HW1 and HW2 would show the same Z value (h2_pos[2]), corrupting the
    molecular geometry.

    The fix changes h2_pos[2] to h1_pos[2] on the HW1 output line.
    """

    @pytest.fixture(autouse=True)
    def _build_custom(self, interface_slab):
        """Build custom molecule structure for all tests in this class."""
        self.custom = _insert_custom_molecules(interface_slab, n_molecules=3)

    def test_hw1_z_differs_from_hw2_z(self, tmp_path):
        """HW1 Z-coordinate differs from HW2 Z when H positions differ.

        Before BUG-05 fix, HW1 Z == HW2 Z (both used h2_pos[2]).
        After fix, HW1 Z == h1_pos[2] and HW2 Z == h2_pos[2], which differ
        for most water molecules (only identical for perfectly symmetric molecules).
        """
        gro_path = str(tmp_path / "custom.gro")
        write_custom_molecule_gro_file(self.custom, gro_path)

        # Parse GRO file to find SOL residues with HW1 and HW2 atoms
        sol_molecules = _parse_sol_molecules(gro_path)

        # At least one water molecule must have hw1_z != hw2_z
        differing = [
            mol for mol in sol_molecules
            if abs(mol["hw1_z"] - mol["hw2_z"]) > 1e-4
        ]
        assert len(differing) > 0, (
            "BUG-05 regression: All water molecules have HW1 Z == HW2 Z. "
            "This indicates HW1 is still using h2_pos[2] instead of h1_pos[2]."
        )

    def test_hw1_z_matches_first_hydrogen(self, tmp_path):
        """HW1 Z-coordinate matches the first hydrogen position from the structure.

        For a subset of SOL molecules, verify that the exported HW1 Z-coordinate
        matches the expected h1_pos[2] from the source positions (not h2_pos[2]).
        """
        gro_path = str(tmp_path / "custom.gro")
        write_custom_molecule_gro_file(self.custom, gro_path)

        sol_molecules = _parse_sol_molecules(gro_path)

        # Get the source molecule_index to find ice/water molecules
        ice_mols = [m for m in self.custom.molecule_index if m.mol_type == "ice"]
        water_mols = [m for m in self.custom.molecule_index if m.mol_type == "water"]

        if ice_mols:
            # Check first ice molecule: positions are O(0), H1(1), H2(2) in 3-atom storage
            # After 3->4 TIP4P expansion: OW, HW1, HW2, MW
            first_ice = ice_mols[0]
            base_idx = first_ice.start_idx
            h1_pos = self.custom.positions[base_idx + 1]
            h2_pos = self.custom.positions[base_idx + 2]

            # Find the corresponding GRO molecule
            if sol_molecules:
                gro_mol = sol_molecules[0]
                # HW1 Z should match h1_pos[2], NOT h2_pos[2]
                assert abs(gro_mol["hw1_z"] - h1_pos[2]) < 0.0015, (
                    f"BUG-05 regression: HW1 Z ({gro_mol['hw1_z']:.4f}) doesn't match "
                    f"h1_pos[2] ({h1_pos[2]:.4f}), matches h2_pos[2] ({h2_pos[2]:.4f}) instead"
                )


# ══════════════════════════════════════════════════════════════════════════════
# MW-01: Atom-level wrapping splits molecules at PBC
# ══════════════════════════════════════════════════════════════════════════════


class TestMW01:
    """Regression tests for MW-01: ice GRO writer uses atom-level wrapping.

    Before the fix, write_ice_gro_file() used wrap_positions_into_box() which
    wraps each atom independently, potentially splitting water molecules across
    PBC boundaries. This produces incorrect MW virtual site positions because
    MW is computed from O, H1, H2 positions that may be in different periodic
    images.

    The fix changes to wrap_molecules_into_box() with a constructed molecule_index,
    keeping all atoms of each molecule together before computing MW.
    """

    def test_mw_position_matches_computation(self, ice_ih_candidate, tmp_path):
        """MW position in GRO output matches compute_mw_position(O, H1, H2).

        For each water molecule in the exported GRO, the MW position should
        match compute_mw_position(o, h1, h2) computed from the wrapped
        O, H1, H2 positions.
        """
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)

        sol_molecules = _parse_sol_molecules(gro_path)

        # Check a sample of molecules (first 10, or all if fewer)
        check_count = min(10, len(sol_molecules))
        max_error = 0.0

        for i in range(check_count):
            mol = sol_molecules[i]
            o_pos = np.array([mol["o_x"], mol["o_y"], mol["o_z"]])
            h1_pos = np.array([mol["hw1_x"], mol["hw1_y"], mol["hw1_z"]])
            h2_pos = np.array([mol["hw2_x"], mol["hw2_y"], mol["hw2_z"]])

            expected_mw = compute_mw_position(o_pos, h1_pos, h2_pos)
            actual_mw = np.array([mol["mw_x"], mol["mw_y"], mol["mw_z"]])

            error = np.max(np.abs(actual_mw - expected_mw))
            max_error = max(max_error, error)

            assert error < 0.001, (
                f"MW-01 regression: Molecule {i} MW position mismatch. "
                f"Expected {expected_mw}, got {actual_mw}, error={error:.4f} nm. "
                f"This indicates molecule atoms may be split across PBC."
            )

    def test_no_split_molecules_across_pbc(self, ice_ih_candidate, tmp_path):
        """No water molecules have atoms split across PBC boundaries.

        After molecule-aware wrapping, O, H1, H2 atoms within each molecule
        should be close together (no large jumps between periodic images).
        """
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)

        sol_molecules = _parse_sol_molecules(gro_path)

        box = ice_ih_candidate.cell
        box_sizes = np.array([box[0, 0], box[1, 1], box[2, 2]])

        # Check that no O-H distance exceeds half the box size
        # (which would indicate a split across PBC)
        check_count = min(20, len(sol_molecules))
        split_count = 0

        for i in range(check_count):
            mol = sol_molecules[i]
            o_pos = np.array([mol["o_x"], mol["o_y"], mol["o_z"]])
            h1_pos = np.array([mol["hw1_x"], mol["hw1_y"], mol["hw1_z"]])
            h2_pos = np.array([mol["hw2_x"], mol["hw2_y"], mol["hw2_z"]])

            # O-H bond should be ~0.1 nm, never > half box
            d_oh1 = np.abs(o_pos - h1_pos)
            d_oh2 = np.abs(o_pos - h2_pos)

            for dim in range(3):
                if d_oh1[dim] > box_sizes[dim] / 2 or d_oh2[dim] > box_sizes[dim] / 2:
                    split_count += 1
                    break

        # With molecule-aware wrapping, no molecules should be split
        assert split_count == 0, (
            f"MW-01 regression: {split_count}/{check_count} molecules have "
            f"atoms split across PBC boundaries. "
            f"wrap_molecules_into_box should prevent this."
        )


# ══════════════════════════════════════════════════════════════════════════════
# DEFLT-01: fudgeLJ/fudgeQQ inconsistency across TOP writers
# ══════════════════════════════════════════════════════════════════════════════


class TestDEFLT01:
    """Regression tests for DEFLT-01: fudgeLJ=0.0, fudgeQQ=0.0 in multi-molecule TOP writers.

    Before the fix, three multi-molecule TOP writers (ion, custom molecule, solute)
    used fudgeLJ=0.0 and fudgeQQ=0.0 instead of the correct Amber forcefield
    defaults fudgeLJ=0.5 and fudgeQQ=0.8333. The three simple writers already used
    the correct values.

    The fix standardizes ALL six writers to use fudgeLJ=0.5, fudgeQQ=0.8333.
    """

    def test_simple_writers_use_amber_defaults(self, ice_ih_candidate, interface_slab, tmp_path):
        """Simple TOP writers (write_top_file, write_interface_top_file) use 0.5/0.8333."""
        # write_top_file (ice candidate)
        ice_top = str(tmp_path / "ice.top")
        write_top_file(ice_ih_candidate, ice_top)
        fudgeLJ, fudgeQQ = _parse_defaults_section(ice_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )

        # write_interface_top_file
        iface_top = str(tmp_path / "interface.top")
        write_interface_top_file(interface_slab, iface_top)
        fudgeLJ, fudgeQQ = _parse_defaults_section(iface_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_interface_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_interface_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )

    def test_ion_top_file_uses_amber_defaults(self, interface_slab, tmp_path):
        """write_ion_top_file uses fudgeLJ=0.5, fudgeQQ=0.8333."""
        ion = _insert_ions(interface_slab, concentration=0.15)
        ion_top = str(tmp_path / "ion.top")
        write_ion_top_file(ion, ion_top)

        fudgeLJ, fudgeQQ = _parse_defaults_section(ion_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_ion_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_ion_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )

    def test_custom_molecule_top_file_uses_amber_defaults(self, interface_slab, tmp_path):
        """write_custom_molecule_top_file uses fudgeLJ=0.5, fudgeQQ=0.8333."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        custom_top = str(tmp_path / "custom.top")
        write_custom_molecule_top_file(custom, custom_top)

        fudgeLJ, fudgeQQ = _parse_defaults_section(custom_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_custom_molecule_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_custom_molecule_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )

    def test_solute_top_file_uses_amber_defaults(self, interface_slab, tmp_path):
        """write_solute_top_file uses fudgeLJ=0.5, fudgeQQ=0.8333."""
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        solute_top = str(tmp_path / "solute.top")
        write_solute_top_file(solute, solute_top)

        fudgeLJ, fudgeQQ = _parse_defaults_section(solute_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_solute_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_solute_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )

    def test_multi_molecule_top_file_uses_amber_defaults(self, interface_slab, tmp_path):
        """write_multi_molecule_top_file uses fudgeLJ=0.5, fudgeQQ=0.8333."""
        mm_top = str(tmp_path / "multi.top")
        # Use molecule_index from interface (ice + water)
        mol_idx = [
            MoleculeIndexType(start_idx=0, count=3, mol_type="ice")
            for m in range(interface_slab.ice_nmolecules)
        ]
        write_multi_molecule_top_file(mol_idx, mm_top, system_name="Test")

        fudgeLJ, fudgeQQ = _parse_defaults_section(mm_top)
        assert fudgeLJ == pytest.approx(0.5, abs=0.01), (
            f"DEFLT-01: write_multi_molecule_top_file fudgeLJ={fudgeLJ}, expected 0.5"
        )
        assert fudgeQQ == pytest.approx(0.8333, abs=0.01), (
            f"DEFLT-01: write_multi_molecule_top_file fudgeQQ={fudgeQQ}, expected 0.8333"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Parsing helpers
# ══════════════════════════════════════════════════════════════════════════════


def _parse_sol_molecules(gro_path: str) -> list[dict]:
    """Parse SOL molecules from a GRO file.

    Returns a list of dicts, one per SOL residue, with keys:
        o_x, o_y, o_z, hw1_x, hw1_y, hw1_z, hw2_x, hw2_y, hw2_z,
        mw_x, mw_y, mw_z

    GRO format (fixed-width columns):
        Residue number: cols 0-4 (right-justified)
        Residue name:   cols 5-9 (left-justified)
        Atom name:      cols 10-14 (left-justified)
        Atom number:    cols 15-19 (right-justified)
        X:             cols 20-27
        Y:             cols 28-35
        Z:             cols 36-43
    """
    molecules = []
    current_mol = {}

    with open(gro_path, 'r') as f:
        lines = f.readlines()

    # Skip title (line 0) and atom count (line 1), stop before box vectors
    for line in lines[2:]:
        # Box vector lines have 9 float values (no residue name)
        if len(line.strip()) < 20:
            continue

        # Check if this is a box vector line (no alphabetic residue name)
        res_name = line[5:10].strip()
        if not res_name or not any(c.isalpha() for c in res_name):
            continue

        atom_name = line[10:15].strip()

        if res_name != "SOL":
            continue

        try:
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
        except (ValueError, IndexError):
            continue

        # Map atom names to positions
        # Accept OW/0W/oW variants for oxygen, HW1/H1 for first H, HW2/H2 for second H
        name_lower = atom_name.lower().replace("0", "o").replace("1", "").replace("2", "")

        if atom_name in ("OW", "oW", "0W"):
            # Start a new molecule
            if current_mol:
                molecules.append(current_mol)
            current_mol = {"o_x": x, "o_y": y, "o_z": z}
        elif atom_name in ("HW1", "H1"):
            current_mol["hw1_x"] = x
            current_mol["hw1_y"] = y
            current_mol["hw1_z"] = z
        elif atom_name in ("HW2", "H2"):
            current_mol["hw2_x"] = x
            current_mol["hw2_y"] = y
            current_mol["hw2_z"] = z
        elif atom_name in ("MW",):
            current_mol["mw_x"] = x
            current_mol["mw_y"] = y
            current_mol["mw_z"] = z

    # Don't forget the last molecule
    if current_mol:
        molecules.append(current_mol)

    return molecules


def _parse_defaults_section(top_path: str) -> tuple[float, float]:
    """Parse fudgeLJ and fudgeQQ from [ defaults ] section of a TOP file.

    Returns:
        (fudgeLJ, fudgeQQ) as floats
    """
    in_defaults = False

    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()

            # Detect section headers
            if stripped.startswith('['):
                section = stripped.strip('[] \t').lower()
                in_defaults = (section == 'defaults')
                continue

            # Skip comments and blank lines
            if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                continue

            # Parse the defaults values line (after [ defaults ] header)
            if in_defaults:
                parts = stripped.split()
                if len(parts) >= 5:
                    # Format: nbfunc comb-rule gen-pairs fudgeLJ fudgeQQ
                    try:
                        fudgeLJ = float(parts[3])
                        fudgeQQ = float(parts[4])
                        return fudgeLJ, fudgeQQ
                    except (ValueError, IndexError):
                        pass

    raise ValueError(f"Could not parse [ defaults ] section from {top_path}")
