# Coding Conventions

**Analysis Date:** 2026-06-18

## Naming Patterns

**Files:**
- snake_case: `ion_inserter.py`, `solute_inserter.py`, `gromacs_writer.py`
- Module directories: snake_case `structure_generation/`, `phase_mapping/`, `output/`
- Test files: `test_<feature>.py` or `test_e2e_<feature>.py` in `tests/`
- Test helper files (non-collected): no `test_` prefix, e.g., `e2e_export_helpers.py`

**Functions:**
- snake_case: `write_gro_file()`, `insert_solutes()`, `calculate_ion_pairs()`
- Private helpers: underscore prefix `_build_existing_atoms_tree()`, `_remove_overlapping_water()`
- Convenience module-level functions: `insert_ions()`, `insert_solutes()` — thin wrappers around class methods

**Variables:**
- Module-level constants: UPPER_SNAKE_CASE: `TIP4P_ICE_OW_SIGMA`, `AVOGADRO`, `WATER_VOLUME_NM3`
- Local variables: snake_case: `ion_pairs`, `water_nmolecules`, `wrapped_positions`
- Dictionaries of metadata: UPPER_SNAKE_CASE: `MOLECULE_TYPE_INFO`, `HYDRATE_LATTICES`, `MOLECULE_TO_GROMACS`

**Types:**
- Dataclasses: PascalCase: `Candidate`, `InterfaceStructure`, `IonStructure`, `SoluteStructure`
- NamedTuples for test helpers: PascalCase: `StagingResult`, `ChainParams`
- Type annotations use `|` union syntax (Python 3.10+): `int | None`, `np.ndarray | None`
- `Any` used for circular-import avoidance: `solute_registry: Any = None`

## Code Style

**Formatting:**
- No auto-formatter configured (no .prettierrc, no black, no ruff)
- 4-space indentation
- Lines typically under 120 chars
- String formatting: f-strings throughout
- GROMACS file output: manual column alignment with f-string field widths

**Linting:**
- No linter configured (no .eslintrc, no flake8, no ruff.toml)
- Type annotations used in function signatures but no mypy configuration

## Import Organization

**Order:**
1. Standard library: `import logging`, `import random`, `from pathlib import Path`
2. Third-party: `import numpy as np`, `from scipy.spatial import cKDTree`
3. Local package: `from quickice.structure_generation.types import ...`

**Path Aliases:**
- No import aliases configured (no pyproject.toml, no setup.cfg)
- `sys.path.insert(0, ...)` used in test files for e2e_export_helpers import:
  ```python
  sys.path.insert(0, str(Path(__file__).parent))
  from e2e_export_helpers import ...
  ```

**Circular import avoidance:**
- `TYPE_CHECKING` guard in `gromacs_writer.py`:
  ```python
  if TYPE_CHECKING:
      from quickice.structure_generation.types import CustomMoleculeStructure, SoluteStructure
  ```
- `Any` type annotations for registry objects to avoid circular imports:
  ```python
  solute_registry: Any = None  # MoleculetypeRegistry (avoid circular import)
  ```

## Error Handling

**Specific exceptions in pipeline and writer code:**
- Use `except (ValueError, OSError) as e:` in file writing and validation code
- Pattern in `quickice/output/gromacs_writer.py` and `quickice/structure_generation/molecule_validator.py`:
  ```python
  try:
      with open(filepath, 'w') as f:
          ...
  except (OSError, ValueError) as e:
      logger.error(f"Failed to write GRO file '{filepath}': {e}")
      if Path(filepath).exists():
          Path(filepath).unlink()
      raise
  ```
- Use `except (ValueError, OSError)` — NOT `except Exception` — in core pipeline code (`quickice/cli/pipeline.py`)
- GUI code uses `except Exception as e:` for broad error catching in user-facing workflows (acceptable in GUI context)
- Dataclass `__post_init__` raises `ValueError` for invalid parameters

**Custom exceptions:**
- Defined in `quickice/structure_generation/errors.py`:
  - `StructureGenerationError` — base error
  - `UnsupportedPhaseError` — for unsupported ice phases
  - `InterfaceGenerationError` — for interface generation failures (includes `mode` attribute)

**File cleanup on write failure:**
- Delete partial output files on `OSError`/`ValueError`:
  ```python
  except (OSError, ValueError) as e:
      if Path(filepath).exists():
          Path(filepath).unlink()
      raise
  ```

## Module-level Physical Constants

**TIP4P-ICE LJ parameters (single source of truth):**
- Defined in `quickice/output/gromacs_writer.py`:
  ```python
  TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
  TIP4P_ICE_OW_EPSILON = 8.82110e-1   # kJ/mol
  ```
- Referenced in ALL 6 TOP-writing functions: `write_top_file()`, `write_interface_top_file()`,
  `write_ion_top_file()`, `write_multi_molecule_top_file()`, `write_custom_molecule_top_file()`,
  `write_solute_top_file()`
- Never hardcode LJ values in f-strings — always use the constants:
  ```python
  f"OW_ice   OW_ice    8  15.9994  0.0  A  {TIP4P_ICE_OW_SIGMA:.5e}    {TIP4P_ICE_OW_EPSILON:.5e}\n"
  ```

**TIP4P-ICE virtual site parameter:**
- Defined in `quickice/output/gromacs_writer.py`:
  ```python
  TIP4P_ICE_ALPHA = 0.13458335
  ```
- NOTE: defined twice in the file (lines 23 and 144) — legacy duplication, both identical

**Water volume constant:**
- Defined in `quickice/structure_generation/types.py`:
  ```python
  WATER_VOLUME_NM3: float = 0.0299
  ```
- Replaces all hardcoded `0.0299` values — single source of truth for volume per TIP4P-ICE water molecule
- Imported and used in `ion_inserter.py`, `solute_inserter.py`, `pipeline.py`

**Avogadro constant (single definition):**
- Defined once in `quickice/structure_generation/ion_inserter.py`:
  ```python
  AVOGADRO = 6.02214076e23  # mol^-1 (CODATA 2017)
  ```
- Imported elsewhere (NOT duplicated):
  ```python
  from quickice.structure_generation.ion_inserter import AVOGADRO
  ```
- Previously duplicated in `pipeline.py` — now imports from `ion_inserter.py`

**Water atoms per molecule:**
- Defined in `quickice/structure_generation/types.py`:
  ```python
  WATER_ATOMS_PER_MOLECULE: int = 4
  ```

**When adding new physical constants:**
- Place in the most domain-relevant module (e.g., force field params in `gromacs_writer.py`,
  molecular properties in `types.py`, ion params in `ion_inserter.py`)
- Import elsewhere — never duplicate
- Use UPPER_SNAKE_CASE

## Comb-rule Convention

**All GROMACS .top files use comb-rule=2 (Lorentz-Berthelot):**
- Every `[ defaults ]` section in all 6 TOP-writing functions writes:
  ```
  1               2               yes             0.5     0.8333
  ```
- This is the AMBER/GAFF2 convention: `sigma_ij = (sigma_i + sigma_j) / 2`, `epsilon_ij = sqrt(eps_i * eps_j)`
- Never use comb-rule=1 (geometric mean) — incompatible with AMBER/GAFF2 force fields
- Regression tests in `test_tip4p_ice_lj_values.py` verify comb-rule=2 is present in all TOP outputs
- Comment explaining the convention appears in every TOP file:
  ```
  ; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, epsilon_ij=sqrt(eps_i*eps_j)
  ; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
  ```

## Input Validation

**CLI validators (argparse type converters):**
- Defined in `quickice/validation/validators.py` — used as `type=` argument in argparse
- Raise `ArgumentTypeError` on invalid input (argparse converts to error message)
- Range validation with clamping:

  ```python
  def validate_concentration_range(value: str) -> float:
      """Clamps to 0.0-5.0 mol/L."""
      val = float(value)
      if not (0.0 <= val <= 5.0):
          raise ArgumentTypeError(f"concentration must be between 0.0 and 5.0 mol/L, got {val}")
      return val

  def validate_occupancy_range(value: str) -> float:
      """Clamps to 0.0-100.0 percent."""
      val = float(value)
      if not (0.0 <= val <= 100.0):
          raise ArgumentTypeError(f"cage occupancy must be between 0.0 and 100.0%, got {val}")
      return val
  ```

**File extension validators (in CLI pipeline):**
- `.gro` extension validation in `quickice/cli/pipeline.py`:
  ```python
  if gro_path.suffix.lower() != '.gro':
      report_progress(f"Error: --custom-gro file must have .gro extension, got '{gro_path.suffix}'")
      return 1
  ```
- `.itp` extension validation similarly:
  ```python
  if itp_path.suffix.lower() != '.itp':
      report_progress(f"Error: --custom-itp file must have .itp extension, got '{itp_path.suffix}'")
      return 1
  ```

**GUI validators:**
- Defined in `quickice/gui/validators.py` — return `tuple[bool, str]` for inline error display
- Different from CLI validators: return `(is_valid, error_message)` instead of raising exceptions
- Smaller ranges (e.g., nmolecules max 216 for GUI vs 100000 for CLI)

**Dataclass `__post_init__` validation:**
- All config dataclasses validate in `__post_init__`:
  ```python
  @dataclass
  class SoluteConfig:
      def __post_init__(self):
          if self.concentration_molar < 0:
              raise ValueError(...)
          if self.solute_type not in ("CH4", "THF"):
              raise ValueError(...)
  ```

## Shared Functions

**`detect_atoms_per_molecule()` — centralized in `types.py`:**
- Was previously duplicated in `gromacs_writer.py` (V-07 dedup)
- Now lives in `quickice/structure_generation/types.py` and is imported by all callers:
  ```python
  from quickice.structure_generation.types import detect_atoms_per_molecule
  ```
- Used in `slab.py`, `pocket.py`, `piece.py` for ice candidate processing
- Pattern: detects 3-atom (GenIce) vs 4-atom (TIP4P/hydrate) molecules:
  ```python
  def detect_atoms_per_molecule(atom_names: list[str]) -> int:
      if len(atom_names) >= 4:
          if atom_names[0] == "OW":
              return 4
      return 3  # Default to GenIce ice (3 atoms)
  ```

**When deduplicating shared logic:**
- Place in the most domain-relevant types module (`types.py` for structure-level functions)
- Import from single source — never copy-paste between modules

## cKDTree Conditional Rebuild Pattern

**Pattern used in BOTH `ion_inserter.py` and `solute_inserter.py`:**
- Initialize tree reference to `None` before loop:
  ```python
  ion_tree = None  # KDTree for ion-ion overlap checking
  ```
- Rebuild ONLY after successful placement (not on rejection iterations):
  ```python
  for i, water_idx in enumerate(selected):
      water_pos = structure.positions[start]
      if ion_tree is not None:
          min_ion_dist = ion_tree.query(water_pos, k=1)[0]
          if min_ion_dist < MIN_SEPARATION:
              continue  # Rejection — NO rebuild
      # Valid position — only reached after overlap checks pass
      ion_positions.append(water_pos)
      ion_tree = cKDTree(np.array(ion_positions))  # Rebuild ONLY on success
  ```
- In `solute_inserter.py`, uses growing `combined_tree_data` array:
  ```python
  combined_tree_data = np.vstack([combined_tree_data, solute_positions])
  existing_tree = cKDTree(combined_tree_data)
  ```
- This gives O(N) rebuilds for N placed molecules instead of O(N × max_attempts)
- Regression tests verify strict size monotonicity (V-03 tests in `test_scancode_bugs_solute.py`)

## Mutation-free Inserter Convention

**SoluteInserter never mutates input InterfaceStructure (V-17 fix):**
- `_remove_overlapping_water()` returns a NEW InterfaceStructure instead of modifying the input
- When no water is removed but custom molecule attrs need propagation:
  ```python
  # Build a new InterfaceStructure with the same data but custom molecule attrs set
  # This avoids mutating the input structure (V-17 fix)
  new_interface = InterfaceStructure(...)
  new_interface.custom_molecule_count = ...
  new_interface.custom_molecule_positions = ...
  return new_interface
  ```
- Previously, the function would set attributes directly on the input structure, causing
  side effects visible to callers

**Convention for inserters:**
- All inserter functions return NEW structure objects (IonStructure, SoluteStructure)
- Never set attributes on input structures — use `getattr()` for reading only
- When attribute propagation is needed, create a new object and set attrs on the new object

## Logging

**Framework:** Python `logging` module with `__name__` loggers

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Used in `solute_inserter.py`, `gromacs_writer.py`, `pipeline.py`, `molecule_validator.py`
- Log levels:
  - `logger.info()` — for generation progress, template loading
  - `logger.warning()` — for partial placement failures, coordinate unit mismatches, format limits
  - `logger.error()` — for file write failures, configuration errors

**Progress reporting (CLI):**
- `report_progress()` in `quickice/cli/pipeline.py` writes to stderr:
  ```python
  def report_progress(message: str) -> None:
      print(f"[PROGRESS] {message}", file=sys.stderr)
  ```

## Comments

**When to Comment:**
- GROMACS file format sections require inline comments explaining field meanings
- Physical constants include citation references:
  ```python
  # TIP4P-ICE LJ parameters (Abascal et al. 2005, DOI: 10.1063/1.1931662)
  TIP4P_ICE_OW_SIGMA = 3.16680e-1    # nm
  ```
- Bug fix references use scan code IDs:
  ```python
  # CRITICAL: Remove water molecules that overlap with placed solutes
  # This avoids mutating the input structure (V-17 fix)
  ```

**JSDoc/TSDoc:**
- Google-style docstrings throughout:
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

## Function Design

**Size:** Functions range from small helpers (~10 lines) to large writer functions (~200+ lines for GRO/TOP writers). Large writer functions are acceptable because GROMACS format output requires sequential line-by-line writes.

**Parameters:** Use dataclass config objects for complex parameter sets:
- `InterfaceConfig`, `HydrateConfig`, `IonConfig`, `SoluteConfig`, `CustomMoleculeConfig`
- Config objects have `__post_init__` validation and `from_dict()` class methods

**Return Values:** Return new structure dataclass objects (not mutation):
- `insert_solutes()` → `SoluteStructure`
- `replace_water_with_ions()` → `IonStructure`
- `_remove_overlapping_water()` → new `InterfaceStructure`

## Module Design

**Exports:**
- Public API: class + convenience function pair:
  ```python
  class IonInserter:
      def replace_water_with_ions(self, ...) -> IonStructure: ...
  
  def insert_ions(structure, concentration_molar, ...) -> IonStructure:
      """Convenience function to insert ions into a structure."""
  ```
- Private helpers prefixed with underscore: `_build_existing_atoms_tree()`, `_check_solute_overlap()`

**Barrel Files:**
- `__init__.py` files exist but are minimal (no re-exports)
- Import directly from submodules:
  ```python
  from quickice.structure_generation.ion_inserter import IonInserter, AVOGADRO
  from quickice.output.gromacs_writer import write_gro_file, write_top_file
  ```

## Attribute Propagation Convention

**Duck-typing for cross-structure attribute propagation:**
- Use `getattr(structure, 'custom_molecule_count', 0)` to safely read optional attributes
- Use `hasattr(structure, 'custom_molecule_atom_count')` before accessing
- Pattern for preserving attributes across workflow chains:
  ```python
  # Preserve solute information from input structure
  solute_type = getattr(structure, 'solute_type', "")
  solute_positions = getattr(structure, 'solute_positions', None)
  ```
- Custom molecule attributes propagated through: Interface → Custom → Solute → Ion workflow chain
- Set attributes on NEW objects, never on input structures

---

*Convention analysis: 2026-06-18*
