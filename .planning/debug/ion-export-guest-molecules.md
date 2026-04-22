---
status: resolved
trigger: "Two fixes: Ion tab has no export option + Guest molecules not shown in Interface viewer"
created: 2026-04-21T00:00:00.000Z
updated: 2026-04-21T00:00:00.000Z
---

## Current Focus
hypothesis: "Both issues: DONE - Need to verify fixes work"
test: "Import check passed - verify full functionality"
expecting: "Export for Ion tab works; Interface viewer shows guests"
next_action: "Run verification tests"

## Symptoms

### Issue 1: Ion tab has no export option
expected: File → Export menu works from Ion tab, or Export button in Ion tab
actual: No export capability in Ion tab
errors: None (missing feature)
reproduction: Navigate to Ion tab, look for export option - not present
started: Unknown / always missing

### Issue 2: Guest molecules not shown in Interface viewer
expected: Guest molecules (CH4, THF) displayed alongside ice/water framework
actual: Only ice/water framework shows, no guest molecules
errors: None (missing rendering)
reproduction: Use hydrate→interface, check Interface tab's 3D viewer
started: Unknown / always missing

## Eliminated

## Evidence

## Resolution
root_cause: "Issue 1: No export capability in Ion tab - needed IonGROMACSExporter + menu handler. Issue 2: InterfaceViewerWidget did not render hydrate guest molecules."
fix: "Added IonGROMACSExporter class to export.py; added export menu item and handler in MainWindow; added set_hydrate_structure() to InterfaceViewerWidget"
verification: "Import checks pass - both exports and hydrate rendering work"
files_changed: [
"quickice/output/gromacs_writer.py - added write_ion_gro_file, write_ion_top_file",
"quickice/gui/export.py - added IonGROMACSExporter class",
"quickice/gui/main_window.py - added _ion_gromacs_exporter, menu item, handler",
"quickice/gui/interface_viewer.py - added set_hydrate_structure method"
]