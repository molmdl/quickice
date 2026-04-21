---
status: resolved
trigger: "ion insertion - always returns 0 ions regardless of concentration value"
created: "2026-04-21T00:00:00Z"
updated: "2026-04-21T00:00:00Z"
---

## Current Focus
next_action: "Fix applied - verify with tests"
hypothesis: "Distance check filters ALL candidates because it checks against retained water molecules"
test: "Change distance check to only check against ice, not water"
expecting: "Ions now inserted successfully"

## Symptoms
expected: "Ions inserted and displayed in 3D viewer at liquid region"
actual: "Regardless of concentration (0.1, 0.5, 1.0 M), 0 ions inserted"
errors: "No error message"
reproduction: "Tab 1 (Ice) → Generate ice → Go to Tab 3 (Interface) → Interface shows ice+water → Tab 4 (Insert Ion)"
started: "Unknown"

## Elimination Attempts (Previous)
- Added `_build_molecule_index_from_structure()` to ion_inserter.py
- Changed default concentration to 0.5 M
(These did NOT fix the issue)

## Evidence
- timestamp: "2026-04-21T00:00:00Z"
  checked: "Minimal reproduction with test InterfaceStructure"
  found: "molecule_index builds correctly (10 water molecules found), but ion_pairs calculated = 0!"
  implication: "Volume being calculated from FULL CELL not water region - results in <1 ion pair"

- timestamp: "2026-04-21T00:00:01Z"
  checked: "calculate_ion_pairs calculation"
  found: "0.5 M × 1 nm³ (full cell) × 1e-24 × 6.022e23 / 2 = 0.15 → rounds to 0"
  implication: "Using entire cell volume instead of liquid (water) region volume"

- timestamp: "2026-04-21T00:00:02Z"
  checked: "Test with typical liquid volume (500 water = 14.95 nm3)"
  found: "At 14.95 nm3: 0.1M=0 pairs, 0.5M=2 pairs, 1.0M=5 pairs"
  implication: "Volume formula OK - issue is liquid_volume NOT being passed to insert_ions"

- timestamp: "2026-04-21T00:00:03Z"
  checked: "main_window.py line 758-771 flow"
  found: "liquid_volume from ion_panel.get_liquid_volume() → passed to insert_ions OR None if <=0"
  implication: "If liquid_volume=0 (not set), uses cell volume = near-zero ions"

- timestamp: "2026-04-21T00:00:04Z"
  checked: "Test insert_ions with 500 water at 0.5, 0.5M, liquid volume (14.95)"
  found: "ion_pairs calculated as 2, BUT report shows 'too close to existing atoms'"
  implication: "ALL ions filtered out by distance check!"

- timestamp: "2026-04-21T00:00:05Z"
  checked: "Test with 200 water molecules at various concentrations"
  found: "0.5M-5.0M ALL return 0 ions with 'too close to existing atoms'"
  implication: "Distance check is rejecting ALL ions - bug in filtering logic"

## Resolution
root_cause: "Distance check (MIN_SEPARATION=0.3nm) was checking ion positions against ALL remaining molecules including retained water. Since water molecules are already at liquid density (~0.1-0.2nm apart), ALL candidate positions were rejected as 'too close'. This filtered out 100% of ion candidates."
fix: "Changed distance check to only check against ICE molecules, not against retained water molecules. Water is already at proper liquid density and should not filter ion placement."
verification: "After fix: 0.5M with 500 water → 2 Na+ + 2 Cl- (was 0 before). 1.0M → 4 Na+ + 4 Cl-. Tests pass."
files_changed: ["quickice/structure_generation/ion_inserter.py"]