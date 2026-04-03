# Codebase Structure

**Analysis Date:** 2026-04-04

## Directory Layout

```
quickice/
├── quickice.py           # CLI entry point script
├── quickice/             # Main package
│   ├── __init__.py       # Package init, version
│   ├── main.py           # CLI orchestration
│   ├── cli/              # CLI argument parsing
│   ├── phase_mapping/    # Phase lookup (Phase 2)
│   ├── structure_generation/  # Structure generation (Phase 3)
│   ├── ranking/          # Candidate ranking (Phase 4)
│   ├── output/           # PDB writing, diagrams (Phase 5)
│   ├── validation/       # Input validation
│   └── gui/              # GUI application (Phase 8-10)
├── tests/                # Test suite
├── output/               # Default output directory
├── docs/                 # Documentation
└── .planning/            # Planning artifacts
```

## Directory Purposes

**quickice/cli:**
- Purpose: Command-line interface components
- Contains: Argument parser, validation adapters
- Key files: `parser.py` (argparse configuration), `__init__.py`

**quickice/phase_mapping:**
- Purpose: Ice phase identification from T, P conditions
- Contains: Curve-based boundary evaluation, triple points, melting curves
- Key files: `lookup.py` (main API), `melting_curves.py` (IAPWS), `solid_boundaries.py` (linear interpolation), `triple_points.py` (constants)

**quickice/structure_generation:**
- Purpose: Ice structure candidate generation via GenIce2
- Contains: Generator wrapper, phase-to-lattice mapping, type definitions
- Key files: `generator.py` (IceStructureGenerator class), `mapper.py` (PHASE_TO_GENICE dict), `types.py` (Candidate dataclass)

**quickice/ranking:**
- Purpose: Score and rank generated ice structure candidates
- Contains: Scoring functions, ranking logic, type definitions
- Key files: `scorer.py` (rank_candidates function), `types.py` (RankedCandidate dataclass)

**quickice/output:**
- Purpose: Write PDB files, generate phase diagrams
- Contains: PDB writer, validators, phase diagram generator, orchestrator
- Key files: `orchestrator.py` (output_ranked_candidates), `pdb_writer.py` (CRYST1 format), `phase_diagram.py` (matplotlib), `validator.py` (structure validation)

**quickice/validation:**
- Purpose: Input validation logic shared between CLI and GUI
- Contains: Type validators for temperature, pressure, molecule count
- Key files: `validators.py` (validate_temperature, validate_pressure, validate_nmolecules)

**quickice/gui:**
- Purpose: PySide6-based GUI application
- Contains: MVVM components (View, ViewModel), VTK 3D viewer, widgets
- Key files: `main_window.py` (MainWindow), `viewmodel.py` (MainViewModel), `view.py` (panels), `workers.py` (QThread worker), `dual_viewer.py` (VTK), `phase_diagram_widget.py` (interactive diagram)

**tests:**
- Purpose: Unit and integration tests
- Contains: Test modules mirroring package structure
- Key files: `test_phase_mapping.py`, `test_structure_generation.py`, `test_ranking.py`, `test_cli_integration.py`, `test_output/test_pdb_writer.py`, `test_output/test_validator.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry script (user runs `python quickice.py ...`)
- `quickice/main.py`: CLI orchestration (`main()` function)
- `quickice/gui/__main__.py`: GUI entry (`python -m quickice.gui`)
- `quickice/gui/main_window.py`: GUI main window (`MainWindow` class)

**Configuration:**
- `quickice/__init__.py`: Version string
- `environment.yml`: Conda environment specification
- `requirements-dev.txt`: Development dependencies

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Ice phase determination algorithm
- `quickice/structure_generation/generator.py`: GenIce2 integration
- `quickice/ranking/scorer.py`: Scoring and ranking logic
- `quickice/output/orchestrator.py`: Output coordination

**Testing:**
- `tests/test_phase_mapping.py`: Phase lookup tests
- `tests/test_structure_generation.py`: Generator tests
- `tests/test_ranking.py`: Scoring tests
- `tests/test_cli_integration.py`: End-to-end CLI tests

## Naming Conventions

**Files:**
- Modules: snake_case (e.g., `phase_mapping.py`, `pdb_writer.py`)
- Test files: `test_<module>.py` (e.g., `test_phase_mapping.py`)
- Private modules: Not used (all modules public)

**Directories:**
- Package directories: snake_case (e.g., `phase_mapping`, `structure_generation`)
- Test directories: Mirror package structure (e.g., `tests/test_output/`)

**Classes:**
- PascalCase (e.g., `IceStructureGenerator`, `RankedCandidate`, `MainWindow`)
- Dataclasses: PascalCase (e.g., `Candidate`, `GenerationResult`)

**Functions:**
- snake_case (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)
- Private functions: Leading underscore (e.g., `_build_result`, `_parse_gro`)

**Variables:**
- snake_case for locals
- Single underscore prefix for private attributes (e.g., `_viewmodel`, `_is_generating`)

## Where to Add New Code

**New Feature (Core Pipeline):**
- Create new module in appropriate phase directory (e.g., `quickice/<phase>/<new_feature>.py`)
- Add public API to `quickice/<phase>/__init__.py`
- Add type definitions to `quickice/<phase>/types.py`
- Add tests to `tests/test_<phase>.py`

**New Ice Phase Support:**
- Add phase metadata to `quickice/phase_mapping/lookup.py:PHASE_METADATA`
- Add boundary curves to `quickice/phase_mapping/solid_boundaries.py`
- Add phase to GenIce mapping in `quickice/structure_generation/mapper.py:PHASE_TO_GENICE`
- Add unit cell size to `quickice/structure_generation/mapper.py:UNIT_CELL_MOLECULES`
- Add color/label to `quickice/output/phase_diagram.py:PHASE_COLORS` and `PHASE_LABELS`
- Add polygon builder to `quickice/output/phase_diagram.py:_build_<phase>_polygon()`

**New GUI Panel:**
- Create widget in `quickice/gui/view.py` (follow `InputPanel`, `ProgressPanel` patterns)
- Add to `MainWindow._setup_ui()` layout
- Connect signals in `MainWindow._setup_connections()`

**New CLI Option:**
- Add argument to `quickice/cli/parser.py:create_parser()`
- Update `quickice/main.py:main()` to use new argument
- Update `tests/test_cli_integration.py` with new test cases

**New Validation Rule:**
- Add validator to `quickice/validation/validators.py`
- Use in both `quickice/cli/parser.py` and `quickice/gui/validators.py`

**Utilities:**
- Shared helpers: `quickice/<appropriate_module>/_utils.py` (private module)
- Pure utility functions: Keep in relevant domain module

## Special Directories

**output:**
- Purpose: Default output directory for generated PDB files and phase diagrams
- Generated: Yes (by pipeline execution)
- Committed: No (in .gitignore)

**tests/test_output:**
- Purpose: Test output artifacts (temporary files)
- Generated: Yes (during test execution)
- Committed: No

**.planning:**
- Purpose: Planning artifacts (phases, research, codebase analysis)
- Generated: Yes (by GSD commands)
- Committed: No (in .gitignore)

**docs:**
- Purpose: Documentation files
- Generated: No
- Committed: Yes

**sample_output:**
- Purpose: Example output for documentation/reference
- Generated: Yes (from previous runs)
- Committed: Yes

## Module Dependencies

**Dependency Order (import direction):**
1. `quickice/validation/` - No internal dependencies
2. `quickice/phase_mapping/errors.py` - No internal dependencies
3. `quickice/phase_mapping/` - Depends on: errors, IAPWS (external)
4. `quickice/structure_generation/errors.py` - No internal dependencies
5. `quickice/structure_generation/types.py` - No internal dependencies
6. `quickice/structure_generation/mapper.py` - Depends on: errors
7. `quickice/structure_generation/generator.py` - Depends on: mapper, types, errors, GenIce2 (external)
8. `quickice/ranking/types.py` - Depends on: structure_generation/types
9. `quickice/ranking/scorer.py` - Depends on: types, structure_generation/types
10. `quickice/output/types.py` - No internal dependencies
11. `quickice/output/pdb_writer.py` - Depends on: types, structure_generation/types
12. `quickice/output/validator.py` - Depends on: structure_generation/types
13. `quickice/output/phase_diagram.py` - Depends on: phase_mapping, matplotlib (external)
14. `quickice/output/orchestrator.py` - Depends on: types, pdb_writer, validator, phase_diagram, ranking/types
15. `quickice/main.py` - Depends on: cli, phase_mapping, structure_generation, ranking, output
16. `quickice/gui/workers.py` - Depends on: all core modules
17. `quickice/gui/viewmodel.py` - Depends on: workers, ranking/types
18. `quickice/gui/view.py` - Depends on: validators, dual_viewer
19. `quickice/gui/main_window.py` - Depends on: view, viewmodel, phase_diagram_widget, export, help_dialog

---

*Structure analysis: 2026-04-04*
