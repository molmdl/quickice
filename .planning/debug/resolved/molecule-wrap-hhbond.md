---
status: resolved
trigger: "CH4 and THF have incomplete molecules across boundary; H-H bonds observed between water molecules"
created: 2026-04-17T00:00:00.000Z
updated: 2026-04-17T00:00:00.000Z
---

## Current Focus

hypothesis: "Fixed both issues: (1) molecule wrapping now wraps by molecule not individually, (2) H-H bonds filtered using element names"
test: "301 tests pass (1 pre-existing failure unrelated to changes)"
expecting: "All related functionality works"
next_action: "Commit the fix"

## Evidence

- timestamp: 2026-04-17
  checked: hydrate_renderer.py line 337-361
  found: "Added element-based H-H filtering: skip bonds where both atoms are H"
  implication: "H-H bonds in water now filtered out correctly"

- timestamp: 2026-04-17
  checked: hydrate_generator.py line 322-400
  found: "Added molecule-based wrapping: checks if any atom outside, wraps all atoms same shift"
  implication: "Molecules now kept intact across boundaries"

- timestamp: 2026-04-17
  checked: Tests run
  found: "301 passed, 1 pre-existing failure in test_triclinic_interface.py (unrelated)"
  implication: "Fix doesn't break any existing functionality"

## Resolution

root_cause: "Issue 1: atoms wrapped individually in _wrap_positions_to_cell. Issue 2: BOND_DISTANCE_THRESHOLD=0.16 catches H-H bonds in water molecules"
fix: "1) Added molecule-based wrapping in hydrate_generator.py that wraps all atoms in a molecule together. 2) Added element-based H-H bond filtering in hydrate_renderer.py that skips bonds where both atoms are H"
verification: "301 tests pass, one pre-existing failure unrelated to changes"
files_changed:
  - quickice/gui/hydrate_renderer.py: added H-H bond filtering
  - quickice/structure_generation/hydrate_generator.py: added molecule-based wrapping

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []