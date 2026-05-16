---
phase: 022-optimize-hbond-detection-kdtree
plan: 01
subsystem: core-performance
tags: [optimization, kdtree, hbonds, pbc, triclinic]
completed: 2026-05-16
duration: "25 minutes"
---

# Phase 022 Plan 01: Optimize H-bond Detection with KDTree Summary

## One-Liner

Optimized H-bond detection from O(n²) to O(n log n) using scipy.spatial.cKDTree with triclinic PBC support.

## Status

✅ **COMPLETE** - All tasks executed successfully, A/B tests verified numerical equivalence.

## Objective

Reduce H-bond detection from O(n²) to O(n log n) complexity, enabling faster candidate loading for large systems (1000+ molecules).

## Tasks Completed

| Task | Description | Status | Commit |
|------|-------------|--------|--------|
| 1 | Implement triclinic-aware supercell KDTree function | ✅ Complete | 447885c |
| 2 | Create A/B comparison tests for numerical equivalence | ✅ Complete | db9badd |
| 3 | Replace original function after A/B tests pass | ✅ Complete | d4a333e |

## Implementation Details

### Algorithm Change

**Before (O(n²) nested loop):**
```python
for h_idx, h_pos, parent_o_idx in h_positions:
    for o_idx, o_pos in o_positions:
        if o_idx != parent_o_idx:
            distance = _pbc_distance(h_pos, o_pos, cell)
            if distance < max_distance:
                o_min_image = _pbc_min_image_position(h_pos, o_pos, cell)
                hbonds.append((h_pos, o_min_image))
```

**After (O(n log n) KDTree):**
```python
# Build 3x3x3 supercell for H atoms
supercell_h = []
for i in (-1, 0, 1):
    for j in (-1, 0, 1):
        for k in (-1, 0, 1):
            offset = i * cell[0] + j * cell[1] + k * cell[2]
            supercell_h.append(h_coords + offset)

# Build KDTree from supercell
tree = cKDTree(supercell_h)

# Query O atoms against KDTree
for o_pos in o_coords:
    indices = tree.query_ball_point(o_pos, max_distance)
    # Process matches...
```

### Key Design Decisions

1. **Triclinic cell handling**: Use full cell matrix for offsets (`i*cell[0] + j*cell[1] + k*cell[2]`) instead of diagonal extraction
2. **Query pattern**: Query O atoms against H supercell (reverse of scorer.py pattern)
3. **Visualization consistency**: Return H atoms in central cell, O atoms in minimum image position
4. **Same-molecule filtering**: Track parent O index to skip covalently bonded O atoms

### Bug Fix

**Issue:** Initial implementation returned H atoms in supercell images instead of central cell.

**Fix:** Use central cell H position (`h_pos`) instead of supercell position (`h_supercell_pos`) for visualization consistency.

**Impact:** A/B tests revealed 0.1 nm discrepancy in PBC edge case test. Fixed in commit db9badd.

## Test Results

### A/B Comparison Tests (Before Replacement)

All 5 A/B tests passed with numerical equivalence (< 1e-10 nm tolerance):

| Test | Description | Result |
|------|-------------|--------|
| test_optimized_matches_original_simple | 2 molecules, no PBC | ✅ Pass |
| test_optimized_matches_original_pbc | PBC edge case | ✅ Pass |
| test_optimized_matches_original_random | 100 random molecules | ✅ Pass |
| test_optimized_matches_original_triclinic | Triclinic cell (tilted) | ✅ Pass |
| test_performance_improvement | Timing comparison | ✅ Pass |

### Existing PBC Tests (After Replacement)

All 6 existing PBC tests passed:

```
tests/test_pbc_hbonds.py::TestPBCDistance::test_pbc_distance_across_boundary PASSED
tests/test_pbc_hbonds.py::TestPBCDistance::test_pbc_distance_within_box PASSED
tests/test_pbc_hbonds.py::TestPBCDistance::test_pbc_distance_3d PASSED
tests/test_pbc_hbonds.py::TestHydrogenBondDetection::test_detect_hbonds_simple PASSED
tests/test_pbc_hbonds.py::TestHydrogenBondDetection::test_detect_hbonds_with_pbc PASSED
tests/test_pbc_hbonds.py::TestHydrogenBondDetection::test_detect_hbonds_pbc_edge_case PASSED
```

### All H-bond Tests

7/7 H-bond related tests passed (including atom ordering validation).

## Performance Metrics

### Expected Speedup

- **100 molecules:** ~2-5x faster
- **1000 molecules:** ~10-50x faster
- **Complexity:** O(n²) → O(n log n)

### Memory Overhead

27x supercell construction (standard for PBC handling with KDTree).

## Files Modified

### Created
- None

### Modified
- `quickice/gui/vtk_utils.py`:
  - Added `scipy.spatial.cKDTree` import
  - Replaced `detect_hydrogen_bonds()` implementation
  - Updated docstring with performance notes

- `tests/test_pbc_hbonds.py`:
  - Moved `simple_candidate` and `pbc_candidate` fixtures to module level
  - Added `TestKDTreeOptimization` class with 5 A/B tests
  - Removed A/B tests after replacement verified
  - Reduced from 11 tests to 6 tests (A/B tests no longer needed)

## Deviations from Plan

None - plan executed exactly as written.

## Lessons Learned

1. **A/B testing is essential for optimization**: Caught visualization bug that would have broken PBC edge cases
2. **Triclinic cells need full matrix**: Using `np.diag(cell)` breaks non-orthorhombic cells
3. **Visualization consistency matters**: H atoms should stay in central cell for proper line rendering
4. **Test coverage is critical**: Existing PBC tests caught no regressions, A/B tests verified correctness

## Success Criteria

✅ All A/B tests pass with numerical equivalence (< 1e-10 nm)
✅ Triclinic PBC handling verified correct
✅ Performance improvement demonstrated (O(n log n) vs O(n²))
✅ All existing PBC tests pass (6/6)
✅ No breaking changes to function signature or behavior
✅ Code committed with descriptive messages

## Next Steps

None - optimization complete and verified.

## Dependencies

### Requires
- scipy (already in dependencies)

### Provides
- Optimized H-bond detection for all ice types
- Faster candidate loading for large systems

### Affects
- `quickice.gui.molecular_viewer` (uses detect_hydrogen_bonds)
- Future: could be used for other PBC-aware distance calculations
