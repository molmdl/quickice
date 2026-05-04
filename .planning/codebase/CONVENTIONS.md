# Coding Conventions

**Analysis Date:** 2026-05-05

## Naming Patterns

**Files:**
- Use lowercase with underscores: `validators.py`, `lookup.py`, `interface_builder.py`
- Test files: `test_<module>.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Module directories: lowercase with underscores: `phase_mapping/`, `structure_generation/`

**Functions:**
- Use snake_case: `validate_temperature()`, `lookup_phase()`, `generate_candidates()`
- Private functions: leading underscore `_build_result()`, `_generate_single()`
- Validator functions: `validate_<parameter>()` pattern
- Factory methods: `from_dict()`, `from_lattice_type()`

**Variables:**
- Use snake_case: `temperature`, `nmolecules`, `phase_id`
- Boolean variables: descriptive names like `was_rounded`, `skip_export`
- Loop variables: `i`, `idx` for simple loops; descriptive names for complex logic

**Classes:**
- Use PascalCase: `Candidate`, `InterfaceConfig`, `IceStructureGenerator`
- Exception classes: suffix with `Error`: `PhaseMappingError`, `UnknownPhaseError`
- Config classes: suffix with `Config`: `InterfaceConfig`, `HydrateConfig`
- Result classes: suffix with `Result`: `GenerationResult`, `RankingResult`

**Constants:**
- Use UPPER_SNAKE_CASE: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `HYDRATE_LATTICES`
- Module-level constants at top of file after imports
- Dictionaries with configuration data: descriptive names like `PHASE_METADATA`, `MOLECULE_TYPE_INFO`

**Type Variables:**
- Use PascalCase: `Candidate`, `RankedCandidate`, `MoleculeIndex`

## Code Style

**Formatting:**
- No formal formatting tool detected (no Black, autopep8, or yapf config)
- Indentation: 4 spaces (standard Python)
- Maximum line length: appears to be ~100-120 characters
- Blank lines: 2 blank lines before top-level functions/classes, 1 blank line between methods

**Linting:**
- No linting configuration detected (no .flake8, .pylintrc, pyproject.toml with linter config)
- Code follows PEP 8 conventions naturally

## Import Organization

**Order:**
1. Standard library imports (alphabetically sorted)
   ```python
   import sys
   import shutil
   from pathlib import Path
   ```

2. Third-party imports (alphabetically sorted)
   ```python
   import numpy as np
   import pytest
   from iapws import IAPWS95
   ```

3. Local application imports (grouped by module)
   ```python
   from quickice.cli.parser import get_arguments
   from quickice.phase_mapping import lookup_phase, UnknownPhaseError
   from quickice.structure_generation import generate_candidates
   from quickice.structure_generation.types import InterfaceConfig
   ```

**Import Patterns:**
- Use absolute imports from `quickice.*` root
- Group related imports from same module:
  ```python
  from quickice.structure_generation.interface_builder import (
      generate_interface,
      InterfaceGenerationError,
  )
  ```
- Import types from `types.py` submodule:
  ```python
  from quickice.structure_generation.types import Candidate, GenerationResult
  ```

**Path Aliases:**
- No path aliases configured
- Use full module paths: `quickice.phase_mapping.lookup`

## Type Annotations

**Style:**
- Use Python 3.10+ union syntax: `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)
- All function parameters and return values are annotated
- Optional parameters: use `Optional[Type]` or `Type | None`
- Class attributes in dataclasses are typed

**Examples:**
```python
def validate_temperature(value: str) -> float:
    """Validate temperature input."""
    
def lookup_phase(temperature: float, pressure: float) -> dict:
    """Determine ice phase using curve-based boundary evaluation."""

def rank_candidates(
    candidates: list[Candidate],
    weights: dict[str, float] | None = None
) -> RankingResult:
    """Rank ice structure candidates by energy, density, diversity."""
```

**Dataclasses:**
```python
@dataclass
class Candidate:
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    nmolecules: int
    phase_id: str
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)
```

## Error Handling

**Custom Exceptions:**
- Define custom exception classes for each module
- Inherit from base exception hierarchy
- Store context attributes for debugging

**Patterns:**
```python
# Exception hierarchy
class PhaseMappingError(Exception):
    """Base exception for phase mapping failures."""
    def __init__(self, message: str, temperature: float = None, pressure: float = None):
        self.temperature = temperature
        self.pressure = pressure
        # Build detailed message with context
        parts = [message]
        if temperature is not None and pressure is not None:
            parts.append(f"Given: T={temperature}K, P={pressure}MPa")
        super().__init__(" | ".join(parts))

class UnknownPhaseError(PhaseMappingError):
    """Raised when T,P conditions fall outside all known phase regions."""
    pass
```

**CLI Validation:**
- Use `ArgumentTypeError` for argparse validators
- Include actual value in error message
```python
def validate_temperature(value: str) -> float:
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
```

**Main Entry Point:**
- Catch specific exceptions first, then general `Exception`
- Return exit codes: 0 for success, non-zero for error
- Print errors to stderr

```python
def main() -> int:
    try:
        # Main logic
        return 0
    except UnknownPhaseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except InterfaceGenerationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

**Data Validation:**
- Use `__post_init__` in dataclasses for validation
```python
@dataclass
class InterfaceConfig:
    overlap_threshold: float = 0.25
    
    def __post_init__(self):
        if not (0.1 <= self.overlap_threshold <= 1.0):
            raise ValueError(
                f"overlap_threshold={self.overlap_threshold} nm is outside reasonable range [0.1, 1.0] nm. "
                f"This suggests a unit mismatch."
            )
```

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
```python
import logging

logger = logging.getLogger(__name__)

# Usage
logger.info("Starting interface generation...")
logger.warning(f"Density {density} outside expected range")
logger.error(f"Failed to generate structure: {e}")
```

**Module-level Logger:**
- Define at top of module after imports: `logger = logging.getLogger(__name__)`
- Use `__name__` to get module-specific logger
- Files using logging: `quickice/phase_mapping/water_density.py`, `quickice/output/gromacs_writer.py`, `quickice/gui/main_window.py`

## Comments

**When to Comment:**
- Module-level docstrings for all files (required)
- Function docstrings for all public functions (required)
- Class docstrings for all classes (required)
- Inline comments for non-obvious logic or workarounds
- TODO/FIXME comments for known issues (none detected in current codebase)

**Docstrings:**
- Use Google-style docstrings
- Triple-quoted with `"""`
- Include sections: Args, Returns, Raises, Example, Note

**Example:**
```python
def lookup_phase(temperature: float, pressure: float) -> dict:
    """
    Determine ice phase using curve-based boundary evaluation.
    
    This function uses hierarchical curve evaluation to determine which ice
    polymorph is stable at the given temperature and pressure.
    
    Args:
        temperature: Temperature in Kelvin
        pressure: Pressure in MPa
    
    Returns:
        Dict with phase_id, phase_name, density, temperature, pressure
    
    Raises:
        UnknownPhaseError: If conditions fall outside all known phase regions
    
    Example:
        >>> result = lookup_phase(273, 0.1)
        >>> result["phase_id"]
        'ice_ih'
    
    Note:
        Uses IAPWS R14-08 certified melting curves for high confidence.
    """
```

**Module Docstrings:**
```python
"""Curve-based ice phase lookup.

Determines ice phase by evaluating boundary curves, not polygon containment.
Uses IAPWS R14-08(2011) melting curves and linear interpolation for solid-solid boundaries.
"""
```

## Function Design

**Size:**
- Functions typically 10-50 lines
- Complex functions broken into helper functions with `_` prefix
- Main entry point functions can be longer (e.g., `main()` in `quickice/main.py` is ~250 lines)

**Parameters:**
- Use type hints for all parameters
- Group related parameters into config dataclasses
- Use optional parameters with defaults for less common options
- Prefer keyword arguments for boolean flags

**Return Values:**
- Always specify return type
- Return dataclasses/typed objects instead of raw tuples/dicts
- Return `int` exit codes from CLI functions
- Raise exceptions for errors rather than returning error codes

**Example:**
```python
def rank_candidates(
    candidates: list[Candidate],
    weights: dict[str, float] | None = None
) -> RankingResult:
    """Rank ice structure candidates by energy, density, diversity.
    
    Args:
        candidates: List of Candidate objects to rank
        weights: Optional custom weights for scoring (default: equal weights)
    
    Returns:
        RankingResult with ranked_candidates and scoring_metadata
    """
```

## Module Design

**Exports:**
- Use `__all__` to explicitly define public API
- Export types, main functions, and errors from `__init__.py`

**Barrel Files:**
- Each module has `__init__.py` that re-exports key classes/functions
- Example from `quickice/structure_generation/__init__.py`:
```python
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.generator import IceStructureGenerator, generate_candidates
from quickice.structure_generation.errors import StructureGenerationError

__all__ = [
    "Candidate",
    "GenerationResult",
    "IceStructureGenerator",
    "generate_candidates",
    "StructureGenerationError",
]
```

**Module Organization:**
- `types.py`: Data classes and type definitions
- `errors.py`: Custom exceptions
- `mapper.py`: Mapping functions and constants
- `generator.py`: Main generator class
- `__init__.py`: Re-exports public API

## File Organization

**Directory Structure Pattern:**
```
quickice/
├── __init__.py              # Package version
├── main.py                  # CLI entry point
├── cli/                     # CLI argument parsing
│   ├── __init__.py
│   └── parser.py
├── validation/              # Input validation
│   ├── __init__.py
│   └── validators.py
├── phase_mapping/           # Phase identification
│   ├── __init__.py
│   ├── lookup.py
│   ├── errors.py
│   └── ...
├── structure_generation/    # Structure generation
│   ├── __init__.py
│   ├── types.py
│   ├── errors.py
│   ├── generator.py
│   └── ...
├── ranking/                 # Candidate ranking
│   ├── __init__.py
│   ├── types.py
│   └── scorer.py
└── gui/                     # GUI components
    ├── __init__.py
    └── main_window.py
```

**File Naming:**
- Descriptive names indicating functionality
- Related functionality grouped in subdirectories
- Test files mirror source structure in `tests/` directory

---

*Convention analysis: 2026-05-05*
