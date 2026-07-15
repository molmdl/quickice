# Coding Conventions

**Analysis Date:** 2026-07-14

## Naming Patterns

**Files:**
- `snake_case.py` for all source modules: `ion_inserter.py`, `solute_inserter.py`, `gromacs_writer.py`, `moleculetype_registry.py`
- `snake_case` for module directories: `structure_generation/`, `phase_mapping/`, `output/`, `validation/`
- Test files: `test_<feature>.py` (unit), `test_e2e_<feature>.py` (end-to-end), `test_scancode_bugs_<module>.py` (regression) — all in `tests/`
- Test helper files MUST NOT have the `test_` prefix (avoids pytest auto-collection): `tests/e2e_export_helpers.py`
- Conftest files: always `conftest.py` (root + each test subdirectory)

**Functions:**
- `snake_case`: `write_gro_file()`, `insert_solutes()`, `calculate_ion_pairs()`, `detect_atoms_per_molecule()`
- Private/internal helpers: leading underscore `_build_existing_atoms_tree()`, `_remove_overlapping_water()`, `_parse_cage_guest_args()`, `_liquid_volume_nm3()`
- Module-level convenience functions: thin wrappers around class methods:
  ```python
  # quickice/structure_generation/ion_inserter.py
  def insert_ions(structure, concentration_molar, ...) -> IonStructure:
      """Convenience function to insert ions into a structure."""
  ```

**Variables:**
- Module-level constants: `UPPER_SNAKE_CASE`: `TIP4P_ICE_OW_SIGMA`, `AVOGADRO`, `WATER_VOLUME_NM3`, `MIN_SEPARATION`
- Local variables: `snake_case`: `ion_pairs`, `water_nmolecules`, `wrapped_positions`
- Metadata dictionaries: `UPPER_SNAKE_CASE`: `MOLECULE_TYPE_INFO`, `HYDRATE_LATTICES`, `GAFF2_ATOMTYPES`, `CHAIN_COMBINATIONS`

**Types:**
- Dataclasses: `PascalCase`: `Candidate`, `InterfaceStructure`, `IonStructure`, `SoluteStructure`, `HydrateConfig`, `IonConfig`, `CustomMoleculeConfig`
- NamedTuples (test helpers): `PascalCase`: `StagingResult`, `ChainParams`
- Type annotations use `|` union syntax (Python 3.10+): `int | None`, `np.ndarray | None`, `list[str] | None`
- Use `Any` for circular-import avoidance: `solute_registry: Any = None`
- Class attributes typed with `Dict`/`Set`/`Tuple` from `typing` in older modules (`moleculetype_registry.py`), but new code uses lowercase `dict`/`set`/`tuple` builtins

## Code Style

**Formatting:**
- No auto-formatter is configured (no black, ruff, flake8, mypy, no `pyproject.toml`)
- 4-space indentation; no tabs
- Lines typically kept under ~120 chars
- String formatting: f-strings throughout (no `%` or `.format()` for new code)
- GROMACS file output: manual column alignment via f-string field widths (e.g. `%5s`, `>5`, fixed-width sections)
- Trailing newlines in f-strings for line-based GROMACS format: `f"...{val}\n"`

**Linting:**
- No linter configured — conventions are enforced by code review and regression tests
- Type annotations ARE used in function signatures, but no `mypy` config enforces them
- Source-scanning regression tests guard against re-introducing known-bad literals (see `tests/test_tip4p_ice_lj_values.py::test_no_31668e_minus3`)

## Import Organization

**Order (3 groups, separated by blank lines):**
1. Standard library: `import logging`, `import random`, `import argparse`, `from pathlib import Path`, `from dataclasses import dataclass`
2. Third-party: `import numpy as np`, `from scipy.spatial import cKDTree`, `from scipy.spatial.transform import Rotation`
3. Local package: `from quickice.structure_generation.types import (...)`, `from quickice.output.gromacs_writer import write_top_file`

Example from `quickice/structure_generation/solute_inserter.py`:
```python
import logging
import random
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from quickice.structure_generation.types import (
    SoluteConfig,
    SoluteStructure,
    InterfaceStructure,
    MoleculeIndex,
    WATER_ATOMS_PER_MOLECULE,
    WATER_VOLUME_NM3,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.ion_inserter import AVOGADRO
```

**Path Aliases:**
- None configured (no `pyproject.toml`, no `setup.cfg`). Always import via full package path: `from quickice.structure_generation.ion_inserter import AVOGADRO`
- Test files use `sys.path.insert` for non-package helper imports:
  ```python
  sys.path.insert(0, str(Path(__file__).parent))
  from e2e_export_helpers import parse_top_molecules, _insert_solutes
  ```
  Use `# noqa: E402` on imports after `sys.path.insert` (no linter, but documents intent).

**Lazy imports (CRITICAL constraint):**
- PySide6, VTK, GenIce2 are imported INSIDE function bodies — NEVER at module top level
- `quickice/entry.py` uses `importlib.util.find_spec('PySide6')` to check availability WITHOUT importing:
  ```python
  def _is_pyside6_available() -> bool:
      try:
          return importlib.util.find_spec('PySide6') is not None
      except (ImportError, ValueError, ModuleNotFoundError):
          return False
  ```
- `quickice/cli/pipeline.py` keeps zero Qt/PySide6/VTK imports (CLI must run headless)
- Heavy sub-imports are deferred inside branches: `from quickice.gui.main_window import run_app` (only in the `--gui` branch of `entry.py::main()`)

**Circular import avoidance:**
- `TYPE_CHECKING` guard in `quickice/output/gromacs_writer.py`:
  ```python
  from typing import TYPE_CHECKING, Optional
  if TYPE_CHECKING:
      from quickice.structure_generation.types import CustomMoleculeStructure, SoluteStructure
  ```
- `Any` type annotations for registry objects to break cycles: `solute_registry: Any = None`
- Deferred imports inside functions in `pipeline.py`: `from quickice.structure_generation.types import CageGuestAssignment, HYDRATE_LATTICES`

## Error Handling

**Specific exceptions in pipeline and writer code (HARD CONSTRAINT):**
- NO bare `except Exception` in core pipeline code (`quickice/cli/pipeline.py`). Use `except (ValueError, OSError) as e:` or more specific
- GUI code MAY use broad `except Exception as e:` for user-facing workflows (acceptable in GUI context only)
- Pattern in `quickice/output/gromacs_writer.py` and `quickice/structure_generation/molecule_validator.py`:
  ```python
  try:
      with open(filepath, 'w') as f:
          ...
  except (OSError, ValueError) as e:
      logger.error(f"Failed to write GRO file '{filepath}': {e}")
      if Path(filepath).exists():
          Path(filepath).unlink()  # cleanup partial output
      raise
  ```

**Custom exceptions (defined in `quickice/structure_generation/errors.py`):**
- `StructureGenerationError` — base error for the hierarchy
- `UnsupportedPhaseError(message, phase_id)` — carries `phase_id` attribute
- `InterfaceGenerationError(message, mode)` — prepends `[{mode}]` to message, carries `mode` attribute
  ```python
  class InterfaceGenerationError(StructureGenerationError):
      def __init__(self, message: str, mode: str):
          full_message = f"[{mode}] {message}"
          super().__init__(full_message)
          self.mode = mode
  ```

**File cleanup on write failure:**
- Always delete partial output files on `OSError`/`ValueError` (see pattern above) — prevents corrupt `.gro`/`.top` files from being used

**Input validation (two distinct styles):**

CLI validators (`quickice/validation/validators.py`) — used as argparse `type=` converters, RAISE `ArgumentTypeError`:
```python
def validate_concentration_range(value: str) -> float:
    try:
        val = float(value)
    except ValueError:
        raise ArgumentTypeError(f"concentration must be a number, got '{value}'")
    if not (0.0 <= val <= 5.0):
        raise ArgumentTypeError(f"concentration must be between 0.0 and 5.0 mol/L, got {val}")
    return val
```

GUI validators (`quickice/gui/validators.py`) — return `Tuple[bool, str]` for inline error display, DO NOT raise:
```python
def validate_temperature(value: str) -> Tuple[bool, str]:
    try:
        temp = float(value)
    except ValueError:
        return (False, "Temperature must be a number")
    if temp < 0 or temp > 500:
        return (False, "Temperature must be between 0 and 500 K")
    return (True, "")
```
- NOTE: GUI molecule-count max is 216 (interactive limit); CLI max is 100000. Different limits are intentional.

**Dataclass `__post_init__` validation:**
- All config dataclasses validate in `__post_init__` and raise `ValueError` on invalid params
```python
@dataclass
class SoluteConfig:
    def __post_init__(self):
        if self.concentration_molar < 0:
            raise ValueError(...)
        if self.solute_type not in ("CH4", "THF"):
            raise ValueError(...)
```

## Module-level Physical Constants (HARD CONSTRAINTS)

**Never hardcode these values — import the module constant:**

| Constant | Location | Value | Notes |
|----------|----------|-------|-------|
| `TIP4P_ICE_OW_SIGMA` | `quickice/output/gromacs_writer.py` | `3.16680e-1` nm | Referenced in all 6 TOP-writing functions |
| `TIP4P_ICE_OW_EPSILON` | `quickice/output/gromacs_writer.py` | `8.82110e-1` kJ/mol | Abascal 2005 |
| `TIP4P_ICE_ALPHA` | `quickice/output/gromacs_writer.py` | `0.13458335` | Virtual site param (NOTE: legacy duplicate exists) |
| `WATER_VOLUME_NM3` | `quickice/structure_generation/types.py` | `0.0299` nm³ | Used in `ion_inserter.py`, `solute_inserter.py`, `pipeline.py` |
| `WATER_ATOMS_PER_MOLECULE` | `quickice/structure_generation/types.py` | `4` | TIP4P-ICE: OW, HW1, HW2, MW |
| `AVOGADRO` | `quickice/structure_generation/ion_inserter.py` | `6.02214076e23` | SINGLE definition — import from here, never duplicate |

Import pattern (always from the single source):
```python
from quickice.structure_generation.ion_inserter import AVOGADRO
from quickice.structure_generation.types import WATER_VOLUME_NM3, WATER_ATOMS_PER_MOLECULE
from quickice.output.gromacs_writer import TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON
```

When adding new physical constants:
- Place in the most domain-relevant module (force-field params in `gromacs_writer.py`, molecular properties in `types.py`, ion params in `ion_inserter.py`)
- Import elsewhere — NEVER duplicate
- Use `UPPER_SNAKE_CASE`
- Include citation comments for literature-derived values:
  ```python
  # TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)
  TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
  TIP4P_ICE_OW_EPSILON = 8.82110e-1   # kJ/mol
  ```

## Comb-rule Convention (HARD CONSTRAINT)

- All GROMACS `.top` files use **comb-rule=2** (Lorentz-Berthelot) — the AMBER/GAFF2 convention
- Every `[ defaults ]` section in all 6 TOP-writing functions writes: `1  2  yes  0.5  0.8333`
- NEVER use comb-rule=1 (geometric mean) — incompatible with AMBER/GAFF2
- Comment explaining the convention appears in every TOP file:
  ```
  ; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)
  ; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
  ```
- Regression tests in `tests/test_tip4p_ice_lj_values.py` verify comb-rule=2 in all TOP outputs

## Moleculetype Naming (HARD CONSTRAINT)

- Hydrate guests use `_H` suffix: `CH4_H`, `THF_H` (5-char max for GRO format)
- Liquid solutes use `_L` suffix: `CH4_L`, `THF_L`
- Custom molecules get unique names via `MoleculetypeRegistry.register_custom_molecule()` (auto-increments: `MOL`, `MOL_1`, `MOL_2`)
- `MoleculetypeRegistry` in `quickice/structure_generation/moleculetype_registry.py` manages ALL naming — NEVER hardcode moleculetype names
- `RESERVED_NAMES` set prevents collisions: `{"SOL", "NA", "CL", "CH4", "THF", "CO2", "H2", "CH4_H", "CH4_L", "THF_H", "THF_L"}`

## cKDTree Conditional Rebuild Pattern

Used in BOTH `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py`:
- Initialize tree reference to `None` BEFORE the placement loop
- Rebuild ONLY after a successful placement — NOT on rejection iterations:
  ```python
  ion_tree = None  # KDTree for ion-ion overlap checking
  for i, water_idx in enumerate(selected):
      water_pos = structure.positions[start]
      if ion_tree is not None:
          min_ion_dist = ion_tree.query(water_pos, k=1)[0]
          if min_ion_dist < MIN_SEPARATION:
              continue  # Rejection — NO rebuild
      # Valid position — reached only after overlap checks pass
      ion_positions.append(water_pos)
      ion_tree = cKDTree(np.array(ion_positions))  # Rebuild ONLY on success
  ```
- Gives O(N) rebuilds for N placed molecules instead of O(N × max_attempts)
- Regression tests verify strict size monotonicity (`tests/test_scancode_bugs_solute.py::TestTREE03`)

## Mutation-free Inserter Convention (HARD CONSTRAINT)

- All inserter functions return NEW structure objects — NEVER mutate input structures (V-17 fix)
- `_remove_overlapping_water()` returns a NEW `InterfaceStructure` instead of modifying input
- When attribute propagation is needed, build a new object and set attrs on the NEW object:
  ```python
  new_interface = InterfaceStructure(...)  # copy data
  new_interface.custom_molecule_count = ...
  new_interface.custom_molecule_positions = ...
  return new_interface
  ```
- Use `getattr(structure, 'attr', default)` for reading only — never `setattr` on inputs

## Attribute Propagation Convention (Duck-typing)

- Cross-structure attribute propagation uses duck-typing via `getattr`/`hasattr` (this is accepted design CP-01, NOT a bug):
  ```python
  solute_type = getattr(structure, 'solute_type', "")
  solute_positions = getattr(structure, 'solute_positions', None)
  if hasattr(structure, 'custom_molecule_atom_count'):
      ...
  ```
- Custom molecule attributes propagate through the chain: Interface → Custom → Solute → Ion
- GUI MainWindow stores results as `_current_*_result` attributes; runtime attrs set on `InterfaceStructure` (e.g., `.solute_type`, `.custom_molecule_positions`)
- Set attributes on NEW objects only, never on inputs

## Shared Functions / Deduplication

- `detect_atoms_per_molecule()` centralized in `quickice/structure_generation/types.py` (was duplicated in `gromacs_writer.py`, V-07 dedup):
  ```python
  def detect_atoms_per_molecule(atom_names: list[str]) -> int:
      if len(atom_names) >= 4:
          if atom_names[0] == "OW":
              return 4
      return 3  # Default to GenIce ice (3 atoms)
  ```
- Import from the single source — never copy-paste between modules
- Place shared logic in the most domain-relevant module (`types.py` for structure-level functions)

## Logging

**Framework:** Python `logging` module with `__name__` loggers

**Patterns:**
- Module-level logger at top of file: `logger = logging.getLogger(__name__)`
- Used in `solute_inserter.py`, `gromacs_writer.py`, `pipeline.py`, `molecule_validator.py`, `moleculetype_registry.py`
- Log levels:
  - `logger.info()` — generation progress, template loading, registry events
  - `logger.warning()` — partial placement failures, coordinate unit mismatches, format limits
  - `logger.error()` — file write failures, configuration errors
- f-string interpolation in log messages: `logger.info(f"Registered hydrate guest: {molecule} → {registered_name}")`

**Progress reporting (CLI only):**
- `report_progress()` in `quickice/cli/pipeline.py` writes to stderr (keeps stdout clean for data):
  ```python
  def report_progress(message: str) -> None:
      print(f"[PROGRESS] {message}", file=sys.stderr)
  ```

## Comments

**When to comment:**
- GROMACS file format sections: inline comments explaining field meanings (`; sigma in nm`, `; epsilon in kJ/mol`)
- Physical constants: ALWAYS include citation references:
  ```python
  # TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)
  # sigma_O = 3.1668 Å = 0.31668 nm; epsilon_O/k_B = 106.1 K → 106.1 × 0.00831446 = 0.88211 kJ/mol
  TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
  ```
- Bug fix references use scan code IDs in code AND docstrings:
  ```python
  # CRITICAL: Remove water molecules that overlap with placed solutes
  # This avoids mutating the input structure (V-17 fix)
  ```
- Section dividers using box comments for grouping:
  ```python
  # ---------------------------------------------------------------------------
  # GAFF2 atomtype definitions for standard guest/solute molecules
  # ---------------------------------------------------------------------------
  ```

**Docstrings (Google-style throughout):**
```python
def calculate_ion_pairs(self, concentration_molar: float, liquid_volume_nm3: float) -> int:
    """Calculate number of ion pairs from concentration and volume.

    Uses: N = C_M × V_L × NA

    Args:
        concentration_molar: NaCl concentration in mol/L (M)
        liquid_volume_nm3: Liquid region volume in nm³

    Returns:
        Number of NaCl formula units (each becomes 1 Na+ + 1 Cl- ion pair)
    """
```
- Module docstrings explain purpose, design decisions, and constraints (see `quickice/entry.py`, `quickice/cli/pipeline.py`)
- Class docstrings include `Attributes:` and `Example:` sections (see `MoleculetypeRegistry`)
- Include `Raises:` section when exceptions are raised

## Function Design

**Size:** Functions range from small helpers (~10 lines) to large GROMACS writer functions (~200+ lines). Large writer functions are acceptable because GROMACS format requires sequential line-by-line writes.

**Parameters:** Use dataclass config objects for complex parameter sets:
- `InterfaceConfig`, `HydrateConfig`, `IonConfig`, `SoluteConfig`, `CustomMoleculeConfig`
- Config objects have `__post_init__` validation and `from_dict()` class methods

**Return Values:** Return new structure dataclass objects (never mutation):
- `insert_solutes()` → `SoluteStructure`
- `replace_water_with_ions()` → `IonStructure`
- `_remove_overlapping_water()` → new `InterfaceStructure`
- CLI step functions return exit codes: `0` for success, `1` for error

## Module Design

**Exports:** Public API = class + convenience function pair:
```python
# quickice/structure_generation/ion_inserter.py
class IonInserter:
    def replace_water_with_ions(self, ...) -> IonStructure: ...

def insert_ions(structure, concentration_molar, ...) -> IonStructure:
    """Convenience function to insert ions into a structure."""
```

**Private helpers:** Prefixed with underscore: `_build_existing_atoms_tree()`, `_check_solute_overlap()`, `_parse_cage_guest_args()`

**Barrel files:** `__init__.py` files exist but are MINIMAL (no re-exports). Import directly from submodules:
```python
from quickice.structure_generation.ion_inserter import IonInserter, AVOGADRO
from quickice.output.gromacs_writer import write_gro_file, write_top_file
```

**Re-exports with noqa:** When backward-compat re-exports are needed, annotate intent:
```python
from quickice.output.guest_info import _build_custom_guest_info  # noqa: F401 (re-exported for backward compat)
```

---

*Convention analysis: 2026-07-14*
