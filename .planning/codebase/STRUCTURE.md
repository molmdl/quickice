# Codebase Structure

**Analysis Date:** 2026-06-12

## Directory Layout

```
quickice/                              # Project root
├── quickice.py                        # CLI entry point script
├── quickice/                          # Main package
│   ├── __init__.py                    # Package version (4.5.0)
│   ├── main.py                        # CLI orchestration (synchronous pipeline)
│   ├── cli/                           # CLI argument parsing
│   │   ├── __init__.py
│   │   └── parser.py                  # Argparse with validators
│   ├── gui/                           # GUI application (MVVM View + ViewModel + Workers)
│   │   ├── __init__.py                # Exports MainWindow, run_app, panels, renderers
│   │   ├── __main__.py                # GUI entry: python -m quickice.gui
│   │   ├── main_window.py             # MainWindow (MVVM View, 2000+ lines)
│   │   ├── viewmodel.py              # MainViewModel (MVVM ViewModel)
│   │   ├── view.py                   # UI panels: InputPanel, ProgressPanel, ViewerPanel, InfoPanel
│   │   ├── workers.py                # GenerationWorker, InterfaceGenerationWorker
│   │   ├── hydrate_worker.py          # HydrateWorker (QThread subclass)
│   │   ├── custom_molecule_worker.py  # CustomMoleculeWorker (QObject→QThread)
│   │   ├── export.py                  # All GROMACS/PDB/Diagram/Viewport exporters
│   │   ├── constants.py               # TabIndex enum
│   │   ├── validators.py              # GUI input validators (return bool, str)
│   │   ├── phase_diagram_widget.py     # Interactive phase diagram panel
│   │   ├── main_window.py             # Main window assembly and tab routing
│   │   ├── interface_panel.py          # Interface Construction tab UI
│   │   ├── interface_viewer.py         # Interface 3D viewer
│   │   ├── hydrate_panel.py           # Hydrate Generation tab UI
│   │   ├── hydrate_viewer.py          # Hydrate 3D viewer
│   │   ├── hydrate_renderer.py        # Hydrate VTK rendering functions
│   │   ├── hydrate_export.py          # HydrateGROMACSExporter
│   │   ├── ion_panel.py               # Ion Insertion tab UI
│   │   ├── ion_viewer.py              # Ion 3D viewer
│   │   ├── ion_renderer.py            # Ion VTK rendering (Na/Cl spheres)
│   │   ├── solute_panel.py            # Solute Insertion tab UI
│   │   ├── solute_viewer.py           # Solute 3D viewer
│   │   ├── solute_renderer.py         # Solute VTK rendering
│   │   ├── custom_molecule_panel.py   # Custom Molecule tab UI
│   │   ├── custom_molecule_viewer.py  # Custom molecule 3D viewer
│   │   ├── custom_molecule_renderer.py # Custom molecule VTK rendering
│   │   ├── molecular_viewer.py        # VTK molecular viewer widget
│   │   ├── dual_viewer.py             # Side-by-side dual viewport
│   │   ├── vtk_utils.py               # VTK utility functions
│   │   └── help_dialog.py             # Quick reference help dialog
│   ├── structure_generation/          # Core Model: structure generation
│   │   ├── __init__.py                # Public API re-exports
│   │   ├── types.py                   # All dataclasses (Candidate, InterfaceConfig, InterfaceStructure, etc.)
│   │   ├── generator.py              # IceStructureGenerator wrapping GenIce2
│   │   ├── interface_builder.py       # Interface orchestrator with validation + mode routing
│   │   ├── mapper.py                 # QuickIce↔GenIce phase ID mapping, supercell calculation
│   │   ├── errors.py                 # StructureGenerationError hierarchy
│   │   ├── modes/                    # Interface assembly modes
│   │   │   ├── __init__.py            # Re-exports assemble_slab, assemble_pocket, assemble_piece
│   │   │   ├── slab.py               # Ice-water-ice sandwich (Z-axis)
│   │   │   ├── pocket.py             # Water cavity in ice matrix
│   │   │   └── piece.py              # Ice crystal in water box
│   │   ├── water_filler.py           # TIP4P water template tiling
│   │   ├── overlap_resolver.py       # O-O overlap detection and removal
│   │   ├── hydrate_generator.py      # HydrateStructureGenerator (GenIce2 hydrate lattices)
│   │   ├── ion_inserter.py           # IonInserter (NaCl concentration-based placement)
│   │   ├── solute_inserter.py        # SoluteInserter (CH4/THF placement with rotation)
│   │   ├── custom_molecule_inserter.py # CustomMoleculeInserter (user GRO/ITP placement)
│   │   ├── gro_parser.py             # GRO file parser (string + file)
│   │   ├── itp_parser.py             # ITP topology file parser
│   │   ├── moleculetype_registry.py   # Unique GROMACS moleculetype naming
│   │   ├── molecule_validator.py      # Molecule structure validation
│   │   ├── cell_utils.py             # Cell orthogonality checks
│   │   └── gromacs_ion_export.py      # Ion ITP generation utilities
│   ├── phase_mapping/                # Ice phase identification
│   │   ├── __init__.py                # Re-exports lookup_phase, errors, triple points
│   │   ├── lookup.py                 # Curve-based phase lookup, PHASE_METADATA dict
│   │   ├── melting_curves.py          # IAPWS R14-08 melting pressure curves
│   │   ├── solid_boundaries.py        # Solid-solid boundary interpolations
│   │   ├── triple_points.py           # Triple point data
│   │   ├── ice_ih_density.py          # IAPWS R10-06 temperature-dependent density
│   │   ├── water_density.py           # Liquid water density calculation
│   │   ├── errors.py                  # PhaseMappingError, UnknownPhaseError
│   │   └── data/                      # Phase boundary data
│   │       ├── __init__.py
│   │       ├── ice_boundaries.py       # Boundary curve data
│   │       └── ice_phases.json         # Phase metadata JSON
│   ├── ranking/                      # Candidate scoring and ranking
│   │   ├── __init__.py                # Re-exports rank_candidates, scoring functions
│   │   ├── types.py                   # RankedCandidate, RankingResult, ScoringConfig
│   │   └── scorer.py                  # Energy/density/diversity scoring + normalization
│   ├── output/                       # File output and validation
│   │   ├── __init__.py                # Re-exports all output functions
│   │   ├── types.py                   # OutputResult dataclass
│   │   ├── pdb_writer.py             # PDB file writer with CRYST1 records
│   │   ├── gromacs_writer.py          # GRO/TOP/ITP writers (2700+ lines, all GROMACS formats)
│   │   ├── validator.py              # Space group and atomic overlap validation
│   │   ├── phase_diagram.py           # Matplotlib phase diagram generation
│   │   └── orchestrator.py            # Output pipeline orchestration
│   ├── validation/                   # Input validation (CLI and shared)
│   │   ├── __init__.py
│   │   └── validators.py             # validate_temperature, validate_pressure, validate_nmolecules
│   ├── utils/                        # Shared utilities
│   │   ├── __init__.py
│   │   └── molecule_utils.py         # count_guest_atoms and other helpers
│   └── data/                         # Bundled molecular data files
│       ├── tip4p-ice.itp              # TIP4P-ICE water model topology
│       ├── tip4p.gro                  # TIP4P water template coordinates
│       ├── ch4.itp                    # Methane topology
│       ├── ch4_hydrate.itp            # CH4 hydrate guest topology
│       ├── ch4_liquid.itp             # CH4 liquid solute topology
│       ├── thf.itp                    # THF topology
│       ├── thf_hydrate.itp            # THF hydrate guest topology
│       ├── thf_liquid.itp             # THF liquid solute topology
│       └── custom/                    # Custom molecule data directory
├── tests/                            # Test suite
│   ├── conftest.py                    # Shared test fixtures
│   ├── test_output/                   # Output-specific tests
│   │   ├── test_validator.py
│   │   ├── test_pdb_writer.py
│   │   ├── test_molecule_wrapping.py
│   │   └── test_gromacs_export_solute.py
│   ├── e2e_export_helpers.py          # E2E test utility functions
│   ├── em.mdp                         # GROMACS energy minimization input
│   ├── test_structure_generation.py   # Structure generation unit tests
│   ├── test_ranking.py               # Ranking tests
│   ├── test_phase_mapping.py          # Phase mapping tests
│   ├── test_validators.py            # Validation tests
│   ├── test_scorer_diversity.py       # Scorer diversity tests
│   ├── test_integration_v35.py        # Integration tests
│   ├── test_e2e_*.py                  # End-to-end test suite (12+ files)
│   └── ...                            # 40+ additional test files
├── docs/                             # Documentation
├── scripts/                          # Utility scripts
├── sample_output/                     # Example output files
├── environment.yml                    # Conda environment specification
├── environment-build.yml              # Build environment
├── requirements-dev.txt               # Development dependencies
├── setup.sh                          # Setup script
├── quickice-gui.spec                 # PyInstaller build spec
├── .github/workflows/                 # CI/CD
├── .planning/                         # GSD planning documents
└── build/                            # Build artifacts
```

## Directory Purposes

**`quickice/gui/`:**
- Purpose: All GUI code following MVVM pattern
- Contains: PySide6 widgets, VTK viewers, workers, exporters, validators
- Key files: `main_window.py` (View orchestrator), `viewmodel.py` (ViewModel), `workers.py` (background workers)

**`quickice/structure_generation/`:**
- Purpose: Core Model layer for all structure generation and modification
- Contains: Generators, inserters, builders, parsers, data types
- Key files: `types.py` (all dataclasses), `generator.py` (ice generation), `interface_builder.py` (interface routing), `gromacs_writer.py` moved here from output (via `gromacs_ion_export.py`)

**`quickice/phase_mapping/`:**
- Purpose: Ice phase identification from T/P conditions
- Contains: IAPWS curve-based lookup, triple points, density models
- Key files: `lookup.py` (main API), `melting_curves.py` (IAPWS R14-08)

**`quickice/ranking/`:**
- Purpose: Score and rank generated ice structure candidates
- Contains: Scoring functions (energy, density, diversity), normalization, ranking
- Key files: `scorer.py` (main algorithm), `types.py` (dataclasses)

**`quickice/output/`:**
- Purpose: File output (PDB, GROMACS, phase diagram)
- Contains: Writers for all export formats, validation, orchestration
- Key files: `gromacs_writer.py` (2700+ lines, handles all GROMACS format variants), `pdb_writer.py`

**`quickice/data/`:**
- Purpose: Bundled molecular topology and coordinate files
- Contains: .itp files (TIP4P-ICE, CH4, THF), .gro template, custom/ subdirectory
- Key files: `tip4p-ice.itp`, `tip4p.gro`

**`tests/`:**
- Purpose: Complete test suite with unit, integration, and E2E tests
- Contains: 55+ test files, conftest.py, helper modules
- Key files: `conftest.py`, `e2e_export_helpers.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI script entry point
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/main.py`: CLI main() function
- `quickice/gui/main_window.py::run_app()`: GUI application bootstrap

**Configuration:**
- `quickice/gui/constants.py`: TabIndex enum for tab positions
- `environment.yml`: Conda environment (Python 3.14, PySide6 6.10, VTK 9.5)
- `quickice-gui.spec`: PyInstaller build configuration

**Core Logic:**
- `quickice/structure_generation/types.py`: All dataclasses (Candidate, InterfaceConfig, InterfaceStructure, IonConfig, IonStructure, SoluteConfig, SoluteStructure, CustomMoleculeConfig, CustomMoleculeStructure, HydrateConfig, HydrateStructure)
- `quickice/structure_generation/generator.py`: IceStructureGenerator (GenIce2 wrapper)
- `quickice/structure_generation/interface_builder.py`: Interface generation orchestrator
- `quickice/structure_generation/modes/slab.py`: Slab interface assembly
- `quickice/structure_generation/modes/pocket.py`: Pocket interface assembly
- `quickice/structure_generation/modes/piece.py`: Piece interface assembly
- `quickice/structure_generation/hydrate_generator.py`: Hydrate lattice generation
- `quickice/structure_generation/ion_inserter.py`: Ion insertion
- `quickice/structure_generation/solute_inserter.py`: Solute insertion
- `quickice/structure_generation/custom_molecule_inserter.py`: Custom molecule placement
- `quickice/phase_mapping/lookup.py`: Phase identification API
- `quickice/ranking/scorer.py`: Candidate scoring algorithm
- `quickice/output/gromacs_writer.py`: GROMACS export (all formats)

**Testing:**
- `tests/conftest.py`: Shared fixtures
- `tests/e2e_export_helpers.py`: E2E test utilities
- `tests/test_e2e_*.py`: End-to-end test suite

**Data:**
- `quickice/data/tip4p-ice.itp`: TIP4P-ICE water model
- `quickice/data/tip4p.gro`: Water template
- `quickice/data/ch4.itp`, `ch4_hydrate.itp`, `ch4_liquid.itp`: Methane topologies
- `quickice/data/thf.itp`, `thf_hydrate.itp`, `thf_liquid.itp`: THF topologies
- `quickice/data/custom/`: Custom molecule data directory

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `interface_builder.py`, `ion_inserter.py`)
- GUI panels: `{feature}_panel.py` (e.g., `hydrate_panel.py`, `ion_panel.py`)
- GUI viewers: `{feature}_viewer.py` (e.g., `hydrate_viewer.py`, `ion_viewer.py`)
- GUI renderers: `{feature}_renderer.py` (e.g., `hydrate_renderer.py`, `ion_renderer.py`)
- Workers: `{feature}_worker.py` (e.g., `hydrate_worker.py`, `custom_molecule_worker.py`)
- Tests: `test_{feature}.py` or `test_e2e_{feature}.py` for end-to-end tests

**Directories:**
- Package modules: `snake_case/` (e.g., `structure_generation/`, `phase_mapping/`)
- Sub-modules: `modes/` for interface modes, `data/` for bundled data

**Classes:**
- Data types: PascalCase (e.g., `Candidate`, `InterfaceStructure`, `IonInserter`)
- Workers: `{Feature}Worker` (e.g., `GenerationWorker`, `HydrateWorker`)
- Generators: `{Feature}Generator` (e.g., `IceStructureGenerator`, `HydrateStructureGenerator`)
- Exporters: `{Feature}Exporter` or `{Feature}GROMACSExporter` (e.g., `PDBExporter`, `IonGROMACSExporter`)

## Where to Add New Code

**New Ice Phase Support:**
- Phase mapping: `quickice/phase_mapping/lookup.py` (add to `PHASE_METADATA`), `quickice/phase_mapping/melting_curves.py` or `solid_boundaries.py` (add boundary curves)
- Generation: `quickice/structure_generation/mapper.py` (add to `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES`)
- Validation: `quickice/structure_generation/generator.py` (no changes needed if GenIce supports it)

**New Interface Mode:**
- Implementation: `quickice/structure_generation/modes/` (new file, e.g., `cylinder.py` with `assemble_cylinder` function)
- Routing: `quickice/structure_generation/interface_builder.py` (add import + route in `generate_interface()`)
- Validation: `quickice/structure_generation/interface_builder.py` (add mode-specific checks in `validate_interface_config()`)
- UI: `quickice/gui/interface_panel.py` (add mode to dropdown, add mode-specific input fields)

**New Insertion Type (like ions/solutes):**
- Model: `quickice/structure_generation/{name}_inserter.py` with `{Name}Inserter` class
- Types: `quickice/structure_generation/types.py` (add `{Name}Config` and `{Name}Structure` dataclasses)
- Worker: `quickice/gui/{name}_worker.py` with `{Name}Worker(QObject)` following the worker pattern
- UI panel: `quickice/gui/{name}_panel.py` with `{Name}Panel(QWidget)`
- UI viewer: `quickice/gui/{name}_viewer.py` with `{Name}Viewer(QWidget)`
- UI renderer: `quickice/gui/{name}_renderer.py` with VTK rendering functions
- Export: `quickice/gui/export.py` (add `{Name}GROMACSExporter`)
- GROMACS writer: `quickice/output/gromacs_writer.py` (add write function, add to `MOLECULE_TO_GROMACS`)
- Data: `quickice/data/` (add .itp files)
- Tab: Add to `quickice/gui/constants.py` (TabIndex), `quickice/gui/main_window.py` (setup + connections)

**New GROMACS Export Format:**
- Writer: `quickice/output/gromacs_writer.py` (add write function)
- Exporter: `quickice/gui/export.py` (add exporter class)
- Menu: `quickice/gui/main_window.py` (add menu action + shortcut)

**New Test:**
- Unit tests: `tests/test_{feature}.py`
- E2E tests: `tests/test_e2e_{feature}.py`
- Output tests: `tests/test_output/test_{feature}.py`

**New Data File:**
- Place in: `quickice/data/`
- Reference via: `quickice/output/gromacs_writer.py::get_tip4p_itp_path()` pattern (uses `importlib.resources` or `Path(__file__).parent / "data"`)

## Special Directories

**`quickice/data/custom/`:**
- Purpose: Custom molecule data storage (uploaded by user)
- Generated: Partially (user-uploaded files)
- Committed: Directory structure yes, user data no

**`quickice/structure_generation/modes/`:**
- Purpose: Interface assembly mode implementations
- Contains: `slab.py`, `pocket.py`, `piece.py`
- Pattern: Each module exports a single `assemble_{mode}()` function

**`quickice/phase_mapping/data/`:**
- Purpose: Phase boundary data (curves, JSON metadata)
- Generated: No
- Committed: Yes

**`tests/test_output/`:**
- Purpose: Output-specific test suite (separated from main test directory)
- Contains: Validation, PDB writer, GROMACS export tests

**`output/`:**
- Purpose: Default output directory for generated files
- Generated: Yes (created by CLI/GUI at runtime)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-06-12*
