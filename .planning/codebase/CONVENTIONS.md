# Coding Conventions

**Analysis Date:** 2026-03-28

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `validators.py`, `pdb_writer.py`)
- Test files: `test_{module}.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Package init: `__init__.py`
- Error definitions: `errors.py` (dedicated file per package)

**Functions:**
- `snake_case` for all functions
- Private helpers prefixed with underscore: `_calculate_cell_parameters()`, `_build_result()`
- Validator functions prefixed with `validate_`: `validate_temperature()`, `validate_space_group()`
- Check functions prefixed with `check_`: `check_atomic_overlap()`

**Variables:**
- `snake_case` for all variables
- Descriptive names preferred: `nmolecules`, `phase_id`, `supercell_matrix`
- Loop indices: single letter `i`, `j` acceptable in simple loops

**Classes:**
- `PascalCase` for class names: `Candidate`, `GenerationResult`, `IceStructureGenerator`
- Exception classes suffixed with `Error`: `PhaseMappingError`, `UnknownPhaseError`, `StructureGenerationError`
- Data classes use `@dataclass` decorator

**Constants:**
- `UPPER_SNAKE_CASE` for module-level constants: `IDEAL_OO_DISTANCE`, `OO_CUTOFF`, `TRIPLE_POINTS`
- Dictionary constants: `PHASE_METADATA`, `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`

**Type Annotations:**
- Use modern Python syntax: `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)
- Return types always specified: `-> float`, `-> tuple[int, str, str]`
- Optional types: `Optional[list]` or `args: Optional[list] = None`

## Code Style

**Formatting:**
- No explicit formatter config detected (no `.prettierrc`, `pyproject.toml` with `[tool.black]`, etc.)
- 4-space indentation
- Max line length appears to be ~100 characters
- Blank lines between class methods, between logical sections

**Linting:**
- No explicit linting config detected (no `.flake8`, `.pylintrc`, `pyproject.toml` with `[tool.ruff]`)
- Code follows PEP 8 conventions naturally

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (numpy, pytest, etc.)
3. Local imports from `quickice.*`

**Pattern:**
```python
# Standard library
import argparse
import sys
from pathlib import Path
from typing import Optional

# Third-party
import numpy as np
import pytest
import spglib

# Local
from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankingResult
```

**Path Aliases:**
- No path aliases configured
- Use full relative imports: `from quickice.phase_mapping.errors import UnknownPhaseError`

## Error Handling

**Custom Exceptions:**
- Define in dedicated `errors.py` files per package
- Inherit from domain-specific base: `StructureGenerationError`, `PhaseMappingError`
- Include context attributes: `phase_id`, `temperature`, `pressure`

**Patterns:**
```python
# Custom exception with context
class UnknownPhaseError(PhaseMappingError):
    def __init__(
        self,
        message: str = "No ice phase found for given conditions",
        temperature: float = None,
        pressure: float = None
    ):
        hint = "Conditions may be outside supported phase diagram regions."
        full_message = f"{message}. {hint}"
        super().__init__(full_message, temperature, pressure)
```

**Exception Chaining:**
```python
try:
    # ... code that may fail
except Exception as e:
    raise StructureGenerationError(
        f"Failed to generate ice structure: {e}"
    ) from e
```

**Validation Errors:**
- Use `ArgumentTypeError` from argparse for CLI validation
- Include original value and constraints in message:
```python
raise ArgumentTypeError(
    f"Temperature must be between 0 and 500K, got {temp}K"
)
```

## Logging

**Framework:** console (print statements)

**Patterns:**
- Main entry point uses `print()` for user output
- Errors go to stderr: `print(f"Error: {e}", file=sys.stderr)`
- No logging framework configured

## Comments

**When to Comment:**
- Module-level docstrings explaining purpose
- Complex algorithms (phase lookup logic in `lookup.py`)
- Physical constants with units
- Non-obvious business logic

**Docstring Style:**
```python
def validate_temperature(value: str) -> float:
    """Validate temperature input.
    
    Args:
        value: String input from CLI argument
        
    Returns:
        Validated temperature as float (0-500K range)
        
    Raises:
        ArgumentTypeError: If value is not numeric or outside valid range
    """
```

**JSDoc/TSDoc:**
- Not applicable (Python codebase)
- Uses Google-style docstrings with Args, Returns, Raises sections

## Function Design

**Size:** 
- Functions typically 10-50 lines
- Complex functions broken into private helpers: `_generate_single()`, `_parse_gro()`

**Parameters:**
- Use type hints for all parameters
- Optional parameters with defaults at the end
- Use dataclasses for complex parameter groups

**Return Values:**
- Always specify return type
- Use dataclasses for structured returns: `GenerationResult`, `RankingResult`
- Return tuples for simple multi-values: `tuple[np.ndarray, list[str], np.ndarray]`

**Private Methods:**
- Prefix with underscore: `_build_result()`, `_calculate_cell_parameters()`
- Called only within the class/module

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` for explicit exports:
```python
__all__ = [
    "lookup_phase",
    "IcePhaseLookup",
    "PhaseMappingError",
    "UnknownPhaseError",
]
```

**Barrel Files:**
- `__init__.py` re-exports from submodules
- Pattern:
```python
from quickice.phase_mapping.lookup import lookup_phase, IcePhaseLookup
from quickice.phase_mapping.errors import PhaseMappingError, UnknownPhaseError

__all__ = [
    "lookup_phase",
    "IcePhaseLookup",
    "PhaseMappingError",
    "UnknownPhaseError",
]
```

**Package Structure:**
- Each feature area is a package with `__init__.py`, `types.py`, `errors.py`
- Examples: `quickice/phase_mapping/`, `quickice/structure_generation/`, `quickice/ranking/`

## Data Structures

**Dataclasses:**
- Use `@dataclass` for structured data
- Include type hints and defaults:
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

**Constants:**
- Define at module level
- Group related constants together
- Include units in comments:
```python
IDEAL_OO_DISTANCE = 0.276  # nm - ideal O-O distance in ice (H-bond length)
OO_CUTOFF = 0.35  # nm - cutoff for H-bond detection
```

---

*Convention analysis: 2026-03-28*
