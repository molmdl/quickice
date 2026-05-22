# Codebase Structure

**Analysis Date:** 2026-05-22

## Directory Layout

```
quickice/                          # Project root
├── quickice.py                    # CLI entry point script
├── quickice-gui.spec              # PyInstaller spec for GUI bundling
├── requirements-dev.txt           # Dev dependencies (pytest, pyinstaller)
├── environment.yml                # Conda environment specification
├── environment-build.yml          # Build environment specification
├── setup.sh                       # Setup script
├── README.md                      # Main documentation
├── README_bin.md                  # Binary distribution docs
├── LICENSE                        # License file
├── licenses/                      # Third-party license files
├── docs/                          # Documentation assets (images)
├── scripts/                       # Build/run helper scripts
├── sample_output/                 # Reference output files for validation
├── quickice/                      # Main Python package (81 .py files, ~30,500 lines)
│   ├── __init__.py                # Package version (4.5.0)
│   ├── main.py                    # CLI pipeline orchestrator
│   ├── cli/                       # CLI argument parsing
│   ├── gui/                       # GUI application (PySide6 + VTK)
│   ├── structure_generation/      # Core structure generation logic
│   ├── phase_mapping/             # Ice phase identification + density
│   ├── ranking/                   # Candidate ranking/scoring
│   ├── output/                    # File writers and validation
│   ├── data/                      # Bundled molecular data files
│   ├── validation/                # Shared input validators
│   └── utils/                     # Utility functions
├── tests/                         # Test suite
│   ├── test_output/               # E2E export tests (conftest + 8 export test files)
│   └── [30+ test_*.py files]      # Unit/integration tests
├── tmp/                           # Temporary debug/test output (not committed)
├── output/                        # Runtime output directory
├── build/                         # PyInstaller build artifacts
├── dist/                          # PyInstaller distribution bundle
└── .planning/                     # Project planning documents
```

## Directory Purposes

**`quickice/cli/`:**
- Purpose: Command-line interface argument parsing and validation
- Contains: `parser.py` (argparse setup), `__init__.py`
- Key files: `quickice/cli/parser.py`

**`quickice/gui/`:**
- Purpose: PySide6 desktop GUI with VTK 3D molecular visualization
- Contains: Main window, tab panels, viewers, renderers, exporters, workers, validators, constants
- Key files: `quickice/gui/main_window.py` (2024 lines), `quickice/gui/export.py` (929 lines), `quickice/gui/interface_panel.py` (935 lines)

**`quickice/structure_generation/`:**
- Purpose: Core physics-based ice/hydrate/interface/solute/ion/custom molecule generation
- Contains: Generators, inserters, interface modes, overlap resolver, ITP/GRO parsers, moleculetype registry
- Key files: `quickice/structure_generation/types.py` (718 lines), `quickice/structure_generation/solute_inserter.py` (888 lines), `quickice/structure_generation/custom_molecule_inserter.py` (886 lines)

**`quickice/structure_generation/modes/`:**
- Purpose: Interface geometry mode implementations (strategy pattern)
- Contains: `slab.py`, `pocket.py`, `piece.py`, `__init__.py`
- Key files: `quickice/structure_generation/modes/slab.py` (641 lines), `quickice/structure_generation/modes/pocket.py` (598 lines)

**`quickice/phase_mapping/`:**
- Purpose: Ice phase identification from T,P using IAPWS melting curves
- Contains: Lookup, melting curves, solid boundaries, triple points, density calculators
- Key files: `quickice/phase_mapping/lookup.py`, `quickice/phase_mapping/water_density.py`, `quickice/phase_mapping/ice_ih_density.py`

**`quickice/ranking/`:**
- Purpose: Ice structure candidate scoring and ranking
- Contains: Scoring functions (energy, density, diversity), types
- Key files: `quickice/ranking/scorer.py`, `quickice/ranking/types.py`

**`quickice/output/`:**
- Purpose: GROMACS/PDB file writers, structure validation, phase diagram generation
- Contains: GROMACS writer (largest file at 2559 lines), PDB writer, validator, phase diagram, orchestrator
- Key files: `quickice/output/gromacs_writer.py` (2559 lines)

**`quickice/data/`:**
- Purpose: Bundled molecular topology and coordinate files for GROMACS
- Contains: TIP4P-ICE ITP, CH4/THF ITP files (hydrate + liquid variants), TIP4P GRO template, custom molecule examples
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/ch4.itp`, `quickice/data/thf.itp`, `quickice/data/ch4_hydrate.itp`, `quickice/data/thf_hydrate.itp`

**`quickice/data/custom/`:**
- Purpose: Example custom molecule files (ethanol demo)
- Contains: `etoh.gro`, `etoh.itp`, `etoh.top`, `etoh.chg`
- Key files: `quickice/data/custom/etoh.itp`

**`quickice/validation/`:**
- Purpose: Shared input validators (CLI-oriented, raise exceptions)
- Contains: `validators.py` only
- Key files: `quickice/validation/validators.py`

**`quickice/utils/`:**
- Purpose: Shared utility functions
- Contains: `molecule_utils.py` (guest atom counting helper)
- Key files: `quickice/utils/molecule_utils.py`

**`tests/`:**
- Purpose: Unit and integration test suite
- Contains: 30+ test files covering phase mapping, structure generation, ranking, CLI, validators, custom molecules, solutes, ions, pockets, GROMACS export
- Key files: All `tests/test_*.py` files

**`tests/test_output/`:**
- Purpose: E2E GROMACS export test suite (Batch 5-6 additions)
- Contains: `conftest.py` (shared fixtures), 8 exporter test files, 3 other test files
- Key files: `tests/test_output/conftest.py` (499 lines of fixtures)

**`scripts/`:**
- Purpose: Build, run, and distribution helper scripts
- Contains: `assemble-dist.sh`, `build-linux.sh`, `run_gui_ssh.sh`, `run_oc.sh`

**`sample_output/`:**
- Purpose: Reference output files for manual validation and regression checking
- Contains: CLI and GUI output samples for ice, interface, and hydrate structures

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI entry point (imports from `quickice.main`)
- `quickice/gui/__main__.py`: GUI entry point (`python -m quickice.gui`)
- `quickice/main.py`: CLI pipeline orchestrator (phase lookup → generation → ranking → output)

**Configuration:**
- `quickice-gui.spec`: PyInstaller bundle specification
- `environment.yml`: Conda environment (Python 3.14)
- `requirements-dev.txt`: pytest, pyinstaller
- `quickice/phase_mapping/data/ice_phases.json`: Ice phase boundary data
- `quickice/phase_mapping/data/ice_boundaries.py`: Programmatic boundary data

**Core Logic:**
- `quickice/structure_generation/types.py`: All dataclass type definitions (718 lines — the single source of truth for data contracts)
- `quickice/structure_generation/generator.py`: `IceStructureGenerator` wrapping GenIce2 API
- `quickice/structure_generation/hydrate_generator.py`: `HydrateStructureGenerator` for sI/sII/sH hydrates
- `quickice/structure_generation/interface_builder.py`: Mode routing + validation for interface generation
- `quickice/structure_generation/modes/slab.py`: Slab (ice-water-ice sandwich) mode
- `quickice/structure_generation/modes/pocket.py`: Pocket (cavity in ice) mode — cubic/sphere branching, 6 invariant assertions
- `quickice/structure_generation/modes/piece.py`: Piece (ice in water box) mode
- `quickice/structure_generation/ion_inserter.py`: NaCl ion insertion with concentration/volume
- `quickice/structure_generation/solute_inserter.py`: CH4/THF solute insertion with all-atom overlap checking
- `quickice/structure_generation/custom_molecule_inserter.py`: Custom molecule placement (random + custom modes)
- `quickice/structure_generation/overlap_resolver.py`: PBC-aware overlap detection via cKDTree, whole-molecule removal
- `quickice/structure_generation/water_filler.py`: TIP4P water template tiling and region filling
- `quickice/structure_generation/moleculetype_registry.py`: Unique GROMACS moleculetype naming (CH4_H vs CH4_L)
- `quickice/structure_generation/itp_parser.py`: GROMACS .itp topology file parser
- `quickice/structure_generation/gro_parser.py`: GRO coordinate file parser (string and file)
- `quickice/structure_generation/gromacs_ion_export.py`: Ion ITP file generation
- `quickice/structure_generation/cell_utils.py`: Orthogonal cell detection
- `quickice/structure_generation/molecule_validator.py`: Molecule validation
- `quickice/structure_generation/mapper.py`: Phase ID → GenIce lattice name mapping + supercell calculation

**GUI Panels (one per tab):**
- `quickice/gui/main_window.py`: MainWindow with 6-tab layout + all event handlers (2024 lines)
- `quickice/gui/viewmodel.py`: MainViewModel (MVVM ViewModel, signal/slot orchestration)
- `quickice/gui/view.py`: InputPanel, ProgressPanel, ViewerPanel, InfoPanel (shared across tabs)
- `quickice/gui/interface_panel.py`: Interface Construction tab (Tab 2)
- `quickice/gui/hydrate_panel.py`: Hydrate Generation tab (Tab 1)
- `quickice/gui/ion_panel.py`: Ion Insertion tab (Tab 5)
- `quickice/gui/solute_panel.py`: Solute Insertion tab (Tab 4)
- `quickice/gui/custom_molecule_panel.py`: Custom Molecule tab (Tab 3) — 1307 lines

**GUI Viewers:**
- `quickice/gui/dual_viewer.py`: Side-by-side candidate comparison (2 synchronized VTK viewports)
- `quickice/gui/molecular_viewer.py`: Single VTK molecular viewer widget
- `quickice/gui/interface_viewer.py`: Interface-specific VTK viewer
- `quickice/gui/hydrate_viewer.py`: Hydrate-specific VTK viewer
- `quickice/gui/ion_viewer.py`: Ion-specific VTK viewer
- `quickice/gui/solute_viewer.py`: Solute-specific VTK viewer
- `quickice/gui/custom_molecule_viewer.py`: Custom molecule VTK viewer
- `quickice/gui/vtk_utils.py`: VTK utility functions (actor creation, bond rendering)

**GUI Renderers:**
- `quickice/gui/hydrate_renderer.py`: Hydrate structure VTK rendering
- `quickice/gui/ion_renderer.py`: Ion structure VTK rendering (Na/Cl actors)
- `quickice/gui/solute_renderer.py`: Solute molecule VTK actor creation
- `quickice/gui/custom_molecule_renderer.py`: Custom molecule VTK rendering

**GUI Exporters:**
- `quickice/gui/export.py`: 5 exporter classes — PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter, InterfaceGROMACSExporter, IonGROMACSExporter, SoluteGROMACSExporter, CustomMoleculeGROMACSExporter
- `quickice/gui/hydrate_export.py`: 1 exporter class — HydrateGROMACSExporter

**GUI Workers:**
- `quickice/gui/workers.py`: GenerationWorker, InterfaceGenerationWorker
- `quickice/gui/hydrate_worker.py`: HydrateWorker
- `quickice/gui/custom_molecule_worker.py`: CustomMoleculeWorker

**GUI Support:**
- `quickice/gui/constants.py`: TabIndex enum for tab positions
- `quickice/gui/validators.py`: GUI-specific input validators (return `tuple[bool, str]`)
- `quickice/gui/phase_diagram_widget.py`: Interactive matplotlib phase diagram panel
- `quickice/gui/help_dialog.py`: Quick reference help dialog

**Output Writers:**
- `quickice/output/gromacs_writer.py`: All GROMACS file writers (2559 lines — write_gro_file, write_top_file, write_interface_*, write_multi_molecule_*, write_solute_*, write_ion_*, compute_mw_position, wrap_molecules_into_box)
- `quickice/output/pdb_writer.py`: PDB file writer with CRYST1 records
- `quickice/output/phase_diagram.py`: Phase diagram generation (matplotlib)
- `quickice/output/validator.py`: Space group and atomic overlap validation
- `quickice/output/orchestrator.py`: Output pipeline coordinator

**Phase Mapping:**
- `quickice/phase_mapping/lookup.py`: Main `lookup_phase()` function + PHASE_METADATA
- `quickice/phase_mapping/melting_curves.py`: IAPWS R14-08 melting pressure functions
- `quickice/phase_mapping/solid_boundaries.py`: Solid-solid boundary curves
- `quickice/phase_mapping/triple_points.py`: Triple point data
- `quickice/phase_mapping/water_density.py`: IAPWS-95 liquid water density
- `quickice/phase_mapping/ice_ih_density.py`: IAPWS R10-06 Ice Ih density

**Testing:**
- `tests/test_output/conftest.py`: E2E export test fixtures (structure factories + mock dialog factories)
- `tests/test_output/test_gromacs_export_ice.py`: Ice GROMACS export tests
- `tests/test_output/test_gromacs_export_hydrate.py`: Hydrate GROMACS export tests
- `tests/test_output/test_gromacs_export_interface.py`: Interface GROMACS export tests
- `tests/test_output/test_gromacs_export_custom.py`: Custom molecule GROMACS export tests
- `tests/test_output/test_gromacs_export_solute.py`: Solute GROMACS export tests
- `tests/test_output/test_gromacs_export_ion.py`: Ion GROMACS export tests
- `tests/test_output/test_gromacs_export_chain.py`: Full chain (interface → custom → solute → ion) export tests
- `tests/test_output/test_itp_parser_edge_cases.py`: ITP parser edge case tests (added Batch 6A)
- `tests/test_output/test_overlap_removal_invariants.py`: Overlap removal invariant tests (added Batch 6A)
- `tests/test_pocket_invariants.py`: Pocket mode invariant assertions tests
- `tests/test_pocket_edge_cases.py`: Pocket mode edge case tests
- `tests/test_pocket_cubic_guests.py`: Pocket cubic shape + guest molecule tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `ion_inserter.py`, `hydrate_generator.py`)
- Test files: `test_{feature}.py` (e.g., `test_solute_insertion.py`, `test_pocket_invariants.py`)
- GUI panels: `{feature}_panel.py` (e.g., `hydrate_panel.py`, `ion_panel.py`)
- GUI viewers: `{feature}_viewer.py` (e.g., `hydrate_viewer.py`, `ion_viewer.py`)
- GUI renderers: `{feature}_renderer.py` (e.g., `hydrate_renderer.py`, `solute_renderer.py`)
- GUI workers: `{feature}_worker.py` (e.g., `hydrate_worker.py`, `custom_molecule_worker.py`)
- Mode modules: `{mode}.py` under `modes/` (e.g., `slab.py`, `pocket.py`, `piece.py`)
- Data files: Descriptive names with extensions (e.g., `tip4p-ice.itp`, `ch4_hydrate.itp`)

**Directories:**
- Python packages: `snake_case/` with `__init__.py`
- Test subpackages: `test_{group}/` with `__init__.py` and `conftest.py`

**Classes:**
- Data types: `PascalCase` dataclasses (e.g., `Candidate`, `InterfaceStructure`, `IonStructure`)
- Generator classes: `PascalCase` with noun suffix (e.g., `IceStructureGenerator`, `HydrateStructureGenerator`, `SoluteInserter`, `CustomMoleculeInserter`)
- GUI panels: `PascalCase` + `Panel` suffix (e.g., `InterfacePanel`, `HydratePanel`)
- GUI viewers: `PascalCase` + `ViewerWidget` suffix (e.g., `DualViewerWidget`, `MolecularViewerWidget`)
- Exporters: `PascalCase` + `Exporter` suffix (e.g., `GROMACSExporter`, `HydrateGROMACSExporter`, `SoluteGROMACSExporter`)
- Workers: `PascalCase` + `Worker` suffix (e.g., `GenerationWorker`, `HydrateWorker`)

**Functions:**
- `snake_case()` for module-level functions (e.g., `assemble_slab()`, `detect_overlaps()`, `generate_candidates()`)
- Private helpers: `_snake_case()` prefix underscore (e.g., `_detect_guest_atoms()`, `_build_result()`)
- Writer functions: `write_{format}_file()` (e.g., `write_gro_file()`, `write_top_file()`, `write_interface_gro_file()`)

## Where to Add New Code

**New Ice Phase Support:**
- Phase mapping: `quickice/phase_mapping/mapper.py` (add to `PHASE_TO_GENICE` dict)
- Boundary data: `quickice/phase_mapping/solid_boundaries.py` (add boundary function)
- Triple points: `quickice/phase_mapping/triple_points.py` (add triple point data)
- Metadata: `quickice/phase_mapping/lookup.py` (add to `PHASE_METADATA`)

**New Interface Mode:**
- Mode implementation: `quickice/structure_generation/modes/{mode}.py` (export `assemble_{mode}(candidate, config) → InterfaceStructure`)
- Register: `quickice/structure_generation/modes/__init__.py` (add to `__all__`)
- Route: `quickice/structure_generation/interface_builder.py` (add dispatch in `generate_interface()`)
- GUI config: `quickice/gui/interface_panel.py` (add UI controls for mode-specific parameters)

**New Molecule Type (e.g., CO2 guest):**
- Types: `quickice/structure_generation/types.py` (add to `MOLECULE_TYPE_INFO`, `GUEST_MOLECULES`)
- Data: `quickice/data/{molecule}.itp`, `quickice/data/{molecule}_hydrate.itp`
- GROMACS mapping: `quickice/output/gromacs_writer.py` (add to `MOLECULE_TO_GROMACS` dict)
- Guest detection: Update `_detect_guest_atoms()` in each mode module

**New Tab:**
- Panel: `quickice/gui/{feature}_panel.py` (QWidget subclass)
- TabIndex: `quickice/gui/constants.py` (add enum value)
- Worker: `quickice/gui/{feature}_worker.py` (QObject subclass)
- Main window: `quickice/gui/main_window.py` (add tab, setup connections, add handlers)
- Tab order: Update `TabIndex` enum and `addTab()` calls

**New Exporter:**
- Exporter class: `quickice/gui/export.py` (or new `quickice/gui/{feature}_export.py` for separate files)
- Writer function: `quickice/output/gromacs_writer.py` (add `write_{feature}_gro_file`, `write_{feature}_top_file`)
- Menu action: `quickice/gui/main_window.py` → `_create_menu_bar()` (add "Export As..." entry)
- Tests: `tests/test_output/test_gromacs_export_{feature}.py`
- Fixtures: `tests/test_output/conftest.py` (add structure fixture)

**New Solute Type:**
- Config: `quickice/structure_generation/types.py` → `SoluteConfig.solute_type` (add to validation)
- Data: `quickice/data/{solute}_liquid.itp` (liquid-phase topology)
- Inserter: `quickice/structure_generation/solute_inserter.py` (add template loading)
- Registry: `quickice/structure_generation/moleculetype_registry.py` (add to `RESERVED_NAMES`)

**New Utility:**
- Shared helpers: `quickice/utils/molecule_utils.py` (for molecule-related utilities)
- New utility module: `quickice/utils/{name}.py` + update `quickice/utils/__init__.py`

## Special Directories

**`quickice/data/`:**
- Purpose: Bundled molecular topology/coordinate files shipped with the application
- Generated: No (hand-curated ITP/GRO files)
- Committed: Yes
- Accessed via: `Path(quickice.__file__).parent / "data"` or `get_tip4p_itp_path()`

**`quickice/data/custom/`:**
- Purpose: Example custom molecule files (ethanol) for demo/testing
- Generated: No
- Committed: Yes
- Accessed via: `Path(quickice.__file__).parent / "data" / "custom"`

**`quickice/phase_mapping/data/`:**
- Purpose: Ice phase boundary data (JSON + Python)
- Generated: No
- Committed: Yes
- Key files: `quickice/phase_mapping/data/ice_phases.json`, `quickice/phase_mapping/data/ice_boundaries.py`

**`sample_output/`:**
- Purpose: Reference GROMACS/PDB output for manual regression checking
- Generated: Yes (from running QuickIce)
- Committed: Yes
- Structure: `cli_ice/`, `cli_interface/`, `gui_interface/`, `gui_v4/` (organized by source and structure type)

**`tmp/`:**
- Purpose: Temporary debug output during development
- Generated: Yes
- Committed: No (should be in .gitignore)
- Contains: Various debug subdirectories with GRO/TOP/ITP files from testing

**`dist/` and `build/`:**
- Purpose: PyInstaller build artifacts and distribution bundle
- Generated: Yes (by `pyinstaller quickice-gui.spec`)
- Committed: No (build artifacts)

**`.planning/`:**
- Purpose: Project planning, phase documents, research, roadmaps, UAT checklists
- Generated: No (authored during development)
- Committed: Yes
- Structure: `phases/`, `quick/`, `research/`, `uat/`, `todos/`, `debug/`, `codebase/`

---

*Structure analysis: 2026-05-22*
