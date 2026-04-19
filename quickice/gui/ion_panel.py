"""Ion insertion panel for QuickIce GUI v4.0.

This module provides the IonPanel class for ion insertion configuration:
- NaCl concentration input (mol/L)
- Ion pair count display
- Liquid volume display
- Insert Ions button
- Log panel for status messages
- 3D viewer for ion visualization

Signals:
    configuration_changed: Emitted when concentration changes
    insert_requested: Emitted when Insert Ions button clicked
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox,
    QFormLayout, QPushButton, QTextEdit
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import IonConfig
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.gui.ion_viewer import IonViewerWidget


class IonPanel(QWidget):
    """Panel for NaCl ion insertion configuration.
    
    Provides UI for:
    - Setting NaCl concentration (mol/L)
    - Displaying calculated ion pair count
    - Displaying liquid volume
    - Inserting ions into structure
    
    Signals:
        configuration_changed: Emitted when concentration changes
        insert_requested: Emitted when Insert Ions button clicked
    """
    
    configuration_changed = Signal()
    insert_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._liquid_volume_nm3 = 0.0  # Set by caller (MainWindow)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup UI components with horizontal layout (like HydratePanel).
        
        Layout:
        - Left column (stretch=2): Configuration controls
        - Right column (stretch=3): Log panel + 3D viewer
        """
        # Create top-level horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # === LEFT COLUMN: Configuration Controls ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Concentration input group
        conc_group = self._create_concentration_group()
        left_layout.addWidget(conc_group)

        # Ion count display group
        count_group = self._create_ion_count_group()
        left_layout.addWidget(count_group)

        # Volume display group
        volume_group = self._create_volume_group()
        left_layout.addWidget(volume_group)

        # Insert button
        self.insert_button = QPushButton("Insert Ions")
        self.insert_button.setToolTip(
            "Insert Na+ and Cl- ions into the liquid water region.\n"
            "Calculated from concentration and liquid volume."
        )
        self.insert_button.clicked.connect(lambda: self.insert_requested.emit())
        left_layout.addWidget(self.insert_button)

        left_layout.addStretch()

        # === RIGHT COLUMN: Viewer Section ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        # Log panel - shows insertion status messages
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout()
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(80)
        self._log_text.setPlaceholderText("Status messages will appear here...")
        log_layout.addWidget(self._log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        # 3D viewer widget (stretch=1 to fill remaining space)
        self.ion_viewer = IonViewerWidget()
        right_layout.addWidget(self.ion_viewer, stretch=1)

        # Add columns to top-level layout (left gets 2/5, right gets 3/5)
        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=3)

    def _create_concentration_group(self) -> QGroupBox:
        """Create concentration input group."""
        group = QGroupBox("NaCl Concentration")
        layout = QFormLayout()

        self.concentration_input = QDoubleSpinBox()
        self.concentration_input.setRange(0.0, 5.0)
        self.concentration_input.setDecimals(2)
        self.concentration_input.setValue(0.0)
        self.concentration_input.setSuffix(" mol/L")
        self.concentration_input.setToolTip(
            "Target NaCl concentration in mol/L (M).\n"
            "Typical seawater: ~0.6 M.\n"
            "For drinking water: <0.05 M."
        )

        layout.addRow("Concentration:", self.concentration_input)
        group.setLayout(layout)
        return group

    def _create_ion_count_group(self) -> QGroupBox:
        """Create ion count display group."""
        group = QGroupBox("Ion Pairs")
        layout = QFormLayout()

        self.ion_count_display = QLabel("Na+ 0, Cl- 0 pairs")
        self.ion_count_display.setStyleSheet("color: #666;")
        self.ion_count_display.setToolTip(
            "Calculated number of ion pairs based on concentration and liquid volume.\n"
            "Each pair = 1 Na+ + 1 Cl- (charge neutral)."
        )

        layout.addRow("Ion count:", self.ion_count_display)
        group.setLayout(layout)
        return group

    def _create_volume_group(self) -> QGroupBox:
        """Create volume display group."""
        group = QGroupBox("Liquid Region")
        layout = QFormLayout()

        self.liquid_volume_label = QLabel("-- nm³")
        self.liquid_volume_label.setStyleSheet("color: #666;")
        self.liquid_volume_label.setToolTip(
            "Volume of liquid water region in the interface structure.\n"
            "Used to calculate ion count: N_ions = concentration × volume × NA"
        )

        layout.addRow("Volume:", self.liquid_volume_label)
        group.setLayout(layout)
        return group
    
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
        self.concentration_input.valueChanged.connect(self._on_concentration_changed)
    
    def _on_concentration_changed(self, value: float):
        """Handle concentration value change."""
        self._update_ion_count()
        self.configuration_changed.emit()
    
    def _update_ion_count(self):
        """Update ion count display based on current concentration and volume."""
        config = self.get_configuration()
        inserter = IonInserter(config)
        
        if self._liquid_volume_nm3 > 0:
            # calculate_ion_pairs needs (concentration_molar, liquid_volume_nm3)
            pair_count = inserter.calculate_ion_pairs(
                config.concentration_molar, 
                self._liquid_volume_nm3
            )
            self.ion_count_display.setText(f"Na+ {pair_count}, Cl- {pair_count} pairs")
        else:
            self.ion_count_display.setText("Na+ 0, Cl- 0 pairs")
    
    def set_liquid_volume(self, volume_nm3: float):
        """Set the liquid volume for ion count calculation.
        
        Args:
            volume_nm3: Liquid region volume in cubic nanometers
        """
        self._liquid_volume_nm3 = volume_nm3
        self.liquid_volume_label.setText(f"{volume_nm3:.2f} nm³")
        self._update_ion_count()
    
    def get_configuration(self) -> IonConfig:
        """Get current IonConfig from panel values.
        
        Returns:
            IonConfig with current concentration setting
        """
        return IonConfig(
            concentration_molar=self.concentration_input.value()
        )
    
    def get_liquid_volume(self) -> float:
        """Get the liquid volume in nm³.
        
        Returns:
            Liquid volume in cubic nanometers
        """
        return self._liquid_volume_nm3
    
    def get_inserter(self) -> IonInserter:
        """Get IonInserter instance with current configuration.
        
        Returns:
            IonInserter configured with current IonConfig
        """
        return IonInserter(self.get_configuration())