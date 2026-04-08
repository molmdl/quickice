# Phase 16: Tab Infrastructure - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users switch between Ice Generation tab (existing) and Interface Construction tab (new), with selected ice candidate passed from Tab 1 to Tab 2. This phase creates the two-tab workflow foundation for v3.0 interface generation.

</domain>

<decisions>
## Implementation Decisions

### Tab Layout & Style
- Tabs positioned at top of main window (horizontal layout)
- Text-only labels, no icons
- Use default PySide6 QTabWidget styling
- Tab labels: "Ice Generation" and "Interface Construction"

### Selection State & Transfer
- Tab 2 contains a candidate dropdown for clarity (not just implicit selection)
- Dropdown allows explicit selection of ice candidate within Tab 2
- Generation in Tab 2 requires a candidate to be selected in the dropdown
- Empty state handling delegated to OpenCode

### Tab State Persistence
- Preserve all Tab 1 state when switching to Tab 2 (candidates, selection, UI)
- Preserve all Tab 2 state when switching to Tab 1 (interface structure, dropdown selection, UI)
- Tab 2 dropdown shows same candidates as Tab 1 list
- When Tab 1 regenerates candidates, Tab 2 keeps old candidates until user action
- Manual "Refresh candidates" button in Tab 2 to sync with Tab 1's current candidate list
- Missing candidate handling delegated to OpenCode

### Empty Tab 2 Handling
- Tab 1 (Ice Generation) is the default tab on app startup
- Empty dropdown state handling delegated to OpenCode
- Generate button behavior without selection delegated to OpenCode

### OpenCode's Discretion
- Empty state messaging in Tab 2 content area
- Dropdown placeholder text when no candidates exist
- Generate button disabled/enabled state with tooltip
- What happens when selected candidate is removed during regeneration

</decisions>

<specifics>
## Specific Ideas

- Dropdown in Tab 2 for explicit candidate selection provides clarity over implicit transfer
- Manual refresh button gives user control over when Tab 2 dropdown syncs with Tab 1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-tab-infrastructure*
*Context gathered: 2026-04-08*
