"""Data types for output phase results."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OutputResult:
    """Complete output result from the ice structure generation pipeline.

    Attributes:
        output_files: Paths to generated PDB files containing ice structures
        phase_diagram_files: Paths to generated diagram files (PNG, SVG, txt)
        validation_results: Per-structure validation info (spacegroup, overlap, valid)
        summary: Summary info (n_candidates, n_validated, user_T, user_P)
    """

    output_files: list[str] = field(default_factory=list)
    phase_diagram_files: list[str] = field(default_factory=list)
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
