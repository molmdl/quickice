# Coding Conventions

**Analysis Date:** 2026-04-10

## Naming Patterns

**Files:**
- Module files use `snake_case.py`: `interface_builder.py`, `water_filler.py`, `phase_diagram.py`
- Test files use `test_` prefix: `test_validators.py`, `test_ranking.py`
- Submodule directories use `snake_case`: `structure_generation/`, `phase_mapping/`, `output/`
- Data files use lowercase: `tip4p.gro`, `ice_phases.json`
- Type/data modules named `types.py`, error modules named `errors.py`

**Classes:**
- Use `PascalCase`: `IceStructureGenerator`, `GenerationResult`, `InterfaceConfig`, `RankedCandidate`
- Exception classes follow hierarchy pattern: `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`
- Exception classes inherit from domain base: `PhaseMappingError` → `UnknownPhaseError`

**Functions:**
- Public API functions use `snake_case`: `lookup_phase()`, `generate_candidates()`, `rank_candidates()`
- Private/internal functions use `_snake_case` prefix: `_calculate_oo_distances_pbc()`, `_calculate_cell_parameters()`, `_pbc_distance()`
- Validation functions use `validate_` prefix: `validate_temperature()`, `validate_pressure()`, `validate_nmolecules()`, `validate_interface_config()`
- Factory/class methods use `from_` prefix: `InterfaceConfig.from_dict()`

**Variables:**
- Constants use `UPPER_SNAKE_CASE`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `MINIMUM_BOX_DIMENSION`, `TIP4P_ICE_ALPHA`
- Regular variables use `snake_case`: `phase_info`, `nmolecules`, `scoring_metadata`
- Physical constants with values in comments: `AVOGADRO = 6.022e23`, `WATER_MASS = 18.01528`

**Types:**
- Type annotations use modern Python syntax: `list[str]`, `dict[str, Any]`, `int | None` (not `Optional[int]` in newer code)
- `typing` module used for `Any`, `Optional`, `List` (older style) in some files
- Dataclasses used extensively for structured data: `Candidate`, `GenerationResult`, `InterfaceConfig`, `RankedCandidate`, `RankingResult`, `ScoringConfig`, `OutputResult`, `InterfaceStructure`

## Code Style

**Formatting:**
- No formal formatter config detected (no `.prettierrc`, `.editorconfig`, `biome.json`, etc.)
- Indentation: 4 spaces
- Line length: Generally under 100 chars, with docstrings occasionally longer
- String quotes: Single quotes for short strings, double quotes for docstrings and f-strings

**Linting:**
- No formal linter config detected (no `.eslintrc`, `flake8`, `pylintrc`, etc.)
- Code follows consistent style organically

**Key Style Rules Observed:**
- Always use f-strings for string formatting, not `.format()` or `%`
- Use `np.array()` for NumPy array creation (not `list` conversions)
- Use `Path` from `pathlib` for file operations, not `os.path`
- Use `math.ceil()` for ceiling operations, not custom implementations
- Use `dataclass` for structured data with `field(default_factory=dict)` for mutable defaults
- Unit annotations in variable names: positions in nm, `cell` vectors in nm, Angstrom conversions multiplied by 10.0
- Physical constants documented with units: `# g/cm³`, `# nm`, `# molecules/mol`

## Import Organization

**Order:**
1. Standard library: `import argparse`, `import math`, `import time`, `from pathlib import Path`
2. Third-party: `import numpy as np`, `import pytest`, `from PySide6.QtWidgets import ...`, `from scipy.spatial import cKDTree`
3. Local imports: `from quickice.structure_generation.types import Candidate`

**Pattern:**
```python
# Standard library
import sys
from pathlib import Path
from typing import Optional

# Third-party
import numpy as np
from scipy.spatial import cKDTree

# Local imports
from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankedCandidate, RankingResult, ScoringConfig
```

**Path Aliases:**
- No import aliases used (no `import quickice.structure_generation as sg`)
- `numpy` always imported as `np`
- Module-level imports from subpackages through `__init__.py`

## Error Handling

**Custom Exception Hierarchy:**
- Domain base exceptions: `StructureGenerationError`, `PhaseMappingError`
- Specific exceptions inherit from domain base: `UnsupportedPhaseError(StructureGenerationError)`, `InterfaceGenerationError(StructureGenerationError)`, `UnknownPhaseError(PhaseMappingError)`
- Each exception carries contextual attributes: `UnsupportedPhaseError(phase_id=...)`, `InterfaceGenerationError(mode=...)`, `UnknownPhaseError(temperature=..., pressure=...)`

**Error Messages:**
- Use descriptive multi-line messages with context, explanation, and remediation
- Pattern in `quickice/structure_generation/interface_builder.py`: error messages include "How to fix:" sections with specific values
- Example: `"Water layer too thin in X dimension.\n\nCalculation:\n  Water layer X = Box X ({config.box_x:.2f} nm) - Ice X ({ice_dims[0]:.2f} nm)\n  = {water_layer_x:.3f} nm\n\n..."`

**Exception Raising Patterns:**
- Validation functions raise `ArgumentTypeError` for CLI input errors: `raise ArgumentTypeError(f"Temperature must be between 0 and 500K, got {temp}K")`
- Domain functions raise custom exceptions with `from e` chaining: `raise StructureGenerationError(f"Failed to generate...") from e`
- Error propagation in CLI: `main()` catches `UnknownPhaseError` separately from general `Exception`

**Return Values for Errors:**
- Functions that can fail return typed results or raise exceptions (no sentinel values)
- `validate_space_group()` returns dict with `'valid': True/False` rather than raising
- `check_atomic_overlap()` returns bool rather than raising

## Logging

**Framework:** Python `logging` module (standard library)

**Patterns:**
- Used in `quickice/output/orchestrator.py` with `logging.warning()`
- Pattern: `logging.warning(f"Failed to write PDB for rank {rank}: {e}")`
- No custom logger configuration; relies on default Python logging
- GUI uses Qt Signal-based status updates, not Python logging

**When to Log:**
- Non-fatal failures during output writing (PDB generation, phase diagram)
- Validation failures that are recovered from
- Not used for normal flow; exceptions handle error cases

## Comments

**When to Comment:**
- Every module has a module-level docstring explaining purpose
- Every public function and class has a docstring with Args, Returns, Raises sections
- Docstrings use triple-double-quote style: `"""Docstring."""`
- Inline comments for physical unit notes: `# nm`, `# g/cm³`, `# Angstrom`
- Scientific references documented: `# IAPWS R14-08(2011)`, `# Journaux et al. (2019, 2020)`

**JSDoc/TSDoc (Python Docstrings):**
- Full Google-style docstrings with Args, Returns, Raises, Note, Example sections
- Example from `quickice/structure_generation/generator.py`:
```python
def generate_candidates(
    phase_info: dict,
    nmolecules: int,
    n_candidates: int = 10,
    base_seed: int | None = None,
) -> GenerationResult:
    """Generate multiple ice structure candidates.

    ...

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

## Function Design

**Size:** Functions typically 20-80 lines. Long functions like `lookup_phase()` (~300 lines) are the exception and handle complex multi-branch logic.

**Parameters:**
- Use type annotations on all public functions
- Default values for optional parameters: `n_candidates: int = 10`, `base_seed: int | None = None`
- Configuration objects (dataclasses) for complex parameter groups: `InterfaceConfig`, `ScoringConfig`
- `from_dict` class methods for dict-to-dataclass conversion: `InterfaceConfig.from_dict()`

**Return Values:**
- Use dataclasses for multi-value returns: `GenerationResult`, `RankingResult`, `OutputResult`
- Use tuples for simple multi-returns: `calculate_supercell()` returns `tuple[np.ndarray, int]`
- Use dicts for flexible results: `lookup_phase()` returns `dict` with keys `phase_id`, `phase_name`, `density`, `temperature`, `pressure`
- Functions that can fail: return typed result on success, raise exception on failure (no None returns)

## Module Design

**Exports:**
- Each package has an `__init__.py` that re-exports public API
- `__all__` lists define the public interface explicitly
- Example from `quickice/ranking/__init__.py`: exports types, main API, and individual scorers
- Example from `quickice/structure_generation/__init__.py`: comprehensive `__all__` with types, errors, functions

**Barrel Files:**
- `__init__.py` files serve as barrel/entry-point files
- They import from internal modules and re-export via `__all__`
- External code imports from the package, not internal modules: `from quickice.ranking import rank_candidates`
- Internal cross-module imports use full path: `from quickice.structure_generation.types import Candidate`

**Package Organization Pattern:**
```
quickice/
├── __init__.py          # Version only
├── main.py              # CLI entry point
├── cli/
│   ├── __init__.py
│   └── parser.py
├── phase_mapping/
│   ├── __init__.py      # Re-exports
│   ├── lookup.py        # Core logic
│   ├── errors.py         # Custom exceptions
│   ├── types.py          # (none, uses dicts)
│   ├── melting_curves.py
│   ├── solid_boundaries.py
│   ├── triple_points.py
│   └── data/
│       ├── __init__.py
│       └── ice_boundaries.py
├── structure_generation/
│   ├── __init__.py      # Re-exports
│   ├── types.py          # Dataclasses
│   ├── errors.py         # Custom exceptions
│   ├── generator.py      # Core logic
│   ├── mapper.py         # Mapping constants/logic
│   ├── interface_builder.py
│   ├── water_filler.py
│   ├── overlap_resolver.py
│   └── modes/
│       ├── __init__.py
│       ├── slab.py
│       ├── pocket.py
│       └── piece.py
├── ranking/
│   ├── __init__.py      # Re-exports
│   ├── types.py          # Dataclasses
│   └── scorer.py         # Scoring functions
├── output/
│   ├── __init__.py      # Re-exports
│   ├── types.py          # Dataclasses
│   ├── orchestrator.py   # Main entry
│   ├── pdb_writer.py
│   ├── validator.py
│   ├── phase_diagram.py
│   └── gromacs_writer.py
├── validation/
│   ├── __init__.py
│   └── validators.py
└── gui/
    ├── __init__.py
    ├── __main__.py
    ├── main_window.py     # MVVM View
    ├── viewmodel.py       # MVVM ViewModel
    ├── view.py            # UI components
    ├── workers.py         # QThread workers
    ├── validators.py      # GUI validators
    ├── interface_panel.py
    ├── molecular_viewer.py
    ├── interface_viewer.py
    ├── dual_viewer.py
    ├── phase_diagram_widget.py
    ├── vtk_utils.py
    ├── export.py
    └── help_dialog.py
```

## Data Model Conventions

**Unit Conventions:**
- All internal coordinates in **nanometers (nm)** - documented in docstrings
- Cell vectors stored as row vectors in `(3, 3)` arrays
- Conversion to Angstrom done at export time (multiply by 10.0)
- `overlap_threshold` parameter uses nm with range validation in `InterfaceConfig.__post_init__()`
- Physical constants: `AVOGADRO = 6.022e23`, `WATER_MASS = 18.01528 g/mol`

**Dataclass Patterns:**
- Use `@dataclass` decorator without `frozen=True`
- Default mutable fields use `field(default_factory=dict)`: `metadata: dict[str, Any] = field(default_factory=dict)`
- `__post_init__` for validation: `InterfaceConfig.__post_init__()` validates `overlap_threshold` range
- Class methods for alternative construction: `InterfaceConfig.from_dict()`
- Nested dataclass references: `RankedCandidate.candidate: Candidate`

**Dict vs Dataclass:**
- Phase mapping returns dicts (legacy design): `lookup_phase()` returns `dict[str, Any]`
- Structure generation uses dataclasses (modern design): `Candidate`, `GenerationResult`
- Ranking uses dataclasses: `RankedCandidate`, `RankingResult`, `ScoringConfig`
- Output uses dataclasses: `OutputResult`

---

*Convention analysis: 2026-04-10*