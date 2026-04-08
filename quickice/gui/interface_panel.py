"""Interface construction panel for QuickIce GUI v3.0.

This module provides the InterfacePanel class for the Interface Construction tab:
- Candidate selection dropdown for ice candidate selection
- Refresh button to sync candidates from Ice Generation tab
- Generate Interface button (Phase 18 placeholder)
- Progress panel for generation feedback
- Info panel for log output
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, 
    QStackedWidget, QGroupBox, QFormLayout
)
from PySide6.QtCore import Signal, Qt

from quickice.gui.view import ProgressPanel, InfoPanel, HelpIcon
from quickice.gui.validators import (
    validate_box_dimension, validate_thickness, 
    validate_pocket_diameter, validate_seed
)


class InterfacePanel(QWidget):
    """Panel for interface construction workflow.
    
    Provides UI for:
    - Selecting ice candidate from dropdown
    - Refreshing candidates from Ice Generation tab
    - Generating interface structures (Phase 18 implementation)
    
    Signals:
        candidate_selected: Emitted when candidate dropdown selection changes
        refresh_requested: Emitted when refresh button is clicked
        generate_requested: Emitted when generate button is clicked with selected index
    """
    
    # Signals for communication with MainWindow
    candidate_selected = Signal(int)  # Emits selected candidate index
    refresh_requested = Signal()  # Emits when refresh button clicked
    generate_requested = Signal(int)  # Emits when generate clicked with selected index
    
    def __init__(self, parent=None):
        """Initialize the interface construction panel.
        
        Args:
            parent: Parent widget (MainWindow)
        """
        super().__init__(parent)
        self._candidates: list = []  # Store ranked candidates
        self._generating = False  # Track generation state
        self._setup_ui()
        self._setup_connections()
    
    def _create_slab_panel(self) -> QWidget:
        """Create slab-specific parameter panel.
        
        Returns:
            QGroupBox with ice thickness and water thickness inputs.
        """
        group = QGroupBox("Slab Parameters")
        layout = QFormLayout()
        
        # Ice thickness row
        ice_row = QHBoxLayout()
        self.ice_thickness_input = QDoubleSpinBox()
        self.ice_thickness_input.setSuffix(" nm")
        self.ice_thickness_input.setRange(0.5, 50.0)
        self.ice_thickness_input.setDecimals(2)
        self.ice_thickness_input.setSingleStep(0.5)
        self.ice_thickness_input.setValue(3.0)
        self.ice_thickness_input.setToolTip("Thickness of ice layer in nanometers")
        ice_row.addWidget(QLabel("Ice thickness:"))
        ice_row.addWidget(HelpIcon("Thickness of ice layer in nanometers"))
        ice_row.addWidget(self.ice_thickness_input)
        ice_row.addStretch()
        
        self.ice_thickness_error = QLabel()
        self.ice_thickness_error.setStyleSheet("color: red;")
        self.ice_thickness_error.hide()
        
        layout.addRow(ice_row)
        layout.addRow(self.ice_thickness_error)
        
        # Water thickness row
        water_row = QHBoxLayout()
        self.water_thickness_input = QDoubleSpinBox()
        self.water_thickness_input.setSuffix(" nm")
        self.water_thickness_input.setRange(0.5, 50.0)
        self.water_thickness_input.setDecimals(2)
        self.water_thickness_input.setSingleStep(0.5)
        self.water_thickness_input.setValue(3.0)
        self.water_thickness_input.setToolTip("Thickness of liquid water layer in nanometers")
        water_row.addWidget(QLabel("Water thickness:"))
        water_row.addWidget(HelpIcon("Thickness of liquid water layer in nanometers"))
        water_row.addWidget(self.water_thickness_input)
        water_row.addStretch()
        
        self.water_thickness_error = QLabel()
        self.water_thickness_error.setStyleSheet("color: red;")
        self.water_thickness_error.hide()
        
        layout.addRow(water_row)
        layout.addRow(self.water_thickness_error)
        
        group.setLayout(layout)
        return group
    
    def _create_pocket_panel(self) -> QWidget:
        """Create pocket-specific parameter panel.
        
        Returns:
            QGroupBox with pocket diameter and shape inputs.
        """
        group = QGroupBox("Pocket Parameters")
        layout = QFormLayout()
        
        # Pocket diameter row
        diameter_row = QHBoxLayout()
        self.pocket_diameter_input = QDoubleSpinBox()
        self.pocket_diameter_input.setSuffix(" nm")
        self.pocket_diameter_input.setRange(0.5, 50.0)
        self.pocket_diameter_input.setDecimals(2)
        self.pocket_diameter_input.setSingleStep(0.5)
        self.pocket_diameter_input.setValue(2.0)
        self.pocket_diameter_input.setToolTip("Diameter of water cavity in nanometers")
        diameter_row.addWidget(QLabel("Pocket diameter:"))
        diameter_row.addWidget(HelpIcon("Diameter of water cavity in nanometers"))
        diameter_row.addWidget(self.pocket_diameter_input)
        diameter_row.addStretch()
        
        self.pocket_diameter_error = QLabel()
        self.pocket_diameter_error.setStyleSheet("color: red;")
        self.pocket_diameter_error.hide()
        
        layout.addRow(diameter_row)
        layout.addRow(self.pocket_diameter_error)
        
        # Pocket shape row
        shape_row = QHBoxLayout()
        self.pocket_shape_combo = QComboBox()
        self.pocket_shape_combo.addItems(["Sphere", "Ellipsoid"])
        self.pocket_shape_combo.setToolTip("Shape of water cavity: sphere or ellipsoid")
        shape_row.addWidget(QLabel("Pocket shape:"))
        shape_row.addWidget(HelpIcon("Shape of water cavity: sphere or ellipsoid"))
        shape_row.addWidget(self.pocket_shape_combo)
        shape_row.addStretch()
        
        layout.addRow(shape_row)
        
        group.setLayout(layout)
        return group
    
    def _create_piece_panel(self) -> QWidget:
        """Create piece-specific parameter panel.
        
        Returns:
            QGroupBox with informational label about candidate-derived dimensions.
        """
        group = QGroupBox("Piece Parameters")
        layout = QFormLayout()
        
        # Informational label
        self.piece_info_label = QLabel("Ice piece dimensions will be derived from selected candidate")
        self.piece_info_label.setStyleSheet("color: #666; font-style: italic;")
        self.piece_info_label.setWordWrap(True)
        
        layout.addRow(self.piece_info_label)
        
        group.setLayout(layout)
        return group
    
    def _setup_ui(self):
        """Set up UI components with vertical layout.
        
        Layout structure:
        - Title label
        - Candidate selection row (label + dropdown)
        - Refresh button row
        - Generate button row
        - Progress panel
        - Info panel (collapsible)
        - Placeholder label (initially visible)
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Interface Construction")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        layout.addSpacing(15)
        
        # === Configuration Controls Section ===
        
        # Mode selector row
        mode_row = QHBoxLayout()
        mode_label = QLabel("Interface mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Slab", "Pocket", "Piece"])
        self.mode_combo.setToolTip("Select interface geometry type")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(HelpIcon("Select interface geometry: slab (layered), pocket (water cavity in ice), or piece (ice crystal in water)"))
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)
        
        layout.addSpacing(10)
        
        # Box dimensions section
        box_header = QHBoxLayout()
        box_header_label = QLabel("Box dimensions:")
        box_header.addWidget(box_header_label)
        box_header.addWidget(HelpIcon("Simulation box dimensions in nanometers. Slab interfaces typically use elongated Z-axis."))
        box_header.addStretch()
        layout.addLayout(box_header)
        
        box_row = QHBoxLayout()
        
        # X dimension
        self.box_x_input = QDoubleSpinBox()
        self.box_x_input.setSuffix(" nm")
        self.box_x_input.setRange(0.5, 100.0)
        self.box_x_input.setDecimals(2)
        self.box_x_input.setSingleStep(0.5)
        self.box_x_input.setValue(5.0)
        self.box_x_input.setToolTip("Box X dimension (nm)")
        box_row.addWidget(QLabel("X:"))
        box_row.addWidget(self.box_x_input)
        
        box_row.addSpacing(10)
        
        # Y dimension
        self.box_y_input = QDoubleSpinBox()
        self.box_y_input.setSuffix(" nm")
        self.box_y_input.setRange(0.5, 100.0)
        self.box_y_input.setDecimals(2)
        self.box_y_input.setSingleStep(0.5)
        self.box_y_input.setValue(5.0)
        self.box_y_input.setToolTip("Box Y dimension (nm)")
        box_row.addWidget(QLabel("Y:"))
        box_row.addWidget(self.box_y_input)
        
        box_row.addSpacing(10)
        
        # Z dimension
        self.box_z_input = QDoubleSpinBox()
        self.box_z_input.setSuffix(" nm")
        self.box_z_input.setRange(0.5, 100.0)
        self.box_z_input.setDecimals(2)
        self.box_z_input.setSingleStep(0.5)
        self.box_z_input.setValue(10.0)
        self.box_z_input.setToolTip("Box Z dimension (nm)")
        box_row.addWidget(QLabel("Z:"))
        box_row.addWidget(self.box_z_input)
        
        box_row.addStretch()
        layout.addLayout(box_row)
        
        # Box dimension error labels (hidden by default)
        self.box_x_error = QLabel()
        self.box_x_error.setStyleSheet("color: red;")
        self.box_x_error.setWordWrap(True)
        self.box_x_error.hide()
        
        self.box_y_error = QLabel()
        self.box_y_error.setStyleSheet("color: red;")
        self.box_y_error.setWordWrap(True)
        self.box_y_error.hide()
        
        self.box_z_error = QLabel()
        self.box_z_error.setStyleSheet("color: red;")
        self.box_z_error.setWordWrap(True)
        self.box_z_error.hide()
        
        box_errors_layout = QHBoxLayout()
        box_errors_layout.addWidget(self.box_x_error)
        box_errors_layout.addSpacing(10)
        box_errors_layout.addWidget(self.box_y_error)
        box_errors_layout.addSpacing(10)
        box_errors_layout.addWidget(self.box_z_error)
        box_errors_layout.addStretch()
        layout.addLayout(box_errors_layout)
        
        layout.addSpacing(10)
        
        # Random seed row
        seed_row = QHBoxLayout()
        seed_label = QLabel("Random seed:")
        self.seed_input = QSpinBox()
        self.seed_input.setRange(1, 999999)
        self.seed_input.setValue(42)
        self.seed_input.setToolTip("Seed for random number generator")
        seed_row.addWidget(seed_label)
        seed_row.addWidget(HelpIcon("Integer seed for reproducible structure generation"))
        seed_row.addWidget(self.seed_input)
        seed_row.addStretch()
        layout.addLayout(seed_row)
        
        # Seed error label (hidden by default)
        self.seed_error = QLabel()
        self.seed_error.setStyleSheet("color: red;")
        self.seed_error.setWordWrap(True)
        self.seed_error.hide()
        
        seed_error_layout = QHBoxLayout()
        seed_error_layout.addWidget(self.seed_error)
        seed_error_layout.addStretch()
        layout.addLayout(seed_error_layout)
        
        layout.addSpacing(15)
        
        # Mode-specific controls
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._create_slab_panel())
        self.stacked_widget.addWidget(self._create_pocket_panel())
        self.stacked_widget.addWidget(self._create_piece_panel())
        layout.addWidget(self.stacked_widget)
        
        layout.addSpacing(15)
        
        # === Candidate Selection Section ===
        
        # Candidate selection row
        candidate_row = QHBoxLayout()
        candidate_label = QLabel("Candidate:")
        self.candidate_dropdown = QComboBox()
        self.candidate_dropdown.setMinimumWidth(200)
        self.candidate_dropdown.setToolTip("Select an ice candidate for interface generation")
        self.candidate_dropdown.addItem("No candidates - generate ice first")
        self.candidate_dropdown.setEnabled(False)
        candidate_row.addWidget(candidate_label)
        candidate_row.addWidget(self.candidate_dropdown)
        candidate_row.addStretch()
        layout.addLayout(candidate_row)
        
        layout.addSpacing(10)
        
        # Refresh button row
        self.refresh_btn = QPushButton("Refresh candidates")
        self.refresh_btn.setToolTip("Sync candidates from Ice Generation tab")
        layout.addWidget(self.refresh_btn)
        
        layout.addSpacing(10)
        
        # Generate button row
        self.generate_btn = QPushButton("Generate Interface")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setToolTip("Generate ice candidates in Tab 1 first")
        layout.addWidget(self.generate_btn)
        
        layout.addSpacing(15)
        
        # Progress panel (reuse from view.py)
        self.progress_panel = ProgressPanel()
        layout.addWidget(self.progress_panel)
        
        layout.addSpacing(10)
        
        # Info panel (collapsible, reuse from view.py)
        self.info_panel = InfoPanel()
        layout.addWidget(self.info_panel)
        
        layout.addSpacing(10)
        
        # Placeholder label (shown initially, hidden after generation)
        self.placeholder_label = QLabel(
            "Select a candidate and click Generate Interface"
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "font-size: 14px; color: #666; background-color: #f0f0f0; "
            "padding: 30px; border: 1px solid #ccc; border-radius: 4px;"
        )
        layout.addWidget(self.placeholder_label, stretch=1)
        
        layout.addStretch()
    
    def _setup_connections(self):
        """Connect internal signals to slots."""
        # Mode selector to stacked widget
        self.mode_combo.currentIndexChanged.connect(self.stacked_widget.setCurrentIndex)
        
        # Dropdown selection change
        self.candidate_dropdown.currentIndexChanged.connect(self._on_candidate_changed)
        
        # Refresh button
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        
        # Generate button
        self.generate_btn.clicked.connect(self._on_generate_clicked)
    
    def _on_candidate_changed(self, index: int):
        """Handle candidate dropdown selection change.
        
        Args:
            index: Selected index in dropdown
        """
        if index >= 0 and self._candidates:
            self.candidate_selected.emit(index)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_requested.emit()
    
    def _on_generate_clicked(self):
        """Handle generate button click."""
        if self._candidates and self.candidate_dropdown.currentIndex() >= 0:
            self.generate_requested.emit(self.candidate_dropdown.currentIndex())
    
    def update_candidates(self, candidates: list) -> None:
        """Update candidate dropdown with new list.
        
        Args:
            candidates: List of RankedCandidate objects from Ice Generation tab
        """
        self._candidates = candidates
        
        # Block signals during update to prevent spurious emissions
        self.candidate_dropdown.blockSignals(True)
        self.candidate_dropdown.clear()
        
        if not candidates:
            # Empty state
            self.candidate_dropdown.addItem("No candidates - generate ice first")
            self.candidate_dropdown.setEnabled(False)
            self.generate_btn.setEnabled(False)
            self.generate_btn.setToolTip("Generate ice candidates in Tab 1 first")
        else:
            # Populate dropdown with ranked candidates
            self.candidate_dropdown.setEnabled(True)
            for rc in candidates:
                self.candidate_dropdown.addItem(
                    f"Rank {rc.rank} ({rc.candidate.phase_id})"
                )
            # Default to first candidate
            self.candidate_dropdown.setCurrentIndex(0)
            
            # Enable generate button
            self.generate_btn.setEnabled(True)
            self.generate_btn.setToolTip("Click to generate interface structure")
        
        self.candidate_dropdown.blockSignals(False)
    
    def set_generating(self, enabled: bool) -> None:
        """Toggle UI state during generation.
        
        Args:
            enabled: True if generation is active, False otherwise
        """
        self._generating = enabled
        
        # Disable controls during generation
        self.candidate_dropdown.setEnabled(not enabled)
        self.refresh_btn.setEnabled(not enabled)
        self.generate_btn.setEnabled(not enabled)
        
        if enabled:
            self.generate_btn.setText("Generating...")
            self.generate_btn.setToolTip("Generation in progress...")
        else:
            self.generate_btn.setText("Generate Interface")
            if self._candidates:
                self.generate_btn.setEnabled(True)
                self.generate_btn.setToolTip("Click to generate interface structure")
    
    def get_selected_candidate_index(self) -> int:
        """Get currently selected candidate index.
        
        Returns:
            Index in candidates list (0-based), or -1 if no selection
        """
        if not self._candidates:
            return -1
        return self.candidate_dropdown.currentIndex()
    
    def show_placeholder(self) -> None:
        """Show placeholder message in main area."""
        self.placeholder_label.show()
    
    def hide_placeholder(self) -> None:
        """Hide placeholder message after generation."""
        self.placeholder_label.hide()
    
    def append_log(self, message: str) -> None:
        """Append message to info panel log.
        
        Convenience method for MainWindow to log messages.
        
        Args:
            message: Log message to append
        """
        self.info_panel.append_log(message)
    
    def clear_log(self) -> None:
        """Clear info panel log.
        
        Convenience method for MainWindow to clear log.
        """
        self.info_panel.clear_log()
    
    def expand_log(self) -> None:
        """Expand info panel.
        
        Convenience method for MainWindow to expand log panel.
        """
        self.info_panel.expand()
    
    def collapse_log(self) -> None:
        """Collapse info panel.
        
        Convenience method for MainWindow to collapse log panel.
        """
        self.info_panel.collapse()
    
    def validate_configuration(self) -> bool:
        """Validate all configuration inputs, show inline errors, return overall validity.
        
        Validates:
        - Box dimensions (X, Y, Z)
        - Random seed
        - Mode-specific parameters based on selected mode
        
        Returns:
            True if all inputs are valid, False otherwise
        """
        valid = True
        
        # Box dimensions
        for dim_input, error_label, dim_name in [
            (self.box_x_input, self.box_x_error, "X"),
            (self.box_y_input, self.box_y_error, "Y"),
            (self.box_z_input, self.box_z_error, "Z")
        ]:
            valid_dim, dim_err = validate_box_dimension(str(dim_input.value()))
            error_label.setText(dim_err)
            error_label.setVisible(not valid_dim)
            if not valid_dim:
                valid = False
        
        # Random seed
        valid_seed, seed_err = validate_seed(str(self.seed_input.value()))
        self.seed_error.setText(seed_err)
        self.seed_error.setVisible(not valid_seed)
        if not valid_seed:
            valid = False
        
        # Mode-specific validation
        current_mode = self.mode_combo.currentText()
        if current_mode == "Slab":
            # Ice thickness
            valid_ice, ice_err = validate_thickness(str(self.ice_thickness_input.value()))
            self.ice_thickness_error.setText(ice_err)
            self.ice_thickness_error.setVisible(not valid_ice)
            if not valid_ice:
                valid = False
            
            # Water thickness
            valid_water, water_err = validate_thickness(str(self.water_thickness_input.value()))
            self.water_thickness_error.setText(water_err)
            self.water_thickness_error.setVisible(not valid_water)
            if not valid_water:
                valid = False
        
        elif current_mode == "Pocket":
            # Pocket diameter
            valid_diam, diam_err = validate_pocket_diameter(str(self.pocket_diameter_input.value()))
            self.pocket_diameter_error.setText(diam_err)
            self.pocket_diameter_error.setVisible(not valid_diam)
            if not valid_diam:
                valid = False
        
        # Piece mode has no editable inputs (dimensions from candidate)
        
        return valid
    
    def clear_configuration_errors(self) -> None:
        """Clear all configuration error messages."""
        # Shared errors
        self.box_x_error.hide()
        self.box_y_error.hide()
        self.box_z_error.hide()
        self.seed_error.hide()
        
        # Mode-specific errors
        self.ice_thickness_error.hide()
        self.water_thickness_error.hide()
        self.pocket_diameter_error.hide()
