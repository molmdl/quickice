# Issue Verification Report

## Summary

**Date:** 2026-05-03
**Files Verified:**
- tmp/ice/ice_ih_273K_0.10MPa_c1.gro
- tmp/ch4/hydrate_sI_ch4_1x1x1.gro
- tmp/thf/hydrate_sII_thf_1x1x1.gro
- sample_output/gui_v4/ice/ice_ih_273K_0.10MPa_c1.gro
- sample_output/gui_v4/ch4/hydrate_sI_ch4_1x1x1.gro
- sample_output/gui_v4/thf/hydrate_sII_thf_1x1x1.gro

---

## Issue #15: Overlap/Duplication in Exported GRO

### Status: ❌ NOT FIXED (Ice Ih only)

**Findings:**
- **Ice Ih:** 6 overlapping molecule pairs detected
  - SOL5 vs SOL6: 0.0082nm
  - SOL11 vs SOL12: 0.0083nm
  - SOL59 vs SOL60: 0.0421nm
  - SOL62 vs SOL63: 0.0382nm
  - SOL78 vs SOL79: 0.0402nm
  - (and 1 more pair)

- **CH4 Hydrate:** ✅ No overlaps
- **THF Hydrate:** ✅ No overlaps

**Note:** These are inter-molecular overlaps (different water molecules), not intramolecular OW-MW overlaps which are expected in TIP4P/Ice.

---

## Issue #16: PBC Unit Cell Completeness

### Status: ⚠️ PARTIAL (Ice Ih only)

**Findings:**
- **Ice Ih:** 8 water molecules split across PBC boundaries
  - Water 5: O-H distance d2=1.377nm (should be ~0.096nm)
  - Water 12: O-H distance d1=1.377nm
  - Water 60: O-H distance d2=1.377nm
  - Water 62: O-H distance d1=1.377nm
  - Water 78: O-H distance d2=1.376nm
  - (and 3 more waters)

- **CH4 Hydrate:** ✅ All molecules complete
- **THF Hydrate:** ✅ All molecules complete

**Pattern:** All affected waters have one hydrogen (HW2) wrapped to y≈1.468 while oxygen is at y≈0.1, creating the 1.377nm gap.

---

## Root Cause Analysis

### Overlap Issue (#15)
The overlaps in Ice Ih suggest that water molecules from different unit cells are being placed too close together. The overlap distances (0.008-0.042nm) indicate that the molecules are nearly on top of each other.

### PBC Issue (#16)
The HW2 atoms being wrapped to y≈1.468 while OW is at y≈0.1 suggests a periodic boundary condition wrapping issue during structure generation or export. The 1.377nm gap matches the box y-dimension minus the expected y-position.

---

## File Comparison

- tmp/ice and sample_output/gui_v4/ice files are **IDENTICAL**
- Both have the same issues
- Files were generated on May 3, after commits 7c72fae (duplicate fix) and 33e0219 (PBC fix)

---

## Conclusion

**Issue #15:** ❌ NOT FIXED for Ice Ih
- Hydrate files (ch4, thf) are fine
- Ice Ih has 6 overlapping molecule pairs

**Issue #16:** ⚠️ PARTIAL
- Hydrate files are complete
- Ice Ih has 8 waters split across PBC

**Recommendation:** The fixes in commits 7c72fae and 33e0219 work for hydrate structures but Ice Ih generation still has issues. May need to regenerate the Ice Ih files or apply additional fixes specific to Ice Ih structure generation.

---

## Related Commits

- 7c72fae: fix: Prevent duplicate molecules in tile_structure by fixing over-tiling bug
- 33e0219: fix: improve molecule unwrapping and exclude MW virtual sites
- 9cf4551: fix: adjust water dimensions to periodicity to prevent overlapping water molecules
