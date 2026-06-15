# Codebase Structure

**Analysis Date:** 2026-06-15

## Directory Layout

```
quickice/                          # Project root
├── quickice/                      # Main package
│   ├── __init__.py                # Version (4.5.0)
│   ├── __main__.py                # python -m quickice entry → entry.main()
│   ├── entry.py                   # Unified router: --cli/--gui/flag detection
│   ├── main.py                    # CLI main: argparse → CLIPipeline or ice-only workflow
│   ├── cli/                       # CLI-specific modules (NO Qt imports)
│   │   ├── __init__.py
│   │   ├── parser.py             # argparse definition + validate_pipeline_args()
│   │   ├── pipeline.py           # CLIPipeline: ordered step execution
│   │   └── itp_helpers.py        # ITP path resolution + copy_itp_files_for_structure()
│   ├── gui/                       # PySide6 GUI modules
│   │   ├── __init__.py
│   │   ├── __main__.py           # python -m quickice.gui entry
│   │   ├── main_window.py        # MainWindow (2024 lines, MVVM View + signal hub)
│   │   ├── viewmodel.py          # MainViewModel (MVVM ViewModel + worker management)
│   │   ├── view.py               # InputPanel, ProgressPanel, ViewerPanel, InfoPanel
│   │   ├── constants.py          # TabIndex IntEnum
│   │   ├── workers.py            # GenerationWorker, InterfaceGenerationWorker (QObject)
│   │   ├── hydrate_worker.py     # HydrateWorker (QThread subclass — not migrated)
│   │   ├── custom_molecule_worker.py  # CustomMoleculeWorker (QObject)
│   │   ├── interface_panel.py    # Interface Construction tab UI
│   │   ├── interface_viewer.py   # VTK viewer for interface structures
│   │   ├── hydrate_panel.py      # Hydrate Generation tab UI
│   │   ├── hydrate_viewer.py     # VTK viewer for hydrate structures
│   │   ├── hydrate_renderer.py   # VTK actor creation for hydrate visualization
│   │   ├── hydrate_export.py     # HydrateGROMACSExporter
│   │   ├── custom_molecule_panel.py   # Custom Molecule tab UI
│   │   ├── custom_molecule_viewer.py  # VTK viewer for custom molecule preview
│   │   ├── custom_molecule_renderer.py # VTK actor creation for custom molecules
│   │   ├── solute_panel.py       # Solute Insertion tab UI
│   │   ├── solute_viewer.py      # VTK viewer for solute structures
│   │   ├── solute_renderer.py    # VTK actor creation for solute visualization
│   │   ├── ion_panel.py          # Ion Insertion tab UI
│   │   ├── ion_viewer.py         # VTK viewer for ion structures
│   │   ├── ion_renderer.py       # VTK actor creation for ion visualization
│   │   ├── export.py             # PDB/Diagram/Viewport/GROMACS exporters
│   │   ├── help_dialog.py        # Quick Reference dialog
│   │   ├── validators.py         # GUI-specific validators
│   │   ├── phase_diagram_widget.py # PhaseDiagramPanel with interactive canvas
│   │   ├── molecular_viewer.py   # Base VTK molecular viewer
│   │   ├── dual_viewer.py        # Side-by-side VTK dual viewport
│   │   └── vtk_utils.py          # VTK utility functions
│   ├── structure_generation/      # Core physics engine (shared CLI+GUI)
│   │   ├── __init__.py           # Re-exports all key types and generators
│   │   ├── types.py              # All dataclasses: Candidate, InterfaceStructure, HydrateStructure, IonStructure, SoluteStructure, CustomMoleculeStructure, configs
│   │   ├── errors.py             # Exception hierarchy
│   │   ├── generator.py          # IceStructureGenerator (GenIce2 wrapper)
│   │   ├── hydrate_generator.py  # HydrateStructureGenerator (GenIce2 wrapper)
│   │   ├── interface_builder.py  # generate_interface() + validate_interface_config()
│   │   ├── modes/                # Interface assembly modes
│   │   │   ├── __init__.py
│   │   │   ├── slab.py           # Slab mode (ice|water|ice sandwich)
│   │   │   ├── pocket.py         # Pocket mode (spherical/cubic cavity)
│   │   │   └── piece.py          # Piece mode (crystal in water)
│   │   ├── ion_inserter.py       # IonInserter + insert_ions()
│   │   ├── solute_inserter.py    # SoluteInserter
│   │   ├── custom_molecule_inserter.py # CustomMoleculeInserter + InsertionError
│   │   ├── water_filler.py       # Water placement utilities
│   │   ├── overlap_resolver.py   # Overlap detection/removal
│   │   ├── gro_parser.py         # GRO file parser
│   │   ├── itp_parser.py         # ITP file parser
│   │   ├── molecule_validator.py # Molecule validation
│   │   ├── moleculetype_registry.py # Unique GROMACS moleculetype naming
│   │   ├── gromacs_ion_export.py # Ion ITP file generator
│   │   ├── mapper.py             # Phase→GenIce lattice name mapping
│   │   └── cell_utils.py        # Cell orthogonality check
│   ├── output/                   # File output modules (shared CLI+GUI)
│   │   ├── __init__.py           # Re-exports
│   │   ├── types.py              # OutputResult dataclass
│   │   ├── orchestrator.py       # output_ranked_candidates() coordinator
│   │   ├── gromacs_writer.py     # All GROMACS .gro/.top/.itp writers (2705 lines)
│   │   ├── pdb_writer.py         # PDB file writer with CRYST1 records
│   │   ├── validator.py          # Space group validation, overlap checking
│   │   └── phase_diagram.py      # Phase diagram PNG generation
│   ├── phase_mapping/            # T/P → phase identification
│   │   ├── __init__.py
│   │   ├── lookup.py             # lookup_phase(), IcePhaseLookup, PHASE_METADATA
│   │   ├── errors.py             # PhaseMappingError, UnknownPhaseError
│   │   ├── melting_curves.py     # IAPWS R14-08 melting pressure functions
│   │   ├── solid_boundaries.py   # Solid-solid phase boundary functions
│   │   ├── triple_points.py      # Triple point data
│   │   ├── ice_ih_density.py     # Ice Ih density calculations
│   │   ├── water_density.py      # Water density calculations
│   │   └── data/                 # Phase mapping data
│   │       ├── __init__.py
│   │       ├── ice_phases.json   # Phase metadata
│   │       └── ice_boundaries.py # Ice boundary coefficient data
│   ├── ranking/                  # Candidate scoring
│   │   ├── __init__.py
│   │   ├── types.py              # RankedCandidate, RankingResult, ScoringConfig
│   │   └── scorer.py             # rank_candidates(), energy/density/diversity scoring
│   ├── validation/               # Input validators
│   │   ├── __init__.py
│   │   └── validators.py         # argparse type converters (T, P, N, box dims)
│   ├── utils/                    # Shared utilities
│   │   ├── __init__.py
│   │   └── molecule_utils.py     # count_guest_atoms() and other molecule helpers
│   └── data/                     # Bundled force-field and template data
│       ├── tip4p-ice.itp         # TIP4P-ICE force field
│       ├── tip4p.gro             # Water template coordinates
│       ├── ch4_hydrate.itp       # CH4 hydrate force field
│       ├── thf_hydrate.itp       # THF hydrate force field
│       ├── ch4_liquid.itp        # CH4 liquid solute force field
│       ├── thf_liquid.itp        # THF liquid solute force field
│       ├── custom/               # Custom molecule examples
│       │   ├── etoh.gro          # Ethanol coordinates
│       │   ├── etoh.itp          # Ethanol topology
│       │   ├── etoh.top          # Ethanol topology (full)
│       │   └── etoh.chg          # Ethanol charges
│       └── examples/
│           └── custom_positions.csv  # Example positions CSV for custom placement
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Shared pytest fixtures
│   ├── test_entry_point.py       # Entry router tests
│   ├── test_cli_integration.py   # CLI integration tests
│   ├── test_cli_pipeline.py      # CLIPipeline unit tests
│   ├── test_structure_generation.py  # Ice generation tests
│   ├── test_e2e_*.py             # End-to-end workflow chain tests
│   ├── test_custom_molecule*.py  # Custom molecule tests
│   ├── test_solute_*.py         # Solute insertion tests
│   ├── test_ion_*.py             # Ion insertion tests
│   ├── test_hydrate_*.py         # Hydrate generation tests
│   ├── test_interface_*.py       # Interface mode tests
│   ├── test_ranking.py          # Ranking tests
│   ├── test_validators.py       # Validator tests
│   ├── test_phase_mapping.py    # Phase mapping tests
│   ├── test_output/             # Output-specific tests
│   │   ├── conftest.py
│   │   ├── test_gromacs_export_*.py  # Per-step GROMACS export tests
│   │   └── test_pdb_writer.py
│   └── test_integration_v35.py  # Cross-feature integration tests
├── scripts/                      # Shell scripts
│   ├── cli-examples.sh           # Reference for all CLI flag combinations
│   ├── hydrate-interface-custom-ion.sh  # Full workflow wrapper script
│   ├── assemble-dist.sh          # PyInstaller dist packaging
│   ├── build-linux.sh            # Linux build script
│   ├── clean-test-output.sh      # Clean test artifacts
│   ├── run_gui_ssh.sh            # SSH X-forwarding GUI launch
│   └── run_oc.sh                 # OpenCode launch
├── docs/                         # Documentation
│   ├── cli-reference.md          # CLI documentation
│   ├── gui-guide.md              # GUI documentation
│   ├── gro-itp-guide.md          # GRO/ITP format guide
│   ├── flowchart.md              # Data flow diagrams
│   ├── principles.md             # Design principles
│   ├── ranking.md                 # Ranking algorithm documentation
│   └── images/                   # Documentation images
├── sample_output/                # Reference output samples
│   ├── cli_ice/                  # CLI ice generation output
│   ├── cli_interface/            # CLI interface output
│   ├── gui_interface/            # GUI interface output
│   └── gui_v4/                   # GUI v4 multi-step output (ch4/ice/thf × ion/pocket/slab)
├── licenses/                     # Third-party license files
├── .github/workflows/            # CI workflows
│   └── build-windows.yml         # Windows build CI
├── conftest.py                   # Project-level pytest config (custom markers)
├── quickice.py                   # Backward-compat entry → entry.main()
├── quickice-gui.spec             # PyInstaller spec (entry: quickice/__main__.py)
├── environment.yml               # Conda environment (with PySide6)
├── environment-build.yml         # Build environment
├── requirements-dev.txt          # Dev dependencies
├── setup.sh                      # Setup script
└── README.md                     # Project README
```

## Directory Purposes

**`quickice/cli/`:**
- Purpose: CLI-only modules — argument parsing, pipeline orchestration, ITP helpers
- Contains: Parser, pipeline class, ITP path resolution/copy functions
- Key files: `quickice/cli/pipeline.py` (744 lines, CLIPipeline), `quickice/cli/parser.py` (533 lines, argparse), `quickice/cli/itp_helpers.py` (406 lines, ITP file management)
- Constraint: NO Qt/PySide6/VTK imports allowed in this directory

**`quickice/gui/`:**
- Purpose: PySide6-based graphical interface with VTK 3D viewers
- Contains: MainWindow (MVVM View), ViewModel, Workers, Panels, Viewers, Renderers, Exporters
- Key files: `quickice/gui/main_window.py` (2024 lines, signal hub + cross-tab data flow), `quickice/gui/viewmodel.py` (276 lines, MVVM ViewModel)

**`quickice/structure_generation/`:**
- Purpose: Physics engine — all structure generation and insertion logic
- Contains: Generator classes, builder functions, data types, error hierarchy, parsers, overlap resolver
- Key files: `quickice/structure_generation/types.py` (722 lines, all dataclass contracts), `quickice/structure_generation/gromacs_writer.py` (moved to output), `quickice/structure_generation/interface_builder.py` (354 lines), `quickice/structure_generation/hydrate_generator.py` (600 lines)
- Shared: Used by both CLI and GUI paths — no UI or CLI specific logic here

**`quickice/output/`:**
- Purpose: File output — GROMACS, PDB, phase diagram generation
- Contains: Writer functions, orchestrator, validator
- Key files: `quickice/output/gromacs_writer.py` (2705 lines — largest file in codebase, all GROMACS writers)

**`quickice/data/`:**
- Purpose: Bundled force-field ITP files, water template, custom molecule examples
- Contains: TIP4P-ICE, CH4/THF hydrate and liquid ITPs, tip4p.gro template, etoh example
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`

## Key File Locations

**Entry Points:**
- `quickice/__main__.py`: Primary entry (`python -m quickice`) → `entry.main()`
- `quickice/entry.py`: Unified router (201 lines)
- `quickice/main.py`: CLI main (195 lines) — argparse → pipeline or ice-only
- `quickice.py`: Backward compat script → `entry.main()`
- `quickice/gui/__main__.py`: GUI-only entry (`python -m quickice.gui`)

**Configuration:**
- `quickice/__init__.py`: Version string (`__version__ = "4.5.0"`)
- `quickice-gui.spec`: PyInstaller spec (entry point: `quickice/__main__.py`)
- `environment.yml`: Conda environment with PySide6
- `environment-build.yml`: Build-only environment
- `requirements-dev.txt`: Dev/test dependencies
- `conftest.py`: Project-level pytest markers

**Core Logic:**
- `quickice/structure_generation/types.py`: All shared dataclasses (Candidate, InterfaceStructure, HydrateStructure, IonStructure, SoluteStructure, CustomMoleculeStructure, all Config types)
- `quickice/cli/pipeline.py`: CLIPipeline — ordered step execution with fail-fast
- `quickice/cli/parser.py`: argparse definition with v4.5 pipeline flags
- `quickice/cli/itp_helpers.py`: ITP file resolution and copy logic
- `quickice/structure_generation/interface_builder.py`: generate_interface() mode router
- `quickice/structure_generation/generator.py`: IceStructureGenerator (GenIce2 wrapper)
- `quickice/structure_generation/hydrate_generator.py`: HydrateStructureGenerator
- `quickice/structure_generation/ion_inserter.py`: IonInserter + insert_ions()
- `quickice/structure_generation/solute_inserter.py`: SoluteInserter
- `quickice/structure_generation/custom_molecule_inserter.py`: CustomMoleculeInserter + InsertionError
- `quickice/output/gromacs_writer.py`: All GROMACS .gro/.top/.itp writer functions

**Testing:**
- `tests/test_cli_pipeline.py`: CLIPipeline unit tests
- `tests/test_cli_integration.py`: CLI integration tests
- `tests/test_entry_point.py`: Entry router tests
- `tests/test_e2e_workflow_chains.py`: End-to-end workflow chain tests
- `tests/test_e2e_*.py`: Per-feature E2E tests (15+ files)
- `tests/test_output/`: Output-specific tests with conftest.py

**Scripts:**
- `scripts/cli-examples.sh`: Reference for all CLI flag combinations
- `scripts/hydrate-interface-custom-ion.sh`: Full F4 workflow wrapper
- `scripts/assemble-dist.sh`: PyInstaller dist packaging

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `hydrate_generator.py`, `ion_inserter.py`)
- GUI panels: `*_panel.py` (e.g., `hydrate_panel.py`, `ion_panel.py`)
- GUI viewers: `*_viewer.py` (e.g., `interface_viewer.py`, `hydrate_viewer.py`)
- GUI renderers: `*_renderer.py` (e.g., `hydrate_renderer.py`, `ion_renderer.py`)
- GUI workers: `*_worker.py` (e.g., `hydrate_worker.py`, `custom_molecule_worker.py`)
- Test files: `test_*.py` or `test_e2e_*.py` (e.g., `test_cli_pipeline.py`, `test_e2e_ion_export.py`)
- Shell scripts: `kebab-case.sh` (e.g., `cli-examples.sh`, `hydrate-interface-custom-ion.sh`)
- Data files: `lowercase.itp`/`.gro` (e.g., `tip4p-ice.itp`, `ch4_hydrate.itp`)

**Directories:**
- Package modules: `snake_case/` (e.g., `structure_generation/`, `phase_mapping/`)
- Mode subdirectories: `modes/` under `structure_generation/`
- Data subdirectories: `data/`, `data/custom/`, `data/examples/`
- Test subdirectories: `tests/test_output/`

**Dataclass types:**
- Config dataclasses: `*Config` (e.g., `InterfaceConfig`, `HydrateConfig`, `SoluteConfig`, `IonConfig`, `CustomMoleculeConfig`)
- Result dataclasses: `*Structure` or `*Result` (e.g., `InterfaceStructure`, `HydrateStructure`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`, `GenerationResult`, `RankingResult`, `OutputResult`)
- Error classes: `*Error` (e.g., `InterfaceGenerationError`, `InsertionError`, `UnknownPhaseError`)

## Where to Add New Code

**New Pipeline Step (e.g., new molecule insertion type):**
- Primary code: `quickice/structure_generation/` — new inserter module (e.g., `new_inserter.py`)
- Type definition: `quickice/structure_generation/types.py` — add `NewConfig` and `NewStructure` dataclasses
- Export: `quickice/__init__.py` — re-export new types
- CLI parser: `quickice/cli/parser.py` — add argument group and validation in `validate_pipeline_args()`
- CLI pipeline: `quickice/cli/pipeline.py` — add `self._new_result`, `_run_new_step()`, step in `execute()`, export dispatch in `_run_export_step()`
- CLI ITP helpers: `quickice/cli/itp_helpers.py` — add ITP copy logic in `copy_itp_files_for_structure()`
- GROMACS writer: `quickice/output/gromacs_writer.py` — add `write_new_gro_file()` and `write_new_top_file()`
- GUI panel: `quickice/gui/new_panel.py` — UI for new step
- GUI viewer: `quickice/gui/new_viewer.py` — VTK viewer
- GUI renderer: `quickice/gui/new_renderer.py` — VTK actor creation
- GUI integration: `quickice/gui/main_window.py` — add tab, connect signals, store `_current_new_result`
- GUI export: `quickice/gui/export.py` — add exporter class
- Tab index: `quickice/gui/constants.py` — add `TabIndex.NEW`
- Tests: `tests/test_e2e_new.py`, `tests/test_new_insertion.py`

**New Interface Mode:**
- Implementation: `quickice/structure_generation/modes/new_mode.py` — add `assemble_new_mode()`
- Registration: `quickice/structure_generation/interface_builder.py` — import and route to new mode in `generate_interface()`
- CLI parser: `quickice/cli/parser.py` — add mode to `--mode` choices, add mode-specific args
- GUI panel: `quickice/gui/interface_panel.py` — add mode-specific UI widgets

**New Solute/Guest Type:**
- ITP file: `quickice/data/newtype_hydrate.itp` + `quickice/data/newtype_liquid.itp`
- Types: `quickice/structure_generation/types.py` — add to `GUEST_MOLECULES` and `MOLECULE_TYPE_INFO`
- Registry: `quickice/structure_generation/moleculetype_registry.py` — may need updates
- CLI parser: `quickice/cli/parser.py` — add to `--guest` and `--solute-type` choices

**New CLI Flag:**
- Parser: `quickice/cli/parser.py` — add argument to appropriate group
- Validation: `quickice/cli/parser.py::validate_pipeline_args()` — add cross-flag validation
- Pipeline: `quickice/cli/pipeline.py` — read flag via `getattr(self.args, 'flag_name', default)`
- Entry router: `quickice/entry.py::_ROUTER_FLAGS` — add if it's a router-only flag, NOT if it's a pipeline flag

**New GUI Tab:**
- Panel: `quickice/gui/new_panel.py`
- Viewer: `quickice/gui/new_viewer.py`
- Renderer: `quickice/gui/new_renderer.py`
- Constants: `quickice/gui/constants.py` — add `TabIndex.NEW`
- MainWindow: `quickice/gui/main_window.py` — add tab widget, connect signals, add handler methods
- Signal connections: `quickice/gui/main_window.py::_setup_connections()`
- Cross-tab data: Add `_current_new_result` attribute and propagation in downstream tabs

**Utilities:**
- Shared helpers: `quickice/utils/molecule_utils.py` — molecule-level utility functions
- General utilities: `quickice/utils/__init__.py` — if adding a new utility module

## Special Directories

**`quickice/data/`:**
- Purpose: Bundled force-field ITP files, water template, custom molecule examples
- Generated: No (manually maintained)
- Committed: Yes
- Note: ITP paths resolved via `Path(quickice.__file__).parent / "data"` pattern (used in `quickice/cli/itp_helpers.py` and `quickice/output/gromacs_writer.py`)

**`sample_output/`:**
- Purpose: Reference output samples for visual verification
- Generated: Partially (some outputs are generated during testing)
- Committed: Yes

**`tests/test_output/`:**
- Purpose: Output-specific test artifacts (GRO/TOP files from test runs)
- Generated: Yes (by test runs)
- Committed: Yes (includes conftest.py for fixture setup)

**`scripts/`:**
- Purpose: Shell scripts for development, CI, and demonstration workflows
- Generated: No
- Committed: Yes
- Key scripts: `cli-examples.sh` (reference), `hydrate-interface-custom-ion.sh` (full workflow), `assemble-dist.sh` (packaging)

**`.planning/`:**
- Purpose: GSD planning artifacts (phases, milestones, debug scripts, codebase docs)
- Generated: Yes (by OpenCode GSD commands)
- Committed: Partially (debug scripts may not be committed)

---

*Structure analysis: 2026-06-15*
