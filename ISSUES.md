# QuickIce - Open Issues

**Last Updated:** 2026-04-10

---

## Resolved Issues

### Issue 1: Interface GRO Export Error ✅
- **Commit:** 721d9b2
- **Root Cause:** `write_gro_file()` assumed 4 atoms/mol but ice Candidates have 3 atoms/mol
- **Fix:** Corrected indexing to use `mol_idx * 3`, compute MW at export time

### Issue 2: Missing Documentation on Unsupported Phase in Interface ✅
- **Commit:** e29f65d
- **Root Cause:** Users could generate ice_ii and ice_v candidates in Tab 1 but fail in Tab 2 with no prior explanation
- **Fix:** Added "Interface Construction Limitation" note to README.md and "Phase Compatibility" section to gui-guide.md
- **Note:** Documentation now clearly states that Ice II (rhombohedral) and Ice V (monoclinic) have triclinic cells and are not supported for interface construction

### Issue 3: Wrong H-bonds in Tab 1 (REGRESSION) ✅
- **Commits:** 4783a73 (H-bond fix), 3ca893b (triclinic validation)
- **Root Cause:** After triclinic PBC fix (commit dee7802), H-bond visualization showed wrong bonds because `detect_hydrogen_bonds()` returned raw O positions without minimum-image correction. When H-bonds crossed periodic boundaries, lines were drawn to wrong periodic images.
- **Fix:** Added `_pbc_min_image_position()` helper and modified `detect_hydrogen_bonds()` to return minimum-image corrected O positions. Also reverted MolecularViewerWidget to use VTK's built-in bond rendering for covalent O-H bonds.
- **Additional Fix:** Added triclinic cell validation to all interface mode functions to provide clear error messages for unsupported phases.

### Issue 4: PBC Overlap in Interface Slab Mode ✅
- **Commits:** 3ca893b (triclinic validation), 6ea4bc4 (slab PBC overlap fix)
- **Root Cause (Part 1):** Mode functions extracted only diagonal elements of cell matrix, discarding off-diagonal tilt factors. This caused incorrect tiling for triclinic cells.
- **Fix (Part 1):** Added `_is_cell_orthogonal()` helper and triclinic validation to all mode functions (slab, pocket, piece).
- **Root Cause (Part 2):** `tile_structure` wrapping logic used `if-elif` structure which only applied one correction at a time. When `min_pos < 0`, shifting up could push `max_pos >= target_region`, creating atoms outside the box. This affected orthogonal phases Ic, VII, VIII.
- **Fix (Part 2):** Added second pass in wrapping logic to check if any atoms are still outside `[0, target_region)` after initial shift, and apply additional `+/-target_region` shift if needed.
- **Verification:** All orthogonal phases (Ih, Ic, III, VI, VII, VIII) now work correctly with slab mode.

### Issue: Phase Diagram Click Lookup Mismatch ✅
- **Commit:** d2346f5
- **Root Cause:** Phase diagram polygons for Ice XV, Ice VI, and Ice II didn't match `lookup_phase()` conditions, causing `PhaseDetector` (used by diagram clicks) to return different phases than `lookup_phase()` (used for structure generation).
- **Fix:** Aligned polygon definitions with `lookup_phase()` conditions:
  - XV polygon: Changed T range from 50-100K to 80-108K
  - VI polygon: Changed start T from 100K to 108K
  - VI lookup: Added check for T=108-218K to fill gap
  - II polygon: Extended to P=2100 MPa for T < 80K

---

## Summary

| Issue | Description | Status | Commits |
|-------|-------------|--------|---------|
| 1 | Interface GRO export error | ✅ Fixed | 721d9b2 |
| 2 | Missing doc on unsupported phases | ✅ Fixed | e29f65d |
| 3 | Wrong H-bonds (regression) | ✅ Fixed | 4783a73, 3ca893b |
| 4 | PBC overlap in slab mode | ✅ Fixed | 3ca893b, 6ea4bc4 |
| - | Phase diagram lookup mismatch | ✅ Fixed | d2346f5 |

All issues from debug session dump resolved.