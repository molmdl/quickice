# Phase 21: Update README, Docs, In-App Help, Tab 2 Tooltip Help - Research

**Researched:** 2026-04-09
**Domain:** Technical documentation update for v3.0 features, PySide6 tooltip/help patterns
**Confidence:** HIGH

## Summary

This phase updates all documentation artifacts to reflect the v3.0 interface construction feature (Phases 16-20). Five files need updating: README.md (346 lines, v2.0 only), README_bin.md (15 lines, references v2.0.0), docs/gui-guide.md (249 lines, v2.0 only), quickice/gui/help_dialog.py (117 lines, partially updated), and Tab 2 tooltips in quickice/gui/interface_panel.py (672 lines, basic tooltips exist).

The existing Phase 13 research established documentation patterns (cognitive funneling, screenshot organization, modal help dialogs). This phase extends those patterns to cover v3.0's Tab 2 workflow: three interface modes (slab/pocket/piece), box dimensions, phase-distinct visualization, and Ctrl+I export. The key challenge is adding Tab 2 content without bloating the README (CLI remains primary) while giving gui-guide.md comprehensive Tab 2 coverage.

**Primary recommendation:** Follow the "CLI-primary, GUI-secondary" pattern from Phase 13. Add brief Tab 2 mentions to README, expand gui-guide.md with full Tab 2 section, enhance help_dialog.py with mode descriptions, and enrich Tab 2 tooltips from short labels to educational descriptions.

## Standard Stack

The established tools/approaches for this documentation update:

### Core
| Tool/Pattern | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| PySide6 QToolTip | 6.x | Widget tooltips | Built-in Qt mechanism, hover-triggered |
| HelpIcon (custom) | existing | ? icon with enhanced tooltip | Already in view.py, used in interface_panel.py |
| Markdown | - | README and docs | Universal, GitHub renders automatically |
| QDialog (existing) | 6.x | In-app help modal | Already implemented as QuickReferenceDialog |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| setToolTip() | Basic widget hover help | Every input widget in interface_panel.py |
| HelpIcon widget | Enhanced ? icon tooltips | Complex inputs needing longer explanation |
| QLabel with setWordWrap | Multi-line help text | Help dialog workflow descriptions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Enhanced tooltips | WhatsThis mode | WhatsThis requires click+click, less discoverable than hover tooltips |
| Single README update | Separate CHANGELOG | CHANGELOG is version-tracking, not feature documentation |
| Help dialog update | Tooltip-only | Help dialog provides consolidated view, tooltips are per-field |

**No new packages needed** — all tools already exist in the codebase.

## Architecture Patterns

### Pattern 1: Documentation Update Hierarchy

The five deliverables form a hierarchy from brief → detailed:

```
README_bin.md    → Version number + brief feature mention (smallest change)
README.md        → Brief Tab 2 mention + link to gui-guide (minimal additions)
gui-guide.md     → Full Tab 2 section with workflow, modes, parameters (most content)
help_dialog.py   → Consolidated in-app reference with mode descriptions
interface_panel  → Per-field educational tooltips (contextual help)
```

**What:** Each document serves a different depth need
**When to use:** Always — don't duplicate full descriptions in README
**Rule:** README mentions existence and links. gui-guide explains. Help dialog summarizes. Tooltips contextualize.

### Pattern 2: README Update (Minimal Additions)

Following Phase 13's "cognitive funneling" and "CLI-primary" pattern:

```markdown
## Overview
# Update: Change "v2.0" → "v3.0", add "interface construction" to feature list

## Installation
# Update: Change comment "v2.0 GUI" → "v3.0 GUI" in environment setup

## Quick Start → GUI Usage
# Update: Change "v2.0" → "v3.0", add brief Tab 2 mention

## GROMACS Export → GUI Usage section
# ADD: Tab 2 GROMACS export (Ctrl+I) brief mention

## Documentation
# ADD: Link to updated gui-guide with v3.0 mention
```

**What:** Targeted insertions, not rewrites. Version bumps and brief additions.
**When to use:** README updates — keep it CLI-focused.

### Pattern 3: GUI Guide Tab 2 Section

New section structure for docs/gui-guide.md:

```markdown
## Interface Construction (Tab 2)

### Overview
- Purpose: Build ice-water interface structures from generated candidates
- Prerequisite: Generate ice candidates in Tab 1 first

### Workflow
1. Generate ice candidates in Tab 1 (Ice Generation)
2. Switch to Tab 2 (Interface Construction)
3. Select interface mode: Slab, Pocket, or Piece
4. Configure box dimensions and mode-specific parameters
5. Select candidate from dropdown (or click Refresh)
6. Click Generate Interface
7. View result in 3D viewer (ice=cyan, water=cornflower blue)
8. Export for GROMACS (Ctrl+I)

### Interface Modes

#### Slab Mode
- Layered ice-water geometry
- Parameters: ice thickness, water thickness (0.5-50 nm)
- Box Z typically elongated for slab interfaces

#### Pocket Mode
- Water cavity within ice matrix
- Parameters: pocket diameter (0.5-50 nm), pocket shape (sphere/ellipsoid)

#### Piece Mode
- Ice crystal piece embedded in water
- No additional parameters — dimensions derived from selected candidate

### Parameters
| Parameter | Range | Description |
|-----------|-------|-------------|
| Box X/Y/Z | 0.5-100 nm | Simulation box dimensions |
| Random seed | 1-999999 | Reproducibility seed |
| Ice thickness | 0.5-50 nm | Slab: ice layer thickness |
| Water thickness | 0.5-50 nm | Slab: water layer thickness |
| Pocket diameter | 0.5-50 nm | Pocket: cavity diameter |
| Pocket shape | sphere/ellipsoid | Pocket: cavity geometry |

### Visualization
- Phase-distinct coloring: ice = cyan, water = cornflower blue
- Line-based bonds (no ball-and-stick for Tab 2)
- H-bonds hidden by default in Tab 2
- Z-axis side-view camera orientation

### Export for GROMACS
- Ctrl+I or File → Export Interface for GROMACS
- Single combined SOL molecule type
- Ice 3→4 atom normalization at export time
- Files: interface_{mode}.gro, .top, .itp
```

**Source:** Existing gui-guide.md structure (Tab 1 sections), Phase 13 research patterns

### Pattern 4: Help Dialog Enhancement

Current help_dialog.py already has Tab 2 workflow (lines 69-73) but lacks mode descriptions. Enhancement:

```python
# Current (lines 62-73):
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

# Enhanced: Add mode descriptions and visualization info
workflow_text = QLabel(
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
```

**Key:** Keep help dialog concise (one screen). Add just enough to guide users to correct mode.

### Pattern 5: Tab 2 Tooltip Enhancement

Current tooltips in interface_panel.py are short labels. Enhancement approach:

**Current tooltips (short labels):**
```python
self.mode_combo.setToolTip("Select interface geometry type")
self.ice_thickness_input.setToolTip("Thickness of ice layer in nanometers")
self.pocket_diameter_input.setToolTip("Diameter of water cavity in nanometers")
```

**Enhanced tooltips (educational descriptions):**
```python
self.mode_combo.setToolTip(
    "Select interface geometry:\n"
    "• Slab — Layered ice-water interface (ice and water as flat layers)\n"
    "• Pocket — Water cavity enclosed within ice matrix\n"
    "• Piece — Ice crystal fragment embedded in liquid water"
)
self.ice_thickness_input.setToolTip(
    "Thickness of the ice layer in nanometers (0.5–50 nm).\n"
    "For slab interfaces, this defines how thick the ice region is\n"
    "along the Z-axis of the simulation box."
)
self.pocket_diameter_input.setToolTip(
    "Diameter of the water cavity in nanometers (0.5–50 nm).\n"
    "The cavity is carved out of the ice matrix.\n"
    "Water molecules are placed inside the spherical/ellipsoidal void."
)
```

**Rule for tooltips:**
- Input widgets (setToolTip): 1-3 lines explaining what the input controls + valid range
- HelpIcon widgets: More detailed explanation including physics context
- Both should be self-contained (user doesn't need to read docs to understand)

### Anti-Patterns to Avoid
- **Don't duplicate gui-guide content in README:** README links, gui-guide explains
- **Don't make tooltips too long:** QToolTip has no scrollbar; >5 lines becomes unusable
- **Don't forget HelpIcon vs setToolTip consistency:** HelpIcon text should be a superset of the setToolTip text for the same input
- **Don't add screenshots that don't exist:** No Tab 2 screenshots currently exist; either capture them or omit image references
- **Don't change existing Tab 1 docs unnecessarily:** Only add v3.0 context where needed

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip display | Custom popup widget | QToolTip + setToolTip() | Qt handles positioning, timing, platform conventions |
| Help icon | Custom click handler | HelpIcon (view.py) | Already exists, handles enterEvent + QToolTip.showText |
| Dialog layout | Custom scroll area | QLabel.setWordWrap + QVBoxLayout | Help dialog content fits one screen |
| Documentation structure | Ad-hoc sections | Cognitive funneling (Phase 13 pattern) | Proven readability |

**Key insight:** The codebase already has HelpIcon and the help dialog infrastructure. Enhancement is purely content, not infrastructure.

## Common Pitfalls

### Pitfall 1: Tooltip Text Too Long for QToolTip
**What goes wrong:** QToolTip has no scrollbar. Long tooltips get clipped or create huge popup windows.
**Why it happens:** Trying to put full documentation in a tooltip
**How to avoid:** Tooltips ≤ 3-4 lines. Use HelpIcon for longer explanations. Link to Help menu for full docs.
**Warning signs:** Tooltip text > 200 characters

### Pitfall 2: Inconsistent Version References
**What goes wrong:** Some files say v2.0, others v3.0, creating confusion about feature set
**Why it happens:** Incremental updates miss some version references
**How to avoid:** Grep all files for "v2.0", "v2.1", "2.0.0" before starting. Update ALL references systematically.
**Warning signs:** README says v3.0 but gui-guide header says v2.0

### Pitfall 3: Missing Ctrl+I in Keyboard Shortcuts
**What goes wrong:** Users don't discover Tab 2 GROMACS export because it's not in shortcuts list
**Why it happens:** Ctrl+I added in Phase 20 but shortcuts docs not updated
**How to avoid:** Every keyboard shortcut table (README, gui-guide, help_dialog) must include Ctrl+I
**Warning signs:** Shortcut section has Ctrl+G but not Ctrl+I

### Pitfall 4: Screenshots Don't Exist for Tab 2
**What goes wrong:** Documentation references `images/tab2-interface.png` but file doesn't exist
**Why it happens:** Writing docs before capturing screenshots
**How to avoid:** Either (a) capture screenshots first, or (b) omit image references for Tab 2 and add TODO comments. Current docs/images/ has 6 files, none are Tab 2.
**Warning signs:** Broken image links in rendered Markdown

### Pitfall 5: HelpIcon and setToolTip Text Mismatch
**What goes wrong:** HelpIcon says "X" but the widget's setToolTip says "Y", confusing users
**Why it happens:** Two separate tooltip mechanisms on the same row, edited independently
**How to avoid:** HelpIcon text should be a superset of the widget's setToolTip. Review both when editing either.
**Warning signs:** HelpIcon and setToolTip for the same input say different things

### Pitfall 6: GUI Guide Still Says "v2.0"
**What goes wrong:** docs/gui-guide.md header still says "v2.0" after updates
**Why it happens:** Forgot to update the version in the title/header of the file
**How to avoid:** Change the very first line of gui-guide.md: "This guide covers the QuickIce v2.0 GUI" → "v3.0"
**Warning signs:** File header version ≠ current version

## Code Examples

### README.md Targeted Update

```markdown
<!-- In Overview section, line 15-20 -->
QuickIce is a command-line tool with an optional GUI that generates plausible 
ice crystal structure candidates for given thermodynamic conditions. Given a 
temperature (K) and pressure (MPa), it:

1. **Identifies the ice polymorph** that would form under those conditions
2. **Generates candidate structures** using GenIce2
3. **Ranks candidates** by energy estimate, density match, and diversity
4. **Constructs ice-water interfaces** (v3.0: slab, pocket, or piece geometries)
5. **Outputs PDB files** and GROMACS-ready structure files

<!-- In GROMACS Export section, after GUI Usage subsection -->
### Interface GROMACS Export (Tab 2)

1. Generate ice candidates in Tab 1 first
2. Switch to Interface Construction tab (Tab 2)
3. Configure mode and parameters, then Generate Interface
4. **File → Export Interface for GROMACS** (Ctrl+I)

<!-- In Keyboard Shortcuts table (gui-guide.md) -->
| Ctrl+G | Export for GROMACS (Tab 1) |
| Ctrl+I | Export Interface for GROMACS (Tab 2) |
```

**Source:** Phase 13 README patterns, current README.md structure

### Tooltip Enhancement in interface_panel.py

```python
# Mode combo tooltip (line 205)
self.mode_combo.setToolTip(
    "Select interface geometry:\n"
    "• Slab — Layered ice-water interface\n"
    "• Pocket — Water cavity in ice matrix\n"  
    "• Piece — Ice fragment in liquid water"
)

# HelpIcon next to mode combo (line 207)
HelpIcon(
    "Interface geometry type. Slab creates flat layered ice-water interfaces "
    "(typical for surface studies). Pocket carves a water-filled cavity "
    "inside ice. Piece embeds an ice crystal fragment in liquid water."
)

# Box dimensions HelpIcon (line 218)
HelpIcon(
    "Simulation box dimensions in nanometers. For slab interfaces, "
    "use an elongated Z-axis to accommodate ice and water layers. "
    "X and Y should match the ice candidate's lateral dimensions."
)

# Seed tooltip (line 297)
self.seed_input.setToolTip(
    "Random seed for water molecule placement (1–999999).\n"
    "Same seed produces same interface structure for given inputs."
)

# Seed HelpIcon (line 299)
HelpIcon(
    "Integer seed for reproducible water molecule placement. "
    "Using the same seed with identical parameters produces identical "
    "interface structures. Change the seed to explore different configurations."
)
```

**Source:** Current interface_panel.py tooltip pattern, HelpIcon implementation in view.py

### gui-guide.md Tab 2 Section

```markdown
## Interface Construction (Tab 2)

The second tab builds ice-water interface structures from candidates 
generated in Tab 1. This is useful for molecular dynamics simulations 
of ice-water interfaces, confined water, or ice nucleation studies.

### Prerequisites

Generate ice candidates in Tab 1 (Ice Generation) before using Tab 2. 
The candidate dropdown in Tab 2 is populated from Tab 1's results.

### Interface Modes

QuickIce supports three interface geometries:

| Mode | Description | Use Case |
|------|-------------|----------|
| Slab | Layered ice-water interface | Surface melting/freezing studies |
| Pocket | Water cavity within ice matrix | Confined water studies |
| Piece | Ice crystal embedded in water | Ice nucleation/growth studies |

### Mode-Specific Parameters

#### Slab Parameters
- **Ice thickness** (0.5–50 nm): Thickness of the ice layer
- **Water thickness** (0.5–50 nm): Thickness of the liquid water layer
- Typical box: elongated Z-axis to accommodate both layers

#### Pocket Parameters
- **Pocket diameter** (0.5–50 nm): Diameter of the water cavity
- **Pocket shape**: Sphere or Ellipsoid

#### Piece Parameters
- No additional parameters — piece dimensions are derived from the 
  selected ice candidate
- An informational label shows the candidate dimensions

### Visualization

Tab 2 uses phase-distinct coloring:
- **Ice phase**: Cyan atoms with line-based bonds
- **Water phase**: Cornflower blue atoms with line-based bonds
- H-bonds are hidden by default in Tab 2

### Export for GROMACS

**File → Export Interface for GROMACS (Ctrl+I)**

Exported files use a single combined SOL molecule type:
- `interface_{mode}.gro` — Combined ice + water coordinates
- `interface_{mode}.top` — Topology with single moleculetype SOL
- `interface_{mode}.itp` — TIP4P-ICE force field parameters

Ice molecules are normalized from 3-atom (O, H, H) to 4-atom (OW, HW1, HW2, MW) 
TIP4P-ICE format at export time. Water molecules pass through as-is (already 4-atom).
```

**Source:** Current gui-guide.md structure, InterfaceConfig/InterfaceStructure types

### Help Dialog Workflow Section Enhancement

```python
# Enhanced workflow section in help_dialog.py _setup_ui()
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
```

**Source:** Current help_dialog.py lines 61-74

## State of the Art

| Old Approach (v2.0 docs) | Current Approach (v3.0 docs) | When Changed | Impact |
|---------------------------|-------------------------------|--------------|--------|
| Single-tab GUI | Two-tab GUI with interface construction | Phase 16-20 | Need Tab 2 docs everywhere |
| Ctrl+G only | Ctrl+G + Ctrl+I | Phase 20 | Shortcuts tables need Ctrl+I |
| "v2.0 GUI" references | "v3.0 GUI" references | This phase | All version strings need bump |
| Short tooltip labels | Educational tooltip descriptions | This phase | Better user guidance |
| One GROMACS export | Two GROMACS export paths | Phase 14 + 20 | Need to distinguish Tab 1 vs Tab 2 export |

**Deprecated/outdated references to update:**
- README.md line 57: "includes v2.0 GUI dependencies" → v3.0
- README.md line 76: "QuickIce v2.0 includes an optional GUI" → v3.0
- README_bin.md line 4: "quickice-v2.0.0-linux-x86_64.tar.gz" → v3.0.0
- gui-guide.md line 3: "covers the QuickIce v2.0 GUI" → v3.0
- gui-guide.md line 164: "QuickIce v2.1 adds direct GROMACS export" → v3.0
- gui-guide.md: No Ctrl+I in keyboard shortcuts table (line 186-191)

## Open Questions

1. **Tab 2 screenshots**
   - What we know: docs/images/ has 6 files, all Tab 1 screenshots
   - What's unclear: Should we capture Tab 2 screenshots in this phase or defer?
   - Recommendation: Capture at least one Tab 2 hero screenshot (interface-construction.png). If capturing is impractical, add `<!-- TODO: Add Tab 2 screenshot -->` comments and omit image references.

2. **Binary version in README_bin.md**
   - What we know: Currently says v2.0.0, needs v3.0.0
   - What's unclear: Will a v3.0.0 binary actually be distributed?
   - Recommendation: Update version string to v3.0.0 regardless — docs should match the codebase version, not the release pipeline state.

3. **Help dialog vs. tooltip content overlap**
   - What we know: Help dialog shows workflow, tooltips show per-field details
   - What's unclear: How much mode detail belongs in help dialog vs. just tooltip?
   - Recommendation: Help dialog: one-line mode summary + step-by-step workflow. Tooltips: mode-specific parameter explanations. gui-guide: full descriptions.

4. **gui-guide.md restructure scope**
   - What we know: Currently 249 lines covering only Tab 1
   - What's unclear: Should Tab 2 content be a new top-level section or subsection?
   - Recommendation: New top-level `## Interface Construction (Tab 2)` section after existing content. Update existing `## Export Options` to add Ctrl+I subsection. Add Ctrl+I to `## Keyboard Shortcuts` table.

## Sources

### Primary (HIGH confidence)
- Current README.md (346 lines) — examined 2026-04-09, all version references and structure mapped
- Current README_bin.md (15 lines) — examined 2026-04-09, version references mapped
- Current docs/gui-guide.md (249 lines) — examined 2026-04-09, structure and gaps mapped
- Current help_dialog.py (117 lines) — examined 2026-04-09, workflow content mapped
- Current interface_panel.py (672 lines) — examined 2026-04-09, all tooltip strings catalogued
- Phase 13 research (13-RESEARCH.md) — examined 2026-04-09, patterns and anti-patterns verified
- InterfaceConfig/InterfaceStructure types — examined 2026-04-09, data model verified

### Secondary (MEDIUM confidence)
- Current main_window.py (898 lines) — menu structure, shortcut bindings verified
- Current view.py HelpIcon implementation — tooltip mechanism verified
- Current interface_viewer.py — visualization behavior (colors, bonds, camera) verified
- Current export.py InterfaceGROMACSExporter — export filenames and flow verified

### Tertiary (LOW confidence)
- None — all findings verified against actual source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in codebase, no new dependencies
- Architecture: HIGH — patterns established in Phase 13, extending to Tab 2
- Pitfalls: HIGH — based on actual code inspection and version reference audit
- Tooltip approach: HIGH — HelpIcon and QToolTip patterns already proven in codebase
- README update scope: HIGH — all version references identified by line number

**Research date:** 2026-04-09
**Valid until:** 2027-04-09 (documentation patterns stable, version references may change with next release)
