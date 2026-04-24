---
status: investigating
created: '2026-04-24'
trigger: Clarify correct ion count calculation for concentration
goal: find_and_fix
---

## Current Focus
Investigating ion concentration calculation in ion_inserter.py

hypothesis: Need to read the ion insertion code to understand the concentration formula
test: Read ion_inserter.py and trace through the ion count calculation
expecting: Find where concentration is calculated and understand if a factor of 2 is needed
next_action: Examining current formula in detail

## Resolution


- timestamp: '2026-04-24'
  checked: Root cause analysis
  found: |
    BUG FOUND: Division by 2 is incorrect
    
    Current formula:
    n_ions = concentration_molar * volume * AVOGADRO  # = mol of formula units
    return int(round(n_ions / 2))  # WRONG - divides out what we need!
    
    For 1 M NaCl with 1 L:
    - Expected: 1 mol NaCl formula units × 2 ions per unit = 1.204e24 ions
    - Current: Only produces 6.022e23 ions (HALF!)
    
    The division by 2 was likely a misunderstanding:
    - "ion_pairs" = pairs of Na+ and Cl- per formula unit
    - But users want TOTAL ion count based on molarity of the SALT
  implication: Fix is to remove the unnecessary division by 2

## Root Cause
The code incorrectly divides by 2 in the `calculate_ion_pairs` method.

## Fix Applied
**File:** `quickice/structure_generation/ion_inserter.py`
**Change:** Removed the erroneous division by 2
- Before: `return int(round(n_ions / 2))`
- After: `return int(round(n_formula_units))`

**Note:** The function name `calculate_ion_pairs` correctly describes what it returns (NaCl formula units, each becomes a Na+/Cl- pair when inserted). The bug was in the implementation dividing by 2 unnecessarily.

## Verification
- Tested with multiple concentration/volume combinations
- Formula now correctly produces: concentration (M) × volume (L) × NA = formula units
- Each formula unit becomes 1 Na+ + 1 Cl- pair during insertion
- Result matches expected physical behavior: 1 M NaCl → 2 mol ions per liter

## Files Changed
- quickice/structure_generation/ion_inserter.py (lines 117-145)