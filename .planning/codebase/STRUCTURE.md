# Codebase Structure

**Analysis Date:** 2026-04-11

## Directory Layout

```
quickice/                          # Project root
├── quickice.py                    # CLI entry point script
├── quickice/                      # Main Python package
│   ├── __init__.py                # Package init, version string
│   ├── main.py                    # CLI orchestration (pipeline wiring)
│   ├── cli/                       # CLI argument parsing
│   │   ├── __init__.py
│   │   └── parser.py              # argparse configuration
│   ├── validation/                # Input validation (CLI validators)
│   │   ├── __init__.py
│   │   └── validators.py          # validate_temperature, validate_pressure, validate_nmolecules
│   ├── phase_mapping/             # Ice phase identification from T,P
│   │   ├── __init__.py            # Re-exports: lookup_phase, IcePhaseLookup, errors, triple points
│   │   ├── lookup.py              # Curve-based lookup_phase(), IcePhaseLookup class, PHASE_METADATA
│   │   ├── errors.py              # PhaseMappingError, UnknownPhaseError
│   │   ├── melting_curves.py      # IAPWS R14-08 melting pressure equations (Ih, III, V, VI, VII)
│   │   ├── solid_boundaries.py    # Linear interpolation boundaries (Ih-II, II-III, III-V, etc.)
│   │   ├── triple_points.py       # TRIPLE_POINTS dict, get_triple_point()
│   │   └── data/                  # Legacy/backup phase data
│   │       ├── __init__.py
│   │       ├── ice_boundaries.py  # Simon-Glatzel approximations (legacy)
│   │       └── ice_phases.json    # Polygon definitions (legacy)
│   ├── structure_generation/       # Ice structure generation and interface building
│   │   ├── __init__.py            # Re-exports: types, mapper, generator, interface, filler
│   │   ├── types.py               # Candidate, GenerationResult, InterfaceConfig, InterfaceStructure
│   │   ├── errors.py              # StructureGenerationError, UnsupportedPhaseError, InterfaceGenerationError
│   │   ├── mapper.py              # PHASE_TO_GENICE, UNIT_CELL_MOLECULES, calculate_supercell()
│   │   ├── generator.py           # IceStructureGenerator, generate_candidates()
│   │   ├── interface_builder.py   # generate_interface(), validate_interface_config(), mode routing
│   │   ├── overlap_resolver.py    # detect_overlaps(), remove_overlapping_molecules()
│   │   ├── water_filler.py        # load_water_template(), tile_structure(), fill_region_with_water()
│   │   └── modes/                 # Interface generation modes
│   │       ├── __init__.py
│   │       ├── slab.py            # assemble_slab() — ice slab + water layer
│   │       ├── pocket.py          # assemble_pocket() — ice with water cavity
│   │       └── piece.py          # assemble_piece() — ice piece in water box
│   ├── ranking/                   # Candidate scoring and ranking
│   │   ├── __init__.py            # Re-exports: types, scorer functions
│   │   ├── types.py               # ScoringConfig, RankedCandidate, RankingResult
│   │   └── scorer.py             # energy_score(), density_score(), diversity_score(), rank_candidates()
│   ├── output/                    # File output and validation
│   │   ├── __init__.py            # Re-exports: OutputResult, orchestrator, writers, validator
│   │   ├── types.py               # OutputResult dataclass
│   │   ├── orchestrator.py        # output_ranked_candidates() — coordinates PDB + validation + diagram
│   │   ├── pdb_writer.py          # write_pdb_with_cryst1(), write_ranked_candidates()
│   │   ├── gromacs_writer.py     # write_gro_file(), write_top_file(), get_tip4p_itp_path()
│   │   ├── phase_diagram.py      # generate_phase_diagram(), polygon builders, matplotlib rendering
│   │   └── validator.py          # validate_space_group(), check_atomic_overlap() — spglib + cKDTree
│   ├── gui/                       # PySide6 GUI application
│   │   ├── __init__.py            # Re-exports: MainWindow, run_app, PhaseDiagramPanel
│   │   ├── __main__.py            # GUI entry point (python -m quickice.gui)
│   │   ├── main_window.py        # MainWindow — assembles all panels, menu bar, signal wiring
│   │   ├── viewmodel.py          # MainViewModel — MVVM ViewModel, QThread management, signal forwarding
│   │   ├── workers.py            # GenerationWorker, InterfaceGenerationWorker — background QThread workers
│   │   ├── view.py               # InputPanel, ProgressPanel, ViewerPanel, InfoPanel — UI components
│   │   ├── validators.py         # GUI-specific validators returning (bool, str) tuples
│   │   ├── phase_diagram_widget.py # PhaseDiagramCanvas (matplotlib), PhaseDiagramPanel, PhaseDetector
│   │   ├── dual_viewer.py        # DualViewerWidget — side-by-side candidate comparison
│   │   ├── molecular_viewer.py    # MolecularViewerWidget — VTK-based 3D molecular renderer
│   │   ├── interface_viewer.py    # InterfaceViewerWidget — VTK renderer for ice-water interfaces
│   │   ├── vtk_utils.py          # candidate_to_vtk_molecule(), interface_to_vtk_molecules(), actor helpers
│   │   ├── interface_panel.py    # InterfacePanel — Tab 2 UI for interface construction configuration
│   │   ├── export.py             # PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter
│   │   └── help_dialog.py        # QuickReferenceDialog — modal keyboard shortcut reference
│   └── data/                      # Bundled static data files
│       ├── tip4p-ice.itp          # GROMACS TIP4P-ICE topology template
│       └── tip4p.gro              # TIP4P water template (4 atoms per molecule)
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_phase_mapping.py
│   ├── test_structure_generation.py
│   ├── test_ranking.py
│   ├── test_validators.py
│   ├── test_cli_integration.py
│   ├── test_atom_names_filtering.py
│   ├── test_atom_ordering_validation.py
│   ├── test_interface_ordering_validation.py
│   ├── test_med03_minimum_box_size.py
│   ├── test_pbc_hbonds.py
│   ├── test_piece_mode_validation.py
│   └── test_output/
│       ├── __init__.py
│       ├── test_pdb_writer.py
│       └── test_validator.py
├── scripts/                       # Build scripts
│   ├── build-linux.sh
│   └── assemble-dist.sh
├── docs/                           # Documentation
├── sample_output/                  # Example output files
│   ├── cli/
│   └── gui_interface/
├── environment.yml                # Conda environment definition
├── environment-build.yml           # Conda env for PyInstaller builds
├── requirements-dev.txt            # Dev dependencies (pytest, pyinstaller)
├── quickice-gui.spec              # PyInstaller spec for GUI binary
├── setup.sh                       # Environment setup script
└── README.md                       # Project documentation
```

## Directory Purposes

**`quickice/` (package root):**
- Purpose: Main Python package containing all application code
- Contains: 9 subpackages, 2 top-level modules (`__init__.py`, `main.py`)
- Key files: `quickice/main.py` is the CLI orchestrator

**`quickice/cli/`:**
- Purpose: CLI argument parsing only (no business logic)
- Contains: Single parser module using argparse
- Key files: `quickice/cli/parser.py`

**`quickice/validation/`:**
- Purpose: Input validation functions shared across CLI
- Contains: Type validators for temperature, pressure, molecule count
- Key files: `quickice/validation/validators.py`
- Note: GUI has its own validators in `quickice/gui/validators.py` (different error interface)

**`quickice/phase_mapping/`:**
- Purpose: Scientific ice phase identification using IAPWS-validated boundary curves
- Contains: Lookup algorithm, melting curve equations, solid-solid boundaries, triple point data
- Key files: `quickice/phase_mapping/lookup.py` (main API), `quickice/phase_mapping/melting_curves.py` (IAPWS equations)
- Note: `quickice/phase_mapping/data/` contains legacy polygon-based data (ice_boundaries.py, ice_phases.json) — kept for reference but not used by lookup

**`quickice/structure_generation/`:**
- Purpose: Crystal structure generation via GenIce2 + ice-water interface construction
- Contains: Generator wrapper, phase-to-GenIce mapper, 3 interface modes, water filling, overlap detection
- Key files: `quickice/structure_generation/generator.py` (main API), `quickice/structure_generation/types.py` (core data types)
- Subpackage `modes/`: Contains `slab.py`, `pocket.py`, `piece.py` for interface generation

**`quickice/ranking/`:**
- Purpose: Heuristic scoring and ranking of generated candidates
- Contains: Three scoring functions + weighted combination + normalization
- Key files: `quickice/ranking/scorer.py` (main API), `quickice/ranking/types.py` (data types)

**`quickice/output/`:**
- Purpose: File I/O — PDB, GROMACS, phase diagrams, structure validation
- Contains: 5 writer/validator modules + orchestrator
- Key files: `quickice/output/orchestrator.py` (main API), `quickice/output/gromacs_writer.py`, `quickice/output/phase_diagram.py`

**`quickice/gui/`:**
- Purpose: Complete PySide6 GUI with MVVM architecture, VTK 3D visualization
- Contains: 15 modules covering main window, viewmodel, workers, panels, viewers, exporters
- Key files: `quickice/gui/main_window.py` (View), `quickice/gui/viewmodel.py` (ViewModel), `quickice/gui/workers.py` (Model access)

**`quickice/data/`:**
- Purpose: Bundled static resource files used at runtime
- Contains: GROMACS TIP4P-ICE topology (`.itp`) and water template (`.gro`)
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`
- Note: Accessed via `Path(__file__).parent / "data"` pattern

**`tests/`:**
- Purpose: Pytest test suite
- Contains: 12 test files covering phase mapping, structure generation, ranking, validation, output
- Key files: `tests/test_phase_mapping.py`, `tests/test_structure_generation.py`, `tests/test_ranking.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry point script (project root)
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/main.py`: CLI pipeline orchestrator

**Configuration:**
- `environment.yml`: Conda environment (runtime + dev dependencies)
- `environment-build.yml`: Conda env for PyInstaller builds
- `requirements-dev.txt`: Dev-only pip dependencies (pytest, pyinstaller)
- `quickice-gui.spec`: PyInstaller binary build spec

**Core Data Types:**
- `quickice/structure_generation/types.py`: `Candidate`, `GenerationResult`, `InterfaceConfig`, `InterfaceStructure`
- `quickice/ranking/types.py`: `RankedCandidate`, `RankingResult`, `ScoringConfig`
- `quickice/output/types.py`: `OutputResult`

**Core Logic:**
- `quickice/phase_mapping/lookup.py`: `lookup_phase()`, `PHASE_METADATA`
- `quickice/structure_generation/generator.py`: `IceStructureGenerator`, `generate_candidates()`
- `quickice/ranking/scorer.py`: `rank_candidates()`, `energy_score()`, `density_score()`, `diversity_score()`
- `quickice/output/orchestrator.py`: `output_ranked_candidates()`
- `quickice/structure_generation/interface_builder.py`: `generate_interface()`, `validate_interface_config()`

**Testing:**
- `tests/test_phase_mapping.py`: Phase lookup and boundary curve tests
- `tests/test_structure_generation.py`: Generator and supercell tests
- `tests/test_ranking.py`: Scoring and ranking tests
- `tests/test_output/test_pdb_writer.py`: PDB output tests
- `tests/test_output/test_validator.py`: Structure validation tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `phase_diagram.py`, `water_filler.py`)
- Data files: `kebab-case.ext` (e.g., `tip4p-ice.itp`, `tip4p.gro`)
- Test files: `test_{module_name}.py` (e.g., `test_phase_mapping.py`, `test_ranking.py`)
- Spec files: `kebab-case.spec` (e.g., `quickice-gui.spec`)
- Shell scripts: `kebab-case.sh` (e.g., `build-linux.sh`)

**Directories:**
- Package directories: `snake_case` (e.g., `phase_mapping`, `structure_generation`)
- Sub-package for modes: `modes/` (simple noun)
- Sub-package for test sub-groups: `test_output/`

**Classes:**
- Main window/view: `PascalCase` (e.g., `MainWindow`, `InputPanel`, `PhaseDiagramPanel`)
- Worker classes: `PascalCase` + `Worker` suffix (e.g., `GenerationWorker`, `InterfaceGenerationWorker`)
- Viewer widgets: `PascalCase` + `Viewer` suffix (e.g., `MolecularViewerWidget`, `InterfaceViewerWidget`)
- Data types: `PascalCase` (e.g., `Candidate`, `RankedCandidate`, `InterfaceConfig`)
- Error classes: `PascalCase` + `Error` suffix (e.g., `UnknownPhaseError`, `InterfaceGenerationError`)

**Functions:**
- Public API: `snake_case` verbs (e.g., `lookup_phase()`, `generate_candidates()`, `rank_candidates()`)
- Private helpers: `_leading_underscore` (e.g., `_build_result()`, `_parse_gro()`)
- Validators: `validate_` prefix (e.g., `validate_temperature()`, `validate_nmolecules()`)
- Scoring: `_score` suffix (e.g., `energy_score()`, `density_score()`)
- Builders: `_build_` prefix for polygon construction (e.g., `_build_ice_ih_polygon()`)
- Unit conversion: `angstrom_to_nm()`, `nm_to_angstrom()`

**Variables/Constants:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `TRIPLE_POINTS`)
- Private module-level: `_leading_underscore` (e.g., `_SHARED_BOUNDARY_CACHE`, `_VTK_AVAILABLE`, `_water_template_cache`)

## Where to Add New Code

**New Ice Phase:**
- Phase boundary functions: `quickice/phase_mapping/solid_boundaries.py`
- Phase lookup logic: `quickice/phase_mapping/lookup.py` (add to hierarchical algorithm)
- Phase metadata: `quickice/phase_mapping/lookup.py` `PHASE_METADATA` dict
- Phase polygon for diagram: `quickice/output/phase_diagram.py` (`_build_{phase_id}_polygon()`)
- Phase colors/labels: `quickice/output/phase_diagram.py` (`PHASE_COLORS`, `PHASE_LABELS`, `PHASE_NAMES`)
- GenIce mapping: `quickice/structure_generation/mapper.py` (`PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`)
- Tests: `tests/test_phase_mapping.py`

**New Interface Mode:**
- Mode implementation: `quickice/structure_generation/modes/{mode_name}.py` (define `assemble_{mode_name}()`)
- Mode routing: `quickice/structure_generation/interface_builder.py` (add to `generate_interface()`)
- Validation: `quickice/structure_generation/interface_builder.py` (add to `validate_interface_config()`)
- GUI panel controls: `quickice/gui/interface_panel.py` (add mode UI widgets)
- Tests: `tests/test_{mode_name}_validation.py`

**New Scoring Function:**
- Score implementation: `quickice/ranking/scorer.py`
- Type update: `quickice/ranking/types.py` (add score field to `RankedCandidate`, weight to config)
- Weight handling: `quickice/ranking/scorer.py` `rank_candidates()` (add to combined score)
- Tests: `tests/test_ranking.py`

**New Output Format:**
- Writer module: `quickice/output/{format}_writer.py`
- Orchestrator integration: `quickice/output/orchestrator.py` (add format to `output_ranked_candidates()`)
- CLI flag: `quickice/cli/parser.py` (add `--{format}` argument)
- CLI orchestration: `quickice/main.py` (add format export block)
- GUI export handler: `quickice/gui/export.py` (add exporter class + menu action)
- GUI menu: `quickice/gui/main_window.py` (`_create_menu_bar()`)

**New GUI Panel/Widget:**
- Widget implementation: `quickice/gui/{widget_name}.py`
- Integration: `quickice/gui/main_window.py` (add to layout + signal connections)
- If background work needed: `quickice/gui/workers.py` (add worker class)
- ViewModel update: `quickice/gui/viewmodel.py` (add signals + thread management)

**New CLI Option:**
- Argument definition: `quickice/cli/parser.py` (add to `create_parser()`)
- Pipeline integration: `quickice/main.py` (use new argument in pipeline)
- Tests: `tests/test_cli_integration.py`

**New Utility/Helper:**
- Domain utilities: Appropriate domain package (e.g., `quickice/structure_generation/` for structure helpers)
- GUI utilities: `quickice/gui/vtk_utils.py` (VTK conversion helpers)
- Shared types: Domain-specific `types.py` files (e.g., `quickice/structure_generation/types.py`)

## Special Directories

**`quickice/phase_mapping/data/`:**
- Purpose: Legacy polygon-based phase boundary data (JSON + Simon-Glatzel approximations)
- Generated: No (manually curated)
- Committed: Yes
- Note: NOT used by current lookup algorithm — curve-based functions in `lookup.py` are the single source of truth. Kept for reference/backup only.

**`quickice/data/`:**
- Purpose: Bundled runtime resource files (GROMACS templates)
- Generated: No (manually provided)
- Committed: Yes
- Note: Accessed via `Path(__file__).parent / "data"` to work regardless of CWD

**`build/`:**
- Purpose: PyInstaller build artifacts
- Generated: Yes (by `scripts/build-linux.sh`)
- Committed: No (in `.gitignore`)

**`dist/`:**
- Purpose: Final distributable binaries
- Generated: Yes (by PyInstaller)
- Committed: No (in `.gitignore`)

**`sample_output/`:**
- Purpose: Example output files for documentation/demonstration
- Generated: Partially (some manually created, some from tool runs)
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning documents (phases, milestones, codebase analysis)
- Generated: Yes (by GSD commands)
- Committed: Yes

**`docs/`:**
- Purpose: Documentation files and images
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-04-11*
