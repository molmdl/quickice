# Architecture

**Analysis Date:** 2026-07-14

## Pattern Overview

**Overall:** Dual-path application with shared core — CLI pipeline (ordered step execution) and GUI (MVVM with QThread workers), both driving the same `quickice.structure_generation` and `quickice.output` layers.

**Key Characteristics:**
- Router pattern at unified entry point: `--cli`/`--gui`/flag detection routes to CLI or GUI path
- CLI uses fail-fast ordered pipeline (source → interface → custom → solute → ion → export)
- GUI uses MVVM (MainWindow → ViewModel → Workers) with signal/slot cross-tab data flow
- Shared dataclass types (`quickice/structure_generation/types.py`) as the contract between CLI and GUI
- Duck-typing attribute propagation for runtime attrs on `InterfaceStructure` (both CLI and GUI paths) — documented as accepted design decision (CP-01), NOT a bug
- Heavy imports are lazy (inside function bodies) to avoid PySide6/VTK in headless mode
- No Qt imports in CLI pipeline module (`quickice/cli/pipeline.py`)
- Inserters all return NEW structure objects (never mutate inputs — V-17 fix); cKDTree rebuilt conditionally only after successful placement
- Module-level constants are the single source of truth for force-field parameters (never hardcode duplicates)

## Layers

**Entry/Routing Layer:**
- Purpose: Detect mode (CLI/GUI/help), route to correct path
- Location: `quickice/entry.py`, `quickice/__main__.py`, `quickice.py`
- Contains: Router logic, PySide6 availability check, display check, pipeline flag detection
- Depends on: `quickice.cli.parser` (for help/version), `quickice.main` (for CLI), `quickice.gui.main_window` (for GUI)
- Used by: `python -m quickice`, `python quickice.py`, PyInstaller binary
- Key invariant: All routing logic lives in `quickice/entry.py::main()` — NOT in `__main__.py` or `quickice.py` (those just delegate)

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
- Key invariant: `HydrateWorker` subclasses `QThread` directly (NOT migrated to QObject+moveToThread) — this is an accepted design decision, do NOT "fix" it

**Structure Generation Layer (Core):**
- Purpose: Physics-based generation of ice, hydrate, interface, solute, ion, custom molecule structures
- Location: `quickice/structure_generation/`
- Contains: Generator classes, builder functions, data types, error types, GRO/ITP parsers, overlap resolver, custom guest bridge
- Depends on: GenIce2 (lazy imported), scipy (`cKDTree`), numpy
- Used by: Both CLI and GUI paths (shared core)
- Key invariants:
  - `detect_atoms_per_molecule()` is the single source for atom counting (deduplicated from gromacs_writer.py into types.py — V-07)
  - All inserters return NEW structure objects, never mutate inputs (V-17)
  - cKDTree initialized as `None`, rebuilt ONLY after successful placement (not on rejection)

**Output/Export Layer:**
- Purpose: Write GROMACS .gro/.top/.itp files, PDB files, phase diagrams
- Location: `quickice/output/`
- Contains: GROMACS writers (4067-line mega-module), PDB writer, phase diagram generator, validator, orchestrator, guest_info builder
- Depends on: `quickice.structure_generation.types`, `quickice.ranking`, `quickice.utils.molecule_utils`
- Used by: Both CLI and GUI paths
- Key: `TIP4P_ICE_OW_SIGMA` and `TIP4P_ICE_OW_EPSILON` constants (lines 56-57 of `quickice/output/gromacs_writer.py`) are the single source of truth for TIP4P-ICE LJ parameters; `comb-rule=2` (Lorentz-Berthelot) used in ALL `.top` files — AMBER/GAFF2 convention, never use comb-rule=1

**Phase Mapping Layer:**
- Purpose: Map temperature/pressure to ice phase via IAPWS melting curves
- Location: `quickice/phase_mapping/`
- Contains: Lookup engine, melting curves, solid boundaries, triple points, ice density data
- Depends on: `iapws` (IAPWS-97 standard), bundled `quickice/phase_mapping/data/ice_phases.json`
- Used by: Structure generation layer, GUI phase diagram widget

**Ranking Layer:**
- Purpose: Score and rank generated ice candidates by energy, density, diversity
- Location: `quickice/ranking/`
- Contains: Scorer functions, ranking result types
- Depends on: `quickice.structure_generation.types`
- Used by: CLI ice-only workflow, GUI Ice Generation tab

**Validation Layer:**
- Purpose: Input validation (temperature, pressure, box dimensions, concentration, occupancy) as argparse type converters
- Location: `quickice/validation/`
- Contains: Validator functions used by CLI parser
- Depends on: Nothing (stdlib only)
- Used by: `quickice/cli/parser.py`
- Key: `validate_concentration_range()` enforces [0.0, 5.0] mol/L; `validate_occupancy_range()` enforces [0.0, 100.0]%

**Utils Layer:**
- Purpose: Shared molecule-level helpers
- Location: `quickice/utils/molecule_utils.py`
- Contains: `count_guest_atoms()` and other molecule helpers
- Depends on: `quickice.structure_generation.types`
- Used by: `quickice/output/gromacs_writer.py`

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
4. `validate_pipeline_args()` validates cross-flag dependencies AND range constraints (concentration 0–5 mol/L, occupancy 0–100%); `pipeline.py::_run_custom_step()` validates file extensions for `--custom-gro` (.gro) and `--custom-itp` (.itp) and rejects directory traversal outside working directory (SEC-02/SEC-04)
5. Pipeline steps execute sequentially, each storing result in `self._*_result`:
   - Step 1 (Source): `generate_candidates()` or `HydrateStructureGenerator.generate()` → `self._ice_candidate` or `self._hydrate_result`
   - Step 2 (Interface): `generate_interface(candidate, config)` → `self._interface_result`
   - Step 3 (Custom): `CustomMoleculeInserter.place_random()`/`place_custom()` → `self._custom_result`
   - Step 4 (Solute): `SoluteInserter.insert_solutes()` → `self._solute_result`
   - Step 5 (Ion): `insert_ions()` with duck-typing attribute propagation → `self._ion_result`
   - Step 6 (Export): GROMACS writer dispatch + ITP copy → output directory
6. Each step checks `self._get_source_structure(source_name)` for cross-step data flow
7. Any step returning non-zero stops execution (fail-fast)
8. Export step catches `(OSError, ValueError)` — NOT bare `Exception`
9. Auto-chaining: `--solute-source`/`--ion-source` default to 'interface' but auto-upgrade to the most downstream available result (solute > custom > interface) to prevent silent data loss

**GUI Cross-Tab Data Flow:**

Tab order (defined in `quickice/gui/constants.py::TabIndex`):
- Tab 0 (ICE): Ice Generation
- Tab 1 (HYDRATE): Hydrate Generation
- Tab 2 (INTERFACE): Interface Construction
- Tab 3 (CUSTOM): Custom Molecule
- Tab 4 (SOLUTE): Solute Insertion
- Tab 5 (ION): Ion Insertion

Flow:
1. Ice Generation (Tab 0) → `_current_result` (RankingResult) → Interface Construction (Tab 2) via `_on_refresh_candidates()`
2. Hydrate Generation (Tab 1) → `_current_hydrate_result` → Interface Construction (Tab 2) via `_on_interface_hydrate_generate()` using `hydrate.to_candidate()`
3. Interface Construction (Tab 2) → `_current_interface_result` → Custom Molecule Panel (Tab 3), Solute Panel (Tab 4), Ion Panel (Tab 5) via `set_interface_available(True)`
4. Custom Molecule (Tab 3) → `_current_custom_molecule_result` → Solute Panel (source=Custom Molecule), Ion Panel (source=Custom Molecule)
5. Solute Insertion (Tab 4) → `_current_solute_result` → Ion Panel (Tab 5, source=Solute)
6. Ion Insertion (Tab 5) → `_current_ion_result` → GROMACS export

**Key cross-tab pattern:** MainWindow stores results as instance attributes (`_current_*_result`). Downstream tabs access these via MainWindow methods. Duck-typing sets runtime attributes on `InterfaceStructure` (e.g., `interface.solute_type = ...`, `interface.custom_molecule_positions = ...`).

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
- Examples: `quickice/structure_generation/types.py` (dataclass), generated by `assemble_slab`/`assemble_pocket`/`assemble_piece`
- Pattern: Mutable dataclass — downstream modules (ion/solute inserters) add runtime attributes via duck-typing (e.g., `interface.solute_type`, `interface.custom_molecule_positions`). This is a documented design decision (CP-01) — runtime attributes are set by both CLI and GUI paths mirroring each other
- Ordering: `positions[0:ice_atom_count]` = ice, `positions[ice_atom_count:ice_atom_count+water_atom_count]` = water, `positions[ice_atom_count+water_atom_count:]` = guests

**HydrateStructure:**
- Purpose: Hydrate lattice with water framework + guest molecules
- Examples: `quickice/structure_generation/types.py` (dataclass), generated by `HydrateStructureGenerator`
- Pattern: Immutable dataclass; converts to Candidate via `to_candidate()` for interface generation

**CLIPipeline:**
- Purpose: Ordered step orchestrator for CLI workflow
- Examples: `quickice/cli/pipeline.py`
- Pattern: Command pattern — each step is a method returning exit code; `_get_source_structure()` resolves cross-step data; auto-chaining upgrades default source to most downstream result

**MainWindow (MVVM View):**
- Purpose: Top-level GUI window, signal hub, cross-tab data router
- Examples: `quickice/gui/main_window.py` (2174 lines)
- Pattern: MVVM View — creates ViewModel, connects signals, stores results, dispatches to exporters

**MoleculetypeRegistry:**
- Purpose: Unique GROMACS moleculetype naming (distinguish hydrate CH4_H from liquid CH4_L)
- Examples: `quickice/structure_generation/moleculetype_registry.py`
- Pattern: Registry with `_H` suffix for hydrate guests, `_L` suffix for liquid solutes; `register_custom_molecule()` for user molecules. Never hardcode moleculetype names — always go through the registry

**CustomGuestBridge:**
- Purpose: Build a synthetic GenIce2 `Molecule` plugin module from a user-provided GRO file so GenIce2 can place custom guests in hydrate cages (Phase 40)
- Examples: `quickice/structure_generation/custom_guest_bridge.py` (394 lines)
- Pattern: Context manager that injects/cleans up a module in `sys.modules`; `sites_` MUST be centroid-centered; `residue_name` ≤3 chars so the `_H` suffix fits GRO's 5-char limit

**Shared Constants Pattern:**
- Purpose: Single source of truth for force-field parameters used across multiple writer functions
- Examples:
  - `TIP4P_ICE_OW_SIGMA = 3.16680e-1` and `TIP4P_ICE_OW_EPSILON = 8.82110e-1` in `quickice/output/gromacs_writer.py` (lines 56-57)
  - `WATER_VOLUME_NM3 = 0.0299` and `WATER_ATOMS_PER_MOLECULE = 4` in `quickice/structure_generation/types.py`
  - `AVOGADRO = 6.02214076e23` in `quickice/structure_generation/ion_inserter.py` (import from there, never duplicate)
- Pattern: Module-level constants referenced by all consumers; never hardcode these values elsewhere

**detect_atoms_per_molecule():**
- Purpose: Detect atoms per molecule from atom names (3 for GenIce ice, 4 for TIP4P)
- Examples: `quickice/structure_generation/types.py` — deduplicated from gromacs_writer.py (V-07)
- Pattern: Standalone function imported by all three mode modules (`slab.py`, `pocket.py`, `piece.py`)

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
  4. `--gui` → check PySide6 (`importlib.util.find_spec('PySide6')`) + display (`_has_display()`) → launch GUI via `run_app()`
  5. `--cli` → strip `--cli`, delegate to `quickice/main.py::main()`
  6. Pipeline flags detected (`_has_pipeline_flags()`) → implicit CLI mode
  7. No flags → print help, return 0
- Returns: exit code (0=success, 1=error, 2=argparse errors)

**CLI Pipeline Entry (`quickice/main.py::main()`):**
- Detects pipeline flags (interface, hydrate, custom_gro, solute_type, ion_concentration)
- If pipeline flags: delegates to `CLIPipeline(args).execute()`
- If ice-only: runs candidate generation → ranking → PDB/GROMACS export (backward compat)

## Error Handling

**Strategy:** Fail-fast with descriptive error messages + exit codes

**Patterns:**
- CLI pipeline: Each step returns `0` (success) or non-zero (failure). First failure stops execution.
- CLI pipeline step methods catch `(ValueError, OSError)` or more specific exceptions — NOT bare `Exception`. Export step catches `(OSError, ValueError)` (line 952 of `pipeline.py`).
- CLI parser: `argparse.ArgumentParser.error()` raises `SystemExit(2)` for argument errors
- CLI custom step: Catches `(FileNotFoundError, ValueError, InsertionError)` separately with step-specific messages
- CLI solute step: Catches `(ValueError, FileNotFoundError)` separately
- CLI ion step: Catches `ValueError`
- GUI: `QMessageBox.critical()` for generation errors; `QMessageBox.warning()` for missing prerequisites
- Structure generation: Custom exception hierarchy (`StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`)
- Entry router: Returns integer exit codes (0=success, 1=error, 2=argparse errors)
- Hydrate wrapper in export step: Assertion on atom count (`water_atom_count + guest_atom_count == len(hydrate.positions)`) — catches bugs where water_count × 4 doesn't match actual positions (EH-02, `pipeline.py` line 901)

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` pattern in all modules; CLI pipeline uses `logger.error()` + `report_progress()` to stderr (prefixed `[PROGRESS]`)

**Validation:** `quickice/validation/validators.py` (206 lines) provides argparse type converters for T, P, N, box dimensions, concentration range [0.0, 5.0], and occupancy range [0.0, 100.0]; `quickice/cli/parser.py::validate_pipeline_args()` provides cross-flag validation; `quickice/cli/pipeline.py::_run_custom_step()` validates file extensions for `--custom-gro` (.gro) and `--custom-itp` (.itp) (SEC-02) and rejects directory traversal outside cwd (SEC-04); CSV row limit `MAX_CSV_ROWS = 10000` (SEC-05); `InterfaceConfig.__post_init__()` validates overlap_threshold; `HydrateConfig.__post_init__()` validates lattice/guest types and ranges

**Authentication:** Not applicable (local scientific application, no auth)

**Thread Safety:**
- GUI GenerationWorker and InterfaceGenerationWorker: QObject + moveToThread pattern (correct)
- GUI HydrateWorker: Subclasses QThread directly (NOT migrated; accepted design decision — do NOT "fix")
- GUI CustomMoleculeWorker: QObject + moveToThread pattern (correct)
- CLI pipeline: Single-threaded synchronous execution (no thread concerns)
- HydrateStructureGenerator: `_genice_lock` (threading.Lock) guards lazy GenIce2 loading for thread-safe v4.7 custom-guest registration
- cKDTree conditional rebuild: Both `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py` rebuild the tree ONLY after successful placement (not on rejection) to avoid O(N×A) tree rebuilds

**Duck-Typing Attribute Propagation:**
- Both CLI (`quickice/cli/pipeline.py::_run_ion_step()`) and GUI (`quickice/gui/main_window.py::_on_insert_ions()`) set runtime attributes on `InterfaceStructure`:
  - `interface.solute_type`, `interface.solute_positions`, `interface.solute_atom_names`, `interface.solute_n_molecules`, `interface.solute_molecule_indices`, `interface.solute_registry`
  - `interface.custom_molecule_positions`, `interface.custom_molecule_atom_names`, `interface.custom_molecule_count`, `interface.custom_molecule_moleculetype`, `interface.custom_gro_path`, `interface.custom_itp_path`
- These are NOT declared in the InterfaceStructure dataclass — they are set at runtime, mirroring each other across CLI and GUI paths
- Documented as CP-01 concern — accepted as design decision, NOT a bug to fix

**Lazy Import Pattern:**
- All heavy imports (PySide6, VTK, GenIce2) are inside function bodies, never at module top level
- `quickice/entry.py` uses `importlib.util.find_spec('PySide6')` to check availability without importing
- Worker `run()` methods import structure generation modules inside the thread
- CLI pipeline step methods lazy-import their structure-generation dependencies inside the method body (keeps `pipeline.py` importable without the full structure_generation stack loaded)

**PBC Wrapping:**
- `quickice/output/gromacs_writer.py::write_interface_gro_file()` wraps solute and custom molecule positions into the PBC box (AN-03 fix): `iface.solute_positions % np.diag(iface.cell)` and `iface.custom_molecule_positions % np.diag(iface.cell)`
- `quickice/output/gromacs_writer.py::write_ion_gro_file()` similarly wraps solute and custom molecule positions (AN-03 fix)
- Two wrapping strategies: `wrap_positions_into_box()` (atom-by-atom, may split molecules) and `wrap_molecules_into_box()` (molecule-aware, keeps molecules intact) — molecule-aware wrapping used when `molecule_index` is available

**GRO Residue Name Validation:**
- `quickice/output/gromacs_writer.py::validate_gro_residue_name()` enforces the 5-char GRO format limit at write time (raises `ValueError` on overflow); custom molecule residue names ≤3 chars recommended so the `_H`/`_L` suffixes fit

---

*Architecture analysis: 2026-07-14*
