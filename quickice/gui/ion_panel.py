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

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox,
    QFormLayout, QPushButton, QTextEdit
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import IonConfig
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.gui.ion_viewer import IonViewerWidget
from quickice.gui.view import HelpIcon

if TYPE_CHECKING:
    from quickice.structure_generation.types import CustomMoleculeStructure, InterfaceStructure, SoluteStructure

logger = logging.getLogger(__name__)


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
        self._current_source = "Interface"  # Track current source selection (default: Interface)
        
        # Source availability tracking
        self._interface_available = False  # Track if Interface source has structure available
        self._custom_molecule_available = False  # Track if Custom Molecule source has structure available
        self._solute_available = False  # Track if Solute source has structure available
        
        # Source structure storage
        self._interface_structure: "InterfaceStructure" | None = None
        self._custom_molecule_structure: "CustomMoleculeStructure" | None = None
        self._solute_structure: "SoluteStructure" | None = None
        
        self._setup_ui()
        self._setup_connections()
        # Set initial button state based on default source (Interface) and availability
        self._update_insert_button_state()
    
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
        
        # Source selector row (at top, before other controls - follows Interface tab pattern)
        source_row = QHBoxLayout()
        source_label = QLabel("Source:")
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Interface", "Custom Molecule", "Solute"])
        self.source_combo.setToolTip(
            "Select source for ion insertion:\n"
            "• Interface — Use interface structure from Tab 2\n"
            "• Custom Molecule — Use custom molecule structure from Tab 3\n"
            "• Solute — Use solute structure from Tab 4"
        )
        source_row.addWidget(source_label)
        source_row.addWidget(HelpIcon(
            "Source type for ion insertion. Interface uses existing ice-water structures. "
            "Custom Molecule and Solute use structures from their respective tabs."
        ))
        source_row.addWidget(self.source_combo)
        source_row.addStretch()
        left_layout.addLayout(source_row)
        
        left_layout.addSpacing(15)
        
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
        insert_row = QHBoxLayout()
        self.insert_button = QPushButton("Insert Ions")
        self.insert_button.clicked.connect(lambda: self.insert_requested.emit())
        insert_row.addWidget(self.insert_button)
        insert_row.addWidget(HelpIcon(
            "Insert Na+ and Cl- ions into the liquid water region.\n"
            "Calculated from concentration and liquid volume."
        ))
        insert_row.addStretch()
        left_layout.addLayout(insert_row)

        # Charge warning label (initially hidden, shown when Custom Molecule source has non-neutral charge)
        self.charge_warning_label = QLabel()
        self.charge_warning_label.setStyleSheet("color: #d9534f; font-weight: bold; padding: 5px;")
        self.charge_warning_label.setWordWrap(True)
        self.charge_warning_label.setVisible(False)  # Initially hidden
        left_layout.addWidget(self.charge_warning_label)

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

        conc_row = QHBoxLayout()
        self.concentration_input = QDoubleSpinBox()
        self.concentration_input.setRange(0.0, 5.0)
        self.concentration_input.setDecimals(2)
        self.concentration_input.setValue(0.5)  # Default 0.5 M NaCl
        self.concentration_input.setSuffix(" mol/L")
        conc_row.addWidget(self.concentration_input)
        conc_row.addWidget(HelpIcon(
            "Target NaCl concentration in mol/L (M).\n"
            "Typical seawater: ~0.6 M.\n"
            "For drinking water: <0.05 M.\n"
            "\n"
            "Ion model: Madrid2019 (Na⁺/Cl⁻ charges ±0.85e).\n"
            "Ref: Zeron et al., J. Chem. Phys. 151, 134504 (2019)."
        ))
        conc_row.addStretch()

        layout.addRow("Concentration:", conc_row)
        group.setLayout(layout)
        return group

    def _create_ion_count_group(self) -> QGroupBox:
        """Create ion count display group."""
        group = QGroupBox("Ion Pairs")
        layout = QFormLayout()

        count_row = QHBoxLayout()
        self.ion_count_display = QLabel("Na+ 0, Cl- 0 pairs")
        self.ion_count_display.setStyleSheet("color: #666;")
        count_row.addWidget(self.ion_count_display)
        count_row.addWidget(HelpIcon(
            "Calculated number of ion pairs based on concentration and liquid volume.\n"
            "Each pair = 1 Na+ + 1 Cl- (charge neutral)."
        ))
        count_row.addStretch()

        layout.addRow("Ion count:", count_row)
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
            "Used to calculate ion count: N_ions = concentration × volume × NA"
        ))
        vol_row.addStretch()

        layout.addRow("Volume:", vol_row)
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
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
    
    def _on_concentration_changed(self, value: float):
        """Handle concentration value change."""
        self._update_ion_count()
        self.configuration_changed.emit()
    
    def _on_source_changed(self, index: int):
        """Handle source selection change.
        
        Follows InterfacePanel._on_source_changed pattern (lines 532-564 of interface_panel.py):
        - Map index to source name
        - Update internal state
        - Enable/disable controls based on source
        - Clear 3D viewer
        - Log source change
        - Update Insert button state
        - Update charge warning visibility
        - Emit configuration_changed signal
        
        Args:
            index: 0 = Interface, 1 = Custom Molecule, 2 = Solute
        """
        # Map index to source name
        source_names = ["Interface", "Custom Molecule", "Solute"]
        source_name = source_names[index] if 0 <= index < len(source_names) else "Interface"
        
        # Update internal state
        self._current_source = source_name
        
        # Enable/disable controls based on source
        # Concentration is always enabled for all sources
        # Insert button state handled by _update_insert_button_state()
        
        # Clear 3D viewer
        if hasattr(self.ion_viewer, 'clear'):
            self.ion_viewer.clear()
        
        # Log source change
        self.append_log(f"Source switched to {source_name}")
        
        # Update Insert button state based on source availability
        self._update_insert_button_state()
        
        # Update charge warning visibility
        self._update_charge_warning()
        
        # Emit configuration_changed signal
        self.configuration_changed.emit()
    
    def _check_source_availability(self) -> bool:
        """Check if current source has data available.
        
        For now, returns True for all sources.
        MainWindow will provide actual availability checks in future integration.
        
        Returns:
            True if source has data available, False otherwise
        """
        # Placeholder implementation - will be enhanced by MainWindow
        # For Interface source: check if interface structure exists
        # For Custom Molecule: check if custom molecule is loaded
        # For Solute: check if solute structure exists
        return True
    
    def _update_insert_button_state(self):
        """Update Insert button enabled state and tooltip based on source availability.
        
        Follows Interface tab pattern: when source has no data, disable button with
        explanatory tooltip.
        """
        if self._current_source == "Interface":
            if not self._interface_available:
                self.insert_button.setEnabled(False)
                self.insert_button.setToolTip("Generate Interface structure first (Tab 2)")
            else:
                self.insert_button.setEnabled(True)
                self.insert_button.setToolTip("Insert Na+ and Cl- ions into the liquid water region.")
        
        elif self._current_source == "Custom Molecule":
            if not self._custom_molecule_available:
                self.insert_button.setEnabled(False)
                self.insert_button.setToolTip("Generate Custom Molecules first (Tab 3)")
            else:
                self.insert_button.setEnabled(True)
                self.insert_button.setToolTip("Insert ions into Custom Molecule system (direct path).")
        
        elif self._current_source == "Solute":
            if not self._solute_available:
                self.insert_button.setEnabled(False)
                self.insert_button.setToolTip("Insert Solutes first (Tab 4)")
            else:
                self.insert_button.setEnabled(True)
                self.insert_button.setToolTip("Insert ions into Solute structure.")
        
        else:
            self.insert_button.setEnabled(False)
            self.insert_button.setToolTip("Select a source structure")
    
    def set_interface_available(self, available: bool):
        """Set whether Interface source has structure available.
        
        Called by MainWindow when interface is generated.
        
        Args:
            available: True if interface structure exists, False otherwise
        """
        self._interface_available = available
        self._update_insert_button_state()
    
    def set_custom_molecule_structure(self, structure: "CustomMoleculeStructure"):
        """Set Custom Molecule structure for use as source.
        
        Args:
            structure: CustomMoleculeStructure from Tab 3 (Custom Molecule tab)
        """
        self._custom_molecule_structure = structure
        self._custom_molecule_available = structure is not None
        
        # Update button state if currently on Custom Molecule source
        if self._current_source == "Custom Molecule":
            self._update_insert_button_state()
        
        # Update charge warning when custom molecule structure changes
        self._update_charge_warning()
        
        logger.info(f"Custom Molecule structure set: {structure.custom_molecule_count} molecules")
    
    def set_interface_structure(self, structure: "InterfaceStructure"):
        """Set Interface structure for use as source.
        
        Args:
            structure: InterfaceStructure from Tab 2 (Interface tab)
        """
        self._interface_structure = structure
        self._interface_available = structure is not None
        
        # Update button state if currently on Interface source
        if self._current_source == "Interface":
            self._update_insert_button_state()
        
        logger.info(f"Interface structure set: {structure.ice_nmolecules} ice + {structure.water_nmolecules} water molecules")
    
    def set_solute_structure(self, structure: "SoluteStructure"):
        """Set Solute structure for use as source.
        
        Args:
            structure: SoluteStructure from Tab 4 (Solute tab)
        """
        self._solute_structure = structure
        self._solute_available = structure is not None
        
        # Update button state if currently on Solute source
        if self._current_source == "Solute":
            self._update_insert_button_state()
        
        logger.info(f"Solute structure set: {structure.n_molecules} {structure.solute_type} molecules")
    
    def get_current_source_structure(self) -> "InterfaceStructure | CustomMoleculeStructure | SoluteStructure | None":
        """Get the current source structure based on selection.
        
        Returns:
            InterfaceStructure, CustomMoleculeStructure, or SoluteStructure based on current source selection
        """
        if self._current_source == "Interface":
            return self._interface_structure
        elif self._current_source == "Custom Molecule":
            return self._custom_molecule_structure
        elif self._current_source == "Solute":
            return self._solute_structure
        else:
            return None
    
    def _update_charge_warning(self):
        """Update charge warning label visibility.
        
        Shows warning when Custom Molecule source has non-neutral charge.
        Warning is informational only - does NOT prevent generation.
        
        Note: For Custom Molecule source, the molecule itself may have non-neutral
        charge (user-provided). Interface and Solute sources assume neutral systems.
        """
        # Only show warning for Custom Molecule source
        if self._current_source != "Custom Molecule":
            self.charge_warning_label.setVisible(False)
            return
        
        # Get total charge from ion configuration
        total_charge = self.get_total_charge()
        
        # Show/hide warning based on charge
        if total_charge != 0:
            self.charge_warning_label.setVisible(True)
            # Format: "Charge: +2.0 (non-neutral)" or "Charge: -1.0 (non-neutral)"
            sign = "+" if total_charge > 0 else ""
            self.charge_warning_label.setText(
                f"Charge: {sign}{total_charge:.1f} (non-neutral)"
            )
        else:
            self.charge_warning_label.setVisible(False)
    
    def get_total_charge(self) -> float:
        """Calculate total charge from source structure.
        
        For Custom Molecule source: total charge = molecule_charge × molecule_count.
        For Interface and Solute sources: always 0.0 (neutral systems).
        
        Returns:
            Total charge (positive = excess positive, negative = excess negative)
        """
        # Custom Molecule source: compute charge from molecule_charge × count
        if self._current_source == "Custom Molecule":
            if self._custom_molecule_structure is not None:
                molecule_charge = getattr(
                    self._custom_molecule_structure, 'molecule_charge', 0.0
                )
                molecule_count = self._custom_molecule_structure.custom_molecule_count
                return molecule_charge * molecule_count
            return 0.0
        
        # Interface and Solute sources: neutral systems by design
        return 0.0
    
    def _update_ion_count(self):
        """Update ion count display based on current concentration and volume.
        
        NOTE: The displayed count is a theoretical estimate based on concentration
        and volume. The actual number of ions inserted may be lower due to:
        1. Limited available water molecules for replacement
        2. MIN_SEPARATION constraint (0.3 nm) from ice/guest molecules
        3. MIN_SEPARATION constraint from already-placed ions
        4. Charge neutrality adjustment
        
        The display shows "up to N" to indicate this is a maximum estimate.
        """
        config = self.get_configuration()
        inserter = IonInserter(config)
        
        if self._liquid_volume_nm3 > 0:
            # calculate_ion_pairs needs (concentration_molar, liquid_volume_nm3)
            pair_count = inserter.calculate_ion_pairs(
                config.concentration_molar, 
                self._liquid_volume_nm3
            )
            # Show "up to N" to indicate actual count may be lower
            self.ion_count_display.setText(f"Up to {pair_count} Na⁺/Cl⁻ pairs")
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
    
    def get_current_source(self) -> str:
        """Get the currently selected source for ion insertion.
        
        Returns:
            Source name: "Interface", "Custom Molecule", or "Solute"
        """
        return self._current_source
    
    def get_inserter(self) -> IonInserter:
        """Get IonInserter instance with current configuration.
        
        Returns:
            IonInserter configured with current IonConfig
        """
        return IonInserter(self.get_configuration())
    
    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.
        
        Delegates to the internal IonViewerWidget.
        """
        self.ion_viewer.hide_placeholder()