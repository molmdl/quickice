"""View layer components for QuickIce GUI.

This module provides the UI panel components that users interact with:
- InputPanel: Temperature, pressure, and molecule count inputs with inline errors
- ProgressPanel: Progress bar and status text for generation feedback
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QProgressBar
from PySide6.QtCore import Signal

from quickice.gui.validators import validate_temperature, validate_pressure, validate_nmolecules


class InputPanel(QWidget):
    """Panel with temperature, pressure, and molecule count inputs.
    
    Each input field has:
    - A label above the field
    - A QLineEdit for user input
    - An inline error label (red text) below the field
    
    Validation occurs on submit (when Generate button clicked), not real-time.
    """
    
    # Signal emitted when Generate button should be enabled/disabled
    validation_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Temperature input
        self.temp_label = QLabel("Temperature (K):")
        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("Enter temperature (0-500 K)")
        self.temp_error = QLabel()
        self.temp_error.setStyleSheet("color: red;")
        self.temp_error.setWordWrap(True)
        self.temp_error.hide()
        
        layout.addWidget(self.temp_label)
        layout.addWidget(self.temp_input)
        layout.addWidget(self.temp_error)
        layout.addSpacing(10)
        
        # Pressure input
        self.pressure_label = QLabel("Pressure (MPa):")
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("Enter pressure (0-1000 MPa)")
        self.pressure_error = QLabel()
        self.pressure_error.setStyleSheet("color: red;")
        self.pressure_error.setWordWrap(True)
        self.pressure_error.hide()
        
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.pressure_input)
        layout.addWidget(self.pressure_error)
        layout.addSpacing(10)
        
        # Molecule count input
        self.mol_label = QLabel("Number of molecules:")
        self.mol_input = QLineEdit()
        self.mol_input.setPlaceholderText("Enter count (4-216)")
        self.mol_error = QLabel()
        self.mol_error.setStyleSheet("color: red;")
        self.mol_error.setWordWrap(True)
        self.mol_error.hide()
        
        layout.addWidget(self.mol_label)
        layout.addWidget(self.mol_input)
        layout.addWidget(self.mol_error)
        layout.addStretch()
    
    def validate_all(self) -> bool:
        """Validate all inputs, show inline errors, return overall validity.
        
        Per CONTEXT.md: Validation errors appear on submit (when Generate clicked),
        not real-time.
        
        Returns:
            True if all inputs are valid, False otherwise
        """
        valid = True
        
        # Temperature validation
        valid_temp, temp_err = validate_temperature(self.temp_input.text())
        self.temp_error.setText(temp_err)
        self.temp_error.setVisible(not valid_temp)
        if not valid_temp:
            valid = False
        
        # Pressure validation
        valid_pressure, pressure_err = validate_pressure(self.pressure_input.text())
        self.pressure_error.setText(pressure_err)
        self.pressure_error.setVisible(not valid_pressure)
        if not valid_pressure:
            valid = False
        
        # Molecule count validation
        valid_mol, mol_err = validate_nmolecules(self.mol_input.text())
        self.mol_error.setText(mol_err)
        self.mol_error.setVisible(not valid_mol)
        if not valid_mol:
            valid = False
        
        return valid
    
    def clear_errors(self):
        """Clear all inline error messages."""
        self.temp_error.hide()
        self.pressure_error.hide()
        self.mol_error.hide()
    
    def get_temperature(self) -> float:
        """Get validated temperature value.
        
        Returns:
            Temperature in Kelvin
            
        Note:
            Should only be called after validate_all() returns True
        """
        return float(self.temp_input.text())
    
    def get_pressure(self) -> float:
        """Get validated pressure value.
        
        Returns:
            Pressure in MPa
            
        Note:
            Should only be called after validate_all() returns True
        """
        return float(self.pressure_input.text())
    
    def get_nmolecules(self) -> int:
        """Get validated molecule count.
        
        Returns:
            Number of molecules
            
        Note:
            Should only be called after validate_all() returns True
        """
        return int(self.mol_input.text())
    
    def set_values(self, temperature: float, pressure: float, nmolecules: int):
        """Set input field values (for Phase 9 phase diagram autofill).
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
            nmolecules: Number of molecules
        """
        self.temp_input.setText(str(temperature))
        self.pressure_input.setText(str(pressure))
        self.mol_input.setText(str(nmolecules))


class ProgressPanel(QWidget):
    """Panel with progress bar and status text for generation feedback.
    
    Shows:
    - Status label with current operation message
    - Progress bar with 0-100 percentage
    
    States:
    - Ready: Initial state
    - Generating: Progress bar updates, status shows current step
    - Complete: Progress at 100%, status shows "Complete"
    - Error: Progress resets, status shows error message
    - Cancelled: Progress resets, status shows "Cancelled"
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)  # Shows percentage
        layout.addWidget(self.progress_bar)
    
    def update_progress(self, value: int):
        """Update progress bar value (0-100).
        
        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)
    
    def update_status(self, text: str):
        """Update status label text.
        
        Args:
            text: Status message to display
        """
        self.status_label.setText(text)
    
    def reset(self):
        """Reset progress panel to initial state."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
    
    def set_generating(self):
        """Set progress panel to generating state."""
        self.status_label.setText("Starting...")
        self.progress_bar.setValue(0)
    
    def set_complete(self):
        """Set progress panel to complete state.
        
        Per CONTEXT.md: Success message appears briefly, then clears.
        """
        self.progress_bar.setValue(100)
        self.status_label.setText("Complete")
    
    def set_error(self, message: str):
        """Set progress panel to error state.
        
        Args:
            message: Error message to display
        """
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {message}")
    
    def set_cancelled(self):
        """Set progress panel to cancelled state."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Cancelled")
