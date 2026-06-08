# Coding Conventions

**Analysis Date:** 2026-06-08

## Naming Patterns

**Files:**
- Source modules: `snake_case.py` (e.g., `ion_inserter.py`, `hydrate_generator.py`, `gromacs_writer.py`)
- Test files: `test_<module>.py` for unit tests (e.g., `test_validators.py`, `test_ranking.py`)
- Test files: `test_e2e_<feature>.py` for end-to-end tests (e.g., `test_e2e_ice_generation.py`, `test_e2e_gmx_validation.py`)
- GUI panel files: `<feature>_panel.py`, `<feature>_viewer.py`, `<feature>_renderer.py` (e.g., `hydrate_panel.py`, `hydrate_viewer.py`, `hydrate_renderer.py`)
- Helper files: Descriptive `snake_case.py` (e.g., `e2e_export_helpers.py`)
- Data files: `.gro`, `.itp`, `.mdp` (GROMACS format files in `quickice/data/`)

**Functions:**
- Public functions: `snake_case` (e.g., `lookup_phase()`, `generate_interface()`, `rank_candidates()`)
- Private/internal functions: `_leading_underscore` (e.g., `_generate_single()`, `_parse_gro_result()`)
- Test helper functions: `_leading_underscore` (e.g., `_insert_ions()`, `_solute_to_ion_source()`)
- Validators: `validate_<field>` (e.g., `validate_temperature()`, `validate_pressure()`)
- Factory class methods: `from_<source>` (e.g., `InterfaceConfig.from_dict()`, `HydrateLatticeInfo.from_lattice_type()`)

**Variables:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `PHASE_CONDITIONS`, `HYDRATE_LATTICES`, `UNIT_CELL_MOLECULES`, `AVOGADRO`, `MIN_SEPARATION`)
- Instance attributes: `snake_case` with leading underscore for private (e.g., `self._temperature`, `self._is_generating`)
- Local variables: `snake_case` (e.g., `phase_info`, `candidate`, `volume_nm3`)
- NumPy arrays: descriptive names with type context (e.g., `positions`, `cell`, `supercell_o`, `o_positions`)

**Types:**
- Dataclasses: `PascalCase` (e.g., `Candidate`, `InterfaceConfig`, `HydrateStructure`, `IonStructure`)
- Exception classes: `PascalCase` with `Error` suffix (e.g., `StructureGenerationError`, `UnknownPhaseError`, `InterfaceGenerationError`)
- Worker classes: `PascalCase` with descriptive suffix (e.g., `GenerationWorker`, `InterfaceGenerationWorker`)
- PySide6 widget classes: `PascalCase` with `Widget`/`Panel` suffix (e.g., `HydratePanel`, `PhaseDiagramWidget`)

## Code Style

**Formatting:**
- No formal formatter config detected (no `.prettierrc`, no `black` config, no `ruff.toml`)
- Python 3.14 with modern syntax: `X | None` union types instead of `Optional[X]` (e.g., `seed: int | None = None`)
- `list[str]`, `dict[str, Any]` generic syntax (not `List[str]`, `Dict[str, Any]`)
- `from __future__ import annotations` is NOT used — project targets Python 3.14 natively

**Linting:**
- No linter config detected (no `.eslintrc`, no `flake8`, no `pylint`, no `ruff`)
- Code follows PEP 8 conventions informally
- Use `logging.getLogger(__name__)` pattern — DO NOT use `print()` for library code

**Key Style Rules:**
- Docstrings: Triple-quoted with `"""..."""` for all public modules, classes, and functions
- Attribute docstrings in dataclasses use `Attributes:` section
- Method docstrings use `Args:`, `Returns:`, `Raises:` sections
- Class-level docstrings include `Signals:` section for PySide6 objects
- Section separators use `# ── Section Name ─────` pattern in long files (see `conftest.py`)
- Unicode box drawing for test section headers: `# ══════════════════ Title ══════════════════` (see `test_e2e_gmx_validation.py`)

## Import Organization

**Order:**
1. Standard library (`import numpy as np`, `import time`, `from pathlib import Path`)
2. Third-party packages (`from PySide6.QtCore import ...`, `from genice2.genice import GenIce`, `from scipy.spatial import cKDTree`)
3. Local application imports (`from quickice.structure_generation.types import ...`, `from quickice.gui.workers import ...`)

**Path Aliases:**
- `numpy` is always imported as `np`
- `pytest` is always imported as `pytest`
- No other aliases used

**Circular Import Avoidance:**
- Use `TYPE_CHECKING` guard for type hints only (e.g., `gromacs_writer.py` line 18: `if TYPE_CHECKING: from quickice.structure_generation.types import CustomMoleculeStructure, SoluteStructure`)
- Use lazy imports inside `run()` methods of QThread workers (e.g., `workers.py` lines 88-89: `from quickice.phase_mapping import lookup_phase` inside `run()`)
- Use `Any` type annotation with comment for forward references (e.g., `registry: Any  # MoleculetypeRegistry (avoid circular import)`)

## Error Handling

**Patterns:**

1. **Custom exception hierarchy** with domain-specific base classes:
   - `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError` in `quickice/structure_generation/errors.py`
   - `PhaseMappingError` → `UnknownPhaseError` in `quickice/phase_mapping/errors.py`
   - Custom errors carry context attributes (e.g., `InterfaceGenerationError.mode`, `UnsupportedPhaseError.phase_id`, `UnknownPhaseError.temperature/pressure`)

2. **Validation in `__post_init__`**: All config dataclasses validate in `__post_init__` and raise `ValueError` with descriptive messages:
   ```python
   def __post_init__(self):
       if self.concentration_molar < 0:
           raise ValueError(f"concentration_molar must be >= 0, got {self.concentration_molar}")
   ```
   See `quickice/structure_generation/types.py` — `InterfaceConfig`, `HydrateConfig`, `IonConfig`, `SoluteConfig`, `CustomMoleculeConfig`

3. **CLI validators raise `ArgumentTypeError`** (from `argparse`):
   ```python
   from argparse import ArgumentTypeError
   raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")
   ```
   See `quickice/validation/validators.py`

4. **GUI validators return `tuple[bool, str]`** (no exceptions):
   ```python
   def validate_temperature(value: str) -> Tuple[bool, str]:
       if temp < 0 or temp > 500:
           return (False, "Temperature must be between 0 and 500 K")
       return (True, "")
   ```
   See `quickice/gui/validators.py`

5. **Exception wrapping with `from e`** for context preservation:
   ```python
   except Exception as e:
       raise StructureGenerationError(
           f'Failed to generate ice structure ({type(e).__name__}): {e}'
       ) from e
   ```
   See `quickice/structure_generation/generator.py` line 152

6. **`finally` blocks for state restoration** (e.g., numpy random state):
   ```python
   original_state = np.random.get_state()
   try:
       np.random.seed(seed)
       # ... generation code
   except Exception as e:
       raise StructureGenerationError(...) from e
   finally:
       np.random.set_state(original_state)
   ```
   See `quickice/structure_generation/generator.py` lines 101-157

## Logging

**Framework:** Python `logging` module

**Pattern:**
- Create logger at module level: `logger = logging.getLogger(__name__)`
- Used in ~20 source files across `quickice/` (GUI panels, renderers, core modules)
- Non-GUI code uses `logging` (e.g., `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/structure_generation/solute_inserter.py`)
- GUI panels use `logger.debug()` and `logger.info()` for user-facing operations
- Scientific computation modules use `logger.debug()` for numerical details
- `print()` is used ONLY in CLI entry points (`quickice/main.py`) for user output — NEVER in library code

**When to Log:**
- Use `logger.debug()` for diagnostic information (coordinates, intermediate values)
- Use `logger.info()` for significant events (generation started, export complete)
- Use `logger.warning()` for recoverable issues (skipped ITP, missing file)
- Use `logger.error()` for unrecoverable errors in library code

## Comments

**When to Comment:**
- Every module has a module-level docstring describing purpose
- Every public class has a docstring with `Attributes:` section
- Every public function/method has a docstring with `Args:`, `Returns:`, `Raises:` sections
- Inline comments explain physics/units (e.g., `# 0.25 nm = 2.5 Å for typical O-O overlap detection`)
- `Note:` sections for non-obvious behavior (e.g., wrapping, coordinate conventions)
- `IMPORTANT:` sections for critical constraints (e.g., "Do NOT wrap positions here!")

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Use Google-style docstrings with `Args:`, `Returns:`, `Raises:`, `Examples:` sections
- Physics references included in docstrings (e.g., "Petrenko & Whitworth, 1999, Physics of Ice")

## Function Design

**Size:** Functions range from 1-liner helpers to ~80 line methods. No strict limit, but complex logic is decomposed.

**Parameters:** Use type hints for all parameters. Use `dataclass` configs for multi-parameter functions instead of many arguments:
```python
# Instead of:
def generate(config_mode, box_x, box_y, box_z, seed, ...):
# Use:
def generate(config: InterfaceConfig):
```
See `quickice/structure_generation/types.py` for all config dataclasses.

**Return Values:**
- Use `dataclass` result types for complex returns (e.g., `GenerationResult`, `RankingResult`, `InterfaceStructure`)
- Use `tuple` for simple multi-value returns (e.g., `(exit_code, stderr_text)`)
- NumPy arrays for coordinate data: always `(N, 3)` shape with `dtype=np.float64`
- Cell matrices: always `(3, 3)` stored as ROW vectors

## Module Design

**Exports:**
- Use `__init__.py` with explicit `__all__` list for public API (see `quickice/structure_generation/__init__.py`)
- Import and re-export commonly-used types from `__init__.py`
- Private functions use `_leading_underscore`

**Barrel Files:**
- `quickice/structure_generation/__init__.py` re-exports key types and functions
- `quickice/ranking/__init__.py` re-exports ranking API
- `quickice/phase_mapping/__init__.py` re-exports `lookup_phase`, `UnknownPhaseError`
- Test helper modules are NOT `test_`-prefixed to avoid pytest auto-collection (see `e2e_export_helpers.py` line 7)

## MVVM Architecture Pattern

**Pattern:** Model-View-ViewModel with QThread workers

- **Model**: Domain logic in `quickice/structure_generation/`, `quickice/phase_mapping/`, `quickice/ranking/`
- **ViewModel**: `quickice/gui/viewmodel.py` — `MainViewModel(QObject)` with Qt signals
- **View**: `quickice/gui/view.py`, `*_panel.py`, `*_viewer.py` — PySide6 widgets
- **Workers**: `quickice/gui/workers.py` — `GenerationWorker(QObject)` with `run()` method moved to QThread

**Signal naming convention:**
- Past tense for completed events: `generation_complete`, `generation_error`, `generation_cancelled`
- State change: `ui_enabled_changed`, `generation_started`
- Streaming: `generation_progress(int)`, `generation_status(str)`, `generation_log(str)`

**Worker pattern (NOT subclassing QThread):**
```python
worker = GenerationWorker(temperature, pressure, nmolecules)
thread = QThread()
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.finished.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()
```

## Domain-Specific Conventions

**Units:**
- All coordinates in nanometers (nm) — NOT Angstroms
- Pressure in MPa
- Temperature in Kelvin
- Concentration in mol/L (M)
- Density in g/cm³
- Validation catches unit mismatches (e.g., `overlap_threshold` range check in `InterfaceConfig`)

**GROMACS File Format:**
- `.gro` files: GROMACS coordinate format with fixed-width columns
- `.top` files: GROMACS topology with `#include` directives for `.itp` files
- `.itp` files: Molecular topology include files
- `.mdp` files: Molecular dynamics parameters (e.g., `tests/em.mdp`)

**Atom naming:**
- TIP3P ice: O, H, H (3 atoms per molecule)
- TIP4P-ICE water: OW, HW1, HW2, MW (4 atoms per molecule)
- CH4 guest: C, H, H, H, H (5 atoms)
- THF guest: O, CA, CA, CB, CB + 8H (13 atoms)
- Ions: NA (Na+), CL (Cl-)

**Cell matrix convention:**
- `cell` is `(3, 3)` stored as ROW vectors
- Each row is a lattice vector: `[[a_x, a_y, a_z], [b_x, b_y, b_z], [c_x, c_y, c_z]]`
- Position transformation: `new_position = position @ cell`
- VTK requires column vectors (transpose needed)

---

*Convention analysis: 2026-06-08*
