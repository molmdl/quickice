# Architecture

**Analysis Date:** 2026-04-10

## Pattern Overview

**Overall:** Pipeline with MVVM GUI layer

**Key Characteristics:**
- Sequential data pipeline for CLI: Input → Phase Mapping → Structure Generation → Ranking → Output
- MVVM (Model-View-ViewModel) for GUI: View (PySide6 widgets) → ViewModel (signal/slot bridge) → Model (pipeline modules)
- Background threading for GUI: QThread worker-object pattern keeps UI responsive during generation
- Shared domain model: Both CLI and GUI use the same `quickice/` package modules
- Dataclass-based type system: `Candidate`, `GenerationResult`, `RankedCandidate`, `RankingResult`, `InterfaceConfig`, `InterfaceStructure`, `OutputResult`

## Layers

**CLI Entry Layer:**
- Purpose: Parse command-line arguments and orchestrate the full pipeline
- Location: `quickice.py`, `quickice/main.py`, `quickice/cli/parser.py`
- Contains: CLI entry point, argparse parser, validation type converters
- Depends on: `quickice.validation`, `quickice.phase_mapping`, `quickice.structure_generation`, `quickice.ranking`, `quickice.output`
- Used by: End user via `python quickice.py`

**GUI Entry Layer:**
- Purpose: Provide interactive graphical interface with 3D visualization
- Location: `quickice/gui/`
- Contains: PySide6 widgets, VTK 3D viewers, matplotlib diagram, ViewModel, background workers
- Depends on: All pipeline modules, PySide6, VTK, matplotlib
- Used by: End user via `python -m quickice.gui` or PyInstaller binary

**Phase Mapping Layer (Domain):**
- Purpose: Determine which ice polymorph is stable at given T,P conditions
- Location: `quickice/phase_mapping/`
- Contains: Curve-based boundary evaluation, IAPWS melting curve equations, triple point data, solid-solid boundary interpolation
- Depends on: `numpy`, `iapws` (for IAPWS97 saturation curve in diagram)
- Used by: `quickice/main.py`, `quickice/gui/workers.py`, `quickice/output/phase_diagram.py`

**Structure Generation Layer (Domain):**
- Purpose: Generate ice crystal structure candidates using GenIce2
- Location: `quickice/structure_generation/`
- Contains: GenIce2 wrapper, phase-to-lattice mapping, supercell calculation, interface builder (slab/pocket/piece modes), water filling, overlap resolution
- Depends on: `genice2`, `numpy`, `quickice.structure_generation.mapper`, `quickice.structure_generation.types`
- Used by: `quickice/main.py`, `quickice/gui/workers.py`

**Ranking Layer (Domain):**
- Purpose: Score and rank ice structure candidates by quality metrics
- Location: `quickice/ranking/`
- Contains: Energy scoring (O-O distance heuristic), density scoring, diversity scoring, min-max normalization
- Depends on: `numpy`, `scipy.spatial.cKDTree`, `quickice.structure_generation.types`
- Used by: `quickice/main.py`, `quickice/gui/workers.py`

**Output Layer:**
- Purpose: Write results to files (PDB, GRO, TOP, phase diagram images)
- Location: `quickice/output/`
- Contains: PDB writer, GROMACS writer (GRO/TOP/ITP), structure validator (spglib), phase diagram generator (matplotlib), orchestrator
- Depends on: `numpy`, `spglib`, `matplotlib`, `shapely`, `quickice.ranking.types`, `quickice.phase_mapping`
- Used by: `quickice/main.py` (via orchestrator)

**Validation Layer (Cross-Cutting):**
- Purpose: Input validation for CLI and GUI
- Location: `quickice/validation/validators.py` (CLI), `quickice/gui/validators.py` (GUI)
- Contains: Temperature/pressure/molecule count validators; GUI validators return `(bool, str)` tuples, CLI validators raise `ArgumentTypeError`
- Depends on: `argparse` (CLI only)
- Used by: `quickice/cli/parser.py`, `quickice/gui/view.py`, `quickice/gui/interface_panel.py`

## Data Flow

**CLI Pipeline:**

1. User runs `python quickice.py --temperature 300 --pressure 100 --nmolecules 96`
2. `quickice.py` calls `quickice.main.main()`
3. `main()` calls `get_arguments()` → parses and validates CLI args via `quickice/cli/parser.py`
4. `main()` calls `lookup_phase(T, P)` → returns `phase_info` dict with `phase_id`, `phase_name`, `density`
5. `main()` calls `generate_candidates(phase_info, nmolecules)` → returns `GenerationResult` with list of `Candidate` objects
6. `main()` calls `rank_candidates(candidates)` → returns `RankingResult` with `RankedCandidate` list
7. `main()` calls `output_ranked_candidates(ranking_result, output_dir)` → writes PDB files, validates structures, optionally generates phase diagram
8. Optionally: `main()` calls GROMACS export functions to write `.gro`, `.top`, `.itp` files
9. Exit code 0 on success, 1 on error

**GUI Pipeline (Tab 1 - Ice Generation):**

1. User enters T, P, nmolecules in `InputPanel` or clicks phase diagram
2. `MainWindow._on_generate_clicked()` validates inputs, calls `MainViewModel.start_generation(T, P, N)`
3. `MainViewModel` creates `GenerationWorker`, moves to `QThread`, starts thread
4. Worker runs same pipeline (lookup → generate → rank) in background, emitting progress/status signals
5. On completion: `ranked_candidates_ready` signal → `MainWindow._on_candidates_ready()` → loads into `DualViewerWidget` for 3D display
6. User can export via File menu (PDB, diagram, viewport, GROMACS)

**GUI Pipeline (Tab 2 - Interface Construction):**

1. User selects candidate from Tab 1 results, configures interface mode (slab/pocket/piece) in `InterfacePanel`
2. `MainWindow._on_interface_generate()` calls `MainViewModel.start_interface_generation(candidate, config)`
3. `InterfaceGenerationWorker` runs `generate_interface(candidate, config)` in background thread
4. On completion: `InterfaceStructure` displayed in `InterfaceViewerWidget` (3D viewer)
5. User can export interface structure as GROMACS files

**State Management:**
- CLI: Stateless pipeline, all data flows through function return values
- GUI: `MainViewModel` stores `_last_ranking_result` and `_last_interface_result` for cross-tab access
- GUI: `MainWindow` stores `_current_result`, `_current_T`, `_current_P`, `_current_interface_result` for export

## Key Abstractions

**Candidate:**
- Purpose: Represents a single generated ice crystal structure
- Examples: `quickice/structure_generation/types.py`
- Pattern: `@dataclass` with `positions` (nm), `atom_names`, `cell` (nm), `nmolecules`, `phase_id`, `seed`, `metadata`
- Key invariant: positions in nm, cell as (3,3) row-vector matrix, `new_position = position @ cell`

**RankedCandidate:**
- Purpose: Wraps a Candidate with its ranking scores
- Examples: `quickice/ranking/types.py`
- Pattern: `@dataclass` with `candidate`, `energy_score`, `density_score`, `diversity_score`, `combined_score`, `rank`

**GenerationResult:**
- Purpose: Bundles multiple candidates with metadata about the generation run
- Examples: `quickice/structure_generation/types.py`
- Pattern: `@dataclass` with `candidates`, `requested_nmolecules`, `actual_nmolecules`, `phase_id`, `phase_name`, `density`, `was_rounded`

**InterfaceConfig:**
- Purpose: Captures all parameters for interface structure generation
- Examples: `quickice/structure_generation/types.py`
- Pattern: `@dataclass` with mode, box dimensions, seed, mode-specific thicknesses, `from_dict()` classmethod for GUI binding
- Validation: `__post_init__` validates `overlap_threshold` range to catch unit mismatches

**InterfaceStructure:**
- Purpose: Result of ice-water interface generation with combined positions
- Examples: `quickice/structure_generation/types.py`
- Pattern: `@dataclass` with combined positions, `ice_atom_count` marking ice/water boundary

**Worker-Object Pattern:**
- Purpose: Run heavy computation off the Qt main thread without subclassing QThread
- Examples: `quickice/gui/workers.py` (`GenerationWorker`, `InterfaceGenerationWorker`)
- Pattern: QObject subclass with `run()` method, moved to QThread via `moveToThread()`, signals for progress/status/completion

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: `python quickice.py --temperature 300 --pressure 100 --nmolecules 96`
- Responsibilities: Imports `quickice.main.main()`, passes sys.exit code

**CLI Main Function:**
- Location: `quickice/main.py` → `main()`
- Triggers: Called by `quickice.py` entry point
- Responsibilities: Full pipeline orchestration (parse → lookup → generate → rank → output → export)

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui`
- Responsibilities: Creates QApplication, MainWindow, starts event loop

**GUI Main Window:**
- Location: `quickice/gui/main_window.py` → `MainWindow` class, `run_app()` function
- Triggers: Called by `__main__.py` or `quickice/gui/__init__.py:run_app()`
- Responsibilities: Assembles all UI components, connects signals, handles user actions

**Standalone Phase Diagram:**
- Location: `quickice/output/phase_diagram.py` → `if __name__ == "__main__"`
- Triggers: `python quickice/output/phase_diagram.py [T P]`
- Responsibilities: Generates phase diagram image for testing

## Error Handling

**Strategy:** Layered exceptions with context-rich error messages

**Patterns:**
- Domain errors use custom exception hierarchy: `PhaseMappingError` → `UnknownPhaseError`; `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`
- CLI: Catches `UnknownPhaseError` separately (exit 1 with message), generic `Exception` fallback (exit 1)
- GUI: Workers catch exceptions and emit `error` signal with message string; `MainWindow` shows `QMessageBox.critical` dialog
- Validation errors: CLI raises `ArgumentTypeError` (argparse handles display); GUI validators return `(bool, error_message)` tuples for inline error labels
- Interface builder validation: `InterfaceGenerationError` raised with detailed "How to fix" instructions in error messages

## Cross-Cutting Concerns

**Logging:** Python `logging` module used in `quickice/output/orchestrator.py` and `quickice/output/phase_diagram.py` for warnings; GUI uses `InfoPanel` (text widget) for user-facing log output

**Validation:** Dual validation system — CLI validators (`quickice/validation/validators.py`) raise `ArgumentTypeError`; GUI validators (`quickice/gui/validators.py`) return `(bool, str)` tuples with different limits (GUI nmolecules max=216 vs CLI max=100000)

**Authentication:** Not applicable — no user accounts or API keys

**Unit Consistency:** All internal coordinates in nanometers (nm); conversion to Ångströms happens only at export boundaries (`quickice/output/pdb_writer.py`, `quickice/output/validator.py`, `quickice/output/gromacs_writer.py`). The `InterfaceConfig.overlap_threshold` has `__post_init__` validation to catch Å/nm unit mismatches.

**Thread Safety:** GenIce2 uses global `np.random` state (not thread-safe); `IceStructureGenerator._generate_single()` saves/restores global state. Workers import modules inside `run()` to avoid blocking main thread. QuickIce is designed for sequential execution only.

**PBC Handling:** Multiple modules implement periodic boundary condition logic using scipy `cKDTree` with 3×3×3 supercell approach:
- `quickice/ranking/scorer.py` → O-O distance calculation
- `quickice/output/validator.py` → atomic overlap check
- `quickice/structure_generation/overlap_resolver.py` → ice-water overlap detection

---

*Architecture analysis: 2026-04-10*
