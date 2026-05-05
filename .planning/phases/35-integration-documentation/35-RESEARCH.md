# Phase 35: Integration & Documentation - Research

**Researched:** 2026-05-05
**Domain:** GUI application integration testing, documentation, keyboard shortcuts, error messaging
**Confidence:** HIGH

## Summary

This research covers best practices for completing a 6-tab GUI workflow with comprehensive documentation. The phase focuses on cross-tab data flow verification, GROMACS export molecule ordering, keyboard shortcut design, documentation updates, and user guidance enhancements.

**Key findings:**
- Qt standard shortcuts favor **unified shortcuts** (Ctrl+S for save) over tab-specific shortcuts
- Tooltips should be **brief, helpful, and non-essential** (per NN/g guidelines)
- Documentation should follow the **Divio system**: tutorials, how-to guides, reference, explanation
- Integration testing requires **explicit data flow verification** between tabs
- GROMACS export ordering requires **centralized molecule collection** logic

**Primary recommendation:** Adopt unified keyboard shortcuts (Ctrl+S for export) with context-aware tab detection, use detailed tooltips for technical parameters, and structure documentation as tutorial-first with reference sections for Tab 4/5.

## Standard Stack

The established libraries/patterns for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | 6.x | Qt Python bindings | Official Qt for Python, cross-platform GUI |
| Qt Standard Shortcuts | 6.x | Platform-specific shortcuts | Ensures platform-native behavior |
| QMessageBox | Qt | Modal dialogs | Standard error/warning/information display |
| QKeySequence | Qt | Keyboard shortcuts | Handles platform differences automatically |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| QToolTip | Qt | Context-sensitive help | Brief, non-essential information |
| QScrollArea | Qt | Help dialog content | Long-form documentation |
| pytest | 7.x | Integration testing | Verify cross-tab data flows |

### Current State
| Component | Current Approach | Status |
|-----------|-----------------|--------|
| Keyboard shortcuts | Tab-specific (Ctrl+G/I/E/J/L/M) | **Needs redesign** |
| Tooltips | Multi-line with examples | **Good pattern** |
| Error messages | QMessageBox-based, user-friendly | **Good pattern** |
| Help dialog | Modal with scroll, sections | **Good structure** |
| README.md | CLI-heavy, 474 lines | **Needs GUI focus** |
| GUI guide | Tab 1-4 documented | **Needs Tab 4-5 sections** |

## Architecture Patterns

### Recommended Pattern: Unified Export Shortcuts

**What:** Single keyboard shortcut (Ctrl+S/Ctrl+E) that exports from currently active tab
**When to use:** Multi-tab applications with export functionality per tab
**Rationale:**
- Qt documentation shows Ctrl+S is standard for "Save" across platforms
- Reduces cognitive load (one shortcut to remember)
- Platform-native behavior (Windows/Linux/macOS all use Ctrl+S for save)
- Current tab-specific shortcuts (G/I/E/J/L/M) conflict with discoverability

**Implementation:**
```python
# Source: Qt standard shortcuts pattern
def _create_menu_bar(self):
    # Unified export shortcut
    export_action = file_menu.addAction("Export for GROMACS...")
    export_action.setShortcut("Ctrl+S")  # Standard save shortcut
    export_action.triggered.connect(self._on_export_current_tab)
    
def _on_export_current_tab(self):
    """Export from currently active tab."""
    current_tab = self.tab_widget.currentIndex()
    
    if current_tab == TabIndex.ICE:
        self._on_export_gromacs()
    elif current_tab == TabIndex.HYDRATE:
        self._on_export_hydrate_gromacs()
    elif current_tab == TabIndex.INTERFACE:
        self._on_export_interface_gromacs()
    elif current_tab == TabIndex.SOLUTE:
        self._on_export_solute_gromacs()
    elif current_tab == TabIndex.CUSTOM:
        self._on_export_custom_molecule_gromacs()
    elif current_tab == TabIndex.ION:
        self._on_export_ion_gromacs()
```

**Alternative: Tab-specific shortcuts with unified naming**
- Keep Ctrl+G/I/E/J/L/M but rename menu items consistently
- Tradeoff: More shortcuts to remember, but clearer tab association
- Use this if user studies show preference for explicit tab-specific shortcuts

### Pattern 2: Tooltip Depth Strategy

**What:** Adaptive tooltip depth based on parameter complexity
**When to use:** Applications with both simple and complex parameters

**Guidelines from NN/g:**
1. **Don't use tooltips for vital information** (must be visible on screen)
2. **Provide brief, helpful content** (avoid redundancy)
3. **Support mouse AND keyboard hover** (accessibility)
4. **Use tooltip arrows** when multiple elements nearby
5. **Be consistent** throughout the application

**Current tooltip pattern (good example):**
```python
# Source: interface_panel.py line 97
self.ice_thickness_input.setToolTip(
    "Thickness of each ice layer in nm (0.5–50).\n"
    "\n"
    "IMPORTANT: For slab mode, box_z must equal:\n"
    "  2 × ice_thickness + water_thickness\n"
    "\n"
    "Example: ice=3.0 nm, water=4.0 nm → box_z=10.0 nm"
)
```

**Recommendation for Tab 4/5:**
- **Solute concentration:** Show formula + example result (e.g., "0.6 M in 10 nm³ = 360 ion pairs")
- **Custom molecule .gro/.itp:** Show brief guidance + reference to docs (e.g., "Upload .gro (coordinates) and .itp (topology) files. See Help > Custom Molecules for format requirements.")

### Pattern 3: Documentation Structure (Divio System)

**What:** Four documentation types with distinct purposes
**When to use:** Any software documentation project

**The four types:**
1. **Tutorials** — Learning-oriented, step-by-step guides
2. **How-to guides** — Problem-oriented, practical steps
3. **Technical reference** — Information-oriented, API documentation
4. **Explanation** — Understanding-oriented, background concepts

**Application to QuickIce:**

| Type | Current | Recommended for v4.5 |
|------|---------|---------------------|
| Tutorials | Missing | Add "Getting Started" section with 5-minute workflow |
| How-to guides | GUI guide has workflow | Extend with Tab 4/5 specific scenarios |
| Reference | CLI reference, ranking | Add GROMACS export reference, molecule ordering docs |
| Explanation | README overview, principles | Keep, move CLI-heavy content to separate doc |

**README simplification:**
- Move CLI-heavy sections to `docs/cli-reference.md` (already exists)
- Keep README focused on: Overview, Installation, Quick Start (GUI), Screenshots
- Target length: ~300 lines (down from 474)

### Pattern 4: GROMACS Export Molecule Ordering

**What:** Enforce molecule ordering: SOL → hydrate guests → liquid solutes → custom molecules → ions
**When to use:** GROMACS topology file generation with multiple molecule types

**Implementation approach:**
```python
# Central molecule collection and ordering
class GROMACSExporter:
    def _collect_molecules_ordered(self, structure) -> list:
        """Collect molecules in GROMACS-standard order.
        
        Order: SOL → guests → solutes → custom → ions
        """
        molecules = []
        
        # 1. Water molecules (SOL)
        water_mols = [m for m in structure.molecules if m.type == "water"]
        molecules.extend(water_mols)
        
        # 2. Hydrate guests (CH4, THF, etc.)
        guest_mols = [m for m in structure.molecules if m.type == "guest"]
        molecules.extend(guest_mols)
        
        # 3. Liquid solutes
        solute_mols = [m for m in structure.molecules if m.type == "solute"]
        molecules.extend(solute_mols)
        
        # 4. Custom molecules
        custom_mols = [m for m in structure.molecules if m.type == "custom"]
        molecules.extend(custom_mols)
        
        # 5. Ions (Na+, Cl-)
        ions = [m for m in structure.molecules if m.type in ("Na+", "Cl-")]
        molecules.extend(ions)
        
        return molecules
```

**Verification:**
- Add integration test that counts molecules per type in exported .gro file
- Assert ordering matches specification
- Test with multi-type system (ice + water + solutes + ions)

### Pattern 5: Cross-Tab Data Flow Testing

**What:** Integration tests verifying data flows between tabs
**When to use:** Multi-tab applications with dependent workflows

**Test scenarios:**
```python
def test_ice_to_interface_flow():
    """Verify ice candidates flow from Tab 1 to Tab 3."""
    # Tab 1: Generate ice
    # Tab 3: Verify candidates available in dropdown
    assert len(interface_panel.candidate_dropdown.items()) > 0

def test_interface_to_solute_flow():
    """Verify interface structure passes to Tab 4."""
    # Tab 3: Generate interface
    # Tab 4: Verify liquid volume available
    assert solute_panel.get_liquid_volume() > 0

def test_interface_to_custom_flow():
    """Verify interface structure passes to Tab 5."""
    # Tab 3: Generate interface
    # Tab 5: Verify interface structure available
    assert custom_panel.has_interface_structure()

def test_custom_to_ion_flow():
    """Verify custom molecule result passes to Tab 6."""
    # Tab 5: Insert custom molecules
    # Tab 6: Verify custom molecules in structure
    assert ion_panel.has_custom_molecules()
```

### Anti-Patterns to Avoid

- **Shortcut conflict:** Don't assign Ctrl+E to export if it's already used for another action (current conflict: Ctrl+E = hydrate export)
- **Tooltip overuse:** Don't hide essential instructions in tooltips (per NN/g: vital info must be visible)
- **Inconsistent shortcuts:** Don't mix tab-specific and unified shortcuts without clear pattern
- **Documentation duplication:** Don't repeat content in README and GUI guide (use references instead)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keyboard shortcuts | Custom key handler | QKeySequence + QAction | Platform-native, handles modifiers automatically |
| Error dialogs | Custom popup widget | QMessageBox | Standard, accessible, user-friendly |
| Help dialog | Custom scroll widget | QDialog + QScrollArea | Standard pattern, maintains focus |
| Molecule ordering | Manual list sorting | Typed molecule collections | Type-safe, enforced ordering |
| Documentation structure | Ad-hoc sections | Divio system (4 types) | Proven structure, comprehensive coverage |

**Key insight:** Qt provides comprehensive patterns for GUI applications. Follow Qt conventions for shortcuts, dialogs, and tooltips to ensure platform-native behavior and accessibility.

## Common Pitfalls

### Pitfall 1: Keyboard Shortcut Conflicts

**What goes wrong:** Assigning shortcuts that conflict with platform standards or other actions
**Why it happens:** Developers choose shortcuts based on their keyboard layout, not cross-platform standards
**How to avoid:**
1. Use Qt's `QKeySequence.StandardKey` enum for standard actions
2. Check for conflicts with existing shortcuts in the application
3. Test on multiple platforms (Windows, macOS, Linux)

**Current conflicts in QuickIce:**
- Ctrl+S = Save PDB (left viewer) — conflicts with standard "Save" action
- Ctrl+E = Export hydrate — conflicts with standard "Export" if unified approach adopted

**Warning signs:** Users report shortcuts don't work as expected on their platform

### Pitfall 2: Inconsistent Tooltip Depth

**What goes wrong:** Some tooltips are minimal, others are verbose, creating unpredictable user experience
**Why it happens:** Different developers add tooltips without consistent guidelines
**How to avoid:**
1. Define tooltip depth strategy: minimal (labels), moderate (constraints), detailed (complex parameters)
2. Use consistent template: description + constraints + example
3. Review all tooltips for consistency

**Warning signs:** Users don't know whether to expect helpful tooltips or not

### Pitfall 3: Documentation Drift

**What goes wrong:** Documentation becomes outdated as features are added
**Why it happens:** No documentation update checklist in development workflow
**How to avoid:**
1. Include documentation task in every feature phase
2. Review README after each release for accuracy
3. Use screenshots as documentation checkpoints (screenshots must be current)

**Warning signs:** Users report documentation doesn't match application behavior

### Pitfall 4: Missing Cross-Tab Data Flow Verification

**What goes wrong:** Data doesn't flow correctly between tabs, but issue discovered late
**Why it happens:** Tabs developed independently, integration testing skipped
**How to avoid:**
1. Write integration tests for each data flow path
2. Test tab switching with intermediate states
3. Verify data persistence across tab switches

**Warning signs:** Null pointer exceptions when switching tabs, empty dropdowns

### Pitfall 5: GROMACS Molecule Ordering Errors

**What goes wrong:** Molecules appear in wrong order in .gro file, breaking GROMACS simulations
**Why it happens:** No explicit ordering logic, molecules collected in arbitrary order
**How to avoid:**
1. Implement centralized molecule ordering function
2. Add tests that verify ordering in exported files
3. Document ordering requirements in GROMACS export reference

**Warning signs:** GROMACS reports topology errors, simulation crashes

## Code Examples

### Unified Export Shortcut Implementation

```python
# Source: Qt standard shortcuts pattern + current main_window.py structure
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

def _create_menu_bar(self):
    """Create menu bar with unified export shortcuts."""
    menubar = self.menuBar()
    file_menu = menubar.addMenu("File")
    
    # Standard save action (unified export)
    export_action = QAction("Export for GROMACS...", self)
    export_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_S))  # Ctrl+S
    export_action.setStatusTip("Export current tab structure for GROMACS")
    export_action.triggered.connect(self._on_export_current_tab)
    file_menu.addAction(export_action)
    
    # Add "Export As..." submenu for tab-specific exports (optional)
    export_submenu = file_menu.addMenu("Export As...")
    
    export_submenu.addAction("Export Ice...", Qt.CTRL | Qt.Key_G, 
                             self._on_export_gromacs)
    export_submenu.addAction("Export Hydrate...", Qt.CTRL | Qt.Key_H,  # Changed from E
                             self._on_export_hydrate_gromacs)
    # ... other tabs
```

### Detailed Tooltip for Solute Concentration

```python
# Source: NN/g tooltip guidelines + current tooltip patterns
def _create_concentration_input(self):
    """Create solute concentration input with detailed tooltip."""
    layout = QHBoxLayout()
    
    self.concentration_input = QDoubleSpinBox()
    self.concentration_input.setSuffix(" M")
    self.concentration_input.setRange(0.0, 5.0)
    self.concentration_input.setDecimals(2)
    self.concentration_input.setSingleStep(0.1)
    self.concentration_input.setValue(0.6)  # Default: seawater
    
    # Detailed tooltip with formula + example
    self.concentration_input.setToolTip(
        "Solute concentration in mol/L (M).\n"
        "\n"
        "Formula: N_molecules = concentration × volume × 10⁻²⁴ × N_A\n"
        "where N_A = Avogadro's number (6.022×10²³)\n"
        "\n"
        "Example: 0.6 M in 10 nm³ → ~36 molecules\n"
        "Typical values: seawater ~0.6 M, drinking water <0.05 M"
    )
    
    layout.addWidget(QLabel("Concentration:"))
    layout.addWidget(HelpIcon(
        "Target concentration for solute insertion. "
        "The actual molecule count depends on available liquid volume. "
        "Seawater has ~0.6 M salt concentration."
    ))
    layout.addWidget(self.concentration_input)
    
    return layout
```

### GROMACS Export Ordering Test

```python
# Source: Testing pattern for molecule ordering verification
import pytest

def test_gromacs_export_molecule_ordering():
    """Test that GROMACS export produces correct molecule ordering."""
    from quickice.structure_generation import create_test_structure
    
    # Create structure with all molecule types
    structure = create_test_structure(
        n_water=1000,
        n_guests=10,
        n_solutes=50,
        n_custom=20,
        n_ions=30
    )
    
    # Export to GROMACS
    exporter = GROMACSExporter()
    gro_lines = exporter._export_gro_lines(structure)
    
    # Verify ordering
    molecule_types = []
    for line in gro_lines:
        if "SOL" in line:
            molecule_types.append("water")
        elif "CH4" in line or "THF" in line:
            molecule_types.append("guest")
        elif "SOLUTE" in line:
            molecule_types.append("solute")
        elif "CUSTOM" in line:
            molecule_types.append("custom")
        elif "NA" in line or "CL" in line:
            molecule_types.append("ion")
    
    # Assert ordering: water → guest → solute → custom → ion
    assert all(t == "water" for t in molecule_types[:1000])
    assert all(t == "guest" for t in molecule_types[1000:1010])
    assert all(t == "solute" for t in molecule_types[1010:1060])
    assert all(t == "custom" for t in molecule_types[1060:1080])
    assert all(t == "ion" for t in molecule_types[1080:])
```

### Documentation Structure Example

```markdown
# README.md (simplified structure)

## Overview
[Keep current overview, add GUI focus]

## Installation
[Keep current installation]

## Quick Start
[Replace CLI example with GUI workflow]
1. Launch GUI: `python -m quickice.gui`
2. Enter temperature and pressure
3. Click Generate
4. Export for GROMACS (Ctrl+S)

## Features
[Brief list with screenshots]
- Ice Generation (Tab 1)
- Hydrate Config (Tab 2)
- Interface Construction (Tab 3)
- Solute Insertion (Tab 4)
- Custom Molecules (Tab 5)
- Ion Insertion (Tab 6)

## Documentation
- **[GUI Guide](docs/gui-guide.md)** — Complete GUI documentation
- **[CLI Reference](docs/cli-reference.md)** — Command-line usage
- **[GROMACS Export](docs/gromacs-export.md)** — Export format and ordering

## Screenshots
[Current screenshots, updated for Tab 4/5]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tab-specific shortcuts | Unified shortcuts with context detection | Phase 35 (planned) | Reduces cognitive load, platform-native |
| CLI-focused README | GUI-focused README | Phase 35 | Matches v4–v4.5 development focus |
| Ad-hoc tooltips | Consistent tooltip strategy | Phase 35 | Predictable user experience |
| Manual testing | Integration tests for data flows | Phase 35 | Earlier bug detection |
| Implicit molecule ordering | Explicit ordering function | Phase 35 | Reliable GROMACS export |

**Deprecated/outdated:**
- Tab-specific export shortcuts (Ctrl+G/I/E/J/L/M): Replace with unified Ctrl+S or context-aware shortcuts
- CLI-heavy README sections: Move to docs/cli-reference.md
- Screenshot naming with tabX prefix: Remove prefix, use descriptive names

## Open Questions

### 1. Unified vs Tab-Specific Export Shortcut

**What we know:**
- Qt standard shortcuts favor Ctrl+S for "Save" across platforms
- Current approach uses tab-specific shortcuts (G/I/E/J/L/M)
- Ctrl+S currently assigned to "Save PDB" action

**What's unclear:**
- Whether users prefer unified shortcut (one to remember) or tab-specific (explicit association)
- How to handle "Save PDB" if Ctrl+S becomes "Export GROMACS"
- Whether to keep tab-specific shortcuts in "Export As..." submenu

**Recommendation:**
- Adopt unified Ctrl+S for GROMACS export (matches "Save" mental model)
- Reassign Ctrl+S from "Save PDB" to "Export GROMACS"
- Move "Save PDB" to Ctrl+Shift+S (already exists for right viewer)
- Add "Export As..." submenu for users who want tab-specific shortcuts
- User approval required after planning

### 2. Hydrate Export Shortcut Conflict

**What we know:**
- Ctrl+E currently assigned to "Export Hydrate"
- If unified export adopted, Ctrl+E becomes available
- Standard "Export" action in some applications uses Ctrl+E

**What's unclear:**
- Whether to repurpose Ctrl+E for other functionality
- Whether hydrate users have muscle memory for Ctrl+E

**Recommendation:**
- If unified export adopted, reassign hydrate to Ctrl+H (H for hydrate)
- Add to "Export As..." submenu for discoverability
- User approval required after planning

### 3. Solute/Custom Tooltip Detail Level

**What we know:**
- Current tooltips for interface panel are detailed (formula + example)
- Custom molecules require .gro/.itp file knowledge (technical users)

**What's unclear:**
- Whether to include .gro/.itp format guidance in tooltip or link to docs
- Balance between tooltip detail and documentation reference

**Recommendation:**
- **Solute concentration:** Show formula + example (detailed, scientific users)
- **Custom molecule:** Brief guidance + doc reference (technical users need full docs)
- User approval required after planning

### 4. Error Recovery Approach

**What we know:**
- Current error messages describe the problem (user-friendly)
- Some errors have obvious solutions (e.g., "Generate interface first")
- GROMACS terminology is acceptable (users know the domain)

**What's unclear:**
- Whether to add suggested fixes to all error messages
- Whether suggested fixes should be actionable buttons or text

**Recommendation:**
- Add suggested fixes to common errors (e.g., "Generate interface in Tab 3 first")
- Use text suggestions in QMessageBox (not buttons, keeps dialog simple)
- User approval required after planning

## Sources

### Primary (HIGH confidence)
- Qt 6 QKeySequence Documentation — https://doc.qt.io/qt-6/qkeysequence.html (standard shortcuts, platform conventions)
- NN/g Tooltip Guidelines — https://www.nngroup.com/articles/tooltip-guidelines/ (UX best practices)
- Divio Documentation System — https://documentation.divio.com/ (documentation structure)
- QuickIce codebase — Current implementation patterns (main_window.py, interface_panel.py, help_dialog.py)

### Secondary (MEDIUM confidence)
- Qt QMessageBox Documentation — https://doc.qt.io/qt-6/qmessagebox.html (modal dialog patterns)
- QuickIce README.md — Current documentation structure (474 lines, CLI-heavy)
- QuickIce GUI guide — docs/gui-guide.md (current GUI documentation)

### Tertiary (LOW confidence)
- None — All findings verified with primary sources or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Qt patterns well-documented, current codebase examined
- Architecture patterns: HIGH — Qt standard shortcuts, NN/g tooltip guidelines, Divio documentation system
- Pitfalls: HIGH — Based on Qt documentation and current codebase analysis
- Keyboard shortcuts: MEDIUM — Need user testing for unified vs tab-specific preference
- Documentation structure: HIGH — Divio system widely adopted
- GROMACS ordering: HIGH — Requirements clear, implementation straightforward
- Tooltip depth: MEDIUM — Need user feedback on detail level preferences

**Research date:** 2026-05-05
**Valid until:** 30 days (stable Qt patterns, but keyboard shortcut preferences may evolve with user feedback)
