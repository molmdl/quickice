"""Tests for input validators."""

import pytest
from argparse import ArgumentTypeError
from quickice.validation.validators import (
    validate_temperature,
    validate_pressure,
    validate_nmolecules,
    validate_box_dimension,
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


class TestValidateBoxDimension:
    """Tests for box dimension validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Box dimension 1.0 nm should be accepted."""
        result = validate_box_dimension("1.0")
        assert result == 1.0
        assert isinstance(result, float)

    def test_accepts_valid_large_value(self):
        """Box dimension 100.0 nm should be accepted."""
        result = validate_box_dimension("100.0")
        assert result == 100.0
        assert isinstance(result, float)

    def test_accepts_valid_middle_value(self):
        """Box dimension 5.0 nm should be accepted."""
        result = validate_box_dimension("5.0")
        assert result == 5.0
        assert isinstance(result, float)

    def test_rejects_value_below_minimum(self):
        """Box dimension 0.999 nm should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("0.999")
        assert "box dimension" in str(exc_info.value).lower()
        assert "1.0" in str(exc_info.value)

    def test_rejects_very_small_value(self):
        """Box dimension 0.5 nm should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("0.5")
        assert "box dimension" in str(exc_info.value).lower()
        assert "1.0" in str(exc_info.value)

    def test_rejects_zero(self):
        """Box dimension 0 nm should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("0")
        assert "positive" in str(exc_info.value).lower()

    def test_rejects_negative_value(self):
        """Negative box dimension should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("-1.0")
        assert "positive" in str(exc_info.value).lower()

    def test_rejects_non_numeric_input(self):
        """Non-numeric input should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("abc")
        assert "number" in str(exc_info.value).lower()

    def test_accepts_float_input(self):
        """Float input like 5.5 should be accepted."""
        result = validate_box_dimension("5.5")
        assert result == 5.5
        assert isinstance(result, float)

    def test_error_message_includes_actual_value(self):
        """Error message should include the actual value provided."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_box_dimension("0.6")
        error_msg = str(exc_info.value)
        assert "0.6" in error_msg

    def test_minimum_matches_interface_builder_constant(self):
        """Ensure validator minimum matches MINIMUM_BOX_DIMENSION constant."""
        from quickice.structure_generation.interface_builder import MINIMUM_BOX_DIMENSION
        # Try value just below minimum
        with pytest.raises(ArgumentTypeError):
            validate_box_dimension(str(MINIMUM_BOX_DIMENSION - 0.001))
        # Try value at minimum (should succeed)
        result = validate_box_dimension(str(MINIMUM_BOX_DIMENSION))
        assert result == MINIMUM_BOX_DIMENSION
