"""Integration tests for QuickIce CLI.

Tests the full CLI flow using subprocess to run 'python quickice.py'.
"""

import subprocess
import sys
from pathlib import Path


# Path to the quickice.py script
QUICKICE_SCRIPT = Path(__file__).parent.parent / "quickice.py"


def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments.
    
    Args:
        *args: Command-line arguments to pass
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode, result.stdout, result.stderr


class TestValidInputs:
    """Test cases for valid CLI inputs."""
    
    def test_valid_inputs_print_values(self):
        """Valid inputs should print temperature, pressure, and molecules."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 273.0K" in stdout
        assert "Pressure: 0.1 MPa" in stdout
        assert "Molecules: 100" in stdout
    
    def test_boundary_temperature_min(self):
        """Low temperature (72K, boundary of Ice Ic) should be accepted."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "72",
            "--pressure", "0.1",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 72.0K" in stdout
    
    def test_boundary_temperature_max(self):
        """High temperature (450K) with sufficient pressure for Ice VII."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "450",
            "--pressure", "5000",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 450.0K" in stdout
    
    def test_boundary_pressure_min(self):
        """Minimum pressure (0 MPa) should be accepted for Ice Ih."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "250",
            "--pressure", "0",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Pressure: 0.0 MPa" in stdout
    
    def test_boundary_pressure_max(self):
        """Maximum pressure (10000 MPa) should be accepted for Ice X."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "200",
            "--pressure", "10000",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Pressure: 10000.0 MPa" in stdout
    
    def test_boundary_nmolecules_min(self):
        """Minimum nmolecules (4) should be accepted."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "4"
        )
        
        assert returncode == 0
        assert "Molecules: 4" in stdout
    
    def test_boundary_nmolecules_max(self):
        """Large nmolecules (1000) should be accepted and complete in reasonable time."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "1000"
        )
        
        assert returncode == 0
        assert "Molecules: 1000" in stdout


class TestInvalidInputs:
    """Test cases for invalid CLI inputs."""
    
    def test_invalid_temperature_too_low(self):
        """Temperature below 0K should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "-1",
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Temperature must be between 0 and 500K" in stderr
    
    def test_invalid_temperature_too_high(self):
        """Temperature above 500K should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "501",
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Temperature must be between 0 and 500K" in stderr
    
    def test_invalid_temperature_not_numeric(self):
        """Non-numeric temperature should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "abc",
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Temperature must be a number" in stderr
    
    def test_invalid_pressure_too_low(self):
        """Pressure below 0 MPa should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "-1",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Pressure must be between 0 and 10000 MPa" in stderr
    
    def test_invalid_pressure_too_high(self):
        """Pressure above 10000 MPa should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "10001",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Pressure must be between 0 and 10000 MPa" in stderr
    
    def test_invalid_pressure_not_numeric(self):
        """Non-numeric pressure should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "abc",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "Pressure must be a number" in stderr
    
    def test_invalid_nmolecules_too_low(self):
        """Molecule count below 4 should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "3"
        )
        
        assert returncode != 0
        assert "Molecule count must be between 4 and 100000" in stderr
    
    def test_invalid_nmolecules_too_high(self):
        """Molecule count above 100000 should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "100001"
        )
        
        assert returncode != 0
        assert "Molecule count must be between 4 and 100000" in stderr
    
    def test_invalid_nmolecules_float(self):
        """Float molecule count should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "4.5"
        )
        
        assert returncode != 0
        assert "Molecule count must be an integer" in stderr
    
    def test_invalid_nmolecules_not_numeric(self):
        """Non-numeric molecule count should be rejected."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "abc"
        )
        
        assert returncode != 0
        assert "Molecule count must be an integer" in stderr


class TestMissingArguments:
    """Test cases for missing required arguments."""
    
    def test_missing_temperature(self):
        """Missing temperature should show error."""
        returncode, stdout, stderr = run_cli(
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "required: --temperature" in stderr.lower() or "required: -T" in stderr.lower()
    
    def test_missing_pressure(self):
        """Missing pressure should show error."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--nmolecules", "100"
        )
        
        assert returncode != 0
        assert "required: --pressure" in stderr.lower() or "required: -P" in stderr.lower()
    
    def test_missing_nmolecules(self):
        """Missing nmolecules should show error."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100"
        )
        
        assert returncode != 0
        assert "--nmolecules is required for ice generation" in stderr.lower()
    
    def test_no_arguments(self):
        """No arguments should show error."""
        returncode, stdout, stderr = run_cli()
        
        assert returncode != 0


class TestHelpAndVersion:
    """Test cases for --help and --version flags."""
    
    def test_help_shows_usage(self):
        """--help should show usage information."""
        returncode, stdout, stderr = run_cli("--help")
        
        # --help causes argparse to exit with 0
        assert returncode == 0
        assert "QuickIce - Ice structure generation" in stdout
        assert "--temperature" in stdout
        assert "--pressure" in stdout
        assert "--nmolecules" in stdout
        assert "0-500K" in stdout
    
    def test_version_shows_version(self):
        """--version should show version number."""
        returncode, stdout, stderr = run_cli("--version")
        
        # --version causes argparse to exit with 0
        assert returncode == 0
        assert "python quickice.py 4.0.0" in stdout
