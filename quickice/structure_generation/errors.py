"""Custom exceptions for structure generation."""


class StructureGenerationError(Exception):
    """Base error for structure generation."""

    pass


class UnsupportedPhaseError(StructureGenerationError):
    """Phase not supported by GenIce."""

    def __init__(self, message: str, phase_id: str):
        super().__init__(message)
        self.phase_id = phase_id
