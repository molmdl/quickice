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
    
    def set_candidates(self, ranked_candidates: list[RankedCandidate]) -> None:
        """Load ranked candidates into the dual viewer.
        
        Stores the candidates and displays the default selections:
        - Viewer 1: Rank #1 (index 0)
        - Viewer 2: Rank #2 (index 1)
        
        Per CONTEXT.md: Default view shows rank #1 in Grid 1 and 
        rank #2 in Grid 2.
        
        Args:
            ranked_candidates: List of ranked candidates sorted by 
                              combined_score (best first).
        """
        self._ranked_candidates = ranked_candidates
        
        # Default selection: index 0 for viewer1, index 1 for viewer2
        self._selected_index1 = 0
        self._selected_index2 = 1 if len(ranked_candidates) >= 2 else 0
        
        # Load candidates into viewers
        if len(ranked_candidates) >= 1:
            self.viewer1.set_ranked_candidate(ranked_candidates[0])
            self._update_title(1, ranked_candidates[0])
        
        if len(ranked_candidates) >= 2:
            self.viewer2.set_ranked_candidate(ranked_candidates[1])
            self._update_title(2, ranked_candidates[1])
        elif len(ranked_candidates) == 1:
            # If only one candidate, show it in both viewers
            self.viewer2.set_ranked_candidate(ranked_candidates[0])
            self._update_title(2, ranked_candidates[0])
        
        # Emit signal with candidate count
        self.candidates_loaded.emit(len(ranked_candidates))
    
    def set_candidate_for_viewer(self, viewer_index: int, candidate_index: int) -> None:
        """Select which candidate to display in a specific viewer.
        
        This method enables MainWindow dropdown selectors to change
        which candidate is shown in each viewport.
        
        Args:
            viewer_index: 0 for viewer1 (left), 1 for viewer2 (right).
            candidate_index: Index in the ranked_candidates list.
        
        Raises:
            IndexError: If viewer_index not in [0, 1] or candidate_index
                       out of bounds.
        """
        if viewer_index not in (0, 1):
            raise IndexError(f"viewer_index must be 0 or 1, got {viewer_index}")
        
        if not self._ranked_candidates:
            return
        
        if candidate_index < 0 or candidate_index >= len(self._ranked_candidates):
            raise IndexError(
                f"candidate_index {candidate_index} out of range "
                f"[0, {len(self._ranked_candidates) - 1}]"
            )
        
        viewer = self.viewer1 if viewer_index == 0 else self.viewer2
        selected_index_attr = "_selected_index1" if viewer_index == 0 else "_selected_index2"
        
        # Update selected index
        setattr(self, selected_index_attr, candidate_index)
        
        # Load candidate into viewer
        candidate = self._ranked_candidates[candidate_index]
        viewer.set_ranked_candidate(candidate)
        
        # Update title
        self._update_title(viewer_index + 1, candidate)
    
    def get_candidate_count(self) -> int:
        """Return the number of loaded candidates.
        
        Returns:
            Number of ranked candidates available for display.
        """
        return len(self._ranked_candidates)
    
    def _update_title(self, viewer_num: int, candidate: RankedCandidate) -> None:
        """Update viewer title with rank and score info.
        
        Args:
            viewer_num: 1 for left viewer, 2 for right viewer.
            candidate: The candidate being displayed.
        """
        title_label = self._title1_label if viewer_num == 1 else self._title2_label
        title_label.setText(f"Candidate {viewer_num} (Rank #{candidate.rank})")
