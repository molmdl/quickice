"""View layer components for QuickIce GUI.

This module provides the UI panel components that users interact with:
- InputPanel: Temperature, pressure, and molecule count inputs with inline errors
- ProgressPanel: Progress bar and status text for generation feedback
- ViewerPanel: 3D molecular viewer with toolbar controls
- InfoPanel: Collapsible log output display
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QComboBox, QToolButton, QTextEdit
)
from PySide6.QtCore import Signal, Qt
import os

from quickice.gui.validators import validate_temperature, validate_pressure, validate_nmolecules

# Check if VTK is available (may fail in remote/indirect rendering environments)
_VTK_AVAILABLE = False
try:
    # Test if we can create a basic VTK render window
    # This will fail in environments with indirect rendering (SSH X11 forwarding)
    if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
        # Likely SSH X11 forwarding - check for direct rendering
        _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
    else:
        # Local display or forced - assume VTK works
        _VTK_AVAILABLE = True
    
    if _VTK_AVAILABLE:
        from quickice.gui.dual_viewer import DualViewerWidget
except Exception:
    _VTK_AVAILABLE = False


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
        
        # Temperature label row with help icon
        temp_header = QHBoxLayout()
        temp_header.addWidget(self.temp_label)
        temp_header.addWidget(HelpIcon(
            "Temperature in Kelvin (0-500 K). Enter the temperature at which to generate ice structure."
        ))
        temp_header.addStretch()
        layout.addLayout(temp_header)
        layout.addWidget(self.temp_input)
        layout.addWidget(self.temp_error)
        layout.addSpacing(10)
        
        # Pressure input
        self.pressure_label = QLabel("Pressure (MPa):")
        self.pressure_input = QLineEdit()
        self.pressure_input.setPlaceholderText("Enter pressure (0-10000 MPa)")
        self.pressure_error = QLabel()
        self.pressure_error.setStyleSheet("color: red;")
        self.pressure_error.setWordWrap(True)
        self.pressure_error.hide()
        
        # Pressure label row with help icon
        pressure_header = QHBoxLayout()
        pressure_header.addWidget(self.pressure_label)
        pressure_header.addWidget(HelpIcon(
            "Pressure in MPa (0-10000 MPa). Enter the pressure at which to generate ice structure."
        ))
        pressure_header.addStretch()
        layout.addLayout(pressure_header)
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
        
        # Molecule count label row with help icon
        mol_header = QHBoxLayout()
        mol_header.addWidget(self.mol_label)
        mol_header.addWidget(HelpIcon(
            "Number of water molecules (4-216). More molecules = larger structure but slower generation."
        ))
        mol_header.addStretch()
        layout.addLayout(mol_header)
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


class ViewerPanel(QWidget):
    """Panel containing the 3D molecular viewer with toolbar controls.
    
    Per VIEWER-04: User can zoom in/out, pan, and rotate 3D structure using mouse.
    Per VIEWER-03: User can switch between ball-and-stick and stick-only representations.
    Per VIEWER-05: User can view hydrogen bonds as dashed lines.
    Per ADVVIZ-01: User can toggle unit cell boundary box.
    Per ADVVIZ-03: User can toggle animated auto-rotation.
    Per ADVVIZ-05: User can color atoms by property (energy/density ranking).
    
    Per CONTEXT.md: Toolbar directly above 3D viewport (not main toolbar).
    
    Falls back to placeholder message if VTK is unavailable (e.g., remote SSH with
    indirect rendering).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vtk_available = _VTK_AVAILABLE
        self._setup_ui()
        if self._vtk_available:
            self._setup_connections()
    
    def _setup_ui(self):
        """Set up the viewer panel layout with toolbar and dual viewer."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar (horizontal layout, directly above viewport)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(8)
        
        # Representation toggle: Ball-and-stick / Stick
        self.btn_representation = QPushButton("Ball-and-stick")
        self.btn_representation.setCheckable(True)
        self.btn_representation.setChecked(True)  # Ball-and-stick is default
        toolbar_layout.addWidget(self.btn_representation)
        
        # H-bonds toggle (default checked per 10-03)
        self.btn_hbonds = QPushButton("H-bonds")
        self.btn_hbonds.setCheckable(True)
        self.btn_hbonds.setChecked(True)
        toolbar_layout.addWidget(self.btn_hbonds)
        
        # Unit cell toggle (default unchecked per 10-03)
        self.btn_unit_cell = QPushButton("Unit cell")
        self.btn_unit_cell.setCheckable(True)
        self.btn_unit_cell.setChecked(False)
        toolbar_layout.addWidget(self.btn_unit_cell)
        
        # Zoom-to-fit button
        self.btn_zoom_fit = QPushButton("Zoom fit")
        toolbar_layout.addWidget(self.btn_zoom_fit)
        
        # Auto-rotate toggle (default unchecked per CONTEXT.md)
        self.btn_auto_rotate = QPushButton("Auto-rotate")
        self.btn_auto_rotate.setCheckable(True)
        self.btn_auto_rotate.setChecked(False)
        toolbar_layout.addWidget(self.btn_auto_rotate)
        
        # Color-by dropdown
        toolbar_layout.addWidget(QLabel("Color:"))
        self.color_dropdown = QComboBox()
        self.color_dropdown.addItems(["CPK", "Energy", "Density"])
        toolbar_layout.addWidget(self.color_dropdown)
        
        toolbar_layout.addStretch()
        
        # Candidate selector (for export) - shows "Rank 1 (Ih)", "Rank 2 (II)", etc.
        toolbar_layout.addWidget(QLabel("Export:"))
        self.candidate_selector = QComboBox()
        self.candidate_selector.setMinimumWidth(120)
        toolbar_layout.addWidget(self.candidate_selector)
        
        layout.addLayout(toolbar_layout)
        
        # Dual viewer widget or fallback
        if self._vtk_available:
            self.dual_viewer = DualViewerWidget()
            layout.addWidget(self.dual_viewer)
        else:
            # Fallback: show message that 3D viewer requires local display
            fallback_label = QLabel(
                "3D Molecular Viewer requires a local display.\n\n"
                "If running remotely, clone to your local machine\n"
                "or use QUICKICE_FORCE_VTK=true to override.\n\n"
                "The rest of the application works normally."
            )
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet(
                "font-size: 14px; color: #666; background-color: #f0f0f0; "
                "padding: 20px; border: 1px solid #ccc; border-radius: 4px;"
            )
            layout.addWidget(fallback_label)
            self.dual_viewer = None  # No viewer available
        
        # Placeholder label (shown before first generation)
        self.placeholder = QLabel("Click Generate to view structure")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(
            "font-size: 16px; color: #666; background-color: #f0f0f0;"
        )
        self.placeholder.hide()  # Hidden by default, shown when no candidates
        
        # Stack placeholder on top of viewer (will handle visibility logic in MainWindow)
        self._placeholder_visible = False
    
    def _setup_connections(self):
        """Connect toolbar buttons to viewer methods."""
        if not self._vtk_available:
            # Disable toolbar buttons when VTK not available
            self.btn_representation.setEnabled(False)
            self.btn_hbonds.setEnabled(False)
            self.btn_unit_cell.setEnabled(False)
            self.btn_zoom_fit.setEnabled(False)
            self.btn_auto_rotate.setEnabled(False)
            self.color_dropdown.setEnabled(False)
            return
        
        # Representation toggle
        self.btn_representation.clicked.connect(self._on_representation_toggled)
        
        # H-bonds toggle
        self.btn_hbonds.clicked.connect(self._on_hbonds_toggled)
        
        # Unit cell toggle
        self.btn_unit_cell.clicked.connect(self._on_unit_cell_toggled)
        
        # Zoom-to-fit
        self.btn_zoom_fit.clicked.connect(self._on_zoom_fit)
        
        # Auto-rotate toggle
        self.btn_auto_rotate.clicked.connect(self._on_auto_rotate_toggled)
        
        # Color-by dropdown
        self.color_dropdown.currentTextChanged.connect(self._on_color_changed)
    
    def _on_representation_toggled(self):
        """Toggle between ball-and-stick and stick representations."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        if self.btn_representation.isChecked():
            self.btn_representation.setText("Ball-and-stick")
            self.dual_viewer.viewer1.set_representation_mode("ball_and_stick")
            self.dual_viewer.viewer2.set_representation_mode("ball_and_stick")
        else:
            self.btn_representation.setText("Stick")
            self.dual_viewer.viewer1.set_representation_mode("stick")
            self.dual_viewer.viewer2.set_representation_mode("stick")
    
    def _on_hbonds_toggled(self):
        """Toggle hydrogen bond visibility."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        visible = self.btn_hbonds.isChecked()
        self.dual_viewer.viewer1.set_hydrogen_bonds_visible(visible)
        self.dual_viewer.viewer2.set_hydrogen_bonds_visible(visible)
    
    def _on_unit_cell_toggled(self):
        """Toggle unit cell box visibility."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        visible = self.btn_unit_cell.isChecked()
        self.dual_viewer.viewer1.set_unit_cell_visible(visible)
        self.dual_viewer.viewer2.set_unit_cell_visible(visible)
    
    def _on_zoom_fit(self):
        """Zoom to fit structure in both viewports."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        self.dual_viewer.viewer1.zoom_to_fit()
        self.dual_viewer.viewer2.zoom_to_fit()
    
    def _on_auto_rotate_toggled(self):
        """Toggle auto-rotation animation."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        enabled = self.btn_auto_rotate.isChecked()
        self.dual_viewer.viewer1.toggle_auto_rotation(enabled)
        self.dual_viewer.viewer2.toggle_auto_rotation(enabled)
    
    def _on_color_changed(self, color_mode: str):
        """Change color-by-property mode."""
        if not self._vtk_available or self.dual_viewer is None:
            return
        
        # Map dropdown text to viewer method
        mode_map = {
            "CPK": "cpk",
            "Energy": "energy",
            "Density": "density"
        }
        mode = mode_map.get(color_mode, "cpk")
        self.dual_viewer.viewer1.set_color_by_property(mode)
        self.dual_viewer.viewer2.set_color_by_property(mode)
    
    def show_placeholder(self):
        """Show placeholder text (before first generation)."""
        self._placeholder_visible = True
        if self._vtk_available and self.dual_viewer is not None:
            self.dual_viewer.hide()
        self.placeholder.show()
        # Add placeholder to layout if not already added
        if self.placeholder.parent() != self:
            self.layout().addWidget(self.placeholder)
    
    def hide_placeholder(self):
        """Hide placeholder and show viewer (after first generation)."""
        self._placeholder_visible = False
        self.placeholder.hide()
        if self._vtk_available and self.dual_viewer is not None:
            self.dual_viewer.show()
    
    def is_placeholder_visible(self) -> bool:
        """Check if placeholder is currently visible."""
        return self._placeholder_visible
    
    def is_vtk_available(self) -> bool:
        """Check if VTK 3D viewer is available.
        
        Returns:
            True if VTK is working, False if fallback mode is active.
        """
        return self._vtk_available
    
    def update_candidate_selector(self, candidates: list):
        """Update candidate selector dropdown with available candidates.
        
        Args:
            candidates: List of RankedCandidate objects
        """
        self.candidate_selector.clear()
        for rc in candidates:
            self.candidate_selector.addItem(
                f"Rank {rc.rank} ({rc.candidate.phase_id})"
            )
    
    def get_selected_candidate_index(self) -> int:
        """Get the index of the currently selected candidate.
        
        Returns:
            Index in the ranked_candidates list (0-based)
        """
        return self.candidate_selector.currentIndex()


class HelpIcon(QLabel):
    """Question mark icon that shows tooltip on hover.
    
    Per RESEARCH.md Pattern 4: QToolTip with Question Mark Icon.
    Per CONTEXT.md: Tooltip triggered by hovering over ? icon.
    """
    
    def __init__(self, help_text: str, parent=None):
        super().__init__(parent)
        
        self.setText("?")
        self.setStyleSheet("""
            QLabel {
                color: #666;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #999;
                border-radius: 8px;
                padding: 2px;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
            }
            QLabel:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.WhatsThisCursor)
        self.setToolTip(help_text)


class InfoPanel(QWidget):
    """Collapsible panel for displaying generation log output.
    
    Per CONTEXT.md: Collapsible panel below/beside viewports, shows full
    generation log output, collapsed by default.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._collapsed = True  # Collapsed by default
        self._update_visibility()
    
    def _setup_ui(self):
        """Set up the info panel with toggle button and log text area."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with toggle button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("▶")  # Right arrow when collapsed
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setFixedWidth(20)
        header_layout.addWidget(self.toggle_btn)
        
        header_label = QLabel("Generation Log")
        header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Log text area (monospace, read-only)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: monospace;")
        self.log_text.setMinimumHeight(100)
        layout.addWidget(self.log_text)
        
        # Connect toggle
        self.toggle_btn.clicked.connect(self.toggle)
    
    def toggle(self):
        """Toggle between collapsed and expanded states."""
        self._collapsed = not self._collapsed
        self._update_visibility()
    
    def _update_visibility(self):
        """Update UI based on collapsed state."""
        if self._collapsed:
            self.toggle_btn.setText("▶")  # Collapsed: right arrow
            self.log_text.hide()
        else:
            self.toggle_btn.setText("▼")  # Expanded: down arrow
            self.log_text.show()
    
    def append_log(self, message: str):
        """Append a message to the log.
        
        Args:
            message: Log message to append
        """
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear all log text."""
        self.log_text.clear()
    
    def is_collapsed(self) -> bool:
        """Check if panel is currently collapsed."""
        return self._collapsed
    
    def expand(self):
        """Expand the panel."""
        self._collapsed = False
        self.toggle_btn.setChecked(True)
        self._update_visibility()
    
    def collapse(self):
        """Collapse the panel."""
        self._collapsed = True
        self.toggle_btn.setChecked(False)
        self._update_visibility()
