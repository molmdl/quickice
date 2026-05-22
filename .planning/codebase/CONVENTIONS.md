# Coding Conventions

**Analysis Date:** 2026-05-22

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `water_filler.py`, `overlap_resolver.py`, `ion_inserter.py`)
- Test files: `test_{module_or_feature}.py` (e.g., `test_overlap_removal_invariants.py`, `test_itp_parser_edge_cases.py`)
- Conftest files: `conftest.py` (only in `tests/test_output/`)
- GUI module files: `snake_case.py` matching class name (e.g., `hydrate_panel.py` for `HydratePanel`)

**Classes:**
- PascalCase: `InterfaceStructure`, `Candidate`, `HydrateConfig`, `CustomMoleculeInserter`
- Exporter classes: `{Type}GROMACSExporter` (e.g., `SoluteGROMACSExporter`, `IonGROMACSExporter`)
- Worker classes: `{Feature}Worker` (e.g., `HydrateWorker`, `GenerationWorker`)
- Error classes: `{Feature}Error` extending base (e.g., `InterfaceGenerationError` extends `StructureGenerationError`)
  - Files: `quickice/structure_generation/errors.py`, `quickice/phase_mapping/errors.py`

**Functions:**
- snake_case: `assemble_slab()`, `detect_overlaps()`, `write_interface_gro_file()`
- Private helpers: underscore prefix `_detect_guest_atoms()`, `_count_guest_molecules()`
- Boolean-returning validators: `validate_temperature()`, `validate_box_dimension()`

**Variables:**
- snake_case: `ice_cell_dims`, `water_positions`, `overlapping_mol_indices`
- Module-level constants: UPPER_SNAKE_CASE (e.g., `TEMPLATE_DENSITY_GCM3`, `TIP4P_ICE_ALPHA`, `ATOMS_PER_WATER_MOLECULE`)
- Lookup dicts: UPPER_SNAKE_CASE (e.g., `MOLECULE_TO_GROMACS`, `HYDRATE_LATTICES`, `GUEST_MOLECULES`)

**Types:**
- Dataclasses: PascalCase with docstring attributes (e.g., `Candidate`, `InterfaceConfig`, `MoleculeIndex`)
- `list[str]` and `list[int]` (Python 3.14 style, not `List[str]`)
- Union types: `X | None` (not `Optional[X]`), seen in `quickice/structure_generation/types.py`

## Code Style

**Formatting:**
- No auto-formatter configured (no black, ruff format, or yapf)
- Indentation: 4 spaces
- Max line length: ~100 characters (soft limit, some lines exceed)
- Trailing newlines at EOF

**Linting:**
- No linter configured (no flake8, pylint, or ruff check)
- Type hints used extensively on public APIs but not enforced

**Type Hints:**
- Use for all public function signatures
- Use Python 3.10+ union syntax: `str | None` (not `Optional[str]`)
- Use `list[str]` not `List[str]` (lowercase generics)
- `Any` from typing for circular import avoidance (e.g., `registry: Any` in types.py)
- `np.ndarray` used directly (not `NDArray`)

## Import Organization

**Order:**
1. Standard library: `import logging`, `import numpy as np`, `from pathlib import Path`
2. Third-party: `from PySide6.QtWidgets import ...`, `from scipy.spatial import cKDTree`
3. Local: `from quickice.structure_generation.types import ...`

**Conventions:**
- `TYPE_CHECKING` guard for types that cause circular imports:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from quickice.structure_generation.types import CustomMoleculeStructure
  ```
  Example: `quickice/output/gromacs_writer.py`
- Conditional imports for optional dependencies:
  ```python
  _VTK_AVAILABLE = False
  try:
      from quickice.gui.interface_viewer import InterfaceViewerWidget
  except Exception:
      _VTK_AVAILABLE = False
  ```
  Example: `quickice/gui/interface_panel.py`
- Lazy imports inside functions for heavy dependencies:
  ```python
  def export_solute_gromacs(self, solute_structure):
      from quickice.output.gromacs_writer import write_solute_gro_file
  ```
  Example: `quickice/gui/export.py`
- Import grouping: stdlib → third-party → local, separated by blank lines

**Path Aliases:**
- None configured (no `pyproject.toml` path aliases)

## Error Handling

**Patterns:**

1. **Custom exception hierarchy** with descriptive error messages:
   ```python
   class StructureGenerationError(Exception):
       """Base error for structure generation."""
       pass

   class InterfaceGenerationError(StructureGenerationError):
       def __init__(self, message: str, mode: str):
           full_message = f"[{mode}] {message}"
           super().__init__(full_message)
           self.mode = mode
   ```
   Files: `quickice/structure_generation/errors.py`, `quickice/phase_mapping/errors.py`

2. **Invariant assertions** for data integrity (NOT for input validation):
   ```python
   # After overlap removal — these are structural invariants, not input checks
   assert len(trimmed_water_positions) % 4 == 0, (
       f"Water atom count {len(trimmed_water_positions)} not divisible by 4 "
       f"after ice-water overlap removal"
   )
   assert len(water_atom_names) == len(water_positions), (
       f"Atom names length {len(water_atom_names)} != positions length {len(water_positions)} "
       f"after ice-water overlap removal"
   )
   ```
   Files: `quickice/structure_generation/modes/slab.py` (lines 377-380, 561-564),
          `quickice/structure_generation/modes/pocket.py` (lines 332-339, 484-491, 522-529)

3. **ValueError with range hints** for parameter validation:
   ```python
   if not (0.1 <= threshold_nm <= 1.0):
       raise ValueError(
           f"threshold_nm={threshold_nm} is outside reasonable range [0.1, 1.0] nm. "
           f"This suggests a unit mismatch. "
           f"If you have a value in Angstrom, divide by 10 to get nm"
       )
   ```
   Files: `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/types.py`

4. **QMessageBox.warning for user-visible errors** (replaces `FileNotFoundError: pass`):
   ```python
   except FileNotFoundError:
       QMessageBox.warning(
           self.parent, "Missing Guest ITP",
           f"Guest ITP file for '{guest_type}' not found.\n"
           f"The exported .top file will reference it, but it won't be bundled.\n"
           f"Add the missing .itp file manually before running GROMACS."
       )
   ```
   Files: `quickice/gui/export.py` (lines 120-125, 250, 370, 917),
          `quickice/gui/main_window.py` (extensive use throughout)

5. **QMessageBox.critical for export failures**:
   ```python
   except Exception as e:
       QMessageBox.critical(self.parent, "Export Error", f"Failed: {e}")
   ```
   File: `quickice/gui/export.py`

6. **Dataclass `__post_init__` validation**:
   ```python
   @dataclass
   class InterfaceConfig:
       overlap_threshold: float = 0.25

       def __post_init__(self):
           if not (0.1 <= self.overlap_threshold <= 1.0):
               raise ValueError(...)
   ```
   Files: `quickice/structure_generation/types.py` (5 classes with `__post_init__`)

7. **Fallback values for external library failures**:
   ```python
   FALLBACK_DENSITY_GCM3 = 0.9998  # Water density at 0°C, 1 atm
   ```
   File: `quickice/phase_mapping/water_density.py`

## Logging

**Framework:** Python `logging` module

**Module-level logger pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Log level conventions:**
- `logger.debug()`: Internal state details, redundant checks
  ```python
  logger.debug(f"Hydrate guest {molecule} already registered as {registered_name}")
  logger.debug(f"Liquid solute {molecule} already registered as {registered_name}")
  ```
  File: `quickice/structure_generation/moleculetype_registry.py`

- `logger.info()`: Significant state changes, registration events, file parsing
  ```python
  logger.info(f"Registered hydrate guest: {molecule} → {registered_name}")
  logger.info(f"Parsing ITP file: {filepath.name}")
  logger.info(f"Solute ITP copied with atomtypes commented: {solute_itp_dest}")
  ```
  Files: `quickice/structure_generation/moleculetype_registry.py`,
         `quickice/structure_generation/itp_parser.py`,
         `quickice/gui/export.py`

- `logger.warning()`: Missing files, potential unit mismatches, degraded operation
  ```python
  logger.warning(f"Could not read ITP file: {e}")
  logger.warning(f"Coordinates may be in Å instead of nm (max={max_coord:.1f})")
  ```
  Files: `quickice/structure_generation/gro_parser.py`,
         `quickice/output/gromacs_writer.py`

## Comments

**When to Comment:**
- Module docstrings: Required for ALL `.py` files (triple-quoted string at top)
- Class docstrings: Required for all public classes (Attributes section with descriptions)
- Function docstrings: Required for all public functions (Args/Returns/Raises/Example sections)
- Inline comments: Used sparingly for CRITICAL and FIX annotations

**Docstring format (Google-style):**
```python
def detect_overlaps(
    ice_o_positions_nm: np.ndarray,
    water_o_positions_nm: np.ndarray,
    box_dims_nm: np.ndarray,
    threshold_nm: float = 0.25,
) -> set[int]:
    """Detect water molecules whose oxygen overlaps with any ice oxygen.

    Uses scipy.spatial.cKDTree with the boxsize parameter for automatic
    periodic boundary condition (PBC) handling.

    Args:
        ice_o_positions_nm: (N_ice, 3) ice oxygen positions in nm.
        water_o_positions_nm: (N_water, 3) water oxygen positions in nm.
        box_dims_nm: [bx, by, bz] box dimensions in nm for PBC.
        threshold_nm: O-O distance threshold in nm (default 0.25 nm = 2.5 Å).

    Returns:
        Set of water molecule indices to remove (0-based).

    Raises:
        ValueError: If threshold_nm is outside reasonable range [0.1, 1.0] nm.
    """
```
File: `quickice/structure_generation/overlap_resolver.py`

**CRITICAL/FIX inline annotations:**
```python
# CRITICAL: boxsize handles periodic boundaries automatically
# CRITICAL: Water template cell is scaled by density
# FIX: Tile guests SEPARATELY for bottom and top ice layers
# SAFEGUARD: Check if the detected "guest" is actually a water molecule
# IMPORTANT: Water molecules (starting with OW) are NEVER classified as guests
```
Files: `quickice/structure_generation/modes/slab.py`, `quickice/structure_generation/modes/pocket.py`

## Function Design

**Size:** Functions range from 5 lines to ~250 lines. The longest functions are the assembly functions (`assemble_slab` ~500 lines, `assemble_pocket` ~530 lines). Prefer decomposing when adding new logic.

**Parameters:**
- Explicit types on all public function parameters
- Default values for optional parameters (e.g., `threshold_nm: float = 0.25`)
- Configuration objects preferred over many parameters (e.g., `InterfaceConfig`, `HydrateConfig`)

**Return Values:**
- Named tuples/dataclasses for complex returns (e.g., `InterfaceStructure`, `GenerationResult`)
- `tuple` for simple multi-value returns (e.g., `tuple[np.ndarray, int]`)
- `set[int]` for index sets (e.g., overlapping molecule indices from `detect_overlaps`)

**Units Convention:**
- All coordinates in **nanometers (nm)** — GROMACS standard
- Distance thresholds in nm (not Angstrom)
- Conversion helpers provided: `angstrom_to_nm()`, `nm_to_angstrom()` in `quickice/structure_generation/overlap_resolver.py`
- Temperature in Kelvin, Pressure in MPa

## Module Design

**Exports:**
- Public API through `__init__.py` in each subpackage
- Example: `quickice/structure_generation/__init__.py` exports `generate_candidates`
- Example: `quickice/ranking/__init__.py` exports `rank_candidates` and types

**Barrel Files:**
- `__init__.py` files re-export key public symbols
- Not all modules re-exported — only the main entry points

**Thread Safety:**
- `threading.Lock` for GenIce2 lazy loading:
  ```python
  _genice_lock = threading.Lock()
  ```
  File: `quickice/structure_generation/hydrate_generator.py` (line 28)

- `@lru_cache` for expensive computations:
  ```python
  @lru_cache(maxsize=1)
  def load_water_template() -> tuple[np.ndarray, list[str], np.ndarray]:
  ```
  File: `quickice/structure_generation/water_filler.py` (line 216)

  ```python
  @lru_cache(maxsize=256)
  def water_density_kgm3(T_K: float, P_MPa: float) -> float:
  ```
  File: `quickice/phase_mapping/water_density.py` (line 40)

**BOM/Encoding Normalization:**
- ITP parser strips UTF-8 BOM and normalizes line endings:
  ```python
  content = content.lstrip('\ufeff')
  content = content.replace('\r\n', '\n').replace('\r', '\n')
  ```
  File: `quickice/structure_generation/itp_parser.py` (lines 62-63)

**MVVM Pattern (GUI):**
- `MainWindow` (View) → `MainViewModel` (ViewModel) → Worker (Model)
- View: `quickice/gui/main_window.py`
- ViewModel: `quickice/gui/viewmodel.py`
- Workers: `quickice/gui/workers.py`, `quickice/gui/hydrate_worker.py`, etc.
- Signals connect View ↔ ViewModel (PySide6 `Signal`/`Slot`)

**Validator Pattern:**
- CLI validators: raise `ArgumentTypeError` on invalid input
  File: `quickice/validation/validators.py`
- GUI validators: return `Tuple[bool, str]` — `(is_valid, error_message)`
  File: `quickice/gui/validators.py`

---

*Convention analysis: 2026-05-22*
