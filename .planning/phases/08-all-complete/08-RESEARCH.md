# Phase 08: GUI Infrastructure + Core Input - Research

**Researched:** 2026-03-31
**Domain:** PySide6 Desktop GUI Development
**Confidence:** HIGH

## Summary

This phase implements the foundational GUI infrastructure for QuickIce using PySide6. Users can enter temperature, pressure, and molecule count parameters, trigger ice structure generation with progress feedback, and use keyboard shortcuts. The implementation uses MVVM architecture with QThread workers to keep the UI responsive during computation.

**Primary recommendation:** Use the worker-object pattern with QThread (not subclassing QThread), implement validation on Generate button click with inline error labels, use QMessageBox.critical() for error dialogs, and connect keyboard shortcuts via QAction or keyPressEvent override.

## Standard Stack

The established libraries/tools for PySide6 GUI development:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6-Essentials | >= 6.11.0 | Core Qt bindings | Qt Company official, LGPL licensed |
| PySide6-Addons | >= 6.11.0 | Additional widgets | Official Qt extensions |

### Installation
```bash
# As per context, NOT auto-installing - add to env.yml first
conda install pyside6=6.11.0
# OR
pip install PySide6>=6.11.0
```

### Alternative Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PySide6 | PyQt6 | PySide6 chosen (LGPL allows MIT bundling per STATE.md) |
| Worker QThread | QRunnable + QThreadPool | Worker QThread preferred for cancellation support |

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── gui/
│   ├── __init__.py
│   ├── main_window.py      # QMainWindow subclass
│   ├── view.py             # UI widgets and layout
│   ├── viewmodel.py        # Business logic and state
│   └── workers.py          # QThread worker classes
├── validation/
│   └── validators.py       # EXISTING - CLI validators
└── ... (existing modules)
```

### Pattern 1: MVVM with Worker Thread

**What:** Model-View-ViewModel pattern with background workers for computation
**When to use:** When computation may block UI (always for generation)

**Worker Class Structure:**
```python
# Source: Qt 6.11 Documentation - QThread Class
# https://doc.qt.io/qt-6/qthread.html

from PySide6.QtCore import QObject, Signal, QThread

class GenerationWorker(QObject):
    """Worker for running generation in background thread."""
    
    # Signals for progress updates
    progress = Signal(int)  # 0-100 percentage
    status = Signal(str)    # Status message
    finished = Signal(object)  # GenerationResult
    error = Signal(str)     # Error message
    cancelled = Signal()    # Cancellation confirmed
    
    def __init__(self, temperature, pressure, nmolecules):
        super().__init__()
        self._temperature = temperature
        self._pressure = pressure
        self._nmolecules = nmolecules
        self._is_cancelled = False
    
    def run(self):
        """Execute generation - runs in separate thread."""
        try:
            # Check for cancellation periodically
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            self.status.emit("Generating structure...")
            
            # Import and call existing quickice modules
            from quickice.phase_mapping import lookup_phase
            from quickice.structure_generation import generate_candidates
            
            # Phase lookup
            phase_info = lookup_phase(self._temperature, self._pressure)
            self.progress.emit(20)
            
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            # Generate candidates
            self.status.emit("Generating candidates...")
            gen_result = generate_candidates(
                phase_info=phase_info,
                nmolecules=self._nmolecules,
                n_candidates=10
            )
            self.progress.emit(60)
            
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            # Ranking
            self.status.emit("Ranking candidates...")
            from quickice.ranking import rank_candidates
            ranking_result = rank_candidates(candidates=gen_result.candidates)
            self.progress.emit(90)
            
            self.status.emit("Complete")
            self.progress.emit(100)
            self.finished.emit(ranking_result)
            
        except Exception as e:
            self.error.emit(str(e))
```

**Main Window Integration:**
```python
# Source: Qt 6.11 Documentation - QThread Class
# https://doc.qt.io/qt-6/qthread.html

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._thread = None
    
    def start_generation(self, temperature, pressure, nmolecules):
        """Start generation in background thread."""
        # Create worker
        self._worker = GenerationWorker(temperature, pressure, nmolecules)
        
        # Create thread
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        
        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._update_progress)
        self._worker.status.connect(self._update_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        
        # Cleanup on thread finish
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        # Start thread
        self._thread.start()
    
    def cancel_generation(self):
        """Cancel running generation."""
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
```

### Pattern 2: Input Validation with Inline Errors

**What:** Validate on Generate click, show inline error messages below each field
**When to use:** Per CONTEXT.md - validation errors appear on submit

**Implementation:**
```python
# Based on PySide6 QLineEdit and validation patterns

class InputValidator:
    """Reusable validation logic - wraps existing CLI validators."""
    
    @staticmethod
    def validate_temperature(value: str) -> tuple[bool, str]:
        """Validate temperature input.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            temp = float(value)
        except ValueError:
            return False, "Temperature must be a number"
        
        if temp < 0 or temp > 500:
            return False, "Temperature must be between 0 and 500 K"
        
        return True, ""
    
    @staticmethod
    def validate_pressure(value: str) -> tuple[bool, str]:
        """Validate pressure input.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            pressure = float(value)
        except ValueError:
            return False, "Pressure must be a number"
        
        if pressure < 0 or pressure > 10000:
            return False, "Pressure must be between 0 and 10000 bar"
        
        return True, ""
    
    @staticmethod
    def validate_nmolecules(value: str) -> tuple[bool, str]:
        """Validate molecule count input.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            float_val = float(value)
        except ValueError:
            return False, "Molecule count must be an integer"
        
        if float_val != int(float_val):
            return False, "Molecule count must be an integer"
        
        nmol = int(float_val)
        
        if nmol < 4:
            return False, "Molecule count must be at least 4"
        
        if nmol > 216:
            return False, "Molecule count must be at most 216"
        
        return True, ""
```

**UI Integration:**
```python
# Inline error labels below each QLineEdit

from PySide6.QtWidgets import QLabel, QLineEdit

class InputPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Temperature
        self.temp_label = QLabel("Temperature (K):")
        self.temp_input = QLineEdit()
        self.temp_error = QLabel()
        self.temp_error.setStyleSheet("color: red;")
        self.temp_error.hide()
        
        # Pressure  
        self.pressure_label = QLabel("Pressure (bar):")
        self.pressure_input = QLineEdit()
        self.pressure_error = QLabel()
        self.pressure_error.setStyleSheet("color: red;")
        self.pressure_error.hide()
        
        # Molecules
        self.mol_label = QLabel("Number of molecules:")
        self.mol_input = QLineEdit()
        self.mol_error = QLabel()
        self.mol_error.setStyleSheet("color: red;")
        self.mol_error.hide()
        
        # Add to layout with proper spacing
        layout.addWidget(self.temp_label)
        layout.addWidget(self.temp_input)
        layout.addWidget(self.temp_error)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.pressure_input)
        layout.addWidget(self.pressure_error)
        layout.addWidget(self.mol_label)
        layout.addWidget(self.mol_input)
        layout.addWidget(self.mol_error)
    
    def validate_all(self) -> bool:
        """Validate all inputs, show errors, return overall validity."""
        valid = True
        
        # Temperature
        valid_temp, temp_err = InputValidator.validate_temperature(
            self.temp_input.text()
        )
        self.temp_error.setText(temp_err)
        self.temp_error.setVisible(not valid_temp)
        if not valid_temp:
            valid = False
        
        # Pressure
        valid_pressure, pressure_err = InputValidator.validate_pressure(
            self.pressure_input.text()
        )
        self.pressure_error.setText(pressure_err)
        self.pressure_error.setVisible(not valid_pressure)
        if not valid_pressure:
            valid = False
        
        # Molecules
        valid_mol, mol_err = InputValidator.validate_nmolecules(
            self.mol_input.text()
        )
        self.mol_error.setText(mol_err)
        self.mol_error.setVisible(not valid_mol)
        if not valid_mol:
            valid = False
        
        return valid
```

### Pattern 3: Keyboard Shortcuts

**What:** Enter to generate, Escape to cancel
**When to use:** UX requirement UX-01

**Implementation via QAction:**
```python
# Source: Qt 6.11 Documentation - QWidget Class
# https://doc.qt.io/qt-6/qwidget.html

from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Enter to generate
        generate_action = QAction(self)
        generate_action.setShortcut(Qt.Key_Return)
        generate_action.triggered.connect(self._on_generate)
        self.addAction(generate_action)
        
        # Escape to cancel
        cancel_action = QAction(self)
        cancel_action.setShortcut(Qt.Key_Escape)
        cancel_action.triggered.connect(self._on_cancel)
        self.addAction(cancel_action)
```

### Pattern 4: Modal Error Dialog

**What:** Show error in modal dialog ensuring user sees it
**When to use:** When generation fails

**Implementation:**
```python
# Source: Qt 6.11 Documentation - QMessageBox Class
# https://doc.qt.io/qt-6/qmessagebox.html

from PySide6.QtWidgets import QMessageBox

def show_error_dialog(parent, title, message, details=None):
    """Show error dialog.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Main error message
        details: Optional detailed error text
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if details:
        msg_box.setDetailedText(details)
    
    msg_box.exec()

# Or use static method for simpler cases:
def show_error_simple(parent, title, message):
    QMessageBox.critical(parent, title, message)
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background threading | Custom thread management | QThread with worker object | Qt handles event loop, cancellation, signal/slot |
| Modal dialogs | Custom QDialog subclasses | QMessageBox | Platform-native look, accessibility, key handling |
| Progress indication | Custom progress widgets | QProgressBar | Platform styling, accessibility, consistent behavior |

**Key insight:** PySide6 provides robust, battle-tested solutions for all common GUI patterns. Custom implementations risk threading issues, accessibility problems, and platform inconsistencies.

## Common Pitfalls

### Pitfall 1: Blocking the Main Event Loop
**What goes wrong:** UI freezes during generation
**Why it happens:** Running GenIce in main thread blocks Qt event loop
**How to avoid:** Use QThread with worker object moved to thread
**Warning signs:** Window becomes unresponsive, "not responding" in task manager

### Pitfall 2: Improper Worker Cleanup
**What goes wrong:** Memory leaks, crashes on close
**Why it happens:** Worker object not deleted when thread finishes
**How to avoid:** Connect thread.finished to worker.deleteLater
```python
self._thread.finished.connect(self._worker.deleteLater)
self._thread.finished.connect(self._thread.deleteLater)
```

### Pitfall 3: Cross-Thread Signal Connections
**What goes wrong:** Slots not called, runtime errors
**Why it happens:** Missing Qt.QueuedConnection for cross-thread signals
**How to avoid:** PySide6 auto-detects, but be aware default works for cross-thread

### Pitfall 4: Validation Not Matching Requirements
**What goes wrong:** UI accepts invalid input or rejects valid input
**Why it happens:** Using wrong validation ranges
**How to avoid:** Use exact ranges from requirements:
- Temperature: 0-500 K (INPUT-01)
- Pressure: 0-10000 bar (INPUT-02) 
- Molecules: integer, max 216 (INPUT-03)

### Pitfall 5: Pressure Unit Mismatch
**What goes wrong:** Confusion between bar and MPa
**Why it happens:** CLI validators use MPa, requirements say bar
**How to avoid:** Per CONTEXT.md requirements say "bar", use bar in UI even if CLI uses MPa internally (convert display)

## Code Examples

### Progress Bar Integration
```python
from PySide6.QtWidgets import QProgressBar

class ProgressPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, text):
        self.status_label.setText(text)
    
    def reset(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
```

### Complete Generation Flow
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuickIce")
        self.setMinimumSize(400, 500)
        
        # Create panels
        self.input_panel = InputPanel()
        self.progress_panel = ProgressPanel()
        
        # Buttons
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.setEnabled(False)
        
        # Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addWidget(self.input_panel)
        layout.addWidget(self.progress_panel)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.cancel_btn)
        
        # Keyboard shortcuts
        self.setup_shortcuts()
    
    def _on_generate_clicked(self):
        if not self.input_panel.validate_all():
            return
        
        temperature = float(self.input_panel.temp_input.text())
        pressure = float(self.input_panel.pressure_input.text())
        nmolecules = int(self.input_panel.mol_input.text())
        
        self._set_generating_state(True)
        self.start_generation(temperature, pressure, nmolecules)
    
    def _on_cancel_clicked(self):
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
    
    def _set_generating_state(self, generating: bool):
        """Update UI for generation state."""
        self.generate_btn.setEnabled(not generating)
        self.cancel_btn.setEnabled(generating)
        self.input_panel.setEnabled(not generating)
        
        if generating:
            self.progress_panel.reset()
    
    def _on_finished(self, result):
        """Handle generation completion."""
        self._set_generating_state(False)
        self.progress_panel.update_status("Complete")
        # Continue to output phase or show results
    
    def _on_error(self, error_msg):
        """Handle generation error."""
        self._set_generating_state(False)
        show_error_dialog(
            self,
            "Generation Error",
            "Failed to generate ice structure",
            error_msg
        )
    
    def _on_cancelled(self):
        """Handle cancellation."""
        self._set_generating_state(False)
        self.progress_panel.update_status("Cancelled")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Subclass QThread | Worker object with moveToThread() | Qt 4.x+ | Better cleanup, cancellation support |
| Real-time validation | Validate on submit | CONTEXT.md | Per user decision |
| Thread.terminate() | requestInterruption() | Qt 5.x+ | Safe cancellation |

**Deprecated/outdated:**
- QThread subclassing: Use worker object pattern instead
- terminate(): Dangerous, use requestInterruption()

## Open Questions

1. **Pressure Unit Clarification**
   - What we know: Requirements say "bar", existing CLI validators use "MPa"
   - What's unclear: Should UI show "bar" or "MPa"?
   - Recommendation: Show "bar" in UI (matching requirements), convert to MPa internally for CLI calls

2. **GenIce Progress Granularity**
   - What we know: GenIce may not expose granular progress callbacks
   - What's unclear: How to estimate progress percentages?
   - Recommendation: Use fixed percentages per phase (lookup=20%, generate=40%, rank=40%) as shown in worker example

3. **Post-Generation Flow**
   - What we know: Phase 8 only does generation with progress feedback
   - What's unclear: How to handle success - auto-continue to output or wait?
   - Recommendation: Per success criteria, show "Complete" then let user proceed or auto-trigger Phase 5 output

## Sources

### Primary (HIGH confidence)
- Qt 6.11 Documentation - QThread Class: https://doc.qt.io/qt-6/qthread.html
- Qt 6.11 Documentation - QMessageBox Class: https://doc.qt.io/qt-6/qmessagebox.html
- Qt 6.11 Documentation - QWidget Class: https://doc.qt.io/qt-6/qwidget.html

### Secondary (MEDIUM confidence)
- Existing quickice/validation/validators.py - Input validation logic
- Existing quickice/structure_generation/generator.py - Generation workflow

### Tertiary (LOW confidence)
- None required - official Qt documentation sufficient

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PySide6 is well-documented, version 6.11.0 specified
- Architecture: HIGH - QThread worker pattern is standard Qt approach
- Pitfalls: HIGH - Common pitfalls well-documented in Qt docs

**Research date:** 2026-03-31
**Valid until:** 90 days (PySide6 stable, Qt 6.x current)