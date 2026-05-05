"""Solute insertion panel for QuickIce GUI v4.5.

This module provides the SolutePanel class for solute insertion configuration:
- Concentration input (mol/L)
- Solute type selection (THF or CH4)
- Molecule count preview
- Liquid volume display
- Insert Solutes button
- Log panel for status messages
- 3D viewer for solute visualization

Signals:
    configuration_changed: Emitted when concentration or solute type changes
    insert_requested: Emitted when Insert Solutes button clicked
"""

import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox,
    QFormLayout, QPushButton, QTextEdit
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import SoluteConfig
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.gui.solute_viewer import SoluteViewerWidget
from quickice.gui.view import HelpIcon

logger = logging.getLogger(__name__)


class SolutePanel(QWidget):
    """Panel for solute insertion configuration.
    
    Provides UI for:
    - Setting concentration in mol/L
    - Selecting solute type (THF or CH4)
    - Displaying calculated molecule count
    - Displaying liquid volume
    - Inserting solutes into structure
    
    Signals:
        configuration_changed: Emitted when concentration or type changes
        insert_requested: Emitted when Insert Solutes button clicked
    """
    
    configuration_changed = Signal()
    insert_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._liquid_volume_nm3 = 0.0  # Set by caller (MainWindow)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup UI components with horizontal layout (like IonPanel).
        
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

        # Solute type selection group
        solute_type_group = self._create_solute_type_group()
        left_layout.addWidget(solute_type_group)

        # Molecule count display group
        count_group = self._create_molecule_count_group()
        left_layout.addWidget(count_group)

        # Volume display group
        volume_group = self._create_volume_group()
        left_layout.addWidget(volume_group)

        # Insert button
        insert_row = QHBoxLayout()
        self.insert_button = QPushButton("Insert Solutes")
        insert_row.addWidget(self.insert_button)
        insert_row.addWidget(HelpIcon(
            "Insert solute molecules into the liquid water region.\n"
            "Calculated from concentration and liquid volume."
        ))
        insert_row.addStretch()
        left_layout.addLayout(insert_row)

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
        self.solute_viewer = SoluteViewerWidget()
        right_layout.addWidget(self.solute_viewer, stretch=1)

        # Add columns to top-level layout (left gets 2/5, right gets 3/5)
        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=3)

    def _create_concentration_group(self) -> QGroupBox:
        """Create concentration input group."""
        group = QGroupBox("Concentration")
        layout = QFormLayout()

        # Concentration value input with unit label
        conc_layout = QHBoxLayout()
        self.concentration_spin = QDoubleSpinBox()
        self.concentration_spin.setRange(0.0, 2.0)
        self.concentration_spin.setDecimals(3)
        self.concentration_spin.setValue(0.1)
        self.concentration_spin.setSingleStep(0.01)
        conc_layout.addWidget(self.concentration_spin)

        # Unit label (mol/L only for Phase 33)
        unit_label = QLabel("mol/L")
        conc_layout.addWidget(unit_label)

        # Add help icon
        conc_layout.addWidget(HelpIcon(
            "Solute concentration in mol/L (M).\n"
            "Typical values:\n"
            "• CH4 in hydrates: ~0.05-0.10 M\n"
            "• THF in hydrates: ~0.05-0.20 M"
        ))
        conc_layout.addStretch()

        layout.addRow("Value:", conc_layout)

        # Real-time molecule count preview
        self.preview_label = QLabel("0 molecules")
        self.preview_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addRow("Preview:", self.preview_label)

        group.setLayout(layout)
        return group

    def _create_solute_type_group(self) -> QGroupBox:
        """Create solute type selection group."""
        group = QGroupBox("Solute Type")
        layout = QHBoxLayout()
        
        self.solute_type_combo = QComboBox()
        self.solute_type_combo.addItems(["CH₄", "THF"])
        
        layout.addWidget(self.solute_type_combo)
        layout.addWidget(HelpIcon(
            "Select solute type:\n"
            "• CH₄: Methane (gas)\n"
            "• THF: Tetrahydrofuran (liquid)"
        ))
        layout.addStretch()
        
        group.setLayout(layout)
        return group

    def _create_molecule_count_group(self) -> QGroupBox:
        """Create molecule count display group."""
        group = QGroupBox("Molecule Count")
        layout = QFormLayout()

        count_row = QHBoxLayout()
        self.molecule_count_display = QLabel("0 molecules")
        self.molecule_count_display.setStyleSheet("color: #666;")
        count_row.addWidget(self.molecule_count_display)
        count_row.addWidget(HelpIcon(
            "Calculated number of solute molecules based on concentration and liquid volume.\n"
            "N = C_M × V × N_A (Avogadro's number)"
        ))
        count_row.addStretch()

        layout.addRow("Count:", count_row)
        group.setLayout(layout)
        return group

    def _create_volume_group(self) -> QGroupBox:
        """Create volume display group."""
        group = QGroupBox("Liquid Region")
        layout = QFormLayout()

        vol_row = QHBoxLayout()
        self.liquid_volume_label = QLabel("-- nm³")
        self.liquid_volume_label.setStyleSheet("color: #666;")
        vol_row.addWidget(self.liquid_volume_label)
        vol_row.addWidget(HelpIcon(
            "Volume of liquid water region in the interface structure.\n"
            "Used to calculate solute molecule count."
        ))
        vol_row.addStretch()

        layout.addRow("Volume:", vol_row)
        group.setLayout(layout)
        return group
    
    def _setup_connections(self):
        """Setup signal connections."""
        # Real-time molecule count preview
        self.concentration_spin.valueChanged.connect(self._update_preview)
        self.solute_type_combo.currentIndexChanged.connect(self._update_preview)

        # Emit configuration_changed signal
        self.concentration_spin.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.solute_type_combo.currentIndexChanged.connect(lambda: self.configuration_changed.emit())

        # Insert button connects to insert_requested signal
        self.insert_button.clicked.connect(lambda: self.insert_requested.emit())
    
    def _update_preview(self):
        """Update molecule count preview in real-time."""
        if self._liquid_volume_nm3 <= 0:
            self.preview_label.setText("No liquid volume")
            return

        concentration = self.concentration_spin.value()

        inserter = SoluteInserter()
        molecule_count = inserter.calculate_molecule_count(concentration, self._liquid_volume_nm3)

        self.preview_label.setText(f"{molecule_count} molecules")
    
    def set_liquid_volume(self, volume_nm3: float):
        """Set the liquid volume for molecule count calculation.
        
        Args:
            volume_nm3: Liquid region volume in cubic nanometers
        """
        self._liquid_volume_nm3 = volume_nm3
        self.liquid_volume_label.setText(f"{volume_nm3:.2f} nm³")
        self._update_preview()
    
    def get_configuration(self) -> SoluteConfig:
        """Get current SoluteConfig from panel values.
        
        Returns:
            SoluteConfig with current concentration and solute type
        """
        # Map combo box text to solute type string
        solute_type_text = self.solute_type_combo.currentText()
        solute_type = "CH4" if solute_type_text == "CH₄" else "THF"
        
        return SoluteConfig(
            concentration_molar=self.concentration_spin.value(),
            solute_type=solute_type
        )
    
    def get_liquid_volume(self) -> float:
        """Get the liquid volume in nm³.
        
        Returns:
            Liquid volume in cubic nanometers
        """
        return self._liquid_volume_nm3
    
    def log_message(self, message: str):
        """Append a message to the log display with timestamp.
        
        Args:
            message: Message to append
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{timestamp}] {message}")
    
    def clear_log(self):
        """Clear the log display."""
        self._log_text.clear()
    
    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.
        
        Delegates to the internal SoluteViewerWidget.
        """
        self.solute_viewer.hide_placeholder()
