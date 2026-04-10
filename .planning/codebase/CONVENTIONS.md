# Coding Conventions

**Analysis Date:** 2026-04-11

## Naming Patterns

**Files:**
- Module files use `snake_case.py`: `interface_builder.py`, `water_filler.py`, `phase_diagram.py`, `pdb_writer.py`, `overlap_resolver.py`
- Test files use `test_` prefix: `test_validators.py`, `test_ranking.py`, `test_phase_mapping.py`
- Test subdirectories mirror source structure: `tests/test_output/test_pdb_writer.py`
- Submodule directories use `snake_case`: `structure_generation/`, `phase_mapping/`, `output/`
- Data files use lowercase: `tip4p.gro`, `ice_phases.json`
- Type/data modules named `types.py`, error modules named `errors.py` — consistent across all subpackages

**Functions:**
- Public API functions use `snake_case`: `lookup_phase()`, `generate_candidates()`, `rank_candidates()`
- Private/internal functions use `_snake_case` prefix: `_calculate_oo_distances_pbc()`, `_calculate_cell_parameters()`, `_generate_single()`, `_parse_gro()`
- Validation functions use `validate_` prefix: `validate_temperature()`, `validate_pressure()`, `validate_nmolecules()`, `validate_interface_config()`
- Factory/class methods use `from_` prefix: `InterfaceConfig.from_dict()`
- Unit conversion helpers use descriptive `x_to_y` naming: `angstrom_to_nm()`, `nm_to_angstrom()`

**Variables:**
- Constants use `UPPER_SNAKE_CASE`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `MINIMUM_BOX_DIMENSION`, `AVOGADRO`, `WATER_MASS`
- Regular variables use `snake_case`: `phase_info`, `nmolecules`, `scoring_metadata`, `actual_nmolecules`
- Boolean variables use `is_`/`was_` prefixes: `was_rounded`, `is_cell_orthogonal()`, `_generating`, `_vtk_available`
- Physical constants documented with units in comments: `AVOGADRO = 6.022e23  # molecules/mol`, `WATER_MASS = 18.01528  # g/mol`

**Types:**
- All classes and dataclasses use `PascalCase`: `Candidate`, `GenerationResult`, `InterfaceConfig`, `RankedCandidate`, `IceStructureGenerator`
- Exception classes use `Error` suffix and follow hierarchy: `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`; `PhaseMappingError` → `UnknownPhaseError`
- Exception classes carry contextual attributes: `UnsupportedPhaseError.phase_id`, `InterfaceGenerationError.mode`, `PhaseMappingError.temperature`, `PhaseMappingError.pressure`

## Code Style

**Formatting:**
- No formal formatter or linter configuration detected (no `pyproject.toml`, `.editorconfig`, `setup.cfg`, `flake8`, `black`, `ruff` config)
- Indentation: 4 spaces (standard Python)
- Line length: Generally under 100 characters; docstrings occasionally longer
- String quotes: Single quotes for short strings, double quotes for docstrings and f-strings
- Always use f-strings for string formatting (not `.format()` or `%`)
- Trailing newlines at end of files

**Key Style Rules Observed:**
- Use `np.array()` for NumPy array creation
- Use `Path` from `pathlib` for file operations, not `os.path`
- Use `math.ceil()` for ceiling operations
- Use `@dataclass` for structured data with `field(default_factory=dict)` for mutable defaults
- Unit annotations in parameter names where ambiguity exists: `threshold_nm`, `box_dims_nm`, `value_angstrom`
- Physical constants documented with units in inline comments: `# g/cm³`, `# nm`, `# molecules/mol`
- Scientific references in comments: `# IAPWS R14-08(2011)`, `# Journaux et al. (2019, 2020)`

**Type Hints:**
- Use modern Python 3.10+ union syntax: `int | None` not `Optional[int]`, `list[str]` not `List[str]`, `dict[str, Any]` not `Dict[str, Any]`
- Some older files still use `from typing import Optional, List` — newer code uses the modern syntax
- Return types annotated on all public functions: `-> int`, `-> float`, `-> tuple[np.ndarray, int]`, `-> GenerationResult`
- Parameter types always annotated in public APIs
- Example from `quickice/structure_generation/generator.py`:
  ```python
  def generate_all(self, n_candidates: int = 10, base_seed: int | None = None) -> list[Candidate]:
  ```

## Import Organization

**Order:**
1. Standard library: `import argparse`, `import math`, `import time`, `import sys`, `from pathlib import Path`
2. Third-party: `import numpy as np`, `import pytest`, `from scipy.spatial import cKDTree`, `from PySide6.QtWidgets import ...`
3. Local imports: `from quickice.structure_generation.types import Candidate`

**Pattern:**
```python
# Standard library
import sys
from pathlib import Path
from argparse import ArgumentTypeError

# Third-party
import numpy as np
from scipy.spatial import cKDTree

# Local imports
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.errors import StructureGenerationError
```

**Path Aliases:**
- No import aliases for project modules (no `import quickice.structure_generation as sg`)
- `numpy` always imported as `np` — universal convention
- Module-level imports from subpackages go through `__init__.py`

**Special Import Patterns:**
- Late/optional imports for GUI dependencies wrapped in try/except: VTK and PySide6 imports in `quickice/gui/interface_panel.py`
- Conditional VTK availability check at module level:
  ```python
  _VTK_AVAILABLE = False
  try:
      if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
          _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
      else:
          _VTK_AVAILABLE = True
      if _VTK_AVAILABLE:
          from quickice.gui.interface_viewer import InterfaceViewerWidget
  except Exception:
      _VTK_AVAILABLE = False
  ```

## Error Handling

**Custom Exception Hierarchy:**
- Domain base exceptions inherit from `Exception`:
  - `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`
  - `PhaseMappingError` → `UnknownPhaseError`
- Each exception carries contextual attributes for debugging:
  - `UnsupportedPhaseError(phase_id="ice_xxx")`
  - `InterfaceGenerationError(mode="slab")`
  - `PhaseMappingError(temperature=273, pressure=0)`

**Exception Raising Patterns:**
- Wrap third-party exceptions with domain errors using `from e`:
  ```python
  except Exception as e:
      raise StructureGenerationError(
          f"Failed to generate ice structure ({type(e).__name__}): {e}"
      ) from e
  ```
- Re-raise domain exceptions without wrapping:
  ```python
  except InterfaceGenerationError:
      raise
  ```
- CLI validators raise `ArgumentTypeError`:
  ```python
  raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")
  ```
- Dataclass `__post_init__` for structural validation:
  ```python
  def __post_init__(self):
      if not (0.1 <= self.overlap_threshold <= 1.0):
          raise ValueError(f"overlap_threshold={self.overlap_threshold} nm is outside reasonable range...")
  ```

**Error Messages:**
- Include specific values that caused the error: `f"Box Z ({config.box_z:.2f} nm) must equal 2×ice + water = {expected_z:.2f} nm"`
- Provide "How to fix" guidance with specific remediation steps (especially in `quickice/structure_generation/interface_builder.py`)
- Include unit information to catch mismatches: `f"overlap_threshold={self.overlap_threshold} nm is outside reasonable range [0.1, 1.0] nm"`
- Build detailed messages with multiple parts: `PhaseMappingError.__init__` joins message with context using `" | ".join(parts)`

**CLI Error Handling:**
- `main()` catches `UnknownPhaseError` separately, then general `Exception`
- `SystemExit` re-raised (argparse calls `sys.exit` on `--help`/`--version`)
- Exit codes: 0 for success, 1 for error
- Errors printed to stderr: `print(f"Error: {e}", file=sys.stderr)`

**GUI Validation Pattern:**
- GUI validators return `(valid: bool, error_message: str)` tuples — they do NOT raise exceptions
- Used by `InterfacePanel.validate_configuration()` to show inline error labels
- Example from `quickice/gui/validators.py`:
  ```python
  def validate_box_dimension(value: str) -> tuple[bool, str]:
      """Returns (valid, error_message)."""
  ```

## Logging

**Framework:** Python `logging` module (standard library) + Qt signals for GUI

**Patterns:**
- Used in `quickice/output/orchestrator.py` with `logging.warning()`: `logging.warning(f"Failed to write PDB for rank {rank}: {e}")`
- CLI output via `print()` in `quickice/main.py`: structured tabular output with separators
- GUI logging via `InfoPanel.append_log()` and Qt Signal-based status updates in `quickice/gui/interface_panel.py`
- No custom logger configuration; relies on default Python logging

**When to Log:**
- Non-fatal failures during output writing (PDB generation, phase diagram)
- Validation failures that are recovered from
- Not used for normal flow; exceptions handle error cases
- CLI uses `print()` for all user-facing output (not `logging`)

## Comments

**When to Comment:**
- Every module has a module-level docstring explaining its purpose
- Every public function and class has a Google-style docstring
- Inline comments for physical unit notes: `# nm`, `# g/cm³`, `# Angstrom`
- Inline comments for non-obvious algorithm decisions: `# GenIce uses np.random internally (see genice2/genice.py lines 58, 816, 1072)`
- Scientific references documented: `# IAPWS R14-08(2011)`, `# Journaux et al. (2019, 2020)`
- CRITICAL/IMPORTANT markers for non-obvious constraints: `# CRITICAL: boxsize handles periodic boundaries automatically`

**Docstring Format — Google-style throughout:**
```python
def generate_candidates(
    phase_info: dict,
    nmolecules: int,
    n_candidates: int = 10,
    base_seed: int | None = None,
) -> GenerationResult:
    """Generate multiple ice structure candidates.

    This is a convenience function that creates a generator instance
    and returns results in a single call.

    Args:
        phase_info: Dict from lookup_phase() containing phase_id, density, etc.
        nmolecules: Target number of water molecules
        n_candidates: Number of candidates to generate (default 10)
        base_seed: Base seed for random number generation. If None, uses
            current time for automatic diversity. Specify a seed for reproducibility.

    Returns:
        GenerationResult with list of candidates and metadata

    Raises:
        UnsupportedPhaseError: If phase not supported by GenIce
        StructureGenerationError: If GenIce fails to generate

    Example:
        >>> from quickice.phase_mapping import lookup_phase
        >>> phase_info = lookup_phase(273, 0)  # Ice Ih
        >>> result = generate_candidates(phase_info, nmolecules=100)
    """
```

- Class docstrings include `Attributes:` section listing all fields with descriptions
- Use `Note:` sections for important caveats (thread safety, unit conventions, algorithm limitations)
- Use `Example:` sections for public convenience functions

## Function Design

**Size:** Functions typically 10-40 lines. Long functions like `lookup_phase()` (~300 lines) are exceptions handling complex multi-branch logic.

**Parameters:**
- Use `config` objects (dataclasses) for multi-parameter functions: `ScoringConfig`, `InterfaceConfig`
- Provide sensible defaults: `n_candidates: int = 10`, `base_seed: int | None = None`, `cutoff: float = 0.35`
- Accept `None` with documented default behavior: `base_seed: int | None = None` → uses `time.time_ns()`
- Unit conversion helpers accept value with unit in name: `angstrom_to_nm(value_angstrom: float)`

**Return Values:**
- Use dataclasses for complex multi-value returns: `GenerationResult`, `RankingResult`, `InterfaceStructure`, `OutputResult`
- Use tuples for simple multi-value returns: `calculate_supercell()` returns `tuple[np.ndarray, int]`
- Use dicts for flexible legacy results: `lookup_phase()` returns `dict` with keys `phase_id`, `phase_name`, `density`, `temperature`, `pressure`
- Return lists for collections: `list[Candidate]`, `list[str]` (output file paths)
- Functions that can fail: return typed result on success, raise exception on failure (no None returns, no sentinel values)

## Module Design

**Exports:**
- Every `__init__.py` defines `__all__` with explicit export list
- Re-export public API from subpackage `__init__.py`: `quickice/structure_generation/__init__.py` exports types, errors, functions, and constants
- Internal modules (private functions, internal helpers) not listed in `__all__`
- External code imports from the package, not internal modules: `from quickice.ranking import rank_candidates`

**Barrel Files:**
- `__init__.py` files serve as barrel files aggregating subpackage API
- Example from `quickice/structure_generation/__init__.py`:
  ```python
  from quickice.structure_generation.types import (Candidate, GenerationResult, ...)
  from quickice.structure_generation.errors import (StructureGenerationError, ...)
  from quickice.structure_generation.mapper import (PHASE_TO_GENICE, ...)
  __all__ = ["Candidate", "GenerationResult", ...]
  ```

**Data Model Convention:**
- Use `@dataclass` for all structured data types (not TypedDict or plain dicts)
- All dataclasses in dedicated `types.py` files within each subpackage: `quickice/structure_generation/types.py`, `quickice/ranking/types.py`, `quickice/output/types.py`
- Use `field(default_factory=dict)` for mutable defaults (never `{}` as default arg)
- `__post_init__` for validation: `InterfaceConfig.__post_init__()` validates `overlap_threshold` range
- Class methods for alternative construction: `InterfaceConfig.from_dict()`
- Nested dataclass references: `RankedCandidate.candidate: Candidate`

**Dict vs Dataclass Convention:**
- Phase mapping returns dicts (legacy design): `lookup_phase()` returns `dict[str, Any]`
- Structure generation uses dataclasses (modern design): `Candidate`, `GenerationResult`
- Ranking uses dataclasses: `RankedCandidate`, `RankingResult`, `ScoringConfig`
- Output uses dataclasses: `OutputResult`

**Unit Convention:**
- All internal coordinates in **nanometers (nm)** — documented in docstrings
- Cell vectors stored as row vectors in `(3, 3)` arrays (each row is a lattice vector)
- Position convention: `new_position = position @ cell` (row vectors)
- Conversion to Angstrom done at export time (multiply by 10.0) in `quickice/output/pdb_writer.py`
- `overlap_threshold` parameter uses nm with range validation in `InterfaceConfig.__post_init__()`
- Parameter names include unit suffix where ambiguity exists: `threshold_nm`, `box_dims_nm`, `value_angstrom`
- Physical constants documented with units: `AVOGADRO = 6.022e23  # molecules/mol`, `WATER_MASS = 18.01528  # g/mol`

---

*Convention analysis: 2026-04-11*
