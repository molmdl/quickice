# Phase 32: Architecture Preparation - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Infrastructure foundation for multi-tab molecule insertion — tab reordering (Ion Tab 4→6), molecule type tracking (MoleculetypeRegistry), ITP parsing, and GRO/ITP validation. This phase delivers the structural changes that Phases 33-34 will build on.

</domain>

<decisions>
## Implementation Decisions

### Dependency and Data Flow

**Tab Dependency Graph:**
- Ice (Tab 1) → Hydrate (Tab 2) → Interface (Tab 3)
- Interface → Solute (Tab 4) and Custom (Tab 5) [both use liquid region only]
- Ion (Tab 6) needs source dropdown: Interface, Custom, or Internal CH4/THF
- Custom insertion replaces overlapping liquid water, can feed to Ion or Internal CH4/THF
- Internal CH4/THF can take from Interface or Custom, feeds to Ion

**Dependency Handling:**
- Soft block with error message (current behavior) - user can click action button but sees error explaining they need to generate source first
- Example: "No Interface - Please generate an interface structure first in the Interface Construction tab."

**Result Persistence:**
- Keep all results (current behavior) - each tab keeps its result even if source changes
- No automatic invalidation when source regenerates
- Export combines whatever exists at time of export

**Visualization Behavior:**
- Each tab shows placeholder until generated
- After generation, shows complete result for that tab
- Ion tab shows Interface+Ions combined system
- Solute tab shows Interface+Solute combined system
- Custom tab shows Interface+Custom combined system
- Independent of what source tab shows

### Tab Reordering

**User Experience:**
- Tab positions change silently on upgrade to v4.5
- No notification, tooltip, or first-run dialog about reordering
- Users discover new tab order naturally

**Tab Reference Style:**
- Remove all numbering from error messages and UI text
- Use tab names only: "Ice Generation tab", "Hydrate Config tab", "Interface Construction tab", "Solute Insertion tab", "Custom Molecule tab", "Ion Insertion tab"
- Error message example: "Generate interface in Interface Construction tab first"
- Rationale: Flexibility for future maintenance, avoids confusion after reordering

**Tab Order Policy:**
- Fixed workflow order for simplicity: Ice→Hydrate→Interface→Solute→Custom→Ion
- Not customizable by user
- Follows logical dependency flow

### Moleculetype Naming Visibility

**Internal Registry Names:**
- CH4_HYD, THF_HYD for hydrate guests
- CH4_LIQ, THF_LIQ for liquid solutes
- CUSTOM_MOL_1, CUSTOM_MOL_2, etc. for custom molecules

**GROMACS Export:**
- Use registry names directly in .top files to avoid duplicate moleculetype errors
- Example: [ molecules ] section lists "CH4_HYD  10" and "CH4_LIQ  5" separately

**User-Facing Names:**
- UI dropdowns and labels: "CH4 solute", "THF solute", "Custom molecule 1"
- Export success messages: Show actual GROMACS moleculetype names used
- Log output: Show registry names for debugging

**Custom Molecule Naming:**
- Default: "MOL" (increment to "MOL_1", "MOL_2" for uniqueness if needed)
- User can change name during upload/configuration
- Validation: Must not duplicate internally supported names (SOL, CH4, THF, NA, CL, CO2, H2, etc.)

### Validation Feedback Timing

**When to Validate:**
- Immediate on file upload (as soon as user selects .gro/.itp files)
- Rationale: Simpler workflow, prevents discovering errors at export time

**Validation Feedback:**
- Show validation status immediately after file selection
- Specific error messages about what's missing and what's skipped
- Example: "Missing [ atomtypes ] section in custom_mol.itp" or "Atom count mismatch: GRO has 15 atoms, ITP defines 12 atoms"

**Validation Thoroughness:**
- Research this in research phase (depends on ITP parser capabilities)
- Minimum: File existence, parseable format, GRO/ITP consistency (atom counts, residue names)
- Potential: [ atomtypes ] presence, mass/charge sanity checks

### Error Message Specificity

**Specificity Level:**
- Research phase determines feasible specificity based on ITP parser
- Target: File-level details + line-level details where feasible
- Example good: "Missing [ atomtypes ] section in custom_mol.itp"
- Example better: "Line 45: Expected 12 atoms, found 15 in custom_mol.gro"

**Error Reporting Strategy:**
- Clear, concise, easy to read
- Sufficient technical info for debugging
- Two channels: Error dialog + in-app log box
- Optional: Write detailed error log to text file (unique filename) for user reference after closing QuickIce

**Error Message Tone:**
- Match current application style: Plain language, friendly but professional
- Action-oriented guidance when possible
- Example current style: "No hydrate structure available.\n\nPlease:\n1. Go to Hydrate Config tab\n2. Generate a hydrate structure\n3. Click 'Use in Interface →'"

**Multiple Issues Reporting:**
- OpenCode's Discretion: Choose between batch report (all issues at once), fail fast (stop at first), or warnings+errors approach
- Priority: Clarity and user-friendliness

### OpenCode's Discretion

**Tab Order Implementation:**
- Exact positioning logic for fixed workflow order
- How to enforce non-customizable order (if needed)

**Validation Implementation:**
- Validation thoroughness level (after research confirms ITP parser capabilities)
- Multiple issues reporting format (batch vs. fail-fast vs. warnings+errors)
- Whether to write error log files (and filename format)

**TabIndex Enum:**
- Exact enum structure and values
- How to integrate with existing tab index references in codebase

**MoleculetypeRegistry:**
- Internal data structure design
- Name collision detection logic
- Integration with existing MOLECULE_TO_GROMACS mapping

</decisions>

<specifics>
## Specific Ideas

**Current Behavior References:**
- Ion tab dependency check: Shows QMessageBox.warning with "Please generate an interface structure first in the Interface Construction tab" (main_window.py:747-750)
- Hydrate tab dependency check: Shows step-by-step guidance (main_window.py:596-604)
- Result persistence: Interface result stored at main_window.py:537, Ion result at main_window.py:777, no invalidation when source regenerates
- Tab reference in code: Currently uses "Tab 1", "Tab 2" style in comments and some tooltips (to be replaced with tab names only)

**Dependency Graph Visualization:**
- Consider showing tab dependencies in help dialog or documentation
- "Workflow: Ice → Hydrate → Interface → Solute/Custom → Ion" with branches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 32-architecture-preparation*
*Context gathered: 2026-05-05*
