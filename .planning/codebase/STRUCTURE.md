# Codebase Structure

**Analysis Date:** 2026-03-31

## Directory Layout

```
quickice/
├── quickice.py              # CLI entry point (user-facing script)
├── quickice/                # Main Python package
│   ├── __init__.py          # Package init, version
│   ├── main.py              # Pipeline orchestration
│   ├── cli/                 # Command-line interface
│   ├── validation/          # Input validation
│   ├── phase_mapping/       # T,P → ice phase lookup
│   ├── structure_generation/# GenIce2 integration
│   ├── ranking/             # Candidate scoring
│   └── output/              # PDB/diagram output
├── tests/                   # Test suite
├── docs/                    # Documentation
├── sample_output/           # Example output files
├── .planning/               # Project planning documents
├── env.yml                  # Conda environment specification
├── requirements-dev.txt     # Development dependencies
├── README.md                # Project documentation
├── LICENSE                  # MIT license
└── setup.sh                 # Environment setup script
```

## Directory Purposes

**`quickice/`:**
- Purpose: Main Python package containing all source code
- Contains: Six submodules (cli, validation, phase_mapping, structure_generation, ranking, output)
- Key files: `main.py` (orchestration), `__init__.py` (package metadata)

**`quickice/cli/`:**
- Purpose: Command-line argument parsing
- Contains: `parser.py` (argparse configuration)
- Key files: `quickice/cli/parser.py`

**`quickice/validation/`:**
- Purpose: Input validation logic
- Contains: `validators.py` (type converters for argparse)
- Key files: `quickice/validation/validators.py`

**`quickice/phase_mapping/`:**
- Purpose: Map temperature/pressure to ice phase
- Contains: Phase lookup, melting curves, solid boundaries, triple points
- Key files: `quickice/phase_mapping/lookup.py`, `quickice/phase_mapping/melting_curves.py`, `quickice/phase_mapping/solid_boundaries.py`
- Data: `quickice/phase_mapping/data/` (ice boundary data)

**`quickice/structure_generation/`:**
- Purpose: Generate ice structure candidates
- Contains: GenIce wrapper, phase-to-lattice mapper, data types
- Key files: `quickice/structure_generation/generator.py`, `quickice/structure_generation/mapper.py`, `quickice/structure_generation/types.py`

**`quickice/ranking/`:**
- Purpose: Score and rank candidates
- Contains: Scoring functions, ranking algorithm, data types
- Key files: `quickice/ranking/scorer.py`, `quickice/ranking/types.py`

**`quickice/output/`:**
- Purpose: Write output files and generate visualizations
- Contains: PDB writer, validator, phase diagram generator, orchestrator
- Key files: `quickice/output/orchestrator.py`, `quickice/output/pdb_writer.py`, `quickice/output/phase_diagram.py`

**`tests/`:**
- Purpose: Unit and integration tests
- Contains: Test files mirroring package structure
- Key files: `tests/test_phase_mapping.py`, `tests/test_structure_generation.py`, `tests/test_ranking.py`, `tests/test_cli_integration.py`

**`docs/`:**
- Purpose: User documentation
- Contains: CLI reference, ranking algorithm, design principles

**`sample_output/`:**
- Purpose: Example output files for users
- Contains: Generated PDB files and phase diagrams

**`.planning/`:**
- Purpose: Project planning and phase documentation
- Contains: Milestone docs, phase plans, codebase analysis
- Key files: `.planning/codebase/` (this document)

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry point (what users run)
- `quickice/main.py`: Pipeline orchestration function

**Configuration:**
- `env.yml`: Conda environment with all dependencies
- `requirements-dev.txt`: Development dependencies (pytest)
- `setup.sh`: Environment activation script

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Phase identification algorithm
- `quickice/structure_generation/generator.py`: GenIce integration
- `quickice/ranking/scorer.py`: Scoring functions
- `quickice/output/orchestrator.py`: Output coordination

**Data Types:**
- `quickice/structure_generation/types.py`: `Candidate`, `GenerationResult`
- `quickice/ranking/types.py`: `RankedCandidate`, `RankingResult`
- `quickice/output/types.py`: `OutputResult`

**Testing:**
- `tests/test_phase_mapping.py`: Phase lookup tests
- `tests/test_structure_generation.py`: Generator tests
- `tests/test_ranking.py`: Scoring tests
- `tests/test_cli_integration.py`: End-to-end tests

## Naming Conventions

**Files:**
- Python modules: lowercase with underscores (e.g., `melting_curves.py`, `solid_boundaries.py`)
- Test files: `test_<module>.py` (e.g., `test_phase_mapping.py`)
- Types files: `types.py` within each submodule
- Error files: `errors.py` within each submodule

**Directories:**
- Python packages: lowercase with underscores (e.g., `phase_mapping/`, `structure_generation/`)
- Test directories: `tests/`, `test_output/` (mirrors package structure)

**Classes:**
- Data classes: PascalCase nouns (e.g., `Candidate`, `GenerationResult`, `RankingResult`)
- Exception classes: PascalCase with "Error" suffix (e.g., `PhaseMappingError`, `UnknownPhaseError`)
- Generator classes: PascalCase (e.g., `IceStructureGenerator`)

**Functions:**
- Public API: snake_case verbs (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)
- Private helpers: leading underscore (e.g., `_build_result`, `_parse_gro`)
- Type converters: `validate_<name>` (e.g., `validate_temperature`)

**Constants:**
- Module-level: SCREAMING_SNAKE_CASE (e.g., `IDEAL_OO_DISTANCE`, `TRIPLE_POINTS`, `PHASE_COLORS`)

## Where to Add New Code

**New Feature (e.g., new scoring metric):**
- Primary code: `quickice/ranking/scorer.py` (add function)
- Tests: `tests/test_ranking.py` (add test)

**New Component/Module (e.g., new analysis stage):**
- Implementation: Create new directory `quickice/<module_name>/`
- Include: `__init__.py`, `types.py`, `errors.py`, main module file
- Wire into pipeline: `quickice/main.py`

**New Ice Phase Support:**
- Phase mapping: `quickice/phase_mapping/lookup.py` (add to algorithm)
- Metadata: `quickice/phase_mapping/lookup.py` (add to `PHASE_METADATA`)
- GenIce mapping: `quickice/structure_generation/mapper.py` (add to `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`)
- Phase diagram: `quickice/output/phase_diagram.py` (add to `PHASE_COLORS`, `PHASE_LABELS`, polygon builder)

**New Output Format:**
- Writer: `quickice/output/` (add new writer module)
- Wire into: `quickice/output/orchestrator.py`
- Types: `quickice/output/types.py` (extend if needed)

**Utilities:**
- Shared helpers: Keep within the module that uses them
- If truly cross-cutting: Create `quickice/utils/` module

**Tests:**
- Unit tests: `tests/test_<module>.py`
- Integration tests: `tests/test_<feature>_integration.py`

## Special Directories

**`.planning/`:**
- Purpose: GSD (Grok Sprint Development) planning documents
- Contains: Milestone definitions, phase plans, codebase analysis
- Generated: Yes (by GSD commands)
- Committed: Yes (for project history)

**`output/`:**
- Purpose: Default output directory for generated structures
- Contains: PDB files, phase diagrams (created at runtime)
- Generated: Yes
- Committed: No (in `.gitignore`)

**`sample_output/`:**
- Purpose: Example output for documentation
- Contains: Pre-generated example files
- Generated: Yes (manually)
- Committed: Yes (for user reference)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (automatically by Python)
- Committed: No (in `.gitignore`)

---

*Structure analysis: 2026-03-31*
