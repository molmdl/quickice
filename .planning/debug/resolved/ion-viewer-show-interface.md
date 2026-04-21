---
status: resolved
trigger: "Improve ion viewer - show interface structure alongside ions with proper representations"
created: "2026-04-21T19:27:00Z"
updated: "2026-04-21T19:40:00Z"
---

## Current Focus
hypothesis: "IonViewerWidget only gets IonStructure, needs InterfaceStructure too for ice+water rendering"
test: "Modified IonViewer to render interface structure, verified syntax"
expecting: "Syntax passes - ready to test in application"
next_action: "N/A - debugging complete"

## Symptoms
expected: "Ion viewer shows both interface structure (ice + water) AND ions"
actual: "Ion viewer shows only ions (spheres), no interface structure displayed"
errors: "None - just missing visual content"
reproduction: "Open Ion tab in viewer, see only yellow/green spheres, no ice/water structure"
started: "Unknown - feature not implemented correctly"

## Eliminated

## Evidence
- timestamp: "2026-04-21T19:30:00Z"
  checked: "InterfaceViewerWidget.set_interface_structure and IonViewerWidget.set_ion_structure"
  found: "InterfaceViewer renders InterfaceStructure (ice+water bonds via interface_to_vtk_molecules). IonViewer renders only IonStructure (ions via render_ion_structure)."
  implication: "IonViewer doesn't receive the InterfaceStructure to render"

## Resolution
root_cause: "IonViewerWidget only received IonStructure (ions as spheres) but was not given InterfaceStructure (ice+water interface) to render. The viewer only showed ions, the interface was displayed only in InterfaceViewer, not the Ion viewer."
fix: "Modified IonViewerWidget to support both set_interface_structure() and set_ion_structure() methods. Updated main_window._on_insert_ions() to call both methods sequentially: first show interface (ice+water bonds), then ions (spheres). Uses same VTK visualization as InterfaceViewerWidget."
verification: "Import tests pass. Syntax valid. Code follows same pattern as InterfaceViewerWidget."
files_changed: ["quickice/gui/ion_viewer.py", "quickice/gui/main_window.py"]
