# Phase 27: Documentation Update - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Document v3.5 features across README, docs/, in-app help, tooltips, and screenshots. Updates existing documentation where v3.5 features appear; does not create new feature documentation system or rewrite user manual.

**Critical constraint:** No fake references, no fake contents, only truth about the code and science. Always verify before adding.

</domain>

<decisions>
## Implementation Decisions

### README content & depth
- Revise outdated contents and add minimal info on updated features
- No highlighting, no new feature section - just update related sections accordingly
- No changelog or version history section
- No version badges

### docs/ organization
- Update existing files (`cli-reference.md`, `gui-guide.md`) where v3.5 features appear
- Technical depth: Similar to current docs style
- Both CLI and GUI docs need updates
- CLI examples: Match existing style (check current `cli-reference.md` for pattern)
- No new v3.5-specific file

### In-app help scope
- Update existing sections where v3.5 features appear
- Correct outdated triclinic error message (line 156: "Triclinic cell: Select different ice phase" is now wrong)
- Add minimal density context within workflow/notes sections
- If new IAPWS reference added, tell user the reference found and seek approval before adding
- Match current style for density mentions

### Tooltip strategy
- No new tooltips needed - check if current tooltips need updates for v3.5
- Fix global tooltip width issues while doing documentation
- Apply global width limit (not manual rewording)
- Fix ALL tooltips (not just v3.5 related)
- Match existing tooltip style
- Some info should go to info panel, not tooltips

### Transformation indicator (Tab 2)
- Show transformation status AND message in Tab 2 info panel log when triclinic phase is transformed
- Candidate metadata includes: `transformation_status`, `transformation_multiplier`, `transformation_message`
- Display after candidate info line in interface generation log

### Screenshot coverage
- Update screenshots showing GUI-related v3.5 features
- Main GUI screenshot: User will decide - list options
- Skip CLI screenshots
- Manual capture if necessary, update current screenshots mainly
- Ensure info/log boxes of both Tab 1 and Tab 2 are up-to-date with v3.5 info

</decisions>

<specifics>
## Specific Items to Update

### README.md
- Review for outdated content related to density, triclinic, CLI
- Add minimal info where features changed
- No new sections or changelog

### docs/cli-reference.md
- Update `--interface` flag documentation
- Add density-related parameter notes if applicable
- Match existing example command style

### docs/gui-guide.md
- Update density display explanation (now IAPWS for Ice Ih and Liquid)
- Update triclinic phase handling (Ice II, V, VI now work in interfaces)
- Note transformation indicator in Tab 2 log

### quickice/gui/help_dialog.py
- Line 156: Remove/fix "Triclinic cell: Select different ice phase" error message
- Update workflow/notes sections for density context
- No new sections

### quickice/gui/main_window.py
- Tab 2 interface log: Add transformation status/message display after candidate info line
- Current line 450: `self.interface_panel.append_log(f"  Candidate: {candidate.phase_id} ({candidate.nmolecules} molecules)")`
- Add: transformation status from `candidate.metadata.get("transformation_status")`
- Add: transformation message from `candidate.metadata.get("transformation_message")`

### Tooltips (all files)
- Apply global width limit via QToolTip stylesheet
- Review all tooltips in: `dual_viewer.py`, `interface_panel.py`, `view.py`
- Match existing tooltip format

### docs/images/
- Review current screenshots for accuracy
- Update if density display or transformation indicator changes visual appearance
- Tab 1 info panel screenshot if density display changed
- Tab 2 info panel screenshot if transformation indicator added

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 27-documentation-update*
*Context gathered: 2026-04-12*
