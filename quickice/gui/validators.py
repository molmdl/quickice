"""GUI-specific input validators for QuickIce.

These validators return tuple[bool, str] for inline error display in the GUI.
They differ from CLI validators in:
- Return (is_valid, error_message) tuples instead of raising exceptions
- Pressure uses BAR units (0-10000 bar) instead of MPa
- Molecule count max is 216 (GUI limit) instead of 100000 (CLI limit)
"""

from typing import Tuple


def validate_temperature(value: str) -> Tuple[bool, str]:
    """Validate temperature input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_temperature("300")
        (True, "")
        >>> validate_temperature("600")
        (False, "Temperature must be between 0 and 500 K")
        >>> validate_temperature("abc")
        (False, "Temperature must be a number")
    """
    try:
        temp = float(value)
    except ValueError:
        return (False, "Temperature must be a number")
    
    if temp < 0 or temp > 500:
        return (False, "Temperature must be between 0 and 500 K")
    
    return (True, "")


def validate_pressure(value: str) -> Tuple[bool, str]:
    """Validate pressure input for GUI.
    
    IMPORTANT: This validator uses BAR units (not MPa like CLI validators).
    The valid range is 0-10000 bar.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_pressure("100")
        (True, "")
        >>> validate_pressure("15000")
        (False, "Pressure must be between 0 and 10000 bar")
        >>> validate_pressure("abc")
        (False, "Pressure must be a number")
    """
    try:
        pressure = float(value)
    except ValueError:
        return (False, "Pressure must be a number")
    
    if pressure < 0 or pressure > 10000:
        return (False, "Pressure must be between 0 and 10000 bar")
    
    return (True, "")


def validate_nmolecules(value: str) -> Tuple[bool, str]:
    """Validate molecule count input for GUI.
    
    IMPORTANT: The GUI maximum is 216 molecules (not 100000 like CLI).
    This limit is due to computational constraints in the interactive GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_nmolecules("96")
        (True, "")
        >>> validate_nmolecules("300")
        (False, "Molecule count must be between 4 and 216")
        >>> validate_nmolecules("4.5")
        (False, "Molecule count must be an integer")
        >>> validate_nmolecules("abc")
        (False, "Molecule count must be an integer")
    """
    # Check if it's a float first (reject floats like "4.5")
    try:
        float_val = float(value)
    except ValueError:
        return (False, "Molecule count must be an integer")
    
    # Check if the float representation differs from integer (e.g., 4.5 != 4)
    if float_val != int(float_val):
        return (False, "Molecule count must be an integer")
    
    # Convert to int
    nmol = int(float_val)
    
    if nmol < 4 or nmol > 216:
        return (False, "Molecule count must be between 4 and 216")
    
    return (True, "")
