# Architecture Research: Interface Generation Integration

**Domain:** Computational Chemistry / Ice Structure Visualization  
**Researched:** 2026-04-08  
**Confidence:** HIGH  

## Executive Summary

This document specifies how ice-water interface generation integrates with QuickIce's existing MVVM architecture. The core finding is that interface generation follows the identical pattern as existing ice generation—Worker runs in QThread, MainViewModel manages lifecycle, Services provide business logic—with only the service layer requiring new components. No changes to existing GenIce integration, VTK viewer, or ViewModel signal architecture are required. The integration adds new components in parallel with existing ones, minimizing risk to existing functionality.

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VIEW LAYER (GUI)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │   InputPanel        │  │   ViewerPanel       │  │   PhaseDiagramPanel │ │
│  │   (T, P, N inputs)  │  │   (VTK viewport)    │  │   (phase diagram)   │ │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘ │
│             │                        │                        │             │
│             └────────────────────────┼────────────────────────┘             │
│                                      │                                      │
├──────────────────────────────────────┼──────────────────────────────────────┤
│                              VIEWMODEL LAYER                                │
│  ┌──────────────────────────────────▼──────────────────────────────────┐    │
│  │                        MainViewModel                                 │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │    │
│  │  │  Signals: generation_started/complete/error (existing)        │ │    │
│  │  │  Signals: interface_started/complete/error (NEW)              │ │    │
│  │  │  Methods: start_generation() / start_interface_generation()   │ │    │
│  │  └─────────────────────────────────────────────────────────────────┘ │    │
│  └──────────────────────────────────┬──────────────────────────────────┘    │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                                       │ QThread lifecycle
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              WORKER LAYER                                    │
│  ┌───────────────────────┐        ┌───────────────────────────────────────┐  │
│  │   GenerationWorker    │        │   InterfaceGenerationWorker (NEW)    │  │
│  │   (existing)          │        │   - Same signal pattern              │  │
│  │   - phase lookup      │        │   - Calls InterfaceGenerator         │  │
│  │   - GenIce generation │        │   - Returns InterfaceCandidate       │  │
│  │   - ranking           │        └───────────────────────────────────────┘  │
│  └───────────────────────┘                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Service calls
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE LAYER                                   │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌────────────────┐   │
│  │   IceStructureGenerator│  │   InterfaceGenerator  │  │  ExportService │   │
│  │   (existing)          │  │   (NEW)               │  │  (existing)    │   │
│  │   - wraps GenIce2     │  │   - generates liquid  │  │  - PDB export  │   │
│  │   - pure ice output   │  │   - assembles layers  │  │  - GROMACS     │   │
│  └───────────────────────┘  └───────────────────────┘  └────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│                           ┌─────────────────────┐                           │
│                           │  LiquidGenerator    │                           │
│                           │  (NEW - sub-module) │                           │
│                           │  - random positions │                           │
│                           │  - TIP4P water      │                           │
│                           └─────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ External library
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL DEPENDENCIES                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   GenIce2       │  │   VTK           │  │   NumPy/SciPy              │  │
│  │   (ice crystals)│  │   (rendering)   │  │   (numerical operations)   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation | Modified? |
|-----------|----------------|----------------|------------|
| MainViewModel | Manages UI state, worker lifecycle, signal emission | PySide6 QObject with signals | YES - add new signals/methods |
| GenerationWorker | Runs ice generation pipeline in QThread | QObject with run() method | NO - existing |
| InterfaceGenerationWorker | Runs interface generation in QThread | QObject with run() method | NEW |
| IceStructureGenerator | Wraps GenIce2 for pure ice generation | Class with generate_all() | NO - existing |
| InterfaceGenerator | Assembles ice + liquid into interface structure | Class with generate() | NEW |
| LiquidGenerator | Generates liquid water configurations | Sub-module of interface | NEW |
| MolecularViewerWidget | Renders molecular structures | VTK-based QWidget | YES - add phase coloring |
| ExportService | Handles PDB/GROMACS file export | Multiple exporter classes | NO - add interface support |

## Recommended Project Structure

```
quickice/
├── gui/
│   ├── viewmodel.py           # MODIFIED: Add interface signals/methods
│   ├── workers.py             # MODIFIED: Add InterfaceGenerationWorker
│   ├── main_window.py         # MODIFIED: Add interface mode UI controls
│   ├── molecular_viewer.py    # MODIFIED: Add phase-based coloring
│   └── export.py              # MODIFIED: InterfaceCandidate handling
│
├── structure_generation/
│   ├── generator.py           # NO CHANGE: Existing IceStructureGenerator
│   ├── interface.py           # NEW: InterfaceGenerator class
│   ├── liquid.py              # NEW: LiquidGenerator sub-module
│   ├── types.py               # MODIFIED: Add InterfaceCandidate
│   └── __init__.py            # MODIFIED: Export new classes
│
├── ranking/
│   └── types.py               # NO CHANGE: Existing types sufficient
│
└── output/
    ├── orchestrator.py        # MODIFIED: Add interface output handling
    └── gromacs_writer.py      # NO CHANGE: Works with both Candidate types
```

### Structure Rationale

- **gui/workers.py modification:** Adding InterfaceGenerationWorker in same file as GenerationWorker keeps thread management centralized. Both workers share identical signal patterns, making this the most maintainable approach.
- **structure_generation/interface.py:** New top-level module (not sub-directory) signals that this is a first-class feature, not an afterthought. The module contains InterfaceGenerator and helper classes.
- **structure_generation/liquid.py:** Separate from interface.py for single-responsibility—liquid generation could potentially be reused in other contexts.
- **structure_generation/types.py modification:** Adding InterfaceCandidate as a new dataclass alongside existing Candidate maintains type hierarchy clarity.
- **gui/viewmodel.py modification:** Adding signals/methods rather than creating a separate ViewModel preserves the single-source-of-truth pattern for UI state.

## Architectural Patterns

### Pattern 1: Worker Thread Pattern (Existing - No Change)

**What:** QObject worker runs in dedicated QThread, emitting signals for progress updates.  
**When to use:** Any computationally intensive operation that would block the main GUI thread.  
**Trade-offs:** Ensures responsive UI but requires careful signal/slot thread affinity management.

**Example:**
```python
# From existing gui/workers.py - pattern reused for interface generation
class GenerationWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)  # GenerationResult
    error = Signal(str)
    
    def run(self):
        try:
            self.status.emit("Starting...")
            self.progress.emit(10)
            # ... computation ...
            self.finished.emit(GenerationResult(success=True, result=result))
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(GenerationResult(success=False, error=str(e)))
```

**Reuse for Interface:** InterfaceGenerationWorker follows identical signature pattern.

### Pattern 2: Service Layer Abstraction (Existing - No Change)

**What:** Business logic isolated in service classes, called by workers. Workers handle threading; services handle computation.  
**When to use:** Any operation requiring external libraries (GenIce2) or complex logic.  
**Trade-offs:** Clean separation enables testing and reuse, but adds indirection.

**Example:**
```python
# From existing structure_generation/generator.py
class IceStructureGenerator:
    def __init__(self, phase_info: dict, nmolecules: int):
        self.phase_id = phase_info["phase_id"]
        self.lattice_name = get_genice_lattice_name(self.phase_id)
        # ...
    
    def generate_all(self, n_candidates: int = 10) -> list[Candidate]:
        # Complex GenIce2 interaction here
        pass
```

**Reuse for Interface:** New InterfaceGenerator follows identical pattern.

### Pattern 3: ViewModel Signal Forwarding (Existing - No Change)

**What:** Worker signals connect to ViewModel slots, which re-emit for View consumption. ViewModel is intermediary, not consumer.  
**When to use:** When View needs to react to worker progress without direct coupling.  
**Trade-offs:** Decouples worker from View but adds indirection; enables ViewModel to transform data before emission.

**Example:**
```python
# From existing gui/viewmodel.py - pattern reused for interface
@Slot(int)
def _on_progress(self, value: int):
    """Handle worker progress signal - forward to View."""
    self.generation_progress.emit(value)

@Slot(object)
def _on_finished(self, result: GenerationResult):
    """Handle worker finished signal - forward to View."""
    self._is_generating = False
    self.ui_enabled_changed.emit(True)
    if result.success:
        self.generation_complete.emit(result.result)
    else:
        self.generation_error.emit(result.error or "Unknown error")
```

**Reuse for Interface:** Add similar slots/handlers for interface signals.

### Pattern 4: Phase-Aware Visualization (NEW)

**What:** Viewer distinguishes between ice and liquid regions through atom-level phase identification.  
**When to use:** When rendering heterogeneous structures with distinct regions.  
**Trade-offs:** Requires extending atom data structures but provides clear visual distinction.

**Example:**
```python
# Conceptual extension to molecular_viewer.py
class MolecularViewerWidget:
    def set_candidate(self, candidate: Candidate) -> None:
        mol = candidate_to_vtk_molecule(candidate)
        
        # NEW: If candidate has phase info, apply phase-based coloring
        if hasattr(candidate, 'phase_regions'):
            self._apply_phase_coloring(candidate, mol)
        
        self._mapper.SetInputData(mol)
        self.reset_camera()
        self.render_window.Render()
    
    def _apply_phase_coloring(self, candidate, mol):
        """Color atoms by phase region (ice vs liquid)."""
        # Ice phase: blue/cyan tones (existing)
        # Liquid phase: different hue or transparency
        pass
```

## Data Flow

### Flow 1: Existing Ice Generation (Unchanged)

```
User Input (temperature, pressure, nmolecules)
    │
    ▼
MainViewModel.start_generation(temperature, pressure, nmolecules)
    │
    ├─► Creates GenerationWorker(temperature, pressure, nmolecules)
    │       │
    │       ▼
    │   GenerationWorker.run()
    │       │
    │       ├─► lookup_phase(temperature, pressure)
    │       │       │
    │       │       ▼
    │       │   Returns: phase_info dict
    │       │
    │       ├─► generate_candidates(phase_info, nmolecules)
    │       │       │
    │       │       ▼
    │       │   IceStructureGenerator.generate_all()
    │       │       │
    │       │       ▼
    │       │   Returns: list[Candidate]
    │       │
    │       └─► rank_candidates(candidates)
    │               │
    │               ▼
    │           Returns: RankingResult
    │
    │       Emits: progress(0-100), status(message), finished(result)
    │
    ▼
MainViewModel slots forward signals
    │
    ▼
View (MainWindow) updates:
    - ProgressPanel shows progress
    - ViewerPanel displays ranked_candidates[0]
    - Generation complete message
```

### Flow 2: NEW Interface Generation

```
User Input (ice_phase, ice_nmolecules, liquid_nmolecules, orientation)
    │
    ▼
MainViewModel.start_interface_generation(ice_phase, ice_n, liquid_n, orientation)
    │
    ├─► Creates InterfaceGenerationWorker(InterfaceConfig(...))
    │       │
    │       ▼
    │   InterfaceGenerationWorker.run()
    │       │
    │       ├─► InterfaceGenerator.generate(config)
    │       │       │
    │       │       ├─► IceStructureGenerator(phase_info, ice_n)
    │       │       │       │
    │       │       │       ▼
    │       │       │   Returns: ice_candidate
    │       │       │
    │       │       ├─► LiquidGenerator.generate(liquid_n, density, cell)
    │       │       │       │
    │       │       │       ▼
    │       │       │   Returns: liquid_positions, liquid_atom_names
    │       │       │
    │       │       └─► InterfaceAssembler.assemble(ice_candidate, liquid)
    │       │               │
    │       │               ▼
    │       │           Returns: InterfaceCandidate
    │       │
    │       └─► (Optional) No ranking needed for MVP - direct output
    │
    │       Emits: progress(0-100), status(message), finished(result)
    │
    ▼
MainViewModel slots forward signals
    │
    ▼
View (MainWindow) updates:
    - ProgressPanel shows progress
    - ViewerPanel displays InterfaceCandidate with phase coloring
    - Interface generation complete message
```

### State Management

```
┌─────────────────────────────────────────────────────────────────┐
│                     MainViewModel State                         │
├─────────────────────────────────────────────────────────────────┤
│  _worker: Optional[GenerationWorker]          (existing)       │
│  _thread: Optional[QThread]                   (existing)       │
│  _is_generating: bool                         (existing)       │
│  _last_ranking_result: Optional[RankingResult] (existing)      │
│                                                              NEW│
│  _interface_worker: Optional[InterfaceGenerationWorker]        │
│  _last_interface_result: Optional[InterfaceCandidate]          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Signals emitted
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Connected Slots                            │
├─────────────────────────────────────────────────────────────────┤
│  View (MainWindow):                                            │
│    - generation_started → disable inputs, show progress        │
│    - generation_progress → update progress bar                 │
│    - generation_status → update status text                    │
│    - generation_complete → enable inputs, show result          │
│    - generation_error → show error dialog                      │
│                                                              NEW│
│    - interface_started → disable inputs, show progress         │
│    - interface_progress → update progress bar                  │
│    - interface_status → update status text                     │
│    - interface_complete → enable inputs, show result           │
│    - interface_error → show error dialog                       │
└─────────────────────────────────────────────────────────────────┘
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single MainViewModel instance is sufficient. Interface generation runs in worker thread, does not block UI. |
| 1k-100k users | Same architecture. Interface generation is fast (seconds), not a bottleneck. Consider caching common configurations. |
| 100k+ users | Consider: (1) Background queue for batch interface generation, (2) Template library for instant lookup of common cases. Not currently needed. |

### Scaling Priorities

1. **First bottleneck:** Interface generation time (rule-based is fast; MD relaxation would be slow). Current approach generates in seconds—no optimization needed.

2. **Second bottleneck:** VTK rendering of large interface structures (thousands of atoms). Consider level-of-detail rendering if this becomes an issue.

3. **Third bottleneck:** Template library growth. If hundreds of templates stored, consider database-backed storage instead of Python modules.

## Anti-Patterns

### Anti-Pattern 1: Creating Separate ViewModel for Interface

**What people do:** Create a new InterfaceViewModel instead of extending MainViewModel.  
**Why it's wrong:** Creates two sources of truth for UI state. Both ViewModels would need to coordinate on enabling/disabling UI elements.  
**Do this instead:** Add interface signals and methods to existing MainViewModel. This preserves single-source-of-truth and follows existing pattern.

### Anti-Pattern 2: Running Interface Generation in Main Thread

**What people do:** Call InterfaceGenerator directly from button click handler.  
**Why it's wrong:** Interface generation involves NumPy operations that will freeze GUI for seconds.  
**Do this instead:** Always use InterfaceGenerationWorker in QThread, following existing GenerationWorker pattern.

### Anti-Pattern 3: Modifying Existing Viewer for Interface-Only

**What people do:** Create a separate viewer widget for interfaces instead of extending existing MolecularViewerWidget.  
**Why it's wrong:** Duplicates VTK setup code, breaks dual-viewer functionality, inconsistent UX.  
**Do this instead:** Extend MolecularViewerWidget with phase-aware rendering that handles both Candidate and InterfaceCandidate.

### Anti-Pattern 4: Skipping Interface Validation

**What people do:** Assume rule-generated interfaces are physically valid without checks.  
**Why it's wrong:** Interface may have overlapping atoms, unrealistic densities, or broken hydrogen bonds.  
**Do this instead:** Run validation checks (atomic overlap, density, interface continuity) and warn users. Reuse existing validator infrastructure where possible.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GenIce2 | Direct import in worker run() | Already integrated; InterfaceGenerator calls IceStructureGenerator which uses it. No changes needed. |
| VTK | QVTKRenderWindowInteractor | Already integrated; MolecularViewerWidget handles rendering. Phase coloring added without changing rendering pipeline. |
| GROMACS writers | Direct function calls | Existing write_gro_file() works with Candidate; verify it works with InterfaceCandidate or add adapter. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| View ↔ ViewModel | Signals/Slots | New interface signals connect to View slots exactly like existing generation signals. |
| ViewModel ↔ Worker | Signal emission | InterfaceGenerationWorker emits same signal types as GenerationWorker. ViewModel slots forward identically. |
| Worker ↔ Service | Direct method call | InterfaceGenerationWorker calls InterfaceGenerator.generate() synchronously within run(). |
| Service ↔ Service | Composition | InterfaceGenerator composes IceStructureGenerator + LiquidGenerator + InterfaceAssembler. |

### Specific Integration Points (Modified Components)

| Component | Integration Point | Change Type |
|-----------|-------------------|-------------|
| gui/viewmodel.py | add_interface_generation() method | ADD new method |
| gui/viewmodel.py | add interface signals | ADD signals |
| gui/viewmodel.py | add _on_interface_finished() slot | ADD slot |
| gui/workers.py | add InterfaceGenerationWorker class | ADD class |
| gui/workers.py | add InterfaceConfig, InterfaceGenerationResult | ADD dataclasses |
| gui/main_window.py | add interface mode toggle (checkbox/mode selector) | ADD UI element |
| gui/main_window.py | connect ViewModel interface signals to slots | ADD connections |
| gui/molecular_viewer.py | add set_interface_candidate() method | ADD method |
| gui/molecular_viewer.py | add _apply_phase_coloring() private method | ADD method |
| structure_generation/types.py | add InterfaceCandidate dataclass | ADD class |
| structure_generation/types.py | add InterfaceConfig dataclass | ADD class |
| structure_generation/interface.py | add InterfaceGenerator class | ADD module |
| structure_generation/liquid.py | add LiquidGenerator class | ADD module |
| structure_generation/__init__.py | export new classes | ADD exports |

## Build Order

### Phase 1: Core Infrastructure (Days 1-3)

**Goal:** Get interface generation working end-to-end without GUI integration.

1. **structure_generation/types.py** — Add InterfaceCandidate, InterfaceConfig dataclasses
2. **structure_generation/liquid.py** — Implement LiquidGenerator for random water positions
3. **structure_generation/interface.py** — Implement InterfaceGenerator that composes ice + liquid
4. **gui/workers.py** — Add InterfaceGenerationWorker with same signal pattern as GenerationWorker
5. **Quick test:** Run worker in isolation, verify InterfaceCandidate output

**Rationale:** Build service layer first, isolated from GUI. This enables unit testing without Qt event loop.

### Phase 2: ViewModel Integration (Days 3-4)

**Goal:** Connect worker to ViewModel, enable signal flow.

1. **gui/viewmodel.py** — Add interface signals: interface_started, interface_progress, interface_status, interface_complete, interface_error
2. **gui/viewmodel.py** — Add start_interface_generation() method
3. **gui/viewmodel.py** — Add _on_interface_finished(), _on_interface_error() slots
4. **Quick test:** Verify signals emit correctly from ViewModel

**Rationale:** ViewModel changes are low-risk additions. Signals follow existing pattern exactly.

### Phase 3: View Integration (Days 4-6)

**Goal:** Connect ViewModel to View, enable user interaction.

1. **gui/main_window.py** — Add mode selector (Ice Generation vs Interface Generation radio buttons)
2. **gui/main_window.py** — Update input panel to show relevant fields for each mode
3. **gui/main_window.py** — Connect ViewModel interface signals to View slots
4. **gui/molecular_viewer.py** — Add set_interface_candidate() with phase coloring

**Rationale:** View changes require UI understanding. Build incrementally, test each connection.

### Phase 4: Export and Polish (Days 6-8)

**Goal:** Complete feature with export support.

1. **gui/export.py** — Verify PDB/GROMACS exporters handle InterfaceCandidate (or add adapter)
2. **gui/main_window.py** — Add export buttons for interface mode
3. **Testing:** End-to-end test: generate interface → view in 3D → export to file
4. **Validation:** Check interface has no atomic overlaps, reasonable density

**Rationale:** Export is the completion criteria for usable feature. Validate before calling done.

## Sources

- **QuickIce source code:** gui/viewmodel.py, gui/workers.py, structure_generation/generator.py — Verified existing MVVM patterns
- **GenIce2 documentation:** https://pypi.org/project/GenIce/ — Confirmed ice-only generation capability
- **Previous interface research:** .planning/research/ARCHITECTURE_INTERFACE.md — Comprehensive approach analysis
- **PySide6 documentation:** QThread worker pattern — Standard Qt async pattern

---

*Architecture research for: Ice-Water Interface Generation Integration*  
*Researched: 2026-04-08*  
*Confidence: HIGH - Integration follows identical patterns to existing ice generation, no architectural uncertainty*