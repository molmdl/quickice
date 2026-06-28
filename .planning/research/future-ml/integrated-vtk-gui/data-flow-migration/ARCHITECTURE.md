# Architecture: Data Flow Migration — Tabs to Integrated VTK GUI

**Domain:** GUI architecture migration (PySide6 + VTK)
**Researched:** 2026-06-28

## Recommended Architecture: PipelineSession + Linear Modifier Stack

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      MainWindow (~200 lines)                │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │Pipeline  │  │Viewer     │  │Export     │  │Dock      │ │
│  │Manager   │  │Manager    │  │Manager    │  │Manager   │ │
│  └────┬─────┘  └────┬──────┘  └────┬──────┘  └────┬─────┘ │
│       │             │             │              │        │
│       ▼             ▼             ▼              ▼        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              PipelineSession (shared state)          │  │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ │  │
│  │  │Source   │→│Modifier1 │→│Modifier2│→│Modifier3 │ │  │
│  │  │(Ice/Hyd)│ │(Interface)│ │(Custom) │ │(Solute)  │ │  │
│  │  └─────────┘ └──────────┘ └─────────┘ └──────────┘ │  │
│  │                                    ↓                 │  │
│  │                              ┌──────────┐            │  │
│  │                              │Modifier4 │            │  │
│  │                              │(Ion)    │            │  │
│  │                              └──────────┘            │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                 │
│                          ▼                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           UnifiedViewerWidget (central VTK)          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │  │
│  │  │Ice      │ │Interface │ │Modifiers │  ←vtkAssembly│  │
│  │  │Actors   │ │Actors    │ │Actors    │   groups     │  │
│  │  └──────────┘ └──────────┘ └──────────┘             │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1. PipelineSession Data Model

The PipelineSession replaces the 9 `_current_*` attributes on MainWindow with a single typed object that owns all pipeline state.

```python
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum, auto

class StepKind(Enum):
    SOURCE_ICE = auto()
    SOURCE_HYDRATE = auto()
    INTERFACE = auto()
    CUSTOM_MOLECULE = auto()
    SOLUTE = auto()
    ION = auto()

@dataclass
class PipelineStep:
    """One step in the linear pipeline.
    
    Each step has: input (previous step's output), parameters, output.
    Steps are ordered by physical constraints and cannot be reordered.
    """
    kind: StepKind
    enabled: bool = True
    parameters: dict = field(default_factory=dict)
    output: Any = None          # The structure dataclass (InterfaceStructure, IonStructure, etc.)
    error: Optional[str] = None
    is_running: bool = False
    
    @property
    def has_output(self) -> bool:
        return self.output is not None and self.error is None

@dataclass
class PipelineSession:
    """Central state model replacing MainWindow's 9 `_current_*` attributes.
    
    Implements OVITO-style linear modifier stack:
      Source (Ice or Hydrate) → Interface → Custom → Solute → Ion
    
    The session tracks:
    - Which steps are active/enabled
    - Each step's parameters and output structure
    - The current "effective" structure (output of the last enabled step)
    - Export history
    """
    steps: list[PipelineStep] = field(default_factory=list)
    source_type: str = "ice"  # "ice" or "hydrate"
    temperature: float = 0.0
    pressure: float = 0.0
    
    # Ranking result (Ice tab only — candidates before interface)
    ranking_result: Any = None  # RankingResult
    
    def __post_init__(self):
        """Initialize with default step ordering."""
        if not self.steps:
            self.steps = [
                PipelineStep(kind=StepKind.SOURCE_ICE),
                PipelineStep(kind=StepKind.INTERFACE),
                PipelineStep(kind=StepKind.CUSTOM_MOLECULE, enabled=False),
                PipelineStep(kind=StepKind.SOLUTE, enabled=False),
                PipelineStep(kind=StepKind.ION, enabled=False),
            ]
    
    @property
    def current_structure(self) -> Any:
        """Get the output of the last completed enabled step.
        
        This is the 'effective' structure — what the viewer should display
        and what export uses by default.
        """
        for step in reversed(self.steps):
            if step.enabled and step.has_output:
                return step.output
        return None
    
    def get_step(self, kind: StepKind) -> Optional[PipelineStep]:
        """Get a step by kind."""
        for step in self.steps:
            if step.kind == kind:
                return step
        return None
    
    def get_source_step(self) -> Optional[PipelineStep]:
        """Get the active source step (ICE or HYDRATE)."""
        for step in self.steps:
            if step.kind in (StepKind.SOURCE_ICE, StepKind.SOURCE_HYDRATE):
                if step.enabled:
                    return step
        return None
    
    def get_interface_step(self) -> Optional[PipelineStep]:
        """Convenience: get the interface step."""
        return self.get_step(StepKind.INTERFACE)
    
    def set_source_hydrate(self):
        """Switch source from ice to hydrate."""
        # Disable ice source, add hydrate source
        ice_step = self.get_step(StepKind.SOURCE_ICE)
        if ice_step:
            ice_step.enabled = False
        # Add hydrate source if not present
        if not self.get_step(StepKind.SOURCE_HYDRATE):
            self.steps.insert(0, PipelineStep(kind=StepKind.SOURCE_HYDRATE))
        self.source_type = "hydrate"
    
    def set_source_ice(self):
        """Switch source from hydrate to ice."""
        hydrate_step = self.get_step(StepKind.SOURCE_HYDRATE)
        if hydrate_step:
            hydrate_step.enabled = False
        ice_step = self.get_step(StepKind.SOURCE_ICE)
        if ice_step:
            ice_step.enabled = True
        self.source_type = "ice"
    
    # --- Backward-compatible accessors (bridge pattern during migration) ---
    
    @property
    def current_result(self):
        """Backward compat: _current_result → ranking_result."""
        return self.ranking_result
    
    @property
    def current_interface_result(self):
        """Backward compat: _current_interface_result → interface step output."""
        step = self.get_interface_step()
        return step.output if step else None
    
    @property
    def current_hydrate_result(self):
        """Backward compat: _current_hydrate_result → hydrate source output."""
        step = self.get_step(StepKind.SOURCE_HYDRATE)
        return step.output if step else None
    
    @property
    def current_custom_molecule_result(self):
        """Backward compat: _current_custom_molecule_result → custom step output."""
        step = self.get_step(StepKind.CUSTOM_MOLECULE)
        return step.output if step else None
    
    @property
    def current_solute_result(self):
        """Backward compat: _current_solute_result → solute step output."""
        step = self.get_step(StepKind.SOLUTE)
        return step.output if step else None
    
    @property
    def current_ion_result(self):
        """Backward compat: _current_ion_result → ion step output."""
        step = self.get_step(StepKind.ION)
        return step.output if step else None
```

### 2. MainWindow Decomposition

#### Current structure (2126 lines, 1 class)

MainWindow currently handles:
- **Pipeline orchestration** (~500 lines): `_on_generate_clicked`, `_on_interface_generate`, `_on_insert_ions`, `_on_insert_solutes`, `_on_custom_generate_clicked`, `_on_hydrate_generate_clicked`
- **State storage** (~70 lines): 9 `_current_*` attributes + 7 exporter instances
- **Signal wiring** (~80 lines): `_setup_connections` with 30+ signal/slot connections
- **Export logic** (~300 lines): 7 export handlers routing to 7 exporter classes
- **Viewer updates** (~200 lines): result → viewer rendering calls
- **Menu/shortcut setup** (~100 lines): menu bar, keyboard shortcuts
- **Utility helpers** (~80 lines): `_on_diagram_selected`, `_on_input_changed`, `_on_phase_info`
- **Tab change handling** (~30 lines): `_on_tab_changed`

#### Proposed decomposition (4 managers + slim MainWindow)

| Component | Lines (est.) | Responsibility |
|-----------|-------------|----------------|
| **MainWindow** | ~200 | Menu bar, window setup, orchestrates managers |
| **PipelineManager** | ~350 | Pipeline step execution, worker lifecycle, state transitions |
| **ViewerManager** | ~250 | Unified viewer updates, actor group management, camera |
| **ExportManager** | ~300 | Export routing, per-step export, file dialogs |
| **DockManager** | ~200 | QDockWidget creation, tabification, contextual switching |

**MainWindow becomes:**

```python
class MainWindow(QMainWindow):
    """Slim orchestrator — delegates to concern managers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Central pipeline state (THE key change)
        self._pipeline = PipelineSession()
        
        # Concern managers
        self._pipeline_mgr = PipelineManager(self._pipeline, self)
        self._viewer_mgr = ViewerManager(self._pipeline, self)
        self._export_mgr = ExportManager(self._pipeline, self)
        self._dock_mgr = DockManager(self._pipeline, self)
        
        # Wire managers to each other
        self._pipeline_mgr.step_completed.connect(self._viewer_mgr.update_from_step)
        self._pipeline_mgr.step_completed.connect(self._dock_mgr.on_step_completed)
        self._export_mgr.export_requested.connect(self._pipeline_mgr.on_export)
```

#### Manager Responsibilities

**PipelineManager:**
- Owns all QThread workers (GenerationWorker, InterfaceGenerationWorker, HydrateWorker, CustomMoleculeWorker)
- Updates PipelineSession on step completion
- Emits `step_completed(StepKind)` signal
- Handles cancellation per-step or full-pipeline
- Manages progress reporting: "Step 2/5: Building Interface..."

**ViewerManager:**
- Owns the single UnifiedViewerWidget (central VTK widget)
- Maps PipelineStep outputs to vtkAssembly actor groups
- Handles actor visibility toggling (show/hide per modifier layer)
- Camera reset on structure changes
- Viewport export delegation

**ExportManager:**
- Routes export requests to the correct exporter based on selected step
- Supports both "export current" and "export specific step"
- Owns all 7 exporter instances
- Handles file dialogs

**DockManager:**
- Creates and manages all QDockWidget instances
- Handles tabification, contextual raise_()
- saveState/restoreState with proper objectName
- Feature flag for tabs vs docks layout

### 3. Linear Modifier Stack Design

#### Step dependency graph (physically constrained)

```
Source(ICE) ─┐
             ├─→ Interface ─→ Custom ─┐
Source(HYD) ─┘                      ├─→ Solute ─→ Ion
                                     ┘
```

Rules:
1. **Steps cannot be reordered**: Interface always follows Source; Solute/Ion always follow Interface
2. **Steps can be toggled off**: Skip Custom, skip Solute, skip both — Ion uses Interface directly
3. **Source switching**: Ice ↔ Hydrate are mutually exclusive source steps
4. **Auto-chaining** (from CLI pipeline FIX #9): If upstream steps produced results, downstream steps auto-detect them

#### Step parameter → output type mapping

| Step | Parameter Type | Output Type | VTK Actor Group |
|------|---------------|-------------|-----------------|
| SOURCE_ICE | `{T, P, nmolecules}` | `RankingResult` (candidates) | Ice actors (dual-view candidates) |
| SOURCE_HYDRATE | `HydrateConfig` | `HydrateStructure` | Hydrate actors |
| INTERFACE | `InterfaceConfig` | `InterfaceStructure` | Ice bonds + water bonds + unit cell |
| CUSTOM_MOLECULE | `CustomMoleculeConfig` | `CustomMoleculeStructure` | Custom molecule ball-and-stick |
| SOLUTE | `SoluteConfig` | `SoluteStructure` | Solute ball-and-stick |
| ION | `IonConfig` | `IonStructure` | Na+ gold spheres + Cl- green spheres |

#### Toggle behavior

When a step is disabled:
- Its output is cleared (set to None)
- Downstream steps that depended on it fall back to the previous enabled step's output
- The viewer hides the corresponding actor group
- Export skips that step in per-step export mode

Example: Custom disabled, Solute enabled:
```
Source → Interface (skip Custom) → Solute → Ion
```
Solute uses Interface output directly (same as `--solute-source interface` in CLI).

### 4. CP-01 Duck-Typing Resolution

**Finding:** The "duck-typing" described in AGENTS.md (CP-01) is actually setting **dataclass fields with defaults**, not arbitrary runtime attributes. Verified by source analysis:

All 13 runtime-attribute-sets on `interface` in MainWindow:
- `solute_type`, `solute_positions`, `solute_atom_names`, `solute_n_molecules`, `solute_molecule_indices`, `solute_registry` → ALL are InterfaceStructure dataclass fields
- `custom_molecule_positions`, `custom_molecule_atom_names`, `custom_molecule_count`, `custom_molecule_atom_count`, `custom_molecule_moleculetype`, `custom_gro_path`, `custom_itp_path` → ALL are InterfaceStructure dataclass fields

**Resolution in PipelineSession:** The modifier stack eliminates the need to set attributes on InterfaceStructure at all. Each step produces its own typed output:
- `CustomMoleculeStep.output` is a `CustomMoleculeStructure` (contains `interface_structure` as a field)
- `SoluteStep.output` is a `SoluteStructure` (contains `interface_structure` as a field)
- `IonStep` reads from the previous step's output, not from a mutated InterfaceStructure

The duck-typing was a workaround for the flat `_current_*` attribute model. With PipelineSession's step-chain, each step owns its typed result, and the next step reads it via `session.get_step(StepKind.SOLUTE).output`.

**Migration path:** During Phase 0, add `to_interface_structure()` methods on SoluteStructure and CustomMoleculeStructure that produce the same "enriched" InterfaceStructure (for backward compatibility with existing exporters). In Phase 1+, the exporters are refactored to accept step outputs directly.

### 5. Export Workflow in Integrated Model

**Current model (tab-based):**
- Active tab determines export: Ctrl+S from Ice tab exports ice, from Ion tab exports ions
- 7 separate exporter classes, each with its own file dialog

**Proposed model (pipeline-based):**

**Option B (RECOMMENDED): Export any pipeline step's output.**

```python
class ExportManager:
    def export_current(self):
        """Ctrl+S: Export the current_structure (last enabled step's output)."""
        structure = self._pipeline.current_structure
        if structure is None:
            QMessageBox.warning(self, "No Data", "Generate a structure first.")
            return
        self._export_structure(structure)
    
    def export_step(self, kind: StepKind):
        """Export a specific step's output (from pipeline browser)."""
        step = self._pipeline.get_step(kind)
        if step is None or not step.has_output:
            QMessageBox.warning(self, "No Data", f"No {kind.name} result available.")
            return
        self._export_structure(step.output)
    
    def _export_structure(self, structure):
        """Route to the correct exporter based on structure type."""
        if isinstance(structure, RankingResult):
            self._ice_exporter.export(structure)
        elif isinstance(structure, InterfaceStructure):
            self._interface_exporter.export(structure)
        elif isinstance(structure, CustomMoleculeStructure):
            self._custom_exporter.export(structure)
        elif isinstance(structure, SoluteStructure):
            self._solute_exporter.export(structure)
        elif isinstance(structure, IonStructure):
            self._ion_exporter.export(structure)
        elif isinstance(structure, HydrateStructure):
            self._hydrate_exporter.export(structure)
```

The pipeline browser (a QDockWidget showing the modifier stack) lets users click any step to:
1. See that step's parameters
2. See that step's output summary
3. Export that step's output

**Menu structure:**
- File → Export Current (Ctrl+S): exports `current_structure`
- File → Export As → [Ice / Hydrate / Interface / Custom / Solute / Ion]: exports specific step

### 6. Worker Lifecycle in Integrated Model

**Current:** 4 worker types, managed in 3 different patterns:
1. **GenerationWorker** / **InterfaceGenerationWorker**: QObject+moveToThread, managed by MainViewModel
2. **HydrateWorker**: Subclasses QThread directly (AGENTS.md says NOT to fix this), managed by MainWindow
3. **CustomMoleculeWorker**: QObject+moveToThread, managed by MainWindow

**Proposed:** PipelineManager unifies all worker management.

```python
class PipelineManager(QObject):
    step_started = Signal(StepKind)
    step_progress = Signal(StepKind, int)    # StepKind, percentage
    step_status = Signal(StepKind, str)      # StepKind, message
    step_completed = Signal(StepKind)         # StepKind
    step_error = Signal(StepKind, str)       # StepKind, error message
    pipeline_progress = Signal(int, str)     # overall %, description
    
    def __init__(self, pipeline: PipelineSession, parent=None):
        super().__init__(parent)
        self._pipeline = pipeline
        self._active_worker = None
        self._active_thread = None
        self._active_step_kind = None
    
    def run_step(self, kind: StepKind, **kwargs):
        """Execute a pipeline step in a background thread."""
        step = self._pipeline.get_step(kind)
        step.is_running = True
        step.error = None
        self._active_step_kind = kind
        self.step_started.emit(kind)
        
        # Create appropriate worker
        worker = self._create_worker(kind, **kwargs)
        thread = QThread()
        worker.moveToThread(thread)
        
        # Wire signals
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self._on_step_finished(kind, result))
        worker.error.connect(lambda msg: self._on_step_error(kind, msg))
        worker.progress.connect(lambda pct: self._on_step_progress(kind, pct))
        worker.status.connect(lambda msg: self._on_step_status(kind, msg))
        
        # Cleanup
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._active_worker = worker
        self._active_thread = thread
        thread.start()
    
    def cancel_step(self):
        """Cancel the currently running step."""
        if self._active_thread and self._active_thread.isRunning():
            self._active_thread.requestInterruption()
            self._active_thread.quit()
            self._active_thread.wait(100)
        self._finalize_step(self._active_step_kind, cancelled=True)
    
    def _on_step_finished(self, kind, result):
        """Store result in PipelineSession and emit step_completed."""
        step = self._pipeline.get_step(kind)
        step.output = result.result if hasattr(result, 'result') else result
        step.is_running = False
        self.step_completed.emit(kind)
        self._update_pipeline_progress()
    
    def _update_pipeline_progress(self):
        """Calculate overall pipeline progress (Step X/N: description)."""
        enabled_steps = [s for s in self._pipeline.steps if s.enabled]
        completed = sum(1 for s in enabled_steps if s.has_output)
        total = len(enabled_steps)
        pct = int(completed / total * 100) if total > 0 else 0
        desc = f"Step {completed}/{total} complete"
        self.pipeline_progress.emit(pct, desc)
```

**Key change:** SoluteInserter and IonInserter currently run synchronously (no worker). They should be wrapped in workers for consistency, but this is a lower priority since they're fast (< 1 second typically).

### 7. Migration Phases (Detailed)

#### Phase 0: PipelineSession Extraction (NO GUI CHANGE)

**Goal:** Introduce PipelineSession alongside existing `_current_*` attributes.

**Steps:**
1. Create `quickice/gui/pipeline_session.py` with PipelineSession and PipelineStep
2. Add `self._pipeline = PipelineSession()` to MainWindow.__init__
3. After each `_current_*` attribute is set, also update the corresponding PipelineStep:
   ```python
   # Existing:
   self._current_interface_result = result
   # Add:
   self._pipeline.get_step(StepKind.INTERFACE).output = result
   ```
4. Add backward-compatible properties to PipelineSession (already designed above)
5. Add integration test: PipelineSession properties == MainWindow `_current_*` attributes

**Exit criteria:** All existing tests still pass. PipelineSession mirrors all `_current_*` state.

**Lines of code:** ~200 (PipelineSession) + ~30 (bridge lines in MainWindow) = ~230 lines

#### Phase 1: MainWindow Decomposition

**Goal:** Extract 4 concern-managers from MainWindow.

**Steps:**
1. Create `quickice/gui/pipeline_manager.py` (extract pipeline orchestration)
2. Create `quickice/gui/viewer_manager.py` (extract viewer update logic)
3. Create `quickice/gui/export_manager.py` (extract export routing)
4. Create `quickice/gui/dock_manager.py` (extract tab/dock management — initially just wraps QTabWidget)
5. Replace MainWindow's direct `_current_*` reads with `self._pipeline.*` reads
6. Replace direct viewer calls with `self._viewer_mgr.update_from_step(kind)`
7. Replace direct export calls with `self._export_mgr.export_step(kind)`

**Key invariant:** All managers receive PipelineSession, not MainWindow. They never reference `self._parent._current_*`.

**Exit criteria:** MainWindow < 300 lines. All existing functionality preserved. No GUI visible change.

**Lines of code:** ~1100 (managers) + ~-1800 (from MainWindow) = net ~-700 lines in MainWindow

#### Phase 2: UnifiedViewerWidget

**Goal:** Replace 6 separate VTK viewers with 1 central widget.

**Steps:**
1. Create `quickice/gui/unified_viewer.py` with single QVTKRenderWindowInteractor
2. Create `quickice/gui/actor_group.py` wrapper (wrapping vtkAssembly per Wave 1 findings)
3. Map each PipelineStep output type to an ActorGroup factory
4. ViewerManager.update_from_step(kind) creates/updates the corresponding ActorGroup
5. Visibility toggling: show/hide actor groups per modifier toggle
6. Dual-view replaced by `vtkRenderer.SetViewport()` (from single-viewport-arch research)
7. Remove individual viewer widgets (IonViewerWidget, SoluteViewerWidget, etc.)

**Exit criteria:** Single render window. All structure types renderable. Camera/reset works.

**Performance target:** Full interface structure (768 ice + 4000 water) in < 40ms (already verified by Wave 1).

#### Phase 3: QDockWidget Migration

**Goal:** Replace QTabWidget with dock panel layout.

**Steps:**
1. DockManager creates QDockWidgets with proper objectName (for saveState)
2. Tabify parameter docks: Ice, Hydrate, Interface, Modifiers (Solute/Ion/Custom combined)
3. Add Results dock (right), Log dock (bottom), Phase Diagram dock (floating)
4. Toolbar buttons raise_() tabified docks for contextual switching
5. Replace `tab_widget.currentIndex()` with active tool/dock state
6. Feature flag: `--layout tabs` vs `--layout integrated` (see Coexistence section)

**Exit criteria:** Dock layout matches proposed layout from dock-panel-system research. saveState/restoreState works.

#### Phase 4: Tool Mode System

**Goal:** Add toolbar + VTK interactor style switching.

**Steps:**
1. Create `quickice/gui/tool_mode_manager.py` (from tool-mode-system research)
2. Pre-built interactor styles: TrackballCamera, RegionSelect, CustomMoleculePlace
3. Toolbar mode buttons: View, Select, Place Custom, Measure
4. Mode switching changes interactor style AND raises corresponding parameter dock
5. VTK widgets (contour, bounded plane) for region selection

**Exit criteria:** At least 2 tool modes working (View + Custom Molecule Place). Contextual dock switching.

### 8. Coexistence: Tabs + Docks Layout Switch

**Verdict: YES, but with strict timebox.**

Both layouts can coexist using a feature flag in DockManager:

```python
class DockManager:
    def __init__(self, pipeline, parent, layout="tabs"):
        self._layout = layout
        if layout == "tabs":
            self._setup_tabs()  # Current QTabWidget layout
        else:
            self._setup_docks()  # New QDockWidget layout
```

**Code cost:**
- DockManager handles both paths: ~100 extra lines
- All other managers are layout-agnostic (they only see PipelineSession)
- Total cost: ~150 extra lines for the coexistence period

**Removal strategy:**
- Timebox coexistence to 1 release cycle
- After integrated layout is validated by users, remove `--layout tabs` flag
- The tabs path is NOT maintained with new features — it's strictly a rollback safety net

**Backward compatibility:**
- Keyboard shortcuts (Enter=generate, Escape=cancel, Ctrl+S=export) work identically in both layouts
- Export workflow is pipeline-based, not tab-based, so it's layout-agnostic
- The only behavioral difference is WHERE parameters appear (tab vs dock)

### 9. CLI Pipeline → PipelineSession Convergence

The CLI pipeline (`CLIPipeline` in `quickice/cli/pipeline.py`) already implements the same linear step chain with the same auto-chaining logic. PipelineSession should converge with it:

| CLIPipeline field | PipelineSession field | Status |
|-------------------|----------------------|--------|
| `_interface_result` | `steps[INTERFACE].output` | Converged |
| `_hydrate_result` | `steps[SOURCE_HYDRATE].output` | Converged |
| `_custom_result` | `steps[CUSTOM].output` | Converged |
| `_solute_result` | `steps[SOLUTE].output` | Converged |
| `_ion_result` | `steps[ION].output` | Converged |
| `_ice_candidate` | `steps[SOURCE_ICE].output` | Converged |

**Long-term goal:** PipelineSession becomes the shared state model between CLI and GUI, with CLIPipeline accepting a PipelineSession instead of managing its own `_current_*` attributes.

This is a post-migration cleanup — don't attempt during the dock migration phases.

## Sources

- Source code analysis: `quickice/gui/main_window.py` (2126 lines)
- Source code analysis: `quickice/gui/viewmodel.py` (276 lines)
- Source code analysis: `quickice/gui/workers.py` (225 lines)
- Source code analysis: `quickice/gui/export.py` (922 lines)
- Source code analysis: `quickice/structure_generation/types.py` (835 lines)
- Source code analysis: `quickice/cli/pipeline.py` (849 lines)
- Source code analysis: `quickice/gui/ion_viewer.py` (642 lines)
- Source code analysis: `quickice/gui/solute_viewer.py` (619 lines)
- Wave 1 sibling research: single-viewport-arch, dock-panel-system, tool-mode-system, comparative-analysis
