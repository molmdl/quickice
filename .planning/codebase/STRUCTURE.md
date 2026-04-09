# Codebase Structure

**Analysis Date:** 2026-04-10

## Directory Layout

```
quickice/                          # Project root
├── quickice.py                    # CLI entry point script
├── quickice/                      # Main Python package
│   ├── __init__.py                # Package init, version="3.0.0"
│   ├── main.py                    # CLI pipeline orchestrator
│   ├── cli/                       # CLI argument parsing
│   ├── data/                      # Bundled data files
│   ├── gui/                       # GUI application (PySide6 + VTK)
│   ├── output/                    # File output and diagram generation
│   ├── phase_mapping/             # Ice phase identification
│   ├── ranking/                   # Candidate scoring and ranking
│   ├── structure_generation/      # Ice structure generation (GenIce2)
│   └── validation/               # Input validation (CLI)
├── tests/                         # Test suite
├── docs/                          # Documentation and images
├── scripts/                       # Build/packaging scripts
├── sample_output/                 # Example output files
├── build/                         # PyInstaller build artifacts
├── dist/                          # PyInstaller distribution
├── .planning/                     # GSD planning artifacts
├── .github/workflows/             # CI/CD
├── environment.yml                # Conda environment (dev)
├── environment-build.yml          # Conda environment (build)
├── requirements-dev.txt           # Dev pip dependencies
├── quickice-gui.spec              # PyInstaller spec
└── setup.sh                       # Environment setup script
```

## Directory Purposes

**`quickice/` (main package):**
- Purpose: Core application logic, both CLI and GUI
- Contains: All Python modules for the application
- Key files: `__init__.py` (version), `main.py` (pipeline)

**`quickice/cli/`:**
- Purpose: CLI argument parsing
- Contains: argparse configuration, validation type converters
- Key files: `parser.py` (argument parser), `__init__.py`

**`quickice/data/`:**
- Purpose: Bundled molecular data files
- Contains: GROMACS water model files
- Key files: `tip4p-ice.itp` (TIP4P-ICE topology), `tip4p.gro` (water template)

**`quickice/gui/`:**
- Purpose: Graphical user interface
- Contains: PySide6 widgets, VTK 3D viewers, ViewModel, workers, exporters
- Key files: `main_window.py` (window assembly), `viewmodel.py` (MVVM bridge), `workers.py` (background threads), `view.py` (UI panels), `interface_panel.py` (Tab 2), `molecular_viewer.py` (3D viewer), `dual_viewer.py` (side-by-side), `phase_diagram_widget.py` (interactive diagram), `interface_viewer.py` (Tab 2 3D viewer), `export.py` (file export handlers), `vtk_utils.py` (VTK conversion), `validators.py` (GUI validation), `help_dialog.py` (help dialog)

**`quickice/output/`:**
- Purpose: File output, structure validation, diagram generation
- Contains: PDB/GROMACS writers, spglib validator, phase diagram generator, orchestrator
- Key files: `orchestrator.py` (output coordination), `pdb_writer.py` (PDB format), `gromacs_writer.py` (GRO/TOP/ITP), `validator.py` (space group + overlap), `phase_diagram.py` (matplotlib diagram), `types.py` (OutputResult)

**`quickice/phase_mapping/`:**
- Purpose: Ice phase identification from T,P conditions
- Contains: Curve-based boundary evaluation, IAPWS equations, triple point data
- Key files: `lookup.py` (main `lookup_phase()` function, `IcePhaseLookup` class), `melting_curves.py` (IAPWS R14-08 equations), `solid_boundaries.py` (linear interpolation), `triple_points.py` (triple point coordinates), `errors.py` (exception hierarchy), `data/` (legacy polygon data)

**`quickice/ranking/`:**
- Purpose: Score and rank ice structure candidates
- Contains: Multi-metric scoring with min-max normalization
- Key files: `scorer.py` (energy/density/diversity scoring, `rank_candidates()`), `types.py` (RankedCandidate, RankingResult, ScoringConfig)

**`quickice/structure_generation/`:**
- Purpose: Generate ice crystal structures using GenIce2
- Contains: GenIce2 wrapper, phase mapping, interface modes, water filling
- Key files: `generator.py` (IceStructureGenerator, `generate_candidates()`), `mapper.py` (phase-to-GenIce mapping, supercell calculation), `types.py` (Candidate, GenerationResult, InterfaceConfig, InterfaceStructure), `errors.py` (exception hierarchy), `interface_builder.py` (interface orchestrator with validation), `water_filler.py` (TIP4P water template loading and tiling), `overlap_resolver.py` (PBC-aware overlap detection and molecule removal), `modes/slab.py` (slab interface), `modes/pocket.py` (pocket interface), `modes/piece.py` (piece interface)

**`quickice/validation/`:**
- Purpose: CLI input validation
- Contains: Type converter functions for argparse
- Key files: `validators.py` (validate_temperature, validate_pressure, validate_nmolecules)

**`tests/`:**
- Purpose: Test suite
- Contains: Unit and integration tests
- Key files: `test_phase_mapping.py`, `test_structure_generation.py`, `test_ranking.py`, `test_validators.py`, `test_cli_integration.py`, `test_pbc_hbonds.py`, `test_atom_ordering_validation.py`, `test_interface_ordering_validation.py`, `test_med03_minimum_box_size.py`, `test_piece_mode_validation.py`, `test_output/`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry point (imports `quickice.main.main`)
- `quickice/main.py`: CLI pipeline orchestrator (full pipeline: parse → lookup → generate → rank → output)
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/gui/main_window.py`: MainWindow class and `run_app()` function

**Configuration:**
- `environment.yml`: Conda environment specification (dev dependencies)
- `environment-build.yml`: Conda environment for PyInstaller builds
- `requirements-dev.txt`: Dev pip dependencies (pytest, pyinstaller)
- `quickice-gui.spec`: PyInstaller build specification
- `setup.sh`: Environment setup script

**Core Logic (Pipeline):**
- `quickice/phase_mapping/lookup.py`: Phase identification (`lookup_phase()`, `PHASE_METADATA`)
- `quickice/phase_mapping/melting_curves.py`: IAPWS R14-08 melting curve equations
- `quickice/phase_mapping/solid_boundaries.py`: Solid-solid boundary interpolation
- `quickice/structure_generation/generator.py`: GenIce2 wrapper (`IceStructureGenerator`, `generate_candidates()`)
- `quickice/structure_generation/mapper.py`: Phase ID → GenIce lattice mapping, supercell calculation
- `quickice/structure_generation/interface_builder.py`: Interface generation orchestrator
- `quickice/ranking/scorer.py`: Multi-metric scoring (`rank_candidates()`)

**Type Definitions:**
- `quickice/structure_generation/types.py`: Candidate, GenerationResult, InterfaceConfig, InterfaceStructure
- `quickice/ranking/types.py`: RankedCandidate, RankingResult, ScoringConfig
- `quickice/output/types.py`: OutputResult
- `quickice/phase_mapping/errors.py`: PhaseMappingError, UnknownPhaseError
- `quickice/structure_generation/errors.py`: StructureGenerationError, UnsupportedPhaseError, InterfaceGenerationError

**Data Files:**
- `quickice/data/tip4p-ice.itp`: GROMACS TIP4P-ICE topology file
- `quickice/data/tip4p.gro`: TIP4P water template (864 molecules, equilibrated)
- `quickice/phase_mapping/data/ice_phases.json`: Legacy phase polygon data (not used by curve-based lookup)
- `quickice/phase_mapping/data/ice_boundaries.py`: Legacy boundary data (not used by curve-based lookup)
- `quickice/phase_mapping/triple_points.py`: Triple point coordinates (used by curve-based lookup)

**Testing:**
- `tests/test_phase_mapping.py`: Phase mapping tests
- `tests/test_structure_generation.py`: Structure generation tests
- `tests/test_ranking.py`: Ranking tests
- `tests/test_validators.py`: Validation tests
- `tests/test_cli_integration.py`: CLI integration tests
- `tests/test_output/`: Output-related test artifacts

**Build/Packaging:**
- `scripts/`: Build scripts
- `build/`: PyInstaller build output
- `dist/`: PyInstaller distribution output
- `quickice-gui.spec`: PyInstaller specification

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `melting_curves.py`, `pdb_writer.py`, `interface_builder.py`)
- Test files: `test_` prefix + `snake_case.py` (e.g., `test_phase_mapping.py`, `test_ranking.py`)
- Data files: lowercase with hyphens/extensions (e.g., `tip4p-ice.itp`, `tip4p.gro`)
- GUI widget files: descriptive `snake_case.py` matching class purpose (e.g., `main_window.py` → `MainWindow`, `dual_viewer.py` → `DualViewerWidget`)

**Directories:**
- Python packages: `snake_case/` (e.g., `phase_mapping/`, `structure_generation/`)
- Sub-packages use nested `snake_case/` (e.g., `structure_generation/modes/`)
- Data directories: `data/` within relevant package (e.g., `quickice/data/`, `quickice/phase_mapping/data/`)
- Test directory: `tests/` at project root

**Classes:**
- Data types: `PascalCase` dataclasses (e.g., `Candidate`, `GenerationResult`, `RankedCandidate`, `InterfaceConfig`, `InterfaceStructure`, `OutputResult`, `ScoringConfig`, `RankingResult`)
- Exceptions: `PascalCase` with `Error` suffix (e.g., `PhaseMappingError`, `UnknownPhaseError`, `StructureGenerationError`, `InterfaceGenerationError`)
- GUI widgets: `PascalCase` with descriptive suffix (e.g., `MainWindow`, `InputPanel`, `ProgressPanel`, `ViewerPanel`, `DualViewerWidget`, `MolecularViewerWidget`, `InterfaceViewerWidget`, `PhaseDiagramPanel`, `QuickReferenceDialog`)
- Workers: `PascalCase` with `Worker` suffix (e.g., `GenerationWorker`, `InterfaceGenerationWorker`)
- Exporters: `PascalCase` with `Exporter` suffix (e.g., `PDBExporter`, `DiagramExporter`, `ViewportExporter`, `GROMACSExporter`)

**Functions:**
- Public API: `snake_case` (e.g., `lookup_phase()`, `generate_candidates()`, `rank_candidates()`, `output_ranked_candidates()`, `generate_interface()`, `validate_interface_config()`)
- Private helpers: `_snake_case` prefix (e.g., `_build_result()`, `_calculate_oo_distances_pbc()`, `_linear_interpolate()`, `_parse_gro()`)
- Type converters (CLI): `validate_snake_case` (e.g., `validate_temperature`, `validate_pressure`, `validate_nmolecules`)
- GUI validators return tuples: `(bool, str)` pattern in `quickice/gui/validators.py`

**Constants:**
- `UPPER_SNAKE_CASE` for module-level constants (e.g., `PHASE_TO_GENICE`, `UNIT_CELL_MOLECULES`, `TRIPLE_POINTS`, `PHASE_COLORS`, `PHASE_LABELS`, `ATOMS_PER_WATER_MOLECULE`, `TIP4P_ICE_ALPHA`, `MINIMUM_BOX_DIMENSION`, `VII_VIII_ORDERING_TEMP`)

## Where to Add New Code

**New Ice Phase:**
- Phase mapping: Add entry to `PHASE_METADATA` in `quickice/phase_mapping/lookup.py`, add boundary curve in `quickice/phase_mapping/solid_boundaries.py`, add triple points in `quickice/phase_mapping/triple_points.py`, add detection logic in `lookup_phase()`
- Structure generation: Add mapping in `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES` in `quickice/structure_generation/mapper.py`
- Phase diagram: Add polygon builder in `quickice/output/phase_diagram.py`, add to `PHASE_COLORS` and `PHASE_LABELS`, add to `phases_to_plot` list
- GUI diagram: Add detection in `PhaseDetector` in `quickice/gui/phase_diagram_widget.py`
- Tests: Add phase mapping tests in `tests/test_phase_mapping.py`

**New Interface Mode:**
- Create mode module: `quickice/structure_generation/modes/<mode_name>.py` with `assemble_<mode>()` function
- Add routing: In `quickice/structure_generation/interface_builder.py` → `generate_interface()` function
- Add validation: In `validate_interface_config()` in same file
- Add UI: In `quickice/gui/interface_panel.py` → new mode in `QStackedWidget`
- Tests: Add `test_<mode_name>_validation.py` in `tests/`

**New Export Format:**
- Create writer: `quickice/output/<format>_writer.py`
- Add orchestrator call: In `quickice/output/orchestrator.py` or `quickice/main.py`
- Add GUI exporter: In `quickice/gui/export.py` → new exporter class
- Add menu action: In `quickice/gui/main_window.py` → `_create_menu_bar()`
- Add worker export: In `quickice/gui/workers.py` if background processing needed

**New Scoring Metric:**
- Add score function: In `quickice/ranking/scorer.py`
- Add weight: In `rank_candidates()` weight dict
- Add field: In `quickice/ranking/types.py` → `RankedCandidate` dataclass
- Update display: In `quickice/main.py` ranking table output and `quickice/gui/main_window.py` log output

**New GUI Widget:**
- Create widget: `quickice/gui/<widget_name>.py`
- Import in: `quickice/gui/__init__.py` if public
- Assemble in: `quickice/gui/main_window.py` → `_setup_ui()` or `_setup_connections()`
- Connect signals: In `MainWindow._setup_connections()`

**Utilities:**
- Shared helpers: `quickice/gui/vtk_utils.py` (VTK conversion), `quickice/structure_generation/overlap_resolver.py` (PBC overlap), `quickice/structure_generation/water_filler.py` (water template)

## Special Directories

**`quickice/data/`:**
- Purpose: Bundled molecular data files used at runtime
- Generated: No (manually maintained)
- Committed: Yes
- Used by: `quickice/structure_generation/water_filler.py` (tip4p.gro), `quickice/output/gromacs_writer.py` (tip4p-ice.itp via `get_tip4p_itp_path()`)

**`quickice/phase_mapping/data/`:**
- Purpose: Legacy polygon-based phase boundary data (pre-curve-based)
- Generated: No
- Committed: Yes
- Used by: NOT used by current curve-based lookup (kept for backward compatibility); `ice_phases.json` and `ice_boundaries.py` are legacy artifacts

**`build/` and `dist/`:**
- Purpose: PyInstaller build artifacts and distribution output
- Generated: Yes (by PyInstaller)
- Committed: Yes (currently in repo)
- Used by: Binary distribution

**`sample_output/`:**
- Purpose: Example output files for documentation
- Generated: Yes (by running QuickIce)
- Committed: Yes
- Used by: README documentation

**`.planning/`:**
- Purpose: GSD planning artifacts (phases, milestones, codebase analysis)
- Generated: Yes (by GSD commands)
- Committed: Yes
- Used by: GSD orchestrator

**`tests/test_output/`:**
- Purpose: Test output artifacts
- Generated: Yes (by test runs)
- Committed: Partially (some test data)
- Used by: Test suite

---

*Structure analysis: 2026-04-10*
