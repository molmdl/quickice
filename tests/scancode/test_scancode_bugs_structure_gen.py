"""Regression tests for scancode structure-generation robustness issues.

This file covers Group 7 of the scancode fix plan:

SUSP-03 (LOW): Fragile GRO box-line parse in
``HydrateStructureGenerator._parse_gro_result`` (hydrate_generator.py:390-399).
The old loop skipped lines whose first char was not a digit and relied on the
``box_line = lines[-1]`` fallback, which (a) broke on trailing blank/whitespace
lines and (b) silently returned a 10 nm default box for malformed input. The
fix scans backwards for the last line matching the GRO box-line format
(exactly 3 or 9 numeric values) and raises a clear ``ValueError`` if none is
found. Standard GenIce2 output parses identically.

SUSP-06 section is appended in a follow-up commit.
"""

import logging
from pathlib import Path

import numpy as np
import pytest

from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import (
    CustomMoleculeConfig,
    HydrateConfig,
    InterfaceStructure,
)
from quickice.structure_generation.custom_molecule_inserter import (
    CustomMoleculeInserter,
)


# ── GRO string helpers ────────────────────────────────────────────────────────

def _gro_line(resnum, resname, atomname, atomnum, x, y, z):
    """Format one atom line in standard GRO v3.3 fixed-width columns.

    Columns: resnum(5) resname(5) atomname(5) atomnum(5) x(8.3f) y(8.3f) z(8.3f).
    Total width = 44 chars (the minimum the parser accepts at hydrate_generator
    line 350). Right-aligns resnum/atomnum/coords, left-aligns resname,
    right-aligns atomname — matching GenIce2 output.
    """
    return f"{resnum:>5}{resname:<5}{atomname:>5}{atomnum:>5}{x:8.3f}{y:8.3f}{z:8.3f}"


def _make_gro(atom_lines, box_line, title="test", trailing=""):
    """Build a complete GRO document string.

    Args:
        atom_lines: list of pre-formatted atom line strings (no trailing \\n).
        box_line: the box-vector line string (no trailing \\n).
        title: GRO title line (line 1).
        trailing: optional string appended AFTER the box line (e.g. "\\n\\n" to
            simulate trailing blank/whitespace lines).
    """
    n = len(atom_lines)
    body = "\n".join(atom_lines)
    return f"{title}\n{n:>5}\n{body}\n{box_line}{trailing}\n"


# ── SUSP-03: robust GRO box-line parse ────────────────────────────────────────

class TestSUSP03BoxLineParse:
    """SUSP-03: ``_parse_gro_result`` robustly identifies the GRO box line and
    raises a clear ``ValueError`` on malformed input.

    The fix scans backwards for the last line matching the box-line format
    (exactly 3 or 9 numeric values). Standard GenIce2 output (3- or 9-value
    box line as the final line) must parse identically to before the fix.
    """

    @staticmethod
    def _parse(gro_string):
        gen = HydrateStructureGenerator()
        # Suppress the cosmetic "Failed to parse coordinates" warning for
        # deliberately-malformed atom lines in the malformed-input tests.
        return gen._parse_gro_result(gro_string)

    def test_standard_orthorhombic_box_parsed(self):
        """Standard GenIce2 GRO with a 3-value box line parses to diag cell."""
        atoms = [
            _gro_line(1, "ICE", "OW", 1, 1.0, 0.0, 0.0),
            _gro_line(1, "ICE", "HW1", 2, 1.095, 0.0, 0.0),
            _gro_line(1, "ICE", "HW2", 3, 1.0, 0.095, 0.0),
        ]
        gro = _make_gro(atoms, "   2.00000   2.00000   2.00000")
        pos, cell, atom_names, res_names, res_seq = self._parse(gro)
        np.testing.assert_allclose(cell, np.diag([2.0, 2.0, 2.0]))
        assert atom_names == ["OW", "HW1", "HW2"]
        assert pos.shape == (3, 3)

    def test_trailing_blank_lines_box_still_parsed(self):
        """GRO with trailing blank/whitespace lines still parses the box line.

        This is the core SUSP-03 fragility: the old fallback ``lines[-1]`` would
        pick the trailing blank line and silently fall back to a 10 nm default
        box. The fix skips trailing blanks.
        """
        atoms = [
            _gro_line(1, "ICE", "OW", 1, 1.0, 0.0, 0.0),
            _gro_line(1, "ICE", "HW1", 2, 1.095, 0.0, 0.0),
            _gro_line(1, "ICE", "HW2", 3, 1.0, 0.095, 0.0),
        ]
        standard = _make_gro(atoms, "   2.00000   2.00000   2.00000")
        with_blanks = _make_gro(
            atoms, "   2.00000   2.00000   2.00000", trailing="\n\n   \n"
        )
        _, cell_std, _, _, _ = self._parse(standard)
        _, cell_blanks, _, _, _ = self._parse(with_blanks)
        np.testing.assert_allclose(cell_blanks, cell_std)
        np.testing.assert_allclose(cell_blanks, np.diag([2.0, 2.0, 2.0]))

    def test_triclinic_9value_box_parsed(self):
        """Triclinic GRO with a 9-value box line parses to a full 3x3 cell."""
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        box = "   1.0   1.0   1.0   0.1   0.0   0.1   0.0   0.1   0.0"
        gro = _make_gro(atoms, box)
        _, cell, _, _, _ = self._parse(gro)
        # GRO triclinic order: v1x v2y v3z v1y v1z v2x v2z v3x v3y
        expected = np.array([
            [1.0, 0.1, 0.0],
            [0.1, 1.0, 0.0],
            [0.1, 0.0, 1.0],
        ])
        np.testing.assert_allclose(cell, expected)

    def test_triclinic_with_trailing_blanks_parsed(self):
        """Triclinic GRO with trailing blank lines parses the same as without."""
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        box = "   1.0   1.0   1.0   0.1   0.0   0.1   0.0   0.1   0.0"
        clean = _make_gro(atoms, box)
        with_blanks = _make_gro(atoms, box, trailing="\n\n")
        _, cell_clean, _, _, _ = self._parse(clean)
        _, cell_blanks, _, _, _ = self._parse(with_blanks)
        np.testing.assert_allclose(cell_blanks, cell_clean)

    def test_malformed_non_numeric_last_line_raises_value_error(self):
        """Last non-blank line is non-numeric text -> clear ValueError.

        Old behavior: ``_parse_box_line`` would attempt ``float('not')`` and
        raise an opaque ``ValueError: could not convert string to float``;
        for a <3-value line it would silently return a 10 nm default box.
        The fix raises a clear "no box-vector line found" error before reaching
        ``_parse_box_line``.
        """
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        gro = _make_gro(atoms, "not a box line")
        with pytest.raises(ValueError, match="box"):
            self._parse(gro)

    def test_malformed_trailing_blanks_only_raises_value_error(self):
        """No box line at all (only trailing blanks after atom lines).

        The last non-blank line is an atom line (7 whitespace-split fields, not
        3 or 9), so the fix correctly determines no box-vector line is present
        and raises. Old behavior would fall back to ``lines[-1]`` (a blank
        line) and silently return a 10 nm default box.
        """
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        gro = _make_gro(atoms, "", trailing="")  # empty box line + no trailing
        # Replace the empty box line with trailing blanks only (no box line):
        gro_no_box = (
            f"test\n{1:>5}\n{atoms[0]}\n\n\n\n"
        )
        with pytest.raises(ValueError, match="box"):
            self._parse(gro_no_box)

    def test_malformed_too_few_box_values_raises_value_error(self):
        """Box line with only 2 values (< 3) -> clear ValueError.

        Old behavior: ``_parse_box_line`` would silently return a 10 nm default
        box (``np.eye(3) * 10.0``) for ``len(values) < 3``. The fix rejects this
        before calling ``_parse_box_line``.
        """
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        gro = _make_gro(atoms, "   2.0   2.0")
        with pytest.raises(ValueError, match="box"):
            self._parse(gro)

    def test_malformed_completely_empty_raises_value_error(self):
        """Completely malformed input (no lines matching box format) raises."""
        # Two atom lines, no box line, no trailing blanks — just ends after atoms.
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        gro = f"test\n{1:>5}\n{atoms[0]}\n"
        with pytest.raises(ValueError, match="box"):
            self._parse(gro)

    def test_error_message_is_clear(self):
        """The ValueError message mentions the box line / box-vector explicitly."""
        atoms = [_gro_line(1, "ICE", "OW", 1, 0.5, 0.5, 0.5)]
        gro = _make_gro(atoms, "not a box line")
        try:
            self._parse(gro)
        except ValueError as e:
            msg = str(e)
            assert "box" in msg.lower(), f"error message should mention 'box': {msg!r}"
            assert "3 or 9" in msg, f"error message should mention '3 or 9': {msg!r}"

    def test_real_genice2_hydrate_box_parsed(self):
        """Integration: a real GenIce2 sI hydrate parses with a non-trivial cell.

        Guards against regressions in the real generate() -> _parse_gro_result
        path. sI is orthorhombic so the box line has 3 values.
        """
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type="sI",
            guest_type="ch4",
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        struct = gen.generate(config)
        # The generated structure's cell comes from the same _parse_gro_result
        # path; confirm it is a sensible non-default box (NOT the 10 nm default
        # that the old silent fallback would produce).
        assert struct.cell.shape == (3, 3)
        box_diag = np.diag(struct.cell)
        # sI CH4 1x1x1 unit cell is ~1.2 nm per side (well below 10 nm default)
        assert np.all(box_diag > 0.5) and np.all(box_diag < 5.0), (
            f"sI cell diagonal {box_diag} outside expected ~1.2 nm range — "
            f"possible silent 10 nm default fallback?"
        )


# ── SUSP-06: place_custom overlap warning ────────────────────────────────────

# Logger name used by custom_molecule_inserter (``logging.getLogger(__name__)``).
_SUSP06_LOGGER = "quickice.structure_generation.custom_molecule_inserter"


def _make_custom_inserter(tmp_path, min_separation=0.3):
    """Build a minimal CustomMoleculeInserter backed by temp .gro/.itp files.

    The template is a 3-atom molecule (C1 + 2 H) centred near the origin so that
    COM-COM distance between two placements approximates the atom-atom overlap.
    ``place_custom`` reads the template via ``parse_gro_file`` in the
    constructor, so real files are required.
    """
    gro_path = tmp_path / "suscp06_test.gro"
    gro_path.write_text(
        "SUSP06 test\n"
        "    3\n"
        "    1MOL    C1    1   0.000   0.000   0.000\n"
        "    1MOL    H1    2   0.150   0.000   0.000\n"
        "    1MOL    H2    3  -0.150   0.000   0.000\n"
        "   5.0  5.0  5.0\n"
    )
    itp_path = tmp_path / "suscp06_test.itp"
    itp_path.write_text(
        "[ moleculetype ]\n"
        "MOL       3\n"
        "\n"
        "[ atoms ]\n"
        "    1   CT      1    MOL    C1    1   0.00  12.01\n"
        "    2   HC      1    MOL    H1    2   0.00   1.008\n"
        "    3   HC      1    MOL    H2    3   0.00   1.008\n"
    )
    # placement_mode="custom" requires positions/rotations to be set; use a
    # placeholder that we override when calling place_custom directly.
    config = CustomMoleculeConfig(
        placement_mode="custom",
        gro_path=gro_path,
        itp_path=itp_path,
        positions=[(0.0, 0.0, 0.0)],
        rotations=[(0.0, 0.0, 0.0)],
        min_separation=min_separation,
    )
    return CustomMoleculeInserter(config)


def _make_minimal_interface(cell_diag=10.0):
    """Build a minimal InterfaceStructure with no ice/water/guests.

    ``place_custom`` only reads ``.cell``, ``.ice_atom_count``,
    ``.water_atom_count``, ``.guest_atom_count``, ``.positions``,
    ``.atom_names``, ``.ice_nmolecules``, ``.water_nmolecules``, and
    ``.molecule_index`` from the structure, so an empty structure suffices.
    """
    return InterfaceStructure(
        positions=np.zeros((0, 3), dtype=np.float64),
        atom_names=[],
        cell=np.eye(3) * cell_diag,
        ice_atom_count=0,
        water_atom_count=0,
        ice_nmolecules=0,
        water_nmolecules=0,
        mode="slab",
        report="",
    )


class TestSUSP06PlaceCustomWarning:
    """SUSP-06: ``place_custom`` emits a warning that no overlap check is
    performed, plus an additional distance-based warning when placed molecules
    are closer than ``config.min_separation``.

    Placement is NOT rejected (users may intentionally place overlapping
    molecules); only a warning is emitted.
    """

    def test_notice_on_call_warning_always_emitted(self, tmp_path, caplog):
        """Every ``place_custom`` call emits a 'no overlap check' notice."""
        inserter = _make_custom_inserter(tmp_path)
        iface = _make_minimal_interface()
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0)],
                rotations=[(0.0, 0.0, 0.0)],
            )
        notice_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "without overlap" in r.getMessage()
        ]
        assert len(notice_records) == 1, (
            f"expected exactly 1 notice-on-call WARNING, got "
            f"{[r.getMessage() for r in notice_records]}"
        )

    def test_overlap_pair_emits_overlap_warning(self, tmp_path, caplog):
        """Two molecules closer than min_separation emit a 'possible overlap'
        warning in addition to the notice-on-call warning."""
        inserter = _make_custom_inserter(tmp_path, min_separation=0.3)
        iface = _make_minimal_interface()
        # COM-COM distance 0.1 nm < min_separation 0.3 nm -> overlap warning.
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            result = inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0), (1.1, 1.0, 1.0)],
                rotations=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
            )
        overlap_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "possible overlap" in r.getMessage()
        ]
        assert len(overlap_records) == 1, (
            f"expected 1 'possible overlap' WARNING, got "
            f"{[r.getMessage() for r in overlap_records]}"
        )
        # Placement is NOT rejected — both molecules are placed.
        assert result.custom_molecule_count == 2

    def test_non_overlap_pair_emits_no_overlap_warning(self, tmp_path, caplog):
        """Two molecules far apart (COM-COM >> min_separation) do NOT emit the
        'possible overlap' warning; only the notice-on-call warning is emitted."""
        inserter = _make_custom_inserter(tmp_path, min_separation=0.3)
        iface = _make_minimal_interface()
        # COM-COM distance 2.0 nm >> min_separation 0.3 nm -> no overlap warning.
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0), (3.0, 1.0, 1.0)],
                rotations=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
            )
        overlap_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "possible overlap" in r.getMessage()
        ]
        notice_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "without overlap" in r.getMessage()
        ]
        assert len(overlap_records) == 0, (
            f"expected NO 'possible overlap' WARNING for non-overlapping pair, "
            f"got {[r.getMessage() for r in overlap_records]}"
        )
        assert len(notice_records) == 1, (
            f"expected 1 notice-on-call WARNING, got "
            f"{[r.getMessage() for r in notice_records]}"
        )

    def test_single_molecule_emits_notice_only(self, tmp_path, caplog):
        """A single molecule placement emits the notice but no overlap warning
        (no pairs to check)."""
        inserter = _make_custom_inserter(tmp_path)
        iface = _make_minimal_interface()
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0)],
                rotations=[(0.0, 0.0, 0.0)],
            )
        overlap_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "possible overlap" in r.getMessage()
        ]
        notice_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "without overlap" in r.getMessage()
        ]
        assert len(overlap_records) == 0
        assert len(notice_records) == 1

    def test_overlapping_placement_not_rejected(self, tmp_path, caplog):
        """Overlapping molecules are still placed (no exception). SUSP-06 only
        adds a warning; it does NOT add a hard rejection."""
        inserter = _make_custom_inserter(tmp_path, min_separation=0.3)
        iface = _make_minimal_interface()
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            result = inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0), (1.01, 1.0, 1.0)],  # 0.01 nm apart
                rotations=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
            )
        # Both molecules placed despite the overlap.
        assert result.custom_molecule_count == 2
        # The overlap warning was emitted (informational, not a rejection).
        assert any(
            "possible overlap" in r.getMessage()
            for r in caplog.records
            if r.levelno >= logging.WARNING
        )

    def test_three_molecules_counts_pairs_correctly(self, tmp_path, caplog):
        """With 3 molecules, the warning reports the correct number of close
        pairs out of 3 total pairs (C(3,2)=3)."""
        inserter = _make_custom_inserter(tmp_path, min_separation=0.3)
        iface = _make_minimal_interface()
        # mol 0 and 1 overlap (0.1 nm); mol 2 is far from both.
        with caplog.at_level(logging.WARNING, logger=_SUSP06_LOGGER):
            inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0), (1.1, 1.0, 1.0), (5.0, 5.0, 5.0)],
                rotations=[(0.0, 0.0, 0.0)] * 3,
            )
        overlap_records = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and "possible overlap" in r.getMessage()
        ]
        assert len(overlap_records) == 1
        msg = overlap_records[0].getMessage()
        # 1 close pair out of 3 total pairs.
        assert "1 of 3" in msg, f"expected '1 of 3' in message: {msg!r}"

    def test_validation_error_still_raised(self, tmp_path):
        """The positions/rotations length mismatch check still raises
        (unaffected by the warning additions)."""
        inserter = _make_custom_inserter(tmp_path)
        iface = _make_minimal_interface()
        with pytest.raises(ValueError, match="same length"):
            inserter.place_custom(
                iface,
                positions=[(1.0, 1.0, 1.0), (2.0, 2.0, 2.0)],
                rotations=[(0.0, 0.0, 0.0)],  # length mismatch
            )
