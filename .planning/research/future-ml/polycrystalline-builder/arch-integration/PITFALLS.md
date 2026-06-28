# Domain Pitfalls — Polycrystalline Builder Architecture Integration

**Domain:** QuickIce GUI architecture integration for polycrystalline builder
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Polycrystal as Interface Sub-Mode

**What goes wrong:** Adding "Polycrystal" as a 4th mode in InterfacePanel's QStackedWidget, alongside Slab/Pocket/Piece.

**Why it happens:** Both Interface and Polycrystal deal with ice-water structures; the Interface tab already has "mode" switching; feels like "just another mode."

**Consequences:**
- InterfacePanel grows from ~935 lines to 2000+ lines (shape editor, region model, undo stack, phase assignment all crammed in)
- QStackedWidget switching destroys polycrystal state when user switches to Slab mode
- Polycrystal's shape editor needs QGraphicsView which Interface tab doesn't have
- User confusion: "Which mode should I use?" when slab and polycrystal overlap
- Future: polycrystal tab gets sub-modes (Voronoi, manual, preset) — these would need a SECOND QStackedWidget nested inside the first
- Testing: polycrystal-specific tests must set up InterfacePanel context

**Prevention:** New dedicated tab (TabIndex=6). The Interface tab stays focused on single-phase interfaces.

**Detection:** If interface_panel.py exceeds 1200 lines, polycrystal code has leaked in.

### Pitfall 2: PolycrystalStructure Not Compatible with Downstream Pipeline

**What goes wrong:** `PolycrystalStructure` is designed independently of `InterfaceStructure`, making it impossible to feed into Solute/Ion insertion without rewriting those modules.

**Why it happens:** PolycrystalStructure has different atom ordering (per-region grouping) vs InterfaceStructure (ice→water→guest grouping). The SoluteInserter expects InterfaceStructure's `ice_atom_count`, `water_atom_count`, `guest_atom_count` fields.

**Consequences:**
- Solute and Ion tabs can't consume polycrystal results
- User must export to PDB/GRO and re-import — terrible UX
- Duplicating solute/ion logic for polycrystal creates maintenance burden

**Prevention:** `PolycrystalStructure.to_interface_structure()` method that:
1. Reorders atoms: ice first → water → guest
2. Sets `ice_atom_count`, `water_atom_count`, `guest_atom_count`
3. Populates `ice_nmolecules`, `water_nmolecules`, `guest_nmolecules`
4. Preserves `cell` array
5. Builds `molecule_index` list in correct order

**Detection:** If SolutePanel's source dropdown doesn't include "Polycrystal" or `_on_insert_solutes` can't handle polycrystal source, this pitfall has manifested.

### Pitfall 3: Blocking GUI During Multi-Region Generation

**What goes wrong:** Polycrystal generation runs synchronously in the main thread, freezing the GUI for 0.3–30 seconds.

**Why it happens:** Developer thinks "it's just a few GenIce2 calls" and skips the QThread boilerplate. Or copies HydrateWorker's QThread-subclass pattern without realizing it's a legacy pattern.

**Consequences:**
- GUI becomes unresponsive during generation
- No progress updates visible
- No cancel button works
- OS may report "application not responding"
- Violates AGENTS.md guidance about HydrateWorker pattern

**Prevention:** Always use PolycrystalWorker(QObject) + moveToThread(QThread). Check isInterruptionRequested() between every region. Emit progress/status signals.

**Detection:** If `QApplication.processEvents()` appears in generation code, this pitfall has manifested.

### Pitfall 4: Memory Leak from QUndoStack with Complex Shape Editing

**What goes wrong:** QUndoStack grows unbounded as user adds, moves, and resizes dozens of regions. Each undo command stores a copy of the affected PhaseRegion and QGraphicsItem state.

**Why it happens:** QUndoStack default has no limit. Complex polycrystals with 50+ regions can generate 200+ undo commands in a session.

**Consequences:**
- Memory grows to hundreds of MB with complex editing sessions
- Eventually crashes on memory-constrained systems
- Undo history becomes unusably deep (user can't find the action they want to undo)

**Prevention:** Set `QUndoStack.setUndoLimit(100)` on the shape editor's undo stack. This is the standard Qt recommendation.

**Detection:** If memory usage exceeds 500MB after a shape-editing session with 50+ region operations.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Molecule-Level Clipping Not Used for Region Boundaries

**What goes wrong:** Filtering atoms (not molecules) by spatial region membership, splitting water molecules at boundaries.

**Why it happens:** Atom-level filtering is simpler to implement (one loop instead of molecule-grouped loop).

**Consequences:** Broken molecules at region boundaries (e.g., O inside, H outside). GROMACS energy minimization fails with "1-4 interactions" errors. VTK rendering shows disconnected bonds.

**Prevention:** Always clip by center-of-mass: `com = positions[i:i+4].mean(axis=0)`, then check `polygon.contains(Point(com[0], com[1]))`.

**Detection:** If GROMACS `gmx grompp` reports bond/angle errors after energy minimization.

### Pitfall 6: VTK Z-Buffer Fighting with Translucent Region Shells

**What goes wrong:** Multiple overlapping translucent actors (region preview shells) cause z-buffer fighting, producing flickering or incorrect rendering.

**Why it happens:** VTK's default depth buffer doesn't handle layered translucent objects well. When two translucent actors overlap, the rendering order matters.

**Consequences:** 3D preview looks wrong; regions appear to "pop" in and out; user can't see the correct 3D shape.

**Prevention:** 
1. Set `vtkActor.GetProperty().SetOpacity(0.2)` (lower opacity = less fighting)
2. Use `vtkDepthSortPolyData` mapper for correct translucent rendering
3. Or render regions as wireframe outlines instead of filled translucent shells

**Detection:** If 3D preview flickers when two regions overlap in the view.

### Pitfall 7: Shapely Polygon Coordinate Units Mismatch

**What goes wrong:** QGraphicsView works in pixel coordinates; shapely works in nanometers. A coordinate mapping bug puts shape data in the wrong units.

**Why it happens:** The nm ↔ scene coordinate mapping has two directions; bugs in either direction corrupt the polygon data.

**Consequences:** Region clipping fails (polygon too large or too small by 100x); molecules are included/excluded incorrectly; generated structure is wrong.

**Prevention:** Use a SceneCoordinateMapper class with unit tests. Never pass pixel coordinates to shapely. Add assertions: `assert polygon.bounds[0] < 1000  # Must be in nm, not pixels`.

**Detection:** If generated structure has wildly wrong molecule counts for the box dimensions.

### Pitfall 8: InterfaceStructure Duck-Typed Attributes Not Forwarded

**What goes wrong:** `PolycrystalStructure.to_interface_structure()` creates a valid InterfaceStructure but doesn't forward the solute/custom_molecule duck-typed attributes that downstream workflows expect.

**Why it happens:** The duck-typed attributes (solute_type, custom_molecule_positions, etc.) are set at runtime by MainWindow, not by the structure dataclasses themselves. The conversion method doesn't know about them.

**Consequences:** If a polycrystal result has solutes inserted, then ions are inserted, the solute information is lost during the InterfaceStructure conversion.

**Prevention:** In MainWindow's `_on_insert_solutes()` when source="Polycrystal": after calling `to_interface_structure()`, copy any existing solute/custom attributes from the polycrystal structure to the new InterfaceStructure. This mirrors the existing pattern for Interface→Solute→Ion flow.

**Detection:** If ion insertion on a polycrystal-with-solutes source loses solute molecule positions.

### Pitfall 9: GROMACS .top File with Conflicting Atomtypes from Multiple Hydrate Types

**What goes wrong:** A polycrystal with both sI-CH4 and sII-THF hydrate regions produces a .top file with conflicting GAFF2 atomtype definitions (e.g., "hc" defined twice with different parameters from different ITP files).

**Why it happens:** The `_write_atomtypes_block` function deduplicates within a single molecule type, but different molecule types might define the same atomtype name with different parameters (though in practice, GAFF2 atomtypes are consistent across molecule types).

**Consequences:** GROMACS `gmx grompp` fails with "Duplicate atomtype" or uses wrong parameters.

**Prevention:** Use the existing `_check_custom_atomtype_conflict()` function for each atomtype before writing. The existing deduplication in `write_multi_molecule_top_file` handles this case — just need to use it correctly.

**Detection:** If `gmx grompp` reports duplicate atomtype errors for a multi-hydrate polycrystal.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 10: Phase Color Confusion Without Legend

**What goes wrong:** Multiple similar blue/cyan phases (Ice Ih = cyan, Ice II = blue, Ice III = slate blue, liquid = cornflower) are hard to distinguish in 3D preview.

**Why it happens:** Ice phases are all shades of blue/cyan by convention; there aren't enough distinct colors for 5+ phases.

**Consequences:** User can't tell which region is which phase in the 3D preview.

**Prevention:** Add a simple phase color legend (QLabel with colored squares) in the VTK viewer corner. Also allow clicking a region in the legend to highlight it in the 3D view.

**Detection:** If users report confusion about which color represents which phase.

### Pitfall 11: QUndoStack Reset on Tab Switch

**What goes wrong:** User draws shapes on Tab 6, switches to Tab 0 to generate ice, switches back — and the undo history is gone.

**Why it happens:** QUndoStack is owned by PolycrystalPanel, which stays alive during tab switches. But if the panel is somehow recreated or the stack is cleared, history is lost.

**Prevention:** QUndoStack persists as long as PolycrystalPanel exists. Don't clear it on tab switches. Only clear on "New Polycrystal" action or when user explicitly resets.

**Detection:** If Ctrl+Z doesn't work after switching tabs and back.

### Pitfall 12: Region ID Collision After Delete + Re-Add

**What goes wrong:** User deletes region 3, then adds a new region — which gets region_id=4 instead of 3. Later, region IDs have gaps.

**Why it happens:** Simple counter-based ID assignment.

**Consequences:** GROMACS export references region IDs that don't match the visual numbering. Log messages say "Region 5" but user sees only 4 regions.

**Prevention:** Region IDs are internal identifiers, not display numbers. Display uses 1-based sequential numbering. Region IDs are never reused (avoids ambiguity). Gap in IDs is fine.

**Detection:** If region list shows "Region 1, Region 2, Region 5" after deletion.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Tab scaffolding | Pitfall 1: Polycrystal as sub-mode | Design as separate tab from the start |
| PolycrystalConfig dataclass | Pitfall 7: Unit mismatch in polygon coords | SceneCoordinateMapper with assertions |
| PolycrystalWorker | Pitfall 3: Blocking GUI | QObject+moveToThread pattern from day 1 |
| PolycrystalStructure | Pitfall 2: Incompatible with downstream | `.to_interface_structure()` method from day 1 |
| Region clipping | Pitfall 5: Atom-level clipping | Always clip by molecule COM |
| VTK region preview | Pitfall 6: Z-buffer fighting | Low opacity + depth sort |
| QUndoStack | Pitfall 4: Memory leak | Set undoLimit=100 |
| Multi-phase generation | Pitfall 9: Conflicting atomtypes | Reuse existing dedup in gromacs_writer |
| Source dropdown integration | Pitfall 8: Lost duck-typed attributes | Forward solute/custom attributes during conversion |
| 3D preview | Pitfall 10: Phase color confusion | Add color legend widget |

## Sources

- QuickIce codebase: Direct analysis of all pitfalls identified from existing patterns
- Wave 1 research: Pitfalls from shape-gui, poly-gen, phase-boundary research
- Qt QUndoStack documentation: Memory management guidance
- VTK translucent rendering: Known z-buffer fighting issue with layered translucent actors
- AGENTS.md: CP-01 decision, HydrateWorker guidance
