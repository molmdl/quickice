# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```
quickice/
├── quickice/              # Main package
│   ├── cli/               # CLI argument parsing
│   ├── validation/        # Input validators
│   ├── phase_mapping/     # Phase lookup logic
│   │   └── data/          # Phase boundary data
│   ├── structure_generation/  # GenIce wrapper
│   ├── ranking/           # Candidate scoring
│   ├── output/            # PDB/diagram output
│   ├── gui/               # GUI (PySide6/Qt)
│   └── data/              # Static data files (ITP, GRO)
├── tests/                 # Test suite
│   └── test_output/       # Output module tests
├── docs/                  # Documentation
│   └── images/            # Documentation images
├── .planning/             # Planning documents
├── scripts/               # Build/utility scripts
├── sample_output/         # Example output files
├── tmp/                   # Temporary test output
├── dist/                  # PyInstaller output
└── build/                 # Build artifacts
```

## Directory Purposes

**quickice/:**
- Purpose: Main Python package
- Contains: All source modules, __init__.py with version
- Key files: `main.py` (CLI entry), `__init__.py` (package init)

**quickice/cli/:**
- Purpose: CLI interface
- Contains: Argument parser configuration
- Key files: `parser.py` (argparse setup)

**quickice/validation/:**
- Purpose: Input validation
- Contains: Validators for temperature, pressure, molecule count
- Key files: `validators.py` (type validation functions)

**quickice/phase_mapping/:**
- Purpose: Ice phase identification
- Contains: Curve-based lookup, boundary functions, triple points
- Key files: `lookup.py` (main API), `melting_curves.py`, `solid_boundaries.py`

**quickice/structure_generation/:**
- Purpose: Ice structure generation
- Contains: GenIce wrapper, phase mapping, supercell calculation
- Key files: `generator.py` (IceStructureGenerator), `mapper.py` (phase → lattice)

**quickice/ranking/:**
- Purpose: Candidate scoring and ranking
- Contains: Energy, density, diversity scorers
- Key files: `scorer.py` (rank_candidates)

**quickice/output/:**
- Purpose: File output and validation
- Contains: PDB writer, GROMACS writer, validator, diagram generator
- Key files: `orchestrator.py` (main API), `pdb_writer.py`, `gromacs_writer.py`

**quickice/gui/:**
- Purpose: Graphical user interface
- Contains: View, ViewModel, Workers, 3D viewers, panels
- Key files: `main_window.py` (MainWindow), `viewmodel.py`, `workers.py`

**quickice/data/:**
- Purpose: Static data files
- Contains: TIP4P-ICE ITP file, reference GRO structure
- Key files: `tip4p-ice.itp`, `tip4p.gro`

**tests/:**
- Purpose: Unit and integration tests
- Contains: Test files for each module
- Key files: `test_phase_mapping.py`, `test_structure_generation.py`, `test_ranking.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry script (root directory)
- `quickice/main.py`: CLI main function
- `quickice/gui/__main__.py`: GUI entry point

**Configuration:**
- `requirements-dev.txt`: Development dependencies
- `environment.yml`: Conda environment specification
- `opencode.json`: OpenCode tool configuration

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Phase lookup algorithm
- `quickice/structure_generation/generator.py`: Structure generation
- `quickice/ranking/scorer.py`: Scoring functions
- `quickice/output/orchestrator.py`: Output coordination

**Types:**
- `quickice/structure_generation/types.py`: Candidate, GenerationResult
- `quickice/ranking/types.py`: RankedCandidate, RankingResult
- `quickice/output/types.py`: OutputResult

**Errors:**
- `quickice/phase_mapping/errors.py`: PhaseMappingError, UnknownPhaseError
- `quickice/structure_generation/errors.py`: StructureGenerationError

**Testing:**
- `tests/test_validators.py`: Validation tests
- `tests/test_phase_mapping.py`: Phase mapping tests
- `tests/test_structure_generation.py`: Generation tests
- `tests/test_ranking.py`: Ranking tests
- `tests/test_output/`: Output module tests

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `pdb_writer.py`, `melting_curves.py`)
- Tests: `test_<module>.py` (e.g., `test_ranking.py`)
- Types: `types.py` (dataclasses)
- Errors: `errors.py` (custom exceptions)
- Init: `__init__.py` (public API exports)

**Directories:**
- Modules: `snake_case/` (e.g., `phase_mapping/`, `structure_generation/`)
- Tests: `tests/` (mirrors package structure)
- Planning: `.planning/` (plans, phases, research)

**Classes:**
- PascalCase (e.g., `IceStructureGenerator`, `RankedCandidate`, `MainWindow`)

**Functions:**
- snake_case (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)

**Variables:**
- snake_case (e.g., `temperature`, `phase_info`, `n_candidates`)

## Where to Add New Code

**New Feature (pipeline stage):**
- Create new module: `quickice/<feature>/`
- Add files: `__init__.py`, `types.py`, `<feature>.py`, `errors.py`
- Export public API in `__init__.py`
- Add tests: `tests/test_<feature>.py`

**New Component/Module:**
- Implementation: `quickice/<module>/<component>.py`
- Types: `quickice/<module>/types.py`
- Tests: `tests/test_<module>.py`

**New GUI Panel:**
- Panel widget: `quickice/gui/<panel_name>_panel.py`
- Add to MainWindow: `quickice/gui/main_window.py`
- Connect signals in `_setup_connections()`

**New Scoring Function:**
- Add to: `quickice/ranking/scorer.py`
- Update `rank_candidates()` to include new score
- Add tests: `tests/test_ranking.py`

**New Output Format:**
- Writer: `quickice/output/<format>_writer.py`
- Add to orchestrator: `quickice/output/orchestrator.py`
- Export in `quickice/output/__init__.py`

**Utilities:**
- Shared helpers: Create `quickice/utils.py` if needed
- Module-specific: Keep in module file

**Data Files:**
- Static data: `quickice/data/`
- Generated data: `output/` or user-specified directory

## Special Directories

**.planning/:**
- Purpose: GSD planning documents, phases, research
- Generated: Yes (by GSD tools)
- Committed: Yes (tracks planning history)

**__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (Python automatically)
- Committed: No (in .gitignore)

**.pytest_cache/:**
- Purpose: pytest cache and test discovery
- Generated: Yes (pytest automatically)
- Committed: No (in .gitignore)

**dist/:**
- Purpose: PyInstaller build output (standalone executable)
- Generated: Yes (build process)
- Committed: No (artifacts)

**build/:**
- Purpose: Build intermediate files
- Generated: Yes (build process)
- Committed: No (artifacts)

**tmp/:**
- Purpose: Temporary test output
- Generated: Yes (tests)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-04-07*
