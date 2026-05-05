# Phase 33: Solute Insertion (Tab 4) - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Insert THF or CH₄ solutes into liquid water at specified concentration with GROMACS-ready output. This phase delivers the solute insertion workflow: concentration input (mol/L or wt%), molecule type selection (THF or CH₄ dropdown), random placement with all-atom overlap checking, visualization, and GROMACS export. Placement occurs in liquid phase only (after interface generation), replacing liquid water molecules. Creating posts, ion insertion, and custom molecule upload are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Placement Strategy
- Placement occurs **after** interface generation in **liquid region only** (replaces liquid water, not ice, not hydrate, not guests)
- Maximum 1000 attempts per molecule before considering placement failed
- OpenCode's discretion: failure action when max attempts reached (check how ion insertion handles partial success)
- OpenCode's discretion: whether to show attempt count feedback during placement

### Concentration UX
- **Unit selection:** mol/L (molarity) or wt% — both options available in dropdown selector
- **Molecule count preview:** Real-time preview as user types concentration value (not on blur or on generate)
- OpenCode's discretion: validation behavior when concentration outside reasonable range (too high for system)
- OpenCode's discretion: whether to display concentration range limits (min/max) in UI

### Visual Presentation
- **Follow existing hydrate guest visualization pattern** for consistency
- Check interface code for current hydrate guest rendering (color scheme, style, atom size)
- Use same rendering approach as hydrate guests (not creating new distinct style)
- Researcher: verify hydrate guest visualization in existing interface code

### Error & Progress
- **Progress feedback:** Both progress bar and status messages during generation (e.g., "Placing molecule 5 of 20...")
- **Error messages:** Specific messages with partial success count (e.g., "Only able to place 15 of 20 molecules. Try lower concentration.")
- **Failure recovery:** Match existing ion insertion error handling pattern
- OpenCode's discretion: whether to include cancel button during generation

### OpenCode's Discretion
- Failure action when max placement attempts reached (check ion pattern)
- Attempt count feedback visibility during placement
- Concentration range validation (warn vs block)
- Whether to show concentration limits in UI
- Cancel button presence during generation

</decisions>

<specifics>
## Specific Ideas

- "It's after interface, it only considers liquid region, it will replace liquid water not ice not hydrate not guest" — placement context
- "See how interface is currently done, follow interface style" — visual consistency
- "See how interface handles hydrate guest" — rendering pattern reference
- Error messages should show partial success: "only able to place n molecules"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-solute-insertion-(tab-4)*
*Context gathered: 2026-05-05*
