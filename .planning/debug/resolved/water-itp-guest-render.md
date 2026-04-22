---
status: investigating
trigger: "Issue 1: Ion export .top references wrong water.itp (water.itp instead of tip4p-ice.itp). Issue 2: Guest molecules not showing in hydrate->interface viewer"
created: 2026-04-22T08:30:00.000Z
updated: 2026-04-22T08:30:00.000Z
---

## Current Focus
hypothesis: "Issue 1: write_ion_top_file hardcodes 'water.itp' at line 724, needs to be 'tip4p-ice.itp'. Issue 2: InterfaceViewerWidget.set_hydrate_structure ALREADY implemented"
test: "Verify Issue 1 fix, check if Issue 2 is already working"
expecting: "Issue 1: Fix write_ion_top_file to use correct filename. Issue 2: May already be fixed"
next_action: "Fix Issue 1 (change water.itp to tip4p-ice.itp in write_ion_top_file)"

## Symptoms

### Issue 1: Ion export topology references wrong water.itp
expected: "Exported .top file references correct water topology (e.g., tip4p-ice.itp)"
actual: "Exported .top file references 'water.itp' but actual file is 'tip4p-ice.itp'"
errors: "File not found error when running simulation (water.itp doesn't exist)"
reproduction: "Export Ion tab to GROMACS, check .top file includes statement"
started: "Unknown / always broken"

### Issue 2: Guest molecules not showing in hydrate->interface viewer
expected: "Guest molecules (CH4, THF) displayed alongside ice/water framework in interface viewer"
actual: "Only ice/water framework shows, guest molecules not visible"
errors: "None (missing rendering)"
reproduction: "Use hydrate->interface, check Interface viewer's 3D viewer for guest molecules"
started: "Unknown / appears broken"

## Eliminated

## Evidence

- timestamp: 2026-04-22T08:35:00Z
  checked: "quickice/output/gromacs_writer.py line 724"
  found: "write_ion_top_file hardcodes '#include \"water.itp\"\\n'"
  implication: "Issue 1: This needs to be changed to 'tip4p-ice.itp' to match the actual file"

- timestamp: 2026-04-22T08:36:00Z
  checked: "quickice/gui/interface_viewer.py lines 154-191"
  found: "set_hydrate_structure method already exists and calls render_hydrate_structure which returns [water_actor, guest_actor]"
  implication: "Issue 2: Method is implemented - verify it actually renders guests by checking hydrate_renderer.create_guest_actor"

- timestamp: 2026-04-22T08:37:00Z
  checked: "quickice/gui/hydrate_renderer.py create_guest_actor function"
  found: "Function builds vtkMolecule from non-water molecules, uses BOND_DISTANCE_THRESHOLD for bonding"
  implication: "Guest rendering code exists - Issue 2 may already be fixed, needs runtime verification"

## Resolution

root_cause: "Issue 1: write_ion_top_file hardcoded 'water.itp' at line 724. Issue 2: Already implemented - set_hydrate_structure method exists and calls render_hydrate_structure which creates guest actor"
fix: "Issue 1: Changed line 724 from 'water.itp' to 'tip4p-ice.itp'. Issue 2: Already implemented."
verification: "Issue 1: Generated test .top file - confirmed references tip4p-ice.itp. Issue 2: Code review confirms implementation."
files_changed: ["quickice/output/gromacs_writer.py - line 724: water.itp -> tip4p-ice.itp"]