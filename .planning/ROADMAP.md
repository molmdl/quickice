# QuickIce Roadmap

**Project:** QuickIce - Condition-based Ice Structure Generation

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-29)
- ✅ **v1.1 Hotfix** — Phase 7.1 (shipped 2026-03-31)
- 🚧 **v2.0 GUI Application** — Phases 8-12 (in progress)

---

## Phase Structure

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-03-29</summary>

- [x] Phase 1: Input Validation (3/3 plans) — completed 2026-03-26
- [x] Phase 2: Phase Mapping (4/4 plans) — completed 2026-03-27
- [x] Phase 3: Structure Generation (2/2 plans) — completed 2026-03-26
- [x] Phase 4: Ranking (4/4 plans) — completed 2026-03-26
- [x] Phase 5: Output (7/7 plans) — completed 2026-03-27
- [x] Phase 5.1: Add Missing Ice Phases (3/3 plans) — completed 2026-03-27
- [x] Phase 6: Documentation (2/2 plans) — completed 2026-03-28
- [x] Phase 7: Audit & Correctness (5/5 plans) — completed 2026-03-28

**Full details:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

</details>

<details>
<summary>✅ v1.1 Hotfix (Phase 7.1) — SHIPPED 2026-03-31</summary>

- [x] Phase 7.1: Fix Performance & Critical Bugs (4/6 plans) — completed 2026-03-31

**Full details:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

</details>

---

## v2.0 GUI Application

**Goal:** Transform QuickIce from CLI tool to cross-platform GUI application with interactive phase diagram and 3D structure viewer

**Stack:** PySide6 6.11.0 + VTK 9.6.1 (MIT-compatible)

### Phase 8: GUI Infrastructure + Core Input

**Goal:** Users can enter temperature, pressure, and molecule count parameters and trigger ice structure generation with progress feedback

**Requirements:** INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05, PROGRESS-01, PROGRESS-02, PROGRESS-03, PROGRESS-04, UX-01

**Dependencies:** None (foundation)

**Plans:** 4 plans in 4 waves

Plans:
- [ ] 08-01-PLAN.md — Model + Worker Foundation (validators, workers)
- [ ] 08-02-PLAN.md — View Layer (InputPanel, ProgressPanel)
- [ ] 08-03-PLAN.md — ViewModel (state management, worker orchestration)
- [ ] 08-04-PLAN.md — MainWindow (buttons, shortcuts, checkpoint for UI testing)

**Success Criteria:**
1. User can enter temperature value in textbox and see inline error message for invalid inputs (< 0 or > 500 K)
2. User can enter pressure value in textbox and see inline error message for invalid inputs (< 0 or > 10000 bar)
3. User can enter molecule count in textbox and see inline error message for invalid inputs (not integer or > 216)
4. User can click Generate button to trigger ice structure generation
5. User sees progress bar during ice structure generation
6. User sees status text indicating current operation (e.g., "Generating structure...", "Ranking candidates...")
7. User can click Cancel button to abort generation mid-process
8. User sees error dialog when generation fails with details about what went wrong
9. User can press Enter key to trigger generation when input fields have focus
10. User can press Escape key to cancel generation

---

### Phase 9: Interactive Phase Diagram

**Goal:** Users can visually select thermodynamic conditions by clicking on an interactive phase diagram

**Requirements:** DIAGRAM-01, DIAGRAM-02, DIAGRAM-03, DIAGRAM-04

**Dependencies:** Phase 8 (input handling)

**Success Criteria:**
1. User can view 12-phase ice phase diagram in GUI with labeled regions
2. User can click anywhere on phase diagram to select temperature and pressure coordinates
3. User sees visual indicator (crosshair/marker) showing selected T,P location on diagram
4. User sees phase name label appear when clicking on a diagram region

---

### Phase 10: 3D Molecular Viewer

**Goal:** Users can view and interact with generated ice structures in a 3D viewport with multiple visualization options

**Requirements:** VIEWER-01, VIEWER-02, VIEWER-03, VIEWER-04, VIEWER-05, ADVVIZ-01, ADVVIZ-02, ADVVIZ-03, ADVVIZ-04, ADVVIZ-05

**Dependencies:** Phase 8 (threading for background generation)

**Success Criteria:**
1. User can view generated ice structure in 3D viewport (VTK-based) after generation completes
2. User can view ball-and-stick molecular representation with oxygen atoms red and hydrogen atoms white
3. User can switch between ball-and-stick and stick-only representation modes
4. User can zoom in/out, pan, and rotate 3D structure using mouse controls
5. User can view hydrogen bonds displayed as dashed lines between neighboring molecules
6. User can toggle unit cell boundary box to visualize the simulation cell
7. User can click zoom-to-fit button to automatically frame the structure in viewport
8. User can toggle animated auto-rotation of the structure for presentation
9. User can view multiple structure candidates side-by-side in separate viewports for comparison
10. User can color atoms by property (energy ranking or density ranking) to highlight favorable structures

---

### Phase 11: Save/Export + Information

**Goal:** Users can export results to standard formats and access scientific information about ice phases

**Requirements:** EXPORT-01, EXPORT-02, EXPORT-03, INFO-01, INFO-02, INFO-03, INFO-04

**Dependencies:** Phase 9 (phase diagram), Phase 10 (3D viewer)

**Success Criteria:**
1. User can save generated PDB file via native file save dialog with .pdb extension
2. User can save phase diagram image to file (PNG or SVG format)
3. User can save 3D viewport as image (PNG format)
4. User can open info window displaying citations and references for the selected ice phase
5. User sees tooltip with phase information (density, structure type) when hovering over phase regions
6. User sees help tooltips on UI elements when hovering over question mark icons
7. User can view in-app markdown manual/documentation for application usage

---

### Phase 12: Packaging & Distribution

**Goal:** Users receive a standalone executable with all dependencies bundled, with verified license compliance

**Requirements:** PACKAGE-01, PACKAGE-02

**Dependencies:** All previous phases (8-11 must be complete)

**Success Criteria:**
1. User can download/run standalone executable that launches QuickIce GUI without requiring Python installation
2. License compatibility audit confirms all bundled libraries (PySide6, VTK, GenIce2) are legally compatible with MIT license

---

## Progress

| Phase | Milestone | Status | Requirements |
|-------|-----------|--------|--------------|
| 1 - Input Validation | v1.0 | ✅ Complete | 3 |
| 2 - Phase Mapping | v1.0 | ✅ Complete | 6 |
| 3 - Structure Generation | v1.0 | ✅ Complete | 2 |
| 4 - Ranking | v1.0 | ✅ Complete | 4 |
| 5 - Output | v1.0 | ✅ Complete | 7 |
| 5.1 - Missing Ice Phases | v1.0 | ✅ Complete | 3 |
| 6 - Documentation | v1.0 | ✅ Complete | 2 |
| 7 - Audit & Correctness | v1.0 | ✅ Complete | 5 |
| 7.1 - Fix Performance & Bugs | v1.1 | ✅ Complete | 4 |
| **8 - GUI Infrastructure** | v2.0 | 🔄 Planned | 10 |
| **9 - Phase Diagram** | v2.0 | 🔄 Planned | 4 |
| **10 - 3D Viewer** | v2.0 | 🔄 Planned | 10 |
| **11 - Save/Export** | v2.0 | 🔄 Planned | 7 |
| **12 - Packaging** | v2.0 | 🔄 Planned | 2 |

---

## v2.0 Coverage Summary

| Category | Requirements | Phase |
|----------|--------------|-------|
| Input & Controls | 5 | Phase 8 |
| Interactive Phase Diagram | 4 | Phase 9 |
| 3D Molecular Viewer | 5 | Phase 10 |
| Progress & Feedback | 4 | Phase 8 |
| Advanced Visualization | 5 | Phase 10 |
| Save/Export | 3 | Phase 11 |
| Information & Education | 4 | Phase 11 |
| User Experience | 1 | Phase 8 |
| Packaging & Licensing | 2 | Phase 12 |

**Total v2.0 Requirements:** 33

---

*Roadmap last updated: 2026-03-31*