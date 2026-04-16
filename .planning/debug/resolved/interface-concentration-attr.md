---
status: resolved
trigger: "Interface generation crash - IonConfig missing concentration attribute"
created: 2026-04-16T00:00:00
updated: 2026-04-16T00:00:00
---

## Current Focus
hypothesis: "IonConfig class is missing the 'concentration' attribute that ion_panel._update_ion_count() expects"
test: "Read IonConfig class definition to verify what attributes it has"
expecting: "If IonConfig lacks concentration, need to add it or fix the access pattern"
next_action: "Read ion_panel.py to see how _update_ion_count uses config.concentration"

## Symptoms
expected: After generating interface in Tab 3, 3D viewer should show structure
actual: Terminal stderr shows AttributeError, 3D viewer shows placeholder (no structure)
errors: "AttributeError: 'IonConfig' object has no attribute 'concentration'" at ion_panel.py:128 in _update_ion_count
reproduction: Tab 1 generate ice Ih → Tab 3 Interface → Generate default → Crash before viewer updates
started: Worked in tag v3.5, broke before phase 28.1

## Eliminated

## Evidence
- timestamp: 2026-04-16T00:01
  checked: "IonConfig class definition in types.py"
  found: "IonConfig only has 'concentration_molar' attribute (line 320), not 'concentration'"
  implication: "Code accessing config.concentration will raise AttributeError"
- timestamp: 2026-04-16T00:02
  checked: "ion_panel.py _update_ion_count method"
  found: "Line 128 accesses config.concentration which doesn't exist - should be config.concentration_molar"
  implication: "This is the bug causing the crash"
- timestamp: 2026-04-16T00:03
  checked: "IonInserter.calculate_ion_pairs signature"
  found: "Method takes concentration_molar parameter (line 62), confirming the correct attribute name"
  implication: "Fix is to change config.concentration to config.concentration_molar"

## Resolution
root_cause: "ion_panel.py line 128 accesses config.concentration but IonConfig only has concentration_molar attribute"
fix: "Changed config.concentration to config.concentration_molar on line 128"
verification: "Verified: test_structure_generation.py (57 tests), test_integration_v35.py (11 tests) all pass. Direct Python simulation confirms IonConfig.concentration_molar works correctly."
files_changed: ["quickice/gui/ion_panel.py"]
fix:
verification:
files_changed: []
