"""Custom exceptions for structure generation."""


class StructureGenerationError(Exception):
    """Base error for structure generation."""

    pass


class UnsupportedPhaseError(StructureGenerationError):
    """Phase not supported by GenIce."""

    def __init__(self, message: str, phase_id: str):
        super().__init__(message)
        self.phase_id = phase_id


class InterfaceGenerationError(StructureGenerationError):
    """Error during interface structure generation.

    Attributes:
        mode: Interface mode that failed ("slab", "pocket", or "piece")
    """

    def __init__(self, message: str, mode: str):
        """Initialize interface generation error.

        Args:
            message: Error description
            mode: Interface mode that failed
        """
        super().__init__(message)
        self.mode = mode
