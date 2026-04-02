"""Export handlers for PDB files, phase diagram images, and 3D viewport screenshots.

This module provides exporter classes for saving user work to standard file formats:
- PDBExporter: Save ranked ice structure candidates to PDB format
- DiagramExporter: Export phase diagram to PNG or SVG images
- ViewportExporter: Capture 3D molecular viewport to image files
"""

from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox

from quickice.output.pdb_writer import write_pdb_with_cryst1
from quickice.ranking.types import RankedCandidate


class PDBExporter:
    """Handle PDB file export with proper dialogs and validation.
    
    Per CONTEXT.md:
    - Default filename: {phase}_{T}K_{P}bar_c{candidate_num}.pdb
    - Prompt before overwriting
    """
    
    def __init__(self, parent_widget):
        """Initialize PDB exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_candidate(self, ranked_candidate: RankedCandidate, T: float, P: float) -> bool:
        """Export a ranked candidate to PDB file.
        
        Args:
            ranked_candidate: RankedCandidate with candidate structure and metadata
            T: Temperature in Kelvin
            P: Pressure in bar (will be converted to bar for filename)
            
        Returns:
            True if export succeeded, False if cancelled or failed
            
        Per CONTEXT.md:
        - Default filename format: {phase}_{T}K_{P}bar_c{candidate_num}.pdb
        - Overwrite behavior: Prompt before overwriting
        """
        # Generate default filename
        phase_id = ranked_candidate.candidate.phase_id or "ice"
        rank = ranked_candidate.rank
        default_name = f"{phase_id}_{T:.0f}K_{P:.0f}bar_c{rank}.pdb"
        
        # Show save dialog
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save PDB File",
            default_name,
            "PDB Files (*.pdb);;All Files (*)",
            "PDB Files (*.pdb)"
        )
        
        if not filepath:
            return False
        
        # Ensure .pdb extension
        path = Path(filepath)
        if path.suffix.lower() != '.pdb':
            path = path.with_suffix('.pdb')
        
        # Check for overwrite
        if path.exists():
            reply = QMessageBox.question(
                self.parent,
                "Overwrite File?",
                f"File '{path.name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
        
        # Write file using existing PDB writer
        try:
            write_pdb_with_cryst1(ranked_candidate.candidate, str(path))
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save PDB file:\n\n{str(e)}"
            )
            return False
