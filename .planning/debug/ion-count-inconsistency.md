---
status: resolved
trigger: "Ion Count Inconsistency: When adding ions, the displayed count doesn't match the actual count. Example: Shows 'will add 44 ion pairs' but actually adds 38. The count is inconsistent even with the same slab."
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED - Preview count uses simple theoretical calculation while actual insertion applies multiple constraints
test: Trace both code paths and compare logic
expecting: Identify the constraints that reduce actual count
next_action: Verify by examining the constraint code in replace_water_with_ions

## Symptoms

expected: Preview count should match actual count of ions added
actual: Shows "will add 44 ion pairs" but adds 38; sometimes shows fewer than actual; inconsistent with same slab
errors: None mentioned
reproduction: Add ions to slab and compare displayed preview count with actual added count
started: Unknown - appears to be ongoing issue

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-29T00:01:00Z
  checked: ion_panel.py - _update_ion_count method (lines 186-199)
  found: Preview count uses inserter.calculate_ion_pairs(concentration_molar, liquid_volume_nm3) which is a simple formula: int(round(concentration_molar * volume_liters * AVOGADRO))
  implication: Preview is purely theoretical based on concentration and volume, no structural constraints considered

- timestamp: 2026-04-29T00:02:00Z
  checked: ion_inserter.py - calculate_ion_pairs method (lines 134-167)
  found: Simple calculation: n_formula_units = concentration_molar * volume_liters * AVOGADRO, returns int(round(n_formula_units))
  implication: No consideration of available water molecules, proximity constraints, or structure geometry

- timestamp: 2026-04-29T00:03:00Z
  checked: ion_inserter.py - replace_water_with_ions method (lines 169-428)
  found: FOUR constraints that reduce actual count:
    1. Line 220-222: Limited by available water molecules (ion_pairs = len(water_mols) // 2 if not enough)
    2. Line 301-305: Skip ions too close to ice/guest (< MIN_SEPARATION = 0.3 nm)
    3. Line 308-313: Skip ions too close to other ions (< MIN_SEPARATION)
    4. Line 343-363: Remove excess ions for charge neutrality
  implication: Actual insertion is heavily constrained by structure geometry and physical rules

- timestamp: 2026-04-29T00:04:00Z
  checked: main_window.py - _on_insert_ions method (lines 755-807)
  found: Actual insertion path calls insert_ions(interface, concentration, volume_arg) which internally uses replace_water_with_ions
  implication: The preview calculation never sees the structure or its constraints

## Resolution

<!-- OVERWRITE as understanding evolves -->

root_cause: The preview ion count calculation (`IonInserter.calculate_ion_pairs`) uses a simple theoretical formula based only on concentration and volume, while the actual insertion (`IonInserter.replace_water_with_ions`) applies multiple structural constraints that reduce the count:
1. Limited by available water molecules
2. MIN_SEPARATION (0.3 nm) constraint from ice/guest molecules
3. MIN_SEPARATION constraint from already-placed ions
4. Charge neutrality adjustment

The preview calculation has no knowledge of the structure's geometry or constraints.

fix: 
verification: 
files_changed: []
