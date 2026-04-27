---
status: resolved
trigger: "hydrate -> interface -> ion workflow, no guest shown in ion tab's 3D viewer"
created: 2026-04-27T00:00:00.000Z
updated: 2026-04-27T00:00:00.000Z
goal: find_and_fix
---

## Current Focus
hypothesis: "ion_viewer.py set_interface_structure() extracts guest_mol but never creates an actor or adds it to renderer"
test: "Compare set_interface_structure() in ion_viewer.py vs interface_viewer.py"
expecting: "Find missing guest rendering code in ion_viewer.py"
next_action: "Apply fix: add guest rendering similar to interface_viewer.py"

## Symptoms
expected: Guest molecule (CH4 from default hydrate generation) should appear in ion tab's 3D viewer
actual: No guest shown in ion tab's 3D viewer
errors: None shown
timeline: Never worked - but user mentions "interface" tab had same issue and was just fixed
reproduction: 
  1. Generate hydrate (uses CH4 as default guest)
  2. Generate interface from hydrate
  3. Insert ion (select an ion)
  4. Check ion tab's 3D viewer - guest molecule is not visible

## Eliminated

## Evidence
- timestamp: 2026-04-27T00:00:00.000Z
  checked: "ion_viewer.py set_interface_structure() method"
  found: "Line 267: Gets guest_mol correctly, but lines 275-276 only create actors for ice, water, unit cell"
  implication: "guest_mol is extracted but never rendered!"

- timestamp: 2026-04-27T00:00:00.000Z
  checked: "interface_viewer.py set_interface_structure() method"
  found: "Lines 146-165: Creates guest actor using _create_guest_ball_and_stick_actor() and adds to renderer"
  implication: "This is the fix that was applied to interface tab - same code needed in ion_viewer.py"

- timestamp: 2026-04-27T00:00:00.000Z
  checked: "InterfaceStructure type for guest atom count"
  found: "structure.guest_atom_count attribute available"
  implication: "Can check if guest atoms exist before rendering"

## Resolution
root_cause: "ion_viewer.py set_interface_structure() extracts guest_mol from interface_to_vtk_molecules() but never creates an actor or adds it to renderer - the guest rendering code was simply missing"
fix: "Added guest molecule rendering to ion_viewer.py with:
  - Added GUEST_COLOR and ANGSTROM_TO_NM constants
  - Added _guest_actor state variable
  - Added _create_guest_ball_and_stick_actor() method (same as interface_viewer.py)
  - Added guest actor creation in set_interface_structure() when guest_mol exists and guest_atom_count > 0
  - Added guest actor to renderer
  - Updated _clear_interface_actors() to also remove guest actor"
verification: "Syntax verified - Python compiles without errors"
files_changed:
  - "quickice/gui/ion_viewer.py": Added guest molecule rendering (same fix as applied to interface_viewer.py)