# Phase 31: Tab 2 - Hydrate Generation - Context

**Gathered:** 2026-04-15
**Updated:** 2026-04-15 (FF decisions clarified)
**Status:** BLOCKED — awaiting user-provided .itp files

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
- **CO2 and H2 REMOVED** from UI — do not include
- Force field: **User will provide .itp files**
- .itp files go in `quickice/data/`

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

<force_field_pending>
## Force Field Files — PENDING USER APPROVAL

### Guest Molecule .itp Files Needed

| Guest | .itp File | Location | Status |
|-------|-----------|----------|--------|
| Methane | `ch4.itp` | `quickice/data/` | ❌ User must provide |
| THF | `thf.itp` | `quickice/data/` | ❌ User must provide |

**Requirements:**
- Must include: `[moleculetype]`, `[atoms]`, `[bonds]`, `[angles]`, `[dihedrals]` sections
- Atom counts must match `GUEST_MOLECULES` dict:
  - CH4: 5 atoms (1 C + 4 H)
  - THF: 12 atoms (4 C + 1 O + 8 H)

### Ion Parameters (Phase 30)

**File:** `quickice/structure_generation/gromacs_ion_export.py`

| Parameter | Current Value | Force Field |
|-----------|---------------|-------------|
| Atom type (Na) | NA | amberGS.ff |
| Atom type (Cl) | CL | amberGS.ff |
| Na mass | 22.9898 g/mol | amberGS.ff |
| Cl mass | 35.453 g/mol | amberGS.ff |
| Na charge | +1 | - |
| Cl charge | -1 | - |

**⚠️ User approval needed:**
- Is amberGS.ff acceptable for ions?
- Or do you have different ion parameters to provide?

### Water Model (TIP4P-ice)

**File:** `quickice/data/tip4p-ice.itp` (existing)

- Source: sklogwiki.org (CC-BY-NC-SA 3.0)
- Credits cited in file header

**⚠️ User approval needed:**
- Is TIP4P-ice acceptable for water model?
- Or do you use a different water model?

</force_field_pending>

<code_cleanup>
## Code Cleanup Required

### Remove CO2/H2 from UI

These files need modification to remove co2/h2:

| File | Action |
|------|--------|
| `quickice/structure_generation/types.py` | Remove co2/h2 from `GUEST_MOLECULES` dict |
| `quickice/gui/hydrate_panel.py` | Remove co2/h2 from guest_combo |
| `quickice/structure_generation/hydrate_generator.py` | Remove co2/h2 parameter mapping |
| `quickice/gui/hydrate_export.py` | Remove co2/h2 from `_get_guest_itp_path()` |

### Remove Fake .itp Files

**DELETE these files if they exist:**
- `quickice/data/ch4.itp` (fake GAFF — user will provide real one)
- `quickice/data/thf.itp` (fake GAFF — user will provide real one)

</code_cleanup>

<specifics>
## Specific References

- "Follow current" refers to established patterns in InterfacePanel, IonPanel
- Tab order in GUI: Ice Generation → Hydrate Config → Ion Insertion → Interface Construction
- Cell type constraint: sH is non-orthogonal, may need warning like Ice II blocking

</specifics>

<deferred>
## Deferred Ideas

- **CO2 guest option** — TRAPPE-AA compatibility with TIP4P-ice needs investigation. User explicitly removed. Add later with proper FF research and approval.
- **H2 guest option** — Removed from Phase 31, defer to later phase with proper FF research and approval.
- **sH hydrate cell type** — Research whether sH can be used for interfaces. Add warning if non-orthogonal cells create gaps.
- **Custom guest molecules** — Phase 32 path for user-uploaded .gro/.itp files

</deferred>

---

*Phase: 31-tab-2-hydrate-generation*
*Context updated: 2026-04-15*

