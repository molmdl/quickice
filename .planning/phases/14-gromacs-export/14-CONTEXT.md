# Phase 14: GROMACS Export - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable direct GROMACS simulation workflow from QuickIce by generating valid .gro, .top, and bundled force field files. Single "Export for GROMACS" menu option produces all three files simultaneously.

</domain>

<decisions>
## Implementation Decisions

### Export type
- GUI feature (not CLI)
- Follows existing QuickIce export pattern: QFileDialog, File menu, consistent UI

### Output location
- QFileDialog.getSaveFileName() lets user pick save location each time
- Follows same pattern as PDB and image export (Phase 11)

### Multi-file handling
- Single dialog for .gro file
- User picks base name (e.g., my_ice.gro)
- .top and .itp files auto-saved in same directory automatically

### Default filename
- User input determines base name
- If user enters "my_ice.gro" → generates my_ice.gro, my_ice.top, my_ice.itp

### Conflict handling
- Default QFileDialog behavior (OS-dependent overwrite warning)
- Consistent with existing PDB export approach

### Validation feedback
- Silent export (no gmx check internally)
- Files saved, user runs gmx check manually if desired

### Menu placement
- "Export for GROMACS" in File → Export submenu
- Same location as Save PDB, Save Diagram, Save Viewport

### OpenCode's Discretion
- Exact dialog button text and labels
- Menu item icon/shortcut
- .itp file inclusion method (copy vs generate)
- .top file format details (atomtypes section, etc.)

</decisions>

<specifics>
## Specific Ideas

- Follow existing export workflow from Phase 11 (PDB, PNG, SVG)
- QFileDialog pattern consistent with current file save operations
- tip4p-ice.itp bundled as application resource

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-gromacs-export*
*Context gathered: 2026-04-05*