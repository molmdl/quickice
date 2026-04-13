# Codebase Structure

**Analysis Date:** 2026-04-13

## Directory Layout

```
quickice/                          # Project root
├── quickice.py                    # CLI entry point script
├── quickice/                      # Main Python package
│   ├── __init__.py                # Package init, version string (3.0.0)
│   ├── main.py                    # CLI orchestration (pipeline wiring)
│   ├── cli/                       # CLI argument parsing
│   │   ├── __init__.py
│   │   └── parser.py              # argparse configuration, validate_interface_args()
│   ├── validation/                # Input validation (CLI validators)
│   │   ├── __init__.py
│   │   └── validators.py          # validate_temperature, validate_pressure, validate_nmolecules, validate_positive_float, validate_box_dimension
│   ├── phase_mapping/             # Ice phase identification from T,P
│   │   ├── __init__.py            # Re-exports: lookup_phase, IcePhaseLookup, errors, triple points, melting_pressure, solid_boundary
│   │   ├── lookup.py              # Curve-based lookup_phase(), IcePhaseLookup class, PHASE_METADATA
│   │   ├── errors.py              # PhaseMappingError, UnknownPhaseError
│   │   ├── melting_curves.py      # IAPWS R14-08 melting pressure equations (Ih, III, V, VI, VII)
│   │   ├── solid_boundaries.py    # Linear interpolation boundaries (Ih-II, II-III, III-V, II-V, V-VI, VI-VII, VII-VIII, XI, IX, X, XV)
│   │   ├── triple_points.py       # TRIPLE_POINTS dict, get_triple_point()
│   │   ├── ice_ih_density.py     # IAPWS R10-06(2009) temperature-dependent Ice Ih density
│   │   ├── water_density.py      # IAPWS-based liquid water density calculator
│   │   └── data/                  # Legacy/backup phase data
│   │       ├── __init__.py
│   │       └── ice_boundaries.py  # Simon-Glatzel approximations (legacy, NOT used by lookup)
│   ├── structure_generation/       # Ice structure generation and interface building
│   │   ├── __init__.py            # Re-exports: types, mapper, generator, interface, filler, overlap resolver
│   │   ├── types.py               # Candidate, GenerationResult, InterfaceConfig, InterfaceStructure
│   │   ├── errors.py              # StructureGenerationError, UnsupportedPhaseError, InterfaceGenerationError
│   │   ├── mapper.py              # PHASE_TO_GENICE, UNIT_CELL_MOLECULES, calculate_supercell(), get_genice_lattice_name()
│   │   ├── generator.py           # IceStructureGenerator, generate_candidates()
│   │   ├── interface_builder.py   # generate_interface(), validate_interface_config(), mode routing
│   │   ├── overlap_resolver.py    # detect_overlaps(), remove_overlapping_molecules(), angstrom_to_nm(), nm_to_angstrom()
│   │   ├── water_filler.py        # load_water_template(), tile_structure(), fill_region_with_water(), get_cell_extent()
│   │   └── modes/                 # Interface generation modes
│   │       ├── __init__.py        # Re-exports: assemble_slab, assemble_pocket, assemble_piece
│   │       ├── slab.py            # assemble_slab() — ice | water | ice sandwich along Z
│   │       ├── pocket.py          # assemble_pocket() — water cavity carved from ice matrix
│   │       └── piece.py          # assemble_piece() — ice crystal fragment centered in water box
│   ├── ranking/                   # Candidate scoring and ranking
│   │   ├── __init__.py            # Re-exports: types, scorer functions
│   │   ├── types.py               # ScoringConfig, RankedCandidate, RankingResult
│   │   └── scorer.py             # energy_score(), density_score(), diversity_score(), normalize_scores(), rank_candidates()
│   ├── output/                    # File output and validation
│   │   ├── __init__.py            # Re-exports: OutputResult, orchestrator, writers, validator
│   │   ├── types.py               # OutputResult dataclass
│   │   ├── orchestrator.py        # output_ranked_candidates() — coordinates PDB + validation + diagram
│   │   ├── pdb_writer.py          # write_pdb_with_cryst1(), write_ranked_candidates()
│   │   ├── gromacs_writer.py     # write_gro_file(), write_top_file(), write_interface_gro_file(), write_interface_top_file(), get_tip4p_itp_path()
│   │   ├── phase_diagram.py      # generate_phase_diagram(), polygon builders, PHASE_COLORS, PHASE_LABELS, IAPWS_MELTING_RANGES
│   │   └── validator.py          # validate_space_group(), check_atomic_overlap() — spglib + cKDTree
│   ├── gui/                       # PySide6 GUI application
│   │   ├── __init__.py            # Re-exports: MainWindow, run_app, PhaseDiagramPanel
│   │   ├── __main__.py            # GUI entry point (python -m quickice.gui)
│   │   ├── main_window.py        # MainWindow — assembles all panels, menu bar, signal wiring
│   │   ├── viewmodel.py          # MainViewModel — MVVM ViewModel, QThread management, signal forwarding
│   │   ├── workers.py            # GenerationWorker, InterfaceGenerationWorker — background QThread workers
│   │   ├── view.py               # InputPanel, ProgressPanel, ViewerPanel, InfoPanel, HelpIcon — UI components
│   │   ├── validators.py         # GUI-specific validators returning (bool, str) tuples
│   │   ├── phase_diagram_widget.py # PhaseDiagramCanvas (matplotlib), PhaseDiagramPanel, PhaseDetector
│   │   ├── dual_viewer.py        # DualViewerWidget — side-by-side candidate comparison
│   │   ├── molecular_viewer.py    # MolecularViewerWidget — VTK-based 3D molecular renderer
│   │   ├── interface_viewer.py    # InterfaceViewerWidget — VTK renderer for ice-water interfaces
│   │   ├── vtk_utils.py          # candidate_to_vtk_molecule(), interface_to_vtk_molecules(), actor helpers
│   │   ├── interface_panel.py    # InterfacePanel — Tab 2 UI for interface construction configuration
│   │   ├── export.py             # PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter, InterfaceGROMACSExporter
│   │   └── help_dialog.py        # QuickReferenceDialog — modal keyboard shortcut reference
│   └── data/                      # Bundled static data files
│       ├── tip4p-ice.itp          # GROMACS TIP4P-ICE topology template
│       └── tip4p.gro              # TIP4P water template (4 atoms per molecule: OW, HW1, HW2, MW)
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_phase_mapping.py      # Phase lookup and boundary curve tests
│   ├── test_structure_generation.py # Generator and supercell tests
│   ├── test_ranking.py            # Scoring and ranking tests
│   ├── test_validators.py         # CLI validator tests
│   ├── test_cli_integration.py   # Full CLI pipeline integration tests
│   ├── test_ice_ih_density.py     # IAPWS Ice Ih density tests
│   ├── test_water_density.py     # IAPWS water density tests
│   ├── test_integration_v35.py   # Integration tests for v3.5 features
│   ├── test_atom_names_filtering.py # Atom name filtering tests
│   ├── test_atom_ordering_validation.py # Atom ordering tests
│   ├── test_interface_ordering_validation.py # Interface atom ordering tests
│   ├── test_med03_minimum_box_size.py # Minimum box size validation tests
│   ├── test_pbc_hbonds.py        # PBC hydrogen bond tests
│   ├── test_piece_mode_validation.py # Piece mode validation tests
│   ├── test_triclinic_interface.py # Triclinic cell interface tests
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
├── environment.yml                # Conda environment definition (runtime + dev)
├── environment-build.yml           # Conda env for PyInstaller builds
├── requirements-dev.txt            # Dev-only pip dependencies (pytest, pyinstaller)
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
- Purpose: Input validation functions for CLI
- Contains: Type validators for temperature, pressure, molecule count, positive float, box dimension
- Key files: `quickice/validation/validators.py`
- Note: GUI has its own validators in `quickice/gui/validators.py` (different error interface: `(bool, str)` tuples vs `ArgumentTypeError`)

**`quickice/phase_mapping/`:**
- Purpose: Scientific ice phase identification using IAPWS-validated boundary curves
- Contains: Lookup algorithm, melting curve equations, solid-solid boundaries, triple point data, density calculators
- Key files: `quickice/phase_mapping/lookup.py` (main API), `quickice/phase_mapping/melting_curves.py` (IAPWS equations), `quickice/phase_mapping/ice_ih_density.py` (IAPWS R10-06 density), `quickice/phase_mapping/water_density.py` (liquid water density)
- Note: `quickice/phase_mapping/data/` contains legacy polygon-based data (`ice_boundaries.py`) — kept for reference but NOT used by current lookup algorithm

**`quickice/structure_generation/`:**
- Purpose: Crystal structure generation via GenIce2 + ice-water interface construction
- Contains: Generator wrapper, phase-to-GenIce mapper, 3 interface modes, water filling, overlap detection, unit conversion helpers
- Key files: `quickice/structure_generation/generator.py` (main API), `quickice/structure_generation/types.py` (core data types), `quickice/structure_generation/interface_builder.py` (mode routing + validation)
- Subpackage `modes/`: Contains `slab.py`, `pocket.py`, `piece.py` for interface geometry assembly

**`quickice/ranking/`:**
- Purpose: Heuristic scoring and ranking of generated candidates
- Contains: Three scoring functions (energy, density, diversity) + weighted combination + normalization
- Key files: `quickice/ranking/scorer.py` (main API), `quickice/ranking/types.py` (data types)

**`quickice/output/`:**
- Purpose: File I/O — PDB, GROMACS, phase diagrams, structure validation
- Contains: 5 writer/validator modules + orchestrator + types
- Key files: `quickice/output/orchestrator.py` (main API), `quickice/output/gromacs_writer.py`, `quickice/output/phase_diagram.py`

**`quickice/gui/`:**
- Purpose: Complete PySide6 GUI with MVVM architecture, VTK 3D visualization
- Contains: 15 modules covering main window, viewmodel, workers, panels, viewers, exporters
- Key files: `quickice/gui/main_window.py` (View), `quickice/gui/viewmodel.py` (ViewModel), `quickice/gui/workers.py` (Model access via QThread)

**`quickice/data/`:**
- Purpose: Bundled static resource files used at runtime
- Contains: GROMACS TIP4P-ICE topology (`.itp`) and water template (`.gro`)
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`
- Note: Accessed via `Path(__file__).parent / "data"` pattern to work regardless of CWD

**`tests/`:**
- Purpose: Pytest test suite
- Contains: 15 test files covering phase mapping, structure generation, ranking, validation, output, interfaces, density
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
- `quickice/phase_mapping/lookup.py`: `lookup_phase()`, `PHASE_METADATA`, `IcePhaseLookup`
- `quickice/phase_mapping/melting_curves.py`: `melting_pressure()` (IAPWS R14-08 for Ih, III, V, VI, VII)
- `quickice/phase_mapping/solid_boundaries.py`: `ih_ii_boundary()`, `ii_iii_boundary()`, `iii_v_boundary()`, etc.
- `quickice/phase_mapping/ice_ih_density.py`: `ice_ih_density_gcm3()` (IAPWS R10-06)
- `quickice/phase_mapping/water_density.py`: `water_density_gcm3()`
- `quickice/structure_generation/generator.py`: `IceStructureGenerator`, `generate_candidates()`
- `quickice/structure_generation/mapper.py`: `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `calculate_supercell()`
- `quickice/structure_generation/interface_builder.py`: `generate_interface()`, `validate_interface_config()`
- `quickice/ranking/scorer.py`: `rank_candidates()`, `energy_score()`, `density_score()`, `diversity_score()`
- `quickice/output/orchestrator.py`: `output_ranked_candidates()`
- `quickice/output/gromacs_writer.py`: `write_gro_file()`, `write_top_file()`, `write_interface_gro_file()`, `write_interface_top_file()`

**Error Types:**
- `quickice/phase_mapping/errors.py`: `PhaseMappingError`, `UnknownPhaseError`
- `quickice/structure_generation/errors.py`: `StructureGenerationError`, `UnsupportedPhaseError`, `InterfaceGenerationError`

**Testing:**
- `tests/test_phase_mapping.py`: Phase lookup and boundary curve tests
- `tests/test_structure_generation.py`: Generator and supercell tests
- `tests/test_ranking.py`: Scoring and ranking tests
- `tests/test_validators.py`: CLI validator tests
- `tests/test_cli_integration.py`: Full CLI pipeline integration tests
- `tests/test_ice_ih_density.py`: IAPWS Ice Ih density tests
- `tests/test_water_density.py`: IAPWS water density tests
- `tests/test_output/test_pdb_writer.py`: PDB output tests
- `tests/test_output/test_validator.py`: Structure validation tests
- `tests/test_triclinic_interface.py`: Triclinic cell interface tests

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
- Viewer widgets: `PascalCase` + `ViewerWidget` suffix (e.g., `MolecularViewerWidget`, `InterfaceViewerWidget`, `DualViewerWidget`)
- Data types: `PascalCase` (e.g., `Candidate`, `RankedCandidate`, `InterfaceConfig`)
- Error classes: `PascalCase` + `Error` suffix (e.g., `UnknownPhaseError`, `InterfaceGenerationError`)
- Result containers: `PascalCase` + `Result` suffix (e.g., `GenerationResult`, `RankingResult`, `OutputResult`)
- Config containers: `PascalCase` + `Config` suffix (e.g., `ScoringConfig`, `InterfaceConfig`)

**Functions:**
- Public API: `snake_case` verbs (e.g., `lookup_phase()`, `generate_candidates()`, `rank_candidates()`)
- Private helpers: `_leading_underscore` (e.g., `_build_result()`, `_parse_gro()`, `_calculate_oo_distances_pbc()`)
- Validators: `validate_` prefix (e.g., `validate_temperature()`, `validate_nmolecules()`, `validate_interface_config()`)
- Scoring: `_score` suffix (e.g., `energy_score()`, `density_score()`)
- Assembly: `assemble_` prefix for interface modes (e.g., `assemble_slab()`, `assemble_pocket()`)
- Writers: `write_` prefix (e.g., `write_gro_file()`, `write_pdb_with_cryst1()`)
- Builders: `_build_` prefix for polygon/data construction (e.g., `_build_result()`, `_build_phase_polygon_from_curves()`)
- Unit conversion: `angstrom_to_nm()`, `nm_to_angstrom()`

**Variables/Constants:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `TRIPLE_POINTS`, `PHASE_METADATA`, `TIP4P_ICE_ALPHA`)
- Private module-level: `_leading_underscore` (e.g., `_SHARED_BOUNDARY_CACHE`, `_VTK_AVAILABLE`, `_water_template_cache`)

## Where to Add New Code

**New Ice Phase:**
- Phase boundary functions: `quickice/phase_mapping/solid_boundaries.py` (add boundary function)
- Phase lookup logic: `quickice/phase_mapping/lookup.py` (add to hierarchical algorithm, add to `PHASE_METADATA`)
- Phase polygon for diagram: `quickice/output/phase_diagram.py` (`_build_{phase_id}_polygon()`)
- Phase colors/labels: `quickice/output/phase_diagram.py` (`PHASE_COLORS`, `PHASE_LABELS`, `PHASE_NAMES`)
- GenIce mapping: `quickice/structure_generation/mapper.py` (`PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`)
- Tests: `tests/test_phase_mapping.py`

**New Interface Mode:**
- Mode implementation: `quickice/structure_generation/modes/{mode_name}.py` (define `assemble_{mode_name}()`)
- Mode re-export: `quickice/structure_generation/modes/__init__.py`
- Mode routing: `quickice/structure_generation/interface_builder.py` (add to `generate_interface()` and `validate_interface_config()`)
- GUI panel controls: `quickice/gui/interface_panel.py` (add mode UI widgets)
- GUI viewer: `quickice/gui/vtk_utils.py` (add VTK rendering if needed)
- Tests: `tests/test_{mode_name}_validation.py`

**New Scoring Function:**
- Score implementation: `quickice/ranking/scorer.py`
- Type update: `quickice/ranking/types.py` (add score field to `RankedCandidate`, weight key to config)
- Weight handling: `quickice/ranking/scorer.py` `rank_candidates()` (add to combined score calculation)
- Tests: `tests/test_ranking.py`

**New Output Format:**
- Writer module: `quickice/output/{format}_writer.py`
- Orchestrator integration: `quickice/output/orchestrator.py` (add format to `output_ranked_candidates()`)
- CLI flag: `quickice/cli/parser.py` (add `--{format}` argument)
- CLI orchestration: `quickice/main.py` (add format export block)
- GUI export handler: `quickice/gui/export.py` (add exporter class)
- GUI menu: `quickice/gui/main_window.py` (`_create_menu_bar()`)

**New GUI Panel/Widget:**
- Widget implementation: `quickice/gui/{widget_name}.py`
- Integration: `quickice/gui/main_window.py` (add to layout + signal connections in `_setup_ui()` and `_setup_connections()`)
- If background work needed: `quickice/gui/workers.py` (add worker class)
- ViewModel update: `quickice/gui/viewmodel.py` (add signals + thread management)

**New CLI Option:**
- Argument definition: `quickice/cli/parser.py` (add to `create_parser()`)
- Conditional validation: `quickice/cli/parser.py` (`validate_interface_args()`)
- Pipeline integration: `quickice/main.py` (use new argument in pipeline)
- Tests: `tests/test_cli_integration.py`

**New Utility/Helper:**
- Domain utilities: Appropriate domain package (e.g., `quickice/structure_generation/` for structure helpers)
- GUI utilities: `quickice/gui/vtk_utils.py` (VTK conversion helpers)
- Shared types: Domain-specific `types.py` files (e.g., `quickice/structure_generation/types.py`)
- Do NOT create a shared `quickice/utils.py` — keep utilities co-located with their domain

## Special Directories

**`quickice/phase_mapping/data/`:**
- Purpose: Legacy polygon-based phase boundary data (Simon-Glatzel approximations)
- Generated: No (manually curated)
- Committed: Yes
- Note: NOT used by current lookup algorithm — curve-based functions in `lookup.py` and `melting_curves.py` are the single source of truth. Kept for reference/backup only.

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

**`output/`:**
- Purpose: Default output directory for CLI-generated files (PDB, GRO, TOP, diagrams)
- Generated: Yes (by CLI runs)
- Committed: No (in `.gitignore`)

---

*Structure analysis: 2026-04-13*
