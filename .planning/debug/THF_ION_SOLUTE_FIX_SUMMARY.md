# THF-Ion-Solute Issues Fix Summary

## Issue Report

Three critical issues were reported after previous fixes:

1. **THF solute bonds STILL wrong in liquid phase** (hydrate THF is correct, solute THF is wrong)
2. **Water replacement message needs revision** (not clear and concise)
3. **Ion panel with "Solute" source STILL not showing solutes** in viewer

## Root Causes Identified

### Issue 1: THF Solute Bonds

**Location:** `quickice/gui/solute_renderer.py` lines 146-160

**Problem:** 
- When MW virtual sites are skipped during atom rendering (lines 126-138), the `visible_positions` array becomes shorter than the original `positions` array
- However, `molecule_indices` still references the ORIGINAL indices (including MW atoms)
- This causes incorrect slicing: `visible_positions[start_idx:end_idx]` uses wrong indices

**Impact:** Bonds detected between wrong atoms, causing incorrect molecular structure

### Issue 2: Water Replacement Message

**Location:** `quickice/gui/main_window.py` line 959

**Problem:** 
- Message said "Water replacement: Removed N water molecules to make room"
- Not clear and concise enough

### Issue 3: Ion Panel Solute Rendering

**Location:** `quickice/gui/main_window.py` lines 902-903

**Problem:** 
- When "Solute" source is selected for ion insertion, only the interface structure was rendered
- The solute molecules themselves were NOT rendered
- Ion viewer lacked support for solute actors and cleanup

## Fixes Applied

### Fix 1: Index Mapping in solute_renderer.py

**File:** `quickice/gui/solute_renderer.py`

**Changes:**
- Added `original_to_visible_idx` dictionary to track index mapping
- When skipping MW atoms, map each original index to its visible index
- Use mapped indices when slicing for bond detection
- This ensures bonds are detected between correct atoms even when MW atoms are skipped

**Code:**
```python
# Track which original indices map to visible atoms
original_to_visible_idx = {}  # Map original index -> visible index
visible_idx = 0

for orig_idx, (pos, name) in enumerate(zip(positions, atom_names)):
    element = get_element_from_atom_name(name)
    if element is None:
        continue  # Skip MW virtual sites
    
    # ... add atom ...
    original_to_visible_idx[orig_idx] = visible_idx
    visible_idx += 1

# When detecting bonds, use mapped indices
for start_idx, end_idx in molecule_indices:
    # Get visible atom indices for this molecule
    mol_visible_indices = []
    for orig_idx in range(start_idx, end_idx):
        if orig_idx in original_to_visible_idx:
            mol_visible_indices.append(original_to_visible_idx[orig_idx])
    
    # Detect bonds using visible indices
    # ...
```

### Fix 2: Water Replacement Message

**File:** `quickice/gui/main_window.py`

**Changes:**
- Line 959: Changed from "Water replacement: Removed N water molecules to make room"
- To: "Replaced N overlapping liquid water molecules"
- Clear, concise, and accurate

### Fix 3: Ion Panel Solute Rendering

**Files:** `quickice/gui/main_window.py`, `quickice/gui/ion_viewer.py`

**Changes in main_window.py:**
- Imported `create_solute_actor` from solute_renderer
- After ion insertion with "Solute" source, render solute molecules
- Add solute actor to renderer and store for cleanup

**Code:**
```python
# If source was Solute, also render the solute molecules
if current_source == "Solute" and hasattr(self, '_current_solute_result'):
    solute_structure = self._current_solute_result
    solute_actor = create_solute_actor(
        solute_structure.positions,
        solute_structure.atom_names,
        solute_structure.cell,
        molecule_indices=solute_structure.molecule_indices
    )
    if solute_actor and self.ion_panel.ion_viewer.renderer is not None:
        self.ion_panel.ion_viewer.renderer.AddActor(solute_actor)
        self.ion_panel.ion_viewer._solute_actors.append(solute_actor)
```

**Changes in ion_viewer.py:**
- Added `_solute_actors` list to track solute actors
- Added `_clear_solute_actors()` method for cleanup
- Updated `_clear_actors()` to also clear solute actors
- Updated `clear_interface_only()` to clear solute actors (since solutes are part of interface when source is "Solute")

## Verification

### Automated Tests

All tests pass:

1. **test_thf_ion_solute_fixes.py** - Verifies all three fixes:
   - ✓ Solute renderer index mapping with MW atoms
   - ✓ Water replacement message wording
   - ✓ Ion viewer solute support
   - ✓ Main window solute rendering

2. **test_cross_molecule_bonds.py** - Verifies critical fix:
   - ✓ Cross-molecule bonds correctly prevented
   - ✓ Bonds detected ONLY within each molecule

### Manual Verification Steps

To verify the fixes work in the actual application:

1. **THF Solute Bonds:**
   - Insert THF solute in liquid phase
   - Check bonds in 3D viewer
   - Expected: Correct THF ring structure with proper C-C, C-O, C-H bonds
   - No incorrect bonds between different THF molecules

2. **Water Replacement Message:**
   - Insert solutes that replace water molecules
   - Check log message
   - Expected: "Replaced N overlapping liquid water molecules"

3. **Ion Panel Solute Source:**
   - Insert solutes first
   - Go to Ion tab, select "Solute" source
   - Insert ions
   - Expected: Both solute molecules AND ions visible in viewer

## Technical Details

### Bond Detection Logic

The fix ensures that:
1. MW virtual sites are properly skipped during rendering
2. Original atom indices are correctly mapped to visible atom indices
3. Bond detection uses correct indices for each molecule
4. No cross-molecule bonds are created

### Memory Management

The ion_viewer now properly tracks and cleans up:
- Interface actors (ice + water)
- Solute actors (when source is "Solute")
- Ion actors (Na+, Cl-)
- Guest actors (from hydrate interface)

### Performance Impact

Minimal:
- Index mapping adds O(N) overhead where N = number of atoms
- Only executed during rendering, not during structure generation
- No impact on existing functionality

## Files Changed

1. `quickice/gui/solute_renderer.py` - Fixed index mapping for bond detection
2. `quickice/gui/main_window.py` - Updated message, added solute rendering
3. `quickice/gui/ion_viewer.py` - Added solute actor support and cleanup

## Conclusion

All three issues have been successfully fixed and verified:
- ✓ THF solute bonds now correct (same as hydrate THF)
- ✓ Water replacement message clear and concise
- ✓ Ion panel shows solutes when "Solute" source selected

The fixes are minimal, targeted, and maintain backward compatibility while addressing the root causes of all three issues.
