"""
Error types for phase mapping operations.

This module defines custom exceptions for phase mapping failures,
providing clear error messages and context for debugging.
"""


class PhaseMappingError(Exception):
    """
    Base exception for phase mapping failures.

    Raised when the phase mapping operation cannot complete successfully.
    This is the base class for all phase mapping related errors.

    Attributes:
        message: Human-readable error description.
        temperature: Optional temperature value that caused the error.
        pressure: Optional pressure value that caused the error.
    """

    def __init__(
        self,
        message: str,
        temperature: float = None,
        pressure: float = None
    ):
        self.temperature = temperature
        self.pressure = pressure

        # Build detailed message with context
        parts = [message]
        if temperature is not None and pressure is not None:
            parts.append(f"Given: T={temperature}K, P={pressure}MPa")

        super().__init__(" | ".join(parts))


class UnknownPhaseError(PhaseMappingError):
    """
    Raised when T,P conditions fall outside all known phase regions.

    This error indicates that the given temperature and pressure combination
    does not map to any of the supported ice phases. This typically occurs
    when conditions are outside the phase diagram boundaries or in regions
    not yet supported (e.g., liquid water, supercritical water).

    Example:
        >>> raise UnknownPhaseError(
        ...     "No ice phase found",
        ...     temperature=400,
        ...     pressure=50
        ... )
    """

    def __init__(
        self,
        message: str = "No ice phase found for given conditions",
        temperature: float = None,
        pressure: float = None
    ):
        hint = "Conditions may be outside supported phase diagram regions."
        full_message = f"{message}. {hint}"
        super().__init__(full_message, temperature, pressure)
