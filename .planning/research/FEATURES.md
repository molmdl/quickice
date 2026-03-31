# Feature Landscape: QuickIce v2.0 GUI Application

**Domain:** Scientific GUI application for ice structure generation
**Researched:** 2026-03-31
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

QuickIce v2.0 transforms the existing CLI tool into a cross-platform GUI application. Based on research into scientific visualization tools like OVITO, Pymatgen, and Avogadro, this document categorizes features into table stakes (expected), differentiators (competitive advantage), and anti-features (avoid building). Key insights include the importance of non-blocking computation with progress feedback, interactive viewport controls for 3D viewing, and maintaining feature parity with the CLI while adding discoverability through visual interaction.

---

## Table Stakes (Must Have)

Features that users expect in any scientific GUI application. Missing these makes the product feel incomplete or unprofessional.

### Input & Controls

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Temperature input (textbox) | Core parameter for ice phase selection | LOW | Numeric input with validation, pre-filled default (300K) | Existing CLI --temperature |
| Pressure input (textbox) | Core parameter for ice phase selection | LOW | Numeric input with validation, pre-filled default (100 MPa) | Existing CLI --pressure |
| Molecule count input | System size control | LOW | Numeric input with validation, pre-filled default (64) | Existing CLI --nmolecules |
| Generate button | Primary action to trigger computation | LOW | Disabled during computation, re-enabled on completion | All inputs |
| Input validation with error messages | Prevents invalid computation | LOW | Inline error display, prevents generation | Textbox inputs |

### Interactive Phase Diagram

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Phase diagram visualization | Shows T,P→phase mapping visually | MEDIUM | Display existing 12-phase diagram, rendered as image/widget | Existing phase mapping logic |
| Click to select T,P | Intuitive input method | MEDIUM | Click on diagram updates T,P textboxes | Phase diagram display |
| Current selection indicator | Shows selected T,P on diagram | LOW | Crosshair or marker at selected point | Phase diagram + click |
| Phase label on selection | Shows which phase is selected | LOW | Tooltip or label showing phase name | Phase diagram + click |

### 3D Molecular Viewer

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| 3D viewport | Display generated ice structure | MEDIUM-HIGH | Requires 3D rendering library (OpenGL/Mesa) | Generated PDB data |
| Ball-and-stick representation | Standard molecular visualization | MEDIUM | Oxygen=red, Hydrogen=white, bonds visible | 3D viewport |
| Stick representation | Alternative viewing mode | LOW | Atoms as sticks, good for large structures | 3D viewport |
| Zoom/pan/rotate controls | Explore 3D structure | LOW | Mouse drag, scroll wheel, right-click pan | 3D viewport |
| Hydrogen bond visualization | Shows ice hydrogen bonding network | MEDIUM | Dashed lines between bonded molecules | 3D viewport + bond calculation |

### Progress & Feedback

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Progress bar | Shows computation status | LOW | Indeterminate or percentage-based | Generate button |
| Status text | Shows current operation | LOW | "Generating candidates...", "Ranking..." | Generate button |
| Cancel button | Allow stopping long computation | LOW | Abort generation mid-process | Generate button |
| Error display | Show what went wrong | LOW | Dialog or inline error message | Generation logic |

### Save/Export

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Save PDB file | Export generated structure | LOW | Standard file save dialog | Generated candidates |
| Save phase diagram | Export visualization | LOW | PNG/SVG export | Phase diagram widget |
| Save 3D scene | Export viewport state | MEDIUM | Depends on viewer library capabilities | 3D viewport |

---

## Differentiators (Competitive Advantage)

Features that set QuickIce apart from competitors or add significant user value beyond basic expectations.

### Information & Education

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Info window with phase citations | Scientific credibility, helps users cite properly | MEDIUM | Show DOI/references for each ice phase |
| Phase information tooltip | Discoverability of phase properties | LOW | Hover over phase shows density, structure info |
| Help tooltips on UI elements | Reduces learning curve | LOW | "?" icons or hover help |
| Markdown manual viewer | In-app documentation | MEDIUM | Browse full documentation without leaving app |

### Advanced Visualization

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multiple structure comparison | Compare ranked candidates side-by-side | HIGH | Requires multiple viewports |
| Animated rotation | Showcase structure dynamically | LOW | Auto-rotate toggle |
| Color by property | Visualize energy/density ranking | MEDIUM | Color atoms by candidate rank |
| Unit cell visualization | Show periodic boundary | LOW | Toggle unit cell box display |
| Zoom to fit button | Quickly frame structure | LOW | One-click to center and fit |

### User Experience

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Recent calculations history | Resume previous work | MEDIUM | Store T,P,N combinations |
| Keyboard shortcuts | Power user efficiency | LOW | Enter to generate, Escape to cancel |
| Dark/light theme | User preference | LOW | Theme toggle |
| Undo/redo in viewer | Correct mistakes | MEDIUM | For view transformations |

---

## Anti-Features (Do NOT Build)

Features commonly requested but problematic for this domain. Documented to prevent scope creep and ensure focused development.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Real-time 3D structure preview while typing | "Modern" UX expectation | GenIce generation is too slow (~seconds), would freeze UI | Generate button is appropriate |
| Automatic phase diagram updates | Appears useful | Phase diagram is static, no need to recalculate | Static image is fine |
| In-app DFT/MD simulation | Comprehensive tool | Outside project scope (generation only) | CLI integration for external tools |
| Collaborative features | Modern app expectation | Scientific tools are typically single-user | Keep simple |
| Cloud sync | Data portability | Adds complexity, scientific data often local | Local file save is sufficient |
| Plugin system | Extensibility | Over-engineering for tool's scope | Python API for scripting (future) |
| Direct email support | User expectation | Beyond project resources | Link to GitHub issues |

---

## Feature Dependencies

### Generation Pipeline

```
User Input (T, P, N)
        │
        ▼
Input Validation ──────► Error Display
        │
        ▼
Phase Mapping (T,P → phase)
        │
        ▼
GenIce Generation (10 candidates)
        │
        ▼
Ranking & Validation
        │
        ▼
PDB Output + Display
```

### Visualization Pipeline

```
PDB Data
        │
        ▼
3D Parser (coordinates → render objects)
        │
        ▼
Bond Calculator (hydrogen bonds)
        │
        ▼
Viewport Renderer
        │
        ▼
User Interaction (zoom, rotate, pan)
```

### Key Dependency Notes

1. **Input validation must complete before generation** - Prevents invalid GenIce calls
2. **Phase mapping must complete before structure generation** - GenIce needs phase name
3. **3D viewer requires valid PDB data** - Cannot display without coordinates
4. **Progress feedback requires thread management** - GenIce blocks UI thread without async
5. **Cancel functionality requires interruption points** - Must check cancel flag during generation

---

## User Interaction Patterns

### Primary Workflow

1. **Enter conditions** - Type T, P, N or click phase diagram
2. **Review selection** - See selected phase indicated on diagram
3. **Generate** - Click button, see progress
4. **View results** - Browse 3D structure in viewer
5. **Save** - Export PDB or diagram image

### Interaction Timing Expectations

| Action | Expected Response Time |
|--------|------------------------|
| Text input validation | < 100ms (instant) |
| Phase diagram click | < 100ms (selection update) |
| Generate button enable | Immediate |
| Generation start | < 500ms (after click) |
| Structure display | < 2s for 216 molecules |
| 3D viewport rotation | 60fps (smooth) |
| Save file dialog | Immediate |

### Error Handling Patterns

| Scenario | Expected Behavior |
|----------|-------------------|
| Invalid T value | Red border on input, error message below |
| Invalid P value | Red border on input, error message below |
| GenIce failure | Error dialog with details, option to report |
| No valid candidates | Warning, show available alternatives |
| Cancel during generation | Clean stop, restore UI state |

---

## MVP Recommendation

For v2.0 initial release, prioritize:

### Phase 1 (MVP - Must Have)

1. Temperature/pressure/molecule textbox inputs with validation
2. Generate button with progress bar
3. Phase diagram display (static image)
4. Click-to-select on phase diagram
5. Basic 3D viewer (ball-and-stick)
6. Zoom/pan/rotate controls
7. Save PDB file

### Phase 2 (Enhanced Experience)

1. Phase info window with citations
2. Help tooltips throughout UI
3. Stick representation mode
4. Hydrogen bond visualization
5. Export phase diagram image

### Phase 3 (Differentiation)

1. Markdown manual viewer
2. Recent calculations history
3. Unit cell toggle
4. Animated rotation
5. Multiple candidate browser

---

## Technical Implementation Notes

### Rendering Library Options

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| PyQt/PySide + OpenGL | Full-featured, cross-platform | Complex setup | Recommended |
| VTK | Scientific visualization built-in | Heavy dependency | Consider if needed |
| Matplotlib 3D | Simple, familiar | Limited interactivity | MVP only |
| pyvista | Wraps VTK, Pythonic | Heavy dependency | For advanced features |

### Threading Strategy

Scientific computation (GenIce) must run in background thread:
- Main thread: UI responsiveness
- Worker thread: GenIce generation
- Progress updates: signals/emitted from worker to main

---

## Research Sources

- [OVITO](https://www.ovito.org/) — Scientific visualization tool patterns
- [Avogadro](https://github.com/avogadro/avogadro) — Molecular editor reference
- [Pymatgen](https://github.com/materialsproject/pymatgen) — Phase diagram generation
- QuickIce CLI implementation — Existing functionality to preserve

---

*Research for: QuickIce v2.0 GUI Application*
*Generated: 2026-03-31*