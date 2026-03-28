# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
quickice/
├── quickice/                 # Main package source
│   ├── __init__.py           # Package init, version
│   ├── main.py               # CLI entry point
│   ├── cli/                  # CLI argument parsing
│   ├── validation/           # Input validators
│   ├── phase_mapping/        # Ice phase identification
│   ├── structure_generation/ # Ice structure generation
│   ├── ranking/              # Candidate ranking
│   └── output/               # Output and visualization
├── tests/                    # Test suite (mirrors package structure)
├── .planning/                # Planning documents
├── quickice.py               # Entry script
├── env.yml                   # Conda environment
├── requirements-dev.txt      # Development dependencies
└── README.md                 # Project documentation
```

## Directory Purposes

**quickice/:**
- Purpose: Main package source code
- Contains: All Python modules organized by pipeline phase
- Key files: `main.py` (orchestrator), `__init__.py` (package init)

**quickice/cli/:**
- Purpose: Command-line interface
- Contains: Argument parser setup
- Key files: `parser.py` (argparse configuration)

**quickice/validation/:**
- Purpose: Input validation for CLI
- Contains: Type validator functions
- Key files: `validators.py` (temperature, pressure, nmolecules validators)

**quickice/phase_mapping/:**
- Purpose: Ice phase identification from T,P conditions
- Contains: Curve-based lookup, boundary functions, triple points, melting curves
- Key files: `lookup.py` (main API), `melting_curves.py` (IAPWS equations), `solid_boundaries.py` (interpolation), `triple_points.py` (data), `errors.py` (exceptions)
- Subdirectory: `data/ice_boundaries.py` (detailed boundary coefficients)

**quickice/structure_generation/:**
- Purpose: Ice structure generation using GenIce
- Contains: Generator class, phase mapping, supercell logic, types
- Key files: `generator.py` (IceStructureGenerator class), `mapper.py` (phase→GenIce mapping), `types.py` (Candidate, GenerationResult), `errors.py` (exceptions)

**quickice/ranking/:**
- Purpose: Score and rank candidates
- Contains: Scoring functions, types
- Key files: `scorer.py` (energy, density, diversity scoring, rank_candidates), `types.py` (RankedCandidate, RankingResult)

**quickice/output/:**
- Purpose: Output files, validation, visualization
- Contains: PDB writer, validator, phase diagram generator, orchestrator
- Key files: `orchestrator.py` (output_ranked_candidates), `pdb_writer.py` (PDB format), `validator.py` (spglib validation), `phase_diagram.py` (matplotlib visualization), `types.py` (OutputResult)

**tests/:**
- Purpose: Test suite
- Contains: Unit and integration tests
- Key files: `test_phase_mapping.py`, `test_structure_generation.py`, `test_ranking.py`, `test_validators.py`, `test_cli_integration.py`
- Subdirectory: `test_output/` (output-specific tests)

**.planning/:**
- Purpose: Project planning documents
- Contains: Phase plans, research notes, codebase analysis
- Key files: Organized by phase number

## Key File Locations

**Entry Points:**
- `quickice.py`: Script entry point (imports from `quickice.main`)
- `quickice/main.py`: `main()` function orchestrates pipeline
- `quickice/__init__.py`: Package initialization

**Configuration:**
- `env.yml`: Conda environment specification
- `requirements-dev.txt`: Development dependencies (pytest)
- `opencode.json`: OpenCode configuration

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: `lookup_phase()` - main phase identification API
- `quickice/structure_generation/generator.py`: `IceStructureGenerator` - GenIce wrapper
- `quickice/ranking/scorer.py`: `rank_candidates()` - scoring and ranking
- `quickice/output/orchestrator.py`: `output_ranked_candidates()` - output coordination

**Data Files:**
- `quickice/phase_mapping/triple_points.py`: TRIPLE_POINTS dictionary
- `quickice/phase_mapping/data/ice_boundaries.py`: MELTING_CURVE_COEFFICIENTS, PHASE_POLYGONS

**Testing:**
- `tests/test_phase_mapping.py`: Phase identification tests (593 lines)
- `tests/test_structure_generation.py`: Structure generation tests (567 lines)
- `tests/test_ranking.py`: Ranking tests
- `tests/test_validators.py`: Input validation tests

## Naming Conventions

**Files:**
- Python modules: snake_case (e.g., `melting_curves.py`, `solid_boundaries.py`)
- Test files: `test_<module>.py` (e.g., `test_phase_mapping.py`)
- Entry script: lowercase no extension pattern (`quickice.py`)

**Directories:**
- Package directories: snake_case (e.g., `phase_mapping`, `structure_generation`)
- Test directories mirror package structure

**Classes:**
- PascalCase (e.g., `IcePhaseLookup`, `IceStructureGenerator`, `Candidate`, `GenerationResult`)
- Exception suffix: `Error` (e.g., `UnknownPhaseError`, `UnsupportedPhaseError`)

**Functions:**
- snake_case (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)
- Private functions: underscore prefix (e.g., `_build_result`, `_linear_interpolate`)

**Constants:**
- UPPER_SNAKE_CASE (e.g., `TRIPLE_POINTS`, `PHASE_TO_GENICE`, `IDEAL_OO_DISTANCE`)

**Variables:**
- snake_case with descriptive names
- Short names in small scopes (e.g., `T`, `P` for temperature/pressure)

## Where to Add New Code

**New Feature:**
- Primary code: Create module in appropriate layer directory
- Tests: Create `tests/test_<module>.py`
- Update `__init__.py`: Export new public API

**New Ice Phase:**
- Phase mapping: Add to `PHASE_METADATA` in `quickice/phase_mapping/lookup.py`
- Structure generation: Add to `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES` in `quickice/structure_generation/mapper.py`
- Boundaries: Add boundary function in `quickice/phase_mapping/solid_boundaries.py`
- Triple points: Add to `TRIPLE_POINTS` in `quickice/phase_mapping/triple_points.py`
- Phase diagram: Add polygon builder and colors in `quickice/output/phase_diagram.py`

**New Component/Module:**
- Implementation: Create new directory under `quickice/` with `__init__.py`
- Types: Create `types.py` for dataclasses
- Errors: Create `errors.py` for custom exceptions
- API: Export from `__init__.py`

**Utilities:**
- Shared helpers: Add to module that needs them first
- If truly cross-cutting: Create `utils.py` in package root

**New CLI Option:**
- Parser: Add argument in `quickice/cli/parser.py`
- Validation: Add validator in `quickice/validation/validators.py` if needed
- Main: Handle in `quickice/main.py`

## Special Directories

**.planning/:**
- Purpose: Project planning and phase documentation
- Generated: No (manually created)
- Committed: Yes
- Subdirectories: `phases/`, `research/`, `codebase/`, `quick/`, `debug/`

**.pytest_cache/:**
- Purpose: pytest cache
- Generated: Yes (by pytest)
- Committed: No (in .gitignore)

**__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python)
- Committed: No (in .gitignore)

**tests/test_output/:**
- Purpose: Tests specific to output module
- Generated: No
- Committed: Yes
- Contains: `test_validator.py`, `test_pdb_writer.py`

## Module Organization Pattern

Each major module follows this pattern:

```
module_name/
├── __init__.py      # Public API exports
├── types.py         # Dataclasses and type definitions
├── errors.py        # Custom exceptions (if needed)
├── <main_logic>.py  # Core implementation
└── data/            # Data files (optional)
    └── __init__.py
```

Example: `structure_generation/`
- `__init__.py` → exports `generate_candidates`, `Candidate`, `GenerationResult`
- `types.py` → `Candidate`, `GenerationResult` dataclasses
- `errors.py` → `StructureGenerationError`, `UnsupportedPhaseError`
- `generator.py` → `IceStructureGenerator` class
- `mapper.py` → `PHASE_TO_GENICE`, `calculate_supercell`

---

*Structure analysis: 2026-03-28*
