# Codebase Structure

**Analysis Date:** 2026-05-05

## Directory Layout

```
quickice/
├── quickice.py              # CLI entry point (wrapper)
├── quickice/                # Main package
│   ├── __init__.py          # Package init, version
│   ├── main.py              # CLI main() function, orchestration
│   ├── cli/                 # CLI argument parsing
│   ├── gui/                 # GUI components (MVVM)
│   ├── phase_mapping/       # Ice phase lookup
│   ├── structure_generation/ # Ice/hydrate/ion generation
│   ├── ranking/             # Candidate ranking
│   ├── output/              # File export (PDB, GRO, TOP)
│   ├── validation/          # Input validation
│   ├── utils/               # Shared utilities
│   └── data/                # Static resources
├── tests/                   # Test suite
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── .planning/               # Planning documents (phases, research)
├── output/                  # Default output directory
├── sample_output/           # Example outputs
└── dist/                    # PyInstaller build artifacts
```

## Directory Purposes

**quickice/cli/:**
- Purpose: Command-line interface argument parsing
- Contains: parser.py with argparse configuration
- Key files: `parser.py` (create_parser, get_arguments, validate_interface_args)

**quickice/gui/:**
- Purpose: Graphical user interface (PySide6 + VTK)
- Contains: MainWindow, panels, viewers, workers, exporters
- Key files: `main_window.py` (MainWindow), `viewmodel.py` (MainViewModel), `workers.py` (background threads)
- Subdirectories: None (flat structure in gui/)

**quickice/phase_mapping/:**
- Purpose: Ice phase identification from temperature and pressure
- Contains: Phase lookup logic, boundary curves, triple points, density calculations
- Key files: `lookup.py` (lookup_phase), `melting_curves.py` (IAPWS R14-08), `ice_ih_density.py` (IAPWS R10-06)
- Subdirectory: `data/` (ice_boundaries.py)

**quickice/structure_generation/:**
- Purpose: Generate ice, hydrate, and interface structures
- Contains: GenIce2 wrapper, interface builder, mode implementations, hydrate generator, ion inserter
- Key files: `generator.py` (IceStructureGenerator), `interface_builder.py` (generate_interface), `hydrate_generator.py`, `ion_inserter.py`
- Subdirectory: `modes/` (slab.py, pocket.py, piece.py)

**quickice/ranking/:**
- Purpose: Score and rank candidate structures
- Contains: Scoring algorithms, ranking logic
- Key files: `scorer.py` (rank_candidates, energy_score, density_score, diversity_score), `types.py` (RankedCandidate)

**quickice/output/:**
- Purpose: Export structures to file formats
- Contains: PDB writer, GROMACS writer (GRO/TOP/ITP), phase diagram generator, orchestrator
- Key files: `gromacs_writer.py` (write_gro_file, write_top_file), `pdb_writer.py`, `orchestrator.py` (output_ranked_candidates)

**quickice/validation/:**
- Purpose: Input validation functions
- Contains: Validators for CLI arguments
- Key files: `validators.py` (validate_temperature, validate_pressure, validate_nmolecules)

**quickice/utils/:**
- Purpose: Shared utility functions
- Contains: Molecule utilities, common helpers
- Key files: `molecule_utils.py`

**quickice/data/:**
- Purpose: Static resource files
- Contains: Water templates (tip4p.gro), force field files (tip4p_ice.itp), hydrate templates
- Key files: `tip4p.gro`, `tip4p_ice.itp`

**tests/:**
- Purpose: Test suite (pytest)
- Contains: Unit tests, integration tests, validation tests
- Key files: `test_phase_mapping.py`, `test_structure_generation.py`, `test_integration_v35.py`, `test_cli_integration.py`
- Subdirectory: `test_output/` (temporary test outputs)

**docs/:**
- Purpose: Documentation
- Contains: User documentation, API references
- Key files: (documentation files)

**scripts/:**
- Purpose: Utility scripts for development and deployment
- Contains: Build scripts, packaging helpers
- Key files: (various utility scripts)

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry wrapper
- `quickice/main.py`: CLI main() function, pipeline orchestration
- `quickice/gui/__main__.py`: GUI entry point (python -m quickice.gui)
- `quickice/gui/main_window.py`: MainWindow class, primary GUI window

**Configuration:**
- `quickice/cli/parser.py`: CLI argument parser configuration
- `quickice/structure_generation/types.py`: Dataclass configurations (InterfaceConfig, HydrateConfig)
- `quickice/structure_generation/mapper.py`: Phase-to-GenIce mapping constants

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: Phase identification algorithm
- `quickice/structure_generation/generator.py`: Ice structure generation (GenIce2 wrapper)
- `quickice/structure_generation/interface_builder.py`: Interface generation orchestrator
- `quickice/structure_generation/hydrate_generator.py`: Hydrate structure generation
- `quickice/structure_generation/ion_inserter.py`: Ion insertion into interfaces
- `quickice/ranking/scorer.py`: Candidate scoring and ranking

**Mode Implementations:**
- `quickice/structure_generation/modes/slab.py`: Slab interface mode (ice-water-ice layers)
- `quickice/structure_generation/modes/pocket.py`: Pocket interface mode (water cavity in ice)
- `quickice/structure_generation/modes/piece.py`: Piece interface mode (ice fragment in water)

**GUI Components:**
- `quickice/gui/viewmodel.py`: MVVM ViewModel, thread management
- `quickice/gui/workers.py`: Background workers for computation
- `quickice/gui/view.py`: View components (InputPanel, ProgressPanel, ViewerPanel, InfoPanel)
- `quickice/gui/phase_diagram_widget.py`: Interactive phase diagram
- `quickice/gui/export.py`: Export handlers (PDB, GROMACS, diagrams)
- `quickice/gui/interface_panel.py`: Interface Construction tab (Tab 3)
- `quickice/gui/hydrate_panel.py`: Hydrate Configuration tab (Tab 2)
- `quickice/gui/ion_panel.py`: Ion Insertion tab (Tab 4)

**Output:**
- `quickice/output/gromacs_writer.py`: GRO/TOP/ITP file writers
- `quickice/output/pdb_writer.py`: PDB file writers
- `quickice/output/orchestrator.py`: Output coordination
- `quickice/output/phase_diagram.py`: Phase diagram generation

**Testing:**
- `tests/test_phase_mapping.py`: Phase lookup tests
- `tests/test_structure_generation.py`: Structure generation tests
- `tests/test_ranking.py`: Ranking algorithm tests
- `tests/test_integration_v35.py`: Full integration tests
- `tests/test_cli_integration.py`: CLI end-to-end tests

## Naming Conventions

**Files:**
- Modules: snake_case (e.g., `interface_builder.py`, `hydrate_generator.py`)
- Test files: test_<module>.py (e.g., `test_phase_mapping.py`)
- GUI panels: <feature>_panel.py (e.g., `interface_panel.py`, `hydrate_panel.py`)
- GUI viewers: <feature>_viewer.py (e.g., `interface_viewer.py`, `ion_viewer.py`)
- Data files: lowercase with extensions (e.g., `tip4p.gro`, `tip4p_ice.itp`)

**Directories:**
- Packages: lowercase (e.g., `phase_mapping/`, `structure_generation/`)
- Subpackages: lowercase (e.g., `modes/`, `data/`)

**Classes:**
- PascalCase (e.g., `MainWindow`, `IceStructureGenerator`, `InterfaceStructure`)
- Config classes: <Feature>Config (e.g., `InterfaceConfig`, `HydrateConfig`)
- Structure classes: <Feature>Structure (e.g., `InterfaceStructure`, `HydrateStructure`)
- Result classes: <Feature>Result (e.g., `GenerationResult`, `RankingResult`)

**Functions:**
- snake_case (e.g., `lookup_phase`, `generate_interface`, `rank_candidates`)
- Validators: validate_<name> (e.g., `validate_temperature`, `validate_interface_config`)
- Getters: get_<name> (e.g., `get_arguments`, `get_genice_lattice_name`)
- Writers: write_<format>_<type> (e.g., `write_gro_file`, `write_top_file`)

**Variables:**
- snake_case for local variables (e.g., `temperature`, `pressure`, `nmolecules`)
- Private attributes: _name (e.g., `_worker`, `_thread`, `_is_generating`)

**Constants:**
- UPPER_SNAKE_CASE (e.g., `PHASE_METADATA`, `HYDRATE_LATTICES`, `MINIMUM_BOX_DIMENSION`)

## Where to Add New Code

**New Feature (CLI):**
- Core logic: `quickice/<domain>/` (create new module or extend existing)
- CLI args: `quickice/cli/parser.py` (add argument, validation)
- Pipeline: `quickice/main.py` (integrate into workflow)
- Tests: `tests/test_<domain>.py` or `tests/test_<feature>.py`

**New Feature (GUI):**
- Panel component: `quickice/gui/<feature>_panel.py`
- Worker (if needed): Add to `quickice/gui/workers.py`
- ViewModel integration: `quickice/gui/viewmodel.py` (add worker, signals)
- MainWindow integration: `quickice/gui/main_window.py` (add tab, connect signals)
- Export handler: `quickice/gui/export.py` or create `quickice/gui/<feature>_export.py`

**New Component/Module:**
- Implementation: `quickice/<module_name>/` (create package with __init__.py)
- Types: `quickice/<module_name>/types.py` (dataclasses)
- Core logic: `quickice/<module_name>/<logic>.py`
- Exports: `quickice/<module_name>/__init__.py` (add to __all__)

**New Interface Mode:**
- Implementation: `quickice/structure_generation/modes/<mode>.py` (create assemble_<mode> function)
- Routing: `quickice/structure_generation/interface_builder.py` (add to generate_interface, validation)
- Tests: `tests/test_interface_modes_audit.py` or `tests/test_<mode>_mode.py`

**New Hydrate Lattice:**
- Definition: `quickice/structure_generation/types.py` (add to HYDRATE_LATTICES dict)
- Generator: `quickice/structure_generation/hydrate_generator.py` (ensure GenIce2 support)
- Tests: `tests/test_hydrate_guest_tiling.py`

**New Guest Molecule:**
- Definition: `quickice/structure_generation/types.py` (add to GUEST_MOLECULES, MOLECULE_TYPE_INFO)
- Template: `quickice/data/<guest>.gro` (create template file)
- Generator: `quickice/structure_generation/hydrate_generator.py` (handle new molecule type)
- Tests: `tests/test_hydrate_guest_tiling.py`

**Utilities:**
- Shared helpers: `quickice/utils/<utility>.py`
- Validators: `quickice/validation/validators.py`

**New Ice Phase:**
- Metadata: `quickice/phase_mapping/lookup.py` (add to PHASE_METADATA)
- Mapping: `quickice/structure_generation/mapper.py` (add to PHASE_TO_GENICE, UNIT_CELL_MOLECULES)
- Boundary curves: `quickice/phase_mapping/solid_boundaries.py` (add boundary function if needed)
- Tests: `tests/test_phase_mapping.py`

**Tests:**
- Unit tests: `tests/test_<module>.py`
- Integration tests: `tests/test_integration_<feature>.py`
- Validation tests: `tests/test_<feature>_validation.py`

## Special Directories

**.planning/:**
- Purpose: Project planning documents, phase plans, research notes, debug artifacts
- Contains: phases/, research/, debug/, milestones/, quick/, codebase/
- Generated: Yes (created by planning process)
- Committed: Yes (tracks project history)

**quickice/data/:**
- Purpose: Static resource files bundled with package
- Contains: GRO templates, ITP files, other static resources
- Generated: No (manually maintained)
- Committed: Yes (part of package)

**output/:**
- Purpose: Default output directory for generated structures
- Contains: User-generated PDB, GRO, TOP, diagram files
- Generated: Yes (at runtime)
- Committed: No (in .gitignore)

**dist/:**
- Purpose: PyInstaller build artifacts
- Contains: Executable binaries, build logs
- Generated: Yes (by PyInstaller)
- Committed: No (in .gitignore)

**build/:**
- Purpose: PyInstaller temporary build files
- Contains: Intermediate build artifacts
- Generated: Yes (by PyInstaller)
- Committed: No (in .gitignore)

**tests/test_output/:**
- Purpose: Temporary test outputs
- Contains: Test-generated files
- Generated: Yes (during test runs)
- Committed: No (cleaned after tests)

---

*Structure analysis: 2026-05-05*
