"""Unit tests for the 10 DRY-extracted GRO formatting helpers (Phase 48.1, Wave 2a).

Each test proves a helper produces BYTE-IDENTICAL output to the inline code in
the reference GRO writer(s). The expected strings are built with the SAME
f-string format as the inline source (the reference pattern), then compared
to the helper's actual output. If any assertion fails, the helper's f-string
diverges from the inline code — the helper must be corrected to match the
source byte-for-byte.

Reference inline code locations (post-48.1-02 gromacs_writer.py):
  - write_gro_file:              lines 56-169   (header, sol-ice, box)
  - write_interface_gro_file:     lines 231-547  (sol-ice, sol-water, guest, box)
  - write_multi_molecule_gro_file: lines 750-897 (header, generic guest, box)
  - write_ion_gro_file:          lines 1106-1541 (sol-ice, sol-water, guest,
                                                  custom, solute, NA, CL, box)
  - write_custom_molecule_gro_file: lines 1865-2161 (header [divergent — not
                                  tested here], sol-ice, sol-water, guest, custom)
  - write_solute_gro_file:       lines 2398-2827 (sol-ice, sol-water, guest,
                                                   custom, solute, box)

The 14 byte-equivalence tests in test_gro_top_byte_equivalence.py
gate the END-TO-END writer output. These unit tests gate the HELPER output in
isolation — together they form a two-layer safety net so that when plans
48.1-04/05/06 swap inline code for helper calls, any divergence is caught
immediately at the unit level (fast feedback) before the byte-equivalence
tests run (slower, end-to-end).
"""

import io

import numpy as np
import pytest

from quickice.output._gro_format import (
    _format_cl_ion,
    _format_custom_molecule,
    _format_guest_molecule,
    _format_na_ion,
    _format_sol_ice_molecule,
    _format_sol_water_molecule,
    _format_solute_molecule,
    _write_gro_box_vectors,
    _write_gro_header,
    _wrap_aux_positions,
)
from quickice.output._shared import compute_mw_position


# ---------------------------------------------------------------------------
# Helper 1: _write_gro_header
# Used by 5 of 6 GRO writers (NOT write_custom_molecule_gro_file — divergent).
# Reference: write_gro_file:103-104, write_interface_gro_file:341,344,
#            write_multi_molecule_gro_file:821-822, write_ion_gro_file:1280,1283,
#            write_solute_gro_file:2608,2611.
# ---------------------------------------------------------------------------


class TestWriteGroHeader:
    """Verify _write_gro_header produces byte-identical title + atom-count lines."""

    @pytest.mark.parametrize("n_atoms,expected_count_line", [
        (42, "   42\n"),        # basic case: 3-space-prefixed 2-digit count
        (99999, "99999\n"),     # 5-digit edge: exactly fills the :5d field
        (100000, "100000\n"),   # overflow edge: :5d expands to 6 digits (GROMACS wraps)
    ])
    def test_header_lines(self, n_atoms, expected_count_line):
        lines: list[str] = []
        _write_gro_header(lines, "test title", n_atoms)
        assert lines == ["test title\n", expected_count_line]


# ---------------------------------------------------------------------------
# Helper 2: _format_sol_ice_molecule
# Used by 5 of 6 (NOT write_multi_molecule_gro_file — generic per-atom loop).
# Reference: write_gro_file:136-156 (canonical).
# ---------------------------------------------------------------------------


class TestFormatSolIceMolecule:
    """Verify 4 SOL ice lines (OW, HW1, HW2, MW) byte-identical to write_gro_file."""

    def test_sol_ice_four_lines(self):
        o_pos = np.array([0.100, 0.200, 0.300])
        h1_pos = np.array([0.150, 0.250, 0.300])
        h2_pos = np.array([0.050, 0.250, 0.300])
        mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
        counter = [0]
        lines: list[str] = []
        _format_sol_ice_molecule(lines, o_pos, h1_pos, h2_pos, mw_pos,
                                 res_num=1, atom_num_counter=counter)
        # Expected built from the inline f-strings at write_gro_file:136-156.
        expected = [
            f"{1:5d}SOL  "
            f"   OW{1:5d}"
            f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n",
            f"{1:5d}SOL  "
            f"  HW1{2:5d}"
            f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n",
            f"{1:5d}SOL  "
            f"  HW2{3:5d}"
            f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n",
            f"{1:5d}SOL  "
            f"   MW{4:5d}"
            f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n",
        ]
        assert lines == expected
        assert counter[0] == 4, "atom_num_counter must increment by 4 (OW, HW1, HW2, MW)"


# ---------------------------------------------------------------------------
# Helper 3: _format_sol_water_molecule
# Used by 4 of 6 (NOT multi_molecule, NOT write_gro_file which is ice-only).
# Reference: write_interface_gro_file:431-433 (generic {name:>5s} loop).
# Note: write_ion/custom/solute inline the water branch with EXPLICIT "   OW"
# literals, but {name:>5s} produces byte-identical output ("OW".rjust(5)=="   OW").
# ---------------------------------------------------------------------------


class TestFormatSolWaterMolecule:
    """Verify 4 SOL water pass-through lines byte-identical to inline code."""

    def test_sol_water_four_lines(self):
        positions = np.array([
            [0.100, 0.200, 0.300],   # OW
            [0.150, 0.250, 0.300],   # HW1
            [0.050, 0.250, 0.300],   # HW2
            [0.120, 0.220, 0.300],   # MW (already computed, pass-through)
        ])
        counter = [0]
        lines: list[str] = []
        _format_sol_water_molecule(lines, positions, res_num=5,
                                   atom_num_counter=counter)
        # Expected built from the inline f-string at write_interface_gro_file:431-433.
        atom_names = ["OW", "HW1", "HW2", "MW"]
        expected = [
            f"{5:5d}SOL  "
            f"{name:>5s}{i + 1:5d}"
            f"{positions[i][0]:8.3f}{positions[i][1]:8.3f}{positions[i][2]:8.3f}\n"
            for i, name in enumerate(atom_names)
        ]
        assert lines == expected
        assert counter[0] == 4
        # Cross-check: the {name:>5s} form must produce the SAME bytes as the
        # explicit "   OW"/"  HW1"/"  HW2"/"   MW" literals used by the
        # ion/custom/solute writers' water branches.
        explicit = {
            "OW": "   OW", "HW1": "  HW1", "HW2": "  HW2", "MW": "   MW",
        }
        for name, lit in explicit.items():
            assert f"{name:>5s}" == lit, f"{name:>5s!r} != explicit literal {lit!r}"


# ---------------------------------------------------------------------------
# Helper 4: _format_guest_molecule
# Used by 4 of 6 (interface, multi_molecule, ion, solute).
# Reference: write_interface_gro_file:480-482 (custom branch),
#            write_interface_gro_file:529-531 (built-in branch),
#            write_ion_gro_file:1442-1444, write_solute_gro_file:2754-2756,
#            write_multi_molecule_gro_file:887-889.
# ---------------------------------------------------------------------------


class TestFormatGuestMolecule:
    """Verify guest lines (CH4) byte-identical to write_interface_gro_file."""

    def test_ch4_guest_five_atoms(self):
        mol_atom_names = ["C", "H", "H", "H", "H"]
        mol_positions = np.array([
            [0.000, 0.000, 0.000],
            [0.100, 0.000, 0.000],
            [-0.100, 0.000, 0.000],
            [0.000, 0.100, 0.000],
            [0.000, -0.100, 0.000],
        ])
        counter = [10]  # non-zero start to verify counter threading
        lines: list[str] = []
        _format_guest_molecule(lines, mol_atom_names, mol_positions,
                               res_num=5, res_name="CH4",
                               atom_num_counter=counter)
        # Expected built from write_interface_gro_file:480-482 / 529-531.
        expected = [
            f"{5:5d}{'CH4':<5s}{name:>5s}{10 + i + 1:5d}"
            f"{mol_positions[i][0]:8.3f}{mol_positions[i][1]:8.3f}"
            f"{mol_positions[i][2]:8.3f}\n"
            for i, name in enumerate(mol_atom_names)
        ]
        assert lines == expected
        assert counter[0] == 15, "counter must thread from 10 to 15 (5 atoms)"


# ---------------------------------------------------------------------------
# Helper 5: _format_custom_molecule
# Used by 3 of 6 (ion, custom_molecule, solute).
# Reference: write_ion_gro_file:1471-1473, write_custom_molecule_gro_file:2143-2146,
#            write_solute_gro_file:2780-2782.
# Format string is identical to _format_guest_molecule (kept separate for readability).
# ---------------------------------------------------------------------------


class TestFormatCustomMolecule:
    """Verify custom molecule lines byte-identical to write_ion_gro_file."""

    def test_custom_three_atoms(self):
        mol_atom_names = ["C", "H", "H"]
        mol_positions = np.array([
            [0.000, 0.000, 0.000],
            [0.100, 0.000, 0.000],
            [-0.100, 0.000, 0.000],
        ])
        counter = [0]
        lines: list[str] = []
        _format_custom_molecule(lines, mol_atom_names, mol_positions,
                                 res_num=7, res_name="MOL",
                                 atom_num_counter=counter)
        # Expected built from write_ion_gro_file:1471-1473.
        expected = [
            f"{7:5d}{'MOL':<5s}{name:>5s}{i + 1:5d}"
            f"{mol_positions[i][0]:8.3f}{mol_positions[i][1]:8.3f}"
            f"{mol_positions[i][2]:8.3f}\n"
            for i, name in enumerate(mol_atom_names)
        ]
        assert lines == expected
        assert counter[0] == 3


# ---------------------------------------------------------------------------
# Helper 6: _format_solute_molecule
# Used by 2 of 6 (ion, solute).
# Reference: write_ion_gro_file:1503-1505, write_solute_gro_file:2810-2812.
# Format identical to _format_custom_molecule / _format_guest_molecule.
# ---------------------------------------------------------------------------


class TestFormatSoluteMolecule:
    """Verify solute lines (CH4_L) byte-identical to write_solute_gro_file."""

    def test_ch4_l_solute_five_atoms(self):
        mol_atom_names = ["C", "H", "H", "H", "H"]
        mol_positions = np.array([
            [0.000, 0.000, 0.000],
            [0.100, 0.000, 0.000],
            [-0.100, 0.000, 0.000],
            [0.000, 0.100, 0.000],
            [0.000, -0.100, 0.000],
        ])
        counter = [0]
        lines: list[str] = []
        # res_name "CH4_L" is exactly 5 chars — exercises the 5-char GRO limit.
        _format_solute_molecule(lines, mol_atom_names, mol_positions,
                                 res_num=3, res_name="CH4_L",
                                 atom_num_counter=counter)
        # Expected built from write_solute_gro_file:2810-2812.
        expected = [
            f"{3:5d}{'CH4_L':<5s}{name:>5s}{i + 1:5d}"
            f"{mol_positions[i][0]:8.3f}{mol_positions[i][1]:8.3f}"
            f"{mol_positions[i][2]:8.3f}\n"
            for i, name in enumerate(mol_atom_names)
        ]
        assert lines == expected
        assert counter[0] == 5
        # Verify the 5-char res_name fills the field exactly (no padding).
        assert f"{'CH4_L':<5s}" == "CH4_L"


# ---------------------------------------------------------------------------
# Helper 7: _format_na_ion
# Used by 1 of 6 (write_ion_gro_file only — unique).
# Reference: write_ion_gro_file:1515-1517.
# NOTE: the plan's placeholder template was ADJUSTED to match the source
# byte-for-byte. Source uses resname field "NA   " (NA + 3 spaces) and
# atom-name field "   NA" (3 spaces + NA), NOT the plan's "NA       NA".
# ---------------------------------------------------------------------------


class TestFormatNaIon:
    """Verify NA ion line byte-identical to write_ion_gro_file:1515-1517."""

    def test_na_ion_single_line(self):
        pos = np.array([1.500, 2.500, 3.500])
        counter = [0]
        lines: list[str] = []
        _format_na_ion(lines, pos, res_num=100, atom_num_counter=counter)
        # Expected built verbatim from write_ion_gro_file:1515-1517.
        expected = [
            f"{100:5d}NA   "
            f"   NA{1:5d}"
            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n"
        ]
        assert lines == expected
        assert counter[0] == 1
        # Verify column alignment: resname="NA   " (5 chars), atom="   NA" (5 chars).
        assert lines[0][:5] == "  100"          # residue number field
        assert lines[0][5:10] == "NA   "        # residue name field (NA + 3 spaces)
        assert lines[0][10:15] == "   NA"       # atom name field (3 spaces + NA)
        assert lines[0][15:20] == "    1"       # atom number field


# ---------------------------------------------------------------------------
# Helper 8: _format_cl_ion
# Used by 1 of 6 (write_ion_gro_file only — unique).
# Reference: write_ion_gro_file:1526-1528. Same column pattern as NA.
# ---------------------------------------------------------------------------


class TestFormatClIon:
    """Verify CL ion line byte-identical to write_ion_gro_file:1526-1528."""

    def test_cl_ion_single_line(self):
        pos = np.array([0.500, 1.500, 2.500])
        counter = [5]  # non-zero start
        lines: list[str] = []
        _format_cl_ion(lines, pos, res_num=200, atom_num_counter=counter)
        # Expected built verbatim from write_ion_gro_file:1526-1528.
        expected = [
            f"{200:5d}CL   "
            f"   CL{6:5d}"
            f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n"
        ]
        assert lines == expected
        assert counter[0] == 6
        # Verify column alignment: resname="CL   " (5 chars), atom="   CL" (5 chars).
        assert lines[0][5:10] == "CL   "
        assert lines[0][10:15] == "   CL"


# ---------------------------------------------------------------------------
# Helper 9: _write_gro_box_vectors
# Used by 5 of 6 (NOT write_custom_molecule_gro_file — divergent 3-value diagonal).
# Reference: write_gro_file:161-163, write_interface_gro_file:539-541,
#            write_multi_molecule_gro_file:894-896, write_ion_gro_file:1534-1536,
#            write_solute_gro_file:2818-2820.
# ---------------------------------------------------------------------------


class TestWriteGroBoxVectors:
    """Verify 9-value triclinic box line byte-identical to write_gro_file:161-163."""

    def test_box_vectors_orthogonal_and_triclinic(self):
        # Orthogonal cell: off-diagonal elements are 0.0.
        cell_ortho = np.diag([3.0, 3.0, 8.0])
        f1 = io.StringIO()
        _write_gro_box_vectors(f1, cell_ortho)
        expected_ortho = (
            f"{cell_ortho[0, 0]:10.5f}{cell_ortho[1, 1]:10.5f}{cell_ortho[2, 2]:10.5f}"
            f"{cell_ortho[0, 1]:10.5f}{cell_ortho[0, 2]:10.5f}{cell_ortho[1, 0]:10.5f}"
            f"{cell_ortho[1, 2]:10.5f}{cell_ortho[2, 0]:10.5f}{cell_ortho[2, 1]:10.5f}\n"
        )
        assert f1.getvalue() == expected_ortho
        # Orthogonal: the 6 off-diagonal values are all 0.00000 -> "   0.00000" (10 chars).
        assert f1.getvalue().count("   0.00000") == 6

        # Triclinic cell: cell[0,1] = 0.1 (non-zero off-diagonal).
        cell_tri = np.array([
            [3.0, 0.1, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 0.0, 8.0],
        ])
        f2 = io.StringIO()
        _write_gro_box_vectors(f2, cell_tri)
        expected_tri = (
            f"{cell_tri[0, 0]:10.5f}{cell_tri[1, 1]:10.5f}{cell_tri[2, 2]:10.5f}"
            f"{cell_tri[0, 1]:10.5f}{cell_tri[0, 2]:10.5f}{cell_tri[1, 0]:10.5f}"
            f"{cell_tri[1, 2]:10.5f}{cell_tri[2, 0]:10.5f}{cell_tri[2, 1]:10.5f}\n"
        )
        assert f2.getvalue() == expected_tri
        # The non-zero off-diagonal 0.1 -> "   0.10000" must appear exactly once.
        assert f2.getvalue().count("   0.10000") == 1


# ---------------------------------------------------------------------------
# Helper 10: _wrap_aux_positions
# Used by 3 of 6 (interface, ion, solute).
# Reference: write_interface_gro_file:330,334, write_ion_gro_file:1256,1262,
#            write_solute_gro_file:2574,2584.
# Pattern: positions % np.diag(cell) (diagonal modulo — AN-03 fix).
# ---------------------------------------------------------------------------


class TestWrapAuxPositions:
    """Verify diagonal-modulo PBC wrap byte-identical to inline AN-03 pattern."""

    def test_wrap_none_empty_and_normal(self):
        cell = np.diag([3.0, 3.0, 8.0])

        # None input -> None output (caller-friendly no-op).
        assert _wrap_aux_positions(None, cell) is None

        # Empty input -> returned unchanged.
        empty = np.array([]).reshape(0, 3)
        result_empty = _wrap_aux_positions(empty, cell)
        assert result_empty.shape == (0, 3)

        # Normal case: positions outside the box wrap via diagonal modulo.
        positions = np.array([
            [4.0, -1.0, 10.0],   # outside box -> wraps
            [1.5, 2.5, 3.5],    # inside box -> unchanged
        ])
        result = _wrap_aux_positions(positions, cell)
        # Expected: positions % np.diag(cell) — the inline AN-03 pattern.
        expected = positions % np.diag(cell)
        np.testing.assert_allclose(result, expected)
        # Spot-check the wrapped values.
        np.testing.assert_allclose(result[0], [1.0, 2.0, 2.0])  # 4%3, -1%3, 10%8
        np.testing.assert_allclose(result[1], [1.5, 2.5, 3.5])  # inside box
