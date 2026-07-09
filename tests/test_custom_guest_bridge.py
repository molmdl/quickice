"""Unit tests for custom_guest_bridge (Phase 40-04).

Tests build_custom_guest_module, validate_custom_guest_files, and the
sys.modules injection/cleanup primitives (custom_guest_module context
manager + register_custom_guest/unregister_custom_guest pair).

Validation reject paths covered:
- unparseable GRO (not_a_gro.txt, etoh_mismatch.gro)
- atom count mismatch (etoh_mismatch.gro)
- residue name >3 chars (synthetic 'ETHAN' GRO via tmp_path)
- comb-rule=1 (etoh_combrule1.itp)
- invalid guest_type (audit_name failure)

Injection/cleanup lifecycle covered:
- context manager registers + cleans up (normal exit)
- context manager cleans up on exception (try/finally)
- register/unregister pair (GUI async path)
- unregister when absent is safe
- re-register after cleanup works
- safe_import finds the injected module
"""

import sys
from pathlib import Path

import pytest

from quickice.structure_generation.custom_guest_bridge import (
    build_custom_guest_module,
    custom_guest_module,
    register_custom_guest,
    unregister_custom_guest,
    validate_custom_guest_files,
)

# Project root (tests/ -> project root)
PROJECT_ROOT = Path(__file__).parent.parent
CUSTOM_DIR = PROJECT_ROOT / "quickice" / "data" / "custom"
INVALID_DIR = CUSTOM_DIR / "test_invalid"
ETOH_GRO = CUSTOM_DIR / "etoh.gro"
ETOH_ITP = CUSTOM_DIR / "etoh.itp"
ETOH_MISMATCH_GRO = INVALID_DIR / "etoh_mismatch.gro"
NOT_A_GRO = INVALID_DIR / "not_a_gro.txt"
ETOH_COMBRULE1_ITP = INVALID_DIR / "etoh_combrule1.itp"
ETOH_NO_ATOMTYPES_ITP = INVALID_DIR / "etoh_no_atomtypes.itp"

# Ethanol atoms (9) used to synthesize GRO fixtures with arbitrary resnames.
ETOH_ATOMS = [
    ("H", 0.208, 0.048, -0.000),
    ("C", 0.122, -0.022, 0.000),
    ("H", 0.130, -0.086, -0.089),
    ("H", 0.130, -0.086, 0.089),
    ("C", -0.009, 0.054, -0.000),
    ("H", -0.014, 0.120, 0.089),
    ("H", -0.014, 0.120, -0.089),
    ("O", -0.115, -0.040, -0.000),
    ("H", -0.198, 0.009, 0.000),
]


def _write_gro(path: Path, resname: str, atoms=ETOH_ATOMS) -> Path:
    """Write a properly-formatted GRO file with the given residue name.

    GRO fixed-width columns (0-indexed):
        0-4  resnum, 5-9 resname (5, left-justified), 10-14 atomname (5,
        right-justified), 15-19 atomnum, 20-27/28-35/36-43 x/y/z (8.3).
    """
    lines = [resname.lower(), str(len(atoms))]
    for i, (name, x, y, z) in enumerate(atoms, 1):
        lines.append(
            f"{i:5d}{resname:<5}{name:>5}{i:5d}{x:8.3f}{y:8.3f}{z:8.3f}"
        )
    lines.append("   0.00000   0.00000   0.00000")
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture(autouse=True)
def _clean_sys_modules():
    """Remove any stale custom guest keys before/after each test.

    Defensive cleanup so a leaked registration in one test cannot break the
    `assert key not in sys.modules` entry guard in another.
    """
    stale = [k for k in list(sys.modules) if k.startswith("genice2.molecules.etoh")]
    for k in stale:
        sys.modules.pop(k, None)
    yield
    stale = [k for k in list(sys.modules) if k.startswith("genice2.molecules.etoh")]
    for k in stale:
        sys.modules.pop(k, None)


# ── Build tests ────────────────────────────────────────────────────────────


class TestBuildCustomGuestModule:
    """Tests for build_custom_guest_module (GRO -> centered Molecule module)."""

    def test_build_valid_etoh(self):
        """Build a module from etoh.gro; verify name_, labels_, sites_ centered."""
        mod = build_custom_guest_module(ETOH_GRO, "etoh_test", "MOL")
        mol = mod.Molecule()
        assert mol.name_ == "MOL"
        assert len(mol.labels_) == 9
        assert mol.sites_.shape == (9, 3)
        # sites_ must be centered (mean ~0 per axis) because GenIce2's
        # arrange() adds the cage center to sites_.
        assert abs(mol.sites_.mean(axis=0)).max() < 1e-10
        # labels_ match the GRO atom names
        assert mol.labels_ == ["H", "C", "H", "H", "C", "H", "H", "O", "H"]

    def test_build_invalid_guest_type_raises(self):
        """guest_type with a dot fails audit_name -> ValueError."""
        with pytest.raises(ValueError, match="Invalid guest type name"):
            build_custom_guest_module(ETOH_GRO, "bad.name", "MOL")

    def test_build_missing_gro_raises(self):
        """A nonexistent GRO file raises ValueError with context."""
        with pytest.raises(ValueError, match="Failed to parse GRO file"):
            build_custom_guest_module("nonexistent.gro", "etoh_test", "MOL")

    def test_build_module_name_is_namespaced(self):
        """The module is named genice2.molecules.<guest_type>."""
        import types

        mod = build_custom_guest_module(ETOH_GRO, "etoh_namespaced", "MOL")
        assert isinstance(mod, types.ModuleType)
        assert mod.__name__ == "genice2.molecules.etoh_namespaced"
        assert hasattr(mod, "Molecule")


# ── Validation tests ───────────────────────────────────────────────────────


class TestValidateCustomGuestFiles:
    """Tests for validate_custom_guest_files (GRO+ITP validation)."""

    def test_validate_valid_etoh(self):
        """Valid etoh pair passes; comb_rule is None (no [ defaults ] in etoh.itp)."""
        r = validate_custom_guest_files(ETOH_GRO, ETOH_ITP, "etoh_custom")
        assert r.is_valid is True
        assert r.gro_atom_count == 9
        assert r.itp_atom_count == 9
        assert r.comb_rule is None
        assert r.residue_name == "MOL"
        assert r.errors == []

    def test_validate_rejects_mismatch(self):
        """etoh_mismatch.gro (header 9, body 6) is rejected via parse or count."""
        r = validate_custom_guest_files(ETOH_MISMATCH_GRO, ETOH_ITP, "etoh_custom")
        assert r.is_valid is False
        assert any(
            "Atom count mismatch" in e or "parse" in e.lower() for e in r.errors
        ), f"expected parse/count error, got {r.errors}"

    def test_validate_rejects_not_gro(self):
        """not_a_gro.txt is rejected with a parse-failure error."""
        r = validate_custom_guest_files(NOT_A_GRO, ETOH_ITP, "etoh_custom")
        assert r.is_valid is False
        assert any("parse" in e.lower() for e in r.errors), (
            f"expected parse error, got {r.errors}"
        )

    def test_validate_rejects_comb_rule_1(self):
        """etoh_combrule1.itp is rejected with the specific comb-rule message."""
        r = validate_custom_guest_files(ETOH_GRO, ETOH_COMBRULE1_ITP, "etoh_custom")
        assert r.is_valid is False
        assert r.comb_rule == 1
        assert any("comb-rule must be 2" in e for e in r.errors), (
            f"expected comb-rule error, got {r.errors}"
        )

    def test_validate_rejects_name_too_long(self, tmp_path):
        """A GRO with residue name 'ETHAN' (5 chars) is rejected (<=3 chars rule)."""
        gro = _write_gro(tmp_path / "ethan.gro", "ETHAN")
        r = validate_custom_guest_files(gro, ETOH_ITP, "etoh_custom")
        assert r.is_valid is False
        assert any("exceeds 3 chars" in e for e in r.errors), (
            f"expected name-too-long error, got {r.errors}"
        )

    def test_validate_warns_no_atomtypes(self):
        """ITP without [ atomtypes ] is valid but warns (warn not block)."""
        r = validate_custom_guest_files(ETOH_GRO, ETOH_NO_ATOMTYPES_ITP, "etoh_custom")
        assert r.is_valid is True
        assert len(r.warnings) > 0
        assert any("atomtypes" in w.lower() for w in r.warnings), (
            f"expected atomtypes warning, got {r.warnings}"
        )

    def test_validate_rejects_bad_guest_type(self):
        """Invalid guest_type (audit_name failure) is rejected."""
        r = validate_custom_guest_files(ETOH_GRO, ETOH_ITP, "bad.name")
        assert r.is_valid is False
        assert any("Invalid guest type name" in e for e in r.errors), (
            f"expected invalid-name error, got {r.errors}"
        )


# ── Injection / cleanup tests ──────────────────────────────────────────────


class TestSysModulesInjection:
    """Tests for custom_guest_module context manager + register/unregister pair.

    Each test uses a unique guest_type to avoid cross-test pollution.
    """

    def test_context_manager_registers_and_cleans_up(self):
        """Context manager registers the module and removes it on normal exit."""
        from genice2.plugin import safe_import

        mod = build_custom_guest_module(ETOH_GRO, "etoh_cm", "MOL")
        key = "genice2.molecules.etoh_cm"
        with custom_guest_module("etoh_cm", mod) as k:
            assert k == key
            assert sys.modules[key] is mod
            loaded = safe_import("molecule", "etoh_cm")
            assert loaded is mod
        # After the block, the key must be gone (cleanup ran).
        assert key not in sys.modules

    def test_context_manager_cleans_up_on_exception(self):
        """Context manager cleans up sys.modules even when an exception propagates."""
        mod = build_custom_guest_module(ETOH_GRO, "etoh_exc", "MOL")
        key = "genice2.molecules.etoh_exc"
        with pytest.raises(RuntimeError, match="boom"):
            with custom_guest_module("etoh_exc", mod):
                raise RuntimeError("boom")
        assert key not in sys.modules, "sys.modules leaked on exception path"

    def test_register_unregister_pair(self):
        """register_custom_guest/unregister_custom_guest work for GUI async."""
        from genice2.plugin import safe_import

        mod = build_custom_guest_module(ETOH_GRO, "etoh_pair", "MOL")
        key = "genice2.molecules.etoh_pair"
        register_custom_guest("etoh_pair", mod)
        assert key in sys.modules
        assert sys.modules[key] is mod
        assert safe_import("molecule", "etoh_pair") is mod
        unregister_custom_guest("etoh_pair")
        assert key not in sys.modules

    def test_unregister_when_absent_is_safe(self):
        """unregister_custom_guest on a missing key does not raise."""
        # Should be a no-op (pop with default).
        unregister_custom_guest("nonexistent")
        assert "genice2.molecules.nonexistent" not in sys.modules

    def test_re_register_after_cleanup(self):
        """register -> unregister -> register with the same key all succeed."""
        mod = build_custom_guest_module(ETOH_GRO, "etoh_rereg", "MOL")
        key = "genice2.molecules.etoh_rereg"
        register_custom_guest("etoh_rereg", mod)
        assert key in sys.modules
        unregister_custom_guest("etoh_rereg")
        assert key not in sys.modules
        # Re-register with the same key after cleanup must succeed.
        register_custom_guest("etoh_rereg", mod)
        assert key in sys.modules
        unregister_custom_guest("etoh_rereg")
        assert key not in sys.modules


# ── count_guest_atoms explicit atom count tests (Phase 44.1-03) ────────────


class TestCountGuestAtomsCustomExplicit:
    """Tests that count_guest_atoms honors guest_atom_count for custom guests.

    Phase 44.1-03 root-cause fix: the ch4/thf heuristic in count_guest_atoms
    miscounts custom guest atoms (e.g. ethanol=9 miscounted as 5), which
    causes an IndexError when interface modes (slab/pocket/piece) tile guests
    using the wrong atom count and the accumulated indices overshoot the
    atom_names array. The new ``guest_atom_count`` param short-circuits the
    heuristic for custom guests.
    """

    # Ethanol atom layout per molecule (9 atoms, mirrors ETOH_ATOMS labels).
    ETOH_ATOM_NAMES = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]

    def test_count_guest_atoms_custom_explicit(self):
        """Explicit guest_atom_count=9 yields exactly 8 ethanol molecules.

        Stepping through 8 ethanol molecules (72 atom names) with the explicit
        count returns 9 per step — no IndexError, no overshoot. The heuristic
        path (no guest_atom_count) is shown to miscount the same atoms,
        documenting WHY the explicit count is required. Built-in ch4 (no
        guest_atom_count) still returns 5 — regression guard.
        """
        from quickice.utils.molecule_utils import count_guest_atoms

        # 8 ethanol molecules x 9 atoms = 72 atom names
        atoms = self.ETOH_ATOM_NAMES * 8
        assert len(atoms) == 72

        # Stepping with the explicit count must yield exactly 8 molecules,
        # each step returning 9. No IndexError, no overshoot.
        total = 0
        idx = 0
        while idx < len(atoms):
            step = count_guest_atoms(
                atoms, idx, guest_type="etoh_e2e", guest_atom_count=9
            )
            assert step == 9, f"expected 9 atoms per molecule, got {step} at idx {idx}"
            if step == 0:
                break
            total += 1
            idx += step
        assert total == 8, f"expected 8 molecules, got {total}"
        assert idx == 72, f"expected final idx 72, got {idx}"

        # HEURISTIC MISCOUNT PROOF: the same atoms WITHOUT guest_atom_count
        # do NOT yield 9 per molecule — documenting why the explicit count is
        # required. The ch4/thf heuristic returns 1/2/13 for ethanol atoms
        # (fragile pattern matching), so either the per-step count != 9 OR
        # the resulting molecule count != 8.
        first_step_heuristic = count_guest_atoms(
            atoms, 0, guest_type="etoh_e2e"
        )
        # Also check the None heuristic path for completeness.
        first_step_none = count_guest_atoms(atoms, 0, guest_type=None)
        # At least one heuristic path must disagree with 9 — proves the
        # heuristic is wrong for custom guests (the bug we're fixing).
        assert first_step_heuristic != 9 or first_step_none != 9, (
            "Heuristic unexpectedly agrees with 9 for both custom-guest_type "
            "and None paths — explicit count would be redundant"
        )

        # REGRESSION GUARD: built-in ch4 (no guest_atom_count) still 5.
        assert count_guest_atoms(["C", "H", "H", "H", "H"], 0, guest_type="ch4") == 5
        # And built-in thf still 13.
        assert count_guest_atoms(["O", "CA", "CA", "CB", "CB"], 0, guest_type="thf") == 13

    def test_count_guest_atoms_ignores_explicit_count_for_builtins(self):
        """guest_atom_count is IGNORED when guest_type is ch4/thf/None.

        This guards the gate condition ``guest_type not in ("ch4", "thf", None)``
        so a stray guest_atom_count cannot corrupt built-in counts or the
        heuristic fallback.
        """
        from quickice.utils.molecule_utils import count_guest_atoms

        # ch4 with a wrong explicit count still returns 5 (builtin wins).
        assert (
            count_guest_atoms(
                ["C", "H", "H", "H", "H"], 0, guest_type="ch4", guest_atom_count=99
            )
            == 5
        )
        # thf with a wrong explicit count still returns 13.
        assert (
            count_guest_atoms(
                ["O", "CA", "CA", "CB", "CB"], 0, guest_type="thf", guest_atom_count=99
            )
            == 13
        )
        # None guest_type with an explicit count falls through to heuristic
        # (guest_atom_count is only honored for non-builtin guest types).
        # CH4-pattern atoms with guest_type=None + guest_atom_count=99 still
        # return the heuristic result (5), NOT 99.
        assert (
            count_guest_atoms(
                ["C", "H", "H", "H", "H"], 0, guest_type=None, guest_atom_count=99
            )
            == 5
        )


# ── _build_custom_guest_info neutral-module test (Phase 44.1-04) ────────────


def test_build_custom_guest_info_from_guest_info_module():
    """_build_custom_guest_info is importable from the neutral
    quickice.output.guest_info module (no Qt/CLI cross-import) and behaves
    identically for None / built-in / custom configs.

    Phase 44.1-04 moved the builder from quickice/cli/pipeline.py to
    quickice/output/guest_info.py so GUI exporters (plan 08+) and CLI export
    branches (plan 17) share it without GUI->CLI (argparse) or CLI->Qt (headless
    break) cross-imports. pipeline.py re-exports it for backward compatibility
    (existing call sites unchanged).
    """
    from quickice.output.guest_info import _build_custom_guest_info
    from quickice.structure_generation.types import HydrateConfig

    # None config -> None
    assert _build_custom_guest_info(None) is None

    # Built-in ch4 config -> None (no custom guests; the MoleculetypeRegistry
    # handles built-in ch4/thf — _build_custom_guest_info excludes them).
    cfg_builtin = HydrateConfig(lattice_type="sI", guest_type="ch4")
    assert _build_custom_guest_info(cfg_builtin) is None

    # Custom etoh_e2e config: the legacy single-custom-guest path goes through
    # the 42-01 __post_init__ shim which populates cage_guest_assignments for
    # BOTH small and large cages (same etoh_e2e guest). _build_custom_guest_info
    # dedups by mol_type so the returned list has ONE entry (not two) — matching
    # the 42-02 ExitStack dedup and the 42-03 writers' custom_by_moltype dict.
    cfg_custom = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path=str(ETOH_GRO),
        guest_itp_path=str(ETOH_ITP),
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
    )
    info = _build_custom_guest_info(cfg_custom)
    assert info is not None, "custom config should yield a non-None list"
    assert len(info) == 1, f"expected 1 entry (deduped), got {len(info)}: {info}"
    entry = info[0]
    assert entry["mol_type"] == "etoh_e2e", entry
    assert entry["residue_name"] == "MOL_H", entry
    assert entry["itp_path"] == ETOH_ITP, entry


# ── _stage_hydrate_guest_itps shared helper tests (Phase 44.1-08) ─────────────


def test_stage_hydrate_guest_itps_helper(tmp_path):
    """_stage_hydrate_guest_itps stages hydrate-guest ITPs for the 4 GUI
    exporters (interface / solute / custom-molecule / ion) in a config-driven
    way, returning (custom_guest_info, itp_files).

    Phase 44.1-08 DRYs the broken ``_detect_guest_type_from_structure`` (returns
    None for custom) + ``shutil.copy({guest_type}_hydrate.itp)`` (FileNotFoundError
    for custom) pattern duplicated 4x in quickice/gui/export.py. Mirrors
    hydrate_export.py:253-359 (42-08) but config-driven (44.1-RESEARCH §5 Option A
    — safe for the interface path: you can't change the interface without
    regenerating from the hydrate, so no 42-08-style desync).

    Three cases:
    - No-guest: hydrate_config=None + zero counts -> (None, {}); nothing staged.
    - Custom: etoh_e2e config -> custom_guest_info is a 1-entry list with
      mol_type='etoh_e2e'/residue_name='MOL_H', and a transformed etoh.itp
      (moleculetype 'MOL_H', [atomtypes] commented, [atoms] resname 'MOL_H') is
      written to output_dir.
    - Built-in: ch4 config -> custom_guest_info is None (no custom) and the
      bundled ch4_hydrate.itp is copied to output_dir (pre-transformed; no
      transform needed, matching the existing export.py built-in path).
    """
    from quickice.output.guest_info import _stage_hydrate_guest_itps
    from quickice.structure_generation.types import HydrateConfig

    # ── No-guest case: hydrate_config=None, zero counts -> (None, {}) ──
    # This is the ion-only / ice-only export path: no hydrate guests to stage.
    # The helper short-circuits at the presence gate without touching the
    # filesystem (no ITP reads/writes/copies).
    cgi_none, itps_none = _stage_hydrate_guest_itps(
        tmp_path, None, None, guest_atom_count=0, guest_nmolecules=0
    )
    assert cgi_none is None, f"no-guest -> expected None custom_guest_info, got {cgi_none}"
    assert itps_none == {}, f"no-guest -> expected empty itp_files, got {itps_none}"
    # Nothing was staged to the output dir.
    assert list(tmp_path.iterdir()) == [], "no-guest path must not stage any files"

    # ── Custom case: etoh_e2e config -> transform + write custom ITP ──
    # 72 atoms / 8 molecules = 9 atoms/mol (ethanol). The presence gate passes
    # (both > 0), _build_custom_guest_info returns a 1-entry list (deduped:
    # sI small+large both etoh_e2e -> 1 entry), and the helper transforms the
    # source etoh.itp (moleculetype 'MOL' -> 'MOL_H', [atomtypes] commented,
    # [atoms] resname 'MOL' -> 'MOL_H') and writes it to output_dir.
    cfg_custom = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path=str(ETOH_GRO),
        guest_itp_path=str(ETOH_ITP),
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
    )
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    cgi_custom, itps_custom = _stage_hydrate_guest_itps(
        custom_dir, cfg_custom, None, guest_atom_count=72, guest_nmolecules=8
    )
    # custom_guest_info is a 1-entry list (deduped) for the gro/top writers.
    assert cgi_custom is not None, "custom path -> custom_guest_info must not be None"
    assert isinstance(cgi_custom, list), cgi_custom
    assert len(cgi_custom) == 1, f"expected 1 entry (deduped), got {len(cgi_custom)}: {cgi_custom}"
    centry = cgi_custom[0]
    assert centry["mol_type"] == "etoh_e2e", centry
    assert centry["residue_name"] == "MOL_H", centry
    assert centry["itp_path"] == ETOH_ITP, centry
    # The transformed ITP was written to output_dir under the source filename.
    staged_itp = custom_dir / "etoh.itp"
    assert staged_itp.exists(), f"expected staged {staged_itp}, dir contents: {list(custom_dir.iterdir())}"
    assert "etoh.itp" in itps_custom, itps_custom
    assert itps_custom["etoh.itp"] == str(staged_itp), itps_custom
    # Verify the transform was applied (mirrors hydrate_export.py:353-359):
    # - [atomtypes] commented out (Step 1)
    # - moleculetype name -> 'MOL_H' (Step 2)
    # - [atoms] resname column -> 'MOL_H' (Step 3, deferred from 38-04)
    transformed = staged_itp.read_text()
    assert "; [ atomtypes ]" in transformed, "Step 1: [atomtypes] must be commented out"
    assert "MOL_H" in transformed, "transformed ITP must carry the MOL_H moleculetype/resname"
    # moleculetype line: 'MOL_H       3' (name + nrexcl)
    moltype_lines = [
        ln for ln in transformed.splitlines()
        if ln.strip() and not ln.strip().startswith(";")
        and ln.split()[0] == "MOL_H"
    ]
    assert moltype_lines, "expected a 'MOL_H ...' moleculetype name line"
    # Every [atoms] data row carries resname 'MOL_H' (field index 3).
    in_atoms = False
    atom_rows_checked = 0
    for ln in transformed.splitlines():
        s = ln.strip()
        if s.startswith("[") and "atoms" in s.lower():
            in_atoms = True
            continue
        if in_atoms and s.startswith("["):
            break
        if in_atoms and s and not s.startswith(";"):
            fields = s.split()
            if len(fields) >= 4:
                assert fields[3] == "MOL_H", f"[atoms] resname must be MOL_H, got {fields[3]!r}: {ln!r}"
                atom_rows_checked += 1
    # Sanity: we actually inspected [atoms] rows (etoh.itp has 9 atoms).
    assert atom_rows_checked == 9, f"expected 9 [atoms] rows with MOL_H resname, got {atom_rows_checked}"

    # ── Built-in case: ch4 config -> copy bundled ch4_hydrate.itp ──
    # _build_custom_guest_info returns None for ch4 (built-in excluded), so the
    # helper takes the built-in path: detect guest_type (config fallback here
    # since structure=None) and shutil.copy the pre-transformed ch4_hydrate.itp.
    # custom_guest_info is None (no custom guests for the writers).
    cfg_builtin = HydrateConfig(lattice_type="sI", guest_type="ch4")
    builtin_dir = tmp_path / "builtin"
    builtin_dir.mkdir()
    cgi_builtin, itps_builtin = _stage_hydrate_guest_itps(
        builtin_dir, cfg_builtin, None, guest_atom_count=40, guest_nmolecules=8
    )
    # Built-in path -> custom_guest_info is None (the MoleculetypeRegistry handles
    # built-in ch4/thf in the gro/top writers; no custom_guest_info kwarg needed).
    assert cgi_builtin is None, f"built-in ch4 -> expected None custom_guest_info, got {cgi_builtin}"
    # The bundled ch4_hydrate.itp was copied to output_dir.
    assert "ch4_hydrate.itp" in itps_builtin, itps_builtin
    staged_builtin = builtin_dir / "ch4_hydrate.itp"
    assert staged_builtin.exists(), f"expected staged {staged_builtin}, dir contents: {list(builtin_dir.iterdir())}"
    assert itps_builtin["ch4_hydrate.itp"] == str(staged_builtin), itps_builtin
    # The bundled _hydrate.itp is pre-transformed (moleculetype 'CH4_H'); the
    # built-in path copies it unchanged (matches existing export.py:185-187).
    builtin_content = staged_builtin.read_text()
    assert "CH4_H" in builtin_content, "bundled ch4_hydrate.itp must carry the CH4_H moleculetype"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
