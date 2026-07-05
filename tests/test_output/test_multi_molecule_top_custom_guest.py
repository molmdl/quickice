"""Unit tests for custom guest residue name + atomtypes merge in
write_multi_molecule_top_file.

Phase 41-03 (EXPORT-01 + EXPORT-03): When a hydrate system has a custom guest
molecule (e.g. ethanol with `mol_type == "etoh_e2e"`), the TOP writer must
(1) list the custom guest under custom_guest_info['residue_name'] (e.g.
"MOL_H") in [ molecules ] instead of falling through to "UNK", and
(2) merge the custom guest's [ atomtypes ] into the main .top [ atomtypes ]
block via _merge_custom_atomtypes (dedup against already-written types).

The `custom_guest_info` dict has the shape:
    {"mol_type": str, "residue_name": str, "itp_path": Path}

The `#include` for the custom guest .itp is already produced by the existing
`itp_files` mapping (unchanged by this plan); this plan only adds the
residue-name branch and the atomtypes merge.
"""

import re
import sys
from pathlib import Path

from quickice.output.gromacs_writer import write_multi_molecule_top_file
from quickice.structure_generation.types import MoleculeIndex

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e2e_export_helpers import parse_top_molecules, parse_top_includes  # noqa: E402


# Real etoh.itp fixture (cwd-independent absolute path; same convention as
# test_merge_custom_atomtypes.py in this directory).  The TOP writer opens
# this path via parse_itp_atomtypes, so it must resolve regardless of CWD.
_ETOH_ITP = (
    Path(__file__).resolve().parent.parent.parent
    / "quickice" / "data" / "custom" / "etoh.itp"
)


# ── Synthetic custom-guest system (no GenIce2) ──────────────────────────────
# 2 water molecules (TIP4P: 4 atoms each) + 1 custom ethanol guest (9 atoms).
# molecule_index only — write_multi_molecule_top_file does not need positions.


def _build_custom_guest_system():
    """Build molecule_index + itp_files + custom_guest_info for the etoh test."""
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
    ]
    itp_files = {"etoh_e2e": "etoh.itp"}
    custom_guest_info = {
        "mol_type": "etoh_e2e",
        "residue_name": "MOL_H",
        "itp_path": _ETOH_ITP,
    }
    return molecule_index, itp_files, custom_guest_info


def _write_custom_guest_top(tmp_path):
    """Write the custom-guest .top and return (top_path_str, text)."""
    molecule_index, itp_files, custom_guest_info = _build_custom_guest_system()
    top_path = tmp_path / "out.top"
    write_multi_molecule_top_file(
        molecule_index,
        str(top_path),
        "test",
        itp_files=itp_files,
        custom_guest_info=custom_guest_info,
    )
    text = top_path.read_text()
    return str(top_path), text


def _atomtypes_block(text):
    """Slice the [ atomtypes ] block from the .top text.

    Returns the text from the '[ atomtypes ]' header up to (but not including)
    the next section header that begins a line with '[ '.
    """
    start = text.index("[ atomtypes ]")
    next_section = text.find("\n[ ", start + 1)
    if next_section == -1:
        return text[start:]
    return text[start:next_section]


# ── Test 1: [ molecules ] lists MOL_H (not UNK) ───────────────────────────────
def test_molecules_has_mol_h(tmp_path):
    top_path, _ = _write_custom_guest_top(tmp_path)
    molecules = parse_top_molecules(top_path)

    assert molecules.get("MOL_H") == 1, (
        f"expected MOL_H count 1, got {molecules!r}"
    )
    assert molecules.get("SOL") == 2, (
        f"expected SOL count 2, got {molecules!r}"
    )
    assert "UNK" not in molecules, (
        f"'UNK' present in [ molecules ] (fall-through bug): {molecules!r}"
    )


# ── Test 2: [ atomtypes ] has oh and ho (ethanol-only types) ─────────────────
def test_atomtypes_has_oh_ho(tmp_path):
    _, text = _write_custom_guest_top(tmp_path)
    block = _atomtypes_block(text)

    def _has_first_token(block_text, token):
        for line in block_text.splitlines():
            parts = line.split()
            if parts and parts[0] == token:
                return True
        return False

    assert _has_first_token(block, "oh"), (
        f"expected an 'oh' atomtype line in [ atomtypes ], got:\n{block}"
    )
    assert _has_first_token(block, "ho"), (
        f"expected an 'ho' atomtype line in [ atomtypes ], got:\n{block}"
    )


# ── Test 3: hc/c3/h1 deduped (appear at most once) ──────────────────────────
def test_atomtypes_dedup_hc_c3_h1(tmp_path):
    _, text = _write_custom_guest_top(tmp_path)
    block = _atomtypes_block(text)

    for name in ("hc", "c3", "h1"):
        # Count lines whose first non-whitespace token is exactly `name`.
        count = len(re.findall(rf"^{re.escape(name)}\b", block, re.MULTILINE))
        assert count <= 1, (
            f"atomtype '{name}' appears {count} times in [ atomtypes ] "
            f"(should be deduped to <= 1):\n{block}"
        )


# ── Test 4: #include etoh.itp + tip4p-ice.itp ────────────────────────────────
def test_includes_etoh_itp(tmp_path):
    top_path, _ = _write_custom_guest_top(tmp_path)
    includes = parse_top_includes(top_path)

    assert "etoh.itp" in includes, (
        f"expected 'etoh.itp' in #includes, got {includes!r}"
    )
    assert "tip4p-ice.itp" in includes, (
        f"expected 'tip4p-ice.itp' in #includes, got {includes!r}"
    )


# ── Test 5: atomtypes merge precedes #include (GROMACS ordering invariant) ──
def test_atomtypes_before_include(tmp_path):
    _, text = _write_custom_guest_top(tmp_path)
    # The '; custom guest ...' merge comment must precede the first #include.
    assert text.index("#include") > text.index("custom guest"), (
        "atomtypes merge (custom guest comment) must precede the #include "
        "block (GROMACS ordering invariant). "
        f"custom guest at {text.index('custom guest')}, "
        f"#include at {text.index('#include')}"
    )


# ── Test 6: built-in ch4 regression (no custom_guest_info) ───────────────────
def test_builtin_ch4_regression(tmp_path):
    """Built-in CH4 hydrate path must remain unchanged with no custom_guest_info.

    [ molecules ] must list 'CH4' (from get_guest_residue_name('ch4')) and
    'SOL'; 'UNK' must be absent.  Confirms no regression from adding the
    custom_guest_info parameter.
    """
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 5, "ch4"),
    ]
    itp_files = {"ch4": "ch4_hydrate.itp"}
    top_path = tmp_path / "out_ch4.top"

    # No custom_guest_info → defaults to None → built-in path unchanged.
    write_multi_molecule_top_file(
        molecule_index,
        str(top_path),
        "test",
        itp_files=itp_files,
    )

    molecules = parse_top_molecules(str(top_path))
    assert molecules.get("CH4") == 1, (
        f"expected CH4 count 1, got {molecules!r}"
    )
    assert molecules.get("SOL") == 1, (
        f"expected SOL count 1, got {molecules!r}"
    )
    assert "UNK" not in molecules, (
        f"'UNK' present in built-in ch4 [ molecules ] (regression): {molecules!r}"
    )
