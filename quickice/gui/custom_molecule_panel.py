"""Custom molecule upload panel for QuickIce GUI v4.5.

This module provides the CustomMoleculePanel class for custom molecule upload:
- Separate file upload buttons for .gro and .itp files
- Validation status display
- Placement mode selection (Random or Custom)
- Position and rotation inputs for Custom mode
- Generate button for molecule insertion

Signals:
    files_uploaded: Emitted when both files are validated (True) or invalid (False)
    generate_requested: Emitted when Generate button clicked
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import CustomMoleculeConfig
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.gui.view import HelpIcon
from quickice.gui.custom_molecule_viewer import CustomMoleculeViewerWidget

logger = logging.getLogger(__name__)


class CustomMoleculePanel(QWidget):
    """Panel for custom molecule upload and placement configuration.
    
    Provides UI for:
    - Uploading .gro and .itp files via separate file dialogs
    - Viewing validation status
    - Selecting placement mode (Random or Custom)
    - Configuring position and rotation for Custom mode
    - Generating custom molecule structures
    
    Signals:
        files_uploaded: Emitted when both files validated (True) or invalid (False)
        generate_requested: Emitted when Generate button clicked
    """
    
    files_uploaded = Signal(bool)
    generate_requested = Signal()
    
    # NEW: Signals for preview request and clearing
    preview_requested = Signal(tuple, tuple)  # (position, rotation)
    preview_all_requested = Signal(list)  # List of (position, rotation) tuples
    preview_cleared = Signal()  # Clear preview
    clear_previous_results = Signal()  # Clear previous custom molecule insertion results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # File paths and validation state
        self.gro_path: Path | None = None
        self.itp_path: Path | None = None
        self.itp_info = None  # ITPMoleculeInfo from parser
        self.validation_result = None  # ValidationResult from validator
        
        # Placement configuration
        self.placement_mode = "Random"  # or "Custom"
        self.positions_added: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        self._interface_structure = None  # Interface structure for validation
        
        # Track if previous insertion was done (for mode switching)
        self._has_previous_insertion = False
        
        # UI setup
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup UI components with horizontal layout (like SolutePanel).
        
        Layout:
        - Left column (stretch=2): File upload + placement controls
        - Right column (stretch=3): Log panel + 3D viewer (added by MainWindow)
        """
        # Create top-level horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # === LEFT COLUMN: Configuration Controls ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # File upload group
        upload_group = self._create_file_upload_group()
        left_layout.addWidget(upload_group)
        
        # Validation status group
        validation_group = self._create_validation_group()
        left_layout.addWidget(validation_group)
        
        # Placement mode group
        placement_group = self._create_placement_mode_group()
        left_layout.addWidget(placement_group)
        
        # Generate button
        generate_row = QHBoxLayout()
        self.generate_button = QPushButton("Generate Custom Molecules")
        self.generate_button.setEnabled(False)  # Disabled until files validated
        generate_row.addWidget(self.generate_button)
        generate_row.addWidget(HelpIcon(
            "Generate custom molecule structure with configured placement.\n"
            "Requires valid .gro and .itp files."
        ))
        generate_row.addStretch()
        left_layout.addLayout(generate_row)
        
        left_layout.addStretch()
        
        # === RIGHT COLUMN: Log Panel + 3D Viewer ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # Log panel - shows status messages
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout()
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(120)
        self._log_text.setPlaceholderText("Status messages will appear here...")
        log_layout.addWidget(self._log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # 3D viewer widget (stretch=1 to fill remaining space)
        self.custom_viewer = CustomMoleculeViewerWidget()
        right_layout.addWidget(self.custom_viewer, stretch=1)
        
        # Add columns to top-level layout (left gets 2/5, right gets 3/5)
        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=3)
    
    def _create_file_upload_group(self) -> QGroupBox:
        """Create file upload group with separate .gro and .itp buttons."""
        group = QGroupBox("File Upload")
        layout = QVBoxLayout()
        
        # GRO file upload
        gro_row = QHBoxLayout()
        self.gro_button = QPushButton("Upload .gro File")
        self.gro_button.setMaximumWidth(150)
        self.gro_button.setToolTip(
            "Upload GROMACS coordinate file (.gro) for custom molecule.\n"
            "\n"
            "Requirements:\n"
            "• Coordinates in nm (GROMACS units)\n"
            "• Residue name in columns 6-10\n"
            "• Atom names in columns 11-15\n"
            "\n"
            "See Help > Custom Molecules for format details."
        )
        gro_row.addWidget(self.gro_button)
        gro_row.addWidget(HelpIcon(
            "Upload GROMACS coordinate file (.gro).\n"
            "Coordinates in nm, residue name in columns 6-10."
        ))
        
        self.gro_status = QLabel("No file selected")
        self.gro_status.setStyleSheet("color: gray;")
        gro_row.addWidget(self.gro_status)
        gro_row.addStretch()
        layout.addLayout(gro_row)
        
        # ITP file upload
        itp_row = QHBoxLayout()
        self.itp_button = QPushButton("Upload .itp File")
        self.itp_button.setMaximumWidth(150)
        self.itp_button.setToolTip(
            "Upload GROMACS topology file (.itp) for custom molecule.\n"
            "\n"
            "Required sections:\n"
            "• [ atomtypes ] — atom type definitions\n"
            "• [ moleculetype ] — molecule definition\n"
            "• [ atoms ] — atom list\n"
            "\n"
            "See Help > Custom Molecules for format details."
        )
        itp_row.addWidget(self.itp_button)
        itp_row.addWidget(HelpIcon(
            "Upload GROMACS topology file (.itp).\n"
            "Must include [ atomtypes ], [ moleculetype ], [ atoms ] sections."
        ))
        
        self.itp_status = QLabel("No file selected")
        self.itp_status.setStyleSheet("color: gray;")
        itp_row.addWidget(self.itp_status)
        itp_row.addStretch()
        layout.addLayout(itp_row)
        
        group.setLayout(layout)
        return group
    
    def _create_validation_group(self) -> QGroupBox:
        """Create validation status display group."""
        group = QGroupBox("Validation Status")
        layout = QVBoxLayout()
        
        # Molecule info section (hidden initially)
        self.molecule_info_widget = QWidget()
        info_layout = QFormLayout(self.molecule_info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.atom_count_label = QLabel("-- atoms")
        self.atom_count_label.setStyleSheet("color: #666;")
        info_layout.addRow("Atoms:", self.atom_count_label)
        
        self.residue_name_label = QLabel("--")
        self.residue_name_label.setStyleSheet("color: #666;")
        info_layout.addRow("Residue:", self.residue_name_label)
        
        self.molecule_info_widget.setVisible(False)
        layout.addWidget(self.molecule_info_widget)
        
        # Validation status label
        self.validation_label = QLabel("Upload both files to validate")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)
        
        group.setLayout(layout)
        return group
    
    def _create_placement_mode_group(self) -> QGroupBox:
        """Create placement mode selection group."""
        group = QGroupBox("Placement Mode")
        layout = QVBoxLayout()
        
        # Mode dropdown
        mode_row = QHBoxLayout()
        self.placement_mode_combo = QComboBox()
        self.placement_mode_combo.addItems(["Random", "Custom"])
        self.placement_mode_combo.setToolTip(
            "Placement mode for custom molecules.\n"
            "\n"
            "Random: Automatic placement with overlap checking\n"
            "  - Molecules placed randomly in liquid region\n"
            "  - All-atom overlap checking prevents clashes\n"
            "  - Specify number of molecules to insert\n"
            "\n"
            "Custom: User-specified positions and rotations\n"
            "  - Manually define center-of-mass position (nm)\n"
            "  - Manually define rotation angles (degrees)\n"
            "  - No overlap checking (user responsibility)"
        )
        mode_row.addWidget(self.placement_mode_combo)
        mode_row.addWidget(HelpIcon(
            "Select placement mode:\n"
            "• Random: Automatic placement with overlap checking\n"
            "• Custom: User-specified position and rotation"
        ))
        mode_row.addStretch()
        layout.addLayout(mode_row)
        
        # Random mode controls (shown by default)
        self.random_controls = self._create_random_controls()
        layout.addWidget(self.random_controls)
        
        # Custom mode controls (hidden initially)
        self.custom_controls = self._create_custom_controls()
        self.custom_controls.setVisible(False)
        layout.addWidget(self.custom_controls)
        
        # Validation section for Custom mode
        validation_group = QGroupBox("Placement Validation")
        validation_layout = QVBoxLayout()
        
        self.placement_validation_label = QLabel("Click 'Validate & Preview' to check placement")
        self.placement_validation_label.setWordWrap(True)
        self.placement_validation_label.setStyleSheet("color: gray;")
        validation_layout.addWidget(self.placement_validation_label)
        
        # Validate & Preview button
        validate_row = QHBoxLayout()
        self.validate_button = QPushButton("Validate & Preview")
        self.validate_button.setEnabled(False)  # Enabled only when files uploaded and custom mode
        self.validate_button.setToolTip(
            "Validate proposed placement before insertion.\n"
            "Checks:\n"
            "• Position is within liquid region\n"
            "• No overlap with existing atoms\n"
            "\n"
            "After validation, you can preview in 3D viewer."
        )
        validate_row.addWidget(self.validate_button)
        validate_row.addWidget(HelpIcon(
            "Validate placement bounds and overlap.\n"
            "Shows result in status log.\n"
            "Optionally shows 3D preview."
        ))
        validation_layout.addLayout(validate_row)
        
        # Clear preview button
        clear_row = QHBoxLayout()
        self.clear_preview_button = QPushButton("Clear Preview")
        self.clear_preview_button.setEnabled(False)
        self.clear_preview_button.setToolTip("Remove preview molecule from 3D viewer")
        clear_row.addWidget(self.clear_preview_button)
        clear_row.addStretch()
        validation_layout.addLayout(clear_row)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        group.setLayout(layout)
        return group
    
    def _create_random_controls(self) -> QWidget:
        """Create controls for Random placement mode."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Input mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Input Mode:"))
        self.input_mode_combo = QComboBox()
        self.input_mode_combo.addItems(["By Count", "By Concentration"])
        self.input_mode_combo.setToolTip(
            "Select input mode for molecule count:\n"
            "• By Count — Specify molecule count directly\n"
            "• By Concentration — Specify concentration (mol/L)"
        )
        mode_row.addWidget(self.input_mode_combo)
        mode_row.addWidget(HelpIcon(
            "Input mode for custom molecule count:\n"
            "• By Count — Direct molecule count\n"
            "• By Concentration — Specify concentration in mol/L"
        ))
        mode_row.addStretch()
        layout.addLayout(mode_row)
        
        # Count mode widget (shown by default)
        self.count_mode_widget = QWidget()
        count_layout = QVBoxLayout(self.count_mode_widget)
        count_layout.setContentsMargins(0, 0, 0, 0)
        
        # Molecule count input
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Molecule Count:"))
        self.molecule_count_spin = QDoubleSpinBox()
        self.molecule_count_spin.setRange(1, 1000)
        self.molecule_count_spin.setValue(10)
        self.molecule_count_spin.setDecimals(0)
        count_row.addWidget(self.molecule_count_spin)
        
        count_row.addWidget(HelpIcon(
            "Number of molecules to place randomly.\n"
            "Each molecule will have random position and orientation."
        ))
        count_row.addStretch()
        count_layout.addLayout(count_row)
        
        # Calculated concentration label
        conc_label_row = QHBoxLayout()
        conc_label_row.addWidget(QLabel("Calculated:"))
        self.calculated_concentration_label = QLabel("-- mol/L")
        self.calculated_concentration_label.setStyleSheet("color: gray; font-style: italic;")
        conc_label_row.addWidget(self.calculated_concentration_label)
        conc_label_row.addStretch()
        count_layout.addLayout(conc_label_row)
        
        layout.addWidget(self.count_mode_widget)
        
        # Concentration mode widget (hidden initially)
        self.concentration_mode_widget = QWidget()
        conc_layout = QVBoxLayout(self.concentration_mode_widget)
        conc_layout.setContentsMargins(0, 0, 0, 0)
        self.concentration_mode_widget.setVisible(False)
        
        # Concentration input
        conc_input_row = QHBoxLayout()
        conc_input_row.addWidget(QLabel("Concentration:"))
        self.concentration_spin = QDoubleSpinBox()
        self.concentration_spin.setRange(0.0, 2.0)
        self.concentration_spin.setDecimals(3)
        self.concentration_spin.setValue(0.1)
        self.concentration_spin.setSingleStep(0.01)
        self.concentration_spin.setToolTip(
            "Custom molecule concentration in mol/L (M).\n"
            "\n"
            "Formula: N = C_M × V × 10⁻²⁴ × N_A\n"
            "where N_A = Avogadro's number (6.022×10²³)"
        )
        conc_input_row.addWidget(self.concentration_spin)
        
        unit_label = QLabel("mol/L")
        conc_input_row.addWidget(unit_label)
        
        conc_input_row.addWidget(HelpIcon(
            "Custom molecule concentration in mol/L.\n"
            "Typical values depend on your system."
        ))
        conc_input_row.addStretch()
        conc_layout.addLayout(conc_input_row)
        
        # Calculated count label
        count_label_row = QHBoxLayout()
        count_label_row.addWidget(QLabel("Calculated:"))
        self.calculated_count_label = QLabel("-- molecules")
        self.calculated_count_label.setStyleSheet("color: gray; font-style: italic;")
        count_label_row.addWidget(self.calculated_count_label)
        count_label_row.addStretch()
        conc_layout.addLayout(count_label_row)
        
        layout.addWidget(self.concentration_mode_widget)
        
        # Volume display
        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Liquid Volume:"))
        self.liquid_volume_label = QLabel("-- nm³")
        self.liquid_volume_label.setStyleSheet("color: gray;")
        volume_row.addWidget(self.liquid_volume_label)
        volume_row.addWidget(HelpIcon(
            "Volume of liquid water region.\n"
            "Used to estimate feasible molecule counts."
        ))
        volume_row.addStretch()
        layout.addLayout(volume_row)
        
        # Estimated molecule count range
        estimate_row = QHBoxLayout()
        estimate_row.addWidget(QLabel("Recommended:"))
        self.molecule_estimate_label = QLabel("-- molecules")
        self.molecule_estimate_label.setStyleSheet("color: gray; font-style: italic;")
        estimate_row.addWidget(self.molecule_estimate_label)
        estimate_row.addWidget(HelpIcon(
            "Approximate maximum molecules based on liquid volume and minimum separation.\n"
            "Actual capacity depends on molecule shape and packing efficiency."
        ))
        estimate_row.addStretch()
        layout.addLayout(estimate_row)
        
        return widget
    
    def _create_custom_controls(self) -> QWidget:
        """Create controls for Custom placement mode."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Position inputs (X, Y, Z)
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position (nm):"))
        
        self.pos_x_edit = QLineEdit("0.0")
        self.pos_x_edit.setMaximumWidth(80)
        self.pos_x_edit.setPlaceholderText("X")
        pos_layout.addWidget(self.pos_x_edit)
        
        self.pos_y_edit = QLineEdit("0.0")
        self.pos_y_edit.setMaximumWidth(80)
        self.pos_y_edit.setPlaceholderText("Y")
        pos_layout.addWidget(self.pos_y_edit)
        
        self.pos_z_edit = QLineEdit("0.0")
        self.pos_z_edit.setMaximumWidth(80)
        self.pos_z_edit.setPlaceholderText("Z")
        pos_layout.addWidget(self.pos_z_edit)
        
        pos_layout.addWidget(HelpIcon(
            "Center-of-mass position in nanometers.\n"
            "Constrained to liquid region bounds."
        ))
        pos_layout.addStretch()
        layout.addLayout(pos_layout)
        
        # Rotation inputs (α, β, γ)
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Rotation (°):"))
        
        self.rot_alpha_spin = QDoubleSpinBox()
        self.rot_alpha_spin.setRange(0, 360)
        self.rot_alpha_spin.setValue(0)
        self.rot_alpha_spin.setDecimals(1)
        self.rot_alpha_spin.setPrefix("α: ")
        self.rot_alpha_spin.setMaximumWidth(100)
        rot_layout.addWidget(self.rot_alpha_spin)
        
        self.rot_beta_spin = QDoubleSpinBox()
        self.rot_beta_spin.setRange(0, 360)
        self.rot_beta_spin.setValue(0)
        self.rot_beta_spin.setDecimals(1)
        self.rot_beta_spin.setPrefix("β: ")
        self.rot_beta_spin.setMaximumWidth(100)
        rot_layout.addWidget(self.rot_beta_spin)
        
        self.rot_gamma_spin = QDoubleSpinBox()
        self.rot_gamma_spin.setRange(0, 360)
        self.rot_gamma_spin.setValue(0)
        self.rot_gamma_spin.setDecimals(1)
        self.rot_gamma_spin.setPrefix("γ: ")
        self.rot_gamma_spin.setMaximumWidth(100)
        rot_layout.addWidget(self.rot_gamma_spin)
        
        rot_layout.addWidget(HelpIcon(
            "Euler angles in degrees (ZXZ convention).\n"
            "α: First rotation around Z-axis\n"
            "β: Second rotation around X-axis\n"
            "γ: Third rotation around Z-axis"
        ))
        rot_layout.addStretch()
        layout.addLayout(rot_layout)
        
        # Liquid region bounds display
        bounds_row = QHBoxLayout()
        bounds_row.addWidget(QLabel("Liquid Region:"))
        self.liquid_bounds_label = QLabel("No interface structure")
        self.liquid_bounds_label.setStyleSheet("color: gray;")
        bounds_row.addWidget(self.liquid_bounds_label)
        bounds_row.addWidget(HelpIcon(
            "Valid XYZ range for molecule placement.\n"
            "Constrained to liquid water region in interface structure."
        ))
        bounds_row.addStretch()
        layout.addLayout(bounds_row)
        
        # Add Position button
        add_row = QHBoxLayout()
        self.add_position_button = QPushButton("Add Position")
        add_row.addWidget(self.add_position_button)
        
        self.position_count_label = QLabel("Positions added: 0")
        self.position_count_label.setStyleSheet("color: #666;")
        add_row.addWidget(self.position_count_label)
        add_row.addStretch()
        layout.addLayout(add_row)
        
        # Position list table
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels([
            "X (nm)", "Y (nm)", "Z (nm)", "α (°)", "β (°)", "γ (°)", "Preview"
        ])
        self.position_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.position_table.setMaximumHeight(150)
        self.position_table.setAlternatingRowColors(True)
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.position_table.cellClicked.connect(self._on_position_table_clicked)
        layout.addWidget(self.position_table)
        
        # Preview All button
        preview_all_row = QHBoxLayout()
        self.preview_all_button = QPushButton("Preview All Positions")
        self.preview_all_button.setToolTip(
            "Show all added molecule positions in 3D viewer.\n"
            "Useful to verify the complete configuration before generating."
        )
        self.preview_all_button.setEnabled(False)  # Enabled when positions are added
        preview_all_row.addWidget(self.preview_all_button)
        preview_all_row.addStretch()
        layout.addLayout(preview_all_row)
        
        return widget
    
    def _setup_connections(self):
        """Setup signal connections."""
        # File upload buttons
        self.gro_button.clicked.connect(self._upload_gro)
        self.itp_button.clicked.connect(self._upload_itp)
        
        # Placement mode switching
        self.placement_mode_combo.currentTextChanged.connect(self._on_placement_mode_changed)
        
        # Input mode switching (concentration/count toggle)
        self.input_mode_combo.currentIndexChanged.connect(self._on_input_mode_changed)
        self.molecule_count_spin.valueChanged.connect(self._update_concentration_from_count)
        self.concentration_spin.valueChanged.connect(self._update_count_from_concentration)
        
        # Add position button
        self.add_position_button.clicked.connect(self._add_position)
        
        # Validation and preview
        self.validate_button.clicked.connect(self._on_validate_clicked)
        self.clear_preview_button.clicked.connect(self._on_clear_preview_clicked)
        
        # Preview all button
        self.preview_all_button.clicked.connect(self._on_preview_all_clicked)
        
        # Generate button
        self.generate_button.clicked.connect(lambda: self.generate_requested.emit())
    
    def _upload_gro(self):
        """Handle GRO file selection."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select GRO File",
            "",
            "GRO Files (*.gro);;All Files (*)"
        )
        
        if filepath:
            self.gro_path = Path(filepath)
            self.gro_status.setText(self.gro_path.name)
            self.gro_status.setStyleSheet("color: black;")
            self.log_message(f"Selected GRO file: {self.gro_path.name}")
            self._validate_files()
    
    def _upload_itp(self):
        """Handle ITP file selection."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select ITP File",
            "",
            "ITP Files (*.itp);;All Files (*)"
        )
        
        if filepath:
            self.itp_path = Path(filepath)
            
            try:
                from quickice.structure_generation.itp_parser import parse_itp_file
                self.itp_info = parse_itp_file(self.itp_path)
                
                self.itp_status.setText(f"{self.itp_path.name} ({self.itp_info.atom_count} atoms)")
                self.itp_status.setStyleSheet("color: black;")
                self.log_message(f"Selected ITP file: {self.itp_path.name} ({self.itp_info.atom_count} atoms)")
                
                self._validate_files()
                
            except Exception as e:
                self.itp_status.setText(f"Error: {e}")
                self.itp_status.setStyleSheet("color: red;")
                self.log_message(f"Failed to parse ITP file: {e}")
                self.itp_info = None
    
    def _validate_files(self):
        """Validate both files when uploaded."""
        if not self.gro_path or not self.itp_info:
            return
        
        try:
            from quickice.structure_generation.molecule_validator import validate_custom_molecule
            
            self.validation_result = validate_custom_molecule(
                self.gro_path, self.itp_info
            )
            
            if self.validation_result.is_valid:
                # Show molecule info
                self.atom_count_label.setText(f"{self.validation_result.gro_atom_count} atoms")
                self.residue_name_label.setText(self.validation_result.itp_residue_name or self.validation_result.gro_residue_name)
                self.molecule_info_widget.setVisible(True)
                
                # Check for residue name mismatch
                if self.validation_result.residue_name_mismatch:
                    self._show_residue_mismatch_dialog()
                else:
                    self.validation_label.setText("✓ Files validated successfully")
                    self.validation_label.setStyleSheet("color: green;")
                    self.generate_button.setEnabled(True)
                    # Enable validate button for Custom mode
                    self.validate_button.setEnabled(
                        self.validation_result is not None 
                        and self.placement_mode == "Custom"
                    )
                    self.files_uploaded.emit(True)
                    self.log_message("Files validated successfully")
                    
            else:
                self.validation_label.setText(
                    "✗ Validation failed:\n" + "\n".join(self.validation_result.errors)
                )
                self.validation_label.setStyleSheet("color: red;")
                self.generate_button.setEnabled(False)
                self.validate_button.setEnabled(False)
                self.files_uploaded.emit(False)
                self.log_message("Validation failed: " + "; ".join(self.validation_result.errors))
                
        except Exception as e:
            self.validation_label.setText(f"✗ Validation error: {e}")
            self.validation_label.setStyleSheet("color: red;")
            self.generate_button.setEnabled(False)
            self.validate_button.setEnabled(False)
            self.files_uploaded.emit(False)
            self.log_message(f"Validation error: {e}")
    
    def _show_residue_mismatch_dialog(self):
        """Show dialog asking if ITP residue name should override."""
        reply = QMessageBox.question(
            self,
            "Residue Name Mismatch",
            f"GRO file uses residue name '{self.validation_result.gro_residue_name}'\n"
            f"ITP file uses residue name '{self.validation_result.itp_residue_name}'\n\n"
            f"Use ITP residue name? (Select 'No' to re-upload files)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Accept ITP residue name, proceed
            self.validation_label.setText(
                f"✓ Files validated (using ITP residue: {self.validation_result.itp_residue_name})"
            )
            self.validation_label.setStyleSheet("color: green;")
            self.residue_name_label.setText(self.validation_result.itp_residue_name)
            self.generate_button.setEnabled(True)
            self.files_uploaded.emit(True)
            self.log_message(f"Accepted ITP residue name: {self.validation_result.itp_residue_name}")
        else:
            # Reject, require re-upload
            self.validation_label.setText("Residue name mismatch. Please upload matching files.")
            self.validation_label.setStyleSheet("color: orange;")
            self.generate_button.setEnabled(False)
            self.files_uploaded.emit(False)
            self.log_message("User rejected residue name mismatch")
    
    def _on_placement_mode_changed(self, mode: str):
        """Handle placement mode switching.
        
        Args:
            mode: "Random" or "Custom"
        """
        # Check if there are previous custom molecule insertions
        if self._has_previous_insertion:
            # Ask user what to do
            reply = QMessageBox.question(
                self,
                "Previous Custom Molecules Found",
                "You have previously inserted custom molecules.\n\n"
                "Do you want to start fresh (clear previous molecules) or add to existing?\n\n"
                "• 'Yes' = Start fresh (previous molecules will be cleared)\n"
                "• 'No' = Add to existing (previous molecules will remain)",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                # Revert to previous mode
                self.placement_mode_combo.blockSignals(True)
                self.placement_mode_combo.setCurrentText("Random" if mode == "Custom" else "Custom")
                self.placement_mode_combo.blockSignals(False)
                return
            
            if reply == QMessageBox.Yes:
                # Clear previous results
                self.clear_previous_results.emit()
                self._has_previous_insertion = False
                self.positions_added.clear()
                self.position_count_label.setText("Positions added: 0")
                self.log_message("Cleared previous custom molecules - starting fresh")
        
        self.placement_mode = mode
        
        # Show/hide controls
        self.random_controls.setVisible(mode == "Random")
        self.custom_controls.setVisible(mode == "Custom")
        
        # Update displays based on active mode
        if mode == "Custom":
            self._update_liquid_bounds()
        else:  # Random mode
            self._update_volume_preview()
        
        # Enable/disable validate button based on mode
        self.validate_button.setEnabled(
            self.validation_result is not None 
            and mode == "Custom"
        )
        
        self.log_message(f"Switched to {mode} placement mode")
    
    def _add_position(self):
        """Add current position and rotation to the list."""
        try:
            # Parse position
            x = float(self.pos_x_edit.text())
            y = float(self.pos_y_edit.text())
            z = float(self.pos_z_edit.text())
            position = (x, y, z)
            
            # Get rotation
            alpha = self.rot_alpha_spin.value()
            beta = self.rot_beta_spin.value()
            gamma = self.rot_gamma_spin.value()
            rotation = (alpha, beta, gamma)
            
            # Add to list
            self.positions_added.append((position, rotation))
            
            # Update count
            self.position_count_label.setText(f"Positions added: {len(self.positions_added)}")
            
            # Update table
            self._update_position_table()
            
            self.log_message(f"Added position {len(self.positions_added)}: ({x:.2f}, {y:.2f}, {z:.2f}), "
                            f"rotation ({alpha:.1f}°, {beta:.1f}°, {gamma:.1f}°)")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Invalid position value: {e}")
    
    def _update_position_table(self):
        """Update the position table with current positions_added list."""
        self.position_table.setRowCount(len(self.positions_added))
        
        for i, (pos, rot) in enumerate(self.positions_added):
            # Position columns
            self.position_table.setItem(i, 0, QTableWidgetItem(f"{pos[0]:.2f}"))
            self.position_table.setItem(i, 1, QTableWidgetItem(f"{pos[1]:.2f}"))
            self.position_table.setItem(i, 2, QTableWidgetItem(f"{pos[2]:.2f}"))
            
            # Rotation columns
            self.position_table.setItem(i, 3, QTableWidgetItem(f"{rot[0]:.1f}"))
            self.position_table.setItem(i, 4, QTableWidgetItem(f"{rot[1]:.1f}"))
            self.position_table.setItem(i, 5, QTableWidgetItem(f"{rot[2]:.1f}"))
            
            # Preview button column
            preview_item = QTableWidgetItem("Click to preview")
            preview_item.setForeground(Qt.blue)
            self.position_table.setItem(i, 6, preview_item)
        
        # Enable/disable Preview All button based on whether positions exist
        self.preview_all_button.setEnabled(len(self.positions_added) > 0)
    
    def _on_position_table_clicked(self, row: int, column: int):
        """Handle click on position table row.
        
        Args:
            row: Row index that was clicked
            column: Column index that was clicked
        """
        if row < 0 or row >= len(self.positions_added):
            return
        
        position, rotation = self.positions_added[row]
        
        # If preview column clicked, show preview for this position
        if column == 6:  # Preview column
            self.log_message(f"Previewing position {row + 1}")
            self.preview_requested.emit(position, rotation)
            self.clear_preview_button.setEnabled(True)
        else:
            # Load position/rotation into input fields for editing
            self.pos_x_edit.setText(f"{position[0]:.2f}")
            self.pos_y_edit.setText(f"{position[1]:.2f}")
            self.pos_z_edit.setText(f"{position[2]:.2f}")
            self.rot_alpha_spin.setValue(rotation[0])
            self.rot_beta_spin.setValue(rotation[1])
            self.rot_gamma_spin.setValue(rotation[2])
            self.log_message(f"Loaded position {row + 1} into input fields")
    
    def _on_preview_all_clicked(self):
        """Handle Preview All button click.
        
        Shows all positions in the 3D viewer for verification before generation.
        """
        if not self.positions_added:
            QMessageBox.information(
                self, "No Positions",
                "Add at least one position before previewing all."
            )
            return
        
        # Check files are loaded
        if not self.gro_path or not self.itp_path:
            QMessageBox.warning(
                self, "No Files",
                "Please upload .gro and .itp files first."
            )
            return
        
        # Check interface structure exists
        if self._interface_structure is None:
            QMessageBox.warning(
                self, "No Structure",
                "Please generate an interface structure first."
            )
            return
        
        # Emit signal with all positions
        self.preview_all_requested.emit(self.positions_added)
        self.clear_preview_button.setEnabled(True)
        self.log_message(f"Previewing all {len(self.positions_added)} positions")
    
    def _on_validate_clicked(self):
        """Handle Validate & Preview button click.
        
        Validates current position/rotation settings and shows result.
        Offers to show 3D preview if validation succeeds.
        """
        # Check files uploaded
        if not self.gro_path or not self.itp_path:
            QMessageBox.warning(
                self, "Validation Error",
                "Please upload .gro and .itp files first"
            )
            return
        
        # Get current position and rotation
        try:
            position = (
                float(self.pos_x_edit.text()),
                float(self.pos_y_edit.text()),
                float(self.pos_z_edit.text())
            )
            rotation = (
                self.rot_alpha_spin.value(),
                self.rot_beta_spin.value(),
                self.rot_gamma_spin.value()
            )
        except ValueError as e:
            QMessageBox.warning(
                self, "Invalid Input",
                f"Invalid position value: {e}"
            )
            return
        
        # Get current interface structure (stored by MainWindow)
        if self._interface_structure is None:
            QMessageBox.warning(
                self, "No Structure",
                "Please generate an interface structure first"
            )
            return
        
        # Create validation inserter
        from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
        from quickice.structure_generation.types import CustomMoleculeConfig
        
        config = CustomMoleculeConfig(
            placement_mode="custom",
            gro_path=self.gro_path,
            itp_path=self.itp_path,
            positions=[position],
            rotations=[rotation],
            min_separation=0.25  # Default
        )
        
        try:
            inserter = CustomMoleculeInserter(config)
            result = inserter.validate_single_placement(
                self._interface_structure, position, rotation
            )
            
            # Show result in validation label
            if result.is_valid:
                self.placement_validation_label.setText(
                    f"✓ Placement valid\n"
                    f"  Position: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f}) nm\n"
                    f"  Min distance to nearest atom in ice/hydrate layer: {result.min_distance:.3f} nm"
                )
                self.placement_validation_label.setStyleSheet("color: green; font-weight: bold;")
                self.log_message(f"Placement validated: min distance {result.min_distance:.3f} nm")
                
                # Offer to show preview
                reply = QMessageBox.question(
                    self, "Show Preview",
                    "Placement is valid. Show preview in 3D viewer?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.preview_requested.emit(position, rotation)
                    self.clear_preview_button.setEnabled(True)
                
                # Ensure validate button remains enabled for re-validation
                self.validate_button.setEnabled(True)
            else:
                error_msg = result.error_message or "Validation failed"
                self.placement_validation_label.setText(f"✗ {error_msg}")
                self.placement_validation_label.setStyleSheet("color: red; font-weight: bold;")
                self.log_message(f"Validation failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            QMessageBox.critical(
                self, "Validation Error",
                f"Failed to validate placement: {e}"
            )
    
    def _on_clear_preview_clicked(self):
        """Handle Clear Preview button click."""
        # Emit signal to indicate clear
        self.preview_cleared.emit()
        self.clear_preview_button.setEnabled(False)
        self.log_message("Preview cleared")
    
    def _update_liquid_bounds(self):
        """Update liquid region bounds display.
        
        Calculates and displays the XYZ bounds of the liquid water region
        from the current interface structure.
        """
        if self._interface_structure is None:
            self.liquid_bounds_label.setText("No interface structure")
            self.liquid_bounds_label.setStyleSheet("color: gray;")
            return
        
        # Get liquid region info (same logic as CustomMoleculeInserter)
        ice_count = getattr(self._interface_structure, 'ice_atom_count', 0)
        water_count = getattr(self._interface_structure, 'water_atom_count', 0)
        
        if water_count == 0:
            self.liquid_bounds_label.setText("No liquid region")
            self.liquid_bounds_label.setStyleSheet("color: orange;")
            return
        
        # Calculate bounds from liquid positions
        liquid_pos = self._interface_structure.positions[ice_count:ice_count + water_count]
        min_coords = liquid_pos.min(axis=0)
        max_coords = liquid_pos.max(axis=0)
        
        bounds_text = f"X=({min_coords[0]:.2f}, {max_coords[0]:.2f}), " \
                      f"Y=({min_coords[1]:.2f}, {max_coords[1]:.2f}), " \
                      f"Z=({min_coords[2]:.2f}, {max_coords[2]:.2f})"
        
        self.liquid_bounds_label.setText(bounds_text)
        self.liquid_bounds_label.setStyleSheet("color: #666;")
    
    def _update_volume_preview(self):
        """Update volume and molecule count preview for Random mode.
        
        Calculates liquid volume and estimates maximum molecules based on
        packing fraction and minimum separation.
        """
        if self._interface_structure is None:
            self.liquid_volume_label.setText("-- nm³")
            self.molecule_estimate_label.setText("-- molecules")
            return
        
        # Get liquid region info
        ice_count = getattr(self._interface_structure, 'ice_atom_count', 0)
        water_count = getattr(self._interface_structure, 'water_atom_count', 0)
        
        if water_count == 0:
            self.liquid_volume_label.setText("0 nm³")
            self.molecule_estimate_label.setText("0 molecules")
            return
        
        # Calculate liquid volume
        liquid_pos = self._interface_structure.positions[ice_count:ice_count + water_count]
        min_coords = liquid_pos.min(axis=0)
        max_coords = liquid_pos.max(axis=0)
        
        volume = np.prod(max_coords - min_coords)
        self.liquid_volume_label.setText(f"{volume:.2f} nm³")
        
        # Estimate max molecules (rough approximation)
        # Assumes min_separation is center-to-center distance
        min_separation = 0.25  # Default value from CustomMoleculeConfig
        molecule_radius = min_separation / 2
        molecule_volume = (4/3) * np.pi * molecule_radius**3
        packing_fraction = 0.64  # Random close packing
        
        max_molecules = int(volume * packing_fraction / molecule_volume)
        self.molecule_estimate_label.setText(f"~{max_molecules} molecules (max)")
        
        # Update concentration/count preview based on input mode
        if self.input_mode_combo.currentText() == "By Count":
            self._update_concentration_from_count()
        else:
            self._update_count_from_concentration()
    
    def _on_input_mode_changed(self, index: int):
        """Handle input mode switching.
        
        Args:
            index: Combo box index (0 = By Count, 1 = By Concentration)
        """
        # Show appropriate widget
        if index == 0:  # By Count
            self.count_mode_widget.setVisible(True)
            self.concentration_mode_widget.setVisible(False)
        else:  # By Concentration
            self.count_mode_widget.setVisible(False)
            self.concentration_mode_widget.setVisible(True)
        
        # Refresh calculated values
        self._update_volume_preview()
    
    def _update_concentration_from_count(self):
        """Update concentration label when molecule count changes."""
        if self._interface_structure is None:
            self.calculated_concentration_label.setText("-- mol/L")
            return
        
        # Get liquid volume
        water_count = getattr(self._interface_structure, 'water_atom_count', 0)
        if water_count == 0:
            self.calculated_concentration_label.setText("-- mol/L")
            return
        
        water_nmolecules = water_count // 4
        liquid_volume_nm3 = water_nmolecules * 0.0299
        
        # Calculate concentration from count
        molecule_count = int(self.molecule_count_spin.value())
        concentration = CustomMoleculeInserter.calculate_concentration(
            molecule_count, liquid_volume_nm3
        )
        
        self.calculated_concentration_label.setText(f"{concentration:.4f} mol/L")
    
    def _update_count_from_concentration(self):
        """Update molecule count label when concentration changes."""
        if self._interface_structure is None:
            self.calculated_count_label.setText("-- molecules")
            return
        
        # Get liquid volume
        water_count = getattr(self._interface_structure, 'water_atom_count', 0)
        if water_count == 0:
            self.calculated_count_label.setText("-- molecules")
            return
        
        water_nmolecules = water_count // 4
        liquid_volume_nm3 = water_nmolecules * 0.0299
        
        # Calculate count from concentration
        concentration = self.concentration_spin.value()
        count = CustomMoleculeInserter.calculate_molecule_count(
            concentration, liquid_volume_nm3
        )
        
        self.calculated_count_label.setText(f"{count} molecules")
        
        # Also update molecule_estimate_label for consistency
        self.molecule_estimate_label.setText(f"{count} molecules")
    
    def set_interface_structure(self, structure):
        """Set the current interface structure for validation.
        
        Called by MainWindow when interface is generated.
        
        Args:
            structure: InterfaceStructure to validate against
        """
        self._interface_structure = structure
        
        # Update all dependent displays
        self._update_liquid_bounds()
        self._update_volume_preview()
        
        self.log_message("Interface structure loaded for validation")
        if structure is not None:
            ice_count = getattr(structure, 'ice_atom_count', 0)
            water_count = getattr(structure, 'water_atom_count', 0)
            self.log_message(f"Liquid region: {water_count} water atoms")
    
    def get_configuration(self) -> CustomMoleculeConfig:
        """Get current CustomMoleculeConfig from panel values.
        
        Returns:
            CustomMoleculeConfig with current placement settings
        """
        if self.placement_mode == "Random":
            # Check input mode
            mode_text = self.input_mode_combo.currentText()
            
            if mode_text == "By Count":
                # Use molecule count directly
                molecule_count = int(self.molecule_count_spin.value())
            else:  # By Concentration
                # Calculate molecule count from concentration
                concentration = self.concentration_spin.value()
                
                # Get liquid volume
                water_count = getattr(self._interface_structure, 'water_atom_count', 0) if self._interface_structure else 0
                water_nmolecules = water_count // 4
                liquid_volume_nm3 = water_nmolecules * 0.0299
                
                molecule_count = CustomMoleculeInserter.calculate_molecule_count(
                    concentration, liquid_volume_nm3
                )
            
            return CustomMoleculeConfig(
                placement_mode="random",
                gro_path=self.gro_path,
                itp_path=self.itp_path,
                molecule_count=molecule_count
            )
        else:  # Custom
            # If no positions added, use current inputs
            if not self.positions_added:
                self._add_position()
            
            positions = [pos_rot[0] for pos_rot in self.positions_added]
            rotations = [pos_rot[1] for pos_rot in self.positions_added]
            
            return CustomMoleculeConfig(
                placement_mode="custom",
                gro_path=self.gro_path,
                itp_path=self.itp_path,
                positions=positions,
                rotations=rotations
            )
    
    def get_gro_path(self) -> Path | None:
        """Get current GRO file path.

        Returns:
            Path to .gro file or None if not uploaded
        """
        return self.gro_path
    
    def get_itp_path(self) -> Path | None:
        """Get current ITP file path.

        Returns:
            Path to .itp file or None if not uploaded
        """
        return self.itp_path
    
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
    
    def reset(self):
        """Reset the panel to initial state."""
        self.gro_path = None
        self.itp_path = None
        self.itp_info = None
        self.validation_result = None
        self.positions_added.clear()
        self._has_previous_insertion = False
        
        self.gro_status.setText("No file selected")
        self.gro_status.setStyleSheet("color: gray;")
        
        self.itp_status.setText("No file selected")
        self.itp_status.setStyleSheet("color: gray;")
        
        self.validation_label.setText("Upload both files to validate")
        self.validation_label.setStyleSheet("color: black;")
        
        self.molecule_info_widget.setVisible(False)
        self.generate_button.setEnabled(False)
        
        self.position_count_label.setText("Positions added: 0")
        self.position_table.setRowCount(0)
        self.preview_all_button.setEnabled(False)
        self.placement_mode_combo.setCurrentText("Random")
        
        self.clear_log()
        self.log_message("Panel reset")
    
    def mark_insertion_complete(self):
        """Mark that a custom molecule insertion has been completed.
        
        Called by MainWindow after successful insertion to track state
        for mode switching behavior.
        """
        self._has_previous_insertion = True
    
    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.
        
        Delegates to the internal CustomMoleculeViewerWidget.
        """
        self.custom_viewer.hide_placeholder()
