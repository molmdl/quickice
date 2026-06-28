# Domain Pitfalls: Data Flow Migration

**Domain:** GUI architecture migration (PySide6 + VTK)
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Decomposing MainWindow Before PipelineSession

**What goes wrong:** If you extract PipelineManager, ExportManager, etc. from MainWindow while the 9 `_current_*` attributes still live on MainWindow, every extracted manager needs a reference to MainWindow to read state. This reproduces the god-object pattern across 4 files instead of 1.

**Why it happens:** It feels natural to start decomposition by extracting the "easiest" concern (e.g., export logic). But export logic reads `_current_interface_result`, `_current_ion_result`, etc. — which are on MainWindow. So the extracted ExportManager gets `parent: MainWindow` and calls `parent._current_*`. Now you have distributed coupling.

**Consequences:**
- Managers depend on MainWindow internals, not on a shared state model
- PipelineSession becomes impossible to introduce without rewriting all managers
- Tests can't instantiate managers without a full MainWindow

**Prevention:** ALWAYS introduce PipelineSession first (Phase 0). Managers receive PipelineSession, not MainWindow. This is a hard dependency.

**Detection:** If any manager file contains `self._parent._current_`, the decomposition is wrong.

### Pitfall 2: Breaking the Solute→Ion Attribute Propagation Chain

**What goes wrong:** The current code propagates solute and custom molecule attributes onto InterfaceStructure via duck-typing (setting dataclass fields). If the PipelineSession doesn't preserve this propagation chain, IonStructure exports will silently drop solutes and custom molecules.

**Why it happens:** The propagation chain is complex:
1. Interface → Custom: sets `interface.custom_molecule_*` attributes
2. Custom → Solute: SoluteInserter reads CustomMoleculeStructure, writes to SoluteStructure
3. Solute → Ion: MainWindow reads `_current_solute_result`, sets `interface.solute_*` attributes, THEN calls `insert_ions(interface, ...)`

If PipelineSession only stores step outputs but doesn't chain them properly, the ion step will receive a "clean" InterfaceStructure without solute/custom attributes, and the exported .gro/.top files will be wrong.

**Consequences:** Silent data loss in GROMACS exports. Ions exported without solutes. Solute exports missing custom molecules. The .top [molecules] section will be wrong.

**Prevention:** 
- PipelineManager's `run_step(ION)` must read from the correct upstream step output
- Auto-chaining (from CLI FIX #9) must be replicated: if SoluteStep has output, use it as source; else if CustomStep has output, use it; else use InterfaceStep
- Each step's `input` is determined by PipelineManager, not by user selection
- Integration test: run full pipeline (Ice→Interface→Custom→Solute→Ion), export ion structure, verify .top [molecules] section includes all molecule types

**Detection:** Run the full chain and compare .top output with current code output. Any missing molecule type is a regression.

### Pitfall 3: HydrateWorker Subclassing QThread

**What goes wrong:** AGENTS.md explicitly states: "HydrateWorker subclasses QThread directly (not migrated to QObject+moveToThread) — do not 'fix' this." But PipelineManager needs a unified worker interface. If we "fix" HydrateWorker to use QObject+moveToThread, we risk breaking hydrate generation.

**Why it happens:** The AGENTS.md instruction exists because HydrateWorker works as-is. Migrating it to QObject+moveToThread during the pipeline refactor introduces risk with no user-visible benefit.

**Consequences:** HydrateWorker can't be managed by PipelineManager's standard worker lifecycle (which assumes QObject+moveToThread pattern). Workaround needed.

**Prevention:** PipelineManager's `_create_worker()` method returns a worker adapter that wraps HydrateWorker differently:

```python
def _create_worker(self, kind, **kwargs):
    if kind == StepKind.SOURCE_HYDRATE:
        # HydrateWorker subclasses QThread — special handling
        worker = HydrateWorker(kwargs['config'])
        # Connect signals directly (no moveToThread needed)
        worker.progress_updated.connect(...)
        worker.generation_complete.connect(...)
        worker.generation_error.connect(...)
        return worker  # It IS the thread
    else:
        # Standard QObject+moveToThread pattern
        worker = StandardWorker(kind, **kwargs)
        return worker
```

**Detection:** Hydrate generation must still work after PipelineManager integration. Test with `sI` lattice + `ch4` guest.

### Pitfall 4: Viewer State Loss During Unified Viewer Migration

**What goes wrong:** When replacing 6 separate viewers with 1 unified viewer, the current-viewer-per-tab state is lost. If a user has generated an interface in Tab 2, then switches to Tab 4 (Solute), the current viewer shows the interface structure. With a unified viewer, what gets shown?

**Why it happens:** Each tab currently has its own viewer that persists independently. Unified viewer needs to decide what to render when the user switches contexts.

**Consequences:** User sees wrong structure. "Where did my ions go?" — they're hidden because the unified viewer is showing the interface step's output, not the ion step's.

**Prevention:** 
- UnifiedViewerWidget always renders `PipelineSession.current_structure` (output of last enabled step)
- Actor groups for ALL completed steps are loaded simultaneously, with visibility controlled by the pipeline browser
- When user clicks a step in the pipeline browser, that step's actor group gets highlight/focus, others dim
- Camera reset preserves all actor groups

**Detection:** After migration, switching between steps should show all accumulated modifiers, not just the clicked step.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Signal/Slot Wiring Explosion During Dock Migration

**What goes wrong:** The current `_setup_connections()` method in MainWindow has 30+ signal/slot connections. When migrating from tabs to docks, each panel's signals need to be rewired from `self.tab_widget.currentChanged` to `dock_manager.active_step_changed`. Missing a connection causes a panel to become unresponsive.

**Prevention:** 
- Create a signal wiring checklist before Phase 3
- Use PipelineManager signals as the central routing point (panels → PipelineManager → ViewerManager)
- Each panel only emits configuration/intent signals, never directly modifies other panels
- Integration test: click every button in the GUI and verify the corresponding action fires

### Pitfall 6: Export Filename Convention Change

**What goes wrong:** The current per-tab export has specific filename conventions:
- Ice: `{phase}_{T}K_{P}MPa_c{rank}.gro`
- Interface: `interface_{mode}.gro`
- Ion: `ions_{na_count}na_{cl_count}cl.gro`
- Solute: `solute_{type}_{count}molecules.gro`
- Custom: `custom_{moleculetype}_{count}molecules.gro`

If PipelineSession-based export uses different conventions (e.g., `step_1.gro`, `step_2.gro`), users' downstream GROMACS workflows break.

**Prevention:** ExportManager preserves the exact same filename conventions per structure type. The step kind → filename mapping is explicit:

```python
STEP_FILENAME_PATTERNS = {
    StepKind.SOURCE_ICE: "{phase}_{T}K_{P}MPa_c{rank}.gro",
    StepKind.SOURCE_HYDRATE: "hydrate_{lattice}_{guest}.gro",
    StepKind.INTERFACE: "interface_{mode}.gro",
    StepKind.CUSTOM_MOLECULE: "custom_{moleculetype}_{count}molecules.gro",
    StepKind.SOLUTE: "solute_{type}_{count}molecules.gro",
    StepKind.ION: "ions_{na}na_{cl}cl.gro",
}
```

**Detection:** Compare exported filenames before and after migration.

### Pitfall 7: QDockWidget saveState Requires objectName

**What goes wrong:** `QMainWindow.saveState()` / `restoreState()` only work if every QDockWidget has a unique `objectName`. If names are missing or duplicated, the layout isn't restored on next launch.

**Prevention:** 
- Every QDockWidget gets a unique `objectName` at creation
- Naming convention: `"dock_ice_params"`, `"dock_hydrate_params"`, `"dock_interface_params"`, `"dock_modifiers_params"`, `"dock_results"`, `"dock_log"`, `"dock_phase_diagram"`
- Test: save state, close, reopen, verify layout

**Detection:** Run saveState/restoreState roundtrip test.

### Pitfall 8: Synchronous Inserter Steps Blocking UI

**What goes wrong:** SoluteInserter and IonInserter currently run synchronously on the main thread (no QThread worker). In the integrated model, if PipelineManager runs them on the main thread, the UI freezes during insertion.

**Why it happens:** These inserters are fast (< 1 second for typical structures), so the original code didn't bother with background threads. But for large structures (millions of atoms), they could take longer.

**Prevention:** 
- Short term: Wrap both in QThread workers (SoluteWorker, IonWorker) during Phase 1
- Long term: PipelineManager always runs steps on background threads
- Fallback: For steps that complete in < 100ms, run synchronously but show a progress indicator

**Detection:** Time the inserters with large structures. If > 200ms, they need background threading.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 9: Tab Index Constants Becoming Meaningless

**What goes wrong:** The `TabIndex` enum (ICE=0, HYDRATE=1, etc.) is used throughout the codebase for routing (export, tab changes, etc.). When switching to docks, these constants have no meaning.

**Prevention:** Replace TabIndex with StepKind everywhere. StepKind is layout-agnostic (works in both tabs and docks).

### Pitfall 10: Missing `--layout` Command-Line Flag

**What goes wrong:** If both layouts coexist but there's no way to switch, users can't opt into the new layout.

**Prevention:** Add `--layout integrated` flag to `entry.py` routing. Default stays `tabs` during migration, then flips to `integrated`.

### Pitfall 11: Phase Diagram Widget Size in Dock

**What goes wrong:** The PhaseDiagramPanel currently takes ~550px of horizontal space in the Ice tab. As a floating QDockWidget, it may appear at a different size, making the diagram harder to read.

**Prevention:** Set minimum size on the dock widget. Use `setFloating(True)` with a reasonable default size.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 0 (PipelineSession) | Backward compat properties return stale data | Mirror every `_current_*` set with PipelineStep update; add assertion tests |
| Phase 1 (Decomposition) | Managers create circular dependencies | Enforce: managers only receive PipelineSession, never other managers |
| Phase 2 (Unified Viewer) | Actor group ordering (z-fighting) | Use `vtkRenderer.SetLayer()` for 2D overlays; `vtkAssembly` for hierarchical grouping |
| Phase 3 (Docks) | Signal wiring breaks during migration | Create wiring checklist; add per-panel integration tests |
| Phase 4 (Tool modes) | VTK widget event conflicts with TrackballCamera | Configure event translators per Wave 1 tool-mode-system research |
| Coexistence | `--layout tabs` accumulates tech debt | Timebox to 1 release; don't add features to tabs path |

## Sources

- Source code analysis of `quickice/gui/main_window.py` (2126 lines): 9 state attributes, 30+ signal connections, 7 exporter classes
- Source code analysis of `quickice/cli/pipeline.py` (849 lines): auto-chaining logic (FIX #9), attribute propagation (FIX #4)
- Source code analysis of `quickice/structure_generation/types.py` (835 lines): 6 structure dataclasses, CP-01 duck-typing verification
- AGENTS.md constraints: HydrateWorker QThread, comb-rule=2, no bare except
- Wave 1 research: single-viewport-arch, dock-panel-system, tool-mode-system
