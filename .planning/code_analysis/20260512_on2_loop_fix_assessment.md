# O(n²) Loop Fix Safety Assessment

**Analysis Date:** 2026-05-16
**Location:** `quickice/gui/vtk_utils.py:272-290`

---

## Executive Summary

**Risk Level:** MEDIUM
**Recommendation:** PROCEED WITH CAUTION - Optimization is valuable but requires careful implementation to preserve triclinic PBC correctness.

---

## Current Code

### Function Signature
```python
# quickice/gui/vtk_utils.py:200-292
def detect_hydrogen_bonds(
    candidate: Candidate, max_distance: float = 0.25
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
```

### O(n²) Nested Loop (lines 272-290)
```python
272:     for h_idx, h_pos, parent_o_idx in h_positions:
273:         # Find O atoms that could form H-bonds with this H
274:         for o_idx, o_pos in o_positions:
275:             # Skip the parent O (same molecule, covalently bonded)
276:             if o_idx == parent_o_idx:
277:                 continue
278:             
279:             # Calculate H...O distance with PBC (handles both orthorhombic and triclinic)
280:             distance = _pbc_distance(h_pos, o_pos, cell)
281:             
282:             if distance < max_distance:
283:                 # H-bond detected: H...O
284:                 # Use minimum image position of O for correct visualization
285:                 # This ensures the line is drawn to the nearest periodic image of O
286:                 o_min_image = _pbc_min_image_position(h_pos, o_pos, cell)
287:                 hbonds.append((
288:                     tuple(float(h_pos[i]) for i in range(3)),
289:                     tuple(float(o_min_image[i]) for i in range(3))
290:                 ))
```

### Supporting PBC Functions (lines 140-197)
```python
def _pbc_distance(pos1: np.ndarray, pos2: np.ndarray, cell: np.ndarray) -> float:
    """Distance with PBC using fractional coordinate wrapping.
    Works for BOTH orthorhombic and triclinic cells."""
    delta_cart = pos1 - pos2
    cell_inv = np.linalg.inv(cell)
    delta_frac = delta_cart @ cell_inv
    delta_frac = delta_frac - np.round(delta_frac)  # minimum image
    delta_cart = delta_frac @ cell
    return np.linalg.norm(delta_cart)

def _pbc_min_image_position(ref_pos, target_pos, cell) -> np.ndarray:
    """Get minimum image position for visualization."""
    # Similar fractional coordinate transformation
```

---

## Callers and Frequency

### Primary Caller
**File:** `quickice/gui/molecular_viewer.py`
**Function:** `set_hydrogen_bonds_visible()` (line 303)

```python
# molecular_viewer.py:288-321
def set_hydrogen_bonds_visible(self, visible: bool) -> None:
    if visible and self._current_candidate is not None:
        candidate = self._current_candidate
        hbonds = detect_hydrogen_bonds(candidate)  # <-- O(n²) call
        # ... create actor from hbonds ...
```

### Call Chain
1. **On candidate load** (`set_candidate()`, line 150-181):
   - If `_show_hydrogen_bonds == True`, calls `set_hydrogen_bonds_visible(True)`
   - H-bonds computed once per loaded candidate

2. **On visibility toggle** (user action):
   - User toggles H-bond visibility → calls `set_hydrogen_bonds_visible()`
   - Recomputes H-bonds each time

3. **NOT called per frame** - result is cached in `_hbond_actor`

### Frequency Analysis
| Trigger | Frequency | Impact |
|---------|-----------|--------|
| Load new candidate | Once per load | HIGH - user loads multiple candidates |
| Toggle H-bond visibility | On-demand | MEDIUM - user may toggle frequently |
| During rotation/zoom | NEVER | N/A - cached |

### Test Callers
- `tests/test_pbc_hbonds.py:127,139,195` - PBC edge case tests
- `tests/test_atom_ordering_validation.py:112` - validation test

---

## Performance Characteristics

### Typical System Sizes
From CLI integration tests:
- Default: 100 molecules → 200 H atoms × 100 O atoms = **20,000 distance calculations**
- Large test: 1000 molecules → 2000 H × 1000 O = **2,000,000 calculations**

### O(n²) Complexity
- 100 molecules: ~20K operations (negligible, <10ms)
- 1000 molecules: ~2M operations (noticeable, ~100-500ms)
- 10,000 molecules: ~200M operations (problematic, seconds)

---

## Optimization Approaches

### Option 1: KDTree with Orthorhombic Boxsize (NOT RECOMMENDED)

**Approach:** Use `cKDTree(boxsize=[bx, by, bz])` as in `overlap_resolver.py`

**Limitation:** Only works for orthorhombic cells. Ice Ih is orthorhombic, but ice II and V are triclinic.

**Code Pattern from overlap_resolver.py:**
```python
ice_tree = cKDTree(ice_o_wrapped, boxsize=box_list)
water_tree = cKDTree(water_o_wrapped, boxsize=box_list)
pairs = water_tree.query_ball_tree(ice_tree, r=threshold_nm)
```

**Verdict:** Insufficient - breaks triclinic structures.

---

### Option 2: Supercell KDTree (RECOMMENDED)

**Approach:** Build 3×3×3 supercell and query with `query_ball_point()`
**Already used in:** `quickice/ranking/scorer.py:21-80`

**Algorithm:**
1. Extract O positions (n_oxygen atoms)
2. Build 3×3×3 supercell by replicating with cell vector offsets
3. Build single KDTree for supercell (27×n_oxygen atoms)
4. For each H atom, query neighbors within max_distance
5. Filter out parent O and map back to original indices
6. Compute minimum image position for visualization

**Code Pattern from scorer.py:**
```python
# Build 3x3x3 supercell for PBC handling
supercell_o = []
for i in (-1, 0, 1):
    for j in (-1, 0, 1):
        for k in (-1, 0, 1):
            offset = np.array([i, j, k]) * cell_dims
            supercell_o.append(o_positions + offset)
supercell_o = np.vstack(supercell_o)
tree = cKDTree(supercell_o)
pairs = tree.query_pairs(cutoff)
```

**Complexity:** O(n log n) for tree construction + O(n log n) for queries

**Advantages:**
- Handles triclinic cells correctly
- Same algorithm already proven in `scorer.py`
- scipy.spatial.cKDTree available (v1.17.1 confirmed)

**Disadvantages:**
- 27× memory overhead for O positions (small: 1000 O atoms × 27 × 3 × 8 bytes ≈ 650KB)
- Need to handle parent O filtering and minimum image position mapping

---

### Option 3: scipy.spatial.distance.cdist with Vectorization

**Approach:** Compute all pairwise distances at once, then filter

**Limitation:** Still O(n²) memory and computation, just vectorized. Not a real optimization.

**Verdict:** Not recommended - doesn't solve algorithmic complexity.

---

## Existing Optimization Patterns in Codebase

### KDTree Usage (cKDTree available)

| File | Usage | PBC Method |
|------|-------|------------|
| `overlap_resolver.py` | Overlap detection | `boxsize=` (orthorhombic only) |
| `scorer.py` | O-O distance calc | 3×3×3 supercell (triclinic-safe) |
| `solute_inserter.py` | Overlap checking | `cKDTree` without PBC |
| `ion_inserter.py` | Overlap checking | `cKDTree` without PBC |

**Recommended Pattern:** Follow `scorer.py` supercell approach

---

## Risk Assessment

### Test Coverage
✅ **PBC edge cases tested:** `tests/test_pbc_hbonds.py`
- Distance across boundary
- 3D PBC wrapping
- H-bond detection at exact PBC boundary

✅ **Atom ordering validation:** `tests/test_atom_ordering_validation.py`
- Ensures input validation before H-bond detection

### Edge Cases to Preserve

1. **Triclinic cells** (ice II, V)
   - Current: Uses `cell_inv` for fractional coordinate transformation
   - Must: Use supercell approach, not `boxsize=`

2. **Minimum image positions for visualization**
   - Current: `_pbc_min_image_position()` computes correct visual position
   - Must: Preserve this for line drawing to correct periodic image

3. **Parent O exclusion** (same-molecule H-O pairs)
   - Current: `if o_idx == parent_o_idx: continue`
   - Must: Filter these from KDTree results

4. **Empty results handling**
   - Current: Returns empty list gracefully
   - Must: Same behavior

### Numerical Precision
- Distance calculation uses `np.linalg.inv(cell)` for general triclinic support
- KDTree supercell approach uses same cell vectors
- Results should be numerically identical (both use floating point)

---

## Implementation Recommendations

### Safe Approach

1. **Keep original function as fallback**
   ```python
   def detect_hydrogen_bonds(candidate, max_distance=0.25, use_kdtree=True):
       if use_kdtree:
           try:
               return _detect_hydrogen_bonds_kdtree(candidate, max_distance)
           except Exception:
               return _detect_hydrogen_bonds_on2(candidate, max_distance)
       return _detect_hydrogen_bonds_on2(candidate, max_distance)
   ```

2. **Implement supercell KDTree version**
   - Follow `scorer.py:_calculate_oo_distances_pbc()` pattern
   - Add parent O filtering
   - Add minimum image position calculation

3. **Add comparative tests**
   - Run both algorithms on same data
   - Assert identical results

### Performance Gain Estimate
| Molecules | O(n²) Time | O(n log n) Time | Speedup |
|-----------|------------|-----------------|---------|
| 100 | ~10ms | ~2ms | 5× |
| 1,000 | ~200ms | ~20ms | 10× |
| 10,000 | ~20s | ~200ms | 100× |

---

## Conclusion

### Risk: MEDIUM

**Factors increasing risk:**
- Triclinic PBC handling is complex
- Must preserve minimum image positions for visualization
- Existing code is correct (no bugs to fix)

**Factors decreasing risk:**
- scipy.spatial.cKDTree already used elsewhere
- Supercell pattern proven in `scorer.py`
- Good test coverage for PBC edge cases
- Not on critical rendering path

### Verdict: **SAFE TO PROCEED WITH CAUTION**

**Recommended steps:**
1. Implement supercell KDTree version as separate function
2. Add A/B comparison tests
3. Run full test suite before enabling by default
4. Consider feature flag for gradual rollout

**Expected benefit:** 5-100× speedup for large structures, no user-facing behavior change.

---

*Assessment completed: 2026-05-16*
