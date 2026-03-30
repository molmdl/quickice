# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules
- Module names describe purpose: `lookup.py`, `validators.py`, `scorer.py`
- Test files: `test_<module>.py` pattern

**Classes:**
- Use `PascalCase` for all classes
- Test classes: `Test<FeatureName>` pattern (e.g., `TestValidateTemperature`)
- Data classes: descriptive nouns (`Candidate`, `GenerationResult`, `RankingResult`)
- Exception classes: `<Domain>Error` pattern (`UnknownPhaseError`, `StructureGenerationError`)

**Functions:**
- Use `snake_case` for all functions
- Verb-first naming for actions: `validate_temperature`, `calculate_supercell`, `rank_candidates`
- Noun naming for getters: `lookup_phase`, `get_genice_lattice_name`

**Variables:**
- Use `snake_case` for local variables and parameters
- Descriptive names: `nmolecules`, `phase_id`, `temperature`, `pressure`
- Short names acceptable in limited scope: `T`, `P` for temperature/pressure in physics contexts

**Constants:**
- Use `UPPER_SNAKE_CASE` for module-level constants
- Examples: `PHASE_TO_GENICE`, `TRIPLE_POINTS`, `IDEAL_OO_DISTANCE`, `OO_CUTOFF`

**Private Functions:**
- Use underscore prefix for internal functions: `_build_result`, `_calculate_oo_distances_pbc`

## Code Style

**Formatting:**
- No explicit formatter configuration detected
- 4-space indentation
- Line length appears flexible (100+ characters observed)
- Blank lines between class methods (2 lines before class, 1 between methods)

**Type Hints:**
- Use type hints on all public functions
- Modern Python 3.9+ syntax: `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)
- Union syntax for optional: `param: type | None = None`
- Return types always specified: `def function(...) -> ReturnType:`

**Example:**
```python
def lookup_phase(temperature: float, pressure: float) -> dict:
    """Docstring..."""

def rank_candidates(
    candidates: list[Candidate],
    weights: dict[str, float] | None = None
) -> RankingResult:
    """Docstring..."""
```

## Dataclasses

**Usage:**
- Use `@dataclass` decorator for data containers
- Include docstrings with `Attributes:` section

**Pattern:**
```python
@dataclass
class Candidate:
    """A single generated ice structure candidate.

    Attributes:
        positions: (N_atoms, 3) coordinates in nm
        atom_names: List of atom names ["O", "H", "H", ...]
        cell: (3, 3) cell vectors in nm
        nmolecules: Actual number of water molecules
        phase_id: Phase identifier (e.g., "ice_ih")
        seed: Random seed used for generation
        metadata: Additional info from Phase 2 (density, T, P)
    """
    positions: np.ndarray
    atom_names: list[str]
    cell: np.ndarray
    nmolecules: int
    phase_id: str
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Mutable Defaults:**
- Use `field(default_factory=dict)` or `field(default_factory=list)` for mutable defaults
- Never use `[]` or `{}` directly as default values

## Import Organization

**Order:**
1. Standard library imports (alphabetically)
2. Third-party imports (alphabetically)
3. Local imports (alphabetically)

**Pattern:**
```python
"""Module docstring."""

import subprocess
import sys
from argparse import ArgumentTypeError
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

from quickice.phase_mapping import lookup_phase, UnknownPhaseError
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import Candidate
```

**Public API:**
- Define `__all__` in `__init__.py` files
- List all public symbols explicitly

**Example from `quickice/ranking/__init__.py`:**
```python
__all__ = [
    # Types
    "RankedCandidate",
    "RankingResult",
    # Main API
    "rank_candidates",
    # Individual scorers (for advanced use)
    "energy_score",
    "density_score",
    "diversity_score",
    "normalize_scores",
]
```

## Error Handling

**Custom Exceptions:**
- Create domain-specific exception classes
- Inherit from appropriate base exception
- Include context in exception attributes

**Pattern:**
```python
class PhaseMappingError(Exception):
    """Base exception for phase mapping failures."""

    def __init__(
        self,
        message: str,
        temperature: float = None,
        pressure: float = None
    ):
        self.temperature = temperature
        self.pressure = pressure
        parts = [message]
        if temperature is not None and pressure is not None:
            parts.append(f"Given: T={temperature}K, P={pressure}MPa")
        super().__init__(" | ".join(parts))


class UnknownPhaseError(PhaseMappingError):
    """Raised when T,P conditions fall outside all known phase regions."""
    
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

**Validation Pattern:**
```python
def validate_temperature(value: str) -> float:
    """Validate temperature input."""
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

## Logging

**Approach:**
- No logging framework detected
- Use `print()` for CLI output
- Use `sys.stderr` for error messages

**Pattern from `main.py`:**
```python
print("QuickIce - Ice structure generation")
print()
print(f"Temperature: {args.temperature}K")
print(f"Pressure: {args.pressure} MPa")

# Errors to stderr
print(f"Error: {e}", file=sys.stderr)
return 1
```

## Comments

**When to Comment:**
- Module-level docstrings explain purpose and usage
- Function docstrings with Args, Returns, Raises, Note sections
- Inline comments for non-obvious logic (e.g., physics constants, algorithm details)
- TODO/FIXME comments for future work

**Docstring Style:**
- Google-style docstrings
- Include Args, Returns, Raises, Note sections as appropriate

**Example:**
```python
def energy_score(candidate: Candidate) -> float:
    """Calculate energy score based on O-O distance deviation from ideal.
    
    This is a heuristic estimate of the energy based on the assumption that
    ideal ice structures have O-O distances close to 0.276 nm (the typical
    hydrogen bond length in ice). Structures with O-O distances close to
    this ideal value are assumed to have lower energy.
    
    Args:
        candidate: A Candidate object from Phase 3
    
    Returns:
        Energy score (lower = better, lower = closer to ideal O-O distances).
        Returns float('inf') if no O-O distances found (degenerate case).
    
    Note:
        This is NOT an actual energy calculation - it's a heuristic based on
        O-O distance statistics. For real energies, use MD simulations with
        appropriate force fields.
    """
```

## Function Design

**Size:**
- Functions typically 10-50 lines
- Longer functions acceptable when logic is cohesive (e.g., `lookup_phase`)

**Parameters:**
- Use type hints for all parameters
- Default values for optional parameters
- Dictionary unpacking avoided - prefer explicit parameters

**Return Values:**
- Always specify return type
- Use dataclasses for complex return types
- Use dictionaries for simple key-value returns

**Example:**
```python
def _build_result(phase_id: str, T: float, P: float) -> dict:
    """Build result dictionary for a matched phase."""
    meta = PHASE_METADATA[phase_id]
    return {
        "phase_id": phase_id,
        "phase_name": meta["name"],
        "density": meta["density"],
        "temperature": T,
        "pressure": P,
    }
```

## Module Design

**Exports:**
- Define public API via `__all__` in `__init__.py`
- Import from submodules explicitly

**Barrel Files:**
- `__init__.py` files re-export public symbols
- Keep barrel files minimal - just imports and `__all__`

**Example from `quickice/structure_generation/__init__.py`:**
```python
"""Structure generation module for QuickIce."""

from quickice.structure_generation.errors import (
    StructureGenerationError,
    UnsupportedPhaseError,
)
from quickice.structure_generation.mapper import (
    PHASE_TO_GENICE,
    UNIT_CELL_MOLECULES,
    calculate_supercell,
    get_genice_lattice_name,
)
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.generator import (
    IceStructureGenerator,
    generate_candidates,
)

__all__ = [
    "Candidate",
    "GenerationResult",
    "StructureGenerationError",
    "UnsupportedPhaseError",
    "get_genice_lattice_name",
    "calculate_supercell",
    "IceStructureGenerator",
    "generate_candidates",
    "PHASE_TO_GENICE",
    "UNIT_CELL_MOLECULES",
]
```

---

*Convention analysis: 2026-03-30*