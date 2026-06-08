# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```
quickice/                          # Project root
├── quickice/                      # Main Python package
│   ├── __init__.py                # Version (4.5.0)
│   ├── main.py                    # CLI entry point orchestration
│   ├── gui/                       # PySide6 GUI application
│   ├── cli/                       # CLI argument parser
│   ├── structure_generation/      # Core: ice/hydrate/interface/ion/solute/custom generation
│   ├── phase_mapping/             # Ice phase identification from T,P
│   ├── ranking/                   # Candidate scoring and ranking
│   ├── output/                    # PDB/GRO/TOP export and validation
│   ├── validation/                # Input validators (shared CLI/GUI)
│   ├── utils/                     # Shared utilities
│   └── data/                      # Bundled forcefield files (.itp, .gro)
├── tests/                         # Test suite
│   ├── test_output/               # Output-specific tests
│   ├── conftest.py                # Shared fixtures
│   └── test_*.py                  # Unit/integration/e2e tests
├── scripts/                       # Build and utility scripts
├── docs/                          # Documentation
├── sample_output/                 # Reference GROMACS output files
├── licenses/                      # Third-party license files
├── build/                         # PyInstaller build artifacts
├── dist/                          # PyInstaller built executables
├── quickice.py                    # CLI script entry point
├── environment.yml                # Conda environment specification
├── requirements-dev.txt           # Dev dependencies
└── setup.sh                       # Environment activation script
```

## Directory Purposes

**`quickice/structure_generation/`:**
- Purpose: Core scientific computing — all molecular structure generation logic
- Contains: Generator classes, inserter classes, mode implementations, type definitions, parsers
- Key files: `types.py` (all dataclasses), `generator.py` (ice), `hydrate_generator.py` (hydrate), `interface_builder.py` (interface orchestrator), `solute_inserter.py`, `ion_inserter.py`, `custom_molecule_inserter.py`, `moleculetype_registry.py`

**`quickice/structure_generation/modes/`:**
- Purpose: Interface geometry implementations (strategy pattern)
- Contains: `slab.py` (ice-water-ice sandwich), `pocket.py` (water cavity in ice), `piece.py` (ice in water box)
- Key files: Each mode has `assemble_*()` function called by `interface_builder.py`

**`quickice/phase_mapping/`:**
- Purpose: Ice phase identification using IAPWS R14-08 melting curves
- Contains: Curve evaluation functions, triple point data, boundary calculations
- Key files: `lookup.py` (lookup_phase function), `melting_curves.py` (IAPWS equations), `solid_boundaries.py` (solid-solid boundaries), `ice_ih_density.py` (temperature-dependent density), `data/ice_boundaries.py` (numerical boundary data)

**`quickice/ranking/`:**
- Purpose: Score and rank ice structure candidates
- Contains: Scoring functions, type definitions
- Key files: `scorer.py` (energy_score, density_score, diversity_score, rank_candidates), `types.py` (RankedCandidate, RankingResult, ScoringConfig)

**`quickice/output/`:**
- Purpose: Export structures to PDB, GRO, TOP formats; generate phase diagrams
- Contains: File writers, validator, orchestrator, diagram generator
- Key files: `gromacs_writer.py` (GRO/TOP file writers with TIP4P MW computation), `pdb_writer.py`, `validator.py` (space group, overlap checks), `orchestrator.py` (output_ranked_candidates), `phase_diagram.py`

**`quickice/gui/`:**
- Purpose: PySide6 GUI with 6-tab workflow
- Contains: Main window, panels, viewers, workers, renderers, export handlers
- Key files: See "Key File Locations" below

**`quickice/gui/viewmodel.py`:**
- Purpose: MVVM ViewModel — bridges View and Model, manages worker threads
- Contains: `MainViewModel` class with Qt Signals

**`quickice/validation/`:**
- Purpose: Shared input validators for CLI and GUI
- Contains: `validators.py` with validate_temperature, validate_pressure, validate_nmolecules, validate_positive_float, validate_box_dimension

**`quickice/data/`:**
- Purpose: Bundled GROMACS forcefield files and molecular templates
- Contains: `.itp` files (tip4p-ice, ch4, thf, ch4_hydrate, thf_hydrate, ch4_liquid, thf_liquid), `.gro` template (tip4p.gro), `custom/` subfolder with example molecules
- Generated: No
- Committed: Yes

**`tests/`:**
- Purpose: Full test suite — unit, integration, and end-to-end
- Contains: 40+ test files covering every subsystem
- Key files: `conftest.py` (shared fixtures), `test_e2e_*.py` (workflow chain tests), `test_output/` (export-specific tests)

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI script entry point
- `quickice/main.py`: CLI orchestration logic
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/gui/main_window.py`: MainWindow class, run_app() function

**Configuration:**
- `environment.yml`: Conda environment with all dependencies
- `setup.sh`: Environment activation (PYTHONPATH setup)
- `quickice-gui.spec`: PyInstaller build specification

**Core Logic (Model Layer):**
- `quickice/structure_generation/types.py`: ALL domain dataclasses (Candidate, InterfaceConfig, InterfaceStructure, HydrateConfig, HydrateStructure, IonConfig, IonStructure, SoluteConfig, SoluteStructure, CustomMoleculeConfig, CustomMoleculeStructure, MoleculeIndex, PlacementValidationResult, HydrateLatticeInfo)
- `quickice/structure_generation/generator.py`: IceStructureGenerator (GenIce2 wrapper)
- `quickice/structure_generation/hydrate_generator.py`: HydrateStructureGenerator (GenIce2 hydrate API)
- `quickice/structure_generation/interface_builder.py`: generate_interface(), validate_interface_config()
- `quickice/structure_generation/modes/slab.py`: assemble_slab() — slab interface mode
- `quickice/structure_generation/modes/pocket.py`: assemble_pocket() — pocket interface mode
- `quickice/structure_generation/modes/piece.py`: assemble_piece() — piece interface mode
- `quickice/structure_generation/solute_inserter.py`: SoluteInserter — concentration-based CH4/THF placement
- `quickice/structure_generation/ion_inserter.py`: IonInserter — concentration-based NaCl placement
- `quickice/structure_generation/custom_molecule_inserter.py`: CustomMoleculeInserter — user-provided molecule placement
- `quickice/structure_generation/water_filler.py`: Water template loading and region filling
- `quickice/structure_generation/overlap_resolver.py`: Overlap detection and removal
- `quickice/structure_generation/gro_parser.py`: GRO format parser
- `quickice/structure_generation/itp_parser.py`: ITP format parser
- `quickice/structure_generation/molecule_validator.py`: Molecule validation
- `quickice/structure_generation/moleculetype_registry.py`: GROMACS moleculetype naming registry
- `quickice/structure_generation/mapper.py`: Phase-to-GenIce lattice name mapping, supercell calculation
- `quickice/structure_generation/errors.py`: Domain exception types
- `quickice/structure_generation/cell_utils.py`: Cell orthogonality check
- `quickice/structure_generation/gromacs_ion_export.py`: Ion ITP generation

**Phase Mapping:**
- `quickice/phase_mapping/lookup.py`: lookup_phase() — curve-based phase identification
- `quickice/phase_mapping/melting_curves.py`: IAPWS R14-08 melting pressure equations
- `quickice/phase_mapping/solid_boundaries.py`: Solid-solid boundary functions
- `quickice/phase_mapping/triple_points.py`: Triple point data
- `quickice/phase_mapping/ice_ih_density.py`: Temperature-dependent Ice Ih density (IAPWS R10-06)
- `quickice/phase_mapping/water_density.py`: Liquid water density calculation

**Ranking:**
- `quickice/ranking/scorer.py`: energy_score(), density_score(), diversity_score(), rank_candidates()
- `quickice/ranking/types.py`: RankedCandidate, RankingResult, ScoringConfig

**Output:**
- `quickice/output/gromacs_writer.py`: GRO/TOP file writers, TIP4P MW position computation
- `quickice/output/pdb_writer.py`: PDB file writer with CRYST1 records
- `quickice/output/validator.py`: Space group and atomic overlap validation
- `quickice/output/orchestrator.py`: output_ranked_candidates() coordinator
- `quickice/output/phase_diagram.py`: Phase diagram generation (matplotlib)

**GUI (View Layer):**
- `quickice/gui/main_window.py`: MainWindow — assembles all tabs, handles cross-tab data flow
- `quickice/gui/view.py`: InputPanel, ProgressPanel, ViewerPanel, InfoPanel
- `quickice/gui/viewmodel.py`: MainViewModel — worker thread orchestration
- `quickice/gui/workers.py`: GenerationWorker, InterfaceGenerationWorker
- `quickice/gui/hydrate_worker.py`: HydrateWorker (QThread subclass)
- `quickice/gui/custom_molecule_worker.py`: CustomMoleculeWorker
- `quickice/gui/constants.py`: TabIndex enum (tab position constants)
- `quickice/gui/export.py`: PDBExporter, GROMACSExporter, InterfaceGROMACSExporter, IonGROMACSExporter, SoluteGROMACSExporter, CustomMoleculeGROMACSExporter, etc.
- `quickice/gui/hydrate_export.py`: HydrateGROMACSExporter
- `quickice/gui/validators.py`: GUI-specific validator wrappers
- `quickice/gui/help_dialog.py`: Quick reference help dialog
- `quickice/gui/phase_diagram_widget.py`: Interactive phase diagram panel
- `quickice/gui/interface_panel.py`: Interface Construction tab panel
- `quickice/gui/hydrate_panel.py`: Hydrate Generation tab panel
- `quickice/gui/custom_molecule_panel.py`: Custom Molecule tab panel
- `quickice/gui/solute_panel.py`: Solute Insertion tab panel
- `quickice/gui/ion_panel.py`: Ion Insertion tab panel

**VTK 3D Visualization:**
- `quickice/gui/molecular_viewer.py`: Base VTK molecular viewer
- `quickice/gui/dual_viewer.py`: Side-by-side dual VTK viewer
- `quickice/gui/vtk_utils.py`: VTK utility functions
- `quickice/gui/interface_viewer.py`: Interface 3D viewer
- `quickice/gui/hydrate_viewer.py`: Hydrate 3D viewer
- `quickice/gui/custom_molecule_viewer.py`: Custom molecule 3D viewer
- `quickice/gui/solute_viewer.py`: Solute 3D viewer
- `quickice/gui/ion_viewer.py`: Ion 3D viewer
- `quickice/gui/hydrate_renderer.py`: Hydrate-specific VTK rendering
- `quickice/gui/custom_molecule_renderer.py`: Custom molecule VTK rendering
- `quickice/gui/solute_renderer.py`: Solute VTK rendering
- `quickice/gui/ion_renderer.py`: Ion VTK rendering (Na/Cl sphere actors)

**Validation (Shared):**
- `quickice/validation/validators.py`: Input validators (CLI and GUI)
- `quickice/gui/validators.py`: GUI-specific validator wrappers

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures
- `tests/test_e2e_*.py`: End-to-end workflow tests
- `tests/test_output/`: GROMACS export validation tests
- `tests/test_pocket_*.py`: Pocket mode tests
- `tests/test_custom_molecule*.py`: Custom molecule tests
- `tests/test_solute_*.py`: Solute insertion tests
- `tests/test_ion_*.py`: Ion insertion tests
- `tests/test_ranking.py`: Ranking tests
- `tests/test_phase_mapping.py`: Phase mapping tests
- `tests/test_structure_generation.py`: Ice generation tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `interface_builder.py`, `solute_inserter.py`)
- GUI panels: `{subsystem}_panel.py` (e.g., `hydrate_panel.py`, `ion_panel.py`)
- GUI viewers: `{subsystem}_viewer.py` (e.g., `hydrate_viewer.py`, `ion_viewer.py`)
- GUI renderers: `{subsystem}_renderer.py` (e.g., `hydrate_renderer.py`, `ion_renderer.py`)
- Workers: `{subsystem}_worker.py` (e.g., `hydrate_worker.py`, `custom_molecule_worker.py`)
- Test files: `test_{feature}.py` or `test_e2e_{workflow}.py`
- E2E tests: `test_e2e_{workflow}.py` (e.g., `test_e2e_ice_generation.py`, `test_e2e_workflow_chains.py`)
- Data files: `{molecule}.itp`, `{molecule}.gro` (GROMACS convention)

**Directories:**
- Python packages: `snake_case/` (e.g., `structure_generation/`, `phase_mapping/`)
- GUI subpackage: `gui/` with sub-components following `{subsystem}_{role}.py` pattern
- Test directories: `tests/` (flat) with `test_output/` subdirectory
- Data: `data/` with `custom/` subdirectory for example molecules

## Where to Add New Code

**New Interface Mode (e.g., cylinder):**
- Mode implementation: `quickice/structure_generation/modes/cylinder.py` — implement `assemble_cylinder(candidate, config) -> InterfaceStructure`
- Register in `quickice/structure_generation/modes/__init__.py` — add import and __all__ entry
- Add routing in `quickice/structure_generation/interface_builder.py` — add elif branch in `generate_interface()`
- Add validation in `quickice/structure_generation/interface_builder.py` — add mode-specific checks in `validate_interface_config()`
- Add config field in `quickice/structure_generation/types.py` — add to InterfaceConfig dataclass
- Add GUI controls: `quickice/gui/interface_panel.py` — add mode-specific input widgets
- Add tests: `tests/test_cylinder_mode.py`

**New Solute Type (e.g., CO2):**
- Template in `quickice/structure_generation/solute_inserter.py` — add `_generate_co2_coordinates()` method
- Register in `quickice/structure_generation/types.py` — add to GUEST_MOLECULES dict
- ITP file: `quickice/data/co2.itp` and `quickice/data/co2_liquid.itp`
- MoleculetypeRegistry: Add CO2_H and CO2_L to RESERVED_NAMES in `quickice/structure_generation/moleculetype_registry.py`
- Update SoluteConfig validation in `quickice/structure_generation/types.py`
- Add tests: `tests/test_co2_solute.py`

**New Tab (e.g., Membrane):**
- Panel: `quickice/gui/membrane_panel.py` — QWidget subclass with configuration inputs and VTK viewer
- Worker: `quickice/gui/membrane_worker.py` — QThread-based worker (if computation is heavy)
- Viewer: `quickice/gui/membrane_viewer.py` — VTK 3D viewer
- Renderer: `quickice/gui/membrane_renderer.py` — VTK actor creation
- Exporter: Add to `quickice/gui/export.py` — GROMACS exporter class
- TabIndex: Add to `quickice/gui/constants.py` — new enum value
- MainWindow: Add tab to `quickice/gui/main_window.py` — `tab_widget.addTab()`, signal connections, cross-tab data flow
- Type: Add dataclass to `quickice/structure_generation/types.py` if new structure type

**New GROMACS Export:**
- Add exporter class in `quickice/gui/export.py` (follow existing pattern: SoluteGROMACSExporter, IonGROMACSExporter)
- Add GRO/TOP writer in `quickice/output/gromacs_writer.py` if new file format needed
- Add menu action in `quickice/gui/main_window.py` `_create_menu_bar()`
- Add test in `tests/test_output/`

**Utilities:**
- Shared helpers: `quickice/utils/` (currently `molecule_utils.py`)
- Validators: `quickice/validation/validators.py` (CLI), `quickice/gui/validators.py` (GUI)

## Special Directories

**`quickice/data/`:**
- Purpose: Bundled GROMACS forcefield files (.itp) and molecular templates (.gro)
- Generated: No
- Committed: Yes
- Contains: tip4p-ice.itp, tip4p.gro, ch4.itp, thf.itp, ch4_hydrate.itp, thf_hydrate.itp, ch4_liquid.itp, thf_liquid.itp, custom/ (example molecules etoh.gro/itp/top/chg)

**`sample_output/`:**
- Purpose: Reference GROMACS output files for validation and user reference
- Generated: Yes (by running the application)
- Committed: Yes (serves as reference)

**`build/` and `dist/`:**
- Purpose: PyInstaller build artifacts and compiled executables
- Generated: Yes (by `scripts/build-linux.sh`)
- Committed: Partially (build metadata tracked, large binaries excluded)

**`.planning/`:**
- Purpose: GSD planning documents (codebase analysis, phase plans)
- Generated: By GSD commands
- Committed: Yes

**`output/` and `tmp/`:**
- Purpose: Runtime output and temporary files (gitignored)
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-06-08*
