"""Dual viewport widget for side-by-side candidate comparison.

This module provides the DualViewerWidget class for displaying multiple
structure candidates in separate synchronized viewports.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Signal

from quickice.gui.molecular_viewer import MolecularViewerWidget
from quickice.ranking.types import RankedCandidate


class DualViewerWidget(QWidget):
    """Dual viewport container for candidate comparison.
    
    This widget displays two MolecularViewerWidget instances side-by-side
    with synchronized cameras for easy visual comparison of candidates.
    
    Per ADVVIZ-04: User can view multiple candidates side-by-side in 
    separate viewports for comparison.
    
    Per CONTEXT.md: Always dual view after generation (1 row, 2 grids).
    Default: Grid 1 shows rank #1, Grid 2 shows rank #2.
    
    Attributes:
        viewer1: First molecular viewer (left).
        viewer2: Second molecular viewer (right).
        _ranked_candidates: List of ranked candidates to display.
        _selected_index1: Index of candidate shown in viewer1.
        _selected_index2: Index of candidate shown in viewer2.
    """
    
    # Signal emitted when candidates are loaded, with count
    candidates_loaded = Signal(int)
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize the dual viewer widget.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        # State tracking
        self._ranked_candidates: list[RankedCandidate] = []
        self._selected_index1: int = 0
        self._selected_index2: int = 1
        
        # Set up UI with two viewports
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the dual viewport layout.
        
        Creates a horizontal layout with two columns, each containing
        a title label and a MolecularViewerWidget. Equal stretch factors
        ensure balanced sizing.
        """
        # Main horizontal layout (1 row, 2 grids per CONTEXT.md)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # Column 1: Candidate 1 viewer
        column1_layout = QVBoxLayout()
        column1_layout.setContentsMargins(0, 0, 0, 0)
        column1_layout.setSpacing(0)
        
        title1_label = QLabel("Candidate 1")
        title1_label.setStyleSheet("font-weight: bold; padding: 4px;")
        column1_layout.addWidget(title1_label)
        
        self.viewer1 = MolecularViewerWidget()
        column1_layout.addWidget(self.viewer1)
        
        main_layout.addLayout(column1_layout, stretch=1)
        
        # Column 2: Candidate 2 viewer
        column2_layout = QVBoxLayout()
        column2_layout.setContentsMargins(0, 0, 0, 0)
        column2_layout.setSpacing(0)
        
        title2_label = QLabel("Candidate 2")
        title2_label.setStyleSheet("font-weight: bold; padding: 4px;")
        column2_layout.addWidget(title2_label)
        
        self.viewer2 = MolecularViewerWidget()
        column2_layout.addWidget(self.viewer2)
        
        main_layout.addLayout(column2_layout, stretch=1)
        
        # Store title labels for updates
        self._title1_label = title1_label
        self._title2_label = title2_label
