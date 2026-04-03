# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface  
**Current Focus:** v2.0 GUI Application - Phase 13 complete, ready for Phase 12

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions

**Current focus:** v2.0 GUI Application - Transforming CLI tool to desktop GUI

**Tech stack for v2.0:**
- PySide6 >= 6.9.3 (LGPL, MIT-compatible)
- VTK >= 9.5.2 (BSD-licensed)
- Matplotlib Qt backend
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v2.0 (GUI Application) |
| Phase | Phase 12 - Packaging & Distribution |
| Plan | 2 of 4 in current phase |
| Status | In progress |
| Last activity | 2026-04-04 - Completed 12-03-PLAN.md |

**Progress:** ████████████████████ 97% (63 of 65 plans across v2.0)

---

## v2.0 Phase Overview

### Phase 8: GUI Infrastructure + Core Input (COMPLETE ✓)

**Goal:** Users can enter temperature, pressure, and molecule count parameters and trigger ice structure generation with progress feedback

**Requirements:** 10 (INPUT-01 to INPUT-05, PROGRESS-01 to PROGRESS-04, UX-01)

**Key deliverables:**
- PySide6 main window with input panel
- Temperature/pressure/molecule count textboxes with validation
- Generate button with progress bar
- Status text during generation
- Cancel button support
- Error dialogs for failures
- Keyboard shortcuts (Enter to generate, Escape to cancel)

**Status:** Complete - all 4 plans executed

### Phase 9: Interactive Phase Diagram (COMPLETE ✓)

**Goal:** Users can visually select thermodynamic conditions by clicking on an mouse-interactive phase diagram

**Requirements:** 4 (DIAGRAM-01 to DIAGRAM-04)

**Key deliverables:**
- PhaseDiagramWidget with 12-phase ice diagram
- Hover for live T,P coordinates
- Click to select coordinates and detect phase
- MainWindow integration with split view layout
- Diagram clicks populate input fields
- Input field changes update marker on diagram

**Status:** Complete - 5/5 plans executed, user approved verification

### Phase 10: 3D Molecular Viewer (COMPLETE ✓)

**Goal:** Users can view and interact with generated ice structures in a 3D viewport

**Requirements:** 9 (VIEWER-01 to VIEWER-05, ADVVIZ-01 to ADVVIZ-04)

**Key deliverables:**
- VTK-based molecular viewer with ball-and-stick rendering
- Representation toggle (VDW, Ball-and-stick, Stick)
- H-bond dashed line visualization
- Unit cell wireframe box
- Auto-rotation animation
- Dual viewport for candidate comparison
- Camera synchronization between viewports
- Toolbar integration with MainWindow
- Collapsible info panel for logs

**Note:** ADVVIZ-05 (color-by-property) not implemented per user decision.

**Status:** Complete - all 6 plans executed, verification passed

**Issues Fixed:**
- SetLattice TypeError (vtkMatrix3x3 requirement)
- Separate empty window (QLabel parent)
- Candidate selector connection

### Phase 11: Save/Export + Information (COMPLETE ✓)

**Goal:** Users can export results to standard formats and access scientific information

**Requirements:** 7 (EXPORT-01 to EXPORT-03, INFO-01 to INFO-04)

**Key deliverables:**
- PDBExporter with native file dialog, overwrite protection
- DiagramExporter for PNG/SVG phase diagram images
- ViewportExporter for 3D scene screenshots
- Menu bar with File menu and keyboard shortcuts (Ctrl+S, Ctrl+D, Ctrl+Shift+S)
- HelpIcon class for input field tooltips
- Phase info display in log panel with citations
- Candidate selector for export selection

**Notes:**
- INFO-02 (hover tooltip) deferred — existing T,P display sufficient
- INFO-04 (in-app manual) deferred to Phase 13

**Status:** Complete - 4/4 plans executed, verification passed (5/7 must-haves, 2 deferred by design)

### Phase 12: Packaging & Distribution

**Goal:** Users receive standalone executable with all dependencies bundled, with verified license compliance

**Requirements:** 2 (PACKAGE-01, PACKAGE-02)

**Status:** Ready to begin - Phase 13 complete, documentation ready for packaging

### Phase 13: Update README and Documentation After Finishing the GUI (COMPLETE ✓)

**Goal:** Users and developers have comprehensive, up-to-date documentation reflecting the v2.0 GUI application

**Requirements:** 4 (documentation coverage)

**Key deliverables:**
- Updated README.md with System Requirements (GLIBC 2.28+ for Linux, Windows 10/11)
- GUI Usage subsection with launch instructions
- docs/gui-guide.md (221 lines) with comprehensive GUI documentation
- docs/images/ folder for screenshots
- QuickReferenceDialog class for in-app help (INFO-04)
- Help menu integration in MainWindow

**Status:** Complete - all 4 plans executed, verification passed (5/5 must-haves)

---

## Milestone History

### v1.1 Hotfix (Shipped 2026-03-31)

**Phase:** 7.1 - Fix Performance & Critical Bugs
**Plans:** 4 of 6 (7.1-04 discarded, 7.1-06 deferred)

**Fixes applied:**
- Ice XV pressure range corrected (950-2100 MPa)
- Ice Ic checked before Ice Ih fallback
- Path traversal protection added
- O(n²)→O(n log n) KDTree optimization
- Exception handling with proper logging

**Verification:** 10/10 must-haves verified

### v1.0 MVP (Shipped 2026-03-29)

**Phases:** 9 (01-07 + 05.1 + 07.1)
**Plans:** 30+
**Code:** ~7,151 lines Python

---

## Known Issues

### v2.0 Technical Considerations

1. **UI Threading:** GenIce generation must run in QThread to avoid freezing main UI
2. **Progress Callbacks:** GenIce may not expose granular progress - may need wrapper estimation
3. **VTK Integration:** Need to verify molecular rendering API for ball-and-stick with colors
4. **Cross-Platform:** Use pathlib for all file operations

### v1.x Technical Debt (Resolved)

- Phase polygon overlap → Fixed with curve-based lookup
- Phase diagram axis arrangement → Fixed
- Performance for large structures → Fixed with KDTree
- Security vulnerabilities → Fixed

---

## Decisions Made (v2.0)

| Phase | Decision | Rationale |
|-------|----------|-----------|
| All | Use PySide6 (not PyQt6) | LGPL allows MIT bundling |
| All | Direct module import (not subprocess) | Preserves typed objects |
| All | MVVM architecture | Clean separation of UI and logic |
| All | QThread workers | Prevents UI freezing during computation |
| 08-01 | Pressure in bar (not MPa) | More intuitive for users |
| 08-01 | Max 216 molecules (not 100000) | Computational limit for interactive GUI |
| 08-01 | Worker-object pattern | Proper Qt pattern for cancellable work |
| 08-01 | Import modules inside run() | Avoids blocking main thread |
| 08-02 | Validation on submit (not real-time) | Per CONTEXT.md requirements |
| 08-02 | Inline error labels hidden by default | Clean UI, errors shown on validation failure |
| 08-02 | ProgressPanel lifecycle state methods | Clear state management for generation flow |
| 08-03 | ViewModel manages generation state | MVVM pattern: bridge between View and Model |
| 08-03 | UI state via ui_enabled_changed signal | Enables/disables UI during generation |
| 08-03 | Thread cleanup via deleteLater | Proper Qt memory management |
| 08-04 | QAction for keyboard shortcuts | Works globally in window |
| 08-04 | Generate button as default | Enter key triggers generation |
| 08-04 | QMessageBox.critical for errors | Per PROGRESS-04 requirement |
| 09-02 | Default molecule count 96 | Reasonable middle value from 4-216 range |
| 09-02 | Temperature rounded to 1 decimal | Better readability for users |
| 09-02 | Pressure rounded to 0 decimals | Simpler integer display |
| 09-02 | Splitter sizing 60/40 | Balanced view for diagram and inputs |
| 09-02 | Window minimum 800x500 | Accommodate both panels comfortably |
| 09-04 | subplots_adjust for explicit margins | Ensures labels are fully visible without clipping |
| 09-04 | Vapor label at (380K, 0.25 MPa) | Better position in visible vapor region |
| 10-01 | Use vtkMolecule for molecular data | VTK handles rendering automatically, no manual geometry |
| 10-01 | H-bond detection with 0.25 nm threshold | Typical H...O distance threshold (2.5 Å) |
| 10-01 | vtkOutlineSource for unit cell | Simpler than transform approach for orthogonal cells |
| 10-01 | Line stipple 0x0F0F for H-bonds | Medium dash pattern (4 on, 4 off) |
| 10-02 | Ball-and-stick default via UseBallAndStickSettings() | Per VIEWER-02 requirement |
| 10-02 | TrackballCamera interactor style | Standard 3D mouse controls |
| 10-02 | Dark blue background (0.1, 0.2, 0.4) | Good contrast for molecules |
| 10-03 | H-bonds default visible per CONTEXT.md | User can view H-bonds as dashed lines |
| 10-03 | Unit cell default hidden per CONTEXT.md | "Non-intrusive" wireframe box |
| 10-03 | zoom_to_fit() delegates to reset_camera() | Simpler toolbar integration |
| 10-04 | Auto-rotation at ~10°/sec via QTimer | Per CONTEXT.md presentation quality |
| 10-04 | Viridis colormap for property coloring | Per CONTEXT.md scientific standard |
| 10-04 | Property coloring falls back to CPK | No crash when no ranked candidate |
| 10-05 | Dual viewport QHBoxLayout (1 row, 2 grids) | Per CONTEXT.md "always dual view" |
| 10-05 | Camera sync via ModifiedEvent observer | Per RESEARCH.md Pattern 6 |
| 10-05 | Guard flag prevents camera sync recursion | Prevents infinite feedback loop |
| 11-02 | QLabel as base for HelpIcon | Simple, lightweight, native Qt tooltip support |
| 11-02 | Inline help text in InputPanel | QHBoxLayout for label rows keeps help icon adjacent |
| 11-02 | Phase info emitted on every click | Immediate feedback for user interaction |
| 11-03 | Store generation params in MainWindow | Enables export handlers to access current data |
| 11-03 | Phase info in log panel (not separate window) | Per CONTEXT.md repurpose existing components |
| 11-03 | Helper functions for structure/citation | Enables scientific information display |
| 11-03 | Citations from GenIce2 README | Correct citations matching GenIce2 source |
| 11-04 | HelpIcon manual tooltip via enterEvent | Stylesheet interferes with auto-tooltip |
| 11-04 | Candidate selector as QComboBox | Independent of viewport for export |
| 10-06 | vtkMatrix3x3 for SetLattice | VTK API requires matrix object, not list |
| 10-06 | QLabel with parent to prevent top-level window | Fixes separate empty window issue |
| 13-01 | System Requirements before installation | Prevent failed installs on old Linux |
| 13-01 | GUI as supplementary (brief sections) | Maintain CLI-first documentation |
| 13-01 | Link to separate gui-guide.md | Detailed GUI documentation in dedicated file |
| 13-02 | Screenshot placeholders before Phase 12 | Enable early documentation before screenshots exist |
| 13-03 | Use QDialog (modal) for QuickReferenceDialog | Per CONTEXT.md requirement, not panel or F1 shortcut |
| 13-04 | Use QDialog.exec() for modal dialog | Per INFO-04 requirement, blocks parent until closed |
| 13-04 | Help menu after File menu | Standard UI convention, logical menu ordering |
| 12-01 | PyInstaller as dev-only dependency | Users building executable install dev dependencies separately |
| 12-01 | License files from SPDX repository | Plain text format (opensource.org returned HTML) |
| 12-01 | Windows workflow with manual trigger | User-controlled execution, not auto-triggered |
| 12-01 | PyInstaller --onedir mode | Faster startup, easier debugging than --onefile |
| 12-03 | Conda packages with single = | Standard conda version pinning format |
| 12-03 | Pip packages with == | Standard pip version pinning format |

---

## Session Continuity

**Last session:** 2026-04-04
**Stopped at:** Completed 12-03-PLAN.md
**Next steps:**
1. Run `/gsd-execute-phase 12-04` to create Windows build workflow
2. Run `/gsd-execute-phase 12-02` to build Linux executable and create tarball
3. Release v2.0.0

---

## Roadmap Evolution

- Phase 13 added: Update README and documentation after finishing the GUI

---

## Dependencies to Install

Per project constraint: Do NOT auto-install. Add to env.yml, seek approval first.

**Required for v2.0:**
- PySide6 >= 6.9.3 — **installed**
- VTK >= 9.5.2 — **installed**
- matplotlib (existing)

**Status:** All v2.0 dependencies installed

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v1.0 Requirements: [.planning/milestones/v1-REQUIREMENTS.md](./milestones/v1-REQUIREMENTS.md)
- v1.0 Audit: [.planning/milestones/v1-MILESTONE-AUDIT.md](./milestones/v1-MILESTONE-AUDIT.md)

---

## v2.0 Requirements Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | Phase 8 | Complete |
| INPUT-02 | Phase 8 | Complete |
| INPUT-03 | Phase 8 | Complete |
| INPUT-04 | Phase 8 | Complete |
| INPUT-05 | Phase 8 | Complete |
| DIAGRAM-01 | Phase 9 | Complete |
| DIAGRAM-02 | Phase 9 | Complete |
| DIAGRAM-03 | Phase 9 | Complete |
| DIAGRAM-04 | Phase 9 | Complete |
| VIEWER-01 | Phase 10 | Complete |
| VIEWER-02 | Phase 10 | Complete |
| VIEWER-03 | Phase 10 | Complete |
| VIEWER-04 | Phase 10 | Complete |
| VIEWER-05 | Phase 10 | Complete |
| ADVVIZ-01 | Phase 10 | Complete |
| ADVVIZ-02 | Phase 10 | Complete |
| ADVVIZ-03 | Phase 10 | Complete |
| ADVVIZ-04 | Phase 10 | Complete |
| ADVVIZ-05 | Phase 10 | NOT IMPLEMENTED |
| UX-01 | Phase 8 | Complete |
| PACKAGE-01 | Phase 12 | In Progress |
| PACKAGE-02 | Phase 12 | Pending |
| PACKAGE-03 | Phase 12 | Complete |

**Coverage:** 33/34 requirements mapped (ADVVIZ-05 not implemented) ✓

---

*State updated: 2026-04-04 - Completed 12-03-PLAN.md (dependency version pinning)*
