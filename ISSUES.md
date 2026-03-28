# Phase Diagram Polygon Issues

> Status: **Open** - Requires thermodynamic boundary verification

## Summary

Phase diagram polygons have gaps between some boundaries and overlaps in others. The polygon definitions need verification against thermodynamic phase boundaries.

---

## Issue 1: Polygon Gaps

### a. Ih-XI Gap
- **Location**: Between Ice Ih (T=72-273K) and Ice XI (T=50-72K)
- **Problem**: Gap exists at the boundary where Ih ends and XI should take over
- **Expected**: Polygons should meet at T≈72K with matching pressures (~196 MPa)

### b. IX-II Gap  
- **Location**: Between Ice IX and Ice II boundaries
- **Problem**: No continuous boundary between these phases
- **Expected**: Either direct boundary connection or identification of intermediate phase

### c. IX-VI Gap
- **Location**: Between Ice IX (T=100-140K, P=200-400 MPa) and Ice VI
- **Problem**: Gap exists in the P=400-620 MPa region
- **Expected**: Proper boundary connection or identification of missing phase

---

## Issue 2: Polygon Overlaps

### a. XV Overlaps VI
- **Location**: Ice XV extends beyond its thermodynamic region
- **Problem**: XV polygon overlaps with Ice VI region
- **Fix needed**: Restrict XV to T=80-108K, P≈1100 MPa without extending to meet VI

### b. Ih Covers XI
- **Location**: Ice Ih extends into Ice XI region
- **Problem**: Ih polygon covers the entire XI region at low temperature
- **Fix needed**: Ih should stop at T≈72K where XI begins

---

## Issue 3: Size Issues

### XV Too Small
- **Problem**: Ice XV exists in a narrow T=80-108K, P≈1100 MPa band
- **Note**: This may be thermodynamically correct - XV is only stable in this narrow region
- **Action**: Verify against literature; may need to accept as-is or expand for visualization

---

## Root Cause

Polygon vertices are defined with fixed boundaries that don't properly meet at triple points:
1. Boundary functions from `solid_boundaries.py` have discontinuities
2. Fixed vertex definitions override actual boundary intersections
3. No dynamic checking that polygons are gapless and non-overlapping

---

## Files to Review

| File | Purpose |
|------|---------|
| `quickice/output/phase_diagram.py` | Polygon vertex definitions |
| `quickice/phase_mapping/solid_boundaries.py` | Boundary curve functions |
| `quickice/phase_mapping/__init__.py` | Triple point definitions |

---

## Debug History

| Session | Date | Issue | Resolution |
|---------|------|-------|------------|
| polygon-gaps-in-diagram | 2026-03-27 | Gaps: Ih-XI, II-IX, XV isolated, VIII-X | Extended polygons - created overlaps |
| fix-polygon-overlaps | 2026-03-27 | Overlaps: XV, IX/II, Ih covers XI | Corrected boundaries - created new gaps |

---

## Suggested Approach

1. **Use boundary functions dynamically** - Instead of fixed vertices, compute boundaries at render time using curve functions
2. **Add validation** - Check for gaps/overlaps before rendering
3. **Consult phase diagram literature** - Verify actual boundary connections
4. **Accept small gaps if thermodynamically correct** - Some regions may have no ice phase

---

*Last updated: 2026-03-28*