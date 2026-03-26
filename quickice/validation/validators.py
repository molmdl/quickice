"""Input validators for CLI arguments.

These validators are used as argparse type converters to validate and convert
user input for temperature, pressure, and molecule count.
"""

from argparse import ArgumentTypeError


def validate_temperature(value: str) -> float:
    """Validate temperature input.
    
    Args:
        value: String input from CLI argument
        
    Returns:
        Validated temperature as float (0-500K range)
        
    Raises:
        ArgumentTypeError: If value is not numeric or outside valid range
    """
    try:
        temp = float(value)
    except ValueError:
        raise ArgumentTypeError(
            f"Temperature must be a number, got '{value}'"
        )
    
    if temp < 0 or temp > 500:
        raise ArgumentTypeError(
            f"Temperature must be between 0 and 500K, got {temp}K"
        )
    
    return temp


def validate_pressure(value: str) -> float:
    """Validate pressure input.
    
    Args:
        value: String input from CLI argument
        
    Returns:
        Validated pressure as float (0-10000 MPa range)
        
    Raises:
        ArgumentTypeError: If value is not numeric or outside valid range
    """
    try:
        pressure = float(value)
    except ValueError:
        raise ArgumentTypeError(
            f"Pressure must be a number, got '{value}'"
        )
    
    if pressure < 0 or pressure > 10000:
        raise ArgumentTypeError(
            f"Pressure must be between 0 and 10000 MPa, got {pressure} MPa"
        )
    
    return pressure


def validate_nmolecules(value: str) -> int:
    """Validate molecule count input.
    
    Args:
        value: String input from CLI argument
        
    Returns:
        Validated molecule count as integer (4-100000 range)
        
    Raises:
        ArgumentTypeError: If value is not an integer or outside valid range
    """
    # Check if it's a float first (reject floats like "4.5")
    try:
        float_val = float(value)
    except ValueError:
        raise ArgumentTypeError(
            f"Molecule count must be an integer, got '{value}'"
        )
    
    # Check if the float representation differs from integer (e.g., 4.5 != 4)
    if float_val != int(float_val):
        raise ArgumentTypeError(
            f"Molecule count must be an integer, got {value}"
        )
    
    # Convert to int
    nmol = int(float_val)
    
    if nmol < 4 or nmol > 100000:
        raise ArgumentTypeError(
            f"Molecule count must be between 4 and 100000, got {nmol}"
        )
    
    return nmol
