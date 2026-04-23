---
status: resolved
trigger: "Debug hang when generating hydrate→interface - both slab and piece modes hang"
created: "2026-04-23T12:00:00.000Z"
updated: "2026-04-23T17:00:00.000Z"
---

## Current Focus
Fixed: hydrate→interface now works correctly in both slab and piece modes

## Symptoms
expected: "Interface generates and displays in viewer when using hydrate source with guest molecules"
actual: "Application hangs - no response, no error, no viewer update after clicking Generate in slab/piece mode"
errors: []
reproduction: "1. User goes to Tab 2 (Hydrate), generates a hydrate with guests 2. User clicks Use in Interface → to go to Tab 3 3. User selects Hydrate Structure from dropdown 4. User selects slab mode or piece mode 5. User clicks Generate 6. Application hangs"
started: "Unknown - appears to be related to recent guest molecule changes"

## Root Cause
When hydrate.to_candidate() combines water framework + guest molecules (CH4, THF) into a single positions array, the detect_atoms_per_molecule() function returns 4 (for TIP4P water framework). However:
1. tile_structure() then treats every 4 atoms as one molecule
2. But CH4 has 5 atoms, THF has 12 atoms
3. This corrupts the molecular structure in tile_structure
4. Downstream operations work on corrupted data, causing infinite loop / hang

## Fix Applied
1. **modes/slab.py**:
   - Added hydrate detection via `is_hydrate = candidate.metadata.get("original_hydrate", False)`
   - Extract water framework positions only (using molecule_index) for tiling
   - Use atoms_per_mol=4 for TIP4P water framework
   - Add guests to output AFTER tiling (so viewer can find them)
   - Fixed overlap detection to only check water framework O atoms

2. **modes/piece.py**:
   - Same fix as slab.py
   - Extract water framework only for tiling
   - Add guests to output for viewer

## Verification
- All 64 tests pass
- Manual test: hydrate→piece mode generates successfully with guests
- Manual test: hydrate→slab mode generates successfully with guests
- Carbon atoms present in output for viewer detection

## Files Changed
- quickice/structure_generation/modes/slab.py
- quickice/structure_generation/modes/piece.py