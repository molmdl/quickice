# Coding Conventions

**Analysis Date:** 2026-04-07

## Naming Patterns

**Files:**
- Python modules use `snake_case`: `phase_mapping.py`, `pdb_writer.py`, `melting_curves.py`
- Test files prefixed with `test_`: `test_validators.py`, `test_ranking.py`
- Package directories use `snake_case`: `quickice/`, `phase_mapping/`, `structure_generation/`

**Functions:**
- `snake_case` for all functions: `validate_temperature()`, `lookup_phase()`, `calculate_supercell()`
- Private methods prefixed with underscore: `_generate_single()`, `_parse_gro()`, `_calculate_oo_distances_pbc()`
- Factory functions prefixed with `create_` or `get_`: `create_parser()`, `get_arguments()`, `get_genice_lattice_name()`

**Variables:**
- `snake_case` for variables: `nmolecules`, `phase_info`, `supercell_matrix`
- Constants in `UPPER_SNAKE_CASE`: `IDEAL_OO_DISTANCE`, `OO_CUTOFF`, `TRIPLE_POINTS`, `PHASE_TO_GENICE`

**Types/Classes:**
- `PascalCase` for classes: `Candidate`, `GenerationResult`, `IceStructureGenerator`, `UnknownPhaseError`
- Dataclasses used for data containers: `Candidate`, `GenerationResult`, `RankedCandidate`, `RankingResult`
- Exception classes suffixed with `Error`: `PhaseMappingError`, `UnknownPhaseError`, `StructureGenerationError`, `UnsupportedPhaseError`

**Type Annotations:**
- Modern Python 3.14 syntax: `list[str]`, `dict[str, Any]`, `tuple[np.ndarray, list[str], np.ndarray]`
- Return type annotations on all public functions: `-> float`, `-> dict[str, Any]`, `-> GenerationResult`
- Optional types use `| None`: `temperature: float = None`, `weights: dict[str, float] | None = None`

## Code Style

**Formatting:**
- No formal formatter config detected (no .prettierrc, .editorconfig, biome.json)
- 4-space indentation (Python standard)
- Line length appears to follow PEP 8 conventions
- Blank lines between class methods, after import blocks

**Linting:**
- No formal linter config detected (no .flake8, .pylintrc, pyproject.toml linting section)
- Code follows PEP 8 conventions organically

**Imports:**
- Standard library imports first
- Third-party imports second (numpy, pytest, scipy, etc.)
- Local imports last
- Absolute imports preferred: `from quickice.phase_mapping import lookup_phase`
- Import grouping with blank lines between sections

## Import Organization

**Order:**
1. Standard library: `import sys`, `from pathlib import Path`, `from argparse import ArgumentTypeError`
2. Third-party packages: `import numpy as np`, `import pytest`, `from scipy.spatial import cKDTree`
3. Local modules: `from quickice.structure_generation.types import Candidate`

**Path Aliases:**
- None detected - all imports use full module paths
- Package structure allows clean imports: `from quickice.ranking import rank_candidates`

## Error Handling

**Custom Exceptions:**
- Base exception classes for each module domain:
  - `quickice/phase_mapping/errors.py`: `PhaseMappingError`, `UnknownPhaseError`
  - `quickice/structure_generation/errors.py`: `StructureGenerationError`, `UnsupportedPhaseError`
- Exception classes include contextual attributes:
```python
class UnknownPhaseError(PhaseMappingError):
    def __init__(self, message: str, temperature: float = None, pressure: float = None):
        self.temperature = temperature
        self.pressure = pressure
```

**Error Messages:**
- Descriptive error messages with context: `"Temperature must be between 0 and 500K, got {temp}K"`
- Include user input in error messages for debugging
- CLI validators raise `ArgumentTypeError` for argparse integration

**Exception Handling:**
- Wrap external library errors with custom exceptions:
```python
except Exception as e:
    raise StructureGenerationError(
        f"Failed to generate ice structure ({type(e).__name__}): {e}"
    ) from e
```

- Main entry points catch and format exceptions:
```python
except UnknownPhaseError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

## Logging

**Framework:** No logging framework detected - uses `print()` statements

**Patterns:**
- User-facing output via `print()`:
```python
print(f"Temperature: {args.temperature}K")
print(f"Phase: {phase_info['phase_name']} ({phase_info['phase_id']})")
```
- Errors printed to stderr: `print(f"Error: {e}", file=sys.stderr)`
- Progress indicators during generation: `print(f"Generated {len(gen_result.candidates)} candidates")`

## Comments

**When to Comment:**
- Module-level docstrings for all modules
- Function/method docstrings for all public APIs
- Inline comments for non-obvious calculations or unit conversions:
```python
# Convert from nm³ to cm³ (1 nm³ = 1e-21 cm³)
volume_cm3 = volume_nm3 * 1e-21
```

**Docstrings:**
- Google-style docstrings throughout:
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

- Examples in docstrings where helpful:
```python
"""
Example:
    >>> from quickice.phase_mapping import lookup_phase
    >>> phase_info = lookup_phase(273, 0)  # Ice Ih
    >>> result = generate_candidates(phase_info, nmolecules=100)
"""
```

- Module-level docstrings describe purpose:
```python
"""GenIce-based ice structure generator.

This module provides the IceStructureGenerator class that wraps GenIce's API
to generate physically valid ice structures with diverse hydrogen bond networks.
"""
```

## Function Design

**Size:** Functions typically 10-50 lines, complex functions up to ~100 lines

**Parameters:**
- Type-hinted parameters with defaults for optional args
- Dictionary inputs for complex configurations: `phase_info: dict`
- Optional parameters with clear defaults: `n_candidates: int = 10`, `symprec: float = 1e-4`

**Return Values:**
- Dataclasses for structured returns: `GenerationResult`, `RankingResult`, `OutputResult`
- Tuple unpacking for multiple values: `-> tuple[np.ndarray, list[str], np.ndarray]`
- Consistent return patterns: validators return validated value or raise exception

**Function Naming Patterns:**
- Validators: `validate_*`, `check_*`
- Calculators: `calculate_*`
- Generators: `generate_*`
- Writers: `write_*`
- Lookups: `lookup_*`, `get_*`

## Module Design

**Exports:**
- Explicit `__all__` in all `__init__.py` files:
```python
__all__ = [
    "lookup_phase",
    "IcePhaseLookup",
    "PhaseMappingError",
    "UnknownPhaseError",
    # ...
]
```

**Barrel Files:**
- `__init__.py` files re-export public API from submodules
- Clean import paths: `from quickice.ranking import rank_candidates`
- Types, errors, and functions organized in separate files within modules

**Module Structure:**
- `types.py`: Dataclasses for data containers
- `errors.py`: Custom exception classes
- Main functionality in module-specific files (e.g., `scorer.py`, `generator.py`, `lookup.py`)
- Constants defined at module level or in dedicated `data/` submodules

**Private Members:**
- Internal functions prefixed with underscore
- Private methods for implementation details
- Module-level constants can be public if part of API

---

*Convention analysis: 2026-04-07*
