"""Hydrate configuration panel for QuickIce GUI v4.0.

This module provides the HydratePanel class for hydrate configuration:
- Lattice type selection (sI, sII, sH)
- Guest molecule selection (CH4, THF, CO2, H2)
- Cage occupancy controls
- Supercell dimensions
- Lattice info display
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox,
    QFormLayout, QTextEdit, QPushButton, QStackedWidget
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import (
    HydrateConfig, HydrateLatticeInfo,
    HYDRATE_LATTICES, GUEST_MOLECULES
)
from quickice.gui.hydrate_viewer import HydrateViewerWidget


class HydratePanel(QWidget):
    """Panel for hydrate structure configuration.
    
    Provides UI for:
    - Selecting hydrate lattice type
    - Selecting guest molecule
    - Setting cage occupancy percentages
    - Setting supercell dimensions
    
    Signals:
        configuration_changed: Emitted when any configuration changes
        generate_requested: Emitted when generate button clicked
    """
    
    configuration_changed = Signal()
    generate_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # State tracking for generation workflow
        self._current_structure = None
        self._worker = None
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup UI components with horizontal layout (matching Interface Panel).
        
        Layout:
        - Left column: Configuration controls (lattice, guest, occupancy, supercell, info, generate)
        - Right column: Log panel + 3D viewer (stretch=1)
        """
        # Create top-level horizontal layout (like InterfacePanel)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # === LEFT COLUMN: Configuration Controls ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Lattice selection group
        lattice_group = self._create_lattice_group()
        left_layout.addWidget(lattice_group)
        
        # Guest molecule group
        guest_group = self._create_guest_group()
        left_layout.addWidget(guest_group)
        
        # Occupancy group
        occupancy_group = self._create_occupancy_group()
        left_layout.addWidget(occupancy_group)
        
        # Supercell group
        supercell_group = self._create_supercell_group()
        left_layout.addWidget(supercell_group)
        
        # Lattice info display
        info_group = self._create_info_group()
        left_layout.addWidget(info_group)
        
        # Generate button
        self.generate_button = QPushButton("Generate Hydrate")
        self.generate_button.clicked.connect(lambda: self.generate_requested.emit())
        left_layout.addWidget(self.generate_button)
        
        left_layout.addStretch()
        
        # === RIGHT COLUMN: Viewer Section ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # Log info panel - shows generation progress
        log_group = QGroupBox("Generation Log")
        log_layout = QVBoxLayout()
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(100)
        self._log_text.setPlaceholderText("Generation log will appear here...")
        log_layout.addWidget(self._log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Viewer toolbar with toggle buttons
        viewer_toolbar = QStackedWidget()
        viewer_toolbar.setMaximumHeight(40)
        
        # Toolbar page (index 0) - toolbar row
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Unit cell toggle button (matching Tab 1's btn_unit_cell)
        self.btn_unit_cell = QPushButton("Unit cell")
        self.btn_unit_cell.setCheckable(True)
        self.btn_unit_cell.setChecked(False)
        self.btn_unit_cell.clicked.connect(self._on_unit_cell_toggled)
        toolbar_layout.addWidget(self.btn_unit_cell)
        
        toolbar_layout.addStretch()
        
        # Add toolbar to stacked widget
        viewer_toolbar.addWidget(toolbar_widget)
        
        # Add toolbar above viewer
        right_layout.addWidget(viewer_toolbar)
        
        # 3D viewer widget (stretch=1 to fill remaining space)
        self.hydrate_viewer = HydrateViewerWidget()
        right_layout.addWidget(self.hydrate_viewer, stretch=1)
        
        # Add columns to top-level layout (left gets 2/5, right gets 3/5)
        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=3)
    
    def _create_lattice_group(self) -> QGroupBox:
        """Create lattice type selection group."""
        group = QGroupBox("Hydrate Lattice")
        layout = QFormLayout()
        
        self.lattice_combo = QComboBox()
        for lattice_id, lattice_info in HYDRATE_LATTICES.items():
            self.lattice_combo.addItem(
                f"{lattice_id} - {lattice_info['description']}",
                lattice_id
            )
        
        layout.addRow("Lattice type:", self.lattice_combo)
        group.setLayout(layout)
        return group
    
    def _create_guest_group(self) -> QGroupBox:
        """Create guest molecule selection group."""
        group = QGroupBox("Guest Molecule")
        layout = QFormLayout()
        
        self.guest_combo = QComboBox()
        for guest_id, guest_info in GUEST_MOLECULES.items():
            self.guest_combo.addItem(
                f"{guest_info['name']} ({guest_info['formula']})",
                guest_id
            )
        
        layout.addRow("Guest type:", self.guest_combo)
        
        # Force field info label
        self.ff_label = QLabel()
        self.ff_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addRow("Force field:", self.ff_label)
        self._update_ff_label()
        
        group.setLayout(layout)
        return group
    
    def _create_occupancy_group(self) -> QGroupBox:
        """Create cage occupancy controls group."""
        group = QGroupBox("Cage Occupancy")
        layout = QFormLayout()
        
        # Small cage occupancy
        self.occupancy_small = QDoubleSpinBox()
        self.occupancy_small.setRange(0.0, 100.0)
        self.occupancy_small.setValue(100.0)
        self.occupancy_small.setSuffix("%")
        self.occupancy_small.setDecimals(1)
        layout.addRow("Small cages:", self.occupancy_small)
        
        # Large cage occupancy
        self.occupancy_large = QDoubleSpinBox()
        self.occupancy_large.setRange(0.0, 100.0)
        self.occupancy_large.setValue(100.0)
        self.occupancy_large.setSuffix("%")
        self.occupancy_large.setDecimals(1)
        layout.addRow("Large cages:", self.occupancy_large)
        
        group.setLayout(layout)
        return group
    
    def _create_supercell_group(self) -> QGroupBox:
        """Create supercell dimensions group."""
        group = QGroupBox("Supercell Dimensions")
        layout = QFormLayout()
        
        row = QHBoxLayout()
        self.supercell_x = QSpinBox()
        self.supercell_x.setRange(1, 10)
        self.supercell_x.setValue(1)
        row.addWidget(self.supercell_x)
        row.addWidget(QLabel("×"))
        
        self.supercell_y = QSpinBox()
        self.supercell_y.setRange(1, 10)
        self.supercell_y.setValue(1)
        row.addWidget(self.supercell_y)
        row.addWidget(QLabel("×"))
        
        self.supercell_z = QSpinBox()
        self.supercell_z.setRange(1, 10)
        self.supercell_z.setValue(1)
        row.addWidget(self.supercell_z)
        
        layout.addRow("Repetition:", row)
        group.setLayout(layout)
        return group
    
    def _create_info_group(self) -> QGroupBox:
        """Create lattice info display group."""
        group = QGroupBox("Lattice Information")
        layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self._update_info_display()
        
        layout.addWidget(self.info_text)
        group.setLayout(layout)
        return group
    
    def _setup_viewer_section(self):
        """Placeholder - viewer is integrated directly in _setup_ui layout now."""
    
    def append_log(self, message: str):
        """Append a message to the log display.
        
        Args:
            message: Message to append
        """
        self._log_text.append(message)
    
    def clear_log(self):
        """Clear the log display."""
        self._log_text.clear()
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.lattice_combo.currentIndexChanged.connect(self._on_lattice_changed)
        self.guest_combo.currentIndexChanged.connect(self._on_guest_changed)
        self.occupancy_small.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.occupancy_large.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_x.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_y.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_z.valueChanged.connect(lambda: self.configuration_changed.emit())
    
    def _on_lattice_changed(self):
        """Handle lattice type change."""
        self._update_info_display()
        self.configuration_changed.emit()
    
    def _on_guest_changed(self):
        """Handle guest molecule change."""
        self._update_ff_label()
        self._update_info_display()  # Update guest fit info
        self.configuration_changed.emit()
    
    def _update_ff_label(self):
        """Update force field label based on selected guest."""
        guest_id = self.guest_combo.currentData()
        if guest_id and guest_id in GUEST_MOLECULES:
            ff = GUEST_MOLECULES[guest_id].get('force_field', 'Unknown')
            self.ff_label.setText(ff)
    
    def _update_info_display(self):
        """Update lattice info display."""
        lattice_id = self.lattice_combo.currentData()
        guest_id = self.guest_combo.currentData()
        
        if not lattice_id:
            return
        
        try:
            info = HydrateLatticeInfo.from_lattice_type(lattice_id)
        except ValueError:
            self.info_text.setText("Invalid lattice type")
            return
        
        lines = [
            f"Lattice: {info.description}",
            f"Water molecules per unit cell: {info.unit_cell_molecules}",
            f"Total cages per unit cell: {info.total_cages}",
            "",
            "Cage types:",
        ]
        
        for cage_name, count in info.cage_counts.items():
            # Check if guest fits
            fits = ""
            if guest_id and guest_id in GUEST_MOLECULES:
                # Check if guest fits in this cage (from HYDRATE_LATTICES)
                lattice = HYDRATE_LATTICES[lattice_id]
                for cage_size, cage_info in lattice["cages"].items():
                    if cage_info["name"] == cage_name:
                        if guest_id in cage_info.get("guest_fits", []):
                            fits = " ✓"
                        else:
                            fits = " ✗ (too large)"
                        break
            lines.append(f"  {cage_name}: {count}{fits}")
        
        self.info_text.setText("\n".join(lines))
    
    def get_configuration(self) -> HydrateConfig:
        """Get current configuration as HydrateConfig.
        
        Returns:
            HydrateConfig with current UI values
        """
        return HydrateConfig(
            lattice_type=self.lattice_combo.currentData(),
            guest_type=self.guest_combo.currentData(),
            cage_occupancy_small=self.occupancy_small.value(),
            cage_occupancy_large=self.occupancy_large.value(),
            supercell_x=self.supercell_x.value(),
            supercell_y=self.supercell_y.value(),
            supercell_z=self.supercell_z.value(),
        )
    
    def _on_unit_cell_toggled(self):
        """Toggle unit cell box visibility."""
        if not self.hydrate_viewer.is_vtk_available():
            return
        
        visible = self.btn_unit_cell.isChecked()
        self.hydrate_viewer.set_unit_cell_visible(visible)
