"""Tests for input validators."""

import pytest
from argparse import ArgumentTypeError
from quickice.validation.validators import (
    validate_temperature,
    validate_pressure,
    validate_nmolecules,
)


class TestValidateTemperature:
    """Tests for temperature validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Temperature 0K should be accepted."""
        result = validate_temperature("0")
        assert result == 0.0
        assert isinstance(result, float)

    def test_accepts_valid_maximum_boundary(self):
        """Temperature 500K should be accepted."""
        result = validate_temperature("500")
        assert result == 500.0
        assert isinstance(result, float)

    def test_accepts_valid_middle_value(self):
        """Temperature 300K should be accepted."""
        result = validate_temperature("300")
        assert result == 300.0
        assert isinstance(result, float)

    def test_rejects_negative_temperature(self):
        """Temperature -1K should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_temperature("-1")
        assert "temperature" in str(exc_info.value).lower()

    def test_rejects_temperature_above_maximum(self):
        """Temperature 501K should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_temperature("501")
        assert "temperature" in str(exc_info.value).lower()

    def test_rejects_non_numeric_input(self):
        """Non-numeric input should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_temperature("abc")
        assert "temperature" in str(exc_info.value).lower()

    def test_accepts_float_input(self):
        """Float input like 300.5 should be accepted."""
        result = validate_temperature("300.5")
        assert result == 300.5
        assert isinstance(result, float)


class TestValidatePressure:
    """Tests for pressure validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Pressure 0 MPa should be accepted."""
        result = validate_pressure("0")
        assert result == 0.0
        assert isinstance(result, float)

    def test_accepts_valid_maximum_boundary(self):
        """Pressure 10000 MPa should be accepted."""
        result = validate_pressure("10000")
        assert result == 10000.0
        assert isinstance(result, float)

    def test_accepts_valid_middle_value(self):
        """Pressure 5000 MPa should be accepted."""
        result = validate_pressure("5000")
        assert result == 5000.0
        assert isinstance(result, float)

    def test_rejects_negative_pressure(self):
        """Pressure -1 MPa should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_pressure("-1")
        assert "pressure" in str(exc_info.value).lower()

    def test_rejects_pressure_above_maximum(self):
        """Pressure 10001 MPa should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_pressure("10001")
        assert "pressure" in str(exc_info.value).lower()

    def test_rejects_non_numeric_input(self):
        """Non-numeric input should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_pressure("abc")
        assert "pressure" in str(exc_info.value).lower()

    def test_accepts_float_input(self):
        """Float input like 5000.5 should be accepted."""
        result = validate_pressure("5000.5")
        assert result == 5000.5
        assert isinstance(result, float)


class TestValidateNmolecules:
    """Tests for molecule count validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Molecule count 4 should be accepted."""
        result = validate_nmolecules("4")
        assert result == 4
        assert isinstance(result, int)

    def test_accepts_valid_maximum_boundary(self):
        """Molecule count 100000 should be accepted."""
        result = validate_nmolecules("100000")
        assert result == 100000
        assert isinstance(result, int)

    def test_accepts_valid_middle_value(self):
        """Molecule count 100 should be accepted."""
        result = validate_nmolecules("100")
        assert result == 100
        assert isinstance(result, int)

    def test_rejects_count_below_minimum(self):
        """Molecule count 3 should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_nmolecules("3")
        assert "molecule" in str(exc_info.value).lower()

    def test_rejects_count_above_maximum(self):
        """Molecule count 100001 should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_nmolecules("100001")
        assert "molecule" in str(exc_info.value).lower()

    def test_rejects_float_input(self):
        """Float input like 4.5 should be rejected (no silent truncation)."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_nmolecules("4.5")
        assert "molecule" in str(exc_info.value).lower()

    def test_rejects_non_numeric_input(self):
        """Non-numeric input should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_nmolecules("abc")
        assert "molecule" in str(exc_info.value).lower()

    def test_returns_integer_not_float(self):
        """Ensure return type is int, not float."""
        result = validate_nmolecules("100")
        assert isinstance(result, int)
        assert not isinstance(result, bool)  # bool is subclass of int, exclude it
