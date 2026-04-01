# Phase 11: Save/Export + Information - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can export generated content to files (PDB, images) and access scientific information about ice phases through the existing log panel. No new windows — leverage existing UI components.

</domain>

<decisions>
## Implementation Decisions

### Save workflow UX
- Default PDB filename: `{phase}_{T}K_{P}bar_c{candidate_num}.pdb` (e.g., `ice_Ih_250K_1000bar_c1.pdb`)
- Save dialog location: OpenCode's discretion
- Overwrite behavior: Prompt before overwriting (safe, prevents accidental data loss)
- Success notification: OpenCode's discretion

### Export format controls
- Image quality/resolution options: OpenCode's discretion
- PDB export: Save selected/viewed candidate only (not batch)
- Phase diagram image format: OpenCode's discretion (PNG and/or SVG)
- 3D viewport screenshot format: OpenCode's discretion

### Info panel (log panel)
- Use existing log panel — no new info window needed
- Phase info synced to diagram selection (shows info about last-clicked region)
- Content depth: OpenCode's discretion (density, structure type, citation)
- Citations: Include copy button for easy pasting

### Help tooltips
- Context tooltips only — no in-app manual (INFO-04 deferred to Phase 13)
- Each UI element has its own `?` icon
- Tooltip triggered by hovering over `?` icon
- Tooltip content detail: OpenCode's discretion (brief description)

### OpenCode's Discretion
- Default save dialog location
- Success notification style (toast/status bar/dialog)
- Image quality/resolution options for exports
- Diagram format (PNG only, PNG+SVG, etc.)
- Viewport screenshot format
- Info panel content depth
- Tooltip content detail

</decisions>

<specifics>
## Specific Ideas

- Log panel already exists — repurpose it for phase info display
- Diagram hover already shows T,P — no additional hover info needed
- Phase info synced to what user clicked on diagram

</specifics>

<deferred>
## Deferred Ideas

- INFO-04 (in-app markdown manual) — Phase 13 (documentation update phase)
- INFO-02 (diagram hover beyond T,P) — existing T,P display sufficient

</deferred>

---
*Phase: 11-save-export-information*
*Context gathered: 2026-04-02*
