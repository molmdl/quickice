# Coding Conventions

**Analysis Date:** 2026-05-12

## Naming Patterns

**Files:**
- Python modules use `snake_case.py` (e.g., `interface_builder.py`, `solute_inserter.py`)
- Test files use `test_<module>.py` pattern (e.g., `test_validators.py`, `test_phase_mapping.py`)
- GUI modules are in `quickice/gui/` with descriptive names (`solute_panel.py`, `main_window.py`)

**Functions:**
- Use `snake_case` for all function names
- Validator functions prefixed with `validate_` (e.g., `validate_temperature`, `validate_pressure`)
- Private methods prefixed with single underscore (e.g., `_generate_single`, `_parse_gro`)
- Factory methods use `from_` prefix (e.g., `from_dict`, `from_lattice_type`)

**Variables:**
- Use `snake_case` for local and module-level variables
- Constants use `UPPER_SNAKE_CASE` (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `MINIMUM_BOX_DIMENSION`)
- Loop indices use single letters or descriptive names (`i`, `idx`)

**Types:**
- Dataclasses use `PascalCase` (e.g., `Candidate`, `InterfaceConfig`, `HydrateStructure`)
- Exception classes use `PascalCase` with `Error` suffix (e.g., `UnknownPhaseError`, `UnsupportedPhaseError`)
- Type aliases use `PascalCase` (e.g., `MoleculeIndex`)

## Code Style

**Formatting:**
- No explicit formatting tool detected (no .prettierrc, black config, etc.)
- 4-space indentation throughout
- Max line length appears to be ~100 characters
- Double quotes for strings in most files

**Linting:**
- No linting configuration files detected
- Code follows PEP 8 conventions organically

**Type Hints:**
- Type hints used throughout the codebase
- Import from `typing` module: `from typing import Any, Optional`
- Modern union syntax used: `int | None` (Python 3.10+)
- Example from `quickice/structure_generation/types.py`:
  ```python
  def to_candidate(self) -> Candidate:
      """Convert hydrate structure to ice Candidate."""
  
  positions: np.ndarray
  atom_names: list[str]  # Modern syntax, not List[str]
  metadata: dict[str, Any] = field(default_factory=dict)
  ```

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (numpy, pytest)
3. Local application imports

**Example from `quickice/structure_generation/generator.py`:**
```python
import time  # Standard library

import numpy as np  # Third-party

from genice2.plugin import safe_import  # Third-party
from genice2.genice import GenIce

from quickice.structure_generation.mapper import (...)  # Local
from quickice.structure_generation.types import Candidate, GenerationResult
```

**Path Aliases:**
- Imports use full module path: `from quickice.structure_generation.types import Candidate`
- No path aliases configured (no `from ..types import`)

## Error Handling

**Custom Exceptions:**
- Hierarchical exception classes with base exception
- Example from `quickice/structure_generation/errors.py`:
  ```python
  class StructureGenerationError(Exception):
      """Base error for structure generation."""
      pass

  class UnsupportedPhaseError(StructureGenerationError):
      """Phase not supported by GenIce."""
      def __init__(self, message: str, phase_id: str):
          super().__init__(message)
          self.phase_id = phase_id

  class InterfaceGenerationError(StructureGenerationError):
      """Error during interface structure generation."""
      def __init__(self, message: str, mode: str):
          full_message = f"[{mode}] {message}"
          super().__init__(full_message)
          self.mode = mode
  ```

**Error Context:**
- Errors include relevant context in message
- Example from `quickice/phase_mapping/errors.py`:
  ```python
  class UnknownPhaseError(PhaseMappingError):
      def __init__(self, message: str = "No ice phase found", 
                   temperature: float = None, pressure: float = None):
          hint = "Conditions may be outside supported phase diagram regions."
          full_message = f"{message}. {hint}"
          super().__init__(full_message, temperature, pressure)
  ```

**Validation Errors:**
- Use `ArgumentTypeError` for CLI validation
- Example from `quickice/validation/validators.py`:
  ```python
  def validate_temperature(value: str) -> float:
      try:
          temp = float(value)
      except ValueError:
          raise ArgumentTypeError(f"Temperature must be a number, got '{value}'")
      
      if temp < 0 or temp > 500:
          raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")
      
      return temp
  ```

## Logging

**Framework:** Python standard library `logging`

**Pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Usage:**
- `logger.info()` for significant events (registration, initialization)
- `logger.warning()` for fallback behavior, out-of-range values
- `logger.debug()` for detailed diagnostic information

**Example from `quickice/structure_generation/moleculetype_registry.py`:**
```python
logger.info(f"Registered hydrate guest: {molecule} → {registered_name}")
logger.debug(f"Hydrate guest {molecule} already registered as {registered_name}")
```

## Comments

**When to Comment:**
- Module-level docstrings explain purpose and context
- Class docstrings document attributes and usage
- Method docstrings use Google-style with Args, Returns, Raises
- Inline comments for non-obvious logic

**JSDoc/TSDoc Equivalent (Python Docstrings):**
- Google-style docstrings used throughout
- Example from `quickice/structure_generation/generator.py`:
  ```python
  def _generate_single(self, seed: int) -> Candidate:
      '''Generate a single ice structure candidate.

      Args:
          seed: Random seed for hydrogen bond network diversity

      Returns:
          Candidate with generated coordinates and metadata

      Raises:
          StructureGenerationError: If GenIce fails to generate

      Note:
          GenIce internally uses the global np.random state (not the newer
          Generator API). We save and restore the global state around each
          generation call to minimize side effects on external code.
      '''
  ```

## Function Design

**Size:** Functions generally under 50 lines; complex operations split into helper methods

**Parameters:**
- Use dataclasses for complex configurations
- Optional parameters use `Optional` type hint with `None` default
- Example from `quickice/structure_generation/types.py`:
  ```python
  @dataclass
  class HydrateConfig:
      lattice_type: str = "sI"
      guest_type: str = "ch4"
      cage_occupancy_small: float = 100.0
      cage_occupancy_large: float = 100.0
      supercell_x: int = 1
      supercell_y: int = 1
      supercell_z: int = 1
  ```

**Return Values:**
- Return dataclasses/typed objects, not raw dictionaries
- Use result objects for complex return data (e.g., `GenerationResult`, `RankingResult`)

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` files for explicit public API
- Example from `quickice/structure_generation/__init__.py`:
  ```python
  __all__ = [
      # Types
      "Candidate",
      "GenerationResult",
      "InterfaceConfig",
      # Errors
      "StructureGenerationError",
      "UnsupportedPhaseError",
      # Generator
      "IceStructureGenerator",
      "generate_candidates",
  ]
  ```

**Barrel Files:**
- Each module has `__init__.py` that exports key classes/functions
- Sub-modules imported explicitly: `from quickice.structure_generation.types import Candidate`

## Dataclasses

**Pattern:**
- Heavy use of `@dataclass` decorator for structured data
- Use `field(default_factory=dict)` for mutable defaults
- Validation in `__post_init__` method
- Example from `quickice/structure_generation/types.py`:
  ```python
  @dataclass
  class InterfaceConfig:
      mode: str
      box_x: float
      box_y: float
      box_z: float
      seed: int
      ice_thickness: float = 0.0
      overlap_threshold: float = 0.25

      def __post_init__(self):
          """Validate configuration parameters after initialization."""
          if not (0.1 <= self.overlap_threshold <= 1.0):
              raise ValueError(f"overlap_threshold={self.overlap_threshold} nm is outside range")

      @classmethod
      def from_dict(cls, d: dict) -> "InterfaceConfig":
          """Create InterfaceConfig from dictionary."""
          return cls(
              mode=d["mode"],
              box_x=d["box_x"],
              # ...
          )
  ```

## Constants

**Module-Level Constants:**
- Define at top of module after imports
- Use dictionaries for lookup tables
- Example from `quickice/structure_generation/types.py`:
  ```python
  MOLECULE_TYPE_INFO: dict[str, dict[str, Any]] = {
      "ice":   {"atoms": 3, "res_name": "SOL", "description": "Ice (TIP3P)"},
      "water": {"atoms": 4, "res_name": "SOL", "description": "Water (TIP4P-ICE)"},
      "na":    {"atoms": 1, "res_name": "NA",  "description": "Sodium ion"},
  }
  ```

---

*Convention analysis: 2026-05-12*
