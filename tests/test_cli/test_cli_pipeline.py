"""CLI pipeline integration tests for QuickIce v4.5.

Tests the full CLI pipeline via subprocess, covering:
- Flag validation (cross-flag dependency errors exit code 2)
- Exit codes (0 success, 1 runtime, 2 argument)
- Progress reporting ([PROGRESS] on stderr, clean stdout)
- Basic workflows (slab, pocket, piece, hydrate, solute, ion)
- Advanced workflows (hydrate+interface+solute, custom+solute+ion, etc.)
- Export correctness (GRO atom counts, TOP molecules, ITP files)
- Grompp validation (CLI output passes gmx grompp)

Uses the subprocess pattern from test_cli_integration.py with longer
timeouts for pipeline steps that involve GenIce2 generation.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from tests.conftest import run_quickice, gmx_skipif

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from e2e_export_helpers import run_gmx_grompp, MDP_PATH

# Custom molecule data paths
ETOH_GRO = str(Path(__file__).resolve().parents[2] / "quickice" / "data" / "custom" / "etoh.gro")
ETOH_ITP = str(Path(__file__).resolve().parents[2] / "quickice" / "data" / "custom" / "etoh.itp")


def make_temp_output_dir() -> str:
    """Create a temporary output directory for a pipeline test.

    The directory is created UNDER the current working directory (``<cwd>/tmp/``)
    rather than under the system temp dir (``/tmp``). This is required because
    ``CLIPipeline.execute`` (SAFE-05) rejects ``--output`` paths that resolve
    outside the working directory, mirroring the input-path containment checks
    at pipeline.py:242-249 and :494-509. ``<cwd>/tmp/`` is ignored by
    ``.gitignore`` (the ``tmp/`` entry). Each caller cleans up its own subdir
    via ``shutil.rmtree(outdir, ignore_errors=True)``.

    Returns:
        Path to the temporary directory (under ``<cwd>/tmp/``).
    """
    tmp_base = Path.cwd() / "tmp"
    tmp_base.mkdir(parents=True, exist_ok=True)
    return tempfile.mkdtemp(prefix="test_cli_pipeline_", dir=str(tmp_base))


# ---------------------------------------------------------------------------
# Flag validation tests (fast, no computation)
# ---------------------------------------------------------------------------


class TestPipelineFlagValidation:
    """Cross-flag dependency validation: errors produce exit code 2."""

    def test_solute_type_without_concentration(self):
        """--solute-type CH4 without --solute-concentration → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--solute-type", "CH4",
            timeout=120,
        )
        assert rc == 2
        assert "solute-concentration" in stderr.lower() or "solute-type" in stderr.lower()

    def test_custom_gro_without_custom_itp(self):
        """--custom-gro X.gro without --custom-itp → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--custom-gro", "X.gro",
            timeout=120,
        )
        assert rc == 2
        assert "custom-itp" in stderr.lower()

    def test_custom_itp_without_custom_gro(self):
        """--custom-itp X.itp without --custom-gro → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--custom-itp", "X.itp",
            timeout=120,
        )
        assert rc == 2
        assert "custom-gro" in stderr.lower()

    def test_custom_placement_custom_without_csv(self):
        """--custom-placement custom without --custom-positions-file → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--custom-gro", "X.gro", "--custom-itp", "X.itp",
            "--custom-placement", "custom",
            timeout=120,
        )
        assert rc == 2
        assert "custom-positions-file" in stderr.lower()

    def test_ion_source_solute_without_solute(self):
        """--ion-source solute without --solute-type → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--ion-concentration", "0.15",
            "--ion-source", "solute",
            timeout=120,
        )
        assert rc == 2
        assert "solute-type" in stderr.lower()

    def test_ion_source_custom_without_custom(self):
        """--ion-source custom without --custom-gro → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--ion-concentration", "0.15",
            "--ion-source", "custom",
            timeout=120,
        )
        assert rc == 2
        assert "custom-gro" in stderr.lower()

    def test_solute_source_custom_without_custom(self):
        """--solute-source custom without --custom-gro → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--solute-type", "CH4", "--solute-concentration", "0.5",
            "--solute-source", "custom",
            timeout=120,
        )
        assert rc == 2
        assert "custom-gro" in stderr.lower()

    def test_custom_count_and_concentration_mutually_exclusive(self):
        """Both --custom-count and --custom-concentration → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "--custom-gro", "X.gro", "--custom-itp", "X.itp",
            "--custom-placement", "random",
            "--custom-count", "5",
            "--custom-concentration", "0.5",
            timeout=120,
        )
        assert rc == 2
        assert "mutually exclusive" in stderr.lower()


# ---------------------------------------------------------------------------
# Exit code tests
# ---------------------------------------------------------------------------


class TestPipelineExitCodes:
    """Verify exit codes: 0=success, 2=argument error, 1=runtime error."""

    def test_success_exit_code_0(self):
        """Valid interface slab pipeline → exit code 0."""
        outdir = make_temp_output_dir()
        try:
            rc, stdout, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_invalid_args_exit_code_2(self):
        """Missing required flag → exit code 2."""
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5",
            # Missing --water-thickness for slab mode
            timeout=120,
        )
        assert rc == 2

    def test_runtime_error_exit_code_1(self):
        """Invalid file path for --custom-gro → exit code 1."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--custom-gro", "/nonexistent/path.gro",
                "--custom-itp", "/nonexistent/path.itp",
                "--custom-placement", "random",
                "--custom-count", "3",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 1
        finally:
            shutil.rmtree(outdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Progress reporting tests
# ---------------------------------------------------------------------------


class TestPipelineProgressReporting:
    """Progress messages appear on stderr, not stdout."""

    def test_progress_on_stderr(self):
        """Pipeline output has [PROGRESS] messages on stderr."""
        outdir = make_temp_output_dir()
        try:
            rc, stdout, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            assert "[PROGRESS]" in stderr
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_no_progress_on_stdout(self):
        """stdout remains clean — no [PROGRESS] markers."""
        outdir = make_temp_output_dir()
        try:
            rc, stdout, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            assert "[PROGRESS]" not in stdout
        finally:
            shutil.rmtree(outdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Basic workflow tests (subprocess, 30-60s each)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPipelineBasicWorkflows:
    """Basic pipeline workflows producing correct GROMACS output files."""

    def test_interface_slab(self):
        """Interface slab mode produces interface.gro, interface.top, tip4p-ice.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "interface.gro").exists()
            assert (outpath / "interface.top").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_interface_pocket(self):
        """Pocket mode produces interface.gro, interface.top, tip4p-ice.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "pocket",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--pocket-diameter", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "interface.gro").exists()
            assert (outpath / "interface.top").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_interface_piece(self):
        """Piece mode produces interface.gro, interface.top, tip4p-ice.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "piece",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "interface.gro").exists()
            assert (outpath / "interface.top").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_hydrate_only(self):
        """Hydrate-only produces hydrate.gro, hydrate.top, ch4_hydrate.itp, tip4p-ice.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--hydrate", "--lattice-type", "sI", "--guest", "CH4",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "hydrate.gro").exists()
            assert (outpath / "hydrate.top").exists()
            assert (outpath / "ch4_hydrate.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_interface_solute(self):
        """Interface+solute produces solute.gro, solute.top, ch4_liquid.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "solute.gro").exists()
            assert (outpath / "solute.top").exists()
            assert (outpath / "ch4_liquid.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_interface_ion(self):
        """Interface+ion produces ion.gro, ion.top, ion.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--ion-concentration", "0.15",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "ion.gro").exists()
            assert (outpath / "ion.top").exists()
            assert (outpath / "ion.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Advanced workflow tests (subprocess, 60-120s each)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPipelineAdvancedWorkflows:
    """Advanced multi-step pipeline workflows."""

    def test_interface_custom_solute_ion(self):
        """Full chain: interface→custom→solute→ion with etoh produces ion.gro + 4 ITPs."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--custom-gro", ETOH_GRO, "--custom-itp", ETOH_ITP,
                "--custom-placement", "random", "--custom-count", "3",
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "--solute-source", "custom",
                "--ion-concentration", "0.15",
                "--ion-source", "solute",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "ion.gro").exists()
            assert (outpath / "ion.top").exists()
            assert (outpath / "tip4p-ice.itp").exists()
            assert (outpath / "etoh.itp").exists()
            assert (outpath / "ch4_liquid.itp").exists()
            assert (outpath / "ion.itp").exists()
            # 4 ITP files total
            itp_files = list(outpath.glob("*.itp"))
            assert len(itp_files) == 4
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_hydrate_interface_ion(self):
        """Hydrate+interface+ion with hydrate guest ITP."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--hydrate", "--lattice-type", "sI", "--guest", "CH4",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--ion-concentration", "0.15",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "ion.gro").exists()
            assert (outpath / "ion.top").exists()
            assert (outpath / "ch4_hydrate.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
            assert (outpath / "ion.itp").exists()
            # 3 ITP files total
            itp_files = list(outpath.glob("*.itp"))
            assert len(itp_files) == 3
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_hydrate_interface_solute(self):
        """FIX #11: hydrate+interface+solute verifies ch4_hydrate.itp in output.

        This test specifically covers the workflow that exposed the previous
        blocker where hydrate-only path was not reachable in the export step.
        """
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--hydrate", "--lattice-type", "sI", "--guest", "CH4",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "solute.gro").exists()
            assert (outpath / "solute.top").exists()
            # FIX #11: ch4_hydrate.itp MUST be present in the output
            assert (outpath / "ch4_hydrate.itp").exists(), (
                "FIX #11: ch4_hydrate.itp missing from hydrate+interface+solute output"
            )
            assert (outpath / "ch4_liquid.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
            # 3 ITP files total
            itp_files = list(outpath.glob("*.itp"))
            assert len(itp_files) == 3
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_solute_source_custom(self):
        """Solute from custom source produces correct output with custom ITP."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--custom-gro", ETOH_GRO, "--custom-itp", ETOH_ITP,
                "--custom-placement", "random", "--custom-count", "3",
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "--solute-source", "custom",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "solute.gro").exists()
            assert (outpath / "solute.top").exists()
            assert (outpath / "etoh.itp").exists()
            assert (outpath / "ch4_liquid.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
            # 3 ITP files total
            itp_files = list(outpath.glob("*.itp"))
            assert len(itp_files) == 3
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_pocket_mode_ion(self):
        """Pocket mode + ion insertion produces ion.gro with ion.itp."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "pocket",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--pocket-diameter", "2.0",
                "--ion-concentration", "0.15",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "ion.gro").exists()
            assert (outpath / "ion.top").exists()
            assert (outpath / "ion.itp").exists()
            assert (outpath / "tip4p-ice.itp").exists()
        finally:
            shutil.rmtree(outdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Export correctness tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPipelineExportCorrectness:
    """Validate content of exported GROMACS files."""

    @staticmethod
    def _parse_gro_atom_count(gro_path: str) -> int:
        """Parse atom count from line 2 of a .gro file."""
        with open(gro_path) as f:
            lines = f.readlines()
        if len(lines) < 2:
            return 0
        try:
            return int(lines[1].strip())
        except ValueError:
            return 0

    @staticmethod
    def _parse_top_molecules(top_path: str) -> dict[str, int]:
        """Parse [ molecules ] section from .top file.

        Returns dict mapping molecule name → count.
        """
        molecules = {}
        in_section = False
        with open(top_path) as f:
            for line in f:
                line = line.strip()
                if line == "[ molecules ]":
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("[") or (not line and molecules):
                        break
                    if line and not line.startswith(";") and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                molecules[parts[0]] = int(parts[1])
                            except ValueError:
                                pass
        return molecules

    def test_gro_file_has_correct_atom_count(self):
        """GRO file atom count matches declared count on line 2."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            gro_path = os.path.join(outdir, "interface.gro")
            atom_count = self._parse_gro_atom_count(gro_path)
            assert atom_count > 0, "GRO file should have positive atom count"
            # Verify atom count matches actual atom lines
            with open(gro_path) as f:
                lines = f.readlines()
            # Lines 2 to -1 are atom lines (last line is box vector)
            actual_atoms = len(lines) - 3  # title, count, box vector
            assert actual_atoms == atom_count, (
                f"GRO declared {atom_count} atoms but found {actual_atoms} atom lines"
            )
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_top_file_has_molecules_section(self):
        """TOP file contains [ molecules ] section with at least SOL."""
        outdir = make_temp_output_dir()
        try:
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            top_path = os.path.join(outdir, "interface.top")
            molecules = self._parse_top_molecules(top_path)
            assert "SOL" in molecules, "TOP [molecules] should contain SOL"
            assert molecules["SOL"] > 0, "SOL count should be positive"
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_itp_files_copied(self):
        """Expected ITP files exist in output directory."""
        outdir = make_temp_output_dir()
        try:
            # Test with solute to get ch4_liquid.itp
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--solute-type", "CH4", "--solute-concentration", "0.5",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0
            outpath = Path(outdir)
            assert (outpath / "tip4p-ice.itp").exists()
            assert (outpath / "ch4_liquid.itp").exists()
            # 2 ITP files total for interface+solute
            itp_files = list(outpath.glob("*.itp"))
            assert len(itp_files) == 2
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_no_overwrite_flag(self):
        """--no-overwrite in non-empty directory → graceful skip with exit code 0."""
        outdir = make_temp_output_dir()
        try:
            # Create a pre-existing file
            Path(outdir, "existing.txt").write_text("existing content")
            rc, _, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--no-overwrite",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0, (
                f"--no-overwrite skip should exit 0 (graceful), got {rc}"
            )
            assert "--no-overwrite" in stderr, (
                "stderr should mention --no-overwrite"
            )
        finally:
            shutil.rmtree(outdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Grompp validation tests (subprocess, 60-120s each)
# ---------------------------------------------------------------------------


@gmx_skipif
@pytest.mark.slow
class TestPipelineGromppValidation:
    """Validate CLI pipeline output passes gmx grompp.

    Tests the full CLI subprocess → gmx grompp path, validating
    CLI-specific ITP staging (copy_itp_files_for_structure from
    itp_helpers.py) which differs from API test staging.
    """

    def test_slab_interface_grompp(self):
        """Slab interface export from CLI passes gmx grompp."""
        outdir = make_temp_output_dir()
        try:
            rc, stdout, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--gromacs", "-g", "--no-diagram",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed: {stderr[-500:]}"

            # Run gmx grompp on output
            workspace = Path(outdir)
            gro_file = "interface.gro"
            top_file = "interface.top"

            # Verify output files exist
            assert (workspace / gro_file).exists(), f"{gro_file} not found"
            assert (workspace / top_file).exists(), f"{top_file} not found"

            # Copy MDP file
            shutil.copy(MDP_PATH, workspace / "em.mdp")

            exit_code, gmx_stderr = run_gmx_grompp(
                workspace, gro_file=gro_file, top_file=top_file
            )
            assert exit_code == 0, f"gmx grompp failed:\n{gmx_stderr[-500:]}"
        finally:
            shutil.rmtree(outdir, ignore_errors=True)

    def test_solute_ion_chain_grompp(self):
        """Interface→Solute→Ion chain export from CLI passes gmx grompp."""
        outdir = make_temp_output_dir()
        try:
            rc, stdout, stderr = run_quickice(
                "-T", "270", "-P", "0.1",
                "--interface", "--mode", "slab",
                "--box-x", "3", "--box-y", "3", "--box-z", "5",
                "--ice-thickness", "1.5", "--water-thickness", "2.0",
                "--solute-type", "CH4", "--solute-concentration", "0.15",
                "--ion-concentration", "0.15",
                "--gromacs", "-g", "--no-diagram",
                "-o", outdir,
                timeout=120,
            )
            assert rc == 0, f"CLI pipeline failed: {stderr[-500:]}"

            workspace = Path(outdir)
            # Ion is the most downstream step → ion.gro, ion.top
            gro_file = "ion.gro"
            top_file = "ion.top"

            assert (workspace / gro_file).exists(), f"{gro_file} not found"
            assert (workspace / top_file).exists(), f"{top_file} not found"

            shutil.copy(MDP_PATH, workspace / "em.mdp")
            exit_code, gmx_stderr = run_gmx_grompp(
                workspace, gro_file=gro_file, top_file=top_file
            )
            assert exit_code == 0, f"gmx grompp failed:\n{gmx_stderr[-500:]}"
        finally:
            shutil.rmtree(outdir, ignore_errors=True)
