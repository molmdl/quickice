# Architecture

**Analysis Date:** 2026-10-15

## Pattern Overview

**Overall:** Dual-path application (CLI + GUI) sharing a single core physics engine, with the GUI path following Model-View-ViewModel (MVVM).

**Key Characteristics:**
- Two execution paths (`quickice/cli/`, `quickice/gui/`) share a common core (`quickice/structure_generation/` + `quickice/output/`). The two paths must never depend on each other.
- Single entry router (`quickice/entry.py::main()`) decides CLI vs GUI vs help; all routing logic lives there, never in `__main__.py` or `quickice.py`.
- Fail-fast ordered pipeline in CLI; event-driven signal/slot orchestration in GUI.
- **Lazy-import architecture (slow-gui-startup fix, now significant):** PEP 562 `__getattr__`/`__dir__` lazy re-export maps in `quickice/gui/__init__.py` and `quickice/structure_generation/__init__.py`; `scipy.spatial` deferred to first use; `vtk_utils.py` heavy imports inside function bodies; GUI exporters defer matplotlib/VTK. `entry.py` probes PySide6 via `importlib.util.find_spec` (never imports).
- Pure-functional inserters that return NEW structure objects and never mutate inputs; `cKDTree` rebuilt only on successful placement.
- `InterfaceStructure` is the central shared data structure; downstream steps attach solute/custom-molecule/guest metadata via duck-typing (accepted design decision CP-01, NOT a bug).

## Layers

**Entry / Router Layer:**
- Purpose: Decide CLI vs GUI vs help and delegate; keep heavy imports lazy.
- Location: `quickice/entry.py`
- Contains: `main()` (line 105), `_is_pyside6_available()` (line 26), `_has_display()` (line 42), `_has_pipeline_flags()` (line 72), `_get_install_hint()` (line 91)
- Depends on: stdlib only at module top (`importlib.util`, `platform`, `sys`); `quickice.cli.parser`, `quickice.main`, `quickice.gui.main_window` imported lazily inside branches.
- Used by: `quickice/__main__.py`, `quickice.py` (both call `entry.main()`).
- Note: `_has_display()` treats `QT_QPA_PLATFORM` ∈ {`wayland`, `xcb`, `offscreen`} as a display, so headless GUI runs with `offscreen` pass the check.

**CLI Layer:**
- Purpose: Argument parsing + ordered pipeline orchestration + GROMACS ITP copying. NO Qt/PySide6/VTK imports (verified: source files contain no such imports).
- Location: `quickice/cli/`
- Contains: `parser.py` (`create_parser` line 23, `validate_pipeline_args` line 450, `get_arguments` line 514), `pipeline.py` (`CLIPipeline` orchestrator, class at line 133), `itp_helpers.py` (ITP path resolution + `copy_itp_files_for_structure`)
- Depends on: `quickice.validation.validators`, `quickice.phase_mapping`, `quickice.structure_generation`, `quickice.output.gromacs_writer`, `quickice.output.guest_info`, `quickice.cli.itp_helpers`. Heavy structure-generation imports are done lazily inside each step method (e.g. `from quickice.structure_generation.types import HydrateConfig` inside `_run_source_step`).
- Used by: `quickice/main.py` (CLI dispatcher for ice-only legacy path and pipeline delegation).

**GUI Layer (MVVM):**
- Purpose: Qt-based interactive UI; tabbed workflow mirroring the CLI pipeline order.
- Location: `quickice/gui/`
- Contains:
  - View: `view.py` (`InputPanel` line 33, `ProgressPanel` line 204, `ViewerPanel` line 287, `HelpIcon` line 634, `InfoPanel` line 679), `main_window.py` (`MainWindow`), per-tab panels (`hydrate_panel.py`, `interface_panel.py`, `custom_molecule_panel.py`, `solute_panel.py`, `ion_panel.py`), viewers (`hydrate_viewer.py`, `interface_viewer.py`, `solute_viewer.py`, `custom_molecule_viewer.py`, `ion_viewer.py`, `molecular_viewer.py`, `dual_viewer.py`), renderers (`hydrate_renderer.py`, `ion_renderer.py`, `solute_renderer.py`, `custom_molecule_renderer.py`), `phase_diagram_widget.py` (lightweight panel; lazy-loads canvas), `phase_diagram_canvas.py` (heavy matplotlib+shapely canvas, see Key Abstractions), `help_dialog.py`, `validators.py`, `constants.py` (`TabIndex`), `vtk_utils.py`.
  - ViewModel: `viewmodel.py` (`MainViewModel` line 14).
  - Model / Workers: `workers.py` (`GenerationWorker` line 26, `InterfaceGenerationWorker` line 146 — both QObject+moveToThread pattern, plus local `GenerationResult`/`InterfaceGenerationResult` payload dataclasses), `hydrate_worker.py` (`HydrateWorker` — direct `QThread` subclass, accepted design decision, do not "fix"), `custom_molecule_worker.py` (`CustomMoleculeWorker` line 18, QObject), and inline `IonInsertionWorker` in `main_window.py:45` (also direct `QThread` subclass, mirrors `HydrateWorker`).
  - Export: `export.py` (1259 lines — `GROMACSExporter`, `InterfaceGROMACSExporter`, `SoluteGROMACSExporter` line 151, `CustomMoleculeGROMACSExporter` line 333, `IonGROMACSExporter` line 508, `PDBExporter` line 705, `DiagramExporter` line 786, `ViewportExporter` line 875), `hydrate_export.py` (`HydrateGROMACSExporter` line 78).
- Depends on: PySide6, VTK (via `vtk_utils.py`), and the shared core (`structure_generation`, `output`, `phase_mapping`). GenIce2, matplotlib, and vtkmodules imported inside worker/exporter method bodies.
- Used by: `quickice/entry.py` (via `from quickice.gui.main_window import run_app` when `--gui`), `quickice/gui/__main__.py`.

**Core Physics Engine (shared):**
- Purpose: Generate ice/hydrate candidates, assemble ice-water interfaces, insert solutes/custom molecules/ions. Used by BOTH CLI and GUI.
- Location: `quickice/structure_generation/`
- Contains: `types.py` (all dataclasses + constants), `generator.py` (`IceStructureGenerator`, `generate_candidates` — wraps GenIce2), `hydrate_generator.py` (`HydrateStructureGenerator` line 43 — wraps GenIce2, lazy `_ensure_genice_import` line 67), `interface_builder.py` (`generate_interface`, `validate_interface_config` — routes to modes), `modes/` (`slab.py`, `pocket.py`, `piece.py` — each exposes `assemble_<mode>(candidate, config) -> InterfaceStructure`), `ion_inserter.py` (`IonInserter`, `insert_ions`), `solute_inserter.py` (`SoluteInserter`, `insert_solutes`), `custom_molecule_inserter.py` (`CustomMoleculeInserter`, `InsertionError`), `water_filler.py`, `overlap_resolver.py`, `moleculetype_registry.py` (`MoleculetypeRegistry` line 13), `molecule_validator.py`, `gro_parser.py`, `itp_parser.py` (`parse_itp_file`), `mapper.py` (phase→GenIce lattice), `cell_utils.py`, `errors.py`, `gromacs_ion_export.py`, `custom_guest_bridge.py`.
- Depends on: numpy, scipy.spatial.cKDTree (lazy), GenIce2 (lazy). No Qt/VTK.
- Used by: `quickice/cli/pipeline.py`, `quickice/gui/main_window.py`, `quickice/gui/workers.py`, `quickice/gui/hydrate_worker.py`.

**Output Layer (shared):**
- Purpose: Serialize structures to GROMACS `.gro`/`.top`/`.itp`, PDB, and phase diagrams. Used by BOTH paths.
- Location: `quickice/output/`
- Contains: `gromacs_writer.py` (re-export facade — imports from `ice_writer`, `interface_writer`, `multi_molecule_writer`, `ion_writer`, `custom_writer`, `solute_writer`, `_shared`, `_gro_format`), `_shared.py` (aggregator over 6 domain sub-modules: `_constants`, `_atomtypes`, `_pbc`, `_itp`, `_guest`, `_tip4p`), `_gro_format.py` (GRO line formatters), `guest_info.py` (`_build_custom_guest_info`, hydrate guest ITP staging, `_stage_hydrate_guest_itps`), `orchestrator.py` (`output_ranked_candidates`), `pdb_writer.py`, `validator.py` (space-group + overlap checks), `phase_diagram.py`, `types.py` (`OutputResult`).
- Depends on: numpy, matplotlib (phase diagram), `quickice.structure_generation`, `quickice.utils.molecule_utils`, `quickice.ranking.types`.
- Used by: `quickice/main.py`, `quickice/cli/pipeline.py`, `quickice/gui/export.py`, `quickice/gui/hydrate_export.py`.
- Note: `quickice/output/__init__.py` is NOT lazy (eager facade over orchestrator + writer functions); keep heavy additions out of it.

**Supporting Layers:**
- `quickice/phase_mapping/` — IAPWS R14-08 melting-curve-based ice phase lookup. Entry: `lookup_phase(t, p)`. Files: `lookup.py`, `melting_curves.py`, `solid_boundaries.py`, `triple_points.py`, `water_density.py`, `ice_ih_density.py`, `errors.py` (`PhaseMappingError`, `UnknownPhaseError`), `data/` (`ice_phases.json`, `ice_boundaries.py`).
- `quickice/ranking/` — multi-criteria candidate scoring (energy, density, diversity). Entry: `rank_candidates(candidates)`. Files: `scorer.py`, `types.py` (`RankedCandidate`, `RankingResult`, `ScoringConfig`).
- `quickice/validation/` — input validators used by CLI argparse `type=` callbacks. File: `validators.py` (`validate_temperature`, `validate_pressure`, `validate_nmolecules`, `validate_positive_float`, `validate_box_dimension`, `validate_concentration_range`, `validate_occupancy_range`).
- `quickice/utils/` — shared helpers. File: `molecule_utils.py` (`identify_guest_type` line 25, `count_guest_atoms` line 102, `iter_guest_molecules` line 242, `separate_guests_by_type` line 294).
- `quickice/data/` — bundled static data (ITP files, water template, examples). See STRUCTURE.md.

## Data Flow

**CLI Pipeline (`CLIPipeline.execute()` in `quickice/cli/pipeline.py:154`):**

Ordered steps with fail-fast (each step returns `int`; non-zero aborts):
1. **Output dir setup** (line 162): resolve `--output`, reject paths outside cwd (SEC-05), mkdir.
2. **Source** (`_run_source_step`, line 330): if `--hydrate`, build `HydrateConfig` + `HydrateStructureGenerator().generate()` → `self._hydrate_result`; if `--interface` also set, convert via `hydrate.to_candidate()` → `self._ice_candidate`. Else if `--interface` only, `generate_candidates()` → `self._ice_candidate`.
3. **Interface** (`_run_interface_step`, line 437): build `InterfaceConfig`, `generate_interface(self._ice_candidate, config)` → `self._interface_result`.
4. **Custom** (`_run_custom_step`, line 487): validate `--custom-gro`/`--custom-itp` extensions + cwd containment (SEC-04), parse positions CSV (random or custom, `MAX_CSV_ROWS = 10000` at line 21), `CustomMoleculeInserter.place_random/place_custom` → `self._custom_result`.
5. **Solute** (`_run_solute_step`, line 629): resolve source via `--solute-source` (auto-chains `interface`→`custom` when custom molecules exist), `SoluteInserter(config, seed=args.seed).insert_solutes` → `self._solute_result`.
6. **Ion** (`_run_ion_step`, line 700): resolve `--ion-source` (auto-chains `interface`→`solute`→`custom`), propagate solute/custom attrs onto the `InterfaceStructure` via duck-typing (lines ~780-832: `interface.solute_type`, `interface.solute_positions`, `interface.custom_molecule_positions`, etc.), `insert_ions(...)` → `self._ion_result`.
7. **Export** (`_run_export_step`, line 859): pick most downstream structure (ion > solute > custom > interface > hydrate > ice), dispatch to the matching `write_*_gro_file`/`write_*_top_file`, then `copy_itp_files_for_structure(...)`.

**CLI Ice-only legacy path (`quickice/main.py:23`):** when no pipeline flags, runs `generate_candidates` → `rank_candidates` → `output_ranked_candidates` (+ optional `write_gro_file`/`write_top_file` for `--gromacs`).

**GUI Cross-Tab Data Flow (`quickice/gui/main_window.py`):**

Tab order (defined in `quickice/gui/constants.py::TabIndex`, IntEnum): Tab 0 (ICE) → Tab 1 (HYDRATE) → Tab 2 (INTERFACE) → Tab 3 (CUSTOM) → Tab 4 (SOLUTE) → Tab 5 (ION) → Export.

Flow:
1. Tab 0/1: `GenerationWorker`/`HydrateWorker` produces a `RankingResult`/`HydrateStructure`; stored as `self._current_result` / `self._current_hydrate_result` (line 857).
2. Tab 2: `InterfaceGenerationWorker` (or hydrate→candidate path) produces `InterfaceStructure`; stored as `self._current_interface_result` (line 692).
3. Tab 3: custom molecule placement → `self._current_custom_molecule_result` (line 1334); passed to SolutePanel/IonPanel source dropdowns.
4. Tab 4: solute insertion (`_on_insert_solutes`, line 1137) reads interface + optional custom; stores `self._current_solute_result` (line 1195); passes to IonPanel.
5. Tab 5: `_on_insert_ions` (line 902) reads solute (`self._current_solute_result`, line 935) and custom (`self._current_custom_molecule_result`, line 968), duck-types attributes onto the interface: `interface.solute_type = solute_structure.solute_type` (line 948), `interface.custom_molecule_positions = ...` (line 980). Stores `self._current_ion_result` (line 1058).
6. Export: per-step exporters in `quickice/gui/export.py` consume the matching `_current_*_result`.

**State Management:**
- CLI: instance attributes on `CLIPipeline` (`_interface_result`, `_hydrate_result`, `_custom_result`, `_solute_result`, `_ion_result`, `_ice_candidate`, `_output_dir`). Pure local state, one pipeline run per process.
- GUI: `MainWindow` holds `_current_*_result` attributes (lines 154-179). `MainViewModel` holds `_last_ranking_result` / `_last_interface_result` plus worker/thread refs. Workers are the bridge to the core engine.

## Key Abstractions

**InterfaceStructure (`quickice/structure_generation/types.py:348`):**
- Purpose: Central data structure carrying combined ice+water+guest atom positions plus metadata for downstream steps.
- Pattern: Dataclass with ordered position regions: `positions[0:ice_atom_count]` = ice, `[ice_atom_count:ice_atom_count+water_atom_count]` = water, then guests. Carries optional solute_* and custom_molecule_* fields (default empty/None) populated by downstream inserters/exporters via duck-typing (CP-01).
- Examples: built in `quickice/structure_generation/modes/slab.py::assemble_slab`, `pocket.py::assemble_pocket`, `piece.py::assemble_piece`; wrapped from `HydrateStructure` in `quickice/cli/pipeline.py`; mutated via duck-typing in `quickice/cli/pipeline.py` (~lines 780-832) and `quickice/gui/main_window.py` (lines 948, 980).

**Structure Dataclasses (`quickice/structure_generation/types.py`, 1346 lines):**
- Purpose: Typed results passed between steps.
- Examples: `MoleculeIndex` (63), `Candidate` (224), `GenerationResult` (255), `InterfaceConfig` (278), `InterfaceStructure` (348), `CageGuestAssignment` (442), `GuestDescriptor` (482), `HydrateConfig` (514), `IonConfig` (824), `IonStructure` (838), `SoluteConfig` (892), `SoluteStructure` (921), `CustomMoleculeConfig` (965), `CustomMoleculeStructure` (1022), `HydrateLatticeInfo` (1091), `HydrateStructure` (1212, with `to_candidate()`).
- Constants colocated: `WATER_VOLUME_NM3 = 0.0299` (line 39), `WATER_ATOMS_PER_MOLECULE = 4` (line 22), `MOLECULE_TYPE_INFO`, `HYDRATE_LATTICES`, `GUEST_MOLECULES`, `detect_atoms_per_molecule()`. Use these constants; never hardcode `0.0299`, `4`, or moleculetype names.

**Inserters (return-NEW, never-mutate):**
- Purpose: Place molecules/ions into a liquid region, returning a new structure dataclass; the input is never mutated.
- Examples: `quickice/structure_generation/ion_inserter.py::IonInserter.replace_water_with_ions` (returns `IonStructure`), `insert_ions`; `quickice/structure_generation/solute_inserter.py::SoluteInserter.insert_solutes` (returns `SoluteStructure`, builds fresh `new_interface = InterfaceStructure(...)` carrying forward custom attrs); `quickice/structure_generation/custom_molecule_inserter.py::CustomMoleculeInserter.place_random` / `place_custom` → `CustomMoleculeStructure`.
- Pattern: Initialize `cKDTree`/`ion_tree`/`buffer_tree` as `None`; rebuild ONLY after a successful placement (never on rejection). Solute batches main-tree rebuilds every `_SOLUTE_BATCH_SIZE = 8` successful placements.

**Lazy module-attribute import handle (`quickice/structure_generation/ion_inserter.py:37`):**
- Purpose: `cKDTree = None` at module top with a `global cKDTree; if cKDTree is None: from scipy.spatial import cKDTree` prologue at call sites (line ~316).
- Pattern: This is deliberately a real module attribute (NOT a function-local import) because the scancode TREE regression tests patch `quickice.structure_generation.ion_inserter.cKDTree` to track rebuilds — a function-local import would bypass the patch. Preserve this shape when editing. `overlap_resolver.py` uses plain function-local scipy imports (no patching dependency).

**MoleculetypeRegistry (`quickice/structure_generation/moleculetype_registry.py:13`):**
- Purpose: Unique GROMACS moleculetypes naming to distinguish same molecule from different sources.
- Pattern: `register_hydrate_guest(mol)` → `f"{mol}_H"` (e.g. `CH4_H`); `register_liquid_solute(mol)` → `f"{mol}_L"` (e.g. `CH4_L`); `register_custom_molecule(user_name)` → unique name with collision counter; `RESERVED_NAMES` (line 35, includes `CH4_H`/`CH4_L`/`THF_H`/`THF_L`) rejects collisions. Suffixes kept ≤5 chars for GRO-format compatibility. Never hardcode `CH4_H`/`CH4_L` — always go through the registry.

**TIP4P-ICE Constants (`quickice/output/_constants.py`, re-exported via `quickice/output/_shared.py` and `quickice/output/gromacs_writer.py`):**
- Purpose: Single source of truth for TIP4P-ICE LJ params + atom charges.
- Examples: `TIP4P_ICE_OW_SIGMA`, `TIP4P_ICE_OW_EPSILON`, `TIP4P_ICE_HW_CHARGE`, `TIP4P_ICE_MW_CHARGE`, `TIP4P_ICE_ALPHA`, `TIP4P_ICE_SETTLE_DOH`, `TIP4P_ICE_SETTLE_DHH`; plus `_registry` singleton (`MoleculetypeRegistry`). Import via `from quickice.output.gromacs_writer import TIP4P_ICE_OW_SIGMA, TIP4P_ICE_OW_EPSILON`. Never hardcode these values. Verify against `quickice/data/tip4p-ice.itp` or Abascal et al. 2005 (DOI: 10.1063/1.1931662).

**`_write_top_defaults` (`quickice/output/_shared.py:65`):**
- Purpose: Single emitter for the GROMACS `[defaults]` block. CRITICAL: always writes comb-rule=2 (Lorentz-Berthelot, AMBER/GAFF2 convention). Never use comb-rule=1. All 6 TOP writers call this helper.

**Output Writer Facade (`quickice/output/gromacs_writer.py`):**
- Purpose: Single import surface for all GROMACS writers; re-exports per-structure writers + shared helpers. Downstream code does `from quickice.output.gromacs_writer import write_ion_gro_file, TIP4P_ICE_OW_SIGMA, ...`.
- Backed by: `ice_writer.py`, `interface_writer.py`, `multi_molecule_writer.py`, `ion_writer.py`, `custom_writer.py`, `solute_writer.py`, `_gro_format.py`, `_shared.py` (→ `_constants`, `_atomtypes`, `_pbc`, `_itp`, `_guest`, `_tip4p`).

**Workers (GUI background threads):**
- Purpose: Run GenIce2 / interface / ion generation off the UI thread; emit Qt signals.
- Examples: `quickice/gui/workers.py::GenerationWorker` + `InterfaceGenerationWorker` (QObject + `moveToThread` pattern); `quickice/gui/hydrate_worker.py::HydrateWorker` (direct `QThread` subclass — ACCEPTED design decision, do not refactor); inline `IonInsertionWorker` in `quickice/gui/main_window.py:45` (also direct `QThread` subclass, mirrors `HydrateWorker`).

**PEP 562 lazy re-export packages (slow-gui-startup fix):**
- Purpose: Keep package-level imports off the startup path. Both `quickice/gui/__init__.py` and `quickice/structure_generation/__init__.py` define a `_EXPORT_TO_MODULE` name→submodule map resolved through module-level `__getattr__` (import on first attribute access, cached in `globals()`), with `__dir__` exposing the union.
- Why: the eager `structure_generation/__init__.py` previously pulled the whole chain (generator → genice2 + networkx, interface_builder → water_density → iapws, ion_inserter/overlap_resolver → scipy.spatial) for any submodule import — ~0.5 s on both CLI and GUI startup.
- Side effect: names previously listed in `__all__` but missing from eager imports (`IonConfig`, `IonStructure` — they live in `types.py`) are now actually importable from `quickice.structure_generation`.
- Corollary: NEW code must import from the defining submodule (`from quickice.structure_generation.types import X`) or add the name to `_EXPORT_TO_MODULE` if the package-level access is needed.
- Related shims: `quickice/gui/phase_diagram_widget.py` keeps a lightweight `__getattr__` (lines ~226-232) forwarding `PhaseDiagramCanvas`/`PhaseDetector` to `quickice.gui.phase_diagram_canvas`, so legacy `from quickice.gui.phase_diagram_widget import PhaseDiagramCanvas` still works without loading matplotlib at panel import time.

**Heavy GUI canvas split (`quickice/gui/phase_diagram_canvas.py`, 635 lines):**
- Purpose: Host the expensive matplotlib + shapely imports (≈0.3 s) away from the eagerly-imported panel module.
- Contains: `PhaseDetector` (line 36, shapely-polygon phase lookup), `PhaseDiagramCanvas` (line 286, `FigureCanvasQTAgg`).
- Pattern: `PhaseDiagramPanel` (`phase_diagram_widget.py`) imports this module LAZILY (only when the canvas is actually built, after the main window is shown). When adding heavy rendering, follow this split: lightweight panel module + lazy heavy canvas module.

**VTK availability gate (`quickice/gui/vtk_utils.py::is_vtk_available()`, line 958):**
- Purpose: Environment-based VTK usability check, shared by the 6 GUI viewer modules. Does NOT import VTK.
- Pattern: SSH-X11 heuristic — if `DISPLAY` contains `localhost`, VTK is only enabled when `QUICKICE_FORCE_VTK=true`; otherwise (local display or headless with `QT_QPA_PLATFORM=offscreen`) assume available. Result cached (`_vtk_available_cache`); `reset_vtk_available_cache()` (line 1001) exists for tests that monkeypatch env vars.
- Each viewer imports its own VTK modules inside `if is_vtk_available():` blocks. `vtk_utils.py` itself keeps ALL heavy imports (vtkmodules, scipy.spatial, structure types) inside function bodies / under `TYPE_CHECKING` — a top-level heavy import here would silently defeat every viewer's guard.

## Entry Points

**`quickice/entry.py::main(argv=None) -> int` (line 105):**
- Triggers: `python -m quickice` (`quickice/__main__.py`), `python quickice.py` (`quickice.py`), `python -m quickice.gui` indirectly via `run_app`.
- Responsibilities: Route to CLI/GUI/help. Routing priority: (1) no args → help (line 143); (2) `--help`/`-h` → argparse help (line 150); (3) `--version`/`-V` → argparse version (line 159); (4) `--gui` → check PySide6 (`_is_pyside6_available`) + display (`_has_display`), then `from quickice.gui.main_window import run_app; run_app()` (line 168); (5) `--cli` → strip flag, `from quickice.main import main as cli_main; cli_main()` (line 181); (6) pipeline flags detected by `_has_pipeline_flags` → implicit CLI (line 190); (7) else → help (line 197).

**`quickice/main.py::main() -> int` (line 23):**
- Triggers: `entry.main()` when CLI mode selected.
- Responsibilities: Parse args (`get_arguments`); if pipeline flags present, delegate to `CLIPipeline(args).execute()`; else run ice-only legacy workflow (generate → rank → export PDB/diagram, optional GROMACS).

**`CLIPipeline.execute()` (`quickice/cli/pipeline.py:154`):**
- Triggers: `quickice/main.py:45` when pipeline flags detected.
- Responsibilities: Ordered step execution (source → interface → custom → solute → ion → export), fail-fast.

**`quickice/gui/main_window.py::run_app()` (line 2287):**
- Triggers: `entry.main()` when `--gui` selected; also `python -m quickice.gui`.
- Responsibilities: Configure OpenGL for remote displays (`_configure_opengl_for_remote`, line 2260), create `QApplication`, instantiate `MainWindow`, run Qt event loop.

## Error Handling

**Strategy:** Fail-fast with typed exceptions; CLI returns exit codes, GUI emits error signals and shows dialogs.

**Patterns:**
- CLI pipeline: each step returns `int` (0 success, non-zero failure). Steps catch typed exceptions and report via `report_progress(...)` to stderr + `logger.error`. `_run_export_step` and `_run_custom_step` catch `(OSError, ValueError)` / `FileNotFoundError` / `InsertionError`. AGENTS.md rule: NO bare `except Exception` in `quickice/cli/pipeline.py` core pipeline code (use `except (ValueError, OSError)` or more specific). GUI code may use broad catches for user-facing workflows (see `HydrateWorker.run`).
- `_validate_hydrate_atom_counts` (`cli/pipeline.py:33`) replaces a stripped `assert` (CRIT-04): uses real `if ...: raise ValueError` so it stays active under `python -O`.
- Core generation: `InterfaceGenerationError` (in `quickice/structure_generation/errors.py`) raised by `validate_interface_config` and the modes; `StructureGenerationError`, `UnsupportedPhaseError` for phase issues; `InsertionError` (`custom_molecule_inserter.py`) for placement failures.
- Phase lookup: `UnknownPhaseError` / `PhaseMappingError` (`quickice/phase_mapping/errors.py`).
- Path security: SEC-04/SEC-05 reject input/output paths resolving outside cwd via `Path.is_relative_to(cwd)` in `cli/pipeline.py` and `output/orchestrator.py`.

## Cross-Cutting Concerns

**Logging:** stdlib `logging.getLogger(__name__)` per module (e.g. `cli/pipeline.py`, `output/gromacs_writer.py`, `structure_generation/moleculetype_registry.py`, `gui/vtk_utils.py`). CLI also prints `[PROGRESS] ...` to stderr via `report_progress` for user feedback, distinct from logger.

**Validation:**
- Input validation: `quickice/validation/validators.py` functions used as argparse `type=` callbacks (CLI) and `quickice/gui/validators.py` (GUI inline field validation).
- Config validation: dataclass `__post_init__` (e.g. `InterfaceConfig.__post_init__` in `types.py` validates `overlap_threshold` range; `HydrateConfig.__post_init__` synthesizes legacy fields).
- Pre-generation validation: `validate_interface_config(config, candidate)` in `interface_builder.py` raises `InterfaceGenerationError` before expensive generation.
- Output validation: `output/validator.py::validate_space_group`, `check_atomic_overlap` invoked by `output_ranked_candidates`.

**Authentication:** None (offline scientific tool; no auth/network).

**Reproducibility:** `seed` threaded through `InterfaceConfig.seed`, `IonInserter(seed)`, `SoluteInserter(seed)`, `CustomMoleculeInserter(seed)`, and GenIce2 generation. `random.Random(seed)` per inserter (NOT global `random.seed`).

**Path containment (security):** All file inputs (`--custom-gro`, `--custom-itp`, `--custom-positions-file`) and `--output` must resolve under cwd; enforced in `cli/pipeline.py` and `output/orchestrator.py`. CSV row cap `MAX_CSV_ROWS = 10000` (`cli/pipeline.py:21`).

**Lazy imports (cross-cutting, startup-critical):**
- PySide6 probing: `entry.py` uses `importlib.util.find_spec('PySide6')` — never imports.
- GenIce2: `HydrateStructureGenerator._ensure_genice_import` (`hydrate_generator.py:67`) lazily imports GenIce2 under a thread-safe lock; numeric lattice names (`16`, `17`) loaded via `genice2.plugin.safe_import` at generation time (line 255-261), not the import dict.
- scipy: function-local imports in `overlap_resolver.py`; module-attribute `cKDTree = None` handle in `ion_inserter.py` (see Key Abstractions).
- VTK/matplotlib: all `vtkmodules` imports in `vtk_utils.py`, viewer modules, and `export.py` live inside function/method bodies or `if is_vtk_available():` blocks; `export.py` imports matplotlib `Figure` inside methods (comment at line 15). `phase_diagram_canvas.py` is only imported when the canvas is built.
- Package `__init__` lazy re-exports: `quickice/gui/__init__.py` and `quickice/structure_generation/__init__.py` (see Key Abstractions). Rule for new code: never add a heavy top-level import to any module reachable from GUI/CLI startup — put it inside the function that needs it, and label with the AGENTS.md lazy-import comment.

---

*Architecture analysis: 2026-10-15*
