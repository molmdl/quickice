"""Export handlers for PDB files, phase diagram images, and 3D viewport screenshots.

This module provides exporter classes for saving user work to standard file formats:
- PDBExporter: Save ranked ice structure candidates to PDB format
- DiagramExporter: Export phase diagram to PNG or SVG images
- ViewportExporter: Capture 3D molecular viewport to image files
"""

from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox
from matplotlib.figure import Figure

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


class DiagramExporter:
    """Handle phase diagram image export to PNG or SVG format.
    
    Per CONTEXT.md: OpenCode's discretion on formats (PNG and/or SVG).
    """
    
    def __init__(self, parent_widget):
        """Initialize diagram exporter.
        
        Args:
            parent_widget: Parent widget for dialog centering
        """
        self.parent = parent_widget
    
    def export_diagram(self, figure: Figure) -> bool:
        """Export matplotlib figure to PNG or SVG.
        
        Args:
            figure: Matplotlib figure to export
            
        Returns:
            True if export succeeded, False if cancelled or failed
            
        Per RESEARCH.md Pattern 2:
        - PNG: dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.2
        - SVG: format='svg', bbox_inches='tight', facecolor='white'
        """
        # Show save dialog with PNG and SVG options
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Save Phase Diagram Image",
            "phase_diagram.png",
            "PNG Image (*.png);;SVG Image (*.svg);;All Files (*)",
            "PNG Image (*.png)"
        )
        
        if not filepath:
            return False
        
        path = Path(filepath)
        
        # Determine format from selected filter or extension
        if 'SVG' in selected_filter or path.suffix.lower() == '.svg':
            path = path.with_suffix('.svg')
            format_type = 'svg'
        else:
            path = path.with_suffix('.png')
            format_type = 'png'
        
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
        
        # Export using matplotlib savefig
        try:
            if format_type == 'svg':
                figure.savefig(
                    str(path),
                    format='svg',
                    bbox_inches='tight',
                    facecolor='white'
                )
            else:
                figure.savefig(
                    str(path),
                    dpi=300,
                    bbox_inches='tight',
                    facecolor='white',
                    pad_inches=0.2
                )
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Error",
                f"Failed to save diagram image:\n\n{str(e)}"
            )
            return False
