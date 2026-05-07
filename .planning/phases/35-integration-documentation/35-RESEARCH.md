# Phase 35: Integration & Documentation - Research (Re-research)

**Researched:** 2026-05-07
**Domain:** GUI application integration testing, documentation, keyboard shortcuts, error messaging
**Confidence:** HIGH
**Previous research:** 2026-05-05 (updated after phases 32-34.4)

## Summary

This re-research updates integration and documentation requirements after completing phases 32-34.4. The phase now focuses on verifying the completed 6-tab workflow, updating outdated documentation (README, GUI guide, help dialog), fixing keyboard shortcut inconsistencies, and ensuring comprehensive user guidance for v4.5 features.

**Key findings:**
- Unified Ctrl+S export is **implemented** (Phase 35-01 complete)
- Tab order is **finalized**: Ice(0)→Hydrate(1)→Interface(2)→Custom(3)→Solute(4)→Ion(5)
- Help dialog has **outdated shortcuts** (Ctrl+E for hydrate, should be Ctrl+H)
- GUI guide lacks **Tab 3 (Custom) and Tab 4 (Solute) sections**
- README is **CLI-heavy** (474 lines, needs GUI focus per v4–v4.5 development)
- Screenshots **missing** for Custom (Tab 3), Solute (Tab 4), and updated Ion (Tab 5)
- Cross-tab data flow **needs integration tests** for new workflow chains

**Primary recommendation:** Fix help dialog shortcuts, add Tab 3/4 sections to GUI guide, simplify README to GUI focus, add tooltips for Custom/Solute controls, create user guide for .gro/.itp creation, and verify integration tests for Custom→Solute→Ion workflow chain.

## Standard Stack

The established libraries/patterns for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | 6.10.2 | Qt Python bindings | Official Qt for Python, cross-platform GUI |
| Qt Standard Shortcuts | 6.x | Platform-specific shortcuts | Ensures platform-native behavior |
| QMessageBox | Qt | Modal dialogs | Standard error/warning/information display |
| QKeySequence | Qt | Keyboard shortcuts | Handles platform differences automatically |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| QToolTip | Qt | Context-sensitive help | Brief, non-essential information |
| QScrollArea | Qt | Help dialog content | Long-form documentation |
| pytest | 7.x | Integration testing | Verify cross-tab data flows |

### Current State (Updated 2026-05-07)
| Component | Current Approach | Status |
|-----------|-----------------|--------|
| Tab order | Ice(0)→Hydrate(1)→Interface(2)→Custom(3)→Solute(4)→Ion(5) | ✓ **Finalized** (Phase 34.3) |
| Keyboard shortcuts | Unified Ctrl+S + tab-specific (Ctrl+G/H/I/L/M/J) | ✓ **Implemented** (Phase 35-01) |
| Hydrate shortcut | Ctrl+H (was Ctrl+E) | ✓ **Fixed** (Phase 35-01) |
| Help dialog shortcuts | Shows Ctrl+E for hydrate | ❌ **Outdated** (needs Ctrl+H) |
| Tooltips | Multi-line with examples, dynamic state-based | ✓ **Good pattern** |
| Error messages | QMessageBox-based, user-friendly | ✓ **Good pattern** |
| README.md | CLI-heavy, 474 lines | ❌ **Needs GUI focus** |
| GUI guide | Tab 1-4 documented (Ice, Hydrate, Interface, Ion) | ❌ **Missing Tab 3/4** |
| Integration tests | test_gromacs_molecule_ordering.py exists | ⚠️ **Needs Custom→Solute tests** |
| Screenshots | Tab 1/2/3/6 (old Ion) exist | ❌ **Missing Tab 3/4/5** |

## Architecture Patterns

### Pattern 1: Current Keyboard Shortcut State

**What:** Unified export shortcut + tab-specific shortcuts in submenu
**Status:** ✓ Implemented in Phase 35-01

**Current shortcuts (main_window.py lines 342-403):**
```python
# Unified export (Ctrl+S)
export_current_action.setShortcut("Ctrl+S")  # Exports from current tab
export_current_action.triggered.connect(self._on_export_current_tab)

# Tab-specific exports in "Export As..." submenu:
# Ctrl+G - Export Ice (GROMACS)
# Ctrl+H - Export Hydrate (GROMACS) ← Changed from Ctrl+E
# Ctrl+I - Export Interface (GROMACS)
# Ctrl+L - Export Solute (GROMACS)
# Ctrl+M - Export Custom Molecule (GROMACS)
# Ctrl+J - Export Ion (GROMACS)

# PDB/visualization exports:
# Ctrl+Alt+P - Save PDB (left viewer)
# Ctrl+Shift+S - Save PDB (right viewer)
# Ctrl+D - Save diagram
# Ctrl+Alt+S - Save viewport
```

**Help dialog inconsistency (help_dialog.py lines 68-75):**
```python
# OUTDATED: Still shows Ctrl+E for hydrate
"Ctrl+E — Export hydrate for GROMACS\n"  # ← Should be Ctrl+H
```

**Action required:** Update help_dialog.py to match current shortcuts

### Pattern 2: Current Tab Structure

**What:** Finalized tab order after Phase 34.3 swap
**Status:** ✓ Documented in constants.py

**Tab positions (TabIndex enum):**
```python
# Source: quickice/gui/constants.py lines 9-28
class TabIndex(IntEnum):
    ICE = 0          # Ice Generation tab
    HYDRATE = 1      # Hydrate Config tab
    INTERFACE = 2    # Interface Construction tab
    CUSTOM = 3       # Custom Molecule tab (Phase 34)
    SOLUTE = 4       # Solute Insertion tab (Phase 33)
    ION = 5          # Ion Insertion tab
```

**GUI guide inconsistency (docs/gui-guide.md lines 26-30):**
```markdown
The main window is divided into four tabs:
- Tab 1 (Ice Generation)
- Tab 2 (Hydrate Config)
- Tab 3 (Interface Construction)  ← Now Tab 3 is Custom Molecule
- Tab 4 (Ion Insertion)           ← Now Tab 4 is Solute, Ion is Tab 5
```

**Action required:** Update GUI guide to reflect 6-tab structure with correct numbering

### Pattern 3: Tooltip Depth Strategy

**What:** Adaptive tooltip depth based on parameter complexity
**When to use:** Applications with both simple and complex parameters

**Current tooltip pattern (good examples from solute_panel.py):**
```python
# Source: solute_panel.py lines 171-176
conc_layout.addWidget(HelpIcon(
    "Solute concentration in mol/L (M).\n"
    "Typical values:\n"
    "• CH4 in hydrates: ~0.05-0.10 M\n"
    "• THF in hydrates: ~0.05-0.20 M"
))

# Source: custom_molecule_panel.py lines 101-104
generate_row.addWidget(HelpIcon(
    "Generate custom molecule structure with configured placement.\n"
    "Requires valid .gro and .itp files."
))
```

**Recommendation for Tab 3 (Custom Molecule):**
- **File upload:** Show brief guidance + reference to docs (e.g., "Upload .gro (coordinates) and .itp (topology) files. See Help > Custom Molecules for format requirements.")
- **Placement mode:** Explain Random vs Custom mode tradeoffs
- **Rotation angles:** Show Euler angle convention (ZXZ)

**Recommendation for Tab 4 (Solute):**
- **Concentration:** Current tooltip is good (formula + typical values)
- **Source dropdown:** Explain Interface vs Custom Molecule source
- **Molecule count preview:** Already good (shows real-time calculation)

**Decision needed:** User approval on tooltip detail level after planning

### Pattern 4: Documentation Structure (Divio System)

**What:** Four documentation types with distinct purposes
**When to use:** Any software documentation project

**Application to QuickIce v4.5:**

| Type | Current | Required for v4.5 |
|------|---------|------------------|
| Tutorials | Missing | Add "Getting Started" section with 6-tab workflow |
| How-to guides | GUI guide has workflows | Extend with Custom Molecule and Solute scenarios |
| Reference | CLI reference, ranking | Add GROMACS export reference, .gro/.itp format guide |
| Explanation | README overview | Keep, move CLI-heavy content to separate doc |

**README simplification strategy:**
- Move CLI-heavy sections to `docs/cli-reference.md` (already exists)
- Keep README focused on: Overview, Installation, Quick Start (GUI), Features, Screenshots
- Target length: ~300 lines (down from 474)
- Add v4.5 features to Overview: Custom Molecules, Solute Insertion

**GUI guide extension:**
- Add Tab 3 (Custom Molecule Upload) section
- Add Tab 4 (Solute Insertion) section
- Update Tab 5 (Ion Insertion) with source dropdown explanation
- Update keyboard shortcuts table (Ctrl+H for hydrate)

**Help dialog enhancement:**
- Fix keyboard shortcuts (Ctrl+E → Ctrl+H)
- Add Custom Molecule workflow section
- Add Solute Insertion workflow section
- Update tab numbering in workflow steps

**Decision needed:** User approval on README outline and GUI guide structure after planning

### Pattern 5: Cross-Tab Data Flow Testing

**What:** Integration tests verifying data flows between tabs
**When to use:** Multi-tab applications with dependent workflows

**Existing tests:**
- `test_gromacs_molecule_ordering.py` — Verifies molecule ordering in exports (✓ Phase 35-01)
- `test_integration_v35.py` — CLI interface generation tests (v3.5 features)
- `test_custom_molecule.py` — Custom molecule rendering tests
- `test_solute_insertion.py` — Solute insertion tests

**Required new tests:**
1. **Custom → Solute workflow chain:**
   - Generate custom molecules in Tab 3
   - Switch to Tab 4, select "Custom Molecule" source
   - Verify custom molecule structure available in solute panel
   
2. **Solute → Ion workflow chain:**
   - Insert solutes in Tab 4
   - Switch to Tab 5, select appropriate source
   - Verify solute molecules in structure for ion insertion

3. **Full workflow chain:**
   - Ice → Interface → Custom → Solute → Ion
   - Verify each step passes correct data to next tab

**Test pattern:**
```python
def test_custom_to_solute_workflow():
    """Verify Custom Molecule structure flows to Solute tab."""
    # Tab 3: Generate custom molecules
    main_window._on_generate_custom_molecules()
    
    # Tab 4: Select Custom Molecule source
    main_window.solute_panel.source_combo.setCurrentText("Custom Molecule")
    
    # Verify custom molecule structure available
    assert main_window.solute_panel._custom_molecule_available
    assert main_window.solute_panel.get_liquid_volume() > 0
```

### Pattern 6: GROMACS Export Molecule Ordering

**What:** Enforce molecule ordering: SOL → hydrate guests → liquid solutes → custom molecules → ions
**Status:** ✓ Implemented and tested (Phase 35-01)

**Verification tests exist:**
- `test_solute_molecule_ordering()` — SOL → CH4_LIQ ordering
- `test_custom_molecule_ordering()` — SOL → custom molecules ordering
- `test_combined_ordering()` — SOL → CH4 → custom molecules ordering
- `test_itp_bundling()` — Verifies .itp files bundled correctly

**No action required:** Molecule ordering tests are complete

### Anti-Patterns to Avoid

- **Inconsistent documentation:** Help dialog shows Ctrl+E but code uses Ctrl+H
- **Outdated screenshots:** Screenshots must match current UI (Tab 3/4/5 missing)
- **Missing tab documentation:** GUI guide lacks Custom/Solute tabs
- **CLI-heavy README:** v4–v4.5 development focused on GUI, but README still CLI-heavy
- **Incomplete integration tests:** Custom→Solute workflow chain not tested

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keyboard shortcuts | Custom key handler | QKeySequence + QAction | Platform-native, handles modifiers automatically |
| Error dialogs | Custom popup widget | QMessageBox | Standard, accessible, user-friendly |
| Help dialog | Custom scroll widget | QDialog + QScrollArea | Standard pattern, maintains focus |
| Documentation structure | Ad-hoc sections | Divio system (4 types) | Proven structure, comprehensive coverage |
| Integration tests | Manual verification | pytest + QApplication | Automated, repeatable, catches regressions |

**Key insight:** Qt provides comprehensive patterns for GUI applications. Follow Qt conventions for shortcuts, dialogs, and tooltips to ensure platform-native behavior and accessibility.

## Common Pitfalls

### Pitfall 1: Documentation Drift After Tab Reorder

**What goes wrong:** Documentation references old tab numbers after tab order change
**Why it happens:** Tab order changed in Phase 34.3, but documentation not updated
**Current examples:**
- GUI guide shows Tab 3 = Interface (now Tab 3 = Custom)
- GUI guide shows Tab 4 = Ion (now Tab 4 = Solute, Ion = Tab 5)
- Help dialog workflow steps reference old tab numbers

**How to avoid:**
1. Update all documentation immediately after tab reorder
2. Add documentation update checklist to tab reorder tasks
3. Use TabIndex enum names in documentation, not hardcoded numbers

**Warning signs:** Users confused about tab positions, workflow steps reference wrong tabs

### Pitfall 2: Keyboard Shortcut Documentation Out of Sync

**What goes wrong:** Help dialog shows old shortcuts after code changes
**Why it happens:** Code updated (Ctrl+E → Ctrl+H) but help text not updated
**Current example:**
- main_window.py: `export_hydrate_action.setShortcut("Ctrl+H")`
- help_dialog.py: `"Ctrl+E — Export hydrate for GROMACS\n"`

**How to avoid:**
1. Include help dialog update in keyboard shortcut change tasks
2. Add verification step: run app, check Help menu, compare to code
3. Use single source of truth for shortcut strings (constants or config)

**Warning signs:** Users report shortcuts in help don't work

### Pitfall 3: Missing Screenshots for New Tabs

**What goes wrong:** Documentation lacks screenshots for new features
**Why it happens:** Screenshots taken early, new tabs added later
**Current gaps:**
- No screenshot for Tab 3 (Custom Molecule Upload)
- No screenshot for Tab 4 (Solute Insertion)
- Tab 5 (Ion) screenshot is old (shows old position as Tab 4)

**How to avoid:**
1. Create screenshot checklist for each new tab
2. Include screenshot task in each phase
3. Use human checkpoint: provide list of required screenshots, user takes them

**Warning signs:** Documentation text references missing screenshots

### Pitfall 4: CLI-Heavy README in GUI-Focused Release

**What goes wrong:** README emphasizes CLI but development focused on GUI
**Why it happens:** README written for v1 CLI, not updated for v4–v4.5 GUI focus
**Current state:**
- README has extensive CLI sections (Quick Start, CLI Options, More Examples)
- GUI mentioned only briefly in "GUI Usage" section
- v4.5 features (Custom Molecules, Solute Insertion) not in README

**How to avoid:**
1. Reorganize README to match development focus (v4–v4.5 = GUI)
2. Move CLI sections to dedicated CLI reference document
3. Add v4.5 features to Overview and Quick Start

**Warning signs:** Users skip README because it doesn't match GUI experience

### Pitfall 5: Missing Integration Tests for Workflow Chains

**What goes wrong:** Workflow chains work manually but break after refactoring
**Why it happens:** Only unit tests exist, no cross-tab integration tests
**Current gap:**
- Custom → Solute workflow chain untested
- Solute → Ion workflow chain untested
- Full 6-tab workflow chain untested

**How to avoid:**
1. Write integration tests for each workflow chain
2. Test tab switching with intermediate states
3. Verify data persistence across tab switches

**Warning signs:** Bugs discovered late in release cycle, during user testing

## Code Examples

### Help Dialog Shortcut Fix

```python
# Source: help_dialog.py lines 68-75 (NEEDS UPDATE)
# BEFORE:
shortcuts_text = QLabel(
    "Enter — Generate structures\n"
    "Escape — Cancel generation\n"
    "Ctrl+S — Save PDB (left viewer)\n"  # ← OUTDATED
    "Ctrl+Shift+S — Save PDB (right viewer)\n"
    "Ctrl+D — Save phase diagram\n"
    "Ctrl+G — Export for GROMACS\n"       # ← INCOMPLETE
    "Ctrl+I — Export interface for GROMACS\n"
    "Ctrl+E — Export hydrate for GROMACS\n"  # ← WRONG: should be Ctrl+H
    "Ctrl+J — Export ions for GROMACS\n"
    "Ctrl+Alt+S — Save viewport screenshot"
)

# AFTER (CORRECT):
shortcuts_text = QLabel(
    "Enter — Generate structures\n"
    "Escape — Cancel generation\n"
    "Ctrl+S — Export current tab for GROMACS (unified)\n"  # ← UPDATED
    "Ctrl+Alt+P — Save PDB (left viewer)\n"  # ← UPDATED
    "Ctrl+Shift+S — Save PDB (right viewer)\n"
    "Ctrl+D — Save phase diagram\n"
    "Ctrl+Alt+S — Save viewport screenshot\n"
    "\n"
    "Tab-specific exports (Export As... menu):\n"
    "Ctrl+G — Export Ice for GROMACS\n"
    "Ctrl+H — Export Hydrate for GROMACS\n"  # ← FIXED
    "Ctrl+I — Export Interface for GROMACS\n"
    "Ctrl+L — Export Solute for GROMACS\n"  # ← NEW
    "Ctrl+M — Export Custom Molecule for GROMACS\n"  # ← NEW
    "Ctrl+J — Export Ions for GROMACS"
)
```

### GUI Guide Tab Structure Update

```markdown
# Source: docs/gui-guide.md lines 26-30 (NEEDS UPDATE)

## BEFORE (OUTDATED):
The main window is divided into four tabs:
- **Tab 1 (Ice Generation)**: Interactive phase diagram, input controls, and 3D viewer
- **Tab 2 (Hydrate Config)**: Generate clathrate hydrate structures with guest molecules
- **Tab 3 (Interface Construction)**: Build ice-water interfaces for MD simulations
- **Tab 4 (Ion Insertion)**: Insert NaCl ions into liquid water regions

## AFTER (CORRECT):
The main window is divided into six tabs:
- **Tab 1 (Ice Generation)**: Interactive phase diagram, input controls, and 3D viewer
- **Tab 2 (Hydrate Config)**: Generate clathrate hydrate structures with guest molecules
- **Tab 3 (Interface Construction)**: Build ice-water interfaces for MD simulations
- **Tab 4 (Custom Molecule Upload)**: Upload and place custom molecules in interface structures
- **Tab 5 (Solute Insertion)**: Insert solutes (CH₄, THF) into liquid water regions
- **Tab 6 (Ion Insertion)**: Insert NaCl ions into liquid water regions

Note: Tab order changed in v4.5 to enable Custom → Solute → Ion workflow chain.
```

### Integration Test for Custom → Solute Workflow

```python
# Source: New test pattern for workflow chains
import pytest
from PySide6.QtWidgets import QApplication
from quickice.gui.main_window import MainWindow

def test_custom_to_solute_workflow(qtbot):
    """Verify Custom Molecule structure flows to Solute tab.
    
    Workflow chain: Tab 3 (Custom) → Tab 4 (Solute)
    """
    # Setup
    app = QApplication.instance() or QApplication([])
    main_window = MainWindow()
    
    # Generate custom molecules in Tab 3
    main_window.tab_widget.setCurrentIndex(3)  # Custom tab
    # ... upload valid .gro and .itp files
    # ... generate custom molecules
    qtbot.wait(1000)  # Wait for generation
    
    # Verify custom molecule structure available
    assert main_window._current_custom_molecule_result is not None
    
    # Switch to Tab 4 (Solute)
    main_window.tab_widget.setCurrentIndex(4)  # Solute tab
    
    # Select Custom Molecule source
    main_window.solute_panel.source_combo.setCurrentText("Custom Molecule")
    
    # Verify custom molecule availability in solute panel
    assert main_window.solute_panel._custom_molecule_available
    assert main_window.solute_panel.get_liquid_volume() > 0
    
    # Verify Insert button is enabled
    assert main_window.solute_panel.insert_button.isEnabled()
```

### README Simplification Outline

```markdown
# README.md (simplified structure for v4.5)

## Overview
[Keep current overview, add v4.5 features]
- Custom Molecule Upload (Tab 3)
- Solute Insertion (Tab 4)
- Enhanced Ion Insertion (Tab 5)

## Installation
[Keep current installation]

## Quick Start
[Replace CLI-heavy examples with GUI workflow]

### GUI Quick Start
1. Launch GUI: `python -m quickice.gui`
2. Enter temperature and pressure
3. Click Generate
4. Export for GROMACS (Ctrl+S)

### Basic Workflow
[Ice → Hydrate → Interface → Custom → Solute → Ion chain]

## Features
[Brief list with screenshots]
- Ice Generation (Tab 1)
- Hydrate Config (Tab 2)
- Interface Construction (Tab 3)
- Custom Molecule Upload (Tab 4) ← NEW
- Solute Insertion (Tab 5) ← NEW
- Ion Insertion (Tab 6)

## Documentation
- **[GUI Guide](docs/gui-guide.md)** — Complete GUI documentation
- **[CLI Reference](docs/cli-reference.md)** — Command-line usage
- **[GROMACS Export](docs/gromacs-export.md)** — Export format and molecule ordering

## Screenshots
[Current screenshots + Tab 3/4/5 screenshots]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tab-specific shortcuts (Ctrl+G/I/E/J/L/M) | Unified Ctrl+S + submenu | Phase 35-01 | Reduces cognitive load, platform-native |
| Tab order: Ice→Hydrate→Interface→Ion→Custom→Solute | Tab order: Ice→Hydrate→Interface→Custom→Solute→Ion | Phase 34.3 | Enables Custom→Solute→Ion workflow |
| Hydrate export Ctrl+E | Hydrate export Ctrl+H | Phase 35-01 | More intuitive (H for hydrate) |
| CLI-focused README | GUI-focused README | Phase 35 (planned) | Matches v4–v4.5 development focus |
| Manual testing | Integration tests for workflow chains | Phase 35 (planned) | Earlier bug detection |

**Deprecated/outdated:**
- Help dialog showing Ctrl+E for hydrate (must update to Ctrl+H)
- GUI guide showing 4-tab structure (must update to 6 tabs)
- GUI guide showing Tab 4 = Ion (must update to Tab 4 = Solute, Ion = Tab 5)
- README Quick Start using CLI examples (must update to GUI workflow)

## Open Questions

### 1. README Reorganization Scope

**What we know:**
- README is 474 lines, CLI-heavy
- v4–v4.5 development focused on GUI
- User feedback: "Simplify to match latest development"

**What's unclear:**
- Exact sections to keep/move/condense
- Whether to keep CLI examples at all or move entirely to CLI reference
- How much v4.5 feature detail to add

**Recommendation:**
- Move "CLI Options" and "More Examples" to CLI reference
- Keep "Quick Start" but replace CLI with GUI workflow
- Add v4.5 features to Overview (Custom Molecules, Solute Insertion)
- Target ~300 lines
- User approval required after planning

### 2. GUI Guide Tab 3/4 Section Structure

**What we know:**
- GUI guide currently has Tab 1-4 (Ice, Hydrate, Interface, Ion)
- Missing Tab 3 (Custom) and Tab 4 (Solute)
- Tab 5 (Ion) needs source dropdown explanation

**What's unclear:**
- Level of detail for Custom Molecule section (.gro/.itp format guidance?)
- Level of detail for Solute section (concentration formula details?)
- Whether to add separate user guide for .gro/.itp creation

**Recommendation:**
- Custom Molecule section: Workflow steps + parameter explanations + link to .gro/.itp guide
- Solute section: Workflow steps + concentration calculation explanation
- Create separate "docs/custom-molecule-guide.md" for .gro/.itp format requirements
- User approval required after planning

### 3. User Guide for .gro/.itp Creation

**What we know:**
- Custom molecules require valid .gro and .itp files
- GROMACS users know the format, but need QuickIce-specific guidance
- MoleculetypeRegistry requires consistent residue naming

**What's unclear:**
- Whether to include in GUI guide, separate doc, or in-app help
- How much GROMACS format detail to include
- Whether to link to GROMACS documentation

**Recommendation:**
- Create `docs/custom-molecule-guide.md` with:
  - Required .gro format (residue name in columns 6-10)
  - Required .itp format ([ moleculetype ] section)
  - Naming conventions (residue name consistency)
  - Example files for common molecules
  - Links to GROMACS documentation
- Link from GUI guide and tooltips
- User approval required after planning

### 4. Tooltip Detail Level

**What we know:**
- Current tooltips are detailed (multi-line with examples)
- Custom molecule users are technical (know GROMACS)
- Solute users may be less technical (concentration-based)

**What's unclear:**
- Balance between tooltip detail and documentation reference
- Whether to include .gro/.itp format hints in tooltips

**Recommendation:**
- **Custom molecule tooltips:** Brief + doc reference (technical users need full docs)
- **Solute tooltips:** Detailed with formula (scientific users need calculation clarity)
- User approval required after planning

### 5. Screenshot Naming Convention

**What we know:**
- Current screenshots use `tabX-` prefix (e.g., `tab2-hydrate-panel.png`)
- Tab reordering makes this confusing
- User requested: "Remove tabX prefix from figure filenames"

**What's unclear:**
- New naming convention (descriptive vs. tab-agnostic)
- Whether to rename existing screenshots

**Recommendation:**
- Use descriptive names: `quickice-v4-gui.png`, `hydrate-panel.png`, `custom-molecule-panel.png`
- Rename existing screenshots during this phase for consistency
- User approval required after planning

## Sources

### Primary (HIGH confidence)
- Qt 6 QKeySequence Documentation — https://doc.qt.io/qt-6/qkeysequence.html (standard shortcuts, platform conventions)
- NN/g Tooltip Guidelines — https://www.nngroup.com/articles/tooltip-guidelines/ (UX best practices)
- Divio Documentation System — https://documentation.divio.com/ (documentation structure)
- QuickIce codebase — Current implementation patterns (main_window.py, help_dialog.py, solute_panel.py, custom_molecule_panel.py)
- QuickIce constants.py — TabIndex enum with finalized tab order

### Secondary (MEDIUM confidence)
- Qt QMessageBox Documentation — https://doc.qt.io/qt-6/qmessagebox.html (modal dialog patterns)
- QuickIce README.md — Current documentation structure (474 lines, CLI-heavy)
- QuickIce GUI guide — docs/gui-guide.md (current GUI documentation, missing Tab 3/4)
- Phase 35-01 SUMMARY.md — Unified export implementation details
- Phase 34.3 SUMMARY.md — Tab order swap rationale

### Tertiary (LOW confidence)
- None — All findings verified with primary sources or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Qt patterns well-documented, current codebase examined
- Architecture patterns: HIGH — Current state verified in code (main_window.py, help_dialog.py, constants.py)
- Pitfalls: HIGH — Based on current codebase analysis and documentation gaps
- Keyboard shortcuts: HIGH — Implemented in Phase 35-01, verified in code
- Documentation structure: HIGH — Divio system widely adopted, gaps identified
- Integration tests: MEDIUM — Pattern established, new tests need implementation
- Tooltip depth: MEDIUM — Need user feedback on detail level preferences

**Research date:** 2026-05-07
**Valid until:** 30 days (stable Qt patterns, but keyboard shortcut documentation may need updates if shortcuts change)
**Previous research:** 2026-05-05 (updated after phases 32-34.4)
