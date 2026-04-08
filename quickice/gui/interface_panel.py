"""Interface construction panel for QuickIce GUI v3.0.

This module provides the InterfacePanel class for the Interface Construction tab:
- Candidate selection dropdown for ice candidate selection
- Refresh button to sync candidates from Ice Generation tab
- Generate Interface button (Phase 18 placeholder)
- Progress panel for generation feedback
- Info panel for log output
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox
)
from PySide6.QtCore import Signal, Qt

from quickice.gui.view import ProgressPanel, InfoPanel


class InterfacePanel(QWidget):
    """Panel for interface construction workflow.
    
    Provides UI for:
    - Selecting ice candidate from dropdown
    - Refreshing candidates from Ice Generation tab
    - Generating interface structures (Phase 18 implementation)
    
    Signals:
        candidate_selected: Emitted when candidate dropdown selection changes
        refresh_requested: Emitted when refresh button is clicked
        generate_requested: Emitted when generate button is clicked with selected index
    """
    
    # Signals for communication with MainWindow
    candidate_selected = Signal(int)  # Emits selected candidate index
    refresh_requested = Signal()  # Emits when refresh button clicked
    generate_requested = Signal(int)  # Emits when generate clicked with selected index
    
    def __init__(self, parent=None):
        """Initialize the interface construction panel.
        
        Args:
            parent: Parent widget (MainWindow)
        """
        super().__init__(parent)
        self._candidates: list = []  # Store ranked candidates
        self._generating = False  # Track generation state
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Set up UI components with vertical layout.
        
        Layout structure:
        - Title label
        - Candidate selection row (label + dropdown)
        - Refresh button row
        - Generate button row
        - Progress panel
        - Info panel (collapsible)
        - Placeholder label (initially visible)
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Interface Construction")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        layout.addSpacing(15)
        
        # Candidate selection row
        candidate_row = QHBoxLayout()
        candidate_label = QLabel("Candidate:")
        self.candidate_dropdown = QComboBox()
        self.candidate_dropdown.setMinimumWidth(200)
        self.candidate_dropdown.setToolTip("Select an ice candidate for interface generation")
        self.candidate_dropdown.addItem("No candidates - generate ice first")
        self.candidate_dropdown.setEnabled(False)
        candidate_row.addWidget(candidate_label)
        candidate_row.addWidget(self.candidate_dropdown)
        candidate_row.addStretch()
        layout.addLayout(candidate_row)
        
        layout.addSpacing(10)
        
        # Refresh button row
        self.refresh_btn = QPushButton("Refresh candidates")
        self.refresh_btn.setToolTip("Sync candidates from Ice Generation tab")
        layout.addWidget(self.refresh_btn)
        
        layout.addSpacing(10)
        
        # Generate button row
        self.generate_btn = QPushButton("Generate Interface")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setToolTip("Generate ice candidates in Tab 1 first")
        layout.addWidget(self.generate_btn)
        
        layout.addSpacing(15)
        
        # Progress panel (reuse from view.py)
        self.progress_panel = ProgressPanel()
        layout.addWidget(self.progress_panel)
        
        layout.addSpacing(10)
        
        # Info panel (collapsible, reuse from view.py)
        self.info_panel = InfoPanel()
        layout.addWidget(self.info_panel)
        
        layout.addSpacing(10)
        
        # Placeholder label (shown initially, hidden after generation)
        self.placeholder_label = QLabel(
            "Select a candidate and click Generate Interface"
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "font-size: 14px; color: #666; background-color: #f0f0f0; "
            "padding: 30px; border: 1px solid #ccc; border-radius: 4px;"
        )
        layout.addWidget(self.placeholder_label, stretch=1)
        
        layout.addStretch()
    
    def _setup_connections(self):
        """Connect internal signals to slots."""
        # Dropdown selection change
        self.candidate_dropdown.currentIndexChanged.connect(self._on_candidate_changed)
        
        # Refresh button
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        
        # Generate button
        self.generate_btn.clicked.connect(self._on_generate_clicked)
    
    def _on_candidate_changed(self, index: int):
        """Handle candidate dropdown selection change.
        
        Args:
            index: Selected index in dropdown
        """
        if index >= 0 and self._candidates:
            self.candidate_selected.emit(index)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_requested.emit()
    
    def _on_generate_clicked(self):
        """Handle generate button click."""
        if self._candidates and self.candidate_dropdown.currentIndex() >= 0:
            self.generate_requested.emit(self.candidate_dropdown.currentIndex())
    
    def update_candidates(self, candidates: list) -> None:
        """Update candidate dropdown with new list.
        
        Args:
            candidates: List of RankedCandidate objects from Ice Generation tab
        """
        self._candidates = candidates
        
        # Block signals during update to prevent spurious emissions
        self.candidate_dropdown.blockSignals(True)
        self.candidate_dropdown.clear()
        
        if not candidates:
            # Empty state
            self.candidate_dropdown.addItem("No candidates - generate ice first")
            self.candidate_dropdown.setEnabled(False)
            self.generate_btn.setEnabled(False)
            self.generate_btn.setToolTip("Generate ice candidates in Tab 1 first")
        else:
            # Populate dropdown with ranked candidates
            self.candidate_dropdown.setEnabled(True)
            for rc in candidates:
                self.candidate_dropdown.addItem(
                    f"Rank {rc.rank}: {rc.candidate.phase_id}"
                )
            # Default to first candidate
            self.candidate_dropdown.setCurrentIndex(0)
            
            # Enable generate button
            self.generate_btn.setEnabled(True)
            self.generate_btn.setToolTip("Click to generate interface structure")
        
        self.candidate_dropdown.blockSignals(False)
    
    def set_generating(self, enabled: bool) -> None:
        """Toggle UI state during generation.
        
        Args:
            enabled: True if generation is active, False otherwise
        """
        self._generating = enabled
        
        # Disable controls during generation
        self.candidate_dropdown.setEnabled(not enabled)
        self.refresh_btn.setEnabled(not enabled)
        self.generate_btn.setEnabled(not enabled)
        
        if enabled:
            self.generate_btn.setText("Generating...")
            self.generate_btn.setToolTip("Generation in progress...")
        else:
            self.generate_btn.setText("Generate Interface")
            if self._candidates:
                self.generate_btn.setEnabled(True)
                self.generate_btn.setToolTip("Click to generate interface structure")
    
    def get_selected_candidate_index(self) -> int:
        """Get currently selected candidate index.
        
        Returns:
            Index in candidates list (0-based), or -1 if no selection
        """
        if not self._candidates:
            return -1
        return self.candidate_dropdown.currentIndex()
    
    def show_placeholder(self) -> None:
        """Show placeholder message in main area."""
        self.placeholder_label.show()
    
    def hide_placeholder(self) -> None:
        """Hide placeholder message after generation."""
        self.placeholder_label.hide()
    
    def append_log(self, message: str) -> None:
        """Append message to info panel log.
        
        Convenience method for MainWindow to log messages.
        
        Args:
            message: Log message to append
        """
        self.info_panel.append_log(message)
    
    def clear_log(self) -> None:
        """Clear info panel log.
        
        Convenience method for MainWindow to clear log.
        """
        self.info_panel.clear_log()
    
    def expand_log(self) -> None:
        """Expand info panel.
        
        Convenience method for MainWindow to expand log panel.
        """
        self.info_panel.expand()
    
    def collapse_log(self) -> None:
        """Collapse info panel.
        
        Convenience method for MainWindow to collapse log panel.
        """
        self.info_panel.collapse()
