# Codebase Structure

**Analysis Date:** 2026-05-22

## Directory Layout

```
quickice/                           # Project root
├── quickice/                       # Main Python package
│   ├── __init__.py                 # Package version (4.5.0)
│   ├── main.py                     # CLI entry point logic
│   ├── cli/                        # CLI argument parsing
│   │   ├── __init__.py
│   │   └── parser.py               # argparse definition + validation
│   ├── gui/                        # PySide6 GUI (MVVM View + ViewModel + Workers)
│   │   ├── __init__.py             # Exports MainWindow, run_app, panels
│   │   ├── __main__.py             # GUI entry: python -m quickice.gui
│   │   ├── main_window.py         # MainWindow (MVVM View, tab orchestrator)
│   │   ├── viewmodel.py            # MainViewModel (MVVM ViewModel, worker manager)
│   │   ├── view.py                 # InputPanel, ProgressPanel, ViewerPanel, InfoPanel
│   │   ├── constants.py            # TabIndex IntEnum (ICE=0..ION=5)
│   │   ├── validators.py           # GUI-side input validators
│   │   ├── workers.py             # GenerationWorker, InterfaceGenerationWorker
│   │   ├── hydrate_worker.py       # HydrateWorker (QThread subclass)
│   │   ├── custom_molecule_worker.py # CustomMoleculeWorker (QObject)
│   │   ├── export.py              # PDBExporter, GROMACSExporter, SoluteGROMACSExporter, etc.
│   │   ├── molecular_viewer.py    # MolecularViewerWidget (VTK 3D viewport)
│   │   ├── dual_viewer.py         # DualViewerWidget (side-by-side comparison)
│   │   ├── vtk_utils.py           # candidate_to_vtk_molecule, hbond/unit_cell actors
│   │   ├── interface_panel.py     # Interface Construction tab UI
│   │   ├── interface_viewer.py    # Interface 3D viewer
│   │   ├── hydrate_panel.py       # Hydrate Generation tab UI
│   │   ├── hydrate_viewer.py      # Hydrate 3D viewer
│   │   ├── hydrate_renderer.py    # Hydrate VTK rendering functions
│   │   ├── hydrate_export.py      # HydrateGROMACSExporter
│   │   ├── ion_panel.py          # Ion Insertion tab UI
│   │   ├── ion_viewer.py         # Ion 3D viewer
│   │   ├── ion_renderer.py        # Ion VTK rendering (Na+, Cl- actors)
│   │   ├── solute_panel.py       # Solute Insertion tab UI
│   │   ├── solute_viewer.py      # Solute 3D viewer
│   │   ├── solute_renderer.py    # Solute VTK rendering (CH4/THF actors)
│   │   ├── custom_molecule_panel.py  # Custom Molecule tab UI
│   │   ├── custom_molecule_viewer.py # Custom Molecule 3D viewer
│   │   ├── custom_molecule_renderer.py # Custom Molecule VTK rendering
│   │   ├── custom_molecule_worker.py  # CustomMoleculeWorker (background thread)
│   │   ├── phase_diagram_widget.py # Interactive matplotlib phase diagram
│   │   ├── help_dialog.py        # Quick reference modal dialog
│   │   ├── molecular_viewer.py    # Core VTK viewer widget
│   │   └── dual_viewer.py        # Side-by-side dual viewport
│   ├── structure_generation/       # Core computation (Model layer)
│   │   ├── __init__.py            # Public API exports
│   │   ├── types.py              # Dataclasses: Candidate, InterfaceStructure, IonStructure, etc.
│   │   ├── errors.py             # StructureGenerationError, UnsupportedPhaseError, InterfaceGenerationError
│   │   ├── mapper.py             # Phase ID → GenIce name mapping, supercell calculation
│   │   ├── generator.py          # IceStructureGenerator (GenIce2 wrapper)
│   │   ├── hydrate_generator.py  # HydrateStructureGenerator (GenIce2 hydrate wrapper)
│   │   ├── interface_builder.py  # validate_interface_config + generate_interface (mode router)
│   │   ├── ion_inserter.py       # IonInserter (NaCl concentration-based insertion)
│   │   ├── solute_inserter.py    # SoluteInserter (CH4/THF concentration-based insertion)
│   │   ├── custom_molecule_inserter.py # CustomMoleculeInserter (random/custom placement)
│   │   ├── water_filler.py       # TIP4P water template loading, tiling, region filling
│   │   ├── overlap_resolver.py   # PBC-aware overlap detection, whole-molecule removal
│   │   ├── gro_parser.py         # GRO format string/file parser
│   │   ├── itp_parser.py         # ITP format parser for custom molecules
│   │   ├── molecule_validator.py # Single-molecule placement validation
│   │   ├── moleculetype_registry.py # Unique GROMACS moleculetype naming (_H/_L suffixes)
│   │   ├── gromacs_ion_export.py # Ion ITP file generation
│   │   ├── cell_utils.py         # is_cell_orthogonal(), cell extent calculations
│   │   └── modes/                 # Interface assembly implementations
│   │       ├── __init__.py
│   │       ├── slab.py           # Slab mode (ice-water-ice sandwich)
│   │       ├── pocket.py        # Pocket mode (spherical/cubic cavity in ice)
│   │       └── piece.py         # Piece mode (ice crystal in water box)
│   ├── phase_mapping/             # Ice phase identification from T, P
│   │   ├── __init__.py           # Exports lookup_phase, IcePhaseLookup
│   │   ├── lookup.py             # Curve-based phase lookup (IAPWS R14-08)
│   │   ├── errors.py            # PhaseMappingError, UnknownPhaseError
│   │   ├── melting_curves.py     # IAPWS melting pressure curves
│   │   ├── solid_boundaries.py   # Solid-solid boundary linear interpolation
│   │   ├── triple_points.py     # Triple point data (T, P coordinates)
│   │   ├── ice_ih_density.py    # IAPWS R10-06 temperature-dependent density
│   │   ├── water_density.py     # Liquid water density calculation
│   │   └── data/                 # Phase boundary reference data
│   │       ├── __init__.py
│   │       ├── ice_boundaries.py # Boundary curve coefficients
│   │       └── ice_phases.json   # Phase metadata JSON
│   ├── ranking/                   # Candidate scoring and ranking
│   │   ├── __init__.py           # Exports rank_candidates, scoring functions
│   │   ├── types.py             # RankedCandidate, RankingResult, ScoringConfig
│   │   └── scorer.py            # energy_score, density_score, diversity_score
│   ├── output/                    # File output and validation
│   │   ├── __init__.py           # Exports writers and orchestrator
│   │   ├── types.py             # OutputResult dataclass
│   │   ├── orchestrator.py      # output_ranked_candidates (PDB + diagram + validation)
│   │   ├── pdb_writer.py        # PDB format writer with CRYST1 records
│   │   ├── gromacs_writer.py    # GRO/TOP/ITP writers (ice, interface, multi-molecule)
│   │   ├── validator.py         # Space group validation, atomic overlap check
│   │   └── phase_diagram.py     # Matplotlib phase diagram generation
│   ├── validation/                 # Shared input validators
│   │   ├── __init__.py
│   │   └── validators.py        # validate_temperature, validate_pressure, validate_nmolecules
│   ├── utils/                      # Shared utilities
│   │   ├── __init__.py
│   │   └── molecule_utils.py    # count_guest_atoms, atom type detection
│   ├── data/                        # Bundled force field and template files
│   │   ├── tip4p.gro             # TIP4P water template structure
│   │   ├── tip4p-ice.itp         # TIP4P-ICE water model topology
│   │   ├── ch4.itp               # Methane topology (standalone)
│   │   ├── ch4_hydrate.itp       # Methane topology (hydrate cage context)
│   │   ├── ch4_liquid.itp        # Methane topology (liquid solute context)
│   │   ├── thf.itp               # THF topology (standalone)
│   │   ├── thf_hydrate.itp       # THF topology (hydrate cage context)
│   │   ├── thf_liquid.itp        # THF topology (liquid solute context)
│   │   └── custom/               # Example custom molecule files
│   │       ├── etoh.gro          # Ethanol example structure
│   │       ├── etoh.itp          # Ethanol example topology
│   │       ├── etoh.chg          # Ethanol example charges
│   │       └── etoh.top          # Ethanol example topology
│   └── output/                     # (Empty) Default output directory
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_structure_generation.py
│   ├── test_phase_mapping.py
│   ├── test_ranking.py
│   ├── test_integration_v35.py
│   ├── test_custom_molecule.py
│   ├── test_custom_molecule_concentration.py
│   ├── test_custom_molecule_panel_34_6.py
│   ├── test_custom_molecule_renderer.py
│   ├── test_solute_insertion.py
│   ├── test_solute_ion_molecule_index.py
│   ├── test_ion_hydrate_fix.py
│   ├── test_ion_source_dropdown.py
│   ├── test_hydrate_guest_tiling.py
│   ├── test_interface_modes_audit.py
│   ├── test_interface_ordering_validation.py
│   ├── test_cli_integration.py
│   ├── test_validators.py
│   ├── test_atom_names_filtering.py
│   ├── test_atom_ordering_validation.py
│   ├── test_gromacs_molecule_ordering.py
│   ├── test_ice_ih_density.py
│   ├── test_water_density.py
│   ├── test_med03_minimum_box_size.py
│   ├── test_moleculetype_registry.py
│   ├── test_pbc_hbonds.py
│   ├── test_piece_mode_validation.py
│   ├── test_triclinic_interface.py
│   └── test_output/                # Output-specific tests
│       ├── __init__.py
│       ├── test_molecule_wrapping.py
│       ├── test_pdb_writer.py
│       └── test_validator.py
├── quickice.py                     # CLI script entry point
├── environment.yml                 # Conda environment (runtime)
├── environment-build.yml           # Conda environment (build with PyInstaller)
├── requirements-dev.txt            # Dev dependencies
├── setup.sh                        # Setup script
├── scripts/                        # Utility scripts
├── docs/                           # Documentation
│   └── images/
├── sample_output/                  # Sample GROMACS output files
├── licenses/                       # License files
└── .github/workflows/              # CI pipeline
```

## Directory Purposes

**`quickice/gui/`:**
- Purpose: All GUI code — PySide6 widgets, VTK viewers, MVVM ViewModel, workers
- Contains: Panel widgets (6 tabs), viewer widgets (VTK 3D), exporter classes, workers, main window
- Key files: `quickice/gui/main_window.py` (2025 lines — the central orchestrator), `quickice/gui/viewmodel.py`, `quickice/gui/workers.py`
- Pattern: Each tab has a panel file (UI), a viewer file (VTK), a renderer file (VTK actor creation), and optionally a worker file (background thread)

**`quickice/structure_generation/`:**
- Purpose: Core computation — ice/hydrate generation, interface assembly, insertion algorithms
- Contains: Generator classes, inserter classes, mode implementations, type definitions
- Key files: `quickice/structure_generation/types.py` (718 lines — all dataclasses), `quickice/structure_generation/generator.py`, `quickice/structure_generation/interface_builder.py`
- Pattern: No Qt imports — pure Python/NumPy/scipy for testability and CLI reuse

**`quickice/structure_generation/modes/`:**
- Purpose: Interface assembly implementations for each mode
- Contains: `slab.py` (ice-water-ice sandwich), `pocket.py` (cavity in ice), `piece.py` (ice crystal in water)
- Key files: `quickice/structure_generation/modes/slab.py` (largest, 631 lines)

**`quickice/phase_mapping/`:**
- Purpose: Ice phase identification from temperature and pressure using IAPWS boundary curves
- Contains: Lookup functions, melting curves, solid boundaries, triple points, density functions
- Key files: `quickice/phase_mapping/lookup.py` (430 lines), `quickice/phase_mapping/melting_curves.py`

**`quickice/ranking/`:**
- Purpose: Candidate scoring and ranking after generation
- Contains: Scoring functions (energy, density, diversity), result types
- Key files: `quickice/ranking/scorer.py`, `quickice/ranking/types.py`

**`quickice/output/`:**
- Purpose: File output — PDB, GROMACS (.gro/.top/.itp), phase diagram, validation
- Contains: Writers, orchestrator, validator, phase diagram generator
- Key files: `quickice/output/gromacs_writer.py` (largest, 1400+ lines — handles all GROMACS export variants)

**`quickice/data/`:**
- Purpose: Bundled force field files and molecular templates
- Contains: TIP4P-ICE water model ITP, water template GRO, guest molecule ITPs (CH4, THF in hydrate/liquid/standalone contexts), example custom molecule files
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`

**`quickice/validation/`:**
- Purpose: Shared input validation functions used by both CLI and GUI
- Contains: Range validators for temperature, pressure, molecule count, box dimensions
- Key files: `quickice/validation/validators.py`

**`quickice/utils/`:**
- Purpose: Shared utility functions
- Contains: Molecule utility functions (atom counting, type detection)
- Key files: `quickice/utils/molecule_utils.py`

## Key File Locations

**Entry Points:**
- `quickice.py`: CLI script entry (`python quickice.py --temperature 300 --pressure 100`)
- `quickice/gui/__main__.py`: GUI entry (`python -m quickice.gui`)
- `quickice/main.py`: CLI main function (called by `quickice.py`)

**Configuration:**
- `quickice/gui/constants.py`: `TabIndex` IntEnum — type-safe tab routing constants
- `environment.yml`: Conda runtime environment specification
- `environment-build.yml`: Conda build environment (adds PyInstaller)
- `requirements-dev.txt`: Development dependencies

**Core Logic (Model Layer):**
- `quickice/structure_generation/types.py`: All data types (Candidate, InterfaceStructure, IonStructure, SoluteStructure, CustomMoleculeStructure, HydrateStructure, configs)
- `quickice/structure_generation/generator.py`: IceStructureGenerator (GenIce2 wrapper)
- `quickice/structure_generation/hydrate_generator.py`: HydrateStructureGenerator
- `quickice/structure_generation/interface_builder.py`: validate + generate_interface (mode router)
- `quickice/structure_generation/ion_inserter.py`: IonInserter (NaCl concentration-based)
- `quickice/structure_generation/solute_inserter.py`: SoluteInserter (CH4/THF)
- `quickice/structure_generation/custom_molecule_inserter.py`: CustomMoleculeInserter
- `quickice/structure_generation/water_filler.py`: TIP4P water template + tiling
- `quickice/structure_generation/overlap_resolver.py`: PBC-aware overlap detection + molecule removal
- `quickice/structure_generation/mapper.py`: Phase ID → GenIce name mapping

**GUI Core:**
- `quickice/gui/main_window.py`: MainWindow (2025 lines) — central tab orchestrator, cross-tab data mediator
- `quickice/gui/viewmodel.py`: MainViewModel — worker lifecycle management, signal forwarding
- `quickice/gui/workers.py`: GenerationWorker, InterfaceGenerationWorker
- `quickice/gui/view.py`: InputPanel, ProgressPanel, ViewerPanel, InfoPanel

**VTK Rendering:**
- `quickice/gui/molecular_viewer.py`: MolecularViewerWidget (base VTK 3D viewer)
- `quickice/gui/dual_viewer.py`: DualViewerWidget (side-by-side comparison)
- `quickice/gui/vtk_utils.py`: candidate_to_vtk_molecule, hydrogen bond actors, unit cell actors
- `quickice/gui/interface_viewer.py`: Interface-specific 3D viewer
- `quickice/gui/hydrate_viewer.py`: Hydrate-specific 3D viewer
- `quickice/gui/ion_viewer.py`: Ion-specific 3D viewer
- `quickice/gui/solute_viewer.py`: Solute-specific 3D viewer
- `quickice/gui/custom_molecule_viewer.py`: Custom molecule 3D viewer

**Export Pipeline:**
- `quickice/gui/export.py`: PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter, InterfaceGROMACSExporter, IonGROMACSExporter, SoluteGROMACSExporter, CustomMoleculeGROMACSExporter
- `quickice/gui/hydrate_export.py`: HydrateGROMACSExporter
- `quickice/output/gromacs_writer.py`: write_gro_file, write_top_file, write_interface_gro_file, write_interface_top_file, write_multi_molecule_gro_file, write_multi_molecule_top_file
- `quickice/output/pdb_writer.py`: PDB format writers
- `quickice/output/orchestrator.py`: output_ranked_candidates (CLI PDB + diagram pipeline)

**Testing:**
- `tests/`: All test files (see Testing section below)

## Naming Conventions

**Files:**
- Panel widgets: `{feature}_panel.py` (e.g., `ion_panel.py`, `hydrate_panel.py`)
- VTK viewers: `{feature}_viewer.py` (e.g., `ion_viewer.py`, `interface_viewer.py`)
- VTK renderers: `{feature}_renderer.py` (e.g., `ion_renderer.py`, `solute_renderer.py`)
- Workers: `{feature}_worker.py` (e.g., `hydrate_worker.py`, `custom_molecule_worker.py`)
- Exporters: `{feature}_export.py` (e.g., `hydrate_export.py`) or in `export.py`
- Types: `types.py` (one per module, contains all dataclasses)
- Errors: `errors.py` (one per module, contains domain exceptions)
- Utilities: `utils.py` or `{feature}_utils.py`
- Modes: `modes/{mode_name}.py`

**Directories:**
- Feature modules: `quickice/{feature}/` (e.g., `structure_generation/`, `phase_mapping/`)
- Test directories match source structure: `tests/test_{feature}.py`
- Data files: `quickice/data/` (bundled ITP/GRO files)
- Sub-modes: `quickice/structure_generation/modes/`

**Tab Widget Naming:**
- Tab panels stored as `self.{feature}_panel` in MainWindow (e.g., `self.ion_panel`, `self.solute_panel`)
- Tab viewers stored as `self.{feature}_viewer` inside panels
- Tab constants: `TabIndex.ICE`, `TabIndex.HYDRATE`, `TabIndex.INTERFACE`, `TabIndex.CUSTOM`, `TabIndex.SOLUTE`, `TabIndex.ION`

**Instance Variables in MainWindow:**
- Current results: `self._current_{feature}_result` (e.g., `_current_interface_result`, `_current_ion_result`)
- Current configs: `self._current_{feature}_config` (e.g., `_current_hydrate_config`)
- Workers: `self._{feature}_worker` (e.g., `_hydrate_worker`, `_custom_worker`)
- Threads: `self._{feature}_thread` (e.g., `_interface_thread`, `_custom_worker_thread`)
- Exporters: `self._{feature}_exporter` or `self._{feature}_gromacs_exporter`

## Where to Add New Code

**New Feature (e.g., new molecule type):**
- Primary code: `quickice/structure_generation/{new_inserter}.py` — follow pattern of `ion_inserter.py`/`solute_inserter.py`
- Types: Add config/structure dataclasses to `quickice/structure_generation/types.py`
- GUI panel: `quickice/gui/{feature}_panel.py`
- GUI viewer: `quickice/gui/{feature}_viewer.py`
- GUI renderer: `quickice/gui/{feature}_renderer.py`
- GUI worker: `quickice/gui/{feature}_worker.py` (use QObject + moveToThread pattern)
- Export: Add exporter class to `quickice/gui/export.py` or create `quickice/gui/{feature}_export.py`
- Data files: Add ITP/GRO templates to `quickice/data/`
- Tests: `tests/test_{feature}.py`

**New Tab:**
1. Add `TabIndex` constant in `quickice/gui/constants.py`
2. Create panel widget following `quickice/gui/ion_panel.py` pattern
3. Add tab to `MainWindow._setup_ui()` with `self.tab_widget.addTab()`
4. Connect signals in `MainWindow._setup_connections()`
5. Add export route in `MainWindow._on_export_current_tab()`

**New Interface Mode:**
- Implementation: `quickice/structure_generation/modes/{mode_name}.py`
- Routing: Add mode case to `generate_interface()` in `quickice/structure_generation/interface_builder.py`
- Validation: Add mode-specific checks to `validate_interface_config()`
- Config: Add mode parameters to `InterfaceConfig` dataclass in `quickice/structure_generation/types.py`

**New GROMACS Exporter:**
- Exporter class: Add to `quickice/gui/export.py` following existing patterns
- Writer functions: Add to `quickice/output/gromacs_writer.py`
- Register in `MainWindow.__init__()` and `MainWindow._create_menu_bar()`

**Utilities:**
- Shared helpers: `quickice/utils/molecule_utils.py`
- Molecule type info: `quickice/structure_generation/types.py` → `MOLECULE_TYPE_INFO` dict

**Tests:**
- Unit tests: `tests/test_{feature}.py`
- Output tests: `tests/test_output/test_{feature}.py`

## Special Directories

**`quickice/data/`:**
- Purpose: Bundled force field ITP files, water template GRO, example custom molecules
- Generated: No (manually maintained)
- Committed: Yes (part of package distribution)
- Note: Referenced by `get_tip4p_itp_path()` and other file-loading functions using `Path(quickice.__file__).parent / "data"`

**`quickice/data/custom/`:**
- Purpose: Example custom molecule files (ethanol demo)
- Contains: etoh.gro, etoh.itp, etoh.chg, etoh.top

**`quickice/phase_mapping/data/`:**
- Purpose: Ice phase boundary reference data
- Contains: `ice_boundaries.py` (boundary curve coefficients), `ice_phases.json` (metadata)
- Committed: Yes

**`sample_output/`:**
- Purpose: Example GROMACS output files for reference/validation
- Generated: Yes (from running the application)
- Committed: Yes (for documentation purposes)

**`tests/test_output/`:**
- Purpose: Temporary test output directory
- Generated: Yes (created during test runs)
- Committed: Partially (only `__init__.py`)

**`.planning/`:**
- Purpose: GSD planning documents, phase tracking, debug scripts
- Not part of the application package

---

*Structure analysis: 2026-05-22*
