# Architecture

**Analysis Date:** 2026-05-22

## Pattern Overview

**Overall:** MVVM (Model-View-ViewModel) with a dual-entry-point design (CLI + GUI)

**Key Characteristics:**
- MVVM for GUI: View (PySide6 widgets) → ViewModel (signal/slot orchestration) → Model (structure generation, phase mapping, ranking)
- Pipeline pattern for CLI: Phase lookup → Generation → Ranking → Output/Export
- Worker-object pattern for background threading (QObject moved to QThread, NOT QThread subclass)
- Strategy pattern for interface modes (slab/pocket/piece) dispatched by `interface_builder.py`
- Dataclass-based data contracts between layers (`Candidate`, `InterfaceStructure`, `IonStructure`, `SoluteStructure`, `CustomMoleculeStructure`)
- Tab-based workflow with cross-tab data flow (Ice → Hydrate → Interface → Custom → Solute → Ion)

## Layers

**GUI View Layer:**
- Purpose: PySide6 widgets for user interaction, 3D VTK visualization, input validation
- Location: `quickice/gui/`
- Contains: Panels, viewers, validators, renderers, exporters
- Depends on: ViewModel signals, PySide6, VTK
- Used by: End user

**ViewModel Layer:**
- Purpose: Orchestrate worker threads, manage UI state, bridge View ↔ Model
- Location: `quickice/gui/viewmodel.py`, `quickice/gui/workers.py`
- Contains: `MainViewModel`, `GenerationWorker`, `InterfaceGenerationWorker`
- Depends on: Model layer (structure_generation, ranking, output)
- Used by: View layer (signal/slot connections)

**Model / Core Logic Layer:**
- Purpose: Physics-based ice structure generation, phase mapping, ranking, file I/O
- Location: `quickice/structure_generation/`, `quickice/phase_mapping/`, `quickice/ranking/`, `quickice/output/`
- Contains: Generators, inserters, mappers, scorers, writers
- Depends on: GenIce2, IAPWS, scipy, numpy
- Used by: ViewModel (via workers), CLI (direct function calls)

**Data Layer:**
- Purpose: Bundled molecular data files (ITP topology, GRO coordinates)
- Location: `quickice/data/`
- Contains: `.itp` files (TIP4P-ICE, CH4, THF, hydrate-specific), `.gro` files (TIP4P water template), custom molecule examples
- Depends on: Nothing
- Used by: Structure generation, GROMACS export

**Validation Layer:**
- Purpose: Input validation shared between CLI and GUI
- Location: `quickice/validation/validators.py` (CLI), `quickice/gui/validators.py` (GUI)
- Contains: Type-validated argparse converters and tuple-returning GUI validators
- Depends on: Nothing
- Used by: CLI parser, GUI input panels

## Data Flow

**CLI Pipeline (Ice Generation):**

1. User runs `python quickice.py -T 273 -P 0.1 -N 256`
2. `quickice/cli/parser.py` validates inputs via `quickice/validation/validators.py`
3. `quickice/main.py` calls `lookup_phase(T, P)` → returns `phase_info` dict
4. `generate_candidates(phase_info, nmolecules)` → `GenerationResult` with list of `Candidate`
5. `rank_candidates(candidates)` → `RankingResult` with `RankedCandidate` list
6. `output_ranked_candidates(ranking_result, output_dir)` → PDB files + phase diagram
7. `write_gro_file` / `write_top_file` → GROMACS format export

**CLI Pipeline (Interface Generation):**

1. User runs `python quickice.py -T 273 -P 0.1 --interface --mode slab ...`
2. Same phase lookup + candidate generation as ice pipeline
3. `InterfaceConfig.from_dict()` creates validated config
4. `generate_interface(candidate, config)` → routes to `assemble_slab` / `assemble_pocket` / `assemble_piece`
5. `write_interface_gro_file` / `write_interface_top_file` → GROMACS format export

**GUI Pipeline (Ice Generation):**

1. User enters T, P in `InputPanel` → clicks Generate
2. `MainWindow._on_generate_clicked()` validates, calls `MainViewModel.start_generation()`
3. ViewModel creates `GenerationWorker` (QObject), moves to `QThread`, starts
4. Worker calls `lookup_phase()` → `generate_candidates()` → `rank_candidates()`
5. Worker emits `finished` signal with `GenerationResult`
6. ViewModel forwards via `ranked_candidates_ready` signal
7. View updates: `DualViewerWidget` renders VTK, `InfoPanel` logs rankings

**GUI Pipeline (Hydrate Generation):**

1. User configures `HydratePanel` → clicks Generate
2. `MainWindow._on_hydrate_generate_clicked()` creates `HydrateWorker(config)`
3. Worker calls `HydrateStructureGenerator.generate(config)` → `HydrateStructure`
4. Result stored in `MainWindow._current_hydrate_result`
5. Cross-tab: Hydrate available as source for Interface Construction tab

**GUI Pipeline (Interface → Solute → Ion Chain):**

1. Interface Construction tab: user selects ice candidate, configures mode → Generate
2. `MainViewModel.start_interface_generation(candidate, config)` → `InterfaceGenerationWorker`
3. Result: `InterfaceStructure` stored in `MainWindow._current_interface_result`
4. Cross-tab: `ion_panel.set_liquid_volume()`, `solute_panel.set_liquid_volume()`, `custom_molecule_panel.set_interface_structure()`
5. Custom Molecule tab: `CustomMoleculeInserter.insert()` → `CustomMoleculeStructure`
6. Solute Insertion tab: `SoluteInserter.insert_solutes()` → `SoluteStructure`
7. Ion Insertion tab: source dropdown (Interface / Solute / Custom Molecule) → `insert_ions()` → `IonStructure`

**State Management:**
- GUI state is managed via instance variables on `MainWindow` (e.g., `_current_result`, `_current_interface_result`, `_current_hydrate_result`, `_current_solute_result`, `_current_custom_molecule_result`, `_current_ion_result`)
- Cross-tab communication is direct: `MainWindow` methods update downstream tab panels
- No global state or state management library; all state lives in `MainWindow` and `MainViewModel`

## Key Abstractions

**Candidate:**
- Purpose: A single generated ice structure with positions, cell, phase info
- Examples: `quickice/structure_generation/types.py` (class `Candidate`)
- Pattern: Immutable dataclass; generated by `IceStructureGenerator`, consumed by ranking and interface modes

**InterfaceStructure:**
- Purpose: Combined ice + water + guest atom positions with phase distinction
- Examples: `quickice/structure_generation/types.py` (class `InterfaceStructure`)
- Pattern: Dataclass with `ice_atom_count` / `water_atom_count` / `guest_atom_count` partitioning; ordering: ice first, then water, then guests

**MoleculeIndex:**
- Purpose: Tracks each molecule's position in atom arrays (handles variable atoms-per-molecule)
- Examples: `quickice/structure_generation/types.py` (class `MoleculeIndex`)
- Pattern: `(start_idx, count, mol_type)` tuples in a list; used throughout structure types

**MoleculetypeRegistry:**
- Purpose: Unique GROMACS moleculetype naming (distinguishes CH4_H vs CH4_L)
- Examples: `quickice/structure_generation/moleculetype_registry.py`
- Pattern: Singleton-style registry with `_H` (hydrate) and `_L` (liquid) suffixes

**Mode Strategy (Interface Modes):**
- Purpose: Different geometry modes for interface assembly
- Examples: `quickice/structure_generation/modes/slab.py`, `pocket.py`, `piece.py`
- Pattern: Each module exports `assemble_*()` function with same signature `(candidate, config) → InterfaceStructure`; `interface_builder.py` dispatches by `config.mode`

**Exporter Classes:**
- Purpose: GROMACS/PDB/Diagram/Viewport file export from GUI
- Examples: `quickice/gui/export.py` (5 classes: PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter, InterfaceGROMACSExporter, IonGROMACSExporter, SoluteGROMACSExporter, CustomMoleculeGROMACSExporter), `quickice/gui/hydrate_export.py` (1 class: HydrateGROMACSExporter)
- Pattern: Each exporter holds a reference to `parent_widget` for `QFileDialog` access; calls `gromacs_writer.py` functions for actual file writing

**Worker Pattern:**
- Purpose: Background computation without freezing the GUI
- Examples: `quickice/gui/workers.py` (`GenerationWorker`, `InterfaceGenerationWorker`), `quickice/gui/hydrate_worker.py` (`HydrateWorker`), `quickice/gui/custom_molecule_worker.py` (`CustomMoleculeWorker`)
- Pattern: QObject subclass with `run()` method; moved to QThread; emits `progress`, `status`, `finished`, `error`, `cancelled` signals

## Entry Points

**CLI Entry Point:**
- Location: `quickice.py` (project root)
- Triggers: `python quickice.py --temperature ... --pressure ...`
- Responsibilities: Argparse, pipeline orchestration, console output

**GUI Entry Point:**
- Location: `quickice/gui/__main__.py`
- Triggers: `python -m quickice.gui` or PyInstaller bundle
- Responsibilities: Create `QApplication`, instantiate `MainWindow`, start Qt event loop

**Main Function (shared logic):**
- Location: `quickice/main.py`
- Triggers: Called by CLI entry point
- Responsibilities: Phase lookup, generation, ranking, output orchestration, GROMACS export

**GUI App Launcher:**
- Location: `quickice/gui/main_window.py` → `run_app()` function
- Triggers: Called by `__main__.py`
- Responsibilities: Create `QApplication`, set style, show `MainWindow`, `exec()`

**PyInstaller Spec:**
- Location: `quickice-gui.spec`
- Triggers: `pyinstaller quickice-gui.spec`
- Responsibilities: Bundle collection for all dependencies (GenIce2, scipy, numpy, matplotlib, VTK, etc.)

## Error Handling

**Strategy:** Layered exception hierarchy with descriptive error messages

**Patterns:**
- `quickice/structure_generation/errors.py`: `StructureGenerationError` → `UnsupportedPhaseError`, `InterfaceGenerationError` (carries `mode` attribute)
- `quickice/phase_mapping/errors.py`: `PhaseMappingError` → `UnknownPhaseError`
- `quickice/structure_generation/custom_molecule_inserter.py`: `InsertionError` (carries `attempts` attribute)
- CLI: try/except in `main()` catches `UnknownPhaseError`, `InterfaceGenerationError`, generic `Exception`; returns non-zero exit code
- GUI: Workers catch exceptions and emit `error` signal with message; ViewModel forwards; View shows `QMessageBox.critical()`
- Validation: `InterfaceConfig.__post_init__()`, `HydrateConfig.__post_init__()`, `SoluteConfig.__post_init__()`, `CustomMoleculeConfig.__post_init__()` raise `ValueError` for invalid parameters
- Overlap threshold validation: `ValueError` if `threshold_nm` outside [0.1, 1.0] nm range to catch unit mismatches

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` pattern throughout; logger instances in `main_window.py`, `solute_inserter.py`, `gromacs_writer.py`, `moleculetype_registry.py`, `water_density.py`, `ice_ih_density.py`, `itp_parser.py`

**Validation:** Two parallel validator sets:
- CLI: `quickice/validation/validators.py` — raise `ArgumentTypeError` (for argparse type= parameter)
- GUI: `quickice/gui/validators.py` — return `tuple[bool, str]` (for inline error display)

**Authentication:** Not applicable (desktop application, no external auth)

**Coordinate System:** All internal coordinates in nanometers (nm); GenIce outputs in nm; GRO format uses nm; ITP files use nm; Angstrom-to-nm conversion helpers in `overlap_resolver.py`

**Periodic Boundary Conditions:** PBC-aware overlap detection via `scipy.spatial.cKDTree(boxsize=...)` in `overlap_resolver.py`; PBC-aware O-O distance calculation in `ranking/scorer.py`; molecule wrapping for GRO export in `gromacs_writer.py`

**Atom Naming Convention:**
- Ice from GenIce: 3 atoms per molecule (`O`, `H`, `H`) — TIP3P format
- Water from tip4p.gro: 4 atoms per molecule (`OW`, `HW1`, `HW2`, `MW`) — TIP4P-ICE format
- Ice is normalized to TIP4P-ICE at GROMACS export time (MW position computed via `TIP4P_ICE_ALPHA`)
- `detect_atoms_per_molecule()` in each mode module detects which format is present

**Data Bundling:** `quickice/data/` contains bundled ITP/GRO files accessed via `Path(quickice.__file__).parent / "data"`; custom molecules in `quickice/data/custom/`; PyInstaller spec copies `quickice/data` into bundle

---

*Architecture analysis: 2026-05-22*
