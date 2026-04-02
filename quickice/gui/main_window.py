"""Main application window for QuickIce GUI.

This module provides the MainWindow class that assembles all GUI components:
- InputPanel for temperature, pressure, and molecule count inputs
- ProgressPanel for progress bar and status text
- PhaseDiagramPanel for interactive phase diagram
- ViewerPanel for 3D molecular visualization
- InfoPanel for generation log output
- Generate/Cancel buttons
- Keyboard shortcuts (Enter to generate, Escape to cancel)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QMessageBox, QApplication, QSplitter, QMenuBar, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot

from quickice.gui.view import InputPanel, ProgressPanel, ViewerPanel, InfoPanel
from quickice.gui.viewmodel import MainViewModel
from quickice.gui.phase_diagram_widget import PhaseDiagramPanel
from quickice.gui.export import PDBExporter, DiagramExporter, ViewportExporter


class MainWindow(QMainWindow):
    """Main application window for QuickIce GUI.
    
    This is the MVVM "View" layer that connects to the ViewModel.
    
    The window provides:
    - Input panel for thermodynamic parameters
    - Progress panel for generation feedback
    - Generate button to trigger ice structure generation
    - Cancel button to abort generation mid-process
    - Keyboard shortcuts: Enter to generate, Escape to cancel
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QuickIce - Ice Structure Generator")
        self.setMinimumSize(1300, 600)
        
        # Create viewmodel
        self._viewmodel = MainViewModel(self)
        
        # Export handlers
        self._pdb_exporter = PDBExporter(self)
        self._diagram_exporter = DiagramExporter(self)
        self._viewport_exporter = ViewportExporter(self)
        
        # Store current generation result for export
        self._current_result = None
        self._current_T = 0.0
        self._current_P = 0.0
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        
        # Create menu bar (after shortcuts so it appears in proper order)
        self._create_menu_bar()
    
    def _setup_ui(self):
        """Setup UI components with split view layout."""
        # Create splitter for horizontal split view
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Phase diagram panel
        self.diagram_panel = PhaseDiagramPanel()
        splitter.addWidget(self.diagram_panel)
        
        # Right side: Input panel, progress panel, viewer, buttons
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Input panel
        self.input_panel = InputPanel()
        right_layout.addWidget(self.input_panel)
        
        # Progress panel
        self.progress_panel = ProgressPanel()
        right_layout.addWidget(self.progress_panel)
        
        # Viewer panel (3D molecular viewer with toolbar)
        self.viewer_panel = ViewerPanel()
        right_layout.addWidget(self.viewer_panel, stretch=1)  # Give viewer extra space
        
        # Info panel (collapsible log output)
        self.info_panel = InfoPanel()
        right_layout.addWidget(self.info_panel)
        
        # Buttons
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setDefault(True)  # Responds to Enter key when focused
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        
        right_layout.addWidget(self.generate_btn)
        right_layout.addWidget(self.cancel_btn)
        
        splitter.addWidget(right_widget)
        
        # Set initial sizes (diagram 550px, right panel 750px for dual viewer)
        splitter.setSizes([550, 750])
        
        # Set splitter as central widget
        self.setCentralWidget(splitter)
        
        # Show placeholder before first generation
        self.viewer_panel.show_placeholder()
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        # Button connections
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        # Diagram selection -> input panel
        self.diagram_panel.diagram_canvas.coordinates_selected.connect(
            self._on_diagram_selected
        )
        
        # Input field changes -> diagram marker (bidirectional binding)
        self.input_panel.temp_input.textChanged.connect(self._on_input_changed)
        self.input_panel.pressure_input.textChanged.connect(self._on_input_changed)
        
        # ViewModel connections - progress
        self._viewmodel.generation_progress.connect(self.progress_panel.update_progress)
        self._viewmodel.generation_status.connect(self.progress_panel.update_status)
        
        # ViewModel connections - state
        self._viewmodel.generation_started.connect(self._on_generation_started)
        self._viewmodel.generation_complete.connect(self._on_generation_complete)
        self._viewmodel.generation_error.connect(self._on_generation_error)
        self._viewmodel.generation_cancelled.connect(self._on_generation_cancelled)
        
        # ViewModel connections - viewer
        self._viewmodel.ranked_candidates_ready.connect(self._on_candidates_ready)
        
        # ViewModel connections - log
        self._viewmodel.generation_status.connect(self.info_panel.append_log)
        
        # UI state connections
        self._viewmodel.ui_enabled_changed.connect(self._on_ui_enabled_changed)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts.
        
        Per UX-01: Enter to generate, Escape to cancel.
        """
        # Enter to generate
        generate_action = QAction(self)
        generate_action.setShortcut(Qt.Key.Key_Return)
        generate_action.triggered.connect(self._on_generate_clicked)
        self.addAction(generate_action)
        
        # Also handle Enter on keypad
        generate_action_kp = QAction(self)
        generate_action_kp.setShortcut(Qt.Key.Key_Enter)
        generate_action_kp.triggered.connect(self._on_generate_clicked)
        self.addAction(generate_action_kp)
        
        # Escape to cancel
        cancel_action = QAction(self)
        cancel_action.setShortcut(Qt.Key.Key_Escape)
        cancel_action.triggered.connect(self._on_cancel_clicked)
        self.addAction(cancel_action)
    
    def _create_menu_bar(self):
        """Create menu bar with File menu.
        
        Per must_haves: Menu bar with File menu containing Save PDB, 
        Save Diagram, and Save Viewport actions.
        """
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Save PDB action
        save_pdb_action = file_menu.addAction("Save PDB...")
        save_pdb_action.setShortcut("Ctrl+S")
        save_pdb_action.triggered.connect(self._on_save_pdb)
        
        # Save Diagram action
        save_diagram_action = file_menu.addAction("Save Diagram...")
        save_diagram_action.setShortcut("Ctrl+D")
        save_diagram_action.triggered.connect(self._on_save_diagram)
        
        # Save Viewport action
        save_viewport_action = file_menu.addAction("Save Viewport...")
        save_viewport_action.setShortcut("Ctrl+Shift+S")
        save_viewport_action.triggered.connect(self._on_save_viewport)
    
    @Slot()
    def _on_generate_clicked(self):
        """Handle Generate button click."""
        # Clear previous errors
        self.input_panel.clear_errors()
        
        # Validate inputs
        if not self.input_panel.validate_all():
            return
        
        # Get values
        temperature = self.input_panel.get_temperature()
        pressure = self.input_panel.get_pressure()
        nmolecules = self.input_panel.get_nmolecules()
        
        # Store current generation parameters for export
        self._current_T = temperature
        self._current_P = pressure
        
        # Reset progress
        self.progress_panel.reset()
        self.progress_panel.set_generating()
        
        # Start generation
        self._viewmodel.start_generation(temperature, pressure, nmolecules)
    
    @Slot()
    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        self._viewmodel.cancel_generation()
    
    @Slot()
    def _on_generation_started(self):
        """Handle generation started."""
        self.progress_panel.set_generating()
        self.info_panel.clear_log()
        self.info_panel.append_log("Starting ice structure generation...")
    
    @Slot(object)
    def _on_generation_complete(self, result):
        """Handle generation complete."""
        self.progress_panel.set_complete()
        self.input_panel.clear_errors()
        # Result is passed to _on_candidates_ready via ranked_candidates_ready signal
    
    @Slot(object)
    def _on_candidates_ready(self, result):
        """Handle ranked candidates ready for display.
        
        Args:
            result: RankingResult containing ranked_candidates list
        """
        # Store result for export
        self._current_result = result
        
        # Hide placeholder and show viewer
        self.viewer_panel.hide_placeholder()
        
        # Load candidates into dual viewer (if VTK available)
        if self.viewer_panel.is_vtk_available():
            if hasattr(result, 'ranked_candidates') and result.ranked_candidates:
                self.viewer_panel.dual_viewer.set_candidates(result.ranked_candidates)
                
                # Log to info panel
                self.info_panel.append_log(
                    f"\nLoaded {len(result.ranked_candidates)} candidate(s) into viewer"
                )
                self.info_panel.append_log("Rank #1 shown in left viewport, Rank #2 in right")
        else:
            # VTK not available - show message in log
            self.info_panel.append_log(
                f"\nGenerated {len(result.ranked_candidates) if hasattr(result, 'ranked_candidates') else 0} candidate(s)"
            )
            self.info_panel.append_log(
                "3D viewer unavailable in remote environment. "
                "Clone to local machine for full visualization."
            )
    
    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """Handle generation error.
        
        Per PROGRESS-04: User sees error dialog when generation fails.
        """
        self.progress_panel.set_error(error_msg)
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "Generation Error",
            f"Failed to generate ice structure:\n\n{error_msg}",
            QMessageBox.StandardButton.Ok
        )
    
    @Slot()
    def _on_generation_cancelled(self):
        """Handle generation cancelled."""
        self.progress_panel.set_cancelled()
    
    @Slot(bool)
    def _on_ui_enabled_changed(self, enabled: bool):
        """Handle UI enabled/disabled state change."""
        self.generate_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(not enabled)
        self.input_panel.setEnabled(enabled)
        self.viewer_panel.setEnabled(enabled)
    
    @Slot(float, float)
    def _on_diagram_selected(self, temperature: float, pressure: float):
        """Handle diagram selection - populate input fields.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        """
        # Set values in input panel with rounding
        self.input_panel.set_values(
            round(temperature, 1),
            round(pressure, 2),  # Round to 2 decimals for MPa
            96  # Default molecule count
        )
    
    @Slot()
    def _on_input_changed(self):
        """Handle input field changes - update diagram marker.
        
        This creates bidirectional binding: typing in input fields
        updates the diagram marker position.
        """
        try:
            temp = float(self.input_panel.temp_input.text())
            pressure = float(self.input_panel.pressure_input.text())
            # Only update if values are in valid range
            if 50 <= temp <= 500 and 0.1 <= pressure <= 10000:
                self.diagram_panel.set_coordinates(temp, pressure)
        except (ValueError, TypeError):
            pass  # Invalid input, don't update marker


def run_app():
    """Run the QuickIce GUI application.
    
    This is the entry point for the QuickIce GUI.
    Creates QApplication, MainWindow, and starts the event loop.
    
    Usage:
        from quickice.gui import run_app
        run_app()
    """
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
