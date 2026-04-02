---
phase: 11-save-export-information
plan: 01
subsystem: export
tags: pyside6, qfiledialog, matplotlib, vtk, pdb, png, svg, jpeg

# Dependency graph
requires:
  - phase: 08-gui-infrastructure
    provides: PySide6 widgets, parent widget for dialog centering
  - phase: 09-interactive-phase-diagram
    provides: Matplotlib figure for diagram export
  - phase: 10-3d-molecular-viewer
    provides: VTK render window for viewport capture
provides:
  - PDBExporter for saving ice structure candidates to PDB format
  - DiagramExporter for exporting phase diagram to PNG/SVG images
  - ViewportExporter for capturing 3D viewport screenshots
affects:
  - Phase 11-02 (MainWindow integration for export menu/toolbar)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Native file dialogs via QFileDialog.getSaveFileName()
    - Overwrite confirmation via QMessageBox.question()
    - VTK viewport capture via vtkWindowToImageFilter
    - Matplotlib export with proper DPI and padding

key-files:
  created:
    - quickice/gui/export.py
  modified: []

key-decisions:
  - "Use native QFileDialog for all file save operations (better OS integration)"
  - "PNG dpi=300 for publication-quality diagram exports"
  - "VTK SetScale(2) for 2x viewport resolution"
  - "JPEG quality=95 for viewport screenshots"
  - "Force render_window.Render() before VTK capture to avoid black images"

patterns-established:
  - "Pattern: Native file dialog with overwrite confirmation for all exporters"
  - "Pattern: Path.with_suffix() for ensuring correct file extensions"
  - "Pattern: Error handling with QMessageBox.critical() and return False"

# Metrics
duration: 5min
completed: 2026-04-02
---

# Phase 11 Plan 01: Export Module Summary

**Three exporter classes for saving user work to standard file formats: PDB files for ice structures, PNG/SVG images for phase diagrams, and PNG/JPEG screenshots for 3D viewports.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-02T05:59:42Z
- **Completed:** 2026-04-02T06:04:53Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- PDBExporter with native file dialog, default filename generation, overwrite confirmation, and error handling
- DiagramExporter with PNG (300 DPI) and SVG format support, proper padding to avoid clipping
- ViewportExporter with VTK capture pipeline, forced render to avoid black images, 2x scale for quality

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PDBExporter class** - `5e4afbc` (feat)
2. **Task 2: Create DiagramExporter class** - `40ff9ef` (feat)
3. **Task 3: Create ViewportExporter class** - `9ffd29c` (feat)

**Plan metadata:** Coming in next commit

_Note: All commits are independent and revertible_

## Files Created/Modified
- `quickice/gui/export.py` - Export handlers for PDB, diagram, and viewport (285 lines)

## Decisions Made
- Native QFileDialog for all file saves (per RESEARCH.md Pattern 1)
- PNG dpi=300 for high-resolution diagram exports (per RESEARCH.md Pattern 2)
- SVG format='svg', bbox_inches='tight' for vector diagram exports
- VTK SetScale(2) for 2x viewport resolution (per RESEARCH.md Pitfall 5)
- JPEG quality=95 for viewport screenshots (near-lossless)
- Force render_window.Render() before VTK capture (per RESEARCH.md Pitfall 1)
- ReadFrontBufferOff() for offscreen buffer capture
- pad_inches=0.2 for PNG export to avoid label clipping (per RESEARCH.md Pitfall 2)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Export module complete with all three exporter classes
- Ready for 11-02-PLAN.md: MainWindow integration (menu bar, toolbar, wiring)
- No blockers or concerns

---
*Phase: 11-save-export-information*
*Completed: 2026-04-02*