# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** Pipeline architecture with MVVM GUI

**Key Characteristics:**
- Sequential pipeline for CLI: validation → phase mapping → generation → ranking → output
- MVVM pattern for GUI with Qt/PySide6
- Clear module boundaries with explicit public APIs
- Functional core, imperative shell (pipeline is pure, I/O at boundaries)

## Layers

**CLI Layer:**
- Purpose: Command-line interface entry point
- Location: `quickice/main.py`, `quickice/cli/parser.py`
- Contains: Argument parsing, validation, orchestration
- Depends on: All pipeline modules (phase_mapping, structure_generation, ranking, output)
- Used by: User via `python quickice.py`

**Validation Layer:**
- Purpose: Input validation for CLI arguments
- Location: `quickice/validation/validators.py`
- Contains: Type validators (temperature, pressure, molecule count)
- Depends on: argparse (standard library)
- Used by: CLI parser

**Phase Mapping Layer:**
- Purpose: Map (T, P) conditions to ice phase
- Location: `quickice/phase_mapping/`
- Contains: Curve-based lookup, boundary calculations, triple points
- Depends on: NumPy (for calculations), standard library
- Used by: CLI main, GUI workers

**Structure Generation Layer:**
- Purpose: Generate ice structure candidates using GenIce
- Location: `quickice/structure_generation/`
- Contains: GenIce wrapper, phase-to-lattice mapping, supercell calculation
- Depends on: GenIce2 (external), NumPy
- Used by: CLI main, GUI workers

**Ranking Layer:**
- Purpose: Score and rank generated candidates
- Location: `quickice/ranking/`
- Contains: Energy, density, diversity scoring functions
- Depends on: NumPy, SciPy (KDTree)
- Used by: CLI main, GUI workers

**Output Layer:**
- Purpose: Write PDB files, validate structures, generate diagrams
- Location: `quickice/output/`
- Contains: PDB writer, GROMACS writer, validators, phase diagram generator
- Depends on: Matplotlib, MDAnalysis (optional)
- Used by: CLI main

**GUI Layer:**
- Purpose: Interactive graphical interface
- Location: `quickice/gui/`
- Contains: View (MainWindow, panels), ViewModel, Workers, 3D viewers
- Depends on: PySide6 (Qt), VTK (optional), Matplotlib
- Used by: User via `python -m quickice.gui`

## Data Flow

**CLI Pipeline:**

1. User runs `python quickice.py --temperature 300 --pressure 100 --nmolecules 100`
2. `quickice/cli/parser.py` parses and validates arguments
3. `quickice/phase_mapping/lookup.py` maps (T, P) → phase_info dict
4. `quickice/structure_generation/generator.py` generates N candidates
5. `quickice/ranking/scorer.py` scores and ranks candidates
6. `quickice/output/orchestrator.py` writes PDB files, generates diagram

**GUI Pipeline:**

1. User clicks Generate button in MainWindow
2. MainViewModel.start_generation() creates GenerationWorker
3. Worker moved to QThread, runs pipeline asynchronously
4. Worker emits progress/status signals → ViewModel → View
5. On completion, ranked candidates loaded into 3D viewer

**State Management:**
- CLI: No state, sequential execution
- GUI: ViewModel holds last ranking result, current generation state
- Workers: State isolated to thread, cleaned up on completion

## Key Abstractions

**Candidate:**
- Purpose: Single generated ice structure with coordinates
- Examples: `quickice/structure_generation/types.py`
- Pattern: Dataclass with positions, atom_names, cell, metadata

**RankedCandidate:**
- Purpose: Candidate with scoring and rank
- Examples: `quickice/ranking/types.py`
- Pattern: Dataclass wrapping Candidate + scores

**GenerationResult, RankingResult, OutputResult:**
- Purpose: Container types for pipeline stage outputs
- Examples: `quickice/structure_generation/types.py`, `quickice/ranking/types.py`, `quickice/output/types.py`
- Pattern: Result objects with success/failure state, data, metadata

**Phase Info:**
- Purpose: Ice phase metadata (ID, name, density)
- Examples: `quickice/phase_mapping/lookup.py` PHASE_METADATA
- Pattern: Dict with phase_id, phase_name, density keys

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py`
- Triggers: User runs `python quickice.py [args]`
- Responsibilities: Import main(), call sys.exit(main())

**CLI Main:**
- Location: `quickice/main.py`
- Triggers: Called by `quickice.py`
- Responsibilities: Parse args, run pipeline, print results, handle errors

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: User runs `python -m quickice.gui`
- Responsibilities: Create QApplication, MainWindow, start event loop

**GUI Run App:**
- Location: `quickice/gui/main_window.py` run_app()
- Triggers: Called by `__main__.py`
- Responsibilities: Initialize Qt application, show window, exec event loop

## Error Handling

**Strategy:** Exception-based with custom exception hierarchy

**Patterns:**
- Base exceptions in each module: `errors.py`
- `PhaseMappingError`, `UnknownPhaseError` in `quickice/phase_mapping/errors.py`
- `StructureGenerationError`, `UnsupportedPhaseError` in `quickice/structure_generation/errors.py`
- CLI catches exceptions, prints to stderr, returns non-zero exit code
- GUI catches exceptions in worker, emits error signal to ViewModel

## Cross-Cutting Concerns

**Logging:** Python logging module (standard library)
- Used in output orchestrator for validation warnings
- GUI status messages via Qt signals

**Validation:** 
- Input validation via argparse type functions
- Structure validation in `quickice/output/validator.py`

**Authentication:** Not applicable (local scientific tool)

**Threading:**
- GUI uses QThread for background generation
- Worker pattern: QObject with run() method, not QThread subclass
- Cancellation via thread interruption requests

---

*Architecture analysis: 2026-04-07*
