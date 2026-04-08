"""Main application window for QuickIce GUI.

This module provides the MainWindow class that assembles all GUI components:
- InputPanel for temperature, pressure, and molecule count inputs
- ProgressPanel for progress bar and status text
- PhaseDiagramPanel for interactive phase diagram
- ViewerPanel for 3D molecular visualization
- InfoPanel for generation log output
- Generate/Cancel buttons
- Keyboard shortcuts (Enter to generate, Escape to cancel)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QMessageBox, QApplication, QSplitter, QMenuBar, QMenu,
    QTabWidget
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot

from quickice.gui.view import InputPanel, ProgressPanel, ViewerPanel, InfoPanel
from quickice.gui.viewmodel import MainViewModel
from quickice.gui.phase_diagram_widget import PhaseDiagramPanel
from quickice.gui.export import PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter
from quickice.gui.help_dialog import QuickReferenceDialog
from quickice.gui.interface_panel import InterfacePanel
from quickice.phase_mapping.lookup import PHASE_METADATA


class MainWindow(QMainWindow):
    """Main application window for QuickIce GUI.
    
    This is the MVVM "View" layer that connects to the ViewModel.
    
    The window provides:
    - Input panel for thermodynamic parameters
    - Progress panel for generation feedback
    - Generate button to trigger ice structure generation
    - Cancel button to abort generation mid-process
    - Keyboard shortcuts: Enter to generate, Escape to cancel
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QuickIce - Ice Structure Generator")
        self.setMinimumSize(1300, 600)
        
        # Create viewmodel
        self._viewmodel = MainViewModel(self)
        
        # Export handlers
        self._pdb_exporter = PDBExporter(self)
        self._diagram_exporter = DiagramExporter(self)
        self._viewport_exporter = ViewportExporter(self)
        self._gromacs_exporter = GROMACSExporter(self)
        
        # Store current generation result for export
        self._current_result = None
        self._current_T = 0.0
        self._current_P = 0.0
        
        # Store current interface result for export
        self._current_interface_result = None
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        
        # Create menu bar (after shortcuts so it appears in proper order)
        self._create_menu_bar()
    
    def _setup_ui(self):
        """Setup UI components with two-tab layout.
        
        Tab 1: Ice Generation (existing functionality)
        Tab 2: Interface Construction (new in v3.0)
        """
        # Create tab widget as central container
        self.tab_widget = QTabWidget()
        
        # === Tab 1: Ice Generation ===
        # Wrap existing content in a QWidget for Tab 1
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        tab1_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for horizontal split view (Phase Diagram + Right panels)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Phase diagram panel
        self.diagram_panel = PhaseDiagramPanel()
        splitter.addWidget(self.diagram_panel)
        
        # Right side: Input panel, progress panel, viewer, buttons
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Input panel
        self.input_panel = InputPanel()
        right_layout.addWidget(self.input_panel)
        
        # Progress panel
        self.progress_panel = ProgressPanel()
        right_layout.addWidget(self.progress_panel)
        
        # Viewer panel (3D molecular viewer with toolbar)
        self.viewer_panel = ViewerPanel()
        right_layout.addWidget(self.viewer_panel, stretch=1)  # Give viewer extra space
        
        # Info panel (collapsible log output)
        self.info_panel = InfoPanel()
        right_layout.addWidget(self.info_panel)
        
        # Buttons
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setDefault(True)  # Responds to Enter key when focused
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        
        right_layout.addWidget(self.generate_btn)
        right_layout.addWidget(self.cancel_btn)
        
        splitter.addWidget(right_widget)
        
        # Set initial sizes (diagram 550px, right panel 750px for dual viewer)
        splitter.setSizes([550, 750])
        
        # Add splitter to Tab 1 layout
        tab1_layout.addWidget(splitter)
        
        # === Tab 2: Interface Construction ===
        self.interface_panel = InterfacePanel()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(tab1_widget, "Ice Generation")
        self.tab_widget.addTab(self.interface_panel, "Interface Construction")
        
        # Set Tab 1 as default on startup
        self.tab_widget.setCurrentIndex(0)
        
        # Set tab widget as central widget
        self.setCentralWidget(self.tab_widget)
        
        # Show placeholder before first generation
        self.viewer_panel.show_placeholder()
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        # Button connections
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        # Diagram selection -> input panel
        self.diagram_panel.diagram_canvas.coordinates_selected.connect(
            self._on_diagram_selected
        )
        
        # Phase info from diagram click
        self.diagram_panel.diagram_canvas.phase_info_ready.connect(self._on_phase_info)
        
        # Input field changes -> diagram marker (bidirectional binding)
        self.input_panel.temp_input.textChanged.connect(self._on_input_changed)
        self.input_panel.pressure_input.textChanged.connect(self._on_input_changed)
        
        # ViewModel connections - progress
        self._viewmodel.generation_progress.connect(self.progress_panel.update_progress)
        self._viewmodel.generation_status.connect(self.progress_panel.update_status)
        
        # ViewModel connections - state
        self._viewmodel.generation_started.connect(self._on_generation_started)
        self._viewmodel.generation_complete.connect(self._on_generation_complete)
        self._viewmodel.generation_error.connect(self._on_generation_error)
        self._viewmodel.generation_cancelled.connect(self._on_generation_cancelled)
        
        # ViewModel connections - viewer
        self._viewmodel.ranked_candidates_ready.connect(self._on_candidates_ready)
        
        # ViewModel connections - log
        self._viewmodel.generation_status.connect(self.info_panel.append_log)
        
        # UI state connections
        self._viewmodel.ui_enabled_changed.connect(self._on_ui_enabled_changed)
        
        # Tab change handling - preserve state during tab switches
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Tab 2 (Interface Construction) connections
        self.interface_panel.refresh_requested.connect(self._on_refresh_candidates)
        
        # Tab 2 (Interface Construction) generation connections
        self.interface_panel.generate_requested.connect(self._on_interface_generate)
        
        # ViewModel interface generation signals
        self._viewmodel.interface_generation_started.connect(self._on_interface_generation_started)
        self._viewmodel.interface_generation_progress.connect(self.interface_panel.progress_panel.update_progress)
        self._viewmodel.interface_generation_status.connect(self.interface_panel.progress_panel.update_status)
        self._viewmodel.interface_generation_status.connect(self.interface_panel.append_log)
        self._viewmodel.interface_generation_complete.connect(self._on_interface_generation_complete)
        self._viewmodel.interface_generation_error.connect(self._on_interface_generation_error)
        self._viewmodel.interface_generation_cancelled.connect(self._on_interface_generation_cancelled)
        self._viewmodel.interface_ui_enabled_changed.connect(self._on_interface_ui_enabled_changed)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts.
        
        Per UX-01: Enter to generate, Escape to cancel.
        """
        # Enter to generate
        generate_action = QAction(self)
        generate_action.setShortcut(Qt.Key.Key_Return)
        generate_action.triggered.connect(self._on_generate_clicked)
        self.addAction(generate_action)
        
        # Also handle Enter on keypad
        generate_action_kp = QAction(self)
        generate_action_kp.setShortcut(Qt.Key.Key_Enter)
        generate_action_kp.triggered.connect(self._on_generate_clicked)
        self.addAction(generate_action_kp)
        
        # Escape to cancel
        cancel_action = QAction(self)
        cancel_action.setShortcut(Qt.Key.Key_Escape)
        cancel_action.triggered.connect(self._on_cancel_clicked)
        self.addAction(cancel_action)
    
    def _create_menu_bar(self):
        """Create menu bar with File menu.
        
        Per must_haves: Menu bar with File menu containing Save PDB, 
        Save Diagram, and Save Viewport actions.
        """
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Save PDB from Left Viewer action
        save_pdb_left_action = file_menu.addAction("Save PDB (Left Viewer)...")
        save_pdb_left_action.setShortcut("Ctrl+S")
        save_pdb_left_action.triggered.connect(self._on_save_pdb_left)
        
        # Save PDB from Right Viewer action
        save_pdb_right_action = file_menu.addAction("Save PDB (Right Viewer)...")
        save_pdb_right_action.setShortcut("Ctrl+Shift+S")
        save_pdb_right_action.triggered.connect(self._on_save_pdb_right)
        
        # Separator
        file_menu.addSeparator()
        
        # Save Diagram action
        save_diagram_action = file_menu.addAction("Save Diagram...")
        save_diagram_action.setShortcut("Ctrl+D")
        save_diagram_action.triggered.connect(self._on_save_diagram)
        
        # Save Viewport action
        save_viewport_action = file_menu.addAction("Save Viewport...")
        save_viewport_action.setShortcut("Ctrl+Alt+S")
        save_viewport_action.triggered.connect(self._on_save_viewport)
        
        # Separator before Export for GROMACS
        file_menu.addSeparator()
        
        # Export for GROMACS action
        export_gromacs_action = file_menu.addAction("Export for GROMACS...")
        export_gromacs_action.setShortcut("Ctrl+G")
        export_gromacs_action.triggered.connect(self._on_export_gromacs)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # Quick Reference action
        quick_ref_action = help_menu.addAction("Quick Reference")
        quick_ref_action.triggered.connect(self._on_help)
    
    @Slot()
    def _on_generate_clicked(self):
        """Handle Generate button click."""
        # Clear previous errors
        self.input_panel.clear_errors()
        
        # Validate inputs
        if not self.input_panel.validate_all():
            return
        
        # Get values
        temperature = self.input_panel.get_temperature()
        pressure = self.input_panel.get_pressure()
        nmolecules = self.input_panel.get_nmolecules()
        
        # Store current generation parameters for export
        self._current_T = temperature
        self._current_P = pressure
        
        # Reset progress
        self.progress_panel.reset()
        self.progress_panel.set_generating()
        
        # Start generation
        self._viewmodel.start_generation(temperature, pressure, nmolecules)
    
    @Slot()
    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        self._viewmodel.cancel_generation()
    
    @Slot()
    def _on_generation_started(self):
        """Handle generation started."""
        self.progress_panel.set_generating()
        self.info_panel.clear_log()
        self.info_panel.append_log("Starting ice structure generation...")
    
    @Slot(object)
    def _on_generation_complete(self, result):
        """Handle generation complete."""
        self.progress_panel.set_complete()
        self.input_panel.clear_errors()
        # Result is passed to _on_candidates_ready via ranked_candidates_ready signal
    
    @Slot(object)
    def _on_candidates_ready(self, result):
        """Handle ranked candidates ready for display.
        
        Args:
            result: RankingResult containing ranked_candidates list
        """
        # Store result for export
        self._current_result = result
        
        # Hide placeholder and show viewer
        self.viewer_panel.hide_placeholder()
        
        # Log candidate rankings with scores (CLI-style output)
        self.info_panel.append_log("\n" + "="*50)
        self.info_panel.append_log("Ranked Candidates")
        self.info_panel.append_log("="*50)
        
        if hasattr(result, 'ranked_candidates') and result.ranked_candidates:
            for rc in result.ranked_candidates:
                self.info_panel.append_log(
                    f"  Rank {rc.rank}: {rc.candidate.phase_id} | "
                    f"energy={rc.energy_score:.3f} density={rc.density_score:.3f} "
                    f"combined={rc.combined_score:.3f}"
                )
            self.info_panel.append_log("")
            
            # Update candidate selector in viewer panel
            self.viewer_panel.update_candidate_selector(result.ranked_candidates)
            
            # Update Tab 2 dropdown with candidates
            self.interface_panel.update_candidates(result.ranked_candidates)
        
        # Load candidates into dual viewer (if VTK available)
        if self.viewer_panel.is_vtk_available():
            if hasattr(result, 'ranked_candidates') and result.ranked_candidates:
                self.viewer_panel.dual_viewer.set_candidates(result.ranked_candidates)
                
                # Log viewer info
                self.info_panel.append_log(
                    f"Rank #1 shown in left viewport, Rank #2 in right"
                )
        else:
            # VTK not available - show message in log
            self.info_panel.append_log(
                "3D viewer unavailable in remote environment. "
                "Clone to local machine for full visualization."
            )
    
    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """Handle generation error.
        
        Per PROGRESS-04: User sees error dialog when generation fails.
        """
        self.progress_panel.set_error(error_msg)
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "Generation Error",
            f"Failed to generate ice structure:\n\n{error_msg}",
            QMessageBox.StandardButton.Ok
        )
    
    @Slot()
    def _on_generation_cancelled(self):
        """Handle generation cancelled."""
        self.progress_panel.set_cancelled()
    
    @Slot()
    def _on_refresh_candidates(self):
        """Refresh candidates in Tab 2 from Tab 1's current candidates."""
        result = self._viewmodel.get_last_ranking_result()
        if result and hasattr(result, 'ranked_candidates'):
            self.interface_panel.update_candidates(result.ranked_candidates)
            if result.ranked_candidates:
                self.interface_panel.append_log(f"Candidates refreshed: {len(result.ranked_candidates)} available")
            else:
                self.interface_panel.append_log("No candidates available")
        else:
            # No candidates exist
            self.interface_panel.update_candidates([])
            self.interface_panel.append_log("No candidates available")
    
    # === Interface Generation Handlers (Tab 2) ===
    
    @Slot(int)
    def _on_interface_generate(self, candidate_index: int):
        """Handle Generate Interface button click from Tab 2.
        
        Args:
            candidate_index: Index of selected candidate in ranked candidates list
        """
        from quickice.structure_generation.types import InterfaceConfig
        
        # Get the ranked candidates result
        ranking_result = self._viewmodel.get_last_ranking_result()
        if not ranking_result or not hasattr(ranking_result, 'ranked_candidates'):
            self.interface_panel.append_log("No candidates available. Generate ice in Tab 1 first.")
            return
        
        if candidate_index < 0 or candidate_index >= len(ranking_result.ranked_candidates):
            self.interface_panel.append_log("Invalid candidate selection.")
            return
        
        # Get selected candidate
        ranked = ranking_result.ranked_candidates[candidate_index]
        candidate = ranked.candidate
        
        # Get configuration from InterfacePanel
        config_dict = self.interface_panel.get_configuration()
        config = InterfaceConfig.from_dict(config_dict)
        
        # Reset progress and log
        self.interface_panel.progress_panel.reset()
        self.interface_panel.progress_panel.set_generating()
        self.interface_panel.clear_log()
        self.interface_panel.append_log(f"Starting {config.mode} interface generation...")
        self.interface_panel.append_log(f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm")
        self.interface_panel.append_log(f"  Candidate: {candidate.phase_id} ({candidate.nmolecules} molecules)")
        
        # Start generation via ViewModel
        self._viewmodel.start_interface_generation(candidate, config)
    
    @Slot()
    def _on_interface_generation_started(self):
        """Handle interface generation started."""
        self.interface_panel.set_generating(True)
        # Keep placeholder visible during generation
        # (viewer will replace it when structure is ready)
    
    @Slot(object)
    def _on_interface_generation_complete(self, result):
        """Handle interface generation complete.
        
        Args:
            result: InterfaceStructure from generation
        """
        self._current_interface_result = result
        
        # Update progress
        self.interface_panel.progress_panel.set_complete()
        self.interface_panel.set_generating(False)
        
        # Log the generation report
        if result.report:
            self.interface_panel.append_log("\n" + "=" * 50)
            self.interface_panel.append_log(result.report)
            self.interface_panel.append_log("=" * 50)
        
        self.interface_panel.append_log(f"\nInterface generation complete.")
        
        # Display structure in 3D viewer
        self.interface_panel._interface_viewer.set_interface_structure(result)
        self.interface_panel.hide_placeholder()
    
    @Slot(str)
    def _on_interface_generation_error(self, error_msg: str):
        """Handle interface generation error."""
        self.interface_panel.progress_panel.set_error(error_msg)
        self.interface_panel.set_generating(False)
        
        QMessageBox.critical(
            self,
            "Interface Generation Error",
            f"Failed to generate interface structure:\n\n{error_msg}",
            QMessageBox.StandardButton.Ok
        )
    
    @Slot()
    def _on_interface_generation_cancelled(self):
        """Handle interface generation cancelled."""
        self.interface_panel.progress_panel.set_cancelled()
        self.interface_panel.set_generating(False)
    
    @Slot(bool)
    def _on_interface_ui_enabled_changed(self, enabled: bool):
        """Handle Tab 2 UI enabled/disabled state change."""
        self.interface_panel.set_generating(not enabled)
    
    @Slot(int)
    def _on_tab_changed(self, index: int):
        """Handle tab switch - preserve state.
        
        Qt widgets automatically preserve their state, so no explicit
        saving/loading is needed. This handler exists for future
        extensibility (e.g., logging tab changes).
        
        Args:
            index: New tab index (0 = Ice Generation, 1 = Interface Construction)
        """
        # Qt preserves all widget state automatically
        # No explicit state saving needed - widgets maintain their own state
        pass
    
    @Slot(bool)
    def _on_ui_enabled_changed(self, enabled: bool):
        """Handle UI enabled/disabled state change."""
        self.generate_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(not enabled)
        self.input_panel.setEnabled(enabled)
        self.viewer_panel.setEnabled(enabled)
    
    @Slot(float, float)
    def _on_diagram_selected(self, temperature: float, pressure: float):
        """Handle diagram selection - populate input fields.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        """
        # Set values in input panel with rounding
        self.input_panel.set_values(
            round(temperature, 1),
            round(pressure, 2),  # Round to 2 decimals for MPa
            96  # Default molecule count
        )
    
    @Slot()
    def _on_input_changed(self):
        """Handle input field changes - update diagram marker.
        
        This creates bidirectional binding: typing in input fields
        updates the diagram marker position.
        """
        try:
            temp = float(self.input_panel.temp_input.text())
            pressure = float(self.input_panel.pressure_input.text())
            # Only update if values are in valid range
            if 50 <= temp <= 500 and 0.1 <= pressure <= 10000:
                self.diagram_panel.set_coordinates(temp, pressure)
        except (ValueError, TypeError):
            pass  # Invalid input, don't update marker
    
    @Slot()
    def _on_save_pdb_left(self):
        """Handle Save PDB (Left Viewer) menu action.
        
        Per EXPORT-01: User can save generated PDB file via native file save dialog.
        """
        if not self._current_result or not hasattr(self._current_result, 'ranked_candidates'):
            QMessageBox.warning(self, "No Data", "Generate a structure first before saving.")
            return
        
        if not self._current_result.ranked_candidates:
            QMessageBox.warning(self, "No Data", "No candidates available to save.")
            return
        
        # Get selected candidate from left viewer dropdown
        selected_idx = self.viewer_panel.get_selected_candidate_index_left()
        if selected_idx < 0 or selected_idx >= len(self._current_result.ranked_candidates):
            selected_idx = 0  # Fallback to rank 1
        
        ranked = self._current_result.ranked_candidates[selected_idx]
        self._pdb_exporter.export_candidate(ranked, self._current_T, self._current_P)
    
    @Slot()
    def _on_save_pdb_right(self):
        """Handle Save PDB (Right Viewer) menu action.
        
        Per EXPORT-01: User can save generated PDB file via native file save dialog.
        """
        if not self._current_result or not hasattr(self._current_result, 'ranked_candidates'):
            QMessageBox.warning(self, "No Data", "Generate a structure first before saving.")
            return
        
        if not self._current_result.ranked_candidates:
            QMessageBox.warning(self, "No Data", "No candidates available to save.")
            return
        
        # Get selected candidate from right viewer dropdown
        selected_idx = self.viewer_panel.get_selected_candidate_index_right()
        if selected_idx < 0 or selected_idx >= len(self._current_result.ranked_candidates):
            selected_idx = 0  # Fallback to rank 1
        
        ranked = self._current_result.ranked_candidates[selected_idx]
        self._pdb_exporter.export_candidate(ranked, self._current_T, self._current_P)
    
    @Slot()
    def _on_save_diagram(self):
        """Handle Save Diagram menu action.
        
        Per EXPORT-02: User can save phase diagram as PNG or SVG image file.
        """
        figure = self.diagram_panel.diagram_canvas.figure
        self._diagram_exporter.export_diagram(figure)
    
    @Slot()
    def _on_save_viewport(self):
        """Handle Save Viewport menu action.
        
        Per EXPORT-03: User can save 3D viewport screenshot as PNG image.
        
        Exports both viewports with unique filenames (left/right) to avoid conflicts.
        """
        if not self.viewer_panel.is_vtk_available():
            QMessageBox.warning(self, "Not Available", "3D viewer not available in remote environment.")
            return
        
        if self.viewer_panel.is_placeholder_visible():
            QMessageBox.warning(self, "No Data", "Generate a structure first before saving viewport.")
            return
        
        # Export left viewport (viewer1)
        vtk_widget_left = self.viewer_panel.dual_viewer.viewer1.vtk_widget
        left_success = self._viewport_exporter.capture_viewport(vtk_widget_left, "left")
        
        # Export right viewport (viewer2) if left export succeeded
        if left_success:
            vtk_widget_right = self.viewer_panel.dual_viewer.viewer2.vtk_widget
            self._viewport_exporter.capture_viewport(vtk_widget_right, "right")
    
    @Slot()
    def _on_export_gromacs(self):
        """Handle Export for GROMACS menu action.
        
        Per plan 14-02: Single action exports .gro, .top, and .itp files.
        """
        if not self._current_result or not hasattr(self._current_result, 'ranked_candidates'):
            QMessageBox.warning(self, "No Data", "Generate a structure first.")
            return
        
        if not self._current_result.ranked_candidates:
            QMessageBox.warning(self, "No Data", "No candidates available.")
            return
        
        # Get selected candidate from viewer
        selected_idx = self.viewer_panel.get_selected_candidate_index_left()
        if selected_idx < 0 or selected_idx >= len(self._current_result.ranked_candidates):
            selected_idx = 0
        
        ranked = self._current_result.ranked_candidates[selected_idx]
        
        # Get T and P from input panel
        T = self.input_panel.get_temperature()
        P = self.input_panel.get_pressure()
        
        success = self._gromacs_exporter.export_gromacs(ranked, T, P)
        
        # Show success message with water model information
        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"GROMACS files exported successfully.\n\n"
                f"Water model: TIP4P-ICE\n"
                f"(Abascal et al. 2005, DOI: 10.1063/1.1931662)\n\n"
                f"Files generated:\n"
                f"• {ranked.candidate.phase_id}_{T:.0f}K_{P:.0f}bar_c{ranked.rank}.gro\n"
                f"• {ranked.candidate.phase_id}_{T:.0f}K_{P:.0f}bar_c{ranked.rank}.top\n"
                f"• {ranked.candidate.phase_id}_{T:.0f}K_{P:.0f}bar_c{ranked.rank}.itp"
            )

    @Slot()
    def _on_help(self):
        """Open quick reference help dialog.

        Per INFO-04: Modal dialog with keyboard shortcuts and workflow summary.
        """
        dlg = QuickReferenceDialog(self)
        dlg.exec()

    @Slot(str, float, float)
    def _on_phase_info(self, phase_id: str, T: float, P: float):
        """Display phase information in log panel when user clicks diagram.
        
        Per INFO-01: User can view info window with citations/references.
        Per CONTEXT.md: Use existing log panel for phase info.
        
        Args:
            phase_id: Phase identifier (e.g., "Ih", "II", "Vapor", "Liquid")
            T: Temperature in Kelvin
            P: Pressure in MPa
        """
        # Expand log panel to show info
        self.info_panel.expand()
        
        # Clear and add phase info
        self.info_panel.clear_log()
        self.info_panel.append_log(f"{'='*50}")
        self.info_panel.append_log(f"Phase Information")
        self.info_panel.append_log(f"{'='*50}")
        self.info_panel.append_log(f"Conditions: T = {T:.1f} K, P = {P:.2f} MPa")
        
        # Debug: Log the phase_id being processed
        print(f"[DEBUG] _on_phase_info called with phase_id='{phase_id}'")
        
        # Handle special cases (Vapor, Liquid, boundary regions)
        if phase_id in ("Vapor", "Liquid") or "/" in phase_id:
            if "/" in phase_id:
                self.info_panel.append_log(f"Phase: {phase_id} (boundary)")
            else:
                self.info_panel.append_log(f"Phase: {phase_id}")
            self.info_panel.append_log(f"")
            self.info_panel.append_log(f"No ice phase data available for this region.")
        elif phase_id and phase_id != "unknown":
            # Get phase metadata
            # Convert short form to full phase_id (e.g., "Ih" -> "ice_ih")
            phase_id_full = _get_full_phase_id(phase_id)
            print(f"[DEBUG] Converted to phase_id_full='{phase_id_full}'")
            meta = PHASE_METADATA.get(phase_id_full, {})
            print(f"[DEBUG] PHASE_METADATA lookup returned: {meta}")
            phase_name = meta.get("name", phase_id)
            density = meta.get("density", "Unknown")
            density_note = meta.get("density_note")
            
            self.info_panel.append_log(f"Phase: {phase_name}")
            self.info_panel.append_log(f"Density: {density} g/cm³")
            if density_note:
                # Word wrap the note for display
                words = density_note.split()
                line = ""
                for word in words:
                    if len(line) + len(word) + 1 <= 60:
                        line = f"{line} {word}".strip()
                    else:
                        self.info_panel.append_log(f"  {line}")
                        line = word
                if line:
                    self.info_panel.append_log(f"  {line}")
            self.info_panel.append_log(f"Structure: {_get_structure_type(phase_id_full)}")
            self.info_panel.append_log(f"")
            self.info_panel.append_log(f"Citation:")
            self.info_panel.append_log(_get_citation(phase_id_full))
        else:
            self.info_panel.append_log("Phase: Unknown (click on a phase region)")


def _get_full_phase_id(phase_id: str) -> str:
    """Convert short phase ID to full phase ID.
    
    Args:
        phase_id: Short form (e.g., "Ih", "II") or full form (e.g., "ice_ih")
    
    Returns:
        Full phase ID (e.g., "ice_ih")
    """
    # Mapping from short form to full form
    short_to_full = {
        "Ih": "ice_ih",
        "Ic": "ice_ic",
        "II": "ice_ii",
        "III": "ice_iii",
        "V": "ice_v",
        "VI": "ice_vi",
        "VII": "ice_vii",
        "VIII": "ice_viii",
        "XI": "ice_xi",
        "IX": "ice_ix",
        "X": "ice_x",
        "XV": "ice_xv",
    }
    
    # If already full form, return as-is
    if phase_id.startswith("ice_"):
        return phase_id
    
    # Convert short form to full form
    return short_to_full.get(phase_id, phase_id)


def _get_structure_type(phase_id: str) -> str:
    """Get human-readable structure type.
    
    Args:
        phase_id: Full phase ID (e.g., "ice_ih")
    
    Returns:
        Human-readable structure type with space group
    """
    structure_types = {
        "ice_ih": "Hexagonal (P6₃/mmc)",
        "ice_ic": "Cubic diamond (Fd3m)",
        "ice_ii": "Rhombohedral (R-3)",
        "ice_iii": "Tetragonal (P4₁2₁2)",
        "ice_v": "Monoclinic (C2/c)",
        "ice_vi": "Tetragonal (P4₂/nmc)",
        "ice_vii": "Cubic (Pn-3m)",
        "ice_viii": "Tetragonal (I4₁/amd)",
        "ice_xi": "Hexagonal ordered (Cmc2₁)",
        "ice_ix": "Tetragonal ordered (P4₁2₁2)",
        "ice_x": "Symmetric H-bonds (Pn-3m)",
        "ice_xv": "Ordered (P-1)",
    }
    return structure_types.get(phase_id, "Unknown")


def _get_citation(phase_id: str) -> str:
    """Get primary citation for phase.
    
    Citations are from GenIce2 (https://github.com/genice-dev/GenIce2).
    
    Args:
        phase_id: Full phase ID (e.g., "ice_ih")
    
    Returns:
        Primary literature citation for the phase
    """
    # Citations from GenIce2 README and citations.json
    # https://github.com/genice-dev/GenIce2
    citations = {
        "ice_ih": "Hexagonal ice Ih (most common ice). No specific citation required.",
        "ice_ic": (
            "Vos, W.L. et al. (1993). Phys. Rev. Lett., 71(19), 3150-3153.\n"
            "DOI: 10.1103/PhysRevLett.71.3150\n\n"
            "Note: Ice Ic is metastable with respect to Ice Ih in this T-P region. "
            "For simplicity, QuickIce generates Ice Ic (cubic) structures only when "
            "conditions fall in the metastable T=72-150K region below the Ih-II boundary."
        ),
        "ice_ii": "Kamb, B. (1964). Acta Cryst., 17, 1437-1449. DOI: 10.1107/S0365110X64003553\nKamb, B. et al. (2003). J. Chem. Phys., 55, 1934-1945.",
        "ice_iii": "Petrenko, V.F. & Whitworth, R.W. (1999). Physics of Ice, Table 11.2.",
        "ice_v": "Monoclinic ice V. No specific citation in GenIce2.",
        "ice_vi": "Petrenko, V.F. & Whitworth, R.W. (1999). Physics of Ice, Table 11.2.",
        "ice_vii": "High-pressure ice VII. No specific citation in GenIce2.",
        "ice_viii": "Kuhs, W.F. et al. (1984). J. Chem. Phys., 81(8), 3612-3623. DOI: 10.1063/1.448109",
        "ice_xi": "Jackson, S.M. et al. (1997). J. Phys. Chem. B, 101, 6142.\nFan, X. et al. (2010). Comput. Mater. Sci., 49, S170-S175.",
        "ice_ix": "Londono, J.D. et al. (1993). J. Chem. Phys., 98(6), 4878-4888. DOI: 10.1063/1.464942",
        "ice_x": "Symmetric hydrogen-bond ice at extreme pressure. See IAPWS R14-08(2011) for phase boundaries.",
        "ice_xv": "Salzmann, C.G. et al. (2009). Phys. Rev. Lett., 103(10), 105701. DOI: 10.1103/PhysRevLett.103.105701",
    }
    return citations.get(phase_id, "See IAPWS R14-08(2011) for phase data.")


def run_app():
    """Run the QuickIce GUI application.
    
    This is the entry point for the QuickIce GUI.
    Creates QApplication, MainWindow, and starts the event loop.
    
    Usage:
        from quickice.gui import run_app
        run_app()
    """
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
