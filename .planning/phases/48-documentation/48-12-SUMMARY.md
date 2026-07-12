---
phase: 48-documentation
plan: 12
subsystem: docs
tags: [pyside6, helpicon, tooltips, hydrate-panel, gui, mixed-cage-occupancy]

# Dependency graph
requires:
  - phase: 42-06
    provides: Per-cage guest QComboBox + occupancy QDoubleSpinBox rows in HydratePanel._rebuild_cage_rows (one row per cage_type_map key)
  - phase: 44-02
    provides: "Custom: {residue}" combo option appended per cage when a custom guest is loaded
provides:
  - HelpIcon tooltips on per-cage guest QComboBox (built-in CH4/THF + custom guest + mixed cage occupancy)
  - HelpIcon tooltips on per-cage occupancy QDoubleSpinBox (0-100% range, default 100%, independent per cage type)
affects: [48-02 in-app help restructure, future GUI tooltip sweeps]

# Tech tracking
tech-stack:
  added: []  # HelpIcon already exists in quickice/gui/view.py (no new deps)
  patterns:
    - "widget-then-HelpIcon convention extended to per-cage rows (matches lines 193/223/562: widget, HelpIcon, addStretch)"

key-files:
  created: []
  modified:
    - quickice/gui/hydrate_panel.py  # +16 lines: 2 HelpIcon widgets in _rebuild_cage_rows

key-decisions:
  - "HelpIcon placed immediately AFTER each widget (combo then spin) matching the existing hydrate_panel convention at lines 193/223/562 — NOT before the widget"
  - "row.addStretch() between combo and spin preserved (critical constraint); HelpIcons sit adjacent to their described widgets"
  - "Reused existing HelpIcon class from view.py (line 26 import already present) — no new tooltip mechanism created"

patterns-established:
  - "Per-cage-row tooltip layout: [combo][?] [stretch] [spin][?] — HelpIcon adjacent to each widget, addStretch preserves combo/spin separation"

# Metrics
duration: 1 min
completed: 2026-07-12
---

# Phase 48 Plan 12: Hydrate Panel Per-Cage Tooltips Summary

**HelpIcon tooltips on per-cage guest QComboBox + occupancy QDoubleSpinBox in HydratePanel._rebuild_cage_rows — closes the last tooltip gap in the hydrate panel for v4.7 mixed cage occupancy**

## Performance

- **Duration:** 1 min (92 sec)
- **Started:** 2026-07-12T12:08:05Z
- **Completed:** 2026-07-12T12:09:37Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added HelpIcon next to each per-cage guest QComboBox explaining guest choice (built-in CH4/THF or uploaded custom guest; built-in CH4/THF only on CLI for v4.7; different cage types can have different guests = mixed cage occupancy)
- Added HelpIcon next to each per-cage occupancy QDoubleSpinBox explaining occupancy (0-100%, default 100% fully occupied, lower values create partial occupancy, each cage type has independent occupancy e.g. 60% CH4 in small + 100% THF in large)
- Followed the existing widget-then-HelpIcon convention already used 4x elsewhere in hydrate_panel.py (lines 193 lattice, 223 depol, 103 generate button, 562 supercell) — no new tooltip mechanism introduced
- Preserved the critical `row.addStretch()` between combo and spin (HelpIcons sit adjacent to their described widgets, not in the stretch gap)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add HelpIcon tooltips to per-cage guest combo + occupancy spin** - `be8d39f` (docs)

**Plan metadata:** (this commit — docs(48-12): complete hydrate panel per-cage tooltips plan)

## Files Created/Modified
- `quickice/gui/hydrate_panel.py` - Added 2 HelpIcon widgets in `_rebuild_cage_rows` (one after the guest QComboBox, one after the occupancy QDoubleSpinBox) + 2 explanatory comments; HelpIcon import at line 26 was already present so no import change needed

## Decisions Made
- **HelpIcon placement (after widget, not before):** Placed each HelpIcon immediately AFTER its described widget (combo → HelpIcon → addStretch → spin → HelpIcon) matching the established convention at lines 193/223/562 in the same file. The plan's Step 4 said to "follow the existing pattern used in other parts of hydrate_panel.py (check how HelpIcon is placed at lines 193/223 and match that style)" — those placements are all widget-then-HelpIcon, so this is the only placement consistent with both the plan's instruction and the critical constraint to preserve `row.addStretch()` between combo and spin.
- **Reused existing HelpIcon import:** `from quickice.gui.view import HelpIcon` was already present at line 26 (added during an earlier tooltip phase) — no import change needed. The plan's Step 1 directed to check for an existing import and only add if missing; it was already there.
- **Tooltip text content:** Used the plan's suggested wording verbatim (CH4/THF built-in + custom guest + mixed cage occupancy for the combo; 0-100% default 100% + independent per cage type for the spin), which aligns with the v4.7 mixed-occupancy feature documentation and the DOCS-02 in-app help requirement.

## Deviations from Plan

None - plan executed exactly as written.

The plan's Step 1 anticipated the import might be missing ("If `HelpIcon` is not imported, add it") — it was already present, so that conditional was a no-op (not a deviation, just a satisfied precondition). The plan's Step 4 placement guidance ("follow the existing pattern at lines 193/223") resolved unambiguously to widget-then-HelpIcon since all three referenced sites (193/223/562) place HelpIcon after the widget. The plan's referenced line numbers (487, 515) had shifted to 512/529 in the current file; located via reading `_rebuild_cage_rows` directly as the project_context instructed ("Verify the actual line numbers by reading the file — they may have shifted").

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hydrate panel now has comprehensive tooltips on ALL interactive widgets (lattice combo, depol combo, supercell, generate button, AND per-cage guest combo + occupancy spin) — the per-cage widgets were the last tooltip gap identified in DOCS-02 (in-app).
- Independent of the help_dialog restructure (plan 48-02 / 48-09/10/11) which touches `quickice/gui/help_dialog.py` (a different file); this plan only modified `hydrate_panel.py` so there is no merge conflict with the parallel help_dialog work.
- Phase 48 (Documentation) remains IN PROGRESS — 48-01, 48-03, 48-06, 48-08, 48-12, 48-13 done; remaining plans per the RESEARCH 14-plan split continue to be executed (some by parallel agents).

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
