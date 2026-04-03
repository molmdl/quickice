# QuickIce Roadmap

**Project:** QuickIce - Condition-based Ice Structure Generation

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-29)
- ✅ **v1.1 Hotfix** — Phase 7.1 (shipped 2026-03-31)
- ✅ **v2.0 GUI Application** — Phases 8-13 (complete)

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

### Phase 8: GUI Infrastructure + Core Input ✅

**Goal:** Users can enter temperature, pressure, and molecule count parameters and trigger ice structure generation with progress feedback

**Requirements:** INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05, PROGRESS-01, PROGRESS-02, PROGRESS-03, PROGRESS-04, UX-01

**Dependencies:** None (foundation)

**Plans:** 4 plans in 4 waves — completed 2026-03-31

Plans:
- [x] 08-01-PLAN.md — Model + Worker Foundation (validators, workers)
- [x] 08-02-PLAN.md — View Layer (InputPanel, ProgressPanel)
- [x] 08-03-PLAN.md — ViewModel (state management, worker orchestration)
- [x] 08-04-PLAN.md — MainWindow (buttons, shortcuts, UI testing)

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

### Phase 9: Interactive Phase Diagram ✅

**Goal:** Users can visually select thermodynamic conditions by clicking on an interactive phase diagram

**Requirements:** DIAGRAM-01, DIAGRAM-02, DIAGRAM-03, DIAGRAM-04

**Dependencies:** Phase 8 (input handling)

**Plans:** 5 plans in 4 waves (2 gap closure plans added) — completed 2026-04-01

Plans:
- [x] 09-01-PLAN.md — Create PhaseDiagramWidget (matplotlib canvas, hover, click, phase detection)
- [x] 09-02-PLAN.md — Integrate into MainWindow (split view, input population)
- [x] 09-03-PLAN.md — Manual verification (GUI testing) — user approved
- [x] 09-04-PLAN.md — GAP CLOSURE: Fix diagram layout (wider figure, label placement)
- [x] 09-05-PLAN.md — GAP CLOSURE: Fix phase detection (vapor region, boundary handling, input binding)

**Success Criteria:**
1. User can view 12-phase ice phase diagram in GUI with labeled regions
2. User can click anywhere on phase diagram to select temperature and pressure coordinates
3. User sees visual indicator (crosshair/marker) showing selected T,P location on diagram
4. User sees phase name label appear when clicking on a diagram region

---

### Phase 10: 3D Molecular Viewer ✅

**Goal:** Users can view and interact with generated ice structures in a 3D viewport with multiple visualization options

**Requirements:** VIEWER-01, VIEWER-02, VIEWER-03, VIEWER-04, VIEWER-05, ADVVIZ-01, ADVVIZ-02, ADVVIZ-03, ADVVIZ-04

**Dependencies:** Phase 8 (threading for background generation)

**Plans:** 6 plans in 6 waves — completed 2026-04-02

Plans:
- [x] 10-01-PLAN.md — VTK Utilities (molecule conversion, H-bond detection, actors)
- [x] 10-02-PLAN.md — Basic Molecular Viewer Widget (VTK setup, ball-and-stick, mouse controls)
- [x] 10-03-PLAN.md — Visualization Toggles (representation, H-bonds, unit cell, zoom-fit)
- [x] 10-04-PLAN.md — Advanced Features (auto-rotation, color-by-property)
- [x] 10-05-PLAN.md — Dual Viewport Comparison (synchronized cameras, selectors)
- [x] 10-06-PLAN.md — MainWindow Integration (layout, toolbar, info panel)

**Note:** ADVVIZ-05 (color-by-property) not implemented per user decision.

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
10. User can color atoms by property (energy ranking or density ranking) to highlight favorable structures — NOT IMPLEMENTED

---

### Phase 11: Save/Export + Information ✅

**Goal:** Users can export results to standard formats and access scientific information about ice phases

**Requirements:** EXPORT-01, EXPORT-02, EXPORT-03, INFO-01, INFO-03 (INFO-02 and INFO-04 deferred)

**Dependencies:** Phase 9 (phase diagram), Phase 10 (3D viewer)

**Plans:** 4 plans in 3 waves — completed 2026-04-02

Plans:
- [x] 11-01-PLAN.md — Export Module (PDBExporter, DiagramExporter, ViewportExporter)
- [x] 11-02-PLAN.md — Help Icons + Phase Info Signal (tooltips, phase_info_ready)
- [x] 11-03-PLAN.md — MainWindow Integration (menu bar, wiring, phase info display)
- [x] 11-04-PLAN.md — User Verification (manual GUI testing)

**Notes:**
- INFO-02 (phase hover tooltip) deferred per design decision — existing T,P display sufficient
- INFO-04 (in-app manual) deferred to Phase 13 (documentation update)

**Success Criteria:**
1. ✓ User can save generated PDB file via native file save dialog with .pdb extension
2. ✓ User can save phase diagram image to file (PNG or SVG format)
3. ✓ User can save 3D viewport as image (PNG format)
4. ✓ User can open info window displaying citations and references for the selected ice phase
5. User sees tooltip with phase information (density, structure type) when hovering over phase regions — DEFERRED
6. ✓ User sees help tooltips on UI elements when hovering over question mark icons
7. User can view in-app markdown manual/documentation for application usage — DEFERRED to Phase 13

---

### Phase 12: Packaging & Distribution ✅ Complete

**Goal:** Users receive a standalone executable with all dependencies bundled, with verified license compliance

**Requirements:** PACKAGE-01, PACKAGE-02, PACKAGE-03

**Dependencies:** Phase 13 (documentation complete for packaging)

**Note:** Phase 13 documentation will be included in the standalone distribution.

**Plans:** 5 plans (all complete)

Plans:
- [x] 12-01-PLAN.md — Verify dev environment + collect licenses
- [x] 12-02-PLAN.md — Build Linux executable with PyInstaller
- [x] 12-03-PLAN.md — Pin all dependency versions to exact versions in environment.yml
- [x] 12-04-PLAN.md — Create cross-platform build env + Windows GitHub Actions workflow
- [x] 12-05-PLAN.md — GAP CLOSURE: Fix BSD-3-Clause license (30 lines from NumPy)

**Verification:** 3/3 requirements satisfied (PACKAGE-01 ✓, PACKAGE-02 ✓, PACKAGE-03 ✓)

**Success Criteria:**
1. User can download/run standalone executable that launches QuickIce GUI without requiring Python installation — ✓ COMPLETE (quickice-v2.0.0-linux-x86_64.tar.gz)
2. License compatibility audit confirms all bundled libraries (PySide6, VTK, GenIce2) are legally compatible with MIT license — ✓ COMPLETE
3. All dependency versions pinned to exact versions (`=x.y.z`) in environment.yml for reproducibility and security — ✓ COMPLETE

---

### Phase 13: Update README and Documentation After Finishing the GUI ✅

**Goal:** Users and developers have comprehensive, up-to-date documentation reflecting the v2.0 GUI application

**Dependencies:** Phase 11 (GUI features complete, ready for screenshots)

**Note:** Executing before Phase 12 allows documentation to be packaged with standalone executable.

**Plans:** 4 plans in 3 waves — completed 2026-04-03

Plans:
- [x] 13-01-PLAN.md — Update README.md with GUI mentions and OS requirements
- [x] 13-02-PLAN.md — Create docs/images/ and docs/gui-guide.md
- [x] 13-03-PLAN.md — Create QuickReferenceDialog class (INFO-04)
- [x] 13-04-PLAN.md — Add Help menu to MainWindow and wire dialog

**Success Criteria:**
1. User can read updated README with accurate v2.0 installation and usage instructions
2. User can access in-app documentation reflecting current GUI features
3. Developer can find updated API documentation for all v2.0 components
4. User sees accurate screenshots and examples in documentation matching current UI

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
| **8 - GUI Infrastructure** | v2.0 | ✅ Complete | 10 |
| **9 - Phase Diagram** | v2.0 | ✅ Complete | 4 |
| **10 - 3D Viewer** | v2.0 | ✅ Complete | 9 |
| **11 - Save/Export** | v2.0 | ✅ Complete | 7 (5 complete, 2 deferred) |
| **12 - Packaging** | v2.0 | ✅ Complete | 3 |
| **13 - Documentation Update** | v2.0 | ✅ Complete | 4 |

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
| Packaging & Licensing | 3 | Phase 12 |

**Total v2.0 Requirements:** 33 (ADVVIZ-05 not implemented)

---

*Roadmap last updated: 2026-04-04*
