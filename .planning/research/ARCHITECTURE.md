# Architecture Research: GUI Integration with CLI Pipeline

**Domain:** Desktop GUI application integrating with existing CLI backend
**Project:** QuickIce v2.0 GUI Application
**Researched:** 2026-03-31
**Confidence:** HIGH

## Executive Summary

This document outlines the architecture for adding a GUI front-end to QuickIce's existing CLI pipeline. The key insight is that the GUI should call the existing Python modules directly (not invoke the CLI as a subprocess), maintaining a clean separation between presentation and business logic. The recommended pattern is **Model-View-ViewModel (MVVM)** with a dedicated backend service layer that wraps existing pipeline components.

## Current Architecture (CLI)

The existing pipeline follows a linear flow:

```
CLI Args → Validator → Phase Mapper → GenIce → Ranker → PDB Writer
```

Key modules:
- `quickice/cli/parser.py` — Argument parsing with validation
- `quickice/main.py` — CLI entry point orchestrating the pipeline
- `quickice/phase_mapping/` — T,P to ice phase mapping
- `quickice/structure_generation/generator.py` — GenIce wrapper for coordinate generation
- `quickice/ranking/` — Energy/density-based candidate ranking
- `quickice/output/orchestrator.py` — PDB writing and validation
- `quickice/output/phase_diagram.py` — Static matplotlib phase diagram generation

## Recommended Architecture (GUI)

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Application                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    View Layer (PyQt)                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │ MainWin  │  │PhaseDiag │  │3D Viewer │  │Progress │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘  │   │
│  └───────┼─────────────┼─────────────┼─────────────┼───────┘   │
│          │             │             │             │            │
│          ▼             ▼             ▼             ▼            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  ViewModel Layer                         │   │
│  │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐   │   │
│  │  │MainViewModel │  │DiagramVM    │  │StructureViewer│   │   │
│  │  └──────┬───────┘  └──────┬──────┘  └───────┬───────┘   │   │
│  └─────────┼─────────────────┼─────────────────┼───────────┘   │
│            │                 │                 │                │
│            ▼                 ▼                 ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Backend Service Layer (NEW)                │   │
│  │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐   │   │
│  │  │PipelineServ  │  │DiagramServ  │  │ViewerService  │   │   │
│  │  └──────────────┘  └─────────────┘  └───────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Existing CLI Modules (READ-ONLY)           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐   │   │
│  │  │Validator │  │PhaseMap  │  │GenIce  │  │ Ranker   │   │   │
│  │  └──────────┘  └──────────┘  └────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **GUI View Layer** | User interface, widgets, event handling | ViewModel via signals/slots |
| **ViewModel Layer** | UI state, command binding, data transformation | Services, Views via Qt signals |
| **PipelineService** | Wraps CLI modules, exposes async generation | PhaseMapper, Generator, Ranker |
| **DiagramService** | Interactive phase diagram with click selection | PhaseMapping lookup functions |
| **ViewerService** | 3D molecular structure rendering | Existing Candidate data structures |
| **Existing Modules** | Unchanged CLI business logic | Called directly by services |

### Data Flow

#### Flow 1: User Input to Structure Generation

```
1. User enters T, P, N in GUI text fields
2. MainViewModel validates input via PipelineService
3. PipelineService calls existing validators (quickice.validation)
4. On validation success:
   a. PhaseMapper returns phase_info for T,P
   b. DiagramService updates interactive diagram with selection point
   c. User clicks "Generate"
5. PipelineService.generate_async() runs in background thread:
   - Generate candidates (GenIce)
   - Rank candidates
   - Emit progress signals
6. On completion, emit results signal with ranked candidates
7. MainViewModel updates UI state
8. ViewerService loads top candidate for 3D display
```

#### Flow 2: Interactive Phase Diagram

```
1. DiagramService initializes static phase diagram from existing module
2. Makes diagram interactive (click-enabled)
3. On click at (T_click, P_click):
   - Look up phase via PhaseMapper.lookup_phase()
   - Update selection marker
   - Pre-fill T,P fields in main form
   - Show phase info tooltip
```

#### Flow 3: 3D Structure Viewing

```
1. ViewerService receives Candidate object from pipeline
2. Extracts positions, atom_names, cell from Candidate
3. Renders in 3D widget (PyMOL, nglview, or matplotlib 3D)
4. Supports rotation, zoom, atom selection
5. Exports to image file on user request
```

## Threading and Concurrency Model

### Recommended: Qt Threading with Worker Objects

For PyQt/PySide, the recommended pattern uses **QThread with worker objects**:

```python
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from quickice.validation.validators import validate_temperature, validate_pressure

class GenerationWorker(QObject):
    """Worker object that runs generation in a separate thread."""
    
    progress = pyqtSignal(int, str)  # (percent, status_message)
    result_ready = pyqtSignal(object)  # RankingResult
    error_occurred = pyqtSignal(str)   # error_message
    
    def __init__(self, temperature, pressure, nmolecules):
        super().__init__()
        self.temperature = temperature
        self.pressure = pressure
        self.nmolecules = nmolecules
    
    def run(self):
        """Execute generation pipeline in background thread."""
        try:
            # Step 1: Validate inputs (10%)
            self.progress.emit(10, "Validating inputs...")
            validate_temperature(self.temperature)
            validate_pressure(self.pressure)
            # (nmolecules validated in structure generation)
            
            # Step 2: Phase lookup (20%)
            self.progress.emit(20, "Looking up ice phase...")
            from quickice.phase_mapping import lookup_phase
            phase_info = lookup_phase(self.temperature, self.pressure)
            
            # Step 3: Generate candidates (70%)
            self.progress.emit(30, "Generating ice structures...")
            from quickice.structure_generation import generate_candidates
            gen_result = generate_candidates(
                phase_info=phase_info,
                nmolecules=self.nmolecules,
                n_candidates=10
            )
            self.progress.emit(70, f"Generated {len(gen_result.candidates)} candidates")
            
            # Step 4: Rank candidates (90%)
            self.progress.emit(80, "Ranking candidates...")
            from quickice.ranking import rank_candidates
            ranking_result = rank_candidates(candidates=gen_result.candidates)
            
            # Complete
            self.progress.emit(100, "Complete")
            self.result_ready.emit(ranking_result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
```

### Usage in ViewModel

```python
class MainViewModel(QObject):
    """Main view model coordinating generation."""
    
    generation_progress = pyqtSignal(int, str)
    generation_complete = pyqtSignal(object)
    generation_error = pyqtSignal(str)
    is_generating = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self._thread = None
        self._worker = None
    
    def start_generation(self, temperature, pressure, nmolecules):
        """Start async generation in background thread."""
        # Prevent concurrent generation
        if self._thread is not None and self._thread.isRunning():
            return
        
        # Create worker and thread
        self._worker = GenerationWorker(temperature, pressure, nmolecules)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        
        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self.is_generating.emit(True)
        self._thread.start()
    
    def _on_progress(self, percent, message):
        self.generation_progress.emit(percent, message)
    
    def _on_result(self, ranking_result):
        self.generation_complete.emit(ranking_result)
        self.is_generating.emit(False)
        self._thread.quit()
    
    def _on_error(self, error_msg):
        self.generation_error.emit(error_msg)
        self.is_generating.emit(False)
        self._thread.quit()
```

### Progress Integration with Existing Pipeline

For progress feedback during generation, wrap the generation step with progress callbacks:

```python
def generate_candidates_with_progress(phase_info, nmolecules, n_candidates, progress_callback):
    """Generate candidates with progress reporting."""
    generator = IceStructureGenerator(phase_info, nmolecules)
    candidates = []
    
    for i in range(n_candidates):
        seed = 1000 + i
        candidate = generator._generate_single(seed)
        candidates.append(candidate)
        
        # Report progress (30% to 70% range)
        progress = 30 + (i + 1) * 40 // n_candidates
        progress_callback(progress, f"Generating structure {i+1}/{n_candidates}")
    
    return candidates
```

## Integration Points with Existing Components

### Direct Module Import (Recommended)

The GUI should import existing modules directly, not invoke CLI:

```python
# WRONG: Subprocess invocation
import subprocess
result = subprocess.run(['python', 'quickice.py', '-T', '250', '-P', '100', '-N', '216'])

# RIGHT: Direct module import
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.ranking import rank_candidates

phase_info = lookup_phase(250, 100)
gen_result = generate_candidates(phase_info, 216, 10)
ranking_result = rank_candidates(gen_result.candidates)
```

### Validation Reuse

The GUI reuses all existing validation:

```python
from quickice.validation.validators import (
    validate_temperature,
    validate_pressure,
    validate_nmolecules
)

# In ViewModel
try:
    validate_temperature(user_input.temperature)
    validate_pressure(user_input.pressure)
    validate_nmolecules(user_input.nmolecules)
except ValueError as e:
    self.validation_error.emit(str(e))
```

### Phase Diagram Service

The existing `phase_diagram.py` generates static images. For the GUI, we need an interactive version:

```python
class DiagramService:
    """Service for interactive phase diagram."""
    
    def __init__(self):
        self._phase_data = {}  # Cache phase boundaries
    
    def get_phase_at(self, temperature, pressure):
        """Return phase ID for given T,P."""
        from quickice.phase_mapping import lookup_phase
        return lookup_phase(temperature, pressure)
    
    def get_diagram_data(self):
        """Return phase boundaries for interactive plotting."""
        # Reuse existing phase boundary calculations
        from quickice.phase_mapping import melting_pressure, solid_boundary
        # Return structured data for matplotlib interactive widget
        return self._phase_data
    
    def create_interactive_widget(self, parent):
        """Create Qt matplotlib widget for interactive diagram."""
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        
        fig = Figure()
        canvas = FigureCanvasQTAgg(fig)
        # Plot phase regions, make clickable
        return canvas
```

## New Components Needed

| Component | File Location | Purpose |
|-----------|--------------|---------|
| `gui/main_window.py` | `quickice/gui/` | Main application window |
| `gui/viewmodels/main_viewmodel.py` | `quickice/gui/viewmodels/` | Main window state and commands |
| `gui/viewmodels/diagram_viewmodel.py` | `quickice/gui/viewmodels/` | Phase diagram state |
| `gui/viewmodels/viewer_viewmodel.py` | `quickice/gui/viewmodels/` | 3D viewer state |
| `gui/services/pipeline_service.py` | `quickice/gui/services/` | Async pipeline wrapper |
| `gui/services/diagram_service.py` | `quickice/gui/services/` | Interactive diagram |
| `gui/services/viewer_service.py` | `quickice/gui/services/` | 3D rendering |
| `gui/widgets/phase_diagram_widget.py` | `quickice/gui/widgets/` | Interactive diagram widget |
| `gui/widgets/structure_viewer_widget.py` | `quickice/gui/widgets/` | 3D viewer widget |
| `gui/widgets/progress_panel.py` | `quickice/gui/widgets/` | Progress display |

## Build Order

### Phase 1: Infrastructure (Week 1)

1. Create `quickice/gui/` package structure
2. Add GUI dependencies to environment (PyQt6 or PySide6)
3. Create basic main window with input fields
4. Connect validation to ViewModel

### Phase 2: Service Layer (Week 2)

1. Implement `PipelineService` with thread-safe generation
2. Add progress signal integration
3. Create `DiagramService` for phase lookup
4. Test module import paths

### Phase 3: Interactive Features (Week 3)

1. Implement interactive phase diagram widget
2. Add click-to-select functionality
3. Integrate 3D viewer (matplotlib 3D or nglview)
4. Add structure rotation/zoom

### Phase 4: Polish (Week 4)

1. Add progress bar to main window
2. Implement save/export functionality
3. Add phase info dialog
4. System integration (window controls, menus)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Invoking CLI as Subprocess

**What:** Running `python quickice.py` via subprocess and parsing output
**Why bad:** Fragile (output format changes), loses typed objects, slow (process spawn)
**Instead:** Import modules directly

### Anti-Pattern 2: Blocking UI Thread

**What:** Running generation in main thread with `time.sleep()` for progress
**Why bad:** UI freezes, appears unresponsive, may trigger OS "not responding"
**Instead:** Use QThread with worker object

### Anti-Pattern 3: Tight Coupling to CLI Entry Point

**What:** GUI directly calls `quickice.main.main()`
**Why bad:** CLI main() includes print statements, sys.exit() calls, not designed for GUI
**Instead:** Call individual modules (phase_mapping, structure_generation, ranking)

### Anti-Pattern 4: Reimplementing Validation

**What:** Duplicating validation logic in GUI
**Why bad:** Inconsistency, extra maintenance burden
**Instead:** Import and call existing validators

## Scalability Considerations

| Concern | Current (CLI) | GUI Extension |
|---------|---------------|---------------|
| **Generation time** | Sequential | Add threading (already addressed in design) |
| **Memory (216 molecules)** | ~50MB | Add ~100MB for 3D viewer buffers |
| **UI responsiveness** | N/A | Worker thread pattern ensures <16ms frame time |
| **Phase diagram** | Static PNG | Interactive matplotlib in Qt canvas |

### Performance Targets

- **Startup time**: <2 seconds to main window
- **Generation start**: <500ms from button click to progress bar
- **3D viewer**: 60fps rotation for 216 molecules (648 atoms)
- **Memory**: <500MB total for typical workflow

## Sources

- [PyQt Threading Best Practices](https://doc.qt.io/qtforpython-6/overviews/qthread.html) — Official Qt documentation
- [Qt Model/View Programming](https://doc.qt.io/qt-6/model-view-programming.html) — MVVM pattern reference
- [Matplotlib in Qt](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html) — Interactive plots in PyQt
- [QuickIce Existing Modules](file://~/quickice/quickice/) — Current pipeline implementation

---

*Architecture research for: QuickIce v2.0 GUI Application*
*Researched: 2026-03-31*