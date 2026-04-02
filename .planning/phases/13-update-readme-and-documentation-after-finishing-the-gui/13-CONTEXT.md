# Phase 13: Update README and Documentation After Finishing the GUI - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Update existing v1.x documentation to reflect v2.0 GUI application. Create in-app quick reference help (INFO-04 deferred from Phase 11). Add screenshots demonstrating the GUI. Keep CLI documentation prominent while making GUI documentation supplementary.

</domain>

<decisions>
## Implementation Decisions

### README structure
- Keep current CLI-focused approach (CLI remains primary, GUI supplementary)
- Update Overview section to mention GUI exists
- Update "What is QuickIce?" definition statement to include GUI
- Add brief GUI calling method after installation section
  - Leave placeholder for standalone executable (Phase 12 pending)
  - Example: `python quickice_gui.py` or link to docs for details
- Link to docs/ folder for full GUI documentation
- Ask users to refer to docs or in-app help for GUI usage details

### In-app help content (INFO-04)
- Help dropdown menu option in menu bar
- Opens modal dialog (not panel, not F1 shortcut)
- Quick reference content (plain text format):
  - Brief explanation of what QuickIce does
  - Keyboard shortcuts list (Enter to generate, Escape to cancel, Ctrl+S save, etc.)
  - Workflow summary: input parameters → click diagram → generate → view in 3D → export
- For scientific background: suggest external sources (GenIce2, IAPWS)
  - Clicking on phase already shows validated references (Phase 11 feature)
  - Don't duplicate that content in help dialog

### Screenshots & demos
- PNG format for all screenshots (lossless, good for UI)
- Static screenshots only, no animated GIFs
- Hero screenshot in README:
  - Single main window screenshot near top
  - Use markdown: `![QuickIce GUI](docs/images/quickice-gui.png)`
  - Leave placeholder comment for user to add actual image
- Full screenshot set in docs/images/ folder:
  - `docs/images/quickice-gui.png` — main window (hero)
  - `docs/images/phase-diagram.png` — phase diagram panel
  - `docs/images/3d-viewer.png` — 3D molecular viewer (single viewport)
  - `docs/images/dual-viewport.png` — dual viewport comparison
  - `docs/images/export-menu.png` — export menu/dropdown

### OpenCode's Discretion
- Exact wording of quick reference text
- Screenshot capture timing (before/after package build)
- docs/images/ folder structure if different naming preferred

</decisions>

<specifics>
## Specific Ideas

- Current README has good structure — minimal changes to preserve clarity
- Phase diagram click already shows scientific reference (Phase 11) — leverage that instead of duplicating
- Tooltips on input fields already exist (Phase 11) — in-app help complements, doesn't replace

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-update-readme-and-documentation-after-finishing-the-gui*
*Context gathered: 2026-04-02*
