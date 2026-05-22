# Coding Conventions

**Analysis Date:** 2026-05-22

## Naming Patterns

**Files:**
- Python modules use `snake_case.py`: `interface_builder.py`, `hydrate_generator.py`, `overlap_resolver.py`
- Test files use `test_` prefix + `snake_case`: `test_structure_generation.py`, `test_phase_mapping.py`
- Subdirectory test packages: `tests/test_output/` (with `__init__.py`)
- GUI modules are in `quickice/gui/` with descriptive names: `main_window.py`, `phase_diagram_widget.py`, `custom_molecule_worker.py`

**Functions:**
- Public functions use `snake_case`: `lookup_phase()`, `generate_candidates()`, `calculate_supercell()`
- Private/internal functions use `_` prefix: `_calculate_oo_distances_pbc()`, `_build_result()`, `_parse_gro()`
- Signal handler methods use `_on_` prefix: `_on_generate_clicked()`, `_on_hydrate_generation_complete()`
- Setup methods use `_setup_` prefix: `_setup_ui()`, `_setup_connections()`, `_setup_shortcuts()`
- Class methods for construction use `from_dict()` or `from_lattice_type()` pattern: `InterfaceConfig.from_dict()`, `HydrateLatticeInfo.from_lattice_type()`
- Validator functions use `validate_` prefix: `validate_temperature()`, `validate_box_dimension()`

**Variables:**
- Instance attributes use `_` prefix for private: `self._viewmodel`, `self._current_result`, `self._is_generating`
- Module-level constants use `UPPER_SNAKE_CASE`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `HYDRATE_LATTICES`, `MINIMUM_BOX_DIMENSION`
- Temporary/local variables use `snake_case`: `pressure_mpa`, `lattice_info`, `gen_result`
- Type-checked private attributes with type hints: `self._worker: Optional[GenerationWorker] = None`

**Types:**
- Dataclasses use `PascalCase`: `Candidate`, `InterfaceConfig`, `HydrateStructure`, `RankedCandidate`
- Exception classes use `PascalCase` with `Error` suffix: `StructureGenerationError`, `InterfaceGenerationError`, `UnknownPhaseError`
- Enums use `PascalCase` for class, `UPPER_SNAKE_CASE` for members: `TabIndex(IntEnum)` with `ICE = 0`, `HYDRATE = 1`

## Code Style

**Formatting:**
- PEP 8 compliant with 4-space indentation
- No formal formatting tool (no black, ruff format, or autopep8 detected in configs)
- Line length follows PEP 8 default (~79-100 chars, no strict enforcement)
- Trailing newlines at end of files

**Linting:**
- No linter config files detected (no `.eslintrc`, `flake8`, `pylint`, `ruff.toml`)
- Code follows PEP 8 conventions by convention, not enforcement

## Import Organization

**Order:**
1. Standard library: `import logging`, `import os`, `import sys`, `from dataclasses import dataclass, field`
2. Third-party: `import numpy as np`, `from PySide6.QtCore import QObject, Signal`, `from scipy.spatial import cKDTree`
3. Local application: `from quickice.structure_generation.types import Candidate`, `from quickice.ranking.types import RankingResult`

**Style:**
- Standard library imports use `import X` for top-level, `from X import Y` for specific items
- NumPy always imported as `np`
- PySide6 imports use `from PySide6.QtWidgets import (multi-line)` with parenthesized wrapping
- Local imports use absolute paths: `from quickice.structure_generation.types import ...`
- Lazy imports inside `run()` methods of QThread workers to avoid blocking main thread

**Path Aliases:**
- No path aliases or `sys.path` modifications used
- All imports are absolute from package root `quickice.*`

## Error Handling

**Patterns:**
- Custom exception hierarchy with base classes:
  - `StructureGenerationError` in `quickice/structure_generation/errors.py` → `UnsupportedPhaseError`, `InterfaceGenerationError`
  - `PhaseMappingError` in `quickice/phase_mapping/errors.py` → `UnknownPhaseError`
- Error attributes for structured context:
  ```python
  class UnsupportedPhaseError(StructureGenerationError):
      def __init__(self, message: str, phase_id: str):
          super().__init__(message)
          self.phase_id = phase_id
  ```
- Error messages include `[mode]` prefix for mode-specific failures:
  ```python
  # In InterfaceGenerationError
  full_message = f"[{mode}] {message}"
  ```
- `__post_init__` validation in dataclasses raises `ValueError` with descriptive messages:
  ```python
  def __post_init__(self):
      if not (0.1 <= self.overlap_threshold <= 1.0):
          raise ValueError(
              f"overlap_threshold={self.overlap_threshold} nm is outside reasonable range..."
          )
  ```
- Worker pattern: try/except in `run()` catches specific exceptions first, then generic `Exception`:
  ```python
  except InterfaceGenerationError as e:
      error_result = InterfaceGenerationResult(success=False, error=str(e))
      self.error.emit(str(e))
      self.finished.emit(error_result)
  except Exception as e:
      error_result = InterfaceGenerationResult(
          success=False,
          error=f"Interface generation failed ({type(e).__name__}): {e}"
      )
  ```
- CLI error handling: catch specific exceptions and exit with code 1, print to stderr:
  ```python
  except UnknownPhaseError as e:
      print(f"Error: {e}", file=sys.stderr)
      return 1
  ```
- GUI error handling: `QMessageBox.critical()` for user-facing errors:
  ```python
  QMessageBox.critical(self, "Generation Error",
      f"Failed to generate ice structure:\n\n{error_msg}",
      QMessageBox.StandardButton.Ok)
  ```
- Validation functions differ by context:
  - CLI validators raise `ArgumentTypeError` (from `quickice/validation/validators.py`)
  - GUI validators return `Tuple[bool, str]` (from `quickice/gui/validators.py`)
- `raise ... from e` used for exception chaining in generator:
  ```python
  raise StructureGenerationError(
      f'Failed to generate ice structure ({type(e).__name__}): {e}'
  ) from e
  ```

## Logging

**Framework:** Python `logging` module

**Pattern:**
- Module-level logger at top of file: `logger = logging.getLogger(__name__)`
- Used in 20 modules across the codebase
- GUI workers and main_window use logger for error tracking
- Structure generation modules use logger for info/debug messages

**When to Log:**
- `logger.info()`: Registry operations, generation start/complete, molecule counts
- `logger.debug()`: Cache hits, already-registered items
- `logger.error()`: Caught exceptions in workers and handlers, always with `exc_info=True`:
  ```python
  logger.error(f"Solute insertion failed: {e}", exc_info=True)
  ```
- No `logger.warning()` usage detected in current codebase

**No explicit log configuration:**
- No `logging.basicConfig()` or custom handlers in application code
- Relies on root logger configuration (if any)

## Comments

**When to Comment:**
- Module-level docstrings on ALL files (triple-quoted with purpose description)
- Class-level docstrings describing attributes, signals, and usage patterns
- Method-level docstrings with Args/Returns/Raises sections
- Inline comments for physics/science context (e.g., unit conversions, IAPWS references)
- Section headers using `# ===` for grouping related methods:
  ```python
  # === Interface Generation Handlers (Interface Construction tab) ===
  # === Worker signal handlers ===
  ```

**Docstrings:**
- Google-style docstrings with `Args:`, `Returns:`, `Raises:`, `Example:` sections
- Attribute docstrings in dataclasses using `"""description."""` format
- Signal documentation in class docstring:
  ```python
  Signals:
      progress: Emitted with percentage (0-100)
      status: Emitted with status message
      finished: Emitted with GenerationResult on completion
  ```
- Usage examples in worker class docstrings showing the pattern

## Function Design

**Size:** Methods range from 5-50 lines. Long methods (>50 lines) are typically event handlers in `MainWindow` that orchestrate multiple UI updates.

**Parameters:**
- Type hints on all public methods: `def start_generation(self, temperature: float, pressure: float, nmolecules: int):`
- Optional parameters use `Optional[T]` or `T | None`: `base_seed: int | None = None`
- Dataclass configs preferred over dict parameters for complex configurations

**Return Values:**
- Dataclasses for structured results: `GenerationResult`, `RankingResult`, `HydrateStructure`
- `Tuple[bool, str]` for validation results (is_valid, error_message)
- `Optional[T]` for results that may be absent: `get_last_ranking_result() -> Optional[RankingResult]`
- `set[int]` for overlap detection results

## Module Design

**Exports:**
- `__init__.py` files define explicit `__all__` lists
- `quickice/structure_generation/__init__.py` re-exports all key types, errors, and functions
- `quickice/ranking/__init__.py` re-exports types and scoring functions
- Individual scoring functions exported "for advanced use"

**Barrel Files:**
- `__init__.py` modules serve as barrel files for each subpackage
- Import from barrel files in application code: `from quickice.structure_generation import generate_candidates`
- Import from specific modules for targeted use: `from quickice.structure_generation.types import Candidate`

## PySide6/Qt Conventions

**Signal-Slot Pattern:**
- Signals declared as class attributes: `progress = Signal(int)`, `finished = Signal(object)`
- Slot methods decorated with `@Slot(type)`: `@Slot(int)`, `@Slot(str)`, `@Slot(object)`, `@Slot()`
- Signal names use `snake_case`: `generation_started`, `generation_progress`, `generation_complete`
- Signal connections use direct method reference: `self._worker.progress.connect(self._on_progress)`
- Signal emission uses `.emit()`: `self.progress.emit(10)`, `self.generation_complete.emit(result)`

**MVVM Architecture:**
- `MainWindow` = View layer (connects UI to ViewModel)
- `MainViewModel` = ViewModel (manages workers and state, emits UI update signals)
- `GenerationWorker`, `InterfaceGenerationWorker` = Model workers (background computation)

**QThread Worker Conventions (Two Patterns Used):**

Pattern 1 - QObject + QThread (preferred for new workers):
```python
# Worker is QObject, NOT QThread subclass
# See: quickice/gui/workers.py, quickice/gui/custom_molecule_worker.py
class GenerationWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    
    def __init__(self, temperature, pressure, nmolecules):
        super().__init__()
        self._temperature = temperature
    
    def run(self):
        # Imports INSIDE run() for thread safety
        from quickice.phase_mapping import lookup_phase
        try:
            # Check cancellation
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            # Do work, emit progress
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(error_result)
```

Pattern 2 - QThread subclass (used for hydrate worker):
```python
# See: quickice/gui/hydrate_worker.py
class HydrateWorker(QThread):
    progress_updated = Signal(str)
    generation_complete = Signal(object)
    
    def run(self):
        # QThread.run() already runs in worker thread
        try:
            self.generation_complete.emit(result)
        except Exception as e:
            self.generation_error.emit(str(e))
```

**ViewModel Thread Setup Pattern:**
```python
# See: quickice/gui/viewmodel.py
self._worker = GenerationWorker(temperature, pressure, nmolecules)
self._thread = QThread()
self._worker.moveToThread(self._thread)

# Connect thread start to worker run
self._thread.started.connect(self._worker.run)

# Connect worker signals to ViewModel slots
self._worker.progress.connect(self._on_progress)
self._worker.finished.connect(self._on_finished)

# Cleanup on thread finish
self._thread.finished.connect(self._worker.deleteLater)
self._thread.finished.connect(self._thread.deleteLater)

self._thread.start()
```

**Cancellation Pattern:**
```python
# Request interruption (non-blocking)
self._thread.requestInterruption()
self._thread.quit()
# Wait with timeout to prevent UI freeze
self._thread.wait(100)  # 100ms timeout

# In worker, check periodically:
if QThread.currentThread().isInterruptionRequested():
    self.cancelled.emit()
    return
```

**VTK Availability Check:**
```python
# See: quickice/gui/view.py
_VTK_AVAILABLE = False
try:
    if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
        _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
    else:
        _VTK_AVAILABLE = True
    if _VTK_AVAILABLE:
        from quickice.gui.dual_viewer import DualViewerWidget
except Exception:
    _VTK_AVAILABLE = False
```

**GUI State Management:**
- `ui_enabled_changed = Signal(bool)` - True = UI enabled, False = generating
- ViewModel emits UI state signals; View connects and enables/disables controls
- Store current results as instance variables: `self._current_result`, `self._current_interface_result`
- Tab data flow managed through stored state, not direct method calls

## Dataclass Conventions

**Config Dataclasses:**
- Always include `__post_init__` for validation
- Provide `from_dict()` classmethod for UI dict → dataclass conversion:
  ```python
  @classmethod
  def from_dict(cls, d: dict) -> "InterfaceConfig":
      return cls(mode=d["mode"], box_x=d["box_x"], ...)
  ```
- Use `field(default_factory=dict)` for mutable default attributes
- Use `field(default_factory=list)` for list defaults

**Result Dataclasses:**
- Carry all data needed for downstream processing and export
- Include `metadata: dict[str, Any] = field(default_factory=dict)` for extensible info
- Use `Any` type for cross-module references to avoid circular imports:
  ```python
  interface_structure: Any = None  # InterfaceStructure (avoid circular import)
  ```

**Type Annotations:**
- Python 3.10+ union syntax: `int | None` (not `Optional[int]`)
- `list[str]` not `List[str]` (PEP 585 style)
- `dict[str, Any]` not `Dict[str, Any]`
- `np.ndarray` for numpy arrays (no generic parameterization)

**Molecule Index Tracking:**
- `MoleculeIndex` dataclass with `start_idx`, `count`, `mol_type`
- `molecule_index: list[MoleculeIndex]` tracks each molecule's position in atom array
- Supports variable atoms-per-molecule: ions (1), ice (3), TIP4P water (4), CH4 (5), THF (12)

## Unit Conventions

**All internal coordinates and distances are in nanometers (nm).**
- Explicit unit in parameter names: `threshold_nm`, `box_dims_nm`, `positions` (nm)
- Pressure in MPa throughout (no GPa or Pa)
- Temperature in Kelvin
- Concentration in mol/L (M)
- Angle values in degrees (Euler angles for rotations)
- Density in g/cm³
- Unit validation in `__post_init__`: range checks to catch nm vs Å mismatches
  ```python
  if not (0.1 <= self.overlap_threshold <= 1.0):
      raise ValueError("...This suggests a unit mismatch...")
  ```

---

*Convention analysis: 2026-05-22*
