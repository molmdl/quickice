# Phase 31: Tab 2 - Hydrate Generation - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

User can generate hydrate structures with guest molecules (CH4, THF) via GenIce2, view in 3D, and export to GROMACS. Hydrate structures can be selected in Interface Construction tab as ice layer for ice-hydrate interfaces. Building hydrate for interface is in-scope; custom guest molecules (Phase 32) is separate.

</domain>

<decisions>
## Implementation Decisions

### Hydrate Generation Workflow
- Generate button → show progress + info in info panel → show 3D in viewer → user exports on demand
- Supercell defaults: 1×1×1 (single unit cell)
- Step-by-step log during generation ("Generating sI lattice...", "Placing guests...", "Building supercell...")
- Summary at end: total atoms, molecule counts, cage breakdown

### Guest Molecules (Phase 31)
- **CH4, THF only** for Phase 31
- Force field: GAFF/GAFF2
- User will provide .itp files when prompted
- **Remove H2** from guest options
- **Research CO2** separately, seek approval before adding to Phase 31

### Guest Rendering
- Guests render as **ball-and-stick** (distinct from water framework)
- Colors: **standard chemistry colors** (C=gray, O=red, H=white)
- Water framework renders as **lines** (same as existing ice style)
- Dedicated hydrate viewer (not shared with main viewer)

### Hydrate Viewer Layout
- Dedicated viewer widget in Hydrate Config tab
- **Same stacked pattern as InterfaceViewer**: placeholder until generation, then 3D viewer
- Below HydratePanel controls (split or vertical layout)

### Unit Cell Info Display
- Info panel in Hydrate Config tab (layout similar to Interface tab)
- Shows: cage types (512, 51262), cage counts, occupancy achieved, guest count
- Step-by-step generation log + final summary

### Hydrate GROMACS Export
- Menu-based: File → Export Hydrate for GROMACS
- Files produced: `.gro` + `.top` + bundled guest `.itp`
- Water model: **TIP4P-ice** (shipped with app)
- Atom numbering: wrap at 100000 (follow GROMACS convention)

### Hydrate → Interface Builder
- **Yes** - hydrate structures feed into Interface Construction tab
- Generate hydrate in Hydrate tab → dropdown in Interface tab to select
- Similar to how Tab 1 (Ice Generation) feeds Interface Builder
- Any Tab 1 or Hydrate generation updates the Interface Builder dropdown
- **Cell type handling**: Follow current ice handling pattern
  - Some hydrate lattices can do interfaces (sI, sII likely orthogonal)
  - sH may not be usable for interfaces (non-orthogonal cells → gaps)
  - Show warning in info panel if selected lattice is non-orthogonal

### OpenCode's Discretion
- Exact layout arrangement (split vs vertical)
- Specific info panel formatting
- Implementation details for guest placement visualization
- Hydrate viewer widget internals
- Export dialog specifics

</decisions>

<specifics>
## Specific References

- "Follow current" refers to established patterns in InterfacePanel, IonPanel
- Tab order in GUI: Ice Generation → Hydrate Config → Ion Insertion → Interface Construction
- Cell type constraint: sH is non-orthogonal, may need warning like Ice II blocking

</specifics>

<deferred>
## Deferred Ideas

- **CO2 force field research** — TRAPPE-AA compatibility with TIP4P-ice needs investigation. Seek user approval before adding CO2 guest option.
- **sH hydrate cell type** — Research whether sH can be used for interfaces. Add warning if non-orthogonal cells create gaps.
- **Custom guest molecules** — Phase 32 path for user-uploaded .gro/.itp files
- **H2 guest molecule** — Removed from Phase 31, defer to later phase with proper FF research

</deferred>

---

*Phase: 31-tab-2-hydrate-generation*
*Context gathered: 2026-04-15*
