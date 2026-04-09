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
            "1. Enter temperature, pressure, and molecule count\n"
            "2. Click on phase diagram OR type values directly\n"
            "3. Press Enter or click Generate button\n"
            "4. View ranked candidates in dual 3D viewer\n"
            "5. Use File menu to export PDB, GROMACS files, diagram, or screenshots\n"
            "\n"
            "Tab 2 — Interface Construction:\n"
            "6. Switch to Interface Construction tab\n"
            "7. Select a candidate and configure parameters\n"
            "8. Generate interface structure\n"
            "9. Export interface for GROMACS (Ctrl+I)"
        )
        workflow_text.setWordWrap(True)
        layout.addWidget(workflow_text)
        
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
