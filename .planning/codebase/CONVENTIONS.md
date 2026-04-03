# Coding Conventions

**Analysis Date:** 2025-04-04

## Language & Version

**Primary:** Python 3.10+ - Modern syntax features used throughout

**Key Features Used:**
- Modern type hint syntax: `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)
- Union types with `|` operator
- `match` statements where appropriate
- Dataclasses with `field(default_factory=...)`

## Naming Patterns

**Files:**
- Snake_case: `phase_mapping.py`, `structure_generation.py`
- Test files: `test_<module>.py` (e.g., `test_validators.py`)
- Private modules: None observed

**Functions:**
- Snake_case: `validate_temperature()`, `lookup_phase()`, `calculate_supercell()`
- Private functions: Prefix underscore `_calculate_oo_distances_pbc()`
- Validator functions: `validate_<noun>()` pattern

**Variables:**
- Snake_case: `temperature`, `pressure`, `nmolecules`
- Constants: UPPER_SNAKE_CASE: `IDEAL_OO_DISTANCE`, `OO_CUTOFF`, `AVOGADRO`

**Types/Classes:**
- PascalCase: `Candidate`, `GenerationResult`, `RankedCandidate`
- Exception classes: `<Name>Error` pattern: `UnknownPhaseError`, `UnsupportedPhaseError`
- Dataclasses for data containers

**Module Constants:**
```python
# Module-level constants in UPPER_SNAKE_CASE
IDEAL_OO_DISTANCE = 0.276  # nm
OO_CUTOFF = 0.35  # nm
AVOGADRO = 6.022e23  # molecules/mol
```

## Code Style

**Formatting:**
- No external formatter detected (no .prettierrc, .editorconfig, biome.json)
- Indentation: 4 spaces
- Line length: ~100 characters observed
- Trailing commas in multi-line collections

**Linting:**
- No ESLint/Pylint configuration detected
- Rely on pytest for validation

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports
3. Local application imports

**Example from `quickice/ranking/scorer.py`:**
```python
import numpy as np
from collections import Counter
from scipy.spatial import cKDTree

from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankedCandidate, RankingResult
```

**Path Imports:**
- Use relative imports within package: `from .types import Candidate`
- Use absolute imports for cross-module: `from quickice.structure_generation.types import Candidate`

## Error Handling

**Custom Exceptions:**
- Base exception per module: `PhaseMappingError`, `StructureGenerationError`
- Specific exceptions inherit from base: `UnknownPhaseError(PhaseMappingError)`

**Pattern from `quickice/phase_mapping/errors.py`:**
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

**Raising Exceptions:**
```python
# In validators - use ArgumentTypeError for CLI
from argparse import ArgumentTypeError

raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")

# In library code - use custom exceptions
raise UnknownPhaseError(
    "No ice phase found for given conditions",
    temperature=T,
    pressure=P,
)
```

## Logging

**Pattern:** `print()` statements for CLI output, no structured logging detected

**CLI Output Pattern from `quickice/main.py`:**
```python
print("QuickIce - Ice structure generation")
print()
print(f"Temperature: {args.temperature}K")
print(f"Pressure: {args.pressure} MPa")
print(f"Molecules: {args.nmolecules}")

# Error output to stderr
print(f"Error: {e}", file=sys.stderr)
```

## Comments

**When to Comment:**
- Module-level docstrings explaining purpose
- Function docstrings for all public functions
- Inline comments explaining non-obvious calculations or physical constants

**Docstring Format (Google-style):**
```python
def validate_temperature(value: str) -> float:
    """Validate temperature input.
    
    Args:
        value: String input from CLI argument
        
    Returns:
        Validated temperature as float (0-500K range)
        
    Raises:
        ArgumentTypeError: If value is not numeric or outside valid range
        
    Example:
        >>> validate_temperature("300")
        300.0
    """
```

**Note sections for important caveats:**
```python
def energy_score(candidate: Candidate) -> float:
    """Calculate energy score based on O-O distance deviation from ideal.
    
    Note:
        This is NOT an actual energy calculation - it's a heuristic based on
        O-O distance statistics. For real energies, use MD simulations with
        appropriate force fields.
    """
```

## Function Design

**Size:** Functions typically 10-50 lines; longer functions have clear sections

**Parameters:**
- Use type hints for all parameters
- Default values for optional parameters
- Use `| None` for optional types

**Return Values:**
- Single return type preferred
- Use dataclasses for complex return values
- Return `dict` for dynamic structures

**Example signature:**
```python
def rank_candidates(
    candidates: list[Candidate],
    weights: dict[str, float] | None = None
) -> RankingResult:
```

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` for explicit public API
- Export types, errors, and main functions

**Pattern from `quickice/ranking/__init__.py`:**
```python
from quickice.ranking.types import RankedCandidate, RankingResult
from quickice.ranking.scorer import (
    rank_candidates,
    energy_score,
    density_score,
    diversity_score,
    normalize_scores,
)

__all__ = [
    "RankedCandidate",
    "RankingResult",
    "rank_candidates",
    "energy_score",
    "density_score",
    "diversity_score",
    "normalize_scores",
]
```

**File Organization:**
- `types.py`: Data structures and types
- `errors.py`: Custom exceptions
- `<domain>.py`: Main functionality
- `__init__.py`: Public API exports

## Type Annotations

**Modern Python 3.10+ Syntax:**
```python
# Use built-in generics
def lookup_phase(temperature: float, pressure: float) -> dict[str, Any]:
    ...

# Use | for unions
def get_arguments(args: list[str] | None = None) -> argparse.Namespace:
    ...

# Use dataclass for structured data
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

## Data Structures

**Dataclasses for Data Containers:**
- Use `@dataclass` decorator
- Use `field(default_factory=dict)` for mutable defaults
- Include docstring with Attributes section

```python
@dataclass
class GenerationResult:
    """Result of generating multiple candidates.

    Attributes:
        candidates: List of generated Candidate objects
        requested_nmolecules: Number of molecules requested by user
        actual_nmolecules: Actual number generated (may differ due to supercell)
        phase_id: Phase identifier
        phase_name: Human-readable phase name
        density: Density in g/cm³
        was_rounded: True if actual_nmolecules != requested_nmolecules
    """
    candidates: list[Candidate]
    requested_nmolecules: int
    actual_nmolecules: int
    phase_id: str
    phase_name: str
    density: float
    was_rounded: bool
```

## Constants

**Physical Constants:**
```python
IDEAL_OO_DISTANCE = 0.276  # nm - ideal O-O distance in ice (H-bond length)
OO_CUTOFF = 0.35  # nm - cutoff for H-bond detection
AVOGADRO = 6.022e23  # molecules/mol
WATER_MASS = 18.01528  # g/mol
```

**Mapping Constants:**
```python
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",
    "ice_ic": "ice1c",
    "ice_ii": "ice2",
    ...
}

UNIT_CELL_MOLECULES = {
    "ice1h": 16,
    "ice1c": 8,
    ...
}
```

---

*Convention analysis: 2025-04-04*
