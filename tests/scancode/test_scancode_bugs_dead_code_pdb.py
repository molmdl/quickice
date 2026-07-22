"""Regression tests for scancode CRIT-03 + CRIT-05: deletion of dead code
``write_interface_pdb_file`` from ``quickice/output/pdb_writer.py``.

Background (from ``.planning/scancode-fixes/RESEARCH.md``):
  - CRIT-03: ``write_interface_pdb_file`` hardcoded ``i // 3`` (3 atoms/ice),
    wrong for 4-atom TIP4P hydrate ice. Real bug, but the function was DEAD
    CODE (zero callers, not exported).
  - CRIT-05: ``atom_name[0]`` → ``MW`` becomes ``"M"`` (no element "M"). Real
    latent bug, but the ``MW`` trigger existed only in the dead
    ``write_interface_pdb_file``; the reachable ``write_pdb_with_cryst1`` only
    sees O/H atoms (Candidate ice-only structures from GenIce2 use 3-atom
    TIP3P-style water: O, H, H — no MW).

User-approved decision: DELETE the dead function (removes both latent bugs in
one stroke) rather than wire it up. These tests pin the deletion so the
function (and its two latent bugs) cannot be silently reintroduced.

The reachable ``write_pdb_with_cryst1`` (used by ``output/orchestrator.py``
and ``gui/export.py``) must remain UNTOUCHED and still work — tested here
with a small 3-atom TIP3P-style Candidate matching the real GenIce2 output
shape.
"""

from pathlib import Path

import numpy as np
import pytest

from quickice.output import pdb_writer
from quickice.output.pdb_writer import write_pdb_with_cryst1
from quickice.structure_generation.types import Candidate


# ══════════════════════════════════════════════════════════════════════════════
# CRIT-03 + CRIT-05: dead function is gone
# ══════════════════════════════════════════════════════════════════════════════

class TestDeadFunctionDeleted:
    """``write_interface_pdb_file`` was dead code carrying two latent bugs
    (CRIT-03 ``i//3``, CRIT-05 ``MW→M``). It must remain deleted."""

    def test_function_not_an_attribute_of_pdb_writer(self):
        """The function must not be importable or accessible as an attribute
        of the ``pdb_writer`` module.

        Pre-deletion: ``hasattr(pdb_writer, 'write_interface_pdb_file')`` was
        True. Post-deletion: must be False. If this fails, the dead function
        (and its two latent bugs) was reintroduced.
        """
        assert not hasattr(pdb_writer, "write_interface_pdb_file"), (
            "pdb_writer.write_interface_pdb_file still exists — the dead code "
            "carrying CRIT-03 (i//3) and CRIT-05 (MW→M) was reintroduced. "
            "This function had zero callers and was deleted by user approval; "
            "do NOT re-add it without also wiring it up and fixing both bugs."
        )

    def test_function_not_importable_from_pdb_writer(self):
        """``from quickice.output.pdb_writer import write_interface_pdb_file``
        must fail with ImportError. Pins the deletion at the import level."""
        with pytest.raises(ImportError):
            from quickice.output.pdb_writer import write_interface_pdb_file  # noqa: F401
            assert False, "ImportError expected — function should be deleted"

    def test_function_not_exported_from_output_package(self):
        """The function must not be exported via ``quickice.output.__init__``'s
        ``__all__`` or as an attribute of the ``quickice.output`` package.

        Pre-deletion it was already NOT exported (this was part of the
        dead-code confirmation). Post-deletion it must remain not exported.
        """
        import quickice.output as output_pkg
        # Not in the package's __all__.
        assert "write_interface_pdb_file" not in getattr(output_pkg, "__all__", []), (
            "write_interface_pdb_file listed in quickice.output.__all__ — "
            "the dead function was exported. It should be deleted, not wired."
        )
        # Not accessible as an attribute of the package either.
        assert not hasattr(output_pkg, "write_interface_pdb_file"), (
            "quickice.output.write_interface_pdb_file exists — the dead "
            "function is reachable via the package. It should be deleted."
        )

    def test_function_name_absent_from_pdb_writer_source(self):
        """The literal string ``write_interface_pdb_file`` must not appear
        anywhere in ``pdb_writer.py`` source — not even as a comment or
        docstring referencing the removed function.

        This is a belt-and-suspenders source-level guard against the function
        (or a reference to it) being reintroduced. The only acceptable
        mention of this name post-deletion is in the test file itself and in
        ``.planning/`` documentation.
        """
        src = Path(pdb_writer.__file__).read_text()
        assert "write_interface_pdb_file" not in src, (
            "The string 'write_interface_pdb_file' still appears in "
            f"{pdb_writer.__file__!r} source. The dead function (or a "
            "reference to it) must be fully removed."
        )

    def test_interfacestructure_no_longer_imported_by_pdb_writer(self):
        """After deletion, ``InterfaceStructure`` is no longer needed by
        ``pdb_writer.py`` (it was used only in the deleted function's type
        hint). The import must be removed to avoid a dead import.

        ``Candidate`` (used by the surviving ``write_pdb_with_cryst1`` and
        ``write_ranked_candidates``) must still be imported.
        """
        src = Path(pdb_writer.__file__).read_text()
        assert "InterfaceStructure" not in src, (
            "InterfaceStructure is still referenced in pdb_writer.py — the "
            "deleted function's type hint import should have been removed "
            "along with the function (it is no longer used by any survivor)."
        )
        # Candidate must still be imported (used by the survivors).
        assert "from quickice.structure_generation.types import Candidate" in src, (
            "Candidate import missing from pdb_writer.py — the deletion "
            "accidentally removed the wrong import. Candidate is still "
            "needed by write_pdb_with_cryst1 and write_ranked_candidates."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Reachable survivor: write_pdb_with_cryst1 still works
# ══════════════════════════════════════════════════════════════════════════════

def _make_small_tip3p_candidate(n_molecules: int = 4) -> Candidate:
    """Build a small 3-atom TIP3P-style ice Candidate matching GenIce2's
    actual output shape (atom_names = ["O","H","H","O","H","H",...], no MW).

    This is the shape the reachable ``write_pdb_with_cryst1`` actually sees
    in production (Candidate ice-only structures; CRIT-05's MW trigger never
    appears here). 4 molecules × 3 atoms = 12 atoms.
    """
    atoms_per_water = 3
    n_atoms = n_molecules * atoms_per_water
    # Place atoms on a small cubic grid in nm (well inside a 1 nm box).
    positions = np.zeros((n_atoms, 3), dtype=float)
    for mol_idx in range(n_molecules):
        base = mol_idx * atoms_per_water
        # O at the molecule's base position
        positions[base + 0] = [0.1 * mol_idx, 0.0, 0.0]
        # Two H atoms offset from O
        positions[base + 1] = [0.1 * mol_idx + 0.0096, 0.0, 0.0075]
        positions[base + 2] = [0.1 * mol_idx - 0.0096, 0.0, 0.0075]
    atom_names = ["O", "H", "H"] * n_molecules
    # 1 nm cubic cell (orthogonal — matches the slab/interface forced
    # orthogonal cells; the reachable function does not see triclinic cells
    # from the Candidate path).
    cell = np.diag([1.0, 1.0, 1.0])
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_molecules,
        phase_id="ice_ih",
        seed=42,
        metadata={},
    )


class TestReachableSurvivorStillWorks:
    """The reachable ``write_pdb_with_cryst1`` (used by orchestrator.py and
    gui/export.py) must remain UNTOUCHED by the deletion and still produce
    correct PDB output."""

    def test_write_pdb_with_cryst1_still_callable(self):
        """The survivor must remain a callable attribute of pdb_writer."""
        assert hasattr(pdb_writer, "write_pdb_with_cryst1")
        assert callable(pdb_writer.write_pdb_with_cryst1)

    def test_writes_valid_pdb_file(self, tmp_path):
        """End-to-end: write a small Candidate to a .pdb file and assert the
        file exists, is non-empty, and has the expected PDB structure:
        CRYST1 header, N HETATM records, END footer.
        """
        candidate = _make_small_tip3p_candidate(n_molecules=4)
        pdb_path = tmp_path / "small.pdb"
        write_pdb_with_cryst1(candidate, str(pdb_path))

        assert pdb_path.exists(), "PDB file was not written"
        content = pdb_path.read_text()
        assert content, "PDB file is empty"

        lines = content.splitlines()
        # CRYST1 + 12 HETATM + END = 14 lines.
        assert lines[0].startswith("CRYST1"), f"First line is not CRYST1: {lines[0]!r}"
        assert lines[-1] == "END", f"Last line is not END: {lines[-1]!r}"

        hetatm_lines = [ln for ln in lines if ln.startswith("HETATM")]
        assert len(hetatm_lines) == 12, (
            f"Expected 12 HETATM records (4 mols × 3 atoms), got {len(hetatm_lines)}"
        )

    def test_atom_count_matches_positions(self, tmp_path):
        """The number of HETATM records must equal len(candidate.positions)."""
        candidate = _make_small_tip3p_candidate(n_molecules=4)
        pdb_path = tmp_path / "count.pdb"
        write_pdb_with_cryst1(candidate, str(pdb_path))

        content = pdb_path.read_text()
        hetatm_count = sum(1 for ln in content.splitlines() if ln.startswith("HETATM"))
        assert hetatm_count == len(candidate.positions) == 12

    def test_residue_numbers_correct_for_3_atom_water(self, tmp_path):
        """The reachable function dynamically detects atoms_per_water from
        len(positions) // nmolecules (= 3 for TIP3P). Residue numbers must be
        1,1,1,2,2,2,3,3,3,4,4,4 for 4 molecules of 3-atom water.

        This is the CORRECT dynamic behavior that the dead function's
        hardcoded ``i // 3`` lacked generality for (CRIT-03 was about 4-atom
        TIP4P hydrate ice, which the dead function never saw because it was
        never called). The survivor's dynamic detection is correct.
        """
        candidate = _make_small_tip3p_candidate(n_molecules=4)
        pdb_path = tmp_path / "resid.pdb"
        write_pdb_with_cryst1(candidate, str(pdb_path))

        content = pdb_path.read_text()
        # Residue number is in columns 23-26 of the HETATM line (1-indexed),
        # i.e. the 4 chars after "HOH A". Format: "HETATM{serial:5d} {name:4s}HOH A{resSeq:4d}    ..."
        # so resSeq starts at column index 22 (0-indexed) and is 4 chars wide.
        residue_nums = []
        for ln in content.splitlines():
            if ln.startswith("HETATM"):
                # "HETATM" (6) + serial (5) + " " (1) + name (4) + "HOH" (3) + " " (1) + "A" (1) = 21 chars
                # then resSeq (4 chars) starting at index 22.
                res_seq = ln[22:26]
                residue_nums.append(int(res_seq))
        assert residue_nums == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4], (
            f"Residue numbers wrong for 3-atom water: {residue_nums}"
        )

    def test_element_labels_correct_for_OH_atoms(self, tmp_path):
        """The reachable function sees only O/H atoms (no MW). ``atom_name[0]``
        yields "O" and "H" — both valid element symbols. This is the
        non-triggering case for CRIT-05 (the MW→M bug only existed in the dead
        function). Assert the produced element column is correct.
        """
        candidate = _make_small_tip3p_candidate(n_molecules=2)
        pdb_path = tmp_path / "elem.pdb"
        write_pdb_with_cryst1(candidate, str(pdb_path))

        content = pdb_path.read_text()
        # Element symbol is right-justified in columns 77-78 (1-indexed),
        # i.e. index 76-78 (0-indexed, 2 chars wide).
        elements = []
        for ln in content.splitlines():
            if ln.startswith("HETATM"):
                elem = ln[76:78].strip()
                elements.append(elem)
        # 2 mols × 3 atoms = 6 atoms: O, H, H, O, H, H.
        assert elements == ["O", "H", "H", "O", "H", "H"], (
            f"Element labels wrong: {elements}. The reachable function only "
            "ever sees O/H atoms (no MW), so atom_name[0] is correct here. "
            "If MW appears, the CRIT-05 trigger leaked into the survivor path."
        )

    def test_cryst1_record_present_with_cell_parameters(self, tmp_path):
        """The CRYST1 record must be present with the cell parameters
        computed from the 1 nm cubic cell (a=b=c=10 Angstrom, alpha=beta=gamma=90)."""
        candidate = _make_small_tip3p_candidate(n_molecules=2)
        pdb_path = tmp_path / "cryst.pdb"
        write_pdb_with_cryst1(candidate, str(pdb_path))

        content = pdb_path.read_text()
        cryst1 = content.splitlines()[0]
        # CRYST1 + a(9.3) b(9.3) c(9.3) alpha(7.2) beta(7.2) gamma(7.2)
        # 1 nm = 10 Angstrom.
        assert cryst1.startswith("CRYST1"), f"First line not CRYST1: {cryst1!r}"
        # The 1 nm cubic cell → a=b=c=10.000 Angstrom, angles=90.00.
        assert "   10.000   10.000   10.000" in cryst1, (
            f"Cell lengths wrong in CRYST1: {cryst1!r} (expected 10.000 Angstrom for 1 nm)"
        )
        assert " 90.00  90.00  90.00" in cryst1, (
            f"Cell angles wrong in CRYST1: {cryst1!r} (expected 90.00 for cubic)"
        )
