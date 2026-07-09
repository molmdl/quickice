"""Hydrate configuration panel for QuickIce GUI v4.7.

This module provides the HydratePanel class for hydrate configuration:
- Lattice type selection (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17)
- Per-cage-type guest + occupancy rows (one per cage_type_map key; rebuilt on
  lattice change) — Phase 42 mixed cage occupancy
- Supercell dimensions
- Lattice info display (handles water-only and filled-ice structures)
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox,
    QFormLayout, QTextEdit, QPushButton, QStackedWidget,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from quickice.structure_generation.types import (
    HydrateConfig, HydrateLatticeInfo, CageGuestAssignment,
    HYDRATE_LATTICES, GUEST_MOLECULES
)
from quickice.gui.hydrate_viewer import HydrateViewerWidget
from quickice.gui.view import HelpIcon


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
        
        # Custom guest upload group (Phase 44-02). ONE shared slot; on valid
        # upload the custom guest becomes a "Custom: {residue}" option in
        # every per-cage combo (added by _rebuild_cage_rows).
        custom_guest_group = self._create_custom_guest_group()
        left_layout.addWidget(custom_guest_group)
        
        # Cage guest assignment group (per-cage-type guest + occupancy rows
        # rebuilt when the lattice changes; one row per cage_type_map key)
        cage_group = self._create_cage_assignment_group()
        left_layout.addWidget(cage_group)
        
        # Supercell group
        supercell_group = self._create_supercell_group()
        left_layout.addWidget(supercell_group)
        
        # Depolarization mode (Phase 43)
        depol_group = self._create_depol_group()
        left_layout.addWidget(depol_group)
        
        # Lattice info display
        info_group = self._create_info_group()
        left_layout.addWidget(info_group)
        
        # Generate button
        gen_row = QHBoxLayout()
        self.generate_button = QPushButton("Generate Hydrate")
        self.generate_button.clicked.connect(lambda: self.generate_requested.emit())
        gen_row.addWidget(self.generate_button)
        gen_row.addWidget(HelpIcon(
            "Generate hydrate structure with current configuration.\n"
            "Uses GenIce2 for structure generation.\n"
            "Structure appears in 3D viewer on the right."
        ))
        gen_row.addStretch()
        left_layout.addLayout(gen_row)

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
        
        # H-bonds toggle button (matching Tab 1's btn_hbonds)
        self.btn_hbonds = QPushButton("H-bonds")
        self.btn_hbonds.setCheckable(True)
        self.btn_hbonds.setChecked(True)
        self.btn_hbonds.clicked.connect(self._on_hbonds_toggled)
        toolbar_layout.addWidget(self.btn_hbonds)
        
        # Unit cell toggle button (matching Tab 1's btn_unit_cell)
        self.btn_unit_cell = QPushButton("Unit cell")
        self.btn_unit_cell.setCheckable(True)
        self.btn_unit_cell.setChecked(False)
        self.btn_unit_cell.clicked.connect(self._on_unit_cell_toggled)
        toolbar_layout.addWidget(self.btn_unit_cell)
        
        # Representation mode toggle button (matching Tab 1's btn_representation)
        self.btn_representation = QPushButton("Ball-and-stick")
        self.btn_representation.setCheckable(False)  # Cycles through modes
        self.btn_representation.clicked.connect(self._on_representation_toggled)
        toolbar_layout.addWidget(self.btn_representation)
        
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
        
        # Set initial UI state: build per-cage rows for the default lattice,
        # then refresh the force-field label + info display (they read the
        # first cage row's selected guest).
        self._update_guest_ui_for_lattice()
        self._update_ff_label()
        self._update_info_display()
    
    def _create_lattice_group(self) -> QGroupBox:
        """Create lattice type selection group."""
        group = QGroupBox("Hydrate Lattice")
        layout = QFormLayout()
        
        lattice_row = QHBoxLayout()
        self.lattice_combo = QComboBox()
        for lattice_id, lattice_info in HYDRATE_LATTICES.items():
            self.lattice_combo.addItem(
                f"{lattice_id} - {lattice_info['description']}",
                lattice_id
            )
        lattice_row.addWidget(self.lattice_combo)
        lattice_row.addWidget(HelpIcon(
            "Hydrate lattice structure type.\n"
            "• sI — Structure I (CH₄, CO₂ hydrates)\n"
            "• sII — Structure II (THF hydrates)\n"
            "• sH — Structure H (requires helper molecule)\n"
            "• c0te — Filled ice C0 (triclinic)\n"
            "• c1te — Filled ice C1 (triclinic)\n"
            "• c2te — Filled ice C2 (orthorhombic)\n"
            "• ice1hte — Filled ice Ih (orthorhombic)\n"
            "• sTprime — Filled ice sT′ (water-only)\n"
            "• 16 — Ice XVI (empty sII framework)\n"
            "• 17 — Ice XVII (water-only)"
        ))
        lattice_row.addStretch()
        
        layout.addRow("Lattice type:", lattice_row)
        group.setLayout(layout)
        return group

    def _create_depol_group(self) -> QGroupBox:
        """Create the depolarization mode selection group (Phase 43)."""
        group = QGroupBox("Depolarization")
        layout = QFormLayout()

        row = QHBoxLayout()
        self.depol_combo = QComboBox()
        self.depol_combo.addItem("Strict (ice rules, zero net dipole)", "strict")
        self.depol_combo.addItem("Optimal (relaxed)", "optimal")
        # currentIndex 0 = "strict" = default (preserves pre-Phase-43 behavior)
        row.addWidget(self.depol_combo)
        row.addWidget(HelpIcon(
            "Depolarization mode for hydrogen-bond orientation.\n"
            "• Strict — enforce ice rules / zero net dipole (default, safe).\n"
            "• Optimal — relaxed depolarization.\n"
            "Affects H-bond orientation only; does not change atom count."
        ))
        row.addStretch()

        layout.addRow("Depol mode:", row)
        group.setLayout(layout)
        return group

    def _create_custom_guest_group(self) -> QGroupBox:
        """Create the custom guest upload group (Phase 44-02).

        Adds a single shared custom-guest upload slot: two ``QPushButton``s
        opening ``QFileDialog`` for ``.gro`` / ``.itp`` files, each with a
        status ``QLabel`` (gray "No file selected" -> black filename on
        selection), and a word-wrapped validation ``QLabel`` (gray prompt ->
        green ``✓`` on success, red ``✗`` + specific engine error messages on
        failure). On a valid upload the custom guest becomes a
        "Custom: {residue}" option in every per-cage combo (added by
        ``_rebuild_cage_rows``).

        All custom-guest state (``_custom_guest``, ``_cg_gro_path``,
        ``_cg_itp_path``) is initialized here so it stays co-located with the
        panel it belongs to (not in ``__init__``).
        """
        group = QGroupBox("Custom Guest (optional)")
        layout = QFormLayout()

        # .gro row
        gro_row = QHBoxLayout()
        self.cg_gro_button = QPushButton("Upload .gro File")
        self.cg_gro_button.setMaximumWidth(150)
        self.cg_gro_button.clicked.connect(self._upload_custom_gro)
        self.cg_gro_status = QLabel("No file selected")
        self.cg_gro_status.setStyleSheet("color: gray;")
        gro_row.addWidget(self.cg_gro_button)
        gro_row.addWidget(self.cg_gro_status)
        gro_row.addStretch()
        layout.addRow("GRO:", gro_row)

        # .itp row
        itp_row = QHBoxLayout()
        self.cg_itp_button = QPushButton("Upload .itp File")
        self.cg_itp_button.setMaximumWidth(150)
        self.cg_itp_button.clicked.connect(self._upload_custom_itp)
        self.cg_itp_status = QLabel("No file selected")
        self.cg_itp_status.setStyleSheet("color: gray;")
        itp_row.addWidget(self.cg_itp_button)
        itp_row.addWidget(self.cg_itp_status)
        itp_row.addStretch()
        layout.addRow("ITP:", itp_row)

        # Validation feedback (word-wrapped so long engine error messages
        # wrap instead of stretching the panel).
        self.cg_validation_label = QLabel("Upload both files to validate")
        self.cg_validation_label.setWordWrap(True)
        layout.addRow(self.cg_validation_label)

        # Slot state (None until a valid pair is uploaded). All
        # custom-guest state co-located here for readability.
        self._custom_guest = None  # dict: guest_type, residue_name, gro_path,
                                  #      itp_path, atom_labels, atom_count
        self._cg_gro_path = None
        self._cg_itp_path = None

        group.setLayout(layout)
        return group

    def _upload_custom_gro(self):
        """Handle .gro file upload via QFileDialog (Phase 44-02)."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Custom Guest GRO File", "",
            "GRO Files (*.gro);;All Files (*)"
        )
        if filepath:
            self._cg_gro_path = Path(filepath)
            self.cg_gro_status.setText(self._cg_gro_path.name)
            self.cg_gro_status.setStyleSheet("color: black;")
            self._try_validate_custom_guest()

    def _upload_custom_itp(self):
        """Handle .itp file upload via QFileDialog (Phase 44-02)."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Custom Guest ITP File", "",
            "ITP Files (*.itp);;All Files (*)"
        )
        if filepath:
            self._cg_itp_path = Path(filepath)
            self.cg_itp_status.setText(self._cg_itp_path.name)
            self.cg_itp_status.setStyleSheet("color: black;")
            self._try_validate_custom_guest()

    def _derive_guest_type_slug(self, itp_path) -> str:
        """Derive the GenIce2 plugin slug for the uploaded custom guest.

        Single-occupancy slot: a fixed slug is sufficient (re-upload
        overwrites ``_custom_guest`` entirely; the generator only registers
        what is in ``cage_guest_assignments``). ``audit_name`` accepts
        ``^[A-Za-z0-9-_]+$`` and is already called inside
        ``validate_custom_guest_files`` step 7, so ``"custom_gui"`` passes.

        The ``itp_path`` parameter is kept for API stability / future
        derivation if multi-slot is ever added; it is intentionally unused.
        """
        return "custom_gui"

    def _try_validate_custom_guest(self):
        """Validate the uploaded .gro + .itp pair and store the descriptor.

        Reuses :func:`validate_custom_guest_files` (the canonical engine
        validator — never reimplement per GUI-05). On a valid pair, calls
        :func:`parse_gro_file` once to get the atom-name list (the validator
        does NOT return atom names — Pitfall 3) and stores the descriptor on
        ``self._custom_guest``. Rebuilds the per-cage rows so the
        "Custom: {residue}" option appears in every combo. Emits
        ``configuration_changed``.

        On an invalid pair: sets the validation label red with the specific
        engine error messages, clears ``self._custom_guest``, rebuilds the
        cage rows (removes any previously-added Custom option), and emits
        ``configuration_changed``.

        All engine imports (``validate_custom_guest_files``,
        ``parse_gro_file``) are lazy imports INSIDE this handler per
        AGENTS.md (no top-level engine imports in ``hydrate_panel.py``). GUI
        code may use a broad ``except Exception`` as a safety net per
        AGENTS.md (only ``quickice/cli/pipeline.py`` forbids bare
        ``except Exception``).
        """
        # Early-return when not both paths are selected.
        if not (self._cg_gro_path and self._cg_itp_path):
            return

        guest_type = self._derive_guest_type_slug(self._cg_itp_path)

        # REUSE the canonical validator (do NOT reimplement — GUI-05).
        from quickice.structure_generation.custom_guest_bridge import (
            validate_custom_guest_files,
        )
        result = validate_custom_guest_files(
            self._cg_gro_path, self._cg_itp_path, guest_type
        )

        if not result.is_valid:
            self.cg_validation_label.setText(
                "✗ Validation failed:\n" + "\n".join(result.errors)
            )
            self.cg_validation_label.setStyleSheet("color: red;")
            self._custom_guest = None
            self._rebuild_cage_rows()  # remove any stale Custom option
            self.configuration_changed.emit()
            return

        # Warnings are non-blocking (e.g. missing [ atomtypes ]). Surface them
        # via a modal dialog but still treat the upload as valid. Pattern
        # from custom_molecule_panel.py::_show_validation_warnings.
        if result.warnings:
            QMessageBox.warning(
                self, "Custom Guest Warnings", "\n".join(result.warnings)
            )

        # Valid: parse the GRO once to get atom_names (the validator does NOT
        # return them — Pitfall 3). Defensive broad except per AGENTS.md for
        # GUI code (validation already ran, so this should not fail, but be
        # safe).
        try:
            from quickice.structure_generation.gro_parser import parse_gro_file
            _, atom_names, _ = parse_gro_file(self._cg_gro_path)
        except Exception as exc:
            self.cg_validation_label.setText(
                f"✗ Validation succeeded but GRO re-parse failed: {exc}"
            )
            self.cg_validation_label.setStyleSheet("color: red;")
            self._custom_guest = None
            self._rebuild_cage_rows()
            self.configuration_changed.emit()
            return

        self._custom_guest = {
            "guest_type": guest_type,
            "residue_name": result.residue_name,
            "gro_path": str(self._cg_gro_path),
            "itp_path": str(self._cg_itp_path),
            "atom_labels": list(atom_names),       # -> CageGuestAssignment.guest_atom_labels
            "atom_count": result.gro_atom_count,   # -> CageGuestAssignment.guest_atom_count
        }
        self.cg_validation_label.setText(
            f"✓ Custom guest validated: {result.residue_name} "
            f"({result.gro_atom_count} atoms)"
        )
        self.cg_validation_label.setStyleSheet("color: green;")
        self._rebuild_cage_rows()  # add "Custom: {residue}" to every combo
        self.configuration_changed.emit()

    def _create_cage_assignment_group(self) -> QGroupBox:
        """Create the per-cage guest assignment group.

        Builds a dynamic ``QFormLayout`` with one row per cage key in the
        selected lattice's ``cage_type_map`` (rebuilt by
        ``_rebuild_cage_rows``). Each row has a guest ``QComboBox`` (built-in
        guests from ``GUEST_MOLECULES``) + an occupancy ``QDoubleSpinBox``
        (0-100 %). Water-only lattices show a "no cages" label and no rows.

        A force-field info label is kept (reads the first cage row's guest via
        ``_update_ff_label``), preserving the legacy single-guest display.
        """
        group = QGroupBox("Cage Guest Assignment")
        self._cage_form_layout = QFormLayout()
        # Per-cage widgets are built in _rebuild_cage_rows(); keep references
        # in dicts keyed by cage key ("small"/"medium"/"large"/"guest").
        self._cage_guest_combos: dict[str, QComboBox] = {}
        self._cage_occupancy_spins: dict[str, QDoubleSpinBox] = {}
        # Wrapper widget so the per-cage rows can be rebuilt cleanly without
        # disturbing the outer form layout (which also holds the ff label).
        self._cage_rows_container = QWidget()
        self._cage_rows_layout = QFormLayout(self._cage_rows_container)
        self._cage_form_layout.addRow(self._cage_rows_container)
        # Force field info label (reads the first cage row's selected guest).
        self.ff_label = QLabel()
        self.ff_label.setStyleSheet("color: gray; font-style: italic;")
        self._cage_form_layout.addRow("Force field:", self.ff_label)
        group.setLayout(self._cage_form_layout)
        return group

    def _rebuild_cage_rows(self):
        """Rebuild per-cage guest+occupancy rows from the selected lattice.

        Clears any existing rows and creates one row per cage key in
        ``HYDRATE_LATTICES[lattice]["cage_type_map"]``. Each row pairs a guest
        ``QComboBox`` (built-in guests) with an occupancy ``QDoubleSpinBox``
        (0-100 %, default 100 %). Water-only lattices (empty
        ``cage_type_map``) show a "No cages — water-only structure" label and
        no rows. Filled ices (single "small" key) show one "Guest cages" row.

        ``configuration_changed`` is emitted when any per-cage combo or spin
        changes; combo changes also refresh the force-field label and lattice
        info display (mirrors the legacy ``_on_guest_changed`` flow).
        """
        # Clear existing rows + widget references.
        self._cage_guest_combos.clear()
        self._cage_occupancy_spins.clear()
        while self._cage_rows_layout.rowCount():
            self._cage_rows_layout.removeRow(0)

        lattice_id = self.lattice_combo.currentData()
        if not lattice_id:
            return
        lattice_entry = HYDRATE_LATTICES.get(lattice_id, {})
        cage_type_map = lattice_entry.get("cage_type_map", {})

        if not cage_type_map:
            # Water-only lattice: no cage rows.
            label = QLabel("No cages — water-only structure")
            label.setStyleSheet("color: gray; font-style: italic;")
            self._cage_rows_layout.addRow(label)
            return

        num_keys = len(cage_type_map)
        for cage_key in cage_type_map:
            row = QHBoxLayout()
            # Guest combo (built-in guests with guest_id as item data).
            combo = QComboBox()
            for guest_id, guest_info in GUEST_MOLECULES.items():
                combo.addItem(
                    f"{guest_info['name']} ({guest_info['formula']})",
                    guest_id,
                )
            # Phase 44-02: if a custom guest is loaded, add it as an option.
            # is_custom_guest detects via guest_type not in GUEST_MOLECULES
            # (types.py:466); the item data is the custom guest_type slug.
            if self._custom_guest is not None:
                combo.addItem(
                    f"Custom: {self._custom_guest['residue_name']}",
                    self._custom_guest['guest_type'],
                )
            # Phase 44-02: route per-cage combo changes through
            # _on_cage_guest_changed so the ff label + lattice info refresh on
            # every change. Plan 44.1-01 relaxed the engine to allow the same
            # custom guest in multiple cages (same guest_type aggregates into one
            # _H moleculetype exactly like ch4), so the per-cage change just
            # updates the combo without auto-clearing (the 44-02 auto-clear
            # mitigation was removed in 44.1-18). The lambda captures cage_key
            # by default arg to avoid late-binding.
            combo.currentIndexChanged.connect(
                lambda _idx, ck=cage_key: self._on_cage_guest_changed(ck)
            )
            row.addWidget(combo)
            row.addStretch()
            # Occupancy spinbox (0-100 %, default 100 %).
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 100.0)
            spin.setValue(100.0)
            spin.setSuffix("%")
            spin.setDecimals(1)
            spin.valueChanged.connect(lambda: self.configuration_changed.emit())
            row.addWidget(spin)
            # Store references + add the row.
            self._cage_guest_combos[cage_key] = combo
            self._cage_occupancy_spins[cage_key] = spin
            row_label = "Guest cages" if num_keys == 1 else f"{cage_key.capitalize()} cages"
            self._cage_rows_layout.addRow(row_label, row)

    def _first_cage_guest_id(self):
        """Return the selected guest_id of the first per-cage row, or None.

        Used by ``_update_ff_label`` and ``_update_info_display`` to mirror the
        legacy single-guest display using the first cage row's guest (the
        per-cage fit display is a nice-to-have, not required by this plan).
        """
        if self._cage_guest_combos:
            first_combo = next(iter(self._cage_guest_combos.values()))
            return first_combo.currentData()
        return None
    
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
        row.addWidget(HelpIcon(
            "Unit cell repetition in X, Y, Z directions.\n"
            "Range: 1-10 each. Typical: 1-3 for testing, 3-5 for production.\n"
            "Higher values = larger structure = more molecules."
        ))
        row.addStretch()
        
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
        # Per-cage combo/spin connections are wired in _rebuild_cage_rows
        # (the widgets are rebuilt whenever the lattice changes).
        self.depol_combo.currentIndexChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_x.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_y.valueChanged.connect(lambda: self.configuration_changed.emit())
        self.supercell_z.valueChanged.connect(lambda: self.configuration_changed.emit())
    
    def _on_lattice_changed(self):
        """Handle lattice type change."""
        # Rebuild per-cage rows FIRST so the ff label + info display read the
        # new (default) cage row guest instead of the now-removed old widgets.
        self._update_guest_ui_for_lattice()
        self._update_ff_label()
        self._update_info_display()
        self.configuration_changed.emit()
    
    def _on_cage_guest_changed(self, cage_key):
        """Handle a per-cage guest combo change (Phase 44-02).

        Refreshes the force-field label + lattice info display (mirrors the
        legacy ``_on_guest_changed`` flow) and emits ``configuration_changed``.

        The engine (relaxed in plan 44.1-01) allows the same custom guest in
        multiple cages — same ``guest_type`` across cages aggregates into one
        ``_H`` moleculetype exactly like ``ch4`` — so this handler no longer
        auto-clears a previously-selected cage. The 44-02 auto-clear
        mitigation was removed in 44.1-18 because the
        ``residue_name``→``guest_type`` check in
        ``HydrateConfig.__post_init__`` only rejects genuine collisions (a
        DIFFERENT ``guest_type`` claiming an already-seen residue name).
        """
        self._update_ff_label()
        self._update_info_display()  # Update guest fit info
        self.configuration_changed.emit()

    def _update_guest_ui_for_lattice(self):
        """Rebuild per-cage guest+occupancy rows for the selected lattice.

        Water-only lattices show a "no cages" label; filled ices show one row;
        sI/sII show two rows; sH shows three rows. Enabling is handled by the
        rows simply existing or not (no separate setEnabled calls).
        """
        self._rebuild_cage_rows()
    
    def _update_ff_label(self):
        """Update force field label based on the first cage row's selected guest."""
        guest_id = self._first_cage_guest_id()
        if guest_id and guest_id in GUEST_MOLECULES:
            ff = GUEST_MOLECULES[guest_id].get('force_field', 'Unknown')
            self.ff_label.setText(ff)
        else:
            self.ff_label.setText("")
    
    def _update_info_display(self):
        """Update lattice info display."""
        lattice_id = self.lattice_combo.currentData()
        guest_id = self._first_cage_guest_id()
        
        if not lattice_id:
            return
        
        try:
            info = HydrateLatticeInfo.from_lattice_type(lattice_id)
        except ValueError:
            self.info_text.setText("Invalid lattice type")
            return
        
        lattice_entry = HYDRATE_LATTICES.get(lattice_id, {})
        is_water_only = lattice_entry.get("is_water_only", False)
        
        lines = [
            f"Lattice: {info.description}",
            f"Water molecules per unit cell: {info.unit_cell_molecules}",
        ]
        
        if is_water_only or info.total_cages == 0:
            lines.append("")
            lines.append("No cages — water-only structure")
            lines.append("Guest molecule placement is not applicable.")
        else:
            lines.append(f"Total cages per unit cell: {info.total_cages}")
            lines.append("")
            lines.append("Cage types:")

            for cage_name, count in info.cage_counts.items():
                # Check if guest fits
                fits = ""
                if guest_id and guest_id in GUEST_MOLECULES:
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

        Builds ``cage_guest_assignments`` from the per-cage rows (one
        ``CageGuestAssignment`` per cage key with its selected guest type +
        occupancy). Built-in guest metadata (``guest_atom_labels`` /
        ``guest_atom_count``) is auto-populated per-assignment by
        ``HydrateConfig.__post_init__`` (the canonical single source of truth
        per 42-01), so this method only supplies ``guest_type`` + ``occupancy``.

        Returns:
            HydrateConfig with current UI values
        """
        cage_guest_assignments = {}
        for cage_key, combo in self._cage_guest_combos.items():
            guest_id = combo.currentData() or "ch4"
            occ = self._cage_occupancy_spins[cage_key].value()
            if guest_id not in GUEST_MOLECULES and self._custom_guest is not None:
                # Phase 44-02: custom guest — supply FULL metadata (no
                # auto-populate; __post_init__ only auto-populates built-ins).
                cg = self._custom_guest
                cage_guest_assignments[cage_key] = CageGuestAssignment(
                    guest_type=cg['guest_type'],
                    occupancy=occ,
                    guest_residue_name=cg['residue_name'],
                    guest_gro_path=cg['gro_path'],
                    guest_itp_path=cg['itp_path'],
                    guest_atom_labels=list(cg['atom_labels']),
                    guest_atom_count=cg['atom_count'],
                )
            else:
                cage_guest_assignments[cage_key] = CageGuestAssignment(
                    guest_type=guest_id, occupancy=occ
                )
        return HydrateConfig(
            lattice_type=self.lattice_combo.currentData(),
            cage_guest_assignments=cage_guest_assignments,
            supercell_x=self.supercell_x.value(),
            supercell_y=self.supercell_y.value(),
            supercell_z=self.supercell_z.value(),
            depol_mode=self.depol_combo.currentData(),
        )
    
    def _on_hbonds_toggled(self):
        """Toggle water framework / H-bonds visibility."""
        if not self.hydrate_viewer.is_vtk_available():
            return
        
        visible = self.btn_hbonds.isChecked()
        self.hydrate_viewer.set_hbonds_visible(visible)
    
    def _on_unit_cell_toggled(self):
        """Toggle unit cell box visibility."""
        if not self.hydrate_viewer.is_vtk_available():
            return
        
        visible = self.btn_unit_cell.isChecked()
        self.hydrate_viewer.set_unit_cell_visible(visible)
    
    def _on_representation_toggled(self):
        """Cycle through VDW, Ball-and-stick, and Stick representations."""
        if not self.hydrate_viewer.is_vtk_available():
            return
        
        # Get current mode from button text
        current_text = self.btn_representation.text()
        
        # Cycle through modes: Ball-and-stick -> VDW -> Stick -> Ball-and-stick
        if current_text == "Ball-and-stick":
            self.btn_representation.setText("VDW")
            self.hydrate_viewer.set_representation_mode("vdw")
        elif current_text == "VDW":
            self.btn_representation.setText("Stick")
            self.hydrate_viewer.set_representation_mode("stick")
        else:  # Stick
            self.btn_representation.setText("Ball-and-stick")
            self.hydrate_viewer.set_representation_mode("ball_and_stick")
    
    def set_hydrate_structure(self, structure):
        """Set hydrate structure for display in viewer."""
        self._current_structure = structure
        self.hydrate_viewer.set_hydrate_structure(structure)
