# Phase 30: Tab 4 - Ion Insertion (NaCl) - Context

**Gathered:** 2026-04-15
**Status:** Ready for research/planning

<domain>
## Phase Boundary

User can insert NaCl ions into liquid phase of interface with concentration-based calculation. Reuses InterfaceStructure from Tab 3. Replacement approach (replace water in liquid). Charge neutrality enforced. GROMACS export with ion parameters. Water density display in Tab 1 info panel (WATER-02).
</domain>

<decisions>
## Implementation Decisions

### Concentration input
- Units: mol/L (Molar) only
- Display: Show calculated ion count only (Na+ and Cl- pairs), not mass
- Volume: Liquid phase volume only (not ice, not total box)
- Threshold: OpenCode's discretion to handle edge cases

### Placement behavior
- Method: Replace water molecules in liquid region (not insert in empty space)
- Charge neutrality: Neutralizes total charge from custom molecules (for Phase 32 compatibility)
  - If custom molecule has +Q charge, add Q* Cl- to neutralize
  - If custom molecule has -Q charge, add Q* Na+ to neutralize
- Region: Skip ice region molecules (replace only in liquid region, after ice index)

### Ion rendering (3D viewer)
- Style: VDW spheres (not ball-and-stick)
- Colors: Na+ = gold (paler), Cl- = lime/paler green
- Bonds: No bonds to nearby water (solvation bonds not shown)

### GROMACS export
- Format: Bundle as ion.itp file (not inline in .top)
- Names: NA / CL (GROMACS standard residue/atom names)
- Custom itp: User will provide ion.itp - research needed for how to include

### OpenCode's Discretion
- Minimum concentration threshold handling
- Exact VDW sphere radii (standard or scaled)
- Default ion.itp parameters if user doesn't provide custom

</decisions>

<specifics>
## Specific Ideas

- "User wants to provide ion.itp - needs research on force field compatibility (KBFF vs Amber)"
- "System neutralizes charge from custom molecules for Phase 32 compatibility"
- Colors should be "paler" - less saturated gold/lime for better visual contrast with ice

*Research needed for Phase 30:*
- Which force fields (KBFF, Amber, etc.) are compatible with TIP4P-ICE water model
- How to include user-provided custom ion.itp in GROMACS export
- KBFF ion parameters vs Amber ion parameters - tradeoffs

</specifics>

<deferred>
## Deferred Ideas

- Custom ion force field (user provides ion.itp) — Phase 32 or separate phase
- Support for custom charged molecules — Phase 32 (Phase 30 prepares the neutralization logic)
- g/kg mass fraction input option — not in Phase 30 scope

</deferred>

---

*Phase: 30-ion-insertion*
*Context gathered: 2026-04-15*