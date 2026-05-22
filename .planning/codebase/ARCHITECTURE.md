# Architecture

**Analysis Date:** 2026-05-22

## Pattern Overview

**Overall:** MVVM (Model-View-ViewModel) with QThread Worker pattern for background computation

**Key Characteristics:**
- MVVM separation: View (PySide6 widgets) → ViewModel (signal orchestrator) → Model (pure computation)
- QThread worker-object pattern: Worker QObject moved to QThread, NOT QThread subclassing (except `HydrateWorker`)
- Tab-based GUI with `TabIndex` IntEnum constants for type-safe tab routing
- Pipeline architecture: generation → ranking → interface → (custom molecule / solute) → ion → GROMACS export
- Dual-entry architecture: CLI (`quickice.py` → `quickice/main.py`) and GUI (`quickice/gui/__main__.py` → `MainWindow`)
- Cross-tab data flow via MainWindow mediator (stores results and passes between panels)

## Layers

**View Layer (PySide6 Widgets):**
- Purpose: UI rendering, user interaction, signal emission
- Location: `quickice/gui/`
- Contains: Panel widgets, viewer widgets, input forms, export dialogs
- Depends on: ViewModel (signals), VTK (3D rendering), PySide6
- Used by: User interaction only
- Key files: `quickice/gui/view.py`, `quickice/gui/main_window.py`, `quickice/gui/interface_panel.py`, `quickice/gui/hydrate_panel.py`, `quickice/gui/ion_panel.py`, `quickice/gui/solute_panel.py`, `quickice/gui/custom_molecule_panel.py`

**ViewModel Layer (Signal Orchestrator):**
- Purpose: Manage UI state, create workers, forward worker signals to view
- Location: `quickice/gui/viewmodel.py`
- Contains: `MainViewModel` QObject with Qt signals for generation lifecycle
- Depends on: Workers (creates and manages), Model (receives results)
- Used by: MainWindow (View layer)
- Pattern: ViewModel creates Worker → moves to QThread → connects worker signals to ViewModel slots → ViewModel re-emits signals to View

**Model Layer (Pure Computation):**
- Purpose: Ice structure generation, phase mapping, ranking, insertion, export
- Location: `quickice/structure_generation/`, `quickice/phase_mapping/`, `quickice/ranking/`, `quickice/output/`, `quickice/validation/`
- Contains: Generator classes, inserter classes, writer functions, lookup functions
- Depends on: GenIce2, scipy, numpy, matplotlib
- Used by: Workers (GUI) and CLI (`quickice/main.py`)
- Key principle: No Qt imports — pure Python/NumPy for testability and CLI reuse

**Worker Layer (QThread Bridge):**
- Purpose: Run Model computations in background threads without freezing UI
- Location: `quickice/gui/workers.py`, `quickice/gui/hydrate_worker.py`, `quickice/gui/custom_molecule_worker.py`
- Contains: QObject-based workers with `run()` method, signal definitions
- Depends on: Model (imports inside `run()` for thread safety)
- Used by: ViewModel (creates, connects signals, manages lifecycle)
- Pattern: Imports Model modules inside `run()` to avoid blocking main thread during heavy imports

## Data Flow

**Ice Generation Pipeline (Tab 0):**

1. User enters T, P, N in `InputPanel` → clicks Generate
2. `MainWindow._on_generate_clicked()` → validates inputs → calls `ViewModel.start_generation(T, P, N)`
3. `MainViewModel` creates `GenerationWorker(T, P, N)`, moves to `QThread`, starts
4. `GenerationWorker.run()` calls Model: `lookup_phase(T, P)` → `generate_candidates(phase_info, N)` → `rank_candidates(candidates)`
5. Worker emits `finished(GenerationResult)` → ViewModel forwards to View via `generation_complete` and `ranked_candidates_ready` signals
6. `MainWindow._on_candidates_ready()` stores result, updates `DualViewerWidget` (VTK 3D), updates `InterfacePanel` candidate dropdown

**Interface Generation Pipeline (Tab 2):**

1. User selects candidate + configures mode/box in `InterfacePanel` → clicks Generate
2. `MainWindow._on_interface_generate(candidate_index)` → gets candidate from stored `RankingResult` → calls `ViewModel.start_interface_generation(candidate, config)`
3. `MainViewModel` creates `InterfaceGenerationWorker(candidate, config)`, moves to QThread
4. Worker calls Model: `validate_interface_config(config, candidate)` → routes to mode (`assemble_slab`/`assemble_pocket`/`assemble_piece`)
5. Worker emits `finished(InterfaceGenerationResult)` → ViewModel forwards via `interface_generation_complete`
6. `MainWindow._on_interface_generation_complete()` stores `InterfaceStructure`, renders in `InterfacePanel` viewer, passes liquid volume to Ion/Solute panels

**Cross-Tab Data Flow (Full Pipeline):**

```
Tab 0 (Ice)           → Tab 2 (Interface)    → Tab 3 (Custom)    → Tab 4 (Solute)    → Tab 5 (Ion)
GenerationResult        InterfaceStructure      CustomMolecule      SoluteStructure     IonStructure
  └─ ranked_candidates    └─ ice+water+guests     Structure           └─ with solutes     └─ with ions
     passed to Tab 2       liquid_volume          (random/custom       passed to Tab 5     GROMACS export
                            passed to Tab 5        placement)           + Tab 5             
                            passed to Tab 3,4      passed to Tab 4,5
```

Data flows through `MainWindow` as mediator: each tab completion stores result in `MainWindow._current_*_result`, then explicitly calls downstream panel methods (e.g., `self.solute_panel.set_interface_available(True)`, `self.ion_panel.set_custom_molecule_structure(result)`).

**Ion Source Selection (Tab 5):**
- Source "Interface": Uses `MainWindow._current_interface_result` directly
- Source "Solute": Uses `MainWindow._current_solute_result.interface_structure` (solute-modified interface)
- Source "Custom Molecule": Uses `MainWindow._current_custom_molecule_result.interface_structure` (custom-modified interface)
- Each source adds molecule metadata (solute_type, positions, etc.) to the interface structure for downstream export

**State Management:**
- No global state store — each result stored as `MainWindow` instance variable
- `_current_result` (RankingResult from Tab 0)
- `_current_interface_result` (InterfaceStructure from Tab 2)
- `_current_hydrate_result` (HydrateStructure from Tab 1)
- `_current_custom_molecule_result` (CustomMoleculeStructure from Tab 3)
- `_current_solute_result` (SoluteStructure from Tab 4)
- `_current_ion_result` (IonStructure from Tab 5)
- Tab state preserved by Qt widget lifecycle (no explicit save/restore needed)

## Key Abstractions

**Candidate (`quickice/structure_generation/types.py`):**
- Purpose: Represents a single generated ice structure from GenIce2
- Pattern: Immutable dataclass with positions (nm), atom_names, cell (nm), nmolecules, phase_id, seed, metadata
- Usage: Created by `IceStructureGenerator._generate_single()`, consumed by rankers and interface builders

**InterfaceStructure (`quickice/structure_generation/types.py`):**
- Purpose: Combined ice + water + guest atom positions for an ice-water interface
- Pattern: Dataclass with ordered atom regions: ice first, then water, then guests (marked by ice_atom_count, water_atom_count, guest_atom_count)
- Usage: Created by `assemble_slab`/`assemble_pocket`/`assemble_piece`, consumed by VTK renderers and GROMACS exporters
- Critical: Atom ordering contract — positions[0:ice_atom_count] = ice, [ice_atom_count:ice+water] = water, [ice+water:] = guests

**MoleculeIndex (`quickice/structure_generation/types.py`):**
- Purpose: Tracks molecule boundaries in a flat atom array with variable atoms per molecule
- Pattern: Dataclass with start_idx, count, mol_type — enables handling 1-atom ions, 3-atom ice, 4-atom water, 5-atom CH4, 12-atom THF
- Usage: Stored in InterfaceStructure, IonStructure, HydrateStructure, CustomMoleculeStructure for export

**InterfaceConfig (`quickice/structure_generation/types.py`):**
- Purpose: Captures all interface generation parameters from UI
- Pattern: Validated dataclass with `from_dict()` factory method for UI dict → config conversion
- Modes: "slab" (ice-water-ice sandwich), "pocket" (spherical/cubic cavity in ice), "piece" (ice crystal in water box)

**MoleculetypeRegistry (`quickice/structure_generation/moleculetype_registry.py`):**
- Purpose: Unique GROMACS moleculetype naming to distinguish molecules from different sources
- Pattern: Registry with suffix-based naming — hydrate guests use `_H` suffix (CH4_H), liquid solutes use `_L` suffix (CH4_L)
- Usage: Prevents GROMACS topology conflicts when same molecule type appears in different contexts

**GenerationWorker / InterfaceGenerationWorker / CustomMoleculeWorker (`quickice/gui/workers.py`, `quickice/gui/custom_molecule_worker.py`):**
- Purpose: Run Model computations in background QThread without freezing UI
- Pattern: Worker-object pattern — QObject with `run()` method, moved to QThread via `moveToThread()`
- Signals: progress (int 0-100), status (str), finished (result object), error (str), cancelled ()
- Import strategy: Model imports inside `run()` method to avoid blocking main thread during heavy GenIce2 imports

**HydrateWorker (`quickice/gui/hydrate_worker.py`):**
- Purpose: Background thread for hydrate generation
- Pattern: QThread subclass (different from other workers which use worker-object pattern)
- Signals: progress_updated (str), generation_complete (HydrateStructure), generation_error (str)

## Entry Points

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui` or `from quickice.gui import run_app`
- Responsibilities: Creates QApplication, configures OpenGL for remote displays, creates MainWindow, starts Qt event loop
- Flow: `_configure_opengl_for_remote()` → `QApplication` → `MainWindow()` → `app.exec()`

**CLI Entry Point:**
- Location: `quickice.py` (root) → `quickice/main.py`
- Triggers: `python quickice.py --temperature 300 --pressure 100 --nmolecules 100`
- Responsibilities: Parse args, lookup phase, generate candidates, rank, export (PDB + GROMACS + phase diagram)
- Flow: `get_arguments()` → `lookup_phase(T, P)` → `generate_candidates(phase_info, N)` → `rank_candidates()` → `output_ranked_candidates()` + optional GROMACS export

**Main Function (`quickice/main.py`):**
- Two modes: ice generation (default) and interface generation (`--interface` flag)
- Interface mode: Creates `InterfaceConfig` from CLI args → generates ice candidate → calls `generate_interface(candidate, config)` → exports GROMACS files
- Error handling: Catches `UnknownPhaseError`, `InterfaceGenerationError`, generic exceptions → returns non-zero exit code

## Error Handling

**Strategy:** Layered exceptions with descriptive messages, fail-fast validation before expensive operations

**Patterns:**
- Domain exceptions: `StructureGenerationError`, `UnsupportedPhaseError`, `InterfaceGenerationError`, `PhaseMappingError`, `UnknownPhaseError` (all in their respective modules' `errors.py`)
- Validation-before-generation: `validate_interface_config()` in `quickice/structure_generation/interface_builder.py` performs all validation checks before calling assembly functions, with detailed "How to fix" messages
- Worker error propagation: Workers catch exceptions in `run()`, emit `error` signal with message string, ViewModel forwards to View which shows `QMessageBox.critical()`
- CLI error handling: `main()` catches domain exceptions, prints to stderr, returns non-zero exit code
- InsertionError: Custom exception in `quickice/structure_generation/custom_molecule_inserter.py` for max-attempts exhaustion with attempt count

## Cross-Cutting Concerns

**Logging:** Python `logging` module with `logger = logging.getLogger(__name__)` pattern throughout. GUI uses logger for debug/info, panel `append_log()` for user-visible messages.

**Validation:** Two validation layers:
1. Input validation: `quickice/validation/validators.py` (CLI) and `quickice/gui/validators.py` (GUI) — range checks on T, P, N
2. Structural validation: `quickice/output/validator.py` — space group checks, atomic overlap detection after generation
3. Config validation: `InterfaceConfig.__post_init__()`, `HydrateConfig.__post_init__()`, `SoluteConfig.__post_init__()`, `CustomMoleculeConfig.__post_init__()` — parameter range checks

**Authentication:** Not applicable (offline desktop application)

**Unit Conversion:** All internal coordinates in nanometers (nm). GROMACS format also uses nm. Angstrom constants defined in `quickice/structure_generation/overlap_resolver.py` (`angstrom_to_nm = 0.1`). TIP3P→TIP4P-ICE normalization at export time (3-atom ice → 4-atom water with MW virtual site computed via `compute_mw_position()` in `quickice/output/gromacs_writer.py`).

**Thread Safety:** Model layer (`quickice/structure_generation/`) has no Qt imports — pure Python/NumPy/scipy. Workers import Model inside `run()`. `IceStructureGenerator._generate_single()` saves/restores `np.random` state around GenIce calls (GenIce uses global random state, not thread-safe). Design assumes sequential execution within each worker thread.

**PBC (Periodic Boundary Conditions):** Multiple modules handle PBC:
- `overlap_resolver.py`: cKDTree with `boxsize` parameter for minimum-image convention
- `gromacs_writer.py`: `wrap_positions_into_box()` and `wrap_molecules_into_box()` for GRO file output
- `ranking/scorer.py`: 3×3×3 supercell expansion for O-O distance calculation

---

*Architecture analysis: 2026-05-22*
