---
status: resolved
trigger: "ion insertion into hydrate→interface places ions in hydrate layer"
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
---

## Root Cause FOUND
**Root Cause:** When hydrate is converted to interface, the `_build_molecule_index_from_structure()` method assumed ice always has 3 atoms per molecule. But hydrate framework uses TIP4P water with 4 atoms per molecule (OW, HW1, HW2, MW). This caused the molecule_index to have incorrect start_idx values:
- For 10 hydrate molecules: marked at indices 0-29 instead of 0-39
- First liquid water: marked at 30 instead of 40
- **Ions were placed at wrong positions (some in the hydrate framework)**

## Fix Applied
Modified `ion_inserter.py` lines 85-102:
- Added detection of actual atoms per molecule from atom_names pattern
- If first atom is "OW" -> hydrate (4 atoms)
- Otherwise -> GenIce ice (3 atoms)

## Verification
1. Hydrate→interface: molecule_index now has correct start_idx (water starts at 40)
2. Regular ice→interface: still works (3 atoms/mol for GenIce)
3. Full ion insertion: all ions go into liquid water (not hydrate framework)
4. 307/308 tests pass (1 pre-existing failure unrelated to fix)

## Files Changed
- quickice/structure_generation/ion_inserter.py: _build_molecule_index_from_structure method