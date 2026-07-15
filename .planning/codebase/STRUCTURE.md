# Codebase Structure

**Analysis Date:** 2026-07-14

## Directory Layout

```
quickice/                          # Project root
├── quickice/                      # Main package
│   ├── __init__.py                # Version (4.7.0)
│   ├── __main__.py                # python -m quickice entry → entry.main()
│   ├── entry.py                   # Unified router: --cli/--gui/flag detection (201 lines)
│   ├── main.py                    # CLI main: argparse → CLIPipeline or ice-only workflow (195 lines)
│   ├── cli/                       # CLI-specific modules (NO Qt imports)
│   │   ├── __init__.py
│   │   ├── parser.py             # argparse definition + validate_pipeline_args() (561 lines)
│   │   ├── pipeline.py           # CLIPipeline: ordered step execution (957 lines)
│   │   └── itp_helpers.py        # ITP path resolution + copy_itp_files_for_structure() (522 lines)
│   ├── gui/                       # PySide6 GUI modules
│   │   ├── __init__.py
│   │   ├── __main__.py           # python -m quickice.gui entry
│   │   ├── main_window.py        # MainWindow (2174 lines, MVVM View + signal hub)
│   │   ├── viewmodel.py          # MainViewModel (276 lines, MVVM ViewModel + worker management)
│   │   ├── view.py               # InputPanel, ProgressPanel, ViewerPanel, InfoPanel
│   │   ├── constants.py          # TabIndex IntEnum (tab order)
│   │   ├── workers.py            # GenerationWorker, InterfaceGenerationWorker (QObject) (225 lines)
│   │   ├── hydrate_worker.py     # HydrateWorker (QThread subclass — NOT migrated, accepted design)
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
│   │   ├── __init__.py           # Re-exports all key types and generators (112 lines)
│   │   ├── types.py              # All dataclasses + detect_atoms_per_molecule() + constants (1267 lines)
│   │   ├── errors.py             # Exception hierarchy
│   │   ├── generator.py          # IceStructureGenerator (GenIce2 wrapper)
│   │   ├── hydrate_generator.py  # HydrateStructureGenerator (GenIce2 wrapper) (835 lines, thread-safe)
│   │   ├── interface_builder.py  # generate_interface() + validate_interface_config() (375 lines)
│   │   ├── custom_guest_bridge.py # Phase 40: synthetic GenIce2 Molecule plugin for custom guests (394 lines)
│   │   ├── modes/                # Interface assembly modes
│   │   │   ├── __init__.py
│   │   │   ├── slab.py           # Slab mode (ice|water|ice sandwich)
│   │   │   ├── pocket.py         # Pocket mode (spherical/cubic cavity)
│   │   │   └── piece.py          # Piece mode (crystal in water)
│   │   ├── ion_inserter.py       # IonInserter + insert_ions() (649 lines, conditional cKDTree rebuild)
│   │   ├── solute_inserter.py    # SoluteInserter (999 lines, no input mutation V-17, conditional cKDTree)
│   │   ├── custom_molecule_inserter.py # CustomMoleculeInserter + InsertionError (968 lines)
│   │   ├── water_filler.py       # Water placement utilities
│   │   ├── overlap_resolver.py   # Overlap detection/removal
│   │   ├── gro_parser.py         # GRO file parser
│   │   ├── itp_parser.py         # ITP file parser
│   │   ├── molecule_validator.py # Molecule validation
│   │   ├── moleculetype_registry.py # Unique GROMACS moleculetype naming (_H/_L suffixes) (166 lines)
│   │   ├── gromacs_ion_export.py # Ion ITP file generator
│   │   ├── mapper.py             # Phase→GenIce lattice name mapping
│   │   └── cell_utils.py        # Cell orthogonality check
│   ├── output/                   # File output modules (shared CLI+GUI)
│   │   ├── __init__.py           # Re-exports
│   │   ├── types.py              # OutputResult dataclass
│   │   ├── orchestrator.py       # output_ranked_candidates() coordinator (141 lines)
│   │   ├── gromacs_writer.py     # All GROMACS .gro/.top/.itp writers (4067 lines)
│   │   ├── pdb_writer.py         # PDB file writer with CRYST1 records
│   │   ├── validator.py          # Space group validation, overlap checking
│   │   ├── phase_diagram.py      # Phase diagram PNG generation
│   │   └── guest_info.py         # _build_custom_guest_info() for custom-guest ITP metadata
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
│   │   └── validators.py         # argparse type converters (206 lines): T, P, N, box dims, concentration, occupancy
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
│   ├── test_cli/                 # CLI-specific tests subpackage
│   ├── test_cli_pipeline.py      # CLIPipeline unit tests
│   ├── test_structure_generation.py  # Ice generation tests
│   ├── test_e2e_*.py             # End-to-end workflow chain tests
│   ├── test_tip4p_ice_lj_values.py   # TIP4P-ICE LJ constant verification (288 lines)
│   ├── test_pbc_wrapping.py      # PBC wrapping tests (224 lines, AN-03)
│   ├── test_scancode_bugs_solute.py   # Solute inserter bug fix tests (174 lines, V-17)
│   ├── test_e2e_gmx_param_validation.py # GROMACS param validation E2E (311 lines)
│   ├── test_e2e_gmx_validation.py      # GROMACS validation E2E (1231 lines)
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
- Key files: `quickice/cli/pipeline.py` (957 lines, CLIPipeline), `quickice/cli/parser.py` (561 lines, argparse), `quickice/cli/itp_helpers.py` (522 lines, ITP file management)
- Constraint: NO Qt/PySide6/VTK imports allowed in this directory

**`quickice/gui/`:**
- Purpose: PySide6-based graphical interface with VTK 3D viewers
- Contains: MainWindow (MVVM View), ViewModel, Workers, Panels, Viewers, Renderers, Exporters
- Key files: `quickice/gui/main_window.py` (2174 lines, signal hub + cross-tab data flow), `quickice/gui/viewmodel.py` (276 lines, MVVM ViewModel), `quickice/gui/constants.py` (TabIndex enum defining tab order)

**`quickice/structure_generation/`:**
- Purpose: Physics engine — all structure generation and insertion logic
- Contains: Generator classes, builder functions, data types, error hierarchy, parsers, overlap resolver, custom guest bridge
- Key files: `quickice/structure_generation/types.py` (1267 lines, all dataclass contracts + constants + `detect_atoms_per_molecule()`), `quickice/structure_generation/interface_builder.py` (375 lines), `quickice/structure_generation/hydrate_generator.py` (835 lines, thread-safe GenIce2 loading), `quickice/structure_generation/solute_inserter.py` (999 lines), `quickice/structure_generation/ion_inserter.py` (649 lines), `quickice/structure_generation/custom_molecule_inserter.py` (968 lines), `quickice/structure_generation/custom_guest_bridge.py` (394 lines, Phase 40 custom-guest GenIce2 plugin), `quickice/structure_generation/moleculetype_registry.py` (166 lines)
- Shared: Used by both CLI and GUI paths — no UI or CLI-specific logic here
- Subpackage: `quickice/structure_generation/modes/` holds the three interface assembly modes (`slab.py`, `pocket.py`, `piece.py`)

**`quickice/output/`:**
- Purpose: File output — GROMACS, PDB, phase diagram generation
- Contains: Writer functions, orchestrator, validator, guest_info builder
- Key files: `quickice/output/gromacs_writer.py` (4067 lines — largest file in codebase, all GROMACS writers, `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` constants, PBC wrapping, `validate_gro_residue_name()`)

**`quickice/validation/`:**
- Purpose: Input validators as argparse type converters
- Contains: Temperature, pressure, molecule count, box dimension, concentration range, occupancy range validators
- Key files: `quickice/validation/validators.py` (206 lines)

**`quickice/data/`:**
- Purpose: Bundled force-field ITP files, water template, custom molecule examples
- Contains: TIP4P-ICE, CH4/THF hydrate and liquid ITPs, tip4p.gro template, etoh example
- Key files: `quickice/data/tip4p-ice.itp`, `quickice/data/tip4p.gro`

## Key File Locations

**Entry Points:**
- `quickice/__main__.py`: Primary entry (`python -m quickice`) → `entry.main()`
- `quickice/entry.py`: Unified router (201 lines) — add routing logic HERE, not in `__main__.py` or `quickice.py`
- `quickice/main.py`: CLI main (195 lines) — argparse → pipeline or ice-only
- `quickice.py`: Backward compat script → `entry.main()`
- `quickice/gui/__main__.py`: GUI-only entry (`python -m quickice.gui`)

**Configuration:**
- `quickice/__init__.py`: Version string (`__version__ = "4.7.0"`)
- `quickice-gui.spec`: PyInstaller spec (entry point: `quickice/__main__.py`)
- `environment.yml`: Conda environment with PySide6
- `environment-build.yml`: Build-only environment
- `requirements-dev.txt`: Dev/test dependencies
- `conftest.py`: Project-level pytest markers

**Core Logic:**
- `quickice/structure_generation/types.py`: All shared dataclasses (Candidate, InterfaceStructure, HydrateStructure, IonStructure, SoluteStructure, CustomMoleculeStructure, all Config types) + `detect_atoms_per_molecule()` + `WATER_VOLUME_NM3`/`WATER_ATOMS_PER_MOLECULE` constants + `HYDRATE_LATTICES`/`GUEST_MOLECULES` tables
- `quickice/cli/pipeline.py`: CLIPipeline — ordered step execution with fail-fast; catches `(OSError, ValueError)` in export; atom count assertion for hydrate wrapper (EH-02)
- `quickice/cli/parser.py`: argparse definition with v4.5+ pipeline flags; `validate_pipeline_args()` cross-flag validation
- `quickice/cli/itp_helpers.py`: ITP file resolution and copy logic
- `quickice/structure_generation/interface_builder.py`: `generate_interface()` mode router → `modes/{slab,pocket,piece}.py::assemble_*()`
- `quickice/structure_generation/generator.py`: `IceStructureGenerator` (GenIce2 wrapper)
- `quickice/structure_generation/hydrate_generator.py`: `HydrateStructureGenerator` (thread-safe GenIce2 loading via `_genice_lock`)
- `quickice/structure_generation/ion_inserter.py`: `IonInserter` + `insert_ions()` (conditional cKDTree rebuild; `AVOGADRO` constant defined here — import from here, never duplicate)
- `quickice/structure_generation/solute_inserter.py`: `SoluteInserter` (999 lines, no input structure mutation V-17, conditional cKDTree rebuild)
- `quickice/structure_generation/custom_molecule_inserter.py`: `CustomMoleculeInserter` + `InsertionError`
- `quickice/structure_generation/custom_guest_bridge.py`: Phase 40 — synthetic GenIce2 `Molecule` plugin from user GRO for custom guests in hydrate cages
- `quickice/structure_generation/moleculetype_registry.py`: `MoleculetypeRegistry` — `_H`/`_L`/custom moleculetype naming
- `quickice/output/gromacs_writer.py`: All GROMACS .gro/.top/.itp writer functions (4067 lines); `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` constants (lines 56-57, single source of truth for LJ params); PBC wrapping for solute/custom positions (AN-03); `validate_gro_residue_name()`
- `quickice/gui/constants.py`: `TabIndex` IntEnum defining tab order (ICE=0, HYDRATE=1, INTERFACE=2, CUSTOM=3, SOLUTE=4, ION=5)

**Validation:**
- `quickice/validation/validators.py`: Argparse type converters — `validate_temperature()`, `validate_pressure()`, `validate_nmolecules()`, `validate_positive_float()`, `validate_box_dimension()`, `validate_concentration_range()` [0.0, 5.0], `validate_occupancy_range()` [0.0, 100.0]

**Testing:**
- `tests/test_cli_pipeline.py`: CLIPipeline unit tests
- `tests/test_cli_integration.py`: CLI integration tests
- `tests/test_entry_point.py`: Entry router tests
- `tests/test_e2e_workflow_chains.py`: End-to-end workflow chain tests
- `tests/test_e2e_*.py`: Per-feature E2E tests (15+ files)
- `tests/test_tip4p_ice_lj_values.py`: TIP4P-ICE LJ constant verification (288 lines)
- `tests/test_pbc_wrapping.py`: PBC wrapping tests (224 lines, AN-03 fix)
- `tests/test_scancode_bugs_solute.py`: Solute inserter bug fix tests (174 lines, V-17)
- `tests/test_e2e_gmx_param_validation.py`: GROMACS parameter validation E2E (311 lines)
- `tests/test_e2e_gmx_validation.py`: GROMACS validation E2E (1231 lines)
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
- Test files: `test_*.py` (unit), `test_e2e_*.py` (e2e), `test_scancode_bugs_*.py` (regression)
- Non-collected test helpers: NO `test_` prefix (e.g., `e2e_export_helpers.py`)
- Shell scripts: `kebab-case.sh` (e.g., `cli-examples.sh`, `hydrate-interface-custom-ion.sh`)
- Data files: `lowercase.itp`/`.gro` (e.g., `tip4p-ice.itp`, `ch4_hydrate.itp`)

**Directories:**
- Package modules: `snake_case/` (e.g., `structure_generation/`, `phase_mapping/`)
- Mode subdirectories: `modes/` under `structure_generation/`
- Data subdirectories: `data/`, `data/custom/`, `data/examples/`
- Test subdirectories: `tests/test_output/`, `tests/test_cli/`

**Dataclass types:**
- Config dataclasses: `*Config` (e.g., `InterfaceConfig`, `HydrateConfig`, `SoluteConfig`, `IonConfig`, `CustomMoleculeConfig`)
- Result dataclasses: `*Structure` or `*Result` (e.g., `InterfaceStructure`, `HydrateStructure`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`, `GenerationResult`, `RankingResult`, `OutputResult`)
- Error classes: `*Error` (e.g., `InterfaceGenerationError`, `InsertionError`, `UnknownPhaseError`)

**Shared Constants:**
- Module-level constants in UPPERCASE_SNAKE_CASE (e.g., `TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON`, `WATER_ATOMS_PER_MOLECULE`, `WATER_VOLUME_NM3`, `AVOGADRO`)
- Defined once at module top level and referenced by all consumers (single source of truth pattern)
- Never hardcode these values — import from the defining module

## Where to Add New Code

**New Pipeline Step (e.g., new molecule insertion type):**
- Primary code: `quickice/structure_generation/` — new inserter module (e.g., `new_inserter.py`)
- Type definition: `quickice/structure_generation/types.py` — add `NewConfig` and `NewStructure` dataclasses
- Export: `quickice/structure_generation/__init__.py` — re-export new types
- CLI parser: `quickice/cli/parser.py` — add argument group and validation in `validate_pipeline_args()`
- CLI pipeline: `quickice/cli/pipeline.py` — add `self._new_result`, `_run_new_step()`, step in `execute()`, export dispatch in `_run_export_step()`
- CLI ITP helpers: `quickice/cli/itp_helpers.py` — add ITP copy logic in `copy_itp_files_for_structure()`
- GROMACS writer: `quickice/output/gromacs_writer.py` — add `write_new_gro_file()` and `write_new_top_file()` (use `TIP4P_ICE_OW_SIGMA`/`TIP4P_ICE_OW_EPSILON` constants for OW atomtypes; `comb-rule=2` — never comb-rule=1)
- GUI panel: `quickice/gui/new_panel.py` — UI for new step
- GUI viewer: `quickice/gui/new_viewer.py` — VTK viewer
- GUI renderer: `quickice/gui/new_renderer.py` — VTK actor creation
- GUI integration: `quickice/gui/main_window.py` — add tab, connect signals in `_setup_connections()`, store `_current_new_result`, add handler methods
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
- Registry: `quickice/structure_generation/moleculetype_registry.py` — may need updates (use `_H`/`_L` suffix registration, never hardcode names)
- CLI parser: `quickice/cli/parser.py` — add to `--guest` and `--solute-type` choices

**New CLI Flag:**
- Parser: `quickice/cli/parser.py` — add argument to appropriate group
- Validation: `quickice/cli/parser.py::validate_pipeline_args()` — add cross-flag validation; for range-constrained values, add a `validate_*` function in `quickice/validation/validators.py`
- Pipeline: `quickice/cli/pipeline.py` — read flag via `getattr(self.args, 'flag_name', default)`
- Entry router: `quickice/entry.py::_ROUTER_FLAGS` — add ONLY if it's a router-only flag (NOT if it's a pipeline computation flag)

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

**New Shared Constants:**
- Define at module top level in UPPERCASE_SNAKE_CASE in the appropriate module (e.g., force-field params in `quickice/output/gromacs_writer.py`, water constants in `quickice/structure_generation/types.py`, `AVOGADRO` in `quickice/structure_generation/ion_inserter.py`)
- Reference from all consumer functions — single source of truth pattern
- Add verification tests (see `tests/test_tip4p_ice_lj_values.py` as example)

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

**`tests/test_cli/`:**
- Purpose: CLI-specific test subpackage
- Generated: No
- Committed: Yes

**`scripts/`:**
- Purpose: Shell scripts for development, CI, and demonstration workflows
- Generated: No
- Committed: Yes
- Key scripts: `cli-examples.sh` (reference), `hydrate-interface-custom-ion.sh` (full workflow), `assemble-dist.sh` (packaging)

**`.planning/`:**
- Purpose: GSD planning artifacts (phases, milestones, debug scripts, codebase docs)
- Generated: Yes (by OpenCode GSD commands)
- Committed: Partially (debug scripts may not be committed)

**`tmp/`:**
- Purpose: Scratch directory for transient GROMACS validation artifacts (e.g., `tmp/e2e-gmx-validation/`)
- Generated: Yes (by E2E test runs)
- Committed: No (gitignored)

---

*Structure analysis: 2026-07-14*
