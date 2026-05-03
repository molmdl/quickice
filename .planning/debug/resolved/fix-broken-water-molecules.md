---
status: resolved
trigger: "Fix Broken Water Molecules in Liquid Region"
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:02Z
---

## Current Focus

hypothesis: Atom-level wrapping in load_water_template() breaks molecules spanning PBC boundaries
test: Remove lines 250-261 from water_filler.py and regenerate structure
expecting: Water molecules in liquid region will have correct geometry
next_action: Remove the incorrect atom-level wrapping code

## Symptoms

expected: Water molecules in liquid region should have correct molecular geometry (O-H bonds ~0.1 nm)
actual: Water molecules in liquid region are broken across PBC - atoms of same molecule appear on opposite sides of the box, creating fake bonds ~1.7 nm long
errors: None reported
reproduction: Generate ice interface structure and check liquid water region for broken molecules
started: Introduced in current version (lines 250-261 added to load_water_template)

## Eliminated

(None yet)

## Evidence

- timestamp: Initial
  checked: Template file tip4p.gro
  found: 32 molecules (out of 216) have atoms outside [0, box)
  implication: Template has molecules spanning PBC boundaries
  
- timestamp: Initial
  checked: v4.0 code (working version)
  found: Did NOT have atom-level wrapping in load_water_template()
  implication: Atom-level wrapping is the regression
  
- timestamp: Initial
  checked: v4.0 code
  found: Used molecule-level filtering in tile_structure() to remove incomplete molecules
  implication: Correct approach is molecule-level filtering, not atom wrapping

## Resolution

root_cause: Lines 250-261 added atom-level wrapping (positions = positions % box_dims) to load_water_template(), which breaks molecules spanning PBC boundaries
fix: Removed atom-level wrapping from load_water_template() function. The tile_structure() function correctly handles molecules spanning PBC boundaries at the molecule level using filter_molecules=True parameter.
verification: 
  - Water template loading: No molecules broken (atoms within molecules stay close together)
  - Tiled structure test: All 3916 molecules have correct geometry (span < 0.5 nm)
  - O-H bond distances: 0.095-0.097 nm (valid range)
  - Ice interface test: All 1018 water molecules in liquid region have correct geometry
  - All O-H bonds in ice interface: 0.094-0.096 nm (valid range)
  - All interface tests passed (22/22)
files_changed: [quickice/structure_generation/water_filler.py]
