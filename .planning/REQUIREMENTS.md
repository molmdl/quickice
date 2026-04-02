# Requirements: QuickIce v2.0 GUI Application

**Defined:** 2026-03-31
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface

## v2 Requirements

Requirements for v2.0 GUI application. Each maps to roadmap phases.

### Input & Controls

- [x] **INPUT-01**: User can enter temperature value in textbox with validation
- [x] **INPUT-02**: User can enter pressure value in textbox with validation
- [x] **INPUT-03**: User can enter molecule count in textbox with validation (max 216)
- [x] **INPUT-04**: User can click Generate button to trigger ice structure generation
- [x] **INPUT-05**: User sees inline error messages for invalid inputs

### Interactive Phase Diagram

- [x] **DIAGRAM-01**: User can view 12-phase ice diagram in GUI
- [x] **DIAGRAM-02**: User can click on phase diagram to select T,P coordinates
- [x] **DIAGRAM-03**: User sees selection indicator (crosshair/marker) at selected T,P
- [x] **DIAGRAM-04**: User sees phase name label when clicking on diagram region

### 3D Molecular Viewer

- [x] **VIEWER-01**: User can view generated ice structure in 3D viewport (VTK-based)
- [x] **VIEWER-02**: User can view ball-and-stick molecular representation (O=red, H=white)
- [x] **VIEWER-03**: User can switch to stick representation mode
- [x] **VIEWER-04**: User can zoom, pan, and rotate 3D structure with mouse controls
- [x] **VIEWER-05**: User can view hydrogen bonds as dashed lines between molecules

### Progress & Feedback

- [x] **PROGRESS-01**: User sees progress bar during ice structure generation
- [x] **PROGRESS-02**: User sees status text indicating current operation
- [x] **PROGRESS-03**: User can cancel generation mid-process via Cancel button
- [x] **PROGRESS-04**: User sees error dialog when generation fails with details

### Save/Export

- [x] **EXPORT-01**: User can save generated PDB file via file save dialog
- [x] **EXPORT-02**: User can save phase diagram image (PNG/SVG)
- [x] **EXPORT-03**: User can save 3D scene image from viewport

### Information & Education

- [x] **INFO-01**: User can view info window with citations/references for selected ice phase
- [ ] **INFO-02**: User sees phase information tooltip on hover (density, structure type) — DEFERRED
- [x] **INFO-03**: User sees help tooltips on UI elements (question mark icons)
- [ ] **INFO-04**: User can view in-app markdown manual/documentation — DEFERRED to Phase 13

### Advanced Visualization

- [x] **ADVVIZ-01**: User can toggle unit cell boundary box display
- [x] **ADVVIZ-02**: User can click zoom-to-fit to frame structure in viewport
- [x] **ADVVIZ-03**: User can toggle animated auto-rotation of structure
- [x] **ADVVIZ-04**: User can view multiple candidates side-by-side for comparison
- [ ] **ADVVIZ-05**: User can color atoms by property (energy/density ranking) — NOT IMPLEMENTED

### User Experience

- [x] **UX-01**: User can use keyboard shortcuts (Enter to generate, Escape to cancel)

### Packaging & Licensing

- [ ] **PACKAGE-01**: User receives standalone bundled executable with all dependencies
- [ ] **PACKAGE-02**: License compatibility audit confirms bundling is legally compliant

## v2.1 Requirements

Deferred to future release. Tracked but not in current roadmap.

### User Experience (Deferred)

- **UX-02**: User can toggle dark/light theme
- **UX-03**: User can view recent calculations history
- **UX-04**: User can undo/redo view transformations in 3D viewer

### Advanced Features (Deferred)

- **ADVVIZ-06**: User can export to CIF format
- **ADVVIZ-07**: User can export to GRO format
- **ADVVIZ-08**: User can adjust hydrogen bond distance threshold

## Constraints

- **Dependency installation**: Do NOT auto-install new dependencies. Add to env.yml, seek approval, wait for user to install before proceeding.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web-based viewer | User specified standalone desktop app only |
| Real-time preview while typing | GenIce too slow (~seconds), would freeze UI |
| Automatic phase diagram updates | Phase diagram is static, no recalculation needed |
| In-app DFT/MD simulation | Outside project scope (generation only) |
| Cloud sync/collaboration | Scientific tools typically single-user, local data |
| Plugin system | Over-engineering for tool's scope |
| >216 molecules | Performance constraint, defer to v3 |
| ML-based phase prediction | Deferred to v2.1+ |
| Confidence scoring | Deferred to v2.1+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

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
| PROGRESS-01 | Phase 8 | Complete |
| PROGRESS-02 | Phase 8 | Complete |
| PROGRESS-03 | Phase 8 | Complete |
| PROGRESS-04 | Phase 8 | Complete |
| EXPORT-01 | Phase 11 | Complete |
| EXPORT-02 | Phase 11 | Complete |
| EXPORT-03 | Phase 11 | Complete |
| INFO-01 | Phase 11 | Complete |
| INFO-02 | Phase 11 | Deferred |
| INFO-03 | Phase 11 | Complete |
| INFO-04 | Phase 11 | Deferred |
| ADVVIZ-01 | Phase 10 | Complete |
| ADVVIZ-02 | Phase 10 | Complete |
| ADVVIZ-03 | Phase 10 | Complete |
| ADVVIZ-04 | Phase 10 | Complete |
| ADVVIZ-05 | Phase 10 | NOT IMPLEMENTED |
| UX-01 | Phase 8 | Complete |
| PACKAGE-01 | Phase 12 | Pending |
| PACKAGE-02 | Phase 12 | Pending |

**Coverage:**
- v2 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-04-02 after Phase 11 completion*