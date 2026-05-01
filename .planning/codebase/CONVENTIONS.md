# Coding Conventions

**Analysis Date:** 2026-05-02

## Naming Patterns

**Files:**
- Python modules: lowercase with underscores (e.g., `validators.py`, `interface_builder.py`)
- Test files: `test_*.py` prefix with descriptive names (e.g., `test_validators.py`, `test_cli_integration.py`)
- Package directories: lowercase with underscores (e.g., `phase_mapping/`, `structure_generation/`)

**Functions:**
- Snake_case: `validate_temperature()`, `calculate_supercell()`, `generate_interface()`
- Validator functions: prefixed with `validate_` (e.g., `validate_temperature`, `validate_pressure`)
- Factory methods: prefixed with `from_` (e.g., `from_dict()`, `from_lattice_type()`)
- Boolean getters: prefixed with `is_` (e.g., `is_cell_orthogonal()`)

**Variables:**
- Snake_case: `temperature`, `pressure`, `nmolecules`
- Descriptive names preferred over abbreviations: `nmolecules` not `nmol`, `temperature` not `temp`
- Loop variables: `i`, `idx`, or descriptive names when context matters

**Types:**
- PascalCase for classes: `Candidate`, `InterfaceConfig`, `InterfaceGenerationError`
- Type hints: Use built-in types (`list[str]`, `dict[str, Any]`) and `Optional[T]` for optional values
- Dataclasses: Used for data structures (e.g., `Candidate`, `InterfaceConfig`, `HydrateConfig`)

## Code Style

**Formatting:**
- No automated formatting tool configured (no `.prettierrc`, `pyproject.toml`, or `setup.cfg` with formatting rules)
- Indentation: 4 spaces (standard Python)
- Max line length: ~100 characters (observed in source files)
- Blank lines: 2 blank lines before class definitions, 1 blank line before method definitions

**Linting:**
- No linter configuration detected (no `.flake8`, `.pylintrc`, or `pyproject.toml` with linting rules)
- Code quality maintained through code review and testing

## Import Organization

**Order:**
1. Standard library imports (e.g., `import sys`, `from pathlib import Path`)
2. Third-party imports (e.g., `import numpy as np`, `import pytest`)
3. Local application imports (e.g., `from quickice.cli.parser import get_arguments`)

**Example from `quickice/main.py`:**
```python
import sys
import shutil
from pathlib import Path

from quickice.cli.parser import get_arguments
from quickice.phase_mapping import lookup_phase, UnknownPhaseError
from quickice.structure_generation import generate_candidates
```

**Path Aliases:**
- No path aliases configured
- Imports use full package paths: `from quickice.structure_generation.types import Candidate`
- Relative imports: Not used, all imports are absolute from package root

## Error Handling

**Patterns:**
- Custom exception classes for domain-specific errors
- Exception hierarchy: Base exception classes with specific subclasses
- Error messages include context and actionable hints

**Custom Exceptions:**
- `PhaseMappingError` → `UnknownPhaseError` (in `quickice/phase_mapping/errors.py`)
- `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError` (in `quickice/structure_generation/errors.py`)
- Exceptions store relevant context (temperature, pressure, mode, etc.)

**Example from `quickice/phase_mapping/errors.py`:**
```python
class PhaseMappingError(Exception):
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
```

**Exception Handling in CLI:**
- Specific exceptions caught first, general exceptions last
- Exit codes: 0 for success, 1 for error
- Error messages written to stderr

**Example from `quickice/main.py`:**
```python
try:
    args = get_arguments()
    # ... processing ...
    return 0
except UnknownPhaseError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
except InterfaceGenerationError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
except SystemExit:
    raise
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

## Logging

**Framework:** No logging framework configured (no `logging` module usage detected)

**Patterns:**
- CLI output: Direct `print()` statements to stdout
- Error output: `print(..., file=sys.stderr)`
- No log levels (INFO, DEBUG, WARNING, etc.)
- No log file output

**Example from `quickice/main.py`:**
```python
print("QuickIce - Ice structure generation")
print()
print(f"Temperature: {args.temperature}K")
print(f"Pressure: {args.pressure} MPa")
```

**Recommendation:** Consider implementing Python's `logging` module for better log management in production environments.

## Comments

**When to Comment:**
- Module-level docstrings: Every module has a docstring explaining purpose
- Class-level docstrings: Explain class purpose, attributes, and usage
- Function docstrings: All public functions have docstrings
- Inline comments: Used sparingly for complex logic or non-obvious decisions

**Docstring Format:** Google-style docstrings with Args, Returns, Raises sections

**Example from `quickice/validation/validators.py`:**
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

**Example from `quickice/structure_generation/types.py`:**
```python
@dataclass
class Candidate:
    """A single generated ice structure candidate.

    Attributes:
        positions: (N_atoms, 3) coordinates in nm from GenIce.
        atom_names: List of atom names ["O", "H", "H", ...]
        cell: (3, 3) cell vectors in nm, stored as ROW vectors.
        nmolecules: Actual number of water molecules
        phase_id: Phase identifier (e.g., "ice_ih")
        seed: Random seed used for generation
        metadata: Additional info from Phase 2 (density, T, P)
    """
```

## Function Design

**Size:** Functions typically 10-30 lines, with complex operations broken into helper functions

**Parameters:**
- Type hints used for all parameters
- Default values used for optional parameters
- Configuration objects passed as dataclasses (e.g., `InterfaceConfig`)

**Return Values:**
- Dataclasses for structured return data (e.g., `GenerationResult`, `InterfaceStructure`)
- Tuples for simple multi-value returns (e.g., `(supercell, actual_count)`)
- Exit codes (int) for CLI main functions

**Example from `quickice/structure_generation/mapper.py`:**
```python
def calculate_supercell(target_nmolecules: int, unit_cell_molecules: int) -> tuple[np.ndarray, int]:
    """Calculate supercell dimensions to reach target molecule count.
    
    Args:
        target_nmolecules: Desired number of molecules
        unit_cell_molecules: Molecules per unit cell
        
    Returns:
        Tuple of (supercell matrix, actual molecule count)
    """
```

## Module Design

**Exports:**
- Each package has an `__init__.py` that exports public API
- Use `__all__` to explicitly list exports
- Import from submodules in `__init__.py` for clean public API

**Example from `quickice/structure_generation/__init__.py`:**
```python
from quickice.structure_generation.types import (
    Candidate,
    GenerationResult,
    InterfaceConfig,
    # ... more imports
)

__all__ = [
    "Candidate",
    "GenerationResult",
    "InterfaceConfig",
    # ... more exports
]
```

**Barrel Files:** 
- Used consistently across packages
- Re-exports from `__init__.py` for clean imports
- Allows: `from quickice.structure_generation import Candidate` instead of `from quickice.structure_generation.types import Candidate`

**Package Structure:**
- `quickice/cli/` - Command-line interface
- `quickice/validation/` - Input validation
- `quickice/phase_mapping/` - Phase diagram lookup
- `quickice/structure_generation/` - Core structure generation
- `quickice/ranking/` - Candidate ranking
- `quickice/output/` - File output writers
- `quickice/gui/` - PySide6 GUI
- `quickice/data/` - Static data files (GROMACS templates)

---

*Convention analysis: 2026-05-02*
