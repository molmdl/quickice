"""Quick reference help dialog for QuickIce GUI.

Per INFO-04: Modal dialog showing keyboard shortcuts and workflow summary.
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class QuickReferenceDialog(QDialog):
    """Quick reference help dialog for QuickIce GUI.
    
    This modal dialog provides:
    - Brief application description
    - Keyboard shortcuts list
    - Workflow summary
    - Links to external resources
    
    Per CONTEXT.md: Uses modal QDialog (not panel, not F1 shortcut).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Reference - QuickIce")
        self.setMinimumWidth(450)
        self.setMaximumWidth(600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup dialog content."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Introduction
        intro = QLabel(
            "QuickIce generates plausible ice crystal structure candidates "
            "for given thermodynamic conditions (temperature and pressure)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        # Keyboard shortcuts section
        layout.addWidget(self._create_section_label("Keyboard Shortcuts"))
        shortcuts_text = QLabel(
            "Enter — Generate structures\n"
            "Escape — Cancel generation\n"
            "Ctrl+S — Save PDB (left viewer)\n"
            "Ctrl+Shift+S — Save PDB (right viewer)\n"
            "Ctrl+D — Save phase diagram\n"
            "Ctrl+G — Export for GROMACS\n"
            "Ctrl+I — Export interface for GROMACS\n"
            "Ctrl+Alt+S — Save viewport screenshot"
        )
        shortcuts_text.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        layout.addWidget(shortcuts_text)
        
        # Workflow section
        layout.addWidget(self._create_section_label("Workflow"))
        workflow_text = QLabel(
            "Tab 1 — Ice Generation:\n"
            "1. Enter temperature, pressure, and molecule count\n"
            "2. Click on phase diagram OR type values directly\n"
            "3. Press Enter or click Generate button\n"
            "4. View ranked candidates in dual 3D viewer\n"
            "5. Use File menu to export PDB, GROMACS files, diagram, or screenshots\n"
            "\n"
            "Tab 2 — Interface Construction:\n"
            "6. Switch to Interface Construction tab\n"
            "7. Select mode: Slab (layered), Pocket (water cavity), or Piece (ice in water)\n"
            "8. Set box dimensions and mode-specific parameters\n"
            "9. Select a candidate and click Generate Interface\n"
            "10. View result (ice=cyan, water=cornflower blue)\n"
            "11. Export interface for GROMACS (Ctrl+I)"
        )
        workflow_text.setWordWrap(True)
        layout.addWidget(workflow_text)
        
        # Dimension Relationships section (NEW)
        layout.addWidget(self._create_section_label("Dimension Relationships"))
        dimension_text = QLabel(
            "SLAB MODE:\n"
            "• Box Z MUST equal: 2 × ice_thickness + water_thickness\n"
            "• Example: ice=3.0 nm, water=4.0 nm → box_z = 10.0 nm\n"
            "• Structure: bottom ice (Z: 0–3.0) | water (Z: 3.0–7.0) | top ice (Z: 7.0–10.0)\n"
            "• Typical values: ice 2–10 nm, water 2–10 nm\n"
            "\n"
            "POCKET MODE:\n"
            "• Pocket diameter MUST be smaller than all box dimensions\n"
            "• Example: pocket=2.0 nm → box must be >2.0 nm in X, Y, and Z\n"
            "• The pocket is a spherical water cavity carved inside ice\n"
            "• Typical values: pocket 1–5 nm for confined water studies\n"
            "\n"
            "PIECE MODE:\n"
            "• Box dimensions MUST exceed ice piece dimensions\n"
            "• Ice piece dimensions shown in 'Piece Parameters' section\n"
            "• Example: ice 2.5×2.5×2.0 nm → box must be larger (e.g., 4.0×4.0×3.0 nm)\n"
            "• Water molecules within 0.25 nm of ice surface are removed\n"
            "• Minimum water layer: 0.25 nm (overlap threshold)\n"
            "\n"
            "OVERLAP THRESHOLD (all modes):\n"
            "• Distance threshold for removing overlapping water molecules\n"
            "• Default: 0.25 nm (2.5 Å) — typical O-O distance for overlap detection\n"
            "• Water molecules closer than this to ice oxygen atoms are removed\n"
            "• Prevents atomic overlaps between ice and water"
        )
        dimension_text.setWordWrap(True)
        layout.addWidget(dimension_text)
        
        # Best Practices section (NEW)
        layout.addWidget(self._create_section_label("Best Practices"))
        best_practices_text = QLabel(
            "CHOOSING BOX DIMENSIONS:\n"
            "• X, Y: Large enough to contain ice candidate lateral dimensions\n"
            "• Z: Depends on mode (see Dimension Relationships above)\n"
            "• Larger boxes → more molecules → longer generation time\n"
            "• Typical systems: 5–10 nm per dimension\n"
            "\n"
            "CHOOSING ICE/WATER THICKNESS (slab mode):\n"
            "• Ice thickness: 2–10 nm for surface studies\n"
            "• Water thickness: 2–10 nm for sufficient water layer\n"
            "• Thicker layers → more realistic but slower\n"
            "• Minimum: 1–2 nm for each layer\n"
            "\n"
            "CHOOSING POCKET DIAMETER:\n"
            "• 1–3 nm: Small cavities (tens of water molecules)\n"
            "• 3–5 nm: Medium cavities (hundreds of water molecules)\n"
            "• >5 nm: Large cavities (requires large boxes)\n"
            "\n"
            "TROUBLESHOOTING:\n"
            "• 'Box too small': Increase box dimensions\n"
            "• 'Water layer too thin': Increase box or decrease ice thickness\n"
            "• 'No water molecules': Box too small or ice piece too large\n"
            "• 'Triclinic cell': Select different ice phase (ice_ii, ice_v are triclinic)"
        )
        best_practices_text.setWordWrap(True)
        layout.addWidget(best_practices_text)
        
        # External references
        layout.addWidget(self._create_section_label("More Information"))
        refs_text = QLabel(
            "• Click phase regions in diagram to see scientific references\n"
            "• GenIce2 repository: https://github.com/genice-dev/GenIce2\n"
            "• IAPWS (water standards): https://www.iapws.org"
        )
        refs_text.setOpenExternalLinks(True)
        refs_text.setWordWrap(True)
        layout.addWidget(refs_text)
        
        # Important notes section
        layout.addWidget(self._create_section_label("Important Notes"))
        notes_text = QLabel(
            "• Actual molecule count may differ from requested to satisfy\n"
            "  crystal structure symmetry constraints\n"
            "• GROMACS export generates .gro, .top, and .itp files\n"
            "• TIP4P-ICE water model used for GROMACS compatibility\n"
            "• GROMACS export uses candidate selected in left viewport dropdown\n"
            "• Interface GROMACS export uses same TIP4P-ICE model for both ice and water"
        )
        notes_text.setWordWrap(True)
        layout.addWidget(notes_text)
        
        # Standard OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def _create_section_label(self, text: str) -> QLabel:
        """Create a section header label.
        
        Args:
            text: Section title text
            
        Returns:
            QLabel with bold formatting
        """
        label = QLabel(f"<b>{text}</b>")
        return label
