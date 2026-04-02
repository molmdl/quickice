# Phase 13: Update README and Documentation After Finishing the GUI - Research

**Researched:** 2026-04-02
**Domain:** Technical documentation, GUI application help systems, README best practices
**Confidence:** HIGH

## Summary

This phase focuses on updating existing v1.x documentation to reflect the v2.0 GUI application, creating in-app quick reference help (INFO-04 deferred from Phase 11), and adding GUI screenshots. The research reveals established patterns for README structure, in-app help dialogs in Qt/PySide6, and documentation best practices from the Write the Docs community and Diátaxis framework.

The GUI is supplementary to the CLI (per CONTEXT.md decisions), so the README maintains CLI-focus while adding brief GUI mentions. In-app help uses a modal QDialog (not panel, not F1 shortcut) with keyboard shortcuts and workflow summary. Screenshots use PNG format in docs/images/ folder.

**Primary recommendation:** Use standard PySide6 QDialog with QDialogButtonBox for in-app help. Update README with minimal changes following "cognitive funneling" pattern. Create docs/images/ folder with hero screenshot and feature screenshots.

## Standard Stack

The established tools/approaches for documentation in Qt/PySide6 applications:

### Core
| Library/Approach | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| PySide6 QDialog | 6.x | Modal help dialogs | Qt standard, platform-native buttons |
| PySide6 QMessageBox | 6.x | Simple alerts/information | Built-in convenience methods |
| Markdown | - | README and docs | Universal format, GitHub renders automatically |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| QDialogButtonBox | Standard dialog buttons (OK/Cancel) | When creating custom dialogs |
| QVBoxLayout | Dialog content layout | Simple single-column layouts |
| QLabel | Text content in dialogs | Quick reference text |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| QDialog modal | QDockWidget panel | Modal is simpler for quick reference, per CONTEXT.md decision |
| F1 shortcut | Menu-only trigger | F1 not requested; menu is more discoverable for this use case |
| HTML in QLabel | Plain text | Plain text sufficient for quick reference list |

**Implementation:**
```python
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Reference")
        
        # Standard OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        # Content
        layout = QVBoxLayout()
        help_text = QLabel("Help content here...")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        layout.addWidget(button_box)
        self.setLayout(layout)
```

## Architecture Patterns

### Recommended README Structure

Following "cognitive funneling" from Art of README (broad → specific):

```markdown
# QuickIce

> Experimental disclaimer

Brief one-liner description

## Overview
**What is QuickIce?** - Include CLI and GUI mention
**Why QuickIce?** - Keep existing
**How it works:** - Keep existing

## Installation
- Keep existing setup instructions
- Add brief GUI launch method after installation

## Quick Start
### Basic Usage (CLI)
- Keep existing CLI examples

### GUI Usage
- Brief mention or link to docs/

## Supported Ice Phases
- Keep existing table

## Documentation
- Link to CLI reference
- Link to GUI guide (new: docs/gui-guide.md)

## Known Issues
- Keep existing

## Project Structure
- Keep existing (CLI-focused)

## Testing
- Keep existing

## Dependencies
- Keep existing

## Reference
- Keep existing GenIce2, IAPWS, spglib citations
```

### Pattern 1: In-App Help Dialog (INFO-04)
**What:** Modal dialog showing keyboard shortcuts and workflow summary
**When to use:** Help menu action triggered by user
**Example:**
```python
# In MainWindow._create_menu_bar()
def _create_menu_bar(self):
    menubar = self.menuBar()
    
    # File menu (existing)
    file_menu = menubar.addMenu("File")
    # ... file actions ...
    
    # Help menu (new)
    help_menu = menubar.addMenu("Help")
    help_action = help_menu.addAction("Quick Reference")
    help_action.triggered.connect(self._on_help)
    
def _on_help(self):
    """Open quick reference help dialog."""
    dlg = HelpDialog(self)
    dlg.exec()

# HelpDialog class
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Reference - QuickIce")
        self.setMinimumWidth(400)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        layout = QVBoxLayout()
        
        # What QuickIce does
        intro = QLabel(
            "QuickIce generates plausible ice crystal structure candidates "
            "for given thermodynamic conditions (temperature and pressure)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addSpacing(10)
        
        # Keyboard shortcuts
        shortcuts_title = QLabel("<b>Keyboard Shortcuts</b>")
        layout.addWidget(shortcuts_title)
        
        shortcuts = QLabel(
            "Enter — Generate structures\n"
            "Escape — Cancel generation\n"
            "Ctrl+S — Save PDB (left viewer)\n"
            "Ctrl+Shift+S — Save PDB (right viewer)\n"
            "Ctrl+D — Save phase diagram\n"
            "Ctrl+Alt+S — Save viewport screenshot"
        )
        layout.addWidget(shortcuts)
        
        layout.addSpacing(10)
        
        # Workflow summary
        workflow_title = QLabel("<b>Workflow</b>")
        layout.addWidget(workflow_title)
        
        workflow = QLabel(
            "1. Enter temperature, pressure, molecule count\n"
            "2. Click phase diagram OR type values\n"
            "3. Press Enter or click Generate\n"
            "4. View ranked candidates in 3D viewer\n"
            "5. Export PDB files, diagram, or screenshots"
        )
        layout.addWidget(workflow)
        
        layout.addSpacing(10)
        
        # External references
        refs = QLabel(
            "<i>For scientific background, click on phase regions in the "
            "diagram to see validated references.</i>\n\n"
            "More info: <a href='https://github.com/vitroid/GenIce2'>GenIce2</a> | "
            "<a href='https://www.iapws.org'>IAPWS</a>"
        )
        refs.setOpenExternalLinks(True)
        refs.setWordWrap(True)
        layout.addWidget(refs)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
```

**Source:** PySide6 documentation patterns, PythonGUIs tutorials

### Pattern 2: Screenshot Organization
**What:** Standard location and naming for GUI screenshots
**When to use:** Documentation images for README and GUI guide
**Structure:**
```
docs/
├── images/
│   ├── quickice-gui.png         # Hero screenshot (main window)
│   ├── phase-diagram.png        # Phase diagram panel
│   ├── 3d-viewer.png           # Single viewport view
│   ├── dual-viewport.png       # Dual viewport comparison
│   └── export-menu.png         # Export menu/dropdown
├── cli-reference.md            # Existing
├── gui-guide.md                # New: Full GUI documentation
├── ranking.md                  # Existing
├── principles.md               # Existing
└── flowchart.md                # Existing
```

**Naming convention:** kebab-case, descriptive feature names

**Source:** Documentation best practices, Write the Docs

### Anti-Patterns to Avoid
- **Don't duplicate phase info in help dialog:** Phase diagram already shows references when clicked (Phase 11 feature)
- **Don't use animated GIFs:** CONTEXT.md specifies static PNGs only
- **Don't make README GUI-heavy:** CLI remains primary interface, GUI is supplementary
- **Don't embed critical info only in images:** README must work without images loaded
- **Don't use F1 shortcut for help:** Not requested in CONTEXT.md, menu trigger is sufficient

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Standard dialog buttons | Custom QPushButton layout | QDialogButtonBox | Platform-native button ordering, standard icons |
| Simple help display | Custom widget | QDialog + QLabel | Modal behavior, proper parent centering |
| Information alert | Custom dialog | QMessageBox.information() | Native styling, simpler API |
| Document structure | Ad-hoc sections | Cognitive funneling pattern | Proven readability, matches user mental model |

**Key insight:** Qt provides excellent built-in dialog support. Modal help dialogs are simple and effective for quick reference content.

## Common Pitfalls

### Pitfall 1: Outdated Screenshots
**What goes wrong:** Screenshots don't match current UI, creating user confusion
**Why it happens:** UI evolves but screenshots aren't updated
**How to avoid:** 
- Capture screenshots after final UI freeze (Phase 12 complete)
- Add comment in README: `<!-- TODO: Update screenshot after UI changes -->`
- Use descriptive filenames that match feature names
**Warning signs:** User reports discrepancy between docs and actual app

### Pitfall 2: Over-Documenting GUI in README
**What goes wrong:** README becomes GUI-heavy, obscuring primary CLI interface
**Why it happens:** Excitement about new feature leads to overemphasis
**How to avoid:** 
- Keep README changes minimal per CONTEXT.md
- Link to docs/gui-guide.md for detailed GUI docs
- Use one hero screenshot, brief mention of GUI launch
**Warning signs:** README longer than 300 lines, GUI sections longer than CLI sections

### Pitfall 3: Inconsistent Documentation Style
**What goes wrong:** New docs don't match existing docs' tone and structure
**Why it happens:** Different author or lack of style guide awareness
**How to avoid:**
- Review existing docs/cli-reference.md structure before writing
- Use similar headings, code block formatting, tone
- Keep "Experimental" disclaimer consistent
**Warning signs:** Different formatting, terminology, or voice in new docs

### Pitfall 4: Missing In-App Help Discoverability
**What goes wrong:** Users don't find help menu, assume no help exists
**Why it happens:** Help menu hidden or non-obvious
**How to avoid:**
- Place Help menu after File menu in menu bar
- Use standard menu name "Help" (not "Quick Reference" or "Documentation")
- Consider tooltip on menu bar explaining help location
**Warning signs:** Users ask questions answered by help dialog

### Pitfall 5: Modal Dialog Blocks Critical Information
**What goes wrong:** User needs to reference help while interacting with app
**Why it happens:** Modal dialogs block all interaction with parent window
**How to avoid:**
- Keep help content brief (fits on one screen)
- Use word wrap to prevent horizontal scrolling
- If help needs reference during operation, consider non-modal (but CONTEXT.md specifies modal)
**Warning signs:** Users close and reopen help repeatedly

## Code Examples

### Help Dialog Implementation (Verified Pattern)

```python
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

class QuickReferenceDialog(QDialog):
    """Quick reference help dialog for QuickIce GUI.
    
    Per INFO-04: Modal dialog with keyboard shortcuts and workflow summary.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Reference")
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
            "5. Use File menu to export PDB, diagram, or screenshots"
        )
        workflow_text.setWordWrap(True)
        layout.addWidget(workflow_text)
        
        # External references
        layout.addWidget(self._create_section_label("More Information"))
        refs_text = QLabel(
            "• Click phase regions in diagram to see scientific references\n"
            "• <a href='https://github.com/vitroid/GenIce2'>GenIce2 repository</a>\n"
            "• <a href='https://www.iapws.org'>IAPWS (water standards)</a>"
        )
        refs_text.setOpenExternalLinks(True)
        refs_text.setWordWrap(True)
        layout.addWidget(refs_text)
        
        # Standard OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def _create_section_label(self, text: str) -> QLabel:
        """Create a section header label."""
        label = QLabel(f"<b>{text}</b>")
        return label


# Usage in MainWindow
def _on_help(self):
    """Open quick reference dialog."""
    dlg = QuickReferenceDialog(self)
    dlg.exec()
```

**Source:** PySide6 documentation patterns from PythonGUIs tutorial

### README Update Pattern (Minimal Changes)

```markdown
# QuickIce

> **Experimental** - This is a "pure vibe coding project"...

Condition-based ice structure candidate generation from thermodynamic conditions.

## Overview

**What is QuickIce?**

QuickIce is a command-line tool with an optional GUI that generates plausible 
ice crystal structure candidates for given thermodynamic conditions. Given a 
temperature (K) and pressure (MPa), it:
...
```

**Source:** Art of README, Write the Docs principles

### Screenshot Markdown Pattern

```markdown
<!-- In README.md -->
![QuickIce GUI](docs/images/quickice-gui.png)
*QuickIce GUI showing phase diagram and dual 3D molecular viewer*

<!-- In docs/gui-guide.md -->
### Phase Diagram Panel
![Phase Diagram](images/phase-diagram.png)
*Interactive phase diagram with clickable regions*

### 3D Molecular Viewer
![3D Viewer](images/3d-viewer.png)
*Single viewport showing molecular structure*
```

**Source:** Documentation best practices, Write the Docs

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PDF user manuals | Markdown in repo | ~2015+ | Version-controlled, searchable |
| FAQ sections | Task-based guides | ~2018+ | Better user experience |
| Separate help files | In-app help dialogs | ~2010+ | Immediate access |
| Custom dialog buttons | QDialogButtonBox | Qt 4+ | Platform-native consistency |

**Deprecated/outdated:**
- **FAQ sections:** Write the Docs explicitly discourages FAQs as primary documentation
- **PDF-only manuals:** Hard to update, not searchable, not version-controlled
- **Screenshot-dependent docs:** README must work without images loaded

## Open Questions

1. **When to capture screenshots?**
   - What we know: Phase 12 packages the application
   - What's unclear: Before or after packaging?
   - Recommendation: Capture after Phase 12 complete, when UI is frozen
   
2. **GUI guide depth?**
   - What we know: CONTEXT.md says link to docs/ for full details
   - What's unclear: How comprehensive should docs/gui-guide.md be?
   - Recommendation: Cover all major features, 200-400 lines, include all screenshots

3. **Help dialog content wording?**
   - What we know: CONTEXT.md specifies keyboard shortcuts and workflow
   - What's unclear: Exact phrasing for descriptions
   - Recommendation: Use straightforward language, match existing docs tone

## Sources

### Primary (HIGH confidence)
- Write the Docs - Documentation principles, beginner's guide (fetched 2026-04-02)
- Art of README - README structure and best practices (fetched 2026-04-02)
- PySide6 Dialog Tutorial - QDialog, QMessageBox patterns (fetched 2026-04-02)
- Diátaxis Documentation System - Four types of documentation (fetched 2026-04-02)

### Secondary (MEDIUM confidence)
- Current README.md structure (examined 2026-04-02)
- Current docs/ structure (examined 2026-04-02)
- Current main_window.py menu implementation (examined 2026-04-02)

### Tertiary (LOW confidence)
- None - all findings verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PySide6 QDialog is well-documented standard
- Architecture: HIGH - README patterns from Art of README, Write the Docs
- Pitfalls: HIGH - Common documentation anti-patterns well-known
- Screenshot practices: MEDIUM - Conventional patterns, not library-specific

**Research date:** 2026-04-02
**Valid until:** 2027-04-02 (documentation patterns stable)
