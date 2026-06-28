# Research Summary: Architecture Integration — Polycrystalline Builder into QuickIce

**Domain:** GUI architecture integration for polycrystalline ice builder
**Researched:** 2026-06-28
**Overall confidence:** HIGH (first-party code analysis; patterns derived from direct inspection)

## Executive Summary

The polycrystalline builder should integrate as a **new top-level tab (TabIndex=6, "Polycrystal Builder")** — not as a sub-mode of the existing Interface tab. This is the strongest recommendation of this research. The Interface tab has a fundamentally different interaction model (select candidate → configure mode → generate) compared to the polycrystal builder (draw regions → assign phases → preview in 3D → generate → iterate). Cramming a shape editor with phase assignment, undo stack, and 2D/3D split preview into the Interface tab's QStackedWidget would violate the existing two-column layout pattern and make both features harder to use. A dedicated tab preserves the clean separation and allows each tab to evolve independently.

The polycrystal result should be stored as `_current_polycrystal_result` (a new `PolycrystalStructure` dataclass) on MainWindow, following the established CP-01 duck-typing pattern. It should be **compatible with `InterfaceStructure`** so the downstream pipeline (Solute → Ion → GROMACS Export) works unchanged. The cleanest approach: `PolycrystalStructure` inherits from or is convertible to `InterfaceStructure`, with the multi-phase breakdown carried as additional metadata (per-region molecule counts, boundary info) that the export pipeline can use for richer `.top` files.

Worker threading follows the `InterfaceGenerationWorker` pattern (QObject + moveToThread), not the `HydrateWorker` pattern (QThread subclass). The polycrystal generation is multi-step (N regions × generate+clip+rotate), so progress reporting needs two levels: region-level ("Generating region 3/7: Ice Ih grain...") and sub-step-level ("Clipping molecules... 340/512"). Cancellation must be checked between every region, as each GenIce2 call takes 0.05–3s.

The multi-phase VTK rendering is straightforward: each phase region gets its own bond-line actor with a distinct color. VTK handles 5+ actor groups efficiently (the existing viewers already manage ice+water+guests as separate actors). A phase color legend widget (simple QLabel with colored dots) is sufficient for MVP.

## Key Findings

**Tab placement:** New Tab 6 is strongly recommended. Sub-mode under Interface creates UX and code organization problems. Sub-tabs add nesting complexity. (HIGH confidence)

**Data flow:** Polycrystal output should flow into Solute → Ion → Export via the existing cross-tab pipeline. The `InterfaceStructure` format is already the canonical interchange type. PolycrystalStructure extends it with multi-phase metadata. (HIGH confidence)

**Worker architecture:** QObject + moveToThread pattern (consistent with workers.py and custom_molecule_worker.py). Two-level progress signals. Per-region cancellation checks. (HIGH confidence)

**State management:** `_current_polycrystal_result` attribute on MainWindow, parallel to existing `_current_interface_result` pattern. New `PolycrystalConfig` and `PolycrystalStructure` dataclasses. (HIGH confidence)

**Multi-phase rendering:** Per-phase vtkActor groups with phase-specific colors. VTK handles this fine — no architectural changes needed. (HIGH confidence)

**GROMACS export:** All phases use the same water model (TIP4P-ICE), so the main `.top` file structure is unchanged. Multiple guest types in different hydrate regions need per-region moleculetype tracking via MoleculetypeRegistry, which already supports `_H` and `_L` suffixes. Extension for per-grain moleculetypes (e.g., `SOL_G1`, `SOL_G2`) is feasible but not needed for MVP. (MEDIUM-HIGH confidence)

**Coexistence with Interface tab:** Interface tab's slab/pocket/piece modes should remain as "quick modes." The polycrystal builder is an "advanced mode" for multi-grain/multi-phase systems. The simpler Interface modes handle 90% of use cases; polycrystal handles the remaining 10%. No replacement planned. (HIGH confidence)

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Tab scaffolding + shape editor + single-phase generate** — Create new tab with QGraphicsView shape editor, single-phase generation (all regions same phase, e.g., all Ice Ih with different orientations). This validates the data flow, worker architecture, and VTK rendering with minimal algorithmic complexity.
   - Addresses: tab placement, PolycrystalConfig/Structure dataclasses, worker pattern, per-phase VTK colors
   - Avoids: multi-phase boundary complexity, GROMACS export changes

2. **Phase 2: Multi-phase generation + grain boundaries** — Add multi-phase support with the buffer-zone strategy from phase-boundary research. Ice Ih + liquid water first (uses existing overlap_resolver), then Ice Ih + Ice II (needs buffer zone).
   - Addresses: buffer zone generation, density mismatch handling
   - Avoids: hydrate-containing polycrystals (most complex)

3. **Phase 3: Hydrate-containing polycrystals** — Add sI/sII/sH hydrate regions with guest molecules. Guest molecule handling at grain boundaries. Extended GROMACS export for per-region moleculetypes.
   - Addresses: hydrate grain generation, guest molecule survival at boundaries

4. **Phase 4: Voronoi auto-generation + presets** — Add auto grain generation via Voronoi tessellation. Preset buttons for common polycrystal geometries.
   - Addresses: UX acceleration for common workflows

**Phase ordering rationale:**
- Phase 1 establishes the GUI architecture (most code, least physics)
- Phase 2 adds multi-phase physics incrementally (reuses overlap_resolver)
- Phase 3 adds hydrate complexity (builds on Phase 2 buffer zones)
- Phase 4 adds convenience features (lowest risk, highest UX value)

**Research flags for phases:**
- Phase 1: Shape editor ↔ core engine data contract needs precise specification
- Phase 2: Buffer zone width and composition needs empirical validation
- Phase 3: Guest molecule escape from hydrate cages at boundaries needs investigation
- Phase 4: Voronoi with mirror-point technique needs PBC testing

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Tab placement | HIGH | Direct code analysis of existing 6-tab structure; clear UX reasoning |
| Data flow design | HIGH | Based on inspection of all existing cross-tab flows and dataclasses |
| Worker architecture | HIGH | Two existing patterns (QThread subclass vs QObject+moveToThread); clear precedent |
| State management | HIGH | CP-01 pattern documented in AGENTS.md; 5 existing `_current_*_result` attributes |
| Multi-phase VTK rendering | HIGH | Existing viewers handle 2-3 actor groups; scaling to 5+ is architecturally identical |
| GROMACS multi-phase export | MEDIUM-HIGH | write_multi_molecule_top_file already handles arbitrary molecule_index; per-region granularity is new |
| Interface coexistence | HIGH | Interface modes cover simple cases; polycrystal covers complex; no overlap in use cases |

## Gaps to Address

- **PolycrystalStructure ↔ InterfaceStructure compatibility**: Exact field mapping needs design. Option A: subclass InterfaceStructure. Option B: separate dataclass with `to_interface_structure()` method. Option B is cleaner (no inheritance coupling) but needs more code.
- **Per-region molecule tracking in GROMACS export**: Current export treats all ice water as "SOL" and all guests as "CH4_H"/"THF_H". Multi-phase polycrystal needs per-region tracking for physical accuracy (different regions may have different guest types).
- **Undo stack scope**: QUndoStack lives on the shape editor panel. When user switches tabs, should undo history be preserved? Yes — but memory management needs consideration.
- **Shape editor ↔ core engine data contract**: The `PolycrystalConfig` needs to carry a list of `PhaseRegion` objects (from shape-gui research). The core engine receives this and generates the structure. The exact interface needs specification.
