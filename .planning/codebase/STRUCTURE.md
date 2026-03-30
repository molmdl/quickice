# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
quickice/
├── quickice.py              # CLI entry point
├── quickice/                # Main package
│   ├── __init__.py          # Package init, version
│   ├── main.py              # Main orchestrator
│   ├── cli/                 # CLI layer
│   │   ├── __init__.py
│   │   └── parser.py        # Argument parser
│   ├── validation/          # Input validation
│   │   ├── __init__.py
│   │   └── validators.py    # Range validators
│   ├── phase_mapping/       # Phase identification
│   │   ├── __init__.py      # Exports
│   │   ├── lookup.py        # Main lookup function
│   │   ├── errors.py        # Custom exceptions
│   │   ├── melting_curves.py # IAPWS melting equations
│   │   ├── solid_boundaries.py # Solid-solid boundaries
│   │   ├── triple_points.py # Triple point constants
│   │   └── data/            # Data subpackage
│   │       ├── __init__.py
│   │       └── ice_boundaries.py
│   ├── structure_generation/ # GenIce wrapper
│   │   ├── __init__.py      # Exports
│   │   ├── generator.py    # IceStructureGenerator class
│   │   ├── mapper.py        # Phase ID → GenIce mapping
│   │   ├── types.py         # Candidate, GenerationResult
│   │   └── errors.py        # Custom exceptions
│   ├── ranking/             # Candidate scoring
│   │   ├── __init__.py      # Exports
│   │   ├── scorer.py        # Scoring functions
│   │   └── types.py         # RankedCandidate, RankingResult
│   └── output/              # Output generation
│       ├── __init__.py      # Exports
│       ├── orchestrator.py  # Main output coordinator
│       ├── pdb_writer.py    # PDB file writer
│       ├── validator.py     # Structure validation
│       ├── phase_diagram.py # Diagram generation
│       └── types.py         # OutputResult
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_cli_integration.py
│   ├── test_phase_mapping.py
│   ├── test_structure_generation.py
│   ├── test_ranking.py
│   ├── test_validators.py
│   └── test_output/         # Output tests
│       ├── __init__.py
│       ├── test_validator.py
│       └── test_pdb_writer.py
├── docs/                    # Documentation
├── sample_output/           # Example output files
├── .planning/               # Planning documents
├── requirements-dev.txt     # Dev dependencies
├── README.md               # Project readme
└── env.yml                 # Conda environment
```

## Directory Purposes

**quickice/ (package root):**
- Purpose: Main Python package
- Contains: All modules organized by functional layer
- Key files: `__init__.py` (version), `main.py` (orchestrator)

**quickice/cli/:**
- Purpose: Command-line interface
- Contains: Argument parser configuration
- Key files: `parser.py` (argparse setup)

**quickice/validation/:**
- Purpose: Input validation
- Contains: Type validators for CLI arguments
- Key files: `validators.py` (validate_temperature, validate_pressure, validate_nmolecules)

**quickice/phase_mapping/:**
- Purpose: Ice phase identification from T, P conditions
- Contains: Phase lookup algorithm, boundary curves, triple points
- Key files: `lookup.py` (lookup_phase function), `melting_curves.py` (IAPWS equations)

**quickice/structure_generation/:**
- Purpose: Ice structure generation using GenIce
- Contains: Generator class, phase-to-lattice mapping, types
- Key files: `generator.py` (IceStructureGenerator), `mapper.py` (PHASE_TO_GENICE dict)

**quickice/ranking/:**
- Purpose: Candidate scoring and ranking
- Contains: Energy, density, diversity scoring functions
- Key files: `scorer.py` (rank_candidates, energy_score, density_score, diversity_score)

**quickice/output/:**
- Purpose: File output and phase diagram generation
- Contains: PDB writer, structure validator, diagram generator
- Key files: `orchestrator.py` (output_ranked_candidates), `phase_diagram.py` (generate_phase_diagram)

**tests/:**
- Purpose: Unit and integration tests
- Contains: pytest test modules mirroring package structure
- Key files: `test_structure_generation.py`, `test_phase_mapping.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry point (run with `python quickice.py`)
- `quickice/main.py`: Main orchestration function `main()`

**Configuration:**
- `requirements-dev.txt`: Development dependencies (pytest)
- `env.yml`: Conda environment specification

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Phase identification algorithm (388 lines)
- `quickice/structure_generation/generator.py`: Structure generation (269 lines)
- `quickice/ranking/scorer.py`: Scoring functions (345 lines)
- `quickice/output/orchestrator.py`: Output coordination (141 lines)

**Data & Constants:**
- `quickice/structure_generation/mapper.py`: PHASE_TO_GENICE mapping, UNIT_CELL_MOLECULES
- `quickice/phase_mapping/triple_points.py`: Triple point coordinates
- `quickice/phase_mapping/melting_curves.py`: IAPWS melting curve equations
- `quickice/phase_mapping/solid_boundaries.py`: Solid-solid boundary equations

**Types:**
- `quickice/structure_generation/types.py`: Candidate, GenerationResult dataclasses
- `quickice/ranking/types.py`: RankedCandidate, RankingResult dataclasses
- `quickice/output/types.py`: OutputResult dataclass

**Testing:**
- `tests/test_structure_generation.py`: Generator and mapper tests (567 lines)
- `tests/test_phase_mapping.py`: Phase lookup tests
- `tests/test_ranking.py`: Scoring function tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `melting_curves.py`, `pdb_writer.py`)
- Test files: `test_<module>.py` (e.g., `test_ranking.py`)
- Package inits: `__init__.py` with module docstring

**Functions:**
- Public API: `snake_case` (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)
- Private helpers: `_leading_underscore` (e.g., `_build_result`, `_parse_gro`, `_calculate_oo_distances_pbc`)
- Validators: `validate_<noun>` (e.g., `validate_temperature`)

**Classes:**
- Class names: `PascalCase` (e.g., `IceStructureGenerator`, `IcePhaseLookup`, `Candidate`)
- Exceptions: `<Name>Error` (e.g., `PhaseMappingError`, `UnknownPhaseError`, `StructureGenerationError`)

**Variables:**
- Local variables: `snake_case` (e.g., `phase_info`, `candidates`, `n_molecules`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `TRIPLE_POINTS`)

**Dataclasses:**
- Field names: `snake_case` (e.g., `nmolecules`, `phase_id`, `was_rounded`)
- No leading underscores for fields

## Where to Add New Code

**New Ice Phase:**
- Phase mapping: Add entry to `PHASE_METADATA` in `quickice/phase_mapping/lookup.py`
- Structure generation: Add mapping in `PHASE_TO_GENICE` in `quickice/structure_generation/mapper.py`
- Output: Add color/label in `PHASE_COLORS`, `PHASE_LABELS` in `quickice/output/phase_diagram.py`
- Boundary: Add boundary functions in `quickice/phase_mapping/solid_boundaries.py`

**New Scoring Metric:**
- Add scoring function in `quickice/ranking/scorer.py`
- Add score fields to `RankedCandidate` in `quickice/ranking/types.py`
- Update `rank_candidates()` to include new score

**New Output Format:**
- Add writer function in `quickice/output/`
- Export from `quickice/output/__init__.py`
- Update `output_ranked_candidates()` in `quickice/output/orchestrator.py`

**New CLI Option:**
- Add argument in `quickice/cli/parser.py`
- Update `main()` in `quickice/main.py` to handle new option

**New Test:**
- Create test file in `tests/` mirroring module structure
- Use pytest fixtures for common setup

**New Utility:**
- If used by multiple modules: Create new module in `quickice/`
- If used locally: Add as private function in existing module

## Special Directories

**.planning/:**
- Purpose: Planning documents for GSD workflow
- Contains: Phase plans, research notes, codebase analysis
- Generated: Yes (by GSD commands)
- Committed: Yes (for reference)

**docs/:**
- Purpose: Project documentation
- Contains: User-facing documentation
- Generated: No (manually maintained)
- Committed: Yes

**sample_output/:**
- Purpose: Example output files for reference
- Contains: Generated PDB files, phase diagrams
- Generated: Yes (by running the tool)
- Committed: Yes (for demonstration)

**.pytest_cache/:**
- Purpose: Pytest cache directory
- Contains: Test cache files
- Generated: Yes (automatically)
- Committed: No (in .gitignore)

**__pycache__/:**
- Purpose: Python bytecode cache
- Contains: .pyc files
- Generated: Yes (automatically)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-03-30*