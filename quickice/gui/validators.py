"""GUI-specific input validators for QuickIce.

These validators return tuple[bool, str] for inline error display in the GUI.
They differ from CLI validators in:
- Return (is_valid, error_message) tuples instead of raising exceptions
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
    
    IMPORTANT: This validator uses MPa units for consistency with phase diagram.
    The valid range is 0-10000 MPa (matches CLI, covers all ice phases including Ice X).
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_pressure("100")
        (True, "")
        >>> validate_pressure("50000")
        (False, "Pressure must be between 0 and 10000 MPa")
        >>> validate_pressure("abc")
        (False, "Pressure must be a number")
    """
    try:
        pressure = float(value)
    except ValueError:
        return (False, "Pressure must be a number")
    
    if pressure < 0 or pressure > 10000:
        return (False, "Pressure must be between 0 and 10000 MPa")
    
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


def validate_box_dimension(value: str) -> Tuple[bool, str]:
    """Validate box dimension input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_box_dimension("5.0")
        (True, "")
        >>> validate_box_dimension("0.1")
        (False, "Box dimension must be between 1.0 and 100 nm")
        >>> validate_box_dimension("abc")
        (False, "Box dimension must be a number")
    """
    try:
        dim = float(value)
    except ValueError:
        return (False, "Box dimension must be a number")
    
    if dim < 1.0 or dim > 100.0:
        return (False, 
                f"Box dimension must be between 1.0 and 100 nm. "
                f"Got {dim:.2f} nm. "
                f"Typical values: 5–10 nm for small systems, 20–50 nm for large systems."
        )
    
    return (True, "")


def validate_thickness(value: str) -> Tuple[bool, str]:
    """Validate thickness input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_thickness("3.0")
        (True, "")
        >>> validate_thickness("100")
        (False, "Thickness must be between 0.5 and 50 nm")
        >>> validate_thickness("abc")
        (False, "Thickness must be a number")
    """
    try:
        thick = float(value)
    except ValueError:
        return (False, "Thickness must be a number")
    
    if thick < 0.5 or thick > 50.0:
        return (False, 
                f"Thickness must be between 0.5 and 50 nm. "
                f"Got {thick:.2f} nm. "
                f"For slab mode: ice and water thickness typically 2–10 nm. "
                f"Remember: box_z = 2×ice_thickness + water_thickness."
        )
    
    return (True, "")


def validate_pocket_diameter(value: str) -> Tuple[bool, str]:
    """Validate pocket diameter input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_pocket_diameter("2.0")
        (True, "")
        >>> validate_pocket_diameter("100")
        (False, "Diameter must be between 0.5 and 50 nm")
        >>> validate_pocket_diameter("abc")
        (False, "Diameter must be a number")
    """
    try:
        diam = float(value)
    except ValueError:
        return (False, "Diameter must be a number")
    
    if diam < 0.5 or diam > 50.0:
        return (False, 
                f"Pocket diameter must be between 0.5 and 50 nm. "
                f"Got {diam:.2f} nm. "
                f"Typical values: 1–5 nm for confined water studies. "
                f"Remember: pocket diameter must be smaller than all box dimensions."
        )
    
    return (True, "")


def validate_seed(value: str) -> Tuple[bool, str]:
    """Validate random seed input for GUI.
    
    Args:
        value: String input from GUI text field
        
    Returns:
        Tuple of (is_valid, error_message). error_message is empty string on success.
        
    Examples:
        >>> validate_seed("42")
        (True, "")
        >>> validate_seed("4.5")
        (False, "Seed must be an integer between 1 and 999999")
        >>> validate_seed("0")
        (False, "Seed must be an integer between 1 and 999999")
        >>> validate_seed("abc")
        (False, "Seed must be an integer")
    """
    # Check if it's a float first (reject floats like "4.5")
    try:
        float_val = float(value)
    except ValueError:
        return (False, "Seed must be an integer")
    
    # Check if the float representation differs from integer (e.g., 4.5 != 4)
    if float_val != int(float_val):
        return (False, "Seed must be an integer between 1 and 999999")
    
    # Convert to int
    seed = int(float_val)
    
    if seed < 1 or seed > 999999:
        return (False, "Seed must be an integer between 1 and 999999")
    
    return (True, "")
