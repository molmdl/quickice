"""Quick reference help dialog for QuickIce GUI.

Per INFO-04: Modal dialog showing keyboard shortcuts and workflow summary.

Structure (Phase 48-09): QStackedWidget + QListWidget TOC layout. The single
QScrollArea was replaced with a left TOC (QListWidget) and right stacked pages
(QStackedWidget). Each page wraps its content in a QScrollArea for independent
scrolling. The OK button lives in the outer layout, outside the stacked widget,
so it is always visible regardless of the selected page.
"""

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)
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
        self.setMinimumWidth(600)
        self.setMaximumWidth(800)
        self.setMinimumHeight(400)
        self.setMaximumHeight(700)

        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog content with a TOC + stacked pages layout."""
        # Outer vertical layout: body (TOC + pages) on top, OK button below.
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # Body horizontal layout: TOC (left, fixed) + pages (right, stretches).
        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        # --- TOC (left) ---
        self.toc = QListWidget()
        self.toc.setFixedWidth(160)
        self.toc.currentRowChanged.connect(self._on_section_changed)

        # --- Pages (right) ---
        self.pages = QStackedWidget()

        # --- 8 sections (verbatim content migrated from the prior QScrollArea) ---
        # 1. Introduction
        intro_label = QLabel(
            "QuickIce generates plausible ice crystal structure candidates "
            "for given thermodynamic conditions (temperature and pressure), "
            "and constructs ice-water interfaces (GUI only) for molecular dynamics simulations."
        )
        intro_label.setWordWrap(True)
        intro_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Introduction", self._make_page(intro_label))

        # 2. Keyboard Shortcuts
        shortcuts_label = QLabel(
            "Enter — Generate structures\n"
            "Escape — Cancel generation\n"
            "Ctrl+S — Export current tab for GROMACS\n"
            "Ctrl+Shift+S — Save PDB (right viewer)\n"
            "Ctrl+Alt+P — Save PDB (left viewer)\n"
            "Ctrl+D — Save phase diagram\n"
            "Ctrl+G — Export ice for GROMACS\n"
            "Ctrl+H — Export hydrate for GROMACS\n"
            "Ctrl+I — Export interface for GROMACS\n"
            "Ctrl+L — Export solutes for GROMACS\n"
            "Ctrl+M — Export custom molecules for GROMACS\n"
            "Ctrl+J — Export ions for GROMACS\n"
            "Ctrl+Alt+S — Save viewport screenshot"
        )
        shortcuts_label.setWordWrap(True)
        shortcuts_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Keyboard Shortcuts", self._make_page(shortcuts_label))

        # 3. Workflow
        workflow_label = QLabel(
            "Tab 0 — Ice Generation:\n"
            "1. Enter temperature, pressure, and molecule count\n"
            "2. Click on phase diagram OR type values directly\n"
            "3. Press Enter or click Generate button\n"
            "4. View ranked candidates in dual 3D viewer\n"
            "5. Use File menu to export PDB, GROMACS files, diagram, or screenshots\n"
            "\n"
            "Tab 1 — Hydrate Generation:\n"
            "6. Switch to Hydrate Generation tab\n"
            "7. Select lattice type (10 types: sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17) and guest type per cage\n"
            "8. Set unit cell repetitions and generate hydrate structure\n"
            "9. Export hydrate for GROMACS (Ctrl+H)\n"
            "\n"
            "Tab 2 — Interface Construction:\n"
            "10. Switch to Interface Construction tab\n"
            "11. Select mode: Slab (layered), Pocket (water cavity), or Piece (ice in water)\n"
            "12. Set box dimensions and mode-specific parameters\n"
            "13. Select a candidate and click Generate Interface\n"
            "14. View result (ice=cyan, water=cornflower blue)\n"
            "15. Export interface for GROMACS (Ctrl+I)\n"
            "\n"
            "Tab 3 — Custom Molecule:\n"
            "16. Switch to Custom Molecule tab (requires interface from Tab 2)\n"
            "17. Upload .gro and .itp files for your custom molecule\n"
            "18. Choose placement mode (Random or Custom)\n"
            "19. Set position/rotation (Custom mode) or count/concentration (Random mode)\n"
            "20. Click Validate & Preview to check placement validity (Custom mode)\n"
            "21. Click Generate Custom Molecules to insert custom molecules\n"
            "22. Export custom molecules for GROMACS (Ctrl+M)\n"
            "\n"
            "Tab 4 — Solute Insertion:\n"
            "23. Switch to Solute Insertion tab (requires interface from Tab 2)\n"
            "    If using Custom Molecule as source, complete Tab 3 (Custom Molecule) first.\n"
            "24. Select solute source (Interface or Custom Molecule)\n"
            "25. Set concentration (mol/L) and select solute type (THF or CH₄)\n"
            "26. Click Insert Solutes to place molecules in liquid region\n"
            "27. Export solutes for GROMACS (Ctrl+L)\n"
            "\n"
            "Tab 5 — Ion Insertion:\n"
            "28. Switch to Ion Insertion tab (requires interface from Tab 2)\n"
            "29. Select ion source (Interface, Custom Molecule, or Solute)\n"
            "30. Set ion concentration and insert ions into interface\n"
            "31. Export ions for GROMACS (Ctrl+J)"
        )
        workflow_label.setWordWrap(True)
        workflow_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Workflow", self._make_page(workflow_label))

        # 4. Extended Lattice Types (v4.7 — new)
        extended_lattices_label = QLabel(
            "<b>Extended Lattice Types (v4.7)</b><br><br>"
            "QuickIce supports 10 hydrate lattice types:<br><br>"
            "<b>Classical clathrates:</b> sI, sII, sH<br>"
            "<b>Filled ices:</b> c0te (C0), c1te (C1), c2te (C2), ice1hte (Ih) "
            "— Teeratchanan 2015<br>"
            "<b>Water-only:</b> sTprime (sT′, Smirnov 2013), 17 (Ice XVII) "
            "— no cage guests; guest/occupancy controls hidden<br>"
            "<b>Empty frameworks:</b> 16 (Ice XVI, empty sII framework)<br><br>"
            "<b>Triclinic lattices</b> (c0te, c1te): Blocked for interface generation. "
            "sH is triclinic for data accuracy but NOT blocked.<br>"
            "<b>Filled ices</b> use cage key 'small' (not 'guest') for CLI --cage-guest."
        )
        extended_lattices_label.setWordWrap(True)
        extended_lattices_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Extended Lattice Types", self._make_page(extended_lattices_label))

        # 5. Custom Guest in Hydrate (v4.7 — new, GUI-only)
        custom_guest_label = QLabel(
            "<b>Custom Guest in Hydrate (v4.7 — GUI-only)</b><br><br>"
            "Upload a custom guest molecule (.gro + .itp) for hydrate cage placement.<br><br>"
            "<b>Workflow:</b><br>"
            "1. Upload .gro + .itp file pair<br>"
            "2. Validate: comb-rule=2 mandatory, residue name ≤3 chars, GRO parseable<br>"
            "3. Select 'Custom: {residue}' in per-cage guest dropdowns<br>"
            "4. Generate hydrate structure<br>"
            "5. Export: .itp bundled with [atomtypes] commented out + merged into .top; "
            "residue name gets _H suffix (e.g. MOL → MOL_H)<br><br>"
            "<b>GUI-only for v4.7.</b> The CLI supports built-in CH₄/THF only.<br>"
            "See Help > GRO/ITP Guide (external) for detailed ITP requirements."
        )
        custom_guest_label.setWordWrap(True)
        custom_guest_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Custom Guest in Hydrate", self._make_page(custom_guest_label))

        # 6. Mixed Cage Occupancy (v4.7 — new)
        mixed_occupancy_label = QLabel(
            "<b>Mixed Cage Occupancy (v4.7)</b><br><br>"
            "Assign different guest types to different cage types with independent occupancy:<br><br>"
            "• Each cage type (small/medium/large) has its own guest dropdown + occupancy spinner<br>"
            "• Multi-guest: e.g. CH₄ in small cages (60%) + THF in large cages (100%)<br>"
            "• Water-only lattices (sTprime, 17): guest/occupancy controls hidden<br>"
            "• Filled ices: single cage row (small only)<br><br>"
            "<b>CLI:</b> Use --cage-guest KEY=GUEST:OCC (repeatable).<br>"
            "Example: --cage-guest small=CH4:60 --cage-guest large=THF:100<br><br>"
            "Note: --guest and --cage-occupancy-small/large are DEPRECATED; use --cage-guest."
        )
        mixed_occupancy_label.setWordWrap(True)
        mixed_occupancy_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Mixed Cage Occupancy", self._make_page(mixed_occupancy_label))

        # 7. Depol Mode (v4.7 — new)
        depol_label = QLabel(
            "<b>Depol Mode (v4.7)</b><br><br>"
            "Controls H-bond orientation during hydrate generation:<br><br>"
            "• <b>Strict</b> (default): Ice rules enforced, zero net dipole. Standard behavior.<br>"
            "• <b>Optimal</b>: Relaxed dipole optimization.<br><br>"
            "Select from the Depol dropdown in the Hydrate tab.<br>"
            "CLI: --depol strict | optimal (default: strict)<br><br>"
            "Note: In GenIce2 2.2.13.1, strict and optimal produce identical atom counts. "
            "The mode affects H-bond orientation, not the number of atoms."
        )
        depol_label.setWordWrap(True)
        depol_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Depol Mode", self._make_page(depol_label))

        # 8. Dimension Relationships
        dimension_label = QLabel(
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
        dimension_label.setWordWrap(True)
        dimension_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Dimension Relationships", self._make_page(dimension_label))

        # 9. Best Practices
        best_practices_label = QLabel(
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
            "• 'Ice II not supported': Ice II (rhombohedral) cannot form orthogonal supercells - use Ice V or Ice VI instead\n"
            "• 'Triclinic cell': Transformation applied automatically for Ice V (monoclinic)"
        )
        best_practices_label.setWordWrap(True)
        best_practices_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Best Practices", self._make_page(best_practices_label))

        # 10. Custom Molecule Preparation
        custom_mol_label = QLabel(
            "GRO file: Coordinates in nm, residue name in columns 6-10\n"
            "ITP file: Must include [ atomtypes ], [ moleculetype ], [ atoms ] sections\n"
            "Force field: User-provided [ atomtypes ] required\n"
            "Validation: Atom count and residue name checked on upload\n"
            "See Help > Custom Molecules in menu for detailed format guide"
        )
        custom_mol_label.setWordWrap(True)
        custom_mol_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._add_section("Custom Molecule Preparation", self._make_page(custom_mol_label))

        # 11. More Information & Notes (combined from the former "More Information"
        #    and "Important Notes" pages — both QLabels in one QVBoxLayout, with
        #    the notes content below the references, wrapped in a single
        #    QScrollArea for independent scrolling; matches the _make_page pattern).
        refs_label = QLabel(
            "• Click phase regions in diagram to see scientific references\n"
            "• GenIce2 repository: https://github.com/genice-dev/GenIce2 — DOI: 10.1002/jcc.25077\n"
            "• spglib (crystal symmetry detection) — DOI: 10.1080/27660400.2024.2384822\n"
            "• Madrid2019 ion parameters (Na⁺/Cl⁻ ±0.85e) — DOI: 10.1063/1.5121392\n"
            "• IAPWS (water standards): https://www.iapws.org"
        )
        refs_label.setOpenExternalLinks(True)
        refs_label.setWordWrap(True)
        refs_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )

        notes_label = QLabel(
            "• Actual molecule count may differ from requested to satisfy\n"
            "  crystal structure symmetry constraints\n"
            "• GROMACS export generates .gro, .top, and .itp files\n"
            "• TIP4P-ICE water model used for GROMACS compatibility (Abascal et al. 2005, DOI: 10.1063/1.1931662)\n"
            "• GROMACS export uses candidate selected in left viewport dropdown\n"
            "• Interface GROMACS export uses same TIP4P-ICE model for both ice and water\n"
            "• Ice Ih density uses IAPWS R10-06(2009) for temperature-dependent accuracy (https://www.iapws.org/release/Ice-2009.html)\n"
            "• Water density for interfaces uses IAPWS-95 formulation (https://www.iapws.org/relguide/IAPWS-95.html)"
        )
        notes_label.setWordWrap(True)
        notes_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )

        combined_scroll = QScrollArea()
        combined_scroll.setWidgetResizable(True)
        combined_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        combined_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        combined_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        combined_content = QWidget()
        combined_layout = QVBoxLayout(combined_content)
        combined_layout.setSpacing(12)
        combined_layout.setContentsMargins(12, 12, 12, 12)
        combined_layout.addWidget(refs_label)
        combined_layout.addWidget(notes_label)
        combined_layout.addStretch()
        combined_scroll.setWidget(combined_content)
        self._add_section("More Information & Notes", combined_scroll)

        body.addWidget(self.toc)
        body.addWidget(self.pages, 1)   # pages stretch
        outer.addLayout(body)

        # OK button OUTSIDE the stacked widget (always visible).
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        outer.addWidget(button_box)

        # Show the first section when the dialog opens.
        self.toc.setCurrentRow(0)

    def _on_section_changed(self, row):
        """Switch the stacked widget page when the TOC selection changes."""
        self.pages.setCurrentIndex(row)

    def _add_section(self, title, content_widget):
        """Add a section to the TOC and the stacked widget.

        Keeps the TOC row index and the stacked page index in sync
        (TOC row N corresponds to page index N).
        """
        item = QListWidgetItem(title)
        self.toc.addItem(item)
        self.pages.addWidget(content_widget)

    def _make_page(self, label):
        """Wrap a QLabel in an independently scrollable page widget.

        Each page scrolls on its own so long content does not affect the
        TOC list or the OK button.
        """
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(label)
        layout.addStretch()

        scroll_area.setWidget(content)
        return scroll_area
