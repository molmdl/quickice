# Phase 20: Export - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Export interface structures as GROMACS simulation files (.gro/.top/.itp) using TIP4P-ICE water model. Ice and water molecules are treated as a single SOL molecule type with no chain distinction. This is Tab 2's export counterpart to Tab 1's existing GROMACS export.

</domain>

<decisions>
## Implementation Decisions

### Atom normalization
- Follow Tab 1's 4-point TIP4P-ICE format — export always outputs 4 atoms per molecule (OW, HW1, HW2, MW) for both ice and water phases
- Ice molecules (internally 3-atom: O, H, H) must be normalized to 4-atom TIP4P-ICE format at export time
- MW virtual site positions computed using standard TIP4P-ICE formula (MW = O + α*(H1+H2)/2 where α=0.13458335)
- Uniform atom names across both phases: OW, HW1, HW2, MW

### Topology structure
- Same SOL molecule type for both ice and water phases — no separate molecule types
- Single combined SOL count in [molecules] section (ice_nmolecules + water_nmolecules as one number)
- Follow Tab 1's .top/.itp pattern: self-contained .top file with inline molecule definition + separate .itp for inclusion in another .top
- **EXP-02 overridden:** No chain A/B distinction in .gro or .top files. Ice and water are not separated by chain identifiers.
- No phase boundary indicator in exported files

### Export trigger & naming
- Separate keyboard shortcut for Tab 2 export (not sharing Ctrl+G with Tab 1)
- Two separate menu actions: one for ice export (Tab 1, existing), one for interface export (Tab 2, new)
- Default filename format: OpenCode's discretion (should identify as interface output)
- Dialog title: OpenCode's discretion (should distinguish from Tab 1 export)

### Chain identifiers in .gro
- No chain distinction — all molecules are SOL
- Continuous residue numbering: ice molecules 1..N_ice, water molecules N_ice+1..N_ice+N_water
- Same SOL residue name for all molecules (ice and water)
- .gro title line: OpenCode's discretion (include enough info to identify the file)
- Box vectors from InterfaceStructure.cell: OpenCode's discretion (should match interface structure)

### OpenCode's Discretion
- Exact default filename format for interface export
- Dialog title text for Tab 2 export
- .gro title line content
- Box vector handling (direct from InterfaceStructure.cell)
- Shortcut key choice for Tab 2 export (avoid conflicts with existing shortcuts)
- How ice 3-atom → 4-atom normalization is implemented (reuse Tab 1 logic or new code)

</decisions>

<specifics>
## Specific Ideas

- Follow Tab 1's existing GROMACS export pattern as closely as possible for consistency
- Tab 1 already handles 4-point TIP4P-ICE normalization — reuse that approach
- Tab 1's .top/.itp output style: self-contained .top + separate .itp for inclusion

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-export*
*Context gathered: 2026-04-09*
