"""Interface construction panel for QuickIce GUI v3.0.

This module provides the InterfacePanel class for the Interface Construction tab:
- Candidate selection dropdown for ice candidate selection
- Refresh button to sync candidates from Ice Generation tab
- Generate Interface button (Phase 18 placeholder)
- Progress panel for generation feedback
- Info panel for log output
"""

import os
import numpy as np

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

# Check if VTK is available (may fail in remote/indirect rendering environments)
# Same logic as view.py for consistency
_VTK_AVAILABLE = False
try:
    # Test if we can create a basic VTK render window
    # Enable VTK if DISPLAY is set (local or X11 forwarding)
    # User can disable with QUICKICE_FORCE_VTK=false
    if os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'false':
        _VTK_AVAILABLE = False
    elif os.environ.get('DISPLAY'):
        _VTK_AVAILABLE = True
    else:
        _VTK_AVAILABLE = False
    
    if _VTK_AVAILABLE:
        from quickice.gui.interface_viewer import InterfaceViewerWidget
except Exception:
    _VTK_AVAILABLE = False


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
        self._vtk_available = _VTK_AVAILABLE
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
        self.ice_thickness_input.setToolTip(
            "Thickness of each ice layer in nm (0.5–50).\n"
            "\n"
            "IMPORTANT: For slab mode, box_z must equal:\n"
            "  2 × ice_thickness + water_thickness\n"
            "\n"
            "Example: ice=3.0 nm, water=4.0 nm → box_z=10.0 nm"
        )
        ice_row.addWidget(QLabel("Ice thickness:"))
        ice_row.addWidget(HelpIcon(
            "Thickness of each ice layer in nanometers. The slab has two ice layers (top and bottom), "
            "each with this thickness. Typical values: 2–10 nm for surface studies.\n\n"
            "CRITICAL: Box Z must equal 2×ice_thickness + water_thickness. "
            "For example, if ice=3.0 nm and water=4.0 nm, then box_z must be 10.0 nm."
        ))
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
        self.water_thickness_input.setToolTip(
            "Thickness of liquid water layer in nm (0.5–50).\n"
            "\n"
            "IMPORTANT: For slab mode, box_z must equal:\n"
            "  2 × ice_thickness + water_thickness\n"
            "\n"
            "Example: ice=3.0 nm, water=4.0 nm → box_z=10.0 nm"
        )
        water_row.addWidget(QLabel("Water thickness:"))
        water_row.addWidget(HelpIcon(
            "Thickness of the liquid water layer in nanometers. This water layer is sandwiched "
            "between the top and bottom ice layers. Typical values: 2–10 nm for surface studies.\n\n"
            "CRITICAL: Box Z must equal 2×ice_thickness + water_thickness. "
            "For example, if ice=3.0 nm and water=4.0 nm, then box_z must be 10.0 nm."
        ))
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
        self.pocket_diameter_input.setToolTip(
            "Diameter of water cavity in nm (0.5–50).\n"
            "\n"
            "IMPORTANT: All box dimensions (X, Y, Z) must exceed\n"
            "the pocket diameter to contain the cavity properly.\n"
            "\n"
            "Example: pocket=2.0 nm → box must be >2.0 nm in X, Y, Z\n"
            "Typical values: 1–5 nm for confined water studies."
        )
        diameter_row.addWidget(QLabel("Pocket diameter:"))
        diameter_row.addWidget(HelpIcon("Diameter of the water cavity in nanometers. The cavity is carved out of the ice matrix and filled with liquid water molecules. Larger diameters create bigger water pockets."))
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
        self.pocket_shape_combo.addItems(["Sphere", "Cubic"])
        self.pocket_shape_combo.setToolTip("Cavity shape: sphere or cube")
        shape_row.addWidget(QLabel("Pocket shape:"))
        shape_row.addWidget(HelpIcon("Shape of the water cavity. Sphere creates a round void. Cubic creates a cube-shaped void."))
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
        """Set up UI components with two-column layout.
        
        Layout structure:
        - QHBoxLayout (top-level)
          - Left column (QVBoxLayout): Title, mode, box dims, seed, candidate, buttons, progress, info
          - Right column (QVBoxLayout): StackedWidget (mode params), viewer stack (stretch=1)
        """
        # Top-level horizontal layout
        top_layout = QHBoxLayout(self)
        top_layout.setContentsMargins(20, 20, 20, 20)
        top_layout.setSpacing(20)
        
        # === LEFT COLUMN: Configuration Controls ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Interface Construction")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_layout.addWidget(title_label)
        
        left_layout.addSpacing(15)
        
        # Mode selector row
        mode_row = QHBoxLayout()
        mode_label = QLabel("Interface mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Slab", "Pocket", "Piece"])
        self.mode_combo.setToolTip("Select interface geometry:\n• Slab — Layered ice-water interface\n• Pocket — Water cavity in ice matrix\n• Piece — Ice fragment in liquid water")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(HelpIcon("Interface geometry type. Slab creates flat layered ice-water interfaces (typical for surface melting studies). Pocket carves a water-filled cavity inside ice (confined water studies). Piece embeds an ice crystal fragment in liquid water (nucleation studies)."))
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        left_layout.addLayout(mode_row)
        
        left_layout.addSpacing(10)
        
        # Box dimensions section
        box_header = QHBoxLayout()
        box_header_label = QLabel("Box dimensions:")
        box_header.addWidget(box_header_label)
        box_header.addWidget(HelpIcon(
            "Simulation box dimensions in nanometers.\n\n"
            "For SLAB mode: box_z must equal 2×ice_thickness + water_thickness\n"
            "  Example: ice=3.0 nm, water=3.0 nm → box_z=9.0 nm\n\n"
            "For POCKET mode: All dimensions must exceed pocket diameter\n"
            "  Example: pocket=2.0 nm → box must be >2.0 nm in X, Y, Z\n\n"
            "For PIECE mode: Box must be larger than ice candidate dimensions\n"
            "  Ice piece dimensions shown in 'Piece Parameters' section"
        ))
        box_header.addStretch()
        left_layout.addLayout(box_header)
        
        box_row = QHBoxLayout()
        
        # X dimension
        self.box_x_input = QDoubleSpinBox()
        self.box_x_input.setSuffix(" nm")
        self.box_x_input.setRange(0.5, 100.0)
        self.box_x_input.setDecimals(2)
        self.box_x_input.setSingleStep(0.5)
        self.box_x_input.setValue(5.0)
        self.box_x_input.setToolTip(
            "Box X dimension in nm (0.5–100).\n"
            "\n"
            "For POCKET mode: X must exceed pocket diameter.\n"
            "For PIECE mode: X must exceed ice candidate width."
        )
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
        self.box_y_input.setToolTip(
            "Box Y dimension in nm (0.5–100).\n"
            "\n"
            "For POCKET mode: Y must exceed pocket diameter.\n"
            "For PIECE mode: Y must exceed ice candidate depth."
        )
        box_row.addWidget(QLabel("Y:"))
        box_row.addWidget(self.box_y_input)
        
        box_row.addSpacing(10)
        
        # Z dimension
        self.box_z_input = QDoubleSpinBox()
        self.box_z_input.setSuffix(" nm")
        self.box_z_input.setRange(0.5, 100.0)
        self.box_z_input.setDecimals(2)
        self.box_z_input.setSingleStep(0.5)
        self.box_z_input.setValue(9.0)
        self.box_z_input.setToolTip(
            "Box Z dimension in nm (0.5–100).\n"
            "\n"
            "For SLAB mode, box_z MUST equal:\n"
            "  2 × ice_thickness + water_thickness\n"
            "\n"
            "Default: 9.0 nm (matches 2×3.0 + 3.0)"
        )
        box_row.addWidget(QLabel("Z:"))
        box_row.addWidget(self.box_z_input)
        
        box_row.addStretch()
        left_layout.addLayout(box_row)
        
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
        left_layout.addLayout(box_errors_layout)
        
        left_layout.addSpacing(10)
        
        # Random seed row
        seed_row = QHBoxLayout()
        seed_label = QLabel("Random seed:")
        self.seed_input = QSpinBox()
        self.seed_input.setRange(1, 999999)
        self.seed_input.setValue(42)
        self.seed_input.setToolTip("Random seed for water placement (1–999999).\nSame seed = same structure for identical inputs.")
        seed_row.addWidget(seed_label)
        seed_row.addWidget(HelpIcon("Integer seed for reproducible water molecule placement. Using the same seed with identical parameters produces identical interface structures. Change the seed to explore different configurations."))
        seed_row.addWidget(self.seed_input)
        seed_row.addStretch()
        left_layout.addLayout(seed_row)
        
        # Seed error label (hidden by default)
        self.seed_error = QLabel()
        self.seed_error.setStyleSheet("color: red;")
        self.seed_error.setWordWrap(True)
        self.seed_error.hide()
        
        seed_error_layout = QHBoxLayout()
        seed_error_layout.addWidget(self.seed_error)
        seed_error_layout.addStretch()
        left_layout.addLayout(seed_error_layout)
        
        left_layout.addSpacing(15)
        
        # === Candidate Selection Section ===
        
        # Candidate selection row
        candidate_row = QHBoxLayout()
        candidate_label = QLabel("Candidate:")
        self.candidate_dropdown = QComboBox()
        self.candidate_dropdown.setMinimumWidth(200)
        self.candidate_dropdown.setToolTip("Select an ice candidate from Tab 1 for interface generation")
        self.candidate_dropdown.addItem("No candidates - generate ice first")
        self.candidate_dropdown.setEnabled(False)
        candidate_row.addWidget(candidate_label)
        candidate_row.addWidget(self.candidate_dropdown)
        candidate_row.addStretch()
        left_layout.addLayout(candidate_row)
        
        left_layout.addSpacing(10)
        
        # Refresh button row
        self.refresh_btn = QPushButton("Refresh candidates")
        self.refresh_btn.setToolTip("Sync candidate list from Ice Generation tab.\nClick after generating new candidates in Tab 1.")
        left_layout.addWidget(self.refresh_btn)
        
        left_layout.addSpacing(10)
        
        # Generate button row
        self.generate_btn = QPushButton("Generate Interface")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setToolTip("Generate ice candidates in Tab 1 first")
        left_layout.addWidget(self.generate_btn)
        
        left_layout.addSpacing(15)
        
        # Progress panel (reuse from view.py)
        self.progress_panel = ProgressPanel()
        left_layout.addWidget(self.progress_panel)
        
        left_layout.addSpacing(10)
        
        # Info panel (collapsible, reuse from view.py)
        self.info_panel = InfoPanel()
        left_layout.addWidget(self.info_panel)
        
        left_layout.addStretch()
        
        # === RIGHT COLUMN: Mode params + Viewer ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # Mode-specific controls at top right
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._create_slab_panel())
        self.stacked_widget.addWidget(self._create_pocket_panel())
        self.stacked_widget.addWidget(self._create_piece_panel())
        right_layout.addWidget(self.stacked_widget)
        
        right_layout.addSpacing(10)
        
        # Viewer stack: placeholder (page 0) and 3D viewer (page 1)
        self._viewer_stack = QStackedWidget()
        
        # Page 0: Placeholder text (shown before generation or when VTK unavailable)
        self.placeholder_label = QLabel(
            "Generate a structure to visualize"
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "font-size: 14px; color: #666; background-color: #f0f0f0; "
            "padding: 30px; border: 1px solid #ccc; border-radius: 4px;"
        )
        self._viewer_stack.addWidget(self.placeholder_label)
        
        # Page 1: 3D interface viewer or fallback (if VTK unavailable)
        if self._vtk_available:
            self._interface_viewer = InterfaceViewerWidget()
            self._viewer_stack.addWidget(self._interface_viewer)
        else:
            # Fallback: show message that 3D viewer requires local display
            # Consistent with Tab 1 behavior
            fallback_label = QLabel(
                "3D Interface Viewer requires a local display.\n\n"
                "If running remotely, clone to your local machine\n"
                "or use QUICKICE_FORCE_VTK=true to override.\n\n"
                "Generate interface structures and export to GRO/PDB files."
            )
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet(
                "font-size: 14px; color: #666; background-color: #f0f0f0; "
                "padding: 20px; border: 1px solid #ccc; border-radius: 4px;"
            )
            self._viewer_stack.addWidget(fallback_label)
            self._interface_viewer = None  # No viewer available
        
        right_layout.addWidget(self._viewer_stack, stretch=1)
        
        # Add columns to top-level layout
        top_layout.addLayout(left_layout, stretch=2)
        top_layout.addLayout(right_layout, stretch=3)
    
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
        """Handle generate button click.
        
        Validates all configuration inputs before emitting generate_requested signal.
        Shows inline errors for invalid inputs.
        """
        if not self._candidates:
            return
        
        # Clear previous errors
        self.clear_configuration_errors()
        
        # Validate configuration
        if not self.validate_configuration():
            return  # Errors shown, don't proceed
        
        # Get selected candidate index
        selected_idx = self.candidate_dropdown.currentIndex()
        if selected_idx < 0:
            return
        
        # Emit signal with candidate index
        # Configuration will be retrieved via get_configuration() by MainWindow
        self.generate_requested.emit(selected_idx)
    
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
                self.generate_btn.setToolTip("Click to generate interface structure with current configuration")
    
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
        self._viewer_stack.setCurrentIndex(0)
    
    def hide_placeholder(self) -> None:
        """Hide placeholder, show 3D viewer (or fallback if VTK unavailable)."""
        if self._vtk_available:
            self._viewer_stack.setCurrentIndex(1)
        else:
            # VTK unavailable - keep showing placeholder/fallback message
            # The fallback message (index 1) explains why 3D viewer is unavailable
            self._viewer_stack.setCurrentIndex(1)
    
    def is_vtk_available(self) -> bool:
        """Check if VTK 3D viewer is available.
        
        Returns:
            True if VTK is working, False if fallback mode is active.
        """
        return self._vtk_available
    
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
        - For slab mode: box_z must equal 2*ice_thickness + water_thickness
        
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
            
            # Slab constraint: box_z must equal 2*ice_thickness + water_thickness
            box_z = self.box_z_input.value()
            ice_thickness = self.ice_thickness_input.value()
            water_thickness = self.water_thickness_input.value()
            expected_z = 2 * ice_thickness + water_thickness
            if abs(box_z - expected_z) > 0.01:  # 0.01 nm tolerance
                self.box_z_error.setText(
                    f"Box Z ({box_z:.2f} nm) must equal 2×ice + water = {expected_z:.2f} nm"
                )
                self.box_z_error.setVisible(True)
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
    
    def get_configuration(self) -> dict:
        """Get validated configuration values.
        
        Returns:
            Dictionary with configuration parameters:
            - mode: str ("slab", "pocket", or "piece")
            - box_x, box_y, box_z: float (nm)
            - seed: int
            - For slab mode: ice_thickness, water_thickness (float, nm)
            - For pocket mode: pocket_diameter (float, nm), pocket_shape (str)
            - For piece mode: no additional params (dimensions from candidate)
        
        Note:
            Should only be called after validate_configuration() returns True
        """
        # Map display text to mode identifier
        mode_map = {"Slab": "slab", "Pocket": "pocket", "Piece": "piece"}
        current_mode = mode_map[self.mode_combo.currentText()]
        
        config = {
            "mode": current_mode,
            "box_x": self.box_x_input.value(),
            "box_y": self.box_y_input.value(),
            "box_z": self.box_z_input.value(),
            "seed": self.seed_input.value(),
        }
        
        # Mode-specific parameters
        if current_mode == "slab":
            config["ice_thickness"] = self.ice_thickness_input.value()
            config["water_thickness"] = self.water_thickness_input.value()
        
        elif current_mode == "pocket":
            config["pocket_diameter"] = self.pocket_diameter_input.value()
            config["pocket_shape"] = self.pocket_shape_combo.currentText().lower()
        
        # Piece mode uses candidate dimensions (no additional params needed)
        
        return config
    
    def update_piece_info(self, candidate_size: tuple[float, float, float]) -> None:
        """Update piece mode info label with candidate dimensions.
        
        Args:
            candidate_size: (x, y, z) dimensions in nanometers from selected candidate
        """
        x, y, z = candidate_size
        self.piece_info_label.setText(
            f"Candidate dimensions: {x:.2f} × {y:.2f} × {z:.2f} nm"
        )
    
    def set_from_hydrate(self, hydrate_structure) -> None:
        """Pre-populate interface panel from hydrate structure.
        
        Extracts dimensions from the hydrate structure's unit cell and sets
        interface inputs accordingly.
        
        Args:
            hydrate_structure: HydrateStructure to derive interface from
        """
        from quickice.structure_generation.types import HydrateStructure
        
        # Extract dimensions from hydrate structure cell
        cell = hydrate_structure.cell  # (3, 3) array, stored as ROW vectors
        
        # Compute box extent from lattice vector norms (each row is a lattice vector)
        box_x = float(np.linalg.norm(cell[0]))  # Length of first lattice vector
        box_y = float(np.linalg.norm(cell[1]))  # Length of second lattice vector
        box_z = float(np.linalg.norm(cell[2]))  # Length of third lattice vector
        
        # Estimate ice thickness from water count
        # Rough estimate: ~0.3nm per water molecule layer
        # Get approximate layer count from cell volume
        volume = abs(np.linalg.det(cell))
        water_count = hydrate_structure.water_count
        # Volume per water molecule ≈ 0.03 nm³ (TIP4P-ICE)
        # Estimated thickness = (volume / area)^0.5
        if water_count > 0:
            avg_thickness = (volume / water_count) ** (1/3) * 2  # Two layers
            # Use reasonable thickness, not too thin
            ice_thickness = max(1.0, min(avg_thickness, 10.0))
        else:
            ice_thickness = 3.0  # Default fallback
        
        # Set mode to "Piece" (most appropriate for predefined hydrate structure)
        self.mode_combo.setCurrentText("Piece")
        
        # Set box dimensions using setValue()
        self.box_x_input.setValue(box_x)
        self.box_y_input.setValue(box_y)
        self.box_z_input.setValue(box_z)
        
        # Log the pre-population
        self.info_panel.append_log("")
        self.info_panel.append_log("=" * 50)
        self.info_panel.append_log("Interface pre-populated from hydrate structure")
        self.info_panel.append_log("=" * 50)
        self.info_panel.append_log(f"Box: {box_x:.2f} × {box_y:.2f} × {box_z:.2f} nm")
        self.info_panel.append_log(f"Mode: Piece (hydrate-derived)")
        self.info_panel.append_log(f"Water molecules: {hydrate_structure.water_count}")
        self.info_panel.append_log(f"Guest molecules: {hydrate_structure.guest_count}")
