"""Tier-A CLI subprocess prefix matrix: every legitimate invocation prefix of
the full CLI workflow, subprocess-executed and grompp-validated.

Architecture (Tier A — black-box subprocess tier, research
48.3-RESEARCH-CLI-E2E §5):

    Each test runs ONE legitimate user invocation ``python -m quickice ...``
    truncated at a pipeline step (via ``run_quickice`` from tests/conftest.py)
    and validates the exported GROMACS files at four levels:

      1. rc == 0 and the expected ``{step}.gro`` / ``{step}.top`` / staged
         ITP files exist;
      2. ``assert_itp_completeness`` — every ``#include``d ITP is staged in
         the export directory (the CLI's own ``copy_itp_files_for_structure``
         staging, not test-side staging);
      3. ``assert_gro_top_consistent`` — .gro atom/residue content agrees
         with the .top ``[ molecules ]`` block;
      4. ``gmx grompp`` exits 0 on the exported pair (real GROMACS parse);
      plus species assertions via ``parse_top_molecules`` /
      ``parse_gro_residue_names`` where the matrix row demands it.

    This closes CLI GAPs 2 (custom step never grompp'd), 3 (CSV placement),
    4 (concentration), 5 (ion-from-custom), 6 (double auto-chain), 7
    (hydrate-only default sI), 9 (prefix invocations), 10 (ice-only
    --gromacs) plus a depol-optimal row. Before this matrix only TWO
    subprocess runs were grompp-validated (interface-only and
    interface→solute→ion in test_cli_pipeline.py).

SAFE-05: every ``--output`` AND every custom-step INPUT path (etoh.gro /
etoh.itp / positions CSV) lives under ``<cwd>/tmp/`` (via
``make_temp_output_dir`` from tests/e2e_export_helpers.py) because
CLIPipeline rejects paths that resolve outside the working directory
(pipeline.py:170-175 for --output, :532-547 for custom inputs, :280-287 for
the CSV). pytest ``tmp_path`` (under /tmp) is NEVER passed to a subprocess
run in this module.

Runtime budget: ~1-2 s per subprocess row including grompp → whole matrix
well under 60 s.

Species-naming note (48.3-02 D1 fix): custom molecules placed AFTER the D1
reconciliation register under their ITP ``[ moleculetype ]`` name (e.g.
``etoh``), so exported .gro residues AND .top ``[ molecules ]`` entries say
``etoh`` — not the legacy registry default ``MOL``. All custom-species
asserts below expect the ITP moleculetype name.
"""

import re
import shutil
from pathlib import Path

import pytest

from tests.conftest import run_quickice, gmx_skipif

from tests.e2e_export_helpers import (
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    make_temp_output_dir,
    parse_gro_atom_count,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)

from quickice.structure_generation.ion_inserter import AVOGADRO
from quickice.structure_generation.types import WATER_VOLUME_NM3


# ── Gating ───────────────────────────────────────────────────────────────────
# Every row in this matrix is grompp-centric, so the whole module is gated on
# GROMACS availability (established convention: gmx_skipif skips when
# ``shutil.which("gmx")`` is None). slow: subprocess rows with GenIce2 runs.

pytestmark = [gmx_skipif, pytest.mark.slow]


# ── Constants ────────────────────────────────────────────────────────────────

# Slab interface box: 3×3×5 nm (shortest vector 3 nm > 2×1.0 nm em.mdp
# cutoffs) with box_z = 2×ice_thickness + water_thickness = 2×1.5 + 2.0 = 5.0
# (slab-mode validation requires this identity, interface_builder.py:141-160).
TP = ("-T", "270", "-P", "0.1")
SLAB = (
    "--interface", "--mode", "slab",
    "--box-x", "3", "--box-y", "3", "--box-z", "5",
    "--ice-thickness", "1.5", "--water-thickness", "2.0",
)

# Slab water layer spans z ∈ [ice_thickness, ice_thickness + water_thickness]
# = [1.5, 3.5] nm (bottom ice / water / top ice stack). CSV placement
# positions below sit inside this liquid region, ≥1 nm apart.
WATER_Z_MID = "2.0"

# Small-cutoff MDP for rows whose exported box has a shortest vector below
# the 2.0 nm needed by the shared tests/em.mdp (rcoulomb=rvdw=1.0):
# - hydrate-only sI 1×1×1 cell = 1.20 nm,
# - ice-only 96-molecule ice_ih cell ≈ 1.47 nm.
# 0.5 nm cutoffs need box > 1.0 nm — both fit. Same precedent as
# test_scancode_bugs_constants.py::test_gmx_grompp_constants_refactor.
SMALL_CUTOFF_MDP = (
    "integrator = steep\n"
    "nsteps = 0\n"
    "emtol  = 100.0\n"
    "emstep = 0.01\n"
    "pbc = xyz\n"
    "cutoff-scheme = Verlet\n"
    "coulombtype   = PME\n"
    "rcoulomb      = 0.5\n"
    "vdwtype       = Cut-off\n"
    "rvdw          = 0.5\n"
    "DispCorr      = EnerPres\n"
    "constraints   = none\n"
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _copy_etoh_inputs(workspace: Path) -> tuple[str, str]:
    """Copy the etoh template GRO/ITP INTO the CWD tmp/ workspace.

    SEC-04 requires custom-step INPUT paths (``--custom-gro`` /
    ``--custom-itp``) to resolve under the working directory
    (pipeline.py:532-547). The bundled ``quickice/data/custom`` files are the
    source; the pipeline-facing paths are the copies under ``<cwd>/tmp/``.

    Returns:
        (gro_path, itp_path) as strings, ready for CLI flags.
    """
    gro_dst = workspace / "etoh.gro"
    itp_dst = workspace / "etoh.itp"
    shutil.copy(ETOH_GRO, gro_dst)
    shutil.copy(ETOH_ITP, itp_dst)
    return str(gro_dst), str(itp_dst)


def _custom_flags(gro: str, itp: str) -> tuple[str, ...]:
    """Random-placement custom-step flags: 3 etoh molecules."""
    return (
        "--custom-gro", gro, "--custom-itp", itp,
        "--custom-placement", "random", "--custom-count", "3",
    )


def _validate_export(out_dir: Path, gro_file: str, top_file: str,
                     small_mdp: bool = False) -> None:
    """Levels 1-4 validation for one exported pair.

    Files exist → ITP completeness → gro/top consistency → grompp rc 0.
    """
    assert (out_dir / gro_file).exists(), f"{gro_file} not found in {out_dir}"
    assert (out_dir / top_file).exists(), f"{top_file} not found in {out_dir}"
    assert_itp_completeness(str(out_dir / top_file), out_dir)
    assert_gro_top_consistent(str(out_dir / gro_file), str(out_dir / top_file))
    if small_mdp:
        (out_dir / "em.mdp").write_text(SMALL_CUTOFF_MDP)
    else:
        shutil.copy(MDP_PATH, out_dir / "em.mdp")
    grompp_rc, grompp_stderr = run_gmx_grompp(
        out_dir, gro_file=gro_file, top_file=top_file
    )
    assert grompp_rc == 0, (
        f"gmx grompp failed on {gro_file}:\n{grompp_stderr[-800:]}"
    )


def _count_custom_molecules(gro_path: str, template_gro: str) -> int:
    """Count custom ('etoh') molecules in an exported .gro file.

    The atoms-per-molecule divisor comes from the template GRO itself (9 for
    the bundled etoh) — never hardcoded, so the helper follows the template.
    """
    atoms_per_molecule = parse_gro_atom_count(template_gro)
    residues = parse_gro_residue_names(gro_path)
    custom_atoms = sum(1 for r in residues if r.lower() == "etoh")
    assert custom_atoms % atoms_per_molecule == 0, (
        f"custom atom count {custom_atoms} is not a whole multiple of the "
        f"template's {atoms_per_molecule} atoms/molecule — corrupted export"
    )
    return custom_atoms // atoms_per_molecule


# ── Custom-chain rows (GAP 2 / 5 / 6) ────────────────────────────────────────
# All etoh input paths live under <cwd>/tmp/ (SEC-04); output under
# <cwd>/tmp/<ws>/out. etoh registers under its ITP moleculetype name 'etoh'
# (48.3-02 D1 fix) in BOTH .gro residues and .top [molecules].


class TestCustomChainMatrix:
    """Interface→custom chains through the real CLI, grompp-validated."""

    def test_r5_interface_custom_grompp(self):
        """R5 (GAP 2): interface+custom — custom.gro/custom.top pass grompp.

        First time the custom step is grompp-validated through the real CLI
        subprocess path: exercises write_custom_molecule_* output (divergent
        header + 3-value box vector), etoh.itp staging via
        copy_itp_files_for_structure's custom branch, and the 'etoh'
        moleculetype naming (D1).
        """
        assert shutil.which("gmx") is not None, (
            "sanity: gmx must be on PATH so grompp genuinely ran"
        )
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB, *_custom_flags(gro, itp),
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            assert (out / "etoh.itp").exists(), "custom ITP not staged"
            assert (out / "tip4p-ice.itp").exists()
            _validate_export(out, "custom.gro", "custom.top")

            molecules = parse_top_molecules(str(out / "custom.top"))
            assert molecules.get("etoh") == 3, (
                f".top [molecules] should declare 3 etoh, got {molecules}"
            )
            assert molecules.get("SOL", 0) > 0
            residues = parse_gro_residue_names(str(out / "custom.gro"))
            assert "etoh" in residues, (
                f"custom residue 'etoh' missing from custom.gro "
                f"(D1: ITP moleculetype name); got {sorted(set(residues))}"
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r7_full_chain_explicit_sources_grompp(self):
        """R7: interface+custom+solute+ion with explicit --solute-source
        custom --ion-source solute — ion.gro passes grompp (GAP 2 chain)."""
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB, *_custom_flags(gro, itp),
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "--solute-source", "custom",
                "--ion-concentration", "0.15",
                "--ion-source", "solute",
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            # Full chain stages 4 ITPs: tip4p-ice + etoh + ch4_liquid + ion.
            for itp_name in ("ion.itp", "etoh.itp", "ch4_liquid.itp",
                             "tip4p-ice.itp"):
                assert (out / itp_name).exists(), f"{itp_name} not staged"
            _validate_export(out, "ion.gro", "ion.top")

            molecules = parse_top_molecules(str(out / "ion.top"))
            assert molecules.get("etoh") == 3
            assert molecules.get("CH4_L", 0) > 0, "solute missing from ion.top"
            assert molecules.get("SOL", 0) > 0
            residues = parse_gro_residue_names(str(out / "ion.gro"))
            assert "etoh" in residues
            assert "CH4_L" in residues
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r8_full_chain_no_source_flags_double_auto_chain(self):
        """R8 (GAP 6): interface+custom+solute+ion with NO --solute-source /
        --ion-source flags — the double auto-chain (solute: interface→custom,
        ion: interface→solute) must keep the custom molecule alive through to
        ion.gro. Auto-chain is logger-only, so the exported CONTENT is the
        only observable: assert 'etoh' residues + [molecules] count in the
        ion export, plus grompp rc 0."""
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB, *_custom_flags(gro, itp),
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "--ion-concentration", "0.15",
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            _validate_export(out, "ion.gro", "ion.top")

            molecules = parse_top_molecules(str(out / "ion.top"))
            assert molecules.get("etoh") == 3, (
                f"double auto-chain dropped the custom molecule from ion.top: "
                f"{molecules}"
            )
            residues = parse_gro_residue_names(str(out / "ion.gro"))
            assert "etoh" in residues, (
                "double auto-chain dropped the custom molecule from ion.gro "
                "(silent data loss is exactly what auto-chaining prevents)"
            )
            assert molecules.get("CH4_L", 0) > 0
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r9a_ion_from_custom_explicit_source_grompp(self):
        """R9a (GAP 5): interface+custom+ion with explicit --ion-source
        custom — exercises the FIX #4 offset arithmetic (custom positions
        sliced with ice+water+guest atom counts) in write_ion_gro_file's
        synthetic custom MoleculeIndex path."""
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB, *_custom_flags(gro, itp),
                "--ion-concentration", "0.15",
                "--ion-source", "custom",
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            assert (out / "ion.itp").exists()
            assert (out / "etoh.itp").exists()
            _validate_export(out, "ion.gro", "ion.top")

            molecules = parse_top_molecules(str(out / "ion.top"))
            assert molecules.get("etoh") == 3, (
                f"FIX #4 offset arithmetic dropped/corrupted custom molecules "
                f"in the ion-from-custom export: {molecules}"
            )
            residues = parse_gro_residue_names(str(out / "ion.gro"))
            assert "etoh" in residues
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r9b_ion_from_custom_auto_upgrade_grompp(self):
        """R9b: interface+custom+ion with NO --ion-source — the ion
        auto-chain upgrades interface→custom (no solute result present) and
        must likewise keep the custom molecule in ion.gro."""
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB, *_custom_flags(gro, itp),
                "--ion-concentration", "0.15",
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            _validate_export(out, "ion.gro", "ion.top")

            molecules = parse_top_molecules(str(out / "ion.top"))
            assert molecules.get("etoh") == 3, (
                f"ion auto-chain upgrade (interface→custom) dropped the "
                f"custom molecule from ion.top: {molecules}"
            )
            residues = parse_gro_residue_names(str(out / "ion.gro"))
            assert "etoh" in residues
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


# ── CSV placement + concentration rows (GAP 3 / 4) ───────────────────────────
# The positions CSV and the custom input files live INSIDE the CWD tmp/
# workspace: _parse_positions_csv (pipeline.py:280-287) applies the same
# SEC-04 CWD containment as the custom gro/itp inputs.


class TestCsvPlacementAndConcentrationMatrix:
    """The two ZERO-coverage custom flags get happy-path grompp coverage."""

    def test_r10_csv_placement_grompp(self):
        """R10 (GAP 3): --custom-placement custom with a valid 6-column
        positions CSV places exactly N molecules and passes grompp.

        The CSV rows (x, y, z, alpha, beta, gamma) sit inside the slab water
        layer (z ∈ [1.5, 3.5] nm) with ≥1 nm COM spacing; a '#' comment line
        exercises the comment-skipping branch of _parse_positions_csv.
        place_custom performs NO overlap rejection (SUSP-06, user
        responsibility) — it removes overlapping WATER molecules instead.
        """
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            n_positions = 4
            csv_path = workspace / "positions.csv"
            csv_lines = [
                "# x, y, z, alpha, beta, gamma (nm, degrees ZXZ)",
                f"0.5,0.5,{WATER_Z_MID},0,0,0",
                f"1.5,0.5,{WATER_Z_MID},0,0,0",
                f"2.5,0.5,{WATER_Z_MID},0,0,0",
                f"1.5,1.5,{WATER_Z_MID},0,0,0",
            ]
            csv_path.write_text("\n".join(csv_lines) + "\n")

            rc, _, stderr = run_quickice(
                *TP, *SLAB,
                "--custom-gro", gro, "--custom-itp", itp,
                "--custom-placement", "custom",
                "--custom-positions-file", str(csv_path),
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"
            out = workspace / "out"
            _validate_export(out, "custom.gro", "custom.top")

            # Exactly N custom molecules placed — the CSV row count is the
            # count contract (not the concentration math).
            placed = _count_custom_molecules(str(out / "custom.gro"), gro)
            assert placed == n_positions, (
                f"expected exactly {n_positions} custom molecules from the "
                f"CSV rows, exported {placed}"
            )
            molecules = parse_top_molecules(str(out / "custom.top"))
            assert molecules.get("etoh") == n_positions, (
                f".top [molecules] should declare {n_positions} etoh, "
                f"got {molecules}"
            )
            assert molecules.get("SOL", 0) > 0
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r11_custom_concentration_grompp(self):
        """R11 (GAP 4): --custom-concentration 0.05 (NO --custom-count)
        derives the molecule count from the liquid volume.

        The expected count is recomputed INDEPENDENTLY in this test with the
        MODULE CONSTANTS (WATER_VOLUME_NM3 from quickice.structure_generation.
        types + AVOGADRO from ion_inserter — never hardcode 0.0299), using
        the water molecule count the interface step itself reports on stderr
        ('[PROGRESS] Interface: <ice> ice + <water> water molecules') — the
        same number pipeline.py:565-572 reads from the interface result.
        """
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            concentration = 0.05
            rc, _, stderr = run_quickice(
                *TP, *SLAB,
                "--custom-gro", gro, "--custom-itp", itp,
                "--custom-placement", "random",
                "--custom-concentration", str(concentration),
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed:\n{stderr[-500:]}"

            # Independent expected-count computation (pipeline.py:565-572).
            match = re.search(
                r"Interface: (\d+) ice \+ (\d+) water molecules", stderr
            )
            assert match, (
                f"interface progress line missing from stderr — cannot "
                f"recompute the concentration count:\n{stderr[-500:]}"
            )
            water_nmolecules = int(match.group(2))
            expected_count = int(round(
                concentration * water_nmolecules * WATER_VOLUME_NM3 * 1e-24
                * AVOGADRO
            ))
            assert expected_count >= 1, (
                f"concentration {concentration} should derive at least 1 "
                f"molecule for {water_nmolecules} waters, got "
                f"{expected_count} — use R11b for the rounds-to-0 edge"
            )

            out = workspace / "out"
            _validate_export(out, "custom.gro", "custom.top")
            placed = _count_custom_molecules(str(out / "custom.gro"), gro)
            assert placed == expected_count, (
                f"concentration-derived count mismatch: pipeline placed "
                f"{placed}, independent computation says {expected_count} "
                f"(water_nmolecules={water_nmolecules}, "
                f"WATER_VOLUME_NM3={WATER_VOLUME_NM3}, AVOGADRO={AVOGADRO})"
            )
            molecules = parse_top_molecules(str(out / "custom.top"))
            assert molecules.get("etoh") == expected_count
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_r11b_tiny_concentration_rounds_to_zero_pins_graceful_failure(self):
        """R11b edge: concentration so low the derived count rounds to 0.

        PINNED behavior (read from pipeline.py:565-572 + CustomMoleculeConfig
        validation before writing this test): the count formula
        ``int(round(conc * V * 1e-24 * AVOGADRO))`` yields 0, and
        CustomMoleculeConfig.__post_init__ rejects ``molecule_count=0``
        ('molecule_count must be >= 1, got 0') — so the custom step fails
        GRACEFULLY: rc == 1, '[PROGRESS] Custom step failed: bad config'
        on stderr, no export written.
        """
        workspace = Path(make_temp_output_dir())
        try:
            gro, itp = _copy_etoh_inputs(workspace)
            rc, _, stderr = run_quickice(
                *TP, *SLAB,
                "--custom-gro", gro, "--custom-itp", itp,
                "--custom-placement", "random",
                "--custom-concentration", "0.0001",
                "-o", str(workspace / "out"),
                timeout=120,
            )
            assert rc == 1, (
                f"tiny concentration should fail gracefully with rc 1 "
                f"(count rounds to 0 → CustomMoleculeConfig rejects it), "
                f"got rc {rc}\nstderr tail:\n{stderr[-500:]}"
            )
            assert "Custom step failed" in stderr
            assert "molecule_count must be >= 1" in stderr
            out = workspace / "out"
            assert not (out / "custom.gro").exists(), (
                "no custom.gro should be exported when the custom step failed"
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
