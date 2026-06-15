# Coding Conventions

**Analysis Date:** 2026-06-15

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `gromacs_writer.py`, `ion_inserter.py`, `phase_diagram_widget.py`
- Test files use `test_` prefix: `test_structure_generation.py`, `test_e2e_ice_generation.py`
- E2E test files use `test_e2e_` prefix: `test_e2e_workflow_chains.py`, `test_e2e_gmx_validation.py`
- CLI integration test files: `test_cli_integration.py`, `test_cli_pipeline.py`
- Regression test files reference bug IDs: `test_scancode_bugs_gromacs.py`
- Shared non-test helpers in tests/ use NO `test_` prefix: `e2e_export_helpers.py`
- Subdirectory test packages use `__init__.py`: `tests/test_output/__init__.py`
- Bash scripts in `scripts/` use `snake_case.sh`: `cli-examples.sh`, `hydrate-interface-custom-ion.sh`

**Classes:**
- Use `PascalCase` for all classes: `IceStructureGenerator`, `InterfaceConfig`, `HydrateGROMACSExporter`
- Data classes use descriptive noun names: `Candidate`, `GenerationResult`, `InterfaceStructure`
- Pipeline classes use `{Feature}Pipeline` pattern: `CLIPipeline`
- Test classes use `Test` prefix + descriptive name: `TestLookupPhaseIceIh`, `TestBUG05`, `TestPipelineFlagValidation`
- Exception classes use `Error` suffix: `StructureGenerationError`, `UnknownPhaseError`, `InterfaceGenerationError`
- GUI widget classes use descriptive noun + role: `MainWindow`, `PhaseDiagramPanel`, `SolutePanel`
- GUI worker classes use `Worker` suffix: `GenerationWorker`, `HydrateWorker`, `CustomMoleculeWorker`
- GUI exporter classes use `Exporter` suffix: `GROMACSExporter`, `PDBExporter`, `IonGROMACSExporter`
- Enum classes use `PascalCase`: `TabIndex(IntEnum)`

**Functions:**
- Use `snake_case` for all functions: `lookup_phase()`, `generate_interface()`, `calculate_supercell()`
- Private helper methods use `_` prefix: `_generate_single()`, `_is_orthorhombic()`, `_calculate_oo_distances_pbc()`
- Private parsing helpers use `_parse_` prefix: `_parse_positions_csv()` in `quickice/cli/pipeline.py`
- Boolean predicate functions use `_is_` or `_has_` prefix: `_is_orthorhombic()`, `_is_pyside6_available()`, `_has_display()`, `_has_pipeline_flags()` in `quickice/entry.py`
- Factory class methods use `from_` prefix: `InterfaceConfig.from_dict()`, `HydrateConfig.from_dict()`, `HydrateLatticeInfo.from_lattice_type()`
- Validation functions use `validate_` prefix: `validate_temperature()`, `validate_pressure()`, `validate_nmolecules()`, `validate_pipeline_args()`
- Writer functions use `write_` prefix: `write_gro_file()`, `write_top_file()`, `write_interface_gro_file()`
- Progress reporting function: `report_progress()` — uses `[PROGRESS]` prefix on stderr
- CLI pipeline step methods use `_run_` prefix: `_run_source_step()`, `_run_interface_step()`, `_run_custom_step()`, `_run_solute_step()`, `_run_ion_step()`, `_run_export_step()` in `quickice/cli/pipeline.py`

**Variables:**
- Use `snake_case` for all local variables and module-level constants
- Module-level constants use `UPPER_SNAKE_CASE`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `MINIMUM_BOX_DIMENSION`, `HYDRATE_LATTICES`
- Private module-level constants use `_` prefix: `_ROUTER_FLAGS = frozenset({...})` in `quickice/entry.py`
- Private instance attributes use `_` prefix: `self._viewmodel`, `self._current_interface_result`, `self._interface_result`, `self._output_dir`
- Dictionaries mapping identifiers use descriptive names: `MOLECULE_TO_GROMACS`, `GUEST_MOLECULES`, `PHASE_CONDITIONS`
- CLI argparse groups use `snake_case` variable: `interface_group`, `hydrate_group`, `custom_group`, `solute_group`, `ion_group`

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

**Lazy Imports:**
- Heavy imports (PySide6, quickice.main, quickice.cli.parser) are deferred inside function branches to avoid importing GUI dependencies in headless mode
- Pattern in `quickice/entry.py`:
  ```python
  def main(argv: list[str] | None = None) -> int:
      # ...
      if known.gui:
          from quickice.gui.main_window import run_app  # LAZY — only if --gui
          run_app()
      # ...
      from quickice.main import main as cli_main  # LAZY — only if CLI mode
      return cli_main()
  ```
- Pattern in `quickice/cli/pipeline.py`: all `quickice.structure_generation.*` imports are inside `_run_*_step()` try blocks
- Pattern in `quickice/gui/workers.py`: all computation imports inside `run()` method for thread safety

**Path Aliases:**
- No custom import aliases or `sys.path` modifications in source code
- Test files import shared helpers explicitly: `from tests.conftest import run_quickice`
- Test files sometimes add `sys.path.insert(0, ...)` for e2e helper imports (legacy pattern):
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

**CLI Exit Codes:**
- 0 = success
- 1 = runtime error (file not found, invalid config, generation failure)
- 2 = argument error (argparse validation, missing required flags)
- Pattern in `quickice/main.py`: `SystemExit` from argparse produces exit code 2
- Pattern in `quickice/entry.py`: returns integer exit code from `main()`
- Pattern in `quickice/cli/pipeline.py`: `execute()` returns 0 or 1 per step

**Validation Pattern:**
- CLI validators raise `ArgumentTypeError` with descriptive messages in `quickice/validation/validators.py`
- CLI cross-flag validators use `parser.error()` (causes `SystemExit` with code 2): `validate_pipeline_args()` in `quickice/cli/parser.py`
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

**CLI Pipeline Error Handling:**
- Each step in `CLIPipeline._run_*_step()` catches specific exceptions and returns 1
- Dual reporting: `logger.error()` for logs + `report_progress()` for stderr user feedback
- Import errors caught separately (missing package) vs value errors (bad config)
  ```python
  try:
      from quickice.structure_generation.ion_inserter import insert_ions
  except ImportError as e:
      logger.error("Missing required package: %s", e)
      report_progress(f"Ion step failed: missing package — {e}")
      return 1
  try:
      # actual step logic
  except ValueError as e:
      logger.error("Invalid configuration: %s", e)
      report_progress(f"Ion step failed: bad config — {e}")
      return 1
  ```

**Top-level Error Handling:**
- `quickice/main.py` `main()` catches specific exceptions first, then generic:
  ```python
  except UnknownPhaseError as e:
      print(f"Error: {e}", file=sys.stderr)
      return 1
  except InterfaceGenerationError as e:
      print(f"Error: {e}", file=sys.stderr)
      return 1
  except SystemExit:
      raise  # propagate argparse exit code 2
  except Exception as e:
      print(f"Error: {e}", file=sys.stderr)
      return 1
  ```

## Logging

**Framework:** Python `logging` module

**Pattern:**
- Use `logger = logging.getLogger(__name__)` at module level
- Found in ~25+ source modules across CLI, GUI, and output modules:
  - `quickice/cli/pipeline.py`, `quickice/cli/itp_helpers.py`
  - `quickice/gui/main_window.py`, `quickice/gui/export.py`, `quickice/gui/ion_panel.py`
  - `quickice/output/gromacs_writer.py`, `quickice/structure_generation/solute_inserter.py`
- Non-GUI computation modules (`types.py`, `scorer.py`, `validators.py`) do NOT log
- No central logging configuration found — relies on Python defaults

**Progress Reporting (CLI):**
- `report_progress(message)` in `quickice/cli/pipeline.py` prints `[PROGRESS] {message}` to stderr
- Used at end of each pipeline step to provide user-visible feedback
- Keep stderr for progress/diagnostics, stdout for clean output

**When to Log:**
- GUI worker lifecycle: thread start, completion, cancellation, errors
- Export operations: file path selection, write success/failure
- Computation milestones: generation progress, insertion counts
- ITP file operations: copy success/failure with warning
- NOT for routine validation failures (those raise exceptions)

## Comments

**When to Comment:**
- Module docstrings on ALL source files (triple-double-quoted `"""`)
- Class docstrings with `Attributes:` sections for dataclasses
- Method docstrings with `Args:`, `Returns:`, `Raises:` sections
- Inline comments for non-obvious physical constants or GROMACS-specific formatting
- `# ──` separator lines for section headers in longer files
- `Note:` paragraphs for important caveats (thread safety, backward compatibility)
- `FIX #N:` comments for documented bug workarounds: `# FIX #4: offset includes guest_atom_count`

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
- CLI pipeline step methods include step number and purpose in docstring

## Function Design

**Size:** Most functions are 20-60 lines. Longer functions (up to ~100 lines) exist in writer code that formats GRO/TOP files line-by-line.

**Parameters:**
- Use typed parameters with default values where appropriate
- Config objects (`InterfaceConfig`, `HydrateConfig`, `SoluteConfig`, `CustomMoleculeConfig`) group related parameters
- Use `__post_init__` validation on config dataclasses for fail-fast behavior
- CLI argument validators double as type converters
- Use `getattr(args, 'attr_name', default)` for optional CLI args that may not exist on Namespace: `getattr(self.args, 'no_overwrite', False)`

**Return Values:**
- Use result dataclasses for multi-value returns: `GenerationResult`, `RankingResult`, `PlacementValidationResult`
- Boolean functions return `True`/`False` explicitly (not truthy/falsy)
- Export functions return `bool` for success/failure
- CLI `main()` returns integer exit code
- Pipeline `execute()` returns integer exit code (0 or 1)

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
- Never import GUI modules (`PySide6`) in computation modules (`structure_generation`, `phase_mapping`, `ranking`, `output`, `cli`)
- GUI validators return `tuple[bool, str]`; CLI validators raise `ArgumentTypeError`
- Export classes handle `QFileDialog`/`QMessageBox` interaction and delegate to writer functions
- Tab indices defined in `quickice/gui/constants.py` as `IntEnum`

## CLI Pipeline Conventions

- `CLIPipeline` class in `quickice/cli/pipeline.py` orchestrates ordered step execution
- Fail-fast semantics: first failing step stops execution and returns non-zero exit code
- Step ordering: source → interface → custom → solute → ion → export
- Each step method `_run_*_step()` returns 0 (success) or non-zero (failure)
- Priority order for export: ion > solute > custom > interface > hydrate > ice
- `argparse` module split: `quickice/cli/parser.py` for argument definition + validation, `quickice/cli/pipeline.py` for execution
- Entry routing in `quickice/entry.py`: no args → help, `--cli` → strip flag + CLI mode, `--gui` → GUI mode, pipeline flags → implicit CLI

## Bash Script Conventions

**`scripts/cli-examples.sh`:**
- All commands commented out with `#` prefix — safe to view as reference
- Uncomment to execute specific examples
- Sections delimited with `# === Header ===` markers
- Ends with `echo "This script is a reference..." && exit 0`

**`scripts/hydrate-interface-custom-ion.sh`:**
- Uses `while [ $# -gt 0 ]; do case "$1" in ... esac; shift; done` for flag parsing
- Missing-value guards on every flag that takes an argument:
  ```bash
  --custom-gro)
      shift
      if [ -z "$1" ]; then echo "ERROR: --custom-gro requires a PATH argument"; exit 1; fi
      CUSTOM_GRO="$1"
      ;;
  ```
- Required argument validation after loop: `if [ -z "$CUSTOM_GRO" ]; then echo "ERROR: ..." ; exit 1; fi`
- File existence checks: `if [ ! -f "$CUSTOM_GRO" ]; then echo "ERROR: ..." ; exit 1; fi`
- Print configuration summary before running
- Build command string and execute with `eval $CMD`
- Propagate pipeline exit code: `exit $PIPELINE_EXIT`

## Unit Conventions

- All distances in **nanometers (nm)** throughout the codebase
- Temperatures in **Kelvin (K)**
- Pressures in **MPa** (megapascals)
- Density in **g/cm³**
- Concentration in **mol/L (M)**
- Conversion helpers exist in `quickice/structure_generation/overlap_resolver.py`: `angstrom_to_nm()`, `nm_to_angstrom()`
- Validation ranges include nm rationale (e.g., "0.25 nm = 2.5 Å")

---

*Convention analysis: 2026-06-15*
