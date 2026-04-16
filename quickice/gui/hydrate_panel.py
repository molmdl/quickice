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
    QFormLayout, QTextEdit, QPushButton, QSplitter
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
        self._setup_viewer_section()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        
        # Lattice selection group
        lattice_group = self._create_lattice_group()
        layout.addWidget(lattice_group)
        
        # Guest molecule group
        guest_group = self._create_guest_group()
        layout.addWidget(guest_group)
        
        # Occupancy group
        occupancy_group = self._create_occupancy_group()
        layout.addWidget(occupancy_group)
        
        # Supercell group
        supercell_group = self._create_supercell_group()
        layout.addWidget(supercell_group)
        
        # Lattice info display
        info_group = self._create_info_group()
        layout.addWidget(info_group)
        
        # Generate button
        self.generate_button = QPushButton("Generate Hydrate")
        self.generate_button.clicked.connect(lambda: self.generate_requested.emit())
        layout.addWidget(self.generate_button)
        
        layout.addStretch()
    
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
        """Setup viewer section with horizontal splitter.
        
        Reorganizes the panel to use horizontal layout:
        - Left side: Configuration groups (using existing QVBoxLayout)
        - Right side: Viewer section (QSplitter with log + 3D viewer)
        
        This matches Tab 1 behavior where viewer is on the right side.
        """
        # Store reference to existing layout
        main_layout = self.layout()
        
        # Create a new group for viewer section on the right
        viewer_group = QGroupBox("Structure Viewer")
        
        # Use horizontal splitter for log + viewer on the right side
        viewer_splitter = QSplitter(Qt.Horizontal)
        
        # Log info panel - shows generation progress
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        self._log_text.setPlaceholderText("Generation log will appear here...")
        viewer_splitter.addWidget(self._log_text)
        
        # 3D viewer widget
        self.hydrate_viewer = HydrateViewerWidget()
        viewer_splitter.addWidget(self.hydrate_viewer)
        
        # Set initial sizes: 250px for log, rest to viewer
        viewer_splitter.setSizes([250, 500])
        
        viewer_layout = QVBoxLayout()
        viewer_layout.addWidget(viewer_splitter)
        viewer_group.setLayout(viewer_layout)
        
        # Remove existing widget and add new splitter arrangement
        # First, find the widget that contains all config groups
        # We'll modify the existing main_layout to be horizontal
        
        # Get current main layout widget (if any added via addWidget)
        # Instead, reorganize: wrap existing config in left widget, create right widget
        
        # Create container for configuration controls (left side)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Move all existing widgets except last one to left layout
        # (main layout has: lattice_group, guest_group, occupancy_group, supercell_group, info_group, generate_button, spacer)
        # We need to find and move the config groups to left layout
        for i in range(main_layout.count() - 1):
            item = main_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                main_layout.removeWidget(widget)
                left_layout.addWidget(widget)
        
        # Add the generate button to left
        if self.generate_button:
            left_layout.addWidget(self.generate_button)
        
        left_layout.addStretch()
        
        # Create horizontal splitter for left config + right viewer
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Add left config panel
        top_splitter.addWidget(left_widget)
        
        # Add right viewer group
        top_splitter.addWidget(viewer_group)
        
        # Set initial sizes: 400px for config, 600px for viewer (like Tab 1)
        top_splitter.setSizes([400, 600])
        
        # Remove old layout and add new splitter
        # Clear the main layout (but keep the reference)
        while main_layout.count():
            main_layout.removeItem(main_layout.itemAt(0))
        
        main_layout.addWidget(top_splitter)
    
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
