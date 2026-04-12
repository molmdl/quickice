# Triclinic Transformation - Gap Filling Context

**Created:** 2026-04-13
**Status:** Architectural issue identified, replanning recommended

---

## Summary

The triclinic-to-orthogonal transformer approach has fundamental architectural problems. Multiple debugging sessions have patched symptoms, but gaps persist because forcing triclinic crystals into orthogonal cells is inherently lossy.

---

## Issues Fixed (Chronological)

### Issue 1: atom_names Count Mismatch
- **Problem:** `atom_names` not replicated during transformation, causing ValueError
- **Fix:** Added `atom_names = atom_names * multiplier`
- **Commit:** 97f6158

### Issue 2: Tab 1 Viewer Error
- **Problem:** Transform applied to both tabs, breaking Tab 1 display
- **Fix:** Store original positions/cell in Candidate, Tab 1 uses original
- **Commit:** 9d21e1e

### Issue 3: Tooltip Chopped
- **Problem:** CSS max-width truncating tooltips
- **Fix:** Removed max-width, added newline formatting
- **Commit:** 1d4e52d

### Issue 4: Coordinate Transformation Bug
- **Problem:** Lattice indices used incorrectly as fractional coordinates
- **Fix:** Store supercell fractional coords directly, convert properly
- **Commit:** c614365

### Issue 5: Cell Dimensions for Tiling
- **Problem:** `get_cell_extent()` returned bounding box, not actual lengths
- **Fix:** Added `get_cell_dimensions()` for correct tiling sizes
- **Commit:** 699c1fb

### Issue 6: Molecules Broken During Tiling
- **Problem:** Fractional coordinate transformation broke O-H bonds
- **Fix:** Replicate Cartesian positions directly, wrap molecules as units
- **Commit:** 0cb4901

### Issue 7: Rotated Cell Gaps
- **Problem:** Transformed orthogonal cell rotated in space, tiling created gaps
- **Fix:** Align cell vectors to coordinate axes after transformation
- **Commit:** 9f57bd0

### Current State: Still Has Gaps
- Slab generation with Ice II produces ~2.8 nm gap in middle
- Structure not forming proper lattice
- Each fix addresses one symptom, reveals another

---

## Architectural Problem

The transformer approach is **fundamentally flawed**:

1. **Triclinic crystals have non-90° angles** - that's their natural geometry
2. **Forcing orthogonal representation** changes the lattice vectors
3. **Tiling doesn't fill space the same way** - creates gaps
4. **No library does this** because it's not how crystallography works
5. **GenIce produces correct triclinic cells** - forcing orthogonal is artificial

---

## Phase Transform Requirements

### Phases Requiring Transform (2):
| Phase | Crystal Form | Angles |
|-------|-------------|--------|
| Ice II | Rhombohedral | ~113°, ~113°, ~113° |
| Ice V | Monoclinic | 90°, β≠90°, 90° |

### Phases Already Orthogonal (no transform):
| Phase | Crystal Form |
|-------|-------------|
| Ice Ih | Hexagonal (GenIce produces orthogonal) |
| Ice Ic | Cubic |
| Ice III | Tetragonal |
| Ice VI | Tetragonal |
| Ice VII | Cubic |
| Ice VIII | Tetragonal |

---

## Two Options

### Option 1: Continue Debugging Transformer
- **Pros:** Preserves current architecture
- **Cons:** 
  - Already significant effort with persistent issues
  - Each fix reveals another problem
  - GenIce/spglib won't help (they produce/confirm triclinic, not transform)
  - May never be "perfect" because approach is wrong

### Option 2: Replan - Build Triclinic Interfaces Directly
- **Pros:**
  - Tab 1 already works with original triclinic
  - Scientifically correct
  - Simpler long-term
  - Removes ~300+ lines of transformer complexity
  - Works with crystal's natural periodicity
- **Cons:**
  - Requires interface builder to handle triclinic cells
  - Documentation updates needed
  - More upfront planning

### Recommendation: Option 2

---

## What Option 2 Would Require

### Code Changes:
1. **Interface builder (slab.py, pocket.py, piece.py)**
   - Handle non-orthogonal cell vectors for tiling
   - Triclinic PBC wrapping
   - Correct spatial positioning

2. **Export (gro.py, pdb.py)**
   - GRO already supports triclinic (9 box values)
   - PDB needs CRYST1 record with angles

3. **Visualization (molecular_viewer.py, vtk_utils.py)**
   - VTK handles triclinic via cell matrix
   - Already working in Tab 1

4. **Remove:**
   - `transformer.py` (~300+ lines)
   - Transform-related metadata in Candidate
   - Transform tests

### Documentation Updates:
- Explain triclinic vs orthogonal phases
- Update architecture docs
- User-facing explanation of cell types

---

## Key Files

### Transformer (to be removed):
- `quickice/structure_generation/transformer.py`
- `quickice/structure_generation/transformer_types.py`
- `tests/test_transformer.py`

### Interface Builder (to be updated):
- `quickice/structure_generation/modes/slab.py`
- `quickice/structure_generation/modes/pocket.py`
- `quickice/structure_generation/modes/piece.py`
- `quickice/structure_generation/tiler.py`

### Export (check triclinic support):
- `quickice/export/gro.py` - supports 9 box values
- `quickice/export/pdb.py` - needs CRYST1 with angles

---

## Debug Session Files

- `.planning/debug/resolved/triclinic-transform-issues.md`
- `.planning/debug/resolved/tab1-restore-original-triclinic.md`
- `.planning/debug/resolved/tooltip-wrap-newlines.md`
- `.planning/debug/resolved/triclinic-transform-function.md`
- `.planning/debug/resolved/tab2-transform-broken-piles.md`
- `.planning/debug/resolved/molecules-broken-tiling.md`
- `.planning/debug/resolved/slab-gap-transformed-ice.md`

---

## Sample Corrupted Output

File: `tmp/interface_slab_err.gro`
- Box: 5.192 x 8.992 x 10.501 nm
- Gap: 3.86-6.64 nm (2.8 nm of empty space)
- Bottom layer: 0-3.86 nm
- Top layer: 6.64-10.5 nm
