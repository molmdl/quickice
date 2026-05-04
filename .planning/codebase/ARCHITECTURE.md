# Architecture

**Analysis Date:** 2026-05-05

## Pattern Overview

**Overall:** Layered architecture with MVVM pattern for GUI, pipeline pattern for CLI

**Key Characteristics:**
- Separation of concerns between UI and business logic
- Background threading for computational operations (GUI)
- External library integration (GenIce2, VTK, PySide6)
- Plugin-based structure generation modes
- Curve-based phase mapping (no polygon containment)

## Layers

**Entry Points Layer:**
- Purpose: Handle user input and invoke appropriate workflow
- Location: `quickice.py`, `quickice/main.py`, `quickice/gui/main_window.py`
- Contains: CLI argument parsing, GUI window setup, input validation
- Depends on: ViewModels (GUI), Core logic (CLI)
- Used by: End users

**ViewModel Layer (GUI only):**
- Purpose: Bridge between View and Model, manage threading
- Location: `quickice/gui/viewmodel.py`
- Contains: Signal/slot connections, worker thread management, state coordination
- Depends on: Workers, Core logic
- Used by: MainWindow (View)

**Worker Layer (GUI only):**
- Purpose: Execute computational tasks in background threads
- Location: `quickice/gui/workers.py`
- Contains: GenerationWorker, InterfaceGenerationWorker, progress reporting
- Depends on: Core logic (phase_mapping, structure_generation, ranking)
- Used by: ViewModel

**Core Business Logic Layer:**
- Purpose: Domain-specific computation and data transformation
- Location: `quickice/phase_mapping/`, `quickice/structure_generation/`, `quickice/ranking/`, `quickice/output/`
- Contains: Phase lookup, structure generation, candidate ranking, file export
- Depends on: External libraries (GenIce2, NumPy), Utilities
- Used by: Workers, CLI main

**Utilities Layer:**
- Purpose: Shared validation and helper functions
- Location: `quickice/validation/`, `quickice/utils/`
- Contains: Input validators, molecule utilities
- Depends on: Standard library
- Used by: CLI, GUI components

**Data Layer:**
- Purpose: Static data files and resources
- Location: `quickice/data/`
- Contains: Water templates, ITP files, GRO templates
- Depends on: Nothing
- Used by: Structure generation, output

## Data Flow

**CLI Pipeline (Ice Generation):**

1. Parse command-line arguments via `quickice/cli/parser.py`
2. Validate inputs (temperature 0-500K, pressure 0-10000 MPa, molecules 4-100000)
3. Lookup ice phase via `quickice/phase_mapping/lookup.py` using curve-based boundary evaluation
4. Generate candidate structures via `quickice/structure_generation/generator.py` (calls GenIce2)
5. Rank candidates via `quickice/ranking/scorer.py` (energy, density, diversity scores)
6. Export output files via `quickice/output/orchestrator.py` (PDB, GRO, TOP, phase diagram)

**CLI Pipeline (Interface Generation):**

1. Parse interface-specific arguments (--interface, --mode, --box-x/y/z, mode-specific params)
2. Generate ice candidate (steps 3-4 above)
3. Validate interface configuration via `quickice/structure_generation/interface_builder.py`
4. Assemble interface via mode-specific function (slab/pocket/piece)
5. Export GROMACS files (GRO, TOP, ITP)

**GUI Workflow:**

1. User enters T, P, nmolecules in InputPanel
2. MainWindow._on_generate_clicked() calls ViewModel.start_generation()
3. ViewModel creates GenerationWorker, moves to QThread
4. Worker runs CLI pipeline in background, emits progress signals
5. ViewModel forwards signals to MainWindow
6. MainWindow updates progress bar, status text, log panel
7. On completion, MainWindow receives RankingResult
8. DualViewer loads top candidates into VTK viewports
9. User can export via menu actions (PDB, GROMACS, diagrams)

**State Management:**
- GUI: ViewModel stores last_ranking_result, last_interface_result for cross-tab access
- CLI: Stateless, each run is independent
- Results passed through dataclass containers (GenerationResult, RankingResult, InterfaceStructure)

## Key Abstractions

**Candidate:**
- Purpose: Represents a single ice structure with coordinates and metadata
- Examples: `quickice/structure_generation/types.py`
- Pattern: Immutable dataclass with positions (NumPy array), cell matrix, metadata dict
- Contains: positions, atom_names, cell (3x3 row vectors), nmolecules, phase_id, seed, metadata

**InterfaceStructure:**
- Purpose: Combined ice + water + guest molecule structure for interface systems
- Examples: `quickice/structure_generation/types.py`
- Pattern: Composite dataclass with explicit atom count boundaries
- Contains: positions, atom_names, cell, ice_atom_count, water_atom_count, guest_atom_count, molecule_index list

**HydrateStructure:**
- Purpose: Clathrate hydrate with water framework and guest molecules
- Examples: `quickice/structure_generation/types.py`
- Pattern: Composite dataclass with molecule tracking
- Contains: positions, atom_names, cell, molecule_index, config, lattice_info, guest_count, water_count
- Method: to_candidate() converts to Candidate for interface generation

**IonStructure:**
- Purpose: Interface structure with Na+/Cl- ions inserted in liquid region
- Examples: `quickice/structure_generation/types.py`
- Pattern: Composite dataclass with ion counts
- Contains: positions, atom_names, cell, molecule_index, na_count, cl_count

**GenerationResult:**
- Purpose: Container for multiple candidates with metadata
- Examples: `quickice/structure_generation/types.py`
- Pattern: Result object pattern
- Contains: candidates list, requested_nmolecules, actual_nmolecules, phase_id, was_rounded flag

**RankingResult:**
- Purpose: Ranked candidates with scores
- Examples: `quickice/ranking/types.py`
- Pattern: Result object pattern
- Contains: ranked_candidates list (each with rank, energy_score, density_score, combined_score)

**InterfaceConfig/HydrateConfig/IonConfig:**
- Purpose: Configuration dataclasses for generation modes
- Examples: `quickice/structure_generation/types.py`
- Pattern: Configuration object pattern with validation
- Methods: from_dict() for UI integration

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py` (wrapper) -> `quickice/main.py` (main() function)
- Triggers: `python quickice.py --temperature 300 --pressure 100 --nmolecules 96`
- Responsibilities: Parse args, orchestrate pipeline, print output, handle errors, exit codes

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py` -> `quickice/gui/main_window.py` (MainWindow class)
- Triggers: `python -m quickice.gui` or `quickice-gui` (after PyInstaller packaging)
- Responsibilities: Create MainWindow, setup UI components, connect signals, handle user interactions

**GUI Tabs:**
- Tab 1 (Ice Generation): InputPanel -> ViewModel -> Workers -> DualViewer
- Tab 2 (Hydrate Config): HydratePanel -> HydrateWorker -> HydrateViewer
- Tab 3 (Interface Construction): InterfacePanel -> ViewModel (interface worker) -> InterfaceViewer
- Tab 4 (Ion Insertion): IonPanel -> IonInserter -> IonViewer

## Error Handling

**Strategy:** Fail-fast with descriptive error messages

**Patterns:**
- Custom exception classes: `UnknownPhaseError`, `InterfaceGenerationError`, `StructureGenerationError`
- Validation before expensive operations (validate_interface_config)
- Error messages include context: actual values, expected ranges, how to fix
- GUI shows QMessageBox for errors, CLI prints to stderr with exit code 1
- Workers emit error signals, ViewModel forwards to MainWindow

**Exception Hierarchy:**
```
Exception
├── PhaseMappingError
│   └── UnknownPhaseError (no ice phase at given T,P)
├── StructureGenerationError
│   ├── UnsupportedPhaseError (GenIce doesn't support phase)
│   └── InterfaceGenerationError (validation failures, mode errors)
```

**Error Context:**
- InterfaceGenerationError includes mode name for context
- Messages include actual values, expected ranges, remediation steps
- CLI: "Error: {message}" with context, exit code 1
- GUI: QMessageBox.critical with title and formatted message

## Cross-Cutting Concerns

**Logging:** Python logging module, logger per module, INFO level for progress, DEBUG for details

**Validation:** 
- CLI: argparse type validators (validate_temperature, validate_pressure, validate_nmolecules)
- GUI: InputPanel validators with error highlighting
- Core: Config dataclasses with __post_init__ validation

**Authentication:** None (local desktop application)

**Threading:**
- GUI uses QThread with worker-object pattern (NOT subclassing QThread)
- Workers emit signals for progress, status, completion, errors
- ViewModel manages thread lifecycle with timeouts (100ms) to prevent UI freezing
- CLI is single-threaded, no concurrency concerns

**Testing:**
- pytest framework with test files in `tests/`
- Unit tests for individual modules (test_phase_mapping.py, test_structure_generation.py)
- Integration tests (test_integration_v35.py, test_cli_integration.py)
- Mode-specific validation tests (test_piece_mode_validation.py, test_interface_modes_audit.py)

---

*Architecture analysis: 2026-05-05*
