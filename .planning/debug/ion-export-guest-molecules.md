---
status: investigating
trigger: "Two fixes: Ion tab has no export option + Guest molecules not shown in Interface viewer"
created: 2026-04-21T00:00:00.000Z
updated: 2026-04-21T00:00:00.000Z
---

## Current Focus
hypothesis: "Issue 1: Need IonGROMACSExporter class + menu item + handler. Issue 2: InterfaceViewerWidget needs guest molecule rendering (like HydrateViewerWidget)"
test: "Add IonGROMACSExporter to export.py; Add guest actor to InterfaceViewerWidget"
expecting: "Export menu will work for ions; Interface viewer will show guests"
next_action: "Implement IonGROMACSExporter in export.py"

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
root_cause: 
fix: 
verification: 
files_changed: []