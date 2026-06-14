"""Integration tests for QuickIce CLI.

Tests the full CLI flow using the unified entry point (python -m quickice).
"""

from tests.conftest import run_quickice


class TestValidInputs:
    """Test cases for valid CLI inputs."""
    
    def test_valid_inputs_print_values(self):
        """Valid inputs should print temperature, pressure, and molecules."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode == 0
        assert "Temperature: 273.0K" in stdout
        assert "Pressure: 0.1 MPa" in stdout
        assert "Molecules: 100" in stdout
    
    def test_boundary_temperature_min(self):
        """Low temperature (72K, boundary of Ice Ic) should be accepted."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "72",
            "--pressure", "0.1",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode == 0
        assert "Temperature: 72.0K" in stdout
    
    def test_boundary_temperature_max(self):
        """High temperature (450K) with sufficient pressure for Ice VII."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "450",
            "--pressure", "5000",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode == 0
        assert "Temperature: 450.0K" in stdout
    
    def test_boundary_pressure_min(self):
        """Minimum pressure (0 MPa) should be accepted for Ice Ih."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "250",
            "--pressure", "0",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode == 0
        assert "Pressure: 0.0 MPa" in stdout
    
    def test_boundary_pressure_max(self):
        """Maximum pressure (10000 MPa) should be accepted for Ice X."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "200",
            "--pressure", "10000",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode == 0
        assert "Pressure: 10000.0 MPa" in stdout
    
    def test_boundary_nmolecules_min(self):
        """Minimum nmolecules (4) should be accepted."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "4",
            timeout=10
        )
        
        assert returncode == 0
        assert "Molecules: 4" in stdout
    
    def test_boundary_nmolecules_max(self):
        """Large nmolecules (1000) should be accepted and complete in reasonable time."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "1000",
            timeout=10
        )
        
        assert returncode == 0
        assert "Molecules: 1000" in stdout


class TestInvalidInputs:
    """Test cases for invalid CLI inputs."""
    
    def test_invalid_temperature_too_low(self):
        """Temperature below 0K should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "-1",
            "--pressure", "100",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Temperature must be between 0 and 500K" in stderr
    
    def test_invalid_temperature_too_high(self):
        """Temperature above 500K should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "501",
            "--pressure", "100",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Temperature must be between 0 and 500K" in stderr
    
    def test_invalid_temperature_not_numeric(self):
        """Non-numeric temperature should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "abc",
            "--pressure", "100",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Temperature must be a number" in stderr
    
    def test_invalid_pressure_too_low(self):
        """Pressure below 0 MPa should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "-1",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Pressure must be between 0 and 10000 MPa" in stderr
    
    def test_invalid_pressure_too_high(self):
        """Pressure above 10000 MPa should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "10001",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Pressure must be between 0 and 10000 MPa" in stderr
    
    def test_invalid_pressure_not_numeric(self):
        """Non-numeric pressure should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "abc",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "Pressure must be a number" in stderr
    
    def test_invalid_nmolecules_too_low(self):
        """Molecule count below 4 should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "3",
            timeout=10
        )
        
        assert returncode != 0
        assert "Molecule count must be between 4 and 100000" in stderr
    
    def test_invalid_nmolecules_too_high(self):
        """Molecule count above 100000 should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "100001",
            timeout=10
        )
        
        assert returncode != 0
        assert "Molecule count must be between 4 and 100000" in stderr
    
    def test_invalid_nmolecules_float(self):
        """Float molecule count should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "4.5",
            timeout=10
        )
        
        assert returncode != 0
        assert "Molecule count must be an integer" in stderr
    
    def test_invalid_nmolecules_not_numeric(self):
        """Non-numeric molecule count should be rejected."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "abc",
            timeout=10
        )
        
        assert returncode != 0
        assert "Molecule count must be an integer" in stderr


class TestMissingArguments:
    """Test cases for missing required arguments."""
    
    def test_missing_temperature(self):
        """Missing temperature should show error."""
        returncode, stdout, stderr = run_quickice(
            "--pressure", "100",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "required: --temperature" in stderr.lower() or "required: -T" in stderr.lower()
    
    def test_missing_pressure(self):
        """Missing pressure should show error."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--nmolecules", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "required: --pressure" in stderr.lower() or "required: -P" in stderr.lower()
    
    def test_missing_nmolecules(self):
        """Missing nmolecules should show error."""
        returncode, stdout, stderr = run_quickice(
            "--temperature", "300",
            "--pressure", "100",
            timeout=10
        )
        
        assert returncode != 0
        assert "--nmolecules is required for ice generation" in stderr.lower()
    
    def test_no_arguments(self):
        """No arguments should show help (like git with no args)."""
        returncode, stdout, stderr = run_quickice(timeout=10)
        
        assert returncode == 0
        assert "usage:" in stdout.lower()


class TestHelpAndVersion:
    """Test cases for --help and --version flags."""
    
    def test_help_shows_usage(self):
        """--help should show usage information."""
        returncode, stdout, stderr = run_quickice("--help", timeout=10)
        
        # --help causes argparse to exit with 0
        assert returncode == 0
        assert "QuickIce - Ice structure generation" in stdout
        assert "--temperature" in stdout
        assert "--pressure" in stdout
        assert "--nmolecules" in stdout
        assert "0-500K" in stdout
    
    def test_version_shows_version(self):
        """--version should show version number."""
        returncode, stdout, stderr = run_quickice("--version", timeout=10)
        
        # --version causes argparse to exit with 0
        assert returncode == 0
        assert "4.5.0" in stdout
