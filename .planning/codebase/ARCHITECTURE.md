# Architecture

**Analysis Date:** 2026-06-12

## Pattern Overview

**Overall:** MVVM (Model-View-ViewModel) with QThread-based background workers

**Key Characteristics:**
- Model layer is pure computational (no Qt dependencies)
- ViewModel (`MainViewModel`) mediates between View and Model via Qt Signal/Slot
- View is declarative PySide6 widgets connecting to ViewModel signals
- Background workers use QObject-moved-to-QThread pattern (NOT QThread subclassing)
- Two entry points: CLI (`quickice.main`) and GUI (`quickice.gui.__main__`)
- Data flows between tabs via stored results on `MainWindow` (not through ViewModel)

## Layers

**View Layer (GUI):**
- Purpose: UI panels, 3D viewers, user interaction
- Location: `quickice/gui/`
- Contains: PySide6 widgets, VTK viewers, export dialogs, input validators
- Depends on: ViewModel (`quickice/gui/viewmodel.py`)
- Used by: End user

**ViewModel Layer:**
- Purpose: Orchestrates workers, manages UI state, bridges View↔Model
- Location: `quickice/gui/viewmodel.py`
- Contains: `MainViewModel` class with Qt signals for state propagation
- Depends on: Workers (`quickice/gui/workers.py`), Model layer (imported inside workers)
- Used by: View layer (signal connections)

**Model Layer:**
- Purpose: Pure computational logic for ice structure generation, phase mapping, ranking, export
- Location: `quickice/structure_generation/`, `quickice/phase_mapping/`, `quickice/ranking/`, `quickice/output/`, `quickice/validation/`, `quickice/utils/`
- Contains: Dataclasses, generators, inserters, parsers, writers, error classes
- Depends on: GenIce2, numpy, scipy, iapws (no Qt dependencies)
- Used by: Workers (in background threads), CLI (synchronous)

**Worker Layer:**
- Purpose: Run Model operations in background threads to prevent UI freezing
- Location: `quickice/gui/workers.py`, `quickice/gui/hydrate_worker.py`, `quickice/gui/custom_molecule_worker.py`
- Contains: QObject-based workers with progress/status/error signals
- Depends on: Model layer (imported inside `run()` for thread safety)
- Used by: ViewModel (creates and manages workers)

**CLI Layer:**
- Purpose: Command-line interface for headless/scripted use
- Location: `quickice/cli/`, `quickice/main.py`
- Contains: Argparse parser, main orchestration function
- Depends on: Model layer (synchronous calls, same as Worker but without threading)
- Used by: `quickice.py` entry point

## Data Flow

**Ice Generation Flow (Tab 0):**

1. User enters T, P, N in `InputPanel` → clicks Generate
2. `MainWindow._on_generate_clicked()` validates inputs, calls `MainViewModel.start_generation()`
3. ViewModel creates `GenerationWorker`, moves it to `QThread`, starts thread
4. Worker (in background thread): `lookup_phase()` → `generate_candidates()` → `rank_candidates()`
5. Worker emits `finished` signal → ViewModel forwards via `generation_complete` and `ranked_candidates_ready` signals
6. `MainWindow._on_candidates_ready()` stores result, updates viewer, populates Interface tab dropdown

**Interface Generation Flow (Tab 2):**

1. User configures mode (slab/pocket/piece) in `InterfacePanel`, selects candidate
2. `MainWindow._on_interface_generate()` builds `InterfaceConfig`, calls `MainViewModel.start_interface_generation()`
3. ViewModel creates `InterfaceGenerationWorker`, moves to QThread
4. Worker calls `generate_interface(candidate, config)` which routes to `assemble_slab`/`assemble_pocket`/`assemble_piece`
5. Worker emits result → ViewModel forwards → `MainWindow._on_interface_generation_complete()` stores result, renders in 3D viewer, updates Ion/Solute/Custom panels with liquid volume

**Hydrate Generation Flow (Tab 1):**

1. User configures lattice/guest/occupancy in `HydratePanel`
2. `MainWindow._on_hydrate_generate_clicked()` creates `HydrateWorker(QThread)`
3. Worker runs `HydrateStructureGenerator.generate(config)`
4. Result stored as `_current_hydrate_result`, can be used as source for Interface Construction tab

**Cross-Tab Data Flow:**

1. Ice Generation (Tab 0) → Interface Construction (Tab 2): ranked candidates passed via `interface_panel.update_candidates()`
2. Interface Construction (Tab 2) → Custom Molecule (Tab 3): `custom_molecule_panel.set_interface_structure()`
3. Interface Construction (Tab 2) → Solute Insertion (Tab 4): `solute_panel.set_liquid_volume()`, `solute_panel.set_interface_available()`
4. Interface Construction (Tab 2) → Ion Insertion (Tab 5): `ion_panel.set_liquid_volume()`, `ion_panel.set_interface_available()`
5. Custom Molecule (Tab 3) → Solute (Tab 4): `solute_panel.set_custom_molecule_structure()`
6. Custom Molecule (Tab 3) → Ion (Tab 5): `ion_panel.set_custom_molecule_structure()`
7. Solute (Tab 4) → Ion (Tab 5): `ion_panel.set_solute_structure()`

**State Management:**
- All intermediate results stored as instance variables on `MainWindow` (e.g., `_current_result`, `_current_interface_result`, `_current_hydrate_result`, `_current_ion_result`, `_current_solute_result`, `_current_custom_molecule_result`)
- ViewModel caches last result: `_last_ranking_result`, `_last_interface_result`
- No global state or state management library; Qt widget state is inherently preserved

## Key Abstractions

**Candidate:**
- Purpose: A single generated ice structure with positions, atom names, cell vectors, metadata
- Examples: `quickice/structure_generation/types.py` (line 99)
- Pattern: Frozen dataclass with numpy arrays; created by `IceStructureGenerator._generate_single()`

**InterfaceStructure:**
- Purpose: Combined ice + water + guest positions with region boundaries
- Examples: `quickice/structure_generation/types.py` (line 222)
- Pattern: Dataclass with `ice_atom_count`/`water_atom_count`/`guest_atom_count` partition markers and `MoleculeIndex` list for variable-size molecules

**InterfaceConfig:**
- Purpose: User-specified parameters for interface generation (mode, box, thickness, etc.)
- Examples: `quickice/structure_generation/types.py` (line 152)
- Pattern: Validated dataclass with `from_dict()` factory for UI input mapping

**Worker Pattern (QObject → QThread):**
- Purpose: Run Model operations off the UI thread
- Examples: `quickice/gui/workers.py` (`GenerationWorker`, `InterfaceGenerationWorker`), `quickice/gui/custom_molecule_worker.py` (`CustomMoleculeWorker`)
- Pattern: QObject subclass with `run()` method, moved to QThread via `moveToThread()`. Model imports happen inside `run()` to avoid blocking main thread. Signals: progress(int), status(str), finished(object), error(str), cancelled()

**HydrateWorker (QThread subclass):**
- Purpose: Background hydrate generation
- Examples: `quickice/gui/hydrate_worker.py`
- Pattern: Subclasses QThread directly (different from the QObject→QThread pattern). Signals: progress_updated(str), generation_complete(object), generation_error(str)

**MoleculetypeRegistry:**
- Purpose: Unique GROMACS moleculetype naming to distinguish same molecule from different sources
- Examples: `quickice/structure_generation/moleculetype_registry.py`
- Pattern: Singleton-style registry with suffix naming (_H for hydrate, _L for liquid)

## Entry Points

**GUI Entry:**
- Location: `quickice/gui/__main__.py` → `quickice/gui/main_window.py::run_app()`
- Triggers: `python -m quickice.gui`
- Responsibilities: Creates QApplication, MainWindow, starts event loop. Configures OpenGL for remote X11.

**CLI Entry:**
- Location: `quickice/main.py::main()` via `quickice.py`
- Triggers: `python quickice.py --temperature 300 --pressure 100 --nmolecules 100`
- Responsibilities: Parses args, calls Model layer synchronously, prints results, writes GROMACS files

**Package Entry:**
- Location: `quickice/__init__.py` (defines `__version__ = "4.5.0"`)
- Triggers: `import quickice`
- Responsibilities: Version information only

## Error Handling

**Strategy:** Layered error hierarchy with fail-fast validation

**Patterns:**
- Custom exception hierarchy: `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError`
- Phase mapping errors: `PhaseMappingError` → `UnknownPhaseError`
- Workers catch all exceptions, emit `error` signal with message string
- ViewModel forwards errors to View which shows `QMessageBox.critical()`
- CLI catches specific exceptions and returns non-zero exit codes
- InterfaceConfig/CustomMoleculeConfig have `__post_init__` validation that raises `ValueError`
- `InterfaceGenerationError` carries `mode` attribute for context

## Cross-Cutting Concerns

**Logging:** Python `logging` module with `logger = logging.getLogger(__name__)` pattern throughout. MainWindow uses `logger` for debug/info. Workers emit `status` signals for UI log panel.

**Validation:** Dual validation system:
- CLI: `quickice/validation/validators.py` as argparse type converters (raise `ArgumentTypeError`)
- GUI: `quickice/gui/validators.py` returns `(bool, str)` tuples for inline error display
- Model: `__post_init__` on dataclass configs for parameter validation

**Authentication:** Not applicable (desktop application, no auth)

**Threading:** Workers must import Model modules inside `run()` method (deferred imports) to avoid blocking the main thread during heavy GenIce2 imports. `QThread.currentThread().isInterruptionRequested()` checked at start and between steps for cancellation support. Thread cleanup: `thread.finished.connect(worker.deleteLater)` + `thread.finished.connect(thread.deleteLater)`.

---

*Architecture analysis: 2026-06-12*
