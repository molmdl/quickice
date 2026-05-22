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

import logging
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QMessageBox, QApplication, QSplitter, QMenuBar, QMenu,
    QTabWidget
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot, QThread

logger = logging.getLogger(__name__)

from quickice.gui.view import InputPanel, ProgressPanel, ViewerPanel, InfoPanel
from quickice.gui.viewmodel import MainViewModel
from quickice.gui.phase_diagram_widget import PhaseDiagramPanel
from quickice.gui.export import PDBExporter, DiagramExporter, ViewportExporter, GROMACSExporter, InterfaceGROMACSExporter, IonGROMACSExporter, SoluteGROMACSExporter, CustomMoleculeGROMACSExporter
from quickice.gui.help_dialog import QuickReferenceDialog
from quickice.gui.interface_panel import InterfacePanel
from quickice.gui.hydrate_panel import HydratePanel
from quickice.gui.hydrate_worker import HydrateWorker
from quickice.gui.hydrate_renderer import render_hydrate_structure
from quickice.gui.hydrate_export import HydrateGROMACSExporter
from quickice.gui.ion_panel import IonPanel
from quickice.gui.ion_renderer import render_ion_structure  # Used for export if needed
from quickice.gui.solute_renderer import create_solute_actor
from quickice.structure_generation.ion_inserter import IonInserter, insert_ions
from quickice.phase_mapping.lookup import PHASE_METADATA
from quickice.gui.constants import TabIndex
from quickice.gui.solute_panel import SolutePanel
from quickice.gui.custom_molecule_panel import CustomMoleculePanel


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
        self._interface_gromacs_exporter = InterfaceGROMACSExporter(self)
        self._ion_gromacs_exporter = IonGROMACSExporter(self)
        
        # Store current generation result for export
        self._current_result = None
        self._current_T = 0.0
        self._current_P = 0.0
        
        # Store current interface result for export
        self._current_interface_result = None
        
        # Store current hydrate configuration for export
        self._current_hydrate_config = None
        self._current_hydrate_result = None
        
        # Hydrate GROMACS exporter
        self._hydrate_gromacs_exporter = HydrateGROMACSExporter(self)
        
        # Solute GROMACS exporter (new in Phase 33)
        self._solute_gromacs_exporter = SoluteGROMACSExporter(self)
        
        # Custom Molecule GROMACS exporter (new in Phase 34)
        self._custom_molecule_gromacs_exporter = CustomMoleculeGROMACSExporter(self)
        
        # Store current ion structure for export (Issue 1)
        self._current_ion_result = None
        
        # Store current ion actors for visibility toggling
        self._ion_actors: list = []
        
        # Store current solute structure for export
        self._current_solute_result = None
        
        # Store current custom molecule result for export (Phase 34)
        self._current_custom_molecule_result = None
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        
        # Create menu bar (after shortcuts so it appears in proper order)
        self._create_menu_bar()
    
    def _setup_ui(self):
        """Setup UI components with two-tab layout.
        
        Ice Generation tab (existing functionality)
        Interface Construction tab (new in v4.0)
        """
        # Current tab structure (v4.5 Phase 34.3):
        # Tab 0 (TabIndex.ICE): Ice Generation
        # Tab 1 (TabIndex.HYDRATE): Hydrate Generation
        # Tab 2 (TabIndex.INTERFACE): Interface Construction
        # Tab 3 (TabIndex.CUSTOM): Custom Molecule (Phase 34)
        # Tab 4 (TabIndex.SOLUTE): Solute Insertion (Phase 33)
        # Tab 5 (TabIndex.ION): Ion Insertion (Phase 34)
        
        # Cross-tab data flows (v4.0):
        # Ice Generation → Interface Construction (ice candidates)
        # Hydrate Generation → Interface Construction (hydrate structure as source)
        # Interface Construction → Ion Insertion (interface structure for ions)
        #
        # Future data flows (v4.5):
        # Interface Construction → Solute Insertion (liquid region for solutes)
        # Interface Construction → Custom Molecule (liquid region for custom)
        # Custom Molecule → Ion Insertion (custom molecules + ions)
        
        # Note: Tab reordering (ARCH-05b) happens in Phase 35, not Phase 32.
        # Phase 32 prepares infrastructure (TabIndex constants for current positions, refactoring).
        # Ion tab stays at position 3 during Phase 32, moves to position 5
        # when Solute/Custom tabs are added in Phases 33-35.
        
        # Create tab widget as central container
        self.tab_widget = QTabWidget()
        
        # === Ice Generation tab ===
        # Wrap existing content in a QWidget for Ice Generation tab
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
        
        # Add splitter to Ice Generation tab layout
        tab1_layout.addWidget(splitter)
        
        # === Interface Construction tab ===
        self.interface_panel = InterfacePanel()
        
        # === Hydrate Generation tab (new in v4.0) ===
        self.hydrate_panel = HydratePanel()
        
        # === Solute Insertion tab (new in v4.5 Phase 33) ===
        self.solute_panel = SolutePanel()
        
        # === Custom Molecule tab (new in v4.5 Phase 34) ===
        self.custom_molecule_panel = CustomMoleculePanel()
        
        # === Ion Insertion tab (new in v4.0) ===
        self.ion_panel = IonPanel()
        
        # Add tabs to tab widget (order: Ice → Hydrate → Interface → Custom → Solute → Ion)
        self.tab_widget.addTab(tab1_widget, "Ice Generation")
        self.tab_widget.addTab(self.hydrate_panel, "Hydrate Generation")
        self.tab_widget.addTab(self.interface_panel, "Interface Construction")
        self.tab_widget.addTab(self.custom_molecule_panel, "Custom Molecule")  # Tab 3 (SWAPPED)
        self.tab_widget.addTab(self.solute_panel, "Solute Insertion")  # Tab 4 (SWAPPED)
        self.tab_widget.addTab(self.ion_panel, "Ion Insertion")
        
        # Set Ice Generation tab as default on startup
        self.tab_widget.setCurrentIndex(TabIndex.ICE)
        
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
        
        # Interface Construction tab connections
        self.interface_panel.refresh_requested.connect(self._on_refresh_candidates)
        
        # Interface Construction tab generation connections
        self.interface_panel.generate_requested.connect(self._on_interface_generate)

        # Interface Construction tab hydrate source - when user selects hydrate in Interface Construction tab
        self.interface_panel.generate_hydrate_requested.connect(self._on_interface_hydrate_generate)
        
        # Hydrate Generation tab connections (new in v4.0)
        self.hydrate_panel.configuration_changed.connect(self._on_hydrate_config_changed)
        self.hydrate_panel.generate_requested.connect(self._on_hydrate_generate_clicked)
        
        # Ion Insertion tab connections (new in v4.0)
        self.ion_panel.configuration_changed.connect(self._on_ion_config_changed)
        self.ion_panel.insert_requested.connect(self._on_insert_ions)
        
        # Solute Insertion tab connections (new in v4.5 Phase 33)
        self.solute_panel.insert_requested.connect(self._on_insert_solutes)
        self.solute_panel.configuration_changed.connect(self._on_solute_config_changed)
        
        # Custom Molecule tab connections (new in v4.5 Phase 34)
        self.custom_molecule_panel.generate_requested.connect(self._on_custom_generate_clicked)
        self.custom_molecule_panel.files_uploaded.connect(self._on_custom_files_uploaded)
        self.custom_molecule_panel.preview_requested.connect(self._on_custom_molecule_preview_requested)
        self.custom_molecule_panel.preview_cleared.connect(self._on_custom_molecule_preview_cleared)
        self.custom_molecule_panel.clear_previous_results.connect(self._on_clear_custom_molecule_results)
        
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
        
        # Unified Export action (Ctrl+S - Qt standard "Save" action)
        # Export from currently active tab for GROMACS
        export_current_action = file_menu.addAction("Export Current Tab for GROMACS...")
        export_current_action.setShortcut("Ctrl+S")
        export_current_action.setToolTip("Export current tab for GROMACS (Ctrl+S)")
        export_current_action.triggered.connect(self._on_export_current_tab)
        
        # Save PDB from Left Viewer action (moved to Ctrl+Alt+P)
        save_pdb_left_action = file_menu.addAction("Save PDB (Left Viewer)...")
        save_pdb_left_action.setShortcut("Ctrl+Alt+P")
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
        
        # Separator before Export As submenu
        file_menu.addSeparator()
        
        # Export As submenu for tab-specific exports
        export_as_menu = file_menu.addMenu("Export As...")
        
        # Export Ice for GROMACS
        export_ice_action = export_as_menu.addAction("Export Ice...")
        export_ice_action.setShortcut("Ctrl+G")
        export_ice_action.triggered.connect(self._on_export_gromacs)
        
        # Export Hydrate for GROMACS (Ctrl+H - changed from Ctrl+E)
        export_hydrate_action = export_as_menu.addAction("Export Hydrate...")
        export_hydrate_action.setShortcut("Ctrl+H")
        export_hydrate_action.triggered.connect(self._on_export_hydrate_gromacs)
        
        # Export Interface for GROMACS
        export_interface_action = export_as_menu.addAction("Export Interface...")
        export_interface_action.setShortcut("Ctrl+I")
        export_interface_action.triggered.connect(self._on_export_interface_gromacs)
        
        # Export Solute for GROMACS
        export_solute_action = export_as_menu.addAction("Export Solute...")
        export_solute_action.setShortcut("Ctrl+L")
        export_solute_action.triggered.connect(self._on_export_solute_gromacs)
        
        # Export Custom Molecule for GROMACS
        self.export_custom_action = export_as_menu.addAction("Export Custom Molecule...")
        self.export_custom_action.setShortcut("Ctrl+M")
        self.export_custom_action.triggered.connect(self._on_export_custom_molecule_gromacs)
        
        # Export Ion for GROMACS
        export_ion_action = export_as_menu.addAction("Export Ion...")
        export_ion_action.setShortcut("Ctrl+J")
        export_ion_action.triggered.connect(self._on_export_ion_gromacs)
        
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
            
            # Update Interface Construction tab dropdown with candidates
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
        
        # Update density displays in InfoPanel (both ice and water)
        self.info_panel.update_ice_density(self._current_T, self._current_P)
        self.info_panel.update_water_density(self._current_T, self._current_P)
    
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
        """Refresh candidates in Interface Construction tab from Ice Generation tab's current candidates."""
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
    
    # === Interface Generation Handlers (Interface Construction tab) ===
    
    @Slot(int)
    def _on_interface_generate(self, candidate_index: int):
        """Handle Generate Interface button click from Interface Construction tab.
        
        Args:
            candidate_index: Index of selected candidate in ranked candidates list
        """
        from quickice.structure_generation.types import InterfaceConfig
        
        # Get the ranked candidates result
        ranking_result = self._viewmodel.get_last_ranking_result()
        if not ranking_result or not hasattr(ranking_result, 'ranked_candidates'):
            self.interface_panel.append_log("No candidates available. Generate ice in Ice Generation tab first.")
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
        
        # Show transformation status if candidate was transformed
        if candidate.metadata.get("transformation_status") == "transformed":
            multiplier = candidate.metadata.get("transformation_multiplier", "?")
            message = candidate.metadata.get("transformation_message", "Cell transformed")
            self.interface_panel.append_log(f"  Transformation: {message} ({multiplier}x multiplier)")
        
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

        # Update ion panel with liquid volume for ion count calculation
        # Volume = water_nmolecules * 0.0299 nm³ per molecule (TIP4P water volume)
        liquid_vol = result.water_nmolecules * 0.0299
        self.ion_panel.set_liquid_volume(liquid_vol)
        self.ion_panel.set_interface_available(True)
        
        # Update solute panel with liquid volume for solute count calculation
        self.solute_panel.set_liquid_volume(liquid_vol)
        self.solute_panel.set_interface_available(True)
        
        # Update custom molecule panel with interface structure for validation
        if hasattr(self, 'custom_molecule_panel'):
            self.custom_molecule_panel.set_interface_structure(result)

        # Display structure in 3D viewer (if VTK available)
        if self.interface_panel.is_vtk_available():
            # Always render the generated interface result (ice + water)
            # The interface was generated from hydrate (hydrate.to_candidate() -> assemble_piece)
            # which correctly combines hydrate framework with water layer
            self.interface_panel._interface_viewer.set_interface_structure(result)
            self.interface_panel.hide_placeholder()
        else:
            # VTK not available - show message in log
            self.interface_panel.append_log(
                "3D viewer unavailable in remote environment. "
                "Clone to local machine for full visualization."
            )
    
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
    def _on_interface_hydrate_generate(self):
        """Handle generate when Source=hydrate in Interface Construction tab.

        Uses the last generated hydrate from Hydrate Generation tab to create interface.
        Treats hydrate as template/seed for ice-water interface (same logic as ice candidate).
        """
        from quickice.structure_generation.types import InterfaceConfig
        
        # Check if we have a hydrate from Hydrate Generation tab
        hydrate = self._current_hydrate_result

        if hydrate is None:
            QMessageBox.warning(
                self,
                "No Hydrate",
                "No hydrate structure available.\n\n"
                "Please:\n"
                "1. Go to Hydrate Generation tab\n"
                "2. Generate a hydrate structure\n"
                "3. Click 'Use in Interface →' or return here and generate"
            )
            return

        # Convert hydrate to candidate (same as ice candidate for interface generation)
        try:
            candidate = hydrate.to_candidate()
        except ValueError as e:
            QMessageBox.warning(
                self,
                "Conversion Error",
                f"Cannot convert hydrate to interface template:\n\n{str(e)}"
            )
            return

        # Get configuration from interface panel (set_from_hydrate already pre-populated the values)
        config_dict = self.interface_panel.get_configuration()
        config = InterfaceConfig.from_dict(config_dict)

        # Log the generation start
        self.interface_panel.progress_panel.reset()
        self.interface_panel.progress_panel.set_generating()
        self.interface_panel.clear_log()
        self.interface_panel.append_log(f"Starting {config.mode} interface generation...")
        self.interface_panel.append_log(f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm")
        self.interface_panel.append_log(f"  Template: Hydrate ({hydrate.water_count} water molecules)")
        
        # Add hydrate lattice info if available
        if hasattr(hydrate, 'lattice_info') and hydrate.lattice_info:
            self.interface_panel.append_log(f"  Lattice: {hydrate.lattice_info.description}")

        # Start interface generation (same flow as ice candidate)
        self._viewmodel.start_interface_generation(candidate, config)

    @Slot()
    def _on_interface_generation_cancelled(self):
        """Handle interface generation cancelled."""
        self.interface_panel.progress_panel.set_cancelled()
        self.interface_panel.set_generating(False)
    
    @Slot(bool)
    def _on_interface_ui_enabled_changed(self, enabled: bool):
        """Handle Interface Construction tab UI enabled/disabled state change."""
        self.interface_panel.set_generating(not enabled)
    
    @Slot()
    def _on_hydrate_config_changed(self):
        """Handle hydrate configuration change."""
        self._current_hydrate_config = self.hydrate_panel.get_configuration()
    
    @Slot()
    def _on_hydrate_generate_clicked(self):
        """Handle hydrate generation button click."""
        # Get configuration from panel and STORE IT (for export)
        config = self.hydrate_panel.get_configuration()
        self._current_hydrate_config = config
        
        # Clear previous log and show start message
        self.hydrate_panel.clear_log()
        self.hydrate_panel.append_log(f"Starting {config.lattice_type} hydrate generation...")
        
        # Disable generate button during generation
        self.hydrate_panel.generate_button.setEnabled(False)
        
        # Create and configure worker
        self._hydrate_worker = HydrateWorker(config)
        
        # Connect signals
        self._hydrate_worker.progress_updated.connect(self._on_hydrate_progress)
        self._hydrate_worker.generation_complete.connect(self._on_hydrate_generation_complete)
        self._hydrate_worker.generation_error.connect(self._on_hydrate_generation_error)
        
        # Start generation in background thread
        self._hydrate_worker.start()
    
    def _on_hydrate_progress(self, message: str):
        """Handle hydrate generation progress update.
        
        Args:
            message: Progress message from worker
        """
        self.hydrate_panel.append_log(message)
    
    def _on_hydrate_generation_complete(self, result):
        """Handle hydrate generation complete.
        
        Args:
            result: HydrateStructure from generation
        """
        # Store result
        self._current_hydrate_result = result
        
        # Log completion info
        self.hydrate_panel.append_log(f"Generation complete!")
        self.hydrate_panel.append_log(f"Water molecules: {result.water_count}")
        self.hydrate_panel.append_log(f"Guest molecules: {result.guest_count}")
        
        # Log unit cell info
        if hasattr(result, 'lattice_info') and result.lattice_info:
            lattice_info = result.lattice_info
            self.hydrate_panel.append_log(f"Lattice: {lattice_info.description}")
            if hasattr(lattice_info, 'cage_types') and lattice_info.cage_types:
                self.hydrate_panel.append_log(f"Cage types: {', '.join(lattice_info.cage_types)}")
        
        # Display structure in viewer and enable "Use in Interface" button
        self.hydrate_panel.set_hydrate_structure(result)
        
        # Re-enable generate button
        self.hydrate_panel.generate_button.setEnabled(True)
    
    def _on_hydrate_generation_error(self, error_msg: str):
        """Handle hydrate generation error.
        
        Args:
            error_msg: Error message from worker
        """
        self.hydrate_panel.append_log(f"Error: {error_msg}")
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "Hydrate Generation Error",
            f"Failed to generate hydrate structure:\n\n{error_msg}",
            QMessageBox.StandardButton.Ok
        )
        
        # Re-enable generate button
        self.hydrate_panel.generate_button.setEnabled(True)
    
    def _on_ion_config_changed(self):
        """Handle ion configuration change."""
        config = self.ion_panel.get_configuration()
        self._current_ion_config = config
    
    @Slot()
    def _on_insert_ions(self):
        """Handle Insert Ions button click."""
        # Get configuration from ion_panel
        config = self.ion_panel.get_configuration()
        
        # Get the selected source from ion panel
        current_source = self.ion_panel.get_current_source()
        
        # Get the appropriate interface structure based on source
        interface = None
        source_description = ""
        
        if current_source == "Interface":
            # Use original interface structure
            interface = self._current_interface_result
            source_description = "interface structure"
            
            if interface is None:
                QMessageBox.warning(
                    self, "No Interface",
                    "Please generate an interface structure first in the Interface Construction tab."
                )
                return
                
        elif current_source == "Solute":
            # Solutes are now inserted into the interface, can be used as source for ion insertion
            if not hasattr(self, '_current_solute_result') or self._current_solute_result is None:
                QMessageBox.warning(
                    self, "No Solute Structure",
                    "Please generate solutes first in the Solute tab."
                )
                return
            
            solute_structure = self._current_solute_result
            interface = solute_structure.interface_structure
            source_description = "solute-modified interface structure"
            
            if interface is None:
                QMessageBox.warning(
                    self, "Invalid Solute Structure",
                    "Solute structure does not have an associated interface structure."
                )
                return
            
            # Add solute information to interface structure so ion_inserter can preserve it
            # This allows the IonStructure to carry solute information for export
            interface.solute_type = solute_structure.solute_type
            interface.solute_positions = solute_structure.positions
            interface.solute_atom_names = solute_structure.atom_names
            interface.solute_n_molecules = solute_structure.n_molecules
            interface.solute_molecule_indices = solute_structure.molecule_indices
            interface.solute_registry = solute_structure.registry
            
            # Custom molecule information is already preserved in interface_structure
            # by solute_inserter._remove_overlapping_water() when source is Custom Molecule
            # No need to re-extract from original custom_structure (would use wrong indices)
                
        elif current_source == "Custom Molecule":
            # Custom molecules now replace water, so can be used as source for ion insertion
            if not hasattr(self, '_current_custom_molecule_result') or self._current_custom_molecule_result is None:
                QMessageBox.warning(
                    self, "No Custom Molecule Structure",
                    "Please generate custom molecules first in the Custom Molecule tab."
                )
                return
            
            custom_structure = self._current_custom_molecule_result
            interface = custom_structure.interface_structure
            source_description = "custom molecule-modified interface structure"
            
            if interface is None:
                QMessageBox.warning(
                    self, "Invalid Custom Molecule Structure",
                    "Custom molecule structure does not have an associated interface structure."
                )
                return
            
            # Add custom molecule information to interface structure so ion_inserter can preserve it
            interface.custom_molecule_positions = custom_structure.positions[interface.ice_atom_count + interface.water_atom_count + interface.guest_atom_count:]
            interface.custom_molecule_atom_names = custom_structure.atom_names[interface.ice_atom_count + interface.water_atom_count + interface.guest_atom_count:]
            interface.custom_molecule_count = custom_structure.custom_molecule_count
            interface.custom_molecule_moleculetype = custom_structure.moleculetype_name
            interface.custom_gro_path = custom_structure.gro_path
            interface.custom_itp_path = custom_structure.itp_path
        
        # Log which source is being used
        self.ion_panel.append_log(f"Using {source_description} for ion insertion...")
        
        # Get liquid volume from interface panel (may be 0 if not set)
        liquid_volume = self.ion_panel.get_liquid_volume()
        
        # Extract concentration from config
        concentration = config.concentration_molar
        
        if concentration <= 0:
            QMessageBox.warning(
                self, "Invalid Concentration",
                "Please enter a valid concentration greater than 0 mol/L."
            )
            return
        
        # Pass None if liquid_volume is 0 (let insert_ions calculate from cell)
        volume_arg = None if liquid_volume <= 0 else liquid_volume

        # Call module-level insert_ions function directly
        ion_structure = insert_ions(
            interface,
            concentration,
            volume_arg
        )

        # Store for export (Issue 1)
        self._current_ion_result = ion_structure

        # Render in IonPanel viewer: first show interface (ice + water bonds),
        # then add ions (spheres) on top
        self.ion_panel.ion_viewer.set_interface_structure(interface)
        self.ion_panel.ion_viewer.set_ion_structure(ion_structure)

        # If source was Solute, also render the solute molecules
        if current_source == "Solute" and hasattr(self, '_current_solute_result'):
            # Clear any existing solute actors before adding new ones
            if hasattr(self.ion_panel.ion_viewer, '_clear_solute_actors'):
                self.ion_panel.ion_viewer._clear_solute_actors()
            
            solute_structure = self._current_solute_result
            solute_actor = create_solute_actor(
                solute_structure.positions,
                solute_structure.atom_names,
                solute_structure.cell,
                molecule_indices=solute_structure.molecule_indices
            )
            if solute_actor and self.ion_panel.ion_viewer.renderer is not None:
                self.ion_panel.ion_viewer.renderer.AddActor(solute_actor)
                self.ion_panel.ion_viewer._solute_actors.append(solute_actor)
            
            # If the solute was derived from custom molecules, also render custom molecules
            if hasattr(self, '_current_custom_molecule_result') and self._current_custom_molecule_result is not None:
                custom_structure = self._current_custom_molecule_result
                if hasattr(self.ion_panel.ion_viewer, 'render_custom_molecules'):
                    self.ion_panel.ion_viewer.render_custom_molecules(custom_structure)

        # If source was Custom Molecule, also render the custom molecules
        if current_source == "Custom Molecule" and hasattr(self, '_current_custom_molecule_result'):
            custom_structure = self._current_custom_molecule_result
            if hasattr(self.ion_panel.ion_viewer, 'render_custom_molecules'):
                self.ion_panel.ion_viewer.render_custom_molecules(custom_structure)

        # Mark that ions have been inserted (for any future reference)
        self.ion_panel.hide_placeholder()

        # Log status to IonPanel log
        self.ion_panel.append_log(
            f"Ion insertion complete: {ion_structure.na_count} Na+, {ion_structure.cl_count} Cl-"
        )
    
    def _on_solute_config_changed(self):
        """Handle solute configuration change."""
        # Could update preview or validation here
        pass
    
    @Slot()
    def _on_insert_solutes(self):
        """Handle solute insertion request."""
        from quickice.structure_generation.solute_inserter import SoluteInserter

        # Get current source from panel
        current_source = self.solute_panel.get_current_source()

        # Get appropriate structure based on source
        if current_source == "Interface":
            # Use original interface structure
            if not hasattr(self, '_current_interface_result') or self._current_interface_result is None:
                self.solute_panel.log_message("Error: No interface structure available. Generate interface first.")
                return
            interface = self._current_interface_result
            custom_molecule_data = None  # No custom molecules

        elif current_source == "Custom Molecule":
            # Check that custom molecule structure exists
            if not hasattr(self, '_current_custom_molecule_result') or self._current_custom_molecule_result is None:
                self.solute_panel.log_message("Error: No custom molecule structure available. Generate custom molecules first.")
                return

            custom_structure = self._current_custom_molecule_result

            # Pass the full CustomMoleculeStructure to preserve custom molecule information
            # This allows the solute_inserter to preserve custom molecules through the workflow
            # interface_structure (ice + water) is stored in custom_structure.interface_structure
            interface = custom_structure

            if interface is None:
                self.solute_panel.log_message("Error: Custom molecule structure has no interface structure.")
                return

            # Prepare custom molecule data for GROMACS export (Phase 35)
            # Note: Not passed to SoluteInserter yet - will be used in Phase 35
            custom_molecule_data = {
                'gro_path': self.custom_molecule_panel.get_gro_path(),
                'itp_path': self.custom_molecule_panel.get_itp_path(),
                'residue_name': custom_structure.residue_name,
                'moleculetype_name': custom_structure.moleculetype_name
            }

        else:
            self.solute_panel.log_message(f"Error: Unknown source '{current_source}'")
            return

        # Get configuration from panel
        config = self.solute_panel.get_configuration()

        # Log start with source info
        self.solute_panel.log_message(f"Inserting {config.solute_type} solutes at {config.concentration_molar} M (source: {current_source})...")

        try:
            # Create inserter and insert solutes
            inserter = SoluteInserter(config)
            solute_structure = inserter.insert_solutes(interface, config)

            # Store result
            self._current_solute_result = solute_structure

            # Clear old solute actors from ion viewer to prevent overlap
            if hasattr(self.ion_panel.ion_viewer, '_clear_solute_actors'):
                self.ion_panel.ion_viewer._clear_solute_actors()

            # Pass result to IonPanel (Tab 5) for source selection
            # This enables the workflow: Interface → Solute → Ion
            self.ion_panel.set_solute_structure(solute_structure)

            # Calculate water molecules replaced
            # Handle both InterfaceStructure and CustomMoleculeStructure
            if hasattr(interface, 'water_nmolecules'):
                original_water_count = interface.water_nmolecules
            else:
                # CustomMoleculeStructure - get from its interface_structure
                original_water_count = interface.interface_structure.water_nmolecules
            modified_water_count = solute_structure.interface_structure.water_nmolecules
            water_replaced = original_water_count - modified_water_count

            # Render in viewer
            self.solute_panel.solute_viewer.render_solute(solute_structure)

            # If source was Custom Molecule, also render the custom molecules
            # Use the modified interface structure from solute_structure which has
            # the correct custom molecule positions after water removal
            if current_source == "Custom Molecule" and hasattr(self, '_current_custom_molecule_result'):
                # Pass the modified interface structure, not the original CustomMoleculeStructure
                # The modified structure has custom molecule positions updated after solute insertion
                if hasattr(self.solute_panel.solute_viewer, 'render_custom_molecules'):
                    self.solute_panel.solute_viewer.render_custom_molecules(
                        solute_structure.interface_structure
                    )

            # Hide placeholder
            self.solute_panel.hide_placeholder()

            # Log success with water replacement count
            self.solute_panel.log_message(
                f"Success: Inserted {solute_structure.n_molecules} {config.solute_type} molecules"
            )
            if water_replaced > 0:
                self.solute_panel.log_message(
                    f"Replaced {water_replaced} overlapping liquid water molecules"
                )

        except Exception as e:
            self.solute_panel.log_message(f"Error: {e}")
            logger.error(f"Solute insertion failed: {e}", exc_info=True)
    
    @Slot()
    def _on_custom_generate_clicked(self):
        """Handle custom molecule generate button click."""
        from quickice.gui.custom_molecule_worker import CustomMoleculeWorker
        from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeConfig
        from PySide6.QtWidgets import QMessageBox
        
        # Check for previous insertion - ask user what to do
        if self.custom_molecule_panel._has_previous_insertion:
            reply = QMessageBox.question(
                self,
                "Previous Custom Molecules Found",
                "You have previously inserted custom molecules.\n\n"
                "Do you want to start fresh (clear previous molecules) or cancel?\n\n"
                "• 'Yes' = Start fresh (previous molecules will be cleared)\n"
                "• 'No' = Cancel (keep previous molecules)",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                # User chose to cancel
                self.custom_molecule_panel.log_message("Generation cancelled - keeping previous custom molecules")
                return
            
            # User chose to start fresh - clear previous results
            self._on_clear_custom_molecule_results()
            self.custom_molecule_panel._has_previous_insertion = False
            self.custom_molecule_panel.positions_added.clear()
            self.custom_molecule_panel.position_count_label.setText("Positions added: 0")
            self.custom_molecule_panel.log_message("Cleared previous custom molecules - starting fresh")
        
        # Validate that interface result exists (need ice+water structure)
        if not hasattr(self, '_current_interface_result') or self._current_interface_result is None:
            self.custom_molecule_panel.log_message("Error: No interface structure available. Generate interface first.")
            return
        
        # Get configuration from panel
        config = self.custom_molecule_panel.get_configuration()
        
        if config is None:
            self.custom_molecule_panel.log_message("Error: Invalid configuration")
            return
        
        # Log start
        self.custom_molecule_panel.log_message("Starting custom molecule insertion...")
        
        # Disable generate button during processing (prevent multiple clicks)
        self.custom_molecule_panel.generate_button.setEnabled(False)
        
        try:
            # Create worker and store as instance variable to prevent garbage collection
            self._custom_worker = CustomMoleculeWorker(
                config,
                self._current_interface_result,
                self.custom_molecule_panel.get_gro_path(),
                self.custom_molecule_panel.get_itp_path()
            )

            # Create thread and move worker to it
            self._custom_worker_thread = QThread()
            self._custom_worker.moveToThread(self._custom_worker_thread)

            # Connect signals
            self._custom_worker_thread.started.connect(self._custom_worker.run)
            self._custom_worker.finished.connect(self._custom_worker_thread.quit)
            self._custom_worker.finished.connect(self._on_custom_finished)
            self._custom_worker.error.connect(lambda msg: self.custom_molecule_panel.log_message(f"Error: {msg}"))
            self._custom_worker.status.connect(lambda msg: self.custom_molecule_panel.log_message(msg))
            # Note: progress signal emits int (percentage), convert to string for display
            self._custom_worker.progress.connect(lambda pct: self.custom_molecule_panel.log_message(f"Progress: {pct}%"))

            # Start
            self._custom_worker_thread.start()
            
        except Exception as e:
            # Re-enable button on error
            self.custom_molecule_panel.generate_button.setEnabled(True)
            self.custom_molecule_panel.log_message(f"Error: {e}")
            logger.error(f"Custom molecule insertion failed: {e}", exc_info=True)
    
    @Slot(object)
    def _on_custom_finished(self, result):
        """Handle successful custom molecule insertion.
        
        Args:
            result: CustomMoleculeStructure with complete system data
        """
        try:
            # Store result
            self._current_custom_molecule_result = result

            # Update 3D viewer with complete system
            self.custom_molecule_panel.custom_viewer.update_structure(result)

            # Hide placeholder
            self.custom_molecule_panel.hide_placeholder()

            # Enable export action
            self.export_custom_action.setEnabled(True)
            
            # Mark insertion as complete (for mode switching behavior)
            self.custom_molecule_panel.mark_insertion_complete()

            # Pass result to SolutePanel (Tab 4) for source selection
            self.solute_panel.set_custom_molecule_structure(result)

            # Update solute panel with liquid volume for solute count calculation
            # Calculate from water_atom_count (TIP4P has 4 atoms per molecule)
            # Volume = water_nmolecules * 0.0299 nm³ per molecule
            # CustomMoleculeStructure always has water_atom_count (required dataclass field)
            assert result.water_atom_count >= 0, f"Invalid water_atom_count: {result.water_atom_count}"
            
            if result.water_atom_count > 0:
                water_nmolecules = result.water_atom_count // 4
                liquid_vol = water_nmolecules * 0.0299
                self.solute_panel.set_liquid_volume(liquid_vol)
                logger.info(f"Updated solute panel liquid volume: {liquid_vol:.2f} nm³ from {water_nmolecules} water molecules")
            else:
                logger.warning(f"Cannot set liquid volume: water_atom_count={result.water_atom_count}")

            # Pass result to IonPanel (Tab 5) for source selection
            # This enables both workflow paths:
            # - Interface → Custom → Solute → Ion (with solutes)
            # - Interface → Custom → Ion (direct, skip solutes)
            self.ion_panel.set_custom_molecule_structure(result)

            # Update ion panel with liquid volume for ion count calculation
            if result.water_atom_count > 0:
                self.ion_panel.set_liquid_volume(liquid_vol)

            # Calculate water molecules replaced
            logger.debug(f"[Water Count Debug] Starting water replacement calculation...")
            logger.debug(f"[Water Count Debug] hasattr(_current_interface_result): {hasattr(self, '_current_interface_result')}")
            if hasattr(self, '_current_interface_result'):
                logger.debug(f"[Water Count Debug] _current_interface_result is None: {self._current_interface_result is None}")
            
            if hasattr(self, '_current_interface_result') and self._current_interface_result is not None:
                original_water_count = self._current_interface_result.water_nmolecules
                logger.debug(f"[Water Count Debug] original_water_count: {original_water_count}")
                # CustomMoleculeStructure.interface_structure is a typed dataclass field (can be None)
                if result.interface_structure is not None:
                    modified_water_count = result.interface_structure.water_nmolecules
                    logger.debug(f"[Water Count Debug] modified_water_count: {modified_water_count}")
                else:
                    logger.warning("[Water Count Debug] result.interface_structure is None, using original count as fallback")
                    modified_water_count = original_water_count  # Fallback to avoid negative count
                water_replaced = original_water_count - modified_water_count
                logger.debug(f"[Water Count Debug] water_replaced calculation: {original_water_count} - {modified_water_count} = {water_replaced}")
            else:
                water_replaced = 0
                logger.warning(f"[Water Count Debug] _current_interface_result not available, setting water_replaced=0")

            # Log success with complete system info
            logger.debug(f"[Water Count Debug] Logging success message...")
            self.custom_molecule_panel.log_message(
                f"Custom molecule insertion complete: {result.custom_molecule_count} molecules, "
                f"{len(result.positions)} total atoms (ice+water+custom)"
            )

            # Log water replacement count if any water was replaced
            logger.debug(f"[Water Count Debug] Checking if water_replaced > 0: {water_replaced > 0}")
            if water_replaced > 0:
                logger.debug(f"[Water Count Debug] Logging water replacement message: {water_replaced} waters")
                self.custom_molecule_panel.log_message(
                    f"Replaced {water_replaced} overlapping liquid water molecules"
                )
            else:
                logger.debug(f"[Water Count Debug] No water replacement message (water_replaced={water_replaced})")

        except Exception as e:
            # Log the error with full traceback
            logger.error(f"Failed to display custom molecule structure: {e}", exc_info=True)
            self.custom_molecule_panel.log_message(f"Error displaying structure: {e}")
            return

        finally:
            # Re-enable generate button (always runs, even on exception)
            if hasattr(self, 'custom_molecule_panel'):
                self.custom_molecule_panel.generate_button.setEnabled(True)
            
            # Clean up worker and thread (always runs, even on exception)
            if hasattr(self, '_custom_worker_thread'):
                self._custom_worker_thread.quit()
                self._custom_worker_thread.wait()
                del self._custom_worker_thread
            
            if hasattr(self, '_custom_worker'):
                del self._custom_worker
    
    @Slot(bool)
    def _on_custom_files_uploaded(self, valid: bool):
        """Handle custom molecule file upload validation."""
        # Enable/disable generate button based on validation
        if hasattr(self, 'custom_molecule_panel'):
            # The panel handles its own button state
            pass
    
    @Slot(tuple, tuple)
    def _on_custom_molecule_preview_requested(
        self, position: tuple[float, float, float], rotation: tuple[float, float, float]
    ) -> None:
        """Handle preview request from CustomMoleculePanel.
        
        Transforms position/rotation into molecule positions and renders
        preview in 3D viewer.
        
        Args:
            position: (x, y, z) center-of-mass position in nm
            rotation: (alpha, beta, gamma) Euler angles in degrees
        """
        if not hasattr(self, 'custom_molecule_panel'):
            return
        
        panel = self.custom_molecule_panel
        
        # Check files are loaded
        if not panel.gro_path or not panel.itp_path:
            logger.warning("Cannot preview: no custom molecule files loaded")
            return
        
        # Get current interface structure (the one we validated against)
        if panel._interface_structure is None:
            logger.warning("Cannot preview: no interface structure loaded")
            return
        
        structure = panel._interface_structure
        
        try:
            # Load custom molecule template using parse_gro_file
            from quickice.structure_generation.gro_parser import parse_gro_file
            
            template_positions, atom_names, cell = parse_gro_file(panel.gro_path)
            
            # Rotate template
            center = template_positions.mean(axis=0)
            centered = template_positions - center
            
            # Euler angles to rotation matrix (match CustomMoleculeInserter logic)
            alpha, beta, gamma = rotation
            alpha_rad = np.radians(alpha)
            beta_rad = np.radians(beta)
            gamma_rad = np.radians(gamma)
            
            ca, sa = np.cos(alpha_rad), np.sin(alpha_rad)
            cb, sb = np.cos(beta_rad), np.sin(beta_rad)
            cg, sg = np.cos(gamma_rad), np.sin(gamma_rad)
            
            rot_matrix = np.array([
                [cg*cb, cg*sb*sa - sg*ca, cg*sb*ca + sg*sa],
                [sg*cb, sg*sb*sa + cg*ca, sg*sb*ca - cg*sa],
                [-sb, cb*sa, cb*ca]
            ])
            
            rotated = centered @ rot_matrix.T
            placed_positions = rotated + np.array(position)
            
            # Show preview in viewer
            if hasattr(self.custom_molecule_panel, 'custom_viewer'):
                # Load interface structure first (to show context)
                self.custom_molecule_panel.custom_viewer.load_interface_structure(structure)
                
                # Then show preview molecule overlaid
                self.custom_molecule_panel.custom_viewer.show_preview(
                    placed_positions, atom_names, cell
                )
                self.custom_molecule_panel.log_message(
                    f"Preview: {len(placed_positions)} atoms at "
                    f"({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})"
                )
            else:
                logger.warning("Custom molecule viewer not available")
                
        except Exception as e:
            logger.error(f"Failed to create preview: {e}")
            self.custom_molecule_panel.log_message(f"Preview error: {e}")
    
    @Slot()
    def _on_custom_molecule_preview_cleared(self) -> None:
        """Handle preview clear request from CustomMoleculePanel."""
        if hasattr(self.custom_molecule_panel, 'custom_viewer'):
            self.custom_molecule_panel.custom_viewer.clear_preview()
            self.custom_molecule_panel.log_message("Preview cleared")
    
    @Slot()
    def _on_clear_custom_molecule_results(self) -> None:
        """Handle clear previous custom molecule results request.
        
        Called when user chooses to start fresh when switching placement modes.
        Clears the stored custom molecule result and resets the viewer.
        """
        try:
            # Clear stored result
            if hasattr(self, '_current_custom_molecule_result'):
                self._current_custom_molecule_result = None
            
            # Clear viewer and reload interface structure
            if hasattr(self.custom_molecule_panel, 'custom_viewer'):
                self.custom_molecule_panel.custom_viewer.clear()
                
                # Reload interface structure (ice + water) if available
                if hasattr(self, '_current_interface_result') and self._current_interface_result is not None:
                    self.custom_molecule_panel.custom_viewer.load_interface_structure(
                        self._current_interface_result
                    )
            
            # Disable export action
            if hasattr(self, 'export_custom_action'):
                self.export_custom_action.setEnabled(False)
            
            # Clear results from downstream panels
            if hasattr(self, 'solute_panel'):
                # Clear custom molecule structure from solute panel
                if hasattr(self.solute_panel, '_custom_molecule_structure'):
                    self.solute_panel._custom_molecule_structure = None
            
            if hasattr(self, 'ion_panel'):
                # Clear custom molecule structure from ion panel
                if hasattr(self.ion_panel, '_custom_molecule_structure'):
                    self.ion_panel._custom_molecule_structure = None
            
            logger.info("Cleared previous custom molecule results")
            
        except Exception as e:
            logger.error(f"Error clearing custom molecule results: {e}")
            if hasattr(self, 'custom_molecule_panel') and self.custom_molecule_panel:
                self.custom_molecule_panel.log_message(f"Warning: Could not clear previous results: {e}")
    
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
        # No explicit state saving needed - widgets maintain their state
        
        # Update density displays when switching to Ice Generation tab
        if index == TabIndex.ICE:
            # Only update if we have valid current T/P values
            if self._current_T > 0 and self._current_P > 0:
                self.info_panel.update_ice_density(self._current_T, self._current_P)
                self.info_panel.update_water_density(self._current_T, self._current_P)
    
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
        except (ValueError, TypeError) as e:
            logger.info(f"Invalid user input for temperature/pressure: {e}")
    
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
    def _on_export_current_tab(self):
        """Handle unified Ctrl+S export action.
        
        Exports from currently active tab for GROMACS.
        Per plan 35-01: Unified export shortcut for all tabs.
        
        Tab routing:
            - TabIndex.ICE → Ice GROMACS export
            - TabIndex.HYDRATE → Hydrate GROMACS export
            - TabIndex.INTERFACE → Interface GROMACS export
            - TabIndex.SOLUTE → Solute GROMACS export
            - TabIndex.CUSTOM → Custom Molecule GROMACS export
            - TabIndex.ION → Ion GROMACS export
        """
        current_idx = self.tab_widget.currentIndex()
        
        if current_idx == TabIndex.ICE:
            self._on_export_gromacs()
        elif current_idx == TabIndex.HYDRATE:
            self._on_export_hydrate_gromacs()
        elif current_idx == TabIndex.INTERFACE:
            self._on_export_interface_gromacs()
        elif current_idx == TabIndex.SOLUTE:
            self._on_export_solute_gromacs()
        elif current_idx == TabIndex.CUSTOM:
            self._on_export_custom_molecule_gromacs()
        elif current_idx == TabIndex.ION:
            self._on_export_ion_gromacs()
        else:
            logger.warning(f"Unknown tab index: {current_idx}")
            QMessageBox.warning(
                self,
                "Unknown Tab",
                f"Cannot export from tab index {current_idx}."
            )
    
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
    def _on_export_interface_gromacs(self):
        """Handle Export Interface for GROMACS menu action (Interface Construction tab)."""
        if not self._current_interface_result:
            QMessageBox.warning(self, "No Interface", "Generate an interface structure first.")
            return
        
        iface = self._current_interface_result
        success = self._interface_gromacs_exporter.export_interface_gromacs(iface)
        
        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"GROMACS files exported successfully.\n\n"
                f"Water model: TIP4P-ICE\n"
                f"(Abascal et al. 2005, DOI: 10.1063/1.1931662)\n\n"
                f"Ice molecules: {iface.ice_nmolecules}\n"
                f"Water molecules: {iface.water_nmolecules}\n"
                f"Total: {iface.ice_nmolecules + iface.water_nmolecules}\n\n"
                f"Files generated:\n"
                f"• interface_{iface.mode}.gro\n"
                f"• interface_{iface.mode}.top\n"
                f"• interface_{iface.mode}.itp"
            )
    
    @Slot()
    def _on_export_hydrate_gromacs(self):
        """Handle Export Hydrate for GROMACS menu action (Hydrate tab).
        
        Per plan 31-05: Exports current hydrate structure to GROMACS format.
        """
        if not self._current_hydrate_result:
            QMessageBox.warning(
                self,
                "No Hydrate",
                "Generate a hydrate structure first in the Hydrate Generation tab."
            )
            return
        
        config = self._current_hydrate_config
        if not config:
            QMessageBox.warning(
                self,
                "No Configuration",
                "Configure a hydrate structure first in the Hydrate Generation tab."
            )
            return
        
        structure = self._current_hydrate_result
        success = self._hydrate_gromacs_exporter.export_hydrate(structure, config)
        
        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Hydrate structure exported successfully.\n\n"
                f"Files: hydrate_{config.lattice_type}_{config.guest_type}.gro/.top\n"
                f"Water: {structure.water_count} molecules\n"
                f"Guests: {structure.guest_count} {config.guest_type}"
            )
    
    @Slot()
    def _on_export_ion_gromacs(self):
        """Handle Export Ions for GROMACS menu action (Ion tab).
        
        Per Issue 1: Exports ion structure to GROMACS format.
        Exports: ice + water + ions (Na+, Cl-).
        """
        # Check if ions have been inserted
        if not hasattr(self, '_current_ion_result') or self._current_ion_result is None:
            QMessageBox.warning(
                self,
                "No Ions",
                "Insert ions first in the Ion Insertion tab."
            )
            return
        
        ion_structure = self._current_ion_result
        success = self._ion_gromacs_exporter.export_ion_gromacs(ion_structure)
        
        if success:
            # Count water molecules
            water_count = sum(1 for m in ion_structure.molecule_index if m.mol_type == "water")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Ion structure exported successfully.\n\n"
                f"Files: ions_{ion_structure.na_count}na_{ion_structure.cl_count}cl.gro/.top\n"
                f"Water: {water_count} molecules\n"
                f"Na+: {ion_structure.na_count} ions\n"
                f"Cl-: {ion_structure.cl_count} ions"
            )
    
    @Slot()
    def _on_export_solute_gromacs(self):
        """Handle Export Solutes for GROMACS menu action (Solute tab - Phase 33).
        
        Exports: ice + water + solutes (CH4 or THF).
        """
        # Check if solutes have been inserted
        if not hasattr(self, '_current_solute_result') or self._current_solute_result is None:
            QMessageBox.warning(
                self,
                "No Solutes",
                "Insert solutes first in the Solute Insertion tab."
            )
            return
        
        solute_structure = self._current_solute_result
        success = self._solute_gromacs_exporter.export_solute_gromacs(solute_structure)
        
        if success:
            # Count water molecules from interface
            interface = solute_structure.interface_structure
            water_count = interface.water_nmolecules if interface else 0
            ice_count = interface.ice_nmolecules if interface else 0
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Solute structure exported successfully.\n\n"
                f"Files: solute_{solute_structure.solute_type.lower()}_{solute_structure.n_molecules}molecules.gro/.top\n"
                f"Ice: {ice_count} molecules\n"
                f"Water: {water_count} molecules\n"
                f"{solute_structure.solute_type}: {solute_structure.n_molecules} molecules"
            )
    
    def _on_export_custom_molecule_gromacs(self):
        """Handle Export Custom Molecules for GROMACS menu action (Custom Molecule tab - Phase 34).
        
        Exports: custom molecules with bundled .itp file.
        """
        # Check if custom molecules have been inserted
        if not hasattr(self, '_current_custom_molecule_result') or self._current_custom_molecule_result is None:
            QMessageBox.warning(
                self,
                "No Custom Molecules",
                "Insert custom molecules first in the Custom Molecule tab."
            )
            return
        
        custom_structure = self._current_custom_molecule_result
        success = self._custom_molecule_gromacs_exporter.export_custom_molecule_gromacs(custom_structure)
        
        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Custom molecule structure exported successfully.\n\n"
                f"Files: custom_{custom_structure.moleculetype_name}_{custom_structure.custom_molecule_count}molecules.gro/.top\n"
                f"Molecule type: {custom_structure.moleculetype_name}\n"
                f"Molecules: {custom_structure.custom_molecule_count}\n"
                f"ITP bundled: {custom_structure.itp_path.name}"
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
            meta = PHASE_METADATA.get(phase_id_full, {})
            phase_name = meta.get("name", phase_id)
            
            # Ice Ih: use IAPWS R10-06(2009) temperature-dependent density
            if phase_id_full == "ice_ih":
                from quickice.phase_mapping.ice_ih_density import ice_ih_density_gcm3
                density = f"{ice_ih_density_gcm3(T, P):.4f}"
            elif phase_id_full == "liquid":
                from quickice.phase_mapping.water_density import water_density_gcm3
                density = f"{water_density_gcm3(T, P):.4f}"
            else:
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
        "Liquid": "liquid",
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


def _configure_opengl_for_remote():
    """Configure OpenGL for remote X11 display.
    
    Fixes VTK segfault when running via SSH X11 forwarding.
    The NVIDIA GLX library crashes with indirect rendering (no direct rendering support).
    Mesa GLX handles indirect rendering correctly.
    
    This only applies when running remotely (DISPLAY set, no local GPU).
    """
    import os
    
    # Only apply fix for remote displays
    display = os.environ.get('DISPLAY', '')
    if not display:
        return  # No display, let Qt handle it
    
    # SSH X11 forwarding always goes through localhost:n.n or hostname:n.n
    # Local displays start with :0, :1, etc.
    # Simple heuristic: if DISPLAY contains a colon and doesn't start with :0-9 locally
    if display.startswith(':'):
        # Could be local or remote SSH -:0 style; assume local until proven otherwise
        return
    
    # For remote displays (localhost:12.0, etc.), force Mesa GLX
    os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'mesa'


def run_app():
    """Run the QuickIce GUI application.
    
    This is the entry point for the QuickIce GUI.
    Creates QApplication, MainWindow, and starts the event loop.
    
    Usage:
        from quickice.gui import run_app
        run_app()
    """
    # Configure OpenGL for remote displays before creating QApplication
    _configure_opengl_for_remote()
    
    import sys
    app = QApplication(sys.argv)
    
    # Apply global tooltip styling
    # Note: Qt QToolTip doesn't support max-width for text wrapping.
    # Tooltips with \n characters will wrap naturally.
    # Removed max-width which was causing truncation.
    app.setStyleSheet("""
        QToolTip {
            padding: 4px;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
