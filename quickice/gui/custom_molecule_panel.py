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

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import CustomMoleculeConfig
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
    preview_cleared = Signal()  # Clear preview
    
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
        layout = QFormLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Molecule count input
        count_row = QHBoxLayout()
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
        
        layout.addRow("Molecule Count:", count_row)
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
        
        # Add Position button
        add_row = QHBoxLayout()
        self.add_position_button = QPushButton("Add Position")
        add_row.addWidget(self.add_position_button)
        
        self.position_count_label = QLabel("Positions added: 0")
        self.position_count_label.setStyleSheet("color: #666;")
        add_row.addWidget(self.position_count_label)
        add_row.addStretch()
        layout.addLayout(add_row)
        
        return widget
    
    def _setup_connections(self):
        """Setup signal connections."""
        # File upload buttons
        self.gro_button.clicked.connect(self._upload_gro)
        self.itp_button.clicked.connect(self._upload_itp)
        
        # Placement mode switching
        self.placement_mode_combo.currentTextChanged.connect(self._on_placement_mode_changed)
        
        # Add position button
        self.add_position_button.clicked.connect(self._add_position)
        
        # Validation and preview
        self.validate_button.clicked.connect(self._on_validate_clicked)
        self.clear_preview_button.clicked.connect(self._on_clear_preview_clicked)
        
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
        self.placement_mode = mode
        
        # Show/hide controls
        self.random_controls.setVisible(mode == "Random")
        self.custom_controls.setVisible(mode == "Custom")
        
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
            
            self.log_message(f"Added position {len(self.positions_added)}: ({x:.2f}, {y:.2f}, {z:.2f}), "
                            f"rotation ({alpha:.1f}°, {beta:.1f}°, {gamma:.1f}°)")
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Invalid position value: {e}")
    
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
                    f"  Min distance to nearest atom: {result.min_distance:.3f} nm"
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
    
    def set_interface_structure(self, structure):
        """Set the current interface structure for validation.
        
        Called by MainWindow when interface is generated.
        
        Args:
            structure: InterfaceStructure to validate against
        """
        self._interface_structure = structure
        self.log_message("Interface structure loaded for validation")
    
    def get_configuration(self) -> CustomMoleculeConfig:
        """Get current CustomMoleculeConfig from panel values.
        
        Returns:
            CustomMoleculeConfig with current placement settings
        """
        if self.placement_mode == "Random":
            return CustomMoleculeConfig(
                placement_mode="random",
                molecule_count=int(self.molecule_count_spin.value())
            )
        else:  # Custom
            # If no positions added, use current inputs
            if not self.positions_added:
                self._add_position()
            
            positions = [pos_rot[0] for pos_rot in self.positions_added]
            rotations = [pos_rot[1] for pos_rot in self.positions_added]
            
            return CustomMoleculeConfig(
                placement_mode="custom",
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
        
        self.gro_status.setText("No file selected")
        self.gro_status.setStyleSheet("color: gray;")
        
        self.itp_status.setText("No file selected")
        self.itp_status.setStyleSheet("color: gray;")
        
        self.validation_label.setText("Upload both files to validate")
        self.validation_label.setStyleSheet("color: black;")
        
        self.molecule_info_widget.setVisible(False)
        self.generate_button.setEnabled(False)
        
        self.position_count_label.setText("Positions added: 0")
        self.placement_mode_combo.setCurrentText("Random")
        
        self.clear_log()
        self.log_message("Panel reset")
    
    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.
        
        Delegates to the internal CustomMoleculeViewerWidget.
        """
        self.custom_viewer.hide_placeholder()
