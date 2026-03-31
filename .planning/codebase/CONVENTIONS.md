# Coding Conventions

**Analysis Date:** 2026-03-31

## Naming Patterns

**Files:**
- Python modules use `snake_case.py` (e.g., `validator.py`, `phase_diagram.py`)
- Test files use `test_<module>.py` pattern (e.g., `test_validators.py`, `test_ranking.py`)
- Type definitions go in `types.py` within each module
- Error definitions go in `errors.py` within each module

**Functions:**
- Use `snake_case` for all function names
- Example: `lookup_phase()`, `generate_candidates()`, `write_pdb_with_cryst1()`
- Private helper functions prefixed with underscore: `_calculate_oo_distances_pbc()`, `_build_result()`, `_parse_gro()`

**Variables:**
- Use `snake_case` for local variables
- Single letters acceptable for mathematical/scientific context (e.g., `T` for temperature, `P` for pressure)
- Descriptive names for complex data: `phase_info`, `ranked_candidates`, `scoring_metadata`

**Types:**
- Use `PascalCase` for dataclasses and classes
- Example: `Candidate`, `GenerationResult`, `RankedCandidate`, `RankingResult`, `IcePhaseLookup`
- Module-level constants in `UPPER_SNAKE_CASE`: `IDEAL_OO_DISTANCE`, `OO_CUTOFF`, `TRIPLE_POINTS`, `PHASE_METADATA`

## Code Style

**Formatting:**
- No explicit linter configuration detected
- Follow PEP 8 conventions observed throughout
- Maximum line length approximately 88-100 characters
- Use double quotes for strings consistently

**Linting:**
- No `.eslintrc`, `.prettierrc`, or similar config files detected
- Project relies on Python conventions and code review

**Indentation:**
- 4 spaces for Python code
- Hanging indentation for function arguments when breaking lines

## Import Organization

**Order:**
1. Standard library imports (alphabetical)
2. Third-party imports (numpy, scipy, pytest, argparse, etc.)
3. Local imports from `quickice.*` modules

**Example from `quickice/structure_generation/generator.py`:**
```python
import numpy as np

from genice2.plugin import safe_import
from genice2.genice import GenIce

from quickice.structure_generation.mapper import (
    get_genice_lattice_name,
    calculate_supercell,
    UNIT_CELL_MOLECULES,
)
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.errors import StructureGenerationError
```

**Path Imports:**
- Use absolute imports from `quickice.*` for internal module references
- Example: `from quickice.ranking.types import RankedCandidate`

## Error Handling

**Custom Exceptions:**
- Define exceptions in dedicated `errors.py` files per module
- Use hierarchical exception classes with base class inheritance
- Example from `quickice/phase_mapping/errors.py`:
  ```python
  class PhaseMappingError(Exception):
      """Base exception for phase mapping failures."""
      def __init__(self, message: str, temperature: float = None, pressure: float = None):
          self.temperature = temperature
          self.pressure = pressure
          parts = [message]
          if temperature is not None and pressure is not None:
              parts.append(f"Given: T={temperature}K, P={pressure}MPa")
          super().__init__(" | ".join(parts))

  class UnknownPhaseError(PhaseMappingError):
      """Raised when T,P conditions fall outside all known phase regions."""
  ```

**Exception Chaining:**
- Use exception chaining with `from e` for wrapping exceptions
- Example from `quickice/structure_generation/generator.py`:
  ```python
  except Exception as e:
      raise StructureGenerationError(
          f"Failed to generate ice structure ({type(e).__name__}): {e}"
      ) from e
  ```

**Error Messages:**
- Include context values in error messages (temperature, pressure, phase_id)
- Use descriptive error types that indicate the category of failure
- CLI errors use `ArgumentTypeError` with parameter name included

## Logging

**Framework:** Standard `print()` statements for CLI output

**Patterns:**
- Progress information printed to stdout
- Errors printed to stderr using `print(..., file=sys.stderr)`
- No logging framework configured

**Example from `quickice/main.py`:**
```python
except UnknownPhaseError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

## Comments

**When to Comment:**
- Module-level docstrings explaining purpose and key concepts
- Function docstrings for all public functions (Google-style format)
- Complex algorithms with inline comments explaining physics/scientific context
- TODO comments for future work (none detected in current codebase)

**Docstrings:**
- Use Google-style docstrings with `Args:`, `Returns:`, `Raises:`, `Example:`, `Note:` sections
- Include type information in docstrings even with type hints
- Example from `quickice/phase_mapping/lookup.py`:
  ```python
  def lookup_phase(temperature: float, pressure: float) -> dict:
      """Determine ice phase using curve-based boundary evaluation.
      
      Args:
          temperature: Temperature in Kelvin
          pressure: Pressure in MPa
      
      Returns:
          Dict with phase_id, phase_name, density, temperature, pressure
      
      Raises:
          UnknownPhaseError: If no phase matches the given conditions
      """
  ```

**Inline Comments:**
- Use for explaining scientific/physics context
- Example: `# Ice X: P > x_boundary(T) where boundary varies from 30-62 GPa`
- Use for algorithmic decisions: `# Min-max normalization`

## Function Design

**Size:** Functions range from small (5-20 lines for helpers) to medium (50-100 lines for complex logic)

**Parameters:**
- Use type hints for all parameters
- Provide default values for optional parameters
- Use `Optional[T]` for nullable parameters
- Example: `def rank_candidates(candidates: list[Candidate], weights: dict[str, float] | None = None) -> RankingResult`

**Return Values:**
- Use dataclasses for complex return types
- Return dictionaries for simple key-value results
- Use tuples for internal helper functions
- Example from `quickice/structure_generation/generator.py`:
  ```python
  def _parse_gro(self, gro_string: str) -> tuple[np.ndarray, list[str], np.ndarray]:
      """Parse GRO format string to extract coordinates."""
  ```

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` to explicitly define public API
- Export types, main functions, errors, and constants separately
- Example from `quickice/ranking/__init__.py`:
  ```python
  from quickice.ranking.types import RankedCandidate, RankingResult
  from quickice.ranking.scorer import rank_candidates, energy_score, density_score

  __all__ = [
      "RankedCandidate",
      "RankingResult",
      "rank_candidates",
      "energy_score",
      "density_score",
  ]
  ```

**Barrel Files:**
- Each module directory has an `__init__.py` that exports the public API
- Module structure:
  - `types.py` - Dataclasses and type definitions
  - `errors.py` - Custom exceptions
  - Main module file (e.g., `scorer.py`, `generator.py`, `lookup.py`)
  - `__init__.py` - Public API exports

**Dataclasses:**
- Use `@dataclass` decorator for data containers
- Use `field(default_factory=dict)` for mutable default arguments
- Example from `quickice/structure_generation/types.py`:
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

## Type Hints

**Standard Practice:**
- Use modern Python type hint syntax (PEP 585): `list[str]` instead of `List[str]`
- Use `dict[str, Any]` instead of `Dict[str, Any]`
- Use `Optional[T]` or `T | None` for nullable types
- Import `Any` from `typing` module when needed

**Examples:**
```python
def validate_temperature(value: str) -> float:
def rank_candidates(candidates: list[Candidate], weights: dict[str, float] | None = None) -> RankingResult:
def _calculate_oo_distances_pbc(positions: np.ndarray, atom_names: list[str], cell: np.ndarray, cutoff: float) -> np.ndarray:
```

---

*Convention analysis: 2026-03-31*