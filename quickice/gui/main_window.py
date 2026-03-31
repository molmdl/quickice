"""Main application window for QuickIce GUI.

This module provides the MainWindow class that assembles all GUI components:
- InputPanel for temperature, pressure, and molecule count inputs
- ProgressPanel for progress bar and status text
- Generate/Cancel buttons
- Keyboard shortcuts (Enter to generate, Escape to cancel)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QMessageBox, QApplication
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot

from quickice.gui.view import InputPanel, ProgressPanel
from quickice.gui.viewmodel import MainViewModel


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
        self.setMinimumSize(400, 450)
        
        # Create viewmodel
        self._viewmodel = MainViewModel(self)
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """Setup UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Input panel
        self.input_panel = InputPanel()
        layout.addWidget(self.input_panel)
        
        # Progress panel
        self.progress_panel = ProgressPanel()
        layout.addWidget(self.progress_panel)
        
        # Buttons
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setDefault(True)  # Responds to Enter key when focused
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.cancel_btn)
        
        # Stretch at bottom
        layout.addStretch()
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        # Button connections
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        # ViewModel connections - progress
        self._viewmodel.generation_progress.connect(self.progress_panel.update_progress)
        self._viewmodel.generation_status.connect(self.progress_panel.update_status)
        
        # ViewModel connections - state
        self._viewmodel.generation_started.connect(self._on_generation_started)
        self._viewmodel.generation_complete.connect(self._on_generation_complete)
        self._viewmodel.generation_error.connect(self._on_generation_error)
        self._viewmodel.generation_cancelled.connect(self._on_generation_cancelled)
        
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
    
    @Slot(object)
    def _on_generation_complete(self, result):
        """Handle generation complete."""
        self.progress_panel.set_complete()
        self.input_panel.clear_errors()
        # Future: Pass result to 3D viewer (Phase 10)
    
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
