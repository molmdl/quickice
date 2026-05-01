# Codebase Structure

**Analysis Date:** 2026-05-02

## Directory Layout

```
quickice/
├── quickice/              # Main package (Python module)
│   ├── cli/               # CLI argument parsing
│   ├── data/              # Static data files (ITP, GRO templates)
│   ├── gui/               # GUI components (PySide6 + VTK)
│   ├── output/            # Output writers (PDB, GRO, TOP, diagrams)
│   ├── phase_mapping/     # Ice phase determination
│   ├── ranking/           # Candidate scoring and ranking
│   ├── structure_generation/  # GenIce wrapper, interface builder
│   ├── validation/        # Input validation
│   ├── __init__.py        # Package init, version
│   └── main.py            # CLI main orchestration
├── tests/                 # Test suite
├── docs/                  # User documentation
├── scripts/               # Build and run scripts
├── .github/               # GitHub Actions, Dependabot
├── .planning/             # GSD planning documents
├── quickice.py            # CLI entry point script
├── environment.yml        # Conda environment specification
├── requirements-dev.txt   # Development dependencies (pytest, pyinstaller)
├── README.md              # Project documentation
└── setup.sh               # Environment setup script
```

## Directory Purposes

**quickice/cli:**
- Purpose: Command-line interface implementation
- Contains: Argument parser, validation routing
- Key files: `parser.py` (argparse configuration)

**quickice/data:**
- Purpose: Static template files for GROMACS force field
- Contains: ITP files (force field parameters), GRO template (water structure)
- Key files: `tip4p-ice.itp`, `tip4p.gro`, `ch4.itp`, `thf.itp`
- Note: These are bundled with the package, used at export time

**quickice/gui:**
- Purpose: Graphical user interface
- Contains: MainWindow, panels, viewers, renderers, workers
- Key files: `main_window.py` (main window), `view.py` (widgets), `viewmodel.py` (MVVM ViewModel), `molecular_viewer.py` (VTK), `phase_diagram_widget.py` (matplotlib)
- Sub-modules: `interface_panel.py`, `hydrate_panel.py`, `ion_panel.py` (feature panels)

**quickice/output:**
- Purpose: File output and validation
- Contains: PDB writer, GROMACS writer, phase diagram generator, orchestrator
- Key files: `orchestrator.py` (main entry), `pdb_writer.py`, `gromacs_writer.py`, `phase_diagram.py`, `validator.py`

**quickice/phase_mapping:**
- Purpose: Ice phase determination from T/P conditions
- Contains: Curve-based lookup, triple points, melting curves, solid boundaries
- Key files: `lookup.py` (main API), `melting_curves.py` (IAPWS), `solid_boundaries.py`, `triple_points.py`, `ice_ih_density.py`, `water_density.py`

**quickice/ranking:**
- Purpose: Candidate scoring and ranking
- Contains: Scoring functions for energy/density/diversity
- Key files: `scorer.py` (main API), `types.py` (data structures)

**quickice/structure_generation:**
- Purpose: Ice structure generation and interface construction
- Contains: GenIce wrapper, interface builder, hydrate generator, ion inserter
- Key files: `generator.py` (IceStructureGenerator), `interface_builder.py` (orchestrator), `types.py` (data structures)
- Sub-modules: `modes/` (slab/pocket/piece strategies), `hydrate_generator.py`, `ion_inserter.py`, `water_filler.py`, `overlap_resolver.py`

**quickice/validation:**
- Purpose: Input validation for CLI and GUI
- Contains: Validator functions for T/P/N
- Key files: `validators.py`

**tests:**
- Purpose: Test suite
- Contains: Unit tests and integration tests
- Key files: `test_structure_generation.py`, `test_phase_mapping.py`, `test_ranking.py`, `test_cli_integration.py`
- Sub-modules: `test_output/` (output-specific tests)

**docs:**
- Purpose: User documentation
- Contains: CLI reference, GUI guide, flowchart, principles
- Key files: `cli-reference.md`, `gui-guide.md`, `flowchart.md`, `principles.md`, `ranking.md`

**scripts:**
- Purpose: Build and deployment scripts
- Contains: Linux build script, distribution assembler, SSH run helper
- Key files: `build-linux.sh`, `assemble-dist.sh`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI script entry point (imports from `quickice.main`)
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/main.py`: Main orchestration logic

**Configuration:**
- `environment.yml`: Conda environment with all dependencies
- `requirements-dev.txt`: Development-only dependencies
- `setup.sh`: Environment setup helper

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Phase determination API
- `quickice/structure_generation/generator.py`: Ice structure generation
- `quickice/structure_generation/interface_builder.py`: Interface generation
- `quickice/ranking/scorer.py`: Candidate scoring
- `quickice/output/orchestrator.py`: Output coordination

**Data Structures:**
- `quickice/structure_generation/types.py`: Candidate, InterfaceConfig, InterfaceStructure, HydrateConfig, HydrateStructure
- `quickice/ranking/types.py`: RankedCandidate, RankingResult

**Testing:**
- `tests/test_structure_generation.py`: Structure generation tests
- `tests/test_phase_mapping.py`: Phase mapping tests
- `tests/test_ranking.py`: Ranking tests

## Naming Conventions

**Files:**
- Python modules: lowercase with underscores (`structure_generation.py`, `interface_builder.py`)
- Test files: `test_<module>.py` pattern
- Data files: lowercase with hyphens (`tip4p-ice.itp`, `ch4.itp`)

**Directories:**
- Python packages: lowercase with underscores (`structure_generation/`, `phase_mapping/`)
- Test directories: `tests/` at root level

**Classes:**
- PascalCase: `IceStructureGenerator`, `InterfaceConfig`, `MainWindow`
- Descriptive names: `UnknownPhaseError`, `InterfaceGenerationError`

**Functions:**
- snake_case: `lookup_phase()`, `generate_candidates()`, `rank_candidates()`
- Private helpers: underscore prefix `_parse_gro()`, `_calculate_oo_distances_pbc()`

**Variables:**
- snake_case: `phase_id`, `nmolecules`, `ice_thickness`
- Constants: UPPER_CASE `PHASE_METADATA`, `TRIPLE_POINTS`, `MINIMUM_BOX_DIMENSION`

## Where to Add New Code

**New Ice Phase:**
- Add to `PHASE_METADATA` in `quickice/phase_mapping/lookup.py`
- Add mapping in `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES` in `quickice/structure_generation/mapper.py`
- Add boundary curves in `quickice/phase_mapping/solid_boundaries.py`
- Update tests in `tests/test_phase_mapping.py`

**New Interface Mode:**
- Create assembler in `quickice/structure_generation/modes/<mode>.py`
- Add to `__init__.py` exports
- Add validation in `quickice/structure_generation/interface_builder.py:validate_interface_config()`
- Add routing in `quickice/structure_generation/interface_builder.py:generate_interface()`
- Add tests in `tests/test_interface_modes_audit.py`

**New GUI Panel:**
- Create panel widget in `quickice/gui/<feature>_panel.py`
- Create worker thread in `quickice/gui/<feature>_worker.py` (if async)
- Create renderer in `quickice/gui/<feature>_renderer.py` (if 3D)
- Add to MainWindow tab widget in `quickice/gui/main_window.py`

**New Output Format:**
- Create writer in `quickice/output/<format>_writer.py`
- Add to `quickice/output/__init__.py` exports
- Add exporter class in `quickice/gui/export.py` for GUI

**New Scoring Metric:**
- Add scoring function in `quickice/ranking/scorer.py`
- Add to `rank_candidates()` function
- Update `ScoringConfig` in `quickice/ranking/types.py`
- Update tests in `tests/test_ranking.py`

**New Molecule Type (ions, guests):**
- Add to `MOLECULE_TYPE_INFO` in `quickice/structure_generation/types.py`
- Add ITP file to `quickice/data/`
- Update `MoleculeIndex` tracking if atom count differs

## Special Directories

**quickice/data:**
- Purpose: Static template files bundled with package
- Contains: Force field ITP files, water GRO template
- Generated: No (manually maintained)
- Committed: Yes
- Note: Used by `get_tip4p_itp_path()` and GROMACS exporters

**.planning:**
- Purpose: GSD (planning) documents for AI-assisted development
- Contains: Phase documents, quick fixes, codebase analysis
- Generated: Yes (by GSD commands)
- Committed: Yes (tracked for future reference)

**tests/test_output:**
- Purpose: Output-specific tests with fixtures
- Contains: PDB writer tests, validator tests, molecule wrapping tests
- Note: Output files from tests go to temp directories

**.github/workflows:**
- Purpose: CI/CD automation
- Contains: GitHub Actions workflows (if any)
- Generated: No

**output:**
- Purpose: Default output directory for generated structures
- Created at runtime if needed
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-05-02*
