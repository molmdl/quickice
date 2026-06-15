# Architecture

**Analysis Date:** 2026-06-15

## Pattern Overview

**Overall:** Dual-path application with shared core — CLI pipeline (ordered step execution) and GUI (MVVM with QThread workers), both driving the same `quickice.structure_generation` and `quickice.output` layers.

**Key Characteristics:**
- Router pattern at unified entry point: `--cli`/`--gui`/flag detection routes to CLI or GUI path
- CLI uses fail-fast ordered pipeline (source→interface→custom→solute→ion→export)
- GUI uses MVVM (MainWindow→ViewModel→Workers) with signal/slot cross-tab data flow
- Shared dataclass types (`quickice/structure_generation/types.py`) as the contract between CLI and GUI
- Duck-typing attribute propagation for IonStructure runtime attrs (both CLI and GUI paths)
- Heavy imports are lazy (inside function bodies) to avoid PySide6/VTK in headless mode
- No Qt imports in CLI pipeline module (`quickice/cli/pipeline.py`)

## Layers

**Entry/Routing Layer:**
- Purpose: Detect mode (CLI/GUI/help), route to correct path
- Location: `quickice/entry.py`, `quickice/__main__.py`, `quickice.py`
- Contains: Router logic, PySide6 availability check, display check, pipeline flag detection
- Depends on: `quickice.cli.parser` (for help/version), `quickice.main` (for CLI), `quickice.gui.main_window` (for GUI)
- Used by: `python -m quickice`, `python quickice.py`, PyInstaller binary

**CLI Layer:**
- Purpose: Argument parsing, pipeline orchestration, headless computation
- Location: `quickice/cli/`
- Contains: Argument parser, pipeline class, ITP helper functions
- Depends on: `quickice.main`, `quickice.structure_generation`, `quickice.output`, `quickice.validation`
- Used by: Entry router when `--cli` or pipeline flags detected
- Key invariant: NO Qt/PySide6/VTK imports in any `quickice/cli/` module

**GUI Layer:**
- Purpose: Interactive visual application with 3D molecular viewers
- Location: `quickice/gui/`
- Contains: MainWindow (MVVM View), ViewModel, Workers, Panels, Viewers, Renderers, Exporters
- Depends on: `quickice.structure_generation`, `quickice.output`, `quickice.phase_mapping`, PySide6, VTK
- Used by: Entry router when `--gui` explicit or default mode with display available

**Structure Generation Layer (Core):**
- Purpose: Physics-based generation of ice, hydrate, interface, solute, ion, custom molecule structures
- Location: `quickice/structure_generation/`
- Contains: Generator classes, builder functions, data types, error types, GRO/ITP parsers, overlap resolver
- Depends on: GenIce2, scipy (cKDTree), numpy
- Used by: Both CLI and GUI paths (shared core)

**Output/Export Layer:**
- Purpose: Write GROMACS .gro/.top/.itp files, PDB files, phase diagrams
- Location: `quickice/output/`
- Contains: GROMACS writers (2705-line mega-module), PDB writer, phase diagram generator, validator, orchestrator
- Depends on: `quickice.structure_generation.types`, `quickice.ranking`
- Used by: Both CLI and GUI paths

**Phase Mapping Layer:**
- Purpose: Map temperature/pressure to ice phase via IAPWS melting curves
- Location: `quickice/phase_mapping/`
- Contains: Lookup engine, melting curves, solid boundaries, triple points, ice density data
- Depends on: `iapws` (IAPWS-97 standard), bundled `ice_phases.json`
- Used by: Structure generation layer, GUI phase diagram widget

**Ranking Layer:**
- Purpose: Score and rank generated ice candidates by energy, density, diversity
- Location: `quickice/ranking/`
- Contains: Scorer functions, ranking result types
- Depends on: `quickice.structure_generation.types`
- Used by: CLI ice-only workflow, GUI Ice Generation tab

**Validation Layer:**
- Purpose: Input validation (temperature, pressure, box dimensions) as argparse type converters
- Location: `quickice/validation/`
- Contains: Validator functions used by CLI parser
- Depends on: Nothing (stdlib only)
- Used by: `quickice/cli/parser.py`

**Data Layer:**
- Purpose: Bundled force-field ITP files, GRO templates, custom molecule examples
- Location: `quickice/data/`
- Contains: `tip4p-ice.itp`, `ch4_hydrate.itp`, `thf_hydrate.itp`, `ch4_liquid.itp`, `thf_liquid.itp`, `tip4p.gro`, `custom/etoh.*`
- Depends on: Nothing
- Used by: GROMACS writer, hydrate generator, solute inserter, CLI ITP helpers

## Data Flow

**CLI Pipeline (ordered step execution, fail-fast):**

1. User invokes `python -m quickice [flags]`
2. `quickice/__main__.py` → `quickice/entry.py::main(argv)` routes to CLI or GUI
3. CLI path: `entry.main()` → `quickice/main.py::main()` → `get_arguments()` → `CLIPipeline(args).execute()`
4. Pipeline steps execute sequentially, each storing result in `self._*_result`:
   - Step 1 (Source): `generate_candidates()` or `HydrateStructureGenerator.generate()` → `self._ice_candidate` or `self._hydrate_result`
   - Step 2 (Interface): `generate_interface(candidate, config)` → `self._interface_result`
   - Step 3 (Custom): `CustomMoleculeInserter.place_random/place_custom()` → `self._custom_result`
   - Step 4 (Solute): `SoluteInserter.insert_solutes()` → `self._solute_result`
   - Step 5 (Ion): `insert_ions()` with duck-typing attribute propagation → `self._ion_result`
   - Step 6 (Export): GROMACS writer dispatch + ITP copy → output directory
5. Each step checks `self._get_source_structure(source_name)` for cross-step data flow
6. Any step returning non-zero stops execution (fail-fast)

**GUI Cross-Tab Data Flow:**

1. Ice Generation (Tab 0) → `_current_result` (RankingResult) → Interface Construction (Tab 2) via `_on_refresh_candidates()`
2. Hydrate Generation (Tab 1) → `_current_hydrate_result` → Interface Construction (Tab 2) via `_on_interface_hydrate_generate()` using `hydrate.to_candidate()`
3. Interface Construction (Tab 2) → `_current_interface_result` → Solute Panel (Tab 4), Custom Molecule Panel (Tab 3), Ion Panel (Tab 5) via `set_interface_available(True)`
4. Custom Molecule (Tab 3) → `_current_custom_molecule_result` → Solute Panel (source=Custom), Ion Panel (source=Custom Molecule)
5. Solute Insertion (Tab 4) → `_current_solute_result` → Ion Panel (Tab 5, source=Solute)
6. Ion Insertion (Tab 5) → `_current_ion_result` → GROMACS export

**Key cross-tab pattern:** MainWindow stores results as instance attributes (`_current_*_result`). Downstream tabs access these via MainWindow methods. Duck-typing sets runtime attributes on InterfaceStructure (e.g., `interface.solute_type = ...`, `interface.custom_molecule_positions = ...`).

**State Management:**
- CLI: Pipeline stores intermediate results as `self._*_result` attributes on `CLIPipeline`
- GUI: MainWindow stores results as `self._current_*_result`; ViewModel stores `_last_ranking_result` and `_last_interface_result`
- Neither uses a formal state management library; state is held in object attributes

## Key Abstractions

**Candidate:**
- Purpose: Single generated ice structure (positions + atom_names + cell + phase info)
- Examples: `quickice/structure_generation/types.py` (dataclass), generated by `IceStructureGenerator`
- Pattern: Immutable dataclass; hydrate converts via `to_candidate()`

**InterfaceStructure:**
- Purpose: Combined ice + water (+guest) positions with phase boundary markers
- Examples: `quickice/structure_generation/types.py` (dataclass), generated by `assemble_slab/assemble_pocket/assemble_piece`
- Pattern: Mutable dataclass — downstream modules (ion/solute inserters) add runtime attributes via duck-typing (e.g., `interface.solute_type`, `interface.custom_molecule_positions`)

**HydrateStructure:**
- Purpose: Hydrate lattice with water framework + guest molecules
- Examples: `quickice/structure_generation/types.py`, generated by `HydrateStructureGenerator`
- Pattern: Immutable dataclass; converts to Candidate via `to_candidate()` for interface generation

**CLIPipeline:**
- Purpose: Ordered step orchestrator for CLI workflow
- Examples: `quickice/cli/pipeline.py`
- Pattern: Command pattern — each step is a method returning exit code; `_get_source_structure()` resolves cross-step data

**MainWindow (MVVM View):**
- Purpose: Top-level GUI window, signal hub, cross-tab data router
- Examples: `quickice/gui/main_window.py` (2024 lines)
- Pattern: MVVM View — creates ViewModel, connects signals, stores results, dispatches to exporters

**MoleculetypeRegistry:**
- Purpose: Unique GROMACS moleculetype naming (distinguish hydrate CH4_H from liquid CH4_L)
- Examples: `quickice/structure_generation/moleculetype_registry.py`
- Pattern: Singleton-like registry with `_H`/`_L` suffixes

## Entry Points

**`python -m quickice`:**
- Location: `quickice/__main__.py`
- Triggers: `python -m quickice` invocation
- Responsibilities: Delegates to `quickice/entry.py::main()`

**`python quickice.py`:**
- Location: `quickice.py`
- Triggers: Direct script execution (backward compat)
- Responsibilities: Delegates to `quickice/entry.py::main()`

**`python -m quickice.gui`:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui` invocation (rare, usually via `--gui`)
- Responsibilities: Delegates to `run_app()` — launches PySide6 application

**Entry Router (`quickice/entry.py::main()`):**
- Routing priority:
  1. No args → print help, return 0
  2. `--help`/`-h` → argparse help (exits 0)
  3. `--version`/`-V` → argparse version (exits 0)
  4. `--gui` → check PySide6 (`importlib.util.find_spec`) + display (`_has_display()`) → launch GUI
  5. `--cli` → strip `--cli`, delegate to `quickice/main.py::main()`
  6. Pipeline flags detected (`_has_pipeline_flags()`) → implicit CLI mode
  7. No flags → print help, return 0

**CLI Pipeline Entry (`quickice/main.py::main()`):**
- Detects pipeline flags (interface, hydrate, custom_gro, solute_type, ion_concentration)
- If pipeline flags: delegates to `CLIPipeline(args).execute()`
- If ice-only: runs candidate generation → ranking → PDB/GROMACS export (backward compat)

## Error Handling

**Strategy:** Fail-fast with descriptive error messages + exit codes

**Patterns:**
- CLI pipeline: Each step returns `0` (success) or non-zero (failure). First failure stops execution.
- CLI parser: `argparse.ArgumentParser.error()` raises `SystemExit(2)` for argument errors
- GUI: `QMessageBox.critical()` for generation errors; `QMessageBox.warning()` for missing prerequisites
- Structure generation: Custom exception hierarchy (`StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`)
- Entry router: Returns integer exit codes (0=success, 1=error, 2=argparse errors)

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` pattern in all modules; CLI pipeline uses `logger.error()` + `report_progress()` to stderr

**Validation:** `quickice/validation/validators.py` provides argparse type converters for T, P, N, box dimensions; `InterfaceConfig.__post_init__()` validates overlap_threshold; `HydrateConfig.__post_init__()` validates lattice/guest types and ranges

**Authentication:** Not applicable (local scientific application, no auth)

**Thread Safety:**
- GUI GenerationWorker and InterfaceGenerationWorker: QObject + moveToThread pattern (correct)
- GUI HydrateWorker: Subclasses QThread directly (not migrated; still functional but not recommended pattern)
- GUI CustomMoleculeWorker: QObject + moveToThread pattern (correct)
- CLI pipeline: Single-threaded synchronous execution (no thread concerns)

**Duck-Typing Attribute Propagation:**
- Both CLI (`quickice/cli/pipeline.py::_run_ion_step()`) and GUI (`quickice/gui/main_window.py::_on_insert_ions()`) set runtime attributes on InterfaceStructure:
  - `interface.solute_type`, `interface.solute_positions`, `interface.solute_atom_names`, `interface.solute_n_molecules`, `interface.solute_molecule_indices`, `interface.solute_registry`
  - `interface.custom_molecule_positions`, `interface.custom_molecule_atom_names`, `interface.custom_molecule_count`, `interface.custom_molecule_moleculetype`, `interface.custom_gro_path`, `interface.custom_itp_path`
- These are NOT declared in the InterfaceStructure dataclass — they are set at runtime, mirroring each other across CLI and GUI paths

**Lazy Import Pattern:**
- All heavy imports (PySide6, VTK, GenIce2) are inside function bodies, never at module top level
- `entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing
- Worker `run()` methods import structure generation modules inside the thread

---

*Architecture analysis: 2026-06-15*
