# Architecture

**Analysis Date:** 2026-04-04

## Pattern Overview

**Overall:** Pipeline with MVVM GUI Layer

**Key Characteristics:**
- Sequential data flow through processing phases (Phase 1-5)
- Clean separation between core computation and GUI presentation
- Domain-driven module organization by processing phase
- Type-safe data transfer using dataclasses
- Error propagation via custom exception hierarchy

## Layers

**CLI Entry Layer:**
- Purpose: Command-line interface parsing and execution
- Location: `quickice.py`, `quickice/cli/`
- Contains: Argument parsing, validation, main orchestration
- Depends on: All core modules (phase_mapping, structure_generation, ranking, output)
- Used by: End users via command line

**GUI Presentation Layer:**
- Purpose: Interactive visualization and user interface
- Location: `quickice/gui/`
- Contains: MVVM components (View, ViewModel), VTK 3D rendering, Qt widgets
- Depends on: ViewModel layer, PySide6, VTK
- Used by: End users via `python -m quickice.gui`

**ViewModel Layer:**
- Purpose: Bridge between View and Model, manages UI state and worker threads
- Location: `quickice/gui/viewmodel.py`
- Contains: `MainViewModel` class, signal/slot connections, thread management
- Depends on: Core modules, `GenerationWorker`
- Used by: `MainWindow` and View components

**Core Pipeline Layer:**
- Purpose: Ice structure generation computation
- Location: `quickice/phase_mapping/`, `quickice/structure_generation/`, `quickice/ranking/`, `quickice/output/`
- Contains: Domain logic for each processing phase
- Depends on: GenIce2, NumPy, SciPy, Matplotlib
- Used by: CLI and ViewModel

**External Integration Layer:**
- Purpose: Interface with external libraries (GenIce2, IAPWS)
- Location: `quickice/structure_generation/generator.py`, `quickice/output/phase_diagram.py`
- Contains: Wrappers and adapters for third-party APIs
- Depends on: GenIce2, IAPWS
- Used by: Core pipeline modules

## Data Flow

**CLI Pipeline:**

1. User provides T, P, N via command line
2. `quickice/cli/parser.py` validates and parses arguments
3. `quickice/main.py` orchestrates the pipeline:
4. `quickice/phase_mapping/lookup.py` determines ice phase
5. `quickice/structure_generation/generator.py` generates candidates via GenIce2
6. `quickice/ranking/scorer.py` scores and ranks candidates
7. `quickice/output/orchestrator.py` writes PDB files and phase diagram
8. Results written to output directory

**GUI Pipeline:**

1. User enters T, P, N in `InputPanel` or clicks phase diagram
2. `MainWindow` validates and calls `MainViewModel.start_generation()`
3. `MainViewModel` creates `GenerationWorker` and moves to `QThread`
4. `GenerationWorker.run()` executes same pipeline as CLI in background
5. Progress signals update `ProgressPanel` during execution
6. `ranked_candidates_ready` signal loads results into `DualViewerWidget`
7. User can export PDB, diagram, or viewport screenshots via File menu

**State Management:**
- CLI: Stateless, single-pass execution
- GUI: `MainViewModel` maintains `_last_ranking_result` for export operations
- Both: All state flows through dataclass instances (no hidden global state)

## Key Abstractions

**Candidate:**
- Purpose: Represents a single generated ice structure
- Examples: `quickice/structure_generation/types.py`
- Pattern: Immutable dataclass with NumPy arrays for coordinates
- Fields: positions, atom_names, cell, nmolecules, phase_id, seed, metadata

**RankedCandidate:**
- Purpose: Wraps Candidate with scoring information
- Examples: `quickice/ranking/types.py`
- Pattern: Dataclass with composite scoring (energy, density, diversity)
- Fields: candidate, energy_score, density_score, diversity_score, combined_score, rank

**GenerationResult / RankingResult / OutputResult:**
- Purpose: Result containers for each pipeline phase
- Examples: `quickice/structure_generation/types.py`, `quickice/ranking/types.py`, `quickice/output/types.py`
- Pattern: Immutable result objects with metadata
- Enables clean phase-to-phase data flow

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: `python quickice.py --temperature T --pressure P --nmolecules N`
- Responsibilities: Loads main(), handles SystemExit, returns exit code

**CLI Main Function:**
- Location: `quickice/main.py:main()`
- Triggers: Called by `quickice.py` entry point
- Responsibilities: Parses args, orchestrates pipeline, prints output, returns exit code

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui`
- Responsibilities: Creates QApplication, MainWindow, starts event loop

**Module Entry Points:**
- Each module exposes a single public function via `__init__.py`:
  - `quickice/phase_mapping/__init__.py`: `lookup_phase()`
  - `quickice/structure_generation/__init__.py`: `generate_candidates()`
  - `quickice/ranking/__init__.py`: `rank_candidates()`
  - `quickice/output/__init__.py`: `output_ranked_candidates()`

## Error Handling

**Strategy:** Exception propagation with typed error classes

**Patterns:**
- Custom exception hierarchy: `PhaseMappingError` > `UnknownPhaseError`, `StructureGenerationError` > `UnsupportedPhaseError`
- Errors include context: temperature, pressure values attached to exceptions
- CLI: Prints error to stderr, returns non-zero exit code
- GUI: Shows QMessageBox dialog, updates progress panel to error state
- Validation: Separate validation errors via `ArgumentTypeError` in CLI

**Exception Classes:**
- `quickice/phase_mapping/errors.py`: `PhaseMappingError`, `UnknownPhaseError`
- `quickice/structure_generation/errors.py`: `StructureGenerationError`, `UnsupportedPhaseError`

**Error Flow:**
1. Domain error occurs (e.g., unknown phase)
2. Domain module raises typed exception
3. Orchestrator catches, prints/logs error
4. CLI: Returns exit code 1
5. GUI: Emits `generation_error` signal, shows dialog

## Cross-Cutting Concerns

**Logging:** Python `logging` module, INFO level for pipeline progress, DEBUG for curve calculations

**Validation:** Centralized validators in `quickice/validation/validators.py`, used by CLI parser and GUI validators

**Authentication:** Not applicable (local computation only)

**Configuration:** Environment-based (QUICKICE_FORCE_VTK), no external config files

**Thread Safety:** GUI uses QThread for background work, signals/slots for thread-safe communication

---

*Architecture analysis: 2026-04-04*
