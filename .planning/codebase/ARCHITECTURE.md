# Architecture

**Analysis Date:** 2026-04-11

## Pattern Overview

**Overall:** Pipeline + MVVM hybrid

**Key Characteristics:**
- CLI path: Sequential pipeline (validation → phase mapping → structure generation → ranking → output)
- GUI path: MVVM (Model-ViewModel-View) with background workers on QThread
- Core domain logic is shared between CLI and GUI — neither depends on the other
- Data flows through typed dataclasses (`Candidate`, `GenerationResult`, `RankedCandidate`, `RankingResult`, `OutputResult`, `InterfaceStructure`)
- Phase mapping uses curve-based boundary evaluation (not polygon containment) for scientific accuracy

## Layers

**Presentation (CLI):**
- Purpose: Parse CLI arguments, display results to terminal
- Location: `quickice/cli/`
- Contains: Argument parser, CLI-specific validators
- Depends on: `quickice.validation`, `quickice.main`
- Used by: `quickice.py` entry point

**Presentation (GUI):**
- Purpose: Interactive ice structure generation and visualization
- Location: `quickice/gui/`
- Contains: PySide6 widgets, VTK viewers, matplotlib canvas, MVVM ViewModel, QThread workers
- Depends on: All core modules (`phase_mapping`, `structure_generation`, `ranking`, `output`)
- Used by: `python -m quickice.gui` entry point

**Orchestration:**
- Purpose: Wire pipeline stages together into a single execution flow
- Location: `quickice/main.py` (CLI), `quickice/gui/viewmodel.py` + `quickice/gui/workers.py` (GUI)
- Contains: Sequential call chain from phase lookup through output
- Depends on: All pipeline modules
- Used by: CLI entry point, GUI ViewModel

**Domain — Phase Mapping:**
- Purpose: Determine which ice polymorph is stable at given T,P conditions
- Location: `quickice/phase_mapping/`
- Contains: Curve-based lookup, IAPWS melting equations, solid-solid boundary interpolation, triple point data
- Depends on: `iapws` (for Liquid-Vapor boundary only)
- Used by: `quickice.main`, `quickice/gui/workers.py`, `quickice/output/phase_diagram.py`

**Domain — Structure Generation:**
- Purpose: Generate ice crystal structures using GenIce2 and build ice-water interfaces
- Location: `quickice/structure_generation/`
- Contains: GenIce2 wrapper, phase-to-lattice mapper, supercell calculator, interface builder (slab/pocket/piece modes), water filler, overlap resolver
- Depends on: `genice2`, `quickice.phase_mapping` (for density metadata)
- Used by: `quickice.main`, `quickice/gui/workers.py`

**Domain — Ranking:**
- Purpose: Score and rank generated ice structure candidates
- Location: `quickice/ranking/`
- Contains: Energy scorer (O-O distance heuristic), density scorer, diversity scorer, weighted combination
- Depends on: `quickice.structure_generation.types` (Candidate type)
- Used by: `quickice.main`, `quickice/gui/workers.py`

**Domain — Output:**
- Purpose: Write results to files (PDB, GROMACS, phase diagrams)
- Location: `quickice/output/`
- Contains: PDB writer, GROMACS writer, phase diagram generator, structure validator (spglib), orchestrator
- Depends on: `quickice.ranking.types`, `quickice.phase_mapping` (for diagram boundary curves), `spglib`, `matplotlib`, `shapely`
- Used by: `quickice.main`, `quickice/gui/export.py`

**Validation:**
- Purpose: Validate user inputs (temperature, pressure, molecule count)
- Location: `quickice/validation/`
- Contains: CLI validators (raise `ArgumentTypeError`) and shared validation logic
- Depends on: None (standalone)
- Used by: `quickice/cli/parser.py`, `quickice/gui/validators.py` (separate GUI-specific validators)

**Static Data:**
- Purpose: Bundled reference files (GROMACS topology templates)
- Location: `quickice/data/`
- Contains: `tip4p-ice.itp` (TIP4P-ICE topology), `tip4p.gro` (water template for interface generation)
- Depends on: None
- Used by: `quickice/output/gromacs_writer.py`, `quickice/structure_generation/water_filler.py`

## Data Flow

**CLI Pipeline:**

1. User runs `python quickice.py -T 300 -P 100 -N 96`
2. `quickice/cli/parser.py` parses and validates arguments via `quickice/validation/validators.py`
3. `quickice/main.py:main()` calls `lookup_phase(T, P)` from `quickice/phase_mapping/`
4. `generate_candidates(phase_info, nmolecules)` in `quickice/structure_generation/generator.py` creates `IceStructureGenerator`, calls GenIce2 for each seed
5. `rank_candidates(candidates)` in `quickice/ranking/scorer.py` scores and sorts candidates
6. `output_ranked_candidates(ranking_result)` in `quickice/output/orchestrator.py` writes PDB files, validates structures, generates phase diagram
7. Optionally: GROMACS export writes `.gro`, `.top`, `.itp` files via `quickice/output/gromacs_writer.py`

**GUI Pipeline (MVVM):**

1. User enters parameters in `InputPanel` or clicks `PhaseDiagramPanel`
2. `MainWindow._on_generate_clicked()` calls `MainViewModel.start_generation(T, P, N)`
3. ViewModel creates `GenerationWorker` (QObject), moves to `QThread`, starts thread
4. Worker runs same pipeline as CLI (lookup → generate → rank), emitting progress/status signals
5. ViewModel forwards signals to View: `generation_progress`, `generation_status`, `ranked_candidates_ready`
6. View updates: progress bar, log panel, `DualViewerWidget` loads ranked candidates via VTK
7. Export handlers (`PDBExporter`, `GROMACSExporter`, etc.) save files via native file dialogs

**Interface Construction (GUI Tab 2):**

1. User selects candidate from Tab 1 dropdown, configures mode (slab/pocket/piece) in `InterfacePanel`
2. `MainWindow._on_interface_generate()` creates `InterfaceConfig` and calls `MainViewModel.start_interface_generation()`
3. `InterfaceGenerationWorker` calls `generate_interface(candidate, config)` in `quickice/structure_generation/interface_builder.py`
4. Mode router dispatches to `modes/slab.py`, `modes/pocket.py`, or `modes/piece.py`
5. Each mode: places ice slab/cavity, fills remaining space with water (via `water_filler.py`), resolves overlaps (via `overlap_resolver.py`)
6. Returns `InterfaceStructure` → displayed in `InterfaceViewerWidget`

**State Management:**
- CLI: Stateless pipeline — each run is independent
- GUI: ViewModel holds `_last_ranking_result` and `_last_interface_result` for export access
- No persistent state between sessions — all state is transient (in-memory)

## Key Abstractions

**Candidate (`quickice/structure_generation/types.py`):**
- Purpose: Represents a single generated ice structure with atomic positions, cell vectors, metadata
- Examples: Created by `IceStructureGenerator._generate_single()`, consumed by ranking and output
- Pattern: Immutable dataclass with numpy arrays (positions, cell) + metadata dict

**GenerationResult (`quickice/structure_generation/types.py`):**
- Purpose: Bundles multiple Candidates with generation metadata (requested vs actual molecule count)
- Examples: Return type of `generate_candidates()`
- Pattern: Dataclass container with `was_rounded` flag for crystal symmetry rounding

**RankedCandidate (`quickice/ranking/types.py`):**
- Purpose: A Candidate with scoring breakdown and rank
- Examples: Output of `rank_candidates()`, input to PDB writer and VTK viewer
- Pattern: Dataclass wrapping a Candidate reference + score fields

**InterfaceConfig (`quickice/structure_generation/types.py`):**
- Purpose: Configuration dataclass capturing all interface generation parameters from UI
- Examples: Created by `InterfacePanel.get_configuration()`, validated by `validate_interface_config()`
- Pattern: Validated dataclass with `from_dict()` classmethod for UI→domain conversion

**InterfaceStructure (`quickice/structure_generation/types.py`):**
- Purpose: Combined ice + water atomic positions with phase boundary marker
- Examples: Output of `generate_interface()`, input to VTK `InterfaceViewerWidget`
- Pattern: Dataclass with `ice_atom_count` marking the ice/water split index

**Phase Info Dict (`quickice/phase_mapping/lookup.py`):**
- Purpose: Result of phase lookup containing `phase_id`, `phase_name`, `density`, `temperature`, `pressure`
- Examples: Return type of `lookup_phase()`, passed to `generate_candidates()`
- Pattern: Plain dict with known keys (not a dataclass — legacy from polygon-based design)

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py` (project root)
- Triggers: `python quickice.py --temperature 300 --pressure 100 --nmolecules 96`
- Responsibilities: Imports `quickice.main:main()`, passes `sys.exit()` code

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui`
- Responsibilities: Creates `QApplication`, `MainWindow`, starts Qt event loop

**Main Module Entry Point:**
- Location: `quickice/main.py:main()`
- Triggers: Called by `quickice.py`
- Responsibilities: Parses args, runs full pipeline (lookup → generate → rank → output), handles errors

**Direct Script Execution:**
- Location: `quickice/output/phase_diagram.py` (has `if __name__ == "__main__"` block)
- Triggers: `python quickice/output/phase_diagram.py [T] [P]`
- Responsibilities: Standalone phase diagram generation for testing

## Error Handling

**Strategy:** Fail-fast with typed exceptions, no silent fallbacks

**Patterns:**
- Domain errors use custom exception hierarchies:
  - `PhaseMappingError` → `UnknownPhaseError` (`quickice/phase_mapping/errors.py`)
  - `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError` (`quickice/structure_generation/errors.py`)
- CLI catches exceptions in `quickice/main.py:main()` and prints to stderr with exit code 1
- GUI workers catch exceptions in `run()` methods and emit `error` signals with string messages
- GUI `MainWindow` shows `QMessageBox.critical()` for generation errors
- Validation errors: CLI uses `ArgumentTypeError` (argparse convention), GUI returns `(bool, str)` tuples
- `UnknownPhaseError` carries `temperature` and `pressure` attributes for debugging context
- Interface generation validates config BEFORE starting expensive operations (`validate_interface_config()`)
- Structure validation (spglib) and overlap checking are non-fatal — logged as warnings, not errors

## Cross-Cutting Concerns

**Logging:** Python `logging` module used in output module (`quickice/output/orchestrator.py`, `quickice/output/phase_diagram.py`); GUI uses `InfoPanel` log display fed by ViewModel signals

**Validation:** Dual validation systems — CLI validators raise exceptions (`quickice/validation/validators.py`), GUI validators return `(bool, str)` tuples (`quickice/gui/validators.py`). Same rules, different error propagation.

**Unit Conversions:** Positions and cell vectors are consistently in nanometers (nm) internally. PDB writer converts to Ångströms (`* 10.0`). GROMACS writer converts to nm output. VTK viewer converts nm → Å for rendering. `InterfaceConfig.overlap_threshold` validates nm range [0.1, 1.0] to catch Å/nm unit mismatches.

**Thread Safety:** GenIce2 uses global `np.random` state (not thread-safe). `IceStructureGenerator._generate_single()` saves/restores global state. QuickIce is designed for sequential execution; concurrent generation is explicitly unsupported.

**VTK Availability:** VTK rendering may fail in SSH/X11 forwarding environments. Both `quickice/gui/view.py` and `quickice/gui/interface_panel.py` detect `_VTK_AVAILABLE` and degrade gracefully (show log message instead of 3D viewer). `QUICKICE_FORCE_VTK=true` env var overrides detection.

---

*Architecture analysis: 2026-04-11*
