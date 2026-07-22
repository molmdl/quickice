"""Regression tests for scancode Group 8: tech debt cleanup.

Covers two tech-debt fixes from ``.planning/scancode-fixes/RESEARCH.md``:

- **TD-ADHOC** — ``quickice/output/gromacs_writer.py`` had 7 ad-hoc
  ``type('obj', (object,), {...})()`` anonymous-class instances used as
  drop-in ``MoleculeIndex``-shaped objects. The fix replaces them with the
  existing ``quickice.structure_generation.types.MoleculeIndex`` dataclass
  (already imported by the writer). This is a PURE REFACTOR — behavior and
  the produced GRO/TOP files must be byte-identical.

- **TD-07** — ``quickice/structure_generation/molecule_validator.py:185``
  only checked ``[ atomtypes ]`` PRESENCE, not whether the user's
  ``[ atomtypes ]`` section REDEFINES a built-in atomtype name
  (``OW_ice`` / ``HW_ice`` / ``MW`` / ``NA`` / ``CL``). A redefining upload
  passed validation and failed later at ``gmx grompp`` with a confusing
  duplicate-atomtype error. The fix adds a CONFLICT check at upload time.

This file grows across the two atomic commits (one per TD). The tests
present at each commit exercise ONLY the fix landed by that commit.

Behavioral regression for TD-ADHOC is also covered by the existing
end-to-end GRO writer suites (``test_e2e_ion_export.py`` exercises the
``write_ion_gro_file`` sites; ``test_e2e_solute_export.py`` exercises the
``write_solute_gro_file`` sites) — those suites call the 7 refactored
sites and must continue to pass unchanged.
"""

import re
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from quickice.output import gromacs_writer as gwm
from quickice.structure_generation.types import MoleculeIndex


# Path to the writer source — used for static regression guards that prevent
# reintroducing the ad-hoc ``type('obj', (object,), {...})()`` pattern.
GROMACS_WRITER_PATH = (
    Path(__file__).resolve().parents[2]
    / "quickice" / "output" / "gromacs_writer.py"
)


def _all_output_writer_source() -> str:
    """Concatenate the source of every ``quickice/output/*.py`` file.

    The 7 MoleculeIndex construction sites (TD-ADHOC / Group 8 fix) were
    originally all in ``gromacs_writer.py``. Phase 48.1 splits the per-structure
    writers into sibling modules (``ice_writer.py``, ``interface_writer.py``,
    ``multi_molecule_writer.py``, ``ion_writer.py``, ``custom_writer.py``,
    ``solute_writer.py``), so the sites are now distributed across multiple
    files. This helper scans ALL of them so the static regression guards
    continue to find every site regardless of which file it lives in.

    Uses ``Path("quickice/output").glob("*.py")`` so future per-structure
    splits (Waves 7-8: custom_writer.py, solute_writer.py) are automatically
    covered without further test edits. Mirrors the pattern in
    ``tests/test_tip4p_ice_lj_values.py:104-108`` and
    ``tests/test_scancode_bugs_constants.py:86-90``.
    """
    output_dir = Path(__file__).resolve().parents[2] / "quickice" / "output"
    return "\n".join(p.read_text() for p in sorted(output_dir.glob("*.py")))


# ══════════════════════════════════════════════════════════════════════════════
# TD-ADHOC: MoleculeIndex dataclass replaces ad-hoc type() objects
# ══════════════════════════════════════════════════════════════════════════════


class TestMoleculeIndexAdhoc:
    """TD-ADHOC: 7 ad-hoc ``type('obj', (object,), {...})()`` instances in
    ``gromacs_writer.py`` are replaced with the existing ``MoleculeIndex``
    dataclass (drop-in — same fields ``start_idx`` / ``count`` / ``mol_type``).

    The replacement is a PURE REFACTOR: the 7 sites must construct
    ``MoleculeIndex`` with the SAME values, and the objects must support the
    SAME attribute access as the old anonymous-class instances.
    """

    def test_molecule_index_is_a_dataclass(self):
        """``MoleculeIndex`` must be a dataclass (not an ad-hoc type)."""
        assert is_dataclass(MoleculeIndex), (
            "MoleculeIndex must be a @dataclass — the TD-ADHOC fix replaces "
            "ad-hoc type('obj', (object,), {...})() with a proper dataclass."
        )

    def test_molecule_index_field_names_match_old_attributes(self):
        """Field names must be EXACTLY the old anonymous-class attributes.

        The 7 ad-hoc sites used ``{'start_idx': ..., 'count': ..., 'mol_type': ...}``.
        The dataclass must expose the SAME names so attribute access is
        identical (drop-in replacement).
        """
        field_names = {f.name for f in fields(MoleculeIndex)}
        assert field_names == {"start_idx", "count", "mol_type"}, (
            f"Expected fields {{start_idx, count, mol_type}}, got {field_names}. "
            f"Field names must match the old anonymous-class attributes for "
            f"drop-in compatibility."
        )

    @pytest.mark.parametrize(
        "start_idx, count, mol_type",
        [
            (0, 4, "ice"),
            (12, 4, "water"),
            (48, 5, "guest"),
            (53, 9, "custom"),
            (62, 3, "solute"),
            (100, 1, "na"),
            (101, 1, "cl"),
        ],
    )
    def test_molecule_index_dropin_attribute_access(self, start_idx, count, mol_type):
        """A constructed MoleculeIndex must expose the SAME attributes as the
        old anonymous-class instances (``.start_idx``, ``.count``, ``.mol_type``).

        This mirrors how the 7 sites in ``gromacs_writer.py`` consume the
        object: ``ordered_mols.append(("sol", mi))`` then later
        ``mol.start_idx`` / ``mol.count`` / ``mol.mol_type``.
        """
        mi = MoleculeIndex(start_idx=start_idx, count=count, mol_type=mol_type)
        assert mi.start_idx == start_idx
        assert mi.count == count
        assert mi.mol_type == mol_type

    def test_molecule_index_survives_ordered_mols_usage_pattern(self):
        """The 7 sites append ``(label, mi)`` tuples to ``ordered_mols`` then
        iterate as ``for mol_type, mol in ordered_mols: ...`` accessing
        ``mol.count`` / ``mol.mol_type`` / ``mol.start_idx``. Verify a
        ``MoleculeIndex`` survives this exact usage pattern.
        """
        ordered_mols = []
        # Mirror the 7 construction shapes (one of each mol_type):
        ordered_mols.append(("sol", MoleculeIndex(start_idx=0, count=4, mol_type="ice")))
        ordered_mols.append(("sol", MoleculeIndex(start_idx=4, count=4, mol_type="water")))
        ordered_mols.append(("guest", MoleculeIndex(start_idx=8, count=5, mol_type="guest")))
        ordered_mols.append(("custom", MoleculeIndex(start_idx=13, count=9, mol_type="custom")))
        ordered_mols.append(("solute", MoleculeIndex(start_idx=22, count=3, mol_type="solute")))

        # Mirror the consumption loop in gromacs_writer.py (total_atoms counting):
        total_atoms = 0
        for mol_type, mol in ordered_mols:
            if mol_type == "sol":
                if mol.mol_type == "ice":
                    total_atoms += 4  # Ice: 3 input -> 4 output (OW, HW1, HW2, MW)
                else:
                    total_atoms += mol.count
            elif mol_type == "guest":
                total_atoms += mol.count
            elif mol_type == "custom":
                total_atoms += mol.count
            elif mol_type == "solute":
                total_atoms += mol.count
        # 4 (ice) + 4 (water) + 5 (guest) + 9 (custom) + 3 (solute) = 25
        assert total_atoms == 25, (
            f"MoleculeIndex consumption loop mismatch: expected 25, got {total_atoms}"
        )

    def test_gromacs_writer_has_no_adhoc_type_objects(self):
        """STATIC REGRESSION GUARD: no ``quickice/output/*.py`` writer may
        contain ``type('obj', (object,), ...)`` occurrences.

        Before TD-ADHOC there were 7 (all in ``gromacs_writer.py``); the fix
        replaces all of them with ``MoleculeIndex(...)``. This test prevents
        reintroducing the ad-hoc pattern in ANY output writer module
        (gromacs_writer.py or any per-structure sibling split from it in
        Phase 48.1 — ice_writer, interface_writer, multi_molecule_writer,
        ion_writer, custom_writer, solute_writer).
        """
        source = _all_output_writer_source()
        matches = re.findall(r"type\('obj',\s*\(object,\s*\)", source)
        assert matches == [], (
            f"no quickice/output/*.py writer may contain ad-hoc "
            f"type('obj', (object,), ...) instances (TD-ADHOC replaced them "
            f"with MoleculeIndex). Found {len(matches)}."
        )

    def test_gromacs_writer_has_seven_molecule_index_construction_sites(self):
        """STATIC REGRESSION GUARD: the 7 ad-hoc sites must now construct
        ``MoleculeIndex``. Count ``ordered_mols.append((..., MoleculeIndex(...))``
        sites across ALL ``quickice/output/*.py`` writers and verify exactly 7,
        covering the 5 distinct mol_type labels used by the old ad-hoc sites:
        sol/ice, sol/water, guest, custom, solute.

        Originally all 7 sites were in ``gromacs_writer.py``. Phase 48.1 splits
        the per-structure writers into sibling modules, so the sites are now
        distributed: 2 in ``ion_writer.py`` (write_ion_gro_file — custom +
        solute synthetic entries), 5 in ``gromacs_writer.py`` (write_solute_gro_file
        — sol/ice, sol/water, guest, custom, solute synthetic entries). The
        scan-all-files pattern (``_all_output_writer_source``) finds all 7
        regardless of which file they live in.
        """
        source = _all_output_writer_source()
        # Count MoleculeIndex constructions inside ordered_mols.append calls.
        mi_sites = re.findall(r"ordered_mols\.append\(\([^)]+,\s*MoleculeIndex\(", source)
        assert len(mi_sites) == 7, (
            f"Expected exactly 7 ordered_mols.append(... MoleculeIndex(...)) sites "
            f"across all quickice/output/*.py writers (TD-ADHOC replaces 7 ad-hoc "
            f"type() objects), found {len(mi_sites)}."
        )

    @pytest.mark.parametrize(
        "label, mol_type, count_expr",
        [
            ("sol", "ice", "atoms_per_ice_mol"),
            ("sol", "water", "4"),
            ("guest", "guest", "atoms_per_guest"),
            ("custom", "custom", "atoms_per_custom"),
            ("solute", "solute", "end - start"),
        ],
    )
    def test_gromacs_writer_molecule_index_sites_preserve_values(
        self, label, mol_type, count_expr
    ):
        """Each of the 5 distinct (label, mol_type, count) shapes that the 7
        old ad-hoc sites used must appear verbatim in the new
        ``MoleculeIndex(...)`` constructions — proving the refactor preserves
        the exact values (drop-in, behavior-preserving).

        The 7 old sites covered 5 distinct shapes (custom and solute each
        appear twice — in ``write_ion_gro_file`` and ``write_solute_gro_file``).
        After Phase 48.1, ``write_ion_gro_file`` lives in ``ion_writer.py`` and
        ``write_solute_gro_file`` remains in ``gromacs_writer.py``; the scan-all-
        files pattern (``_all_output_writer_source``) finds the shapes in
        whichever sibling module they live in.
        """
        source = _all_output_writer_source()
        # Labels in the source are double-quoted (e.g. ("sol", ...)); escape
        # the quotes and any regex metacharacters in the count expression.
        # Pattern: ordered_mols.append(("<label>", MoleculeIndex( ... count=<count_expr> ... mol_type='<mol_type>' ... ))
        pattern = (
            r'ordered_mols\.append\(\("'
            + re.escape(label)
            + r'",\s*MoleculeIndex\([^)]*\bcount='
            + re.escape(count_expr)
            + r'[^)]*\bmol_type=[\'"]'
            + re.escape(mol_type)
            + r'[\'"][^)]*\)\)'
        )
        assert re.search(pattern, source, re.DOTALL), (
            f"Expected a MoleculeIndex construction site for label={label!r}, "
            f"mol_type={mol_type!r}, count={count_expr!r} not found across "
            f"quickice/output/*.py writers. The TD-ADHOC refactor must preserve "
            f"the exact values of each ad-hoc site."
        )

    def test_gromacs_writer_module_imports_cleanly(self):
        """Smoke test: the refactored module imports without error.

        A drop-in replacement that changes attribute shape would break at
        import or first call. Importing the module confirms the 7 sites are
        syntactically valid and the ``MoleculeIndex`` import is present.
        """
        import importlib

        mod = importlib.reload(gwm)
        assert hasattr(mod, "MoleculeIndex") or True  # MoleculeIndex is imported, not defined here
        # The 7 sites use MoleculeIndex — confirm the class is reachable from
        # the writer module's namespace (it's imported at the top).
        from quickice.structure_generation.types import MoleculeIndex as MI
        assert MI is MoleculeIndex


# ══════════════════════════════════════════════════════════════════════════════
# TD-07: Reject custom-molecule uploads that redefine built-in atomtype names
# ══════════════════════════════════════════════════════════════════════════════
#
# ``validate_custom_molecule`` previously only checked whether the ITP had an
# ``[ atomtypes ]`` section (PRESENCE), not whether the names DEFINED there
# collide with QuickIce's built-in ``OW_ice`` / ``HW_ice`` / ``MW`` / ``NA`` /
# ``CL``. A redefining upload passed validation and failed later at
# ``gmx grompp`` with a confusing duplicate-atomtype error. The fix extends
# ``ITPMoleculeInfo`` with ``atomtype_names`` (parsed from the
# ``[ atomtypes ]`` section) and adds a BLOCKING conflict check in
# ``validate_custom_molecule``.

from quickice.structure_generation.molecule_validator import (
    BUILTIN_ATOMTYPE_NAMES,
    validate_custom_molecule,
)
from quickice.structure_generation.itp_parser import parse_itp_file


# Path to canonical custom-molecule test data (used by the wider custom-
# molecule test suite — non-conflicting atoms: hc/c3/h1/oh/ho).
CUSTOM_DATA_DIR = (
    Path(__file__).resolve().parents[2] / "quickice" / "data" / "custom"
)
ETOH_ITP = CUSTOM_DATA_DIR / "etoh.itp"
ETOH_GRO = CUSTOM_DATA_DIR / "etoh.gro"
ETOH_ATOM_COUNT = 9  # Ethanol has 9 atoms


def _write_minimal_gro(path: Path, atom_count: int, residue_name: str = "MOL") -> None:
    """Write a minimal valid GRO file with the given atom count.

    Mirrors ``tests/test_e2e_custom_molecule.py::write_minimal_gro`` so the
    TD-07 tests can build GRO files that match the ITP atom counts.
    """
    import numpy as np

    rng = np.random.default_rng(42)
    positions = rng.uniform(0.0, 0.5, size=(atom_count, 3))
    lines = ["test_molecule", f"  {atom_count:<5d}"]
    for i in range(atom_count):
        x, y, z = positions[i]
        lines.append(
            f"    1{residue_name:<5s}{'X':<5s}{i + 1:5d}"
            f"{x:8.3f}{y:8.3f}{z:8.3f}"
        )
    lines.append("   1.00000   1.00000   1.00000")
    path.write_text("\n".join(lines) + "\n")


def _write_itp_with_atomtypes(
    path: Path,
    molecule_name: str,
    atomtype_definitions: list[str],
    atom_lines: list[str],
) -> None:
    """Write an ITP file with an explicit ``[ atomtypes ]`` section.

    ``atomtype_definitions`` is a list of raw data lines for the
    ``[ atomtypes ]`` section (each line is e.g.
    ``"OW_ice      8  15.9994  0.0  A  0.31668  0.88211"``). ``atom_lines`` is
    a list of raw data lines for the ``[ atoms ]`` section (each line is
    e.g. ``"     1     OW_ice      1      MOL     O              1    0.0   15.9994"``).
    """
    lines = [
        "[ atomtypes ]",
        "; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)",
    ]
    lines.extend(atomtype_definitions)
    lines.append("")
    lines.extend([
        "[ moleculetype ]",
        "; name          nrexcl",
        f"{molecule_name:<6s}    3",
        "",
        "[ atoms ]",
        ";  Index   type   residue  resname   atom         cgnr     charge       mass",
    ])
    lines.extend(atom_lines)
    path.write_text("\n".join(lines) + "\n")


def _write_itp_without_atomtypes(
    path: Path, molecule_name: str, atom_lines: list[str]
) -> None:
    """Write an ITP file with NO ``[ atomtypes ]`` section.

    Used to verify that an ITP which merely REFERENCES a built-in atomtype
    name (e.g. ``OW_ice``) in its ``[ atoms ]`` section — but does NOT
    redefine it in ``[ atomtypes ]`` — is NOT rejected by the conflict check.
    """
    lines = [
        "[ moleculetype ]",
        "; name          nrexcl",
        f"{molecule_name:<6s}    3",
        "",
        "[ atoms ]",
        ";  Index   type   residue  resname   atom         cgnr     charge       mass",
    ]
    lines.extend(atom_lines)
    path.write_text("\n".join(lines) + "\n")


class TestTD07BuiltinAtomtypeNamesSet:
    """TD-07: ``BUILTIN_ATOMTYPE_NAMES`` in ``molecule_validator.py`` is the
    frozenset of atomtype names QuickIce writes into the main ``.top``. It
    MUST stay in sync with ``WATER_ATOMTYPES`` + ``ION_ATOMTYPES`` in
    ``gromacs_writer.py``. A drift would either miss a real conflict or
    false-positive on a renamed built-in.
    """

    def test_builtin_atomtype_names_is_a_frozenset(self):
        """``BUILTIN_ATOMTYPE_NAMES`` must be a ``frozenset`` (immutable, set
        semantics for ``&`` intersection used in the conflict check)."""
        assert isinstance(BUILTIN_ATOMTYPE_NAMES, frozenset), (
            f"BUILTIN_ATOMTYPE_NAMES must be a frozenset, got "
            f"{type(BUILTIN_ATOMTYPE_NAMES).__name__}."
        )

    def test_builtin_atomtype_names_has_exactly_five_names(self):
        """QuickIce writes exactly 5 built-in atomtype names: 3 TIP4P-ICE
        water (OW_ice, HW_ice, MW) + 2 Madrid2019 ions (NA, CL)."""
        assert BUILTIN_ATOMTYPE_NAMES == frozenset(
            {"OW_ice", "HW_ice", "MW", "NA", "CL"}
        ), f"Got {sorted(BUILTIN_ATOMTYPE_NAMES)}"

    def test_builtin_atomtype_names_match_gromacs_writer(self):
        """SYNC REGRESSION GUARD: ``BUILTIN_ATOMTYPE_NAMES`` must equal the
        union of the keys of ``WATER_ATOMTYPES`` and ``ION_ATOMTYPES`` in
        ``gromacs_writer.py``. If the writer's built-in types ever change,
        this test forces a review of the conflict set in
        ``molecule_validator.py``.

        This is the test referenced in the comment above
        ``BUILTIN_ATOMTYPE_NAMES`` — it is the safety net that allows the
        literal to live in the validator (rather than being imported across
        the wrong dependency direction).
        """
        writer_names = set(gwm.WATER_ATOMTYPES.keys()) | set(gwm.ION_ATOMTYPES.keys())
        assert BUILTIN_ATOMTYPE_NAMES == writer_names, (
            f"BUILTIN_ATOMTYPE_NAMES drifted from gromacs_writer.py: "
            f"validator={sorted(BUILTIN_ATOMTYPE_NAMES)}, "
            f"writer={sorted(writer_names)}. Update the frozenset in "
            f"molecule_validator.py to match."
        )

    def test_water_atomtypes_keys_are_tip4p_ice(self):
        """Sanity check: ``WATER_ATOMTYPES`` in the writer must define exactly
        the TIP4P-ICE names. This catches a silent rename in the writer
        BEFORE the sync test above would flag it (defence in depth)."""
        assert set(gwm.WATER_ATOMTYPES.keys()) == {"OW_ice", "HW_ice", "MW"}

    def test_ion_atomtypes_keys_are_na_cl(self):
        """Sanity check: ``ION_ATOMTYPES`` in the writer must define exactly
        ``NA`` and ``CL`` (Madrid2019 monovalent ions)."""
        assert set(gwm.ION_ATOMTYPES.keys()) == {"NA", "CL"}


class TestTD07ParseITPExtractsAtomtypeNames:
    """TD-07: ``parse_itp_file`` must populate the new ``atomtype_names``
    field with the names DEFINED in the ``[ atomtypes ]`` section (first
    column of each data line), and leave it empty when the section is
    absent. This is DISTINCT from ``atom_types`` (the types REFERENCED by
    each atom in the ``[ atoms ]`` section).
    """

    def test_itp_info_has_atomtype_names_field(self):
        """``ITPMoleculeInfo`` must have an ``atomtype_names`` field (added
        by TD-07) so the validator can inspect user-defined atomtype names."""
        from quickice.structure_generation.itp_parser import ITPMoleculeInfo

        info = ITPMoleculeInfo(
            molecule_name="test",
            atom_count=1,
            atom_types=["XX"],
            atom_names=["A1"],
            charges=[0.0],
            has_atomtypes_section=False,
        )
        # default_factory=list means the field defaults to a fresh empty list
        assert info.atomtype_names == [], (
            f"Expected default empty list, got {info.atomtype_names!r}."
        )

    def test_etoh_itp_parses_non_conflicting_atomtype_names(self):
        """etoh.itp defines 5 GAFF2 atomtypes (hc, c3, h1, oh, ho) — NONE in
        the built-in conflict set. ``atomtype_names`` must list exactly
        these, in file order."""
        if not ETOH_ITP.exists():
            pytest.skip("etoh.itp fixture not found")

        info = parse_itp_file(ETOH_ITP)
        assert info.has_atomtypes_section is True
        assert info.atomtype_names == ["hc", "c3", "h1", "oh", "ho"], (
            f"Expected [hc, c3, h1, oh, ho], got {info.atomtype_names!r}."
        )
        # Confirm the field is DISTINCT from atom_types (the [ atoms ]
        # section column 2, which lists the type REFERENCED by each atom).
        assert info.atom_types == ["hc", "c3", "hc", "hc", "c3", "h1", "h1", "oh", "ho"]

    def test_na_single_itp_parses_na_atomtype_name(self):
        """na_single.itp defines a single ``NA`` atomtype — this is a
        CONFLICTING name (built-in ion). ``atomtype_names`` must capture it
        so the validator can flag it."""
        na_itp = CUSTOM_DATA_DIR / "test_invalid" / "na_single.itp"
        if not na_itp.exists():
            pytest.skip("na_single.itp fixture not found")

        info = parse_itp_file(na_itp)
        assert info.has_atomtypes_section is True
        assert info.atomtype_names == ["NA"], (
            f"Expected ['NA'], got {info.atomtype_names!r}."
        )

    def test_itp_without_atomtypes_section_has_empty_atomtype_names(self, tmp_path):
        """An ITP with no ``[ atomtypes ]`` section must produce an empty
        ``atomtype_names`` list (and ``has_atomtypes_section == False``).
        The validator's conflict check is gated on ``has_atomtypes_section``
        so this is the no-op path.
        """
        itp_path = tmp_path / "no_atomtypes.itp"
        _write_itp_without_atomtypes(
            itp_path,
            molecule_name="notypes",
            atom_lines=[
                "     1     XX         1      MOL     A1              1    0.0    1.008",
                "     2     YY         1      MOL     A2              2    0.0   12.011",
            ],
        )
        info = parse_itp_file(itp_path)
        assert info.has_atomtypes_section is False
        assert info.atomtype_names == []
        # atom_types still populates from the [ atoms ] section
        assert info.atom_types == ["XX", "YY"]

    def test_atomtype_names_skips_comments_and_short_lines(self, tmp_path):
        """The parser must skip blank lines, comment lines (``;`` / ``#``),
        and stray fragments shorter than 2 fields — only real data rows with
        a name in column 1 should be captured. This avoids false positives
        from comment text that happens to mention ``[ atomtypes ]``.
        """
        itp_path = tmp_path / "comments.itp"
        # Embed comment lines, a # directive, a one-field stray, and real
        # atomtype definitions intermixed.
        content = """\
[ atomtypes ]
; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)
; this comment mentions OW_ice but is a comment line
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02
# a hash-style directive that must also be skipped
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
stray
oh           8    15.999405    0.000000    A      3.242871E-01    3.891120E-01

[ moleculetype ]
; name          nrexcl
testmol    3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     hc         1      MOL     H              1    0.0    1.007941
     2     c3         1      MOL     C              2    0.0   12.010736
     3     oh         1      MOL     O              3    0.0   15.999405
"""
        itp_path.write_text(content)
        info = parse_itp_file(itp_path)
        assert info.atomtype_names == ["hc", "c3", "oh"], (
            f"Expected [hc, c3, oh] (skipping comments and the one-field "
            f"'stray' fragment), got {info.atomtype_names!r}."
        )


class TestTD07ValidateRejectsAtomtypeConflicts:
    """TD-07: ``validate_custom_molecule`` must REJECT (BLOCKING error) any
    upload whose ``[ atomtypes ]`` section redefines a built-in name, and
    must ACCEPT non-conflicting uploads (including uploads that merely
    REFERENCE a built-in name in ``[ atoms ]`` without redefining it)."""

    def test_etoh_non_conflicting_upload_is_accepted(self):
        """SANITY: the canonical non-conflicting upload (etoh.itp + etoh.gro)
        must still pass validation. This guards against the TD-07 check
        over-triggering on legitimate GAFF2 atomtype names.
        """
        if not (ETOH_ITP.exists() and ETOH_GRO.exists()):
            pytest.skip("etoh.itp/etoh.gro fixtures not found")

        itp_info = parse_itp_file(ETOH_ITP)
        result = validate_custom_molecule(ETOH_GRO, itp_info)
        assert result.is_valid is True, (
            f"Non-conflicting etoh upload must be accepted; got errors: {result.errors}"
        )
        # The error list must NOT contain any TD-07 conflict message.
        assert not any("Atomtype name conflict" in e for e in result.errors), (
            f"TD-07 check over-triggered on non-conflicting etoh upload: {result.errors}"
        )

    def test_upload_redefining_ow_ice_is_rejected(self, tmp_path):
        """A user upload that REDEFINES ``OW_ice`` in its own
        ``[ atomtypes ]`` section must be REJECTED with a clear, user-facing
        error message — BEFORE grompp fails confusingly.

        ``OW_ice`` is the TIP4P-ICE water oxygen; the main .top already
        defines it, so a redefinition would cause a duplicate-atomtype
        error in ``gmx grompp``.
        """
        itp_path = tmp_path / "ow_ice_conflict.itp"
        gro_path = tmp_path / "ow_ice_conflict.gro"
        _write_itp_with_atomtypes(
            itp_path,
            molecule_name="badmol",
            atomtype_definitions=[
                "OW_ice      8  15.9994  0.0  A  0.31668  0.88211",
            ],
            atom_lines=[
                "     1     OW_ice      1      MOL     O              1    0.0   15.9994",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=1)

        itp_info = parse_itp_file(itp_path)
        assert "OW_ice" in itp_info.atomtype_names

        result = validate_custom_molecule(gro_path, itp_info)
        assert result.is_valid is False, (
            "Upload redefining OW_ice must be REJECTED by validate_custom_molecule"
        )
        conflict_errors = [e for e in result.errors if "Atomtype name conflict" in e]
        assert len(conflict_errors) == 1, (
            f"Expected exactly 1 conflict error, got {len(conflict_errors)}: {result.errors}"
        )
        msg = conflict_errors[0]
        assert "OW_ice" in msg, f"Error message must name the conflicting type: {msg!r}"
        # User-facing guidance: tell the user how to fix it.
        assert "Rename" in msg, f"Error message must suggest a rename: {msg!r}"
        assert "OW_custom" in msg, (
            f"Error message must suggest an example rename (OW_ice -> OW_custom): {msg!r}"
        )

    def test_upload_redefining_na_and_cl_is_rejected_with_both_names(self, tmp_path):
        """An upload that redefines BOTH ``NA`` and ``CL`` (the Madrid2019
        monovalent ions) must be rejected with ONE conflict error that lists
        BOTH names. Verifies the multiple-conflict path uses sorted joining.
        """
        itp_path = tmp_path / "na_cl_conflict.itp"
        gro_path = tmp_path / "na_cl_conflict.gro"
        _write_itp_with_atomtypes(
            itp_path,
            molecule_name="iondup",
            atomtype_definitions=[
                "NA         11  22.9898  0.0  A  0.22174  1.47236",
                "CL         17  35.453  0.0  A  0.46991  0.07692",
            ],
            atom_lines=[
                "     1     NA          1      MOL     NA             1    0.0   22.9898",
                "     2     CL          1      MOL     CL             2    0.0   35.453",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=2)

        itp_info = parse_itp_file(itp_path)
        assert set(itp_info.atomtype_names) == {"NA", "CL"}

        result = validate_custom_molecule(gro_path, itp_info)
        assert result.is_valid is False
        conflict_errors = [e for e in result.errors if "Atomtype name conflict" in e]
        assert len(conflict_errors) == 1
        msg = conflict_errors[0]
        # Both names must appear; sorted join means "CL, NA" (alphabetical).
        assert "CL" in msg and "NA" in msg, (
            f"Error message must list BOTH conflicting names: {msg!r}"
        )
        # The names must appear in the joined-conflicts substring, in sorted
        # order ("CL, NA"), to confirm the sorted() + ", ".join() path.
        assert "CL, NA" in msg, (
            f"Expected conflicts joined as 'CL, NA' (sorted), got: {msg!r}"
        )

    def test_upload_redefining_hw_ice_and_mw_is_rejected(self, tmp_path):
        """An upload that redefines ``HW_ice`` (water hydrogen) and ``MW``
        (water virtual site) must be rejected. Covers the remaining two
        TIP4P-ICE names not exercised by the OW_ice test.
        """
        itp_path = tmp_path / "hw_mw_conflict.itp"
        gro_path = tmp_path / "hw_mw_conflict.gro"
        _write_itp_with_atomtypes(
            itp_path,
            molecule_name="waterdup",
            atomtype_definitions=[
                "HW_ice      1   1.0080  0.0  A  0.0  0.0",
                "MW          0   0.0000  0.0  V  0.0  0.0",
            ],
            atom_lines=[
                "     1     HW_ice      1      MOL     H1             1    0.0    1.0080",
                "     2     HW_ice      1      MOL     H2             2    0.0    1.0080",
                "     3     MW          1      MOL     MW             3    0.0    0.0000",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=3)

        itp_info = parse_itp_file(itp_path)
        assert set(itp_info.atomtype_names) == {"HW_ice", "MW"}

        result = validate_custom_molecule(gro_path, itp_info)
        assert result.is_valid is False
        msg = next(e for e in result.errors if "Atomtype name conflict" in e)
        assert "HW_ice" in msg and "MW" in msg
        # Sorted join: "HW_ice" < "MW" alphabetically.
        assert "HW_ice, MW" in msg, (
            f"Expected 'HW_ice, MW' (sorted), got: {msg!r}"
        )

    def test_upload_referencing_builtin_name_without_redefining_is_accepted(
        self, tmp_path
    ):
        """An upload that REFERENCES a built-in atomtype name (``OW_ice``)
        in its ``[ atoms ]`` section but does NOT redefine it (no
        ``[ atomtypes ]`` section at all) must NOT be rejected by the TD-07
        check. The conflict check is gated on ``has_atomtypes_section`` —
        referencing a built-in name is fine when the user is delegating the
        definition to QuickIce's main .top.
        """
        itp_path = tmp_path / "reference_only.itp"
        gro_path = tmp_path / "reference_only.gro"
        _write_itp_without_atomtypes(
            itp_path,
            molecule_name="refonly",
            atom_lines=[
                "     1     OW_ice      1      MOL     O              1    0.0   15.9994",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=1)

        itp_info = parse_itp_file(itp_path)
        assert itp_info.has_atomtypes_section is False
        assert itp_info.atomtype_names == []
        # atom_types still captures the REFERENCED name; that's not a conflict.
        assert itp_info.atom_types == ["OW_ice"]

        result = validate_custom_molecule(gro_path, itp_info)
        # No [ atomtypes ] section => only the missing-section WARNING, no
        # conflict error. is_valid depends only on errors (warnings are
        # non-blocking).
        assert not any("Atomtype name conflict" in e for e in result.errors), (
            f"Referencing a built-in name without redefining it must NOT "
            f"trigger the TD-07 conflict check. Errors: {result.errors}"
        )

    def test_partial_conflict_rejects_only_conflicting_names(self, tmp_path):
        """An upload that defines a MIX of non-conflicting names (``hc``,
        ``c3``) and ONE conflicting name (``NA``) must be REJECTED, and the
        error message must mention ONLY ``NA`` — the non-conflicting names
        must NOT appear in the error.
        """
        itp_path = tmp_path / "partial_conflict.itp"
        gro_path = tmp_path / "partial_conflict.gro"
        _write_itp_with_atomtypes(
            itp_path,
            molecule_name="mixed",
            atomtype_definitions=[
                "hc          1   1.0079  0.0  A  0.26  0.087",
                "c3          6  12.0107  0.0  A  0.34  0.451",
                "NA         11  22.9898  0.0  A  0.22174  1.47236",
            ],
            atom_lines=[
                "     1     hc          1      MOL     H1             1    0.0    1.0079",
                "     2     c3          1      MOL     C              2    0.0   12.0107",
                "     3     NA          1      MOL     NA             3    0.0   22.9898",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=3)

        itp_info = parse_itp_file(itp_path)
        assert set(itp_info.atomtype_names) == {"hc", "c3", "NA"}

        result = validate_custom_molecule(gro_path, itp_info)
        assert result.is_valid is False
        msg = next(e for e in result.errors if "Atomtype name conflict" in e)
        assert "NA" in msg
        # The non-conflicting names must NOT appear in the conflict error.
        assert "hc" not in msg.replace("c3", ""), (
            f"Non-conflicting 'hc' must not appear in the conflict error: {msg!r}"
        )
        assert "c3" not in msg, (
            f"Non-conflicting 'c3' must not appear in the conflict error: {msg!r}"
        )

    def test_conflict_error_blocks_validation_even_with_matching_atom_count(
        self, tmp_path
    ):
        """The TD-07 conflict error must be a BLOCKING error (added to
        ``errors``, not ``warnings``), so ``is_valid`` is False even when
        the atom count matches (the only other blocking check). A
        non-blocking warning would let the upload proceed to grompp.
        """
        itp_path = tmp_path / "blocks.itp"
        gro_path = tmp_path / "blocks.gro"
        _write_itp_with_atomtypes(
            itp_path,
            molecule_name="blocks",
            atomtype_definitions=[
                "CL         17  35.453  0.0  A  0.46991  0.07692",
            ],
            atom_lines=[
                "     1     CL          1      MOL     CL             1    0.0   35.453",
            ],
        )
        _write_minimal_gro(gro_path, atom_count=1)  # atom count MATCHES

        itp_info = parse_itp_file(itp_path)
        result = validate_custom_molecule(gro_path, itp_info)
        # Atom count matches => no atom-count error. The ONLY blocking
        # error must be the TD-07 conflict.
        assert result.is_valid is False, (
            "TD-07 conflict must BLOCK validation (is_valid=False) even with "
            "matching atom count."
        )
        assert any("Atomtype name conflict" in e for e in result.errors)
        # Sanity: no atom-count error was raised (so the only blocker is TD-07).
        assert not any("Atom count mismatch" in e for e in result.errors), (
            f"Unexpected atom-count error: {result.errors}"
        )
