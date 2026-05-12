# Codebase Structure

**Analysis Date:** 2026-05-12

## Directory Layout

```
quickice/
├── quickice/                  # Main package
│   ├── cli/                   # CLI argument parsing
│   ├── gui/                   # GUI application (PySide6/VTK)
│   ├── phase_mapping/         # Ice phase lookup (T/P → phase)
│   ├── structure_generation/  # GenIce-based structure generation
│   ├── ranking/               # Candidate scoring and ranking
│   ├── output/                # PDB/GROMACS export, diagrams
│   ├── validation/            # Input validation
│   ├── data/                  # Static data files (ITP, GRO templates)
│   └── utils/                 # Shared utilities
├── tests/                     # pytest test suite
├── docs/                      # User documentation
├── scripts/                   # Build and utility scripts
├── .planning/                 # Project planning and phase history
├── quickice.py                # CLI entry point
├── environment.yml            # Conda environment specification
├── requirements-dev.txt       # Development dependencies
└── README.md                  # Project documentation
```

## Directory Purposes

### `quickice/`
- **Purpose**: Main Python package containing all source code
- **Contains**: Core modules organized by function
- **Key files**: `main.py`, `__init__.py`

### `quickice/cli/`
- **Purpose**: Command-line interface implementation
- **Contains**: Argument parser definitions
- **Key files**: `parser.py`, `__init__.py`

### `quickice/gui/`
- **Purpose**: Graphical user interface with 3D visualization
- **Contains**: 
  - Main window and view components
  - ViewModel for state management
  - Background workers for async operations
  - Renderers for VTK visualization
  - Export handlers
- **Key files**: `main_window.py`, `viewmodel.py`, `workers.py`, `molecular_viewer.py`

### `quickice/phase_mapping/`
- **Purpose**: Determine ice phase from thermodynamic conditions
- **Contains**: IAPWS R14-08 melting curves, solid boundaries, triple points
- **Key files**: `lookup.py`, `melting_curves.py`, `solid_boundaries.py`, `ice_ih_density.py`

### `quickice/structure_generation/`
- **Purpose**: Generate ice crystal structures
- **Contains**: 
  - GenIce wrapper and mapper
  - Interface builder with mode implementations
  - Ion, solute, and custom molecule inserters
  - Hydrate generator
  - Type definitions
- **Key files**: `generator.py`, `interface_builder.py`, `types.py`, `hydrate_generator.py`

### `quickice/structure_generation/modes/`
- **Purpose**: Interface generation mode implementations
- **Contains**: Slab, pocket, and piece mode assembly logic
- **Key files**: `slab.py`, `pocket.py`, `piece.py`

### `quickice/ranking/`
- **Purpose**: Score and rank ice structure candidates
- **Contains**: Energy, density, and diversity scoring algorithms
- **Key files**: `scorer.py`, `types.py`

### `quickice/output/`
- **Purpose**: Export structures to various formats
- **Contains**: PDB writer, GROMACS writer, phase diagram generator, validator
- **Key files**: `gromacs_writer.py`, `pdb_writer.py`, `phase_diagram.py`, `orchestrator.py`

### `quickice/validation/`
- **Purpose**: Input validation for CLI and GUI
- **Contains**: Type validators for temperature, pressure, molecule count
- **Key files**: `validators.py`

### `quickice/data/`
- **Purpose**: Static data files used by the application
- **Contains**: 
  - Force field files (ITP): tip4p-ice.itp, ch4.itp, thf.itp
  - Template structures: tip4p.gro
  - Custom molecule storage: custom/
- **Key files**: `tip4p-ice.itp`, `tip4p.gro`, `ch4.itp`, `thf.itp`

### `tests/`
- **Purpose**: Automated test suite
- **Contains**: Unit tests and integration tests for all modules
- **Key files**: `test_phase_mapping.py`, `test_structure_generation.py`, `test_integration_v35.py`

### `docs/`
- **Purpose**: User-facing documentation
- **Contains**: CLI reference, GUI guide, principles, flowcharts
- **Key files**: `cli-reference.md`, `gui-guide.md`, `principles.md`, `gro-itp-guide.md`

### `scripts/`
- **Purpose**: Build and deployment scripts
- **Contains**: Packaging and utility scripts
- **Key files**: Various shell/Python scripts

### `.planning/`
- **Purpose**: Project management and development history
- **Contains**: 
  - Phase implementation plans (numbered directories)
  - Project state documents (STATE.md, ROADMAP.md)
  - Requirements and milestones
- **Key files**: `STATE.md`, `ROADMAP.md`, `PROJECT.md`, `REQUIREMENTS.md`

## Key File Locations

### Entry Points
- `quickice.py`: CLI entry point script
- `quickice/main.py`: CLI main orchestration logic
- `quickice/gui/__main__.py`: GUI entry point

### Configuration
- `environment.yml`: Conda environment with all dependencies
- `environment-build.yml`: Build-specific environment
- `requirements-dev.txt`: Development dependencies (pytest, pyinstaller)
- `quickice-gui.spec`: PyInstaller specification for binary builds

### Core Logic
- `quickice/phase_mapping/lookup.py`: Phase determination algorithm
- `quickice/structure_generation/generator.py`: Ice structure generation
- `quickice/structure_generation/interface_builder.py`: Interface assembly
- `quickice/structure_generation/types.py`: All data type definitions
- `quickice/ranking/scorer.py`: Candidate scoring algorithms
- `quickice/output/gromacs_writer.py`: GROMACS file export

### GUI Core
- `quickice/gui/main_window.py`: Main application window (2000+ lines)
- `quickice/gui/viewmodel.py`: State management and worker coordination
- `quickice/gui/workers.py`: Background thread workers
- `quickice/gui/molecular_viewer.py`: 3D VTK visualization

### Data Files
- `quickice/data/tip4p-ice.itp`: TIP4P-ICE force field parameters
- `quickice/data/tip4p.gro`: Water template structure
- `quickice/data/ch4.itp`, `ch4_liquid.itp`: Methane force field
- `quickice/data/thf.itp`, `thf_liquid.itp`: THF force field

### Testing
- `tests/test_phase_mapping.py`: Phase lookup tests
- `tests/test_structure_generation.py`: Generator tests
- `tests/test_ranking.py`: Scoring algorithm tests
- `tests/test_integration_v35.py`: Full pipeline integration tests

## Naming Conventions

### Files
- **Python modules**: `snake_case.py` (e.g., `interface_builder.py`)
- **Test files**: `test_<module>.py` (e.g., `test_phase_mapping.py`)
- **Data files**: Descriptive names with extensions (e.g., `tip4p-ice.itp`, `ch4_liquid.itp`)
- **Documentation**: `kebab-case.md` (e.g., `cli-reference.md`, `gui-guide.md`)

### Directories
- **Package directories**: `snake_case/` (e.g., `structure_generation/`)
- **Phase directories**: `NN-description/` where NN is zero-padded phase number (e.g., `01-input-validation/`)

### Classes
- **PascalCase** for all classes (e.g., `IceStructureGenerator`, `InterfaceConfig`, `MainViewModel`)
- **Suffix conventions**:
  - `*Config`: Configuration dataclasses (e.g., `InterfaceConfig`, `HydrateConfig`)
  - `*Structure`: Result dataclasses (e.g., `InterfaceStructure`, `HydrateStructure`)
  - `*Result`: Pipeline stage results (e.g., `GenerationResult`, `RankingResult`)
  - `*Worker`: Background thread workers (e.g., `GenerationWorker`, `HydrateWorker`)
  - `*Panel`: GUI input panels (e.g., `InterfacePanel`, `HydratePanel`)
  - `*Renderer`: VTK rendering helpers (e.g., `HydrateRenderer`, `IonRenderer`)
  - `*Exporter`: Export handlers (e.g., `GROMACSExporter`, `DiagramExporter`)
  - `*Error`: Custom exceptions (e.g., `UnknownPhaseError`, `InterfaceGenerationError`)

### Functions
- **snake_case** for all functions (e.g., `lookup_phase`, `generate_candidates`, `rank_candidates`)
- **Validator functions**: `validate_<name>` (e.g., `validate_temperature`, `validate_pressure`)

### Variables
- **snake_case** for local variables
- **Private attributes**: `_leading_underscore` (e.g., `_viewmodel`, `_current_result`)

### Type Aliases and Constants
- **UPPER_SNAKE_CASE** for constants (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `TRIPLE_POINTS`)

## Where to Add New Code

### New Feature (Pipeline Stage)
- **Primary code**: Add new module directory under `quickice/<feature_name>/`
- **Types**: Add dataclasses to `quickice/<feature_name>/types.py`
- **Exports**: Update `quickice/<feature_name>/__init__.py`
- **Integration**: Import and use in `quickice/main.py` and GUI workers
- **Tests**: Add `tests/test_<feature_name>.py`

### New GUI Tab/Panel
- **Panel**: Create `quickice/gui/<feature>_panel.py`
- **Worker**: Create `quickice/gui/<feature>_worker.py` if async
- **Renderer**: Create `quickice/gui/<feature>_renderer.py` if 3D visualization
- **Export**: Add exporter class to `quickice/gui/export.py`
- **Integration**: Add to `MainWindow._setup_ui()` in `main_window.py`
- **Tab index**: Add constant to `quickice/gui/constants.py`

### New Ice Phase
- **Phase metadata**: Add to `PHASE_METADATA` in `quickice/phase_mapping/lookup.py`
- **Boundary curves**: Add boundary function in `quickice/phase_mapping/solid_boundaries.py`
- **Lookup logic**: Add detection logic in `lookup_phase()` function
- **GenIce mapping**: Add to `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES` in `quickice/structure_generation/mapper.py`
- **Tests**: Add boundary tests in `tests/test_phase_mapping.py`

### New Interface Mode
- **Mode implementation**: Create `quickice/structure_generation/modes/<mode>.py`
- **Integration**: Import and route in `quickice/structure_generation/interface_builder.py`
- **Tests**: Add mode tests in `tests/test_interface_modes_audit.py`

### New Output Format
- **Writer**: Create `quickice/output/<format>_writer.py`
- **Integration**: Import in `quickice/output/__init__.py` and use in orchestrator
- **GUI export**: Add exporter class to `quickice/gui/export.py`

### New Validator
- **Validator**: Add function to `quickice/validation/validators.py`
- **Integration**: Use in CLI parser (`quickice/cli/parser.py`) or GUI panels

### New Test
- **Unit test**: Create `tests/test_<module>.py`
- **Integration test**: Add to `tests/test_integration_v35.py` or create new integration file

### New Data File
- **Force field**: Add `.itp` file to `quickice/data/`
- **Structure template**: Add `.gro` file to `quickice/data/`
- **Custom molecules**: Store in `quickice/data/custom/`

## Special Directories

### `.planning/phases/`
- **Purpose**: Implementation plans for each development phase
- **Generated**: No (manually created during planning)
- **Committed**: Yes
- **Naming**: `NN-description/` (e.g., `01-input-validation/`, `09-interactive-phase-diagram/`)

### `.planning/quick/`
- **Purpose**: Quick fixes and minor enhancements
- **Generated**: No
- **Committed**: Yes
- **Naming**: `NNN-description/` (e.g., `001-add-liquid-vapor-labels/`)

### `quickice/data/custom/`
- **Purpose**: User-uploaded custom molecule files
- **Generated**: Yes (created at runtime)
- **Committed**: No (user data, excluded from git)
- **Contents**: `.gro` and `.itp` files for custom molecules

### `build/`, `dist/`
- **Purpose**: PyInstaller build artifacts
- **Generated**: Yes (build process)
- **Committed**: No (in .gitignore)
- **Contents**: Compiled binary and intermediate files

### `output/`
- **Purpose**: Default output directory for generated structures
- **Generated**: Yes (created at runtime)
- **Committed**: No (user data)
- **Contents**: `.pdb`, `.gro`, `.top`, `.itp`, `.png` files

### `__pycache__/`
- **Purpose**: Python bytecode cache
- **Generated**: Yes (automatic)
- **Committed**: No (in .gitignore)

---

*Structure analysis: 2026-05-12*
