# Phase 29: Data Structures + Multi-Molecule GROMACS - Context

**Gathered:** 2026-04-14
**Status:** Ready for research

<domain>
## Phase Boundary

Establish foundation for multi-molecule work with extensible data structures and multi-type GROMACS export. This phase resolves the molecule-segment index structure (variable atoms-per-molecule) before any Tab 2/4 code works in Phases 30-32.

**In scope:**
- Data structures that track atoms belonging to different molecule types (ions=1, water=4, guests=5+)
- Multi-molecule GROMACS export (.top with multiple [moleculetype] sections)
- Hydrate lattice selection (sI, sII, sH) with guest molecule selection
- Hydrate cage occupancy specification

**Out of scope:**
- Ion insertion (Phase 30)
- Hydrate generation via GenIce2 (Phase 31)
- Custom molecule upload (Phase 32)
- Display controls (Phase 32)

</domain>

<decisions>
## Implementation Decisions

### Molecule index structure
- Use tuple per molecule: (start_idx, count) where start_idx is first atom index, count is number of atoms
- Handles any atoms-per-molecule: ions (1), water (4), CH4 (5), THF (12), etc.
- **OpenCode's Discretion:** Whether to include molecule type in the tuple or track separately. Include type if it simplifies downstream code without adding complexity.

### GROMACS topology format
- Main topology file uses `#include` to include separate .itp files per molecule type
- One .itp file per moleculetype: water.itp, na.itp, cl.itp, ch4.itp, thf.itp, h2.itp
- [molecules] section lists counts per type in order of appearance

### Bundled molecule parameters
User will provide .gro/.itp files for:
- Water (SOL) — already exists in codebase
- Na+ (sodium ion)
- Cl- (chloride ion)  
- CH4 (methane)
- THF (tetrahydrofuran)
- CO2 (carbon dioxide) — research: TraPPE-small compatible with TIP4P-ice? Or skip due to Settle complexity?
- H2 (hydrogen)

**Research needed:**
1. CO2 force field: Check TraPPE-small compatibility with TIP4P-ice water model (requires Settle). If incompatible, suggest alternatives or note as "skip for now"
2. CH4, THF: Compare TraPPE vs GAFF/GAFF2 force fields. User has parameters for both — recommend based on compatibility with TIP4P-ice

### Hydrate lattice display
- Display when user selects sI, sII, or sH
- Show: cage types (e.g., "512" small cage, "5^12 6^8" large cage), cage count per type, unit cell dimensions (a, b, c in Å)
- **OpenCode's Discretion:** Full cell parameters vs simplified. Include what's needed for GROMACS box generation.

### Guest cage occupancy
- User specifies percentage (0-100%) per guest type
- System distributes guests evenly across matching cage types
- **OpenCode's Discretion:** UI design — slider, text input, or dropdown. Best UX for scientific workflow.

</decisions>

<specifics>
## Specific Ideas

- "One main topology and use #include for a clean main topology. One .itp per moleculetype."
- User will provide .gro/.itp parameters — include human checkpoint in execute phase where user provides the files
- "CO2 is more complicated... check if it's compatible with TIP4P-ice... or easier to skip"
- "For CH4, THF... currently plan to use gaff/gaff2, but also check if it's better to use TraPPE"
- No specific UI references — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

- CO2 implementation may be skipped if TraPPE-small incompatible with TIP4P-ice (Phase 31 or later)
- Custom molecule upload (Phase 32)
- Per-molecule-type display controls (Phase 32)

</deferred>

<research_flags>
## Research Needed

1. **CO2 + TIP4P-ice compatibility**: Does TraPPE-small work with TIP4P-ice water model? Requires Settle constraint.
2. **CH4/THF force field recommendation**: TraPPE vs GAFF/GAFF2 — which pairs better with TIP4P-ice?
3. **GenIce2 hydrate API**: How to pass guest molecules and cage occupancy? (documented as needing research)

</research_flags>

---

*Phase: 29-data-structures-gromacs*
*Context gathered: 2026-04-14*
