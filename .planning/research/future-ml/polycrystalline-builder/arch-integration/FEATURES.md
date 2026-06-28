# Feature Landscape — Polycrystalline Builder GUI Integration

**Domain:** GUI features for polycrystalline builder integration into QuickIce
**Researched:** 2026-06-28

## Table Stakes

Features users expect in a polycrystalline builder. Missing = tool feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 2D region drawing (rectangle, circle, polygon) | Standard in all crystal builder tools (Atomsk, OVITO) | Medium | QGraphicsView + custom QGraphicsItem subclasses |
| Phase assignment per region | Core workflow: draw region → assign phase | Low | QComboBox per region in region list |
| 3D structure preview after generation | Consistent with all other QuickIce tabs | Low | Reuse VTK rendering pattern |
| Generation progress reporting | Multi-step generation takes seconds; user needs feedback | Low | Two-level progress: region + sub-step |
| Cancel generation | Long-running task; user may want to abort | Low | isInterruptionRequested() between regions |
| GROMACS export (.gro + .top) | QuickIce's core value proposition | Medium | Extend existing write_multi_molecule_top_file |
| Box dimension inputs | Required for simulation setup | Low | QDoubleSpinBox pattern from Interface tab |
| Z-range per region | 2.5D model requires extrusion depth | Low | Two QDoubleSpinBox per region |
| Region list with selection | User needs to see/select/edit regions | Low | QListWidget or QTableWidget |
| Delete region | Basic editing operation | Low | QUndoCommand + Delete key |
| Undo/redo for shape operations | Standard expectation for drawing editors | Medium | QUndoStack + QUndoCommand subclasses |

## Differentiators

Features that set QuickIce's polycrystal builder apart from Atomsk/OVITO.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live 2D↔3D preview sync | Draw shape in 2D → instantly see 3D extruded preview in VTK | Medium | Signal from RegionModel → VTKPreview update |
| Phase-aware overlap detection | shapely.intersects() between regions of different phases → visual warning | Low | Highlight overlapping regions in red |
| Voronoi auto-generation | One-click N-grain generation from seed count | Medium | Mirror-point technique from poly-gen research |
| Buffer zone visualization | Show grain boundary buffer zones as translucent gray shells in 3D preview | Medium | VTK translucent actor for buffer polygons |
| Per-region rotation input | Set crystal orientation per grain (Euler angles) | Low | Three QDoubleSpinBox per region |
| Preset polycrystal geometries | "Ice Ih polycrystal (5 grains)", "Ice+Hydrate sI", etc. | Low | Pre-populate RegionModel from templates |
| Phase color legend | Color-coded legend showing which color = which phase | Low | QLabel with colored squares in viewer corner |
| PDB export for visualization in external tools | Users may want to view in VMD, OVITO | Low | Reuse existing PDB writer |
| Direct solute/ion insertion into polycrystal | No manual export-import cycle needed | Medium | Source dropdown extension in Solute/Ion tabs |

## Anti-Features

Features to explicitly NOT build. Common mistakes in crystal builder tools.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| 3D shape drawing (VTK widgets for region definition) | VTK 3D widgets only support axis-aligned primitives; no polygon support; terrible UX | 2D QGraphicsView for drawing, VTK for preview only |
| Atom-level region clipping | Splits molecules at boundaries → unphysical fragments | Molecule-level clipping using center-of-mass |
| Crystal alignment to boundary | Forces strain artifacts into bulk crystal | Accept ragged boundaries + buffer zones |
| Matplotlib for interactive drawing | No built-in selection/drag/resize; no undo; slow redraw | QGraphicsView for interactive editing |
| Automatic lattice matching at boundaries | No lattice matching between ice and clathrate (Nguyen 2015); impossible between Ice Ih and Ice II | Buffer zone approach for all incompatible lattice pairs |
| Unlimited undo depth | Memory grows unbounded with complex shape editing | Set QUndoStack.undoLimit = 100 |
| Cross-tab undo | User presses Ctrl+Z in Solute tab and undoes a shape change in Polycrystal tab | Scope undo to active tab only |
| Storing shapes only in QGraphicsScene | Qt coordinate rounding introduces nm-scale errors; no clean serialization | RegionModel as source of truth; QGraphicsItems as views |
| Shape wrapping across PBC boundaries (v1) | Geometrically complex; shapely doesn't understand PBC; high risk of bugs | Constrain shapes to box boundaries; PBC-wrap deferred to later version |
| Per-grain moleculetypes in GROMACS export (MVP) | Not needed for MD; all TIP4P-ICE water uses same parameters | Group all water as "SOL"; distinguish guests by type only |

## Feature Dependencies

```
2D Shape Drawing ──→ Region Model ──→ Phase Assignment
       │                   │                │
       ▼                   ▼                ▼
  QUndoStack         VTK Preview      Generate Button
       │                   │                │
       │                   │                ▼
       │                   │         PolycrystalWorker
       │                   │                │
       │                   ▼                ▼
       │           3D Region Preview   PolycrystalStructure
       │                                      │
       │                                      ▼
       │                              VTK Structure Preview
       │                                      │
       │                                      ▼
       │                           .to_interface_structure()
       │                                      │
       │                                      ▼
       │                            Solute/Ion Insertion
       │                                      │
       │                                      ▼
       │                            GROMACS Export
       │
       ▼
  Region Delete/Move/Resize (requires QUndoStack)
  
  Voronoi Auto-Gen (requires Region Model, independent of drawing)
  Preset Geometries (requires Region Model, independent of drawing)
```

## MVP Recommendation

For MVP, prioritize:
1. **2D shape drawing** (rectangle + circle tools) — table stakes
2. **Region list + phase assignment** — table stakes
3. **Z-range per region** — table stakes
4. **Generate polycrystal** (single-phase first: all Ice Ih) — table stakes
5. **3D structure preview** — table stakes
6. **GROMACS export** — table stakes
7. **Cancel generation** — table stakes

Defer to post-MVP:
- **Voronoi auto-generation**: High UX value but algorithmically independent; can ship later
- **Live 2D↔3D preview sync**: Nice-to-have but adds complexity to rendering pipeline
- **Buffer zone visualization**: MVP can use simple overlap-removal without visible buffer
- **Per-region rotation**: Start with random rotation only; manual input is a UX enhancement
- **Preset geometries**: Need stable RegionModel API first
- **Polygon/freehand drawing tools**: Rectangle + circle cover 80% of use cases

## Source Dropdown Integration Points

For the Solute and Ion tabs, the "Source" dropdown needs a new option:

### SolutePanel (Tab 4)
Current: ["Interface", "Custom Molecule"]
Add: "Polycrystal"

When "Polycrystal" selected:
- `MainWindow._on_insert_solutes()` checks `_current_polycrystal_result`
- Calls `polycrystal_structure.to_interface_structure()` to get compatible structure
- Passes to `SoluteInserter.insert_solutes(interface, config)`
- Solute insertion targets the liquid water region(s) in the polycrystal

### IonPanel (Tab 5)
Current: ["Interface", "Solute", "Custom Molecule"]
Add: "Polycrystal" (direct) and "Polycrystal→Solute" (via solute tab)

When "Polycrystal" selected:
- `MainWindow._on_insert_ions()` checks `_current_polycrystal_result`
- Calls `polycrystal_structure.to_interface_structure()` 
- Passes to `insert_ions(interface, concentration, volume)`

**Note:** The solute/ion insertion logic currently targets the "liquid water region" of an InterfaceStructure. In a polycrystal, there may be multiple disconnected liquid regions (buffer zones between grains). The SoluteInserter currently inserts solutes into ALL water positions — this is correct for polycrystals too (solutes distribute throughout all liquid regions).

## Sources

- QuickIce codebase: Direct analysis of SolutePanel, IonPanel, InterfacePanel source dropdowns
- Wave 1 shape-gui research: Region editor feature requirements
- Wave 1 poly-gen research: Generation pipeline feature requirements
- Atomsk polycrystal tool: Industry reference for feature expectations
