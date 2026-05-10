---
status: analyzed
trigger: "Custom molecule random mode lacks concentration input/calculation functionality. User wants to either input concentration (and see calculated molecule count) or input molecule count (and see calculated concentration). The solute insertion workflow already has this functionality - custom mol random mode should follow the same pattern."
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:01:00Z
---

## Current Focus

hypothesis: Analysis complete - root cause identified
test: N/A - analysis mode
expecting: N/A - analysis mode
next_action: Provide analysis and recommendations to user

## Symptoms

expected: 
- Option 1: User inputs molecule count -> system shows calculated concentration (based on liquid volume)
- Option 2: User inputs concentration -> system shows calculated molecule count (based on liquid volume)
- Similar to solute insertion workflow which already has concentration input

actual: No concentration option, no concentration calculation in custom mol random mode UI

errors: None - feature never implemented

reproduction:
1. Create hydrate or ice structure
2. Create slab interface
3. Add custom molecule in random mode
4. Observe UI - no concentration input field, only molecule count
5. Compare with solute panel - solute has concentration input

timeline: This was discussed as a requirement ("follow how its input in solute panel") but never implemented

priority: High priority for user workflow

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-05-10T00:00:00Z
  checked: SolutePanel implementation (quickice/gui/solute_panel.py)
  found: Has concentration input field (lines 159-203) with real-time molecule count preview
  implication: Working reference implementation exists

- timestamp: 2026-05-10T00:00:00Z
  checked: SoluteInserter calculation logic (quickice/structure_generation/solute_inserter.py)
  found: `calculate_molecule_count()` method (lines 62-89) using formula N = C_M × V_L × N_A
  implication: Reusable calculation logic exists

- timestamp: 2026-05-10T00:00:00Z
  checked: CustomMoleculePanel random mode controls (quickice/gui/custom_molecule_panel.py)
  found: Only has molecule_count_spin (lines 318-366), no concentration input
  implication: Concentration input UI is completely missing

- timestamp: 2026-05-10T00:00:00Z
  checked: CustomMoleculeInserter (quickice/structure_generation/custom_molecule_inserter.py)
  found: No concentration-based calculation methods
  implication: Calculation logic needs to be added

- timestamp: 2026-05-10T00:00:00Z
  checked: Liquid volume accessibility in CustomMoleculePanel
  found: set_interface_structure() method receives interface structure with water atoms (line 859)
  implication: Liquid volume calculation is already available

## Resolution

root_cause: CustomMoleculePanel random mode UI only provides molecule count input. It lacks the concentration input field and calculation logic that exists in SolutePanel. Additionally, neither SolutePanel nor IonPanel implements the requested two-way conversion feature (input count → show concentration OR input concentration → show count).

fix: Add concentration input option to CustomMoleculePanel random mode with two-way conversion:
1. Add mode selector (radio buttons or dropdown) for "By Count" vs "By Concentration"
2. Show/hide appropriate input field based on mode
3. Implement calculate_molecule_count() method (reuse from SoluteInserter)
4. Implement calculate_concentration() method (reverse calculation)
5. Add real-time preview of the calculated value
6. Follow SolutePanel UI pattern for consistency

verification: (empty until verified)
files_changed: []
