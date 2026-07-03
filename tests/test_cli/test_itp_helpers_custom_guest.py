"""Unit tests for ``copy_custom_guest_itp`` + custom-guest routing in the CLI
hydrate ITP copy path (plan 41-07).

Validates that:

1. ``copy_custom_guest_itp`` reads a custom guest ITP, applies the full
   ``transform_guest_itp`` pipeline (``[ atomtypes ]`` commented out,
   ``[ moleculetype ]`` renamed to ``'{residue_name}_H'``, ``[ atoms ]``
   resname column rewritten), and writes it to ``output_dir/<itp basename>``.
2. A missing source ITP returns ``None`` (logs, no exception).
3. A base residue name that pushes ``'{name}_H'`` past the 5-char GRO limit
   returns ``None`` (the underlying ``ValueError`` is caught + logged, not
   re-raised).
4. The hydrate branch of ``copy_itp_files_for_structure`` routes custom guests
   (``config.is_custom_guest``) through ``copy_custom_guest_itp`` — copying
   the custom ``etoh.itp`` AND the always-required ``tip4p-ice.itp``.
5. Built-in ch4 hydrate ITP copy is unchanged (regression): the built-in path
   still uses ``_copy_hydrate_guest_itp`` → ``ch4_hydrate.itp``.

These are pure-Python unit tests (no ``gmx`` dependency, no GenIce2 calls);
``HydrateStructure`` instances are constructed manually with duck-typed
attributes mirroring the pattern in ``tests/test_hydrate_config_metadata.py``.
"""

import re
from pathlib import Path

import numpy as np
import pytest

from quickice.cli.itp_helpers import copy_custom_guest_itp, copy_itp_files_for_structure
from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
)

# Absolute paths to the bundled custom-ethanol fixtures.  Using Path(__file__)
# keeps the tests cwd-independent regardless of pytest's invocation directory.
_TESTS_DIR = Path(__file__).resolve().parents[1]  # .../tests
_DATA_CUSTOM = _TESTS_DIR.parent / "quickice" / "data" / "custom"
ETOH_ITP = _DATA_CUSTOM / "etoh.itp"
ETOH_GRO = _DATA_CUSTOM / "etoh.gro"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _moleculetype_name(text: str) -> str | None:
    """Return the ``[ moleculetype ]`` name declared in ``text``.

    Scans for the ``[ moleculetype ]`` header and returns the first
    non-comment, non-blank line's first whitespace token.  Returns ``None``
    if the section is absent.
    """
    in_molt = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_molt = "moleculetype" in stripped.lower()
            continue
        if in_molt and stripped and not stripped.startswith(";") and not stripped.startswith("#"):
            return stripped.split()[0]
    return None


def _make_hydrate_structure(config: HydrateConfig, *, custom: bool) -> HydrateStructure:
    """Build a minimal HydrateStructure (no GenIce2 needed).

    For ``custom=True``: 2 water + 1 ethanol (17 atoms; ethanol has 9 atoms).
    For ``custom=False`` (built-in ch4): 2 water + 1 ch4 (13 atoms; ch4 has 5).
    """
    if custom:
        n_water_atoms = 8  # 2 waters × 4 atoms (OW, HW1, HW2, MW)
        guest_atoms = 9
        atom_names = (
            ["OW", "HW1", "HW2", "MW"] * 2
            + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
        )
        molecule_index = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 4, "water"),
            MoleculeIndex(8, guest_atoms, config.guest_type),
        ]
        guest_count = 1
    else:
        n_water_atoms = 8
        guest_atoms = 5  # ch4: C + 4H
        atom_names = (
            ["OW", "HW1", "HW2", "MW"] * 2
            + ["C", "H", "H", "H", "H"]
        )
        molecule_index = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 4, "water"),
            MoleculeIndex(8, guest_atoms, config.guest_type),
        ]
        guest_count = 1

    n_atoms = n_water_atoms + guest_atoms
    return HydrateStructure(
        positions=np.zeros((n_atoms, 3)),
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        molecule_index=molecule_index,
        config=config,
        lattice_info=HydrateLatticeInfo.from_lattice_type(config.lattice_type),
        report="Test report",
        guest_count=guest_count,
        water_count=2,
        guest_name=config.guest_name,
        guest_atom_labels=config.guest_atom_labels,
        guest_atom_count=config.guest_atom_count,
        guest_itp_path=config.guest_itp_path,
    )


def _custom_hydrate_config() -> HydrateConfig:
    """Build a custom-guest HydrateConfig pointing at the bundled etoh fixtures."""
    return HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",  # not in GUEST_MOLECULES → is_custom_guest=True
        guest_residue_name="MOL",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        guest_itp_path=str(ETOH_ITP),
        guest_gro_path=str(ETOH_GRO),
    )


# ── copy_custom_guest_itp: transform contract ─────────────────────────────────

def test_copy_custom_guest_itp_transforms(tmp_path):
    """copy_custom_guest_itp produces a transformed etoh.itp with MOL_H moltype,
    [atomtypes] commented, and [atoms] resname MOL_H."""
    itp_name = copy_custom_guest_itp(tmp_path, ETOH_ITP, "MOL")

    # Returns the basename of the source ITP.
    assert itp_name == "etoh.itp", f"expected 'etoh.itp', got {itp_name!r}"

    # File was actually written to the output dir.
    dest = tmp_path / "etoh.itp"
    assert dest.exists(), f"{dest} should exist after copy_custom_guest_itp"
    text = dest.read_text()

    # [ moleculetype ] name is now MOL_H (header followed by name + nrexcl).
    assert re.search(r"\[\s*moleculetype\s*\][\s\S]*?MOL_H\s+\d", text) is not None, (
        "Transformed ITP [ moleculetype ] name should be 'MOL_H'"
    )

    # [ atomtypes ] header is commented out (EXPORT-02).
    assert "; [ atomtypes ]" in text, (
        "Transformed ITP should have [ atomtypes ] header commented out"
    )
    # No uncommented [ atomtypes ] header remains.
    uncommented_atomtypes = [
        line for line in text.splitlines() if line.strip() == "[ atomtypes ]"
    ]
    assert uncommented_atomtypes == [], (
        "Transformed ITP must NOT contain an uncommented [ atomtypes ] header; "
        f"found: {uncommented_atomtypes}"
    )

    # [ atoms ] resname column (4th whitespace field, 0-based index 3) is MOL_H.
    assert re.search(r"(?m)^\s*\d+\s+\S+\s+\d+\s+MOL_H\s", text) is not None, (
        "Transformed ITP [ atoms ] resname column should be 'MOL_H'"
    )


# ── copy_custom_guest_itp: error paths ───────────────────────────────────────

def test_copy_custom_guest_itp_missing_returns_none(tmp_path):
    """A missing source ITP returns None (logs, no exception)."""
    missing = Path("nonexistent.itp")
    result = copy_custom_guest_itp(tmp_path, missing, "MOL")
    assert result is None, (
        "copy_custom_guest_itp on a missing file should return None, not raise"
    )
    # Nothing was written.
    assert not (tmp_path / "nonexistent.itp").exists()


def test_copy_custom_guest_itp_name_too_long(tmp_path):
    """A base name that pushes '{name}_H' over the 5-char GRO limit returns None.

    'ETHAN' (5) + '_H' = 'ETHAN_H' (7 chars) > 5 → transform_guest_itp raises
    ValueError → caught (except (OSError, ValueError)) → logged → None.
    """
    result = copy_custom_guest_itp(tmp_path, ETOH_ITP, "ETHAN")
    assert result is None, (
        "copy_custom_guest_itp with a >5-char residue name should return None "
        "(caught ValueError), not raise"
    )


# ── copy_itp_files_for_structure: hydrate routing ─────────────────────────────

def test_hydrate_step_custom_routes_to_copy_custom(tmp_path):
    """For a custom-guest HydrateStructure, copy_itp_files_for_structure uses
    copy_custom_guest_itp (config.guest_itp_path + config.guest_residue_name),
    copying etoh.itp AND the always-required tip4p-ice.itp."""
    config = _custom_hydrate_config()
    structure = _make_hydrate_structure(config, custom=True)

    copied = copy_itp_files_for_structure(tmp_path, structure, "hydrate")

    # Both tip4p-ice.itp and the custom etoh.itp should be staged.
    assert "tip4p-ice.itp" in copied, f"tip4p-ice.itp missing from {copied}"
    assert "etoh.itp" in copied, f"etoh.itp missing from {copied}"

    # Files exist on disk.
    assert (tmp_path / "tip4p-ice.itp").exists()
    assert (tmp_path / "etoh.itp").exists()

    # The staged etoh.itp has moleculetype MOL_H (not the source 'etoh').
    staged_text = (tmp_path / "etoh.itp").read_text()
    assert _moleculetype_name(staged_text) == "MOL_H", (
        "Staged custom etoh.itp [ moleculetype ] name should be 'MOL_H', "
        f"got {_moleculetype_name(staged_text)!r}"
    )


def test_hydrate_step_builtin_ch4_regression(tmp_path):
    """Built-in ch4 hydrate ITP copy is unchanged: still uses
    _copy_hydrate_guest_itp → ch4_hydrate.itp (NOT copy_custom_guest_itp)."""
    config = HydrateConfig(lattice_type="sI", guest_type="ch4")
    structure = _make_hydrate_structure(config, custom=False)

    copied = copy_itp_files_for_structure(tmp_path, structure, "hydrate")

    # tip4p-ice.itp + ch4_hydrate.itp (NOT etoh.itp, NOT custom path).
    assert "tip4p-ice.itp" in copied, f"tip4p-ice.itp missing from {copied}"
    assert "ch4_hydrate.itp" in copied, (
        f"Built-in ch4 path should stage ch4_hydrate.itp; got {copied}"
    )

    # Files exist on disk.
    assert (tmp_path / "tip4p-ice.itp").exists()
    assert (tmp_path / "ch4_hydrate.itp").exists()
