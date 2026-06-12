# Coding Conventions

**Analysis Date:** 2026-06-12

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `gromacs_writer.py`, `ion_inserter.py`, `phase_diagram_widget.py`
- Test files use `test_` prefix: `test_structure_generation.py`, `test_e2e_ice_generation.py`
- E2E test files use `test_e2e_` prefix: `test_e2e_workflow_chains.py`, `test_e2e_gmx_validation.py`
- Regression test files reference bug IDs: `test_scancode_bugs_gromacs.py`
- Shared non-test helpers in tests/ use NO `test_` prefix: `e2e_export_helpers.py`
- Subdirectory test packages use `__init__.py`: `tests/test_output/__init__.py`

**Classes:**
- Use `PascalCase` for all classes: `IceStructureGenerator`, `InterfaceConfig`, `HydrateGROMACSExporter`
- Data classes use descriptive noun names: `Candidate`, `GenerationResult`, `InterfaceStructure`
- Test classes use `Test` prefix + descriptive name: `TestLookupPhaseIceIh`, `TestBUG05`
- Exception classes use `Error` suffix: `StructureGenerationError`, `UnknownPhaseError`, `InterfaceGenerationError`
- GUI widget classes use descriptive noun + role: `MainWindow`, `PhaseDiagramPanel`, `SolutePanel`
- GUI worker classes use `Worker` suffix: `GenerationWorker`, `HydrateWorker`, `CustomMoleculeWorker`
- GUI exporter classes use `Exporter` suffix: `GROMACSExporter`, `PDBExporter`, `IonGROMACSExporter`
- Enum classes use `PascalCase`: `TabIndex(IntEnum)`

**Functions:**
- Use `snake_case` for all functions: `lookup_phase()`, `generate_interface()`, `calculate_supercell()`
- Private helper methods use `_` prefix: `_generate_single()`, `_is_orthorhombic()`, `_calculate_oo_distances_pbc()`
- Boolean predicate functions use `_is_` prefix: `_is_orthorhombic()`, `is_cell_orthogonal()`
- Factory class methods use `from_` prefix: `InterfaceConfig.from_dict()`, `HydrateConfig.from_dict()`, `HydrateLatticeInfo.from_lattice_type()`
- Validation functions use `validate_` prefix: `validate_temperature()`, `validate_pressure()`, `validate_nmolecules()`
- Writer functions use `write_` prefix: `write_gro_file()`, `write_top_file()`, `write_interface_gro_file()`

**Variables:**
- Use `snake_case` for all local variables and module-level constants
- Module-level constants use `UPPER_SNAKE_CASE`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `MINIMUM_BOX_DIMENSION`, `HYDRATE_LATTICES`
- Private instance attributes use `_` prefix: `self._viewmodel`, `self._current_interface_result`
- Dictionaries mapping identifiers use descriptive names: `MOLECULE_TO_GROMACS`, `GUEST_MOLECULES`, `PHASE_CONDITIONS`

**Types:**
- Use Python 3.10+ union syntax `X | None` for optional types: `seed: int | None = None`
- Use `list[X]` and `dict[X, Y]` (lowercase) for generic types, NOT `List[X]` or `Dict[X, Y]`
- Legacy `typing` imports exist in older files but new code should use built-in generics
- Type hints on `Any` for circular-import avoidance: `registry: Any = None  # MoleculetypeRegistry`
- Use `TYPE_CHECKING` for import-time type checking to avoid circular imports:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from quickice.structure_generation.types import CustomMoleculeStructure
  ```

## Code Style

**Formatting:**
- No project-level formatter config (no `.flake8`, `.prettierrc`, `ruff.toml`, or `black` config found)
- Indentation: 4 spaces
- Max line length: ~100-120 characters (not strictly enforced)
- Trailing newlines in all files

**Linting:**
- No linter config found (no `.eslintrc`, `setup.cfg`, or `ruff.toml`)
- No CI-enforced lint checks
- Code quality maintained through testing discipline, not automated linting

**String Quotes:**
- Both single and double quotes used inconsistently across the codebase
- Some files (e.g., `quickice/structure_generation/generator.py`) use triple single quotes `'''` for module/class docstrings
- Most files use triple double quotes `"""` for docstrings (preferred pattern)
- Use `"""` for docstrings, `"` or `'` for string literals (be consistent within a file)

## Import Organization

**Order:**
1. Standard library imports (`import sys`, `import logging`, `from pathlib import Path`)
2. Third-party imports (`import numpy as np`, `import pytest`, `from PySide6.QtWidgets import ...`)
3. Local application imports (`from quickice.structure_generation.types import ...`)

**Pattern:**
```python
# Standard library
import logging
from pathlib import Path
from typing import Any, Optional

# Third-party
import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import Signal, QThread

# Local application
from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.phase_mapping.lookup import lookup_phase
```

**Path Aliases:**
- No custom import aliases or `sys.path` modifications in source code
- Test files sometimes add `sys.path.insert(0, ...)` for test helper imports:
  ```python
  sys.path.insert(0, str(Path(__file__).parent))
  from e2e_export_helpers import parse_top_includes, run_gmx_grompp
  ```

**Relative vs Absolute Imports:**
- Use ABSOLUTE imports exclusively: `from quickice.structure_generation.types import Candidate`
- NEVER use relative imports like `from .types import Candidate`
- This is consistent across all modules

## Error Handling

**Custom Exception Hierarchy:**
- Base exception per subsystem with specific children:
  - `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError` in `quickice/structure_generation/errors.py`
  - `PhaseMappingError` → `UnknownPhaseError` in `quickice/phase_mapping/errors.py`
- Exceptions carry context attributes: `UnsupportedPhaseError.phase_id`, `InterfaceGenerationError.mode`
- Error messages include physical context and guidance:
  ```python
  raise InterfaceGenerationError(
      f"Box X dimension ({config.box_x:.3f} nm) is too small. "
      f"Minimum is {MINIMUM_BOX_DIMENSION:.1f} nm. "
      f"Water molecules have diameter ~0.28 nm; boxes smaller than 1.0 nm "
      f"cause numerical issues and cannot fit realistic structures.",
      mode=config.mode
  )
  ```

**Validation Pattern:**
- CLI validators raise `ArgumentTypeError` with descriptive messages in `quickice/validation/validators.py`
- GUI validators return `tuple[bool, str]` with `(is_valid, error_message)` in `quickice/gui/validators.py`
- Dataclass `__post_init__` validates config parameters:
  ```python
  def __post_init__(self):
      if self.lattice_type not in HYDRATE_LATTICES:
          raise ValueError(f"Unknown lattice type: {self.lattice_type}")
  ```
- Validation ranges include rationale in error messages (units, typical values)

**Exception Wrapping:**
- Wrap third-party exceptions with context:
  ```python
  except Exception as e:
      raise StructureGenerationError(
          f'Failed to generate ice structure ({type(e).__name__}): {e}'
      ) from e
  ```

**CLI Error Handling:**
- Top-level `main()` catches specific exceptions first, then generic:
  ```python
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

## Logging

**Framework:** Python `logging` module

**Pattern:**
- Use `logger = logging.getLogger(__name__)` at module level
- Found in ~20 source modules, primarily GUI and output modules:
  - `quickice/gui/main_window.py`, `quickice/gui/export.py`, `quickice/gui/ion_panel.py`
  - `quickice/output/gromacs_writer.py`, `quickice/structure_generation/solute_inserter.py`
- Non-GUI computation modules (`types.py`, `scorer.py`, `validators.py`) do NOT log
- No central logging configuration found — relies on Python defaults

**When to Log:**
- GUI worker lifecycle: thread start, completion, cancellation, errors
- Export operations: file path selection, write success/failure
- Computation milestones: generation progress, insertion counts
- NOT for routine validation failures (those raise exceptions)

## Comments

**When to Comment:**
- Module docstrings on ALL source files (triple-double-quoted `"""`)
- Class docstrings with `Attributes:` sections for dataclasses
- Method docstrings with `Args:`, `Returns:`, `Raises:` sections
- Inline comments for non-obvious physical constants or GROMACS-specific formatting
- `# ──` separator lines for section headers in longer files
- `Note:` paragraphs for important caveats (thread safety, backward compatibility)

**Docstring Style:**
- Google-style with `Args:`, `Returns:`, `Raises:`, `Attributes:`, `Example:` sections
- Full docstrings on all public classes and functions
- Private methods (`_method`) also get docstrings
- Test class docstrings explain what the class tests and why:
  ```python
  class TestBUG05:
      """Regression tests for BUG-05: HW1 Z-coordinate uses h2_pos[2] instead of h1_pos[2].
      
      Before the fix, write_custom_molecule_gro_file() output HW1 Z as h2_pos[2]...
      """
  ```

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Use Python docstrings with Google-style sections instead

## Function Design

**Size:** Most functions are 20-60 lines. Longer functions (up to ~100 lines) exist in writer code that formats GRO/TOP files line-by-line.

**Parameters:**
- Use typed parameters with default values where appropriate
- Config objects (`InterfaceConfig`, `HydrateConfig`, `SoluteConfig`, `CustomMoleculeConfig`) group related parameters
- Use `__post_init__` validation on config dataclasses for fail-fast behavior
- CLI argument validators double as type converters

**Return Values:**
- Use result dataclasses for multi-value returns: `GenerationResult`, `RankingResult`, `PlacementValidationResult`
- Boolean functions return `True`/`False` explicitly (not truthy/falsy)
- Export functions return `bool` for success/failure
- CLI `main()` returns integer exit code

## Module Design

**Exports:**
- Each package has `__init__.py` with explicit `__all__` list
- `quickice/structure_generation/__init__.py` re-exports types, errors, generator, builder, and utility functions
- `quickice/phase_mapping/__init__.py` re-exports lookup, errors, and data functions
- Import from package level when multiple items needed: `from quickice.structure_generation import generate_candidates`
- Import from module level for single items: `from quickice.structure_generation.types import Candidate`

**Barrel Files:**
- All packages use barrel `__init__.py` with `__all__`
- Pattern: import specific items, list in `__all__`, enable clean imports from package root
- Example from `quickice/structure_generation/__init__.py`:
  ```python
  from quickice.structure_generation.errors import (
      StructureGenerationError,
      UnsupportedPhaseError,
      InterfaceGenerationError,
  )
  __all__ = [
      "StructureGenerationError",
      "UnsupportedPhaseError",
      ...
  ]
  ```

**Data Files:**
- Molecular topology files (`.itp`, `.gro`) live in `quickice/data/` and `quickice/data/custom/`
- Access via `Path(quickice.__file__).parent / "data"` pattern
- Test MDP file: `tests/em.mdp`

## Dataclass Conventions

- Use `@dataclass` for all structured data types (no raw dicts for domain objects)
- Default values use `field(default_factory=...)` for mutable defaults: `metadata: dict[str, Any] = field(default_factory=dict)`
- Use `__post_init__` for validation that raises `ValueError` on invalid input
- Use `@classmethod` factory methods: `from_dict()`, `from_lattice_type()`
- Store numpy arrays as `np.ndarray` with shape documented in docstring
- Use `Any` type with inline comment to avoid circular imports: `registry: Any = None  # MoleculetypeRegistry`

## GUI Architecture Conventions

- Follow MVVM pattern: `MainWindow` (View) → `MainViewModel` (ViewModel) → Workers (Model)
- Worker pattern: `QObject` subclass with `run()` method, moved to `QThread` via `moveToThread()`
- Signal/Slot communication between layers
- Never import GUI modules (`PySide6`) in computation modules (`structure_generation`, `phase_mapping`, `ranking`, `output`)
- GUI validators return `tuple[bool, str]`; CLI validators raise `ArgumentTypeError`
- Export classes handle `QFileDialog`/`QMessageBox` interaction and delegate to writer functions
- Tab indices defined in `quickice/gui/constants.py` as `IntEnum`

## Unit Conventions

- All distances in **nanometers (nm)** throughout the codebase
- Temperatures in **Kelvin (K)**
- Pressures in **MPa** (megapascals)
- Density in **g/cm³**
- Concentration in **mol/L (M)**
- Conversion helpers exist in `quickice/structure_generation/overlap_resolver.py`: `angstrom_to_nm()`, `nm_to_angstrom()`
- Validation ranges include nm rationale (e.g., "0.25 nm = 2.5 Å")

---

*Convention analysis: 2026-06-12*
