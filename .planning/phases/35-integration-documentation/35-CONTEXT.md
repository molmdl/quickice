# Phase 35: Integration & Documentation - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete 6-tab workflow verification and comprehensive documentation for v4.5. This phase ensures all tabs (Ice, Hydrate, Interface, Solute, Custom, Ion) work together reliably, GROMACS export produces correct molecule ordering, keyboard shortcuts are consistent, and users have documentation and in-app guidance for all v4.5 features.

**Scope:** Cross-tab data flow testing, GROMACS export order enforcement, keyboard shortcut implementation, README update, GUI guide update, help dialog enhancement, tooltips for Tab 4/5 controls, user guide for .gro/.itp creation, and screenshot refresh.

**Out of scope:** New features, CLI support for Tab 4/5 (deferred to v4.5.1), bug fixes outside integration scope.

</domain>

<constraints>
## Project Constraints

### Reference Policy
- References can only be added upon verification and explicit approval from user
- All citations must be manually reviewed before inclusion
- Scientific references require source verification

### Style Consistency
- Documentation style must be consistent with current approach
- Update outdated contents while maintaining familiar structure
- Check current code for existing names/shortcuts to avoid duplicates
- No breaking changes without explicit user approval

### Current State Reference
- README.md: 474 lines, CLI-heavy, comprehensive style
- Help dialog: Detailed workflow, keyboard shortcuts, dimension relationships, best practices
- Tooltips: Multi-line with examples, dynamic state-based messages
- Keyboard shortcuts: Tab-specific (Ctrl+G/I/E/J/L/M), no unified export
- Error messages: User-friendly, minimal jargon, QMessageBox-based

</constraints>

<decisions>
## Implementation Decisions

### Documentation Structure
- **README.md:** Simplify to match v4–v4.5 GUI focus (less CLI-heavy, more GUI-focused)
- **GUI guide (docs/gui-guide.md):** OpenCode decides outline structure for Tab 4/5 sections → user approval after planning
- **User guide (.gro/.itp creation):** OpenCode decides approach (dedicated guide vs in-app vs external reference) → user approval after planning

### Keyboard Shortcuts
- **Design principle:** OpenCode decides (unified vs tab-specific) with rationale → user approval after planning
- **Conflict resolution:** If unified export adopted, OpenCode decides how to remap hydrate (Ctrl+E → Ctrl+H, or other approach) → user approval after planning
- **New shortcuts:** OpenCode decides whether to keep Ctrl+L (solute) and Ctrl+M (custom) or change → user approval after planning
- **Current state:** Ctrl+G (ice), Ctrl+I (interface), Ctrl+E (hydrate), Ctrl+J (ion), Ctrl+L (solute), Ctrl+M (custom) are assigned

### Tooltip & Help Text Style
- **Tooltip depth:** OpenCode decides (detailed vs minimal vs adaptive) with rationale → user approval after planning
- **Solute concentration tooltip:** OpenCode decides what to explain (formula vs result vs both) → user approval after planning
- **Custom molecule tooltip:** OpenCode decides how much .gro/.itp guidance to include → user approval after planning
- **Help dialog:** Extend current help dialog with Tab 4/5 workflow, consider grouping improvements (tab/dropdown/toc for navigation)

### Error Messaging
- **Error tone:** User-friendly style (current approach) — no excessive technical jargon
- **GROMACS terminology:** Use GROMACS terms freely (.gro, .itp, [ atomtypes ], residue name) — users know the domain
- **Validation feedback:** OpenCode decides display method (modal dialog vs in-panel status vs toast+dialog) → user approval after planning
- **Error recovery:** OpenCode decides whether to describe problem only or suggest specific fixes → user approval after planning

### Screenshots
- **Scope:** Full refresh except Tab 1 screenshots (Tab 1 existing screenshots can be reused)
- **Naming:** Remove tabX prefix from figure filenames (e.g., "quickice-v4-gui.png" not "tab1-quickice-v4-gui.png")
- **Quantity:** Minimal but sufficient number of screenshots to document critical states
- **Checkpoint:** Human checkpoint for user to take screenshots themselves (provide list of required screenshots)

### OpenCode's Discretion

**Documentation:**
- README reorganization (what to keep, what to move, what to condense)
- GUI guide outline structure for Tab 4/5 (pending user approval)
- User guide approach for .gro/.itp creation (pending user approval)

**Keyboard shortcuts:**
- Unified vs tab-specific export design (with rationale)
- Conflict resolution if unified export adopted
- Whether to keep/change Ctrl+L and Ctrl+M
- All decisions shown to user after planning for approval

**Tooltips:**
- Depth strategy (detailed/minimal/adaptive) with rationale
- What solute concentration tooltip should explain
- How much .gro/.itp guidance in custom molecule tooltips
- All decisions shown to user after planning for approval

**Error messaging:**
- Validation feedback display method
- Error recovery approach (describe vs suggest fixes)
- All decisions shown to user after planning for approval

</decisions>

<specifics>
## Specific Ideas

**Documentation philosophy:**
- "Simplify README to match latest development, since current is mainly v1 CLI stuff, but now v4–v4.5 focus switched to GUI"
- "U decide first, show me outline after planning for my approval" — OpenCode proposes, user approves

**Help dialog enhancement:**
- "Extend current help, but maybe time to update the help grouping info in tab/dropdown/with toc click"
- Consider improving navigation within help dialog (not just sequential sections)

**Screenshot workflow:**
- "Summarize placeholder and screenshots to take in a human checkpoint for me to take ss myself"
- Planner should create checkpoint task listing required screenshots
- User takes screenshots during execution, not during planning

**Consistency requirements:**
- Check existing code for keyboard shortcuts (found: Ctrl+S, Ctrl+Shift+S, Ctrl+D, Ctrl+Alt+S, Ctrl+G, Ctrl+I, Ctrl+E, Ctrl+J, Ctrl+L, Ctrl+M)
- Check existing tooltip style (found: multi-line with examples, dynamic state-based)
- Check existing error message style (found: user-friendly, QMessageBox-based)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

**Note:** CLI support for Tab 4/5 (Solute/Custom) is deferred to v4.5.1 per ROADMAP.md, not a deferred idea from this discussion.

</deferred>

---

*Phase: 35-integration-documentation*
*Context gathered: 2026-05-05*
